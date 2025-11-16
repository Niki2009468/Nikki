import streamlit as st
import requests
import statistics

st.set_page_config(page_title="NDVI Analyse – NASA MODIS", layout="centered")

st.title("🌱 NDVI Analyse – NASA MODIS Subset API")

# -----------------------------
# 1. Städte definieren
# -----------------------------
CITIES = {
    "Darmstadt, Deutschland": (49.8728, 8.6512),
    "Tucson, USA": (32.2226, -110.9747),
    "Fortaleza, Brasilien": (-3.7319, -38.5267),
    "Malolos, Philippinen": (14.8443, 120.8114),
}

PRODUCT = "MOD13Q1"
BASE_URL = "https://modis.ornl.gov/rst/api/v1"

city_name = st.selectbox("📍 Stadt auswählen", list(CITIES.keys()))
lat, lon = CITIES[city_name]


# -----------------------------
# 2. Hilfsfunktionen für NASA-API
# -----------------------------
def fetch_json(url: str, params: dict):
    """Request-Wrapper mit sauberer Fehlerbehandlung."""
    try:
        r = requests.get(url, params=params, headers={"Accept": "application/json"}, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json(), None
    except Exception as e:
        return None, str(e)


def get_latest_modis_date(lat: float, lon: float):
    """
    Holt alle verfügbaren MODIS-Daten für Produkt/Location
    und gibt das letzte (neueste) Datum zurück.
    """
    url = f"{BASE_URL}/{PRODUCT}/dates"
    params = {"latitude": lat, "longitude": lon}

    data, error = fetch_json(url, params)
    if error:
        return None, None, f"Fehler bei /dates: {error}"

    # Erwartete Struktur laut TESViS-Doku / MODISTools:
    # {"dates": [{"modis_date": "A2000049", "calendar_date": "2000-02-18"}, ...]}
    dates_list = data.get("dates")
    if not dates_list:
        return None, None, "Antwort von /dates enthält keine 'dates'-Liste."

    last = dates_list[-1]
    modis_date = last.get("modis_date") or last.get("modis") or last.get("date")
    calendar_date = last.get("calendar_date") or last.get("calendarDate")

    if not modis_date:
        return None, None, "Konnte 'modis_date' im letzten Eintrag nicht finden."

    return modis_date, calendar_date, None


def get_ndvi_for_date(lat: float, lon: float, modis_date: str):
    """
    Holt für eine Stadt und ein MODIS-Datum die NDVI-Werte und
    berechnet den Mittelwert (skaliert mit 0.0001).
    """
    url = f"{BASE_URL}/{PRODUCT}/subset"
    params = {
        "latitude": lat,
        "longitude": lon,
        "startDate": modis_date,
        "endDate": modis_date,
        "kmAboveBelow": 0,   # nur Pixel direkt um den Punkt
        "kmLeftRight": 0,
    }

    data, error = fetch_json(url, params)
    if error:
        return None, f"Fehler bei /subset: {error}"

    subset = data.get("subset")
    if not subset:
        return None, "Antwort von /subset enthält kein 'subset'."

    # Ein Eintrag pro Band; wir suchen das NDVI-Band
    ndvi_band = None
    for band_entry in subset:
        band_name = band_entry.get("band", "")
        if "250m_16_days_NDVI" in band_name:
            ndvi_band = band_entry
            break

    if ndvi_band is None:
        return None, "Kein NDVI-Band (250m_16_days_NDVI) im 'subset' gefunden."

    raw_values = ndvi_band.get("data")
    if not raw_values:
        return None, "NDVI-Band enthält keine 'data'-Werte."

    # MOD13Q1 NDVI ist skaliert: scale_factor = 0.0001
    scaled = [v * 0.0001 for v in raw_values if isinstance(v, (int, float))]
    if not scaled:
        return None, "Skalierte NDVI-Liste ist leer."

    mean_ndvi = statistics.fmean(scaled)
    return mean_ndvi, None


def classify_ndvi(ndvi: float) -> str:
    if ndvi < 0.2:
        return "🔴 Dürre / sehr schlechte Vegetation"
    elif ndvi < 0.4:
        return "🟠 Stress"
    elif ndvi < 0.6:
        return "🟡 neutral / leicht gestresst"
    else:
        return "🟢 optimal / gesunde Vegetation"


# -----------------------------
# 3. NDVI automatisch laden
# -----------------------------
with st.spinner("Hole aktuelle NDVI-Daten von der NASA…"):
    modis_date, calendar_date, date_error = get_latest_modis_date(lat, lon)

    if date_error:
        st.error("Konnte kein gültiges Datum von der NASA-API holen.")
        with st.expander("Details zum Fehler (Dates-Request)"):
            st.write(date_error)
    else:
        ndvi, ndvi_error = get_ndvi_for_date(lat, lon, modis_date)

        if ndvi_error or ndvi is None:
            st.error("Fehler beim Abruf der NDVI-Daten.")
            with st.expander("Details zum Fehler (Subset-Request)"):
                st.write(ndvi_error)
                st.write("Verwendetes MODIS-Datum:", modis_date, calendar_date)
        else:
            st.success(f"NDVI erfolgreich geladen – MODIS-Datum {modis_date} (Kalender: {calendar_date})")

            st.metric(label=f"🌿 NDVI für {city_name}", value=f"{ndvi:.3f}")
            st.write("Vegetationszustand:", classify_ndvi(ndvi))

            with st.expander("🔍 Debug-Infos"):
                st.write("Latitude / Longitude:", lat, lon)
                st.write("MODIS-Datum:", modis_date)
                st.write("Kalenderdatum:", calendar_date)
                st.write("NDVI-Rohwert:", ndvi)
