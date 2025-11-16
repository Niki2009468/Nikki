import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="ET0 – Referenzverdunstung",
    layout="wide"
)

st.title("💧 Referenz-Evapotranspiration ET₀ (FAO)")

# Standorte
cities = {
    "Darmstadt, Deutschland": (49.8728, 8.6512),
    "Malolos, Philippinen": (14.8549, 120.8100),
    "Fortaleza, Brasilien": (-3.7319, -38.5267),
    "Tucson, USA": (32.2226, -110.9747),
}

city_name = st.selectbox("Standort auswählen", list(cities.keys()))
lat, lon = cities[city_name]

st.write(f"**Koordinaten:** {lat}, {lon}")

# ET0 API CALL
url_et0 = (
    "https://api.open-meteo.com/v1/agrometeo"
    f"?latitude={lat}&longitude={lon}"
    "&daily=et0_fao_evapotranspiration"
    "&timezone=auto&forecast_days=7"
)

res_et0 = requests.get(url_et0).json()

# Prüfen
if "daily" not in res_et0 or "et0_fao_evapotranspiration" not in res_et0["daily"]:
    st.error("⚠️ Für diesen Standort sind keine ET₀-Daten verfügbar.")
    st.json(res_et0)
else:
    et0_days = res_et0["daily"]["time"]
    et0_values = res_et0["daily"]["et0_fao_evapotranspiration"]

    df_et0 = pd.DataFrame({
        "Datum": et0_days,
        "ET0 (mm)": et0_values
    })

    st.subheader("📈 ET₀ (mm/Tag)")
    st.line_chart(df_et0, x="Datum", y="ET0 (mm)")

    st.metric("Letzter ET₀ Wert", f"{et0_values[-1]} mm")

    st.caption("Datenquelle: Open-Meteo Agrometeorology API")
