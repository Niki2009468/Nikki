import streamlit as st
import requests
import statistics
import pandas as pd

# --- Page Setup ---
st.set_page_config(page_title="NDVI Analyse – NASA MODIS", layout="centered")
st.title("🌱 NDVI Analyse – NASA MODIS Subset API")

# --- Cities ---
CITIES = {
    "Darmstadt, Deutschland": (49.8728, 8.6512),
    "Tucson, USA": (32.2226, -110.9747),
    "Fortaleza, Brasilien": (-3.7319, -38.5267),
    "Malolos, Philippinen": (14.8443, 120.8114),
}

city = st.selectbox("📍 Stadt auswählen", list(CITIES.keys()))
lat, lon = CITIES[city]

PRODUCT = "MOD13Q1"
BASE = "https://modis.ornl.gov/rst/api/v1"


# --- Helper: Fetch wrapper ---
def fetch(url, params):
    try:
        res = requests.get(url, params=params, timeout=20)
        if res.status_code != 200:
            return None, f"HTTP {res.status_code}: {res.text[:200]}"
        return res.json(), None
    except Exception as e:
        return None, str(e)


# --- 1) Latest MODIS Date ---
def get_latest_modis_date(lat, lon):
    url = f"{BASE}/{PRODUCT}/dates"
    data, err = fetch(url, {"latitude": lat, "longitude": lon})
    if err:
        return None, None, err
    dates = data.get("dates")
    if not dates:
        return None, None, "Keine MODIS-Daten gefunden."
    latest = dates[-1]
    return latest["modis_date"], latest["calendar_date"], None


# --- 2) NDVI holen ---
def get_ndvi(lat, lon, modis_date):
    url = f"{BASE}/{PRODUCT}/subset"
    params = {
        "latitude": lat,
        "longitude": lon,
        "startDate": modis_date,
        "endDate": modis_date,
        "kmAboveBelow": 0,
        "kmLeftRight": 0
    }
    data, err = fetch(url, params)
    if err:
        return None, err

    for band in data.get("subset", []):
        if band.get("band") == "250m_16_days_NDVI":
            raw = band.get("data", [])
            scaled = [v * 0.0001 for v in raw]
            return statistics.fmean(scaled), None

    return None, "NDVI-Band nicht gefunden."


# --- LOAD AUTOMATICALLY ---
with st.spinner("Hole NASA-Daten…"):
    modis_date, calendar_date, date_err = get_latest_modis_date(lat, lon)

    if date_err:
        st.error(date_err)
    else:
        ndvi, ndvi_err = get_ndvi(lat, lon, modis_date)

        if ndvi_err:
            st.error(ndvi_err)
        else:
            st.success(f"NDVI erfolgreich geladen für {city}")
            st.write(f"📅 MODIS Datum: **{modis_date}**  (Kalender: {calendar_date})")

            # Metric
            st.metric("🌿 NDVI", f"{ndvi:.3f}")

            # Classification
            if ndvi < 0.2:
                status = "🔴 Dürre"
            elif ndvi < 0.4:
                status = "🟠 Stress"
            elif ndvi < 0.6:
                status = "🟡 Neutral"
            else:
                status = "🟢 Optimal"

            st.write("Zustand:", status)

            # --- Chart using Streamlit ---
            df = pd.DataFrame({"NDVI": [ndvi]}, index=["Wert"])
            st.bar_chart(df)

            # Debug
            with st.expander("🔍 Details"):
                st.write("Koordinaten:", lat, lon)
                st.write("MODIS Datum:", modis_date)
