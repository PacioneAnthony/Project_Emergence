# Pré-enregistrement J6-AR001 — replay adaptatif sous contrainte de plasticité

Date de gel: 2026-07-20, avant implémentation, smoke et tout calcul sur les graines
réservées. Filiation: D-010 (non-promotion J6-R001) et D-011 (option A sous D-004).
J6-R001, ses mondes A/B/C et ses graines 10301..10312 sont des historiques gelés et ne
sont utilisés ni pour régler ni pour sélectionner le présent protocole.

## Question et portée

Peut-on conserver la valeur de rétention du replay uniforme sur **deux** domaines qui
induisent un oubli naïf mesurable, sans payer le coût de plasticité courante qui a fait
échouer H3 dans J6-R001?

J6-AR001 teste un ordonnanceur de consolidation minimal. Il ne teste ni une nouvelle
motivation d'exploration, ni la priorité d'épisodes par erreur, ni la réafférence. Les
trois conditions collectent le même corpus par babbling et reçoivent les mêmes mesures
de suivi; seule l'utilisation du budget de replay diffère.

## Hypothèses gelées

- **AR-H0D / AR-H0E — garde d'oubli B1:** l'adaptation naïve régresse de façon
  mesurable sur chacun des deux domaines anciens D et E: régression relative moyenne
  `≥ 0,05` et borne basse BCa 95 % strictement positive. Une garde manquée rend toute
  revendication de rétention sur ce domaine **NON INTERPRÉTABLE**, jamais un rejet du
  replay. La garde n'est jamais calibrée sur le smoke.
- **AR-H1D / AR-H1E — réplication de la valeur du replay:** uniform 50/50 réduit la
  régression relative de naïf d'au moins `0,05` sur D et E séparément, avec borne basse
  positive, test exact/Holm significatif et au moins `5/6` bins favorables.
- **AR-H2D / AR-H2E — rétention du candidat:** le replay adaptatif est non inférieur à
  uniform 50/50 sur la régression D et E, avec marge moyenne `0,02` relatif et aucune
  perte moyenne supérieure à `0,05` dans un bin structuré.
- **AR-H3a — plasticité supérieure à uniform:** sur F, le candidat réduit l'erreur
  structurée finale d'au moins `0,05` relatif face à uniform 50/50, avec borne basse
  positive, test exact significatif et au moins `5/6` bins favorables.
- **AR-H3b — plasticité conservée face à naïf:** sur F, le candidat reste non inférieur
  à naïf dans une marge de `5 %` de l'erreur moyenne naïve; aucun bin F ne régresse de
  plus de `10 %` en moyenne face à naïf.

La promotion exige **toutes** ces hypothèses interprétables et satisfaites. Une moyenne
globale D+E ou entre bins ne peut compenser un domaine ou une région défaillante.

## Graines, conditions et plafond

- Smoke d'intégration hors protocole: `11991`, sans rôle de décision.
- Campagne appariée: graines vierges `11301..11316` (16 triplets).
- Trois conditions et aucune quatrième: `naive`, `uniform_50`, `adaptive_replay`.
- Trois sessions séquentielles D→E→F par run.
- Par domaine et graine: 20 épisodes de 200 images à 10 Hz, soit 4 000 images et
  800 décisions de babbling. Le corpus est généré une fois puis partagé bit à bit entre
  les trois conditions.
- Par condition: exactement 12 000 images, 2 400 décisions, 1 500 pas AdamW par session,
  batch 256, donc 4 500 pas et 1 152 000 exemples-gradient. Les évaluations de suivi ont
  le même calendrier et le même coût dans les trois conditions.
- Plafond: 48 runs et 75 minutes GPU murales cumulées. Runner résumable au niveau run,
  keep-awake et arrêt technique si un manifeste, budget, digest ou plafond diverge.
- Sorties locales: `data/processed/experiments/j6_adaptive_replay_001/`; rapport et
  exports d'audit versionnés sous `docs/research/`.

Le choix de 16 triplets reste sous la limite exacte `n≤20` de
`learning/paired_stats.py` et augmente la puissance de la porte H3, qui était proche
mais non significative après Holm avec n=12 dans J6-R001.

## Apprenant et identité B3

Le JEPA v3 reste inchangé: images 64×64, encodeur largeur 32, latent 128, prédicteur
caché 512, action et horizon conditionnés, horizons 1..5, stop-gradient,
variance/covariance, AdamW `lr=3e-4`, weight decay `1e-4`.

Les trois conditions partagent la même initialisation par graine et sont bit à bit
identiques jusqu'à la fin de D incluse: mêmes corpus, mêmes 1 500 pas, mêmes évaluations
et aucun replay. Le runner réutilise un checkpoint post-D unique et asserte sur le smoke
l'identité des poids, de l'optimiseur, des sondes et des évaluations post-D.

## Mondes neufs D/E/F

Les mondes A/B/C de J6-R001 ne sont pas réutilisés. D/E/F conservent le corps, la
télévision `[130°,170°]`, les objets de fond aléatoires et la distribution de babbling,
mais remplacent le champ visuel structuré entier:

| domaine | ceinture physique de six secteurs structurés | éclairage |
|---|---|---|
| D | damiers saillants carmin/blanc, un panneau MJCF centré dans chaque bin 0..5 | nominal froid |
| E | barres verticales cyan/bleu nuit, mêmes secteurs et emprise | intensité globale ×0,65, neutre |
| F | barres horizontales ambre/violet, mêmes secteurs et emprise | intensité moyenne ×1,15, chaude |

Chaque panneau est un vrai ensemble de geoms/assets MJCF placé dans le monde avant
rendu. Aucun overlay écran-space ne représente la ceinture. La ceinture couvre chaque
compétence structurée afin que la non-stationnarité ne repose pas sur un seul landmark,
défaut observé sur A dans J6-R001. Les palettes, orientations et lumières sont fixées
ici avant implémentation; elles ne sont pas réglées à partir de 11991 ou de la campagne.
Le calendrier de graines de pièces est indépendant du domaine: à épisode égal, D/E/F
partagent les mêmes objets et positions de fond, seuls les facteurs physiques ci-dessus
changent.

Le smoke vérifie seulement la construction: vrai geom dans chaque secteur, maximum de
différence visuelle dans le bin attendu, distance visuelle D/E, E/F et D/F `≥ 0,08`
(moyenne absolue RGB normalisée) dans chacun des six bins, luminance E `≤ 0,75×D` et
chroma F différente de D d'au moins `5 %`. Il ne mesure ni ne calibre l'oubli.

## Trois banques disjointes par domaine

Chaque graine et domaine possède trois ensembles issus de pièces disjointes, identifiés
par des espaces de graines non recouvrants:

1. corpus d'entraînement, seul ensemble utilisé dans les gradients et le replay;
2. banque de suivi, utilisée uniquement par l'ordonnanceur et calculée pour **toutes**
   les conditions;
3. banque de décision finale, utilisée uniquement pour les métriques et les portes.

Les deux banques sont équilibrées par bin et contexte avec 32 ancres par cellule, soit
64 ancres par compétence. Aucune image de suivi ou de décision n'entre dans le buffer,
une priorité d'épisode ou l'autre banque. Le smoke asserte les espaces de graines, les
digests et l'absence d'image identique entre ces trois ensembles.

L'erreur reste bornée et identique à J6-R001:

```text
e = MSE(prediction, cible) / max(MSE(prediction, cible) + MSE(copie, cible), 1e-8)
```

## Conditions à information et calcul égaux

Toutes les conditions évaluent la banque de suivi complète avant chaque bloc de 100 pas
et consignent les mêmes erreurs. Ces mesures ne modifient pas `naive` ou `uniform_50`,
mais leur sont effectivement fournies afin que le candidat ne gagne aucune information
ni aucun calcul d'évaluation supplémentaire. Les trois branches conservent également
le même corpus ancien en lecture seule; les baselines diffèrent seulement par la règle
d'échantillonnage pré-enregistrée.

### `naive`

Les 1 500 pas de E et F utilisent 256 paires courantes. Aucune ancienne paire.

### `uniform_50`

Référence J6-R001 exacte. En E/F, chaque batch contient 128 paires courantes et
128 anciennes. Une ancienne paire est tirée par épisode uniforme, puis paire valide
uniforme. Aucun score d'épisode.

### `adaptive_replay`

Le candidat reprend le même échantillonnage uniforme d'anciennes paires; seule leur
fraction change tous les 100 pas. Avant chaque bloc, sur la banque de suivi:

```text
d_old = max_(ancien domaine, bin 0..5) max(e_t / max(e_acquisition, 1e-8) - 1, 0)
d_current = max_(bin 0..5) max(e_t / max(e_session_start_current, 1e-8) - 0.80, 0)
q = 0.5 * d_old / (d_old + d_current + 1e-3)
rho = clip(floor(16*q + 0.5) / 16, 0, 0.5)
```

Le batch suivant contient exactement `256×rho` anciennes paires et le complément de
paires courantes. `rho` est donc dans `{0, 1/16, …, 1/2}`. La cible `0,80` réutilise la
garde apprenant gelée de 20 %: tant qu'une compétence courante n'est pas acquise, son
déficit concurrence la dette d'oubli. `e_session_start_current` est figée immédiatement
avant le premier pas de la session. Quand ni dette ancienne ni déficit courant ne sont
mesurés, `rho=0`.

Pas de priorité d'épisode, exposant, correction d'importance, nouveauté, accès à la
banque finale ou mise à jour entre deux blocs. Les références d'acquisition d'un domaine
ancien sont figées à la fin de sa propre session. Le calendrier complet de `rho`, les
dettes, le nombre ancien/courant et la masse TV sont consignés.

## Métriques

Pour ancien domaine `d∈{D,E}` et bin structuré `r`:

```text
regression_rel[d,r] = e_final_F[d,r] / max(e_acquisition[d,r], 1e-8) - 1
regression_abs[d,r] = e_final_F[d,r] - e_acquisition[d,r]
```

Métriques obligatoires par graine et condition:

- régressions relative et absolue D/E par bin sur la banque finale;
- erreur initiale, après D, après E et après F sur les trois banques finales;
- erreur F finale par bin et différences relatives candidat−uniform et candidat−naïf;
- trajectoires des banques de suivi par bloc, `d_old`, `d_current` et `rho`;
- fraction totale de gradients anciens par session et domaine;
- masse attendue et fraction effective de replay télévision par session et domaine;
- pertes, probes angle/distance descriptives, budgets, digests et temps mural.

**B2 est conservée:** toute revendication de rétention sur D/E exige l'accord de signe
entre la différence relative et la différence absolue appariée. Moyennes, IC BCa et
signes absolus sont rapportés; le test statistique primaire reste relatif. Aucun énoncé
de difficulté absolue entre D et E n'est autorisé.

## Statistiques et portes

Toutes les différences sont appariées par graine. `learning/paired_stats.py` fournit
les tests exacts par retournement de signes, les tests de non-infériorité, IC BCa 95 %
avec 10 000 rééchantillonnages, Holm, signes, `dz` et rank-bisériale. Graine statistique
`2026072001`; tests unilatéraux; n=16.

### Garde B1 et AR-H1

B1 est évaluée séparément sur D/E. AR-H1 utilise par graine et domaine la moyenne des
six différences `regression_naive - regression_uniform_50`. Portes: moyenne `≥0,05`,
borne BCa basse `>0`, p exacte après Holm D/E `≤0,05`, `≥5/6` bins favorables et accord
absolu/relatif B2.

### AR-H2 — non-infériorité de rétention

Différence par graine entre les moyennes des six bins
`regression_adaptive - regression_uniform_50`, où une valeur positive est une perte.
Test exact de non-infériorité à marge `0,02`, Holm D/E,
p `≤0,05`; moyenne `≤0,02`; aucun bin n'a une perte moyenne `>0,05`; accord B2 sur D/E.
Cette marge ne représente que 40 % de l'effet minimal `0,05` exigé d'uniform et empêche
le candidat de résoudre H3 en abandonnant l'essentiel du bénéfice de rétention.

### AR-H3a — supériorité de plasticité

Réduction relative par graine de l'erreur structurée F finale:

```text
gain_F = (e_uniform_50_F - e_adaptive_F) / max(e_uniform_50_F, 1e-8)
```

Porte: moyenne `≥0,05`, borne BCa basse `>0`, p exacte unilatérale `≤0,05`, au moins
`5/6` bins favorables et aucun bin candidat pire qu'uniform de plus de `0,05` relatif.

### AR-H3b — non-infériorité face à naïf

Différence absolue `e_adaptive_F - e_naive_F`; la marge scalaire vaut `5 %` de la
grand-moyenne de l'erreur F naïve sur les 16 graines. Test exact de non-infériorité
p `≤0,05`. Aucun bin F ne régresse de plus de `10 %` en moyenne relative face à naïf.
Les p de H3a et H3b sont corrigées ensemble par Holm.

## Gardes de validité

- **Apprenant:** après acquisition de D/E/F, l'erreur structurée finale du domaine
  baisse d'au moins `20 %` face à son évaluation initiale dans chaque condition.
- **Activation:** dans chacune des sessions E et F, `adaptive_replay` doit employer au
  moins deux valeurs de `rho`, dont une strictement entre 0 et 0,5, sur au moins 12/16
  graines. Sinon le mécanisme n'a pas été effectivement testé et reste non
  interprétable.
- **Calcul et information:** mêmes 1 500 pas, batch 256, corpus, évaluations de suivi et
  banques finales. Toute divergence arrête techniquement la campagne.
- **Télévision:** la fraction effective TV du candidat ne dépasse pas celle d'uniform
  de plus de `5 points` en moyenne à E ou F. Le résultat ne reçoit aucune interprétation
  causale si cette garde échoue.
- **Construction:** les trois ensembles sont disjoints; les banques finales ne pilotent
  jamais `rho`; priorités d'épisode absentes; corpus bit-identique; B3 passe.
- **Plafond:** 48 runs et 75 minutes GPU cumulées, sans dépassement silencieux.

## Règles de promotion et d'arrêt

- **Toutes les gardes, B1 D/E, H1 D/E, H2 D/E, H3a et H3b passent:** proposer
  `adaptive_replay` comme ordonnanceur minimal de consolidation J6, sous réserve de la
  revue Claude des résultats avant inscription d'une promotion.
- **B1 échoue sur D ou E:** revendications de rétention du domaine NON INTERPRÉTABLE;
  objectif « deux domaines anciens » non atteint, aucune promotion et aucun retuning.
- **H1 échoue sur un domaine où B1 passe:** le nouveau substrat ne réplique pas la valeur
  de la référence uniform; aucune promotion du candidat.
- **H2 échoue:** le candidat résout éventuellement la plasticité en abandonnant trop de
  mémoire; rejet du candidat.
- **H3a ou H3b échoue:** le compromis H3 n'est pas levé; rejet du candidat.
- **Garde activation échoue:** calendrier non testé, résultat non interprétable.
- **Garde apprenant, TV, construction, information ou budget échoue:** campagne non
  interprétable ou arrêt technique selon la garde; aucune correction sur ces graines.
- Un résultat nul signifie absence de valeur démontrée à cette puissance. Toute reprise
  utilise un nouveau pré-enregistrement, de nouveaux mondes et de nouvelles graines.

Qu'il réussisse ou échoue, J6-AR001 clôt cette variante adaptative unique. La réafférence
(étape 3 du brief) redevient alors la suite par défaut, sauf si une réplication
indépendante d'un mécanisme promu est exigée par la revue des résultats.

## Séquence verrouillée

1. Geler le présent fichier et obtenir une revue contradictoire Claude.
2. N'implémenter et ne lancer aucun smoke avant verdict favorable et intégration de
   toute correction pré-calcul.
3. Après autorisation: implémenter additivement, tester, puis exécuter uniquement le
   smoke 11991 et ses assertions de construction.
4. Ouvrir 11301..11316 seulement si le smoke est vert et le manifeste concorde.
5. Analyser les portes gelées, versionner les résultats et demander une seconde revue
   Claude avant toute promotion.

Simulation uniquement sous D-008: aucune action physique, aucun achat, aucun flash.

## Amendement pré-calcul du 2026-07-20 — corrections C1 à C4

Cet amendement est ajouté après la revue contradictoire
`j6_adaptive_replay_001_review.md` et avant toute implémentation, tout smoke 11991 et
tout calcul sur 11301..11316. Il ne modifie aucun monde, graine, budget, seuil, marge ou
règle de promotion.

### C1 — B2 pour la non-infériorité AR-H2

Pour AR-H2, B2 est violée uniquement si la porte relative passe alors que la différence
absolue appariée `adaptive − uniform_50` montre une perte significative: moyenne `> 0`
**et** borne BCa 95 % basse `> 0`. Un simple désaccord de signe autour de zéro ne viole
pas B2. La moyenne, l'IC BCa et les signes de cette différence absolue restent
obligatoirement rapportés.

### C2 — ordre d'agrégation et source exclusive du suivi

Pour AR-H3a, l'agrégat par graine est la moyenne des six erreurs de bin sur la banque
finale F; `gain_F` est calculé sur ces agrégats. Le critère « 5/6 bins favorables »
utilise la réduction relative par bin moyennée sur les 16 graines. Le plafond « aucun
bin pire de plus de 0,05 relatif » s'entend en moyenne inter-graines.

Dans la formule adaptative, `e_t`, `e_acquisition` et `e_session_start_current`
proviennent exclusivement de la banque de suivi. La banque finale de décision ne peut
jamais fournir directement ou indirectement une valeur à `d_old`, `d_current`, `q` ou
`rho`.

### C3 — assertions smoke d'équité et de composition

Le smoke 11991 doit en plus asserter:

1. chaque batch d'`adaptive_replay` contient exactement `256×rho` anciennes paires et
   `256×(1−rho)` courantes;
2. chaque `rho` est recomputable hors ligne au chiffre près depuis les `d_old` et
   `d_current` consignés;
3. les trois conditions exécutent le même nombre d'évaluations de suivi, aux mêmes pas,
   sur des banques de même taille.

Ces assertions portent sur l'exécution effective, pas seulement sur les constantes du
manifeste.

### C4 — fraction télévision invariante à rho

La fraction effective de replay télévision est la part des **paires rejouées** dont
l'angle cible appartient à `[130°,170°]`. Son dénominateur contient uniquement les
paires anciennes effectivement rejouées, de sorte que la mesure est invariante à
`rho`. Les blocs où `rho=0` sont exclus du dénominateur. Si une session entière a
`rho=0`, la garde TV y est vide et la garde d'activation statue; aucune valeur zéro
artificielle n'est imputée.

## Précisions de traçabilité pré-calcul

- La graine `2026072001` est passée explicitement à chaque IC BCa; les tests à n=16
  utilisent l'énumération exacte, jamais Monte Carlo.
- Le temps mural par run est consigné dès le smoke, sans créer de seuil supplémentaire.
- Une éventuelle promotion établira seulement que **ce calendrier** résout le compromis;
  elle ne revendiquera pas que l'adaptativité est nécessaire face à une fraction
  statique basse non testée. Une telle ablation exigerait un pré-enregistrement neuf.
- Le rapport décrira sans réinterprétation la dynamique attendue: `rho=0` en début de
  session, puis saturation potentiellement rapide vers 0,5 une fois le domaine courant
  acquis.
- Chaque évaluation de suivi par bloc et condition possède un digest consigné, afin de
  rendre la parité d'information auditable comme B3.
