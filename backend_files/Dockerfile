# SuperKart Flask backend - serves the serialized sklearn/XGBoost pipeline on port 7860
FROM python:3.13-slim

# Run as a non-root user (uid 1000), as hosted container platforms expect.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR $HOME/app

# Install dependencies first so Docker layer caching skips reinstalling on code changes.
# The optional BuildKit secret "pip_ca" lets the image build behind a TLS-inspecting corporate
# proxy by trusting that proxy's CA bundle (docker build --secret id=pip_ca,src=ca.pem ...).
# It is not provided on Hugging Face, where the mount is simply absent and pip uses its defaults.
COPY --chown=user requirements.txt .
RUN --mount=type=secret,id=pip_ca,uid=1000,mode=0400 \
    if [ -f /run/secrets/pip_ca ]; then export PIP_CERT=/run/secrets/pip_ca; fi && \
    pip install --no-cache-dir --user -r requirements.txt

# Copy the API code and the serialized model
COPY --chown=user . .

EXPOSE 7860

# "app" = app.py module, "superkart_api" = the Flask instance inside it
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:7860", "--timeout", "120", "app:superkart_api"]
