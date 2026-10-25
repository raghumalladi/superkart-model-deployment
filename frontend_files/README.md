# SuperKart Sales Forecaster (Streamlit frontend)

Interactive UI for single and batch (CSV) sales predictions. It collects the raw product and store
attributes, derives the engineered features exactly as in training, and calls the decoupled Flask
backend. The backend address comes from the `BACKEND_URL` environment variable (`http://backend:7860`
on the shared Docker network) - nothing is hard-coded. Runs on port **8501**.

## Build and run

```bash
docker build -t superkart-frontend .
docker run -d --name superkart-frontend --network superkart-net -p 8501:8501 -e BACKEND_URL=http://backend:7860 superkart-frontend
```
