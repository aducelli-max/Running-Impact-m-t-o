import pandas as pd
import pickle
from mon_projet_streamlit.utils.meteo import saison_meteo, moyenne_mois

df = pd.read_csv("activities_with_weather_harmonized.csv")
model = pickle.load(open("ml/model.pkl", "rb"))

def predict_time(distance_km, temp, rh, precip, cloud, wind, month, hour, total_elevation_gain):

    if pd.isna(rh):
        rh = moyenne_mois(df, "rh_mean", month) or saison_meteo(month)[1]
    if pd.isna(precip):
        precip = moyenne_mois(df, "precip_mean", month) or saison_meteo(month)[2]
    if pd.isna(cloud):
        cloud = moyenne_mois(df, "cloud_mean", month) or saison_meteo(month)[3]

    x = pd.DataFrame([{
        "temp_mean": temp,
        "rh_mean": rh,
        "precip_mean": precip,
        "cloud_mean": cloud,
        "wind_mean": wind,
        "temp_x_dist": temp * distance_km,
        "wind_x_dist": wind * distance_km,
        "rh_x_dist": rh * distance_km,
        "precip_x_dist": precip * distance_km,
        "total_elevation_gain": total_elevation_gain,
        "distance_km": distance_km,
        "month": month,
        "hour": hour
    }])

    x = x.fillna(0)

    speed = model.predict(x)[0]
    time_min = (distance_km / speed) * 60
    return speed, time_min
