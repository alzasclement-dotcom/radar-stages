# Radar Stages

Page statique listant les offres de stage (janvier 2027) adaptées au profil décrit dans [`profil.md`](profil.md). Mise à jour chaque matin par un agent Claude qui suit [`MISE_A_JOUR.md`](MISE_A_JOUR.md).

- `index.html` : la page (aucune dépendance).
- `data/offres.json` : les offres, le journal et la date de mise à jour.
- `scripts/score.py` : calcul du score. `scripts/valider.py` : schéma, doublons, scores, tri.
- `tests/` : `python -m unittest discover -s tests`.
- `.github/workflows/pages.yml` : tests, validation, déploiement GitHub Pages à chaque push sur `main`.

Pour voir la page en local : `python -m http.server 8123` puis http://localhost:8123.

Aucune clé API dans ce dépôt.
