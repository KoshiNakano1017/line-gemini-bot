#!/bin/bash
# LINE RAG Bot - Cloud Run デプロイスクリプト
# .env から環境変数を読み込み、API と管理画面をデプロイします。
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# .env を読み込み（コメント・空行を除外）
load_env() {
  if [ ! -f .env ]; then
    echo "Error: .env が見つかりません。sample.env をコピーして .env を作成してください。"
    exit 1
  fi
  set -a
  while IFS= read -r line; do
    line="${line%%$'\r'}"
    [[ "$line" =~ ^#.*$ ]] && continue
    [[ -z "$line" ]] && continue
    if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
      export "$line"
    fi
  done < .env
  set +a
}

load_env

# 必須変数
PROJECT_ID="${FIRESTORE_PROJECT_ID:-$GOOGLE_CLOUD_PROJECT}"
REGION="${GCP_REGION:-asia-northeast1}"

if [ -z "$PROJECT_ID" ]; then
  echo "Error: FIRESTORE_PROJECT_ID または GOOGLE_CLOUD_PROJECT を .env に設定してください。"
  exit 1
fi

if [ -z "$GEMINI_API_KEY" ]; then
  echo "Error: GEMINI_API_KEY を .env に設定してください。"
  exit 1
fi

echo "=== デプロイ開始 ==="
echo "Project: $PROJECT_ID"
echo "Region:  $REGION"
echo ""

# gcloud プロジェクトを設定
gcloud config set project "$PROJECT_ID"

# オプション: --setup-only で初期設定のみ実行
if [ "${1:-}" = "--setup-only" ]; then
  echo "--- 初期設定（API有効化・Artifact Registry）---"
  gcloud services enable run.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com cloudbuild.googleapis.com --quiet
  gcloud artifacts repositories create line-rag --repository-format=docker --location="$REGION" 2>/dev/null || echo "  (line-rag リポジトリは既に存在します)"
  echo "--- Firestore 権限の付与 ---"
  PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/datastore.user" \
    --quiet 2>/dev/null || true
  echo "初期設定完了。デプロイするには ./deploy.sh を実行してください。"
  exit 0
fi

# FastAPI デプロイ
echo "--- FastAPI (LINE Webhook) をビルド・デプロイ ---"
gcloud builds submit --config=cloudbuild.api.yaml \
  --substitutions="_PROJECT_ID=$PROJECT_ID,_REGION=$REGION"

# Streamlit デプロイ
echo "--- Streamlit 管理画面をビルド・デプロイ ---"
gcloud builds submit --config=cloudbuild.admin.yaml \
  --substitutions="_PROJECT_ID=$PROJECT_ID,_REGION=$REGION"

# 環境変数を設定（.env の値を使用）
echo "--- 環境変数を Cloud Run に反映 ---"

# カンマや特殊文字をエスケープ（値にカンマが含まれると gcloud が誤解析するため）
escape_for_gcloud() {
  printf '%s' "$1" | sed "s/,/\\\\,/g"
}

API_ENV_VARS="FIRESTORE_PROJECT_ID=$PROJECT_ID"
API_ENV_VARS="$API_ENV_VARS,GEMINI_API_KEY=$(escape_for_gcloud "${GEMINI_API_KEY}")"
[ -n "$LINE_CHANNEL_SECRET" ]    && API_ENV_VARS="$API_ENV_VARS,LINE_CHANNEL_SECRET=$(escape_for_gcloud "${LINE_CHANNEL_SECRET}")"
[ -n "$LINE_CHANNEL_ACCESS_TOKEN" ] && API_ENV_VARS="$API_ENV_VARS,LINE_CHANNEL_ACCESS_TOKEN=$(escape_for_gcloud "${LINE_CHANNEL_ACCESS_TOKEN}")"

gcloud run services update line-rag-api \
  --region="$REGION" \
  --set-env-vars="$API_ENV_VARS"

gcloud run services update line-rag-admin \
  --region="$REGION" \
  --set-env-vars="FIRESTORE_PROJECT_ID=$PROJECT_ID,GEMINI_API_KEY=$(escape_for_gcloud "${GEMINI_API_KEY}")"

# URL を表示
echo ""
echo "=== デプロイ完了 ==="
API_URL=$(gcloud run services describe line-rag-api --region="$REGION" --format='value(status.url)')
ADMIN_URL=$(gcloud run services describe line-rag-admin --region="$REGION" --format='value(status.url)')
echo ""
echo "API (LINE Webhook):  $API_URL/webhook"
echo "管理画面:            $ADMIN_URL"
echo ""
echo "LINE Developers の Webhook URL に上記 API の URL を設定してください。"
