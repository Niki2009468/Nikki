import streamlit as st
import requests
import pandas as pd
import statistics

# -----------------------------------------------------------
# PAGE SETUP
# -----------------------------------------------------------
st.set_page_config(page_title="🌍 Risiko-Dashboard", layout="wide")
st.title("🌍 Globales Risiko-Dashboard")
st.write("Integratives Vegetations-, Dürre- und Überflutungsmodell")

# -----------------------------------------------------------
# STANDORTE
# -----------------------------------------------------------
CITIES = {
    "Darmstadt, Deutschland": (49.8728, 8.6512),
    "Tucson, USA": (32.2226, -110.9747),
    "Fortaleza, Brasilien": (-3.7319, -38.5267),
    "Malolos, Philippinen": (14.8443, 120.8114),
}

city = st.selectbox("📍 Standort auswählen", list(CITIES.keys()))
lat, lon = CITIES[city]

# -----------------------------------------------------------
# 1) NDVI FETCH (NASA MODIS)
# -----------------------------------------------------------
BASE = "https://modis.ornl.gov/rst/api/v1"
PRODUCT = "MOD13Q1"

def fetch(url, params):
    try:
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

def get_current_ndvi(lat, lon):
    # MODIS Dates
    d = fetch(f"{BASE}/{PRODUCT}/dates", {"latitude": lat, "longitude": lon})
    if not d:
        return None
    latest = d["dates"][-1]
    modis_date = latest["modis_date"]

    # NDVI fetch
    data = fetch(f"{BASE}/{PRODUCT}/subset", {
        "latitude": lat,
        "longitude": lon,
        "startDate": modis_date,
        "endDate": modis_date,
        "kmAboveBelow": 0,
        "kmLeftRight": 0
    })

    if not data:
        return None

    for band in data["subset"]:
        if band["band"] == "250m_16_days_NDVI":
            raw_mean = statistics.fmean(band["data"])
            return raw_mean * 0.0001  # scale factor

    return None


# -----------------------------------------------------------
# 2) DÜRREINDEX (ET0 - REGEN)
# -----------------------------------------------------------
def get_drought(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "et0_fao_evapotranspiration",
        "daily": "precipitation_sum",
        "timezone": "auto",
        "past_days": 3,
        "forecast_days": 0,
    }
    data = requests.get(url, params).json()

    # ET0 DAILY (sum hourly)
    df_hourly = pd.DataFrame({
        "time": pd.to_datetime(data["hourly"]["time"]),
        "et0": data["hourly"]["et0_fao_evapotranspiration"],
    })
    df_hourly["date"] = df_hourly["time"].dt.date
    df_et0 = df_hourly.groupby("date")["et0"].sum().reset_index()

    # DAILY RAIN
    df_rain = pd.DataFrame({
        "date": pd.to_datetime(data["daily"]["time"]).dt.date,
        "rain": data["daily"]["precipitation_sum"],
    })

    df = pd.merge(df_et0, df_rain, on="date")
    last = df.iloc[-1]
    drought_index = last["et0"] - last["rain"]

    return drought_index


# -----------------------------------------------------------
# 3) ÜBERFLUTUNGSINDEX (1h, 3h, 24h)
# -----------------------------------------------------------
def get_flood(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation",
        "daily": "precipitation_sum",
        "timezone": "auto",
        "past_days": 2,
        "forecast_days": 0
    }
    data = requests.get(url, params).json()

    df = pd.DataFrame({
        "time": pd.to_datetime(data["hourly"]["time"]),
        "p1h": data["hourly"]["precipitation"]
    })
    df["p3h"] = df["p1h"].rolling(3).sum()

    # last valid 3h
    row = df.dropna().iloc[-1]
    return row["p1h"], row["p3h"], data["daily"]["precipitation_sum"][-1]


# -----------------------------------------------------------
# RISK SCORING (0–3)
# -----------------------------------------------------------
def score_ndvi(ndvi):
    if ndvi is None:
        return 2
    if ndvi > 0.6: return 0
    if ndvi > 0.4: return 1
    if ndvi > 0.2: return 2
    return 3

def score_drought(d):
    if d < 0: return 0
    if d < 1.5: return 1
    if d < 3: return 2
    return 3

def score_flood(p3h, p24h):
    if p3h < 10 and p24h < 20:
        return 0
    if p3h < 20 or p24h < 50:
        return 2
    return 3


# -----------------------------------------------------------
# FETCH ALL THREE MODULES
# -----------------------------------------------------------
with st.spinner("Lade Risikoindikatoren…"):
    ndvi = get_current_ndvi(lat, lon)
    drought = get_drought(lat, lon)
    p1h, p3h, p24h = get_flood(lat, lon)

# -----------------------------------------------------------
# RISK SCORES
# -----------------------------------------------------------
veg_score = score_ndvi(ndvi)
drought_score = score_drought(drought)
flood_score = score_flood(p3h, p24h)

total_score = max(veg_score, drought_score, flood_score)

AMP = {
    0: "🟢 Gering",
    1: "🟡 Leicht",
    2: "🟠 Mittel",
    3: "🔴 Hoch"
}

# -----------------------------------------------------------
# VISUAL OUTPUT
# -----------------------------------------------------------
st.header("📊 Gesamtrisiko")

st.metric("Gesamt-Risiko", AMP[total_score])

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🌱 Vegetation (NDVI)")
    st.metric("NDVI", f"{ndvi:.3f}" if ndvi else "–")
    st.write("Risiko:", AMP[veg_score])

with col2:
    st.subheader("🔥 Dürreindex")
    st.metric("ET₀ – Regen", f"{drought:.2f} mm")
    st.write("Risiko:", AMP[drought_score])

with col3:
    st.subheader("🌊 Überflutung")
    st.metric("3h Regen", f"{p3h:.1f} mm")
    st.metric("24h Regen", f"{p24h:.1f} mm")
    st.write("Risiko:", AMP[flood_score])
