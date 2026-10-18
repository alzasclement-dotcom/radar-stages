"""Calcul deterministe du score d'adequation (0 a 100) d'une offre."""
import re
import unicodedata
from datetime import date

METIER_POINTS = {"allocation": 40, "banque_privee": 32, "asset_management": 28}
NIVEAU_POINTS = {"m1_accepte": 15, "non_precise": 8, "m2_exige": 0}
COMPETENCES = ("excel_vba_python", "relation_patrimoniale", "assurance_vie", "marches")
COMPETENCES_POINTS = {0: 0, 1: 4, 2: 7, 3: 10, 4: 10}

FENETRE_DEBUT = date(2026, 12, 15)
FENETRE_FIN = date(2027, 2, 28)
REGIONS_PREFEREES = {"ile-de-france", "occitanie"}


def normaliser(texte):
    """Minuscules, sans accents, espaces/ponctuation ramenes a un tiret."""
    s = unicodedata.normalize("NFKD", str(texte or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def parse_date(valeur):
    """AAAA-MM-JJ ou AAAA-MM (mois seul = le 15). None si absente ou illisible."""
    if not valeur:
        return None
    m = re.fullmatch(r"(\d{4})-(\d{2})(?:-(\d{2}))?", str(valeur).strip())
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3] or 15))
    except ValueError:
        return None


def points_date(offre):
    debut = parse_date(offre.get("date_debut"))
    if debut is None:
        return 10
    if FENETRE_DEBUT <= debut <= FENETRE_FIN:
        return 20 if offre.get("duree") in (5, 6) else 14
    return 5


def points_lieu(offre):
    return 15 if normaliser(offre.get("region")) in REGIONS_PREFEREES else 6


def points_competences(offre):
    n = len({c for c in offre.get("competences", []) if c in COMPETENCES})
    return COMPETENCES_POINTS[n]


def detail_score(offre):
    return {
        "metier": METIER_POINTS.get(offre.get("metier"), 0),
        "date": points_date(offre),
        "niveau": NIVEAU_POINTS.get(offre.get("niveau"), 0),
        "lieu": points_lieu(offre),
        "competences": points_competences(offre),
    }


def calculer_score(offre):
    return sum(detail_score(offre).values())
