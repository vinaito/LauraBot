"""Guia gastronômico de Pinheiros com chat conversacional.

Este aplicativo Streamlit lê uma base JSON contendo informações de
restaurantes no bairro de Pinheiros, em São Paulo, e disponibiliza
uma interface de chat para que o usuário converse em linguagem
natural. O modelo da OpenAI responde às perguntas baseando‑se nos
dados carregados. Se a resposta não estiver na base, o bot avisará
que não tem a informação.

Para que o chat funcione, é necessário definir a variável secreta
`OPENAI_API_KEY` nas configurações da aplicação do Streamlit
Community Cloud. O valor **não** deve ser armazenado neste
arquivo de código. Localmente, você pode criar um arquivo
`.streamlit/secrets.toml` com a chave.

O app também mostra uma lista completa de restaurantes em um
expansor para referência.
"""

import json
import os
from typing import Dict, Any, List

import streamlit as st
from PIL import Image

# Importa o cliente OpenAI a partir do SDK 1.x. Para versões
# anteriores (<=0.28), este import não existe e será necessário
# piná‑lo ou atualizar seu código.
try:
    from openai import OpenAI  # type: ignore
except ImportError:
    # Mensagem amigável caso o módulo openai não esteja instalado.
    OpenAI = None  # type: ignore


def load_data(path: str) -> List[Dict[str, Any]]:
    """Lê e retorna a base de restaurantes a partir de um arquivo JSON.

    O arquivo deve estar codificado em UTF‑8. Em caso de erro de
    abertura ou decodificação, será lançada a exceção correspondente.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    """Função principal que monta a interface e executa o chat."""
    st.set_page_config(page_title="Guia Gastronômico de Pinheiros", page_icon="🍽️")
    st.title("🍽️ Guia Gastronômico de Pinheiros")
    st.markdown(
        "Converse sobre restaurantes em Pinheiros! Faça perguntas em "
        "linguagem natural e receba respostas baseadas em nossa base de "
        "dados. Se não soubermos a resposta, avisaremos."
    )

    # Caminhos para a base e as imagens
    base_path = os.path.dirname(__file__)
    data_path = os.path.join(base_path, "pinheiros_restaurants.json")

    # Carrega os dados e exibe um erro amigável se o arquivo não existir.
    try:
        data = load_data(data_path)
    except FileNotFoundError:
        st.error(
            "Arquivo 'pinheiros_restaurants.json' não encontrado. "
            "Certifique‑se de que o arquivo está na mesma pasta que o app."
        )
        return

    # Mapeia nome do restaurante para o arquivo de imagem. Use
    # 'placeholder_light_gray_block.png' para imagens ausentes.
    images: Dict[str, str] = {
        "Gael Cozinha Mestiça": "e7618e6d-1c71-4d26-ae8b-b98d58904dc7.png",
        "Otoshi Izakaya": "a4c1545e-5b25-4d35-aeb1-b26ff005b1e1.png",
        "Jojo Ramen (Pinheiros)": "6ce64bee-567c-4fc6-b659-ec32bd181acd.png",
        "Modern Mamma Osteria (Moma) – Pinheiros": "a23da210-f677-45d8-831f-36e6826555ee.png",
        "Momokuri": "0b8093ff-c821-4186-ab5e-59392575d051.png",
        "Arlete Bar e Mercearia": "ef1b98a1-9fa7-442b-9969-2c51b25bc897.png",
        "Pirajá (Faria Lima)": "cfbdc833-d2bc-4c9e-bac2-e582a5a6a71e.png",
        "Buzina Burgers (Baixo Pinheiros)": "78cf8129-c001-4bdf-8daf-9644137aeaf3.png",
        "Notorious Fish": "placeholder_light_gray_block.png",
        "Hi Pokee – Pinheiros": "placeholder_light_gray_block.png",
    }

    # Lê a pergunta do usuário via chat_input. Este campo aparece na
    # parte inferior da página.
    question = st.chat_input("Pergunte algo sobre restaurantes em Pinheiros…")

    if question:
        # Verifica se a biblioteca openai está disponível
        if OpenAI is None:
            st.error(
                "A biblioteca 'openai' não está instalada. Inclua 'openai' no "
                "arquivo requirements.txt e faça o deploy novamente."
            )
        else:
            # Tenta obter a chave da OpenAI a partir dos segredos configurados
            api_key = st.secrets.get("OPENAI_API_KEY")
            if not api_key:
                st.error(
                    "Chave OPENAI_API_KEY não encontrada nos segredos. "
                    "Adicione sua chave no painel de Secrets da aplicação no "
                    "Streamlit Cloud."
                )
            else:
                # Cria o cliente OpenAI com a chave fornecida
                client = OpenAI(api_key=api_key)
                # Constrói o contexto com os dados convertidos para JSON
                context = json.dumps(data, ensure_ascii=False)
                # Monta o prompt com instruções e a pergunta
                prompt = (
                    "Você é um guia gastronômico especializado em restaurantes "
                    "em Pinheiros, São Paulo. Use **apenas** as informações "
                    "abaixo (fornecidas em formato JSON) para responder à "
                    "pergunta do usuário. Se a resposta não estiver na base, "
                    "diga que não possui essa informação.\n\n"
                    f"Base de dados:\n{context}\n\n"
                    f"Pergunta: {question}\n\n"
                    "Resposta:"
                )
                try:
                    # Chama o modelo chat para gerar a resposta
                    completion = client.chat.completions.create(
                        model="gpt-3.5-turbo",  # ou outro modelo autorizado
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=600,
                    )
                    answer = completion.choices[0].message.content.strip()
                    st.markdown(answer)
                except Exception as exc:
                    st.error(f"Erro ao consultar a API da OpenAI: {exc}")

    # Expansor com a lista completa de restaurantes para referência
    with st.expander("Ver lista completa de restaurantes"):
        for item in data:
            name = item["name"]
            st.markdown(f"### {name}")
            col1, col2 = st.columns([1, 3])
            with col1:
                img_file = images.get(name, "placeholder_light_gray_block.png")
                img_path = os.path.join(base_path, img_file)
                if os.path.exists(img_path):
                    st.image(Image.open(img_path), use_column_width=True)
            with col2:
                cuisines = ", ".join(item.get("cuisine", [])) or "–"
                price = item.get("price_level", "–")
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
                    access_str = "Possui"
                elif accessibility is False:
                    access_str = "Não possui"
                else:
                    access_str = "Não informado"
                hours = item.get("hours", "Não informado")
                st.markdown(f"- **Culinária:** {cuisines}")
                st.markdown(f"- **Preço:** {price}")
                st.markdown(f"- **Vale-refeição:** {voucher_str}")
                st.markdown(f"- **Opções de dieta:** {diets}")
                st.markdown(f"- **Acessibilidade:** {access_str}")
                st.markdown(f"- **Horário:** {hours}")
                st.markdown(f"- **Endereço:** {item['address']}")
                st.markdown(f"- **Descrição:** {item['description']}")

if __name__ == "__main__":
    main()