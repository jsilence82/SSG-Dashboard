#!/bin/bash
cd "$(dirname "$0")"

# Stop any existing instance (from .app launcher or a previous run)
launchctl remove "com.ssg.ticket-dashboard" 2>/dev/null
pid=$(lsof -ti :8501 2>/dev/null)
[ -n "$pid" ] && kill "$pid" 2>/dev/null && sleep 1

exec .venv/bin/python3 -m streamlit run app.py "$@"
