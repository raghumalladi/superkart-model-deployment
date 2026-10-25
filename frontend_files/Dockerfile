# SuperKart Streamlit frontend - talks to the Flask backend via BACKEND_URL
FROM python:3.13-slim

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR $HOME/app

# Optional BuildKit secret "pip_ca": trusts a corporate proxy CA during local builds only
# (docker build --secret id=pip_ca,src=ca.pem ...). Absent on Hugging Face.
COPY --chown=user requirements.txt .
RUN --mount=type=secret,id=pip_ca,uid=1000,mode=0400 \
    if [ -f /run/secrets/pip_ca ]; then export PIP_CERT=/run/secrets/pip_ca; fi && \
    pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .

EXPOSE 8501

# XSRF protection is disabled so the file uploader works behind the Hugging Face reverse proxy
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true", "--server.enableXsrfProtection=false"]
