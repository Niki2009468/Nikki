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

import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="ET₀ & Dürreindex", layout="centered")

st.title("💧 Referenz-Evapotranspiration ET₀ (FAO) & Dürreindex")

# -----------------------------
# Standorte
# -----------------------------
CITIES = {
    "Darmstadt, Deutschland": (49.8728, 8.6512),
    "Tucson, USA": (32.2226, -110.9747),
    "Fortaleza, Brasilien": (-3.7319, -38.5267),
    "Malolos, Philippinen": (14.8443, 120.8114),
}

city = st.selectbox("📍 Standort auswählen", list(CITIES.keys()))
lat, lon = CITIES[city]

st.write(f"Koordinaten: {lat:.4f}, {lon:.4f}")

# -----------------------------
# Daten von Open-Meteo holen
# -----------------------------
def fetch_et0_and_rain(lat, lon, past_days=7, forecast_days=7):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "et0_fao_evapotranspiration",
        "daily": "precipitation_sum",
        "timezone": "auto",
        "past_days": past_days,
        "forecast_days": forecast_days,
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

with st.spinner("Lade ET₀- und Niederschlagsdaten von Open-Meteo…"):
    data = fetch_et0_and_rain(lat, lon)

# -----------------------------
# 1) ET₀ – stündlich ➜ täglich
# -----------------------------
hourly = data["hourly"]
df_hourly = pd.DataFrame({
    "time": pd.to_datetime(hourly["time"]),
    "et0": hourly["et0_fao_evapotranspiration"],
})
df_hourly["date"] = df_hourly["time"].dt.normalize()  # nur Datum

df_et0_daily = (
    df_hourly.groupby("date", as_index=False)["et0"]
    .sum()
    .sort_values("date")
)

# -----------------------------
# 2) Niederschlag – täglich
# -----------------------------
daily = data["daily"]
df_rain = pd.DataFrame({
    "date": pd.to_datetime(daily["time"]),
    "rain": daily["precipitation_sum"],
}).sort_values("date")

# -----------------------------
# 3) Dürreindex berechnen
# -----------------------------
df_combined = pd.merge(df_et0_daily, df_rain, on="date", how="inner")
df_combined["drought"] = df_combined["et0"] - df_combined["rain"]

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

# -----------------------------
# 4) Charts anzeigen
# -----------------------------
st.subheader("📊 ET₀ – tägliche Referenzverdunstung")
st.line_chart(
    df_et0_daily.set_index("date")["et0"],
    height=250
)

st.caption("Hinweis: ET₀ ist aus stündlichen Werten summiert (mm/Tag).")

st.subheader("🌧 Niederschlag (mm/Tag)")
st.bar_chart(
    df_rain.set_index("date")["rain"],
    height=250
)

st.subheader("🔥 Dürreindex (ET₀ – Niederschlag)")
st.line_chart(
    df_combined.set_index("date")["drought"],
    height=250
)

# Letzter Tag zusammengefasst
last = df_combined.iloc[-1]
st.markdown(
    f"**Letzter Tag:** {last['date'].date()} – "
    f"Dürreindex: `{last['drought']:.2f} mm/Tag` → {last['status']}"
)

with st.expander("🔍 Details (Tabelle)"):
    st.dataframe(df_combined.reset_index(drop=True))

# --- Tabelle als Übersicht ---
with st.expander("Details – Dürreindex"):
    st.dataframe(df_combined)
