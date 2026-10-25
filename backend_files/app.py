"""
SuperKart Sales Forecasting - Flask backend API.

Loads the serialized scikit-learn Pipeline (preprocessing + tuned regressor)
and exposes two prediction endpoints:

    POST /v1/predict        - online inference, one JSON record  -> {"Sales": <float>}
    POST /v1/predictbatch   - batch inference, multipart CSV file -> {"<row_index>": <float>, ...}
    GET  /                  - health check

Both prediction responses may carry an extra "warnings" list when a categorical
value was not seen during training (it is then encoded as "unknown" and the
prediction relies on the remaining features).

The pipeline was trained on these 10 engineered features:
    Product_Weight, Product_Sugar_Content, Product_Allocated_Area, Product_MRP,
    Store_Size, Store_Location_City_Type, Store_Type,
    Product_Id_char, Store_Age_Years, Product_Type_Category
"""

import io
import logging
import os

import joblib
import pandas as pd
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("superkart_api")

# ---------------------------------------------------------------------------
# Model loading (once, at import time, so every worker reuses the same object)
# ---------------------------------------------------------------------------
MODEL_PATH = os.environ.get("MODEL_PATH", "superkart_model.joblib")
model = joblib.load(MODEL_PATH)
log.info("Loaded model from %s", MODEL_PATH)

# ---------------------------------------------------------------------------
# Feature contract - must stay identical to the training notebook
# ---------------------------------------------------------------------------
NUMERIC_FEATURES = ["Product_Weight", "Product_Allocated_Area", "Product_MRP", "Store_Age_Years"]
CATEGORICAL_FEATURES = [
    "Product_Sugar_Content",
    "Store_Size",
    "Store_Location_City_Type",
    "Store_Type",
    "Product_Id_char",
    "Product_Type_Category",
]
FEATURES = [
    "Product_Weight",
    "Product_Sugar_Content",
    "Product_Allocated_Area",
    "Product_MRP",
    "Store_Size",
    "Store_Location_City_Type",
    "Store_Type",
    "Product_Id_char",
    "Store_Age_Years",
    "Product_Type_Category",
]

REFERENCE_YEAR = 2025  # same constant used to derive Store_Age_Years during training

SUGAR_MAP = {
    "low sugar": "Low Sugar",
    "regular": "Regular",
    "reg": "Regular",  # dirty label present in the raw data
    "no sugar": "No Sugar",
}

PERISHABLES = {"Fruits and Vegetables", "Dairy", "Meat", "Seafood", "Breads", "Breakfast"}
_PERISHABLES_LOWER = {p.lower() for p in PERISHABLES}

NULL_TOKENS = {"", "nan", "none", "null", "na", "n/a"}


def _training_categories(pipeline):
    """Labels the one-hot encoder saw during training, per categorical column."""
    ct = pipeline.named_steps["preprocessor"]
    for _, transformer, columns in ct.transformers_:
        if hasattr(transformer, "categories_"):
            return {col: [str(v) for v in cats] for col, cats in zip(columns, transformer.categories_)}
    return {}


KNOWN_CATEGORIES = _training_categories(model)
# lower-cased label -> canonical training label, used for case-insensitive matching
CANONICAL = {col: {v.lower(): v for v in vals} for col, vals in KNOWN_CATEGORIES.items()}
log.info("Known categories: %s", {k: len(v) for k, v in KNOWN_CATEGORIES.items()})


def clean_input(df: pd.DataFrame):
    """
    Normalise an incoming DataFrame into the exact feature frame the model expects.

    - Tolerates the *raw* schema too: derives Product_Id_char, Store_Age_Years and
      Product_Type_Category from Product_Id, Store_Establishment_Year and Product_Type
      when the engineered columns are absent.
    - Harmonises labels case-insensitively (e.g. 'reg' -> 'Regular', 'tier 2' -> 'Tier 2').
    - Rejects missing values (numeric or categorical) with a ValueError -> HTTP 400.
    - Returns (clean_df, warnings) where warnings lists categorical values that were
      never seen in training; such values are encoded as all-zeros by the pipeline.
    """
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # ---- derive engineered features from raw columns if needed -------------
    if "Product_Id_char" not in df.columns and "Product_Id" in df.columns:
        df["Product_Id_char"] = df["Product_Id"].astype(str).str[:2].str.upper()
    if "Store_Age_Years" not in df.columns and "Store_Establishment_Year" in df.columns:
        df["Store_Age_Years"] = REFERENCE_YEAR - pd.to_numeric(df["Store_Establishment_Year"], errors="coerce")
    if "Product_Type_Category" not in df.columns and "Product_Type" in df.columns:
        is_perishable = df["Product_Type"].astype(str).str.strip().str.lower().isin(_PERISHABLES_LOWER)
        df["Product_Type_Category"] = is_perishable.map({True: "Perishables", False: "Non Perishables"})

    # ---- validate presence of every feature --------------------------------
    missing = [c for c in FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required feature(s): {missing}. Expected columns: {FEATURES}")

    df = df[FEATURES]
    warnings = []

    # ---- categoricals: nulls -> 400, case-insensitive match, unseen -> warning
    for col in CATEGORICAL_FEATURES:
        values = df[col].astype(str).str.strip()
        is_null = df[col].isnull() | values.str.lower().isin(NULL_TOKENS)
        if is_null.any():
            raise ValueError(f"Missing value in '{col}' for row(s): {df.index[is_null].tolist()}")
        if col == "Product_Sugar_Content":
            values = values.str.lower().map(SUGAR_MAP).fillna(values)
        if col == "Product_Id_char":
            values = values.str.upper()
        canonical = CANONICAL.get(col)
        if canonical:
            values = values.map(lambda v: canonical.get(v.lower(), v))
            unseen = sorted(set(values[~values.isin(list(canonical.values()))]))
            if unseen:
                warnings.append(
                    f"{col}: value(s) {unseen} were not seen in training and are treated as unknown; "
                    f"known values: {KNOWN_CATEGORIES[col]}"
                )
        df[col] = values

    # ---- numerics: coerce, nulls -> 400 ------------------------------------
    for col in NUMERIC_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    bad = df[NUMERIC_FEATURES].isnull().any(axis=1)
    if bad.any():
        raise ValueError(
            f"Non-numeric or missing value in {NUMERIC_FEATURES} for row(s): {df.index[bad].tolist()}"
        )
    return df, warnings


# ---------------------------------------------------------------------------
# Flask app - the instance name must match the Dockerfile CMD (app:superkart_api)
# ---------------------------------------------------------------------------
superkart_api = Flask("SuperKart Sales Forecaster")


@superkart_api.get("/")
def home():
    return jsonify(
        {
            "service": "SuperKart Sales Forecasting API",
            "status": "ok",
            "endpoints": {"online": "POST /v1/predict", "batch": "POST /v1/predictbatch"},
            "expected_features": FEATURES,
            "known_categories": KNOWN_CATEGORIES,
        }
    )


@superkart_api.post("/v1/predict")
def predict():
    """Online inference: JSON body with one record -> predicted Product_Store_Sales_Total."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object with the feature values."}), 400
    try:
        X, warnings = clean_input(pd.DataFrame([payload]))
        prediction = float(model.predict(X)[0])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        log.exception("Prediction failed")
        return jsonify({"error": f"Prediction failed: {exc}"}), 500
    log.info("online prediction=%.2f warnings=%d", prediction, len(warnings))
    body = {"Sales": round(prediction, 2)}
    if warnings:
        body["warnings"] = warnings
    return jsonify(body)


@superkart_api.post("/v1/predictbatch")
def predict_batch():
    """Batch inference: multipart form field 'file' holding a CSV -> {row_index: prediction}."""
    if "file" not in request.files:
        return jsonify({"error": "Upload a CSV file in the multipart form field named 'file'."}), 400
    try:
        raw = request.files["file"].read()
        df = pd.read_csv(io.BytesIO(raw))
        if df.empty:
            return jsonify({"error": "Uploaded CSV has no rows."}), 400
        X, warnings = clean_input(df)
        preds = model.predict(X)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        log.exception("Batch prediction failed")
        return jsonify({"error": f"Batch prediction failed: {exc}"}), 500
    log.info("batch prediction rows=%d warnings=%d", len(preds), len(warnings))
    body = {str(i): round(float(p), 2) for i, p in enumerate(preds)}
    if warnings:
        body["warnings"] = warnings
    return jsonify(body)


if __name__ == "__main__":
    # Local debugging only; the container runs under gunicorn (see Dockerfile).
    superkart_api.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)), debug=False)
