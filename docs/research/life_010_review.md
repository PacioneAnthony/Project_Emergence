# Revue contradictoire pré-calcul LIFE-010 — curriculum appris, dynamique protégée

Date: 2026-07-27. Revue demandée avant implémentation, smoke `18191..18196`, banques
`18201..18248` et test `18301..18324`. Fichiers audités intégralement:
`docs/research/life_010_preregistration.md`,
`docs/research/life_009_preregistration.md`, `docs/research/life_009_review.md`,
`docs/research/life_009_technical_stop.md`, `docs/research/life_008_spec.md`,
`docs/research/kernel_001_implementation.md`, `DEVELOPMENTAL_ARCHITECTURE.md`,
`DECISIONS.md` (D-034 à D-038), `PILOTAGE.md`, `SESSION_HANDOFF.md`; en complément
`learning/paired_stats.py`, `sim3d/life_executor.py`, `sim3d/bench_env.py` et
`sim3d/bench_model.py` pour juger l'implémentabilité du prior physique et des plans.

Aucun test expérimental, simulation, entraînement, smoke ni calcul n'a été lancé. Les
seuls calculs effectués sont une **arithmétique sur les trois plans pré-enregistrés**
(longueur, coût commandé, retour à `90°`, nombre de changements de cible) et une lecture
du limiteur de vitesse de `BenchHeadEnv`. Aucun fichier autre que la présente revue n'a
été modifié.

## Verdict

**AUTORISER AVEC CORRECTIONS BLOQUANTES.**

LIFE-010 est une reconception sérieuse, pas un retuning. Le diagnostic de LIFE-009 a été
compris et traité à la racine: le prior est désormais physique et améliorable, les trois
expériences sont **exactement équicûteuses** — ce qui neutralise le confondant qui avait
enfermé LIFE-009 — la banque privée couvre exactement l'espace d'action, et la marge
oracle redevient une porte préalable. La porte B2 que j'avais imposée à LIFE-009 a
fonctionné mécaniquement: elle a fermé la campagne à `2,383 %` de marge sans qu'aucune
banque réservée soit ouverte. C'est le bon usage de ce dispositif, et LIFE-010 le
conserve en le durcissant.

Les trois plans se vérifient exactement: `32` pas, `560°` commandés, retour à `90°`, avec
`5`, `14` et `28` changements de cible — conformes aux descriptions. Les affectations de
régime par graine modulo trois donnent bien `2/2/2` au smoke et `8/8/8` au test.

Sept corrections bloquantes restent nécessaires. La principale est que **la taille
d'effet est ancrée sur la baseline qui a le plus de chances d'être la plus faible du
lot**, ce qui rend une promotion possible sur une amélioration négligeable face à la
baseline réellement exigeante. Les six autres portent sur une direction de porte inversée,
une validation publique quasi dupliquée de l'ajustement, une incohérence entre le smoke et
l'assiette de projection, un alignement du prior à asserter correctement, et deux limites
de portée à déclarer.

## 0. LIFE-010 corrige-t-il réellement LIFE-009 ?

Oui, et point par point. C'est à porter au crédit du dossier.

| Cause LIFE-009 | Traitement LIFE-010 | Jugement |
|---|---|---|
| Amplitudes `110`/`160` évaluées mais inatteignables (B1) | Banque privée = `2 × 3 × 32 = 192` transitions produites par **les trois plans eux-mêmes**; « couvre exactement l'espace d'action » | **Corrigé à la racine.** La garde anti-sacrifice par motif porte enfin sur des motifs tous atteignables |
| Coût moteur encodant presque l'allocation, plafond P3 enfermant la politique | Coût commandé **exactement** `560°` par plan; total `24 × 560°` identique pour toute politique | **Corrigé.** Le coût cesse d'être un confondant, et la garde P3 correspondante devient structurelle |
| Baseline principale dégénérant en tourniquet | `greedy_public_residual` exploite le signal public par motif; `round_robin` reste baseline secondaire distincte | Corrigé quant à la dégénérescence; voir **B1** quant à la force relative |
| Modèle dégradant le prior (AUC toutes `> 1`) | Prior physique explicite, poids initiaux nuls, apprentissage du **résidu** seul, et porte smoke « MAE privée round-robin finale `≥20 %` sous le prior » | **Corrigé, et bien gardé.** C'est la porte qui manquait |
| Marge oracle non démontrée avant campagne (B2) | Porte smoke: médiane des six `≥15 %` et minimum par régime `≥5 %`, face à la baseline principale | Corrigé et durci |
| Test exact impossible à `n=24` (B3) | `monte_carlo_sign_flip_pvalue`, `200 000` tirages, graine `2026072703`, add-one inchangé | Corrigé exactement |
| Branches contrefactuelles contaminant l'histoire (B4) | Magasins SQLite/J0 temporaires distincts, `mj_copyData`, flux nommés et copiés séparément, replay bit-identique, comptes `24` exacts | Corrigé |
| Assiette de projection amputée du professeur (B5) | Projection chronométrant banque privée, professeur `24×3`, politiques test, oracle, `25` évaluations, analyse et digests, avec multiplicateurs `32/8/24` | Corrigé; voir **B4** ci-dessous pour une incohérence résiduelle |
| Sentinelles et colonnes de variance nulle (B6, R3) | Sentinelle `0.0` + indicateur d'absence; échelle `1.0` pour toute colonne de variance nulle | Corrigé |
| Ordonnancement de P0 (B7) | Séquence explicite en huit étapes, test ouvert seulement si tout passe | Corrigé |

Je n'ai trouvé **aucun succès artificiel** parmi ceux que le prompt demande de chercher,
à deux réserves près traitées en B1 et B3: le prior n'est pas rendu trivialement
améliorable (il est physiquement juste et l'amélioration exige d'apprendre un résidu
d'organisme réel), la protection anti-dégradation n'empêche pas la plasticité (elle est
monotone sur un ensemble croissant, et le candidat est réajusté sur toutes les données à
chaque cycle), et les plans sont réellement équicûteux.

## Corrections bloquantes

### B1 — la taille d'effet est ancrée sur la baseline la plus susceptible d'être faible

`greedy_public_residual` choisit « le motif à MAE publique la plus haute ». C'est un
choix défendable et il reçoit exactement le signal que reçoit la politique apprise, ce
qui satisfait la règle 2 du brief. Mais c'est aussi une heuristique dont la pathologie est
connue et prévisible: **greedy-sur-l'erreur poursuit indéfiniment le motif intrinsèquement
le plus dur**, même lorsque celui-ci a cessé de progresser. Or les trois plans n'ont
aucune raison d'avoir le même résidu irréductible: `probe_step_hold` commande des sauts de
`140°` que le servo ne peut jamais achever en six pas, et ses résidus en degrés seront
structurellement plus grands que ceux de `probe_micro`, dont les commandes valent `20°`.

Le scénario probable est donc: `greedy_public_residual` se verrouille sur `step_hold`,
n'acquiert presque rien sur `reversal` et `micro`, et termine avec une MAE privée
globale médiocre. La politique apprise la bat alors de `≥5 %` **sans avoir rien appris
d'intéressant**, simplement en diversifiant — et `round_robin`, baseline secondaire, la
battrait tout autant.

La structure des portes ne protège qu'à moitié. P2 exige bien que la politique apprise
batte `round_robin`, mais **sans plancher de taille d'effet**: « La taille d'effet est
portée par P1 ». Une promotion pourrait donc être accordée sur `+5 %` face à une baseline
verrouillée et `+0,1 %` face à la baseline réellement exigeante, avec `p ≤ 0,05`.

Le smoke dispose déjà de tout le nécessaire pour trancher: il exécute `round_robin` et
`greedy_public_residual` sur les six graines non réservées.

#### Texte normatif intégrable

> **Ancrage de la taille d'effet.** Le smoke `18191..18196` rapporte, pour les six graines
> et par régime, l'AUC normalisée de `round_robin` et de `greedy_public_residual`. Deux
> cas, tranchés **avant** toute ouverture de banque et écrits au manifeste avec le digest
> du protocole:
>
> 1. si `greedy_public_residual` obtient une AUC moyenne **meilleure ou égale** à celle de
>    `round_robin`, elle demeure la baseline principale de P1 sans changement;
> 2. si `greedy_public_residual` obtient une AUC moyenne **strictement pire** que celle de
>    `round_robin`, alors `round_robin` devient co-principale: le plancher d'amélioration
>    relative de `≥5 %`, la condition `16/24` et la condition de signe par régime de P1
>    s'appliquent **séparément aux deux baselines**, et les deux doivent être franchies.
>
> Dans les deux cas, P2 est complétée d'un plancher: l'amélioration relative moyenne de
> l'AUC apprise face à `round_robin` doit atteindre **`≥3 %`**, en plus de sa
> significativité corrigée par Holm. Ce choix est gelé ici et n'est jamais révisé après
> lecture d'une métrique de développement, de validation ou de test.

### B2 — la direction de la porte P3 sur la MAE finale est inversée

P3 énonce:

> « MAE finale apprise **non inférieure** à la baseline principale avec marge
> `0.02 × MAE_initiale` »

Une MAE plus basse étant meilleure, « non inférieure » exige littéralement que la
politique apprise soit **au moins aussi mauvaise** que la baseline. C'est l'inverse de
l'intention: LIFE-009 écrivait correctement « MAE finale moyenne apprise **au plus**
`MAE_finale_greedy + 0,02 × MAE_initiale` ». Une porte dont le sens de l'inégalité est
ambigu ne peut pas être implémentée sans décision scientifique supplémentaire, et
l'erreur est du type qui survit aux tests unitaires.

#### Texte normatif intégrable

> **P3, non-dégradation de la MAE finale.** La MAE privée finale moyenne de la politique
> apprise satisfait
>
> ```text
> MAE_finale_apprise <= MAE_finale_baseline_principale + 0,02 × MAE_initiale
> ```
>
> c'est-à-dire que la politique apprise n'est pas matériellement pire que la baseline
> principale en fin de campagne. La même convention « plus bas est meilleur » s'applique
> à la porte de pire MAE par motif, qui exige
> `pire_MAE_motif_apprise <= 1,10 × pire_MAE_motif_baseline_principale`.

### B3 — la validation publique est quasi dupliquée de l'ajustement, et deux portes de P3 sont tautologiques

**Autocorrélation.** Le partage pair/impair découpe une trajectoire de `32` transitions
consécutives d'un même essai. Or les transitions voisines d'un servo sont fortement
autocorrélées: pendant une rampe saturée, les transitions `i` et `i+1` partagent le même
signe d'erreur, le même régime et un déplacement quasi identique. L'ensemble « impair »
n'est donc pas une validation tenue à part au sens statistique: c'est un **voisin
immédiat** de chaque point d'ajustement. Il ne peut pas détecter de sur-ajustement, et le
nombre effectif d'observations indépendantes est très inférieur à `16` par essai.

Conséquence directe: la règle d'acceptation « le candidat ne doit pas dégrader la MAE
publique » sera presque toujours satisfaite, puisque bien ajuster les pairs ajuste
mécaniquement les impairs. La « plasticité protégée », annoncée comme l'une des deux
exigences nouvelles de LIFE-010, risque de n'avoir **jamais** l'occasion de mordre.

**Deux portes satisfaites par construction.** Le prompt demande de les signaler; il y en a
exactement deux dans P3:

1. « aucune mise à jour acceptée ne dégrade la MAE publique au-delà de `1e-12` » est
   **logiquement impliquée par la règle d'acceptation elle-même**, qui accepte si et
   seulement si `MAE_candidate <= MAE_courante + 1e-12`. Cette porte ne peut échouer que
   sur un bug d'implémentation;
2. « coût commandé exactement égal entre politiques » est garantie par la construction des
   plans, tous à `560°`, et par le budget fixe de `24` cycles.

Ce sont de bonnes **assertions d'intégrité** — la seconde est même une force réelle du
protocole, puisqu'elle neutralise le confondant qui avait tué LIFE-009 — mais aucune des
deux n'est une preuve scientifique et elles ne doivent pas être présentées comme telles.

#### Texte normatif intégrable

> **Statut de la validation publique et des portes structurelles.** (i) Le
> pré-enregistrement déclare que le partage pair/impair produit une validation publique
> **fortement autocorrélée** avec les données d'ajustement, qu'elle constitue donc une
> garantie de non-dégradation grossière et non un test de généralisation, et que la
> banque privée demeure la seule mesure de compétence. (ii) Le smoke rapporte, pour
> chacune des six graines, le nombre de candidats **acceptés et refusés** sur les `24`
> cycles, ainsi que l'écart médian entre MAE publique et MAE privée. Si aucun refus n'est
> observé sur aucune des six graines, le pré-enregistrement acte que la protection n'a
> pas été exercée et **retire la plasticité protégée de la revendication** d'un succès
> éventuel, sans modifier la règle ni les seuils. (iii) Les deux conditions de P3
> ci-dessus sont reclassées en **assertions d'intégrité** et listées hors des portes
> scientifiques; leur échec reste un arrêt immédiat.

### B4 — le smoke ne mesure pas l'assiette que la projection prétend appliquer

Deux passages se contredisent. La section « Smoke avant banques » énonce:

> « Les six graines smoke exécutent **round-robin, baseline principale et oracle**. »

soit trois politiques. La section suivante énonce que la projection chronomètre

> « banque privée, professeur `24×3`, **six politiques test**, oracle, 25 évaluations,
> analyse et digests. »

Le terme dominant du coût de campagne est le déroulé test — `24 graines × 6 politiques ×
24 cycles = 3 456` exécutions de plan, auxquelles s'ajoutent `1 728` exécutions d'oracle
et `2 880` exécutions de professeur. Si le smoke ne mesure que trois politiques, la
projection extrapole d'un facteur `2` sur ce terme dominant au lieu de le mesurer. C'est
la faiblesse d'assiette que la correction B5 de LIFE-009 avait fermée, réintroduite sous
une autre forme.

L'ordre de grandeur reste plausible — LIFE-009 a mesuré `696 s` pour environ `69 000` pas
de contrôle, LIFE-010 en demande environ `270 000`, soit une projection de l'ordre de
`45` minutes sous un plafond de `90` — mais une projection doit être mesurée, pas estimée.

#### Texte normatif intégrable

> **Assiette mesurée du smoke.** Les six graines smoke exécutent les **six politiques
> test** ainsi que l'oracle contrefactuel, et chronomètrent séparément: génération de la
> banque privée, construction professeur `24 × 3`, déroulé de chacune des six politiques,
> passes d'oracle, les `25` évaluations de courbe, l'analyse et les digests. La projection
> applique les multiplicateurs exacts `32` développement, `8` validation et `24` test aux
> phases correspondantes. Les portes de conception du smoke — progrès `≥20 %`, médiane de
> marge oracle `≥15 %`, minimum par régime `≥5 %` — restent évaluées sur `round_robin`,
> `greedy_public_residual` et l'oracle uniquement; l'exécution des trois autres politiques
> sert exclusivement au chronométrage et à B1, et **aucune de leurs métriques n'entre dans
> une porte de conception**.

### B5 — l'alignement du prior à `12°/pas` doit être asserté sur ce qui est réellement borné

Le prior est `clip(current + clip(next_target − current, ±12°), 10°, 170°)`, justifié par
« pas de contrôle `20 ms`, servo nominal `600°/s` ». La vérification du code confirme
l'essentiel: `sim3d/life_executor.py` exécute exactement `env.step(target_deg)` par pas de
plan, `BenchConfig.control_dt = 0,02 s`, `BenchServoConfig.max_speed_deg_s = 600,0`, et
`bench_env.py` calcule `max_delta = max_speed_deg_s × control_dt = 12,0`. Un pas de plan
vaut donc bien un pas de contrôle de `20 ms`, et la constante `12°` est exacte.

Mais le limiteur s'applique à `self._limited_deg`, **rampe de commande interne**, et non à
l'angle mesuré:

```python
delta = clamp(target - self._limited_deg, -max_delta, max_delta)
self._limited_deg = clamp(self._limited_deg + delta, servo.min_deg, servo.max_deg)
```

L'angle réel poursuit ensuite `_limited_deg` par la boucle PD. Deux conséquences que le
pré-enregistrement ne mentionne pas:

1. **`12°` n'est pas une borne du déplacement mesuré.** Lorsque l'angle réel est en retard
   sur la rampe interne, il peut rattraper de **plus** de `12°` en un pas. Une assertion
   smoke naïve du type « `|Δ as5600| ≤ 12°` » échouerait légitimement et arrêterait le
   protocole à tort.
2. **`_limited_deg` est un état caché non observable.** Ni le prior ni la base résiduelle
   n'y ont accès; les features publiques n'en contiennent qu'un proxy partiel, la
   variation AS5600 précédente. Le résidu n'est donc pas une fonction exacte des features
   disponibles, et il subsiste une erreur irréductible identique pour toutes les
   politiques. C'est acceptable — la porte smoke `≥20 %` la borne empiriquement — mais
   cela doit être écrit, faute de quoi un plancher de MAE sera lu comme un échec de
   curriculum.

#### Texte normatif intégrable

> **Alignement asserté du prior.** Le smoke asserte: (i) qu'un pas de plan correspond à
> exactement un pas de contrôle de `20 ms`, soit `32` pas par plan et
> `control_dt = 0,02 s`; (ii) que la constante `12°` du prior vaut exactement
> `max_speed_deg_s nominal × control_dt = 600 × 0,02`; (iii) que la rampe de commande
> interne, et non l'angle mesuré, est la grandeur bornée par le limiteur, de sorte
> qu'aucune assertion ne borne `|Δ as5600|` à `12°`. Le pré-enregistrement déclare que
> l'état interne de rampe est caché et non reconstructible depuis les observations
> publiques, qu'il induit une erreur résiduelle irréductible commune à toutes les
> politiques, et que cette erreur est bornée empiriquement par la porte de progrès
> `≥20 %` du smoke.

### B6 — deux limites de portée à déclarer avant, pas après

Le prompt demande explicitement de chercher « des régimes mécaniques artificiellement
séparables » et d'évaluer « la portée exacte d'une promotion ». Deux propriétés du dessin
facilitent la tâche par rapport à toute situation réaliste, et ne figurent pas dans la
section « Interprétation limitée ».

**Régimes à un facteur.** Chaque régime perturbe un seul groupe de paramètres, tous les
autres restant **nominaux**. Un organisme réel varie conjointement sur tous ses
paramètres. Inférer le régime depuis les résidus publics est donc considérablement plus
facile ici que sous une distribution jointe, ce qui gonfle la valeur apparente de toute
politique qui exploite cette inférence — apprise comme analytique.

**Banque privée de même distribution.** La banque privée exécute **les mêmes trois plans**
avec deux flux de bruit réservés. Elle mesure donc l'efficacité d'allocation sur l'espace
d'action, ce qui est le bon objectif, mais elle **n'est pas un test de généralisation**:
améliorer la MAE publique améliore quasi mécaniquement la MAE privée. C'est la réponse au
point 16 du prompt — une politique ne peut pas optimiser la validation publique au
détriment de la banque privée — mais cette réponse rassurante tient à l'identité des
distributions, non à une garde, et doit être présentée ainsi.

#### Texte normatif intégrable

> **Limites additionnelles déclarées.** Ajouter à « Interprétation limitée »: (i) les
> trois régimes perturbent un seul groupe de paramètres à la fois, les autres restant
> nominaux; l'inférence de régime y est donc plus facile que sous une variation conjointe,
> et un succès ne se transporte pas tel quel à des organismes variant sur tous leurs
> paramètres; (ii) la banque privée rejoue les mêmes trois plans sous des flux de bruit
> réservés: elle mesure l'efficacité d'allocation sur l'espace d'action et **non** la
> généralisation à des conditions nouvelles; l'impossibilité d'optimiser le public contre
> le privé découle de cette identité de distribution et non d'une garde.

### B7 — les conditions anti-sacrifice de P3 sont des comparaisons de moyennes sans incertitude

P1 et P2 sont correctement outillées: Monte-Carlo des signes, `200 000` tirages, graine
`2026072703`, Holm sur les quatre tests secondaires, P1 tenue hors famille parce que la
promotion est conjonctive — tout cela est juste et conforme au module gelé.

P3 en revanche compare des **moyennes** sans aucun traitement d'incertitude: MAE finale,
pire MAE par motif, à `n=24`. Une différence de moyennes peut franchir ou manquer un seuil
de `1,10×` par pur bruit d'échantillonnage, et le pré-enregistrement ne dit pas si ces
conditions sont des tests ou des vérifications déterministes. `learning/paired_stats.py`
expose pourtant `monte_carlo_noninferiority_pvalue`, exactement adaptée à une condition
de non-infériorité appariée.

#### Texte normatif intégrable

> **Statut statistique de P3.** Les conditions anti-sacrifice de P3 sont des **tests de
> non-infériorité appariés**, évalués par
> `learning.paired_stats.monte_carlo_noninferiority_pvalue` avec `n_resamples = 200 000`
> et graine `2026072703`. La marge de non-infériorité est `0,02 × MAE_initiale` pour la
> MAE finale et `0,10 × pire_MAE_motif_baseline` pour la pire MAE par motif. Chaque test
> doit rendre `p <= 0,05`. Ces deux tests forment une famille Holm distincte de celle de
> P2 et ne s'y mélangent pas. À défaut d'adopter cette formulation, le pré-enregistrement
> doit déclarer explicitement que les conditions de P3 sont des vérifications
> déterministes de moyennes, sans garantie de niveau, et que leur franchissement ne
> constitue pas une preuve statistique d'absence de sacrifice.

## Points audités et jugés conformes

- **Plans.** Vérifiés par arithmétique: `probe_step_hold`, `probe_reversal` et
  `probe_micro` font chacun exactement `32` pas, `560,0°` commandés et se terminent à
  `90°`, avec `5`, `14` et `28` changements de cible conformes au texte. Les portes de
  construction sont exactes et satisfaisables. La complémentarité annoncée — vitesse
  limite et établissement, renversements et transitoires, réponse locale et friction — est
  cohérente avec les trois régimes.
- **Prior physique.** Aligné au code (`600 × 0,02 = 12`), poids initiaux nuls donc modèle
  initial **exactement** égal au prior, apprentissage du résidu seul. C'est la correction
  décisive du pathos LIFE-009 où toutes les AUC dépassaient `1`. Sous réserve de B5.
- **Base résiduelle et `alpha=1.0`.** Les treize features sont analytiquement normalisées,
  sans aucune statistique issue des données — ce qui ferme une voie de fuite classique.
  Elles couvrent la saturation (`clip(erreur, ±12)/12`, qui capte à elle seule un décalage
  de vitesse par un coefficient unique), l'établissement (variation précédente),
  la friction et les maintiens (indicateur `hold` et interactions), et les renversements.
  Avec des colonnes bornées et une pénalité `alpha=1.0`, le rétrécissement est de l'ordre
  de `n/(n+1)`, négligeable dès quelques dizaines de transitions: le choix est doux et
  raisonnable.
- **Espaces RNG.** Six espaces nommés dérivés par SHA-256 de nom, version, graine, cycle
  et expérience, sans générateur global partagé; bruit de primitive indexé par
  `(organisme, cycle, expérience)` pour que la même candidate au même cycle reçoive le
  même bruit quelle que soit la politique. C'est la bonne réponse au problème des
  trajectoires divergentes.
- **Graines et équilibre.** `18191..18196` donne `2/2/2` par régime, `18301..18324` donne
  `8/8/8`, `18241..18248` donne `2/3/3`, `18201..18232` donne `11/11/10`. Toutes disjointes
  des espaces LIFE-009 `17901..17940` / `18001..18024`, jamais ouverts. Comptes d'exemples
  exacts: `32 × 24 × 3 = 2 304` et `8 × 24 × 3 = 576`, sans filtrage.
- **Professeur contrefactuel.** Magasins SQLite/J0 temporaires distincts, `mj_copyData`
  ou recréation bit-identique vérifiée, flux nommés et copiés séparément, replay
  bit-identique, et comptes principaux `24/24/24/24` avec « aucune branche dans
  l'histoire ». La fuite que j'avais identifiée en B4 de LIFE-009 — branches remontant
  dans les `ExperimentSignals` LIFE-002, donc dans les features de la politique — est
  fermée.
- **Features de politique.** Liste positive fermée; régime, paramètres cachés, banque
  privée, progrès professeur, futur, politique concurrente et métriques test nommément
  interdits. Le coût commandé constant `560/560 = 1` est une colonne de variance nulle
  traitée par l'échelle `1.0` déjà prévue. La politique et `greedy_public_residual`
  reçoivent le **même** signal public par motif, ce qui rend la comparaison honnête au
  sens de la règle 2 du brief.
- **P0.** Séquence en huit étapes, ajustement unique, reproduction bit-identique, digest
  gelé, validation ouverte ensuite seulement, Spearman `≥0,25`, gain `≥15 %` sur la
  constante, **et même signe de corrélation dans les trois régimes**. La stratification
  par régime est un ajout pertinent. Test ouvert seulement si tout passe.
- **Règle d'acceptation.** Le modèle courant et le candidat sont comparés sur **le même**
  ensemble impair cumulé, ce qui rend la comparaison équitable; le candidat est réajusté
  sur toutes les données paires à chaque cycle, donc la règle n'est pas un cliquet qui
  gèlerait le modèle après un refus. Le traitement du premier essai est défini sans
  ambiguïté. Sous réserve de B3 quant à la portée réelle de la protection.
- **Arrêts, intégrité et clôture.** Liste exhaustive, aucune analyse partielle, aucune
  seconde campagne, aucun retuning, nouvel identifiant exigé pour toute reprise. Conforme
  au modèle qui a rendu D-020, D-027 et D-037 mécaniques.
- **Portée de la promotion.** « Sélecteur gelé optionnel en simulation », déclaratif par
  défaut, revue Claude des résultats obligatoire, et une liste de non-revendications
  explicite. **Correctement étroit**; je n'y trouve aucune sur-revendication, sous réserve
  des deux limites à ajouter en B6.

## Remarques non bloquantes

- **R1 — puissance de la stratification P0 sur validation.** Le contrôle « même signe de
  corrélation dans chacun des trois régimes » repose sur `2`, `3` et `3` organismes. Au
  niveau organisme, c'est très peu, même si chaque sous-groupe compte `144` à `216`
  exemples. À conserver comme garde de cohérence, sans lui prêter la valeur d'un test.
- **R2 — `greedy_public_residual` au démarrage.** Avec « absence traitée comme priorité
  maximale » et départage ASCII, les trois premiers cycles sont forcément
  `probe_micro`, `probe_reversal`, `probe_step_hold`. Le comportement est bien défini;
  autant l'écrire, car il rend les trois premiers cycles de cette baseline identiques à
  un tourniquet.
- **R3 — rapporter l'allocation par moitié et par régime.** P3 exige déjà « au moins deux
  expériences dans chaque moitié ». Exporter la matrice complète allocation × régime
  éclairerait directement si la politique apprise a découvert la correspondance
  régime→plan, qui est le mécanisme par lequel elle est censée gagner.
- **R4 — nommer l'asymétrie de l'oracle.** L'oracle lit les trois progrès privés réels;
  aucune politique causale ne le peut. L'écart appris/oracle mesure la difficulté
  d'inférence, non une insuffisance de la politique, et le rapport final doit le dire.
- **R5 — déplacement réalisé.** Il est déclaré descriptif, ce qui est correct puisque le
  coût commandé est la grandeur égalisée. Le rapporter par plan et par régime aidera
  néanmoins à interpréter un éventuel échec, les trois plans n'ayant pas le même
  déplacement réel malgré un coût commandé identique.

## Synthèse

LIFE-010 fait ce qu'une reconception doit faire: il attaque les causes établies de
l'échec précédent au lieu d'en ajuster les seuils. L'égalisation exacte du coût commandé
à `560°`, le prior physique dont le modèle part exactement, la banque privée alignée sur
l'espace d'action et la porte de progrès `≥20 %` corrigent respectivement les quatre
défauts que le smoke LIFE-009 avait révélés. Les gardes d'intégrité qui avaient
fonctionné sont conservées sans dilution, et la porte de marge oracle — le dispositif qui
a évité une campagne inutile — est reconduite et durcie.

Le risque résiduel n'est plus qu'une porte soit impossible, mais qu'une promotion soit
**trop facile**: la taille d'effet est adossée à `greedy_public_residual`, dont la
pathologie de verrouillage est prévisible, tandis que la baseline réellement exigeante,
`round_robin`, n'est protégée par aucun plancher. B1 corrige cela au moyen d'une décision
prise sur données non réservées, avant toute banque, exactement comme B2 de LIFE-009 —
qui vient de prouver son utilité.

**Autorisation.** Une fois les corrections **B1 à B7** intégrées au pré-enregistrement
comme amendements pré-calcul datés et additifs, **l'implémentation peut commencer, puis le
smoke `18191..18196` peut être exécuté**. Les banques `18201..18248` et `18301..18324`
restent interdites jusqu'à: intégration de toutes les corrections bloquantes; smoke
entièrement vert sur ses sept portes; décision d'ancrage de B1 écrite au manifeste avec le
digest du protocole; comptes d'acceptation/refus de B3 rapportés; et projection mesurée
sur l'assiette complète de B4 sous les `90` minutes. Toute promotion reste interdite avant
une revue contradictoire des résultats.
