"""Validation de data/offres.json.

Verifie le schema, refuse toute offre sans URL ou de niveau exclu (M2 / Bac+5 / fin d'etudes),
supprime les doublons (meme URL, ou meme entreprise + titre + ville), recalcule id et score
(la fraicheur est calculee par rapport a `derniere_mise_a_jour`), trie par score.

Usage : python scripts/valider.py [chemin] [--check]
  --check : ne reecrit pas le fichier (echoue s'il faudrait le modifier).
Code de sortie : 0 = ok, 1 = erreurs de schema, 2 = fichier a normaliser (--check).
"""
import hashlib
import json
import math
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score import (COMPETENCES, DEBUT_MIN, FAMILLES, METIER_POINTS, NIVEAUX,  # noqa: E402
                   age_jours, calculer_score, normaliser, parse_date)

DEFAUT = Path(__file__).resolve().parent.parent / "data" / "offres.json"
JOURNAL_MAX = 30
MAX_PAR_EMPLOYEUR = 5
PART_AMBITIEUSES = 0.10

TEXTES = ("titre", "entreprise", "ville", "region", "pourquoi", "vigilance", "angle")
CHAMPS = (
    "id", "titre", "entreprise", "famille", "ambitieuse", "ville", "region", "metier", "date_debut",
    "duree", "niveau", "competences", "score", "pourquoi", "vigilance", "angle", "url", "type_source",
    "date_publication", "date_estimee", "premiere_detection", "derniere_verification", "statut",
    "deja_postule",
)
CALCULES = ("id", "score")
RACINE = ("derniere_mise_a_jour", "journal", "offres")
JOURNAL_CLES = {"date", "ajoutees", "expirees", "exclues_niveau_m2", "moins_de_7_jours", "sources_inaccessibles"}
PARAMS_SUIVI = ("utm_", "fbclid", "gclid", "source", "sourcecode")
NIVEAU_EXCLU = re.compile(r"(?:^|-)(?:m2|bac-5|master-2|master-ii)(?:-|$)|fin-d-etudes")


def normaliser_url(url):
    p = urlsplit(url.strip())
    requete = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
               if not k.lower().startswith(PARAMS_SUIVI)]
    chemin = p.path.rstrip("/") or "/"
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), chemin, urlencode(requete), ""))


def identifiant(url):
    return hashlib.sha1(normaliser_url(url).encode("utf-8")).hexdigest()[:12]


def _date_ok(valeur, mois_ok=False):
    if not isinstance(valeur, str):
        return False
    if mois_ok and len(valeur) == 7:
        return parse_date(valeur) is not None
    return len(valeur) == 10 and parse_date(valeur) is not None


def erreurs_offre(o, etiquette):
    """Liste les problemes de schema d'une offre (sans toucher a id/score)."""
    e = []
    if not isinstance(o, dict):
        return [f"{etiquette}: n'est pas un objet"]
    url = o.get("url")
    if not isinstance(url, str) or not url.strip():
        e.append(f"{etiquette}: URL manquante (offre refusee)")
    elif not url.startswith(("http://", "https://")):
        e.append(f"{etiquette}: URL invalide ({url!r})")
    for k in o:
        if k not in CHAMPS:
            e.append(f"{etiquette}: champ inconnu {k!r}")
    for k in CHAMPS:
        if k not in o and k not in CALCULES:
            e.append(f"{etiquette}: champ manquant {k!r}")
    for k in TEXTES:
        if k in o and not (isinstance(o[k], str) and o[k].strip()):
            e.append(f"{etiquette}: {k} doit etre un texte non vide")
    if o.get("metier") not in METIER_POINTS:
        e.append(f"{etiquette}: metier invalide ({o.get('metier')!r})")
    if o.get("niveau") not in NIVEAUX:
        e.append(f"{etiquette}: niveau invalide ({o.get('niveau')!r}) ; M2 / Bac+5 sont exclus")
    if o.get("famille") not in FAMILLES:
        e.append(f"{etiquette}: famille invalide ({o.get('famille')!r})")
    if o.get("type_source") not in ("officielle", "agregateur"):
        e.append(f"{etiquette}: type_source invalide")
    if o.get("statut") not in ("active", "expiree"):
        e.append(f"{etiquette}: statut invalide")
    for k in ("ambitieuse", "date_estimee", "deja_postule"):
        if k in o and not isinstance(o[k], bool):
            e.append(f"{etiquette}: {k} doit etre un booleen")
    comp = o.get("competences")
    if not isinstance(comp, list) or any(c not in COMPETENCES for c in comp):
        e.append(f"{etiquette}: competences doit etre une liste parmi {list(COMPETENCES)}")
    d = o.get("duree")
    if d is not None and not (isinstance(d, int) and not isinstance(d, bool) and 1 <= d <= 24):
        e.append(f"{etiquette}: duree doit etre un entier de mois (ou null)")
    if o.get("date_debut") is not None and not _date_ok(o["date_debut"], mois_ok=True):
        e.append(f"{etiquette}: date_debut illisible ({o['date_debut']!r})")
    if o.get("date_publication") is not None and not _date_ok(o["date_publication"]):
        e.append(f"{etiquette}: date_publication illisible")
    for k in ("premiere_detection", "derniere_verification"):
        if k in o and not _date_ok(o[k]):
            e.append(f"{etiquette}: {k} doit etre AAAA-MM-JJ")
    debut = parse_date(o.get("date_debut")) if isinstance(o.get("date_debut"), str) else None
    if o.get("statut") == "active" and debut and debut < DEBUT_MIN:
        e.append(f"{etiquette}: debut {o['date_debut']} avant le {DEBUT_MIN} (a ecarter ou passer en expiree)")
    if isinstance(o.get("titre"), str) and NIVEAU_EXCLU.search(normaliser(o["titre"])):
        e.append(f"{etiquette}: titre evoquant M2 / Bac+5 / fin d'etudes : offre exclue")
    return e


def erreurs_racine(data):
    if not isinstance(data, dict):
        return ["racine: doit etre un objet"]
    e = [f"racine: champ manquant {k!r}" for k in RACINE if k not in data]
    e += [f"racine: champ inconnu {k!r}" for k in data if k not in RACINE]
    maj = data.get("derniere_mise_a_jour")
    if maj is not None and not _date_ok(maj):
        e.append("derniere_mise_a_jour doit etre AAAA-MM-JJ ou null")
    if not isinstance(data.get("offres"), list):
        e.append("offres doit etre une liste")
    journal = data.get("journal")
    if not isinstance(journal, list):
        e.append("journal doit etre une liste")
    else:
        for i, j in enumerate(journal):
            ok = (isinstance(j, dict) and JOURNAL_CLES <= set(j) <= JOURNAL_CLES | {"notes"}
                  and _date_ok(j["date"]) and isinstance(j["sources_inaccessibles"], list)
                  and all(isinstance(j[k], int) for k in ("ajoutees", "expirees", "exclues_niveau_m2", "moins_de_7_jours"))
                  and isinstance(j.get("notes", []), list))
            if not ok:
                e.append(f"journal[{i}]: entree invalide (cles attendues : {sorted(JOURNAL_CLES)} + notes facultatif)")
    return e


def cles_doublon(o):
    return (("url", normaliser_url(o["url"])),
            ("titre", normaliser(o["entreprise"]) + "|" + normaliser(o["titre"]) + "|" + normaliser(o["ville"])))


def dedoublonner(offres):
    """Garde une offre par URL / (entreprise, titre) : officielle d'abord, puis la plus ancienne."""
    ordre = sorted(range(len(offres)), key=lambda i: (
        offres[i]["type_source"] != "officielle", offres[i]["premiere_detection"], i))
    vues, gardees, supprimees = set(), [], []
    for i in ordre:
        cles = cles_doublon(offres[i])
        if any(c in vues for c in cles):
            supprimees.append(offres[i])
        else:
            vues.update(cles)
            gardees.append(offres[i])
    return gardees, supprimees


def avertissements(offres, aujourdhui):
    actives = [o for o in offres if o["statut"] == "active"]
    w = []
    par_employeur = Counter(normaliser(o["entreprise"]) for o in actives if not o["ambitieuse"])
    for emp, n in par_employeur.items():
        if n > MAX_PAR_EMPLOYEUR:
            w.append(f"{n} offres actives chez {emp} (max {MAX_PAR_EMPLOYEUR} affichees dans la liste principale)")
    amb = sum(o["ambitieuse"] for o in actives)
    if actives and amb > math.ceil(PART_AMBITIEUSES * len(actives)):
        w.append(f"{amb} offres ambitieuses sur {len(actives)} actives (la page n'en affiche que 10 %)")
    inconnues = sum(o["date_publication"] is None for o in actives)
    if inconnues:
        w.append(f"{inconnues} offre(s) active(s) sans date de publication (estimer et mettre date_estimee=true)")
    return w


def normaliser_donnees(data):
    """Retourne (data normalisee, erreurs, messages). Les erreurs bloquent l'ecriture."""
    erreurs = erreurs_racine(data)
    if erreurs:
        return data, erreurs, []
    messages = []
    for i, o in enumerate(data["offres"]):
        etiq = f"offres[{i}] ({o.get('titre', '?')[:40] if isinstance(o, dict) else '?'})"
        erreurs += erreurs_offre(o, etiq)
    if erreurs:
        return data, erreurs, messages
    aujourdhui = parse_date(data["derniere_mise_a_jour"]) or date.today()
    offres = []
    for o in data["offres"]:
        o = dict(o, id=identifiant(o["url"]))
        o["score"] = calculer_score(o, aujourdhui)
        offres.append({k: o[k] for k in CHAMPS})
    offres, supprimees = dedoublonner(offres)
    for s in supprimees:
        messages.append(f"doublon supprime : {s['entreprise']} - {s['titre']}")
    offres.sort(key=lambda o: (o["statut"] != "active", -o["score"], o["entreprise"], o["titre"]))
    journal = [dict(j) for j in data["journal"]][-JOURNAL_MAX:]
    recentes = sum(1 for o in offres if o["statut"] == "active" and not o["deja_postule"]
                   and (age_jours(o, aujourdhui) is not None) and age_jours(o, aujourdhui) < 7)
    for j in journal:
        if j["date"] == data["derniere_mise_a_jour"]:
            j["moins_de_7_jours"] = recentes
    messages += ["attention : " + w for w in avertissements(offres, aujourdhui)]
    sortie = {"derniere_mise_a_jour": data["derniere_mise_a_jour"], "journal": journal, "offres": offres}
    return sortie, [], messages


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    chemin = Path(args[0]) if args else DEFAUT
    verifier = "--check" in argv
    try:
        data = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERREUR: lecture impossible de {chemin}: {exc}")
        return 1
    sortie, erreurs, messages = normaliser_donnees(data)
    for m in messages:
        print(m)
    if erreurs:
        print(f"{len(erreurs)} erreur(s), fichier non modifie :")
        for e in erreurs:
            print(f"  - {e}")
        return 1
    texte = json.dumps(sortie, ensure_ascii=False, indent=2) + "\n"
    if chemin.read_text(encoding="utf-8") != texte:
        if verifier:
            print("Le fichier n'est pas normalise (scores/ids/doublons/tri) : lancer scripts/valider.py")
            return 2
        chemin.write_text(texte, encoding="utf-8", newline="\n")
        print("fichier normalise et reecrit")
    actives = sum(o["statut"] == "active" for o in sortie["offres"])
    print(f"OK : {actives} active(s), {len(sortie['offres']) - actives} expiree(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
