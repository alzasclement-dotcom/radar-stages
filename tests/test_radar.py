import copy
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import valider  # noqa: E402
from score import calculer_score, detail_score, parse_date  # noqa: E402

AUJ = date(2026, 10, 19)


def offre(**kw):
    base = {
        "titre": "Stage Sales Investor Relations", "entreprise": "Exemple Invest", "famille": "plateforme_investissement",
        "ambitieuse": False, "ville": "Montpellier", "region": "Occitanie", "metier": "sales_ir",
        "date_debut": "2026-11-30", "duree": 6, "niveau": "bac3_4",
        "competences": ["excel_vba_python", "marches", "assurance_vie", "relation_patrimoniale"],
        "pourquoi": "p", "vigilance": "v", "angle": "a", "url": "https://exemple.test/offre/1",
        "type_source": "officielle", "date_publication": "2026-10-17", "date_estimee": False,
        "premiere_detection": "2026-10-19", "derniere_verification": "2026-10-19", "statut": "active",
        "deja_postule": False,
    }
    base.update(kw)
    return base


def donnees(*offres, journal=None):
    return {"derniere_mise_a_jour": "2026-10-19", "journal": journal or [], "offres": list(offres)}


class TestScore(unittest.TestCase):
    def d(self, **kw):
        return detail_score(offre(**kw), AUJ)

    def test_score_maximal(self):
        self.assertEqual(calculer_score(offre(), AUJ), 100)

    def test_accessibilite(self):
        self.assertEqual(self.d()["accessibilite"], 30)
        self.assertEqual(self.d(ambitieuse=True)["accessibilite"], 0)
        self.assertEqual(self.d(famille="autre", niveau="bac4_5")["accessibilite"], 15)
        self.assertEqual(self.d(famille="autre", niveau="bac3_4")["accessibilite"], 30)
        self.assertEqual(self.d(famille="cgp", niveau="bac4_5")["accessibilite"], 30)

    def test_metiers(self):
        for m, pts in (("sales_ir", 25), ("allocation", 25), ("patrimoine", 22),
                       ("asset_management", 18), ("epargne_assurance", 15)):
            self.assertEqual(self.d(metier=m)["metier"], pts)

    def test_fraicheur(self):
        for pub, pts in (("2026-10-19", 15), ("2026-10-13", 15), ("2026-10-12", 11), ("2026-10-06", 11),
                         ("2026-10-05", 7), ("2026-09-20", 7), ("2026-09-19", 2), (None, 4)):
            self.assertEqual(self.d(date_publication=pub)["fraicheur"], pts, pub)

    def test_fenetre_dates(self):
        self.assertEqual(self.d(date_debut=None)["date"], 7)
        self.assertEqual(self.d(date_debut="2027-01")["date"], 15)
        self.assertEqual(self.d(duree=9)["date"], 15)
        self.assertEqual(self.d(duree=12)["date"], 10)
        self.assertEqual(self.d(duree=None)["date"], 10)
        self.assertEqual(self.d(date_debut="2026-11-14")["date"], 3)
        self.assertEqual(self.d(date_debut="2026-11-15")["date"], 15)
        self.assertEqual(self.d(date_debut="2027-02-28")["date"], 15)
        self.assertEqual(self.d(date_debut="2027-03-01")["date"], 3)

    def test_lieu_et_competences(self):
        self.assertEqual(self.d(region="Île-de-France")["lieu"], 10)
        self.assertEqual(self.d(region="Bretagne")["lieu"], 4)
        self.assertEqual(self.d(competences=[])["competences"], 0)
        self.assertEqual(self.d(competences=["marches", "marches"])["competences"], 2)

    def test_parse_date(self):
        self.assertIsNone(parse_date("n'importe quoi"))
        self.assertIsNone(parse_date("2027-13-01"))


class TestValidation(unittest.TestCase):
    def run_norm(self, d):
        return valider.normaliser_donnees(copy.deepcopy(d))

    def test_recalcule_score_et_id(self):
        sortie, err, _ = self.run_norm(donnees(offre(score=1, id="x")))
        self.assertEqual(err, [])
        o = sortie["offres"][0]
        self.assertEqual(o["score"], 100)
        self.assertEqual(o["id"], valider.identifiant(o["url"]))

    def test_id_stable_malgre_suivi_et_slash(self):
        a = valider.identifiant("https://Exemple.test/offre/1/?utm_source=x#top")
        self.assertEqual(a, valider.identifiant("https://exemple.test/offre/1"))

    def test_refuse_sans_url(self):
        o = offre()
        del o["url"]
        _, err, _ = self.run_norm(donnees(o))
        self.assertTrue(any("URL manquante" in e for e in err))

    def test_niveau_m2_refuse(self):
        _, err, _ = self.run_norm(donnees(offre(niveau="m2_exige")))
        self.assertTrue(err)
        for titre in ("Stage M2 Gestion de patrimoine", "Stage de fin d'études - CGP", "Stage Bac+5 Sales", "Stage Master 2 finance"):
            _, err, _ = self.run_norm(donnees(offre(titre=titre)))
            self.assertTrue(any("exclue" in e for e in err), titre)
        _, err, _ = self.run_norm(donnees(offre(titre="Stage Bac+4/5 conseiller patrimonial")))
        self.assertEqual(err, [])

    def test_fenetre_debut_active(self):
        _, err, _ = self.run_norm(donnees(offre(date_debut="2026-11-14")))
        self.assertTrue(err)
        _, err, _ = self.run_norm(donnees(offre(date_debut="2026-11-14", statut="expiree")))
        self.assertEqual(err, [])
        _, err, _ = self.run_norm(donnees(offre(date_debut="2026-11-15")))
        self.assertEqual(err, [])

    def test_doublons(self):
        a = offre()
        b = offre(titre="Autre titre", url="https://exemple.test/offre/1/?utm_campaign=z")
        sortie, err, msgs = self.run_norm(donnees(a, b))
        self.assertEqual(err, [])
        self.assertEqual(len(sortie["offres"]), 1)
        agr = offre(url="https://agregateur.test/x", type_source="agregateur", titre="STAGE sales investor relations")
        sortie, _, _ = self.run_norm(donnees(agr, offre(url="https://exemple.test/offre/9")))
        self.assertEqual([o["type_source"] for o in sortie["offres"]], ["officielle"])

    def test_erreurs_schema(self):
        for kw in ({"metier": "trading"}, {"famille": "x"}, {"statut": "x"}, {"duree": "6"}, {"ambitieuse": "oui"},
                   {"competences": ["magie"]}, {"date_debut": "janvier"}, {"date_publication": "hier"}, {"titre": " "}):
            _, err, _ = self.run_norm(donnees(offre(**kw)))
            self.assertTrue(err, kw)
        o = offre()
        del o["deja_postule"]
        self.assertTrue(self.run_norm(donnees(o))[1])

    def test_tri(self):
        a = offre(url="https://e.test/a", titre="A", metier="asset_management")
        b = offre(url="https://e.test/b", titre="B")
        c = offre(url="https://e.test/c", titre="C", statut="expiree")
        sortie, _, _ = self.run_norm(donnees(a, c, b))
        self.assertEqual([o["titre"] for o in sortie["offres"]], ["B", "A", "C"])

    def test_journal_et_compteur_7_jours(self):
        j = {"date": "2026-10-19", "ajoutees": 2, "expirees": 0, "exclues_niveau_m2": 4,
             "moins_de_7_jours": 99, "sources_inaccessibles": [], "notes": ["exclues : niveau M2"]}
        recente = offre(url="https://e.test/r", titre="R")
        ancienne = offre(url="https://e.test/o", titre="O", date_publication="2026-09-01")
        postulee = offre(url="https://e.test/p", titre="P", deja_postule=True)
        sortie, err, _ = self.run_norm(donnees(recente, ancienne, postulee, journal=[j]))
        self.assertEqual(err, [])
        self.assertEqual(sortie["journal"][0]["moins_de_7_jours"], 1)
        _, err, _ = self.run_norm(donnees(journal=[{"date": "2026-10-19", "ajoutees": 1}]))
        self.assertTrue(err)

    def test_avertissements(self):
        offres = [offre(url=f"https://e.test/{i}", titre=f"T{i}") for i in range(6)]
        _, _, msgs = self.run_norm(donnees(*offres))
        self.assertTrue(any("max 5" in m for m in msgs))
        amb = [offre(ambitieuse=True, url=f"https://e.test/amb{i}", titre=f"Amb{i}") for i in range(2)]
        _, _, msgs = self.run_norm(donnees(*amb, offre(url="https://e.test/x", titre="X")))
        self.assertTrue(any("ambitieuses" in m for m in msgs))

    def test_racine(self):
        self.assertTrue(self.run_norm({"offres": []})[1])

    def test_cli_ecrit_et_check(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "offres.json"
            p.write_text(json.dumps(donnees(offre(score=3))), encoding="utf-8")
            self.assertEqual(valider.main([str(p), "--check"]), 2)
            self.assertEqual(valider.main([str(p)]), 0)
            self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["offres"][0]["score"], 100)
            self.assertEqual(valider.main([str(p), "--check"]), 0)

    def test_fichier_du_depot_valide(self):
        self.assertEqual(valider.main([str(valider.DEFAUT), "--check"]), 0)


if __name__ == "__main__":
    unittest.main()
