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

## 管理画面の開き方（Streamlit）

1. 上記のコマンドで管理画面を起動します。
2. ブラウザで以下にアクセスします。
   - `http://localhost:8501`

※ 起動時にターミナルへ `Local URL` が表示される場合は、そのURLを開いてください。

## 管理画面での入力方法（ロール / ナレッジ）

管理画面は上部のタブで操作を切り替えます。

### ロール（System Instruction）の設定

1. タブ **「ロール（System Instruction）」** を開く
2. `BotRole` にロール文（キャラクター設定）を入力
3. **「更新」** を押す（SQLiteに保存されます）

### ナレッジ（想定Q&A）の登録

1. タブ **「ナレッジ（Q&A）」** を開く
2. **「想定質問」** と **「回答」** を入力（必須）
3. （任意）**カテゴリ** / **ソース** を入力
4. **「登録（埋め込み→Chroma保存）」** を押す
   - 登録時に Gemini で埋め込みを生成し、ChromaDBへ保存します

### ナレッジの削除

1. タブ **「ナレッジ（Q&A）」** の **「登録済みナレッジ」** を確認
2. 削除対象を選択し **「削除」** を押す

### ベクトル再作成（全件）

埋め込みモデルを変更した場合など、既存データを再ベクトル化したいときに使います。

1. タブ **「ナレッジ（Q&A）」** の **「ベクトル再作成（全件）」** を開く
2. **「全件を再埋め込みして上書き」** を押す

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
