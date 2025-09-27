"""
Aplicação Streamlit para sugerir restaurantes em Pinheiros.

Esta aplicação lê um arquivo JSON contendo dados de restaurantes no bairro de
Pinheiros (São Paulo) e permite ao usuário selecionar preferências de
culinária, faixa de preço, aceitação de vale refeição, restrições
alimentares e necessidade de acessibilidade.  A partir desses critérios,
filtra os estabelecimentos e exibe até cinco sugestões com descrições,
destaques e informações práticas.

Para executar:

```
streamlit run app.py
```
"""

import json
import os
from typing import List, Dict, Any

import streamlit as st
from PIL import Image


def load_data(path: str) -> List[Dict[str, Any]]:
    """Carrega a base de restaurantes a partir de um arquivo JSON.

    Args:
        path: caminho para o arquivo JSON.

    Returns:
        Lista de dicionários com informações dos restaurantes.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def get_unique_values(data: List[Dict[str, Any]], key: str) -> List[str]:
    """Retorna uma lista única de valores extraídos de um campo da base.

    Para campos que são listas (ex.: 'cuisine' ou 'diet_options'), a função
    concatena os itens antes de deduplicar.

    Args:
        data: base de restaurantes.
        key: chave a ser inspecionada.

    Returns:
        Lista de strings únicas.
    """
    values = []
    for item in data:
        val = item.get(key)
        if isinstance(val, list):
            values.extend(val)
        elif val is not None:
            values.append(val)
    # Remover nulos e duplicados
    clean = sorted({v for v in values if v})
    return clean


def filter_restaurants(
    data: List[Dict[str, Any]],
    cuisines: List[str],
    price: str,
    voucher: str,
    diets: List[str],
    accessibility: str,
) -> List[Dict[str, Any]]:
    """Filtra restaurantes de acordo com critérios selecionados.

    Args:
        data: lista de restaurantes.
        cuisines: lista de culinárias preferidas (vazio significa indiferente).
        price: faixa de preço escolhida ("Todos" para ignorar).
        voucher: aceitação de vale refeição ("Sim", "Não" ou "Indiferente").
        diets: lista de restrições alimentares (vazio significa nenhuma restrição).
        accessibility: necessidade de acessibilidade ("Sim", "Não" ou "Indiferente").

    Returns:
        Lista de restaurantes que atendem aos critérios.
    """
    results = []
    for item in data:
        score = 0

        # Filtra culinária
        if cuisines:
            item_cuisines = [c.lower() for c in item.get("cuisine", [])]
            # Aceita se houver interseção entre as preferências e as culinárias do item
            if not any(c.lower() in item_cuisines for c in cuisines):
                continue
            score += 1

        # Filtra faixa de preço
        if price and price != "Todos":
            if item.get("price_level") != price:
                continue
            score += 1

        # Filtra vale refeição
        if voucher != "Indiferente":
            accepts = item.get("accepts_voucher")
            if voucher == "Sim" and accepts is not True:
                continue
            if voucher == "Não" and accepts is True:
                continue
            score += 1

        # Filtra restrições alimentares
        if diets:
            item_diets = [d.lower() for d in item.get("diet_options") or []]
            # Cada restrição selecionada deve estar presente na lista do item
            if not all(d.lower() in item_diets for d in diets):
                continue
            score += 1

        # Filtra acessibilidade
        if accessibility != "Indiferente":
            acc = item.get("accessibility")
            if accessibility == "Sim" and acc is not True:
                continue
            if accessibility == "Não" and acc is True:
                continue
            score += 1

        # Guarda o score para ordenação futura
        item_copy = dict(item)
        item_copy["score"] = score
        results.append(item_copy)

    # Ordena por score (maior primeiro) e retorna
    results_sorted = sorted(results, key=lambda x: x["score"], reverse=True)
    return results_sorted


def main() -> None:
    """Função principal que define a interface do aplicativo."""
    st.set_page_config(page_title="Guia Gastronômico de Pinheiros", page_icon="🍽️")
    st.title("🍽️ Guia Gastronômico de Pinheiros")
    st.markdown(
        "Descubra restaurantes em Pinheiros de acordo com suas preferências. "
        "Selecione o tipo de culinária, a faixa de preço, se precisa de vale refeição, "
        "restrições alimentares e acessibilidade. O aplicativo retornará até cinco opções adequadas."
    )

    # Caminho para a base e imagens
    base_path = os.path.dirname(__file__)
    data_path = os.path.join(base_path, "pinheiros_restaurants.json")

    # CARREGUE A BASE AQUI
    data = load_data(data_path)

    # Diretório das imagens
    image_dir = base_path
        "Gael Cozinha Mestiça": "e7618e6d-1c71-4d26-ae8b-b98d58904dc7.png",
        "Otoshi Izakaya": "a4c1545e-5b25-4d35-aeb1-b26ff005b1e1.png",
        "Jojo Ramen (Pinheiros)": "6ce64bee-567c-4fc6-b659-ec32bd181acd.png",
        "Modern Mamma Osteria (Moma) – Pinheiros": "a23da210-f677-45d8-831f-36e6826555ee.png",
        "Momokuri": "0b8093ff-c821-4186-ab5e-59392575d051.png",
        "Arlete Bar e Mercearia": "ef1b98a1-9fa7-442b-9969-2c51b25bc897.png",
        "Pirajá (Faria Lima)": "cfbdc833-d2bc-4c9e-bac2-e582a5a6a71e.png",
        "Buzina Burgers (Baixo Pinheiros)": "78cf8129-c001-4bdf-8daf-9644137aeaf3.png",
        # Para Notorious Fish e Hi Pokee, podemos usar uma imagem de placeholder
        "Notorious Fish": "placeholder_light_gray_block.png",
        "Hi Pokee – Pinheiros": "placeholder_light_gray_block.png",
    }

    # Geração de listas de opções
    available_cuisines = get_unique_values(data, "cuisine")
    available_diets = get_unique_values(data, "diet_options")
    price_options = ["Todos", "$", "$$", "$$$"]
    voucher_options = ["Indiferente", "Sim", "Não"]
    accessibility_options = ["Indiferente", "Sim", "Não"]

    # Interface de seleção
    st.sidebar.header("Preferências de busca")
    selected_cuisines = st.sidebar.multiselect(
        "Tipo de culinária", options=available_cuisines, default=[]
    )
    selected_price = st.sidebar.selectbox(
        "Faixa de preço", options=price_options, index=0
    )
    selected_voucher = st.sidebar.selectbox(
        "Aceita vale refeição?", options=voucher_options, index=0
    )
    selected_diets = st.sidebar.multiselect(
        "Restrições alimentares", options=available_diets, default=[]
    )
    selected_access = st.sidebar.selectbox(
        "Necessita de acessibilidade?", options=accessibility_options, index=0
    )

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
            st.write(f"Encontrei {len(results[:5])} opções para você:")
            for idx, item in enumerate(results[:5]):
                name = item["name"]
                img_file = images.get(name)
                # Lê a imagem se existir
                col1, col2 = st.columns([1, 2])
                with col1:
                    if img_file and os.path.exists(os.path.join(image_dir, img_file)):
                        image = Image.open(os.path.join(image_dir, img_file))
                        st.image(image, use_column_width=True)
                    else:
                        # Mostra placeholder
                        placeholder = Image.open(os.path.join(image_dir, "placeholder_light_gray_block.png"))
                        st.image(placeholder, use_column_width=True)
                with col2:
                    st.markdown(f"### {name}")
                    st.markdown(f"**Culinária:** {', '.join(item.get('cuisine', []))}")
                    st.markdown(f"**Faixa de preço:** {item.get('price_level', '–')}")
                    # Vale refeição
                    accepts = item.get("accepts_voucher")
                    if accepts is True:
                        voucher_text = "Aceita vale refeição"
                    elif accepts is False:
                        voucher_text = "Não aceita vale refeição"
                    else:
                        voucher_text = "Aceitação de vale refeição não especificada"
                    st.markdown(f"**Vale refeição:** {voucher_text}")
                    # Restrição alimentar
                    diets = item.get("diet_options") or []
                    if diets:
                        st.markdown(f"**Opções para restrições:** {', '.join(diets)}")
                    # Acessibilidade
                    acc = item.get("accessibility")
                    if acc is True:
                        acc_text = "Possui acessibilidade"
                    elif acc is False:
                        acc_text = "Não possui acessibilidade"
                    else:
                        acc_text = "Acessibilidade não especificada"
                    st.markdown(f"**Acessibilidade:** {acc_text}")
                    # Destaques
                    highlights = item.get("highlights") or []
                    if highlights:
                        st.markdown("**Destaques:**")
                        for h in highlights:
                            st.markdown(f"- {h}")
                    # Descrição
                    st.markdown(f"**Descrição:** {item.get('description')}")
                    # Horário
                    if item.get("hours"):
                        st.markdown(f"**Horário:** {item['hours']}")


if __name__ == "__main__":
    main()