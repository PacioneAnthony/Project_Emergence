# Demande de revue contradictoire Claude — pré-calcul REF-002

Date: 2026-07-26. REF-001 est close sous D-015/D-016. Aucun code REF-002, smoke 13991
ou graine 13301..13316 n'a été ouvert.

Relecteur demandé: Claude Opus 5.

Sortie unique attendue: `docs/research/reafference_002_review.md`.

## Prompt exact

```text
Tu es le relecteur contradictoire pré-calcul de REF-002. Lis intégralement
docs/research/reafference_001_results_review.md,
docs/research/reafference_002_preregistration.md, CODEX_TASK_BRIEF.md,
DEVELOPMENTAL_ARCHITECTURE.md, DECISIONS.md (D-015 à D-017) et PILOTAGE.md.

Vérifie d'abord que REF-002 est une hypothèse réellement neuve et non un retuning de
REF-001, que les graines/mondes sont vierges, et qu'aucune valeur 12301..12316 ne règle
le protocole. Audite ensuite:
- la définition exacte du transport spatial et l'équité paramétrique des trois JEPA;
- l'information disponible avant transition, sans angle futur ni état objet;
- la force et l'équité de yaw_warp et des autres baselines recevant la même information;
- l'appariement des distributions motrices entre banques et l'absence du décalage de
  domaine identifié dans REF-001;
- les deux calibrations statique/mobile, seuils, égalités et masques valides;
- H1–H5, les douze tests sous Holm, directions, agrégations et tailles d'effet;
- les gardes exportées d'action utile, indépendance, visibilité, domaine, fuite,
  équité, warp, apprenant et budget;
- la faisabilité du smoke complet, de la projection à 48 runs et du plafond incluant
  désormais l'évaluation;
- les règles de promotion, arrêt, clôture et limites de revendication.

Cherche activement les fuites, baselines hors domaine, asymétries d'information,
définitions non implémentables et issues post hoc. Réponds par AUTORISER, AUTORISER
AVEC CORRECTIONS BLOQUANTES ou NE PAS AUTORISER. Écris uniquement
docs/research/reafference_002_review.md. Ne modifie aucun autre fichier et ne lance
aucun calcul.
```
