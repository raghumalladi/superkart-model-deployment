---
title: SuperKart Sales Forecasting API
emoji: 🛒
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# SuperKart Sales Forecasting API (Flask backend)

Serves a tuned scikit-learn / XGBoost pipeline that predicts `Product_Store_Sales_Total`
for a product in a given SuperKart outlet.

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/` | – | health + expected feature list |
| POST | `/v1/predict` | JSON object with the 10 features | `{"Sales": 2842.4}` |
| POST | `/v1/predictbatch` | multipart `file` = CSV with the 10 feature columns | `{"0": 2842.4, "1": ...}` |

Expected features: `Product_Weight, Product_Sugar_Content, Product_Allocated_Area, Product_MRP,
Store_Size, Store_Location_City_Type, Store_Type, Product_Id_char, Store_Age_Years, Product_Type_Category`.
