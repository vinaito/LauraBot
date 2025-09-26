# Guia Gastronômico de Pinheiros

Esta aplicação em [Streamlit](https://streamlit.io) demonstra um chatbot simples que sugere
restaurantes do bairro de **Pinheiros** em São Paulo com base nas preferências do usuário.

Ao contrário do exemplo de RAG com PDF, esta versão carrega uma base de dados de
restaurantes (`pinheiros_restaurants.json`) e utiliza filtros estruturados para
recomendar estabelecimentos de acordo com o tipo de cozinha, faixa de preço,
aceitação de vales refeição, restrições alimentares e acessibilidade.  O
objetivo é que moradores e visitantes encontrem locais adequados às suas
necessidades sem depender de integrações externas ou APIs.

## Como usar

1. Instale as dependências a partir do arquivo `requirements.txt`.
   ```bash
   pip install -r requirements.txt
   ```

2. Execute o aplicativo com Streamlit:
   ```bash
   streamlit run app.py
   ```

3. Na interface Web, escolha suas preferências de cozinha, faixa de preço,
   necessidade de vale refeição, restrições alimentares e acessibilidade.  O
   chatbot exibirá até cinco restaurantes que melhor correspondam aos critérios.

Esta aplicação é destinada a demonstração e pode ser facilmente ampliada com
novos restaurantes ou outros bairros ajustando o arquivo JSON.