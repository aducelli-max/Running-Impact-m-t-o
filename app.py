import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import time
import plotly.graph_objects as go

from mon_projet_streamlit.ml.utils_ml import predict_time
from mon_projet_streamlit.utils.couleur_allure import couleur_allure
from mon_projet_streamlit.utils.meteo_penalty import meteo_penalty
from mon_projet_streamlit.utils.meteo_heart_rate import meteo_heart_rate
from mon_projet_streamlit.utils.color_pct import color_pct
from mon_projet_streamlit.utils.folium_color import folium_color
from mon_projet_streamlit.utils.meteo import get_meteo
from mon_projet_streamlit.strava_sync import main

# ---------------------
# INITIALISATION SESSION
# ---------------------
if "page" not in st.session_state:
    st.session_state.page = "home"

if "selected_activity" not in st.session_state:
    st.session_state.selected_activity = None

# ---------------------
# PAGE 1 — ACCUEIL
# ---------------------
if st.session_state.page == "home":

    st.title("🏃‍♂️ Météo et Chrono : Prédire sa perf'")

    # --- Boutons d'action ---
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Mise à jour"):
            with st.spinner("⏳ Mise à jour des activités…"):
                progress = st.progress(0)
                for i in range(100):
                    time.sleep(0.02)
                    progress.progress(i + 1)
                df_updated = main()
            st.success("✔️ Mise à jour terminée !")
            st.write(f"📊 Total activités : {len(df_updated)}")

    with col2:
        uploaded_gpx = st.file_uploader("📥 Import GPX", type=["gpx"])
        if uploaded_gpx is not None:
            st.write("GPX reçu, traitement en cours...")

    # ---------------------
    # CHARGEMENT DES DONNÉES
    # ---------------------
    df = pd.read_csv("activities_with_weather_harmonized.csv")
    df["start_date"] = pd.to_datetime(df["start_date"], utc=True)
    df["start_date_local"] = pd.to_datetime(df["start_date_local"], utc=True)

    gps = pd.read_csv("gps_points.csv")

    # ---------------------
    # MÉTÉO DU JOUR
    # ---------------------
    best_row_today = df.iloc[0]
    lat = best_row_today["lat_start"]
    lon = best_row_today["lon_start"]
    date_str = datetime.now().strftime("%Y-%m-%d")
    hour_now = datetime.now().hour

    meteo_today = get_meteo(lat, lon, date_str, hour_now, df)

    st.subheader("🌦️ La météo du jour")
    st.write(f"**Température :** {meteo_today['temp']} °C")
    st.write(f"**Vent :** {meteo_today['wind']} km/h")
    st.write(f"**Humidité :** {meteo_today['rh']} %")
    st.write(f"**Précipitations :** {meteo_today['precip']} mm")
    st.write(f"**Nuages :** {meteo_today['cloud']} %")

    # ---------------------
    # FILTRES ANNÉE / MOIS / CATÉGORIES
    # ---------------------
    df_cat = df.copy()
    last_activity = df_cat.sort_values(by="start_date_local", ascending=False).iloc[0]
    default_year = int(last_activity["year"])
    default_month = int(last_activity["month"])

    annees_disponibles = sorted(df_cat["year"].unique())
    annee = st.selectbox("Choisir l'année :", annees_disponibles,
                         index=annees_disponibles.index(default_year))

    mois_noms = {
        1:"Janvier",2:"Février",3:"Mars",4:"Avril",5:"Mai",6:"Juin",
        7:"Juillet",8:"Août",9:"Septembre",10:"Octobre",11:"Novembre",12:"Décembre"
    }

    mois_dispo_num = sorted(df_cat[df_cat["year"] == annee]["month"].unique())
    mois_nom = st.selectbox("Choisir le mois :", [mois_noms[m] for m in mois_dispo_num],
                            index=mois_dispo_num.index(default_month))
    mois_num = [k for k,v in mois_noms.items() if v == mois_nom][0]

    df_filtre = df_cat[(df_cat["year"] == annee) & (df_cat["month"] == mois_num)]
    categories_dispo = sorted(df_filtre["categories_distances"].unique())
    categories_selection = st.multiselect("Choisir les catégories :", categories_dispo,
                                          default=categories_dispo)

    df_filtre = df_filtre[df_filtre["categories_distances"].isin(categories_selection)]

    st.subheader("🗺️ Parcours du mois sélectionné")

    # Carte centrée sur la première activité du mois
    carte = folium.Map(
        location=[df_filtre.iloc[0]["lat_start"], df_filtre.iloc[0]["lon_start"]],
        zoom_start=13
    )

    # -----------------------------
    # AFFICHAGE DE TOUS LES PARCOURS
    # -----------------------------
    for activity_id in df_filtre["activity_id"].unique():

        gps_run = gps[gps["activity_id"] == activity_id].dropna()
        if gps_run.empty:
            continue

        gps_run = gps_run.iloc[::3]
        gps_run["pace"] = (1000 / gps_run["velocity"]) / 60
        coords = gps_run[["lat", "lon"]].dropna().values.tolist()
        if len(coords) < 2:
            continue

        # Trace grise de fond
        folium.PolyLine(
            coords,
            color="grey",
            weight=3,
            opacity=0.3
        ).add_to(carte)

        # Trace colorée selon allure
        for i in range(len(coords) - 1):
            folium.PolyLine(
                [coords[i], coords[i+1]],
                color=couleur_allure(float(gps_run.iloc[i].pace)),
                weight=5,
                opacity=0.9
            ).add_to(carte)

        # Markers départ / arrivée
        folium.Marker(
            coords[0],
            popup=str(activity_id),
            icon=folium.Icon(icon="play")
        ).add_to(carte)

        folium.Marker(
            coords[-1],
            popup=str(activity_id),
            icon=folium.Icon(color='black', icon="flag-checkered", prefix="fa")
        ).add_to(carte)

    # -----------------------------
    # ZOOM AUTOMATIQUE SUR TOUTES LES COURSES
    # -----------------------------
    gps_all = gps[gps["activity_id"].isin(df_filtre["activity_id"])].dropna()

    if not gps_all.empty:
        min_lat = gps_all["lat"].min()
        max_lat = gps_all["lat"].max()
        min_lon = gps_all["lon"].min()
        max_lon = gps_all["lon"].max()

        carte.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

    # --- Affichage Folium ---
    map_data = st_folium(carte, height=600, width=900)

    # --- Clic sur un marker → sélection pour prédiction ---
    if map_data and "last_object_clicked" in map_data:
        clicked = map_data["last_object_clicked"]
        if clicked and "popup" in clicked:
            activity_clicked = int(clicked["popup"])
            st.session_state["selected_activity"] = df_filtre[df_filtre["activity_id"] == activity_clicked].iloc[0]
            st.session_state.page = "prediction"
            st.rerun()

    # -----------------------------
    # COURSES DU MOIS
    # -----------------------------
    st.subheader("📅 Courses du mois")

    for cat in categories_selection:

        st.markdown(f"<div class='badge'>🏷️ {cat}</div>", unsafe_allow_html=True)
        st.markdown("""
        <style>
        .badge {
        display: inline-block;
        background-color: #4FC3F7;
        color: white;
        padding: 10px 18px;
        border-radius: 12px;
        font-size: 26px;        /* ← Taille du texte augmentée */
        font-weight: bold;
        margin: 8px 0;
        box-shadow: 0 4px 10px rgba(0,0,0,0.25);}
        </style>
        """, unsafe_allow_html=True)

        df_cat_sorted = df_filtre[df_filtre["categories_distances"] == cat].sort_values(by="duration_min")

        for _, row in df_cat_sorted.iterrows():

            trophy = " 🏆" if row["activity_id"] == df_cat_sorted.iloc[0]["activity_id"] else ""
            bpm = row["average_heartrate"]
            bpm_txt = f"{bpm:.0f} BPM" if pd.notna(bpm) else "—"

            # --- Carte info ---
            st.markdown(f"""
            <div class="card">
                <strong>{row['start_date_local'].strftime('%Y-%m-%d')}</strong>{trophy}
                Distance : {row['distance_km']:.1f} km
                Allure : {row['allure_min_km']:.2f} min/km
                Vitesse : {row['vitesse_kmh']:.2f} km/h
                Cardio : {bpm_txt}
                Temps : {row['duration_min']:.1f} min
            </div>
            """, unsafe_allow_html=True)

            # --- Graphique ---
            stats_labels = ["Allure","Vitesse","Cardio","Temps"]
            stats_values = [
                row["allure_min_km"],
                row["vitesse_kmh"],
                bpm if pd.notna(bpm) else 0,
                row["duration_min"]
            ]

            fig = go.Figure(go.Bar(
                x=stats_values,
                y=stats_labels,
                orientation='h',
                marker=dict(color=["#4FC3F7","#81C784","#E57373","#FFD54F"])
            ))

            fig.update_layout(
                height=150,
                margin=dict(l=0,r=0,t=0,b=0),
                template="plotly_dark",
                xaxis=dict(showgrid=False, visible=False),
                yaxis=dict(showgrid=False),
            )

            st.plotly_chart(fig, use_container_width=True)

            # --- Bouton prédire ---
            if st.button("🔮 Prédire", key=f"btn_predict_{row['activity_id']}"):
                st.session_state["selected_activity"] = row
                st.session_state.page = "prediction"
                st.rerun()

            st.markdown("<hr class='separator'>", unsafe_allow_html=True)


#---------------------
# PAGE PREDICTION
#---------------------


if st.session_state.page == "prediction":
    
    def get_coach_phrase(score_meteo):
        if score_meteo >= 80:
            return """
        Conditions idéales pour performer.
        La météo te porte, ton corps va répondre, et le terrain est avec toi.
        C’est le moment de dérouler une foulée propre, régulière, ambitieuse.
        Reste fluide, respire, et laisse la mécanique faire le travail.
        Aujourd’hui, tu peux viser un chrono solide sans te mettre en danger.
        """, "#00FFAA", "🟢 Conditions parfaites"
    
        elif score_meteo >= 60:
            return """
        Conditions correctes, rien d’alarmant.
        Tu peux faire une bonne course, mais la clé sera la gestion.
        Ne pars pas trop vite, installe ton rythme, reste concentré.
        La météo ne t’aide pas, mais elle ne te pénalise pas non plus.
        Ton mental fera la différence : reste propre, reste lucide.
        """, "#4FC3F7", "🔵 Conditions correctes"
    
        elif score_meteo >= 40:
            return """
        Météo exigeante, il va falloir courir avec la tête.
        Adapte ton allure, protège ton cardio, surveille ton souffle.
        Les conditions vont te tester : vise la régularité plutôt que la vitesse.
        C’est une course de maîtrise, pas de bravoure.
        Reste solide, reste stable, et tu traverseras cette zone sans te cramer.
        """, "#FFD54F", "🟡 Conditions difficiles"
    
        else:
            return """
        Météo hostile : adapte tout, allure, respiration, ambition.
        Aujourd’hui, l’objectif n’est pas le chrono, mais la résistance.
        Chaque kilomètre est un combat, avance avec humilité.
        Protège ton corps, garde la tête froide, et reste maître de ton effort.
        C’est une course de survivant : tu t’adaptes, tu encaisses, tu progresses.
        """, "#FF0080", "🔴 Conditions extrêmes"


    import plotly.graph_objects as go

    st.title("🔮 Prédiction de performance")
    
    # --- Charger GPS ici aussi ---
    gps = pd.read_csv("gps_points.csv")

    # --- Récupération de l'activité sélectionnée ---
    selected_activity = st.session_state.get("selected_activity", None)
    if selected_activity is None:
        st.error("Aucune activité sélectionnée depuis la page principale.")
        st.stop()

    # --- Bouton Reset ML ---
    if st.button("🔄 Reset ML", key="btn_reset_ml"):
        st.session_state["selected_activity"] = None
        st.session_state["temp_slider"] = 0
        st.session_state["wind_slider"] = 0
        st.session_state["rh_slider"] = 0
        st.session_state["precip_slider"] = 0
        st.session_state["cloud_slider"] = 0
        st.session_state["ml_reset"] = True
        st.rerun()

    if st.session_state.get("ml_reset", False):
        st.info("🔄 ML réinitialisé.")
        st.session_state["ml_reset"] = False
        st.stop()

    # --- Calcul ML ---
    st.success(f"Course sélectionnée : {selected_activity['start_date_local']}")

    speed_ml, time_ml = predict_time(
        selected_activity["distance_km"],
        selected_activity["temp_mean"],
        selected_activity["rh_mean"],
        selected_activity["precip_mean"],
        selected_activity["cloud_mean"],
        selected_activity["wind_mean"],
        selected_activity["month"],
        selected_activity["hour"],
        selected_activity["total_elevation_gain"]
    )

    allure_ml = 60 / speed_ml
    bpm_increase = meteo_heart_rate(
        selected_activity["temp_mean"],
        selected_activity["rh_mean"],
        selected_activity["wind_mean"]
    )

    heartrate_ml = selected_activity["average_heartrate"] - bpm_increase
    corrected_hr = heartrate_ml + bpm_increase

    penalty = meteo_penalty(
        selected_activity["temp_mean"],
        selected_activity["rh_mean"],
        selected_activity["wind_mean"],
        selected_activity["precip_mean"]
    )

    corrected_time = time_ml * (1 + penalty / 100)
    corrected_speed = speed_ml * (1 - penalty / 100)
    corrected_allure = 60 / corrected_speed

    # --- Réel ---
    real_allure = selected_activity["allure_min_km"]
    real_speed = selected_activity["vitesse_kmh"]
    real_hr = selected_activity["average_heartrate"]
    real_time = selected_activity["duration_min"]

    # --- % variations ---
    allure_pct = ((corrected_allure - real_allure) / real_allure) * 100
    speed_pct = ((corrected_speed - real_speed) / real_speed) * 100
    hr_pct = ((corrected_hr - real_hr) / real_hr) * 100 if pd.notna(real_hr) else 0
    time_pct = ((corrected_time - real_time) / real_time) * 100

    # -----------------------------
    # AFFICHAGE DES STATS
    # -----------------------------
    st.markdown(
        f"""
        ### 🌦️ Conditions météo du jour
        - Distance : **{selected_activity['distance_km']:.1f} km**

        - Allure corrigée : **{corrected_allure:.2f} min/km**  
          ↳ Variation : {color_pct(allure_pct, "allure")}

        - Vitesse corrigée : **{corrected_speed:.2f} km/h**  
          ↳ Variation : {color_pct(speed_pct, "vitesse")}

        - Cardio corrigé : **{corrected_hr:.0f} BPM**  
          ↳ Variation : {color_pct(hr_pct, "cardio")}

        - Temps corrigé : **{corrected_time:.1f} min**  
          ↳ Variation : {color_pct(time_pct, "temps")}
        """,
        unsafe_allow_html=True
    )

    # -----------------------------
    # IMPACT MÉTÉO
    # -----------------------------
    delta_allure = -allure_pct
    delta_speed = speed_pct
    delta_hr = -hr_pct
    delta_time = -time_pct

    impact_meteo = (
        delta_allure * 0.4 +
        delta_speed * 0.3 +
        delta_hr * 0.2 +
        delta_time * 0.1
    )

    color = folium_color(impact_meteo)

    # -----------------------------
    # CARTE ML
    # -----------------------------
    gps_run = gps[gps["activity_id"] == selected_activity["activity_id"]].dropna()
    gps_run = gps_run.iloc[::3]
    coords = gps_run[["lat", "lon"]].dropna().values.tolist()

    if len(coords) < 2:
        st.warning("⚠️ Impossible d'afficher la carte : pas assez de points GPS.")
    else:
        carte_ml = folium.Map(
            location=[coords[0][0], coords[0][1]],
            zoom_start=13
        )

        for i in range(len(coords) - 1):
            folium.PolyLine(
                [coords[i], coords[i+1]],
                color=color,
                weight=6,
                opacity=0.9
            ).add_to(carte_ml)

        html_ml = carte_ml._repr_html_()
        st.components.v1.html(html_ml, height=600)

    # -----------------------------
    # 📊 COMPARAISON RÉEL vs CORRIGÉ
    # -----------------------------
    st.subheader("📊 Comparaison Réel vs Corrigé")

    real_hr_safe = real_hr if pd.notna(real_hr) else 0
    corrected_hr_safe = corrected_hr if pd.notna(corrected_hr) else 0

    fig_compare = go.Figure()

    fig_compare.add_trace(go.Bar(
        name="Réel",
        x=[real_allure, real_speed, real_hr_safe, real_time],
        y=["Allure (min/km)", "Vitesse (km/h)", "Cardio (BPM)", "Temps (min)"],
        orientation='h',
        marker_color="#4FC3F7"
    ))

    fig_compare.add_trace(go.Bar(
        name="Corrigé",
        x=[corrected_allure, corrected_speed, corrected_hr_safe, corrected_time],
        y=["Allure (min/km)", "Vitesse (km/h)", "Cardio (BPM)", "Temps (min)"],
        orientation='h',
        marker_color="#E57373"
    ))

    fig_compare.update_layout(
        barmode='group',
        height=400,
        template="plotly_dark",
        title="Comparaison des métriques"
    )

    st.plotly_chart(fig_compare, use_container_width=True)

    # -----------------------------
    # 📈 GRAPHIQUE RÉEL vs ML
    # -----------------------------
    fig_compare_stats = go.Figure()

    fig_compare_stats.add_trace(go.Bar(
        name="Réel",
        x=[real_allure, real_speed, real_hr_safe, real_time],
        y=["Allure", "Vitesse", "Cardio", "Temps"],
        orientation='h',
        marker_color="#4FC3F7"
    ))

    fig_compare_stats.add_trace(go.Bar(
        name="ML Corrigé",
        x=[corrected_allure, corrected_speed, corrected_hr_safe, corrected_time],
        y=["Allure", "Vitesse", "Cardio", "Temps"],
        orientation='h',
        marker_color="#E57373"
    ))

    fig_compare_stats.update_layout(
        barmode='group',
        height=350,
        template="plotly_dark",
        title="Comparaison Réel vs ML"
    )

    st.plotly_chart(fig_compare_stats, use_container_width=True)

    # -----------------------------
    # 🕸️ RADAR : RÉEL vs CORRIGÉ
    # -----------------------------
    st.subheader("🕸️ Radar : Réel vs Corrigé")

    categories = ["Allure", "Vitesse", "Cardio", "Temps"]

    real_values = [
        real_allure,
        real_speed,
        real_hr_safe,
        real_time
    ]

    corrected_values = [
        corrected_allure,
        corrected_speed,
        corrected_hr_safe,
        corrected_time
    ]

    fig_radar = go.Figure()

    fig_radar.add_trace(go.Scatterpolar(
        r=real_values,
        theta=categories,
        fill='toself',
        name='Réel',
        line_color="#4FC3F7"
    ))

    fig_radar.add_trace(go.Scatterpolar(
        r=corrected_values,
        theta=categories,
        fill='toself',
        name='Corrigé',
        line_color="#E57373"
    ))

    fig_radar.update_layout(
        polar=dict(
            bgcolor="#111",
            radialaxis=dict(visible=True)
        ),
        template="plotly_dark",
        height=450
    )

    st.plotly_chart(fig_radar, use_container_width=True)

    # -----------------------------
    # SCORE GLOBAL
    # -----------------------------
    score_allure = max(0, 100 - abs(allure_pct) * 4)
    score_speed  = max(0, 100 - abs(speed_pct) * 3)
    score_hr     = max(0, 100 - abs(hr_pct) * 2)
    score_time   = max(0, 100 - abs(time_pct) * 1)

    score_global = (
        score_allure * 0.4 +
        score_speed  * 0.3 +
        score_hr     * 0.2 +
        score_time   * 0.1
    )

    score_global = 50 + impact_meteo
    score_global = max(0, min(100, score_global))

    st.markdown(
        f"""
        <div style="
            background-color:#222;
            padding:20px;
            border-radius:10px;
            border:1px solid #444;
            margin-top:20px;
            text-align:center;
        ">
            <h3 style="color:#4FC3F7;">📊 Score global de performance</h3>
            <p style="font-size:40px; color:white; margin:0;">
                <strong>{score_global:.0f}/100</strong>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # -----------------------------
    # 🔥 SCORE MÉTÉO DJ MARCLJR
    # -----------------------------
    st.subheader("🎧 DJ MARCLJR — Score Météo Dynamique")

    score_meteo = 100

    # Température idéale : 10–14°C
    score_meteo -= abs(selected_activity["temp_mean"] - 12) * 2

    # Vent
    score_meteo -= selected_activity["wind_mean"] * 1.5

    # Humidité
    score_meteo -= selected_activity["rh_mean"] * 0.3

    # Précipitations
    score_meteo -= selected_activity["precip_mean"] * 5
    
    
    score_meteo = max(0, min(100, abs(impact_meteo)))


if score_meteo >= 80:
    dj_mood = "🔥 Conditions parfaites — T'es en mode Ultra Boost"
    dj_color = "#00FFAA"
elif score_meteo >= 60:
    dj_mood = "🎶 Conditions correctes — Allez garde le rythme !! "
    dj_color = "#4FC3F7"
elif score_meteo >= 40:
    dj_mood = "⚡ Conditions difficiles — Passe en mode survie"
    dj_color = "#FFD54F"
else:
    dj_mood = "💀 Conditions extrêmes — T'es en mode Apocalypse"
    dj_color = "#FF0080"


    st.markdown(
        f"""
        <div style="
            background: linear-gradient(90deg, {dj_color}, #7928ca);
            padding: 18px;
            border-radius: 12px;
            margin-top: 20px;
            color: white;
            font-size: 22px;
            font-weight: bold;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        ">
            🎧 DJ MARCLJR — Score météo : {score_meteo:.0f}/100  
            <span style="font-size:18px; font-weight:normal;">{dj_mood}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    fig_dj = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score_meteo,
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': dj_color},
            'steps': [
                {'range': [0, 40], 'color': "#FF0080"},
                {'range': [40, 60], 'color': "#FFD54F"},
                {'range': [60, 80], 'color': "#4FC3F7"},
                {'range': [80, 100], 'color': "#00FFAA"},
            ],
        },
        number={'suffix': "/100"},
    ))

    fig_dj.update_layout(height=300, template="plotly_dark")
    st.plotly_chart(fig_dj, use_container_width=True)
# -----------------------------
# 🧢 COACH MODE 2.0
# -----------------------------
coach_phrase, coach_color, coach_label = get_coach_phrase(score_meteo)

st.markdown(f"""
<div style="
    background: linear-gradient(135deg, #111, #1e1e1e, #111);
    padding: 25px;
    border-radius: 16px;
    border: 2px solid {coach_color};
    margin-top: 25px;
    box-shadow: 0 0 18px rgba(0,0,0,0.45);
">
    <div style="display:flex; align-items:center; gap:12px;">
        <div style="
            background-color:{coach_color};
            width:55px;
            height:55px;
            border-radius:50%;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:28px;
        ">🧢</div>{coach_phrase}

</div>
""", unsafe_allow_html=True)


    

    # --- Bouton Retour ---
if st.button("⬅️ Retour"):
        st.session_state.page = "home"
        



# pour lancer streamlit : streamlit run app.py
