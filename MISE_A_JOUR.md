# Mise à jour quotidienne de Radar Stages

Tu es l'agent chargé de mettre à jour ce dépôt chaque matin. Ces instructions sont autonomes : ne demande rien à l'utilisateur, décide et agis. Le dépôt est un site statique (`index.html` + `data/offres.json`) publié par GitHub Pages.

## 0. Garde-fous

- N'écris jamais de clé API, mot de passe, nom, e-mail ou téléphone dans le dépôt. Le dépôt est public.
- N'invente jamais une offre, une date ou un lien. Une offre entre dans la liste seulement si tu as ouvert sa page (WebFetch) et constaté qu'elle est en ligne.
- Ne scrape rien par script. Utilise la recherche web (WebSearch) et la lecture de pages (WebFetch). Si un site renvoie 403 ou refuse l'accès, ne le contourne pas : note-le dans `sources_inaccessibles`.
- Un résumé de moteur de recherche ne prouve rien : ouvre toujours la page de l'offre.
- Ne modifie pas `index.html`, `scripts/` ni `.github/` sauf demande explicite. Tu ne touches qu'à `data/offres.json`.

## 1. Préparation

1. `git pull --ff-only` puis lis `profil.md` (critères de recherche) et `data/offres.json`.
2. Note la date du jour (AAAA-MM-JJ, heure de Paris) : `AUJOURDHUI`.
3. Lance `python scripts/valider.py --check`. Si le fichier est déjà invalide, corrige-le avant toute chose.

## 2. Revérifier les offres déjà listées

Pour chaque offre `statut: "active"` : ouvre son `url`.
- Toujours en ligne (bouton « Postuler » ou équivalent, pas de message « poste pourvu / offre expirée / page introuvable ») : mets `derniere_verification` à `AUJOURDHUI`.
- Plus en ligne (404, redirection vers la liste, mention « pourvue », « clôturée », ou date de début désormais passée) : passe `statut` à `"expiree"` et mets `derniere_verification` à `AUJOURDHUI`. Ne supprime jamais l'offre.
- Page inaccessible (403, timeout) : ne change pas le statut, laisse `derniere_verification` inchangée, et ajoute le domaine à `sources_inaccessibles`. Si l'inaccessibilité dure plus de 7 jours consécutifs dans le journal, laisse tout de même l'offre active mais ajoute « lien non vérifiable depuis plusieurs jours » à `vigilance`.

Ne repasse jamais une offre `expiree` en `active` sauf si sa page est de nouveau en ligne.

## 3. Chercher de nouvelles offres

Cible : stage de 6 mois démarrant en janvier 2027 (début accepté du 15 décembre 2026 au 28 février 2027). Métiers par priorité : allocation / sélection de fonds, banque privée / gestion de patrimoine, asset management. Exclusions : finance de marché pure, M&A, audit, comptabilité, contrôle de gestion, trésorerie d'entreprise, banque de détail sans dimension patrimoniale. La liste détaillée est dans `profil.md`.

Sources, dans cet ordre :
1. Sites carrières officiels : Amundi, CPR AM, BNP Paribas (Wealth Management et AM), Rothschild & Co et Rothschild Martin Maurel, Edmond de Rothschild, ODDO BHF, Natixis IM et affiliés, AXA IM, Groupama AM, Ofi Invest, La Banque Postale AM, Swiss Life AM et Swiss Life Banque Privée, Indosuez, Société Générale Private Banking, Neuflize OBC, Banque Transatlantique, CIC Banque Privée, LCL Banque Privée, Carmignac, Lazard Frères Gestion, DNCA, Sycomore, Mandarine Gestion, La Financière de l'Échiquier, Tikehau, Ardian, Meeschaert, Cyrus Conseil, Crédit Agricole Assurances.
2. Montpellier / Occitanie : Crédit Agricole du Languedoc, Banque Populaire du Sud, Caisse d'Épargne Languedoc-Roussillon, BNP Paribas Banque Privée et CIC à Montpellier, cabinets de CGP et family offices de la région.
3. Agrégateurs (recherche web uniquement, pour repérer) : Welcome to the Jungle, JobTeaser, Wizbii, Dogfinance, Indeed, LinkedIn. Pour chaque offre repérée, retrouve-la sur le site officiel de l'employeur et garde ce lien (`type_source: "officielle"`). Si elle n'existe que sur un agrégateur et que tu as pu ouvrir sa page, garde-la avec `type_source: "agregateur"`.

Astuce : les moteurs renvoient souvent le même employeur. Varie les requêtes (nom de l'employeur + « stage » + « janvier 2027 », intitulés de poste, villes) et utilise `allowed_domains` pour cibler un site.

### Règles d'admission d'une offre
- Page ouverte et en ligne, sinon elle n'entre pas.
- Début avant le 15 décembre 2026, ou date affichée périmée : écarte l'offre.
- Date de début ou niveau absents : garde l'offre avec `date_debut: null` ou `niveau: "non_precise"` et écris « à vérifier » dans `vigilance`.
- M2 / Bac+5 exigé explicitement : garde l'offre avec `niveau: "m2_exige"` et le dit dans `vigilance`. Si la page dit « Bac+4/5 », c'est `m1_accepte`.
- Doublon (même URL, ou même entreprise + titre) : ne l'ajoute pas ; le validateur en supprimerait un de toute façon.
- Date incohérente sur la page : `date_debut: null` et explique-le dans `vigilance`.

### Remplir une offre
Tous les champs du schéma (`schema/offres.schema.json`) :
- `titre`, `entreprise`, `ville`, `region` (ex. « Île-de-France », « Occitanie »), `url` (URL officielle), `type_source`.
- `metier` : `allocation` | `banque_privee` | `asset_management`.
- `date_debut` : `AAAA-MM-JJ` ou `AAAA-MM`, sinon `null`. `duree` : entier en mois, sinon `null`.
- `niveau` : `m1_accepte` | `non_precise` | `m2_exige`.
- `competences` : sous-ensemble de `excel_vba_python`, `relation_patrimoniale`, `assurance_vie`, `marches`, uniquement ce que l'offre demande ou mobilise vraiment et qui recoupe le profil.
- `pourquoi` (cite un élément concret du parcours dans `profil.md`), `vigilance`, `angle` : une phrase chacune, reformulées, jamais copiées de l'offre.
- `date_publication` si la page l'indique, sinon `null`.
- `premiere_detection` et `derniere_verification` : `AUJOURDHUI`. `statut` : `"active"`.
- `id` et `score` : mets n'importe quelle valeur ou omets-les, le validateur les recalcule. Ne calcule jamais le score à la main.

## 4. Journal et date

- `derniere_mise_a_jour` = `AUJOURDHUI`.
- Ajoute à `journal` une entrée `{"date": AUJOURDHUI, "ajoutees": N, "expirees": M, "sources_inaccessibles": [...]}` (domaines inaccessibles ce jour-là). Le validateur ne garde que les 30 dernières.
- S'il y a eu un passage le même jour, remplace l'entrée au lieu d'en ajouter une.

## 5. Valider, commiter, pousser

1. `python scripts/valider.py` (réécrit le fichier : ids, scores, doublons, tri). Il doit finir par `OK`. S'il liste des erreurs, corrige-les et relance ; n'enregistre rien d'invalide.
2. `python -m unittest discover -s tests` doit passer.
3. S'il n'y a aucun changement à part les dates de vérification, commite quand même (la date de mise à jour affichée change).
4. Message de commit au format exact : `maj AAAA-MM-JJ : +N nouvelles, -M expirées` (N = offres ajoutées, M = offres passées en expirée ce jour).
5. `git add data/offres.json && git commit && git push origin main`. En cas de rejet du push : `git pull --rebase`, relance le validateur, repousse. Si le push échoue encore, arrête-toi et décris l'erreur dans ta réponse finale.

La GitHub Action relance le validateur et déploie le site à chaque push sur `main`.

## 6. Réponse finale

Résume en 3 lignes : offres ajoutées (titre, entreprise, score), offres expirées, sources inaccessibles. Rien d'autre.
