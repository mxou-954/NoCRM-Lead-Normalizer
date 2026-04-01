# noCRM Lead Normalizer

Script Python qui récupère les leads d'une étape de pipeline **noCRM.io**, envoie leur description brute à **ChatGPT (GPT-4o-mini)** pour la reformater, puis met à jour les fiches directement dans le CRM.

Les leads déjà normalisés sont automatiquement détectés et ignorés.

---

## Fonctionnement

1. **Récupération paginée** des leads d'une étape (`STEP_ID`) via l'API noCRM
2. **Détection** des leads déjà normalisés (présence de plus de 4 séparateurs `------`) → ignorés
3. **Reformatage** par ChatGPT : la description brute est envoyée avec un prompt strict qui produit une fiche structurée entreprise + contacts
4. **Mise à jour** de la description du lead dans noCRM via `PUT /leads/{id}`
5. **Résumé** en console : leads normalisés / ignorés / en erreur

---

## Format de sortie (fiche normalisée)

```
SIRET : 123 456 789 00012
NAF : 4941A - Transports routiers de fret
Effectif : 50-99 salariés
Adresse : 12 rue de la Paix, 75001 Paris
Chiffre d'affaire : 8 500 000 €
Résultat net : 320 000 €
Site web : https://www.exemple.fr
Description : Entreprise spécialisée dans le transport frigorifique...
Téléphone accueil : +33 1 23 45 67 89
----------
Nom : Frédéric Mignon
Fonction : Chief Financial Officer
Téléphone : +33 3 80 44 71 63
Email : f.mignon@urgo.fr
Source : https://www.linkedin.com/in/frederic-m-01962710/
----------
Nom : Luca Vascotto
Fonction : International Finance Manager
Téléphone : +33 7 86 60 84 80
Email : Non communiqué
Source : https://www.linkedin.com/in/luca-vascotto-02590139/
```

---

## Prérequis

- Python 3.8+
- Un compte **noCRM.io** avec accès API
- Une clé API **OpenAI**

### Dépendances

```bash
pip install requests python-dotenv
```

---

## Configuration

Créer un fichier `.env` à la racine :

```env
NOCRM_API_KEY=''
NOCRM_SUBDOMAIN=''
OPENAI_API_KEY=''
OPENAI_MODEL=gpt-4o-mini
```

| Variable          | Description                                                              |
|-------------------|--------------------------------------------------------------------------|
| `NOCRM_API_KEY`   | Clé API noCRM (paramètres du compte)                                     |
| `NOCRM_SUBDOMAIN` | Sous-domaine noCRM (ex : `monentreprise` pour `monentreprise.nocrm.io`) |
| `OPENAI_API_KEY`  | Clé API OpenAI                                                           |
| `OPENAI_MODEL`    | Modèle à utiliser (défaut : `gpt-4o-mini`)                              |

Puis dans le script, configurer l'étape cible :

```python
STEP_ID = 45996  # ID de l'étape de pipeline à normaliser
```

---

## Utilisation

```bash
python nocrm_normalizer.py
```

### Exemple de sortie console

```
============================================================
  noCRM Lead Normalizer
  Étape de pipeline : 45996
  Modèle ChatGPT   : gpt-4o-mini
============================================================

Récupération des opportunités...
   → 24 opportunité(s) trouvée(s)

── [1/24] Urgo Group (ID: 1082345)
Envoi à ChatGPT...
   ✅ Reformatage reçu (612 caractères)
Mise à jour dans noCRM...
Lead mis à jour avec succès

── [2/24] Vascotto Logistics (ID: 1082346)
Déjà normalisée (>4 séparateurs trouvés) → skip
...

============================================================
  RÉSUMÉ
============================================================
Normalisées  : 20
Ignorées     : 4
Erreurs      : 0
Total        : 24
============================================================
```

---

## Structure du projet

```
.
├── nocrm_normalizer.py
├── .env
└── README.md
```

---

## Notes

- Une pause de 0.5 s est appliquée entre chaque lead pour respecter les rate-limits des deux APIs.
- Les éventuels blocs markdown (` ``` `) dans la réponse de ChatGPT sont nettoyés automatiquement.
- La détection "déjà normalisé" repose sur le comptage des lignes contenant `------` : au-delà de 4, le lead est ignoré.
