from __future__ import annotations

from dataclasses import dataclass

from google import genai
from google.genai import types
from google.genai.types import GenerateContentConfig
from google.genai.errors import ClientError


@dataclass(frozen=True)
class GeminiModels:
    generate_model: str
    embed_model: str


class GeminiClient:
    def __init__(self, api_key: str, models: GeminiModels):
        self._client = genai.Client(api_key=api_key)
        self._models = models

    def embed_texts(
        self,
        texts: list[str],
        *,
        task_type: str = "RETRIEVAL_DOCUMENT",
        output_dimensionality: int = 768,
    ) -> list[list[float]]:
        if not texts:
            return []
        resp = self._client.models.embed_content(
            model=self._models.embed_model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=output_dimensionality,
            ),
        )
        return [e.values for e in resp.embeddings]

    def generate(self, *, system_instruction: str, user_text: str, temperature: float = 0.2) -> str:
        config = GenerateContentConfig(
            system_instruction=[system_instruction],
            temperature=temperature,
        )
        model_candidates = [self._models.generate_model]
        # If a model is listed but not runnable for this key,
        # fall back to a stable alias.
        if self._models.generate_model not in {"gemini-flash-latest", "gemini-pro-latest"}:
            model_candidates.append("gemini-flash-latest")

        last_err: Exception | None = None
        resp = None
        for model in model_candidates:
            try:
                resp = self._client.models.generate_content(
                    model=model,
                    contents=user_text,
                    config=config,
                )
                break
            except ClientError as e:
                last_err = e
                # Retry on model availability / name issues only.
                msg = str(e)
                if ("no longer available to new users" in msg) or ("is not found" in msg) or (
                    "unexpected model name format" in msg
                ):
                    continue
                raise
        if resp is None:
            assert last_err is not None
            raise last_err
        text = getattr(resp, "text", None)
        if text is None:
            return ""
        return str(text).strip()

    def list_supported_model_names(self) -> dict[str, list[str]]:
        def _simplify(name: str) -> str:
            n = (name or "").strip()
            return n[len("models/") :] if n.startswith("models/") else n

        generate: list[str] = []
        embed: list[str] = []
        for m in self._client.models.list():
            name = getattr(m, "name", None)
            actions = getattr(m, "supported_actions", None) or []
            if not name:
                continue
            if "generateContent" in actions:
                generate.append(_simplify(name))
            if "embedContent" in actions:
                embed.append(_simplify(name))
        return {
            "generateContent": sorted(set(generate)),
            "embedContent": sorted(set(embed)),
        }
