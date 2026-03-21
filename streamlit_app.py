from __future__ import annotations

from dotenv import load_dotenv

import streamlit as st

from app.config import get_settings
from app.llm.gemini import GeminiClient, GeminiModels
from app.storage.registry import get_config_store, get_knowledge_store

load_dotenv()
settings = get_settings()

st.set_page_config(page_title="LINE RAG Bot Admin", layout="wide")
st.title("LINE RAG Bot Admin")

cfg = get_config_store(settings)
store = get_knowledge_store(settings)

if not settings.gemini_api_key:
    st.warning("`GEMINI_API_KEY` が未設定です（ナレッジ登録のベクトル化ができません）")
    gemini = None
else:
    gemini = GeminiClient(
        api_key=settings.gemini_api_key,
        models=GeminiModels(
            generate_model=settings.gemini_model,
            embed_model=settings.gemini_embed_model,
        ),
    )

tab_role, tab_knowledge = st.tabs(["ロール（System Instruction）", "ナレッジ（Q&A）"])

with tab_role:
    st.subheader("ボットのロール設定")
    current = cfg.get()
    role = st.text_area("BotRole", value=current.bot_role, height=200)
    if st.button("更新", type="primary"):
        updated = cfg.set_role(role)
        st.success(f"更新しました（updated_at={updated.updated_at}）")

with tab_knowledge:
    st.subheader("ナレッジ登録")
    col1, col2 = st.columns(2)
    with col1:
        q = st.text_input("想定質問", value="")
        a = st.text_area("回答", value="", height=140)
    with col2:
        category = st.text_input("カテゴリ（任意）", value="")
        source = st.text_input("ソース（任意）", value="")

    if st.button("登録（埋め込み→Chroma保存）", type="primary", disabled=(gemini is None)):
        if not q.strip() or not a.strip():
            st.error("想定質問と回答は必須です")
        else:
            emb = gemini.embed_texts(
                [f"Q: {q.strip()}\nA: {a.strip()}"],
                task_type="RETRIEVAL_DOCUMENT",
            )[0]
            meta = {}
            if category.strip():
                meta["category"] = category.strip()
            if source.strip():
                meta["source"] = source.strip()
            item = store.upsert(question=q, answer=a, embedding=emb, metadata=meta)
            st.success(f"登録しました: id={item.id}")

    st.divider()
    st.subheader("登録済みナレッジ")
    items = store.list_all(limit=1000)
    st.caption(f"件数: {len(items)}")

    if items:
        options = {f"{it.id} | {it.metadata.get('question','')[:50]}": it.id for it in items}
        selected_label = st.selectbox("削除対象", list(options.keys()))
        if st.button("削除", type="secondary"):
            store.delete(options[selected_label])
            st.success("削除しました（画面を再読み込みすると反映されます）")

    st.divider()
    st.subheader("ベクトル再作成（全件）")
    if st.button("全件を再埋め込みして上書き", disabled=(gemini is None)):
        all_items = store.list_all(limit=2000)
        if not all_items:
            st.info("対象がありません")
        else:
            docs = [it.document for it in all_items]
            embs = gemini.embed_texts(docs, task_type="RETRIEVAL_DOCUMENT")
            n = store.reembed_all(embs)
            st.success(f"再埋め込み完了: {n}件")
