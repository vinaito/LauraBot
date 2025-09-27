import json
from pathlib import Path
import time
import sys
import streamlit as st

# -------------------- Config --------------------
st.set_page_config(
    page_title="LauraBot · Guia Pinheiros",
    page_icon="🍽️",
    layout="centered",
    initial_sidebar_state="collapsed",
)
_BOOT_T0 = time.perf_counter()

# Guardas contra loops de rerun/redirect
if "_init_done" not in st.session_state:
    st.session_state._init_done = True
    st.session_state.chat = []  # (role, content)

# -------------------- Dados locais --------------------
@st.cache_data(show_spinner=False)
def load_db(path: str = "pinheiros_restaurants.json"):
    """Lê a base JSON e garante estrutura de lista de dicts."""
    p = Path(path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return [d for d in data if isinstance(d, dict)]
    except Exception as e:
        st.warning(f"Falha ao ler JSON: {e}")
        return []

DB = load_db()

# -------------------- OpenAI client --------------------
@st.cache_resource(show_spinner=False)
def get_openai_client():
    from openai import OpenAI
    api_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else None
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
    """Busca simples na base local com tolerância a None e tipos variados."""
    def as_str(x):
        return "" if x is None else str(x)

    def cuisine_as_str(v):
        if v is None:
            return ""
        if isinstance(v, (list, tuple, set)):
            return " ".join(as_str(x) for x in v if as_str(x))
        return as_str(v)

    q = (query or "").strip().lower()
    if not q:
        return []

    scored = []
    for r in (DB or []):
        if not isinstance(r, dict):
            continue
        parts = [
            as_str(r.get("name")),
            as_str(r.get("address")),
            cuisine_as_str(r.get("cuisine")),
            as_str(r.get("hours")),
            as_str(r.get("price_level")),
            as_str(r.get("description")),
        ]
        blob = " ".join(parts).lower()
        score = sum(token in blob for token in q.split())
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:max_items]]

def format_snippets(snips):
    """Formata lista de restaurantes para exibir na UI."""
    if not snips:
        return "Nenhum item na base local para essa busca."
    out = []
    for r in snips:
        cuisine = r.get("cuisine", [])
        if not isinstance(cuisine, (list, tuple, set)):
            cuisine = [cuisine] if cuisine else []
        cuisine_str = ", ".join(str(x) for x in cuisine) or "cozinha não informada"
        out.append(
            f"**{r.get('name','(sem nome)')}** — {cuisine_str}\n"
            f"{r.get('address','')} • {r.get('price_level','?')} • {r.get('hours','(horário não informado)')}\n"
            f"_{r.get('description','')}_"
        )
    return "\n\n".join(out)

def ask_openai(user_msg: str, context_snips: list, stream: bool = True):
    """Chama OpenAI Responses API com contexto da base local."""
    if client is None:
        raise RuntimeError(client_err or "OpenAI client não inicializado")

    context_text = "\n\n".join(
        [f"- {r.get('name','')} | {', '.join(r.get('cuisine', [])) if isinstance(r.get('cuisine'), list) else str(r.get('cuisine') or '')} | "
         f"{r.get('address','')} | {r.get('hours','')} | {r.get('price_level','')} | {r.get('description','')}"
         for r in context_snips]
    ) or "(sem correspondências locais)"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Pergunta: {user_msg}\n\nBase local (use com prioridade):\n{context_text}"},
    ]

    model_name = "gpt-5-mini"  # ajuste se quiser mais qualidade: "gpt-5"

    if stream:
        return client.responses.create(
            model=model_name,
            messages=messages,
            temperature=0.2,
            stream=True,
        )
    else:
        resp = client.responses.create(
            model=model_name,
            messages=messages,
            temperature=0.2,
        )
        return resp.output_text

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
        # Aqui você pode plugar um extrator usando o mesmo client, sem st.rerun em loop.

if client_err:
    st.warning(f"OpenAI: {client_err}")

user_prompt = st.chat_input("O que você procura?")
if user_prompt:
    st.session_state.chat.append(("user", user_prompt))
    snips = build_context_snippets(user_prompt)

    # Contexto local (colapsado por padrão; mostra só 4 para aliviar mobile)
    with st.expander("Ver itens da base local usados no contexto", expanded=False):
        st.markdown(format_snippets(snips[:4]))

    if client:
        if use_stream:
            # Streaming com throttle para reduzir repaints no iPhone
            with st.chat_message("assistant"):
                placeholder = st.empty()
                acc = ""
                last_paint_len = 0
                paint_every = 120  # atualiza DOM a cada ~120 chars
                try:
                    stream = ask_openai(user_prompt, snips, stream=True)
                    for event in stream:
                        delta = getattr(event, "output_text_delta", None)
                        if delta:
                            acc += delta
                            if len(acc) - last_paint_len >= paint_every:
                                placeholder.markdown(acc)
                                last_paint_len = len(acc)
                    if len(acc) != last_paint_len:
                        placeholder.markdown(acc)
                    final_text = acc.strip() or "Sem resposta."
                except Exception as e:
                    final_text = f"Erro na chamada OpenAI: {e}"
                st.session_state.chat.append(("assistant", final_text))
        else:
            try:
                full = ask_openai(user_prompt, snips, stream=False)
            except Exception as e:
                full = f"Erro na chamada OpenAI: {e}"
            st.session_state.chat.append(("assistant", full))
    else:
        st.session_state.chat.append(("assistant", format_snippets(snips)))

# Limita histórico para não pesar render no mobile
MAX_HISTORY = 20
if len(st.session_state.chat) > MAX_HISTORY:
    st.session_state.chat = st.session_state.chat[-MAX_HISTORY:]

# Replay do histórico (idempotente)
for role, content in st.session_state.chat:
    with st.chat_message(role):
        st.markdown(content)

st.divider()
st.caption(f"⏱️ Boot: {time.perf_counter() - _BOOT_T0:.2f}s • Py {sys.version.split()[0]}")
