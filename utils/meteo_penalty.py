def meteo_penalty(temp, rh, wind, precip):
    # Température
    if temp <= 10:
        pen_temp = 0
    elif temp <= 20:
        pen_temp = 2
    elif temp <= 25:
        pen_temp = 5
    elif temp <= 30:
        pen_temp = 10
    else:
        pen_temp = 15

    # Humidité
    if rh <= 50:
        pen_rh = 0
    elif rh <= 70:
        pen_rh = 2
    elif rh <= 85:
        pen_rh = 4
    else:
        pen_rh = 6

    # Vent
    if wind <= 5:
        pen_wind = 0
    elif wind <= 10:
        pen_wind = 2
    elif wind <= 20:
        pen_wind = 6
    else:
        pen_wind = 12

    # Pluie 
    if precip <= 1:
        pen_precip = 0
    elif precip <= 3:
        pen_precip = 3
    elif precip <= 7:
        pen_precip = 6
    else:
        pen_precip = 10

    return pen_temp + pen_rh + pen_wind + pen_precip

