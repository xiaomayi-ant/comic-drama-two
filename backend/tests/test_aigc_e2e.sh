#!/usr/bin/env bash
# ==========================================================
# AIGC 端到端测试脚本
# 前提：FastAPI 服务 + Celery worker + Redis 已启动
# 用法：bash tests/test_aigc_e2e.sh
# ==========================================================

set -euo pipefail

API_BASE="http://localhost:8000/api/v1/storyboard"
RUN_FILE="outputs/run_20260301T063458Z_e595d574-f469-4152-9310-70a402a63fa7.json"

echo "===== Step 1: 从运行产物提取 script_data 并创建 Episode ====="

# 用 jq 提取 script_data 和 thread_id
THREAD_ID=$(jq -r '.thread_id' "$RUN_FILE")
SCRIPT_DATA=$(jq '.script_data' "$RUN_FILE")

PAYLOAD=$(jq -n \
  --arg tid "$THREAD_ID" \
  --argjson sd "$SCRIPT_DATA" \
  '{script_data: $sd, thread_id: $tid}')

RESP=$(curl -s -X POST "${API_BASE}/episodes/from-script" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

echo "创建 Episode 响应: $RESP"

EPISODE_ID=$(echo "$RESP" | jq -r '.episode_id')
if [ "$EPISODE_ID" = "null" ] || [ -z "$EPISODE_ID" ]; then
  echo "ERROR: 创建 Episode 失败"
  exit 1
fi
echo "Episode ID: $EPISODE_ID"

echo ""
echo "===== Step 2: 触发 AIGC 生成 ====="

AIGC_RESP=$(curl -s -X POST "${API_BASE}/episodes/${EPISODE_ID}/generate-aigc")
echo "AIGC 响应: $AIGC_RESP"

TASK_ID=$(echo "$AIGC_RESP" | jq -r '.task_id')
if [ "$TASK_ID" = "null" ] || [ -z "$TASK_ID" ]; then
  echo "ERROR: 创建 AIGC 任务失败"
  exit 1
fi
echo "Task ID: $TASK_ID"

echo ""
echo "===== Step 3: 轮询任务状态 ====="

while true; do
  STATUS_RESP=$(curl -s "${API_BASE}/tasks/${TASK_ID}")
  STATUS=$(echo "$STATUS_RESP" | jq -r '.status')
  PROGRESS=$(echo "$STATUS_RESP" | jq -r '.progress')
  MESSAGE=$(echo "$STATUS_RESP" | jq -r '.message')

  echo "[$(date +%H:%M:%S)] status=$STATUS progress=$PROGRESS message=$MESSAGE"

  if [ "$STATUS" = "completed" ]; then
    echo ""
    echo "===== AIGC 任务完成 ====="
    echo "$STATUS_RESP" | jq '.'
    break
  fi

  if [ "$STATUS" = "failed" ]; then
    echo ""
    echo "===== AIGC 任务失败 ====="
    echo "$STATUS_RESP" | jq '.'
    exit 1
  fi

  sleep 10
done

echo ""
echo "===== Step 4: 检查 DB 中的 image_url / video_url ====="
echo "请手动检查 SQLite："
echo "  sqlite3 data/writer.db \"SELECT storyboard_number, image_url, video_url FROM storyboards WHERE episode_id=${EPISODE_ID};\""
