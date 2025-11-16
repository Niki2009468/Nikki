import streamlit as st
import requests
import datetime

st.set_page_config(page_title="NDVI Dashboard", layout="centered")

st.title("🌱 NDVI Analyse – NASA MODIS Subset API")


# 1. Deine Städte
cities = {
    "Darmstadt, Deutschland": (49.8728, 8.6512),
    "Tucson, USA": (32.2226, -110.9747),
    "Fortaleza, Brasilien": (-3.7319, -38.5267),
    "Malolos, Philippinen": (14.8443, 120.8114)
}

city = st.selectbox("📍 Stadt auswählen", list(cities.keys()))
lat, lon = cities[city]


# 2. Funktion, um NDVI abzurufen
def get_ndvi(lat, lon):
    url = (
        f"https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset?"
        f"latitude={lat}&longitude={lon}&band=250m_16_days_NDVI&startDate=AUTO&endDate=AUTO"
    )

    try:
        response = requests.get(url).json()

        subset = response.get("subset", [])
        if not subset:
            return None, "Keine NDVI-Daten erhalten."

        # Neuestes Datum
        entry = subset[-1]
        raw_value = entry["value"]  # z.B. 6342
        ndvi = raw_value / 10000    # normieren
        date = entry["date"]

        return ndvi, date

    except Exception as e:
        return None, str(e)


# 3. Button
if st.button("📡 NDVI abrufen"):
    with st.spinner("Lade NDVI-Daten von der NASA..."):
        ndvi, date = get_ndvi(lat, lon)

        if ndvi is None:
            st.error("Fehler beim Abruf der NDVI-Daten.")
        else:
            st.success(f"NDVI erfolgreich geladen ({date})")

            # 4. NDVI-Wert anzeigen
            st.metric(label=f"🌿 NDVI für {city}", value=f"{ndvi:.3f}")

            # 5. Ampelsystem
            def classify_ndvi(x):
                if x < 0.2:
                    return "🔴 Dürre / Sehr schlecht"
                elif x < 0.4:
                    return "🟠 Stress"
                elif x < 0.6:
                    return "🟡 Neutral / Leicht gestresst"
                else:
                    return "🟢 Optimal"

            st.write("Vegetationszustand:", classify_ndvi(ndvi))

            # Debug-Ausgabe
            with st.expander("API-Rohdaten anzeigen"):
                st.write("NDVI (roh):", ndvi)
                st.write("Datum:", date)
