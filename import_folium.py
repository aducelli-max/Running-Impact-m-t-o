import folium
from IPython.display import display
display(carte)


center_lat = activities["start_lat"].mean()
center_lon = activities["start_lon"].mean()

carte = folium.Map(location=[center_lat, center_lon], zoom_start=13)

carte.save("ma_carte.html")
