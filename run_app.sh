#!/usr/bin/env bash
# Run Phase 2 backend (serves both API and frontend), then open the chat UI in the browser.
# From project root. Ensure deps are installed: pip install -r requirements.txt

set -e
cd "$(dirname "$0")"

# If port 8000 is in use, free it so restart works (e.g. after running ./run_app.sh again)
if command -v lsof >/dev/null 2>&1; then
  OLD_PID=$(lsof -ti :8000 2>/dev/null || true)
  if [ -n "$OLD_PID" ]; then
    echo "Stopping existing server on port 8000 (PID $OLD_PID)..."
    kill -9 $OLD_PID 2>/dev/null || true
    sleep 2
  fi
fi

if [ -x ".venv/bin/python" ] && .venv/bin/python -c "import uvicorn" 2>/dev/null; then
  PYTHON=.venv/bin/python
else
  PYTHON=python3
fi

echo "Starting server at http://localhost:8000/ ..."
$PYTHON -m uvicorn phase2.app:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

# Wait for server to bind, then open the frontend in the default browser (first start may take 30s)
sleep 6
if command -v open >/dev/null 2>&1; then
  open "http://localhost:8000/"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:8000/"
elif command -v start >/dev/null 2>&1; then
  start "http://localhost:8000/"
else
  echo "Open in your browser: http://localhost:8000/"
fi

echo "Chat UI should open in your browser. Press Ctrl+C to stop the server."
wait $UVICORN_PID
