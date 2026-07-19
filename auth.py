import os
import requests
from dotenv import load_dotenv, set_key

def refresh_tokens():
    """
    Rafraîche les tokens Strava (access_token et refresh_token).
    - Charge .env
    - Lit client_id, client_secret, refresh_token
    - Envoie la requête OAuth à Strava
    - Vérifie la réponse
    - Met à jour le refresh_token dans .env
    - Retourne (access_token, refresh_token)
    """

    # Charger .env à chaque appel pour toujours lire les valeurs à jour
    load_dotenv()

    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")
    refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")
    
    print("client_id =", client_id)
    print("client_secret =", client_secret)
    print("refresh_token =", refresh_token)

    # Vérification des préconditions
    if not client_id or not client_secret or not refresh_token:
        raise ValueError("client_id, client_secret ou refresh_token manquant dans .env")

    # Construire la requête OAuth
    url = "https://www.strava.com/oauth/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    # Appel API
    response = requests.post(url, data=data)

    # Vérification du code HTTP
    if response.status_code != 200:
        raise RuntimeError(f"Erreur OAuth Strava : {response.status_code} — {response.text}")

    tokens = response.json()

    # Vérification des clés attendues
    if "access_token" not in tokens or "refresh_token" not in tokens:
        raise KeyError("Réponse Strava invalide : clés manquantes dans le JSON")

    new_access_token = tokens["access_token"]
    new_refresh_token = tokens["refresh_token"]

    # Mise à jour du refresh_token dans .env
    set_key(".env", "STRAVA_REFRESH_TOKEN", new_refresh_token)

    # Retourner les deux tokens
    return new_access_token, new_refresh_token


