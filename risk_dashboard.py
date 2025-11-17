import streamlit as st
import pandas as pd
import requests
import statistics

# -----------------------------------------------------------
# STREAMLIT GRUNDEINSTELLUNG
# -----------------------------------------------------------
st.set_page_config(
    page_title="Globales Risiko-Dashboard",
    page_icon="🌍",
    layout="wide",
)

# -----------------------------------------------------------
# STANDORTE
# -----------------------------------------------------------
CITIES = {
    "Darmstadt, Deutschland": (49.8728, 8.6512),
    "Tucson, USA": (32.2226, -110.9747),
    "Fortaleza, Brasilien": (-3.7319, -38.5267),
    "Malolos, Philippinen": (14.8443, 120.8114),
}

CITY_CLIMATE = {
    "Darmstadt, Deutschland": "temperate",
    "Tucson, USA": "semi_arid",
    "Fortaleza, Brasilien": "tropical_humid",
    "Malolos, Philippinen": "tropical_monsoon",
}

# Klimaspezifische Parameter für das Risikomodell
CLIMATE_CONFIG = {
    "temperate": {
        "ndvi_opt": 0.60,
        "ndvi_min": 0.20,
        "drought_low": 0.5,
        "drought_high": 3.0,
        "flood_p3h_med": 10,
        "flood_p3h_high": 25,
        "flood_p24h_med": 20,
        "flood_p24h_high": 50,
    },
    "semi_arid": {
        "ndvi_opt": 0.40,
        "ndvi_min": 0.10,
        "drought_low": 2.0,
        "drought_high": 6.0,
        "flood_p3h_med": 5,
        "flood_p3h_high": 15,
        "flood_p24h_med": 10,
        "flood_p24h_high": 30,
    },
    "tropical_humid": {
        "ndvi_opt": 0.80,
        "ndvi_min": 0.40,
        "drought_low": 1.0,
        "drought_high": 5.0,
        "flood_p3h_med": 10,
        "flood_p3h_high": 30,
        "flood_p24h_med": 25,
        "flood_p24h_high": 80,
    },
    "tropical_monsoon": {
        "ndvi_opt": 0.75,
        "ndvi_min": 0.35,
        "drought_low": 1.0,
        "drought_high": 5.0,
        "flood_p3h_med": 8,
        "flood_p3h_high": 25,
        "flood_p24h_med": 20,
        "flood_p24h_high": 70,
    },
}

# -----------------------------------------------------------
# HILFSFUNKTIONEN
# -----------------------------------------------------------
def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def risk_label(score_0_100: float) -> str:
    if score_0_100 < 20:
        return "🟢 Niedrig"
    elif score_0_100 < 40:
        return "🟡 Leicht erhöht"
    elif score_0_100 < 65:
        return "🟠 Erhöht"
    elif score_0_100 < 85:
        return "🔴 Hoch"
    else:
        return "🟥 Extrem"


# -----------------------------------------------------------
# NDVI – NASA MODIS (wie in deiner NDVI2-App)
# -----------------------------------------------------------
BASE = "https://modis.ornl.gov/rst/api/v1"
PRODUCT = "MOD13Q1"  # 16-Tage NDVI


def fetch(url, params):
    try:
        r = requests.get(url, params=params, timeout=25)
        if r.status_code != 200:
            return None, f"Status {r.status_code}"
        return r.json(), None
    except Exception as e:
        return None, str(e)


def get_current_ndvi(lat, lon):
    # 1) verfügbare MODIS-Daten finden
    dates_url = f"{BASE}/{PRODUCT}/dates"
    dates_data, err = fetch(dates_url, {"latitude": lat, "longitude": lon})
    if err or not dates_data:
        return None

    last_date = dates_data["dates"][-1]["modis_date"]

    # 2) NDVI für letztes Datum holen
    subset_url = f"{BASE}/{PRODUCT}/subset"
    params = {
        "latitude": lat,
        "longitude": lon,
        "startDate": last_date,
        "endDate": last_date,
        "kmAboveBelow": 0,
        "kmLeftRight": 0,
    }
    data, err = fetch(subset_url, params)
    if err or not data:
        return None

    for band in data.get("subset", []):
        if band.get("band") == "250m_16_days_NDVI":
            raw_vals = band.get("data", [])
            if not raw_vals:
                return None
            # Unskaliert → skaliert (Faktor 0.0001)
            ndvi = statistics.fmean(raw_vals) * 0.0001
            return ndvi

    return None


# -----------------------------------------------------------
# DÜRREINDEX – Open-Meteo (ET0 – Niederschlag)
# -----------------------------------------------------------
def get_drought(lat, lon):
    """
    Dürreindex = ET0 - Niederschlag (mm/Tag) für den letzten vollständigen Tag.
    """
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
    r = requests.get(url, params=params, timeout=25)
    data = r.json()

    # ET0 stündlich → täglich
    hourly = data["hourly"]
    df_hourly = pd.DataFrame(
        {
            "time": pd.to_datetime(hourly["time"]),
            "et0": hourly["et0_fao_evapotranspiration"],
        }
    )
    df_hourly["date"] = df_hourly["time"].dt.normalize()
    df_et0_daily = (
        df_hourly.groupby("date", as_index=False)["et0"]
        .sum()
        .sort_values("date")
    )

    # Regen täglich
    daily = data["daily"]
    df_rain = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "rain": daily["precipitation_sum"],
        }
    ).sort_values("date")

    df = pd.merge(df_et0_daily, df_rain, on="date", how="inner")
    last = df.iloc[-1]
    drought_index = float(last["et0"] - last["rain"])
    return drought_index


# -----------------------------------------------------------
# ÜBERFLUTUNG – Open-Meteo (Starkregen)
# -----------------------------------------------------------
def get_flood(lat, lon):
    """
    Liefert:
    - Niederschlag letzte Stunde (mm)
    - 3h-Summe (mm)
    - 24h-Summe (mm)
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation",
        "daily": "precipitation_sum",
        "timezone": "auto",
        "past_days": 2,
        "forecast_days": 0,
    }
    r = requests.get(url, params=params, timeout=25)
    data = r.json()

    df = pd.DataFrame(
        {
            "time": pd.to_datetime(data["hourly"]["time"]),
            "p1h": data["hourly"]["precipitation"],
        }
    ).sort_values("time")

    df["p3h"] = df["p1h"].rolling(3).sum()

    last_row = df.dropna().iloc[-1]
    p1h = float(last_row["p1h"])
    p3h = float(last_row["p3h"])

    # 24h aus daily
    p24h = float(data["daily"]["precipitation_sum"][-1])

    return p1h, p3h, p24h


# -----------------------------------------------------------
# RISIKO-FUNKTIONEN (0–1 Skala)
# -----------------------------------------------------------
def veg_risk_0_1(ndvi: float, cfg: dict) -> float:
    """Vegetationsrisiko (0 = optimal, 1 = stark gestresst)."""
    ndvi_opt = cfg["ndvi_opt"]
    ndvi_min = cfg["ndvi_min"]
    risk = (ndvi_opt - ndvi) / (ndvi_opt - ndvi_min)
    return clamp01(risk)


def drought_risk_0_1(d: float, cfg: dict) -> float:
    """Dürre-Risiko basierend auf ET0 - Regen."""
    low = cfg["drought_low"]
    high = cfg["drought_high"]
    if d <= low:
        return 0.0
    risk = (d - low) / (high - low)
    return clamp01(risk)


def flood_risk_0_1(p3h: float, p24h: float, cfg: dict) -> float:
    """Flutrisiko, kombiniert aus 3h- und 24h-Regensummen."""
    p3_med = cfg["flood_p3h_med"]
    p3_high = cfg["flood_p3h_high"]
    p24_med = cfg["flood_p24h_med"]
    p24_high = cfg["flood_p24h_high"]

    flash = 0.0
    if p3h >= p3_med:
        flash = (p3h - p3_med) / (p3_high - p3_med)
    flash = clamp01(flash)

    daily = 0.0
    if p24h >= p24_med:
        daily = (p24h - p24_med) / (p24_high - p24_med)
    daily = clamp01(daily)

    return max(flash, daily)


# ===========================================================
# STREAMLIT UI – DASHBOARD
# ===========================================================
st.title("🌍 Globales Risiko-Dashboard")
st.caption("Integratives Vegetations-, Dürre- und Überflutungsmodell auf Basis von NASA MODIS & Open-Meteo")

city = st.selectbox("📍 Standort auswählen", list(CITIES.keys()))
lat, lon = CITIES[city]
st.write(f"Koordinaten: `{lat:.4f}, {lon:.4f}`")

climate_type = CITY_CLIMATE.get(city, "temperate")
cfg = CLIMATE_CONFIG[climate_type]

with st.spinner("Lade aktuelle Risikoindikatoren …"):
    ndvi = get_current_ndvi(lat, lon)
    drought = get_drought(lat, lon)
    p1h, p3h, p24h = get_flood(lat, lon)

# Sicherheits-Defaults, falls etwas None ist
if ndvi is None:
    ndvi = cfg["ndvi_min"]
    ndvi_note = "NDVI konnte nicht geladen werden – Schätzwert verwendet."
else:
    ndvi_note = None

# Einzelrisiken 0–1
veg_risk = veg_risk_0_1(ndvi, cfg)
drought_risk = drought_risk_0_1(drought, cfg)
flood_risk = flood_risk_0_1(p3h, p24h, cfg)

# Scores 0–100
veg_score = round(veg_risk * 100)
drought_score = round(drought_risk * 100)
flood_score = round(flood_risk * 100)

# Gesamt-Risiko (Gewichtung)
W_VEG, W_DROUGHT, W_FLOOD = 0.35, 0.40, 0.25
total_risk_0_1 = W_VEG * veg_risk + W_DROUGHT * drought_risk + W_FLOOD * flood_risk
total_score = round(total_risk_0_1 * 100)

# -----------------------------------------------------------
# AUSGABE – KPI-CARDS
# -----------------------------------------------------------
st.markdown("### 📊 Gesamtrisiko")

col_total, _, _ = st.columns([2, 1, 1])
with col_total:
    st.metric("Gesamt-Risiko-Score", f"{total_score}/100")
    st.write("Einstufung:", risk_label(total_score))
    st.write(f"Klimazone: **{climate_type}**")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### 🌱 Vegetation (NDVI)")
    st.metric("NDVI (aktuell)", f"{ndvi:.3f}")
    st.write(f"Risiko-Score: **{veg_score}/100**")
    st.write("Einstufung:", risk_label(veg_score))
    if ndvi_note:
        st.caption(ndvi_note)

with col2:
    st.markdown("#### 🔥 Dürreindex (ET₀ – Niederschlag)")
    st.metric("Dürreindex", f"{drought:.2f} mm")
    st.write(f"Risiko-Score: **{drought_score}/100**")
    st.write("Einstufung:", risk_label(drought_score))

with col3:
    st.markdown("#### 🌊 Überflutungsrisiko")
    st.metric("3h Regen", f"{p3h:.1f} mm")
    st.metric("24h Regen", f"{p24h:.1f} mm")
    st.write(f"Risiko-Score: **{flood_score}/100**")
    st.write("Einstufung:", risk_label(flood_score))

# -----------------------------------------------------------
# DETAIL-INFOS
# -----------------------------------------------------------
with st.expander("🔍 Details zum Risikomodell & Schwellenwerten"):
    st.markdown(
        f"""
        **Klimakonfiguration für {city} ({climate_type}):**
        
        - Optimaler NDVI: `{cfg['ndvi_opt']}`
        - Kritischer NDVI: `{cfg['ndvi_min']}`
        - Dürre-Bereich (ET₀ - Regen): `{cfg['drought_low']}–{cfg['drought_high']} mm/Tag`
        - Flut (3h): moderat ab `{cfg['flood_p3h_med']} mm`, hoch ab `{cfg['flood_p3h_high']} mm`
        - Flut (24h): moderat ab `{cfg['flood_p24h_med']} mm`, hoch ab `{cfg['flood_p24h_high']} mm`
        
        **Gewichtungen im Gesamtrisiko:**
        
        - Vegetation: **{int(W_VEG*100)} %**
        - Dürre: **{int(W_DROUGHT*100)} %**
        - Überflutung: **{int(W_FLOOD*100)} %**
        """
    )
