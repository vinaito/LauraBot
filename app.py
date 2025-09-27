import json
from pathlib import Path
import streamlit as st

# -------------------- Config --------------------
st.set_page_config(page_title="LauraBot · Guia Pinheiros", page_icon="🍽️", layout="centered")

# Guardas contra loops de rerun/redirect
if "_init_done" not in st.session_state:
    st.session_state._init_done = True
    st.session_state.chat = []  # (role, content)

# -------------------- Dados locais --------------------
@st.cache_data(show_spinner=False)
def load_db(path: str = "pinheiros_restaurants.json"):
    p = Path(path)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        st.warning(f"Falha ao ler JSON: {e}")
        return []

DB = load_db()

# -------------------- OpenAI client --------------------
@st.cache_resource(show_spinner=False)
def get_openai_client():
    from openai import OpenAI
    # Usa OPENAI_API_KEY a partir de st.secrets, se existir
    api_key = st.secrets.get("OPENAI_API_KEY", None)
    if not api_key:
        return None, "Defina OPENAI_API_KEY em Secrets (Streamlit Cloud > App > Settings > Secrets)."
    try:
        client = OpenAI(api_key=api_key)
        return client, None
    except Exception as e:
        return None, f"Erro ao iniciar OpenAI: {e}"

client, client_err = get_openai_client()

# -------------------- Funções --------------------
SYSTEM_PROMPT = """Você é o LauraBot. Responda em PT-BR, curto e útil.
Baseie-se primeiro na base local (campos: name, address, cuisine, hours, price_level, description).
Se faltar dado, explique brevemente a limitação. Evite inventar.
Formato: liste 3–8 opções com 1–2 linhas por item.
"""

def build_context_snippets(query: str, max_items: int = 8):
    q = query.strip().lower()
    if not q:
        return []
    scored = []
    for r in DB:
        blob = " ".join([
            r.get("name",""), r.get("address",""),
            " ".join(r.get("cuisine",[])),
            r.get("hours",""), r.get("price_level",""),
            r.get("description","")
        ]).lower()
        score = sum(token in blob for token in q.split())
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:max_items]]

def format_snippets(snips):
    if not snips:
        return "Nenhum item na base local para essa busca."
    out = []
    for r in snips:
        out.append(
            f"**{r.get('name','(sem nome)')}** — {', '.join(r.get('cuisine', [])) or 'cozinha não informada'}\n"
            f"{r.get('address','')} • {r.get('price_level','?')} • {r.get('hours','(horário não informado)')}\n"
            f"_{r.get('description','')}_"
        )
    return "\n\n".join(out)

def ask_openai(user_msg: str, context_snips: list, stream: bool = True):
    """Chama OpenAI Responses API com contexto da base local."""
    if client is None:
        raise RuntimeError(client_err or "OpenAI client não inicializado")

    # Monta um "documento" de contexto para o modelo
    context_text = "\n\n".join(
        [f"- {r.get('name','')} | {', '.join(r.get('cuisine', []))} | {r.get('address','')} | {r.get('hours','')} | {r.get('price_level','')} | {r.get('description','')}"
         for r in context_snips]
    ) or "(sem correspondências locais)"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Pergunta: {user_msg}\n\nBase local (use com prioridade):\n{context_text}"}
    ]

    # Modelo: escolha um estável/custo-eficiente para produção
    model_name = "gpt-5-mini"  # rápido/barato p/ Q&A estruturado
    # Alternativas: "gpt-5" (qualidade maior) — ajuste conforme orçamento/latência.  [oai_citation:1‡OpenAI plataforma](https://platform.openai.com/docs/models?utm_source=chatgpt.com)

    if stream:
        # Streaming incremental
        stream_resp = client.responses.create(
            model=model_name,
            messages=messages,
            temperature=0.2,
            stream=True,
        )
        return stream_resp
    else:
        resp = client.responses.create(
            model=model_name,
            messages=messages,
            temperature=0.2,
        )
        # Extrai texto completo
        full = ""
        for item in resp.output_text.splitlines():
            full += item + "\n"
        return full

# -------------------- UI --------------------
st.title("LauraBot · Guia de Restaurantes em Pinheiros")
st.caption("Pergunte por tipo de cozinha, rua, faixa de preço, horário, etc. (com OpenAI)")

with st.sidebar:
    st.header("Ferramentas")
    st.markdown("- Base local: **pinheiros_restaurants.json**")
    use_stream = st.toggle("Streaming de respostas", value=True)
    st.divider()
    st.subheader("Atualizar base (opcional)")
    up = st.file_uploader("Envie um .txt com descrições (1 restaurante por parágrafo)", type=["txt"])
    if up and st.button("Processar e atualizar JSON"):
        st.info("Rotina de extração via LLM pode ser ligada aqui depois; mantendo offline por segurança.")
        # (Se quiser, aqui você pluga um extrator usando o mesmo client, sem st.rerun em loop.)

if client_err:
    st.warning(f"OpenAI: {client_err}")

user_prompt = st.chat_input("O que você procura?")
if user_prompt:
    st.session_state.chat.append(("user", user_prompt))
    snips = build_context_snippets(user_prompt)

    # UI: imprime contexto local como "debug leve" (colapse)
    with st.expander("Ver itens da base local usados no contexto", expanded=False):
        st.markdown(format_snippets(snips))

    if client:
        if use_stream:
            # Streaming para a UI
            with st.chat_message("assistant"):
                placeholder = st.empty()
                acc = ""
                try:
                    stream = ask_openai(user_prompt, snips, stream=True)
                    for event in stream:
                        # `.output_text_delta` nos eventos de streaming da Responses API
                        delta = getattr(event, "output_text_delta", None)
                        if delta:
                            acc += delta
                            placeholder.markdown(acc)
                    # Garante conteúdo final
                    final_text = acc.strip() or "Sem resposta."
                except Exception as e:
                    final_text = f"Erro na chamada OpenAI: {e}"
                st.session_state.chat.append(("assistant", final_text))
        else:
            # Chamada não-streaming
            try:
                full = ask_openai(user_prompt, snips, stream=False)
            except Exception as e:
                full = f"Erro na chamada OpenAI: {e}"
            st.session_state.chat.append(("assistant", full))
    else:
        # Fallback local (sem OpenAI)
        st.session_state.chat.append(("assistant", format_snippets(snips)))

# Replay do histórico (idempotente; sem mexer em URL/params)
for role, content in st.session_state.chat:
    with st.chat_message(role):
        st.markdown(content)

st.divider()
st.caption("Dica: evite alterar URL/`query_params` no código para não causar loops. Streaming e uso do client seguem a API oficial da OpenAI.")
