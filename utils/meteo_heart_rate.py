def meteo_heart_rate(temp, rh, wind):
    bpm_increase = 0

    # Température
    if temp > 18:
        bpm_increase += (temp - 18) * 0.8   # +0.8 BPM par degré au-dessus de 18°C

    # Humidité
    if rh > 60:
        bpm_increase += (rh - 60) * 0.15    # +0.15 BPM par % au-dessus de 60%

    # Vent (refroidissement)
    if wind > 15:
        bpm_increase -= (wind - 15) * 0.3   # -0.3 BPM par km/h au-dessus de 15 km/h

    return bpm_increase
