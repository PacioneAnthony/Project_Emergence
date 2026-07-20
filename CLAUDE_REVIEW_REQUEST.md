# Demande de revue contradictoire Claude — résultats J6-R001

Date: 2026-07-20

## Contexte

Le pré-enregistrement a reçu le verdict « AUTORISER AVEC CORRECTIONS BLOQUANTES »; B1, B2 et B3 ont été intégrés avant le smoke et avant toute graine réservée. Le smoke 10991 est vert. La campagne appariée 10301..10312 est terminée, sans changement des graines, budgets, ratio 50/50, priorités, seuils ni portes. Aucune promotion n'a encore été faite.

## Fichiers à lire

- `docs/research/j6_replay_001_preregistration.md`
- `docs/research/j6_replay_001_review.md`
- `docs/research/j6_replay_001_results.md`
- `docs/research/j6_replay_001_analysis.json`
- `docs/research/j6_replay_001_runs.json`

## Prompt exact

```text
Tu es le relecteur contradictoire de J6-R001. Lis intégralement docs/research/j6_replay_001_preregistration.md, docs/research/j6_replay_001_review.md, docs/research/j6_replay_001_results.md, docs/research/j6_replay_001_analysis.json et docs/research/j6_replay_001_runs.json. Vérifie l'intégrité des 12 triplets/36 runs, l'application littérale des portes gelées H1A/H1B/H2/H3, de la garde apprenant, de B1 (oubli mesurable et NON INTERPRÉTABLE sinon), de B2 (régression absolue co-primaire et accord de signe sur B), de B3, et de la garde TV +5 points. Recherche les erreurs de calcul ou d'interprétation et distingue absence d'effet, non-interprétabilité et échec. Réponds par un verdict unique AUTORISER / AUTORISER AVEC CORRECTIONS / NE PAS AUTORISER, liste les corrections bloquantes éventuelles, puis dis explicitement si uniform_replay et/ou error_prioritized_replay peuvent être promus. Ne propose aucun retuning post hoc sur 10301..10312.
```
