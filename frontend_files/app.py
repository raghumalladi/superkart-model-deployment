"""
SuperKart Sales Forecasting - Streamlit frontend.

A thin UI that collects product/store attributes and calls the decoupled Flask
backend for predictions (online and batch). The backend address comes from the
BACKEND_URL environment variable so the same image works locally (docker network),
in GitHub Codespaces and on Hugging Face Spaces.
"""

import os

import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_BACKEND = "https://raghuvaran116-superkart-backend.hf.space"
BACKEND_URL = os.environ.get("BACKEND_URL", DEFAULT_BACKEND).rstrip("/")
PREDICT_URL = f"{BACKEND_URL}/v1/predict"
BATCH_URL = f"{BACKEND_URL}/v1/predictbatch"
TIMEOUT = 60  # seconds - hosted backends can be slow to wake up

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

st.set_page_config(page_title="SuperKart Sales Forecaster", page_icon="🛒", layout="centered")
st.title("🛒 SuperKart Sales Forecaster")
st.write(
    "Predict the **quarterly sales revenue** (`Product_Store_Sales_Total`) of a product in a "
    "SuperKart outlet. The UI sends your inputs to a separately deployed Flask API that hosts "
    "the trained model."
)


def show_json_or_text(resp):
    """Render a response body as JSON when possible, otherwise as text (e.g. a proxy's HTML error page)."""
    try:
        st.json(resp.json())
    except ValueError:
        st.code(resp.text[:500] or "<empty body>", language=None)


def show_warnings(body):
    """Surface the backend's 'warnings' list (unseen categorical values), if any."""
    if isinstance(body, dict):
        for w in body.get("warnings", []):
            st.warning(w)


with st.sidebar:
    st.header("Backend")
    st.code(BACKEND_URL, language=None)
    if st.button("Check backend health"):
        try:
            r = requests.get(BACKEND_URL + "/", timeout=TIMEOUT)
            if r.ok:
                st.success(f"HTTP {r.status_code}")
            else:
                st.error(f"HTTP {r.status_code} - the backend is not ready (it may be starting up or asleep)")
            show_json_or_text(r)
        except requests.exceptions.RequestException as exc:
            st.error(f"Backend unreachable: {exc}")

tab_single, tab_batch = st.tabs(["Single prediction", "Batch prediction (CSV)"])

# ---------------------------------------------------------------------------
# Tab 1 - online inference
# ---------------------------------------------------------------------------
with tab_single:
    st.subheader("Product attributes")
    c1, c2 = st.columns(2)
    with c1:
        product_weight = st.number_input("Product weight", min_value=1.0, max_value=50.0, value=12.66, step=0.01)
        product_mrp = st.number_input("Product MRP", min_value=1.0, max_value=500.0, value=117.08, step=0.01)
        product_id_char = st.selectbox(
            "Product category code (first 2 letters of Product_Id)",
            ["FD", "DR", "NC"],
            help="FD = Food, DR = Drinks, NC = Non-Consumable",
        )
    with c2:
        product_allocated_area = st.number_input(
            "Product allocated area (share of store display)",
            min_value=0.0,
            max_value=1.0,
            value=0.027,
            step=0.001,
            format="%.3f",
        )
        sugar_content = st.selectbox("Product sugar content", ["Low Sugar", "Regular", "No Sugar"])
        product_type_category = st.selectbox("Product type category", ["Perishables", "Non Perishables"])

    st.subheader("Store attributes")
    c3, c4 = st.columns(2)
    with c3:
        store_size = st.selectbox("Store size", ["Small", "Medium", "High"], index=1)
        store_type = st.selectbox(
            "Store type",
            ["Supermarket Type1", "Supermarket Type2", "Departmental Store", "Food Mart"],
            index=1,
        )
    with c4:
        city_type = st.selectbox("Store location city type", ["Tier 1", "Tier 2", "Tier 3"], index=1)
        store_age = st.number_input("Store age (years)", min_value=0, max_value=100, value=16, step=1)

    payload = {
        "Product_Weight": product_weight,
        "Product_Sugar_Content": sugar_content,
        "Product_Allocated_Area": product_allocated_area,
        "Product_MRP": product_mrp,
        "Store_Size": store_size,
        "Store_Location_City_Type": city_type,
        "Store_Type": store_type,
        "Product_Id_char": product_id_char,
        "Store_Age_Years": int(store_age),
        "Product_Type_Category": product_type_category,
    }

    with st.expander("Request payload sent to the API"):
        st.json(payload)

    if st.button("Predict sales", type="primary"):
        with st.spinner("Calling the prediction API..."):
            try:
                resp = requests.post(PREDICT_URL, json=payload, timeout=TIMEOUT)
                if resp.status_code == 200:
                    body = resp.json()
                    st.success(f"Predicted quarterly sales revenue: **{body['Sales']:,.2f}**")
                    st.caption(f"POST {PREDICT_URL} -> HTTP {resp.status_code}")
                    show_warnings(body)
                else:
                    st.error(f"API returned HTTP {resp.status_code}")
                    show_json_or_text(resp)
            except requests.exceptions.RequestException as exc:
                st.error(f"Could not reach the backend at {PREDICT_URL}: {exc}")

# ---------------------------------------------------------------------------
# Tab 2 - batch inference
# ---------------------------------------------------------------------------
with tab_batch:
    st.write("Upload a CSV containing the following columns (one row per product/store):")
    st.code(", ".join(FEATURES), language=None)

    template_csv = pd.DataFrame([payload]).to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV template", template_csv, "superkart_batch_template.csv", "text/csv")

    uploaded = st.file_uploader("Choose a CSV file", type=["csv"])
    batch_df = None
    if uploaded is not None:
        # A new file invalidates results kept from a previous one
        source = (uploaded.name, uploaded.size)
        if st.session_state.get("batch_source") != source:
            st.session_state.pop("batch_result", None)
            st.session_state.pop("batch_warnings", None)
            st.session_state["batch_source"] = source

        try:
            batch_df = pd.read_csv(uploaded)
        except Exception as exc:  # noqa: BLE001 - pandas raises several parser/encoding error types
            st.error(f"Could not read the file as CSV: {exc}")
        if batch_df is not None and batch_df.empty:
            st.error("The uploaded CSV has no data rows.")
            batch_df = None
        if batch_df is not None:
            st.write(f"Loaded **{len(batch_df)}** rows from `{uploaded.name}`")
            st.dataframe(batch_df.head(10), width="stretch")

    if batch_df is not None and st.button("Predict for all rows", type="primary"):
        with st.spinner("Calling the batch prediction API..."):
            try:
                # Forward the user's bytes untouched; the backend does the parsing and validation
                files = {"file": (uploaded.name, uploaded.getvalue(), "text/csv")}
                resp = requests.post(BATCH_URL, files=files, timeout=TIMEOUT * 2)
                if resp.status_code == 200:
                    body = resp.json()
                    result = batch_df.copy()
                    result["Predicted_Sales"] = [body[str(i)] for i in range(len(result))]
                    st.session_state["batch_result"] = result
                    st.session_state["batch_warnings"] = body.get("warnings", [])
                    st.session_state["batch_status"] = resp.status_code
                else:
                    st.session_state.pop("batch_result", None)
                    st.error(f"API returned HTTP {resp.status_code}")
                    show_json_or_text(resp)
            except requests.exceptions.RequestException as exc:
                st.session_state.pop("batch_result", None)
                st.error(f"Could not reach the backend at {BATCH_URL}: {exc}")

    # Rendered outside the button branch so the table survives the rerun caused by the download button
    if batch_df is not None and "batch_result" in st.session_state:
        result = st.session_state["batch_result"]
        st.success(f"Received {len(result)} predictions (HTTP {st.session_state.get('batch_status', 200)})")
        for w in st.session_state.get("batch_warnings", []):
            st.warning(w)
        st.dataframe(result, width="stretch")
        st.download_button(
            "Download predictions",
            result.to_csv(index=False).encode("utf-8"),
            "superkart_predictions.csv",
            "text/csv",
        )
