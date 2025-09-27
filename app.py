"""Guia gastronômico de Pinheiros com interface de chat e módulo de atualização.

Este aplicativo em Streamlit permite que a jornalista Laura mantenha seu
conteúdo sobre restaurantes de Pinheiros de forma simples. A base de dados
estruturada é lida de um arquivo JSON (`pinheiros_restaurants.json`),
que é usado para responder às perguntas de forma estruturada e eficiente.
Para facilitar a atualização, o app também aceita um arquivo de texto
(`*.txt`) com descrições em linguagem natural (um restaurante por
parágrafo). Ao carregar esse arquivo, o modelo da OpenAI analisa
automaticamente as descrições e converte para o formato JSON,
atualizando a base estruturada. O prompt utilizado pelo modelo é
lido de `prompt.txt`, permitindo ajustes sem mexer no código.

Para usar a API da OpenAI, inclua a biblioteca ``openai`` nas
dependências (`requirements.txt`) e configure a sua chave secreta
``OPENAI_API_KEY`` no painel de segredos do Streamlit Cloud. O
aplicativo utiliza o cliente da biblioteca `openai` versão 1.x,
conforme indicado na documentação oficial【752441592351756†L60-L77】.

Nota: Este aplicativo não realiza buscas externas em tempo real
(internet), pois o ambiente de execução não disponibiliza APIs de
pesquisa externas. O modelo de linguagem usa apenas as informações
da base de dados e seu conhecimento interno. Para informações
atualizadas, a jornalista deve revisar periodicamente o arquivo
de descrições e realizar o upload pelo módulo de atualização.
"""

import json
import os
from typing import Dict, List, Any

import streamlit as st
from PIL import Image

# Tenta importar o cliente da versão 1.x da biblioteca openai. Caso a
# biblioteca não esteja instalada, o app irá alertar o usuário em
# tempo de execução.
try:
    from openai import OpenAI  # type: ignore
except ImportError:
    OpenAI = None  # type: ignore


def parse_restaurant_line(line: str) -> Dict[str, Any]:
    """Converte uma linha do arquivo de restaurantes em um dicionário.

    Cada campo deve ser separado por ``|`` conforme a especificação. Se
    alguns campos estiverem em branco, eles serão convertidos para
    ``None`` ou listas vazias conforme apropriado. Esta função é
    tolerante com espaçamentos extras ao redor dos campos.

    Retorna um dicionário com as chaves:
    ``name``, ``cuisine`` (lista), ``price_level``, ``accepts_voucher``
    (bool ou None), ``diet_options`` (lista), ``accessibility``
    (bool ou None), ``hours``, ``address`` e ``description``.
    """
    parts = [p.strip() for p in line.split("|")]
    # Garante no mínimo 9 campos
    while len(parts) < 9:
        parts.append("")

    name = parts[0]
    cuisine = [c.strip() for c in parts[1].split(";") if c.strip()] if parts[1] else []
    price = parts[2] if parts[2] else None
    voucher_field = parts[3].lower() if parts[3] else ""
    if voucher_field in {"sim", "yes", "true"}:
        accepts_voucher = True
    elif voucher_field in {"não", "nao", "no", "false"}:
        accepts_voucher = False
    else:
        accepts_voucher = None
    diet_options = [d.strip() for d in parts[4].split(";") if d.strip()] if parts[4] else []
    accessibility_field = parts[5].lower() if parts[5] else ""
    if accessibility_field in {"sim", "yes", "true"}:
        accessibility = True
    elif accessibility_field in {"não", "nao", "no", "false"}:
        accessibility = False
    else:
        accessibility = None
    hours = parts[6] if parts[6] else None
    address = parts[7] if parts[7] else None
    description = parts[8] if parts[8] else None
    return {
        "name": name,
        "cuisine": cuisine,
        "price_level": price,
        "accepts_voucher": accepts_voucher,
        "diet_options": diet_options,
        "accessibility": accessibility,
        "hours": hours,
        "address": address,
        "description": description,
    }


def load_data_from_txt(path: str) -> List[Dict[str, Any]]:
    """Lê o arquivo de base textual e converte cada linha em um dicionário.

    Se o arquivo não existir ou estiver vazio, retorna uma lista vazia.
    """
    if not os.path.exists(path):
        return []
    data: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data.append(parse_restaurant_line(line))
    return data


def load_prompt(path: str) -> str:
    """Carrega o prompt de instrução para o modelo a partir de um arquivo.

    Se o arquivo não existir, retorna um prompt padrão. A jornalista pode
    atualizar esse arquivo manualmente para alterar o comportamento do
    chatbot sem mexer no código.
    """
    default_prompt = (
        "Você é um guia gastronômico especializado em restaurantes em "
        "Pinheiros, São Paulo. Use as informações fornecidas na base de "
        "dados para responder às perguntas do usuário. Se a resposta não "
        "estiver na base ou você não souber, diga que não possui essa "
        "informação. Seja educado e objetivo nas respostas."
    )
    if not os.path.exists(path):
        return default_prompt
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content or default_prompt
    except Exception:
        return default_prompt


def build_context(data: List[Dict[str, Any]]) -> str:
    """Converte a lista de restaurantes em uma string JSON para o modelo."""
    try:
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return "[]"


def main() -> None:
    """Função principal que constrói a interface Streamlit."""
    st.set_page_config(page_title="Guia Gastronômico de Pinheiros", page_icon="🍽️")
    st.title("🍽️ Guia Gastronômico de Pinheiros")
    st.markdown(
        "Este chatbot ajuda a encontrar restaurantes no bairro de Pinheiros "
        "conforme sua preferência. O conhecimento é carregado de um arquivo "
        "de texto que a jornalista pode editar facilmente."\
    )

    base_path = os.path.dirname(__file__)
    # Caminhos padrão para a base estruturada e para as descrições em
    # linguagem natural
    json_path = os.path.join(base_path, "pinheiros_restaurants.json")
    txt_desc_path = os.path.join(base_path, "pinheiros_restaurants.txt")
    prompt_path = os.path.join(base_path, "prompt.txt")

    # Carrega a base de dados estruturada. Se não existir, tenta
    # carregar a versão textual (linha por linha) para inicializar
    # temporariamente a base.
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data: List[Dict[str, Any]] = json.load(f)
        except Exception:
            data = []
    else:
        data = load_data_from_txt(txt_desc_path)

    prompt = load_prompt(prompt_path)

    # Seção para atualização da base estruturada a partir de um arquivo
    # de descrições em linguagem natural. A seção fica na barra lateral.
    st.sidebar.header("Atualizar base de restaurantes")
    st.sidebar.markdown(
        "Faça upload de um arquivo de texto com descrições de restaurantes.\n"
        "Cada restaurante deve estar em um parágrafo separado. O modelo "
        "da OpenAI irá interpretar as descrições e atualizar a base JSON."
    )
    uploaded_file = st.sidebar.file_uploader(
        "Arquivo de descrições", type=["txt"], key="desc_uploader"
    )
    if uploaded_file is not None:
        if OpenAI is None:
            st.sidebar.error(
                "A biblioteca 'openai' não está instalada. Adicione 'openai' ao "
                "seu requirements.txt e redeploy a aplicação."
            )
        else:
            api_key = st.secrets.get("OPENAI_API_KEY")
            if not api_key:
                st.sidebar.error(
                    "Chave OPENAI_API_KEY não encontrada nos segredos. "
                    "Adicione sua chave no painel de Secrets do Streamlit Cloud."
                )
            else:
                raw_text = uploaded_file.getvalue().decode("utf-8")
                # Apenas processa se o usuário clicar no botão
                if st.sidebar.button("Processar descrições e atualizar base"):
                    client = OpenAI(api_key=api_key)
                    # Define o prompt de extração
                    extraction_prompt = (
                        "Você receberá descrições de restaurantes em Português, cada uma "
                        "separada por uma linha em branco. Para cada restaurante, extraia "
                        "os seguintes campos: name (nome), address (endereço), cuisine "
                        "(lista de culinárias, em minúsculas), price_level (símbolos $, $$ ou $$$ "
                        "ou use null se não houver), accepts_voucher (true se aceita vale-" 
                        "refeição, false se não, null se desconhecido), diet_options (lista de "
                        "restrições ou preferências alimentares em minúsculas), accessibility "
                        "(true se possui acessibilidade, false se não, null se desconhecido), "
                        "hours (horários de funcionamento), description (resumo descritivo). "
                        "Responda apenas com um JSON contendo uma lista de objetos, um para "
                        "cada restaurante, sem explicações adicionais."
                    )
                    full_extract_prompt = (
                        f"{extraction_prompt}\n\nDescrições:\n{raw_text}\n\nJSON:"
                    )
                    try:
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": full_extract_prompt}],
                            temperature=0,
                            max_tokens=1500,
                        )
                        json_text = response.choices[0].message.content.strip()
                        # Tenta converter o retorno em lista de dicionários
                        try:
                            new_entries: List[Dict[str, Any]] = json.loads(json_text)
                            # Integra as novas entradas à base existente (substitui se já houver restaurante com mesmo nome)
                            existing_names = {entry.get("name") for entry in data}
                            for entry in new_entries:
                                if entry.get("name") in existing_names:
                                    # substitui registro existente
                                    data = [e for e in data if e.get("name") != entry.get("name")]
                                    data.append(entry)
                                else:
                                    data.append(entry)
                            # Salva a base atualizada no arquivo JSON
                            with open(json_path, "w", encoding="utf-8") as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                            st.sidebar.success("Base atualizada com sucesso!")
                        except json.JSONDecodeError:
                            st.sidebar.error("A resposta do modelo não pôde ser analisada como JSON.")
                    except Exception as exc:
                        st.sidebar.error(f"Erro ao processar as descrições: {exc}")

    # Campo de chat
    question = st.chat_input("Pergunte algo sobre restaurantes em Pinheiros…")

    if question:
        if OpenAI is None:
            st.error(
                "A biblioteca 'openai' não está instalada. Adicione 'openai' ao "
                "seu requirements.txt e redeploy a aplicação."
            )
        else:
            api_key = st.secrets.get("OPENAI_API_KEY")
            if not api_key:
                st.error(
                    "Chave OPENAI_API_KEY não encontrada nos segredos. "
                    "Adicione sua chave no painel de Secrets do Streamlit Cloud."
                )
            else:
                client = OpenAI(api_key=api_key)
                context = build_context(data)
                full_prompt = (
                    f"{prompt}\n\n"
                    f"Base de dados (JSON):\n{context}\n\n"
                    f"Pergunta do usuário: {question}\n\n"
                    "Resposta:"
                )
                try:
                    completion = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": full_prompt}],
                        temperature=0.3,
                        max_tokens=600,
                    )
                    answer = completion.choices[0].message.content.strip()
                    st.markdown(answer)
                except Exception as exc:
                    st.error(f"Erro ao consultar a API da OpenAI: {exc}")

    # Removemos a listagem detalhada de todos os restaurantes para tornar a
    # interface mais enxuta, conforme solicitado. Caso seja necessário
    # apresentar um resumo, essa seção pode ser adicionada novamente.


if __name__ == "__main__":
    main()