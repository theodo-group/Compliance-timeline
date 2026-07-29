# Retours UAT de Manon (QARA) — questions, réponses, propositions

Synthèse de la session de test du portail admin et de la frise publique par Manon Thiberge,
avec les réponses apportées et ce qui est proposé comme suite.

## Workflow d'approbation → publication

| Question / retour de Manon | Réponse | Proposition |
|---|---|---|
| Le processus d'approbation/rejet est-il clair ? | Oui, clair pour elle. | Ajouter un champ de justification au moment du rejet, pour garder un historique de qui a rejeté quoi et pourquoi (utile à plusieurs utilisateurs). Pas encore fait. |
| L'édition du titre/description est-elle facile à trouver ? | Pas repérée au premier coup d'œil — seulement visible au survol de la souris. Facile une fois trouvée. | Rendre l'affordance d'édition plus visible (icône permanente plutôt qu'au survol seul). Pas encore fait. |
| Où ajoute-t-on un commentaire ? | Elle ne l'a pas trouvé. Réponse de Joseph : c'est dans l'onglet "Archivé". | Même remarque que l'édition : peu visible. À rendre plus découvrable. |
| Les news approuvées apparaissent-elles bien dans la frise publique ? | **Non — bug confirmé.** Elle a approuvé une news du 22/07 mais la frise affichait encore l'ancienne, datée fin 2026. | **Cause racine trouvée par Claude** : `admin.html` affiche "Approuvé" dès l'approbation, indépendamment de la réussite du push vers GitHub. Si le push échoue (fichier `decisions.json` modifié entre-temps par une autre session, `sha` périmé), l'échec n'est signalé que par un toast discret — aucun retry, aucune alerte bloquante. Vérifié en direct : `decisions.json` sur GitHub ne contenait aucune des approbations du run du 27/07. Fix proposé : sur échec, refaire un fetch du `sha` actuel et retenter automatiquement, remplacer le toast par une alerte persistante tant que la synchronisation n'est pas confirmée. **Pas encore fait — en attente de confirmation de Joseph.** |
| Pourquoi une proposition a le flag "supprimer" à côté d'un "ajouter" ? | C'est le mécanisme pour remplacer une fiche périmée par la version à jour (delete de l'ancienne + add de la nouvelle), pas une vraie fonction "update" côté timeline. | Idée de Joseph : faire le lien visuellement entre l'ancienne fiche supprimée et celle qui la remplace, pour que ce soit plus clair côté admin. Pas encore fait. |
| Pourquoi une date affichée en "Q4 2026" / "fin 2026" plutôt qu'une date précise ? | Une date vague est utilisée quand la source elle-même ne communique qu'un trimestre/une période, pas une date exacte — fidèle à la source, pas un bug en soi. L'exemple précis soulevé par Manon (prEN 18286 affiché "fin 2026") était en fait la conséquence du bug de synchronisation ci-dessus : elle voyait l'ancienne fiche, jamais remplacée. | Se résout automatiquement une fois le bug de synchronisation corrigé. |
| News MHRA peu claire : la date de fin 2026 correspond à quoi exactement (publication du cadre ? entrée en vigueur ? simples recommandations) ? | Retour de contenu légitime — la description ne précise pas assez explicitement la nature de l'échéance. | Ajouter une règle dans le prompt de rédaction : chaque description doit préciser explicitement ce qui se passe à la date donnée (publication, entrée en vigueur, échéance de mise en conformité...), pas seulement la date elle-même. Pas encore fait. |
| Le dernier "Updated" affiche avril 2026, vraiment ? | **Confirmé : texte statique codé en dur** dans `index.html`, jamais mis à jour automatiquement. | Le calculer dynamiquement (date du dernier commit sur `data.json`/`decisions.json`, ou date de génération de `proposals.json`), ou le retirer. Pas encore fait. |

## Ce qui manque / besoins produit

| Question | Réponse | Proposition |
|---|---|---|
| Quel grand besoin cet outil devrait-il remplir ? | Alimenter directement sa veille personnelle sur sa page Notion à partir des news qu'elle approuve. | Proposition de Joseph : elle met le lien de la frise publique dans son Notion, et demande à son propre Claude (connecteur Notion) de lire la page et d'éditer son Notion — pas de développement nécessaire côté pipeline. |
| Besoin d'ajouter une news manuellement de zéro ? | Rarement — seul cas : infos venant directement d'un comité de normalisation. | Remarque de Joseph : besoin rare mais réel, et probablement facile à développer. Pas encore fait, pas prioritaire. |
| Besoin de modifier une news déjà publiée après coup ? | Non, pas de besoin identifié. | Aucune action. |
| Métadonnées absentes utiles (type de document, deadline, fiabilité de la source) ? | Non — le type (guidance/règlement/norme) et les échéances sont déjà visibles via la newsletter et la frise. | Aucune action. |
| Manque-t-il une rubrique HDS / ISO 27001 / EHDS ? | HDS et la famille ISO 27001/27701 sont **déjà suivis** dans `STANDARDS_REGISTER` (vérifiés chaque semaine) et mentionnés dans une requête Sonar. EHDS n'a en revanche **pas sa propre ligne** de suivi permanent — seulement cité dans le texte d'une requête Sonar, malgré des jalons EHDS déjà présents dans la frise (2027, 2029). | Ajouter une ligne EHDS dédiée à `STANDARDS_REGISTER`, comme les autres réglementations. Pas encore fait — en attente de confirmation de Joseph. |

## Pertinence des propositions IA

| Question | Réponse | Proposition |
|---|---|---|
| Les sujets remontés correspondent-ils à sa veille manuelle ? Faux positifs, oublis ? | Oui globalement, à l'exception du point HDS/27001/EHDS ci-dessus. | Voir ligne EHDS ci-dessus. |
| Comment est déterminée la priorité (critical/high/medium) ? Sur un exemple, elle inverserait l'ordre proposé. | C'est un jugement de l'IA, pas toujours aligné avec le jugement métier. | C'est justement pour ça que le tag peut être corrigé manuellement dans le portail admin (mécanisme déjà existant). Aucune action supplémentaire nécessaire, sinon rappeler cette possibilité aux utilisateurs. |
| Le statut (in-force/draft/proposed) correspond-il à son jugement métier, ou faut-il souvent le corriger ? | Elle ne voit quasiment que des "in-force". Le statut n'apparaît pas sur toutes les news. | **Confirmé par Claude : aucune règle explicite dans le prompt** ne dit au modèle d'omettre le statut en cas de doute plutôt que de deviner — c'est actuellement un flou, pas un choix documenté. Proposition : ajouter une règle explicite — toujours un tag de priorité, et un tag de statut seulement si la source l'indique clairement, sinon l'omettre. Pas encore fait — en attente de confirmation de Joseph. |
| Idée d'amélioration : filtrer les news par priorité ou statut | — | Faisable facilement selon Joseph. Pas encore fait. |
| Les tags régionaux/thématiques (UE, US, UK, France, AI Act, standards, cyber...) sont-ils bien catégorisés ? | Oui. | Aucune action. |

## Fixes proposés, en attente de ton feu vert

1. Corriger la synchronisation silencieuse de `decisions.json` (retry automatique + alerte visible sur échec).
2. Rendre le "Updated [date]" du site public dynamique (ou le retirer).
3. Ajouter une ligne EHDS à `STANDARDS_REGISTER`.
4. Ajouter une règle explicite sur le tag de statut (l'omettre si incertain, ne jamais deviner).
5. Ajouter une règle sur la clarté des descriptions (préciser ce qui se passe à la date donnée).
