# Revue contradictoire pré-calcul LIFE-011 — plans recentrés, éligibilité persistante

Date: 2026-07-27. Revue demandée avant implémentation, avant tout smoke `18491..18496` et
avant toute banque `18501..18624`. Fichiers audités intégralement:
`docs/research/life_011_preregistration.md`,
`docs/research/life_010_preregistration.md` (amendée B1–B7),
`docs/research/life_010_review.md`, `docs/research/life_010_technical_stop.md`,
`docs/research/life_009_technical_stop.md`,
`docs/research/kernel_001_implementation.md`, `DEVELOPMENTAL_ARCHITECTURE.md`,
`DECISIONS.md` (D-037 à D-041), `PILOTAGE.md`, `SESSION_HANDOFF.md`,
`cognitive/observed_signals.py`, `cognitive/experiments.py`, `sim3d/life_executor.py`;
en complément, parce que la question de garde l'exige: `cognitive/models.py`,
`sim3d/bench_env.py`, `sim3d/bench_model.py`, `learning/life_010.py`,
`learning/life_010_campaign.py` et `learning/life_009.py`.

Aucune simulation, aucun entraînement, aucun smoke, aucune graine LIFE-011 et aucun test
du dépôt n'ont été lancés. Les seuls calculs effectués sont une **arithmétique sur les
plans gelés et sur le limiteur de vitesse**: coût commandé, longueur, retour à `90°`,
nombre de changements, trace de la rampe interne `_limited_deg` à `12,0`, `4,8` et
`14,4°/pas`, et comptage d'exposition aux frontières selon la formule exacte de
`cognitive/observed_signals.py`. Cette arithmétique reproduit exactement la valeur
`0,75` observée sur `18191`, ce qui vaut vérification du modèle utilisé ici. Aucun
fichier autre que la présente revue n'a été modifié.

## Verdict

**AUTORISER AVEC CORRECTIONS BLOQUANTES.**

LIFE-011 est un essai légitime et non un contournement de garde: le seuil
`max_predicted_risk = 0,50` n'est pas relevé, le catalogue n'est pas écrasé, les plans
sont changés et les graines sont neuves. Le recentrage `20/160 → 30/150` supprime
effectivement l'exposition structurelle: avec les nouvelles cibles, le compte
d'exposition tombe de `24/32 = 0,75` à `0/32 = 0,0000` **exactement**, pour les trois
plans. La cause de D-040 est traitée, et elle l'est dans la seule direction admissible.

Mais le recentrage n'a pas été gratuit, et son prix n'a pas été payé là où le
pré-enregistrement le croit. À budget de `32` pas, faire descendre le coût commandé de
`560°` à `480°` sous un limiteur de `12°/pas` a un effet mécanique: **les trois plans v2
délivrent désormais exactement la même excitation réalisée** — `24` pas mobiles, `8` pas
inertes, `288°` de déplacement réalisé, chacun des pas mobiles saturé au maximum de
vitesse — et ne diffèrent plus que par la cadence de renversement (`4`, `6`, `12`). En
v1, ces mêmes grandeurs valaient `25/28/28` pas mobiles et `288/336/336°`. La
complémentarité annoncée « 5/12/24 » est une propriété des cibles commandées, pas de ce
que l'organisme subit.

C'est la correction bloquante principale, parce qu'elle porte sur la porte qui a fermé
LIFE-009: la marge oracle. Les cinq autres portent sur la profondeur réelle de la porte
d'éligibilité, sur son statut logique, sur la dilution du banc privé par les pas inertes,
sur la contradiction entre la marge exigée et la seule marge jamais mesurée, et sur la
comptabilité des familles statistiques sous ancrage dynamique.

## 0. Essai légitime ou contournement de la garde ?

Essai légitime. Le point est vérifiable sans simulation.

`boundary_exposure` compte, sur les `32` événements d'un essai, ceux dont l'angle
**demandé ou observé** vaut `<= 20°` ou `>= 160°` (marge `10°` sur `[10°,170°]`), et
`predicted_risk` est le **maximum** de cette fraction sur la moitié récente de
l'historique de la candidate.

| plan | cibles | événements demandés en zone de marge |
|---|---|---:|
| `probe_step_hold` v1 | `20/160` | `24/32 = 0,7500` |
| `probe_reversal` v1 | `50/130` | `0/32` |
| `probe_micro` v1 | `70/110` | `0/32` |
| `probe_step_hold_v2` | `30/150` | `0/32` |
| `probe_reversal_v2` | `50/130` | `0/32` |
| `probe_micro_v2` | `70/110` | `0/32` |

La valeur `0,7500` est exactement celle qu'a produit `18191`: l'exposition de LIFE-010
venait donc entièrement des cibles commandées, et pas des angles mesurés. En v2, la
rampe interne reste confinée à `[66°, 150°]` (voir §B1), donc l'angle mesuré ne peut
atteindre `160°` qu'au prix d'un dépassement de plus de `10°` sur une rampe de `12°/pas`,
et il faudrait `16` tels événements sur `32` pour rouvrir le blocage. Le recentrage est
donc efficace, et il l'est par construction plutôt que par réglage.

Il ne rend pas la tâche artificiellement facile au sens du proxy: le catalogue ne sert
qu'à l'éligibilité, il n'entre pas dans la métrique de compétence, et les six
`ExperimentSignals` restent des features de politique aux mêmes conditions qu'en
LIFE-010. Il rend en revanche la tâche **différente**, et c'est l'objet de B1.

## Corrections bloquantes

### B1 — les trois plans v2 ne sont plus complémentaires: excitation réalisée identique

Le limiteur de `sim3d/bench_env.py` borne la rampe interne à
`max_speed_deg_s × control_dt`, soit `12,0°` au nominal. Un plan de `32` pas ne peut donc
déplacer la rampe que de `384°` au plus, alors que les trois plans en commandent `480°`:
**tous les plans v2 sont sur-commandés**, et la trajectoire réalisée ne dépend plus de
l'amplitude des cibles mais seulement du nombre de pas passés en mouvement et du signe
de ce mouvement.

L'arithmétique sur les plans gelés donne:

| plan | pas | coût | chgts | cibles | rampe atteinte | pas mobiles | pas inertes | déplacement réalisé | renversements |
|---|---:|---:|---:|---|---|---:|---:|---:|---:|
| `step_hold_v2` | 32 | `480°` | 5 | `[30,150]` | `[78,150]` | **24** | **8** | **288°** | 4 |
| `reversal_v2` | 32 | `480°` | 12 | `[50,130]` | `[66,114]` | **24** | **8** | **288°** | 6 |
| `micro_v2` | 32 | `480°` | 24 | `[70,110]` | `[78,102]` | **24** | **8** | **288°** | 12 |
| `step_hold` v1 | 32 | `560°` | 5 | `[20,160]` | `[88,160]` | 25 | 7 | 288° | 4 |
| `reversal` v1 | 32 | `560°` | 14 | `[50,130]` | `[66,114]` | 28 | 4 | 336° | 7 |
| `micro` v1 | 32 | `560°` | 28 | `[70,110]` | `[78,102]` | 28 | 4 | 336° | 14 |

Les `24` pas mobiles de chacun des trois plans v2 sont **tous saturés à `±12,0°`**: la
rampe des trois plans est le même signal carré de vitesse, à la séquence de signes près.
La propriété n'est pas un artefact du régime nominal: à `4,8°/pas` (borne basse de
`speed_dominant`) le déplacement réalisé vaut `115,2°` pour les trois plans, et à
`14,4°/pas` il vaut `345,6°` pour les trois.

Deux conséquences que le pré-enregistrement ne peut pas ignorer:

1. **La différence d'amplitude entre plans est dynamiquement inerte.** Le joint
   `neck_servo` est une charnière d'axe `0 0 1` (`sim3d/bench_model.py`), donc la gravité
   ne produit aucun couple autour de l'axe; les géométries de tête sont
   `contype=0 conaffinity=0`, donc sans contact; les butées `[10°,170°]` ne sont jamais
   approchées. La dynamique est **exactement invariante par l'angle absolu**. Les
   excursions `[78,150]`, `[66,114]` et `[78,102]` ne sont donc pas trois conditions
   mécaniques différentes: elles ne diffèrent que par la valeur d'une feature du modèle
   (`angle centré / 80`) dont le coefficient vrai est nul.
2. **La seule dimension de complémentarité restante est la cadence de renversement**
   (`4`, `6`, `12`). C'est une dimension légitime — elle excite différemment le frottement
   sec et les transitoires — mais elle est unique, et elle ne discrimine rien pour
   `speed_dominant`: `max_speed_deg_s` fixe la pente de rampe, et chacun des trois plans
   la révèle sur chacun de ses `24` pas mobiles, en quantité rigoureusement identique.
   La porte smoke « minimum de chaque régime `>=5 %` » est donc, pour le régime vitesse,
   exposée à un échec prévisible avant tout calcul.

Ce n'est pas un défaut hérité: LIFE-010 différenciait `25/28/28` pas mobiles et
`288/336/336°`. Le passage à `480°` a **supprimé** cette différenciation en la
convertissant en pas inertes. La condition de réouverture « perte de complémentarité »
inscrite en D-041 est précisément celle-ci.

#### Texte normatif intégrable

> **Critères de complémentarité réalisée.** Les trois plans sont gelés seulement après
> vérification arithmétique, écrite au pré-enregistrement et rejouée comme porte de
> construction du smoke, des grandeurs suivantes, calculées sur la rampe interne
> `_limited_deg` aux trois cadences `4,8`, `12,0` et `14,4°/pas`:
>
> - `n_mobiles`: nombre de pas où la rampe se déplace;
> - `n_renversements`: nombre de changements de signe du déplacement de rampe;
> - `n_maintiens_hors_neutre`: nombre de pas où la rampe est immobile à un angle autre
>   que `90°`;
> - `déplacement_réalisé`.
>
> Exigence: pour **chaque paire** de plans et à **chacune** des trois cadences, au moins
> un de ces quatre indicateurs doit différer, et l'ordre relatif des plans sur cet
> indicateur ne doit pas s'inverser entre cadences. Un triplet dont les trois plans
> partagent `n_mobiles`, `n_renversements`, `n_maintiens_hors_neutre` et
> `déplacement_réalisé` est déclaré non complémentaire et ne peut pas être gelé.
>
> Le triplet suivant satisfait cette exigence à coût, longueur, retour et bornes
> inchangés (`32` pas, `480°` commandés, retour à `90°`, cibles dans `[30°,150°]`) et
> peut être adopté tel quel:
>
> ```text
> probe_step_hold_v3 : (150 ×7, 30 ×7, 150 ×7, 30 ×7, 90 ×4)   5 changements
> probe_reversal_v3  : (60,60,90,90,120,120,90,90) ×4         16 changements
> probe_micro_v3     : (75,90,105,90) ×8                      32 changements
> ```
>
> Ses indicateurs à `12,0°/pas` valent respectivement `28/32/32` pas mobiles,
> `4/8/16` renversements, `2/0/0` maintiens hors neutre et `336/384/384°` de déplacement
> réalisé; à `4,8` et `14,4°/pas`, `n_mobiles` et `n_renversements` conservent le même
> ordre. Tout autre triplet satisfaisant les critères ci-dessus est admissible; le choix
> est gelé avant code et n'est jamais révisé après lecture d'une métrique.

### B2 — la marge oracle exigée contredit la seule marge jamais mesurée, et rien dans LIFE-011 ne la fait remonter

La porte 6 exige `>=15 %` de marge médiane de l'oracle et `>=5 %` par régime. La seule
mesure existante dans ce dépôt est celle de LIFE-009: oracle `1,510406` contre
round-robin `1,541603`, soit **`2,02 %`**, et `2,38 %` contre `greedy_uncertainty`
(D-037). LIFE-011 conserve la structure qui produit cette petitesse:

- le banc privé est **uniforme** sur les trois motifs (`2 × 3 × 32`, soit `64`
  transitions par motif, vérifié dans `build_life010_private_bank`);
- les trois plans coûtent le même prix et durent le même temps;
- le budget est de `24` cycles pour `3` options, donc round-robin joue `8/8/8`;
- le modèle de compétence est une ridge à `13` features analytiquement normalisées, dont
  la variance d'estimation s'effondre après quelques dizaines de transitions.

Sous ces quatre propriétés, l'allocation uniforme est proche de l'optimum: la métrique
est une moyenne uniforme sur les trois motifs, et le seul canal par lequel une allocation
peut gagner est la **couverture de plage des régresseurs** — un modèle ajusté seulement
sur `micro` (`Δcommande ∈ {0,20}`) extrapole mal à `step_hold` (`Δcommande ∈ {0,60,120}`).
Ce canal favorise mécaniquement l'uniformité. Il ne reste à l'oracle que l'avantage de
front-loading sur les premiers cycles, que l'AUC sur `0..24` pondère faiblement. C'est
exactement le profil des `2 %` mesurés.

Je ne peux pas démontrer sans calcul que la marge restera sous `15 %`: LIFE-010/011
changent la compétence (résidu d'un prior physique, régimes cachés) et le banc n'est plus
dégénéré comme en LIFE-009. Mais la charge de la preuve a changé de camp après D-037, et
le pré-enregistrement ne dit rien de la raison pour laquelle la marge devrait passer de
`2 %` à `15 %`. Un troisième non-résultat sur cette même porte serait un non-résultat
prévisible.

#### Texte normatif intégrable

> **Marge d'abord, à assiette réduite.** (i) Le pré-enregistrement énonce explicitement
> que la seule marge oracle mesurée dans ce programme vaut `2,02 %` face à round-robin
> (LIFE-009, D-037), qu'elle a été obtenue sous une structure partageant banc uniforme,
> plans équicûteux et budget de `24` cycles, et il énonce le mécanisme par lequel
> LIFE-011 prétend l'augmenter.
> (ii) Le smoke est réordonné: la **plaque de marge** — banc privé, `round_robin`,
> `greedy_public_residual` et oracle sur les six graines — est exécutée et évaluée
> **avant** la construction du professeur `24×3` et avant les trois politiques
> supplémentaires. Les portes 5, 6 et 7 sont tranchées sur cette seule plaque. La plaque
> de chronométrage (professeur, trois politiques restantes, `25` évaluations, analyse,
> digests) n'est exécutée que si les portes 5, 6 et 7 sont vertes.
> (iii) En cas de porte 6 rouge, le manifeste smoke consigne malgré tout, avant clôture,
> la marge oracle par graine et par régime et la matrice `plan préféré par l'oracle ×
> régime`. Ces exports portent exclusivement sur les six graines non réservées; ils ne
> constituent ni une analyse de campagne ni une lecture de banque, et ils sont la donnée
> de conception nécessaire à tout successeur.

### B3 — un quart du banc privé est inerte, ce qui durcit mécaniquement les deux portes de progrès

Chaque plan v2 se termine par `8` pas où la rampe ne bouge pas (`step_hold_v2`: un pas
immobile à `150°` plus sept à `90°`). Le banc privé compte donc `24` transitions inertes
sur `96` par flux, soit **`25,0 %`**, contre `15,6 %` en v1 (`7+4+4` sur `96`). Sur ces
transitions, la cible égale l'angle courant, le prior est quasi exact, et le résidu se
réduit au bruit de quantification AS5600 et au reliquat d'établissement: ni le prior ni
le modèle appris ne peuvent y gagner grand-chose.

Or les deux portes de progrès sont **relatives**: « MAE privée round-robin finale au moins
`20 %` sous le prior » et « marge oracle `>=15 %` ». Diluer la métrique avec un quart de
transitions à progrès quasi nul réduit proportionnellement le progrès relatif atteignable.
Le prix du recentrage est donc payé deux fois: une fois en complémentarité (B1), une fois
en marge mesurable (ici), et les deux fois sur la porte qui a déjà clos LIFE-009.

#### Texte normatif intégrable

> **Décomposition mobile/inerte.** Une transition est dite inerte lorsque la rampe interne
> ne s'est pas déplacée au pas correspondant. Le pré-enregistrement déclare la fraction
> inerte exacte du banc privé pour le triplet gelé. Le smoke exporte, pour chaque graine:
> MAE privée du prior, MAE privée finale de round-robin et marge oracle, **calculées trois
> fois** — sur le banc complet, sur ses transitions mobiles seules et sur ses transitions
> inertes seules. Les portes 5 et 6 restent évaluées sur le banc complet et leurs seuils
> ne sont pas modifiés; la décomposition est un export de diagnostic obligatoire, dont
> l'absence est un arrêt.

### B4 — la porte d'éligibilité vérifie une profondeur d'historique, pas un invariant

Le préflight exécute chaque plan une fois, reconstruit son historique LIFE-002 et exige
que la **seconde** proposition reste éligible. C'est exactement l'état qui a fait tomber
LIFE-010, et c'est donc un progrès réel. Mais ce n'est pas le contrat dont la campagne a
besoin, pour deux raisons vérifiables dans `cognitive/observed_signals.py`:

1. `predicted_risk` est le **maximum** de `boundary_exposure` sur la moitié récente de
   l'historique. Cet ensemble grandit à chaque exécution: une éligibilité constatée à
   profondeur `2` n'implique rien à profondeur `3..24`. Un seul essai anormalement exposé,
   à n'importe quel cycle, suffit à bloquer la candidate et à déclencher
   `AssertionError: cycle did not complete with its selected plan`;
2. le préflight n'est prévu que pour les **six graines smoke**. La garde, elle, s'applique
   à chacun des `24` cycles des `32` organismes de développement, des `8` de validation et
   des `24` de test. Un blocage y surviendrait **après** ouverture de banques réservées,
   c'est-à-dire au pire endroit possible.

La correction n'exige aucun calcul supplémentaire: puisque `predicted_risk` est un maximum
sur un sous-ensemble d'essais, borner **chaque essai** borne la garde à toute profondeur,
pour tout organisme et dans tout magasin. Cette assertion se calcule sur des essais déjà
exécutés et coûte zéro seconde de projection.

#### Texte normatif intégrable

> **Invariant d'exposition par essai.** Pour chaque essai exécuté par LIFE-011 — préflight,
> banc privé, branche contrefactuelle, magasin principal, développement, validation et
> test — le résumé `ServoTrialSummary` correspondant doit vérifier
> `boundary_exposure <= 0,50` et `motor_cost <= 0,80`. La vérification est faite au moment
> où l'essai est résumé, dans tout magasin, temporaire ou principal. Comme
> `predicted_risk` est le maximum de `boundary_exposure` sur un sous-ensemble d'essais de
> la candidate, cet invariant garantit l'éligibilité à toute profondeur d'historique et
> pour tout organisme, ce que le préflight à profondeur `2` ne garantit pas.
>
> Toute violation est un arrêt immédiat de LIFE-011 comme non-résultat de conception, sans
> relèvement de seuil ni reprise. Le préflight des six graines smoke est conservé tel quel
> comme vérification de bout en bout du chemin proposition→garde, en plus de l'invariant.

### B5 — la porte d'éligibilité est satisfaite par construction et doit être présentée comme telle

Avec des cibles dans `[30°,150°]` et une rampe confinée à `[66°,150°]`, aucun événement ne
peut être compté par `boundary_exposure` sauf dépassement d'au moins `10°` de l'angle
mesuré au-delà de la rampe, et il en faudrait `16` sur `32` pour bloquer. La porte 2 du
smoke ne peut donc pas échouer autrement que sur un bug. C'est le bon dessin — le prompt
demandait d'éloigner les maintiens des zones de marge, et c'est fait — mais c'est une
**assertion d'intégrité**, pas une démonstration scientifique, et LIFE-011 ne démontrera
donc pas « qu'un curriculum reste compatible avec des gardes fraîches »: il évite la
question par construction, ce qui est légitime et doit être écrit.

Le même constat vaut pour deux features: `predicted_risk` est identiquement `0,0` pour les
trois candidates et `motor_cost` identiquement `480/(160 × 32) = 0,09375`. Ce sont deux
colonnes de variance nulle de plus dans les six `ExperimentSignals` exposés à la politique,
et deux termes constants de plus dans `transparent_score`, dont il ne reste que
`epistemic_gain + learning_progress + 0,25 · novelty + 0,5 · controllability`. La baseline
`life006_transparent_score`, que P2 doit battre, est donc structurellement affaiblie par le
recentrage.

#### Texte normatif intégrable

> **Statut de la porte d'éligibilité et des signaux constants.** (i) La porte 2 du smoke
> et le préflight sont classés **assertions d'intégrité**, hors portes scientifiques; leur
> échec reste un arrêt immédiat. (ii) Le pré-enregistrement déclare qu'aucune cible des
> plans gelés ne peut atteindre la zone de marge de `10°` et que l'éligibilité persistante
> est obtenue par construction et non démontrée par l'expérience; aucune revendication de
> compatibilité curriculum–garde n'est portée par LIFE-011. (iii) Le pré-enregistrement
> déclare que `predicted_risk` vaut `0,0` et `motor_cost` `0,09375` pour les trois
> candidates, que ces deux colonnes sont de variance nulle et reçoivent l'échelle `1,0`,
> et que `life006_transparent_score` s'en trouve réduite à quatre termes actifs — ce qui
> est rappelé dans l'interprétation de P2.

### B6 — comptabilité des familles P1/P2/P3 sous ancrage dynamique, et une inégalité à écrire en clair

Trois points empêchent une implémentation sans décision scientifique nouvelle.

1. **Sens de la porte 7.** « si greedy a une AUC moyenne **pire** que round-robin » est
   ambigu dans un document où l'AUC basse est meilleure. L'amendement B1 de LIFE-010, gelé
   sous D-039, écrit la condition numériquement; LIFE-011 la compresse et perd ce gel.
   C'est le même type d'inversion que celui corrigé en B2 de LIFE-010.
2. **Taille de la famille P2.** P2 dit « quatre baselines secondaires ». Si round-robin
   devient co-principale, il ne reste que trois autres politiques, alors que l'amendement
   D-039 maintenait round-robin **dans** la famille Holm P2 tout en lui ajoutant un
   plancher. Le nombre de tests corrigés change selon la lecture, donc le seuil corrigé
   aussi.
3. **Plancher `>=3 %`.** LIFE-011 le place dans P1 (« Face à round-robin, amélioration
   moyenne `>=3 %` dans tous les cas ») alors que D-039 le rattache au test P2. Le
   plancher est le même, mais son appartenance de famille doit être écrite une fois.

#### Texte normatif intégrable

> **Ancrage et familles.** (i) La condition de la porte 7 s'écrit:
> `AUC_moyenne(greedy_public_residual) > AUC_moyenne(round_robin)` — l'AUC basse étant
> meilleure — auquel cas `round_robin` devient co-principale; sinon
> `greedy_public_residual` demeure seule principale.
> (ii) La famille Holm de P2 est **invariablement** composée des quatre politiques non
> apprises autres que la baseline principale initiale, soit `greedy_uncertainty`,
> `round_robin`, `life006_transparent_score` et `uniform_random`. Sa taille est `4` dans
> les deux cas d'ancrage: `round_robin` y demeure même lorsqu'elle devient co-principale,
> conformément à l'amendement D-039, et le seuil corrigé ne dépend donc pas de la décision
> d'ancrage.
> (iii) Le plancher `>=3 %` face à `round_robin` est une condition de **taille d'effet**
> évaluée en P1, en plus du test Holm de P2 qui reste inchangé; il s'applique dans les
> deux cas d'ancrage. Lorsque `round_robin` est co-principale, elle doit en outre franchir
> le plancher `>=5 %`, la condition `16/24` et la condition de signe par régime, et la
> famille de non-infériorité P3 comprend quatre tests.

## Points audités et jugés conformes

- **Arithmétique des plans.** Vérifiée exactement: les trois plans v2 font `32` pas,
  `480,0°` commandés avec `target_-1 = 90°`, se terminent à `90°`, tiennent dans
  `[30°,150°]` et comptent `5`, `12` et `24` changements, conformément au texte et à
  D-041. Les portes de construction sont exactes et satisfaisables.
- **Compatibilité avec `boundary_exposure` et `predicted_risk`.** Vérifiée par la formule
  exacte du code: `0/32` pour les trois plans (§0), contre `24/32` pour `step_hold` v1.
  Le modèle utilisé ici reproduit la valeur `0,75` réellement observée sur `18191`.
- **Contrat de sécurité.** `max_predicted_risk = 0,50` et `max_motor_cost = 0,80` sont
  bien au-dessus des défauts de `cognitive/models.py` (`0,25` / `0,50`) mais identiques à
  ceux de LIFE-010: aucun relèvement. `max_proposals_per_session = 100` couvre `24`
  cycles. `min_interval_ns` reste au défaut `0` et l'horloge simulée avance de `1 s` par
  cycle dans `life_010_campaign.py`: la garde de cadence ne peut pas se déclencher.
- **Isolation du préflight.** Magasin temporaire distinct, espace RNG dédié
  `eligibility_preflight`, exécution avant tout professeur et toute trajectoire. Comme
  `proposal_count` et `last_proposal_time` sont indexés par magasin et session, le
  préflight ne consomme ni quota ni cadence de la campagne, et son historique n'entre pas
  dans les `ExperimentSignals` vus par les politiques. Chaque exécution repart d'un
  `reset(seed)` complet, donc l'organisme n'est pas modifié. Aucune fuite identifiée, sous
  réserve que le chronométrage du préflight entre dans la projection.
- **Graines et espaces RNG.** `18491..18496`, `18501..18532`, `18541..18548`,
  `18601..18624` et `2026072704` sont disjoints de tous les espaces LIFE-009 et LIFE-010,
  y compris de `18191..18196` dont seul `18191` a été partiellement ouvert. Avec
  `regime_for_seed(seed) = (...)[seed % 3]`, six graines consécutives donnent `2/2/2` et
  vingt-quatre donnent `8/8/8`, comme annoncé. Développement `32 × 24 × 3 = 2304`,
  validation `8 × 24 × 3 = 576`, sans filtrage. Sept espaces nommés, aucun générateur
  global.
- **Compétence, protection et limites héritées.** Prior physique inchangé, poids initiaux
  nuls, apprentissage du seul résidu, partage pair/impair, règle d'acceptation à `1e-12`,
  et conservation explicite de B1–B7 de LIFE-010: autocorrélation déclarée, banque privée
  seule mesure de compétence, régimes mono-facteur et identité de distribution déclarées.
  Rien n'a été dilué.
- **Professeur, branches et comptes.** Magasins SQLite/J0 temporaires, une seule branche
  carrée-latine rejouée, `24` propositions/exécutions/sessions/assessments, aucune branche
  dans l'histoire. L'assertion `outcome.experiment_id != experiment_id` de
  `life_010_campaign.py` — celle qui a correctement arrêté LIFE-010 — reste la dernière
  ligne de défense et doit être conservée telle quelle.
- **Statistiques.** `monte_carlo_sign_flip_pvalue` et `monte_carlo_noninferiority_pvalue`,
  `200 000` tirages, graine `2026072704`, Holm, P1 hors famille P2 parce que la promotion
  est conjonctive. Conforme au module gelé et à B7 de LIFE-010, sous réserve de B6
  ci-dessus quant aux tailles de famille.
- **P0.** Ajustement unique, reproduction bit-identique, digest gelé, validation ouverte
  ensuite seulement, Spearman `>=0,25`, gain `>=15 %` sur la constante, et signe par
  régime explicitement dégradé au rang de **garde descriptive** — c'est l'intégration
  correcte de la remarque R1 de la revue LIFE-010.
- **Portée de la promotion et limites.** « Sélecteur optionnel gelé en simulation », revue
  contradictoire des résultats obligatoire, et liste de non-revendications explicite
  incluant la variation mécanique conjointe et l'évaluation de même distribution.
  Correctement étroit; aucune sur-revendication détectée, sous réserve de la
  non-revendication supplémentaire exigée en B5.
- **Arrêts.** Liste exhaustive, aucune analyse partielle, aucune reprise, aucune seconde
  campagne. Conforme au modèle qui a rendu D-037 et D-040 mécaniques.

## Remarques non bloquantes

- **R1 — une feature dont le coefficient vrai est nul.** `angle courant centré / 80` ne
  peut porter aucune information physique (§B1, axe vertical), mais sa plage dépend
  fortement du plan (`±0,75` pour `step_hold`, `±0,15` pour `micro`). Sous `alpha=1,0`,
  c'est un régresseur de nuisance dont l'ajustement dépend de l'allocation. Rapporter son
  coefficient final éclairerait un éventuel écart inexpliqué entre politiques.
- **R2 — `greedy_public_residual` au démarrage.** Inchangé depuis LIFE-010: absence traitée
  en priorité maximale et départage ASCII forcent `probe_micro_v2`, `probe_reversal_v2`,
  `probe_step_hold_v2` aux trois premiers cycles, donc un tourniquet initial. À écrire une
  fois de plus avec les identifiants v2.
- **R3 — `novelty` et les bins de couverture.** Avec `bin_for`, les cibles v2 tombent dans
  les bins `{1,4,7}`, `{2,4,6}` et `{3,4,5}`: la nouveauté n'est non nulle qu'au premier
  essai de chaque plan. Comportement défini, mais autant l'écrire, puisque `novelty` reste
  une feature de politique et un terme de `transparent_score`.
- **R4 — asymétrie de l'oracle.** L'oracle lit les trois progrès privés réels; aucune
  politique causale ne le peut. L'écart appris/oracle mesure la difficulté d'inférence, non
  une insuffisance de la politique. À redire dans le rapport final.
- **R5 — chronométrage du préflight.** Trois exécutions de plan par graine smoke, soit
  `18` essais: négligeable, mais la projection doit les inclure explicitement puisque la
  porte 8 porte sur l'assiette complète.

## Synthèse

LIFE-011 corrige proprement la cause de D-040, sans toucher au seuil de garde, et
l'arithmétique confirme que le recentrage supprime l'exposition de manière structurelle et
non marginale. L'ingénierie héritée de LIFE-010 — professeur isolé, replay bit-identique,
espaces RNG nommés, statistiques gelées, ancrage dynamique de la baseline — reste intacte
et n'a pas été diluée.

Le risque n'est plus une garde qui bloque; il est que LIFE-011 arrive au smoke avec trois
plans que l'organisme ne peut pas distinguer. Le passage de `560°` à `480°` sur `32` pas,
sous un limiteur de `12°/pas`, a converti la complémentarité en pas inertes: `24` pas
mobiles, `8` pas inertes et `288°` réalisés pour les trois plans, à toutes les vitesses de
régime. La marge oracle exigée est simultanément portée à `15 %` alors que la seule marge
jamais mesurée dans ce programme vaut `2,02 %`, sous une structure — banc uniforme, plans
équicûteux, `24` cycles pour trois options — que LIFE-011 conserve intégralement. Ce sont
les deux corrections qui décident du sort de cette tranche; les quatre autres protègent
l'attribution du résultat.

**Autorisation.** Une fois **B1 à B6** intégrées au pré-enregistrement comme amendements
pré-calcul datés et additifs, **l'implémentation peut commencer, puis le smoke
`18491..18496` peut être exécuté**, dans l'ordre imposé par B2: plaque de marge d'abord,
plaque de chronométrage ensuite. Les banques `18501..18532`, `18541..18548` et
`18601..18624` restent interdites jusqu'à: intégration de toutes les corrections
bloquantes; triplet de plans satisfaisant les critères de complémentarité réalisée de B1,
gelé avant code; dix portes smoke vertes; décision d'ancrage écrite au manifeste avec le
digest du protocole; décomposition mobile/inerte exportée; invariant d'exposition par essai
actif dans tous les magasins; et projection mesurée sur l'assiette complète sous les `90`
minutes. Toute promotion reste interdite avant une revue contradictoire des résultats.
