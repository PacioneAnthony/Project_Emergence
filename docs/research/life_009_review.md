# Revue contradictoire pré-calcul LIFE-009 — curriculum appris

Date: 2026-07-27. Revue demandée avant implémentation, smoke `17991`, banques
`17901..17940` et test `18001..18024`. Fichiers audités intégralement:
`docs/research/life_009_preregistration.md`, `docs/research/life_008_spec.md`,
`docs/research/life_006_spec.md`, `docs/research/life_007_spec.md`,
`docs/research/kernel_001_implementation.md`, `DEVELOPMENTAL_ARCHITECTURE.md`,
`DECISIONS.md` (D-027 à D-035), `PILOTAGE.md`, `SESSION_HANDOFF.md`; en complément
`docs/research/life_002_spec.md`, `learning/paired_stats.py`, `cognitive/competence.py`,
`cognitive/observed_signals.py` et `cognitive/experiments.py` pour juger
l'implémentabilité.

Aucun test expérimental, génération de données, entraînement, smoke ni calcul n'a été
lancé. Aucune campagne REF n'a été rouverte. Les seuls calculs effectués sont une
**arithmétique sur les constantes du pré-enregistrement** (amplitudes commandées par les
trois primitives, coûts moteurs, part d'erreur initiale par amplitude) et une lecture de
la limite d'énumération de `learning/paired_stats.py`. Aucun fichier autre que la
présente revue n'a été modifié.

## Verdict

**AUTORISER AVEC CORRECTIONS BLOQUANTES.**

LIFE-009 est le premier document de ce programme à viser une capacité **apprise** plutôt
qu'une plomberie déterministe, et il le fait avec la bonne discipline: la porte n'est pas
un changement de statut mais une réduction d'erreur sur une banque tenue à part, les
features de politique sont énumérées et restrictives, le professeur contrefactuel est
déclaré comme information privilégiée, les baselines sont fixées avant calcul et
l'oracle est explicitement hors porte. Les limites déclarées en fin de document sont
honnêtes et complètes.

Mais l'audit établit un problème structurel que le dossier ne mentionne pas: **l'espace
d'action et l'espace d'évaluation ne coïncident pas, et les gardes anti-raccourci
enferment la politique apprise dans un voisinage de la baseline principale.** Pris
ensemble, ces deux faits rendent la porte primaire P1 possiblement inatteignable *par
construction*, indépendamment de la qualité d'une politique apprise. Ce serait un
troisième non-résultat inattribuable après REF-002 et REF-003, et cette fois il serait
prévisible avant calcul.

Sept corrections bloquantes suivent, chacune avec son texte normatif. Aucune n'exige de
calcul, et aucune ne dépend d'une donnée réservée.

## 1. LIFE-009 fait-il avancer l'objectif final ?

Oui, et c'est la première tranche dont on peut le dire.

D-022, D-028, D-029, D-032 et D-034 ont produit une infrastructure réelle mais
entièrement déclarative: LIFE-006 route des besoins selon des priorités écrites par
l'ingénieur, LIFE-008 qualifie l'endurance d'une boucle déterministe. Aucune de ces
tranches ne pouvait échouer scientifiquement. LIFE-009 introduit la première quantité
qui peut réellement infirmer quelque chose: la MAE d'un modèle appris sur 48 transitions
tenues à part, mesurée aux instants `0..24`.

Le faux succès le plus évident — « le statut de compétence change donc l'organisme a
appris » — est correctement fermé: la métrique primaire ne consulte aucun statut, la
banque privée n'entre jamais dans les données d'ajustement, et P0 exige une erreur
initiale strictement positive. Le second faux succès — « la politique choisit l'épreuve
la plus facile » — est visé par P3. Le troisième — « le professeur donne à l'inférence
une information indisponible » — est visé par la liste blanche de features.

Les trois sont visés. Les paragraphes suivants montrent que le premier et le troisième
sont effectivement fermés, et que le deuxième l'est trop bien: la garde anti-raccourci
supprime aussi la marge de manœuvre qui permettrait à la politique de gagner.

## Corrections bloquantes

### B1 — le domaine d'évaluation contient des amplitudes que l'espace d'action ne peut jamais atteindre

Les trois primitives sont des cycles fermés autour de `90°`. Leur développement donne,
pas à pas:

| Primitive | Cibles | `|amplitude|` commandée | Coût moteur |
|---|---|---:|---:|
| `probe_fine` | `(75, 90, 105, 90)` ×3 | **`15°` uniquement** | `180°` |
| `probe_medium` | `(50, 90, 130, 90)` ×3 | **`40°` uniquement** | `480°` |
| `probe_wide` | `(20, 90, 160, 90)` ×3 | **`70°` uniquement** | `840°` |

Chaque primitive ne visite donc **qu'une seule amplitude**, et l'union des trois couvre
`{15, 40, 70}`. Or la base de la compétence porte des charnières aux amplitudes
`0, 15, 40, 70, 110, 160`, et la banque privée « couvre les deux directions et les six
amplitudes charnières ». **Les amplitudes `110` et `160` ne peuvent être produites par
aucune expérience du catalogue, sous aucune politique.**

Trois conséquences, toutes défavorables au protocole:

1. **Dilution de la métrique primaire.** Le prior prédit l'angle courant, donc l'erreur
   initiale d'une transition vaut son déplacement. Sous l'hypothèse d'un servo qui
   rejoint sa cible, la part de masse d'erreur initiale située aux amplitudes
   inatteignables vaut `(110+160) / (0+15+40+70+110+160) ≈ 68 %`. L'aire normalisée,
   métrique primaire, est donc majoritairement composée d'un terme qu'**aucune politique
   ne peut réduire par son choix**. Une amélioration relative de `5 %` sur le total exige
   alors une amélioration bien supérieure sur la partie contrôlable, dans une proportion
   inconnue avant calcul.
2. **La garde « pire amplitude » de P3 devient inerte.** La pire MAE finale parmi les six
   amplitudes sera presque certainement à `160` pour **toutes** les politiques, et sa
   valeur est déterminée par l'extrapolation des charnières, pas par le curriculum. La
   garde ne peut donc pas détecter ce qu'elle vise — « la politique a sacrifié une région
   du domaine » — sur les seules régions où un sacrifice serait possible.
3. **Elle peut même s'inverser.** Les charnières étant cumulatives, la prédiction à
   `110` et `160` dépend des coefficients ajustés sur `≤70°`. Si la dynamique sature au
   delà de `70°`, une politique qui accumule beaucoup de données à `70°` extrapolera une
   pente linéaire et **dégradera** sa MAE aux grandes amplitudes. La garde pénaliserait
   alors la politique la mieux informée.

#### Texte normatif intégrable

> **Domaine d'évaluation restreint à l'espace d'action.** La banque privée est scindée en
> deux sous-ensembles gelés avant tout calcul: le sous-ensemble **atteignable**, limité
> aux amplitudes effectivement productibles par au moins une primitive du catalogue, et
> le sous-ensemble **hors domaine**. Toutes les portes de promotion — aire normalisée de
> P1 et P2, MAE finale et pire amplitude de P3 — sont calculées **exclusivement sur le
> sous-ensemble atteignable**. Les métriques sur le sous-ensemble hors domaine sont
> calculées, exportées et rapportées à titre **descriptif**, comme mesure
> d'extrapolation, et ne peuvent franchir ni faire échouer aucune porte.
>
> Si Codex préfère conserver une porte sur l'ensemble des six amplitudes, il doit alors
> ajouter au catalogue au moins une primitive sûre produisant des amplitudes commandées
> `≥110°` dans `[10°,170°]`, soumise aux mêmes gardes, au même nombre de pas et au même
> traitement d'équité que les trois existantes. Aucune autre option n'est autorisée:
> évaluer une compétence sur un régime que l'organisme ne peut pas explorer n'est pas un
> test de curriculum.

### B2 — aucune marge de progrès n'est démontrée, et les gardes la referment

C'est la correction la plus importante.

**La baseline principale est presque une allocation uniforme.** `greedy_uncertainty`
choisit « la candidate sûre dont l'incertitude ridge moyenne sur ses amplitudes est
maximale ». Comme chaque primitive couvre exactement une amplitude et que l'incertitude
ridge d'une amplitude décroît de façon monotone avec son nombre d'observations,
`greedy_uncertainty` sélectionne mécaniquement l'amplitude la moins visitée. **Elle
dégénère donc en tourniquet**, c'est-à-dire en la baseline secondaire `round_robin`.

Cela a deux effets. D'abord, le test `round_robin` de P2 n'apporte presque aucune
information indépendante de P1: les deux trajectoires seront quasi identiques, et la
correction de Holm sur trois tests dont l'un duplique la porte primaire n'est pas la
preuve de robustesse qu'elle paraît être. Ensuite et surtout, la question devient: **une
allocation non uniforme peut-elle battre une allocation uniforme de plus de `5 %` sur
cette tâche ?** La banque privée pondère les amplitudes atteignables également; à
pondération égale et à modèle linéaire par charnières, l'allocation uniforme est proche
de l'optimum. La marge disponible est donc structurellement faible, et le
pré-enregistrement n'en fournit aucune estimation.

**La garde moteur de P3 referme le peu qui reste.** Les coûts par cycle sont `180`, `480`
et `840` degrés; l'allocation uniforme coûte `500` degrés/cycle et le plafond P3 de
`1,10×` vaut `550`. Une politique concentrée sur `probe_wide` coûterait `840`, soit
`1,68×`: **interdite**. La politique apprise est donc confinée aux allocations dont le
coût moyen reste à `±10 %` de l'uniforme — et comme le coût est une fonction strictement
croissante de l'amplitude et que chaque amplitude correspond à une primitive unique,
contraindre le coût revient à **contraindre l'allocation elle-même** au voisinage de
l'uniforme.

En résumé: la baseline est l'uniforme, la politique apprise est enfermée près de
l'uniforme, et la porte exige `≥5 %` d'écart. Il est très possible que P1 soit
**inatteignable par construction**. Un échec ne dirait alors rien sur les curriculums
appris — exactement le type de non-résultat inattribuable qui a consommé REF-002 puis
REF-003.

Le pré-enregistrement dispose pourtant déjà de l'instrument qui répond à la question:
l'oracle contrefactuel. Il est correctement tenu hors des portes, mais il est
*facultatif* (« peut être rapporté ») et n'est jamais lu avant les portes.

#### Texte normatif intégrable

> **Démonstration de marge avant ouverture des banques réservées.** Le smoke `17991`,
> exécuté sur des organismes **non réservés**, mesure et consigne, avant toute ouverture
> de `17901..17940` et `18001..18024`:
>
> 1. la courbe de MAE atteignable sous allocation uniforme aux instants `0..24`,
>    établissant que la compétence **ne sature pas** avant le cycle `24` — soit une
>    réduction de MAE atteignable strictement positive entre les cycles `12` et `24`;
> 2. l'aire normalisée de l'**oracle** contrefactuel, qui lit les trois progrès réels et
>    choisit le meilleur, et son amélioration relative face à `greedy_uncertainty`.
>
> Ces deux mesures sont écrites dans le manifeste du smoke avec le digest du protocole.
> **Si l'amélioration relative de l'oracle face à `greedy_uncertainty` est inférieure à
> `10 %`** — soit deux fois la marge exigée de P1 — la campagne n'est pas ouverte et
> LIFE-009 est clos comme **non-résultat de conception**, attribué à l'absence de marge
> de la tâche et non à la politique apprise. Aucun ajustement du seuil de P1, du plafond
> moteur de P3 ou du catalogue de primitives n'est permis à ce stade sans nouvelle revue
> contradictoire pré-calcul.
>
> L'oracle est également rapporté sur la banque test comme plafond descriptif, et le
> rapport final lit systématiquement l'écart appris/`greedy_uncertainty` relativement à
> l'écart oracle/`greedy_uncertainty`.
>
> **Redondance déclarée.** Le pré-enregistrement acte que `greedy_uncertainty` et
> `round_robin` sont attendues quasi identiques sur ce catalogue, et que le test
> `round_robin` de P2 n'est donc pas une confirmation indépendante de P1.

### B3 — le test de permutation exact est impossible à `n=24` avec le module gelé

P1 exige un « test exact de permutation des signes unilatéral `p<=0.05` » et P2 « trois
tests de permutation unilatéraux » corrigés par Holm, sur **24** graines appariées.

Or `learning/paired_stats.py`, que la règle 3 du brief impose de réutiliser, fixe
`_MAX_EXACT_N = 20` et **lève `ValueError`** au-delà:
`exact enumeration limited to n <= 20`. À `n=24`, `exact_sign_flip_pvalue` ne s'exécute
pas. Le protocole n'est donc pas implémentable tel qu'écrit, et la seule alternative
offerte par le module — `monte_carlo_sign_flip_pvalue` — n'est ni nommée, ni
paramétrée, ni ensemencée.

#### Texte normatif intégrable

> **Test de permutation à `n=24`.** Les tests de P1 et P2 utilisent
> `learning.paired_stats.monte_carlo_sign_flip_pvalue`, alternative `"greater"`, avec
> `n_resamples = 200 000` et graine `2026072702`, passée explicitement. L'estimateur
> add-one du module est conservé sans modification; la p minimale atteignable vaut
> `1/200 001 ≈ 5,0e-06`, très en dessous du seuil corrigé par Holm sur trois membres.
> La correction de Holm de P2 utilise `learning.paired_stats.holm_correction`. Aucun
> second module statistique n'est écrit. Le nombre de rééchantillonnages et la graine
> sont gelés ici et ne peuvent être modifiés après lecture d'une quelconque métrique.
> P1 est délibérément tenue hors de la famille Holm de P2: la promotion étant
> conjonctive, cette séparation est conservatrice et doit être écrite comme telle.

### B4 — l'isolation des branches contrefactuelles n'est pas spécifiée, et c'est un chemin de fuite

La construction du professeur exécute, à chaque état pré-décision, **trois branches**
dont une seule est suivie. Le pré-enregistrement dit que les branches copient « l'état
MuJoCo public et caché; le modèle de compétence et ses données; les états RNG; la mémoire
cognitive pertinente », et que « les branches non suivies ne rejoignent jamais l'histoire
principale ». Trois lacunes.

**Exactitude de la copie.** « État MuJoCo » n'est pas une liste. Une continuation
bit-exacte exige `qpos`, `qvel`, `act`, `time`, **et** `qacc_warmstart`, que MuJoCo
utilise comme point de départ du solveur: l'omettre rend les branches non reproductibles
et rompt P4. La méthode doit être nommée (`mj_copyData` ou équivalent énuméré).

**Énumération des flux RNG.** « Les états RNG » au pluriel, sans liste. Au minimum:
bruit capteur de `BenchSensorConfig`, bruit de primitive indexé par
`(organisme, cycle, primitive)`, RNG d'ordre de la banque privée, RNG de
`uniform_random`. Un flux oublié fait diverger la branche suivie de la trajectoire
principale.

**Contamination de l'histoire.** C'est le point sérieux. Une branche exécute une
primitive complète via le contrat LIFE-004. Si cette exécution ouvre une session J0 et
persiste une `experiment_execution` dans le SQLite de l'organisme, alors LIFE-003
l'attribue et `recompute_observed_history` la réintègre — de sorte que les six
`ExperimentSignals` LIFE-002, **qui sont des features de la politique**, seraient
calculés sur un historique contenant deux branches jamais vécues. C'est une fuite
directe du professeur vers les features d'inférence, et elle contredirait la liste
blanche sans qu'aucune garde énumérée ne la détecte.

#### Texte normatif intégrable

> **Isolation des branches contrefactuelles.** Chaque branche s'exécute contre un magasin
> cognitif et un magasin J0 **temporaires et distincts**, créés pour la branche et détruits
> après calcul de son label. Aucune écriture de branche n'atteint le SQLite ni les
> journaux J0 de l'organisme. Après le choix du carré latin, l'état principal est celui
> de la branche suivie, rejoué dans le magasin principal, et le smoke asserte que le
> nombre de propositions, d'exécutions et de sessions J0 de l'organisme après `24` cycles
> vaut exactement `24`, `24` et `24`.
>
> **Copie d'état.** La copie contrefactuelle est effectuée par `mj_copyData` sur `mjData`
> complet — incluant `qpos`, `qvel`, `act`, `time` et `qacc_warmstart` — plus la copie du
> modèle de compétence, de ses données d'ajustement, de ses paramètres de standardisation,
> et de l'état de chacun des flux aléatoires suivants, énumérés exhaustivement: bruit
> capteur, bruit de primitive indexé par `(organisme, cycle, primitive)`, ordre de la
> banque privée, et flux réservé de `uniform_random`. Le smoke asserte qu'une branche
> exécutée puis rejouée depuis la copie produit des observations **bit-identiques**.

### B5 — la projection temporelle omet le coût dominant

Le plafond est de `60` minutes et « le smoke exécute un organisme complet sous les cinq
politiques et mesure une projection conservatrice ». Cette mesure ne couvre que le
**côté test**. Or le dénombrement des exécutions de primitive de la campagne est:

| Phase | Exécutions de primitive |
|---|---:|
| Professeur développement, `32 × 24 × 3` | `2 304` |
| Professeur validation, `8 × 24 × 3` | `576` |
| Test, `24 graines × 5 politiques × 24 cycles` | `2 880` |
| **Total** | **`5 760`** |

La construction du professeur représente donc **la moitié du coût total** et n'entre pas
dans l'assiette mesurée par le smoke. S'y ajoutent la génération des banques privées
(`64` organismes × `48` transitions) et environ `5 900` évaluations de banque de `48`
transitions chacune. Un smoke à `120` exécutions projeté sur `5 760` extrapole d'un
facteur `48` à partir de la mauvaise population.

C'est exactement le défaut que la correction C8 de REF-002 avait fermé, et l'échec de
dimensionnement de D-012 sous une autre forme.

#### Texte normatif intégrable

> **Assiette de la projection temporelle.** Le smoke `17991` chronomètre et exporte
> séparément cinq phases: (1) génération de la banque privée d'un organisme;
> (2) construction professeur d'un organisme complet, soit `24` cycles × `3` branches
> contrefactuelles, copies d'état et labels inclus; (3) déroulé test d'un organisme sous
> les cinq politiques; (4) les `25` évaluations de banque de la courbe `0..24`;
> (5) analyse, portes et digests. La projection est
>
> ```text
> 40 × (temps_banque_privée + temps_professeur_organisme)
>  + 24 × (temps_banque_privée + temps_test_organisme + temps_courbe_organisme)
>  + temps_analyse
> ```
>
> Si elle dépasse `60` minutes, arrêt technique avant ouverture des banques, sans
> amendement de plafond et sans nouvelle revue: le pré-enregistrement l'interdit déjà et
> cette interdiction est maintenue.

### B6 — quantités non spécifiées qui deviendraient des décisions scientifiques à l'implémentation

Quatre définitions manquent, et chacune modifie un résultat.

1. **Features aux amplitudes jamais visitées.** Le vecteur candidat contient « compte,
   moyenne des résidus d'ajustement et incertitude ridge pour chacune des six
   amplitudes ». Aux amplitudes `110` et `160`, le compte vaut toujours `0` et la moyenne
   des résidus est **indéfinie**. La valeur choisie — `0`, `NaN`, sentinelle — est une
   décision non écrite qui entre dans la standardisation.
2. **« Avant tout filtrage ».** Le texte annonce `2 304` exemples « avant tout filtrage »
   puis interdit seulement la suppression *selon le label*. Les filtres autorisés ne sont
   pas énumérés, ce qui laisse un degré de liberté post hoc.
3. **Coût moteur.** « Coût moteur cumulé en degrés » ne dit pas si l'on somme les
   amplitudes **commandées** ou le déplacement **réalisé**. P3 étant une porte, l'écart
   entre les deux est décisionnel.
4. **Ordre lexicographique.** Les départages « lexicographiques » supposent un ordre sur
   les identifiants; il faut écrire lequel et sur quelle chaîne exacte.

#### Texte normatif intégrable

> **Définitions gelées.** (i) Pour une amplitude sans observation, le compte vaut `0`, la
> moyenne des résidus vaut `0,0` et l'incertitude ridge vaut sa valeur a priori; ces
> conventions sont appliquées avant standardisation et le smoke asserte qu'aucun `NaN`
> n'atteint le régresseur. (ii) Le seul filtre autorisé sur les exemples professeur est
> l'exclusion d'un organisme entier déclaré inadmissible par le smoke; tout autre filtre
> est interdit, et le compte `2 304 / 576` est une porte exacte de P0. (iii) Le coût
> moteur est la somme des `|cible − angle courant|` **commandées** sur les `12` pas, en
> degrés, indépendante de la dynamique réalisée; le déplacement réalisé est exporté à
> titre descriptif. (iv) Les départages utilisent l'ordre lexicographique ASCII croissant
> sur l'identifiant d'expérience, qui donne `probe_fine < probe_medium < probe_wide`.

### B7 — les sous-portes de validation de P0 doivent être franchies avant d'ouvrir la banque test

P0 mêle des vérifications d'intégrité, des sous-portes mesurées sur la banque
**validation** (Spearman `≥0,20`, MAE `10 %` sous la constante) et une vérification de
reproductibilité. Le pré-enregistrement gèle bien les poids avant d'ouvrir le test, mais
ne dit pas ce qui se passe si les sous-portes de validation échouent. En l'état, rien
n'interdit d'ouvrir `18001..18024` puis de constater P0 rouge — ce qui consommerait la
banque test et créerait la tentation d'un second ajustement.

#### Texte normatif intégrable

> **Ordonnancement de P0.** Les sous-portes de validation de P0 — corrélation de rang
> `≥0,20` et MAE de prédiction au moins `10 %` sous la constante développement — sont
> évaluées **immédiatement après le gel des poids et avant toute ouverture de
> `18001..18024`**. Leur échec est un arrêt technique: la banque test n'est pas ouverte,
> aucune métrique test n'existe, LIFE-009 est clos comme non-résultat et aucun
> réajustement, changement d'hyperparamètre ou nouvelle lecture de la validation n'est
> autorisé. Le manifeste consigne les deux valeurs mesurées et le digest des poids gelés.

## Points audités et jugés conformes

- **Étanchéité de la banque privée.** Jamais dans les données d'ajustement, jamais dans
  les features, jamais dans l'historique LIFE-002/003, entrée à un pas sans rollout
  autorégressif: la définition est nette et referme la voie de fuite la plus évidente.
- **Légitimité du professeur contrefactuel.** L'usage d'une information privilégiée pour
  produire des cibles, alors que l'élève ne voit qu'un vecteur restreint, est une
  distillation classique et parfaitement licite. Le pré-enregistrement le déclare en
  limite explicite, ce qui est la bonne pratique; P0 vérifie que les features suffisent
  réellement à porter le signal.
- **Liste blanche des features.** Paramètres cachés, MAE privée courante, labels futurs,
  métriques test et statut d'une autre politique sont nommément interdits. La liste
  positive est fermée et vérifiable. Sous réserve de B4 et B6-i.
- **Couplage des flux aléatoires.** Indexer le bruit par `(organisme, cycle, primitive)`
  est la bonne réponse au problème de trajectoires divergentes: une même candidate au
  même cycle reçoit le même bruit quelle que soit la politique, sans imposer aux
  politiques de suivre le même chemin.
- **Gel des poids et de la standardisation avant le test**, absence de réentraînement
  pendant les `24` cycles test, exigence de poids bit-identiques après réajustement:
  conforme.
- **Immutabilité du catalogue.** La politique ne peut ni créer une primitive, ni modifier
  une cible, un quota ou un arrêt d'urgence; les gardes fraîches du catalogue restent
  postérieures à l'activation. La séparation LIFE-006 « routes déclaratives » /
  LIFE-009 « choix appris parmi les candidates activées » est nette, et le sélecteur
  appris reste optionnel après promotion, le déclaratif restant le défaut.
- **P4 et reproductibilité analytique** sans réexécution J0: conforme, et cohérent avec
  la discipline de digest déjà éprouvée par LIFE-008.
- **Règles d'arrêt et interdiction d'analyse partielle**: la liste est exhaustive et la
  clause « une nouvelle tentative exige un nouvel identifiant, de nouvelles banques et un
  nouveau pré-enregistrement » reprend le modèle qui a rendu D-015, D-020 et D-027
  mécaniques.
- **Portée de la promotion.** « Intégration de la politique gelée comme sélecteur
  optionnel en simulation KERNEL/LIFE », le déclaratif restant le défaut jusqu'à une
  qualification d'endurance distincte: c'est **correctement étroit**. Rien dans la
  décision ne revendique curiosité générale, découverte de besoins ou causalité, et les
  limites déclarées en fin de document sont les bonnes. Sur ce point précis — « ce qu'un
  succès autoriserait exactement » — je ne trouve aucune sur-revendication.

## Remarques non bloquantes

- **R1 — P2 n'a pas de plancher d'effet.** P1 exige `≥5 %`, P2 seulement « strictement
  meilleure en moyenne » plus `p≤0,05` après Holm. Une amélioration de `0,01 %`
  significative franchirait P2. La promotion étant conjonctive et P1 portant la taille
  d'effet, ce n'est pas dangereux, mais l'asymétrie mérite une phrase.
- **R2 — la sous-porte `16/24` double presque le test de permutation.** Sous l'hypothèse
  nulle, `P(X ≥ 16)` avec `X ~ Bin(24; 0,5)` vaut environ `0,032`. La conjonction
  « `16/24` favorables **et** `p ≤ 0,05` » n'ajoute donc que peu de contrainte au-delà du
  test lui-même. À conserver — elle protège contre un effet porté par peu de graines —
  mais sans la présenter comme une seconde exigence indépendante.
- **R3 — deux features seront constantes.** Les incertitudes ridge aux amplitudes `110`
  et `160` ne varient jamais, faute de données. Après standardisation, une colonne de
  variance nulle doit être traitée explicitement (retrait ou écart-type plancher), sinon
  la standardisation divise par zéro.
- **R4 — exporter l'allocation par politique.** Au-delà de la « fréquence des
  primitives » déjà prévue, rapporter l'allocation par moitié de campagne et par graine
  éclaire directement si la politique apprise a trouvé une structure temporelle
  (explorer large puis affiner, par exemple) ou si elle oscille près de l'uniforme.
- **R5 — compte de tests périmé.** LIFE-008 rapporte `278` tests verts et le dépôt est
  passé à `247` puis au-delà selon les tranches; la séquence LIFE-009 doit exiger l'état
  courant plus ses tests propres, pas un nombre figé.
- **R6 — nommer l'asymétrie de l'oracle.** L'oracle lit les trois progrès réels; il n'est
  pas atteignable par une politique causale. Le rapport doit dire que l'écart
  appris/oracle mesure la difficulté d'inférence, pas une insuffisance de la politique.

## Synthèse

LIFE-009 est bien conçu sur tout ce qui concerne l'**intégrité**: étanchéité des banques,
liste blanche de features, gel des poids, couplage des bruits, reproductibilité, arrêts,
et une portée de promotion honnêtement étroite. C'est la première tranche de ce programme
qui peut réellement échouer, et c'est un progrès.

Sa faiblesse est ailleurs, et elle est structurelle: la tâche telle que paramétrée
pourrait ne pas contenir la marge que la porte primaire exige. Trois primitives couvrant
chacune une amplitude unique font dégénérer la baseline principale en allocation
uniforme; le plafond moteur de P3 enferme la politique apprise dans le voisinage de cette
même allocation; et `68 %` de la masse d'erreur évaluée se trouve à des amplitudes
qu'aucune action ne peut atteindre. Un échec de P1 dans ces conditions ne serait pas
attribuable à l'hypothèse.

Les corrections B1 et B2 suffisent à rendre l'échec attribuable, et B2 le fait au coût
d'un smoke sur organismes non réservés — c'est-à-dire pour presque rien, et **avant** de
dépenser la campagne. Après REF-002 et REF-003, deux non-résultats techniques
consécutifs, c'est le moment d'acheter cette garantie.

**Autorisation.** Une fois les corrections **B1 à B7** intégrées au pré-enregistrement
comme amendements pré-calcul datés et additifs, **l'implémentation peut commencer, puis
le smoke `17991` peut être exécuté**. Les banques `17901..17940` et `18001..18024`
restent interdites jusqu'à: intégration de toutes les corrections bloquantes; smoke
entièrement vert; démonstration de marge de B2 consignée au manifeste avec le digest du
protocole; et projection temporelle de B5 concordante sous les `60` minutes. Toute
promotion reste interdite avant une revue contradictoire des résultats.
