#!/usr/bin/env python3
"""
MCP Server — Météo Tahiti

Serveur MCP custom utilisant l'API Open-Meteo (gratuite, sans authentification).
Retourne les conditions météo à Puna'auia + évaluation praticabilité outdoor.

Installation :
    pip install mcp httpx

Configuration Cowork (claude_desktop_config.json) :
    "meteo-tahiti": {
        "command": "python",
        "args": ["D:/Documents/Claude/Projects/Project management/Code_test/claude-ai-portfolio/04-cowork-skills/mcp_meteo_tahiti.py"]
    }
"""

import httpx
from mcp.server.fastmcp import FastMCP

# Puna'auia, Tahiti
LAT = -17.601
LON = -149.608

mcp = FastMCP("meteo-tahiti")

# ---------------------------------------------------------------------------
# Correspondances codes météo WMO
# ---------------------------------------------------------------------------

WMO_CODES = {
    0: "Ciel dégagé ☀️",
    1: "Principalement dégagé 🌤",
    2: "Partiellement nuageux ⛅",
    3: "Couvert ☁️",
    45: "Brouillard 🌫",
    48: "Brouillard givrant 🌫",
    51: "Bruine légère 🌦",
    53: "Bruine modérée 🌦",
    55: "Bruine dense 🌧",
    61: "Pluie légère 🌧",
    63: "Pluie modérée 🌧",
    65: "Pluie forte 🌧",
    80: "Averses légères 🌦",
    81: "Averses modérées 🌧",
    82: "Averses violentes ⛈",
    95: "Orage ⛈",
    96: "Orage avec grêle ⛈",
    99: "Orage violent avec grêle ⛈",
}


@mcp.tool()
def get_weather() -> str:
    """
    Retourne les conditions météo actuelles et les prévisions du jour
    à Puna'auia, Tahiti (UTC-10). Indique si trail et lagon sont praticables.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "current": [
            "temperature_2m",
            "rain",
            "weather_code",
            "wind_speed_10m",
            "relative_humidity_2m",
        ],
        "daily": [
            "weather_code",
            "precipitation_sum",
            "precipitation_probability_max",
            "wind_speed_10m_max",
            "temperature_2m_max",
            "temperature_2m_min",
        ],
        "hourly": [
            "precipitation_probability",
            "rain",
        ],
        "timezone": "Pacific/Tahiti",
        "forecast_days": 1,
    }

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        return f"❌ Erreur API Open-Meteo : {exc}"

    current = data["current"]
    daily = data["daily"]
    hourly = data.get("hourly", {})

    # Conditions actuelles
    code_actuel = current["weather_code"]
    desc_actuel = WMO_CODES.get(code_actuel, f"Code WMO {code_actuel}")
    temp = current["temperature_2m"]
    pluie_actuelle = current["rain"]
    vent_actuel = current["wind_speed_10m"]
    humidite = current["relative_humidity_2m"]

    # Prévisions journée
    rain_prob_max = daily["precipitation_probability_max"][0]
    rain_sum = daily["precipitation_sum"][0]
    wind_max = daily["wind_speed_10m_max"][0]
    temp_max = daily["temperature_2m_max"][0]
    temp_min = daily["temperature_2m_min"][0]

    # Prévisions après-midi (heures 13h-17h, index 13-17)
    proba_heures = hourly.get("precipitation_probability", [])
    pluie_heures = hourly.get("rain", [])
    aprem_prob = max(proba_heures[13:18], default=0) if proba_heures else rain_prob_max
    aprem_rain = sum(pluie_heures[13:18]) if pluie_heures else 0

    # ---------------------------------------------------------------------------
    # Évaluation praticabilité outdoor
    # ---------------------------------------------------------------------------

    def evaluer_outdoor(prob, cumul, vent):
        if prob >= 70 or cumul >= 15 or vent >= 40:
            return "❌ Impraticable", "Forte pluie ou vent trop élevé"
        elif prob >= 45 or cumul >= 5:
            return "⚠️ Risqué", "Pluie possible — vérifier avant de partir"
        elif prob >= 25:
            return "🟡 Acceptable", "Risque faible mais réel — emporter une veste"
        else:
            return "✅ Praticable", "Bonnes conditions"

    statut_global, detail_global = evaluer_outdoor(rain_prob_max, rain_sum, wind_max)
    statut_aprem, detail_aprem = evaluer_outdoor(aprem_prob, aprem_rain, wind_max)

    return (
        f"🌤 MÉTÉO PUNA'AUIA — Aujourd'hui\n"
        f"{'─' * 40}\n\n"
        f"État actuel : {desc_actuel}\n"
        f"Température : {temp}°C (min {temp_min}° / max {temp_max}°)\n"
        f"Pluie actuelle : {pluie_actuelle} mm  •  Vent : {vent_actuel} km/h  •  Humidité : {humidite}%\n\n"
        f"Prévisions journée :\n"
        f"  • Probabilité de pluie : {rain_prob_max}%\n"
        f"  • Cumul total prévu : {rain_sum} mm\n"
        f"  • Vent max : {wind_max} km/h\n\n"
        f"Prévisions après-midi (13h–17h) :\n"
        f"  • Probabilité de pluie : {aprem_prob}%\n"
        f"  • Cumul prévu : {aprem_rain:.1f} mm\n\n"
        f"{'─' * 40}\n"
        f"Trail / Lagon (journée) : {statut_global} — {detail_global}\n"
        f"Trail / Lagon (après-midi) : {statut_aprem} — {detail_aprem}\n"
    )


if __name__ == "__main__":
    mcp.run()
