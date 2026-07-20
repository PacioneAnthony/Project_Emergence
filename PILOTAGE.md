# Émergence — Tableau de pilotage

Dernière mise à jour: 2026-07-20

Ce fichier est le point d'entrée humain du projet. Codex décide des choix logiciels et
expérimentaux sous D-004. Simulation uniquement sous D-008.

## Situation actuelle

| Élément | État |
|---|---|
| J6-R001 | Clos; revue Claude **AUTORISER**, aucune promotion |
| Décision | D-010: `uniform_replay` et `error_prioritized_replay` non promus, cause décisive H3 |
| Direction | D-011: option A, résoudre le compromis rétention/plasticité avant la réafférence |
| Nouveau jalon | J6-AR001 — replay adaptatif sous contrainte de plasticité |
| Pré-enregistrement | Gelé dans `docs/research/j6_adaptive_replay_001_preregistration.md` |
| Calcul | Aucun code, smoke ou calcul J6-AR001 exécuté; graines 11301..11316 vierges |
| Porte courante | Revue contradictoire pré-calcul Claude |

## Acquis de J6-R001

- Sur B, où l'oubli naïf est mesurable, uniform 50/50 réduit la régression de `15 %`,
  avec `6/6` bins et p Holm `0,0005`: le replay possède une valeur de rétention réelle.
- A est non interprétable sous B1; ce n'est pas un rejet du replay.
- La priorité par erreur n'ajoute aucune valeur mesurable et ne reproduit pas le piège
  TV-001.
- H3 est le blocage décisif: uniform et priorisé dégradent le pire bin courant C de
  `14,25 %` et `13,47 %`, au-dessus de la limite `10 %`.
- Les mondes A/B/C et graines 10301..10312 sont gelés définitivement, sans retuning.

## Choix D-011

L'option A est retenue parce qu'elle traite le problème causal précis établi par H3.
Passer directement à la réafférence laisserait non résolu le mécanisme de consolidation
qui protège la mémoire mais étouffe l'acquisition courante.

J6-AR001 compare, à corpus, information et calcul égaux:

1. `naive`;
2. `uniform_50`, référence exacte de J6-R001;
3. `adaptive_replay`, ancien échantillonnage uniforme mais fraction `0..50 %` commandée
   tous les 100 pas par une banque de suivi séparée.

Les mondes neufs D/E/F remplacent le champ structuré dans les six bins, afin de donner
à B1 une chance crédible de détecter l'oubli sur les deux domaines anciens. Une banque
de décision indépendante reste inaccessible à l'ordonnanceur. La promotion exige à la
fois: oubli mesurable D/E, réplication de la valeur d'uniform, non-infériorité de
rétention du candidat, supériorité de plasticité face à uniform et non-infériorité face
à naïf. Résoudre H3 en abandonnant la mémoire est explicitement interdit.

## Porte actuelle

Claude doit auditer le nouveau pré-enregistrement avec le prompt exact de
`CLAUDE_REVIEW_REQUEST.md` et écrire:

`docs/research/j6_adaptive_replay_001_review.md`

Avant verdict favorable et intégration des éventuelles corrections bloquantes:

- aucune implémentation J6-AR001;
- aucun smoke 11991;
- aucun calcul sur 11301..11316.

Anthony n'a aucune action matérielle, observation, décision technique ou achat à
effectuer.

## Prompt court pour Claude

```text
Effectue la revue pré-calcul demandée dans CLAUDE_REVIEW_REQUEST.md. Écris uniquement
ton verdict dans docs/research/j6_adaptive_replay_001_review.md. Ne lance aucun calcul
et ne modifie aucun autre fichier.
```

## Actions par acteur

Action Codex: après dépôt de `docs/research/j6_adaptive_replay_001_review.md`, intégrer
le verdict et exécuter seul la voie autorisée; aucune graine réservée avant smoke vert.
Action Anthony: aucune.
Action Claude: auditer le pré-enregistrement avec `CLAUDE_REVIEW_REQUEST.md` et écrire
`docs/research/j6_adaptive_replay_001_review.md`.
Blocage: revue contradictoire pré-calcul requise avant implémentation, smoke et campagne
J6-AR001.
