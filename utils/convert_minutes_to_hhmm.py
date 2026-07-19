def convert_minutes_to_hhmm(minutes):
    heures = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{heures}h{mins:02d}"
