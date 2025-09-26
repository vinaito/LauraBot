"""Aplicação Streamlit para perguntar sobre um PDF específico.

Esta aplicação demonstra um pipeline simples de Retrieval‑Augmented Generation (RAG)
para responder perguntas sobre um documento PDF.  Ela realiza as seguintes etapas:

1. Faz o upload de um PDF e extrai o texto de cada página.
2. Divide o texto em trechos (chunks) com sobreposição para preservar o contexto.
3. Gera embeddings para cada trecho usando a API de embeddings da OpenAI.
4. Indexa os vetores em uma estrutura FAISS para busca eficiente de vizinhos mais próximos.
5. Quando o usuário faz uma pergunta, gera o embedding da pergunta, recupera os trechos
   mais relevantes e monta um prompt para a API de chat da OpenAI responder em
   português, citando as páginas do documento.

Para executar:

```
streamlit run app.py
```

Necessita de uma chave de API da OpenAI (`OPENAI_API_KEY`).  Você pode informá‑la
por um campo na interface ou definindo a variável de ambiente homônima.
"""

import os
from typing import List, Dict, Tuple

import numpy as np
import streamlit as st

try:
    import openai  # type: ignore
except ImportError:
    openai = None  # A API não está instalada em tempo de desenvolvimento.

try:
    import faiss  # type: ignore
except ImportError:
    faiss = None  # Faiss será importado apenas em tempo de execução.

try:
    from pypdf import PdfReader  # type: ignore
except ImportError:
    from PyPDF2 import PdfReader  # type: ignore


def extract_text_from_pdf(file) -> List[str]:
    """Extrai o texto de cada página de um PDF.

    Args:
        file: arquivo PDF carregado via Streamlit (UploadedFile ou arquivo em disco).

    Returns:
        Lista de strings, uma por página.
    """
    reader = PdfReader(file)
    pages = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text()
        except Exception:
            text = ""
        pages.append(text or "")
    return pages


def chunk_pages(pages: List[str], chunk_size: int = 500, overlap: int = 50) -> Tuple[List[str], List[Dict]]:
    """Divide o texto de cada página em pedaços menores com sobreposição.

    Os pedaços são gerados palavra a palavra para aproximar a contagem de tokens.  O
    parâmetro `chunk_size` define aproximadamente quantas palavras cada trecho deve
    conter, enquanto `overlap` define quantas palavras do final do trecho anterior
    devem se repetir no início do próximo.  Ambos ajudam a preservar o contexto.

    Args:
        pages: lista de strings contendo o texto de cada página.
        chunk_size: número aproximado de palavras por trecho.
        overlap: número de palavras a sobrepor entre trechos consecutivos.

    Returns:
        Uma tupla com a lista de trechos de texto e uma lista de metadados.  Cada
        metadado é um dicionário contendo a página de origem e a posição do trecho.
    """
    chunks: List[str] = []
    metadata: List[Dict] = []
    for page_num, page_text in enumerate(pages, start=1):
        words = page_text.split()
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)
            if chunk_text.strip():
                chunks.append(chunk_text)
                metadata.append({"page": page_num})
            # Avança start respeitando a sobreposição
            start += max(chunk_size - overlap, 1)
    return chunks, metadata


def compute_embeddings(texts: List[str], api_key: str, model: str = "text-embedding-3-large") -> np.ndarray:
    """Calcula embeddings para uma lista de textos usando a API da OpenAI.

    Args:
        texts: lista de strings a serem embedadas.
        api_key: chave de API da OpenAI para autenticação.
        model: nome do modelo de embeddings da OpenAI.

    Returns:
        Array NumPy de forma (n, d) contendo os embeddings em formato float32.
    """
    if openai is None:
        raise ImportError(
            "openai não está instalado. Por favor, instale as dependências listadas em requirements.txt"
        )
    openai.api_key = api_key
    embeddings = []
    for text in texts:
        try:
            response = openai.Embedding.create(input=text, model=model)
            embedding = response["data"][0]["embedding"]
            embeddings.append(embedding)
        except Exception as e:
            # Em caso de erro, registra e usa um vetor zero como fallback
            st.warning(f"Erro ao gerar embedding: {e}")
            embeddings.append([0.0] * 1536)
    return np.array(embeddings, dtype="float32")


def build_faiss_index(vectors: np.ndarray) -> "faiss.IndexFlatL2":
    """Cria um índice FAISS usando distância Euclidiana (L2).

    Args:
        vectors: array bidimensional com embeddings.

    Returns:
        Índice FAISS pronto para buscas de k vizinhos mais próximos.
    """
    if faiss is None:
        raise ImportError(
            "faiss-cpu não está instalado. Por favor, instale as dependências listadas em requirements.txt"
        )
    dimension = vectors.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(vectors)
    return index


def search_index(index: "faiss.IndexFlatL2", query_vector: np.ndarray, k: int = 5) -> np.ndarray:
    """Retorna os índices dos k trechos mais semelhantes ao vetor de consulta.

    Args:
        index: índice FAISS treinado.
        query_vector: vetor de embedding da pergunta.
        k: número de vizinhos a retornar.

    Returns:
        Array 1D com os índices dos trechos mais semelhantes.
    """
    distances, indices = index.search(query_vector.astype("float32"), k)
    return indices[0]


def generate_answer(api_key: str, context: str, question: str) -> str:
    """Envia um prompt para a API de chat da OpenAI e retorna a resposta.

    O prompt inclui o contexto recuperado do documento e a pergunta do usuário.  O
    modelo é instruído a responder em português de forma educada e a citar as
    páginas do documento quando usar informações do texto.

    Args:
        api_key: chave de API da OpenAI.
        context: trechos concatenados recuperados do índice.
        question: pergunta formulada pelo usuário.

    Returns:
        Resposta gerada pelo modelo.
    """
    if openai is None:
        raise ImportError(
            "openai não está instalado. Por favor, instale as dependências listadas em requirements.txt"
        )
    openai.api_key = api_key
    system_prompt = (
        "Você é um assistente útil que responde a perguntas sobre um artigo de \n"
        "trabalho de conclusão de curso.  Use **apenas** as informações presentes no \n"
        "contexto fornecido para formular sua resposta.  Responda em português e \n"
        "cite as páginas relevantes entre parênteses sempre que usar um trecho. \n"
        "Se a resposta não estiver no contexto, informe que não há informação suficiente."
    )
    user_prompt = (
        f"Contexto:\n{context}\n\n"
        f"Pergunta: {question}\n\n"
        "Resposta:"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=512,
        )
        answer = response["choices"][0]["message"]["content"].strip()
        return answer
    except Exception as e:
        st.error(f"Erro ao chamar OpenAI: {e}")
        return "Erro ao gerar resposta."


def main() -> None:
    """Função principal que define a interface Streamlit."""
    st.set_page_config(page_title="Chatbot do TCC da Laura", page_icon="📄")
    st.title("📄 Chatbot do TCC da Laura")

    st.markdown(
        "Faça upload do PDF do trabalho de conclusão de curso e pergunte sobre o conteúdo. "
        "O chatbot utiliza embeddings e busca vetorial para encontrar trechos relevantes."
    )

    # Campo para chave de API.  Também pode ser definido via variável de ambiente.
    default_key = os.environ.get("OPENAI_API_KEY", "")
    api_key = st.text_input(
        "Chave da API da OpenAI", value=default_key, type="password", help="Obtenha uma chave em https://platform.openai.com/account/api-keys"
    )

    # Upload do PDF
    uploaded_file = st.file_uploader("Carregue o PDF do artigo", type=["pdf"])

    # Estado para indexação e metadados
    if "index" not in st.session_state:
        st.session_state.index = None  # type: ignore
        st.session_state.embeddings = None  # type: ignore
        st.session_state.chunks = None  # type: ignore
        st.session_state.metadata = None  # type: ignore

    # Processa PDF e constrói índice
    if uploaded_file is not None and api_key:
        if st.session_state.index is None:
            with st.spinner("Processando PDF e construindo índice..."):
                pages = extract_text_from_pdf(uploaded_file)
                chunks, metadata = chunk_pages(pages, chunk_size=500, overlap=50)
                embeddings = compute_embeddings(chunks, api_key)
                index = build_faiss_index(embeddings)
                # Armazena no estado
                st.session_state.index = index
                st.session_state.embeddings = embeddings
                st.session_state.chunks = chunks
                st.session_state.metadata = metadata
            st.success("Índice construído com sucesso! Agora você pode fazer perguntas.")
    elif uploaded_file is not None and not api_key:
        st.info("Informe sua chave da OpenAI para processar o PDF.")

    # Interface de pergunta
    if st.session_state.index is not None:
        question = st.text_input("Digite sua pergunta")
        if question:
            if not api_key:
                st.info("Informe sua chave da OpenAI para gerar a resposta.")
            else:
                # Gera embedding da pergunta e recupera trechos
                with st.spinner("Procurando trechos relevantes..."):
                    try:
                        q_embed_resp = openai.Embedding.create(input=question, model="text-embedding-3-large")
                        q_vector = np.array([q_embed_resp["data"][0]["embedding"]], dtype="float32")
                        top_indices = search_index(st.session_state.index, q_vector, k=5)
                        context_pieces = []
                        citations = []
                        for idx in top_indices:
                            text = st.session_state.chunks[idx]
                            meta = st.session_state.metadata[idx]
                            page_label = f"pág. {meta['page']}"
                            context_pieces.append(text)
                            citations.append(page_label)
                        context = "\n---\n".join(context_pieces)
                        answer = generate_answer(api_key, context, question)
                    except Exception as e:
                        st.error(f"Erro ao gerar embedding ou buscar trechos: {e}")
                        answer = ""
                if answer:
                    st.markdown("### Resposta")
                    st.write(answer)
                    # Exibe citações usadas
                    st.markdown("**Trechos utilizados (páginas):** " + ", ".join(citations))


if __name__ == "__main__":
    main()