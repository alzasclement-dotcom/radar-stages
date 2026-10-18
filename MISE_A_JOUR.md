# Mise à jour quotidienne de Radar Stages

Tu es l'agent chargé de mettre à jour ce dépôt chaque matin. Ces instructions sont autonomes : ne demande rien à l'utilisateur, décide et agis. Le dépôt est un site statique (`index.html` + `data/offres.json`) publié par GitHub Pages.

## 0. Garde-fous

- N'écris jamais de clé API, mot de passe, nom, e-mail ou téléphone dans le dépôt. Le dépôt est public.
- N'invente jamais une offre, une date ou un lien. Une offre entre dans la liste seulement si tu as ouvert sa page et constaté qu'elle est en ligne. Un extrait de moteur de recherche ne prouve rien.
- Ne scrape rien par script. Utilise la recherche web (WebSearch), la lecture de pages (WebFetch) et, quand un site refuse WebFetch (403), le navigateur intégré de l'app (outils `mcp__Claude_Browser__*`) pour lire la page comme le ferait un utilisateur. Si un site reste inaccessible, ne le contourne pas : note-le dans `sources_inaccessibles`. Ne passe jamais un mur de connexion (authwall).
- Ne modifie pas `index.html`, `scripts/`, `tests/` ni `.github/` sauf demande explicite. Tu ne touches qu'à `data/offres.json`.

## 1. Préparation

1. `git pull --ff-only`, puis lis `profil.md` (critères, règle de niveau, familles de cibles) et `data/offres.json`.
2. Note la date du jour (AAAA-MM-JJ, heure de Paris) : `AUJOURDHUI`.
3. Lance `python scripts/valider.py --check`. Si le fichier est déjà invalide, corrige-le avant toute chose.

## 2. Règle de niveau, avant toute autre étape

Applique `profil.md` § « Règle de niveau » à chaque offre existante et à chaque candidate :
- M2, Bac+5 ou « Bac+5 en cours », « stage de fin d'études » (sauf Bac+4 ou M1 aussi acceptés explicitement), élève-avocat, école d'ingénieur ou de commerce en dernière année : **exclure complètement**. Une offre déjà listée qui s'avère exclue est supprimée (pas archivée) ; compte-la dans `exclues_niveau_m2` du journal et nomme-la dans `notes`.
- Bac+3, Bac+4, Bac+4/5, M1, « à partir de Bac+3 » : garder. Niveau non précisé : garder avec `niveau: "non_precise"`.

## 3. Revérifier les offres déjà listées

Pour chaque offre `statut: "active"` : ouvre son `url`.
- Toujours en ligne : mets `derniere_verification` à `AUJOURDHUI`.
- Plus en ligne (404, redirection vers la liste, « pourvue », « clôturée », début désormais passé) : passe `statut` à `"expiree"` (archive, ne supprime pas) et mets `derniere_verification` à `AUJOURDHUI`.
- Page inaccessible (403, timeout, authwall) : ne change pas le statut, laisse `derniere_verification`, ajoute le domaine à `sources_inaccessibles`.
- Ne repasse jamais une offre expirée en active sauf si sa page est de nouveau en ligne.
- Mets à jour `date_publication` si elle est devenue exacte.

## 4. Chercher de nouvelles offres, les plus récentes d'abord

Cherche d'abord les offres publiées depuis la veille, puis celles des 30 derniers jours. Cible : stage dans le cadre d'un M1, 6 mois (6 à 9 acceptés), début de la mi-novembre 2026 à fin février 2027. Les familles de cibles, les métiers à repérer et les exclusions sont dans `profil.md`.

### Sources, par ordre de priorité
1. **Welcome to the Jungle** : source prioritaire. WebFetch renvoie 403 sur ce site ; les pages d'offres et d'entreprises se lisent dans le navigateur intégré (navigue sur l'URL, attends 3 secondes, lis `document.body.innerText`). Trouve les URLs par WebSearch (`allowed_domains: ["welcometothejungle.com"]`) et par les pages entreprises des cibles (`/fr/companies/<entreprise>/jobs`), et repère les entreprises similaires.
2. **LinkedIn** : pages de résultats publiques lues dans le navigateur intégré, par exemple `https://www.linkedin.com/jobs/search/?keywords=<mots>&location=<lieu>&f_JT=I&f_TPR=r2592000&sortBy=DD` (stages, 30 derniers jours, plus récentes d'abord). Une offre se lit sur `https://www.linkedin.com/jobs/view/<id>`. Requêtes à faire à chaque passage : « stage gestion de patrimoine », « stage conseiller patrimonial », « stage CGP », « stage investor relations sales investissement », « stage partenariats CGP distribution fonds », « stage gestion pilotée allocation d'actifs », « stage assurance vie épargne », « stage SCPI crowdfunding plateforme d'investissement », chacune en France puis avec Montpellier / Occitanie et Paris / Île-de-France. Lis seulement ce qui est affiché à l'écran, une page à la fois, sans insister si un mur de connexion apparaît.
3. **Sites carrières officiels** des cibles (voir `profil.md`) et des caisses régionales (Crédit Agricole du Languedoc, Banque Populaire du Sud, Caisse d'Épargne Languedoc-Roussillon, CIC, BNP à Montpellier).
4. **Indeed, HelloWork, APEC, France Travail, Meteojob, Jobteaser** : par la recherche web (extraits) pour repérer ; ouvre la page de l'offre avant de la garder.

Pour chaque offre repérée sur un agrégateur, retrouve-la sur le site officiel de l'employeur quand c'est possible et garde ce lien (`type_source: "officielle"`). Sinon garde le lien de l'agrégateur avec `type_source: "agregateur"`.

### Règles d'admission
- Page ouverte et en ligne, sinon elle n'entre pas.
- Niveau : voir § 2.
- Début avant le 15 novembre 2026, ou date affichée périmée : écarte l'offre.
- Date de début absente : `date_debut: null` et « à vérifier » dans `vigilance`. Date incohérente sur la page : `date_debut: null` et explique-le.
- Emploi, CDI, alternance ou apprentissage : écarte. Stage seulement.
- Doublon (même URL, ou même entreprise + titre + ville) : n'ajoute pas.
- **Pas plus de 5 offres d'un même employeur** dans la liste principale (les `ambitieuse: false`).
- **Objectif : au moins 40 offres actives pertinentes.** Si tu n'y arrives pas, dis pourquoi dans `AUDIT.md`, section « Dernier passage ».

### Remplir une offre (schéma : `schema/offres.schema.json`)
- `titre`, `entreprise`, `ville`, `region` (ex. « Île-de-France », « Occitanie »), `url`, `type_source`.
- `famille` : `plateforme_investissement` | `fintech` | `reseau_bancaire` | `cgp` | `assurance` | `gestion_patrimoniale` | `autre`.
- `ambitieuse` : `true` pour les maisons prestigieuses qui recrutent surtout en grandes écoles (Rothschild, Lazard, Pictet, Edmond de Rothschild, Lombard Odier, ODDO BHF, Carmignac, UBS, JPMorgan…), sinon `false`.
- `metier` : `sales_ir` (sales, investor relations, partenariats CGP, distribution) | `allocation` (allocation, gestion pilotée, conseil en investissement) | `patrimoine` (gestion de patrimoine, CGP, banque privée) | `asset_management` (distribution, middle office, analyse en société de gestion) | `epargne_assurance`.
- `date_debut` : `AAAA-MM-JJ` ou `AAAA-MM`, sinon `null`. `duree` : entier en mois, sinon `null`.
- `niveau` : `bac3_4` (Bac+3 ou Bac+4 ou M1 accepté) | `bac4_5` (Bac+4/5) | `non_precise`.
- `competences` : sous-ensemble de `excel_vba_python`, `relation_patrimoniale`, `assurance_vie`, `marches` (seulement ce que l'offre demande et qui recoupe le profil).
- `date_publication` : obligatoire. Date exacte si affichée ; sinon estime-la (« il y a 5 jours » = AUJOURDHUI moins 5 jours) et mets `date_estimee: true`. `null` seulement si rien n'est estimable (le score donne alors 4 points de fraîcheur).
- `pourquoi` (cite un élément concret du parcours), `vigilance`, `angle` : une phrase chacune, reformulées, jamais copiées.
- `premiere_detection` et `derniere_verification` : `AUJOURDHUI`. `statut` : `"active"`. `deja_postule` : `false` (ne le passe à `true` que sur indication de l'utilisateur ; une offre `deja_postule` n'est jamais reproposée comme nouveauté).
- `id` et `score` : n'importe quelle valeur ou rien ; le validateur les recalcule. Ne calcule jamais le score à la main.

## 5. Journal et date

- `derniere_mise_a_jour` = `AUJOURDHUI`.
- Ajoute (ou remplace, si passage le même jour) une entrée de `journal` : `{"date", "ajoutees", "expirees", "exclues_niveau_m2", "moins_de_7_jours", "sources_inaccessibles": [...], "notes": [...]}`. `moins_de_7_jours` est recalculé par le validateur (offres actives publiées depuis moins de 7 jours, hors déjà postulées).

## 6. Valider, commiter, pousser

1. `python scripts/valider.py` (réécrit le fichier : ids, scores, doublons, tri). Il doit finir par `OK` ; corrige les erreurs et relance. Les lignes « attention » sont des alertes à traiter si possible (dates de publication manquantes, plus de 5 offres par employeur).
2. `python -m unittest discover -s tests` doit passer.
3. Message de commit au format exact : `maj AAAA-MM-JJ : +N nouvelles, -M expirées`.
4. `git add data/offres.json AUDIT.md && git commit && git push origin main` (en cas de rejet : `git pull --rebase`, relance le validateur, repousse).

La GitHub Action relance les tests et le validateur puis déploie le site.

## 7. Réponse finale

Résume en 3 lignes : offres ajoutées (titre, entreprise, score), offres expirées ou exclues pour niveau, sources inaccessibles.
