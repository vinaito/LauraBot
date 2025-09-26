# Chatbot PDF TCC da Laura

Este projeto mostra como criar um **chatbot** que responde perguntas sobre um documento PDF específico — por exemplo, o artigo de conclusão de curso da Laura.  A aplicação utiliza a técnica de **Retrieval‑Augmented Generation (RAG)**, que separa o texto em trechos menores, calcula vetores de similaridade (embeddings) e recupera trechos relevantes para compor a resposta do modelo.  Esse método complementa o modelo de linguagem com uma base de conhecimento externa e reduz alucinações, pois a resposta se apoia nas partes do documento encontradas【840513880517767†L7-L9】.

Os vetores de similaridade são armazenados em um índice **FAISS**.  O FAISS é uma biblioteca de busca de vizinhos próximos otimizada para velocidade e uso de memória【323587071565007†L47-L51】【323587071565007†L117-L124】.  Ao fazer uma pergunta, o aplicativo gera o embedding da consulta, recupera os trechos mais próximos e passa esse contexto para o modelo da OpenAI gerar a resposta.

## Pré‑requisitos

- **Python 3.9** ou superior.
- Uma chave de API da OpenAI.  Você pode obter uma chave em <https://platform.openai.com/account/api-keys> e armazená‑la como variável de ambiente ou informá‑la na interface Streamlit.
- Instale as dependências executando:

```bash
pip install -r requirements.txt
```

## Como usar localmente

1. Copie ou clone este diretório `streamlit_pdf_chatbot` para sua máquina.
2. No terminal, navegue até a pasta do projeto e instale as dependências (`pip install -r requirements.txt`).
3. Execute a aplicação Streamlit:

   ```bash
   streamlit run app.py
   ```

4. No navegador que abrir, você verá campos para inserir sua chave da OpenAI e carregar o PDF.  Após o upload, o aplicativo lerá o documento, construirá o índice e habilitará o campo de perguntas.
5. Digite perguntas em linguagem natural.  O chatbot buscará trechos relevantes e responderá em português, citando as páginas usadas quando possível.  Caso o assunto esteja fora do escopo do documento, ele informará que não encontrou a resposta.

## Implantação no Streamlit Community Cloud

Para compartilhar o chatbot com outras pessoas ou apresentá‑lo ao professor, você pode hospedá‑lo gratuitamente no [Streamlit Community Cloud](https://streamlit.io/cloud):

1. Crie um repositório no GitHub contendo os arquivos deste projeto (`app.py`, `requirements.txt`, `README.md` etc.).
2. Acesse o Streamlit Cloud, clique em **“New app”** e selecione seu repositório.  Escolha a branch correta (por exemplo, `main`).
3. Em **Advanced settings**, adicione um *secret* chamado `OPENAI_API_KEY` contendo sua chave da OpenAI.  Assim você não precisa expor a chave na interface.
4. Clique em **Deploy**.  Quando a aplicação iniciar, ela pedirá o upload do PDF e permitirá fazer perguntas.

## Estrutura dos arquivos

- **`app.py`** – código principal do Streamlit; cuida do upload do PDF, da criação do índice FAISS e das interações do chat.
- **`requirements.txt`** – lista de bibliotecas necessárias para executar o projeto.
- **`README.md`** – este guia com instruções de uso e implantação.

## Notas importantes

- A técnica RAG funciona dividindo o documento em pedaços e adicionando uma sobreposição entre eles para não cortar informações importantes【840513880517767†L13-L15】.  O tamanho e a sobreposição podem ser ajustados no código (`chunk_size` e `chunk_overlap`).
- O modelo de embedding usado é `text-embedding-3-large` da OpenAI; ele fornece boa representação e está disponível através da API.  Se preferir, você pode substituir por outro modelo compatível.
- O índice FAISS é reconstruído toda vez que um novo PDF é carregado.  Para documentos muito grandes, esse processo pode demorar alguns minutos.
- Sempre que uma pergunta não tiver resposta no documento, a aplicação tenta avisar em vez de inventar fatos.  Isso ajuda a manter a confiança no chatbot.

Com estes passos, você terá um chatbot simples e eficiente para o trabalho de conclusão de curso da Laura!