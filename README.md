# Guia Gastronômico de Pinheiros

Este repositório contém um aplicativo de demonstração em [Streamlit](https://streamlit.io) que apresenta um **chatbot gastronômico** focado no bairro de **Pinheiros**, em São Paulo. O objetivo é permitir que moradores e visitantes encontrem restaurantes adequados às suas preferências de forma simples e sem necessidade de conhecimentos técnicos.

## Visão geral


O aplicativo possui quatro abas principais:
1. **Chatbot**: Converse sobre restaurantes de Pinheiros, com respostas baseadas na base local e, opcionalmente, IA (OpenAI).
2. **Base**: Visualize, busque e filtre os restaurantes cadastrados.
3. **Importar .txt**: Adicione ou atualize restaurantes via upload de arquivo `.txt`, processado em modo offline (regex) ou por IA (LLM), conforme configuração.
4. **Ferramentas**: Baixe o JSON, veja dicas de configuração e instruções para ativar/desativar o modo IA.

O chatbot responde a perguntas sobre restaurantes com base em uma **base de dados estruturada** (`pinheiros_restaurants.json`). A aplicação também inclui um módulo opcional de **atualização** que permite adicionar ou atualizar restaurantes a partir de um arquivo de texto em linguagem natural, que pode ser interpretado por IA (OpenAI) ou por parser offline.

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
   USE_LLM_EXTRACTOR = true  # (opcional) ativa importação e chat via IA
   OPENAI_API_KEY = "sk‑...sua chave..."
   OPENAI_MODEL = "gpt-4o-mini"  # (opcional, pode ajustar)
   ```

   - `USE_LLM_EXTRACTOR`: se `true`, ativa importação e chat via IA (OpenAI). Se ausente ou `false`, o app funciona apenas em modo offline.
   - `OPENAI_API_KEY`: chave da OpenAI para uso do modo IA.
   - `OPENAI_MODEL`: modelo OpenAI a ser utilizado (padrão: `gpt-4o-mini`).
   Não inclua a chave diretamente no código fonte.

3. **Execute a aplicação**

   ```bash
   streamlit run app.py
   ```

   Acesse a URL local indicada (geralmente `http://localhost:8501/`).

4. **Faça perguntas**

   Utilize o campo de chat na página principal para fazer perguntas sobre restaurantes de Pinheiros. O modelo responderá com base na base de dados atual.

5. **Atualize a base com descrições**


   Na aba **Importar .txt**, faça upload de um arquivo `.txt` conforme as instruções detalhadas em [`instrucoes_txt_atualizacao.md`](instrucoes_txt_atualizacao.md), incluindo um parágrafo por restaurante com as principais informações (nome, endereço, tipo de cozinha, horários, se aceita vale-refeição, etc.).
   - O modo **offline** (sem IA) reconhece campos básicos por regex.
   - O modo **LLM** (IA) extrai campos completos via OpenAI, se ativado.
   - Após o upload, visualize a pré-análise e clique para importar. O sistema mescla os dados ao `pinheiros_restaurants.json`, adicionando ou atualizando registros.
   Consulte o arquivo [`instrucoes_txt_atualizacao.md`](instrucoes_txt_atualizacao.md) para exemplos, dados obrigatórios e dicas de formatação.
   Na barra lateral há uma seção **“Atualizar base de restaurantes”**. Para adicionar ou atualizar restaurantes:
   - Crie um arquivo `.txt` conforme as instruções detalhadas em [`instrucoes_txt_atualizacao.md`](instrucoes_txt_atualizacao.md), incluindo um parágrafo por restaurante com as principais informações (nome, endereço, tipo de cozinha, horários, se aceita vale-refeição, etc.).
   - Faça upload do arquivo na barra lateral e clique em **“Processar descrições e atualizar base”**.
   - O aplicativo enviará essas descrições ao modelo da OpenAI, que irá extrair as informações e mesclá-las ao `pinheiros_restaurants.json`.

   Consulte o arquivo [`instrucoes_txt_atualizacao.md`](instrucoes_txt_atualizacao.md) para exemplos, dados obrigatórios e dicas de formatação.
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


- Mudanças no arquivo JSON feitas via Streamlit Cloud podem ser perdidas em rebuilds do app. Para uso em produção, considere armazenamento externo.
- O modo IA depende da configuração correta das variáveis e da chave da OpenAI.
- O modo offline pode não extrair todos os campos; quanto mais completo o texto, melhor o resultado.
- O aplicativo **não executa buscas na internet**; toda a informação vem do arquivo JSON ou das descrições fornecidas. Caso deseje dados mais recentes, edite o arquivo de descrições e atualize a base.
- A extração automática depende da API da OpenAI. Verifique se sua chave possui crédito suficiente.

## Licença

Este projeto é fornecido apenas para fins educacionais e demonstrativos. Nenhuma garantia é fornecida quanto à atualidade dos dados dos restaurantes ou à disponibilidade contínua das APIs.