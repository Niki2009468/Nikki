import streamlit as st
import requests
import pandas as pd

# -----------------------------------------------------------------------------------
# Seiteneinstellungen
# -----------------------------------------------------------------------------------
st.set_page_config(
    page_title="AcriRisk – ET0 Referenzverdunstung",
    layout="wide"
)

st.title("💧 Referenz-Evapotranspiration ET₀ (FAO)")

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
# API URL – HOURLY ET0 (funktioniert überall)
# -----------------------------------------------------------------------------------
url = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={lat}&longitude={lon}"
    "&hourly=et0_fao_evapotranspiration"
    "&forecast_days=7"
    "&timezone=auto"
)

res = requests.get(url).json()

# -----------------------------------------------------------------------------------
# Fehlerprüfung
# -----------------------------------------------------------------------------------
if "hourly" not in res or "et0_fao_evapotranspiration" not in res["hourly"]:
    st.error("⚠️ Für diesen Standort sind keine ET₀-Daten verfügbar.")
    st.json(res)
    st.stop()

# -----------------------------------------------------------------------------------
# Hourly → Daily aggregieren
# -----------------------------------------------------------------------------------
df = pd.DataFrame({
    "Zeit": res["hourly"]["time"],
    "ET0_h": res["hourly"]["et0_fao_evapotranspiration"]
})

df["Zeit"] = pd.to_datetime(df["Zeit"])
df["Datum"] = df["Zeit"].dt.date

# Tagesdurchschnitt ET0
df_daily = df.groupby("Datum")["ET0_h"].mean().reset_index()
df_daily.rename(columns={"ET0_h": "ET0 (mm/Tag)"}, inplace=True)

# -----------------------------------------------------------------------------------
# Chart anzeigen
# -----------------------------------------------------------------------------------
st.subheader("📈 ET₀ – tägliche Referenzverdunstung (berechnet aus Stundenwerten)")

st.line_chart(df_daily, x="Datum", y="ET0 (mm/Tag)")

# Letzter Wert zeigen
last_value = df_daily["ET0 (mm/Tag)"].iloc[-1]
st.metric("Letzter ET₀-Wert", f"{last_value:.2f} mm/Tag")

st.caption(
    "ET₀ basiert auf stündlichen FAO-Evapotranspirationswerten der Open-Meteo API, "
    "aggregiert zu täglichen Durchschnittswerten."
)
