import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import valider  # noqa: E402
from score import calculer_score, detail_score, parse_date  # noqa: E402


def offre(**kw):
    base = {
        "titre": "Stage Selection de fonds", "entreprise": "Exemple AM", "ville": "Paris",
        "region": "Île-de-France", "metier": "allocation", "date_debut": "2027-01-04", "duree": 6,
        "niveau": "m1_accepte", "competences": ["excel_vba_python", "marches", "assurance_vie", "relation_patrimoniale"],
        "pourquoi": "p", "vigilance": "v", "angle": "a", "url": "https://exemple.test/offre/1",
        "type_source": "officielle", "date_publication": None, "premiere_detection": "2026-10-19",
        "derniere_verification": "2026-10-19", "statut": "active",
    }
    base.update(kw)
    return base


def donnees(*offres):
    return {"derniere_mise_a_jour": "2026-10-19", "journal": [], "offres": list(offres)}


class TestScore(unittest.TestCase):
    def test_score_maximal(self):
        self.assertEqual(calculer_score(offre()), 100)

    def test_metiers(self):
        self.assertEqual(detail_score(offre(metier="banque_privee"))["metier"], 32)
        self.assertEqual(detail_score(offre(metier="asset_management"))["metier"], 28)

    def test_dates(self):
        self.assertEqual(detail_score(offre(date_debut=None))["date"], 10)
        self.assertEqual(detail_score(offre(date_debut="2027-01"))["date"], 20)
        self.assertEqual(detail_score(offre(duree=4))["date"], 14)
        self.assertEqual(detail_score(offre(date_debut="2027-03-15"))["date"], 5)
        self.assertEqual(detail_score(offre(date_debut="2026-12-14"))["date"], 5)
        self.assertEqual(detail_score(offre(date_debut="2026-12-15"))["date"], 20)
        self.assertEqual(detail_score(offre(date_debut="2027-02-28"))["date"], 20)

    def test_niveau(self):
        self.assertEqual(detail_score(offre(niveau="non_precise"))["niveau"], 8)
        self.assertEqual(detail_score(offre(niveau="m2_exige"))["niveau"], 0)

    def test_lieu(self):
        self.assertEqual(detail_score(offre(region="Occitanie"))["lieu"], 15)
        self.assertEqual(detail_score(offre(region="Ile-de-France"))["lieu"], 15)
        self.assertEqual(detail_score(offre(region="Auvergne-Rhône-Alpes"))["lieu"], 6)

    def test_competences(self):
        self.assertEqual(detail_score(offre(competences=[]))["competences"], 0)
        self.assertEqual(detail_score(offre(competences=["marches"]))["competences"], 4)
        self.assertEqual(detail_score(offre(competences=["marches", "marches"]))["competences"], 4)

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
        _, err, _ = self.run_norm(donnees(offre(url="")))
        self.assertTrue(any("URL manquante" in e for e in err))

    def test_doublon_url(self):
        a = offre()
        b = offre(titre="Autre titre", url="https://exemple.test/offre/1/?utm_campaign=z")
        sortie, err, msgs = self.run_norm(donnees(a, b))
        self.assertEqual(err, [])
        self.assertEqual(len(sortie["offres"]), 1)
        self.assertEqual(len(msgs), 1)

    def test_doublon_entreprise_titre_prefere_officielle(self):
        agr = offre(url="https://agregateur.test/x", type_source="agregateur", titre="STAGE sélection de fonds")
        off = offre(url="https://exemple.test/offre/9", entreprise="exemple am")
        sortie, err, _ = self.run_norm(donnees(agr, off))
        self.assertEqual(err, [])
        self.assertEqual([o["type_source"] for o in sortie["offres"]], ["officielle"])

    def test_erreurs_schema(self):
        for kw in ({"metier": "trading"}, {"niveau": "bac+9"}, {"statut": "x"}, {"duree": "6"},
                   {"competences": ["magie"]}, {"date_debut": "janvier"}, {"titre": " "}):
            _, err, _ = self.run_norm(donnees(offre(**kw)))
            self.assertTrue(err, kw)

    def test_debut_trop_tot_refuse_si_active_toleree_si_expiree(self):
        _, err, _ = self.run_norm(donnees(offre(date_debut="2026-11-02")))
        self.assertTrue(err)
        _, err, _ = self.run_norm(donnees(offre(date_debut="2026-11-02", statut="expiree")))
        self.assertEqual(err, [])

    def test_tri_actives_puis_score(self):
        a = offre(url="https://e.test/a", titre="A", metier="asset_management")
        b = offre(url="https://e.test/b", titre="B")
        c = offre(url="https://e.test/c", titre="C", statut="expiree")
        sortie, _, _ = self.run_norm(donnees(a, c, b))
        self.assertEqual([o["titre"] for o in sortie["offres"]], ["B", "A", "C"])

    def test_racine_et_journal(self):
        _, err, _ = self.run_norm({"offres": []})
        self.assertTrue(err)
        d = donnees()
        d["journal"] = [{"date": "2026-10-19", "ajoutees": 1}]
        _, err, _ = self.run_norm(d)
        self.assertTrue(err)

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
