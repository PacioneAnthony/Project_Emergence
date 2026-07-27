# Revue contradictoire pré-calcul REF-003 — transport spatial sous visibilité contrôlée

Date: 2026-07-27. Revue demandée avant implémentation, rendu, smoke `14991` et toute
graine `14301..14316`. Fichiers audités intégralement:
`docs/research/reafference_003_preregistration.md`,
`docs/research/reafference_002_preregistration.md` (amendée C1–C8),
`docs/research/reafference_002_review.md`,
`docs/research/reafference_002_technical_stop.md`,
`docs/research/reafference_001_results_review.md`, `DECISIONS.md` (D-017, D-019 à D-022),
`PILOTAGE.md`, `CODEX_TASK_BRIEF.md`, `DEVELOPMENTAL_ARCHITECTURE.md`; en complément,
lecture du code gelé `learning/reafference_002.py`, `scripts/research/run_reafference_002.py`
et `sim3d/bench_model.py`, dont REF-003 déclare hériter sans changement.

Aucun rendu, entraînement, test expérimental ni calcul sur graine réservée n'a été
lancé. Aucun score `13301..13312` n'a été lu. Le seul calcul effectué est une
**arithmétique de géométrie de caméra sur les distributions du plan gelé** (§2), sans
rendu, sans modèle et sans graine réservée. Aucun fichier autre que la présente revue
n'a été modifié.

## Verdict

**AUTORISER AVEC CORRECTIONS BLOQUANTES.**

REF-003 est un retest légitime d'une hypothèse jamais testée, sur monde et graines
neufs, sans retuning issu de résultats REF-002. Sa correction centrale — la visibilité
contrefactuelle **par paire** — vise exactement le bon défaut, et la distinction
provenance/paire contre trame isolée est scientifiquement juste sur son domaine
d'application.

Mais l'audit établit deux choses que le dossier ne dit pas:

1. **REF-002 n'a pas été arrêté par une « égalité fortuite d'observations ».** Il a été
   arrêté par une **manipulation défaillante**: l'objet externe sortait entièrement du
   champ de la caméra dans environ `3,1 %` des paires `mixed`, et son centre quittait le
   champ dans environ `25 %` d'entre elles. La garde a donc tiré pour la bonne raison
   sous-jacente et la mauvaise raison déclarée. Le diagnostic de
   `reafference_002_technical_stop.md`, de D-020 et de D-021 est matériellement
   incomplet.
2. **La géométrie de REF-003 ne corrige pas ce défaut.** Avec les valeurs
   pré-enregistrées (`bearing = centre du bin − 6°`, distance `1,05 m`, rail `0,44 m`),
   l'objet sort encore **entièrement** du champ dans environ `1,27 %` des paires `mixed`,
   soit `≈10` paires par graine et `≈157` sur la campagne. La garde de visibilité par
   paire, qui est bloquante et interdit tout remplacement, tirera donc — au smoke si l'on
   est chanceux, en cours de campagne sinon. **REF-003 se terminerait en non-résultat
   technique exactement comme REF-002**, plus tard et plus cher.

Ce point est corrigeable avant code, par un changement de paramètres du monde et une
garde structurelle. Sept autres corrections bloquantes portent sur une garde vacuoue,
une régression de la protection anti-fuite, une porte de promotion sans critère, et
l'absence de gel par digest du protocole hérité.

## 0. Légitimité du retest, nouveauté et disjonction — vérifiées

- **Hypothèse non testée.** REF-002 n'a produit aucune porte. D-020 interdit l'analyse
  des 12 triplets et le pré-enregistrement REF-003 le répète. Retester est donc
  légitime, et c'est le traitement exact déjà appliqué à J6-AR001 sous D-012.
- **Aucun retuning.** Les marges (`0,03`, `0,10`), les portes (`TPR mixed 0,70`,
  `FPR 0,07` / bin `0,10`), les budgets (`20×600`, `2 400`, `4 500` pas, batch `256`) et
  la famille Holm de huit tests sont **inchangés** par rapport à REF-002 amendé. Aucune
  valeur n'est une fonction d'un score réservé. Les seules données REF-002 utilisées pour
  concevoir REF-003 sont le hash de la trame en collision et des métadonnées physiques,
  ce qu'autorise D-021. **Je n'ai trouvé aucun réglage dérivé d'un résultat.**
- **Graines.** Balayage du dépôt: `14991` et `14301..14316` n'apparaissent que dans les
  documents de pilotage et le pré-enregistrement; les correspondances dans
  `j6_replay_001_runs.json` sont des sous-chaînes de flottants. Graine statistique
  `2026072701` neuve et disjointe de `2026072002` (REF-001) et `2026072601` (REF-002).
  **Espaces vierges.**
- **Périmètre des modifications déclarées.** Conforme à l'annonce: intégrité,
  visibilité, monde, graines, plafond. Voir toutefois C8 — le changement de monde modifie
  aussi la **difficulté** de H3, ce qui doit être déclaré comme tel.

## 1. Ce qui a réellement arrêté REF-002 — correction du diagnostic

`reafference_002_technical_stop.md` conclut: « L'objet déplacé n'affecte pas la vue
finale dans cette configuration » puis « cette égalité ne démontre ni fuite, ni défaut du
modèle ». La première phrase est exacte; la seconde en tire la mauvaise conséquence. Une
manipulation externe qui n'a **aucun** effet visuel n'est pas une coïncidence: c'est une
paire où `mixed` ne mesure rien.

Le code gelé donne la cause exacte:

- `learning/reafference_002.py:577` construit les banques avec
  `bearing_deg = center + 8.0`; l'objet est donc à `8°` du centre du bin.
- `learning/reafference_002.py:254` tire l'angle de départ à
  `center + U(−4°, +4°)`, et l'amplitude signée vaut `±4, ±6, ±8, ±10°`. **La tête
  s'écarte donc du centre du bin de `±14°` au pire.**
- `sim3d/bench_model.py:59` fixe `camera_fovy_deg = 30,0`; sur une image carrée
  `64×64` le demi-champ horizontal vaut `15°`.
- `scripts/research/run_reafference_002.py:105` mesure la visibilité **tête pointée sur
  le centre du bin**, donc à `+8°` de l'objet: toujours dans le champ, toujours vert.

La garde de visibilité par bin était donc évaluée à une pose favorable unique et ne
pouvait structurellement pas voir que l'objet quitte le champ pour une fraction
importante des paires réellement construites.

### Quantification

Arithmétique sur les distributions du plan gelé (aucun rendu, aucun modèle, aucune graine
réservée): `|amplitude| ∈ {4,6,8,10}` avec effectifs `38/30/30/30` et signes équilibrés,
décalage de départ `U(−4°,+4°)`, position objet de départ `U(−0,13; 0,13) m`,
`|Δ objet| ∈ U(0,05; 0,16) m` bornée au rail. Demi-largeur angulaire de l'objet calculée
depuis `size="0.235"` à la distance du monde.

| Configuration | Centre objet hors champ | Objet **entièrement** hors champ | Paires nulles / graine | Sur 16 graines |
|---|---:|---:|---:|---:|
| REF-002 tel qu'implémenté (`+8°`, `1,32 m`, rail `0,40 m`) | `24,9 %` | **`3,06 %`** | `≈23,5` | `≈376` |
| REF-003 tel que pré-enregistré (`−6°`, `1,05 m`, rail `0,44 m`) | `23,4 %` | **`1,27 %`** | `≈9,8` | `≈157` |
| REF-003 avec décalage `0°` au lieu de `−6°` | `19,7 %` | **`0,00 %`** | `0` | `0` |

Deux conséquences.

**Sur REF-002.** Sa banque `mixed` contenait environ `3 %` de paires sans aucun signal
externe et `25 %` de paires à objet partiellement hors cadre. Si la campagne était allée
à son terme, H3 aurait très probablement échoué pour une raison **inattribuable** — la
manipulation, pas le mécanisme. L'arrêt d'intégrité, déclenché sur un critère mal ciblé,
a en réalité évité un résultat non interprétable. C'est une chance, pas une garantie, et
elle ne doit pas être recommencée.

**Sur REF-003.** Le décalage `−6°` combiné à un rail **allongé** (`0,44` contre `0,40 m`)
et une distance **réduite** (`1,05` contre `1,32 m`) laisse la plage de bearing relatif à
`[−31,8°; +19,8°]`, alors que l'objet disparaît complètement au-delà de
`15° + 12,62° = 27,62°`. Le défaut n'est pas corrigé; il est seulement réduit d'un
facteur `2,4`. Et comme la garde REF-003 est **par paire** et **bloquante sans
remplacement**, il suffit d'**une** paire pour arrêter la campagne: la probabilité
d'atteindre les 16 graines est faible.

## Corrections bloquantes

### C1 — la géométrie du monde REF3 doit garantir la visibilité par construction

Le pré-enregistrement justifie le décalage `−6°` par « rester dans le champ sans livrer
sa position aux modèles ». L'intention est bonne, la valeur est fausse: elle déplace
l'objet vers un bord au lieu de le centrer, et le budget angulaire est déjà saturé par
l'excursion de tête de `±14°`.

Aucun choix de décalage seul ne suffit avec `rail = 0,44 m` à `1,05 m`: il faudrait
`|décalage| ≤ 1,79°`, sans aucune marge. Il faut donc dégager du budget angulaire.

#### Texte normatif intégrable

> **Contrainte structurelle de champ.** Soient `d` la distance de l'objet, `t` la course
> totale du rail, `w` la demi-largeur de l'objet, `δ` le décalage de bearing par rapport
> au centre du bin, `s_max` le décalage maximal de l'angle de départ dans le bin,
> `a_max` l'amplitude signée maximale, et `φ = 15°` le demi-champ horizontal (FOV
> vertical gelé `30°`, image carrée). Le monde REF3 doit satisfaire, pour les six bins et
> pour **toute** configuration atteignable:
>
> ```text
> |δ| + atan(t / 2d) + (s_max + a_max)  ≤  φ + atan(w / d) − 3°
> ```
>
> La marge de `3°` est gelée. La contrainte est vérifiée **analytiquement au gel du
> protocole**, ses termes sont consignés dans le pré-enregistrement, et le smoke la
> réévalue sur l'**enveloppe complète** des configurations atteignables — angles de
> départ extrêmes, amplitudes extrêmes, positions de rail extrêmes — et non sur des poses
> échantillonnées. Une violation est un arrêt avant toute ouverture de graine.
>
> **Paramétrage admissible** (Codex décide sous D-004, tout autre jeu satisfaisant
> l'inégalité est recevable): `d = 1,05 m`, `t ≤ 0,36 m`, `w ≥ 0,30 m`, `δ` tiré par
> paire dans `U(−4°, +4°)` avec un RNG disjoint des RNG moteur, objet, pièce et rendu.
> Ce jeu donne `4 + 9,73 + 14 = 27,73 ≤ 30,95 − 3 = 27,95`, et rend la fraction de paires
> à objet entièrement hors champ **structurellement nulle**.

Le tirage de `δ` par paire, plutôt qu'un décalage gelé, sert aussi la neutralité entre
modèles (§ « Neutralité », C8).

### C2 — la garde de visibilité doit confirmer une propriété, pas jouer une loterie

Telle qu'écrite, la garde est un test par paire, bloquant, sans remplacement, appliqué
`1 536` fois par graine, soit `24 576` occasions d'arrêter la campagne. Elle transforme
une propriété qui doit être **garantie à la conception** en un pari répété à chaque
graine. C'est le mode de défaillance qui vient de coûter REF-002, et le
pré-enregistrement interdit — à juste titre — toute récupération par resampling.

La garde par paire doit être conservée: c'est le bon filet. Mais elle doit devenir un
**contrôle de non-régression** d'une propriété déjà prouvée par C1, et non le mécanisme
principal.

#### Texte normatif intégrable

> **Ordre des gardes de visibilité.** (i) La contrainte structurelle C1 est prouvée
> analytiquement au gel et réévaluée sur l'enveloppe complète au smoke; elle est la
> garantie primaire. (ii) La mesure contrefactuelle par paire `≥0,01` est conservée comme
> contrôle de non-régression: si C1 est satisfaite, aucune paire ne doit la violer, et
> une violation signale un défaut d'implémentation, non un aléa d'échantillonnage.
> (iii) Le smoke `14991` exécute la mesure par paire sur **les sept banques complètes**
> avant toute ouverture de `14301`, et exporte minimum, médiane, maximum et distribution
> par bin. Une violation au smoke interdit l'ouverture des graines réservées; une
> violation en campagne reste un arrêt d'intégrité sans remplacement ni analyse partielle.

### C3 — les collisions de trames doivent rester bloquantes corpus↔banques

REF-003 rend les collisions de trames individuelles descriptives **uniformément**:
« Elles ne sont pas bloquantes si les cinq gardes ci-dessus passent ». Appliqué entre
banques, c'est correct et c'est la leçon juste de l'arrêt 13313: deux banques tenues à
part qui partagent une observation ne constituent pas une fuite, puisque aucune n'est
entraînée.

Appliqué **corpus↔banques**, c'est une régression de sécurité. Une trame de banque
identique à une trame du corpus signifie que l'observation d'évaluation **était dans
l'ensemble d'entraînement**. La garde 2 ne l'attrape pas: elle ne compare que des digests
de **paires** `(frame_start, frame_end)`, et une fuite de ce type ne suppose pas que la
paire entière soit dupliquée. La correction sur-corrige donc le défaut qu'elle vise.

La distinction est connue pour être satisfaisable: l'audit REF-001 avait vérifié par
hachage SHA-256 de chaque trame que le corpus était disjoint des cinq banques sur les
**16** graines, avec pour seule exception une collision entre deux banques tenues à part.

#### Texte normatif intégrable

> **Asymétrie de la garde de collision de trames.** Les collisions de trames
> individuelles **corpus↔banques** restent **bloquantes**: zéro trame de banque ne peut
> être bit-identique à une trame du corpus d'entraînement, sur le smoke et sur chaque
> graine réservée, vérification SHA-256 exportée. Les collisions de trames **entre
> banques** sont descriptives, comptées et exportées avec leurs provenances; elles ne
> bloquent pas, et ne peuvent servir à calibrer, exclure ou pondérer une paire.

### C4 — la garde 4 est vacuoue telle que définie

La garde 4 exige « zéro collision du tuple `(paire, tenseur moteur, provenance)` ». Or
la provenance est définie plus haut comme incluant « banque, graine, bin, contexte et
**index** ». L'index étant unique par construction à l'intérieur d'une banque, le tuple
est **toujours** unique et la garde ne peut jamais tirer. Elle donne une impression de
protection sans en fournir.

Par ailleurs, si l'on retire l'index, la garde devient redondante avec la garde 2, qui
interdit déjà tout digest de paire commun entre banques.

#### Texte normatif intégrable

> **Garde 4 reformulée.** Le tuple audité est `(digest de paire, digest du tenseur
> moteur)`. La garde exige que deux entrées partageant ce tuple partagent aussi la
> **même** provenance complète. Autrement dit: une même observation associée à une même
> commande ne peut pas apparaître sous deux provenances distinctes. Les champs d'index
> n'entrent pas dans la clé de collision. Si cette formulation se révèle strictement
> impliquée par la garde 2, la garde 4 est supprimée plutôt que conservée comme garde
> inopérante.

### C5 — `SANITY-EXTERNAL` figure dans la conjonction de promotion sans critère de succès

La règle de décision exige « conjointement H1, H3, H4, H5, SANITY-EXTERNAL et toutes les
gardes ». Mais l'amendement C2 de REF-002 définit SANITY-EXTERNAL comme purement
descriptive: « aucune supériorité n'y est attendue », et n'assortit « un échec descriptif
de SANITY-EXTERNAL » d'**aucun seuil**. Une condition de promotion sans critère de
franchissement est un degré de liberté post hoc: après la campagne, n'importe quelle
valeur pourra être déclarée « échec » ou « succès ».

#### Texte normatif intégrable

> **Critère gelé de SANITY-EXTERNAL.** SANITY-EXTERNAL est franchie si et seulement si la
> TPR absolue de `transport_jepa` sur `external_only`, au seuil descriptif issu de
> `micro_self_calibration`, est `≥ S`, où `S` est fixé ici, avant tout calcul, et n'est
> jamais ajusté. Aucune comparaison de supériorité n'y entre et aucune valeur
> `external_only` ne peut être citée comme soutien partiel à une revendication de
> réafférence. En dessous de `S`, la campagne est déclarée non interprétable au titre
> d'une manipulation ou d'un détecteur défaillant, sans analyse partielle.

La valeur de `S` relève de Codex sous D-004; elle doit être écrite dans le
pré-enregistrement **avant** implémentation, avec sa justification.

### C6 — l'héritage « exactement REF-002 amendé » n'est gelé par aucun digest

REF-003 déclare reprendre le protocole REF-002 amendé C1–C8 et pose que « toute
différence non explicitement déclarée ci-dessous est interdite ». C'est la bonne
discipline, mais elle est invérifiable: le fichier hérité n'est identifié par aucun
digest, et le code hérité (`learning/reafference_002.py`,
`scripts/research/run_reafference_002.py`) non plus.

Le mécanisme qui a fonctionné existe déjà dans ce projet: le smoke REF-001 consignait le
SHA-256 du pré-enregistrement, et l'audit des résultats a pu vérifier octet pour octet
que le protocole n'avait pas bougé entre le gel, le smoke et la campagne.

#### Texte normatif intégrable

> **Gel par digest de l'héritage.** Le pré-enregistrement REF-003 consigne, à la date de
> gel, le SHA-256 de `docs/research/reafference_002_preregistration.md` amendée et celui
> de chaque module hérité. Le smoke `14991` recalcule ces digests, consigne le sien
> propre et celui du présent fichier, et refuse de s'exécuter en cas de divergence.
> Les modifications autorisées du monde, des graines, de la visibilité et du plafond sont
> exposées comme **paramètres** explicitement énumérés; toute divergence de code au-delà
> de ces paramètres est un arrêt d'intégrité.

### C7 — le seuil `0,01` n'est pas dérivé, et visibilité n'est pas détectabilité

Deux problèmes distincts.

**Dérivation.** `0,01` porte sur `mean(|Δ|)/255` calculée sur **toute la trame**
`64×64×3`. Un objet occupant `p` de la surface doit donc produire un changement local
moyen d'environ `0,01/p`. Le seuil est défendable — le rendu MuJoCo étant déterministe,
le plancher de bruit est exactement `0`, donc tout seuil positif est au-dessus du bruit —
mais sa valeur n'est justifiée nulle part et détermine directement la probabilité d'arrêt
de campagne.

**Visibilité ≠ détectabilité.** Dans `mixed`, la quantité qui décide de la TPR n'est pas
l'effet objet absolu mais son rapport au changement induit par la tête, contre lequel le
seuil est calibré (`moving_self_calibration`). Une paire à effet objet `0,01` sur un fond
de mouvement propre d'ordre `0,25` est un positif indétectable pour **toutes** les
méthodes. Une distribution concentrée près du seuil déprimerait la TPR de tout le monde
et rendrait un échec de H3 inattribuable — exactement ce que l'amendement C3 de REF-001
avait appris à éviter.

#### Texte normatif intégrable

> **Justification et diagnostic du seuil de visibilité.** Le pré-enregistrement écrit la
> dérivation de `0,01` en termes de fraction de surface occupée par l'objet et de
> changement local correspondant, et déclare que ce seuil est un **détecteur de
> pathologie**, non le point de fonctionnement attendu. L'export d'audit consigne, par
> banque, bin et paire, l'effet contrefactuel objet **et** le changement photométrique
> induit par la tête sur la même paire, ainsi que leur rapport; distribution par bin
> exportée. Ces diagnostics sont descriptifs, ne participent à aucune porte et ne peuvent
> déclencher aucun réglage, exclusion ou pondération. Le rapport final lit la TPR de H3
> conjointement à cette distribution.

### C8 — le changement de monde modifie la difficulté et doit être déclaré comme tel

REF-003 déclare ses changements de monde sous « intégrité, visibilité, monde, graines,
coût des rendus ». C'est exact, mais incomplet dans ses conséquences: passer de `1,32 m`
à `1,05 m` fait croître la demi-largeur angulaire de l'objet de `10,09°` à `12,62°`,
c'est-à-dire que **le signal externe devient plus grand** alors que les portes
(`TPR mixed ≥0,70`, marges `0,10`) restent inchangées.

Ce n'est **pas** un retuning — aucun score n'a été lu, et rendre visible une manipulation
qui ne l'était pas est une correction obligatoire. Mais le protocole devient plus facile
à portes constantes, et cela doit être écrit pour qu'un succès futur ne soit pas sur-lu.

#### Texte normatif intégrable

> **Déclaration d'effet du changement de monde.** Le monde REF3 augmente la taille
> angulaire de l'objet externe et garantit sa présence au champ. À portes inchangées, la
> porte absolue de H3 devient plus facile et les marges de supériorité `≥0,10` deviennent
> plus difficiles, les baselines bénéficiant du même gain de signal. Aucun ajustement de
> porte n'est permis à ce titre. Le rapport final déclare explicitement que la TPR
> obtenue n'est pas comparable à celle d'un monde où l'objet quitte le champ.

## Neutralité entre modèles — réponse explicite

La question posée est de savoir si la correction REF-003 est neutre entre modèles ou
peut favoriser `transport_jepa`. Réponse en trois parties.

1. **La garde de visibilité elle-même est neutre.** Elle est calculée à partir de deux
   rendus et d'aucun modèle. Elle ne consulte ni score, ni latent, ni checkpoint. Elle ne
   sélectionne pas de paires: elle arrête, sans remplacement ni resampling, ce qui exclut
   tout biais de sélection post hoc. Sur ce point le pré-enregistrement est bien construit.
2. **Son effet sur les portes est légèrement conservateur.** En supprimant les paires
   sans signal externe, elle relève le plafond de TPR atteignable pour **toutes** les
   méthodes. Elle facilite donc la porte absolue `≥0,70` de `transport_jepa`, mais durcit
   les marges de supériorité `≥0,10`, puisque `pixel_change` et `yaw_warp` profitent du
   même gain. Sur la comparaison décisive, l'effet net va **contre** le candidat.
3. **En revanche, le décalage de bearing gelé n'est pas neutre.** Tant que l'objet est
   placé à un décalage **constant** du centre du bin, sa position attendue dans l'image
   est une fonction déterministe de l'angle de tête — information que les trois
   apprenants reçoivent. Un modèle doté d'une carte spatiale explicite et d'un biais de
   transport peut exploiter cet a priori positionnel plus directement qu'un modèle qui
   diffuse la commande en canaux constants. Un succès de `transport_jepa` pourrait alors
   être attribuable à « le changement externe apparaît toujours vers la colonne `X` étant
   donné la commande » plutôt qu'à une copie d'efférence transportée. **C'est la seule
   voie par laquelle la correction REF-003 pourrait favoriser le candidat**, et elle est
   fermée par le tirage de `δ` par paire prescrit en C1.

En complément, et pour que la garde d'attribution demandée par le prompt soit réellement
opérante, je recommande l'export descriptif ci-dessous (non bloquant, R4).

## Points audités et jugés conformes

- **Disjonction par provenance.** Espaces de RNG et de pièces disjoints corpus↔banques
  puis entre banques, digests de paire, unicité intra-banque: le dispositif est correct et
  couvre le risque réel de réutilisation. Sous réserve de C3 et C4.
- **Choix de rendre les collisions de trames descriptives entre banques.** Justifié.
  Deux banques tenues à part ne sont pas entraînées; l'égalité d'une observation n'y est
  pas une fuite. L'audit REF-001 avait déjà rencontré ce cas exact et conclu de même.
- **Inaccessibilité des contrefactuels.** L'exigence que trame contrefactuelle, valeur de
  visibilité et état objet restent invisibles aux cinq méthodes est correcte et
  implémentable proprement: `set_external_object_displacement` suivi d'un rendu ne
  rejoue pas la dynamique de tête, donc le contrefactuel se calcule à pose de tête
  identique, sans altérer la paire. À asserter comme les autres (R2).
- **`yaw_warp`.** Le prédicteur cinématique gelé de C3 REF-002
  (`clip(c_k − angle_prédit_k, ±12°)`, avec `12° = 600 °/s × 0,02 s`) n'utilise ni
  `as5600_fin`, ni le déplacement réalisé. Les intrinsics (`fx=fy=32/tan(15°)`,
  `cx=cy=31,5`) découlent du FOV gelé. La convention de signe est fixée par trois tests.
  L'asymétrie en faveur de la baseline est nommée et sa limite d'interprétation écrite.
  **Conforme, et c'est une baseline honnête et exigeante.**
- **Information pré-transition et interdiction de l'angle futur.** C5 de REF-002 exige la
  recomputabilité bit à bit du tenseur moteur depuis `as5600` de départ, la séquence de
  commandes et l'horizon, sur les sept banques. C'est la garde qu'il fallait et REF-003
  la reprend explicitement (garde 5).
- **Équité des trois JEPA.** C4 de REF-002 est solide: digest d'encodeur, paramètres
  totaux/entraînables/**actifs**, interdiction des branches de remplissage, ratio de temps
  par pas `≤1,25`, et identité bit à bit du tenseur reçu par le résidu à commande nulle.
  Le smoke REF-002 a d'ailleurs **effectivement tiré** sur ce critère
  (`1,29969 > 1,25`) avant d'être corrigé sans changer information, seuil ni budget: la
  garde fonctionne.
- **Appariement moteur, seuils, masques.** Calendriers appariés par multiensemble entre
  `moving_self_calibration`, `moving_self_test` et `mixed`, seuils par strate,
  égalités non externes, égalité des multiensembles de fractions de pixels valides du
  warp: le décalage de domaine identifié en REF-001 est fermé.
- **H1, H3, H4, H5, Holm.** Famille de huit tests = H1 contre deux contrôles, H3 contre
  quatre, H5 deux perturbations. Compte exact. `H3` seule porte de détection,
  `SANITY-EXTERNAL` hors Holm, H4 déterministe sur `moving_self_test` et
  `micro_self_test` avec dispersions par graine exportées, H5 renommée garde de
  non-dégénérescence et exécutée sur les trois conditions. Toutes mes corrections REF-002
  ont été intégrées fidèlement.
- **Règles d'arrêt et de clôture.** Non-remplacement, absence d'analyse partielle,
  campagne incomplète = non-résultat technique, clôture de la variante quel que soit le
  verdict, seconde revue avant promotion: conforme au précédent D-012/D-015/D-020, qui a
  rendu ces décisions mécaniques.
- **Plafond de 90 minutes.** Faisable et même large. REF-002 a consommé
  `2 109,24 s` pour 12 triplets et une préparation, soit `≈171 s` par graine, en ligne
  avec sa projection de `48,12` min. Les `1 536` rendus contrefactuels par graine
  s'exécutent à pose de tête inchangée: à l'ordre de `2,4 ms` par rendu observé sur ce
  substrat, ils coûtent quelques secondes par graine, soit **moins d'une minute sur toute
  la campagne** — un ordre de grandeur en dessous des `15` minutes ajoutées au plafond.
  La formule de projection `48 × (partagé/3 + moyenne des temps complets)` reste
  arithmétiquement juste. Voir R3.

## Remarques non bloquantes

- **R1 — corriger le compte-rendu de l'arrêt REF-002.** `reafference_002_technical_stop.md`,
  D-020 et D-021 attribuent l'arrêt à une « égalité fortuite d'observations ». L'analyse
  du §1 montre que la cause est une manipulation hors champ affectant `≈3 %` des paires
  `mixed`. Consigner cette rectification protège la mémoire du projet: sans elle, la
  leçon retenue serait « la garde était trop stricte » alors qu'elle est « la garde de
  visibilité était mesurée à la mauvaise pose ». Aucun score n'a besoin d'être lu pour
  écrire cette rectification.
- **R2 — asserter l'étanchéité des contrefactuels.** Sur le modèle de C5, exiger au smoke
  que les tenseurs de banque consommés par les cinq méthodes ne contiennent aucun champ
  contrefactuel ni aucune valeur de visibilité, et que ces grandeurs n'existent que dans
  le manifeste d'audit.
- **R3 — chronométrer les contrefactuels séparément.** Le pré-enregistrement les range
  dans la phase « préparation ». Les isoler permet de vérifier que le relèvement du
  plafond de `75` à `90` minutes correspond bien à leur coût, et empêche qu'un plafond
  généreux absorbe silencieusement une autre croissance de coût sans déclencher la
  discipline d'amendement.
- **R4 — diagnostic d'attribution.** Exporter, à titre descriptif, la TPR de H3 en
  fonction de la position de l'objet dans l'image et de l'amplitude du mouvement propre.
  Un succès concentré sur une bande d'image prédictible depuis la commande serait un
  indice d'exploitation d'a priori positionnel plutôt que de transport; un succès uniforme
  soutiendrait l'attribution au mécanisme.
- **R5 — préciser la plage de départ de l'objet.** REF-003 fixe l'amplitude
  (`0,07..0,18 m`) mais pas la plage des positions de départ, qui entre pourtant dans la
  contrainte de champ de C1. À écrire explicitement.
- **R6 — mettre à jour le compte de tests.** Le dépôt est à `236` tests verts depuis
  D-022; la séquence REF-003 doit exiger au moins ce nombre plus ses tests propres.

## Autorisation

Une fois les corrections **C1 à C8** intégrées au pré-enregistrement comme amendements
pré-calcul datés et additifs, **l'implémentation peut commencer, puis le smoke `14991`
peut être exécuté**. Les graines `14301..14316` restent interdites jusqu'à: intégration
de toutes les corrections bloquantes; preuve analytique de la contrainte de champ C1
consignée au pré-enregistrement; smoke entièrement vert incluant la mesure de visibilité
par paire sur les sept banques, la garde asymétrique de collision de trames, la garde 4
reformulée et la vérification des digests hérités; projection temporelle concordante et
manifeste portant le digest du protocole. Toute promotion reste interdite avant une
seconde revue contradictoire des résultats.

La correction centrale de REF-003 vise juste. Le protocole échouera néanmoins sur sa
propre garde tant que la géométrie du monde ne garantira pas ce que cette garde
vérifie — c'est la même erreur que REF-002, déplacée d'un cran. C1 la ferme; le reste du
dossier est le meilleur état de ce programme depuis son ouverture.
