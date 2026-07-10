"""図面拾い出しAIデモ — Shift Gears
起動: streamlit run app.py
"""
import os

import pandas as pd
import streamlit as st

from excel_export import (COLUMNS, build_estimate_from_rows, rows_from_shiage,
                          rows_from_tategu)
from extractor import extract_shiage, extract_tategu, pdf_to_images

st.set_page_config(page_title="見積もりAI", page_icon="📐", layout="wide")


def _secret(name: str) -> str:
    try:
        return st.secrets.get(name, "") or os.environ.get(name, "")
    except Exception:
        return os.environ.get(name, "")


# パスコードゲート(Secretsに APP_PASSCODE がある場合のみ有効)
_passcode = _secret("APP_PASSCODE")
if _passcode:
    if not st.session_state.get("authed"):
        pw = st.text_input("パスコード", type="password")
        if pw == _passcode:
            st.session_state.authed = True
            st.rerun()
        st.stop()

st.title("📐 見積もりAI")

with st.sidebar:
    provider = st.radio("AI", ["gemini", "claude"], horizontal=True)
    key_env = "GEMINI_API_KEY" if provider == "gemini" else "ANTHROPIC_API_KEY"
    api_key = st.text_input("API Key", type="password", value=_secret(key_env))
    company = st.text_input("宛名", value="株式会社サンプル工務店")

if "rows" not in st.session_state:
    st.session_state.rows = []  # 見積明細行(区分つき)

# ---------- 1. アップロード ----------
input_mode = st.radio("入力", ["ファイル", "カメラ"], horizontal=True, label_visibility="collapsed")

image = None
if input_mode == "ファイル":
    uploaded = st.file_uploader("図面", type=["pdf", "png", "jpg", "jpeg"])
    if uploaded:
        if uploaded.type == "application/pdf":
            pages = pdf_to_images(uploaded.read())
            page_no = st.number_input("対象ページ", 1, len(pages), 1) - 1
            image = pages[page_no]
        else:
            image = uploaded.read()
        st.image(image, width=450)
else:
    shot = st.camera_input("図面を撮影")
    if shot:
        image = shot.read()

# ---------- 2. 拾い出し ----------
doc_type = st.radio("表の種類", ["建具表", "仕上表"], horizontal=True)

if st.button("見積もりデータを表示", type="primary", use_container_width=True,
             disabled=image is None):
    if not api_key:
        st.error("APIキー未入力")
    else:
        with st.spinner("読み取り中…"):
            try:
                prices = pd.read_csv("unit_prices.csv")
                if doc_type == "建具表":
                    new_rows = rows_from_tategu(extract_tategu(image, api_key, provider), prices)
                    kubun = "建具工事"
                else:
                    new_rows = rows_from_shiage(extract_shiage(image, api_key, provider), prices)
                    kubun = "内装工事"
                # 同じ区分は置き換え(再実行で重複しない)
                st.session_state.rows = [r for r in st.session_state.rows
                                         if r.get("区分") != kubun] + new_rows
                st.success(f"{len(new_rows)}行")
            except Exception as e:
                st.error(f"読み取り失敗: {e}")

# ---------- 3. 確認・修正 ----------
df = pd.DataFrame(st.session_state.rows, columns=COLUMNS)
edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="editor")

# 合計金額(編集内容を即時反映: 数量×単価で再計算)
def _calc_total(rows):
    total = 0
    for x in rows:
        try:
            total += round(float(x.get("数量")) * float(x.get("単価")))
        except (TypeError, ValueError):
            pass
    return total

if not edited.empty:
    total = _calc_total(edited.to_dict("records"))
    c1, c2 = st.columns([3, 1])
    with c2:
        st.metric("合計(税別)", f"¥{total:,}")

col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🗑 クリア"):
        st.session_state.rows = []
        st.rerun()

if not edited.empty:
    xlsx = build_estimate_from_rows(edited.to_dict("records"), company=company)
    st.download_button("📄 Excel出力", xlsx,
                       file_name="見積内訳書_AI拾い出し.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       type="primary", use_container_width=True)
