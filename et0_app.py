import streamlit as st
import requests
import pandas as pd

# -----------------------------------------------------------------------------
# Seiteneinstellungen
# -----------------------------------------------------------------------------
st.set_page_config(page_title="ET₀ Referenzverdunstung", layout="wide")
st.title("💧 Referenz-Evapotranspiration ET₀ (FAO)")

# -----------------------------------------------------------------------------
# Standorte (Koordinaten)
# -----------------------------------------------------------------------------
cities = {
    "Darmstadt, Deutschland": (49.8728, 8.6512),
    "Malolos, Philippinen": (14.8549, 120.8100),
    "Fortaleza, Brasilien": (-3.7319, -38.5267),
    "Tucson, USA": (32.2226, -110.9747),
}

city_name = st.selectbox("Standort auswählen", list(cities.keys()))
lat, lon = cities[city_name]

st.write(f"**Koordinaten:** {lat}, {lon}")

# -----------------------------------------------------------------------------
# API Anfrage für stündliche ET₀-Daten
# -----------------------------------------------------------------------------
url = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={lat}&longitude={lon}"
    "&hourly=et0_fao_evapotranspiration"
    "&forecast_days=7"
    "&timezone=auto"
)

res = requests.get(url).json()

# -----------------------------------------------------------------------------
# Fehlerprüfung
# -----------------------------------------------------------------------------
if "hourly" not in res or "et0_fao_evapotranspiration" not in res["hourly"]:
    st.error("⚠️ Für diesen Standort sind keine ET₀-Daten verfügbar.")
    st.write(res)
    st.stop()

# -----------------------------------------------------------------------------
# Daten extrahieren
# -----------------------------------------------------------------------------
times = res["hourly"]["time"]
et0_hourly = res["hourly"]["et0_fao_evapotranspiration"]

df = pd.DataFrame({
    "Zeit": pd.to_datetime(times),
    "ET0_h": et0_hourly
})

df["Datum"] = df["Zeit"].dt.date

# -----------------------------------------------------------------------------
# Tageswerte berechnen (SUMME statt Durchschnitt)
# -----------------------------------------------------------------------------
df_daily = df.groupby("Datum")["ET0_h"].sum().reset_index()
df_daily.rename(columns={"ET0_h": "ET0 (mm/Tag)"}, inplace=True)

# -----------------------------------------------------------------------------
# Chart + Werte anzeigen
# -----------------------------------------------------------------------------
st.subheader("📈 ET₀ – tägliche Referenzverdunstung (berechnet aus Stundenwerten)")

st.line_chart(df_daily, x="Datum", y="ET0 (mm/Tag)")

# Letzter Wert
latest_value = df_daily["ET0 (mm/Tag)"].iloc[-1]
st.metric("Letzter Tageswert", f"{latest_value:.2f} mm/Tag")

# Hinweis
st.markdown(
    """
    **Hinweis:** ET₀ wird aus stündlichen Werten berechnet, indem alle 24 Stundenwerte
    eines Tages aufsummiert werden.  
    Typische Werte:
    - Europa Winter: **0.5 – 1.5 mm/Tag**
    - Tropen: **3 – 6 mm/Tag**
    - Wüstenregionen: **6 – 8+ mm/Tag**
    """
)


import pandas as pd

st.subheader("🔥 Dürreindex (ET₀ – Niederschlag)")

# --- Regen-Daten holen (Open-Meteo) ---
rain_url = "https://api.open-meteo.com/v1/forecast"
params_rain = {
    "latitude": lat,
    "longitude": lon,
    "daily": "precipitation_sum",
    "timezone": "auto"
}

rain_data = requests.get(rain_url, params=params_rain).json()
rain_dates = rain_data["daily"]["time"]
rain_values = rain_data["daily"]["precipitation_sum"]

df_rain = pd.DataFrame({
    "date": pd.to_datetime(rain_dates),
    "rain": rain_values
})

# --- ET₀ Daten (aus deiner bestehenden Berechnung) ---
df_et0["date"] = pd.to_datetime(df_et0["date"])

# --- Zusammenführen ---
df_combined = pd.merge(df_et0, df_rain, on="date", how="inner")

# --- Dürreindex berechnen ---
df_combined["drought"] = df_combined["et0"] - df_combined["rain"]

# --- Klassifikation ---
def classify_drought(x):
    if x < 0:
        return "🟢 Nass"
    elif x < 1.5:
        return "🟢 Normal"
    elif x < 3:
        return "🟠 Moderat"
    else:
        return "🔴 Stark"

df_combined["status"] = df_combined["drought"].apply(classify_drought)

# --- Plot ---
st.line_chart(
    df_combined.set_index("date")[["drought"]],
    height=300
)

# --- Tabelle als Übersicht ---
with st.expander("Details – Dürreindex"):
    st.dataframe(df_combined)
