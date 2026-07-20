# Revue contradictoire J6-R001 — avant implémentation et calcul

Date: 2026-07-20. Revue demandée par `CLAUDE_REVIEW_REQUEST.md`, portant sur
`docs/research/j6_replay_001_preregistration.md` (rétention visuelle en monde non
stationnaire), le substrat réutilisé `learning/tv_exploration.py` /
`learning/train_visual_jepa.py`, `learning/paired_stats.py`,
`DEVELOPMENTAL_ARCHITECTURE.md` §9 et D-009. Aucun calcul lancé; aucun fichier autre
que la présente revue modifié.

## Verdict

**AUTORISER AVEC CORRECTIONS BLOQUANTES.**

Le protocole isole correctement la valeur du replay: motivation gelée, collecte
babbling identique bit à bit, budgets d'optimisation égaux, priorité par erreur
calculée sur les épisodes d'entraînement sans fuite d'ancres, métriques régionales
non moyennées, portes appariées exactes. Trois corrections additives et datées sont
exigées avant tout calcul; aucune ne touche une graine, un budget, un seuil
d'hypothèse ou la question gelée. La plus importante (B1) protège l'**interprétabilité
d'un résultat nul**, exactement comme la garde apprenant a protégé TV-001.

## Défauts bloquants

### B1 — Aucune garde d'oubli: un H1 nul serait ininterprétable

La prémisse de J6 est « l'adaptation naïve oublie, le replay le prévient ». Le
protocole vérifie que chaque domaine est **appris** (garde apprenant ≥ 20 %,
`preregistration.md:191-195`) mais **jamais que l'adaptation naïve oublie
réellement**. Or la non-stationnarité repose sur un seul panneau déplacé de secteur
et un changement d'éclairage (`preregistration.md:64-68`). Si cette perturbation est
trop douce, l'adaptation naïve ne régresse quasiment pas, et J6-H1 est alors nulle
non parce que le replay échoue mais parce que **le monde n'a pas induit d'oubli**.
C'est le pendant exact de l'ambiguïté causale qui a limité TV-001, et il est évitable
ici par une garde pré-enregistrée.

Correction minimale exigée — ajouter une garde d'interprétabilité gelée, sans nouveau
paramètre libre, réutilisant l'échelle de détection de H1:

> **Garde d'oubli (amendement pré-calcul du 2026-07-20).** J6-H1 n'est interprétée
> que si l'adaptation naïve régresse de façon mesurable sur le domaine considéré:
> pour A et pour B séparément, la régression relative moyenne de `naive` doit être
> `≥ 0,05` avec borne basse BCa 95 % strictement positive. Si cette condition échoue
> sur un domaine, la comparaison H1 de ce domaine est déclarée **non interprétable**
> (le monde n'a pas induit d'oubli), et non un rejet du replay. La règle de décision
> « H1 échoue → retour en conception » ne s'applique qu'à un domaine où la garde
> d'oubli est passée.

Cette garde est symétrique de la garde apprenant, n'ajoute aucun seuil arbitraire (elle
reprend `0,05`, l'effet minimal déjà gelé de H1) et se mesure sur les graines de
campagne sans réglage. Elle ne doit **pas** être calibrée sur le smoke 10991 (ce serait
un réglage).

### B2 — Le dénominateur de régression du domaine B dépend de la condition

`regression[d,r] = e_final_C[d,r] / max(e_acquisition[d,r], 1e-8) − 1`
(`preregistration.md:140-145`). Pour le domaine **A**, `e_acquisition[A]` est mesurée
juste après la session A, or les trois conditions sont identiques jusqu'à la fin de A
(le replay ne s'active qu'en B/C): le dénominateur A est **partagé** entre naïf,
uniform et priorisé pour une graine donnée. La comparaison H1A est donc propre.

Pour le domaine **B**, `e_acquisition[B]` est mesurée après la session B, où les
conditions ont déjà divergé: uniform et priorisé diluent l'acquisition de B avec 50 %
de replay de A, donc leur `e_acquisition[B]` peut être **plus élevée** que celle de
naïf. La différence `regression_naive[B] − regression_uniform[B]` soustrait alors deux
ratios à dénominateurs différents: un avantage apparent d'uniform sur B peut refléter
un dénominateur plus grand (moins bonne acquisition de B) autant qu'un oubli moindre.
H1B et la composante B de H2 sont concernées; A ne l'est pas.

Correction minimale exigée — reporter en co-primaire la régression **absolue** et
exiger l'accord de signe pour toute promotion (aucun changement des seuils relatifs
gelés):

> **Amendement pré-calcul du 2026-07-20.** Pour A et B, la régression absolue
> `regression_abs[d,r] = e_final_C[d,r] − e_acquisition[d,r]` est calculée et rapportée
> à côté de la régression relative. La différence appariée absolue
> (`naive − uniform`, puis `uniform − prioritized`) est reportée avec sa moyenne, son
> IC BCa et ses signes. Une promotion fondée sur H1B ou sur la composante B de H2
> n'est valide que si la différence absolue et la différence relative **s'accordent en
> signe**; un désaccord signale un artefact de dénominateur et rend la revendication B
> non interprétable. Le test statistique primaire reste la version relative gelée.

### B3 — L'identité bit à bit des trois conditions jusqu'à la fin de A doit être gelée et testée

Le texte n'énonce l'identité de la session A que sous « Replay uniforme »
(`preregistration.md:113`, « Session A identique à naïf ») et la laisse seulement
implicite pour le priorisé. Comme la propreté de H1A (B2) repose entièrement sur ce
fait, il doit être un invariant explicite et une assertion d'implémentation.

Correction minimale exigée — ajouter au protocole:

> Les trois conditions partagent la même initialisation de modèle par graine et sont
> **bit à bit identiques jusqu'à la fin de la session A incluse** (mêmes données,
> mêmes 1 500 pas, aucun replay avant B). L'implémentation asserte l'égalité des poids
> et des évaluations post-A des trois conditions sur le smoke 10991 avant toute graine
> de campagne.

## Constats non bloquants, par gravité décroissante

- **M1 — Puissance de J6-H2 à n=12.** H2 exige simultanément, sur A **et** B, moyenne
  ≥ 0,03, borne BCa > 0, p Holm ≤ 0,05 et 5/6 bins favorables
  (`preregistration.md:174-177`). C'est la porte la plus dure du protocole: un bénéfice
  réel mais modeste de la priorité peut la manquer. À geler maintenant, avant données:
  un H2 nul s'interprète « aucune valeur ajoutée démontrée à cette puissance », pas
  « la priorité est inutile ». Aucun changement de seuil; clarification de lecture.
- **M2 — Équité de la quantité de données courantes.** À 50/50 et 1 500 pas égaux, les
  conditions replay dépensent la **moitié** de leur gradient de session sur des données
  anciennes: elles voient moins de données courantes que naïf. C'est l'opérationnalisation
  correcte du replay (calcul fixe, réalloué) et J6-H3 en garde le coût de plasticité; un
  contrôle de quantité de données distinct n'est pas nécessaire. À énoncer explicitement:
  un gain uniform > naïf en rétention se lit « dépenser la moitié du calcul en répétition
  aide la rétention », revendication voulue, à ne pas surinterpréter.
- **M3 — Garde anti-télévision du priorisé (point 6).** La garde +5 points
  (`preregistration.md:179-181`) est une protection de promotion légitime, pas un ajout
  vacueux: la priorité par erreur peut sur-échantillonner les épisodes riches en secteur
  bruité (erreur élevée irréductible), rejouant le mode d'échec TV-001 en mémoire. La
  garder comme **porte** est justifié et pré-enregistré. Limite à noter: +5 points établit
  que le priorisé ne sur-réplique pas la TV, non que son éventuel gain H2 est *causé* par
  la TV; conserver la masse de replay TV par domaine comme diagnostic, comme prévu.
- **M4 — Oubli vs difficulté entre domaines (point 1).** Les secteurs de landmark
  (A 30–50°, B 90–110°, C 50–70°) et l'éclairage diffèrent, donc la difficulté intrinsèque
  peut varier entre domaines. La comparaison de conditions reste valide car elle est
  **intra-domaine et appariée**: chaque condition affronte la même difficulté du domaine.
  Ne jamais revendiquer une comparaison A-rétention vs B-rétention en valeur absolue; le
  protocole les garde séparés, ce qui est correct. Rien à corriger.
- **M5 — Priorité et fuite de test (point 4).** `p_i ∝ error_i + 1e-3` est mesuré sur les
  **épisodes d'entraînement anciens** avec le modèle courant, gelé pour la session, sans
  toucher la banque d'ancres tenue à part. Pas de fuite; la priorité isole bien la seule
  variable « distribution des anciens épisodes » (ratio, pas, données identiques à
  uniform). Vérification positive, aucune action.
- **M6 — Faisabilité MJCF (point 8).** `build_bench_mjcf` / `sample_wall_panels`
  (`sim3d/bench_model.py:141-219`) construisent la scène par template avec panneaux muraux
  et lumières; placer un vrai geom de landmark et paramétrer le `diffuse` des lumières est
  faisable sans overlay écran-space. Risque d'implémentation, pas de conception: à couvrir
  par les contrôles de manipulation du smoke (`preregistration.md:76-82`).

## Vérifications positives explicites

- **Motivation gelée et collecte identique.** Aucun ordonnanceur; babbling bit-identique
  partagé entre les trois conditions par graine — conforme à D-009 et à « J6 D'ABORD ».
- **Budgets et ancres.** 12 000 images, 2 400 décisions, 4 500 pas par condition; ancres
  A/B/C tenues à part, jamais entraînées ni utilisées pour la priorité; erreur bornée
  `pred/(pred+copy)` résistante à la dérive d'échelle, identique à TV-001.
- **Statistiques.** Retournement de signes exact (n=12 ≤ 20), Holm sur A/B, BCa graine
  `20260720`, non-infériorité pour H3 via `noninferiority_sign_flip_pvalue`, signes/`dz`/
  rank-bisériale descriptifs: conformes à `learning/paired_stats.py` et cohérents.
- **Règles de décision.** Promotion uniform (H1A+H1B+H3), puis priorisé (H2+H3+garde TV),
  rejets et non-interprétabilités explicites, aucun réglage post hoc, graines vierges à
  toute reprise: cohérentes et falsifiables.
- **Sonde motivation dormante.** Encodeur gelé/plastique maintenue hors J6, condition de
  réouverture de D-009, sans partage de graine — conforme à ma revue de résultats TV-001.

## Écarts texte/code à tester avant calcul (point 8)

À asserter sur le smoke 10991, avant d'ouvrir 10301..10312:

1. Landmark = vrai geom MJCF au secteur cible par domaine, éclairage B ≤ 0,85×A en
   luminance médiane (marge sous le seuil 15 %) et signature chromatique C ≥ 5 % de A;
   aucun rectangle écran-space (contrôles `preregistration.md:78-80`).
2. Mêmes action + domaine + graine ⇒ images **bit-identiques** entre les trois conditions.
3. Identité bit à bit des poids et des évaluations post-A entre naïf/uniform/priorisé (B3).
4. Budgets exacts: 12 000 images, 2 400 décisions, 1 500 pas/session, corpus partagé.
5. ≥ 64 ancres par compétence structurée dans chacun des trois domaines; ancres jamais
   présentes dans le buffer d'entraînement.
6. Priorité: `p_i` calculée sur épisodes d'entraînement uniquement, gelée sur la session,
   sommant à 1; masse de replay TV consignée par domaine.
7. Métriques absolue **et** relative de régression produites pour A et B (B2).

## Confirmation de gel

Graines (`10991`, `10301..10312`), conditions, budgets, ratio 50/50, priorité
`p_i ∝ error_i + 1e-3`, seuils d'hypothèses (0,05 / 0,03 / 5 % / 20 % / +5 points) et
règles de décision restent **gelés et inchangés**. Les trois corrections bloquantes sont
strictement **additives**: une garde d'interprétabilité (B1), une métrique co-primaire de
contrôle (B2), un invariant explicite et testé (B3). Aucune ne modifie une porte de
promotion ni une graine. Aucun calcul sur graines réservées avant leur intégration.

## Séquence autorisée après intégration

1. Insérer B1, B2, B3 comme amendement daté dans le pré-enregistrement (avant calcul).
2. Implémenter le substrat J6 (domaines MJCF réels, banques A/B/C, trois conditions de
   consolidation), sans ajouter de quatrième condition ni toucher l'ordonnanceur.
3. Vérifier par tests unitaires, puis exécuter le smoke hors protocole:

   ```bash
   python scripts/research/run_j6_replay.py --smoke   # graine 10991, assertions ci-dessus
   ```

4. Sur smoke vert (manipulation, budgets, identité post-A, ancres), exécuter le runner
   résumable/keep-awake sur les 12 triplets, sous plafond 36 runs / 90 min GPU:

   ```bash
   python scripts/research/run_j6_replay.py --review-accepted
   ```

5. Consigner les résultats selon les portes gelées et préparer une revue de résultats
   avant toute promotion.

Aucune commande de calcul sur `10301..10312` n'est autorisée avant l'intégration de B1–B3
et un smoke 10991 vert. Simulation uniquement sous D-008.
