# Demande de revue contradictoire Claude Opus 5 — LIFE-012

Date: 2026-07-27
Statut: prête; aucun code, smoke ou calcul LIFE-012 lancé

## Prompt exact

Tu es le relecteur contradictoire pré-calcul de LIFE-012. Lis intégralement:

- `docs/research/life_012_preregistration.md`;
- `docs/research/life_011_review.md`;
- `docs/research/life_011_technical_stop.md`;
- `docs/research/life_011_preregistration.md`;
- `docs/research/life_010_technical_stop.md`;
- `docs/research/kernel_001_implementation.md`;
- `DEVELOPMENTAL_ARCHITECTURE.md`;
- `DECISIONS.md`, D-040 à D-044;
- `learning/life_010.py`, `learning/life_010_campaign.py`;
- `learning/life_011.py`, `learning/life_011_campaign.py`;
- `cognitive/observed_signals.py`, `sim3d/bench_env.py`.

Écris uniquement ta revue dans `docs/research/life_012_review.md`. Ne modifie aucun
autre fichier et ne lance aucune simulation, aucun test, aucun entraînement ni aucune
graine. Une arithmétique littérale des plans est permise.

Audite en priorité:

1. si LIFE-012 est un essai légitime ou un contournement post hoc de l'échec à 4,4039 %;
2. exactitude des coûts, changements, pas mobiles, renversements et maintiens v4 aux
   cadences 4,8/12,0/14,4°;
3. plausibilité mécanique que de vrais plateaux distinguent gain et amortissement;
4. compatibilité des cibles avec `boundary_exposure` et de `0,046875` avec motor_cost;
5. conservation réelle de B1–B6 LIFE-011, des protections et des familles statistiques;
6. suffisance de la plaque de marge pour empêcher une troisième campagne sans
   opportunité de sélection;
7. risques de dilution du banc par les maintiens et validité des diagnostics
   mobile/inerte;
8. toute fuite, sous-spécification ou revendication excessive.

Rends un verdict explicite:

- `AUTORISER`;
- `AUTORISER AVEC CORRECTIONS BLOQUANTES`;
- `REFUSER`.

Si des corrections sont nécessaires, fournis un texte normatif directement intégrable.
L'implémentation et les graines `18791+` restent interdites avant intégration de toutes
les corrections bloquantes.
