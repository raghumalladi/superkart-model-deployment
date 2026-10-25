---
title: SuperKart Sales Forecaster
emoji: 🛒
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8501
pinned: false
---

# SuperKart Sales Forecaster (Streamlit frontend)

Simple UI for single and batch (CSV) sales predictions. It calls the decoupled Flask
backend whose base URL is read from the `BACKEND_URL` environment / Space variable.
