import streamlit as st
import requests
import pandas as pd

# Seiteneinstellungen
st.set_page_config(
    page_title="AcriRisk – Live Klima Daten",
    layout="wide"
)

st.title("🌱 Live Klima- & Wetterdaten für Agrarregionen")

# Städte + Koordinaten
cities = {
    "Darmstadt, Deutschland": (49.8728, 8.6512),
    "Malolos, Philippinen": (14.8549, 120.8100),
    "Fortaleza, Brasilien": (-3.7319, -38.5267),
    "Tucson, USA": (32.2226, -110.9747),
}

city_name = st.selectbox("Standort auswählen", list(cities.keys()))
lat, lon = cities[city_name]

st.write(f"**Koordinaten:** {lat}, {lon}")

# Open-Meteo API
url = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={lat}&longitude={lon}"
    "&daily=temperature_2m_max,precipitation_sum"
    "&forecast_days=7&timezone=auto"
)

res = requests.get(url).json()

days = res["daily"]["time"]
temp_max = res["daily"]["temperature_2m_max"]
precip = res["daily"]["precipitation_sum"]

# ----------------------------------------
# 📈 Temperatur Chart (DataFrame nötig!)
# ----------------------------------------

df_temp = pd.DataFrame({
    "Datum": days,
    "Temperatur": temp_max
})

st.subheader("📈 Max. Temperatur (°C)")
st.line_chart(df_temp, x="Datum", y="Temperatur")

# ----------------------------------------
# 🌧 Niederschlags-Chart
# ----------------------------------------

df_precip = pd.DataFrame({
    "Datum": days,
    "Niederschlag": precip
})
