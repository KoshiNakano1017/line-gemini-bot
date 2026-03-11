# LINE RAG Bot (FastAPI + ChromaDB + Gemini + Streamlit)

LINEで受けた質問に対して、管理画面で設定した **ロール（System Instruction）** と、登録済みの **ナレッジ（RAG）** を元に Gemini が回答します。

## 構成

- **FastAPI**: `POST /webhook`（LINE Webhook受信→RAG検索→Gemini生成→返信）
- **ChromaDB**: ナレッジのベクトルDB（ローカル永続）
- **Streamlit**: 管理画面（ロール編集、Q&A登録/削除、再埋め込み）
- **SQLite**: ロール（BotRole）の保存

## セットアップ

1) 依存関係のインストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) 環境変数

`env.example` を参考に `.env` を作成してください。

必須:
- `GEMINI_API_KEY`
- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`

推奨:
- `GEMINI_MODEL=gemini-1.5-flash`（`.env`で指定。未指定ならこれがデフォルト）
  - ※ `models/` は付けずに指定してください（例: `gemini-2.5-flash`）。付いていても内部で自動的に剥がします。

## 起動

FastAPI:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

管理画面（Streamlit）:

```bash
streamlit run streamlit_app.py
```

## LINE Webhook URL（開発）

ローカルで受信するには **HTTPSの外部URL** が必要です。`ngrok` などを使い、FastAPI(8000)を公開します。

例:

```bash
ngrok http 8000
```

表示された HTTPS URL に `/webhook` を付けたものを、LINE Developers の Messaging API チャネルに設定します。

例:
- `https://xxxx.ngrok-free.app/webhook`

## RAG仕様（実装）

- Embeddingモデル: `gemini-embedding-001`（`output_dimensionality=768`）
- ベクトルDB: ChromaDB（永続: `./data/chroma`）
- 検索: コサイン類似度の Top-K（デフォルト3件）
- プロンプト:
  - System Instruction: 管理画面で設定したロール
  - Context: 検索結果を列挙（該当なしの場合は「分かりかねます」指示）
  - User Input: LINEの入力文

補足（テスト用）:
- ナレッジが0件、または検索結果が0件のときは、Geminiにユーザー入力をそのまま渡して回答させるフォールバックを有効化できます（デフォルトON）
  - `.env`: `RAG_FALLBACK_TO_LLM=true|false`

## データ保存先（デフォルト）

- Chroma: `./data/chroma`
- SQLite: `./data/config.sqlite3`

必要なら `.env` で `DATA_DIR` / `CHROMA_DIR` / `SQLITE_PATH` を変更できます。
