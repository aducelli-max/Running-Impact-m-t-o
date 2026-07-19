def pace_color_pct(pct):
    if pct < -5:      # amélioration nette
        return "green"
    elif pct < 5:     # variation faible
        return "orange"
    else:             # dégradation
        return "red"
