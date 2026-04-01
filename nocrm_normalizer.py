"""
noCRM Lead Normalizer
=====================
Récupère les opportunités de l'étape de pipeline 45996,
envoie le texte à ChatGPT pour reformater, puis met à jour noCRM.

Les opportunités déjà normalisées (contenant plus de 4 "------" consécutifs)
sont automatiquement ignorées.

Usage:
    1. Renseigne tes clés dans le fichier .env ou en variables d'environnement
    2. Lance : python nocrm_normalizer.py
"""

import os
import sys
import time
import requests
from dotenv import load_dotenv

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
load_dotenv()

NOCRM_API_KEY = os.getenv("NOCRM_API_KEY", "")
NOCRM_SUBDOMAIN = os.getenv("NOCRM_SUBDOMAIN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

STEP_ID = 45996
LEADS_PER_PAGE = 100
SEPARATOR = "----------"

NOCRM_BASE = f"https://{NOCRM_SUBDOMAIN}.nocrm.io/api/v2"
NOCRM_HEADERS = {
    "X-API-KEY": NOCRM_API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json",
}

# ──────────────────────────────────────────────
# Prompt ChatGPT
# ──────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es un assistant spécialisé dans le reformatage de fiches entreprise pour un CRM commercial (transport / logistique).

On va te donner le texte brut d'une opportunité commerciale. Tu dois extraire et réorganiser TOUTES les informations disponibles dans le format ci-dessous.

FORMAT OBLIGATOIRE :

SIRET : [valeur ou "Non communiqué"]
NAF : [valeur ou "Non communiqué"]
Effectif : [valeur ou "Non communiqué"]
Adresse : [valeur ou "Non communiqué"]
Chiffre d'affaire : [valeur ou "Non communiqué"]
Résultat net : [valeur ou "Non communiqué"]
Site web : [valeur ou "Non communiqué"]
Description : [résumé de l'activité de l'entreprise, ses besoins en transport, budget transport si disponible. Si rien n'est trouvé : "Non communiqué"]
Téléphone accueil : [valeur ou "Non communiqué"]
----------
Nom : [Nom du contact 1]
Fonction : [valeur ou "Non communiqué"]
Téléphone : [valeur ou "Non communiqué"]
Email : [valeur ou "Non communiqué"]
Source : [valeur ou "Non communiqué"]
----------
Nom : [Nom du contact 2, si présent]
Fonction : [valeur ou "Non communiqué"]
Téléphone : [valeur ou "Non communiqué"]
Email : [valeur ou "Non communiqué"]
Source : [valeur ou "Non communiqué"]

RÈGLES :
- S'il y a plusieurs contacts, répète le bloc contact séparé par "----------" (10 tirets).
- S'il n'y a qu'un seul contact, ne mets qu'un seul bloc contact après le premier "----------".
- Si une information n'est pas trouvée dans le texte, mets "Non communiqué".
- Ne modifie PAS les données (numéros, emails, montants…), recopie-les tels quels.
- Ne rajoute aucun commentaire, explication ou texte superflu. Retourne UNIQUEMENT la fiche reformatée.
- Le séparateur entre la partie entreprise et les contacts est TOUJOURS "----------" (exactement 10 tirets).
- Retourne le résultat en texte brut (pas de blocs de code markdown comme ```).
"""


def validate_config():
    """Vérifie que toutes les variables d'environnement sont renseignées."""
    missing = []
    if not NOCRM_API_KEY:
        missing.append("NOCRM_API_KEY")
    if not NOCRM_SUBDOMAIN:
        missing.append("NOCRM_SUBDOMAIN")
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if missing:
        print(f"Variables manquantes : {', '.join(missing)}")
        print("   Crée un fichier .env avec ces valeurs ou exporte-les.")
        sys.exit(1)


def is_already_normalized(description: str) -> bool:
    """
    Retourne True si l'opportunité contient plus de 4 séquences
    de 6+ tirets consécutifs (------), signe qu'elle est déjà normalisée.
    """
    if not description:
        return False
    count = 0
    for line in description.split("\n"):
        stripped = line.strip()
        if "------" in stripped:
            count += 1
    return count > 4


def fetch_leads_for_step(step_id: int) -> list:
    """Récupère toutes les opportunités de l'étape donnée (avec pagination)."""
    all_leads = []
    offset = 0

    while True:
        url = f"{NOCRM_BASE}/leads"
        params = {
            "step_id": step_id,
            "limit": LEADS_PER_PAGE,
            "offset": offset,
        }
        print(f"Récupération des leads (offset={offset})...")
        resp = requests.get(url, headers=NOCRM_HEADERS, params=params)
        resp.raise_for_status()

        leads = resp.json()
        if not leads:
            break

        all_leads.extend(leads)

        # Si on a reçu moins que la limite, c'est la dernière page
        if len(leads) < LEADS_PER_PAGE:
            break

        offset += LEADS_PER_PAGE
        time.sleep(0.3)  # Respecter le rate-limit noCRM

    return all_leads


def normalize_with_chatgpt(raw_text: str) -> str:
    """Envoie le texte brut à ChatGPT et retourne la fiche normalisée."""
    payload = {
        "model": OPENAI_MODEL,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": raw_text},
        ],
    }

    resp = requests.post(OPENAI_URL, headers=OPENAI_HEADERS, json=payload)
    resp.raise_for_status()
    data = resp.json()

    content = data["choices"][0]["message"]["content"].strip()

    # Nettoyer les éventuels blocs de code markdown
    if content.startswith("```"):
        lines = content.split("\n")
        # Retirer la première et dernière ligne (``` ... ```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines).strip()

    return content


def update_lead_description(lead_id: int, new_description: str) -> dict:
    """Met à jour la description d'un lead dans noCRM."""
    url = f"{NOCRM_BASE}/leads/{lead_id}"
    payload = {"description": new_description}

    resp = requests.put(url, headers=NOCRM_HEADERS, json=payload)
    resp.raise_for_status()
    return resp.json()


def main():
    validate_config()

    print("=" * 60)
    print("  noCRM Lead Normalizer")
    print(f"  Étape de pipeline : {STEP_ID}")
    print(f"  Modèle ChatGPT   : {OPENAI_MODEL}")
    print("=" * 60)

    print("\nRécupération des opportunités...")
    leads = fetch_leads_for_step(STEP_ID)
    print(f"   → {len(leads)} opportunité(s) trouvée(s)\n")

    if not leads:
        print("Aucune opportunité à traiter.")
        return

    # Compteurs
    normalized_count = 0
    skipped_count = 0
    error_count = 0

    for i, lead in enumerate(leads, 1):
        lead_id = lead["id"]
        title = lead.get("title", "Sans titre")
        description = lead.get("description", "") or ""

        print(f"── [{i}/{len(leads)}] {title} (ID: {lead_id})")

        if is_already_normalized(description):
            print(f"Déjà normalisée (>4 séparateurs trouvés) → skip")
            skipped_count += 1
            continue

        if not description.strip():
            print(f"Description vide → skip")
            skipped_count += 1
            continue

        try:
            print(f"Envoi à ChatGPT...")
            new_description = normalize_with_chatgpt(description)
            print(f"   ✅ Reformatage reçu ({len(new_description)} caractères)")
        except requests.exceptions.RequestException as e:
            print(f"Erreur ChatGPT : {e}")
            error_count += 1
            continue

        # 4. Mettre à jour dans noCRM
        try:
            print(f"Mise à jour dans noCRM...")
            update_lead_description(lead_id, new_description)
            print(f"Lead mis à jour avec succès")
            normalized_count += 1
        except requests.exceptions.RequestException as e:
            print(f"Erreur noCRM : {e}")
            error_count += 1
            continue

        # Pause entre chaque lead pour respecter les rate-limits
        time.sleep(0.5)

    # Résumé final
    print("\n" + "=" * 60)
    print("  RÉSUMÉ")
    print("=" * 60)
    print(f"Normalisées  : {normalized_count}")
    print(f"Ignorées     : {skipped_count}")
    print(f"Erreurs      : {error_count}")
    print(f"Total        : {len(leads)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
