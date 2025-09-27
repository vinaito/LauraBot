# Guia Gastronômico de Pinheiros

Este repositório contém um aplicativo de demonstração em [Streamlit](https://streamlit.io) que apresenta um **chatbot gastronômico** focado no bairro de **Pinheiros**, em São Paulo. O objetivo é permitir que moradores e visitantes encontrem restaurantes adequados às suas preferências de forma simples e sem necessidade de conhecimentos técnicos.

## Visão geral

O chatbot responde a perguntas sobre restaurantes com base em uma **base de dados estruturada** (`pinheiros_restaurants.json`). A aplicação também inclui um módulo opcional de **atualização** que permite adicionar ou atualizar restaurantes a partir de um arquivo de texto em linguagem natural, que é interpretado pela API da OpenAI.

Principais características:

- **Interface de chat**: faça perguntas livres sobre restaurantes, horários, tipos de cozinha, etc. O modelo utiliza as informações do JSON como contexto e responde em português.
- **Base de dados estruturada**: os restaurantes são armazenados em `pinheiros_restaurants.json` com campos como nome, endereço, culinária, faixa de preço, aceitação de vale‑refeição, opções de dieta, acessibilidade, horários e descrição.
- **Atualização via arquivo de texto**: pela barra lateral, você pode enviar um `.txt` com descrições em linguagem natural (um restaurante por parágrafo). Um comando da OpenAI extrai os dados relevantes e atualiza o JSON automaticamente.
- **Personalização de prompt**: o arquivo `prompt.txt` define instruções para o modelo (tom de voz, limites, etc.) e pode ser ajustado sem alterar o código.
- **Sem dependência de APIs externas de busca**: o aplicativo funciona offline em relação a buscas na internet. Para novas informações, atualize manualmente o arquivo de descrições.

## Como usar

1. **Instale as dependências**

   Execute em seu ambiente:

   ```bash
   pip install -r requirements.txt
   ```

   Certifique‑se de que `openai>=1.0.0` está listado em `requirements.txt` para utilizar a API da OpenAI.

2. **Configure sua chave da OpenAI**

   Crie um arquivo `.streamlit/secrets.toml` (ou configure via painel do Streamlit Cloud) com o conteúdo:

   ```toml
   OPENAI_API_KEY = "sk‑...sua chave..."
   ```

   Esta chave é utilizada tanto para o chat quanto para a extração de dados do arquivo de texto. Não inclua a chave diretamente no código fonte.

3. **Execute a aplicação**

   ```bash
   streamlit run app.py
   ```

   Acesse a URL local indicada (geralmente `http://localhost:8501/`).

4. **Faça perguntas**

   Utilize o campo de chat na página principal para fazer perguntas sobre restaurantes de Pinheiros. O modelo responderá com base na base de dados atual.

5. **Atualize a base com descrições**

   Na barra lateral há uma seção **“Atualizar base de restaurantes”**. Para adicionar ou atualizar restaurantes:

   - Crie um arquivo `.txt` com um parágrafo por restaurante contendo as principais informações (nome, endereço, tipo de cozinha, horários, se aceita vale‑refeição, etc.).
   - Faça upload do arquivo na barra lateral e clique em **“Processar descrições e atualizar base”**.
   - O aplicativo enviará essas descrições ao modelo da OpenAI, que irá extrair as informações e mesclá‑las ao `pinheiros_restaurants.json`.

   **Exemplo de parágrafo:**

   ```
   Arlete Bar e Mercearia: Bar descolado com drinques autorais e petiscos variados. Fica na Rua Vupabussu, 101, Pinheiros. Horário de funcionamento: ter 17h30–00h, qua–sex 17h30–1h, sáb 13h–1h, dom 13h–20h. Aceita vale‑refeição. Possui área aberta, DJ e música ao vivo. Oferece opções vegetarianas.
   ```

6. **Personalize o prompt**

   Ajuste `prompt.txt` para orientar o comportamento do chatbot. Por exemplo, você pode pedir ao modelo para ser mais formal, informal, sucinto ou incluir dicas culturais.

## Estrutura dos dados

Cada entrada em `pinheiros_restaurants.json` segue o formato:

```json
{
  "name": "Nome do restaurante",
  "address": "Endereço completo",
  "neighborhood": "Pinheiros",
  "cuisine": ["tipo1", "tipo2"],
  "price_level": "$$",          // símbolos $, $$ ou $$$
  "accepts_voucher": true,       // true, false ou null
  "diet_options": ["vegetarian"],
  "accessibility": false,        // true, false ou null
  "highlights": [
    "destaque 1",
    "destaque 2"
  ],
  "description": "Texto descritivo",
  "hours": "Horários de funcionamento"
}
```

Novos restaurantes extraídos do arquivo de descrições serão convertidos para essa estrutura automaticamente.

## Limitações

- O aplicativo **não executa buscas na internet**; toda a informação vem do arquivo JSON ou das descrições fornecidas. Caso deseje dados mais recentes, edite o arquivo de descrições e atualize a base.
- A extração automática depende da API da OpenAI. Verifique se sua chave possui crédito suficiente.

## Licença

Este projeto é fornecido apenas para fins educacionais e demonstrativos. Nenhuma garantia é fornecida quanto à atualidade dos dados dos restaurantes ou à disponibilidade contínua das APIs.