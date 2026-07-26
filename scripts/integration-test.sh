#!/usr/bin/env bash
set -euo pipefail

API="${API:-http://localhost:8000}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLIP="$REPO_DIR/sample-data/pilot_clip.mp4"

if ! command -v curl >/dev/null || ! command -v python3 >/dev/null; then
  echo "curl and python3 are required" >&2
  exit 1
fi

if [ ! -f "$CLIP" ]; then
  echo "Pilot clip not found. Run scripts/test-media/generate_pilot_clip.sh first." >&2
  exit 1
fi

printf '\nHealth check...\n'
curl -fs "$API/health" | python3 -m json.tool

printf '\nCreating project...\n'
PROJECT=$(curl -fs -X POST "$API/projects" -H 'Content-Type: application/json' -d '{"name":"Integration Test","client_name":"CI","preset":"instagram_reel"}')
PROJECT_ID=$(echo "$PROJECT" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
echo "PROJECT_ID=$PROJECT_ID"

printf '\nUploading pilot clip...\n'
ASSET=$(curl -fs -X POST "$API/projects/$PROJECT_ID/assets" -F 'file=@"'"$CLIP"'"' -F 'asset_type=video')
ASSET_ID=$(echo "$ASSET" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
echo "ASSET_ID=$ASSET_ID"

printf '\nAnalyzing...\n'
ANALYZE=$(curl -fs -X POST "$API/projects/$PROJECT_ID/analyze")
echo "$ANALYZE" | python3 -m json.tool | head -n 10

printf '\nAnalysis results...\n'
ANALYSIS=$(curl -fs "$API/projects/$PROJECT_ID/analysis")
SCENES=$(echo "$ANALYSIS" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(len(d[0]["scenes"]))')
TRANSCRIPT=$(echo "$ANALYSIS" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d[0]["transcript"].get("text",""))')
echo "Scenes: $SCENES"
echo "Transcript: $TRANSCRIPT"

if [ "$SCENES" -lt 1 ]; then
  echo "FAIL: no scenes detected" >&2
  exit 1
fi

printf '\nGenerating edit plan...\n'
PLAN=$(curl -fs -X POST "$API/projects/$PROJECT_ID/plan" -H 'Content-Type: application/json' -d '{"target_seconds":4}')
echo "$PLAN" | python3 -m json.tool | head -n 30
CONFIDENCE=$(echo "$PLAN" | python3 -c 'import sys,json; print(json.load(sys.stdin)["confidence"])')
PLAN_ID=$(echo "$PLAN" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
echo "Confidence: $CONFIDENCE"
echo "Plan ID: $PLAN_ID"

if [ "$CONFIDENCE" = "0" ] || [ -z "$CONFIDENCE" ]; then
  echo "FAIL: plan confidence is zero" >&2
  exit 1
fi

printf '\nApproving edit plan...\n'
curl -fs -X POST "$API/plans/$PLAN_ID/approve" | python3 -m json.tool | head -n 10

printf '\nRendering final (queued)...\n'
JOB=$(curl -fs -X POST "$API/projects/$PROJECT_ID/render" -H 'Content-Type: application/json' -d "{\"plan_id\":\"$PLAN_ID\",\"output_name\":\"final\",\"preview\":false}")
JOB_ID=$(echo "$JOB" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
echo "Job ID: $JOB_ID"
echo "$JOB" | python3 -m json.tool | head -n 20

printf '\nWaiting for job to complete...\n'
for i in {1..60}; do
  STATUS_JSON=$(curl -fs "$API/jobs/$JOB_ID")
  STATUS=$(echo "$STATUS_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])')
  PROGRESS=$(echo "$STATUS_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["progress"])')
  echo "  status=$STATUS progress=$PROGRESS"
  if [ "$STATUS" = "COMPLETED" ] || [ "$STATUS" = "COMPLETED_WITH_WARNINGS" ]; then
    FINAL="$STATUS_JSON"
    break
  fi
  if [ "$STATUS" = "FAILED" ]; then
    echo "FAIL: render job failed" >&2
    echo "$STATUS_JSON" | python3 -m json.tool >&2
    exit 1
  fi
  sleep 2
done

if [ -z "${FINAL:-}" ]; then
  echo "FAIL: render job did not complete in time" >&2
  exit 1
fi

echo "$FINAL" | python3 -m json.tool | head -n 40
OK=$(echo "$FINAL" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(all(o["qa"]["ok"] for o in d["outputs"]))')
if [ "$OK" != "True" ]; then
  echo "FAIL: final QA did not pass" >&2
  exit 1
fi

printf '\nPackaging...\n'
curl -fs -X POST "$API/projects/$PROJECT_ID/package" | python3 -m json.tool

printf '\nDelivering...\n'
curl -fs -X POST "$API/projects/$PROJECT_ID/deliver" | python3 -m json.tool

printf '\nNotifications...\n'
curl -fs "$API/projects/$PROJECT_ID/notifications" | python3 -m json.tool

printf '\nPASS: end-to-end integration test complete.\n'
