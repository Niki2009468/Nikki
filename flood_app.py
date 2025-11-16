import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Überflutungsindex – Niederschlagsintensität", layout="centered")

st.title("🌊 Überflutungsindex – Starkregen & Flutrisiko")

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
def fetch_precipitation(lat, lon, past_days=3, forecast_days=1):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation",          # mm/h
        "daily": "precipitation_sum",       # mm/Tag
        "timezone": "auto",
        "past_days": past_days,
        "forecast_days": forecast_days,
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

with st.spinner("Lade Niederschlagsdaten von Open-Meteo…"):
    data = fetch_precipitation(lat, lon)

# -----------------------------
# 1) Stündlicher Niederschlag
# -----------------------------
hourly = data["hourly"]
df_hourly = pd.DataFrame({
    "time": pd.to_datetime(hourly["time"]),
    "precip_1h": hourly["precipitation"],  # mm/h
})
df_hourly = df_hourly.sort_values("time").reset_index(drop=True)

# 3-Stunden-Summe (rolling window)
df_hourly["precip_3h"] = df_hourly["precip_1h"].rolling(3).sum()

# 24-Stunden-Summe (aus hourly neu berechnet für Konsistenz)
df_hourly["date"] = df_hourly["time"].dt.normalize()
df_daily_from_hourly = (
    df_hourly.groupby("date", as_index=False)["precip_1h"]
    .sum()
    .rename(columns={"precip_1h": "precip_24h"})
)

# Alternativ: tägliche Summe direkt aus "daily"
daily = data["daily"]
df_daily_api = pd.DataFrame({
    "date": pd.to_datetime(daily["time"]),
    "precip_24h_api": daily["precipitation_sum"],
})

# Wir nutzen für Risikoanzeige df_daily_from_hourly (besser konsistent mit Stundenreihe)
df_daily = df_daily_from_hourly.sort_values("date").reset_index(drop=True)

# -----------------------------
# 2) Risiko-Klassifikation
# -----------------------------
def classify_flash_flood(p3h: float) -> str:
    """
    Flash-Flood Risiko auf Basis 3-Stunden-Summe.
    Grobe Schwellen (vereinfachtes Heuristik-Modell):
      < 10 mm / 3h  → gering
      10–20 mm / 3h → moderat
      > 20 mm / 3h  → hoch
    """
    if p3h is None or pd.isna(p3h):
        return "⚪ Keine Daten"
    if p3h < 10:
        return "🟢 Gering"
    elif p3h < 20:
        return "🟠 Moderat"
    else:
        return "🔴 Hoch"

def classify_daily_flood(p24h: float) -> str:
    """
    Tagesflut-Risiko auf Basis 24-Stunden-Summe.
    Grobe Schwellen:
      < 20 mm / Tag → gering
      20–50 mm      → moderat
      > 50 mm       → hoch
    """
    if p24h is None or pd.isna(p24h):
        return "⚪ Keine Daten"
    if p24h < 20:
        return "🟢 Gering"
    elif p24h < 50:
        return "🟠 Moderat"
    else:
        return "🔴 Hoch"

# Letzte Stunde mit gültiger 3-Stunden-Summe:
last_row = df_hourly.dropna(subset=["precip_3h"]).iloc[-1]
last_1h = last_row["precip_1h"]
last_3h = last_row["precip_3h"]
last_time = last_row["time"]

# Letzter Tag
last_day = df_daily.iloc[-1]
last_24h = last_day["precip_24h"]
last_date = last_day["date"]

risk_flash = classify_flash_flood(last_3h)
risk_daily = classify_daily_flood(last_24h)

# -----------------------------
# 3) Kennzahlen anzeigen
# -----------------------------
st.subheader("⚠️ Aktuelle Starkregen-Risiko-Einschätzung")

col1, col2 = st.columns(2)
with col1:
    st.metric(
        "Flash-Flood Index (3h-Summe)",
        f"{last_3h:.1f} mm / 3h",
        help=f"Basierend auf den letzten 3 Stunden bis {last_time}."
    )
    st.write("Kurzfristiges Risiko:", risk_flash)

with col2:
    st.metric(
        "Tagesniederschlag (24h)",
        f"{last_24h:.1f} mm / Tag",
        help=f"Summe des letzten vollen Tages ({last_date.date()})."
    )
    st.write("Tages-Flutrisiko:", risk_daily)

st.caption("Hinweis: Schwellenwerte sind heuristische Richtwerte und können lokal angepasst werden (z. B. nach Bodentyp, Hangneigung, Drainage).")

# -----------------------------
# 4) Charts
# -----------------------------
st.subheader("🌧 Stündlicher Niederschlag (mm/h)")
st.line_chart(
    df_hourly.set_index("time")[["precip_1h"]],
    height=250,
)

st.subheader("🌧 3-Stunden-Summe (mm / 3h)")
st.line_chart(
    df_hourly.set_index("time")[["precip_3h"]],
    height=250,
)

st.subheader("🌧 24-Stunden-Summe (mm / Tag)")
st.bar_chart(
    df_daily.set_index("date")[["precip_24h"]],
    height=250,
)

# -----------------------------
# 5) Debug & Details
# -----------------------------
with st.expander("🔍 Details & Rohdaten"):
    st.write("Letzte Stunde:", last_time, "| 1h:", last_1h, "mm | 3h:", last_3h, "mm")
    st.write("Letzter Tag:", last_date.date(), "| 24h:", last_24h, "mm")
    st.markdown("**Stündliche Daten (Ausschnitt):**")
    st.dataframe(df_hourly.tail(24))
    st.markdown("**Tägliche Daten (aus Stunden aggregiert):**")
    st.dataframe(df_daily)
  
