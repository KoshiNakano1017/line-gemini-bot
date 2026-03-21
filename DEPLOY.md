# 案A: Cloud Run + Firestore 完全無料寄りデプロイ

## 構成

| サービス | 役割 | 無料枠 |
|----------|------|--------|
| **Cloud Run** | FastAPI（Webhook）+ Streamlit（管理画面） | 月200万リクエスト、36万GB秒 |
| **Firestore** | ロール + ナレッジ（埋め込み含む） | 1GB、5万読/日、2万書/日 |
| **Gemini API** | 生成・埋め込み | 無料枠あり |

ベクトル検索は Firestore に保存した埋め込みを取得し、アプリ内でコサイン類似度を計算（数十〜100件程度向け）。

---

## 前提条件

- Google Cloud プロジェクト作成済み
- [課金を有効化](https://console.cloud.google.com/billing)（無料枠内でも必要）
- gcloud CLI インストール済み

---

## 1. 初期設定

```bash
# プロジェクトIDを設定
export PROJECT_ID=your-project-id
export REGION=asia-northeast1

gcloud config set project $PROJECT_ID
```

### 有効化する API

```bash
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### Artifact Registry リポジトリ作成

```bash
gcloud artifacts repositories create line-rag \
  --repository-format=docker \
  --location=$REGION
```

### Firestore データベース

[Firestore コンソール](https://console.cloud.google.com/firestore) で「ネイティブモード」の DB を作成（未作成の場合）。

---

## 2. デプロイ

### 一括デプロイ（推奨）

`.env` に必要な値を設定し、以下を実行します。

```bash
chmod +x deploy.sh
./deploy.sh
```

`.env` に必要な項目:
- `FIRESTORE_PROJECT_ID` または `GOOGLE_CLOUD_PROJECT`
- `GEMINI_API_KEY`
- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `GCP_REGION`（任意、デフォルト: asia-northeast1）

初回のみ API 有効化と Artifact Registry 作成が必要な場合:

```bash
./deploy.sh --setup-only   # 初期設定
./deploy.sh                # デプロイ
```

### 手動デプロイ

```bash
# .env を読み込む
set -a && source .env && set +a
export PROJECT_ID=${FIRESTORE_PROJECT_ID:-$GOOGLE_CLOUD_PROJECT}
export REGION=${GCP_REGION:-asia-northeast1}

# FastAPI
gcloud builds submit --config=cloudbuild.api.yaml \
  --substitutions=_PROJECT_ID=$PROJECT_ID,_REGION=$REGION

# Streamlit
gcloud builds submit --config=cloudbuild.admin.yaml \
  --substitutions=_PROJECT_ID=$PROJECT_ID,_REGION=$REGION

# 環境変数は deploy.sh 内の gcloud run services update を参照
```

---

## 4. URL 確認と LINE Webhook 設定

```bash
# API URL（LINE Webhook に設定）
gcloud run services describe line-rag-api --region=$REGION --format='value(status.url)'

# 管理画面 URL
gcloud run services describe line-rag-admin --region=$REGION --format='value(status.url)'
```

**LINE Developers** → Messaging API チャネル → Webhook URL に  
`https://line-rag-api-xxxxx-an.a.run.app/webhook` を設定。

---

## 5. サービスアカウント権限（Firestore）

Cloud Run のデフォルトサービスアカウントに Firestore 権限を付与します。

```bash
# プロジェクト番号を取得
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

# Cloud Datastore ユーザーロールを付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/datastore.user"
```

---

## トラブルシューティング

| 現象 | 対処 |
|------|------|
| Firestore 接続エラー | 上記 IAM 権限を確認、`FIRESTORE_PROJECT_ID` が正しいか確認 |
| 502 Bad Gateway | Cloud Run のログを確認、Gemini API キーが設定されているか |
| LINE Webhook が動かない | Webhook URL が `https://.../webhook` であること、署名検証用に LINE_CHANNEL_SECRET が必須 |

---

## コスト目安（無料枠内）

- **Cloud Run**: 月10人・週3回・5リクエスト程度なら無料枠内
- **Firestore**: 同程度の利用なら無料
- **Gemini API**: 無料枠あり（利用量に応じて）
