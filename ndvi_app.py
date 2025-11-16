import streamlit as st
import requests
from datetime import date, timedelta

st.set_page_config(page_title="AcriRisk – Live Klima & Wetterdaten", layout="wide")
st.title("🌱 Live Klima- & Wetterdaten für Agrarregionen")

# --- Städte-Liste ---
cities = {
    "Darmstadt, Deutschland": (49.8728, 8.6512),
    "Malolos, Philippinen": (14.8549, 120.8100),
    "Fortaleza, Brasilien": (-3.7319, -38.5267),
    "Tucson, USA": (32.2226, -110.9747),
}

city_name = st.selectbox("Standort auswählen", list(cities.keys()))
lat, lon = cities[city_name]

st.write(f"**Koordinaten:** {lat}, {lon}")

# --- API Call (FORECAST, funktioniert sicher) ---
url = (
    "https://api.open-meteo.com/v1/forecast?"
    f"latitude={lat}&longitude={lon}"
    "&daily=temperature_2m_max,precipitation_sum,et0_fao_evapotranspiration"
    "&forecast_days=7&timezone=auto"
)

res = requests.get(url).json()

# Sicherstellen, dass "daily" existiert
if "daily" not in res:
    st.error("❌ Fehler: Die API hat keine täglichen Wetterdaten zurückgegeben.")
    st.json(res)
    st.stop()

daily = res["daily"]

# --- Temperatur ---
temp_dates = daily["time"]
temp_max = daily["temperature_2m_max"]

# --- Niederschlag ---
rain = daily["precipitation_sum"]

# --- ET0 ---
et0 = daily["et0_fao_evapotranspiration"]

# --- Charts ---
st.subheader("🔍 Überblick (7-Tage-Vorhersage)")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🌡️ Max. Temperatur (°C)")
    st.line_chart({"Temperatur (°C)": temp_max}, x=temp_dates)
    st.write(f"**Letzter Wert:** {temp_max[-1]} °C")

with col2:
    st.subheader("🌧️ Niederschlag (mm)")
    st.bar_chart({"Niederschlag (mm)": rain}, x=temp_dates)
    st.write(f"**Summe (7 Tage):** {sum(rain):.1f} mm")

st.subheader("💧 Wasserbedarf & Verdunstung")
st.line_chart({"ET₀ (mm/Tag)": et0}, x=temp_dates)
st.write(f"**Letzter Wert ET₀:** {et0[-1]:.2f} mm")

st.caption(
    "Quelle: Live-Daten von der Open-Meteo API. "
    "ET₀ beschreibt den täglichen Wasserbedarf einer Referenzgrasfläche."
)
