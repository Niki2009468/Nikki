import streamlit as st
import requests
import pandas as pd

# ------------------------------------------------------
# Seiteneinstellungen
# ------------------------------------------------------
st.set_page_config(
    page_title="NDVI – Vegetationsindex",
    layout="wide"
)

st.title("🌿 NDVI – Vegetationsvitalität (Vegetation Index)")

# ------------------------------------------------------
# Städte & Koordinaten
# ------------------------------------------------------
cities = {
    "Darmstadt, Deutschland": (49.8728, 8.6512),
    "Malolos, Philippinen": (14.8549, 120.8100),
    "Fortaleza, Brasilien": (-3.7319, -38.5267),
    "Tucson, USA": (32.2226, -110.9747),
}

city_name = st.selectbox("Standort auswählen", list(cities.keys()))
lat, lon = cities[city_name]

st.write(f"**Koordinaten:** {lat}, {lon}")

# ------------------------------------------------------
# NDVI API Request (Open-Meteo Vegetation API)
# ------------------------------------------------------
url = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={lat}&longitude={lon}"
    "&daily=vegetation_index"
    "&forecast_days=7"
    "&timezone=auto"
)

response = requests.get(url)
data = response.json()

# ------------------------------------------------------
# Fehlerbehandlung
# ------------------------------------------------------
if "daily" not in data:
    st.error("⚠️ API lieferte keine NDVI-Daten.")
    st.write(data)
    st.stop()

daily = data["daily"]

if "vegetation_index" not in daily:
    st.warning("⚠️ Für diesen Standort sind keine NDVI-Daten verfügbar.")
    st.write(data)
    st.stop()

# ------------------------------------------------------
# NDVI Daten extrahieren
# ------------------------------------------------------
dates = daily["time"]
ndvi = daily["vegetation_index"]

df_ndvi = pd.DataFrame({
    "Datum": dates,
    "NDVI": ndvi
})

# ------------------------------------------------------
# NDVI Chart
# ------------------------------------------------------
st.subheader("🌱 NDVI – tägliche Vegetationsvitalität")
st.line_chart(df_ndvi, x="Datum", y="NDVI")

# ------------------------------------------------------
# Kennzahl
# ------------------------------------------------------
st.metric(
    "Letzter NDVI-Wert",
    f"{ndvi[-1]:.2f}",
    help="NDVI beschreibt die Vitalität und Photosyntheseaktivität der Vegetation."
)

# ------------------------------------------------------
# Info
# ------------------------------------------------------
st.markdown("""
**Quelle:** Open-Meteo Vegetation Index API  
NDVI-Werte reichen von **–1 bis +1** und zeigen die Vitalität der Vegetation:
- < 0.20 → kaum Vegetation / Trockenheit  
- 0.20 – 0.40 → mäßige Vegetation  
- 0.40 – 0.60 → gesundes Wachstum  
- > 0.60 → sehr vitale Vegetation  
""")
