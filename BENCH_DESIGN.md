# Émergence — Dossier de conception du banc d'essai v1.0

Dernière mise à jour : 2026-06-12
Statut : `référence mécanique pour modélisation Fusion 360, mesures réelles en attente`
Remplace : montage v0.1 (pâte à fixer, servo posé sur polystyrène)

Le montage successeur a été appelé « v0.2 » pendant les échanges de conception. Ce dossier le versionne `v1.0` car il remplace le prototype v0.1 par une architecture porteuse complète.

### Mesure de référence du montage v0.1

La session `j0-20260612T123848.687322Z-afac9e86` confirme l'observation d'Anthony d'un mouvement tremblant. Le rapport `reports/mechanics.json`, produit par `python -m j0.cli mechanics <session>`, mesure le bruit gyroscopique résiduel entre 0,5 et 1,5 seconde après chaque commande relativement au repos:

- commande 80 degrés: ratio `5,22`;
- commande 100 degrés: ratio `13,45`;
- retour 90 degrés: ratio `9,72`;
- limite provisoire de réception du successeur: ratio inférieur ou égal à `3,0` pour chaque déplacement non nul.

Ce seuil est un critère comparatif d'ingénierie ajouté après observation du v0.1, pas une calibration absolue des vibrations. L'AS5600 reste nécessaire pour mesurer répétabilité, jeu et erreur d'angle.

## 1. Objet et contraintes héritées du projet

Le banc porte la tête mobile (webcam BRIO 100, HC-SR04, IMU MPU-9250/6500/9255, piézo) entraînée
par le servo MF90, et accueille la vérité terrain d'angle AS5600 prévue par P-001, sous réserve
de validation d'achat ANT-008. Contraintes issues
de la documentation existante :

- limites servo 10 à 170 degrés (`J0_PROTOCOL.md`, `J0_RUNBOOK.md`) ;
- IMU fixée **sur la tête mobile** (`DEVELOPMENTAL_ARCHITECTURE.md`, ligne 75 — ceci répond à la
  question en attente dans `ANTHONY_INBOX.md`) ;
- piézo **mécaniquement couplé** à la structure mobile, sinon il reste interprété comme simple
  contact (`J0_PROTOCOL.md`) ; le tapotement de qualification se fait sur le support mobile ;
- AS5600 (`HARDWARE_PURCHASES.md`) : aimant diamétral D6 × 2,5 mm (AS5000-MD6H-1) centré sur
  l'axe du cou, entrefer 0,5 à 2,5 mm, support non ferromagnétique, alignement validé au registre
  AGC avant tout collage définitif, lecture stable sur 10–170° ;
- sessions de 30 minutes : rien ne doit bouger ni se découpler pendant la session.

Décisions actées (session du 2026-06-11) : AS5600 sur **portique fixe au-dessus de la tête**,
plateau **banc complet** (tour servo + Mega + breadboard), imprimante **classe Creality/Ender**
(jeux prudents), livrable ce document.

## 2. Architecture générale

Cinq sous-ensembles imprimés, tous solidaires du plateau :

| Réf. | Pièce | Fonction |
|------|-------|----------|
| A | Plateau | Base 220 × 210 mm, porte tout, pieds antidérapants |
| B | Tour servo | Loge le MF90 axe vertical, porte la piste de glissement |
| C | Tête mobile | Plaque + berceau caméra + clip HC-SR04 + étagère IMU + piézo + mât aimant |
| D | Portique AS5600 | Colonne arrière + bras en porte-à-faux au-dessus de l'axe, réglable Z et XY |
| E | Accessoires | Capuchon aimant, anneau de serrage piézo, peignes de câbles, cales 0,5/1,0 mm |

### Vue de côté (schéma de principe, z en mm depuis le dessus du plateau)

```
                          ┌────────────┐  bras portique (réglage Z par lumières)
                          │  AS5600 ▼  │  carte composants vers le bas
        z≈152 ──────────  └─────┬──────┘
        z≈150,5    aimant ▓▓  entrefer 0,5–2,5         │
        z=150      ┌─[mât]─┐                           │
        z≈130      │HC-SR04│ (transducteurs face avant)│ colonne
        z≈100      │ ◯ BRIO│ (axe optique sur l'axe du │ portique
        z=64       ┌┴──────┴┐ plaque de tête           │ (arrière,
        z=60       ╞══piste══╡ ← glissement PLA/PLA    │ hors balayage
        z=0..60    │  TOUR   │ servo MF90 axe vertical │ 10–170°)
        z=0     ═══╧═════════╧═══════════════════════════╧═══ plateau
```

### Vue de dessus (plateau 220 × 210, origine coin avant-gauche)

```
   y=210 ┌──────────────────────────────────────────────┐
         │   [breadboard 165×55]                        │
   y=145 │  ┌─────┐                                     │
         │  │portq│         ┌──────────────┐            │
   y=115 │  └─────┘         │              │            │
         │   ╭─────╮        │  Mega 2560   │            │
   y=50 ─│──(  TOUR )──axe  │  (verticale) │            │
         │   ╰─────╯        │              │            │
         │   ↑ caméra vise  └──────────────┘            │
   y=0   └───l'avant─(secteur libre 10–170°)────────────┘
        x=0      x=85 (axe)      x=160          x=220
```

Le secteur balayé (160°) regarde l'avant ; la colonne du portique et toute l'électronique sont
dans le secteur mort arrière. Aucun élément fixe ne traverse le champ caméra ni le cône
ultrason (±15°) sur toute la plage 10–170°.

## 3. Nomenclature et cotes des composants

Cotes constructeur quand elles existent, sinon valeurs typiques **à vérifier au pied à coulisse**
(marquées ✋). Les clones HC-SR04 et modules GY varient d'un lot à l'autre.

| Composant | Cotes (mm) | Source / à vérifier |
|-----------|------------|---------------------|
| BRIO 100 (hors clip) | pilule ≈ Ø32 × 73 ; officiel avec clip : 31,9 H × 72,9 L × 66,6 P | Logitech ; ✋ Ø réel de la pilule et **déport de l'objectif** par rapport au centre |
| Servo MF90 (classe MG90S) | corps 22,8 × 12,2 ; entraxe pattes ≈ 27,5–28, trous Ø2 | ✋ H dessous-flasque→sommet cannelure (H_fa), épaisseur flasque, Ø moyeu palonnier |
| Palonnier simple/croix | bras ≈ 18–19 L, épaisseur ≈ 1,8 | ✋ longueur, épaisseur, Ø moyeu |
| HC-SR04 | PCB 45 × 20 × 1,6 ; transducteurs Ø16,2, saillie ≈ 12 ; entraxe ≈ 26,5 | ✋ entraxe transducteurs, position des trous (souvent 2 × Ø1,8 en coins opposés) |
| Module IMU (GY-9250/6500) | ≈ 15,3 × 25,5, 2 trous Ø3 | ✋ tout : les variantes GY diffèrent |
| Piézo | disque laiton Ø27 × 0,5 typ. | ✋ Ø exact |
| Carte AS5600-SO_EK_AB | petite carte SOIC-8 + header 2 rangées 2,54, **sans trous de fixation** | manuel ams ; ✋ contour PCB à réception |
| Aimant AS5000-MD6H-1 | Ø6 × 2,5, aimanté diamétral | manuel ams |
| Arduino Mega 2560 | 101,6 × 53,3 ; trous Ø3,2 : (13,97 ; 2,54) (96,52 ; 2,54) (15,24 ; 50,8) (96,52 ; 50,8) | standard ; ✋ confirmer sur la carte |
| Breadboard 830 pts | ≈ 165 × 55 | ✋ |

**Checklist de mesures avant d'ouvrir Fusion** : Ø et longueur de la pilule BRIO + déport
objectif ; H_fa, flasque et palonnier du servo ; entraxe transducteurs et trous HC-SR04 ;
contour et trous du module IMU ; Ø piézo. Dix minutes de pied à coulisse économisent trois
réimpressions.

## 4. Conception détaillée par sous-ensemble

### 4.1 Tour servo (B) et interface de rotation

Principe : **le servo entraîne, la structure porte**. En v0.1, tout le poids et les tapotements
passent par les pignons du servo. Ici la tête repose sur une piste circulaire imprimée ; le
palonnier ne transmet que le couple.

- Tour cylindrique Ø70, hauteur 60 jusqu'au plan de piste, vissée au plateau (4 × M3 + écrous
  noyés sous le plateau). Imprimée debout.
- Poche servo ouverte par le haut, axe de sortie **confondu avec l'axe du cou** (attention :
  l'arbre du MF90 est déporté vers une extrémité du corps, le corps est donc excentré dans la
  tour). Poche : 23,3 × 12,7 (jeu 0,25/côté), siège de flasque, 2 × M2 autotaraudeuses (avant-trous
  Ø1,8). Canal latéral 6 × 4 pour la nappe servo, sortie en pied de tour.
- Position verticale du servo : sommet du moyeu de palonnier 0,5 mm **sous** le plan de piste,
  pour que la charge axiale aille sur la piste et jamais sur l'arbre. Cote pilotée par le
  paramètre `H_fa` mesuré.
- Piste annulaire : OD 64, ID 40, **surélevée de 8 mm sur un fût Ø58** — la jupe de centrage de
  la tête (hauteur 6) enveloppe ainsi le bord de piste sans jamais toucher le corps Ø70 de la
  tour. Face de piste imprimée vers le haut, poncer 400 + graisse silicone ou PTFE.
- Gravure rapporteur 10°–170° (pas de 10°, creux 0,4) sur la face supérieure Ø70 de la tour,
  index triangulaire en bas de jupe : contrôle visuel immédiat et aide à la calibration AS5600.

Charge : tête ≈ 250 g, rayon de friction 26 mm, μ ≈ 0,2 graissé → couple résistant ≈ 0,15 kg·cm,
négligeable devant les 1,8 kg·cm du MF90.

### 4.2 Tête mobile (C)

Plaque de base Ø80, épaisseur 4, et en sous-face :

- **3 patins** 8 × 6 × 1 à 120° sur PCD 52, qui glissent sur la piste (moins de friction et de
  bruit qu'un contact annulaire complet) ;
- **jupe de centrage** : anneau descendant ID 64,6 / hauteur 6 / paroi 2,4, qui enveloppe la
  piste OD 64 (jeu 0,3 par côté) — c'est elle qui assure la concentricité, pas l'arbre du servo ;
- **poche palonnier** centrale : empreinte du bras (jeu 0,2/côté), lamage moyeu, trou d'accès Ø6
  traversant pour la vis centrale M2, et 2 trous de passage Ø2,2 dans la plaque : des vis M2
  viennent mordre dans les trous Ø1 d'extrémité du palonnier nylon (rétention positive —
  indispensable pour les tapotements piézo).

Au-dessus de la plaque :

- **Colonnes arrière** : 2 × 10 × 10 mm à x = ±20, y = +22, jusqu'à z = 92 (congés 3 mm en pied).
- **Berceau caméra** : selle R16,2 (paramètre `d_pilule`), centre de la pilule à z = 100, pièce
  séparée vissée sur les colonnes (2 × M3) avec **lumières ±8 mm en x** : on centre l'**objectif**
  (pas le corps) sur l'axe du cou. Bénéfice majeur : le point optique sur l'axe rend le
  panoramique équivalent à une rotation pure de caméra — l'image se transforme par homographie
  indépendante de la profondeur de la scène, ce qui simplifie la prédiction visuelle (JEPA) et
  élimine la parallaxe. Contrepartie assumée : le corps déporté de `offset_objectif` porte le
  rayon de giration à ≈ 54 mm. Sangle imprimée ou velcro 20 mm dans deux fentes 22 × 3.
  Imprimer le berceau sur le dos (selle verticale) pour un état de surface propre sans supports.
- **Clip HC-SR04** : au-dessus de la caméra, PCB vertical face à l'avant, centres transducteurs à
  z = 130, point médian entre transducteurs sur le plan de l'axe. Maintien par 2 rails latéraux
  (fente 1,85 pour PCB 1,6, profondeur 3) + clip de retenue supérieur imprimé. Pas de vis : les
  trous des clones ne sont pas fiables.
- **Étagère IMU** : console latérale droite (x ≈ 12–38, y ≈ 18–40, z global ≈ 78–82),
  lumières 3,4 × 8 pour 2 × M3 + écrous — la face arrière de l'épine est réservée à la goulotte
  câble. Rester près de l'axe (le gyro Z est insensible à la position, mais les accéléros
  captent l'accélération centripète ∝ rayon ; consigner `r_IMU` dans la config). Graver une
  flèche `+X avant / +Z haut` et consigner l'orientation retenue dans la config logicielle.
- **Piézo couplé** : poche circulaire Ø27,4 × 1,0 de profondeur sur le dessus de la plaque, zone
  **avant-droite** (centre ≈ x +14 ; y −18 — l'arrière est pris par la descente de câble),
  disque plaqué par un **anneau clipsé à 3 crochets** avec joint mousse 1 mm (pas de vis : zone
  peu accessible sous la pilule). Le disque est ainsi précontraint contre la pièce la plus
  rigide de la tête : tout tapotement sur la structure se propage. Canal de 2 mm pour les fils.
- **Mât aimant** : poutre 12 × 8 partant des colonnes, contournant le HC-SR04 par l'arrière,
  finissant en plateforme 16 × 16 dont le centre est **exactement sur l'axe du cou**, face
  supérieure z = 150. Poche aimant Ø6,1 (à valider par coupon, voir §5) × 2,0 de profondeur :
  l'aimant dépasse de 0,5 mm. Serrage doux démontable — pas de colle avant validation AGC,
  conformément à `HARDWARE_PURCHASES.md`. PLA = support non ferromagnétique : conforme.

### 4.3 Portique AS5600 (D)

- Colonne 30 × 30, **face interne à 65 mm de l'axe** (y = 115 en coordonnées plateau), soit
  ≈ 11 mm de marge sur le rayon de giration maxi de la tête (≈ 54 mm, objectif centré). Marge
  volontairement serrée : à confirmer par l'étude de mouvement Fusion avant impression. Hauteur
  190, vissée au plateau (4 × M3), goussets 45° en pied.
- Bras 16 × 12 en porte-à-faux vers l'avant (~75 mm) jusqu'à l'axe. Imprimé à plat couché sur le
  flanc : les couches travaillent dans le bon sens en flexion. Flèche et fluage négligeables à
  vide avec cette section.
- Fixation bras/colonne par 2 × M3 dans des **lumières verticales 3,4 × 10** : réglage Z grossier
  ±5 mm. Cales imprimées 0,5 et 1,0 mm pour le réglage fin de l'entrefer.
- **Berceau capteur** sous l'extrémité du bras : cadre à rails pour les chants du PCB (fente 1,85),
  carte **composants vers le bas**, le centre du boîtier SOIC-8 (= centre de mesure Hall) sur
  l'axe. Fixation au bras par 2 × M3 dans des **lumières croisées ±3 mm en X et Y** : centrage
  fin au montage. Fenêtre dégagée sous le SOIC-8.
- Chaîne d'entrefer : aimant affleurant à z = 150,5 ; entrefer visé 1,5 (milieu de plage) →
  face du boîtier à z = 152,0. La plage de réglage Z (±5 + cales) couvre largement 0,5–2,5.
- Peigne de câbles sur la colonne à z ≈ 120 : la boucle de service du faisceau mobile y est
  ancrée.

### 4.4 Plateau (A) et gestion des câbles

- 220 × 210 × 6, congés R10 aux coins, chanfrein 0,4 × 45° en sous-face (pied d'éléphant). Si la
  marge sur le plateau de l'imprimante est insuffisante, version en 2 pièces jointes par queue
  d'aronde + 4 × M3.
- 4 pieds : lamages Ø12 × 1 pour patins adhésifs caoutchouc.
- Tour à l'axe (85 ; 50). Aux angles extrêmes, l'extrémité de la pilule déborde de ~4 mm au-dessus
  du bord avant (z ≈ 100) : sans conséquence, documenté. Mega 2560 **verticale** (USB vers la
  droite) sur 4 entretoises imprimées Ø7 × 6 avec avant-trous Ø2,8 (M3 autotaraudées), zone
  x = 160–215, y = 15–117. Breadboard collée dans un lamage 166 × 56 × 1 le long du bord arrière
  (y ≈ 150–206). Grille de fentes zip-tie 4 × 2,5 au pas de 25 dans les zones libres + 2 ancrages
  pour les Wago.
- **Faisceau mobile** (HC-SR04 4 fils, IMU 4–8 fils, piézo 2 fils, USB caméra) : **goulotte en U**
  (10 × 8, ouverte, à ponts clipsants) sur la face arrière de l'épine, centrée en x = 0 —
  descente verticale de z global ≈ 100 à ≈ 68, soit à ~30 mm de l'axe seulement : les fils se
  tordent au lieu de balayer, le couple parasite est minimal et quasi constant. **Bossage
  zip-tie en pied de descente** : c'est lui qui découple la raideur du câble USB de la tête
  (sinon effet ressort visible sur l'IMU). Boucle de service pendante (rayon ≥ 40 mm) vers le
  peigne de la colonne, abaissé à z ≈ 60–80. Vérifier la liberté sur 10–170° avant de serrer
  les zip-ties. C'était le principal défaut mécanique de la v0.1 (câble USB raide tirant sur la
  tête). Détail complet : `BENCH_HEAD_ONSHAPE.md` §2.

## 5. Jeux fonctionnels, tolérances et rétractation PLA (classe Ender)

Stratégie : **ne pas appliquer d'échelle globale** de compensation. La rétractation du PLA
(0,2–0,4 % linéaire) vaut 0,13–0,26 mm sur le Ø64 de la piste : on l'absorbe dans les classes de
jeu ci-dessous, et on valide les ajustements critiques par un **coupon de test** avant de lancer
les grosses pièces.

| Classe | Jeu par côté | Interfaces concernées |
|--------|--------------|----------------------|
| Pressé (démontable) | 0,05–0,08 | poche aimant Ø6 (coupon : 6,0 / 6,05 / 6,1 / 6,15 / 6,2) |
| Serré | 0,15 | empreinte palonnier (0,2), clips |
| Logement PCB/composant | 0,25 | poche servo, contour HC-SR04/IMU/AS5600, berceau pilule |
| Glissant mobile | 0,30 | jupe Ø64,6 sur piste Ø64 |
| Fente PCB 1,6 | 1,85 de large | rails HC-SR04 et AS5600 |

Perçages et visserie :

| Usage | Ø trou |
|-------|--------|
| Passage M3 | 3,4 (lumières : 3,4 × longueur) |
| M3 autotaraudée dans PLA | 2,8 — prévoir 3–4 périmètres autour |
| M2 autotaraudée (servo, palonnier) | 1,8 (palonnier : 1,6) |
| Logement écrou M3 | 5,7 entre-plats × 2,6 |

Règles d'impression spécifiques Ender :

- trous verticaux : +0,1 à +0,2 sur le Ø nominal (polygonisation + rétraction) ; trous
  horizontaux : forme goutte d'eau ou pontage + perçage de reprise ;
- chanfrein 0,4 × 45° sur **toutes** les arêtes en contact avec le plateau (pied d'éléphant) ;
- pièces structurelles (tour, colonne, bras) : 4 périmètres, infill gyroïde 30–40 %, 0,2 mm ;
- piste et patins : face de glissement imprimée vers le haut, ponçage 400, graisse silicone ;
- pas de précontrainte permanente sur le PLA (fluage) : le seul élément précontraint est le
  piézo, via mousse, pas via le plastique ;
- coupon de test (à imprimer en premier, ~20 min) : plaquette portant la gamme de poches aimant,
  une fente 1,85, un secteur de piste/jupe de 20 mm, un coin de poche servo et des piges Ø3/Ø6.
  Mesurer, ajuster les paramètres utilisateur, relancer.

## 6. Paramètres utilisateur Fusion 360

À créer dans Modifier → Changer les paramètres avant toute esquisse. Tout le dossier est cotable
à partir d'eux.

| Paramètre | Valeur initiale | Commentaire |
|-----------|-----------------|-------------|
| `jeu_presse` | 0,06 mm | à caler par coupon |
| `jeu_serre` | 0,15 mm | |
| `jeu_pcb` | 0,25 mm | |
| `jeu_mobile` | 0,30 mm | |
| `fente_pcb` | 1,85 mm | |
| `d_pilule` | 32,0 mm | ✋ mesure BRIO |
| `l_pilule` | 73,0 mm | ✋ |
| `offset_objectif` | 15,0 mm | ✋ déport lentille/centre |
| `H_fa` | — | ✋ servo : dessous-flasque → sommet cannelure |
| `z_piste` | 60 mm | plan de glissement |
| `z_cam` | 100 mm | axe optique |
| `z_us` | 130 mm | centres transducteurs |
| `z_aimant` | 150 mm | face plateforme mât |
| `entrefer` | 1,5 mm | cible AS5600, plage 0,5–2,5 |
| `d_piste_ext` / `d_piste_int` | 64 / 40 mm | |
| `d_aimant` | 6,0 mm | poche = `d_aimant + 2*jeu_presse` |
| `encombrement_cam_L` | 120 mm ✋ | zone d'exclusion caméra (charnière **repliée** — voir `BENCH_HEAD_ONSHAPE.md` §3) |
| `largeur_guide_cable` | 10 mm | goulotte USB en U sur la face arrière de l'épine |
| `d_cable` | 4 mm ✋ | Ø câble BRIO ; lèvre des ponts clipsants = `d_cable − 0,5` |

## 7. Ordre de modélisation recommandé (Fusion 360 / Onshape)

> Note 2026-06-13 : la modélisation se fait finalement sous **Onshape**. La stratégie détaillée
> de la tête mobile (corps unique, outils d'évidement, goulotte câble) est dans
> `BENCH_HEAD_ONSHAPE.md` ; les principes ci-dessous restent valables pour la tour et le portique.

1. Composant racine `squelette` : esquisse de dessus (implantation plateau, position d'axe) +
   esquisse de côté (étages z) + axe de construction vertical « cou ». Aucun corps.
2. Composants dérivés du squelette : `plateau`, `tour`, `tete_plaque`, `berceau_cam`,
   `clip_us`, `mat_aimant`, `portique`, `berceau_as5600`, `accessoires`. Toute cote = paramètre
   ou projection du squelette ; jamais de valeur en dur dans les poches.
3. Liaison pivot tour/tête sur l'axe cou, limites −80°/+80° autour du neutre (= 10–170°).
4. Étude de mouvement : balayage complet, contrôle d'interférence à 10°, 90°, 170° (tête vs
   colonne, câbles, bras du portique).
5. Analyse de section dans le plan de l'axe : vérifier visuellement la chaîne aimant/entrefer/
   capteur et le jeu piste/jupe.
6. Export STL pièce par pièce. Orientations : tour et colonne debout ; plaque de tête à plat ;
   berceau sur le dos ; bras couché sur le flanc ; capuchons et anneaux à plat.

## 8. Plan d'impression, assemblage et validation

Ordre : coupon → ajustement paramètres → accessoires + berceaux (petits, rapides, ce sont eux
qui portent les ajustements critiques) → tête → tour → portique → plateau (le plus long, ~6–8 h).

Assemblage :

1. Servo alimenté, commande au neutre 90° **avant** montage du palonnier ; monter le palonnier
   perpendiculaire à l'avant, visser la vis centrale.
2. Tour sur plateau, servo dans la tour, nappe dans le canal.
3. Tête posée sur la piste, poche sur palonnier, 2 × M2 de rétention. Vérifier à la main le
   glissement doux sur 160° servo hors tension.
4. Capteurs : caméra centrée objectif-sur-axe (lumières), HC-SR04 dans ses rails, IMU orientée
   et notée, piézo serré sous son anneau. Faisceau : peigne du mât → boucle → peigne colonne.
5. AS5600 : aimant pressé dans le capuchon, berceau sur le bras, entrefer ≈ 1,5 à la cale.
   Balayer 10–170° par pas de 10° en lisant le **registre AGC** : viser le milieu de plage,
   stable sur toute la course ; sinon corriger XY (lumières) puis Z (cales). Seulement après :
   point de colle éventuel, conformément à P-001.
6. Qualification J0 : séquence `90 → 80 → 100 → 90` du runbook, tapotement sur la plaque de
   tête (zone piézo) — le couplage mécanique doit maintenant produire une signature nette à 20 Hz.

Critères de réception du banc : aucun jeu perceptible tête/piste ; AGC en milieu de plage sur
10–170° ; pas de variation du couple câble visible dans `SERVO_STATE` ; piézo réagissant au
tapotement structurel sans contact direct du disque ; rapport `j0 mechanics` avec ratio de
stabilisation gyroscopique inférieur ou égal à 3,0 pour chaque déplacement ; aucune oscillation
visible persistante une seconde après la consigne.

## 9. Références

- [Spécifications Logitech Brio 100](https://support.logi.com/hc/en-gb/articles/16131342728471-Specification-Brio-100-Webcam)
- [Datasheet MG90S (Tower Pro)](https://www.electronicoscaldas.com/datasheet/MG90S_Tower-Pro.pdf)
- [Datasheet HC-SR04 (Sparkfun/Elecfreaks)](https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf)
- [Manuel d'utilisation AS5600-SO_EK_AB (ams OSRAM)](https://look.ams-osram.com/m/4f8342513a447495/original/AS5600_UG000254_2-00.pdf)
- `HARDWARE_PURCHASES.md` (P-001), `J0_PROTOCOL.md`, `J0_RUNBOOK.md`, `DEVELOPMENTAL_ARCHITECTURE.md`
