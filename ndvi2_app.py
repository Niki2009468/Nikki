import streamlit as st
import requests
import statistics
import matplotlib.pyplot as plt

# -------------------------------------------------------
# Streamlit Page Setup
# -------------------------------------------------------
st.set_page_config(page_title="NDVI Analyse – NASA MODIS", layout="centered")
st.title("🌱 NDVI Analyse – NASA MODIS Subset API")

# -------------------------------------------------------
# Städte
# -------------------------------------------------------
CITIES = {
    "Darmstadt, Deutschland": (49.8728, 8.6512),
    "Tucson, USA": (32.2226, -110.9747),
    "Fortaleza, Brasilien": (-3.7319, -38.5267),
    "Malolos, Philippinen": (14.8443, 120.8114),
}

city = st.selectbox("📍 Stadt auswählen", list(CITIES.keys()))
lat, lon = CITIES[city]

PRODUCT = "MOD13Q1"
BASE = "https://modis.ornl.gov/rst/api/v1"


# -------------------------------------------------------
# Helper
# -------------------------------------------------------
def fetch(url, params):
    try:
        r = requests.get(url, params=params, timeout=30)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:200]}"
        return r.json(), None
    except Exception as e:
        return None, str(e)


# -------------------------------------------------------
# 1. Holen der MODIS-Datenliste
# -------------------------------------------------------
def get_latest_modis_date(lat, lon):
    url = f"{BASE}/{PRODUCT}/dates"
    params = {"latitude": lat, "longitude": lon}

    resp, err = fetch(url, params)
    if err:
        return None, None, err

    if "dates" not in resp:
        return None, None, "Antwort enthält keine 'dates'-Liste."

    latest = resp["dates"][-1]  # neuester Datensatz

    modis_date = latest.get("modis_date")
    calendar_date = latest.get("calendar_date")

    return modis_date, calendar_date, None


# -------------------------------------------------------
# 2. NDVI für ein MODIS-Datum holen
# -------------------------------------------------------
def get_ndvi(lat, lon, modis_date):
    url = f"{BASE}/{PRODUCT}/subset"
    params = {
        "latitude": lat,
        "longitude": lon,
        "startDate": modis_date,
        "endDate": modis_date,
        "kmAboveBelow": 0,
        "kmLeftRight": 0
    }

    resp, err = fetch(url, params)
    if err:
        return None, err

    subset = resp.get("subset")
    if not subset:
        return None, "Kein 'subset' in Antwort."

    ndvi_band = None
    for b in subset:
        if b.get("band") == "250m_16_days_NDVI":
            ndvi_band = b
            break

    if ndvi_band is None:
        return None, "NDVI-Band nicht gefunden."

    raw = ndvi_band.get("data")
    if not raw:
        return None, "NDVI-Band enthält keine Daten."

    # MODIS NDVI Skalierung
    scaled = [v * 0.0001 for v in raw]

    mean_val = statistics.fmean(scaled)
    return mean_val, None


# -------------------------------------------------------
# AUTOMATISCHES LADEN (OHNE BUTTON)
# -------------------------------------------------------
with st.spinner("Hole aktuelle NDVI-Daten von der NASA…"):

    modis_date, calendar_date, date_err = get_latest_modis_date(lat, lon)

    if date_err:
        st.error("❌ Fehler beim Laden der MODIS-Daten.")
        st.write(date_err)

    else:
        ndvi, ndvi_err = get_ndvi(lat, lon, modis_date)

        if ndvi_err:
            st.error("❌ Fehler beim Abrufen des NDVI.")
            st.write(ndvi_err)
            st.write("Verwendetes MODIS-Datum:", modis_date)

        else:
            st.success(f"✔ NDVI geladen für {city}")
            st.write(f"📅 MODIS-Datum: **{modis_date}** (Kalender: {calendar_date})")
            st.metric("🌿 NDVI", f"{ndvi:.3f}")

            # Vegetationsklassifikation
            if ndvi < 0.2:
                status = "🔴 Dürre / schlechte Vegetation"
            elif ndvi < 0.4:
                status = "🟠 Stress"
            elif ndvi < 0.6:
                status = "🟡 neutral"
            else:
                status = "🟢 optimal"

            st.write("Zustand der Vegetation:", status)

            # -------------------------------------------------------
            # Grafik anzeigen
            # -------------------------------------------------------
            fig, ax = plt.subplots()
            ax.bar(["NDVI"], [ndvi])
            ax.set_ylim(0, 1)
            ax.set_ylabel("NDVI")
            ax.set_title(f"NDVI – {city}")
            st.pyplot(fig)

            # Debug für dich
            with st.expander("🔍 Debug-Info"):
                st.write("MODIS-Date:", modis_date)
                st.write("Koordinaten:", lat, lon)
