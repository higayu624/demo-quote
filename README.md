# 図面拾い出しAI デモ — Shift Gears

図面PDF(建具表・仕上表)をAIが読み取り、見積内訳書Excelを自動生成するデモ。

## セットアップ

```bash
pip install streamlit anthropic pymupdf openpyxl pandas
export ANTHROPIC_API_KEY=sk-ant-...
streamlit run app.py
```

## デモの流れ(商談用)

1. 相手の図面(or 国交省標準図面)の建具表ページをアップロード
2. 「AIで拾い出す」→ 30秒で建具リストが表になる
3. 誤認識があればその場で編集(「AIの下拾い+人の確認」を演出)
4. 「見積内訳書Excelを生成」→ ダウンロードして見せる

## カスタマイズポイント

- `unit_prices.csv` — 商談先の単価表に差し替えると「御社仕様」になる
- `excel_export.py` — 見積書レイアウト。相手のフォーマットに寄せる
- `extractor.py` の PROMPT — 対象工種・表形式に合わせて調整

## 構成

```
app.py          Streamlit UI
extractor.py    PDF→画像→Claude Visionで構造化抽出
excel_export.py 見積内訳書Excel生成
unit_prices.csv 単価マスタ(ダミー)
```

## 注意

- 平面図からの面積自動算出は未対応(精度リスク)。求積表・仕上表の記載面積を読む設計
- 数量・単価は必ず人が確認する前提のツール


## 本番デプロイ(Streamlit Community Cloud)

1. GitHubにprivateリポジトリを作りpush
   ```bash
   cd hiroidashi-demo
   git init && git add -A && git commit -m "demo"
   git remote add origin https://github.com/<user>/hiroidashi-demo.git
   git push -u origin main
   ```
2. https://share.streamlit.io → Sign in with GitHub → New app → リポジトリ/ブランチ/app.pyを指定 → Deploy
3. App settings → Secrets に以下を設定:
   ```toml
   GEMINI_API_KEY = "AIza..."
   APP_PASSCODE = "好きな合言葉"
   ```
4. 発行された https://◯◯.streamlit.app にスマホからアクセス

- APP_PASSCODEを設定すると起動時にパスコード入力を要求(未設定ならゲート無し)
- スマホでは入力を「カメラ」に切り替えると紙図面をその場で撮影→拾い出しできる
- 無料枠はスリープするので商談前に一度アクセスして起動しておくこと
