# Demande de revue contradictoire Claude — pré-calcul REF-003

Date: 2026-07-27. REF-002 est close sous D-020 comme non-résultat technique. Aucun
score 13301..13312 n'a été lu ou agrégé. Aucun code, rendu, smoke 14991 ou graine
14301..14316 de REF-003 n'a été ouvert.

Relecteur demandé: Claude Opus 5.

Statut: demande exécutée. Verdict
`AUTORISER AVEC CORRECTIONS BLOQUANTES`, conservé dans
`docs/research/reafference_003_review.md`; C1–C8 et R1–R6 intégrées sous D-023.

Sortie produite: `docs/research/reafference_003_review.md`.

## Prompt exact

```text
Tu es le relecteur contradictoire pré-calcul de REF-003. Lis intégralement:
- docs/research/reafference_001_results_review.md;
- docs/research/reafference_002_preregistration.md;
- docs/research/reafference_002_review.md;
- docs/research/reafference_002_technical_stop.md;
- docs/research/reafference_003_preregistration.md;
- DECISIONS.md, en particulier D-019 à D-021;
- PILOTAGE.md;
- CODEX_TASK_BRIEF.md;
- DEVELOPMENTAL_ARCHITECTURE.md.

Contexte inviolable: REF-002 s'est arrêté sur une garde d'intégrité avant d'être
complet. Ses scores 13301..13312 sont interdits de lecture et REF-002 n'a aucun verdict
scientifique. Ne lance aucun rendu, entraînement, test expérimental ou calcul sur les
graines réservées.

Vérifie d'abord:
1. que REF-003 reteste légitimement une hypothèse non testée, sans retuning issu de
   résultats REF-002;
2. que le monde REF3, le smoke 14991, les graines 14301..14316 et la graine statistique
   sont neufs et disjoints;
3. que les seules modifications scientifiques déclarées concernent l'intégrité, la
   visibilité de la manipulation, le monde, les graines et le coût des rendus.

Audite ensuite contradictoirement:
- la disjonction par provenance, espaces RNG, pièces et digest de paire;
- la définition du digest de paire et du tuple (paire, tenseur moteur, provenance);
- le choix de rendre les collisions de trames individuelles descriptives lorsque
  paires et provenances sont distinctes;
- la possibilité qu'une fuite ou duplication réelle échappe encore à ces gardes;
- la visibilité contrefactuelle par paire external_only/mixed, en particulier le seuil
  individuel 0,01, la moyenne par bin 0,05 et l'interdiction de resampling;
- l'assurance que trames contrefactuelles, états objet et mesures de visibilité restent
  strictement inaccessibles aux cinq méthodes;
- l'équité des trois JEPA, l'information pré-transition, l'interdiction de l'angle
  futur et la définition analytique de yaw_warp;
- l'appariement des calendriers moteurs, seuils, scores, masques et conditions;
- H1, H3, H4, H5, SANITY-EXTERNAL, la famille Holm et les règles de promotion;
- la capacité des gardes à attribuer un futur succès au transport spatial plutôt qu'à
  un artefact visuel, moteur ou de calibration;
- la faisabilité et la pertinence du plafond initial de 90 minutes, compte tenu des
  1 536 rendus contrefactuels par graine et de la formule de projection;
- les règles d'arrêt, de non-remplacement, de non-analyse partielle et de clôture.

Cherche activement les fuites, asymétries d'information, définitions non implémentables,
seuils insuffisamment justifiés, portes devenues vides et degrés de liberté post hoc.
Dis explicitement si la correction REF-003 est neutre entre modèles ou si elle peut
favoriser transport_jepa.

Rends un verdict unique:
- AUTORISER;
- AUTORISER AVEC CORRECTIONS BLOQUANTES;
- NE PAS AUTORISER.

Pour chaque correction bloquante, fournis un texte normatif directement intégrable au
pré-enregistrement. Sépare les remarques non bloquantes. Écris uniquement
docs/research/reafference_003_review.md. Ne modifie aucun autre fichier et ne lance
aucun calcul.
```
