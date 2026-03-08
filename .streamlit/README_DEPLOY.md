# Streamlit Cloud deployment

**Before deploying:** In **Advanced settings**, set **Python version** to **3.11** or **3.12**.

Python 3.14 is not supported (ChromaDB dependency). If you already deployed and see a Pydantic/ConfigError, delete the app and redeploy with Python 3.11 or 3.12 selected.

Add your `GROQ_API_KEY` in Secrets (TOML format) after creating the app.