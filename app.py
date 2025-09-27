"""Guia gastronômico de Pinheiros com chat.

Este app em Streamlit lê uma base JSON de restaurantes em Pinheiros (São Paulo)
e permite conversar em linguagem natural: o usuário faz perguntas sobre onde
comer, culinárias, horários, etc., e o modelo do OpenAI responde com base
nesses dados. Se a resposta não estiver na base, ele avisa.

Para usar:
- Coloque 'pinheiros_restaurants.json' no mesmo diretório deste arquivo.
- Defina sua chave da OpenAI em secrets (Streamlit Cloud) como OPENAI_API_KEY.
"""

import json
import os
from typing import List, Dict, Any

import streamlit as st
from PIL import Image
import openai


def load_data(path: str) -> List[Dict[str, Any]]:
    """Carrega o JSON da base de restaurantes."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    st.set_page_config(page_title="Guia Gastronômico de Pinheiros", page_icon="🍽️")
    st.title("🍽️ Guia Gastronômico de Pinheiros")

    # Carrega a base
    base_path = os.path.dirname(__file__)
    data_path = os.path.join(base_path, "pinheiros_restaurants.json")
    try:
        data = load_data(data_path)
    except FileNotFoundError:
        st.error("Arquivo pinheiros_restaurants.json não encontrado.")
        return

    # Mapeia imagens para cada restaurante
    images = {
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
    image_dir = base_path

    # Campo de chat
    question = st.chat_input("Pergunte algo sobre restaurantes em Pinheiros…")

    if question:
        # Obtém a chave da API a partir dos segredos
        api_key = st.secrets.get("OPENAI_API_KEY")
        if not api_key:
            st.error("OPENAI_API_KEY não configurado nos segredos da sua aplicação.")
        else:
            openai.api_key = api_key
            # Prepara contexto: converte a base em texto para o modelo
            context = json.dumps(data, ensure_ascii=False)
            prompt = (
                "Você é um guia gastronômico especializado em restaurantes em Pinheiros, São Paulo. "
                "Use **apenas** as informações da base de dados a seguir para responder de forma educada "
                "à pergunta do usuário. Se a resposta não estiver na base, diga que não possui essa informação.\n\n"
                f"Base de dados:\n{context}\n\n"
                f"Pergunta: {question}\n\n"
                "Resposta:"
            )
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=500,
                )
                answer = response["choices"][0]["message"]["content"].strip()
                st.markdown(answer)
            except Exception as e:
                st.error(f"Erro ao consultar a API da OpenAI: {e}")

    # Exibe todos os restaurantes abaixo do chat como referência
    with st.expander("Ver lista completa de restaurantes"):
        for item in data:
            name = item["name"]
            st.markdown(f"### {name}")
            col1, col2 = st.columns([1, 3])
            with col1:
                img_file = images.get(name)
                path_img = os.path.join(image_dir, img_file) if img_file else None
                if path_img and os.path.exists(path_img):
                    st.image(Image.open(path_img), use_column_width=True)
            with col2:
                st.markdown(f"- **Culinária:** {', '.join(item.get('cuisine', []))}")
                st.markdown(f"- **Preço:** {item.get('price_level', '–')}")
                acc_vale = item.get("accepts_voucher")
                if acc_vale is True:
                    st.markdown(f"- **Vale-refeição:** aceita")
                elif acc_vale is False:
                    st.markdown(f"- **Vale-refeição:** não aceita")
                else:
                    st.markdown(f"- **Vale-refeição:** não informado")
                if item.get("diet_options"):
                    st.markdown(f"- **Opções de dieta:** {', '.join(item['diet_options'])}")
                acc = item.get("accessibility")
                if acc is True:
                    st.markdown(f"- **Acessibilidade:** possui")
                elif acc is False:
                    st.markdown(f"- **Acessibilidade:** não possui")
                else:
                    st.markdown(f"- **Acessibilidade:** não informado")
                st.markdown(f"- **Horário:** {item.get('hours', 'não informado')}")
                st.markdown(f"- **Endereço:** {item['address']}")
                st.markdown(f"- **Descrição:** {item['description']}")

if __name__ == "__main__":
    main()