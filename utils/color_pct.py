def color_pct(value, metric):
    """
    metric ∈ {"allure", "vitesse", "cardio", "temps"}
    """

    # Cas neutre (0% ou très proche)
    if abs(value) < 0.1:
        return f"<span style='color:#cccccc;'>**{value:+.1f}%**</span>"

    better_if_lower = ["allure", "cardio", "temps"]
    better_if_higher = ["vitesse"]

    # Exemple : allure plus basse = mieux
    if metric in better_if_lower:
        if value < 0:
            return f"<span style='color:green;'>**{value:+.1f}%**</span>"
        else:
            return f"<span style='color:red;'>**{value:+.1f}%**</span>"

    # Exemple : vitesse plus haute = mieux
    if metric in better_if_higher:
        if value > 0:
            return f"<span style='color:green;'>**{value:+.1f}%**</span>"
        else:
            return f"<span style='color:red;'>**{value:+.1f}%**</span>"
