# SuperKart Sales Forecasting API (Flask backend)

Serves the tuned scikit-learn / XGBoost pipeline (`superkart_model.joblib`) that predicts
`Product_Store_Sales_Total` for a product in a given SuperKart outlet. Runs as a Docker container
on port **7860** (gunicorn, 2 workers).

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/` | - | health, expected feature list and the category labels seen in training |
| POST | `/v1/predict` | JSON object with the 10 features | `{"Sales": 2879.9}` |
| POST | `/v1/predictbatch` | multipart field `file` = CSV with the 10 feature columns | `{"0": 1723.01, "1": ...}` |

Expected features: `Product_Weight, Product_Sugar_Content, Product_Allocated_Area, Product_MRP,
Store_Size, Store_Location_City_Type, Store_Type, Product_Id_char, Store_Age_Years, Product_Type_Category`.
Raw columns (`Product_Id`, `Product_Type`, `Store_Establishment_Year`) are also accepted; the API derives
the engineered features. Bad input returns HTTP 400 with an `error` message; unseen category labels are
reported in a `warnings` list.

## Build and run

```bash
docker build -t superkart-backend .
docker run -d --name superkart-backend --network superkart-net --network-alias backend -p 7860:7860 superkart-backend
curl http://localhost:7860/
```
