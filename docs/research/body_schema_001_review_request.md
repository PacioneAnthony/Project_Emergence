# Demande de revue Claude Opus 5 — BODY-SCHEMA-001

Date: 2026-07-27
Statut: prête; aucun code ou calcul BODY-SCHEMA-001

## Prompt exact

Tu es le relecteur contradictoire pré-calcul de BODY-SCHEMA-001. Lis intégralement:

- `docs/research/body_schema_001_preregistration.md`;
- `docs/research/life_012_technical_stop.md`;
- `docs/research/life_012_review.md`;
- `docs/research/life_011_technical_stop.md`;
- `CODEX_TASK_BRIEF.md`;
- `DEVELOPMENTAL_ARCHITECTURE.md`, notamment définition du succès et J1/J5;
- `learning/life_010.py`, `learning/life_010_campaign.py`;
- `learning/paired_stats.py`;
- `sim3d/bench_env.py`, `sim3d/bench_model.py`;
- `DECISIONS.md`, D-043 à D-047.

Écris uniquement `docs/research/body_schema_001_review.md`. Ne lance aucune simulation,
aucun test, aucun entraînement et aucune graine 19091+.

Audite en priorité:

1. légitimité du retour J1 et absence de retuning déguisé de LIFE;
2. capacité réelle du bootstrap par trials à corriger le défaut 24/24 refus;
3. validité de la protection sur six trials publics réutilisés;
4. définition de l'incertitude, du MAD et de la calibration conformelle;
5. équité des quatre modèles et disjonction des banques;
6. validité de la banque actionneur bloqué et du score de faute;
7. satisfaisabilité et puissance des portes smoke/H1–H5;
8. statistiques, familles Holm et non-infériorité;
9. toute fuite de paramètres, sous-spécification ou revendication excessive.

Rends `AUTORISER`, `AUTORISER AVEC CORRECTIONS BLOQUANTES` ou `REFUSER`. Pour toute
correction, fournis un texte normatif directement intégrable. Code et graines restent
interdits avant intégration complète.
