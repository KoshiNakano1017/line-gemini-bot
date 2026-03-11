from __future__ import annotations

import httpx


class LineMessagingClient:
    def __init__(self, channel_access_token: str):
        self._token = channel_access_token

    async def reply_text(self, *, reply_token: str, text: str) -> None:
        url = "https://api.line.me/v2/bot/message/reply"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        payload = {
            "replyToken": reply_token,
            "messages": [{"type": "text", "text": text}],
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, headers=headers, json=payload)
            try:
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                detail = ""
                try:
                    detail = r.text
                except Exception:
                    detail = ""
                raise httpx.HTTPStatusError(
                    f"{e}. response={detail}",
                    request=e.request,
                    response=e.response,
                ) from e
