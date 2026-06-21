# Émergence — Tête mobile (C) : stratégie de modélisation Onshape

Dernière mise à jour : 2026-06-13
Statut : `guide de modélisation — corps unique`
Référence : `BENCH_DESIGN.md` §4.2 (cotes générales), §5 (jeux), §6 (paramètres)

## 0. Philosophie de construction

Un corps unique, léger et rigide, ne se modélise pas en empilant des features au fil de l'eau.
La stratégie est en trois temps :

1. **Corps additif** : un volume simple, massif, construit à partir de deux esquisses maîtresses.
   On ne se préoccupe ni des capteurs ni du câble — seulement de la structure porteuse.
2. **Outils d'évidement** : chaque élément à loger (pilule, palonnier, câble, aimant, piézo)
   est modélisé comme un **corps séparé** représentant son encombrement réel + jeu. Une
   soustraction booléenne unique creuse tous les logements. Avantage décisif : si une mesure
   au pied à coulisse change, on modifie l'outil, la booléenne se rejoue, la pièce reste saine.
3. **Allègement dirigé** : poches calibrées et nervures — pas de Coque globale (verdict en §7).

### Repère et origine — la décision la plus importante

Placez l'**origine de la Part Studio à l'intersection de l'axe du cou et du plan de piste** :

- axe **Z** = axe du cou (rotation) ;
- **+Y** = vers l'arrière (côté épine, portique) ; **−Y** = direction de visée caméra ;
- **+X** = côté où le corps de la pilule est déporté (l'objectif reste à X = 0) ;
- plan **Top** = plan de piste ; **Right** (X = 0) = plan de symétrie structurelle ;
- correspondance avec le dossier : `z_local = z_global − 60`. Donc plaque 0→4, axe caméra 40,
  transducteurs 70, plateforme aimant 90.

Tout devient lisible : la selle est à `#z_cam`, l'aimant à `(0 ; 0 ; #z_aimant)`, la jupe à
`#d_piste_ext/2 + #jeu_mobile`. Posez un **Mate connector** explicite sur l'origine : ce sera la
liaison pivot de l'assemblage.

## 1. Variables (Variable Studio)

Créez un Variable Studio `params_banc` (réutilisable par la tour et le portique) :

| Variable | Valeur | Rôle |
|----------|--------|------|
| `#jeu_presse` / `#jeu_serre` / `#jeu_pcb` / `#jeu_mobile` | 0,06 / 0,15 / 0,25 / 0,30 | classes d'ajustement (coupon !) |
| `#fente_pcb` | 1,85 | rails HC-SR04 |
| `#d_piste_ext` / `#d_piste_int` | 64 / 40 | interface tour |
| `#d_plaque` / `#ep_plaque` | 80 / 4 | plaque de base |
| `#h_jupe` / `#ep_jupe` | 6 / 2,4 | jupe de centrage |
| `#z_cam` / `#z_us` / `#z_aimant` | 40 / 70 / 90 | étages (repère local) |
| `#d_pilule` / `#l_pilule` / `#offset_objectif` | 32 / 73 / 15 — ✋ tous trois | BRIO 100 |
| `#encombrement_cam_L` | 120 ✋ | zone d'exclusion caméra (X) |
| `#encombrement_cam_P` / `#encombrement_cam_H` | 70 ✋ / 40 ✋ | zone d'exclusion (Y, Z) |
| `#largeur_guide_cable` / `#prof_guide_cable` | 10 / 8 | goulotte USB |
| `#d_cable` | 4 ✋ | Ø câble BRIO (lèvre de clip = `#d_cable − 0,5`) |
| `#largeur_epine` | 20 | épaisseur de l'épine dorsale |
| `#ep_paroi` | 2,4 | parois minces (3 périmètres × 0,4 + marge) |
| `#d_aimant` | 6,0 | poche = `#d_aimant + 2*#jeu_presse` |

## 2. Le câble USB : pourquoi pas le centre exact, et où alors

Votre instinct est le bon — un câble qui plonge **sur** l'axe ne subit que de la torsion lors du
balayage, donc un couple parasite quasi nul et constant. Mais l'axe est occupé à ses deux
extrémités : l'arbre du servo en dessous (z < 0), l'aimant + AS5600 au-dessus (z = 90, entrefer
sanctuarisé par P-001). Y faire passer un câble USB est exclu.

La solution retenue — quasi équivalente mécaniquement :

- **goulotte en U** (`#largeur_guide_cable` × `#prof_guide_cable`, ouverte, à ponts) qui part de
  la sortie du câble derrière la pilule (✋ repérer le point exact de sortie), contourne le flanc
  droit de l'épine et rejoint la **face arrière de l'épine, à X = 0** ;
- **descente verticale** dans cette goulotte de z ≈ 40 à z ≈ 8 : le câble plonge centré en X,
  à un rayon de seulement ~30 mm de l'axe ;
- **ancrage zip-tie** sur un bossage en pied de descente : c'est lui qui découple — toute la
  raideur du câble en amont est reprise par la structure, plus rien ne « ressorte » sur l'IMU ;
- sortie basse vers une **boucle pendante** rejoignant le peigne de la colonne du portique,
  abaissé à z global ≈ 60–80.

Ordre de grandeur : à r = 30 mm, l'extrémité balaye ~84 mm d'arc sur 160°. Avec une boucle de
service de 100 mm et un câble Ø4, le couple résiduel est de quelques N·mm, lisse et sans
hystérésis — invisible pour le gyro une fois le zip serré. À valider en qualification : balayage
lent 10→170° en enregistrant `SERVO_STATE` + IMU.

Conséquences d'implantation (reportées dans `BENCH_DESIGN.md`) : le **piézo** migre en zone
avant-droite de la plaque (centre ≈ (+14 ; −18), anneau **clipsé** à 3 crochets — plus de vis
sous la caméra) ; l'**étagère IMU** passe en console latérale droite (x ≈ 12–38, y ≈ 18–40,
z ≈ 18–22), dégageant la face arrière pour la goulotte.

## 3. Zone d'exclusion caméra — sémantique et avertissement

La zone d'exclusion est un **volume interdit au plastique**, pas un volume balayé : boîte de
`#encombrement_cam_L` × `#encombrement_cam_P` × `#encombrement_cam_H` centrée sur l'axe optique,
étendue en X de `−(#encombrement_cam_L/2 − #offset_objectif)` à
`+(#encombrement_cam_L/2 + #offset_objectif)`.

⚠ **Charnière dépliée = collision.** Si la charnière/clip arrière pend dépliée, le coin de la
zone balaye un rayon ≈ √(70² + 35²) ≈ 78 mm > 65 mm de garde de la colonne du portique : impact
garanti entre 10° et 170°. Deux issues : **(a) recommandé** — charnière repliée sous la pilule,
capturée par la selle (elle participe au serrage, comme en v0.1) ; le rayon de giration reste
≈ 54 mm ; **(b)** reculer la colonne à ≥ 85 mm de l'axe, ce qui pousse le plateau à ~225 de
profondeur — hors lit d'impression Ender. Le guide suppose (a).

## 4. Marche à suivre — arbre de construction

Nommez chaque feature comme ci-dessous ; l'arbre restera lisible dans six mois.

### P1 — Esquisses maîtresses (aucun volume)

1. `esq_layout_top` (plan Top) : cercles construction Ø`#d_piste_int`/`#d_piste_ext`/jupe/
   `#d_plaque` ; rectangle épine (X ± `#largeur_epine`/2, Y 22→30) ; point cheminée (0 ; 32) ;
   PCD 52 des patins ; centre piézo (+14 ; −18) ; emprise IMU ; rectangle construction de la
   zone d'exclusion caméra.
2. `esq_layout_cote` (plan Right) : lignes de niveau 0, `#ep_plaque`, `#z_cam`, `#z_us`,
   `#z_aimant` ; cercle pilule Ø`#d_pilule` en (0 ; `#z_cam`) ; profil construction de l'épine
   en C ; trajet construction du câble (descente X = 0 comprise).

Règle d'or : **toute cote vient d'une variable ou d'une projection de ces deux esquisses.**
Aucune valeur en dur dans les features aval (`Use`/projection plutôt que recotation).

### P2 — Corps additif (booléennes en « Add » sur un seul corps)

3. `rev_plaque_jupe` — Revolve 360° (profil sur Right) : plaque r 0→40 × z 0→4 **+** jupe
   anneau r `32,3 + #jeu_mobile` → `+ #ep_jupe`, z −`#h_jupe`→0. Un seul profil, une feature.
4. `ext_patins` — 3 patins 8 × 6 × 1 extrudés vers le bas depuis z = 0 sur PCD 52 +
   **Circular pattern** ×3 autour de Z. La tête repose sur eux, pas sur la plaque.
5. `ext_epine` — profil en **C** sur Right, extrusion symétrique `#largeur_epine` : pied
   (Y 10→38, z 4→12) fusionné à la plaque ; montant (Y 22→30, z 4→90) ; porte-à-faux
   plateforme (Y −8→30, z 83→90). Une seule feature = colonnes + mât + plateforme.
6. `ext_selle` — bloc selle sur Right (Y −16→16, z 26→40), extrusion asymétrique X −25 / +55
   (le corps de pilule est déporté de `#offset_objectif`) + voiles de liaison vers le montant
   (Y 16→22). Puis `cut_selle` : cercle Ø`#d_pilule + 2*#jeu_pcb` en (Y 0 ; z `#z_cam`) sur
   Right, Extrude **Remove** traversant des deux côtés → la selle naît du cylindre soustrait.
7. `ext_lunette_us` — depuis un plan offset z = 58, cadre en U autour de l'emprise PCB
   (45 × 1,6 + jeux), bras raccordés aux flancs de l'épine, extrusion 24 vers le haut.
8. `ext_goulotte` — parois du U sur la face arrière (X ± (`#largeur_guide_cable`/2 →
   + `#ep_paroi`), Y 30→38, z 8→40) + entonnoir d'entrée sur le flanc droit + 2 **ponts** de
   fermeture (largeur 4, ouverture `#d_cable − 0,5` : le câble se clipse).
9. `ext_bossage_zip` — bossage (0 ; 36→44 ; 6→14) percé de 2 fentes 3 × 2 pour le zip-tie.
10. `ext_etagere_imu` — console (X 12→38, Y 18→40, z 18→22) sur le flanc droit, 2 lumières
    3,4 × 8.

### P3 — Outils d'évidement (booléennes « New », puis une soustraction)

11. `outil_pilule` — cylindre Ø`#d_pilule + 2*#jeu_pcb`, longueur `#l_pilule + 2`, axe X en
    (Y 0 ; z `#z_cam`) **+** boîte « charnière repliée » sous/derrière la pilule (✋ mesurer la
    charnière pliée). 
12. `outil_palonnier` — sous la plaque : empreinte bras 20 × 6 × 2,2 + lamage moyeu Ø7,4 × 4,5
    + accès vis Ø6 traversant + 2 passages Ø2,2.
13. `outil_cable` — **Sweep** d'un disque Ø`#d_cable + 1` le long du trajet construction de
    `esq_layout_cote` (rayons de courbure ≥ 15 — un USB n'aime pas plier court).
14. `outil_aimant` — cylindre Ø`#d_aimant + 2*#jeu_presse` × 2,0 sous la face z = `#z_aimant`,
    centré (0 ; 0) — exactement sur l'axe.
15. `outil_piezo` — galette Ø27,4 × 1,0 en (+14 ; −18) sur la plaque + canal 2 mm vers la
    goulotte pour les deux fils.
16. `bool_evidements` — **Boolean Subtract** : corps cible = tête ; outils = 11→15 (décocher
    « Keep tools » sauf si vous voulez les conserver pour les vérifs — recommandé : les garder
    dans un dossier `outils`, masqués).

### P4 — Allègement et rigidité

17. `cut_poches_epine` — poches dans les flancs du montant : profondeur
    `(#largeur_epine − 2*#ep_paroi)/2` par face, en laissant un cadre périphérique de 6 mm →
    section en I, ~40 % de matière en moins, raideur en flexion quasi intacte.
18. `rib_goussets` — feature **Rib** (3 esquisses d'une ligne chacune) : plaque→face avant du
    montant (X = 0, la face arrière est prise par la goulotte) ; plaque→flancs (X = ±10) ;
    sous le porte-à-faux (Y 22→−2, z 76→83 — vérifier la garde avec le sommet du PCB US à 80).
19. `fillet_chamfer` — congés 3 aux pieds de nervures et jonctions selle/épine ; chanfreins
    0,4 × 45° sur **toutes** les arêtes z = −7 (jupe) et patins ; **dépouille 45° sous le
    porte-à-faux** de la plateforme pour imprimer sans supports.

### P5 — Vérifications avant export

20. Vue en coupe sur Right : chaîne z complète (selle/pilule, garde plateforme↔PCB US ≥ 3,
    goulotte continue, poche aimant).
21. `esq_verif_giration` : cercle construction **R 65** sur Top — aucune arête de la tête ne
    doit le franchir (R 54 attendu pilule comprise).
22. Interférence : Boolean **Intersect** temporaire entre une copie de la tête et
    `outil_pilule` étendu à la zone d'exclusion complète → l'erreur « zéro corps » est le
    succès ; supprimez la feature ensuite.
23. Propriétés de masse (PLA 1,24 g/cm³) : viser ≤ 60 cm³ de solide (~50 g imprimé en 0,2 mm).
24. Export STL : **plaque à plat sur le lit**, épine vers le haut. Supports normalement
    inutiles si la dépouille de 19 est en place ; ponts de goulotte ≤ 10 mm = pontage sain.

## 5. Verdict Coque (Shell)

**Non — pas de Coque globale.** Trois raisons : (a) après les booléennes, la topologie est trop
riche, la Coque échoue ou crée des parois orphelines au moindre changement de cote ; (b) une
cavité fermée est non imprimable proprement (supports internes inaccessibles) ; (c) on perd le
contrôle local de la rigidité. La paroi mince **par construction** (poches 17 + nervures 18)
donne le même gain de masse, en restant paramétrique et imprimable. La Coque reste pertinente
sur un volume convexe simple — ce n'est pas le cas ici.

## 6. Pièges Onshape spécifiques

- extrusion asymétrique de la selle : utilisez deux directions « Blind » (25 / 55), pas
  « Symmetric » — c'est le déport d'objectif qui l'exige ;
- le **Rib** Onshape veut une esquisse ouverte (une ligne) dans un plan sécant aux deux faces ;
- les booléennes référencent des corps, pas des features : nommez les corps (`tête`,
  `outil_*`) dès leur création (clic droit → Rename) ;
- gardez `esq_layout_*` en tête d'arbre et ne cotez **jamais** une feature aval sur une arête
  de corps (fragile au rejeu) — toujours sur les esquisses maîtresses ;
- dérivez `params_banc` aussi dans les Part Studios tour/portique : un seul point de vérité.
