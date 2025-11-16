import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="AcriRisk – Live Klima Daten", layout="wide")

st.title("🌱 Live Klima- & Wetterdaten für Agrarregionen")

cities = {
    "Darmstadt, Deutschland": (49.8728, 8.6512),
    "Malolos, Philippinen": (14.8549, 120.8100),
    "Fortaleza, Brasilien": (-3.7319, -38.5267),
    "Tucson, USA": (32.2226, -110.9747),
}

city_name = st.selectbox("Standort auswählen", list(cities.keys()))
lat, lon = cities[city_name]

st.write(f"**Koordinaten:** {lat}, {lon}")

# --- KORREKTE Open-Meteo Variablen ---
# ✔ temperature_2m          → normale Temperatur
# ✔ precipitation_sum       → Niederschlag
# ✔ et0                     → Referenz-Evapotranspiration

url = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={lat}&longitude={lon}"
    "&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum,et0"
    "&forecast_days=7&timezone=auto"
)

res = requests.get(url).json()

if "daily" not in res:
    st.error("❌ API liefert keine täglichen Daten.")
    st.json(res)
    st.stop()

daily = res["daily"]

# Temperatur-Normalwert: wir nehmen temperature_2m_mean (DAS wolltest du)
temperature = daily["temperature_2m_mean"]

days = daily["time"]
precip = daily["precipitation_sum"]
et0 = daily["et0"]

# ----------------------------
# 📈 Temperatur
# ----------------------------
df_temp = pd.DataFrame({
    "Datum": days,
    "Temperatur (°C)": temperature
})

st.subheader("🌡 Temperatur (°C)")
st.line_chart(df_temp, x="Datum", y="Temperatur (°C)")

# ----------------------------
# 🌧 Niederschlag
# ----------------------------
df_precip = pd.DataFrame({
    "Datum": days,
    "Niederschlag (mm)": precip
})

st.subheader("🌧 Niederschlag (mm)")
st.bar_chart(df_precip, x="Datum", y="Niederschlag (mm)")

# ----------------------------
# 💧 ET₀ – Referenz-Evapotranspiration
# ----------------------------
df_et0 = pd.DataFrame({
    "Datum": days,
    "ET₀ (mm)": et0
})

st.subheader("💦 Referenz-Evapotranspiration ET₀ (mm/Tag)")
st.line_chart(df_et0, x="Datum", y="ET₀ (mm)")
