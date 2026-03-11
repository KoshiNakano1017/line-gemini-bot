from __future__ import annotations

import logging

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request

from app.config import get_settings
from app.line.client import LineMessagingClient
from app.line.dedup import ReplyTokenDeduper
from app.line.security import verify_line_signature
from app.llm.gemini import GeminiClient, GeminiModels
from app.prompting import build_prompt
from app.rag.chroma_store import ChromaKnowledgeStore
from app.storage.config_store import ConfigStore

app = FastAPI()

logger = logging.getLogger("line-rag-bot")

load_dotenv()
settings = get_settings()

config_store = ConfigStore(settings.sqlite_path)
knowledge_store = ChromaKnowledgeStore(settings.chroma_dir)

_gemini: GeminiClient | None = None
if settings.gemini_api_key:
    _gemini = GeminiClient(
        api_key=settings.gemini_api_key,
        models=GeminiModels(
            generate_model=settings.gemini_model,
            embed_model=settings.gemini_embed_model,
        ),
    )

_line: LineMessagingClient | None = None
if settings.line_channel_access_token:
    _line = LineMessagingClient(settings.line_channel_access_token)

reply_deduper = ReplyTokenDeduper(ttl_seconds=600)


@app.get("/health")
def health() -> dict:
    return {"ok": True}

@app.get("/debug/config")
def debug_config() -> dict:
    return {
        "gemini_model": settings.gemini_model,
        "gemini_embed_model": settings.gemini_embed_model,
        "rag_top_k": settings.rag_top_k,
        "rag_min_similarity": settings.rag_min_similarity,
        "rag_fallback_to_llm": settings.rag_fallback_to_llm,
        "has_gemini_api_key": bool(settings.gemini_api_key),
        "has_line_channel_secret": bool(settings.line_channel_secret),
        "has_line_channel_access_token": bool(settings.line_channel_access_token),
        "knowledge_count": knowledge_store.count(),
    }

@app.get("/debug/models")
def debug_models() -> dict:
    if _gemini is None:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set")
    # Returns names like "models/gemini-1.5-flash"
    return _gemini.list_supported_model_names()


@app.post("/webhook")
async def webhook(request: Request) -> dict:
    if not settings.line_channel_secret:
        raise HTTPException(status_code=500, detail="LINE_CHANNEL_SECRET is not set")
    if _line is None:
        raise HTTPException(status_code=500, detail="LINE_CHANNEL_ACCESS_TOKEN is not set")
    if _gemini is None:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set")

    body = await request.body()
    sig = request.headers.get("x-line-signature")
    if not verify_line_signature(
        channel_secret=settings.line_channel_secret,
        body=body,
        x_line_signature=sig,
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    events = payload.get("events") or []

    for ev in events:
        if ev.get("type") != "message":
            continue
        message = ev.get("message") or {}
        if message.get("type") != "text":
            continue

        reply_token = ev.get("replyToken")
        if not reply_token:
            continue
        if not reply_deduper.should_process(reply_token):
            continue

        user_text = (message.get("text") or "").strip()
        if not user_text:
            continue

        try:
            role = config_store.get().bot_role
            if knowledge_store.count() <= 0:
                # No knowledge yet: ask Gemini directly for testing.
                answer = _gemini.generate(
                    system_instruction=role,
                    user_text=user_text,
                    temperature=0.4,
                )
            else:
                q_emb = _gemini.embed_texts([user_text], task_type="RETRIEVAL_QUERY")[0]
                retrieved = knowledge_store.search(
                    query_embedding=q_emb,
                    top_k=settings.rag_top_k,
                    min_similarity=settings.rag_min_similarity,
                )

                if not retrieved and settings.rag_fallback_to_llm:
                    answer = _gemini.generate(
                        system_instruction=role,
                        user_text=user_text,
                        temperature=0.4,
                    )
                else:
                    prompt = build_prompt(role=role, user_input=user_text, contexts=retrieved)
                    answer = _gemini.generate(
                        system_instruction=prompt.system_instruction,
                        user_text=prompt.user_prompt,
                        temperature=0.2,
                    )

            if not answer:
                answer = "分かりかねます"
        except Exception:
            logger.exception(
                "Failed to generate answer (fallback). gemini_model=%r embed_model=%r",
                settings.gemini_model,
                settings.gemini_embed_model,
            )
            try:
                role = config_store.get().bot_role
                answer = _gemini.generate(
                    system_instruction=role,
                    user_text=user_text,
                    temperature=0.4,
                )
            except Exception:
                answer = "分かりかねます"

        try:
            await _line.reply_text(reply_token=reply_token, text=answer)
        except Exception:
            logger.exception("Failed to reply to LINE.")
            # Even if reply fails, do not fail the webhook entirely.
            pass

    return {"ok": True}
