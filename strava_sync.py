import requests
import pandas as pd
from auth import refresh_tokens
from datetime import datetime
from utils.meteo import get_meteo, saison_meteo



# -----------------------------
# Récupération des activités Strava
# -----------------------------
def get_activities(access_token):
    print("📥 Récupération des activités Strava…")
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}

    all_activities = []
    page = 1

    while True:
        params = {"page": page, "per_page": 200}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            raise RuntimeError(f"Erreur API Strava : {response.status_code} — {response.text}")

        data = response.json()
        if not data:
            break

        all_activities.extend(data)
        page += 1

    print(f"✔️ {len(all_activities)} activités récupérées")
    return all_activities


# -----------------------------
# Récupération des streams GPS Strava
# -----------------------------
def get_streams(activity_id, access_token):
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams"
    headers = {"Authorization": f"Bearer {access_token}"}

    params = {
        "keys": "latlng,altitude,velocity_smooth,distance,heartrate",
        "key_by_type": True
    }

    r = requests.get(url, headers=headers, params=params)
    if r.status_code != 200:
        return None

    return r.json()


# -----------------------------
# Fonction robuste pour extraire lat/lon
# -----------------------------
def safe_latlng(value):
    if isinstance(value, list) and len(value) == 2:
        return value[0], value[1]
    return None, None


# -----------------------------
# Pipeline principal
# -----------------------------
def main():
    print("🔄 Rafraîchissement des tokens…")
    access_token, refresh_token = refresh_tokens()

    activities = get_activities(access_token)

    df = pd.DataFrame(activities)
    df.to_csv("activities_raw.csv", index=False)
    print("✔️ activities_raw.csv généré")

    print("🌦️ Ajout de la météo…")

    df_h = df.copy()

    # GPS de départ/arrivée
    df_h["start_lat"], df_h["start_lon"] = zip(*df_h["start_latlng"].apply(safe_latlng))
    df_h["end_lat"], df_h["end_lon"] = zip(*df_h["end_latlng"].apply(safe_latlng))

    # Dates
    df_h["start_date"] = pd.to_datetime(df_h["start_date"], utc=True)
    df_h["start_date_local"] = df_h["start_date"].dt.tz_convert("Europe/Paris")
    df_h["year"] = df_h["start_date"].dt.year
    df_h["month"] = df_h["start_date"].dt.month
    df_h["hour"] = df_h["start_date_local"].dt.hour

    # -----------------------------
    # MÉTÉO BRUTE (sans fallback)
    # -----------------------------
    temp_list, rh_list, precip_list, cloud_list, wind_list = [], [], [], [], []

    for _, row in df_h.iterrows():
        lat = row["start_lat"]
        lon = row["start_lon"]

        if pd.isna(lat) or pd.isna(lon):
            temp_list.append(None)
            rh_list.append(None)
            precip_list.append(None)
            cloud_list.append(None)
            wind_list.append(None)
            continue

        date_str = row["start_date"].strftime("%Y-%m-%d")
        hour = int(row["hour"])

        # ⚠️ IMPORTANT : df_h=None pour éviter les fallback prématurés
        meteo = get_meteo(lat, lon, date_str, hour, None)

        if meteo is None:
            temp_list.append(None)
            rh_list.append(None)
            precip_list.append(None)
            cloud_list.append(None)
            wind_list.append(None)
        else:
            temp_list.append(meteo["temp"])
            rh_list.append(meteo["rh"])
            precip_list.append(meteo["precip"])
            cloud_list.append(meteo["cloud"])
            wind_list.append(meteo["wind"])

    # Création des colonnes météo
    df_h["temperature"] = temp_list
    df_h["wind_speed"] = wind_list
    df_h["temp_mean"] = df_h["temperature"]
    df_h["wind_mean"] = df_h["wind_speed"]
    df_h["rh_mean"] = rh_list
    df_h["precip_mean"] = precip_list
    df_h["cloud_mean"] = cloud_list

    # -----------------------------
    # Fallback météo (maintenant OK)
    # -----------------------------
    for col, idx in [("rh_mean", 1), ("precip_mean", 2), ("cloud_mean", 3)]:
        df_h[col] = df_h.apply(
            lambda row: row[col]
            if pd.notna(row[col])
            else (moyenne_mois(df_h, col, row["month"]) or saison_meteo(row["month"])[idx]),
            axis=1,
        )

    # Colonnes calculées
    df_h["distance_km"] = df_h["distance"] / 1000
    df_h["vitesse_kmh"] = df_h["average_speed"] * 3.6
    df_h["allure_min_km"] = df_h["moving_time"] / df_h["distance_km"] / 60
    df_h["duration_min"] = df_h["moving_time"] / 60

    df_h["temp_x_dist"] = df_h["temp_mean"] * df_h["distance_km"]
    df_h["wind_x_dist"] = df_h["wind_mean"] * df_h["distance_km"]
    df_h["rh_x_dist"] = df_h["rh_mean"] * df_h["distance_km"]
    df_h["precip_x_dist"] = df_h["precip_mean"] * df_h["distance_km"]

    df_h["lat_start"] = df_h["start_lat"]
    df_h["lon_start"] = df_h["start_lon"]
    df_h["activity_id"] = df_h["id"]

    # -----------------------------
    # Catégorisation des distances (±10%)
    # -----------------------------
    def categorize_distance(d):
        km = d / 1000  # conversion en km

        # ±10% de marge
        if 4.5 <= km <= 5.5:
            return "5km"
        elif 9 <= km <= 11:
            return "10km"
        elif 13.5 <= km <= 16.5:
            return "15km"
        elif 18 <= km <= 22:
            return "20km"
        elif 19 <= km <= 23:  # semi-marathon ≈ 21.1 km
            return "Semi-marathon"
        else:
            return "Entrainement"

    df_h["categories_distances"] = df_h["distance"].apply(categorize_distance)


    # -----------------------------
    # Récupération GPS Strava → gps_points.csv
    # -----------------------------
    print("📡 Récupération des traces GPS…")

    gps_rows = []

    for _, row in df_h.iterrows():
        activity_id = row["id"]
        streams = get_streams(activity_id, access_token)

        if streams is None or "latlng" not in streams:
            continue

        latlng = streams["latlng"]["data"]
        altitude = streams.get("altitude", {}).get("data", [])
        velocity = streams.get("velocity_smooth", {}).get("data", [])
        distance = streams.get("distance", {}).get("data", [])
        heartrate = streams.get("heartrate", {}).get("data", [])

        for i in range(len(latlng)):
            gps_rows.append({
                "activity_id": activity_id,
                "lat": latlng[i][0],
                "lon": latlng[i][1],
                "altitude": altitude[i] if i < len(altitude) else None,
                "velocity": velocity[i] if i < len(velocity) else None,
                "distance": distance[i] if i < len(distance) else None,
                "heartrate": heartrate[i] if i < len(heartrate) else None
            })

    gps_df = pd.DataFrame(gps_rows)
    gps_df.to_csv("gps_points.csv", index=False)
    print("✔️ gps_points.csv généré")

    # Export final
    df_h.to_csv("activities_with_weather_harmonized.csv", index=False)
    print("✔️ activities_with_weather_harmonized.csv généré")


if __name__ == "__main__":
    main()
