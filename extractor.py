"""図面PDF → 建具表・仕上表の構造化抽出(Claude / Gemini 両対応)"""
from __future__ import annotations
import base64
import json
import os

import fitz  # pymupdf
import requests

CLAUDE_MODEL = "claude-sonnet-4-6"
GEMINI_MODEL = "gemini-2.5-flash"

TATEGU_PROMPT = """あなたは建設業の積算担当者です。この画像は建築図面の「建具表」です。
表からすべての建具を読み取り、以下のJSON形式のみで出力してください。前置きやMarkdownは不要です。

{
  "items": [
    {
      "記号": "AW-1",
      "種別": "アルミサッシ引違い窓",
      "W": 1690,
      "H": 1170,
      "数量": 4,
      "備考": "網戸付"
    }
  ]
}

ルール:
- W/Hはmm単位の数値。読み取れない場合はnull
- 数量が書かれていない場合はnull(勝手に推定しない)
- 読み取りに自信がない項目は備考に「要確認」と付記する
"""

SHIAGE_PROMPT = """あなたは建設業の積算担当者です。この画像は建築図面の「仕上表(内部仕上表)」です。
表からすべての部屋を読み取り、以下のJSON形式のみで出力してください。前置きやMarkdownは不要です。

{
  "items": [
    {
      "室名": "リビング",
      "床": "複合フローリング t12",
      "壁": "PB t12.5 + ビニルクロス",
      "天井": "PB t9.5 + ビニルクロス",
      "床面積_m2": 21.5,
      "備考": ""
    }
  ]
}

ルール:
- 面積が表に記載されている場合のみ数値を入れる。無ければnull(推定しない)
- 読み取りに自信がない項目は備考に「要確認」と付記する
"""


def pdf_to_images(pdf_bytes: bytes, dpi: int = 300) -> list[bytes]:
    """PDFの各ページをPNG画像(bytes)に変換"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def _parse_json(text: str) -> dict:
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def _call_claude(image_png: bytes, prompt: str, api_key: str) -> dict:
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    b64 = base64.standard_b64encode(image_png).decode()
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return _parse_json(text)


def _call_gemini(image_png: bytes, prompt: str, api_key: str) -> dict:
    """Gemini API(無料枠あり・カード不要)をRESTで直叩き。503/429は自動リトライ"""
    import time
    b64 = base64.standard_b64encode(image_png).decode()
    body = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "image/png", "data": b64}},
                {"text": prompt},
            ]
        }]
    }
    models = [GEMINI_MODEL, "gemini-2.0-flash"]  # 過負荷時は旧モデルにフォールバック
    last_err = None
    for model in models:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent?key={api_key}")
        for attempt in range(3):
            r = requests.post(url, json=body, timeout=120)
            if r.status_code in (429, 503):
                last_err = f"{r.status_code} on {model}"
                time.sleep(5 * (attempt + 1))  # 5s, 10s, 15s
                continue
            r.raise_for_status()
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            return _parse_json(text)
    raise RuntimeError(f"Gemini過負荷でリトライ失敗({last_err})。数分待って再実行してください")


def _call_vision(image_png: bytes, prompt: str, api_key: str | None, provider: str) -> dict:
    key = api_key or os.environ.get(
        "ANTHROPIC_API_KEY" if provider == "claude" else "GEMINI_API_KEY")
    if provider == "gemini":
        return _call_gemini(image_png, prompt, key)
    return _call_claude(image_png, prompt, key)


def extract_tategu(image_png: bytes, api_key: str | None = None, provider: str = "claude") -> list[dict]:
    return _call_vision(image_png, TATEGU_PROMPT, api_key, provider).get("items", [])


def extract_shiage(image_png: bytes, api_key: str | None = None, provider: str = "claude") -> list[dict]:
    return _call_vision(image_png, SHIAGE_PROMPT, api_key, provider).get("items", [])
