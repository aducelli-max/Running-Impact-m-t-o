import requests
import pandas as pd

def saison_meteo(month):
    if month in [3,4,5]: return 12, 65, 1.5, 55
    if month in [6,7,8]: return 22, 55, 1.0, 40
    if month in [9,10,11]: return 13, 75, 2.0, 65
    return 5, 80, 2.5, 70

def moyenne_mois(df, col, month, n=10):
    subset = df[df["month"] == month][col].dropna()
    if len(subset) >= 3:
        return subset.tail(n).mean()
    return None

def get_meteo(lat, lon, date, hour, df_h=None):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relativehumidity_2m,precipitation,cloudcover,windspeed_10m",
        "start_date": date,
        "end_date": date,
        "timezone": "Europe/Paris"
    }

    # -----------------------------
    # 🔥 API METEO AVEC TIMEOUT + FALLBACK
    # -----------------------------
    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        meteo = r.json()
    except Exception as e:
        print("⚠️ API météo non disponible, fallback utilisé :", e)
        return {
            "temp": 12,
            "rh": 60,
            "precip": 0,
            "cloud": 20,
            "wind": 5
        }

    # -----------------------------
    # Extraction des données
    # -----------------------------
    try:
        idx = meteo["hourly"]["time"].index(f"{date}T{hour:02d}:00")
    except ValueError:
        idx = 0

    temp = meteo["hourly"]["temperature_2m"][idx]
    rh = meteo["hourly"]["relativehumidity_2m"][idx]
    precip = meteo["hourly"]["precipitation"][idx]
    cloud = meteo["hourly"]["cloudcover"][idx]
    wind = meteo["hourly"]["windspeed_10m"][idx]

    month = int(date.split("-")[1])

    if pd.isna(rh):
        rh = moyenne_mois(df_h, "rh_mean", month) if df_h is not None else saison_meteo(month)[1]
    if pd.isna(precip):
        precip = moyenne_mois(df_h, "precip_mean", month) if df_h is not None else saison_meteo(month)[2]
    if pd.isna(cloud):
        cloud = moyenne_mois(df_h, "cloud_mean", month) if df_h is not None else saison_meteo(month)[3]

    return {
        "temp": temp,
        "rh": rh,
        "precip": precip,
        "cloud": cloud,
        "wind": wind
    }

