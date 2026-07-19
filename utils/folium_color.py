def folium_color(impact):
    if impact > 5:
        return "green"   # amélioration nette
    elif impact > -5:
        return "orange"  # variation faible
    else:
        return "red"     # dégradation
