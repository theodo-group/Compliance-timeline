# Handoff — reprendre la veille réglementaire

Deux secrets font tourner cette automatisation. Si la personne qui les a créés quitte le
projet, il suffit de régénérer ces deux-là — rien d'autre n'est rattaché à une personne en
particulier.

## 1. Mot de passe d'application Gmail

Utilisé par `weekly_watch.py` pour envoyer le mail hebdomadaire (`GMAIL_ADDRESS` /
`GMAIL_APP_PASSWORD`).

- Où il est stocké : secrets du repo GitHub (Settings → Secrets and variables → Actions).
- Comment le régénérer : dans les paramètres du compte Gmail dédié au projet
  (Sécurité → Mots de passe des applications), révoquer l'ancien, en créer un nouveau,
  mettre à jour le secret `GMAIL_APP_PASSWORD` sur GitHub.

## 2. Token GitHub pour le déclenchement externe (cron-job.org)

> **Note (28 juil. 2026)** : le déclencheur actif est désormais le `schedule:` natif de GitHub
> Actions (`0 4 * * 5`, voir le workflow). cron-job.org n'est PAS requis et ne doit PAS tourner
> en parallèle sur ce workflow (double run). Cette section reste documentée comme repli si l'on
> a un jour besoin d'un déclenchement à l'heure plus fiable — dans ce cas, recommenter/retirer
> le `schedule:` du workflow pour n'avoir qu'un seul déclencheur.

GitHub Actions ne garantit pas un déclenchement à l'heure pile pour un `schedule:` cron
(voir la doc officielle : délais possibles, voire abandon du run en cas de forte charge).
Le déclenchement fiable du job hebdomadaire peut passer par [cron-job.org](https://cron-job.org),
qui appelle l'API GitHub (`workflow_dispatch`) à heure fixe.

- Ce que ça demande : un token GitHub avec accès à l'API Actions du repo. Un token
  **classic** avec le scope `repo` fonctionne (c'est celui actuellement configuré). Un
  token **fine-grained** fonctionne aussi officiellement pour cet usage (vérifié dans la
  doc GitHub REST API) à condition de bien cocher la permission **"Actions" en Read and
  write** (rien d'autre — pas "Workflows", pas "Contents") ; un essai précédent avec un
  fine-grained avait échoué, très probablement à cause d'une permission mal cochée plutôt
  que d'une limitation réelle.
- Où il est stocké : dans la configuration du job cron-job.org (header `Authorization`),
  jamais dans le code ni dans les secrets GitHub.
- Comment le régénérer : GitHub → Settings → Developer settings → Personal access tokens
  → régénérer, puis mettre à jour le header du job sur cron-job.org.
- Ce token reste techniquement rattaché à la personne qui l'a créé (comme le Gmail
  ci-dessus) — c'est un compromis acceptable tant qu'on n'a pas besoin d'une identité
  indépendante d'une personne (voir note plus bas).

## 3. Créer (ou recréer) un job cron-job.org

Si le job actuel doit être reproduit — nouveau compte, nouveau token, ou un second job
en plus de l'existant — voici tous les paramètres, dans l'ordre où cron-job.org les
demande :

- **Title** : libre, ex. `Trigger Compliance-timeline — veille hebdomadaire`.
- **URL** :
  `https://api.github.com/repos/<OWNER>/<REPO>/actions/workflows/<WORKFLOW_FILE>/dispatches`
  — remplacer `<OWNER>/<REPO>` (ex. `theodo-group/Compliance-timeline` une fois basculé)
  et `<WORKFLOW_FILE>` (ex. `regulatory-watch.yml`, ou `cron-test.yml` pour un test à coût
  zéro sans appeler aucun modèle).
- **Request method** : `POST` (pas GET — c'est le point le plus facile à oublier). Par
  défaut cron-job.org crée le job en `GET`, qui n'a pas de champ pour un corps de requête :
  tant qu'on n'a pas basculé sur `POST` dans la config du job, impossible même de saisir le
  `{"ref": "main", ...}` ci-dessous, et l'appel échoue silencieusement (404/405) une fois lancé.
- **Headers** (3, tous nécessaires) :
  - `Authorization` → `Bearer <TON_TOKEN>` (le mot "Bearer" + un espace + le token, tout
    dans le champ *valeur*, jamais dans le champ *clé*).
  - `Accept` → `application/vnd.github+json`
  - `Content-Type` → `application/json`
- **Request body** :
  - Pour `cron-test.yml` (test, aucun coût) : `{"ref": "main"}`
  - Pour `regulatory-watch.yml` (le vrai job) : `{"ref": "main", "inputs": {"dry_run": "false"}}`
    — **important** : sans ce `dry_run: false` explicite, le workflow utilise sa valeur
    par défaut (`true`), donc tourne indéfiniment en test sans jamais envoyer de mail ni
    rien publier, silencieusement.
- **Schedule** : le rythme voulu (ex. chaque vendredi matin). Pour un premier test, un
  intervalle court (15-30 min) permet de confirmer rapidement que ça marche avant de
  repasser au rythme réel.
- Une fois sauvegardé, le bouton **"Test run"** sur la page du job permet de déclencher
  l'appel immédiatement et de voir le code de réponse HTTP (401 = token invalide, 404 =
  mauvaise URL/repo/fichier de workflow, 204 = succès) — plus rapide que d'attendre le
  prochain créneau programmé pour déboguer.

## Note : pourquoi pas une GitHub App ?

Une GitHub App réglerait le problème de dépendance à une personne pour le token GitHub,
mais elle ne résout pas le vrai problème du moment (déclenchement fiable à l'heure) : son
utilisation demande de signer un JWT et d'échanger un token d'installation à chaque appel,
ce qu'un simple service comme cron-job.org ne peut pas faire tout seul — il faudrait un
bout de code intermédiaire, qui aurait lui-même besoin d'un déclencheur fiable pour
tourner. Ça vaudra le coup d'y revenir si le token fine-grained devient un vrai problème
opérationnel, pas avant.

## Autres tâches de migration en attente

Fait :
- Dépôt basculé sur `theodo-group/Compliance-timeline` (remote `origin` actuel).
- Cron hebdomadaire activé : `schedule: cron "0 4 * * 5"` dans
  `.github/workflows/regulatory-watch.yml` (vendredi 06:00 Paris l'été / 05:00 l'hiver — le
  cron GitHub est en UTC, sans heure d'été). NE PAS activer aussi un déclencheur cron-job.org
  sur ce workflow (double run : deux emails, deux lots de propositions).

Encore ouvert avant la bascule en production complète :
- Basculer l'envoi de mail vers **team@hokla.com** (aujourd'hui : le compte Gmail Theodo
  personnel de Joseph + mot de passe d'application, voir §1).
- Créer des **clés d'équipe LiteLLM** pour remplacer la clé au nom personnel de Joseph.
- Étendre `automation/recipients.json` au-delà de l'unique adresse de test.

Pistes d'amélioration identifiées lors de l'audit du 28 juil. 2026 (non bloquantes) :
- Contexte `data.json` compact envoyé au modèle des propositions (économie de tokens).
- Dédup entre sources fixes et Sonar + boucle de feedback sur les propositions rejetées.
- Éditions concurrentes du back office (conflit de SHA à la sauvegarde de `decisions.json`).

## À vérifier lors de la bascule vers le repo Theodo : permissions Actions

Erreur rencontrée sur le repo de test : `The actions actions/checkout@v4,
actions/setup-python@v5, and actions/upload-artifact@v4 are not allowed ... because all
actions must be from a repository owned by <owner>`. Réglage à vérifier dans
Settings → Actions → General → **Actions permissions** : il doit autoriser au minimum les
actions officielles `actions/*` (option "Allow all actions and reusable workflows", ou
"Allow select actions" avec `actions/*` explicitement ajouté). Les organisations comme
Theodo appliquent parfois une policy plus restrictive par défaut au niveau de l'org — à
vérifier aussi dans les paramètres d'organisation si le réglage du repo seul ne suffit pas.
