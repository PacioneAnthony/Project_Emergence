# Émergence — Tableau de pilotage

Dernière mise à jour: 2026-07-20

Codex décide des choix logiciels et expérimentaux sous D-004. Simulation uniquement
sous D-008.

## Situation actuelle

| Élément | État |
|---|---|
| J6-R001 | Clos; valeur de rétention établie sur B, aucune promotion à cause de H3 |
| J6-AR001 | Clos par D-012 comme **non-résultat technique** après plafond de 75 min |
| Intégrité J6-AR001 | C1–C4 intégrées; 181 tests et smoke 11991 verts; aucune analyse partielle |
| Direction | D-013: étape 3, réafférence visuelle |
| Nouveau jalon | REF-001 — séparer changement auto-produit et changement externe |
| Pré-enregistrement | Gelé dans `docs/research/reafference_001_preregistration.md` |
| Calcul REF-001 | Aucun code, smoke ou calcul; 12301..12316 restent vierges |
| Porte courante | Revue contradictoire pré-calcul Claude |

## Clôture de J6-AR001

Après le smoke vert, le runner a atteint le plafond gelé pendant `adaptive_replay` de
11313. Les graines 11301..11312 ont trois conditions complètes; 11313 n'a que deux runs
complets; 11314..11316 n'ont pas été ouvertes. Le protocole exigeait 16 triplets.

Il n'y a donc ni calcul des portes, ni rapport scientifique, ni promotion, ni rejet de
l'hypothèse adaptative. Le plafond n'est pas étendu et la campagne n'est pas reprise.
Les détails auditables sont dans
`docs/research/j6_adaptive_replay_001_technical_stop.md`.

## REF-001 gelé

REF-001 compare deux JEPA de capacité et budget identiques — avec action et avec action
mise à zéro — ainsi qu'une baseline analytique `pixel_change`. Un vrai objet MJCF suit
une trajectoire indépendante du babbling; son état et ses labels ne sont jamais fournis
aux modèles.

Les cinq banques tenues à part séparent calibration du seuil, test du mouvement propre,
changement externe pur, mouvement mixte et garde apprenant. La promotion exige à la fois:

- une meilleure explication du mouvement propre par l'action;
- une TPR externe supérieure aux deux baselines en externe pur et mixte;
- une FPR tenue à part basse;
- toutes les gardes d'apprentissage, visibilité, indépendance, fuite, équité et budget.

Smoke hors protocole: 12991. Campagne réservée: 12301..12316. Aucun de ces calculs ne
peut commencer avant revue favorable et intégration des corrections bloquantes.

## Prompt court pour Claude

```text
Effectue la revue pré-calcul demandée dans CLAUDE_REVIEW_REQUEST.md. Écris uniquement
la revue dans docs/research/reafference_001_review.md. Ne lance aucun calcul et ne
modifie aucun autre fichier.
```

## Actions par acteur

Action Codex: après dépôt de `docs/research/reafference_001_review.md`, intégrer le
verdict puis exécuter seul la voie autorisée; aucune graine réservée avant smoke vert.
Action Anthony: aucune.
Action Claude: auditer REF-001 avec le prompt exact de `CLAUDE_REVIEW_REQUEST.md` et
écrire `docs/research/reafference_001_review.md`.
Blocage: revue contradictoire pré-calcul requise avant implémentation, smoke 12991 et
campagne 12301..12316.
