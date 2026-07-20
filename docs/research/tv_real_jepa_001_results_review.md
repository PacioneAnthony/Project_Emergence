# Revue contradictoire des résultats TV-001 — ordre de la suite

Date: 2026-07-20. Revue demandée par `CLAUDE_REVIEW_REQUEST.md` après le rejet
interprétable de TV-H1 et TV-H2 (`docs/research/tv_real_jepa_001_results.md`,
commit `4c4b8b8`, décision D-009). La non-promotion de `regional_lp_gain` est
acquise par protocole et n'est pas rouverte ici. Aucun calcul n'a été lancé;
aucun fichier autre que la présente revue n'a été modifié.

## Verdict

**J6 D'ABORD.** Motivation gelée, collecte par babbling dans toutes les
conditions, pré-enregistrement de l'étape 2 (adaptation naïve vs replay uniforme
vs replay priorisé). La sonde diagnostique encodeur gelé/plastique est spécifiée
ci-dessous comme expérience dormante — c'est la condition de réouverture de
D-009 — mais elle ne conditionne aucune baseline de J6 et ne doit pas la
retarder. De plus, J6 fournit gratuitement une lecture partielle de la question
diagnostique: la condition replay priorisé par erreur expose exactement le même
mode d'échec potentiel (sur-échantillonner l'irréductible), et le replay
uniforme en est le contrôle interne.

## Conformité du verdict aux règles gelées

Aucun écart constaté entre le verdict documenté et le protocole:

- les deux corrections bloquantes de la revue pré-campagne ont été appliquées
  avant calibration et sont vérifiables dans `4c4b8b8`: porte
  `--review-accepted` déplacée devant la calibration avec test de non-régression
  (`tests/test_tv_exploration.py::RunnerReviewGateTests`), amendement daté
  inséré dans le pré-enregistrement, comptage des ancres de bin visé ≤ 5 avec
  angle réel ≥ 130° consigné (résultat: 0);
- les agrégats du rapport se recoupent: moyenne des 12 réductions relatives
  `-2,80 %`, 5/12 signes favorables sur chaque hypothèse, allocation babbling
  `25,19 %` et regional `28,28 %` (cohérente avec la moyenne des allocations par
  round), demi-largeur de calibration `1,96·s/√4 = 0,000201` sous le seuil
  `0,019979`;
- les règles de décision gelées ont été suivies à la lettre: double rejet,
  garde-fous tous passés, campagne déclarée interprétable, aucune promotion,
  aucune retouche, graines et implémentation gelées, arbitrage de direction
  demandé avant toute modification de l'ordonnanceur — exactement la branche
  « TV-H1 échoue » du pré-enregistrement, actée par D-009 sous D-004.

## Constats, par gravité décroissante

### C1 (moyen) — Le signal régional n'est pas contrefactuel; l'ambiguïté est structurelle

L'interprétation « invariance apprise » de Codex est compatible avec les
métriques, mais elle peut être renforcée d'un cran: avec un apprenant partagé,
le gain avant/après d'une cellule mesure le progrès **global** du modèle
projeté sur les ancres de cette cellule, pas la valeur marginale d'avoir visité
cette cellule. Le babbling passe lui aussi ~25 % de son budget devant la
télévision; l'invariance au bruit s'apprend donc dans les deux conditions, et
les ancres TV d'une graine voient leur erreur baisser même sans visite active du
secteur. Le gain positif initial des cellules TV (`0,498` au round 1 contre
`0,341` en structuré) est ainsi doublement dégénéré: il peut refléter un vrai
progrès de représentation (filtrer le contenu i.i.d., encoder bezel et
périphérie — plausible puisque l'écran ne couvre que 56,25 % des pixels), et il
est de toute façon en partie exogène aux choix de la politique. Un ordonnanceur
qui suit ce signal ne peut pas distinguer « ce secteur me fait progresser » de
« le modèle progresse, et cela se voit aussi sur ce secteur ». L'échec observé
est donc attendu sous au moins deux causes non séparées par le dispositif —
c'est précisément ce que dit la demande de revue, et c'est correct.

Conséquence: TV-001 est décisive sur la promotion, indécise sur la cause. Elle
n'exigeait pas de l'être: aucune décision pendante ne dépend de la cause tant
que la motivation reste gelée.

### C2 (moyen) — TV-H2 opérationnalise « gaspillage » d'une façon partiellement mal spécifiée

TV-H2 compte toute décision dans `[130°, 170°]` comme du gaspillage. Si
l'invariance au niveau de la représentation est apprenable — et les gains tenus
à part quasi identiques entre familles (`0,0780` structuré, `0,0860` TV) sur
toute la campagne montrent qu'un progrès mesurable y a persisté — alors une
fraction de ces visites achète un progrès réel. La leçon est métrologique, pas
un vice du verdict: toute future métrique d'évitement devra viser
l'**incertitude irréductible dans l'espace de la cible**, pas un secteur
angulaire. Le pré-enregistrement avait d'ailleurs restreint honnêtement la
portée de TV-H2 au cas aligné dans l'amendement. Rien à rouvrir; à retenir pour
la conception de toute sonde future.

### C3 (mineur) — L'évitement tardif nuance « le signal ne sépare pas »

L'allocation regional tombe à `8,8 %` puis `10,9 %` aux rounds 9-10, sous le
plancher uniforme: en fin de budget, les moyennes signées des cellules TV sont
devenues durablement négatives pendant que des cellules structurées restaient
positives. Le signal sépare donc les deux familles, mais lentement — après que
le progrès d'invariance s'est épuisé. Tester « même mécanisme, budget plus
long » serait une hypothèse nouvelle sur graines vierges, pas une retouche; je
ne la recommande pas avant J6, et je la mentionne pour que l'affirmation « le
signal ne sépare pas durablement » du rapport ne soit pas surgénéralisée.

### C4 (mineur) — La clause « le bruit calibré n'explique pas l'écart » repose sur le modèle aléatoire

La calibration mesure le bruit d'un JEPA non entraîné (pré-enregistré ainsi et
rappelé dans le rapport). Le bruit de mini-batch d'un modèle entraîné peut être
plus grand. La conclusion tient néanmoins largement: les gains par round
(~`0,08`) dépassent l'écart-type nul (`0,000205`) de deux ordres de grandeur et
demi; même un bruit dix fois plus grand sous entraînement ne rapprocherait pas
les deux. Constat de robustesse, aucune action.

## TV-001 reste informative au-delà de la non-promotion

Trois acquis durables, indépendants de l'ambiguïté causale:

1. le survivant de DC-001..005 n'apporte **aucun** bénéfice face au babbling dès
   que l'apprenant est réel, à ce budget — le banc analytique surestimait la
   famille entière, ce qui valide rétrospectivement le diagnostic du brief;
2. le progrès par cellule sur erreur tenue à part, même correctement agrégé
   avant clip, ne suffit pas à identifier l'irréductible au niveau
   représentation: c'est une contrainte de conception mesurée, pas une opinion;
3. le « piège de la télévision » formulé en allocation angulaire est
   partiellement mal posé quand l'invariance est apprenable (C2) — toute reprise
   de la motivation devra reformuler la cible.

## Justification de l'ordre J6 d'abord

- **Aucune dépendance.** Les trois conditions de J6 (adaptation naïve, replay
  uniforme, replay priorisé) sont des politiques de **consolidation** à collecte
  babbling identique; aucun ordonnanceur d'exploration n'y figure. La cause de
  l'échec TV-001 ne conditionne ni leurs baselines ni leurs métriques.
- **Le brief l'ordonne déjà ainsi.** `CODEX_TASK_BRIEF.md` fait de la
  non-stationnarité/rétention l'étape 2 explicite et la seule où « un
  ordonnanceur a un vrai problème à résoudre »; y aller avec motivation gelée
  respecte D-009 et la règle « pas de biomimétisme non payé ».
- **Le diagnostic est en partie gratuit dans J6.** Si le monde J6 conserve la
  télévision (recommandé, pour la continuité du substrat), la masse de priorité
  que le replay priorisé par erreur accorde aux épisodes contenant le secteur
  bruité doit être consignée par condition. Un replay priorisé qui
  sur-échantillonne l'irréductible contre le contrôle uniforme rejouerait le
  mode d'échec TV-001 dans le domaine mémoire — observation qui affinerait le
  diagnostic sans campagne dédiée.
- **Rien n'est perdu.** Les artefacts TV-001 sont gelés; la sonde diagnostique
  reste exécutable à l'identique plus tard, et D-009 en fait explicitement la
  condition de réouverture.

`ARRÊT/ARBITRAGE OBJECTIF` n'est pas justifié: les deux voies répondent au
brief; il n'y a pas d'opposition durable à soumettre à Anthony.

## Sonde diagnostique dormante — spécification minimale (non planifiée avant J6)

À consigner pour une éventuelle réouverture de D-009; aucune retouche de TV-001.

- **Hypothèse:** le gain initial des cellules TV est un progrès de
  représentation (invariance réductible), pas une attraction pour l'aléatoire.
  Prédiction falsifiable: avec un **encodeur gelé** (pré-entraîné sur corpus
  structuré sans télévision, seul le prédicteur reste plastique), le gain tenu à
  part des cellules TV s'effondre vers le bruit nul calibré tandis que des
  cellules structurées gardent un gain positif; `regional_lp_gain` passe alors
  sous 15 % d'allocation TV. Si l'allocation TV reste ≥ babbling malgré
  l'encodeur gelé, le défaut est dans le signal/l'ordonnanceur, pas dans
  l'invariance.
- **Baseline:** babbling, même encodeur gelé, budgets identiques à TV-001.
- **Métrique primaire:** fraction d'allocation TV de `regional_lp_gain`;
  secondaires: gains tenus à part par famille de cellules, erreur structurée
  appariée.
- **Coût maximal:** le harnais TV-001 réutilisé tel quel (24 runs ≈ 20 min GPU
  mesurées); plafond une seule campagne, graines vierges, calibration réutilisant
  la règle gelée.
- **Règle d'arrêt:** une campagne, aucun réglage intermédiaire; verdict terminal
  dans les deux sens pour la question de cause.

## Ce que Codex est autorisé à préparer ensuite

1. Rédiger et geler le pré-enregistrement de l'étape 2/J6
   (`docs/research/` — nouveau fichier, graines vierges) avec: collecte babbling
   identique dans les trois conditions; non-stationnarité inter-sessions définie
   a priori; conditions adaptation naïve, replay uniforme, replay priorisé (fixer
   avant calcul le critère de priorité primaire — erreur de prédiction ou
   nouveauté — pour ne pas multiplier les hypothèses); métriques de rétention et
   de régression **par compétence/région** sur ancres tenues à part, jamais une
   métrique unique; consignation par condition de la masse de replay accordée aux
   épisodes contenant le secteur télévision; statistiques appariées via
   `learning/paired_stats.py`; budgets strictement égaux.
2. Reporter la sonde diagnostique dormante ci-dessus dans ce pré-enregistrement
   ou dans le registre, comme condition de réouverture de D-009, sans la
   planifier.
3. Soumettre le pré-enregistrement J6 à revue contradictoire avant tout calcul
   sur graines réservées, conformément à `PILOTAGE.md`.

Aucune commande de calcul n'est autorisée par la présente revue: la prochaine
porte est le gel du pré-enregistrement J6, puis sa revue.
