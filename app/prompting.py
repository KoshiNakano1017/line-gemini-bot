from __future__ import annotations

from dataclasses import dataclass

from app.rag.chroma_store import RetrievedItem


@dataclass(frozen=True)
class PromptParts:
    system_instruction: str
    user_prompt: str


def build_prompt(*, role: str, user_input: str, contexts: list[RetrievedItem]) -> PromptParts:
    role = (role or "").strip()
    user_input = (user_input or "").strip()

    ctx_lines: list[str] = [
        "以下のナレッジを参考に回答してください。",
        "該当がない場合は「分かりかねます」と答えてください。",
    ]

    if contexts:
        for idx, item in enumerate(contexts, start=1):
            ctx_lines.append("")
            ctx_lines.append(f"[検索結果{idx}] (similarity={item.similarity:.3f})")
            ctx_lines.append(item.document.strip())
    else:
        ctx_lines.append("")
        ctx_lines.append("[検索結果] 該当なし")

    user_prompt = "\n".join(
        [
            "Context (RAG):",
            "\n".join(ctx_lines).strip(),
            "",
            "User Input:",
            user_input,
        ]
    ).strip()

    return PromptParts(system_instruction=role, user_prompt=user_prompt)
