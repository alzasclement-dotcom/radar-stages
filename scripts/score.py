"""Calcul deterministe du score d'adequation (0 a 100) d'une offre.

Bareme : accessibilite 30 + metier 25 + fraicheur 15 + date de debut 15 + lieu 10 + competences 5.
"""
import re
import unicodedata
from datetime import date

METIER_POINTS = {
    "sales_ir": 25,            # sales / investor relations / partenariats CGP / distribution externe
    "allocation": 25,          # allocation, gestion pilotee, conseil en investissement
    "patrimoine": 22,          # gestion de patrimoine, CGP, banque privee regionale
    "asset_management": 18,    # distribution, middle office, analyse en societe de gestion
    "epargne_assurance": 15,   # epargne et assurance vie en agence
}
NIVEAUX = ("bac3_4", "bac4_5", "non_precise")  # bac3_4 : Bac+3 ou Bac+4 accepte
FAMILLES = (
    "plateforme_investissement", "fintech", "reseau_bancaire", "cgp",
    "assurance", "gestion_patrimoniale", "autre",
)
COMPETENCES = ("excel_vba_python", "relation_patrimoniale", "assurance_vie", "marches")
COMPETENCES_POINTS = {0: 0, 1: 2, 2: 3, 3: 4, 4: 5}

DEBUT_MIN = date(2026, 11, 15)
DEBUT_MAX = date(2027, 2, 28)
DUREES_OK = range(6, 10)  # 6 a 9 mois
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


def points_accessibilite(offre):
    if offre.get("ambitieuse"):
        return 0
    if offre.get("niveau") == "bac3_4" or offre.get("famille") != "autre":
        return 30
    return 15


def age_jours(offre, aujourdhui):
    pub = parse_date(offre.get("date_publication"))
    return None if pub is None else (aujourdhui - pub).days


def points_fraicheur(offre, aujourdhui):
    age = age_jours(offre, aujourdhui)
    if age is None:
        return 4
    if age < 7:
        return 15
    if age < 14:
        return 11
    if age < 30:
        return 7
    return 2


def points_date(offre):
    debut = parse_date(offre.get("date_debut"))
    if debut is None:
        return 7
    if DEBUT_MIN <= debut <= DEBUT_MAX:
        return 15 if offre.get("duree") in DUREES_OK else 10
    return 3


def points_lieu(offre):
    return 10 if normaliser(offre.get("region")) in REGIONS_PREFEREES else 4


def points_competences(offre):
    n = len({c for c in offre.get("competences", []) if c in COMPETENCES})
    return COMPETENCES_POINTS[n]


def detail_score(offre, aujourdhui=None):
    aujourdhui = aujourdhui or date.today()
    return {
        "accessibilite": points_accessibilite(offre),
        "metier": METIER_POINTS.get(offre.get("metier"), 0),
        "fraicheur": points_fraicheur(offre, aujourdhui),
        "date": points_date(offre),
        "lieu": points_lieu(offre),
        "competences": points_competences(offre),
    }


def calculer_score(offre, aujourdhui=None):
    return sum(detail_score(offre, aujourdhui).values())
