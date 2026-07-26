# Émergence — Handoff de session

Date: 2026-07-26

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
9. `docs/research/reafference_001_review.md`
10. `docs/research/reafference_001_results.md`
11. `docs/research/reafference_001_analysis.json`
12. `docs/research/reafference_001_integrity.json`
13. `CLAUDE_REVIEW_REQUEST.md`
14. `DECISIONS.md` — D-014 et D-015

REF-001 est maintenant close sous D-015. Ne relancer aucun run, ne modifier aucun seuil
et ne réutiliser aucune graine 12301..12316. La revue contradictoire des résultats est
préparée dans `CLAUDE_REVIEW_REQUEST.md`. D-004 délègue à Codex les choix techniques;
D-008 interdit toute action physique, tout flash et tout achat.

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

## REF-001 — clôture expérimentale

D-013 passe à l'étape 3 du brief. La question est de savoir si le résidu d'un JEPA
conditionné par l'action explique le mouvement propre tout en détectant un objet dont le
mouvement est externe et indépendant.

Le pré-enregistrement `docs/research/reafference_001_preregistration.md` est gelé avant
implémentation:

- monde REF neuf avec vrai objet geom/joint MJCF sur rail horizontal;
- RNG objet distinct et corrélation absolue action–déplacement `≤0,05`;
- smoke 12991; campagne 12301..12316, n=16, maintenant complète;
- `action_jepa` contre `no_action_jepa` à capacité/calcul identiques;
- baselines simples obligatoires `pixel_change` et `pixel_change_action`;
- 12 000 images, 2 400 décisions, 4 500 pas AdamW par condition, batch 256;
- cinq banques disjointes de 128 paires par bin: calibration, self-test, externe pur,
  mixte et validation apprenant;
- seuil propre à chaque méthode/graine/bin, calibré uniquement sur le mouvement propre;
- H1: avantage d'erreur propre `≥0,05`;
- H2/H3: TPR action absolue `≥0,75/0,70` et avantage `≥0,10` face à chaque baseline;
- H4: FPR self-test globale `≤0,07`, aucun bin `>0,10`;
- six tests de supériorité sous Holm commun, IC BCa et tests exacts appariés;
- plafond 32 runs / 60 minutes, sans analyse partielle en cas d'arrêt.

La campagne complète a rendu un verdict mécanique négatif:

- smoke 12991 vert, 193 tests, projection 31,48 minutes;
- 16 paires / 32 runs complets en 31,80 minutes;
- H1 faux: `−0,00182`, IC BCa `[−0,00666; 0,00287]`, p `0,757`, 2/6 bins;
- H2 faux: TPR externe action `0,37077`; action bat les pixels mais pas no-action;
- H3 faux: TPR mixte action `0,14266`, aucune supériorité robuste;
- H4 faux: FPR globale `0,06372`, mais max bin `0,11865`;
- gardes apprenant et indépendance vraies.

La revendication de réafférence n'est donc pas établie. REF-001 est close sans
promotion et sans retuning. Les résultats restent à auditer contradictoirement.

## Porte Claude des résultats préparée

`CLAUDE_REVIEW_REQUEST.md` demande de recalculer H1, les six comparaisons H2/H3 sous
Holm, les TPR absolues et H4, puis d'auditer les gardes, budgets, fuites, seuils,
diagnostics et plafond depuis l'export d'intégrité versionné. Aucune promotion n'est
proposée et aucun retuning sur les graines réservées n'est permis.

## Contexte durable

- J6-R001 reste clos sans promotion: uniform protège B, mais H3 échoue.
- J6-AR001 reste clos sans résultat scientifique sous D-012.
- TV-001 et `regional_lp_gain` restent gelés par D-009.
- J0/J1 physiques restent suspendus sous D-008; D-005 interdit tout nouvel essai moteur
  sur le banc v0.1.
- La clôture REF-001 doit encore être auditée contradictoirement; aucune promotion
  n'est possible d'après les portes mécaniques.

## Actions par acteur

Action Codex: intégrer la revue contradictoire des résultats puis choisir la prochaine
hypothèse; ne jamais reprendre REF-001.
Action Anthony: aucune.
Action Claude: exécuter le prompt exact de `CLAUDE_REVIEW_REQUEST.md`.
Blocage: revue contradictoire requise avant la prochaine direction; aucun calcul
REF-001 supplémentaire n'est autorisé.
