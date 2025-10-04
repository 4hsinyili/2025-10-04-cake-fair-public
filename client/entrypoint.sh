#!/bin/bash
echo "Build streamlit config"
uv run config.py
cat ./.streamlit/config.toml
echo "Streamlit server starting"
/app/client/.venv/bin/streamlit run app/main.py
echo "Streamlit server stopped"
