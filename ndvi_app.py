import streamlit as st
import requests
import pandas as pd

# Seiteneinstellungen
st.set_page_config(
    page_title="AcriRisk – Live Klima Daten",
    layout="wide"
)

st.title("🌱 Live Klima- & Wetterdaten für Agrarregionen")

# ----------------------------------------
# 📍 Städte
# ----------------------------------------

cities = {
    "Darmstadt, Deutschland": (49.8728, 8.6512),
    "Malolos, Philippinen": (14.8549, 120.8100),
    "Fortaleza, Brasilien": (-3.7319, -38.5267),
    "Tucson, USA": (32.2226, -110.9747),
}

city_name = st.selectbox("Standort auswählen", list(cities.keys()))
lat, lon = cities[city_name]

st.write(f"**Koordinaten:** {lat}, {lon}")

# ----------------------------------------
# 🌤 Open-Meteo URL
# ----------------------------------------

url = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={lat}&longitude={lon}"
    "&daily=temperature_2m_max,precipitation_sum,evapotranspiration"
    "&forecast_days=7"
    "&timezone=auto"
)

res = requests.get(url).json()

# Fail-safe
if "daily" not in res:
    st.error("❌ Fehler: Die API hat keine täglichen Wetterdaten zurückgegeben.")
    st.write("Antwort von der API:")
    st.json(res)
    st.stop()

daily = res["daily"]

days = daily["time"]
temp_max = daily["temperature_2m_max"]
precip = daily["precipitation_sum"]
eto = daily["evapotranspiration"]  # mm/Tag

# ----------------------------------------
# 📊 Temperatur (Line Chart)
# ----------------------------------------

df_temp = pd.DataFrame({
    "Datum": days,
    "Temperatur (°C)": temp_max
})

st.subheader("🌡 Max. Temperatur (°C)")
st.line_chart(df_temp, x="Datum", y="Temperatur (°C)")

# Letzter Wert
st.metric("Letzter Wert (°C)", f"{temp_max[-1]:.1f}")

# ----------------------------------------
# 🌧 Niederschlag (Bar Chart)
# ----------------------------------------

df_precip = pd.DataFrame({
    "Datum": days,
    "Niederschlag (mm)": precip
})

col1, col2 = st.columns([1,1])

with col2:
    st.subheader("🌧 Niederschlag (mm)")
    st.bar_chart(df_precip, x="Datum", y="Niederschlag (mm)")
    st.metric("Summe (7 Tage)", f"{sum(precip):.1f} mm")

# ----------------------------------------
# 💧 ET₀ / Verdunstung (Line Chart)
# ----------------------------------------

df_eto = pd.DataFrame({
    "Datum": days,
    "ET₀ (mm)": eto
})

st.subheader("💦 Wasserbedarf & Verdunstung")
st.line_chart(df_eto, x="Datum", y="ET₀ (mm)")

st.metric("Letzter Wert ET₀", f"{eto[-1]:.2f} mm")

st.caption("Quelle: Live-Daten von der Open-Meteo API.")
