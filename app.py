"""Guia gastronômico de Pinheiros com interface de chat e fonte de dados textual.

Este aplicativo em Streamlit permite que a jornalista Laura mantenha seu
conteúdo sobre restaurantes de Pinheiros de forma simples, sem lidar
com JSON. A base de dados é lida de um arquivo de texto (`*.txt`),
em que cada linha representa um restaurante e os campos são
separados pelo caractere pipe (``|``). Um arquivo de prompt separado
(`prompt.txt`) contém as instruções para o modelo de linguagem.

Estrutura sugerida para cada linha da base de dados (separada por
``|``):

    nome | culinarias separadas por ; | faixa de preço | aceita VR?
    | restrições separadas por ; | acessibilidade | horário |
    endereço | descrição

Campos opcionais podem ser deixados em branco. Por exemplo,
``None`` ou uma string vazia serão interpretados como ausência de
informação. A jornalista pode editar o arquivo com qualquer editor
de texto simples, sem precisar de formatação JSON.

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
``*.txt``.
"""

import json
import os
from typing import Dict, List, Any, Tuple

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
    data_txt_path = os.path.join(base_path, "pinheiros_restaurants.txt")
    prompt_path = os.path.join(base_path, "prompt.txt")

    data = load_data_from_txt(data_txt_path)
    if not data:
        st.warning(
            "Não foi possível carregar a base de dados de restaurantes. "
            "Verifique se o arquivo 'pinheiros_restaurants.txt' existe e "
            "contém dados."
        )

    prompt = load_prompt(prompt_path)

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

    # Expansor com a lista de restaurantes
    with st.expander("Ver lista completa de restaurantes"):
        for item in data:
            name = item.get("name")
            if not name:
                continue
            st.markdown(f"### {name}")
            # Em uma versão mais avançada, este bloco pode mostrar imagens se
            # existirem imagens associadas ao restaurante.
            cuisines = ", ".join(item.get("cuisine", [])) or "–"
            price = item.get("price_level", "–") or "–"
            voucher = item.get("accepts_voucher")
            if voucher is True:
                voucher_str = "Aceita"
            elif voucher is False:
                voucher_str = "Não aceita"
            else:
                voucher_str = "Não informado"
            diets = ", ".join(item.get("diet_options", [])) or "–"
            accessibility = item.get("accessibility")
            if accessibility is True:
                accessibility_str = "Possui"
            elif accessibility is False:
                accessibility_str = "Não possui"
            else:
                accessibility_str = "Não informado"
            hours = item.get("hours", "Não informado") or "Não informado"
            address = item.get("address", "Não informado") or "Não informado"
            description = item.get("description", "")
            st.markdown(f"- **Culinária:** {cuisines}")
            st.markdown(f"- **Preço:** {price}")
            st.markdown(f"- **Vale-refeição:** {voucher_str}")
            st.markdown(f"- **Opções de dieta:** {diets}")
            st.markdown(f"- **Acessibilidade:** {accessibility_str}")
            st.markdown(f"- **Horário:** {hours}")
            st.markdown(f"- **Endereço:** {address}")
            if description:
                st.markdown(f"- **Descrição:** {description}")


if __name__ == "__main__":
    main()