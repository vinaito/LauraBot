"""Aplicação Streamlit para sugerir restaurantes em Pinheiros.

Esta aplicação lê um arquivo JSON contendo dados de restaurantes do bairro
de Pinheiros (São Paulo) e permite ao usuário filtrar por culinária,
faixa de preço, vale-refeição, restrições alimentares e acessibilidade.
"""

import json
import os
from typing import List, Dict, Any

import streamlit as st
from PIL import Image


def load_data(path: str) -> List[Dict[str, Any]]:
    """Carrega a base de restaurantes a partir de um arquivo JSON."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def get_unique_values(data: List[Dict[str, Any]], key: str) -> List[str]:
    """Extrai valores únicos de um campo (lista ou string) da base."""
    values = []
    for item in data:
        val = item.get(key)
        if isinstance(val, list):
            values.extend(val)
        elif val is not None:
            values.append(val)
    return sorted({v for v in values if v})


def filter_restaurants(
    data: List[Dict[str, Any]],
    cuisines: List[str],
    price: str,
    voucher: str,
    diets: List[str],
    accessibility: str,
) -> List[Dict[str, Any]]:
    """Filtra restaurantes de acordo com os critérios selecionados."""
    results = []
    for item in data:
        score = 0
        # Culinária
        if cuisines and not any(c.lower() in [c.lower() for c in item.get("cuisine", [])] for c in cuisines):
            continue
        if cuisines:
            score += 1
        # Preço
        if price != "Todos" and item.get("price_level") != price:
            continue
        if price != "Todos":
            score += 1
        # Vale refeição
        acc_vale = item.get("accepts_voucher")
        if voucher == "Sim" and acc_vale is not True:
            continue
        if voucher == "Não" and acc_vale is True:
            continue
        if voucher != "Indiferente":
            score += 1
        # Restrições
        if diets and not all(d.lower() in [d.lower() for d in (item.get("diet_options") or [])] for d in diets):
            continue
        if diets:
            score += 1
        # Acessibilidade
        acc = item.get("accessibility")
        if accessibility == "Sim" and acc is not True:
            continue
        if accessibility == "Não" and acc is True:
            continue
        if accessibility != "Indiferente":
            score += 1

        item_copy = dict(item)
        item_copy["score"] = score
        results.append(item_copy)

    return sorted(results, key=lambda x: x["score"], reverse=True)


def main() -> None:
    st.set_page_config(page_title="Guia Gastronômico de Pinheiros", page_icon="🍽️")
    st.title("🍽️ Guia Gastronômico de Pinheiros")
    st.markdown(
        "Descubra restaurantes em Pinheiros de acordo com suas preferências. "
        "Selecione o tipo de culinária, a faixa de preço, se precisa de vale refeição, "
        "restrições alimentares e acessibilidade. O aplicativo retornará até cinco opções adequadas."
    )

    # Caminhos
    base_path = os.path.dirname(__file__)
    data_path = os.path.join(base_path, "pinheiros_restaurants.json")
    data = load_data(data_path)  # ← ESSA LINHA CARREGA O JSON
    image_dir = base_path

    # Mapeamento de imagens
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

    # Gera listas de opções para os widgets
    available_cuisines = get_unique_values(data, "cuisine")
    available_diets = get_unique_values(data, "diet_options")
    price_options = ["Todos", "$", "$$", "$$$"]
    voucher_options = ["Indiferente", "Sim", "Não"]
    accessibility_options = ["Indiferente", "Sim", "Não"]

    # Controles na barra lateral
    st.sidebar.header("Preferências de busca")
    selected_cuisines = st.sidebar.multiselect("Tipo de culinária", options=available_cuisines)
    selected_price = st.sidebar.selectbox("Faixa de preço", options=price_options, index=0)
    selected_voucher = st.sidebar.selectbox("Aceita vale refeição?", options=voucher_options, index=0)
    selected_diets = st.sidebar.multiselect("Restrições alimentares", options=available_diets)
    selected_access = st.sidebar.selectbox("Necessita de acessibilidade?", options=accessibility_options, index=0)

    st.sidebar.markdown("\nClique em **Buscar** para ver as recomendações.")
    if st.sidebar.button("Buscar"):
        results = filter_restaurants(
            data,
            cuisines=selected_cuisines,
            price=selected_price,
            voucher=selected_voucher,
            diets=selected_diets,
            accessibility=selected_access,
        )
        st.subheader("Resultados")
        if not results:
            st.write("Nenhum restaurante corresponde aos critérios selecionados.")
        else:
            st.success(f"Encontrei {len(results[:5])} opção(ões) para você!")
            for idx, item in enumerate(results[:5]):
                name = item["name"]
                # Criar um resumo em linguagem natural
                resumo = (
                    f"{idx + 1}. {name}: culinária {', '.join(item.get('cuisine', []))}, "
                    f"preço {item.get('price_level', '–')}. "
                    f"Destaques: {', '.join(item.get('highlights', [])[:2])}."
                )
                st.markdown(resumo)
                img_file = images.get(name)
                col1, col2 = st.columns([1, 2])
                with col1:
                    path_img = os.path.join(image_dir, img_file) if img_file else None
                    if path_img and os.path.exists(path_img):
                        st.image(Image.open(path_img), use_column_width=True)
                with col2:
                    st.markdown(f"**Endereço:** {item['address']}")
                    st.markdown(f"**Vale refeição:** {'Aceita' if item.get('accepts_voucher') else 'Não aceita' if item.get('accepts_voucher') is False else 'Não informado'}")
                    if item.get('diet_options'):
                        st.markdown(f"**Opções para restrições:** {', '.join(item['diet_options'])}")
                    st.markdown(f"**Acessibilidade:** {'Possui' if item.get('accessibility') else 'Não possui' if item.get('accessibility') is False else 'Não informado'}")
                    st.markdown(f"**Horário:** {item.get('hours') or 'Não informado'}")
                    st.markdown(f"**Descrição:** {item.get('description')}")

if __name__ == "__main__":
    main()