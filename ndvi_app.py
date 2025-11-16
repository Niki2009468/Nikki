import streamlit as st
import requests
import pandas as pd

# -----------------------------------------------------------------------------------
# Seiteneinstellungen
# -----------------------------------------------------------------------------------
st.set_page_config(
    page_title="AcriRisk – Live Klima Daten",
    layout="wide"
)

st.title("🌱 Live Klima- & Wetterdaten für Agrarregionen")

# -----------------------------------------------------------------------------------
# Städte + Koordinaten
# -----------------------------------------------------------------------------------
cities = {
    "Darmstadt, Deutschland": (49.8728, 8.6512),
    "Malolos, Philippinen": (14.8549, 120.8100),
    "Fortaleza, Brasilien": (-3.7319, -38.5267),
    "Tucson, USA": (32.2226, -110.9747),
}

city_name = st.selectbox("Standort auswählen", list(cities.keys()))
lat, lon = cities[city_name]

st.write(f"**Koordinaten:** {lat}, {lon}")

# -----------------------------------------------------------------------------------
# Open-Meteo API-URL (korrekte Parameter)
# ACHTUNG: soil_moisture_0_7cm ist korrekt
# -----------------------------------------------------------------------------------
url = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={lat}&longitude={lon}"
    "&daily=temperature_2m_max,precipitation_sum,soil_moisture_0_7cm,evapotranspiration"
    "&forecast_days=7"
    "&models=best_match"
    "&timezone=auto"
)

# -----------------------------------------------------------------------------------
# API Anfrage
# -----------------------------------------------------------------------------------
res = requests.get(url).json()

# Defensive Fehlerprüfung
if "daily" not in res:
    st.error("⚠️ Fehler: Die API hat keine täglichen Wetterdaten zurückgegeben.")
    st.write("Antwort von der API:", res)
    st.stop()

daily = res["daily"]

# -----------------------------------------------------------------------------------
# Werte extrahieren
# -----------------------------------------------------------------------------------
days = daily["time"]
temp_max = daily["temperature_2m_max"]
precip = daily["precipitation_sum"]
soil = daily["soil_moisture_0_7cm"]
et0 = daily["evapotranspiration"]

# -----------------------------------------------------------------------------------
# DataFrames bauen
# -----------------------------------------------------------------------------------
df_temp = pd.DataFrame({
    "Datum": days,
    "Max. Temperatur (°C)": temp_max
})

df_precip = pd.DataFrame({
    "Datum": days,
    "Niederschlag (mm)": precip
})

df_soil = pd.DataFrame({
    "Datum": days,
    "Bodenfeuchte 0–7 cm (m³/m³)": soil
})

df_et0 = pd.DataFrame({
    "Datum": days,
    "Evapotranspiration (mm)": et0
})

# -----------------------------------------------------------------------------------
# Charts anzeigen
# -----------------------------------------------------------------------------------
st.markdown("### 🔎 Überblick (7-Tage-Vorhersage)")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Max. Temperatur (°C)")
    st.line_chart(df_temp, x="Datum", y="Max. Temperatur (°C)")
    st.metric(
        "Letzter Wert (°C)",
        f"{temp_max[-1]:.1f}",
        help="Maximale Temperatur am letzten Vorhersagetag"
    )

with col2:
    st.subheader("🌧 Niederschlag (mm)")
    st.bar_chart(df_precip, x="Datum", y="Niederschlag (mm)")
    st.metric(
        "Summe (7 Tage)",
        f"{sum(precip):.1f} mm",
        help="Gesamtniederschlag über die nächsten 7 Tage"
    )

st.markdown("### 🧪 Boden & Wasserbilanz")

col3, col4 = st.columns(2)

with col3:
    st.subheader("🌱 Bodenfeuchte 0–7 cm (m³/m³)")
    st.line_chart(df_soil, x="Datum", y="Bodenfeuchte 0–7 cm (m³/m³)")
    st.metric(
        "Letzter Wert Bodenfeuchte",
        f"{soil[-1]:.2f}",
        help="Oberflächennahe Bodenfeuchte (0–7 cm) am letzten Vorhersagetag"
    )

with col4:
    st.subheader("💧 Evapotranspiration (mm)")
    st.line_chart(df_et0, x="Datum", y="Evapotranspiration (mm)")
    st.metric(
        "Letzter Wert ET₀",
        f"{et0[-1]:.2f} mm",
        help="Referenz-Evapotranspiration am letzten Vorhersagetag"
    )

st.markdown(
    """
    **Quelle:** Alle Daten stammen live von der [Open-Meteo API](https://open-meteo.com/).  
    Bodenfeuchte und Evapotranspiration sind wichtige Kenngrößen zur Abschätzung von
    Dürre, Wasserstress und Ertragspotenzial.
    """
)
