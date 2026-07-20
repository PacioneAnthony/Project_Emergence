# Émergence — Tableau de pilotage

Dernière mise à jour: 2026-07-20

Ce fichier est le point d'entrée humain du projet. Les choix logiciels et expérimentaux
relèvent de Codex (D-004). Le chemin reste intégralement simulé sous D-008.

## Situation actuelle

| Élément | État |
|---|---|
| Jalon actif | J6-R001 — revue contradictoire des résultats |
| Pré-calcul | Amendements B1/B2/B3 intégrés mot pour mot avant le smoke et toute graine réservée |
| Implémentation | Domaines MJCF A/B/C, corpus babbling partagé, ancres tenues à part et trois consolidations terminés |
| Vérifications | 175 tests verts; smoke hors protocole 10991 vert sur les sept contrôles requis |
| Campagne | 12 triplets 10301..10312, 36 runs complets, 26,9 min cumulées (< 90 min) |
| Résultat mécanique | Aucune condition promue; revue Claude obligatoire avant décision |
| Responsable courant | Claude, pour la revue contradictoire préparée dans `CLAUDE_REVIEW_REQUEST.md` |

## Lecture des résultats gelés

- B1/A ne passe pas: la régression naïve moyenne sur A vaut `0,0397`, sous `0,05`.
  H1A est **NON INTERPRÉTABLE** car le monde n'a pas induit assez d'oubli; ce n'est pas
  un rejet du replay.
- B1/B passe (`0,1414`, borne basse BCa `0,0922`) et H1B passe: le replay uniforme
  réduit la régression relative de `0,1506`, borne basse `0,1066`, p Holm `0,000488`,
  `6/6` bins. La métrique absolue B (`0,0501`) s'accorde en signe avec la relative.
- H2 échoue sur A et B: aucune valeur ajoutée du replay priorisé n'est démontrée à cette
  puissance. Les moyennes relatives valent `-0,00005` et `0,00395`.
- H3 échoue pour uniform et priorisé après Holm; les pires bins C régressent de `14,25 %`
  et `13,47 %`, au-dessus de la limite régionale de `10 %`.
- Les gardes apprenant et télévision passent. Malgré H1B, les règles gelées n'autorisent
  ni uniform ni priorisé: H1A n'est pas interprétable et H3 échoue.

Le rapport lisible est `docs/research/j6_replay_001_results.md`. Les exports versionnés
`docs/research/j6_replay_001_analysis.json` et `docs/research/j6_replay_001_runs.json`
permettent à Claude d'auditer les calculs depuis le dépôt distant.

## Prochaine porte

Claude doit exécuter mot pour mot le prompt de `CLAUDE_REVIEW_REQUEST.md`. Aucune
promotion, aucun retuning et aucune nouvelle graine J6 ne sont autorisés avant son
verdict. Après dépôt de sa revue de résultats dans
`docs/research/j6_replay_001_results_review.md`, Codex intégrera seul le verdict,
mettra à jour les décisions et déterminera le prochain protocole conforme.

Anthony n'a aucune action physique à effectuer. Le banc, les achats et les flashs
restent suspendus sous D-008.

## Prompt court pour Claude

```text
Effectue la revue de résultats demandée dans CLAUDE_REVIEW_REQUEST.md. Lis tous les
fichiers versionnés qui y sont indiqués, puis écris ton verdict dans
docs/research/j6_replay_001_results_review.md. Ne modifie aucun autre fichier et ne
propose aucun retuning sur 10301..10312.
```

## Format obligatoire de fin de session

```text
Action Codex: ce que Codex exécute ensuite seul.
Action Anthony: manipulation/observation/achat précis; sinon « aucune ».
Action Claude: revue préparée avec fichier et prompt; sinon « aucune ».
Blocage: condition réelle empêchant la suite; sinon « aucun ».
```

## Actions par acteur

Action Codex: après dépôt de `docs/research/j6_replay_001_results_review.md`, auditer et
intégrer le verdict sans rouvrir ni régler J6 sur 10301..10312.
Action Anthony: aucune.
Action Claude: exécuter la revue préparée dans `CLAUDE_REVIEW_REQUEST.md` et écrire
`docs/research/j6_replay_001_results_review.md`.
Blocage: revue contradictoire des résultats requise avant toute promotion ou protocole
successeur.
