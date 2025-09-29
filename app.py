# app.py
# LauraBot - Importador e navegador de restaurantes (Pinheiros)
# Compatível com base JSON "pinheiros_restaurants.json"
# - Importação OFFLINE por parser heurístico (regex)
# - Importação opcional via LLM (OpenAI), ativada por flag USE_LLM_EXTRACTOR
# - Confirmações claras e contagens de novos/atualizados/ignorados

import os
import re
import json
import time
from datetime import datetime
from typing import List, Dict, Tuple, Optional

import streamlit as st

# =========================
# Configurações do projeto
# =========================

DATA_FILE = "pinheiros_restaurants.json"

def _get_flag_use_llm() -> bool:
    # Flag pode vir de secrets ou env var
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

# =============
# Utilidades DB
# =============

def load_db() -> List[Dict]:
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            # Caso esteja em outro formato inesperado, normaliza pra lista
            return list(data)
    except Exception as e:
        st.error(f"Falha ao ler {DATA_FILE}: {e}")
        return []

def save_db(rows: List[Dict]) -> None:
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Falha ao salvar {DATA_FILE}: {e}")
        raise

def merge_by_name(db: List[Dict], new_rows: List[Dict]) -> Tuple[List[Dict], List[str], List[str], List[Dict]]:
    """
    Deduplicação por 'name' (casefold). Em conflito, preenche apenas campos vazios na base.
    Retorna: (db_atualizada, nomes_adicionados, nomes_atualizados, itens_ignorados)
    """
    idx = { (r.get("name","")).casefold(): i for i, r in enumerate(db) }
    added, updated, ignored = [], [], []

    for r in new_rows:
        key = (r.get("name","")).casefold()
        if not key:
            ignored.append(r)
            continue

        if key not in idx:
            db.append(r)
            idx[key] = len(db) - 1
            added.append(r["name"])
        else:
            i = idx[key]
            base = db[i]
            changed = False
            # apenas preenche campos vazios ou inexistentes
            for fld in ("address","hours","price_level","highlights","description","neighborhood","cuisine","accepts_voucher","diet_options","accessibility"):
                if (not base.get(fld)) and r.get(fld):
                    base[fld] = r[fld]
                    changed = True
            if changed:
                base["_updated_at"] = datetime.utcnow().isoformat() + "Z"
                updated.append(r["name"])
            else:
                ignored.append(r)
    return db, added, updated, ignored

# ==================
# Parser OFFLINE TXT
# ==================

def _clean_file_urls(text: str) -> str:
    # remove lixo como file:///home/oai/redirect.html...
    return re.sub(r"file:///[^\s]+", "", text)

def offline_parse_txt(raw: str) -> List[Dict]:
    """
    Parser heurístico simples: espera 1 restaurante por bloco/parágrafo
    (separado por uma linha em branco). Campos reconhecidos:
    - name (primeira linha até ':', se existir)
    - address (regex "Endereço:")
    - hours (regex "Horário" / "Horários de funcionamento")
    - price_level (regex "Faixa de preço:")
    - highlights (regex "Destaques:")
    Mantém o texto completo no campo "description".
    """
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
            "address": g(r"Endereç[oa]\s*:\s*(.+)"),
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

        # limpeza adicional
        for k in ("address","price_level"):
            if rec.get(k):
                rec[k] = _clean_file_urls(rec[k]).strip(" .;,")

        if rec["name"] and len(rec["name"]) >= 2:
            out.append(rec)
    return out

# ===================
# (Opcional) LLM parse
# ===================

def _get_openai_client():
    """
    Tenta criar cliente OpenAI se a flag estiver ativa e a lib instalada.
    Suporta:
      - openai>=1.0 (from openai import OpenAI)
      - openai<1.0 (import openai; openai.ChatCompletion.create)
    """
    if not USE_LLM:
        return None, "LLM desativado por flag."
    # busca API KEY
    api_key = None
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", None)
    except Exception:
        pass
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return None, "OPENAI_API_KEY não configurada."

    # tenta import das libs
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=api_key)
        return ("client_v1", client), None
    except Exception:
        pass

    try:
        import openai  # type: ignore
        openai.api_key = api_key
        return ("client_legacy", openai), None
    except Exception as e:
        return None, f"Biblioteca OpenAI não encontrada: {e}"

def llm_parse_txt_to_records(raw: str) -> Tuple[List[Dict], Optional[str]]:
    """
    Chama LLM para extrair uma lista de registros. Retorna (records, error_msg)
    O schema de saída espelha o offline para mesclar sem fricção.
    """
    client_tuple, err = _get_openai_client()
    if err:
        return [], err
    mode, client = client_tuple

    system = (
        "Você é um extrator de dados para restaurantes em Pinheiros (São Paulo). "
        "Receberá um texto livre com um ou mais restaurantes e deve retornar uma lista JSON de objetos "
        "com os campos: name, address, neighborhood='Pinheiros', cuisine, price_level, accepts_voucher, "
        "diet_options, accessibility, highlights (lista de strings), description (texto original do bloco), "
        "hours. Não inclua URLs residuais como 'file:///...'. Não invente dados; deixe ausente se não houver."
    )
    user = (
        "Extraia o máximo de campos por bloco de restaurante. "
        "Considere que cada parágrafo é um restaurante. Texto a seguir:\n\n"
        + raw
    )

    try:
        if mode == "client_v1":
            # SDK openai >= 1.0
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", st.secrets.get("OPENAI_MODEL", "gpt-4o-mini")),
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
        else:
            # SDK legacy
            resp = client.ChatCompletion.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.1,
            )
            content = resp["choices"][0]["message"]["content"] or "{}"
        # Espera um JSON com {"items": [ ... ]}
        data = json.loads(content)
        items = data.get("items")
        if items is None:
            # Tenta fallback: talvez o modelo retornou um array direto
            if isinstance(data, list):
                items = data
            else:
                # tenta detectar json no texto
                match = re.search(r"\[[\s\S]*\]", content)
                items = json.loads(match.group(0)) if match else []

        # Sanitiza minimamente
        out = []
        for r in items:
            if not isinstance(r, dict):
                continue
            r.setdefault("neighborhood", "Pinheiros")
            r.setdefault("_source", "txt_import_llm")
            r["_imported_at"] = datetime.utcnow().isoformat() + "Z"
            # limpeza de file://
            for k in ("address","price_level","hours","description"):
                v = r.get(k)
                if isinstance(v, str):
                    r[k] = _clean_file_urls(v).strip(" .;,")
            # garante highlights como lista
            if "highlights" in r and isinstance(r["highlights"], str):
                r["highlights"] = [h.strip() for h in r["highlights"].split(",") if h.strip()]
            out.append(r)
        return out, None
    except Exception as e:
        return [], f"Falha na extração via LLM: {e}"

# ==========
# Interface
# ==========

st.set_page_config(page_title="LauraBot - Pinheiros", layout="wide")

st.title("LauraBot · Pinheiros")
st.caption("Navegue e importe restaurantes. A base é um arquivo JSON local.")

with st.sidebar:
    st.subheader("Status")
    db = load_db()
    st.metric("Registros na base", len(db))
    if USE_LLM:
        st.success("LLM: ATIVADO (importação por IA disponível)")
    else:
        st.info("LLM: DESATIVADO — importação roda **offline** por segurança.")

    st.divider()
    st.subheader("Ações")
    st.download_button("⬇️ Baixar base JSON", data=json.dumps(db, ensure_ascii=False, indent=2),
                       file_name="pinheiros_restaurants.json", mime="application/json")
    if st.button("🔎 Quais estão na base?"):
        nomes = [r.get("name") for r in db if r.get("name")]
        if nomes:
            st.write(nomes)
        else:
            st.warning("Base vazia.")

tabs = st.tabs(["📚 Base", "⬆️ Importar .txt", "🛠️ Ferramentas"])

# ---- Tab Base ----
with tabs[0]:
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
            if show_raw:
                st.json(r)

# ---- Tab Importar ----
with tabs[1]:
    st.subheader("Importar restaurantes via .txt")
    st.caption("Cada **parágrafo** deve representar um restaurante. O parser offline reconhece campos comuns (nome, endereço, horários, faixa de preço, destaques).")
    upload = st.file_uploader("Selecione o arquivo .txt", type=["txt"])

    if upload:
        raw = upload.read().decode("utf-8", errors="replace")

        st.caption("Pré-visualização do arquivo (primeiros 1200 caracteres):")
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
                    # força refresh do contador na sidebar
                    time.sleep(0.25)
                    st.rerun()

        with colB:
            st.markdown("**Modo LLM (quando ativado)**")
            if not USE_LLM:
                st.caption("Rotina de extração via LLM pode ser ligada depois; mantendo offline por segurança.")
            else:
                records_llm, err = llm_parse_txt_to_records(raw[:8000])  # limita o prompt
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
with tabs[2]:
    st.subheader("Ferramentas")
    st.markdown(
        "- **Download da base**: disponível na sidebar.\n"
        "- **Alternar LLM**: defina `USE_LLM_EXTRACTOR=true` no `.streamlit/secrets.toml` ou `USE_LLM_EXTRACTOR=1` como variável de ambiente.\n"
        "- **Chave OpenAI**: configure `OPENAI_API_KEY` (e opcionalmente `OPENAI_MODEL`) para usar o modo LLM.\n"
        "- **Observações**: quando o LLM estiver desligado, a importação **offline** continua disponível normalmente."
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
