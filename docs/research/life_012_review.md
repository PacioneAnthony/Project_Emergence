# Revue contradictoire pré-calcul LIFE-012 — plateaux d'établissement réalisés

Date: 2026-07-27. Revue demandée avant implémentation et avant toute graine `18791+`.
Fichiers audités intégralement: `docs/research/life_012_preregistration.md`,
`docs/research/life_011_review.md`, `docs/research/life_011_technical_stop.md`,
`docs/research/life_011_preregistration.md` (amendée B1–B6),
`docs/research/life_010_technical_stop.md`,
`docs/research/kernel_001_implementation.md`, `DEVELOPMENTAL_ARCHITECTURE.md`,
`DECISIONS.md` (D-040 à D-044), `learning/life_010.py`,
`learning/life_010_campaign.py`, `learning/life_011.py`,
`learning/life_011_campaign.py`, `cognitive/observed_signals.py`, `sim3d/bench_env.py`;
en complément `sim3d/bench_model.py` pour juger la plausibilité mécanique des plateaux.

Aucune simulation, aucun test, aucun entraînement et **aucune graine** n'ont été
ouverts: en particulier je n'ai tiré aucun paramètre d'organisme, alors que
`sample_life010_organism` le permettrait, parce que `18791..18796` sont interdites avant
intégration des corrections. Les seuls calculs sont l'arithmétique littérale autorisée:
coût, changements, reconstruction de la rampe `_limited_deg` aux cadences `4,8`, `7,5`,
`12,0` et `14,4°/pas`, comptage des pas mobiles, maintiens, renversements et déplacements
réalisés, et deux calculs de proportion sur les familles déclarées. Aucun fichier autre
que la présente revue n'a été modifié.

## Verdict

**AUTORISER AVEC CORRECTIONS BLOQUANTES.**

LIFE-012 est un essai légitime. Aucun seuil n'est relâché — ni le minimum `5 %`, ni la
médiane `15 %`, ni la porte de progrès `20 %`, ni les familles statistiques —,
l'organisme `18496` n'est ni rejoué, ni filtré, ni remplacé, les graines sont neuves, et
le changement proposé est **mécaniste** et non métrique: donner à l'établissement des
pas d'observation réels au lieu d'espérer qu'il transparaisse d'une rampe saturée. C'est
la seule forme de suite admissible après D-043, et le dossier la respecte.

L'arithmétique des plans v4 est par ailleurs **exacte au nominal**: `240°` commandés,
`32` pas, retour à `90°`, cibles dans `[30°,150°]`, et les triplets annoncés
`20/24/32` pas mobiles, `2/4/8` renversements et `6/4/0` maintiens hors neutre se
vérifient au pas près. Le mécanisme visé est plausible: à `12°/pas`, `probe_step_settle_v4`
offre quatre fenêtres de trois pas, soit `60 ms`, à comparer à un temps d'établissement de
l'ordre de `40` à `80 ms` pour la famille `settling_dominant`. La cible est bien atteinte
et le plateau est réel.

Mais le plateau — changement scientifique **unique** de cette tranche — n'existe que
au-dessus d'une cadence critique de `7,5°/pas`, c'est-à-dire `375°/s`. En dessous, les
trois plans v4 redeviennent trois rampes saturées identiques: `32` pas mobiles, `0`
maintien, `153,6°` réalisés, ne différant plus que par le nombre de renversements. Or la
famille `speed_dominant` tire `U[240,720]°/s`: **`28,125 %` de ses organismes tombent sous
cette cadence**, soit `48,3 %` de chance qu'au moins un des deux organismes `speed` du
smoke soit dégénéré, et `92,9 %` de chance qu'au moins un des huit organismes `speed` du
test le soit. Dans ce cas, la classe de diagnostic « inerte » est **vide**, et le code
hérité de LIFE-011 lève une exception au lieu de rendre une porte rouge. Cinq corrections
bloquantes en découlent.

## 1. Arithmétique des plans v4

Reconstruction de `_limited_deg` selon `sim3d/bench_env.py`
(`delta = clamp(target − _limited_deg, ±max_delta)`), depuis un reset à `90°`:

| cadence | plan | pas mobiles | maintiens hors neutre | maintiens au neutre | déplacement réalisé | renversements |
|---|---|---:|---:|---:|---:|---:|
| `12,0` | `step_settle_v4` | **20** | **6** | 6 | `240,0°` | **2** |
| `12,0` | `reversal_v4` | **24** | **4** | 4 | `240,0°` | **4** |
| `12,0` | `micro_v4` | **32** | **0** | 0 | `240,0°` | **8** |
| `14,4` | `step_settle_v4` | 20 | 6 | 6 | `240,0°` | 2 |
| `14,4` | `reversal_v4` | 24 | 4 | 4 | `240,0°` | 4 |
| `14,4` | `micro_v4` | 32 | 0 | 0 | `240,0°` | 8 |
| `7,5` | les trois | 32 | 0 | 0 | `240,0°` | 2 / 4 / 8 |
| `4,8` | les trois | 32 | 0 | 0 | `153,6°` | 2 / 4 / 8 |

Coûts commandés, longueurs, retours et changements: `240,0°` / `32` pas / `90°` /
`4`, `8` et `16` changements pour les trois plans, conformes au texte. `motor_cost`
structurel `240/(160 × 32) = 0,046875` exactement, comme déclaré. Aucune cible n'entre
dans la zone de marge de `10°`: `predicted_risk = 0,0` par construction, et la rampe
atteint désormais `30°` et `150°` **exactement**, sans les approcher à moins de `10°` des
bornes `[10°,170°]`.

La ligne décisive est celle à `4,8°/pas`. Elle n'est pas une hypothèse: à cette cadence,
un plan de `32` pas ne peut déplacer la rampe que de `153,6°`, alors que les trois plans
en commandent `240°`. **Le plan est sur-commandé, donc jamais achevé, donc sans plateau.**
La condition est identique pour les trois plans, parce qu'avec des segments de longueur
uniforme la cadence commandée moyenne vaut `coût / 32 = 7,5°/pas` pour chacun d'eux.

## Corrections bloquantes

### B1 — le plateau n'existe pas sous `375°/s`, alors que la porte exige chaque organisme

La condition d'existence d'un plateau est `amplitude_de_segment / longueur_de_segment <
max_speed × control_dt`. Elle vaut `60/8 = 7,5` pour `step_settle_v4`, `30/4 = 7,5` pour
`reversal_v4` et `15/2 = 7,5` pour `micro_v4`: les trois plans partagent le **même** seuil,
`7,5°/pas`, soit `375°/s`.

Conséquences, sur les familles déclarées telles quelles dans `sample_life010_organism`:

- `settling_dominant` et `friction_dominant` conservent `max_speed = 600°/s` nominal,
  donc `12,0°/pas`: les plateaux existent, et le mécanisme visé est disponible là où
  LIFE-011 a échoué. C'est le bon ciblage;
- `speed_dominant` tire `U[240,720]`, donc `[4,8 ; 14,4]°/pas`. La fraction sous `375°/s`
  vaut `135/480 = 28,125 %`. Avec deux organismes `speed` au smoke:
  `1 − (1 − 0,28125)² = 48,34 %` de chance qu'au moins un soit dégénéré. Avec huit
  organismes `speed` au test: `1 − 0,71875⁸ = 92,88 %`.

Pour un tel organisme, les trois plans sont indiscernables sur trois des quatre
indicateurs gelés et ne diffèrent plus que par le nombre de renversements — exactement la
configuration que j'ai qualifiée de non complémentaire en B1 de LIFE-011, et que le
triplet v3 évitait encore à `4,8°/pas` (`28/32/32` pas mobiles, `134,4/153,6/153,6°`
réalisés). **Sur ce point précis, v4 régresse par rapport à v3, dans le régime qui avait
obtenu la meilleure marge minimale mesurée (`13,1349 %`).**

Ce n'est pas une objection théorique: la porte 5 exige un minimum `>=5 %` **par
organisme** dans chaque régime. Un dessin dont le mécanisme différenciateur disparaît pour
`28 %` d'une famille ne peut pas garantir ce que sa propre porte exige. Et rien ne pourra
être fait après coup: filtrer, remplacer ou rejouer un organisme lent serait précisément
le contournement post hoc que D-043 interdit.

#### Texte normatif intégrable

> **Cadence critique et couverture des familles.** La porte analytique avant code calcule
> et inscrit au pré-enregistrement, pour chaque plan, la **cadence critique**
> `amplitude_de_segment / longueur_de_segment`, et la compare aux bornes de cadence de
> chaque famille d'organismes (`speed_dominant`: `4,8` à `14,4°/pas`; `settling_dominant`
> et `friction_dominant`: `12,0°/pas`). Le triplet n'est gelé qu'après application de
> l'une des deux voies suivantes, choisie et figée avant tout code:
>
> **Voie A — couverture complète.** Le coût commandé commun est abaissé à
> `<= 32 × 4,8 = 153,6°`, de sorte que les plateaux existent pour **tout** organisme
> déclaré. Le triplet suivant satisfait `32` pas, `120°` commandés, départ et retour à
> `90°`, cibles dans `[30°,150°]`, et conserve l'ordre des quatre indicateurs à `4,8`,
> `12,0` et `14,4°/pas`:
>
> ```text
> probe_step_settle_v5 : (120 ×8, 90 ×8, 60 ×8, 90 ×8)      4 changements de 30°
> probe_reversal_v5    : (75 ×4, 90 ×4, 105 ×4, 90 ×4) ×2   8 changements de 15°
> probe_micro_v5       : (82,5 ×2, 90 ×2, 97,5 ×2, 90 ×2) ×4  16 changements de 7,5°
> ```
>
> À `4,8°/pas` il donne `28/32/32` pas mobiles et `2/0/0` maintiens hors neutre; à `12,0`
> et `14,4°/pas`, `12/16/16` pas mobiles et `10/8/8` maintiens hors neutre. Le coût
> `motor_cost` structurel devient `120/(160 × 32) = 0,0234375`. Tout autre triplet de coût
> `<= 153,6°` satisfaisant les critères de complémentarité réalisée est admissible.
>
> **Voie B — dégénérescence déclarée.** Le coût `240°` est conservé, et le
> pré-enregistrement déclare avant tout calcul: la cadence critique `7,5°/pas`, le seuil
> `375°/s`, la fraction `28,125 %` de la famille `speed_dominant`, les probabilités
> `48,34 %` (smoke) et `92,88 %` (test) qu'au moins un organisme concerné apparaisse, et
> le fait qu'un tel organisme ne dispose d'aucun plateau et donc d'aucune différenciation
> autre que le nombre de renversements. Il déclare en outre qu'un échec de la porte 5
> imputable à un organisme sous `375°/s` sera attribué **au dessin des plans** et non à la
> politique, et qu'aucun filtrage, remplacement, resampling, changement de seuil ni
> restriction de la loi `U[240,720]` ne sera appliqué après observation.
>
> Le choix de voie est écrit au manifeste avec le digest du protocole et n'est jamais
> révisé après lecture d'une métrique.

### B2 — une classe de diagnostic vide fait échouer la plaque par exception, pas par porte rouge

`learning/life_011.py::private_bank_mobile_mask` construit le masque mobile à partir de
`step = organism.max_speed_deg_s × 0,02`, donc **par organisme**.
`learning/life_011_campaign.py::_margin_diagnostics` en dérive trois sous-ensembles —
`complete`, `mobile`, `inert` — et appelle pour chacun `prior_mae(...)` puis
`_relative_margin(...)`, lequel appelle `normalized_auc`.

Avec les plans v3, le sous-ensemble `inert` n'était jamais vide: `step_hold_v3` conserve
quatre pas de maintien à toutes les cadences. Avec les plans v4 et un organisme sous
`7,5°/pas`, les trois plans sont intégralement mobiles: le masque `inert` est **vide**,
`prior_mae([])` lève `ValueError("prior MAE requires transitions")`, et
`normalized_auc` refuserait de toute façon une courbe de MAE initiale nulle.

LIFE-012 déclare reprendre ces diagnostics « avec substitution mécanique des identifiants
v4 ». Le défaut se propage donc tel quel, avec les probabilités de B1. Son effet est le
pire possible du point de vue du programme: **une exception non spécifiée, au milieu de la
plaque de marge, c'est-à-dire un quatrième non-résultat technique du type D-040**, alors
que la situation sous-jacente est une information de conception parfaitement exploitable.

#### Texte normatif intégrable

> **Sémantique des classes de diagnostic vides.** Les vues de diagnostic du banc privé
> sont définies pour toute cardinalité, y compris nulle. Lorsqu'une classe est vide pour
> un organisme, le rapport inscrit `count = 0`, `prior_mae = null`,
> `final_mae = null`, `margin = null`, et **aucune exception n'est levée**; les portes
> scientifiques ne sont évaluées que sur la vue `complete`, dont la non-vacuité est déjà
> garantie par les `192` transitions du banc.
>
> En outre, la plaque de marge inscrit pour chaque organisme sa cadence
> `max_speed_deg_s × control_dt`, son statut `plateau_disponible` (`cadence > 7,5°/pas`)
> et, si le statut est faux, la mention explicite que le mécanisme d'établissement de
> LIFE-012 est indisponible pour cet organisme. Ce statut est un export obligatoire; il
> n'est ni une porte, ni un motif d'exclusion, ni un critère de sélection.

### B3 — la taxonomie « mobile / inerte » s'inverse en v4 et doit être remplacée avant d'être lue

En v2 et v3, les pas inertes étaient du **temps mort** au neutre après la fin de la
trajectoire: la correction B3 de LIFE-011 demandait de les isoler parce qu'ils diluaient
la métrique sans rien apprendre. En v4, tous les pas inertes suivent immédiatement une
arrivée: ce sont des **plateaux d'établissement**, c'est-à-dire précisément la classe
informative de la tranche. Le temps mort est nul.

Lire le rapport `inert` de LIFE-012 avec la grille de LIFE-011 conduirait donc à la
conclusion exactement inverse de la vérité. Trois précisions s'imposent, toutes gratuites:

1. **La classe doit être renommée et redéfinie** par sa position relative à l'arrivée, et
   le temps mort doit être compté séparément et asserté nul;
2. **La part de masse d'erreur** portée par les plateaux doit être exportée. La dilution
   passe de `4/96 = 4,17 %` de transitions inertes en v3 à `20/96 = 20,83 %` en v4
   (`12` pour `step_settle`, `8` pour `reversal`, `0` pour `micro`). Les résidus de
   plateau sont de petite amplitude devant les résidus de rampe saturée; la métrique
   restera dominée par les rampes. L'avantage attendu de l'établissement ne peut donc pas
   venir de la masse d'erreur du plateau lui-même: il doit transiter par les paramètres
   `position_gain` et `velocity_damping`, appris sur les plateaux puis réutilisés pour
   mieux prédire le retard pendant les rampes. C'est un mécanisme réel, mais indirect, et
   il doit être vérifié plutôt que supposé;
3. **La base de features ne sépare pas le plateau de la rampe.** L'indicateur de maintien
   gelé vaut `abs(command_delta) < 1e-9`, c'est-à-dire « cible inchangée », et non
   « rampe immobile ». Avec des segments de huit pas, il vaut `1` sur `28` des `32` pas de
   `step_settle_v4`, dont les quatre à cinq pas de rampe qui suivent chaque changement de
   cible. L'interaction `maintien × variation_précédente` ne trace donc pas la décroissance
   du plateau seule. La compétence étant délibérément identique d'un identifiant à l'autre,
   la base n'est pas à modifier — mais cette limite doit être écrite, sous peine
   d'attribuer à la politique un échec de représentation.

#### Texte normatif intégrable

> **Classes de transition et vérification du plateau.** Chaque transition du banc privé et
> de chaque essai est classée en trois catégories exclusives, dérivées de la rampe
> reconstruite: `rampe` (déplacement non nul), `plateau` (déplacement nul, à `k` pas au
> plus d'une arrivée, `k` gelé à `3`), `temps_mort` (déplacement nul au-delà). Le
> pré-enregistrement déclare la composition exacte du banc par classe et par plan, et la
> plaque de marge asserte `temps_mort = 0` pour le triplet gelé.
>
> La plaque exporte, par organisme, par plan et par classe: le nombre de transitions, la
> MAE du prior, la MAE finale de round-robin, la **part de la masse d'erreur totale**
> portée par la classe, et la marge oracle restreinte à la classe. Elle exporte en outre
> la suite des résidus des pas de plateau, afin de vérifier que la décroissance
> d'établissement est effectivement observable au pas de `20 ms` et n'est pas noyée sous
> la quantification AS5600 de `0,0879°`.
>
> Le pré-enregistrement déclare enfin que l'indicateur de maintien de la base gelée signale
> une cible inchangée et non une rampe immobile, qu'il est donc actif pendant une partie
> des pas de rampe, et que la base ne contient aucune feature isolant le plateau.

### B4 — la porte de marge exige plus que ce que P1 exige, et elle est rejouée d'une famille de plans à l'autre

Deux asymétries doivent être écrites avant, pas après.

**La porte est plus stricte que le critère de campagne.** La porte 5 impose un minimum
`>=5 %` **par organisme** dans chaque régime, alors que P1 n'exige qu'une **moyenne
favorable par régime**. Le smoke demande donc au dessin une uniformité de l'opportunité
que la campagne ne réclame nulle part. C'est ce delta qui a fermé LIFE-011: la médiane
valait `16,8853 %`, la moyenne du régime `settling` était largement favorable
(`19,8871 %` et `4,4039 %`), et seul le minimum a échoué. Garder cette porte est
défendable — c'est une garantie d'attribution, pas de puissance — mais alors la charge de
couverture qu'elle impose au dessin doit être reconnue, et c'est exactement ce que B1
rend impossible à tenir pour `28 %` d'une famille.

**Le nombre de tirages est petit et la porte est rejouée.** Le minimum est pris sur deux
organismes par régime. Répéter cette porte sur des familles de plans successives —
v2 jamais mesurée, v3 mesurée à `4,4039 %`, v4 proposée — revient à filtrer les dessins
par un test à deux tirages dont la variance est grande. Rien dans le dossier ne consigne
cette répétition, et un smoke vert au troisième essai pourrait n'être qu'un tirage
favorable.

#### Texte normatif intégrable

> **Statut et historique de la porte de marge.** (i) Le pré-enregistrement déclare que la
> porte 5 (`minimum >= 5 %` par organisme et par régime) est **strictement plus exigeante**
> que la condition correspondante de P1 (moyenne favorable par régime), qu'elle est une
> garantie d'attribution destinée à empêcher une campagne sans opportunité de sélection, et
> qu'elle demande donc au dessin une uniformité que la campagne ne réclame pas.
> (ii) Le pré-enregistrement consigne l'historique de cette porte: v2 jamais mesurée
> (arrêt D-040), v3 mesurée à `16,8853 %` de médiane et `4,4039 %` de minimum `settling`
> (D-043), v4 en cours. Il déclare que le minimum est estimé sur deux organismes par
> régime, que sa variance d'échantillonnage est élevée, et qu'un franchissement au
> troisième dessin ne constitue pas à lui seul une démonstration que l'opportunité est
> uniforme.
> (iii) Ni la forme, ni le seuil, ni le nombre d'organismes de cette porte ne sont modifiés
> sous LIFE-012. Toute modification ultérieure de sa forme devra être argumentée à partir
> de la structure de P1 seule, sans référence à la valeur `4,4039 %`, et sous un nouvel
> identifiant.

### B5 — portée: un succès de LIFE-012 ne démontrerait pas le mécanisme du plateau

Le pré-enregistrement présente la causalité « pas de plateau en v3 → opportunité
insuffisante sur `18496` » comme acquise. Elle est **inférée** d'un motif d'allocation —
l'oracle choisit `step_hold` vingt fois sur vingt-quatre et n'obtient que `4,4039 %` — et
n'a jamais été mesurée. LIFE-012 ne comparera pas non plus v3 et v4 sur les mêmes
organismes: identifiants, graines et plans changent ensemble. Un succès établirait donc
qu'un dessin à plateaux franchit la porte, pas que les plateaux en sont la cause.

Deux conservations de LIFE-011 manquent par ailleurs au texte: la déclaration que
`life006_transparent_score` est réduite à quatre termes actifs lorsque `predicted_risk` et
`motor_cost` sont constants (B5-(iii) de LIFE-011, d'autant plus vraie que `motor_cost`
passe de `0,09375` à `0,046875`), et le rappel que le préflight de profondeur deux est une
vérification de bout en bout **en plus** de l'invariant par essai, non un substitut.

#### Texte normatif intégrable

> **Portée du résultat et conservations.** (i) Le pré-enregistrement déclare que le lien
> entre l'absence de plateau en v3 et la marge `4,4039 %` de `18496` est une **hypothèse
> de conception non mesurée**, qu'aucune comparaison contrefactuelle v3/v4 n'est effectuée
> sur les mêmes organismes, et qu'un succès de LIFE-012 démontrerait le franchissement des
> portes par le dessin v4 sans démontrer que les plateaux en sont la cause.
> (ii) Il déclare que `predicted_risk = 0,0` et `motor_cost = 0,046875` sont constants,
> mis à l'échelle `1,0`, et que `life006_transparent_score` s'en trouve réduite à
> `epistemic_gain + learning_progress + 0,25 · novelty + 0,5 · controllability`; ce point
> est rappelé dans l'interprétation de P2, dont cette baseline est membre.
> (iii) Il rappelle que l'invariant d'exposition par essai s'applique dans tout magasin et
> à toute profondeur, et que le préflight de profondeur deux le complète sans le remplacer.

## Points audités et jugés conformes

- **Légitimité de l'essai.** Aucun seuil relâché, aucun organisme filtré ou rejoué,
  nouvelles graines, nouveaux plans, nouveau digest, revue demandée avant code. Le
  changement est mécaniste et non métrique. Sur le critère « la suite transforme-t-elle
  `4,4039 %` en succès ? », la réponse est **non**, sous réserve de B4-(iii).
- **Arithmétique v4.** Exacte: `240,0°` commandés, `32` pas, départ et retour à `90°`,
  cibles `{30, 60, 75, 90, 105, 120, 150}` toutes dans `[30°,150°]`, `4/8/16` changements,
  et au nominal `20/24/32` pas mobiles, `2/4/8` renversements, `6/4/0` maintiens hors
  neutre, `240,0°` réalisés — conformes au texte au pas près.
- **Compatibilité de garde.** Aucune cible dans la zone de marge de `10°`;
  `predicted_risk = 0,0` par construction; `motor_cost = 240/(160 × 32) = 0,046875`
  exactement, soit dix-sept fois sous la limite `0,80`. La rampe atteint désormais `30°` et
  `150°` et y séjourne, ce qui rapproche l'angle observé de la zone de marge sans jamais
  l'atteindre: il resterait `10°` de dépassement à franchir, puis `16` événements sur `32`
  pour bloquer une candidate. L'invariant par essai couvre le cas résiduel.
- **Plausibilité mécanique du plateau.** Avec `kp ∈ [7,13]`, `kv ∈ [0,08 ; 0,24]` et une
  inertie de l'ordre de `6·10⁻⁴` à `8·10⁻⁴ kg·m²` (`bench_model.py`), la pulsation propre
  est de l'ordre de `95` à `130 rad/s` et l'amortissement réduit de l'ordre de `0,5` à
  `1,2`: le temps d'établissement se situe entre `40` et `80 ms`, soit `2` à `4` pas de
  contrôle. Les quatre fenêtres de trois pas (`60 ms`) de `step_settle_v4` et les huit
  fenêtres d'un pas de `reversal_v4` encadrent donc correctement le transitoire, et
  `micro_v4` n'en offre aucun à aucune cadence déclarée. La séparation `gain`/
  `amortissement` visée est mécaniquement plausible, sous réserve des vérifications
  exigées en B3.
- **Sens du ciblage.** Les régimes `settling_dominant` et `friction_dominant` conservent la
  vitesse nominale, donc la cadence `12,0°/pas`, donc les plateaux. Le mécanisme est
  disponible exactement là où LIFE-011 a échoué. C'est le bon ciblage; c'est sa couverture
  de la famille `speed_dominant` qui pose problème (B1).
- **Graines et espaces RNG.** `18791..18796`, `18801..18832`, `18841..18848`,
  `18901..18924` et `2026072705` sont disjoints de tous les espaces LIFE-009, LIFE-010 et
  LIFE-011, y compris de `18491..18496` déjà consommées. Avec
  `regime_for_seed(seed) = (...)[seed % 3]`, six graines consécutives donnent `2/2/2` et
  vingt-quatre donnent `8/8/8`. Développement `32 × 24 × 3 = 2304`, validation `576`, sans
  filtrage. Sept espaces nommés sous namespace LIFE-012.
- **Conservation de B1–B6 de LIFE-011.** La porte analytique de complémentarité aux trois
  cadences, la plaque de marge avant professeur, l'invariant par essai, le préflight de
  profondeur deux, la déclaration des signaux constants, l'ancrage numérique
  `AUC_moyenne(greedy) > AUC_moyenne(round_robin)`, le plancher `>=3 %` face à round-robin,
  les familles Holm et P3 de non-infériorité appariée sont repris. La structure en deux
  plaques — celle qui a évité une campagne inutile sous D-043 — est conservée et écrite
  comme condition d'ouverture.
- **Compétence, protection et professeur.** Prior à `12°/pas`, ridge résiduelle à treize
  features `alpha=1,0`, partage pair/impair, acceptation à `+1e-12`, magasins temporaires,
  branches isolées, comptes exacts, replay bit-identique: identiques à LIFE-011 amendée,
  sans dilution.
- **Arrêts et interprétation.** Liste exhaustive, aucune analyse partielle, aucune seconde
  campagne, et une section de portée qui exclut explicitement la découverte autonome, la
  causalité générale, le transfert physique et la compatibilité curriculum–garde. Correct,
  sous réserve de B5-(i).

## Remarques non bloquantes

- **R1 — la porte analytique ne survit que par les renversements.** Telle qu'implémentée
  dans `complementarity_gate`, elle exige qu'un indicateur diffère avec un signe constant
  **à toutes** les cadences auditées. À `4,8°/pas`, `n_mobiles`, `n_maintiens_hors_neutre`
  et `déplacement_réalisé` sont à égalité pour les trois plans v4: seul
  `n_renversements` porte la différenciation. Les « ordres gelés » annoncés au
  pré-enregistrement ne valent donc qu'au nominal, ce que le texte devrait dire; la porte
  passe malgré tout, ce qui est la raison pour laquelle B1 est nécessaire.
- **R2 — plateaux d'un seul pas.** `reversal_v4` n'offre qu'un pas de maintien par
  arrivée, soit `20 ms`, inférieur au temps d'établissement le plus court estimé. Sa
  contribution au canal établissement est réelle mais faible; l'essentiel repose sur
  `step_settle_v4`.
- **R3 — porte de progrès sous excitation réduite.** Le déplacement réalisé par essai passe
  de `384°` (v3, plans mobiles) à `240°`. La porte 4 (`MAE finale round-robin <= 80 %` du
  prior) a été franchie en LIFE-011 avec des ratios de `0,15316` à `0,54899`, donc avec une
  marge confortable; le risque est faible, mais il augmente et mérite d'être suivi.
- **R4 — quantification.** À `240°` commandés, les résidus de plateau seront de faible
  amplitude devant le pas AS5600 de `0,0879°`. L'export exigé en B3 permettra de vérifier
  que la décroissance reste résolue; sous la voie A de B1, à `120°`, cette vérification
  devient plus importante encore.
- **R5 — départage initial de greedy.** L'ordre ASCII donne bien
  `probe_micro_v4`, `probe_reversal_v4`, `probe_step_settle_v4` aux trois premiers cycles,
  comme annoncé. Sur `18493` et `18496`, greedy avait choisi `micro` `22/24` fois: la
  prépondérance de `micro` chez greedy est donc un comportement établi et non un accident,
  et vaut d'être suivie sous v4, où `micro_v4` est le seul plan sans aucun plateau.

## Synthèse

LIFE-012 fait ce que D-043 exigeait: elle explique comment augmenter l'opportunité de
sélection dans le régime `settling` sans toucher au seuil qui vient de la refuser. Le
mécanisme choisi — transformer une fraction de rampe saturée en plateaux réellement
atteints — est mécaniquement plausible, correctement dimensionné face au temps
d'établissement du banc, et exactement ciblé sur les familles à vitesse nominale, qui sont
celles où LIFE-011 a échoué. L'arithmétique annoncée est exacte.

Le défaut est de couverture, et il est arithmétique. Avec `240°` commandés sur `32` pas,
le plateau — seul changement scientifique de la tranche — n'existe qu'au-dessus de
`375°/s`, alors que la famille `speed_dominant` descend à `240°/s`. Pour `28,125 %` de
cette famille, les trois plans redeviennent trois rampes identiques, la classe de
diagnostic « inerte » devient vide et le code hérité lève une exception au lieu de rendre
une porte. La probabilité qu'un tel organisme apparaisse est de `48,34 %` au smoke et de
`92,88 %` sur les huit organismes `speed` du test. C'est le seul point qui, laissé en
l'état, transformerait un dessin défendable en quatrième non-résultat technique.

**Autorisation.** Une fois **B1 à B5** intégrées comme amendements pré-calcul datés et
additifs, **l'implémentation peut commencer, puis la plaque de marge `18791..18796` peut
être exécutée**. Les banques `18801..18832`, `18841..18848` et `18901..18924` restent
interdites jusqu'à: choix de voie B1 écrit au manifeste avec le digest du protocole;
sémantique des classes vides implémentée et testée; taxonomie `rampe/plateau/temps_mort`
et exports de masse d'erreur en place, avec `temps_mort = 0` asserté; historique et statut
de la porte de marge déclarés; six portes de plaque vertes; puis dix portes finales vertes
avec projection complète sous `90` minutes. Toute promotion reste interdite avant une
revue contradictoire des résultats.
