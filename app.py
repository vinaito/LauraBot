# app.py
# LauraBot - Catálogo + Chatbot conversacional (Pinheiros)
# - Base JSON local: pinheiros_restaurants.json
# - Importação OFFLINE (regex) e opcional LLM (OpenAI) para extração
# - Chatbot: conversa sobre os restaurantes cadastrados (com/sem LLM)

import os
import re
import json
import time
from datetime import datetime
from typing import List, Dict, Tuple, Optional

import streamlit as st

DATA_FILE = "pinheiros_restaurants.json"

# ---------------------------
# Flags / Config de execução
# ---------------------------

def _get_flag_use_llm() -> bool:
    flag = False
    try:
        flag = bool(st.secrets.get("USE_LLM_EXTRACTOR", False))
    except Exception:
        pass
    envv = os.getenv("USE_LLM_EXTRACTOR")
    if envv is not None:
        flag = envv == "1" or envv.lower() in ("true", "yes", "on")
    return flag

USE_LLM = _get_flag_use_llm()

# =========
# DB utils
# =========

def load_db() -> List[Dict]:
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else list(data)
    except Exception as e:
        st.error(f"Falha ao ler {DATA_FILE}: {e}")
        return []

def save_db(rows: List[Dict]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

def merge_by_name(db: List[Dict], new_rows: List[Dict]) -> Tuple[List[Dict], List[str], List[str], List[Dict]]:
    idx = { (r.get("name","")).casefold(): i for i, r in enumerate(db) }
    added, updated, ignored = [], [], []
    for r in new_rows:
        key = (r.get("name","")).casefold()
        if not key:
            ignored.append(r); continue
        if key not in idx:
            db.append(r); idx[key]=len(db)-1; added.append(r["name"])
        else:
            i = idx[key]; base = db[i]; changed=False
            for fld in ("address","hours","price_level","highlights","description",
                        "neighborhood","cuisine","accepts_voucher","diet_options","accessibility"):
                if (not base.get(fld)) and r.get(fld):
                    base[fld]=r[fld]; changed=True
            if changed:
                base["_updated_at"]=datetime.utcnow().isoformat()+"Z"
                updated.append(r["name"])
            else:
                ignored.append(r)
    return db, added, updated, ignored

# ==================
# Parser OFFLINE TXT
# ==================

def _clean_file_urls(text: str) -> str:
    return re.sub(r"file:///[^\s]+", "", text)

def offline_parse_txt(raw: str) -> List[Dict]:
    raw = raw.replace("\r\n", "\n")
    blocks = [b.strip() for b in re.split(r"\n{2,}", raw) if b.strip()]
    out = []
    for b in blocks:
        first = b.splitlines()[0].strip()
        name = first.split(":", 1)[0].strip() if ":" in first else first

        def g(rx):
            m = re.search(rx, b, flags=re.I|re.M)
            return m.group(1).strip() if m else None

        rec = {
            "name": name,
            "address": g(r"Endereç[oa]\s*:\s*(.+)") or g(r"Fica na\s*(.+?)\."),
            "neighborhood": "Pinheiros",
            "cuisine": None,
            "price_level": g(r"Faixa de pre[cç]o\s*:\s*([$\u0024]{1,4}|.+)"),
            "accepts_voucher": None,
            "diet_options": None,
            "accessibility": None,
            "highlights": [h.strip() for h in (g(r"Destaques?\s*:\s*(.+)") or "").split(",") if h.strip()] or None,
            "description": _clean_file_urls(b),
            "hours": _clean_file_urls(g(r"Hor[áa]rio[s]?(?: de funcionamento)?\s*:\s*(.+)") or "") or None,
            "_source": "txt_import_offline",
            "_imported_at": datetime.utcnow().isoformat() + "Z",
        }
        for k in ("address","price_level"):
            if rec.get(k):
                rec[k] = _clean_file_urls(rec[k]).strip(" .;,")
        if rec["name"] and len(rec["name"]) >= 2:
            out.append(rec)
    return out

# ===================
# (Opcional) OpenAI
# ===================

def _get_openai_client():
    if not USE_LLM:
        return None, "LLM desativado por flag."
    api_key = None
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", None)
    except Exception:
        pass
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, "OPENAI_API_KEY não configurada."

    # openai >=1
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=api_key)
        return ("client_v1", client), None
    except Exception:
        pass
    # fallback legacy
    try:
        import openai  # type: ignore
        openai.api_key = api_key
        return ("client_legacy", openai), None
    except Exception as e:
        return None, f"Biblioteca OpenAI não encontrada: {e}"

def llm_parse_txt_to_records(raw: str) -> Tuple[List[Dict], Optional[str]]:
    client_tuple, err = _get_openai_client()
    if err:
        return [], err
    mode, client = client_tuple

    system = (
        "Você é um extrator de dados para restaurantes em Pinheiros (São Paulo). "
        "Receberá um texto livre com um ou mais restaurantes e deve retornar JSON com lista 'items' "
        "de objetos contendo: name, address, neighborhood='Pinheiros', cuisine, price_level, "
        "accepts_voucher, diet_options, accessibility, highlights (lista), description, hours. "
        "Não invente dados; deixe ausente se não houver. Remova URLs 'file:///...'."
    )
    user = "Texto a extrair:\n\n" + raw

    try:
        if mode == "client_v1":
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", st.secrets.get("OPENAI_MODEL", "gpt-4o-mini")),
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
        else:
            resp = client.ChatCompletion.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                temperature=0.1,
            )
            content = resp["choices"][0]["message"]["content"] or "{}"

        data = json.loads(content)
        items = data.get("items")
        if items is None:
            if isinstance(data, list):
                items = data
            else:
                match = re.search(r"\[[\s\S]*\]", content)
                items = json.loads(match.group(0)) if match else []

        out = []
        for r in items:
            if not isinstance(r, dict):
                continue
            r.setdefault("neighborhood", "Pinheiros")
            r.setdefault("_source", "txt_import_llm")
            r["_imported_at"] = datetime.utcnow().isoformat() + "Z"
            for k in ("address","price_level","hours","description"):
                v = r.get(k)
                if isinstance(v, str):
                    r[k] = _clean_file_urls(v).strip(" .;,")
            if "highlights" in r and isinstance(r["highlights"], str):
                r["highlights"] = [h.strip() for h in r["highlights"].split(",") if h.strip()]
            out.append(r)
        return out, None
    except Exception as e:
        return [], f"Falha na extração via LLM: {e}"

# =========================
# Retrieval para o Chatbot
# =========================

def _blob_for_search(r: Dict) -> str:
    parts = [
        str(r.get("name","")),
        str(r.get("address","")),
        str(r.get("neighborhood","")),
        str(r.get("cuisine","")),
        str(r.get("price_level","")),
        " ".join(r.get("highlights", []) if isinstance(r.get("highlights"), list) else []),
        str(r.get("description","")),
        str(r.get("hours","")),
    ]
    return " ".join(parts).casefold()

def retrieve_top_k(db: List[Dict], query: str, k: int = 5) -> List[Dict]:
    """
    Retrieval leve, sem dependências: pontua por ocorrências de termos no blob.
    Bônus para match no 'name' e em 'highlights'.
    """
    if not query:
        return db[:k]
    q_terms = [t for t in re.split(r"[^\wáéíóúâêîôûãõç]+", query.casefold()) if t]
    scores = []
    for r in db:
        blob = _blob_for_search(r)
        s = 0
        for t in q_terms:
            if t in blob:
                s += 1
            # bônus se bater no nome ou highlights
            if t in str(r.get("name","")).casefold():
                s += 2
            if isinstance(r.get("highlights"), list) and any(t in h.casefold() for h in r["highlights"]):
                s += 1
        scores.append((s, r))
    scores.sort(key=lambda x: x[0], reverse=True)
    return [r for s, r in scores[:k] if s > 0] or db[:min(k, len(db))]

# ===================
# Chatbot (com/sem LLM)
# ===================

def _llm_answer(query: str, context_items: List[Dict]) -> Tuple[str, Optional[str]]:
    client_tuple, err = _get_openai_client()
    if err:
        return "", err
    mode, client = client_tuple

    system = (
        "Você é a Laura, um chatbot que recomenda restaurantes cadastrados em uma base local de Pinheiros. "
        "RESPONDA SEMPRE EM PORTUGUÊS BRASILEIRO. "
        "Use SOMENTE o contexto fornecido a seguir (lista de restaurantes). "
        "Se algo não estiver na base, diga que não sabe. "
        "Se o usuário pedir filtros (ex: $$$, brunch, acessibilidade), priorize itens do contexto que batem, "
        "explique brevemente o motivo da escolha e liste 3-5 opções no máximo. Seja direto."
    )
    context = {"restaurants": context_items}
    user = f"Pergunta do usuário: {query}\n\nContexto (JSON):\n{json.dumps(context, ensure_ascii=False)}"

    try:
        if mode == "client_v1":
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", st.secrets.get("OPENAI_MODEL", "gpt-4o-mini")),
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                temperature=0.2,
            )
            content = resp.choices[0].message.content or ""
        else:
            resp = client.ChatCompletion.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                temperature=0.2,
            )
            content = resp["choices"][0]["message"]["content"] or ""
        return content, None
    except Exception as e:
        return "", f"Falha no LLM: {e}"

def _offline_answer(query: str, context_items: List[Dict]) -> str:
    """
    Geração de resposta offline, simples e objetiva.
    """
    if not context_items:
        return "Não encontrei nada correspondente na base."
    linhas = []
    for r in context_items:
        nome = r.get("name","(sem nome)")
        preco = r.get("price_level","—")
        destaques = ", ".join(r["highlights"]) if isinstance(r.get("highlights"), list) else (r.get("highlights") or "—")
        horas = r.get("hours","—")
        addr = r.get("address","—")
        linhas.append(f"• **{nome}** — {addr} — preço: {preco} — horário: {horas} — destaques: {destaques}")
    intro = "Aqui vão as melhores opções que encontrei na base para o seu pedido:\n\n"
    return intro + "\n".join(linhas[:5])

# ==========
# Interface
# ==========

st.set_page_config(page_title="LauraBot - Pinheiros", layout="wide")
st.title("LauraBot · Pinheiros")
st.caption("Converse e gerencie os restaurantes do bairro Pinheiros (SP).")

with st.sidebar:
    st.subheader("Status")
    db = load_db()
    st.metric("Registros na base", len(db))
    if USE_LLM:
        st.success("LLM: ATIVADO (chat e importação por IA disponíveis)")
    else:
        st.info("LLM: DESATIVADO — chat funciona offline; importação offline ativa.")

    st.divider()
    st.subheader("Ações")
    st.download_button("⬇️ Baixar base JSON", data=json.dumps(db, ensure_ascii=False, indent=2),
                       file_name="pinheiros_restaurants.json", mime="application/json")
    if st.button("🔎 Quais estão na base?"):
        nomes = [r.get("name") for r in db if r.get("name")]
        st.write(nomes if nomes else "Base vazia.")

tabs = st.tabs(["💬 Chatbot", "📚 Base", "⬆️ Importar .txt", "🛠️ Ferramentas"])

# ---- Tab Chatbot ----
with tabs[0]:
    st.subheader("Converse comigo sobre os restaurantes de Pinheiros")
    st.caption("Ex.: “Quero $$$ e brunch no domingo”, “Onde ir com criança?”, “Sugira 3 italianas contemporâneas”")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Oi! Eu sou a Laura 😊 Posso sugerir restaurantes em Pinheiros. O que você procura?"}
        ]

    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_msg = st.chat_input("Escreva sua pergunta…")
    if user_msg:
        # mostra a mensagem do usuário
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)

        # retrieval dos candidatos
        candidates = retrieve_top_k(db, user_msg, k=5)

        # responde com ou sem LLM
        if USE_LLM:
            answer, err = _llm_answer(user_msg, candidates)
            if err:
                answer = f"(Modo offline, pois houve erro no LLM) \n\n{_offline_answer(user_msg, candidates)}"
        else:
            answer = _offline_answer(user_msg, candidates)

        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)

# ---- Tab Base ----
with tabs[1]:
    st.subheader("Base de restaurantes (Pinheiros)")
    q = st.text_input("Busca por nome / endereço / destaque")
    show_raw = st.checkbox("Mostrar JSON bruto", value=False)
    filtered = db
    if q:
        qcf = q.casefold()
        def hit(r: Dict) -> bool:
            blob = " ".join([
                str(r.get("name","")),
                str(r.get("address","")),
                str(r.get("description","")),
                " ".join(r.get("highlights", []) if isinstance(r.get("highlights"), list) else [])
            ]).casefold()
            return qcf in blob
        filtered = [r for r in db if hit(r)]
    st.caption(f"Mostrando {len(filtered)} de {len(db)} registros.")
    for r in filtered:
        with st.expander(r.get("name","(sem nome)")):
            st.write(f"**Endereço:** {r.get('address','—')}")
            st.write(f"**Bairro:** {r.get('neighborhood','—')}")
            st.write(f"**Preço:** {r.get('price_level','—')}")
            st.write(f"**Horários:** {r.get('hours','—')}")
            if r.get("highlights"):
                st.write("**Destaques:**", ", ".join(r["highlights"]) if isinstance(r["highlights"], list) else r["highlights"])
            st.write(f"**Cozinha:** {r.get('cuisine','—')}")
            if show_raw:
                st.json(r)

# ---- Tab Importar ----
with tabs[2]:
    st.subheader("Importar restaurantes via .txt")
    st.caption("Cada **parágrafo** representa um restaurante. O parser offline reconhece campos básicos.")
    upload = st.file_uploader("Selecione o arquivo .txt", type=["txt"])

    if upload:
        raw = upload.read().decode("utf-8", errors="replace")

        st.caption("Pré-visualização (primeiros 1200 caracteres):")
        st.code(raw[:1200] + ("..." if len(raw) > 1200 else ""), language="markdown")

        colA, colB = st.columns(2)
        with colA:
            st.markdown("**Modo OFFLINE (sem IA)**")
            parsed_off = offline_parse_txt(raw)
            st.info(f"Pré-análise offline: {len(parsed_off)} blocos reconhecidos.")
            st.write(parsed_off[:3])

            if st.button("➡️ Iniciar importação (offline)"):
                with st.spinner("Importando (offline)…"):
                    db_before = load_db()
                    db_after, added, updated, ignored = merge_by_name(db_before, parsed_off)
                    save_db(db_after)
                    st.success(f"Importação concluída (OFFLINE). Novos: {len(added)} • Atualizados: {len(updated)} • Ignorados: {len(ignored)} • Total na base: {len(db_after)}")
                    if added: st.write("**Adicionados:**", added[:20])
                    if updated: st.write("**Atualizados:**", updated[:20])
                    st.toast("Base atualizada com sucesso.", icon="✅")
                    time.sleep(0.25)
                    st.rerun()

        with colB:
            st.markdown("**Modo LLM (quando ativado)**")
            if not USE_LLM:
                st.caption("Rotina via LLM pode ser ligada depois; mantendo offline por segurança.")
            else:
                records_llm, err = llm_parse_txt_to_records(raw[:8000])
                if err:
                    st.error(err)
                else:
                    st.info(f"Pré-análise LLM: {len(records_llm)} blocos reconhecidos.")
                    st.write(records_llm[:3])
                    if st.button("➡️ Iniciar importação (LLM)"):
                        with st.spinner("Importando (LLM)…"):
                            db_before = load_db()
                            db_after, added, updated, ignored = merge_by_name(db_before, records_llm)
                            save_db(db_after)
                            st.success(f"Importação concluída (LLM). Novos: {len(added)} • Atualizados: {len(updated)} • Ignorados: {len(ignored)} • Total na base: {len(db_after)}")
                            if added: st.write("**Adicionados:**", added[:20])
                            if updated: st.write("**Atualizados:**", updated[:20])
                            st.toast("Base atualizada com sucesso.", icon="✅")
                            time.sleep(0.25)
                            st.rerun()
    else:
        st.caption("Nenhum arquivo selecionado ainda.")

# ---- Tab Ferramentas ----
with tabs[3]:
    st.subheader("Ferramentas")
    st.markdown(
        "- **Download da base**: disponível na sidebar.\n"
        "- **Alternar LLM**: `USE_LLM_EXTRACTOR=true` em *Secrets* ou `USE_LLM_EXTRACTOR=1` via env.\n"
        "- **OPENAI_API_KEY/OPENAI_MODEL**: configure nos *Secrets* para LLM.\n"
        "- **Observação**: mudanças no JSON em Streamlit Cloud não são persistidas em rebuilds; para produção, considere armazenamento externo."
    )
    st.code(
        """
# .streamlit/secrets.toml (exemplo)
USE_LLM_EXTRACTOR = true
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"
        """.strip(),
        language="toml",
    )
