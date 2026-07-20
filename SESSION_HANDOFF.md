# Émergence — Handoff de session

Date: 2026-07-20

## Instruction de reprise impérative

Lire dans cet ordre:

1. `PILOTAGE.md`
2. `SESSION_HANDOFF.md`
3. `DEVELOPMENTAL_ARCHITECTURE.md`
4. `CODEX_TASK_BRIEF.md`
5. `DECISIONS.md` — D-012 et D-013
6. `docs/research/j6_adaptive_replay_001_review.md`
7. `docs/research/j6_adaptive_replay_001_technical_stop.md`
8. `docs/research/reafference_001_preregistration.md`
9. `CLAUDE_REVIEW_REQUEST.md`
10. `docs/research/reafference_001_review.md`, si disponible

Si la revue REF-001 existe, appliquer immédiatement son verdict. Sinon, maintenir la
porte: ne pas implémenter REF-001, ne pas lancer le smoke 12991 et ne jamais ouvrir les
graines 12301..12316. D-004 délègue à Codex les choix techniques; D-008 interdit toute
action physique, tout flash et tout achat.

## J6-AR001 — clôture technique

La revue pré-calcul a autorisé J6-AR001 après quatre amendements bloquants. C1–C4 ont été
intégrées avant code et calcul. L'implémentation a passé 181 tests et le smoke 11991,
notamment composition exacte des batchs, recomputabilité de `rho`, parité des suivis et
définition conditionnelle de la fraction TV.

La campagne a ensuite atteint le plafond pré-enregistré de 75 minutes pendant le run
`adaptive_replay` de 11313:

- 11301..11312: 12 triplets / 36 runs complets;
- 11313: `naive` et `uniform_50` complets, branche adaptative interrompue;
- 11314..11316: non ouvertes;
- 38 runs complets, mais seulement 12 des 16 triplets requis.

D-012 interdit l'extension du plafond, la reprise et toute analyse partielle. Aucune
porte B1/H1/H2/H3 n'a été calculée. L'hypothèse adaptative reste **non testée**, et non
rejetée. Les artefacts sont conservés uniquement pour audit technique.

## Direction active — REF-001

D-013 passe à l'étape 3 du brief. La question est de savoir si le résidu d'un JEPA
conditionné par l'action explique le mouvement propre tout en détectant un objet dont le
mouvement est externe et indépendant.

Le pré-enregistrement `docs/research/reafference_001_preregistration.md` est gelé avant
implémentation:

- monde REF neuf avec vrai objet geom/joint MJCF sur rail horizontal;
- RNG objet distinct et corrélation absolue action–déplacement `≤0,05`;
- smoke 12991; campagne vierge 12301..12316, n=16;
- `action_jepa` contre `no_action_jepa` à capacité/calcul identiques;
- baseline simple obligatoire `pixel_change`;
- 12 000 images, 2 400 décisions, 4 500 pas AdamW par condition, batch 256;
- cinq banques disjointes de 128 paires par bin: calibration, self-test, externe pur,
  mixte et validation apprenant;
- seuil propre à chaque méthode/graine/bin, calibré uniquement sur le mouvement propre;
- H1: avantage d'erreur propre `≥0,05`;
- H2/H3: TPR action absolue `≥0,75/0,70` et avantage `≥0,10` face à chaque baseline;
- H4: FPR self-test globale `≤0,07`, aucun bin `>0,10`;
- quatre tests de supériorité sous Holm commun, IC BCa et tests exacts appariés;
- plafond 32 runs / 60 minutes, sans analyse partielle en cas d'arrêt.

La revendication possible reste limitée à un détecteur opérationnel de changement
externe. Elle ne vaut ni segmentation, ni inférence générale de causalité ou d'agentivité.

## Porte Claude préparée

`CLAUDE_REVIEW_REQUEST.md` contient le contexte et le prompt exact. Claude doit écrire
uniquement `docs/research/reafference_001_review.md`, sans lancer de calcul ni modifier
un autre fichier. La revue doit auditer la clôture intègre de J6-AR001, la nouveauté des
graines/mondes, l'indépendance de l'objet, l'équité des baselines, les banques et fuites,
les seuils, métriques, statistiques, budgets et règles de promotion.

## Contexte durable

- J6-R001 reste clos sans promotion: uniform protège B, mais H3 échoue.
- J6-AR001 reste clos sans résultat scientifique sous D-012.
- TV-001 et `regional_lp_gain` restent gelés par D-009.
- J0/J1 physiques restent suspendus sous D-008; D-005 interdit tout nouvel essai moteur
  sur le banc v0.1.
- Toute promotion REF-001 exigera une seconde revue contradictoire des résultats.

## Actions par acteur

Action Codex: après dépôt de `docs/research/reafference_001_review.md`, intégrer le
verdict puis implémenter, tester et exécuter uniquement ce qu'il autorise.
Action Anthony: aucune.
Action Claude: exécuter le prompt exact de `CLAUDE_REVIEW_REQUEST.md` et écrire
`docs/research/reafference_001_review.md`.
Blocage: revue contradictoire pré-calcul requise avant implémentation, smoke 12991 et
campagne 12301..12316.
