# Investigation : le raté sur EN 18286 et ce qu'on a corrigé

Récapitulatif des problèmes rencontrés et des solutions apportées, dans l'ordre où ils sont
sortis. Contexte : Joseph a remarqué que la veille automatisée n'avait pas signalé la
ratification d'EN 18286 (norme QMS IA pour l'AI Act) alors que l'info était disponible la
semaine où c'est arrivé.

## 1. Le raté initial — EN 18286 non détecté

**Problème** : la ratification de prEN 18286 en EN 18286:2026 (12 juillet 2026, disponible le
22 juillet) n'a pas été captée par le pipeline, alors que `data.json` contenait encore l'ancienne
mention "Failed Jan 2026 vote".

**Cause racine** : Perplexity Sonar est interrogé avec des requêtes du type "news this week" —
or un changement de statut sur un registre de normalisation (draft → ratifié → publié) n'est
quasiment jamais couvert par la presse. Ce cadrage ne peut structurellement pas capter ce genre
d'info, peu importe la formulation de la requête. Vérifié en ouvrant la page officielle
CEN-CENELEC via navigateur : elle affichait bien "Status: Published", mais un simple
`requests.get()` (utilisé à la fois par le pipeline et par mes propres outils de fetch) renvoie
une coquille vide sur cette page, car elle est rendue en JavaScript (Oracle APEX).

**Solution** : ajout de Playwright (navigateur headless Chromium) pour ce cas précis, en gardant
Sonar et les sources fixes strictement inchangés (décision explicite de Joseph : "on garde sonar
comme ajd").

## 2. Premier jet trop spécifique à un seul cas

**Problème** : la première version du fix pointait vers l'URL exacte de la fiche du projet
prEN 18286 (avec ses IDs internes `80556`/`2916257` codés en dur). Ça aurait résolu ce cas précis
mais aucun autre — chaque nouvelle norme à suivre aurait demandé de retrouver et coder son ID à
la main.

**Solution** : remplacé par le fetch d'une page générique et stable, sans ID de projet :
`https://standards.cencenelec.eu/ords/f?p=CEN:84` ("Standards Evolution and Forecast"), qui liste
toutes les normes CEN publiées ces 2 derniers mois, tous comités confondus. Confirmé qu'elle
contenait bien EN 18286. Pas de troncature : le tableau complet est passé au modèle de triage, qui
filtre lui-même ce qui est pertinent.

**Complément** : ajout de la même page côté CENELEC (organisme distinct, même plateforme) —
`f?p=CENELEC:84` — après avoir constaté qu'elle listait des normes pertinentes absentes de la
page CEN (ISO/TS 24971-2 sur le machine learning, ISO/IEC 27000 sur la sécurité de l'information).

## 3. Risque de pollution hors-sujet

**Problème** : la page CEN/CENELEC couvre tous les secteurs industriels (ferroviaire,
construction, alimentaire...), pas seulement la santé — risque que des items sans rapport
remontent dans le digest.

**Solution** : deux niveaux de protection. `standards_changed` a un filtre technique dur (le champ
`reference` doit correspondre exactement à une ligne de `STANDARDS_REGISTER`, donc un standard
hors-sujet ne peut structurellement pas y apparaître). Pour les `items` généraux, ajout d'une
ligne explicite dans le prompt précisant que la liste couvre tous les secteurs et de n'en retenir
que ce qui touche aux dispositifs médicaux/données de santé/AI Act/cybersécurité santé.

## 4. Audit des 12 sources fixes

**Problème** : Joseph soupçonnait que plusieurs des 12 `FIXED_SOURCES` pointaient vers des pages
d'accueil génériques plutôt que des sous-pages d'actualité, ce qui, combiné à la troncature à
2500 caractères par source, risquait de perdre le contenu utile sous le menu de navigation.

**Solution** : audit un par un. CNIL et ANSM remplacées par des sous-pages d'actualité dédiées
(`/fr/actualite`, `/actualites/a-la-une`). FDA retirée : bloquée par la détection anti-bot du site
(redirection vers une 404, confirmé en run réel). Les autres confirmées correctes.

## 5. Un correctif s'est révélé lui-même cassé

**Problème** : le remplacement proposé pour `health.ec.europa.eu` (la page dédiée
`ec.europa.eu/.../latest-updates_en`) renvoyait du 503 de façon reproductible — confirmé sur un
run GitHub Actions réel ET en local, donc pas un simple souci de réseau ponctuel.

**Solution** : reverti vers l'URL d'origine (`health.ec.europa.eu/.../new-regulations_en`),
confirmée fiable malgré son contenu moins frais.

## 6. IMDRF : confirmé cassé, mais conservé

**Problème** : `imdrf.org` échoue en timeout, confirmé à la fois en local et sur GitHub Actions.

**Décision** : contrairement à FDA, Joseph a choisi de la garder dans `FIXED_SOURCES` "pour
garder une trace" plutôt que de la retirer silencieusement — le fetch échoue proprement (log
explicite) sans bloquer le run.

## 7. Comparaison Playwright vs fetch simple sur les 12 sources

**Question** : fallait-il aussi passer les 12 sources fixes en Playwright ?

**Réponse (testée, pas supposée)** : non. Comparaison faite source par source — contenu quasi
identique dans 9 cas sur 11 entre fetch simple et Playwright, confirmant qu'elles sont bien
server-rendues comme documenté dans le code. `fetch_fixed_sources()` reste inchangé.

## 8. Frictions Git récurrentes (fichiers de verrou)

**Problème** : le dossier `Watch Tower` (synchronisé avec le Mac de Joseph) empêche la
suppression de fichiers une fois écrits — ce qui bloquait systématiquement Git dès qu'un
`index.lock`/`HEAD.lock` restait après une commande interrompue, avec l'erreur "File exists".

**Solution de contournement** : `mv` (renommer) fonctionne là où `rm` échoue avec ce dossier —
donc renommer le fichier de verrou plutôt que le supprimer, avant de relancer la commande Git.

## 9. Branches divergentes après des commits automatiques

**Problème** : le pipeline pousse automatiquement son état (`automation/state/...`) après chaque
run réel, ce qui a fini par diverger des commits locaux faits en parallèle pendant les tests.

**Solution** : `git pull --no-rebase origin main` pour fusionner proprement (pas de conflit réel,
juste des fichiers de debug/état des deux côtés).

## 10. Le portail admin n'affichait pas la proposition EN 18286

**Cause n°1** : le portail (`admin.html`) charge `data.json`/`proposals.json`/`proposals-fr.json`
en `fetch()` relatif — donc depuis la copie locale ou le déploiement consulté, jamais via l'API
GitHub. Résultat : tant que la copie locale n'était pas à jour (voir point 9), le portail
affichait des données périmées.

**Cause n°2, plus structurelle** : le site est probablement consulté via GitHub Pages
(`pages.yml`, déclenché sur chaque push vers `main`). Or les commits automatiques du pipeline sont
poussés avec le `GITHUB_TOKEN` fourni par GitHub Actions — et GitHub bloque volontairement le
déclenchement d'autres workflows par un push fait avec ce token précis (protection anti-boucle).
Donc ces commits-là ne redéploient jamais Pages tout seuls.

**Solution** : pousser les commits humains en attente (`git push`) a déclenché le redéploiement
Pages normalement, et le portail a fini par afficher la bonne proposition.

## 11. Vérifications de robustesse (pas des bugs, des garanties confirmées)

- **Suppression de carte** : approuver un `delete` dans le portail pousse immédiatement
  `decisions.json` (champ `deleted_cards`) sur GitHub — vérifié que `index.html` (site public) ET
  `admin.html` appliquent tous les deux ce filtre à l'affichage. Pas de risque de suppression
  "à moitié appliquée" ou visible d'un côté seulement.
- **Pas de logique codée en dur sur prEN 18286** : grep de toutes les occurrences de "18286" dans
  le code — seulement sa ligne dans `STANDARDS_REGISTER` (traitée comme les 19 autres), des
  commentaires explicatifs, et deux mentions pré-existantes (une requête Sonar, un exemple
  d'acronymes) jamais modifiées pendant cette investigation. Le mécanisme reste générique.
