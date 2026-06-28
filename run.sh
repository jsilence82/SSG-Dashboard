#!/bin/bash
cd "$(dirname "$0")"

PORT=8501
LOG=/tmp/ssg_streamlit_debug.log

# Stop any launchd-managed instance or previous terminal run
launchctl remove "com.ssg.ticket-dashboard" 2>/dev/null
pid=$(lsof -ti :$PORT 2>/dev/null)
[ -n "$pid" ] && kill "$pid" 2>/dev/null && sleep 1

# Run Streamlit with full debug logging captured to file AND shown in terminal
.venv/bin/python3 -m streamlit run app.py \
    --server.port $PORT \
    --server.headless true \
    --browser.gatherUsageStats false \
    --logger.level debug 2>&1 | tee "$LOG" &
ST_PID=$!

# Wait for server, then open a fresh tab
for _ in $(seq 1 30); do
    sleep 0.5
    if lsof -Pi ":$PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
        open "http://localhost:$PORT"
        break
    fi
done

wait $ST_PID
echo "--- Streamlit exited. Full log: $LOG ---"
