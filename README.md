# SuperKart Sales Forecasting – containerized deployment

Decoupled deployment of a tuned XGBoost sales-forecasting pipeline:

| Folder | What | Port |
|---|---|---|
| `backend_files/` | Flask REST API (`POST /v1/predict`, `POST /v1/predictbatch`) + serialized model + Dockerfile | 7860 |
| `frontend_files/` | Streamlit UI (single and batch prediction) + Dockerfile | 8501 |

The frontend finds the backend through the `BACKEND_URL` environment variable
(`http://backend:7860` on the shared Docker network), so no URL is hard-coded.

## Run in GitHub Codespaces

1. **Code → Codespaces → Create codespace on main** (2-core machine is enough).
2. In the terminal:
   ```bash
   bash run.sh
   ```
   This builds both images, creates the `superkart-net` network and starts both containers.
3. In the **PORTS** tab set ports **7860** and **8501** to **Public** (the script tries to do this for you).
4. Open the forwarded URL of port 8501 for the UI, and port 7860 for the API
   (`https://<codespace-name>-7860.app.github.dev/`).

`bash run.sh logs` shows the container logs, `bash run.sh down` stops everything.
`docker compose up --build -d` is an equivalent alternative.

## API

```bash
curl -X POST https://<codespace-name>-7860.app.github.dev/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"Product_Weight":12.66,"Product_Sugar_Content":"Low Sugar","Product_Allocated_Area":0.027,"Product_MRP":117.08,"Store_Size":"Medium","Store_Location_City_Type":"Tier 2","Store_Type":"Supermarket Type2","Product_Id_char":"FD","Store_Age_Years":16,"Product_Type_Category":"Non Perishables"}'
```

Response: `{"Sales": 2879.9}`. Batch: `POST /v1/predictbatch` with a multipart field `file`
holding a CSV with the ten feature columns; response `{"0": ..., "1": ...}`.
