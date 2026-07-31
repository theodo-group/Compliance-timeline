# Compliance Timeline — MDSW / AI Act, Theodo HealthTech

Document unique de référence : intent, fonctionnalités, et le "pourquoi" derrière
les choix de conception. Remplace plusieurs notes éparpillées (voir tout en bas
"Fichiers retirés / historique" pour ce qui a été consolidé ici).

## Intent

Outil de veille réglementaire pour les fabricants de logiciels médicaux (MDSW) :
suit MDR/IVDR, l'AI Act, la cybersécurité (CRA/NIS2), les données de santé
(HDS/EHDS) et les normes associées (ISO, IEC, CEN-CENELEC). Trois usages :

1. Une **frise chronologique publique** (EN + FR) des jalons réglementaires,
   consultable par toute l'équipe QARA.
2. Un **back office** où un(e) QARA (aujourd'hui Manon) passe en revue les
   propositions de mise à jour générées automatiquement chaque semaine.
3. Une **veille automatisée hebdomadaire** (recherche + rédaction + email +
   propositions) qui tourne seule sur GitHub Actions, sans dépendre d'une
   machine ou d'un compte personnel allumé.

## Les trois sous-systèmes

### 1. Frises publiques — `index.html` (EN) / `fr.html` (FR)

Pages statiques, hébergées sur GitHub Pages. Au chargement : `fetch(data.json)`
(jalons de base) + `fetch(proposals.json)` (propositions en attente, pour
prévisualisation) + `fetch(decisions.json)` (état admin : cartes cachées,
propositions approuvées/rejetées). Fusion en mémoire, puis rendu avec filtres
(thème, récence). Les deux pages ont exactement la même structure, seule la
langue des données change (`data.json`/`data-fr.json`, `t_fr`/`x_fr` sur les
propositions traduites).

Tout champ texte est échappé avant injection HTML (`escapeHtml`, `safeUrl` —
schémas http/https uniquement) : corrige un risque XSS stocké identifié le 28
juillet 2026 (contenu web scrapé → proposition → rendu dans le navigateur d'un
admin, sans échappement à l'époque).

### 2. Back office — `admin.html`

Un seul fichier gère les deux langues. Fonctionnalités :

- **Revue des propositions** (onglets Pending / Archived) : Approve / Reject /
  undo. Chaque proposition affiche un diff pour les `update`, et un lien vers
  la source.
- **Édition manuelle avant approbation** (`proposal_edits`) : un admin peut
  corriger le titre/la description proposés par l'IA directement dans le
  textarea avant d'approuver — la correction est conservée (`decisions.json`)
  et appliquée définitivement au moment où la proposition est promue dans
  `data.json`/`data-fr.json` (voir `_apply_proposal_edit` côté pipeline).
- **Paires delete+add groupées** : quand le pipeline remplace une fiche
  périmée (delete de l'ancienne + add de la nouvelle plutôt qu'un vrai
  "update" — la timeline est une chronologie, pas un état, donc un
  remplacement garde les deux dates), le back office affiche les deux
  propositions comme une seule carte groupée avec trois choix : approuver le
  remplacement, garder l'ancienne, ou annuler les deux ensemble. Le lien entre
  les deux propositions est **persisté** (`decisions.paired_proposals`, un
  index bidirectionnel), pas juste deviné visuellement à chaque affichage —
  ça évite qu'un "undo" sépare la paire ou ré-attache la mauvaise carte après
  une décision.
- **Tableau des jalons** : masquer/afficher, recherche, tags éditables par
  clic (dropdown), commentaires bilingues séparés par jalon.
- **Garde-fou "REVIEW"** : si le modèle propose un `update` dont la
  description ne recouvre presque pas (< 20% de vocabulaire commun, indice de
  Jaccard) celle du jalon existant, la proposition est préfixée `[REVIEW: ...]`
  — signe probable qu'un NOUVEAU développement a été déguisé en update au lieu
  d'un `add` (voir `flag_rewritten_updates` côté pipeline).

**Synchronisation** : `decisions.json` est la source de vérité cross-device,
lue/écrite via l'API GitHub (PAT dans le champ en haut de page). En cas
d'échec de push (SHA périmé — une autre session a poussé entre temps), retry
automatique avec fusion (jusqu'à 3 essais) et bannière rouge persistante tant
que la sync n'est pas confirmée (corrige un bug UAT : une approbation de Manon
n'était jamais arrivée sur GitHub, seul un toast discret signalait l'échec).

### 3. Veille automatisée — `automation/weekly_watch.py`

Tourne sur GitHub Actions (`.github/workflows/regulatory-watch.yml`), planifié
chaque vendredi (`schedule: cron "0 4 * * 5"`, soit 06:00 Paris l'été / 05:00
l'hiver — cron GitHub en UTC, sans heure d'été, déclenchement pouvant être
décalé). Étapes :

1. **Recherche** — en parallèle : les ~12 sources fixes (`FIXED_SOURCES`,
   fetch HTTP simple + BeautifulSoup, toutes confirmées server-rendues) ; 8
   requêtes Perplexity Sonar (`SONAR_QUERIES`, bornées "7 derniers jours") ;
   un scraping Playwright (navigateur headless) des pages CEN/CENELEC
   "Standards Evolution and Forecast" + de la page "Work programme" du comité
   JTC 21.
2. **Triage** (1 appel Sonnet) — sélectionne les développements matériels de
   la semaine, sans prose, juste une liste structurée de faits.
3. **Rédaction** (1 appel Haiku par item retenu) — écrit le résumé/détail de
   chaque item séparément.
4. **Propositions** (1 appel Sonnet) — dérive des propositions ADD/UPDATE/
   DELETE à partir du contenu déjà rédigé, jamais en re-recherchant.
5. **Traduction FR** (1 appel Haiku par carte) — traduit chaque proposition
   carte par carte (garantit la parité d'id EN/FR par construction).
6. **Validation stricte** du JSON produit — rien n'est écrit/poussé si invalide.
7. **Promotion** des propositions déjà approuvées dans le back office
   (`decisions.approved_proposals`) vers `data.json`/`data-fr.json`, avant de
   régénérer `proposals.json` (qui redevient une simple boîte de réception
   hebdomadaire, écrasée à chaque run).
8. **Email** (corps concis + rapport complet en pièce jointe) + **push git**
   des fichiers publics, gated par `DRY_RUN`.

**Pourquoi autant de petits appels séparés (fan-out) plutôt que peu de gros
appels** : le gateway LiteLLM (`https://llm-gateway.m33.tech`) coupe tout
appel à 300 secondes pile (mesuré, voir `automation/tools/gateway_cap_probe.py`
— parfois déguisé en `finish_reason="stop"`, donc la validation JSON stricte
en aval est le seul détecteur fiable de troncature). Décision explicite :
le nombre d'appels ne peut pas être réduit tant que cette contrainte tient ;
les optimisations de coût portent donc sur la taille de chaque appel et sur
le modèle utilisé par étape (Sonnet pour les étapes de décision — triage,
propositions ; Haiku, ~3x moins cher, pour les étapes mécaniques — prose d'un
item déjà choisi, traduction de 3 champs), pas sur le nombre d'appels lui-même.

## Modèle de données

- **`data.json` / `data-fr.json`** — jalons publiés (le "grand cahier"
  permanent). Un jalon : `id` (format `YYYY-MM-DD--slug-anglais`, identique
  EN/FR), `d`/`l`/`y` (date), `t`/`x` (titre/description), `u` (source), `tp`
  (topics), `tg` (tags), `v` (variante visuelle : c=critique navy, h=highlight
  or, n=normal).
- **`proposals.json` / `proposals-fr.json`** — boîte de réception hebdomadaire
  (écrasée à chaque run, sauf ce qui vient d'être approuvé et promu juste
  avant). Une proposition : `action` (add/update/delete), `id`, `existing_id`
  (pour update/delete), `reason`, `card`.
- **`decisions.json`** — état du back office, écrit par `admin.html` via
  l'API GitHub (jamais par le pipeline) : cartes cachées, propositions
  approuvées/rejetées, éditions manuelles (`proposal_edits`), tags
  personnalisés, commentaires bilingues, liens de paires (`paired_proposals`).
- **`automation/state/known_topics.json`** — mémoire anti-répétition
  persistante du pipeline (voir plus bas). **Complètement indépendante** des
  trois fichiers ci-dessus : aucun lien code entre elle et
  proposals/decisions/data.

## Décisions de conception importantes (le "pourquoi")

### Recherche — pourquoi Playwright pour CEN/CENELEC/JTC 21

Un changement de statut sur un registre de normalisation (draft → ratifié →
publié) n'est presque jamais couvert par la presse — donc structurellement
invisible à des requêtes Sonar type "news this week", quelle que soit leur
formulation (vécu : la ratification d'EN 18286 manquée alors que la page
officielle l'affichait). Ces pages sont en plus rendues en JavaScript (Oracle
APEX) : un simple `requests.get()` renvoie une coquille vide. D'où un
navigateur headless (Chromium/Playwright), réservé à ce cas précis — Sonar et
les sources fixes restent des fetchs simples (confirmées server-rendues,
`automation/tools/compare_fixed_sources_playwright.py`).

Trois pages génériques et stables (pas d'ID de projet à coder en dur) :
- `f?p=CEN:84` / `f?p=CENELEC:84` — "Standards Evolution and Forecast",
  toutes normes publiées ces 2 derniers mois, tous comités/secteurs
  confondus. Filtrées par pertinence (mots-clés + comités JTC 21/TC 204/TC
  251/TC 215) avant envoi au modèle : ~226 lignes/~40 500 caractères tous
  secteurs réduites à ~23 lignes/~4 100 caractères pertinentes (medical/
  health/AI/cyber/software), ~90% de réduction sans perte (filtre par
  pertinence, pas troncature par position).
- Page "Work programme" du comité **JTC 21** lui-même (org ID 2916257 sur la
  même plateforme `standards.cencenelec.eu`, appli Oracle APEX différente —
  nécessite les page-items `FSP_ORG_ID`/`FSP_LANG_ID` + un checksum `cs=`
  récupéré depuis le lien officiel publié par jtc21.eu, pas inventé). Donne le
  stade EXACT de chaque norme (Drafting/Enquiry/Approval/Approved) et sa date
  de vote prévue — pas seulement "publiée ou non". Déjà scopée au comité,
  donc envoyée sans filtre.

Sources fixes EC (Drupal — `digital-strategy.ec.europa.eu`,
`health.ec.europa.eu`) : scoping sur `#main-content`/`<main>`/`[role=main]`
plutôt que la page entière, pour sauter ~2000-3000 caractères de menu de
navigation/sélecteur 23-langues avant le vrai contenu. Repli automatique sur
la page entière si ce repère est absent (ex. `qualitiso.com/veille`, en
WordPress, n'a ni l'un ni l'autre).

### Anti-répétition — `known_topics.json`

Registre persistant, indépendant de `proposals.json`/`decisions.json`, lu
avant le triage (digest "sujets déjà couverts, ne répète pas sauf changement
matériel") et réécrit après le run (jamais en `DRY_RUN`, pour ne pas
enregistrer des items qu'aucun destinataire n'a réellement reçus).

La clé de correspondance (`_topic_key`) est bâtie sur la **référence de
norme** quand le titre en cite une explicitement (`std-18286`), pas sur un
slug du titre entier : un titre reformulé légèrement d'un run à l'autre
("EN 18286:2026 norme QMS..." vs "Publication de la norme EN 18286:2026...")
créait sinon plusieurs entrées distinctes pour le même sujet. Le repli par
URL (`merge_known_topics`) n'est autorisé que sur une URL **spécifique** à un
sujet (`_is_specific_url`) — une URL de page hub partagée par plusieurs sujets
(ex. la page work programme JTC 21, qui liste 35 projets différents) est
explicitement exclue de cet index, pour ne jamais faire collapser deux sujets
distincts sur la même entrée.

`IGNORE_KNOWN_TOPICS` (flag de test GitHub Actions) fait tourner le triage
comme si cette mémoire était vide, sans jamais toucher au vrai fichier — utile
pour voir ce qu'un run "sans historique" produirait. **Ne "ressuscite" pas**
une vieille actualité : le contenu vient exclusivement de la recherche FRAÎCHE
de la semaine (Sonar bornée 7 jours, sources fixes = contenu actuel des
pages) — si un sujet est sorti de cette fenêtre, ignorer la mémoire n'y change
rien.

### `standards_changed` — matching par alias

Le modèle doit recopier exactement une `reference` de `STANDARDS_REGISTER`
pour que l'annexe "normes suivies" de l'email surligne la bonne ligne. En
pratique il écrit parfois une variante légitime (préfixe `prEN`→`EN` une fois
publié, ou une seule partie d'une famille groupée comme `prEN 18229-3`). Un
système d'alias explicite sur chaque ligne du register (`aliases: [...]`)
reconnaît ces variantes sans risquer de confondre deux normes différentes
entre elles (chaque alias ne pointe que vers UNE ligne).

### Coût — mesure réelle plutôt que suppositions

Le pipeline **mesure** désormais sa propre consommation (`record_usage`,
`log_usage_summary`) — tokens réellement facturés par étape (`usage` renvoyé
par l'API en streaming), agrégés et affichés en fin de run avec un coût
estimé par étape (prix catalogue, hors marge du gateway et hors forfait
Perplexity par recherche, non renvoyé par l'API). Avant cet ajout, l'enquête
"pourquoi ~30 centimes par run" ne pouvait produire que des suppositions —
les fichiers `debug_last_*_output.txt` sont un mauvais proxy (ils contiennent
le résultat de plusieurs étapes empilées, pas le coût de chacune isolément).

Point important : réduire le volume de texte en ENTRÉE (recherche filtrée,
scoping HTML) baisse le coût des deux gros appels (triage, propositions),
mais le total est dominé par le NOMBRE d'appels — qui scale avec le volume de
vraie actualité trouvée, pas avec la propreté de la recherche brute. Rendre
la recherche plus précise (ex. l'ajout JTC 21) peut donc mécaniquement
augmenter le coût d'un run actif (plus d'items réels = plus d'appels de
rédaction/traduction), même si chaque appel individuel est mieux nourri.

### Garde-fous JSON côté propositions

- `build_milestones_index()` envoie un rendu compact de la timeline existante
  au modèle (une ligne par jalon, sans les URL sources — 23% du volume,
  jamais utiles pour choisir add/update) plutôt que le JSON complet
  (−36% sur cette partie du prompt). `backfill_update_urls()` recomplète
  `card.u` depuis le jalon existant côté code, en compensation.
- `flag_rewritten_updates()` : garde-fou déterministe (indice de Jaccard sur
  le vocabulaire) contre un nouveau développement déguisé en `update` d'un
  jalon existant plutôt qu'un `add` — préfixe `[REVIEW: ...]`, visible dans
  le back office, sans jamais bloquer (le modèle peut avoir raison).
- **Jamais d'édition manuelle de `proposals.json`/`proposals-fr.json`/
  `data.json`.** Toute correction doit venir du pipeline lui-même — règle
  explicite, plus haute priorité que la commodité d'un patch ponctuel.

## Limitations connues

- Cross-device sync du back office nécessite un PAT GitHub (`repo` scope) ;
  sans lui, les décisions restent en `localStorage`, propre au navigateur.
- Déploiement GitHub Pages ~30s après un push — pas instantané cross-device.
- Un push du pipeline (via `GITHUB_TOKEN` d'Actions) ne redéclenche jamais
  Pages tout seul (protection anti-boucle de GitHub) — un push humain
  ultérieur redéploie normalement.
- Éditions concurrentes du back office : la seconde à pousser peut essuyer un
  conflit de SHA (retry automatique avec fusion, voir plus haut).
- Recipients de test uniquement (`automation/recipients.json` : une seule
  adresse) — pas encore étendu à la vraie liste de diffusion.
- Envoi d'email toujours via le Gmail personnel de Joseph (app password) —
  migration vers une vraie boîte Workspace dédiée pas encore faite.
  **`team@hokla.com` ne peut PAS remplir ce rôle** : c'est un Google Group
  (liste de diffusion), pas un compte — aucun identifiant d'envoi (app
  password, clé API, OAuth) ne peut être généré dessus, quel que soit le rôle
  (Manager inclus). Il faudrait soit un alias "Send as" depuis un vrai compte,
  soit une vraie boîte Workspace dédiée créée par l'IT.

## Secrets & opérations

Trois secrets font tourner l'automatisation (repo → Settings → Secrets and
variables → Actions), non rattachés à une personne au sens propre mais
régénérables facilement si besoin :

1. **`GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD`** — envoi de l'email hebdomadaire
   (SMTP).
2. **`LITELLM_API_KEY`** — tous les appels modèle du pipeline (triage/
   propositions sur Sonnet, rédaction/traduction sur Haiku, recherche sur
   Perplexity Sonar) via `https://llm-gateway.m33.tech`.
3. **`GITHUB_TOKEN`** — fourni automatiquement par GitHub Actions pour les
   push du pipeline, pas de PAT personnel requis pour ça.

### Renouveler `GMAIL_APP_PASSWORD` ou `LITELLM_API_KEY`

Procédure maintenue à jour dans Notion (source de référence — mets-la à jour
là-bas d'abord si quelque chose change) :
[Modop — Renouveler les clés API (Gmail + LiteLLM)](https://app.notion.com/p/3ae8f3776f4f81e8afa7e1c55b0829ba).

Résumé :

- **Gmail** : compte Gmail dédié → [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
  (l'URL directe, le chemin via Sécurité ne mène pas toujours à la bonne
  page) → créer un nouveau App password → mettre à jour le secret GitHub
  `GMAIL_APP_PASSWORD` (et `GMAIL_ADDRESS` aussi si l'adresse elle-même
  change, pas seulement son mot de passe) → tester sans risque via
  `.github/workflows/cron-test.yml` (email de test, coût zéro).
- **LiteLLM** : [llm-gateway-connection.m33.tech](https://llm-gateway-connection.m33.tech/)
  (compte Google Theodo) → Virtual Keys → Create New Key → équipe
  "Individual usage" (ou l'équipe du projet) → **ne sélectionner aucun
  modèle spécifique** (la clé doit rester utilisable avec tous les modèles
  appelés par le pipeline) → mettre à jour le secret GitHub
  `LITELLM_API_KEY`.
- Dans les deux cas, vérifier ensuite via Actions → Regulatory Watch (weekly)
  → Run workflow avec `dry_run: true`, sans attendre le run planifié du
  vendredi.

Déclenchement : le `schedule:` natif de `regulatory-watch.yml` est actif
(vendredi). Un ancien plan de secours via cron-job.org (token GitHub externe,
scope `repo` ou fine-grained "Actions: Read and write") reste documenté au cas
où le cron GitHub natif se montrerait trop peu fiable à l'usage — pas activé
en parallèle (double run sinon).

## Politique de travail pour un agent Claude sur ce repo

Voir `CLAUDE.md` (racine) pour le détail : routine de push (`rm -f
.git/index.lock .git/HEAD.lock; git pull --no-rebase --no-edit origin main;
git push origin main`), pourquoi les rejets "non-fast-forward" sont normaux
(`decisions.json` est poussé automatiquement par toute session `admin.html`),
et surtout — **l'agent ne lance jamais lui-même de commande git d'écriture**
dans ce dossier partagé (sandbox qui ne peut pas `unlink()` certains fichiers
→ verrous bloqués côté Mac de Joseph). Il édite les fichiers, puis donne la
séquence exacte à lancer.

`automation/UAT-FEEDBACK-MANON.md` reste **local uniquement**, sur demande
explicite de Joseph — jamais `git add`/committé/poussé, même en bloc.

## File map

```
index.html, fr.html          Frises publiques EN/FR
admin.html                    Back office (revue propositions, tags, paires)
data.json, data-fr.json       Jalons publiés (source de vérité permanente)
proposals.json, -fr.json      Boîte de réception hebdomadaire (écrasée)
decisions.json                État admin (écrit par admin.html via API GitHub)
automation/
  weekly_watch.py              Pipeline de veille (voir sections ci-dessus)
  config.json                  Modèle par étape (triage/item/proposals/traduction)
  recipients.json              Destinataires email
  state/                       Debug dumps, archive d'emails, known_topics.json
  tools/                       Scripts de diagnostic ponctuels (pas appelés par le pipeline)
  legacy-macos/                Ancienne automatisation launchd — historique, ne tourne plus
.github/workflows/
  regulatory-watch.yml          Le vrai job hebdomadaire (+ flags de test)
  pages.yml                     Déploiement GitHub Pages sur push main
  cron-test.yml                 Test isolé de déclenchement (email de test, zéro coût LLM)
  gateway-probe.yml             (voir automation/tools/gateway_cap_probe.py)
reports/April_2026.md          Premier rapport de veille (avant automatisation) — historique
CLAUDE.md                      Politique de travail git pour un agent Claude sur ce repo
```

## Fichiers retirés / historique

Ce README consolide et remplace :
- `ARCHITECTURE.md` — diagramme macOS/launchd devenu obsolète, journal
  chronologique difficile à parcourir. Contenu à jour repris ci-dessus.
- `automation/EN18286-INVESTIGATION.md` — investigation ponctuelle sur le
  raté de détection d'EN 18286, close. Leçons reprises dans "Recherche —
  pourquoi Playwright" ci-dessus.
- `automation/HANDOFF.md` — notes opérationnelles (secrets, cron-job.org).
  Reprises dans "Secrets & opérations" ci-dessus.
- `automation/HANDOFF-cost-and-july27-news.md` — brief de passation sur le
  coût et l'anti-répétition, déjà traité (voir sections "Coût" et
  "Anti-répétition" ci-dessus).

Conservés tels quels (pas de doublon, pas obsolètes) :
- `CLAUDE.md` — instructions spécifiquement adressées à un agent Claude,
  chargées automatiquement ; distinct d'un README humain.
- `automation/legacy-macos/` — déjà auto-documenté comme historique, isolé
  dans son propre dossier.
- `automation/UAT-FEEDBACK-MANON.md` — local uniquement par instruction
  explicite, contenu produit encore utile (liste de "pas encore fait").
- `reports/April_2026.md` — premier rapport, avant l'automatisation :
  référence/preuve de concept, pas un doublon de ce README.
