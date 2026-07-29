# Compliance-timeline — notes pour Claude

## Git : la routine de push à utiliser à chaque fois

`decisions.json` est réécrit et poussé automatiquement à chaque clic
Approve/Reject/Undo dans `admin.html`, depuis n'importe quel navigateur/onglet
(Joseph, Manon, ou l'agent qui teste). Résultat : `origin/main` bouge souvent,
même sans qu'un humain touche à git directement. Un `git push` "à sec" (sans
avoir re-pull juste avant) se fait donc rejeter régulièrement — c'est normal,
pas un bug. Toujours utiliser cette séquence complète, jamais un `git push`
isolé :

```bash
rm -f .git/index.lock .git/HEAD.lock
git pull --no-rebase origin main
if [ -f .git/MERGE_HEAD ]; then git commit --no-edit; fi
git push origin main
```

Si le push est quand même rejeté ("fetch first" / "non-fast-forward"), ce
n'est PAS le bug de verrou ci-dessous — c'est juste que quelqu'un a poussé
entre ton pull et ton push (probablement une approbation synchronisée depuis
`admin.html`). Relance simplement toute la séquence une deuxième fois.

## Git : fichiers verrou bloqués (index.lock / HEAD.lock)

Ce dossier est parfois édité depuis deux environnements différents en
parallèle : le Mac de Joseph (terminal normal) et un agent Claude tournant
dans un bac à sable (sandbox) qui monte ce même dossier. Le sandbox a une
restriction technique : il ne peut pas toujours supprimer certains fichiers
(seulement les renommer ou les écraser).

Chaque commande git crée des fichiers verrou temporaires (`.git/index.lock`,
`.git/HEAD.lock`) qu'elle supprime normalement toute seule à la fin. Depuis le
sandbox, cette suppression échoue parfois silencieusement — le verrou reste
sur le disque même si l'opération a réussi. Le prochain `git pull`/`push`
lancé depuis le Mac (ou l'inverse) trouve ce verrou et refuse de continuer,
avec une erreur du style :

```
erreur : Impossible de créer '.git/index.lock' : File exists.
Un autre processus git semble en cours dans ce dépôt, ou le fichier verrou est obsolète
```

La routine du dessus (`rm -f .git/index.lock .git/HEAD.lock` en premier)
couvre déjà ce cas.

`rm -f` sur un fichier `.lock` ne touche jamais le code ni l'historique —
c'est juste un fichier témoin que git oublie parfois d'effacer.

### Cas plus rare : "Vous n'avez pas terminé votre fusion (MERGE_HEAD existe)" alors qu'aucun merge réel n'est en cours

Même problème d'unlink que pour les `.lock`, mais sur un ancien merge déjà
conclu : `.git/MERGE_HEAD` reste bloqué sur le disque. Se reconnaît si
`git diff HEAD <sha du MERGE_HEAD>` ne montre aucune vraie divergence de
contenu utile, ou si ce merge a déjà été commité par ailleurs. Fix :
```bash
rm -f .git/MERGE_HEAD .git/MERGE_MSG .git/MERGE_MODE
```
puis relancer la routine du dessus normalement.

### Politique pour l'agent Claude (côté sandbox)

Pour éviter de recréer ce problème : l'agent ne doit **pas** lancer lui-même
de commandes git d'écriture (`add`, `commit`, `merge`, `pull`, `push`) dans ce
dossier partagé. Il édite les fichiers avec ses outils habituels, puis donne
à Joseph la séquence de commandes git exacte à lancer depuis son propre
terminal. Un seul environnement (celui de Joseph, sans restriction) touche
alors `.git`, ce qui supprime la cause du problème.

## `automation/UAT-FEEDBACK-MANON.md`

Ce fichier reste **local uniquement**, sur demande explicite de Joseph
("je le garde chez moi") — ne jamais le `git add`/committer/pousser, même
dans un commit groupé.
