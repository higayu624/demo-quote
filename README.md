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
