# Revue contradictoire pré-calcul BODY-SCHEMA-001 — schéma corporel probabiliste

Date: 2026-07-27. Revue demandée avant implémentation et avant toute graine `19091+`.
Fichiers audités intégralement: `docs/research/body_schema_001_preregistration.md`,
`docs/research/life_012_technical_stop.md`, `docs/research/life_012_review.md`,
`docs/research/life_011_technical_stop.md`, `CODEX_TASK_BRIEF.md`,
`DEVELOPMENTAL_ARCHITECTURE.md` (définition du succès §2, métriques §12.2, jalons J1 et
J5), `learning/life_010.py`, `learning/life_010_campaign.py`,
`learning/paired_stats.py`, `sim3d/bench_env.py`, `sim3d/bench_model.py`,
`DECISIONS.md` (D-043 à D-047).

Aucune simulation, aucun test, aucun entraînement et aucune graine n'ont été lancés. Les
seuls calculs sont une lecture littérale du chemin de données de `BenchHeadEnv` et deux
calculs de probabilité élémentaires. Aucun fichier autre que la présente revue n'a été
modifié.

## Verdict

**AUTORISER AVEC CORRECTIONS BLOQUANTES.**

Le retour à J1 est la bonne décision, et c'est le mouvement le plus légitime de toute la
série: il abandonne le sélecteur au lieu de le retuner, il suit l'ordre de succès de
`DEVELOPMENTAL_ARCHITECTURE.md` §2, il supprime l'oracle de curriculum dont D-046 vient de
montrer qu'il n'est pas une borne séquentielle, et il attaque le verrou observé — une
compétence qui ne progresse pas — plutôt que le dessin des plans. Le budget est
confortable: `24 × 42 × 32 ≈ 32 000` pas de contrôle, soit environ six minutes au débit
mesuré en LIFE-009, très en deçà des `90` minutes.

Mais le protocole, tel qu'écrit, ne peut mesurer aucune de ses cinq hypothèses, pour une
raison qui tient au substrat et non au dessin: **dans ce banc, le canal observé est
entièrement déterministe**. Le séparateur sur lequel reposent les quatre banques — « des
graines RNG séparées » — n'a aucun effet sur l'angle AS5600. Les six trials publics, les
vingt-quatre trials d'apprentissage, les six trials privés et les six trials de faute ne
contiennent, par organisme, que **trois trajectoires distinctes**, répétées. La
protection, la calibration conformelle et la métrique primaire sont donc calculées sur
les données d'ajustement elles-mêmes.

Ce constat vaut rétroactivement pour LIFE-009 à LIFE-012, et pour mes trois revues
précédentes: j'ai accepté « deux flux de bruit réservés » comme produisant une banque
privée distincte. C'est faux — les deux flux produisent la même séquence d'angles. La
banque privée LIFE mesurait l'erreur d'ajustement, pas une compétence tenue à part. Le
correctif appartient à BODY-SCHEMA-001, qui est précisément la tranche qui prétend
qualifier une prédiction « tenue à part ».

Six corrections bloquantes suivent. La première est structurelle; les cinq autres portent
sur l'équité des comparaisons, l'alignement avec le critère J1, l'attribution d'un échec
et quatre sous-spécifications qui exigeraient sinon une décision scientifique en cours de
code.

## 0. Légitimité du retour J1

Légitime, et sans retuning déguisé:

- aucun seuil LIFE n'est déplacé, aucune graine LIFE n'est réutilisée, aucune campagne
  LIFE n'est rouverte, et D-046 interdit explicitement toute nouvelle variante de
  sélecteur avant qualification J1;
- le changement est de **jalon**, pas de paramètre: l'excitation devient fixe et commune,
  il n'y a plus d'allocation, plus d'oracle, plus de professeur contrefactuel, plus de
  carré latin. Rien de ce qui a échoué n'est reconduit sous un autre nom;
- l'ordre suivi est celui de l'architecture: prédire les conséquences immédiates du cou
  (succès §2.1, jalon J1) avant de choisir une expérience (succès §2.6, jalon J5).

Une réserve de formulation, qui compte pour la suite. La motivation répète que « sur
18793, la protection refuse `24/24` mises à jour ». Ce chiffre suggère vingt-quatre
échecs indépendants. Il n'en est rien: comme les vingt-quatre trials d'apprentissage ne
contiennent que trois trajectoires distinctes (§1), la suite des candidats est
quasi-déterministe et converge de façon monotone vers la solution des moindres carrés sur
les `96` transitions uniques. « `24/24` refusés » est **un seul fait, observé une fois et
répété vingt-quatre fois**: sur cet organisme, le meilleur ajustement possible de la base
gelée est moins bon que le prior sur l'ensemble impair. C'est une information réelle et
suffisante pour motiver un retour à J1; ce n'est pas vingt-quatre preuves.

## 1. Le fait dominant: le canal observé est déterministe

La chaîne complète, dans `sim3d/bench_env.py`:

```text
step(target) -> _limited_deg = clamp(_limited_deg + clamp(target - _limited_deg, ±max_delta))
             -> data.ctrl = radians(_limited_deg - 90)
             -> mj_step ×  n_substeps
_as5600_deg() = round(servo_angle_deg() / (360/2**12)) * (360/2**12)
```

`_as5600_deg` ne dépend que de `data.qpos`. Le générateur `self.rng` n'est consommé que
par `_gyro_bias_dps`, `_accel_bias_g`, `_raw_imu` et `_distance` — gyroscope,
accéléromètre et ultrason, dont aucun n'entre dans les features autorisées ni dans la
cible. `life010_bench_config` fixe `randomize_room=False`, donc la pièce est construite
par `default_rng(0)` indépendamment de la graine d'exécution; les géométries de tête
portent `contype="0" conaffinity="0"`, donc aucun contact ne couple la pièce à l'axe.
`reset` repart toujours de `qpos = 0`, `qvel = 0`.

**Conclusion: pour un organisme et une séquence de cibles donnés, la suite des angles
AS5600 est une fonction déterministe, identique quelle que soit la graine d'exécution.**
Il n'y a aucun bruit d'observation sur la cible; `BenchSensorConfig` ne définit qu'une
quantification à `12` bits, soit `0,087890625°`.

Conséquences directes sur BODY-SCHEMA-001 tel qu'écrit:

1. **Les quatre banques ont le même contenu.** Public (2 trials par motif), apprentissage
   (8 par motif), privée (2 par motif) et faute (« les mêmes commandes que la banque
   privée ») dérivent des trois mêmes plans gelés. Par organisme, l'ensemble du protocole
   observe `3 × 32 = 96` transitions distinctes, répétées douze fois en régime normal.
   La porte smoke 2 vérifie la disjonction « par provenance et digest »: elle sera verte
   sur des banques dont le contenu est identique au pas près.
2. **La protection est calculée en échantillon.** Le candidat est accepté si sa MAE sur
   les six trials publics ne dégrade pas la MAE courante — or ces transitions sont
   exactement celles sur lesquelles il vient d'être ajusté. La protection ne peut plus
   détecter un sur-ajustement; elle acceptera presque toujours. C'est **strictement pire**
   que le partage pair/impair de LIFE, qui utilisait au moins des pas de temps différents.
3. **La calibration conformelle est vide de garantie.** Le facteur est calculé sur des
   résidus en échantillon, donc systématiquement trop petits, puis appliqué à une banque
   privée qui contient les mêmes transitions. Les intervalles seront étroits et H4
   mesurera une couverture en échantillon.
4. **H1 et H2 mesurent une erreur d'ajustement.** « MAE privée finale » est la MAE
   d'apprentissage. Un modèle plus flexible gagne mécaniquement. L'amélioration `>=15 %`
   de H1 et `>=5 %` de H2 deviennent des mesures de capacité, pas de schéma corporel.
5. **La variance inter-membres s'effondre.** Avec des poids `Poisson(1)` sur vingt-quatre
   trials dont trois seulement sont distincts, chaque membre reçoit les trois motifs avec
   un poids total voisin de `8 ± 2,8`: la probabilité qu'un membre perde entièrement un
   motif vaut `e⁻⁸ ≈ 0,03 %`. Les seize membres ajustent donc le même plan d'expérience à
   une repondération près, et leur dispersion sous-estime massivement l'incertitude
   épistémique. Le terme MAD dominera, c'est-à-dire une variance **constante**.
6. **Le point 5 rend H4 satisfaisable par un intervalle constant.** Un facteur conformel
   qui recale une sigma constante atteindra la couverture marginale de `90 %` par
   construction, et la porte de largeur — `< 20°` au test, « inférieure à `[10°,170°]` »
   au smoke — est franchie de très loin par tout intervalle raisonnable: la MAE du prior
   sur `18793` valait `0,888°`. Un modèle qui n'exprime **aucune** variation d'incertitude
   passerait H4.

Aucun de ces six points ne relève de la rédaction. Ils imposent B1.

## Corrections bloquantes

### B1 — rendre les banques réellement distinctes, au niveau du contenu

Tant que les quatre banques dérivent des trois mêmes plans, il n'existe dans ce protocole
aucune donnée tenue à part, et le critère J1 — « prédiction **tenue à part** de l'angle et
de la vitesse » — ne peut pas être évalué. La séparation doit porter sur les
trajectoires, pas sur les graines.

#### Texte normatif intégrable

> **Partition des trajectoires.** Chaque motif `impulsion`, `renversement`, `micro` est
> décliné en **douze instances de plan distinctes**, gelées avant code avec leurs cibles,
> coûts, digests et bornes, toutes conformes aux contraintes déjà en vigueur: `32` pas,
> départ et retour à `90°`, cibles dans `[30°,150°]`, coût commandé commun, éligibilité
> sous `predicted_risk <= 0,50` et `motor_cost <= 0,80`. Deux instances au moins par motif
> doivent différer par la position temporelle de leurs segments, et non seulement par leur
> amplitude.
>
> Les instances sont réparties **sans recouvrement** entre les quatre rôles: `2` par motif
> pour les trials publics, `8` par motif pour les trials d'apprentissage, `2` par motif
> pour la banque privée. La banque faute reprend les instances de la banque privée avec
> l'actionneur bloqué, ce qui conserve son appariement. Aucune instance ne remplit deux
> rôles.
>
> **Porte de disjonction par contenu.** La porte smoke 2 est renforcée: elle asserte, pour
> chaque organisme, qu'aucune transition de la banque privée ou de la banque faute ne
> partage à la fois le digest de plan et l'indice de pas avec une transition publique ou
> d'apprentissage, et que les suites d'angles AS5600 des instances affectées à des rôles
> différents ne sont pas égales au `1e-9` près. La disjonction par provenance et digest de
> session est conservée mais n'est plus suffisante.
>
> **Déclaration de substrat.** Le pré-enregistrement déclare que la suite d'angles AS5600
> est une fonction déterministe de l'organisme et des cibles, qu'aucun bruit d'observation
> n'affecte la cible, que la seule quantification vaut `0,087890625°`, et donc qu'une
> réplication ne peut être obtenue qu'en changeant la trajectoire, jamais la graine
> d'exécution. Une variante admissible, si la génération de douze instances par motif est
> jugée trop lourde, est un **prologue randomisé**: `k` pas tirés dans un espace RNG
> réservé avant le plan gelé, de sorte que l'état initial diffère d'un trial à l'autre;
> dans ce cas la porte de disjonction porte sur les prologues et le pré-enregistrement gèle
> `k` et la loi de tirage avant code.

### B2 — protection et calibration ne peuvent pas partager le même ensemble

Même après B1, les six trials publics servent **deux** fonctions statistiques
incompatibles: ils décident vingt-quatre acceptations successives, et ils calibrent le
facteur conformel à neuf checkpoints. Une calibration conformelle n'est valide que si
l'ensemble de calibration est indépendant du modèle évalué; ici, le modèle a été
*sélectionné* sur cet ensemble vingt-quatre fois. Le facteur sera optimiste, et H4
mesurera une couverture biaisée vers le bas.

Le coût du correctif est nul: six trials supplémentaires par organisme représentent
`192` pas de contrôle, soit moins de `0,5 %` du budget total.

#### Texte normatif intégrable

> **Séparation protection / calibration.** Trois ensembles disjoints par trajectoire sont
> gelés: `apprentissage` (24 trials), `protection` (3 trials, un par motif) et
> `calibration` (3 trials, un par motif), auxquels s'ajoutent la banque privée
> d'évaluation et la banque faute. La règle d'acceptation n'utilise que l'ensemble
> `protection`; le facteur conformel n'est calculé que sur l'ensemble `calibration`, qui
> n'intervient dans aucune décision d'acceptation. Le pré-enregistrement déclare que le
> facteur conformel reste conditionné aux acceptations passées, donc que sa garantie est
> approximative et non exacte, et il exporte à chaque checkpoint la taille effective de
> l'ensemble de calibration.

### B3 — M et B2 ne reçoivent pas la même quantité de données d'ajustement

La ridge LIFE est décrite comme « comparateur historique, y compris ses refus », avec
« protection pair/impair identique à LIFE-012 ». Elle ajuste donc sur les indices pairs
des trials d'apprentissage, soit `16` transitions par trial, tandis que M ajuste sur les
`32`. Sur vingt-quatre trials: `384` transitions pour B2 contre `768` pour M. Le
pré-enregistrement annonce « à budget d'observation identique »: le budget d'**observation**
l'est, le budget d'**ajustement** ne l'est pas, dans un rapport de deux.

H2 exige `>=5 %` d'amélioration de M sur B2. Une part inconnue de cet écart serait
imputable au doublement des données, pas au modèle. Et si la base de features de chaque
membre de M est celle de B2 — le pré-enregistrement ne le dit pas —, alors H2, une fois le
confondant retiré, teste le **bagging d'une ridge linéaire**, dont le gain attendu en MAE
est proche de zéro: le seuil `>=5 %` serait alors inatteignable pour une raison de théorie
et non de dessin.

#### Texte normatif intégrable

> **Base de M et arme de comparaison équitable.** (i) Le pré-enregistrement écrit la
> **liste exhaustive et gelée** des régresseurs de chaque membre de M, avec leurs
> normalisations analytiques, exactement comme LIFE-010 avait gelé ses treize features, et
> indique explicitement en quoi elle diffère ou non de celle de B2.
> (ii) Un quatrième modèle `B2'` est ajouté: **même base et même `alpha` que B2**, mais
> ajusté sur les mêmes transitions que M et protégé par le même ensemble `protection`. H2
> est portée par la comparaison `M` contre `B2'`; la comparaison `M` contre `B2` est
> conservée comme référence historique **descriptive**, hors famille Holm et sans seuil.
> (iii) Si les bases de M et de `B2'` sont identiques, le pré-enregistrement déclare que
> H2 mesure l'effet du bagging par trials et de l'agrégation, justifie le seuil `>=5 %`
> pour cet effet-là, ou abaisse H2 au rang de porte descriptive et laisse H1 porter la
> taille d'effet.

### B4 — les portes ne testent pas le critère J1, et deux d'entre elles sont satisfaites par construction

`DEVELOPMENTAL_ARCHITECTURE.md` §J1 fixe le critère de passage: « prédiction tenue à part
de **l'angle et de la vitesse** meilleure que **persistance**, et détection fiable d'une
commande sans effet ». Le §12.2 reprend « gain sur une baseline persistance ». Or:

1. **Aucune hypothèse ne compare M à B0.** H1 compare M au prior physique, H2 à la ridge
   LIFE. B0 est implémentée mais n'entre dans aucune porte. Le critère nommé du jalon
   n'est pas testé;
2. **Aucune porte ne porte sur la vitesse.** La variation d'angle est déclarée « métrique
   dérivée obligatoire » et n'apparaît dans aucune hypothèse. Le critère J1 en fait
   pourtant une condition explicite;
3. **H5 est séparable par construction.** Dans la banque faute, l'actionneur est bloqué à
   l'angle courant: la variation observée y vaut exactement `0`, alors qu'elle vaut jusqu'à
   `±12°` par pas dans la banque normale. Le score
   `|observed_next − predicted_mean| / max(sigma, 0,0879°)` sépare donc les deux banques
   quel que soit le modèle, y compris le prior physique — et un détecteur trivial sans
   aucun modèle, `|observed_next − current_angle|`, les sépare parfaitement. Une AUROC
   `>= 0,85` ne démontrerait rien sur le schéma corporel ni sur l'incertitude;
4. **Les portes de largeur de H4 sont vacues.** `< 20°` au test et « inférieure à
   `[10°,170°]` » au smoke, pour un prior dont la MAE vaut de l'ordre de `0,9°`. Combinées
   au point 6 du §1, elles laissent passer un intervalle constant.

#### Texte normatif intégrable

> **H0 — critère J1 explicite.** Une hypothèse `H0` est ajoutée, évaluée sur la banque
> privée et dans la même famille Holm que H1: la MAE de M est meilleure que celle de la
> persistance `B0` sur **l'angle** et sur la **variation d'angle**, avec au moins `16/24`
> organismes favorables et une moyenne favorable dans chaque régime. La métrique de
> variation est définie comme `MAE(Δangle_prédite, Δangle_observée)` sur les mêmes
> transitions. H1 et H2 sont également rapportées sur la variation d'angle, avec le même
> seuil relatif que sur l'angle.
>
> **H5 — détecteur de référence et faute graduée.** (i) Un détecteur de référence sans
> modèle, `score_trivial = |observed_next − current_angle|`, est évalué sur les mêmes
> banques et sa courbe AUROC est rapportée. H5 exige que l'AUROC de M soit **au moins égale
> à celle du détecteur trivial**, en plus des seuils absolus déjà pré-enregistrés.
> (ii) La banque faute comprend deux conditions de même taille: `bloqué` (actionneur figé à
> l'angle courant) et **`dégradé`** (actionneur dont la vitesse maximale est divisée par
> trois, mouvement donc préservé mais altéré). Les seuils `>=0,85` agrégé et `>=0,75` par
> régime sont exigés **séparément** sur chaque condition. Le pré-enregistrement déclare que
> la condition `bloqué` est séparable sans modèle et qu'elle ne constitue pas une preuve de
> schéma corporel; seule la condition `dégradé` porte cette revendication.
> (iii) Le seuil opérationnel de la condition « TPR `>=0,80` à FPR normale `<=0,10` » est
> déterminé **sur les six organismes smoke** et gelé au manifeste avant ouverture de
> `19201+`; aucun seuil n'est choisi sur le test.
>
> **H4 — netteté et couverture conditionnelle.** À la couverture marginale s'ajoutent:
> (i) une porte de netteté relative — largeur médiane de l'intervalle `90 %` inférieure à
> `6 × MAE_privée_finale_de_M`, seuil gelé ici et non révisé;
> (ii) une couverture conditionnelle rapportée et bornée dans `[0,80 ; 0,98]` sur chacune
> des classes de transition `rampe` et `plateau` de la taxonomie gelée sous D-045, ainsi que
> sur chaque tercile de déplacement prédit. Un modèle dont l'intervalle ne varie pas avec
> l'état échouera cette porte, ce qui est l'intention.

### B5 — sans plancher irréductible, un échec de plasticité n'est pas attribuable

H3 exige « au moins une acceptation sur `24/24` organismes ». Deux problèmes.

**Le plancher n'est pas connu.** Puisque la cible ne porte aucun bruit d'observation
(§1), toute erreur résiduelle vient d'un **état non observé**: la rampe interne
`_limited_deg` et la vitesse articulaire, explicitement interdites aux features. Le
plancher irréductible de ce protocole est donc exactement la part de la dynamique non
reconstructible depuis les features autorisées, et personne ne l'a jamais mesurée. Sans
lui, une porte rouge sur `18793` ou son successeur reste inattribuable: modèle
insuffisant, ou tâche sans marge?

**La porte peut exiger un sur-ajustement.** Sur un organisme où le prior est déjà proche
du plancher, refuser toutes les mises à jour est le comportement **correct**. H3 exige
pourtant une acceptation partout. Si le taux d'organismes sans marge est de l'ordre de
celui observé — un sur six en LIFE-012 —, la probabilité qu'au moins un des vingt-quatre
organismes de test en soit un vaut `1 − (5/6)²⁴ ≈ 98,7 %`, et `1 − (5/6)⁶ ≈ 66,5 %` sur
les six organismes smoke. Ce taux n'est estimé que sur une observation et son intervalle
est très large, mais l'ordre de grandeur suffit: H3 telle qu'écrite est probablement
inatteignable, pour une raison qui n'est pas un défaut du modèle.

#### Texte normatif intégrable

> **Modèle privilégié de plancher.** Un cinquième modèle `P`, purement diagnostique, est
> ajouté: même base que M, augmentée de `_limited_deg` et de la vitesse articulaire lues
> directement dans le simulateur. `P` n'est jamais une baseline, n'entre dans aucune
> hypothèse, ne fournit aucune feature à M et n'est jamais promu. Sa MAE privée par
> organisme est exportée comme **estimation du plancher irréductible**, et la marge
> disponible d'un organisme est définie comme
> `marge = (MAE_prior − MAE_P) / MAE_prior`.
>
> **Conditionnement de la plasticité.** Le pré-enregistrement gèle un seuil de marge
> `marge >= 0,10` avant tout calcul. H3 exige au moins une acceptation sur **chaque
> organisme dont la marge dépasse ce seuil**, et exige des organismes sous le seuil qu'ils
> ne subissent **aucune dégradation** au-delà de `1e-12` sur l'ensemble `protection`. Le
> nombre d'organismes de chaque catégorie est rapporté. Aucun organisme n'est filtré,
> remplacé ou rejoué; la catégorie est une attribution, pas une exclusion.
>
> **Cas diagnostique 18793.** Le smoke exécute, **hors de toutes les portes** et comme cas
> diagnostique déclaré, les mêmes quatre modèles et `P` sur les paramètres d'organisme de
> la graine `18793` — graine smoke non réservée, déjà entièrement publiée sous D-046. Ce
> cas ne compte dans aucune porte, aucune moyenne, aucune famille statistique et n'ouvre
> aucune banque LIFE. Il a un seul objet: établir si le mécanisme proposé corrige
> effectivement le refus `24/24` observé, ou si cet organisme est sans marge. En l'absence
> de ce contrôle, le lien entre le défaut constaté et le correctif proposé reste une
> hypothèse non testée.

### B6 — quatre sous-spécifications qui exigeraient une décision scientifique en cours de code

1. **Du MAD à une variance.** « Variance robuste des résidus publics, estimateur MAD
   gelé » ne définit ni le facteur de consistance, ni le modèle sur lequel les résidus
   sont calculés, ni s'il est global ou par classe de transition. Un MAD n'est pas une
   variance.
2. **De la variance à un intervalle `90 %`.** Aucun quantile n'est spécifié. Selon que
   l'intervalle vaut `1,645 σ` puis facteur conformel, ou `σ` fois un facteur conformel
   calibré directement sur le score `|résidu| / σ`, les largeurs diffèrent d'un facteur
   proche de deux.
3. **Membre bootstrap vide.** Avec `Poisson(1)` et un seul trial disponible au premier
   pas, environ `6` des `16` membres reçoivent un poids total nul. Une ridge sans donnée
   n'est pas définie par le texte.
4. **Marge de non-infériorité par organisme.** H3 compare « MAE finale » et « meilleur
   checkpoint » avec une marge `0,02 × MAE_initiale` qui varie d'un organisme à l'autre,
   alors que `monte_carlo_noninferiority_pvalue` prend une marge **scalaire**. Sans
   normalisation, le test n'est pas implémentable tel quel — c'est la même ambiguïté que
   B7 de LIFE-010 sous une autre forme.

#### Texte normatif intégrable

> **Spécifications numériques gelées.** (i) L'écart-type robuste vaut
> `sigma_bruit = 1,4826 × MAD(résidus du modèle courant sur l'ensemble calibration)`,
> calculé séparément pour les classes `rampe` et `plateau` et appliqué selon la classe de
> la transition prédite; la variance brute vaut
> `sigma² = variance_inter_membres + sigma_bruit²`.
> (ii) L'intervalle `90 %` vaut `prédiction ± q × sigma`, où `q` est l'unique facteur
> conformel symétrique défini comme le quantile empirique d'ordre `0,90` du score
> `|résidu| / sigma` sur l'ensemble calibration, avec interpolation `higher`. Aucun
> quantile gaussien n'est utilisé.
> (iii) Un membre dont le poids bootstrap total est nul rend exactement le prior physique,
> et sa contribution à la variance inter-membres est comptée normalement.
> (iv) H3 est testée sur les différences normalisées
> `d_i = (MAE_meilleur_checkpoint_i − MAE_finale_i + 0,02 × MAE_initiale_i) / MAE_initiale_i`,
> par `monte_carlo_sign_flip_pvalue(d, alternative="greater", n_resamples=200000,
> seed=2026072706)`, l'hypothèse nulle étant rejetée en faveur de la non-infériorité. La
> graine statistique est passée explicitement à chaque appel de `learning/paired_stats.py`,
> dont le défaut est `seed=0`.

## Points audités et jugés conformes

- **Rupture avec LIFE.** Aucune allocation, aucun oracle, aucun professeur contrefactuel,
  aucun carré latin, excitation fixe et identique pour tous les modèles, aucun seuil LIFE
  repris, aucune graine LIFE réutilisée. La famille close par D-046 n'est pas relancée
  sous un autre nom.
- **Ordre des jalons.** Le retour J1 avant J5 est conforme à `DEVELOPMENTAL_ARCHITECTURE.md`
  §2 et à la condition de réouverture inscrite en D-046. La section « Décision » exclut
  correctement J5, le curriculum, la causalité générale, le transfert physique et la
  conscience.
- **Choix statistiques.** `n = 24` dépasse la limite d'énumération exacte
  `_MAX_EXACT_N = 20` de `learning/paired_stats.py`: le Monte-Carlo des signes à `200 000`
  tirages est le bon appel, et l'estimateur add-one garantit `p > 0`. La famille Holm à
  deux tests pour H1/H2 et une famille séparée pour H3 sont cohérentes avec l'usage gelé
  depuis LIFE-010.
- **Absence de développement inter-organismes.** Tous les hyperparamètres sont gelés au
  pré-enregistrement; il n'y a ni P0 ni ajustement de méta-paramètre, donc aucune fuite
  possible par sélection de modèle entre organismes. C'est une simplification réelle par
  rapport à LIFE.
- **Information autorisée.** La liste des entrées ne contient ni régime, ni paramètre
  MuJoCo, ni `_limited_deg`, ni banque privée, ni graine d'organisme. La cible suivante est
  une commande connue à l'inférence, donc son usage n'est pas une fuite. Sous réserve de
  B3, qui exige que la base exacte soit écrite.
- **Discipline d'échec.** « Un organisme avec zéro acceptation est un échec de plasticité,
  jamais filtré ou remplacé » et « en cas d'échec, aucune variante de sélecteur LIFE n'est
  relancée » sont exactement les clauses qui ont rendu D-037, D-040, D-043 et D-046
  mécaniques. Elles sont conservées.
- **Budget.** `42` trials de `32` pas sur `24` organismes valent environ `32 000` pas de
  contrôle, soit de l'ordre de six minutes au débit mesuré en LIFE-009 (`696 s` pour
  `≈69 000` pas), auxquels s'ajoutent des ajustements de ridge négligeables. Les
  corrections B1, B2, B4 et B5 ajoutent au plus quelques milliers de pas: le plafond de
  `90` minutes reste très largement tenu, et aucune correction n'est refusable pour coût.
- **Attribution déclarée.** « Le rapport attribue l'échec à plasticité, représentation,
  calibration ou détection selon la porte concernée » est la bonne structure; B5 lui donne
  le quatrième terme qui manquait, l'absence de marge.

## Remarques non bloquantes

- **R1 — le banc n'a pas de bruit d'angle.** `BenchSensorConfig` modélise des biais et des
  bruits pour le gyroscope, l'accéléromètre et l'ultrason, mais l'AS5600 n'est que quantifié.
  Un capteur réel a du bruit, de l'hystérésis et une erreur de linéarité. Ce n'est pas à
  corriger dans cette tranche — cela changerait le substrat commun à toutes les campagnes
  passées — mais l'écart mérite d'être inscrit dans les limites, d'autant que la tranche
  prétend qualifier une incertitude calibrée sur un canal sans aléa.
- **R2 — l'incertitude est purement épistémique.** Faute d'aléa d'observation, un
  intervalle calibré exprime ici l'ignorance du modèle sur un état caché, pas un bruit. La
  section de portée devrait le dire, sous peine de laisser croire que la calibration
  transporterait telle quelle sur le banc physique.
- **R3 — `ARX` n'est pas défini.** Le terme apparaît une fois et n'est adossé ni à un ordre
  de retard, ni à une liste de régresseurs. B3 le règle, mais le vocabulaire devrait être
  aligné sur la description effective.
- **R4 — la porte smoke 5 est une porte à minimum.** « M termine avec MAE privée `<=90 %`
  du prior sur **chacun** » reproduit la structure de minimum par organisme qui a fermé
  LIFE-011 et LIFE-012. Elle est ici mieux fondée, parce que J1 exige une prédiction fiable
  partout et non en moyenne; mais elle doit être lue avec le classement de marge exigé en
  B5, faute de quoi elle échouera sur le premier organisme sans marge.
- **R5 — neuf checkpoints, vingt-quatre trials.** La banque privée est lue aux instants
  `0,3,…,24`, donc l'essentiel de la trajectoire d'apprentissage n'est pas observé. Ce
  choix est raisonnable pour le coût, mais avec trois trajectoires distinctes seulement
  (avant B1) toute la courbe est plate après le troisième trial; après B1, il vaudra la
  peine de vérifier que neuf points suffisent à situer le meilleur checkpoint exigé par H3.

## Synthèse

Le diagnostic de D-046 est juste et le retour à J1 est la bonne décision: aucun
ordonnanceur ne peut créer du progrès sur une compétence qui n'en produit pas, et il
fallait cesser de fabriquer des triplets de plans. BODY-SCHEMA-001 pose les bonnes
questions — plasticité, incertitude calibrée, détection d'une commande sans effet — dans
le bon ordre, avec un budget confortable et une discipline d'arrêt éprouvée.

Ce que la tranche n'a pas vu, c'est que le banc ne produit aucun aléa sur le canal qu'elle
mesure. Les « graines RNG séparées » qui fondent la distinction entre banque publique,
banque d'apprentissage, banque privée et banque faute n'agissent que sur le gyroscope,
l'accéléromètre et l'ultrason; la suite d'angles AS5600 est une fonction déterministe de
l'organisme et des cibles. Les quatre banques contiennent donc les mêmes trois
trajectoires, la protection et la calibration conformelle sont calculées en échantillon,
et la métrique primaire est une erreur d'ajustement. Le même constat explique la forme du
défaut qui motive toute la tranche: « `24/24` refus » est un fait unique répété, pas
vingt-quatre observations.

**Autorisation.** Une fois **B1 à B6** intégrées comme amendements pré-calcul datés et
additifs, **l'implémentation peut commencer, puis le smoke `19091..19096` peut être
exécuté**. Les graines de test `19201..19224` restent interdites jusqu'à: partition des
trajectoires gelée et porte de disjonction par contenu verte; ensembles `protection` et
`calibration` disjoints; bases de M et de `B2'` écrites; H0 et les portes de variation
d'angle ajoutées; détecteur trivial et condition de faute dégradée en place; modèle
privilégié `P`, classement de marge et cas diagnostique `18793` exportés; les quatre
spécifications numériques de B6 gelées; puis dix portes smoke vertes. Toute promotion
reste interdite avant une revue contradictoire des résultats.
