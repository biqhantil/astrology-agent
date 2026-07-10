#!/usr/bin/env bash
# Launch ONE multi-turn scenario in the ASTROLOGY-SERVICES tmux window.
#
# Usage:
#   ./tests/harness/run_one_tmux.sh u1
#   ./tests/harness/run_one_tmux.sh u1_quick_daily 1
#   SCENARIO=u4 PANE=0:2.5 ./tests/harness/run_one_tmux.sh
#
# Writes:
#   harness_iterations/single/<scenario>_i<N>.log
#   harness_iterations/single/<scenario>_i<N>.jsonl
#   harness_iterations/single/<scenario>_i<N>.status   (RUNNING|PASS|FAIL)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

SCENARIO="${1:-${SCENARIO:-u1}}"
ITERATION="${2:-${ITERATION:-1}}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8012}"
# Default: ASTROLOGY-SERVICES window, bottom-right bash pane
TMUX_TARGET="${TMUX_TARGET:-0:2.5}"
TIMEOUT="${TIMEOUT:-180}"
VERBOSE="${VERBOSE:-0}"  # set VERBOSE=1 for httpx DEBUG

mkdir -p harness_iterations/single
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
# collapse runs of non-alnum to single underscore; trim edges
SAFE="$(echo "$SCENARIO" | tr -c 'A-Za-z0-9._-' '_' | sed 's/__*/_/g; s/^_//; s/_$//')"
LOG="harness_iterations/single/${SAFE}_i${ITERATION}_${STAMP}.log"
JSONL="harness_iterations/single/${SAFE}_i${ITERATION}_${STAMP}.jsonl"
STATUS="harness_iterations/single/${SAFE}_i${ITERATION}_${STAMP}.status"
LATEST_LINK="harness_iterations/single/LATEST"

# Resolve absolute paths for status file written from tmux shell
ABS_LOG="$ROOT/$LOG"
ABS_JSONL="$ROOT/$JSONL"
ABS_STATUS="$ROOT/$STATUS"

echo "RUNNING" > "$ABS_STATUS"
ln -sfn "$(basename "$ABS_LOG")" "${LATEST_LINK}.log"
ln -sfn "$(basename "$ABS_JSONL")" "${LATEST_LINK}.jsonl"
ln -sfn "$(basename "$ABS_STATUS")" "${LATEST_LINK}.status"
# Also write a pointer file with absolute paths
cat > "${LATEST_LINK}.paths" <<EOF
scenario=$SCENARIO
iteration=$ITERATION
log=$ABS_LOG
jsonl=$ABS_JSONL
status=$ABS_STATUS
tmux=$TMUX_TARGET
started=$STAMP
EOF

echo "→ scenario=$SCENARIO iter=$ITERATION tmux=$TMUX_TARGET"
echo "  log=$ABS_LOG"
echo "  jsonl=$ABS_JSONL"
echo "  status=$ABS_STATUS"

# Ensure target pane exists
if ! tmux list-panes -t "$TMUX_TARGET" &>/dev/null; then
  echo "ERROR: tmux target $TMUX_TARGET not found" >&2
  echo "FAIL" > "$ABS_STATUS"
  exit 1
fi

# Stop anything lingering in the pane, then run the harness
tmux send-keys -t "$TMUX_TARGET" C-c Enter 2>/dev/null || true
sleep 0.3

# Single quoted remote script; expand vars we need
VFLAG=""
if [ "$VERBOSE" = "1" ]; then VFLAG="-v"; fi

REMOTE=$(cat <<EOF
cd '$ROOT' && \
echo RUNNING > '$ABS_STATUS' && \
.venv/bin/python -m tests.harness.multi_turn_runner \
  --base-url '$BASE_URL' \
  --scenario '$SCENARIO' \
  --timeout $TIMEOUT \
  --pause 0.3 \
  --iteration $ITERATION \
  --results '$ABS_JSONL' \
  --skip-preflight \
  $VFLAG \
  2>&1 | tee '$ABS_LOG' ; \
ec=\${PIPESTATUS[0]} ; \
if [ \$ec -eq 0 ]; then echo PASS > '$ABS_STATUS'; else echo FAIL > '$ABS_STATUS'; fi ; \
echo "EXIT \$ec  status=\$(cat '$ABS_STATUS')" ; \
if [ -f '${ABS_JSONL%.jsonl}.summary.json' ]; then echo "SUMMARY ${ABS_JSONL%.jsonl}.summary.json"; fi
EOF
)

tmux send-keys -t "$TMUX_TARGET" "$REMOTE" Enter

echo "Launched in tmux $TMUX_TARGET"
echo "Poll: cat $ABS_STATUS"
echo "Tail:  tail -f $ABS_LOG"
