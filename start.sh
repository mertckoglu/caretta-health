#!/usr/bin/env bash
# Caretta starter for macOS / Linux: ./start.sh
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
if [ ! -x .venv/bin/python ]; then
  echo "First start: setting things up..."
  "$PY" -m venv .venv
fi
if ! cmp -s requirements.txt .venv/.requirements-installed; then
  echo "Installing packages..."
  .venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt
  cp requirements.txt .venv/.requirements-installed
fi
if curl -fs http://localhost:8501/_stcore/health >/dev/null 2>&1; then
  echo "Caretta is already running."
  (command -v open >/dev/null && open http://localhost:8501) || xdg-open http://localhost:8501 || true
  exit 0
fi
exec .venv/bin/python -m streamlit run app/ui/Home.py --server.port 8501 --server.headless false
