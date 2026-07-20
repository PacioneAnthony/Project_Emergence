# Émergence — Handoff de session

Date: 2026-07-20

## Instruction de reprise impérative

Lire dans cet ordre:

1. `PILOTAGE.md`
2. `SESSION_HANDOFF.md`
3. `DEVELOPMENTAL_ARCHITECTURE.md`
4. `CODEX_TASK_BRIEF.md`
5. `docs/research/j6_replay_001_results_review.md`
6. `DECISIONS.md` — D-010 et D-011
7. `docs/research/j6_adaptive_replay_001_preregistration.md`
8. `CLAUDE_REVIEW_REQUEST.md`
9. `docs/research/j6_adaptive_replay_001_review.md`, si disponible

Si la nouvelle revue existe, appliquer immédiatement son verdict. Sinon, maintenir la
porte: ne pas implémenter J6-AR001, ne pas lancer le smoke 11991 et ne jamais ouvrir les
graines 11301..11316. D-004 délègue à Codex les choix techniques; D-008 interdit toute
action physique, tout flash et tout achat.

## État scientifique validé

J6-R001 est clos par `docs/research/j6_replay_001_results_review.md`, verdict
**AUTORISER**, aucune correction bloquante et aucune promotion:

- B1 passe sur B et H1B démontre la valeur de rétention d'uniform 50/50: gain relatif
  `0,1506`, `6/6` bins, p Holm `0,000488`, accord absolu B2.
- A est NON INTERPRÉTABLE parce que l'oubli naïf moyen (`0,0397`) reste sous `0,05`.
- H2 est nul: aucune valeur ajoutée démontrée de la priorité; la garde TV passe et le
  piège TV-001 ne s'est pas reproduit.
- H3 échoue pour uniform et priorisé: pires bins C `+14,25 %` et `+13,47 %` contre
  limite `10 %`; non-infériorité non établie après Holm.
- D-010 gèle la non-promotion, les mondes A/B/C, les graines 10301..10312 et tous leurs
  artefacts. Aucun retuning ni rejeu n'est autorisé.
- Les recommandations éditoriales R1–R3 ont été intégrées dans
  `docs/research/j6_replay_001_results.md` sans changer les données ni les portes.

## Direction choisie sous D-004

D-011 retient l'option A avant l'étape 3 de réafférence. Justification: J6-R001 a isolé
un bénéfice mémoire et un coût de plasticité réels; le mécanisme de consolidation reste
donc le problème causal actif. Cette voie ne change pas l'objectif général et ne demande
aucun arbitrage Anthony.

La campagne neuve s'appelle **J6-AR001**. Son pré-enregistrement est gelé dans
`docs/research/j6_adaptive_replay_001_preregistration.md`, avant tout code et calcul.

## Protocole J6-AR001 gelé

- Smoke hors protocole `11991`; campagne vierge `11301..11316`, 16 triplets.
- Mondes neufs D/E/F: six panneaux physiques MJCF couvrant chacun des bins structurés,
  motifs et lumières distincts; mêmes objets de fond par épisode entre domaines.
- Trois conditions seulement: `naive`, `uniform_50`, `adaptive_replay`.
- Corpus partagé: 12 000 images et 2 400 décisions par condition.
- Calcul égal: 1 500 pas AdamW/session, batch 256, 4 500 pas/condition; mêmes
  évaluations de suivi dans les trois conditions.
- Plafond: 48 runs, 75 minutes GPU cumulées, reprise au niveau run et keep-awake.
- B3: branches bit-identiques jusqu'à la fin de D via un checkpoint partagé.
- Trois ensembles disjoints par graine/domaine: entraînement, banque de suivi et banque
  finale de décision, avec 64 ancres par compétence et par banque.

### Candidat adaptatif

Tous les 100 pas, une banque de suivi séparée mesure:

```text
d_old = pire régression positive d'une compétence ancienne depuis son acquisition
d_current = pire déficit positif vers 20 % d'acquisition depuis le début de session
q = 0.5 * d_old / (d_old + d_current + 1e-3)
rho = q arrondi au 1/16, borné dans [0, 0.5]
```

Le batch suivant emploie `256×rho` anciennes paires, échantillonnées uniformément par
épisode, et le reste courant. Il n'existe aucune priorité d'épisode, accès à la banque
finale, nouveauté ou quatrième condition. `naive` et `uniform_50` calculent et reçoivent
les mêmes erreurs de suivi mais appliquent leur règle fixe.

### Portes indivisibles

- B1 doit détecter un oubli naïf `≥0,05`, borne BCa basse positive, sur D **et** E.
- Uniform doit répliquer un gain de rétention `≥0,05` sur D/E.
- Adaptive doit être non inférieur à uniform sur D/E, marge `0,02`, sans bin perdant
  plus de `0,05`; B2 exige l'accord absolu/relatif.
- Adaptive doit améliorer l'erreur F de `≥0,05` relatif face à uniform et rester non
  inférieur à naïf dans une marge `5 %`, sans bin F au-delà de `10 %`.
- Gardes: apprenant 20 %, activation effective dans E/F sur 12/16 graines, TV +5 points,
  construction, séparation des banques, information/calcul, budgets et plafond.
- Tests exacts appariés, BCa 10 000, Holm et effets via `learning/paired_stats.py`.

Toute garde ou hypothèse manquée interdit la promotion. En particulier, une meilleure
plasticité obtenue en abandonnant la rétention échoue H2. Quelle que soit l'issue,
J6-AR001 clôt cette variante adaptative unique; la réafférence redevient ensuite la
suite par défaut, sauf besoin de réplication d'un mécanisme promu.

## Porte Claude préparée

`CLAUDE_REVIEW_REQUEST.md` contient le contexte, les fichiers et le prompt exact. Sortie
attendue: `docs/research/j6_adaptive_replay_001_review.md`.

La revue doit notamment auditer le caractère neuf des mondes/graines, la plausibilité
de B1 D/E sans calibration smoke, l'équité information/calcul, les fuites entre banques,
la causalité de `rho`, les directions/marges statistiques et les règles empêchant une
fausse résolution de H3.

## Contexte durable

- TV-001 et `regional_lp_gain` restent gelés par D-009; la sonde motivation
  encodeur gelé/plastique demeure dormante.
- La famille fractionnelle et la navigation 2D sont historiques.
- J0/J1 physiques restent spécifiés mais suspendus sous D-008; D-005 interdit tout
  nouvel essai moteur sur le banc v0.1.
- L'étape 3 du brief reste la prochaine capacité développementale après clôture de la
  question de consolidation.

## Actions par acteur

Action Codex: après dépôt de `docs/research/j6_adaptive_replay_001_review.md`, intégrer
le verdict, puis implémenter/tester/exécuter uniquement ce qu'il autorise.
Action Anthony: aucune.
Action Claude: exécuter le prompt exact de `CLAUDE_REVIEW_REQUEST.md` et écrire
`docs/research/j6_adaptive_replay_001_review.md`.
Blocage: revue contradictoire pré-calcul requise avant implémentation, smoke 11991 et
campagne 11301..11316.
