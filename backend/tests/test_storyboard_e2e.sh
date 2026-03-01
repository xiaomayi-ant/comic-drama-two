#!/usr/bin/env bash
# ==========================================================
# 分镜 → AIGC → 视频合成 完整端到端测试脚本
#
# 前提：
#   1. FastAPI 服务已启动:  python main.py --serve
#   2. Celery worker 已启动: celery -A src.core.celery_app worker --loglevel=info
#   3. Redis / DashScope / OSS 外部服务可用
#
# 用法：cd backend && bash tests/test_storyboard_e2e.sh
# ==========================================================

set -euo pipefail

API_BASE="http://localhost:8000/api/v1/storyboard"
RUN_FILE="outputs/run_20260228T173523Z_f9ac3815-7f40-4bc9-af81-24b1524c899b.json"
DB_PATH="data/writer.db"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }

# 检查前置依赖
for cmd in jq curl sqlite3; do
  if ! command -v "$cmd" &>/dev/null; then
    fail "缺少命令: $cmd，请先安装"
    exit 1
  fi
done

if [ ! -f "$RUN_FILE" ]; then
  fail "测试数据文件不存在: $RUN_FILE"
  exit 1
fi

# 检查服务是否可达
if ! curl -s --max-time 3 "http://localhost:8000/docs" >/dev/null 2>&1; then
  fail "FastAPI 服务未启动，请先运行: python main.py --serve"
  exit 1
fi
ok "FastAPI 服务可达"

# ============================================================
# Step 1: 创建 Episode（从 script_data）
# ============================================================
echo ""
echo "============================================================"
info "Step 1: 从 script_data 创建 Episode + Storyboard"
echo "============================================================"

THREAD_ID=$(jq -r '.thread_id' "$RUN_FILE")
SCRIPT_DATA=$(jq '.final_result.script_data' "$RUN_FILE")

if [ "$SCRIPT_DATA" = "null" ]; then
  fail "无法提取 final_result.script_data，检查 RUN_FILE 格式"
  exit 1
fi

SHOT_COUNT=$(echo "$SCRIPT_DATA" | jq '.shots | length')
info "thread_id = $THREAD_ID"
info "script_data 包含 $SHOT_COUNT 个镜头"

PAYLOAD=$(jq -n \
  --arg tid "$THREAD_ID" \
  --argjson sd "$SCRIPT_DATA" \
  '{script_data: $sd, thread_id: $tid}')

RESP=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/episodes/from-script" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
  fail "创建 Episode 失败 (HTTP $HTTP_CODE): $BODY"
  exit 1
fi

EPISODE_ID=$(echo "$BODY" | jq -r '.episode_id')
EPISODE_TITLE=$(echo "$BODY" | jq -r '.title')

if [ "$EPISODE_ID" = "null" ] || [ -z "$EPISODE_ID" ]; then
  fail "创建 Episode 失败，响应: $BODY"
  exit 1
fi

ok "Episode 创建成功 — ID: $EPISODE_ID, 标题: $EPISODE_TITLE"

# ============================================================
# Step 2: 触发分镜生成任务
# ============================================================
echo ""
echo "============================================================"
info "Step 2: 触发分镜生成任务 (episode_id=$EPISODE_ID)"
echo "============================================================"

SB_RESP=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/episodes/storyboards" \
  -H "Content-Type: application/json" \
  -d "{\"episode_id\": $EPISODE_ID}")

HTTP_CODE=$(echo "$SB_RESP" | tail -1)
BODY=$(echo "$SB_RESP" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
  fail "触发分镜生成失败 (HTTP $HTTP_CODE): $BODY"
  exit 1
fi

SB_TASK_ID=$(echo "$BODY" | jq -r '.task_id')
info "分镜生成任务 Task ID: $SB_TASK_ID"

# 轮询分镜生成任务
info "轮询分镜生成任务状态..."
while true; do
  STATUS_RESP=$(curl -s "${API_BASE}/tasks/${SB_TASK_ID}")
  STATUS=$(echo "$STATUS_RESP" | jq -r '.status')
  PROGRESS=$(echo "$STATUS_RESP" | jq -r '.progress')
  MESSAGE=$(echo "$STATUS_RESP" | jq -r '.message')

  echo -e "  [$(date +%H:%M:%S)] status=${CYAN}${STATUS}${NC} progress=${PROGRESS}% message=${MESSAGE}"

  if [ "$STATUS" = "completed" ]; then
    ok "分镜生成完成"
    break
  fi
  if [ "$STATUS" = "failed" ]; then
    fail "分镜生成失败"
    echo "$STATUS_RESP" | jq '.'
    exit 1
  fi
  sleep 5
done

# 查询 DB 确认分镜数量和总时长
SB_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM storyboards WHERE episode_id=$EPISODE_ID;")
TOTAL_DUR=$(sqlite3 "$DB_PATH" "SELECT SUM(duration) FROM storyboards WHERE episode_id=$EPISODE_ID;")
ok "DB 中分镜数量: $SB_COUNT, 总时长: ${TOTAL_DUR}s"

# ============================================================
# Step 3: 触发 AIGC 生成（文生图 + 图生视频）
# ============================================================
echo ""
echo "============================================================"
info "Step 3: 触发 AIGC 生成 (episode_id=$EPISODE_ID)"
echo "============================================================"

AIGC_RESP=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/episodes/${EPISODE_ID}/generate-aigc")

HTTP_CODE=$(echo "$AIGC_RESP" | tail -1)
BODY=$(echo "$AIGC_RESP" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
  fail "触发 AIGC 生成失败 (HTTP $HTTP_CODE): $BODY"
  exit 1
fi

AIGC_TASK_ID=$(echo "$BODY" | jq -r '.task_id')
info "AIGC 任务 Task ID: $AIGC_TASK_ID"

# 轮询 AIGC 任务（间隔 15 秒，AIGC 耗时较长）
info "轮询 AIGC 任务状态（每 15 秒）..."
while true; do
  STATUS_RESP=$(curl -s "${API_BASE}/tasks/${AIGC_TASK_ID}")
  STATUS=$(echo "$STATUS_RESP" | jq -r '.status')
  PROGRESS=$(echo "$STATUS_RESP" | jq -r '.progress')
  MESSAGE=$(echo "$STATUS_RESP" | jq -r '.message')

  echo -e "  [$(date +%H:%M:%S)] status=${CYAN}${STATUS}${NC} progress=${PROGRESS}% message=${MESSAGE}"

  if [ "$STATUS" = "completed" ]; then
    ok "AIGC 生成完成"
    RESULT=$(echo "$STATUS_RESP" | jq -r '.result')
    if [ "$RESULT" != "" ] && [ "$RESULT" != "null" ]; then
      echo "  结果: $RESULT"
    fi
    break
  fi
  if [ "$STATUS" = "failed" ]; then
    fail "AIGC 生成失败"
    echo "$STATUS_RESP" | jq '.'
    exit 1
  fi
  sleep 15
done

# ============================================================
# Step 4: 检查 DB 中的 image_url / video_url
# ============================================================
echo ""
echo "============================================================"
info "Step 4: 检查 DB 中分镜的 image_url / video_url"
echo "============================================================"

echo ""
printf "%-4s %-20s %-60s %-60s\n" "No." "标题" "image_url" "video_url"
printf "%-4s %-20s %-60s %-60s\n" "----" "--------------------" "------------------------------------------------------------" "------------------------------------------------------------"

sqlite3 -separator '|' "$DB_PATH" \
  "SELECT storyboard_number, title, image_url, video_url FROM storyboards WHERE episode_id=$EPISODE_ID ORDER BY storyboard_number;" \
| while IFS='|' read -r num title img vid; do
  # 截断过长的 URL 以便显示
  img_short=$(echo "$img" | cut -c1-58)
  vid_short=$(echo "$vid" | cut -c1-58)
  printf "%-4s %-20s %-60s %-60s\n" "$num" "$title" "$img_short" "$vid_short"
done

# 统计
IMG_OK=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM storyboards WHERE episode_id=$EPISODE_ID AND image_url != '';")
VID_OK=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM storyboards WHERE episode_id=$EPISODE_ID AND video_url != '';")
echo ""
ok "image_url 已填充: $IMG_OK/$SB_COUNT"
ok "video_url 已填充: $VID_OK/$SB_COUNT"

if [ "$VID_OK" -eq 0 ]; then
  warn "没有可用的视频 URL，跳过视频合成步骤"
  echo ""
  echo "============================================================"
  info "测试完成（部分）：AIGC 生成了图片但无视频，跳过合成"
  echo "============================================================"
  exit 0
fi

# ============================================================
# Step 5: 视频合成预检 + 合成
# ============================================================
echo ""
echo "============================================================"
info "Step 5: 视频合成预检 + 合成"
echo "============================================================"

# 构建 clips 数组
CLIPS_JSON=$(sqlite3 -separator '|' "$DB_PATH" \
  "SELECT video_url, duration FROM storyboards WHERE episode_id=$EPISODE_ID AND video_url != '' ORDER BY storyboard_number;" \
| jq -R -s '
  split("\n") | map(select(length > 0)) | to_entries | map(
    (.value | split("|")) as $parts |
    {
      video_url: $parts[0],
      duration: ($parts[1] | tonumber),
      start_time: 0,
      end_time: 0
    }
  )
')

MERGE_PAYLOAD=$(jq -n --argjson clips "$CLIPS_JSON" '{clips: $clips, output_file: "outputs/merged_storyboard.mp4"}')

# 5a: 预检
info "5a: 执行视频合成预检..."
PRECHECK_RESP=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/videos/merge/precheck" \
  -H "Content-Type: application/json" \
  -d "$MERGE_PAYLOAD")

HTTP_CODE=$(echo "$PRECHECK_RESP" | tail -1)
BODY=$(echo "$PRECHECK_RESP" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
  warn "预检失败 (HTTP $HTTP_CODE): $BODY"
  warn "继续尝试合成..."
else
  CLIPS_CNT=$(echo "$BODY" | jq -r '.clips_count')
  EST_DUR=$(echo "$BODY" | jq -r '.estimated_output_duration')
  WARNINGS=$(echo "$BODY" | jq -r '.warnings | length')
  ok "预检通过 — 片段数: $CLIPS_CNT, 预估时长: ${EST_DUR}s, 警告: $WARNINGS"

  if [ "$WARNINGS" -gt 0 ]; then
    echo "$BODY" | jq -r '.warnings[]' | while read -r w; do
      warn "  $w"
    done
  fi
fi

# 5b: 触发合成
info "5b: 触发视频合成任务..."
MERGE_RESP=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/videos/merge" \
  -H "Content-Type: application/json" \
  -d "$MERGE_PAYLOAD")

HTTP_CODE=$(echo "$MERGE_RESP" | tail -1)
BODY=$(echo "$MERGE_RESP" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
  fail "触发视频合成失败 (HTTP $HTTP_CODE): $BODY"
  exit 1
fi

MERGE_TASK_ID=$(echo "$BODY" | jq -r '.task_id')
info "视频合成任务 Task ID: $MERGE_TASK_ID"

# 轮询合成任务
info "轮询视频合成任务状态（每 10 秒）..."
while true; do
  STATUS_RESP=$(curl -s "${API_BASE}/tasks/${MERGE_TASK_ID}")
  STATUS=$(echo "$STATUS_RESP" | jq -r '.status')
  PROGRESS=$(echo "$STATUS_RESP" | jq -r '.progress')
  MESSAGE=$(echo "$STATUS_RESP" | jq -r '.message')

  echo -e "  [$(date +%H:%M:%S)] status=${CYAN}${STATUS}${NC} progress=${PROGRESS}% message=${MESSAGE}"

  if [ "$STATUS" = "completed" ]; then
    ok "视频合成完成"
    RESULT=$(echo "$STATUS_RESP" | jq -r '.result')
    if [ "$RESULT" != "" ] && [ "$RESULT" != "null" ]; then
      echo "  输出: $RESULT"
    fi
    break
  fi
  if [ "$STATUS" = "failed" ]; then
    fail "视频合成失败"
    echo "$STATUS_RESP" | jq '.'
    exit 1
  fi
  sleep 10
done

# ============================================================
# 完成
# ============================================================
echo ""
echo "============================================================"
ok "全流程测试完成！"
echo "============================================================"
echo ""
echo "Episode ID:       $EPISODE_ID"
echo "分镜数量:          $SB_COUNT"
echo "总时长:            ${TOTAL_DUR}s"
echo "图片填充:          $IMG_OK/$SB_COUNT"
echo "视频填充:          $VID_OK/$SB_COUNT"
echo "合成输出:          outputs/merged_storyboard.mp4"
echo ""
