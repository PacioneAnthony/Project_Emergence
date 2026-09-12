# Émergence — Handoff de session

Date : 2026-09-12.

Ce document dit **comment reprendre** et **ce qui a déjà été essayé**, campagne par
campagne. L'état courant — décision active, acquis, fermetures, actions par acteur — est
dans `PILOTAGE.md` et n'est pas répété ici.

## Reprendre ici

Lire dans cet ordre, et rien de plus pour démarrer :

1. `PILOTAGE.md` — état courant et règles permanentes
2. `CODEX_TASK_BRIEF.md` — le prompt de la phase ouverte par D-060
3. `PROPOSITION_SUBSTRAT.md` — l'argumentaire du changement de substrat
4. `DECISIONS.md` — D-060, D-061 et D-062
5. `DEVELOPMENTAL_ARCHITECTURE.md` — le cadrage D-056

Le détail d'une campagne close se lit à la demande : chaque entrée de l'historique
ci-dessous nomme son rapport. Il n'y a pas de lecture préalable obligatoire au-delà des
cinq documents ci-dessus.

Ordre de travail, arrêt à la première porte rouge : ajouter l'articulation d'inclinaison et
son contrat d'observation dans `sim3d/bench_model.py` et `sim3d/bench_env.py` ; construire
la tâche C1 — retrouver un objet désigné par son apparence ; écrire le seuil de marge ;
exécuter la sonde contre le témoin trivial et une borne supérieure ; publier ses deux
chiffres. **Aucun mécanisme cognitif, aucun pré-enregistrement et aucune banque de
confirmation avant que cette marge existe.** Si elle n'existe pas, le substrat est déclaré
épuisé et on n'y construit rien.

### Étape 1 — faite le 11 septembre 2026

L'axe d'inclinaison existe. `sim3d/bench2_model.py` et `sim3d/bench2_env.py` **étendent**
le banc gelé sans le toucher : ses octets sont référencés par 116 et 112 manifestes, donc
`build_bench2_mjcf` transforme le MJCF que produit `build_bench_mjcf` au lieu de le
réécrire, sur des ancres vérifiées une à une — si le banc gelé changeait, la construction
échouerait bruyamment au lieu de rendre un monde à un axe.

Ce qui est vérifié, pas affirmé :

- **grille 5 × 3 = 15 cellules**, centres espacés d'exactement un champ de 30° ;
- **à tilt nul, le rendu est identique au pixel près au banc gelé** sur toute la course de
  panoramique — le monde à deux axes diffère de l'ancien par la charnière et par rien
  d'autre ;
- **les 15 cellules sont distinctes** : identification au plus proche voisin 15/15 sur cinq
  pièces, marge entre 2,1× et 9,7× l'écart d'une cellule avec elle-même ;
- **la charnière ne s'affaisse pas** : elle passe par le barillet, donc le corps mobile est
  équilibré. Articulée au niveau de l'objectif, elle pendait de 0,101° sous les 90 g de la
  caméra et le rendu à tilt nul n'était plus identique.

Deux pièges rencontrés, tous deux verrouillés par un test : le signe du tilt — l'axe naïf
`0 1 0` fait descendre la vue quand on commande une valeur positive, l'axe est donc
`0 -1 0` — et l'affaissement ci-dessus.

Vérification reproductible : `python -m scripts.research.bench2_cells --sheet out.png`.
Planche des 15 cellules : `docs/research/bench2_view_grid.png`.

**Réserve pour l'étape 2.** Les 15 cellules sont distinctes, mais le contenu de la pièce
est dans la seule rangée centrale : à +30° on voit le mur haut et le ciel, à −30° le
plateau uni de la table, contraste 26 contre 46 au centre. Une cible C1 hors rangée
centrale serait invisible. C'est la faute de faisabilité de REF-002 et REF-003 ; elle se
traite en ajoutant du contenu par le paramètre `wall_panels`, sans toucher au banc gelé.

### Étape 2 — faite le 11 septembre 2026

Le contenu d'abord. `sim3d/bench2_content.py` place un objet là où le rayon central d'une
cellule rencontre la pièce — le plateau de la table juste devant la tête, le sol au-delà,
ou un mur — toujours par le paramètre `wall_panels` de `build_bench_mjcf`, le banc gelé
restant intact. Les objets sont dimensionnés **en angle** et non en mètres : une cellule
vise une surface à 0,19 m vers le bas et 3,5 m vers le haut, et une taille métrique unique
remplissait la vue en bas pour trois pixels en haut.

`learning/c1_task.py` construit la tâche : exploration des quinze cellules, délai occupé
par d'autres mouvements, puis une image de référence désigne un objet et la tête doit
répondre en pointant sa cellule. Les objets peuvent changer de place entre les deux
visites, avec probabilité réglable.

Trois choix empêchent la tâche d'être résolue pour une mauvaise raison :

- **la référence est rendue sur fond neutre**, pas découpée dans la scène — une référence
  portant son arrière-plan laisserait la comparaison d'images entières répondre sans que
  l'apparence serve jamais, ce qui est exactement ce qui a rendu les baselines de REF-001
  non informatives ;
- **chaque objet est distracteur des autres** : la cible est tirée du même ensemble, donc
  « il y a quelque chose ici » réduit la recherche sans y répondre, et des cellules restent
  vides pour que ne rien voir informe aussi ;
- **la taille apparente ne fuit pas la réponse** : elle varie par rangée, mais elle ne se
  voit qu'après avoir regardé la cellule, et l'image de référence est rendue à distance
  fixe sur fond neutre — elle ne peut rien encoder du placement. C'est un gradient de
  difficulté, pas une réponse offerte. Un test le verrouille.

Mesuré, pas supposé : 14 à 15 cellules utilisables par pièce, **tous les objets placés
visibles**, le pire à 7,3 % de la vue centrale ; les huit références se distinguent deux à
deux ; le brassage déplace bien les objets, 8 fois sur 8.

Trois défauts trouvés en regardant les rendus, tous corrigés et verrouillés par un test :
un rayon vers le bas rencontre le plateau à 17 cm et non le sol, donc tout objet placé au
sol y était caché ; les panneaux muraux posés à plat sont vus de biais et rétrécissent,
donc ils sont désormais orientés vers le banc ; et la branche « sphère » ignorait la
hauteur calculée, ce qui posait toute sphère de la rangée basse sous la table.

**La leçon de REF-003, retrouvée par l'expérience.** Une sonde générique par cellule
attrape l'occultation mais pas le contraste local : un cylindre sombre sur un mur sombre
passe le garde géométrique et reste invisible. Chaque objet est donc mesuré là où il se
trouve réellement, et déplacé avant que l'épisode commence si sa cellule ne le montre pas.
C'est une construction de monde valide, jamais un re-tirage après résultat.

Vérification reproductible : `python -m scripts.research.c1_check`.
Planche de la tâche et des références : `docs/research/c1_task_grid.png`.

### Vue en direct et orientation

`sim3d/bench2_live.py` sert une page locale : vision de la tête, pièce vue de derrière le
robot avec le regard tracé, grille des quinze cellules, état et journal. Lanceur C1 :
`scripts/research/c1_live.py`, configuration `c1-live` dans `.claude/launch.json`. Un
épisode peut recevoir un `observer` — `on_phase` et `on_step` — qui ne doit ni faire
avancer le monde, ni appeler `mj_forward`, ni tirer dans le générateur de l'épisode ; un
test vérifie qu'observer ne change rien. Sous la grille, quatre graphes tracés sur `<canvas>`
sans bibliothèque externe (`sim3d/bench2_live_charts.py`) suivent les épisodes : succès
cumulé avec intervalle de Wilson et mouvements par politique, écart de pointage et
visibilité face à leurs seuils. Une politique garde sa couleur pour de bon — l'oracle ne
sera pas repeint quand les témoins arriveront — et la palette est validée par le script
de visualisation contre le fond réel de la page.

**Orientation, mesurée et non supposée** : un petit pan tourne la tête vers *sa droite*.
Tête à pan 90, un repère au cap 80 apparaît à droite de l'image, au cap 100 à gauche. Vue
comme le robot la voit, la grille a donc le pan *décroissant* de gauche à droite. Les deux
premières planches contact rangeaient le pan croissant et montraient la pièce en miroir ;
elles sont régénérées dans le bon sens.

### Étape 3 — sonde de marge, faite le 11 septembre 2026

Seuils écrits et commités avant tout code (`6cc7252`), sources gelées avant la banque
(`cc5d082`), banque de 60 pièces jouée une seule fois. Faisabilité 54/60 = 90,0 %, borne de
Wilson 79,9 % : sous le seuil de 80 %, verdict **REJETÉE — FAISABILITÉ**. Ce n'est pas
l'abandon de D-060 ; c'est la tâche qu'on corrige. Les six échecs de l'oracle perceptif sont
un seul mécanisme, un décalage de teinte entre la référence, rendue sous un autre éclairage,
et la scène : cube orange 0 sur 5, et une fois le vert. Toutes les autres cibles sont lues à
100 %.

Deux bogues trouvés et corrigés en route, avant la banque : le brassage sautait la
vérification de visibilité par objet ; et la correction de ce saut fermait les moteurs de
rendu dans le mauvais ordre, ce qui rendait noire toute image après un brassage.
`release_renderer`, dans `sim3d/bench2_env.py`, règle ce second point partout.

Lanceur : `python -m scripts.research.c1_probe` ; il refuse de rejouer une banque.

### Étape 3, version 2 — faite le 12 septembre 2026

Seuils écrits et commités avant toute ligne de code v2 (`86a03c8`), développement consigné
(`89e0b68`), sources gelées avant la banque (`91cf236`), banque de 200 pièces jouée une seule
fois en 86 s. **Faisabilité 178/200 = 89,0 %**, Wilson [83,9 % ; 92,6 %] : la borne passe
largement, le taux manque de deux pièces. Verdict **REJETÉE — FAISABILITÉ**, et toujours pas
l'abandon de D-060.

Trois corrections étaient pré-enregistrées, et il faut retenir ce que chacune a donné, parce
que deux sur trois ont démenti ce qu'on en attendait :

- **référence rendue sous l'éclairage de la pièce** — effet réel mais insuffisant. Le cube
  orange passe de 0/10 à 4/10 en développement, le vert est réparé, rien ne recule. Dans la
  banque, la référence de l'orange est en classe de teinte 2 et l'objet vu en classe 1, 15
  fois sur 15 : un décalage d'exactement une classe, systématique, que l'éclairage réduit
  sans le refermer ;
- **fenêtre centrale pour les témoins** — **aucun effet mesurable**. Les deux témoins
  marquent à l'identique avec et sans. L'hypothèse du fouillis coloré de l'entrée 3 n'est pas
  soutenue ; la fenêtre est conservée parce qu'elle est inoffensive et conservatrice, et elle
  n'est créditée de rien ;
- **banque portée de 60 à 200 pièces** — a fonctionné exactement comme annoncé. À 60 pièces,
  le dispositif ne pouvait pas passer à sa propre cible.

Un second mécanisme d'échec, que la v1 n'avait jamais consigné : le garde de visibilité
compte les pixels *changés*, le lecteur gelé exige des pixels *saturés*, et un objet peut
passer le premier en laissant le second lire une cellule vide. Mesuré à 1,2 % des objets
placés en développement, il coûte 5 des 22 échecs de la banque. **Il n'a pas été corrigé** :
le réparer aurait augmenté la faisabilité après qu'un chiffre de développement a été vu,
c'est-à-dire dans la direction que la discipline interdit. Il est pré-enregistré comme la
première correction de la v3.

Lanceur : `python -m scripts.research.c1_probe_v2`, qui refuse lui aussi de rejouer une
banque. La v2 étend la v1 sans la toucher : ses modules importent le lecteur, l'oracle et les
seuils gelés au lieu d'en tenir copie, et onze tests le vérifient par identité d'objet.

### Étape 3, version 3 — faite le 12 septembre 2026, **verdict vert**

Seuils avant tout code v3 (`5be9c8b`), développement (`0081425`), gel (`b668872`), banque de
300 pièces jouée une seule fois en 132 s. **Faisabilité 298/300 = 99,3 %**, Wilson
[97,6 % ; 99,8 %] : elle passe. **Marge : MARGE EXPLOITABLE** — mémoire 49,3 %, écart +50,0
points à coût égal ; balayage 88,3 %, écart +11,0 points [BCa +7,7 ; +14,7] pour quinze
mouvements de plus. Le balayage n'établit pas de marge en succès (borne +7,7 sous le seuil de
+10) ; sa marge est celle du coût.

Ce qui a fait la différence, et qui avait été pré-enregistré avant d'être mesuré : **la
palette était le problème, pas la règle.** La tolérance que l'entrée 4 avait pré-enregistrée
a été réfutée par la mesure avant d'être adoptée — lisser l'histogramme ne change rien, une
distance circulaire dégrade — parce que l'orange et le jaune n'étaient séparés que de
1,23 classe quand le décalage de rendu en vaut une. Huit teintes à trois classes d'écart et à
saturation uniforme 0,90 corrigent les deux objets fautifs à la fois, le second pour une
raison arithmétique : le lecteur exige une saturation de 0,45 **après** rendu et le rendu ne
peut que la baisser, or l'ancien magenta partait de 0,588.

Lecture par objet à travers les trois versions : 83,8 % → 91,2 % → **98,8 %**.

**La vérification qui pouvait invalider le verdict vert tient.** Le témoin de mémoire tombe
de 86,3 % à **10,9 %** quand les objets bougent ; le balayage reste stable, 86,3 % puis
90,5 %. La marge vient du mécanisme que la tâche prétend isoler.

**Revue contradictoire rendue** le 12 septembre par GPT Astra (`docs/research/c1_margin_review.md`),
verdict **AUTORISER AVEC CORRECTIONS BLOQUANTES**. Elle a revérifié l'ordre des commits, les
quinze empreintes et tous les chiffres depuis le résultat brut. Rien n'y est rejeté.

### B1 — sonde complémentaire, faite le 12 septembre 2026, **B1 levée**

Seuils avant tout code (`3fbac61`), développement et figeage des variantes (`0acb914`), gel
(`bb1b712`), banque de 100 pièces jouée une seule fois en 79 s, sur `C1EpisodeV3` strictement
inchangé — les quinze empreintes de la v3 sont revérifiées par le manifeste hybride.

Sept règles de vérification pré-enregistrées, quatre non dominées emportées dans la banque, y
compris les deux plus économes qui ressortaient « proches de l'oracle » en développement :
les écarter aurait conservé une marge en coût **par sélection**, ce que la clause de la revue
interdit. Faisabilité 99/100 ; **aucune variante n'est proche de l'oracle** ; verdict
**MARGE EXPLOITABLE**.

Deux mesures comptent plus que le verdict :

- la baseline adaptative **égale le balayage exhaustif pour la moitié du prix**, 90,0 % de
  succès pour 8,02 mouvements contre 15,93. Le coin laissé à un mécanisme vaut donc **+9 points
  et −7 mouvements**, et non le contraste 1 contre 16 de la v3. Sous P1, c'est elle le
  comparateur primaire d'un futur mécanisme ;
- une règle de vérification triviale est déjà un **détecteur de changement quasi parfait** :
  elle accepte dans 90,9 % des pièces stables et 4,4 % des pièces brassées. Les erreurs qui
  restent sont perceptives — les adaptatives font mieux en pièce brassée (93,3 %) qu'en pièce
  stable (87,3 %), où elles héritent des erreurs de lecture de la mémoire.

La caractéristique calculée avant de jouer s'est vérifiée : la marge en coût s'effondrerait
au-delà de 70,4 % d'acceptation, les variantes pivots ont accepté 52 et 53 %, et leur borne
basse projetée de 4,5 est sortie à 5,68 et 5,53.

Lanceur : `python -m scripts.research.c1_probe_hybrid`.

### Pré-enregistrement C1-M1 — écrit le 12 septembre 2026

`docs/research/c1_preregistration.md`, commité avant la première ligne de code du mécanisme.
Hypothèse : deux régularités non exploitées par les comparateurs — l'exclusion mutuelle des
placements et la fiabilité de lecture par apparence — sont apprenables et suffisent à réduire
le coût sans perdre en justesse.

Ce qu'il verrouille : **trois portes** et non une, l'axe de gain déclaré avant la banque,
supériorité à borne basse BCa ≥ 1,5 mouvement ou ≥ +3 points, non-infériorité à borne haute
≤ 2 points et ≤ 0,5 mouvement, intersection sur les trois portes, une banque de 300 pièces
jouée une fois, apprentissage en ligne avec reprise déterministe, et un test de dépendance
bloquant qui falsifie chaque champ privilégié pour prouver que la politique ne le lit pas.

**Une objection portée contre notre propre baseline y est intégrée.** Le repli adaptatif
visite les quatorze cellules restantes sans s'arrêter ; s'arrêter au premier bon appariement
coûterait 4,52 mouvements au lieu de 8,02 et ramènerait la marge contre l'oracle de 7,02 à
3,52. B1 survit, mais cette politique devient la **porte 3**, gelée sur graines de
développement avec la clause des variantes non dominées.

Deux bornes mesurées, écrites avant de concevoir : le placement après brassage est **uniforme**
— rien n'est apprenable sur où un objet est parti — et la détection du changement est **déjà
résolue** par une règle à un seuil, 90,9 % contre 4,4 %. Ce qui reste exploitable est la seule
conduite de la recherche après réfutation.

**Reprendre par la revue contradictoire de ce pré-enregistrement** (D-062), puis seulement par
le mécanisme. Aucun code de mécanisme avant son retour.

La marge en succès, elle, est **perceptive** : le balayage perd 33 pièces en retenant un faux
ami plus ressemblant que la cible, parce qu'il lit une cellule entière là où l'oracle lit les
pixels exacts d'un objet. L'écart oracle–balayage ne mesure donc pas la place d'un mécanisme
mnésique.

Portée resserrée (B2) : le résultat vaut pour C1 v3 à `p(brassage) = 0,5`, palette v3, lecteur
à 24 classes, moteur gelé. Un écart perceptif de 12,4 points subsiste dans les pièces stables.
Changer `p`, la palette, le lecteur, le garde ou le rendu exige une nouvelle sonde de marge.

Un défaut connu et non corrigé, sans conséquence sur la marge : espacer huit teintes à `k/8`
avec 24 classes les place toutes exactement sur une frontière de classe. Les deux seuls
échecs de l'oracle viennent de là. Une v4 décalerait la palette d'une demi-classe ; elle
n'est pas nécessaire.

Lanceur : `python -m scripts.research.c1_probe_v3`.

Réutiliser sans le réécrire : le noyau persistant, `FunctionalStore`,
`learning/paired_stats.py` pour toutes les portes statistiques, `learning/visual_jepa.py`,
et le banc `sim3d/bench_model.py` / `sim3d/bench_env.py`, qui contient déjà la pièce
meublée, les panneaux contrastés, l'éclairage, l'objet externe sur rail, la caméra
embarquée de 30° et son rendu.

État au moment de la reprise : 438 tests verts. Aucun processus, aucune réservation de
budget et aucune simulation ne restent actifs sur les campagnes closes ; leurs registres
`budget.sqlite` sont soldés.

## Règles qui bloquent un commit

- **Octets bruts (D-061).** `.gitattributes` déclare `* -text` : n'ajoute aucun attribut
  `text`, `eol` ni `working-tree-encoding`. Une normalisation de fin de ligne casse en
  silence les empreintes que gèlent les manifestes — le 10 septembre elle a réécrit onze
  sources `.py` et cassé 566 références dans 113 manifestes, toutes restaurées depuis. Si
  une empreinte ne correspond plus, l'anomalie est dans les octets et non dans le
  manifeste : on restaure les octets, on ne recalcule pas l'empreinte.
- **Archive des sources.** Toute source destinée au gel est copiée à côté de ses
  résultats, convention `source_v1`. C'est cette copie qui a rendu six des onze sources
  récupérables sans reconstruction. L'allègement documentaire de D-060 ne la supprime pas.
- **Sources gelées et banques closes.** Ne pas modifier une source gelée puis appeler cela
  une reprise. Ne pas réouvrir une banque consommée, ni régler une recette sur une
  validation déjà dépensée.
- **Graines.** Graines vierges à chaque campagne ; l'unité indépendante est l'organisme ou
  la vie, jamais le tick corrélé.
- **D-008.** Simulation uniquement : aucune action matérielle, aucun flash, aucun achat.

## Historique par campagne

Ordre chronologique par décision. Chaque entrée dit ce qui a été testé, le verdict, et ce
qui reste interdit. Un **non-résultat technique** signifie que l'hypothèse n'a pas été
testée, pas qu'elle est rejetée.

### J6-R001 et J6-AR001 — rejeu adaptatif (jusqu'à D-012)

J6-R001 est clos sans promotion : la valeur de rétention est établie sur B, mais H3
échoue. TV-001 et `regional_lp_gain` sont gelés par D-009.

J6-AR001 a passé sa revue pré-calcul avec quatre amendements bloquants, puis 181 tests et
le smoke 11991. La campagne a atteint le plafond pré-enregistré de 75 minutes pendant le
run `adaptive_replay` de 11313 : 12 triplets complets sur les 16 requis, 11314..11316
jamais ouvertes. D-012 interdit l'extension du plafond, la reprise et toute analyse
partielle. Aucune porte n'a été calculée ; l'hypothèse adaptative reste **non testée**.

Détail : `docs/research/j6_adaptive_replay_001_technical_stop.md`.

### REF-001 — réafférence par résidu conditionné à l'action (D-013 à D-016)

Question : le résidu d'un JEPA conditionné par l'action explique-t-il le mouvement propre
tout en détectant un objet dont le mouvement est externe et indépendant ?

Dispositif gelé avant implémentation : monde REF neuf avec vrai objet MJCF sur rail, RNG
objet distinct, corrélation action–déplacement `≤ 0,05`, `action_jepa` contre
`no_action_jepa` à capacité et calcul identiques, baselines `pixel_change` et
`pixel_change_action` obligatoires, cinq banques disjointes de 128 paires par bin, seuil
calibré uniquement sur le mouvement propre, six tests de supériorité sous Holm commun.

Portes chiffrées avant campagne, sans lesquelles les résultats ci-dessous ne se lisent
pas : H1 avantage d'erreur propre `≥ 0,05` ; H2 et H3 TPR absolue `≥ 0,75` et `≥ 0,70`
avec un avantage `≥ 0,10` face à chaque baseline ; H4 FPR globale `≤ 0,07` et aucun bin
au-dessus de `0,10`. Plafond 32 runs / 60 minutes, sans analyse partielle en cas d'arrêt.

Campagne complète : 16 paires / 32 runs en 31,80 minutes. **Les quatre hypothèses
échouent** — H1 `−0,00182` (IC BCa `[−0,00666 ; 0,00287]`, p `0,757`, 2/6 bins), H2 TPR
externe `0,37077`, H3 TPR mixte `0,14266`, H4 max par bin `0,11865` malgré une FPR globale
`0,06372`. Les gardes apprenant et indépendance passent.

La revue contradictoire a reproduit tous les calculs au chiffre près et a produit quatre
corrections durables : les succès face aux pixels en externe pur sont **non informatifs**
— `pixel_change` y a une TPR exactement nulle par décalage de domaine entre calibration
tête mobile et test tête tenue ; en mixte, `pixel_change = 0,13924` égale
`action_jepa = 0,14266` ; H4 révèle une instabilité réelle (`5/16` graines et `16/96`
cellules au-dessus des plafonds) ; la garde « action utile » était satisfaite
structurellement mais sans export chiffré. Exception d'audit sans portée décisionnelle :
une trame de `external_only` entre en collision avec `learner_validation` sur 12312, aucune
image du corpus d'entraînement ne collisionne avec une banque.

Clos sans promotion ni retuning. Ne relancer aucun run, ne modifier aucun seuil, ne
réutiliser aucune graine 12301..12316.

Rapport : `docs/research/reafference_001_results.md`.

### REF-002 — transport spatial par commande relative (D-017 à D-020)

Hypothèse neuve : la copie d'efférence exige un transport explicite de la carte spatiale
par une commande **relative**, plutôt qu'une concaténation de commande absolue au latent
global. `transport_jepa` contre `concat_relative_jepa`, `no_command_jepa`, `pixel_change`
et `yaw_warp`, banques appariées par strate de mouvement pour supprimer le décalage de
domaine de REF-001. H5 exige que permuter ou inverser les commandes dégrade le modèle
gelé, preuve que l'action est causalement utilisée.

La revue a rendu `AUTORISER AVEC CORRECTIONS BLOQUANTES` ; C1–C8 et R1–R6 intégrées
additivement. Correction centrale : les banques strictement statiques rendaient le score
normalisé dégénéré — elles deviennent des banques de micro-mouvement `2°`, H2 devient
descriptive, et H3 `mixed` est l'unique porte de détection.

Le smoke 13991 était vert (projection `48,11896` min sous plafond 75, ratio d'équité
temporelle `1,12630`). La campagne a terminé 13301..13312, soit 12 triplets / 36 runs. La
préparation de 13313 s'est arrêtée **avant tout entraînement** sur une collision bit à bit
entre une trame finale de `moving_self_calibration` et une trame finale de `mixed`. La
revue REF-003 a montré ensuite que l'objet pouvait sortir entièrement du champ dans environ
`3,06 %` des paires `mixed` : la collision révélait une manipulation visuellement nulle,
pas une coïncidence.

13314..13316 n'ont jamais été ouvertes. D-020 clôt en **non-résultat technique**.
Interdit de lire ou d'agréger les scores des 12 triplets, de reprendre 13313, ou de
modifier la garde post hoc.

Détail : `docs/research/reafference_002_technical_stop.md`.

### REF-003 — même hypothèse, visibilité contrôlée (D-021 à D-027)

Monde et espaces de graines neufs, modèles et portes de REF-002 amendé conservés puisque
l'hypothèse n'avait pas été testée. Les corrections portent sur l'attribuabilité :
disjonction bloquante par provenance et digest de paire, collisions corpus↔banques
bloquantes, champ garanti analytiquement avec marge `3°` puis vérifié par paire, rendu
contrefactuel par paire invisible aux modèles, effet objet `≥ 0,01` par paire et `≥ 0,05`
en moyenne par bin, aucun resampling après observation.

Trois tentatives de smoke ont été nécessaires. La première s'est arrêtée sur une différence
d'une paire dans le multiensemble des masques warp du bin 0 ; D-024 pose désormais chaque
banque à l'état pré-transition exact avec vitesse nulle. La deuxième s'est arrêtée sur un
ratio temporel `1,275399 > 1,25` ; D-025 intercale les conditions en ordre tournant et
synchronise CUDA autour de chaque durée. La troisième, 14991, est entièrement verte : ratio
`1,10334`, marge de champ résiduelle `2,22165°`, visibilité minimale `0,15308` en externe
pur et `0,05794` en mixte, zéro collision, projection `39,92741` min sous plafond 90.

La campagne a terminé 14301..14302 puis s'est arrêtée pendant la préparation de 14303 sur
deux paires `external_only` sous le seuil contrefactuel individuel, `0,004453` et
`0,006999 < 0,01`. Les objets étaient dans le champ : **la preuve angulaire ne garantit ni
l'absence d'occlusion ni un contraste photométrique local minimal.** C'est la leçon qui
fonde la porte de faisabilité de D-060.

14303 n'a reçu aucun entraînement et 14304..14316 n'ont jamais été ouvertes. D-027 clôt
en **non-résultat technique**. Interdit de lire ou d'agréger 14301..14302, de reprendre
14303, ou de remplacer les paires fautives. Toute suite REF exige protocole,
monde et graines neufs.

Détail : `docs/research/reafference_003_technical_stop.md`.

### KERNEL-001 et LIFE-001 à LIFE-008 — infrastructure persistante (D-018 à D-034)

Voie d'infrastructure menée en parallèle des campagnes scientifiques. Le paquet
`cognitive/` maintient des croyances incertaines et sourcées, segmente des épisodes sans
regarder le futur, ne conserve que des références et digests J0, suit les compétences et
produit des propositions sous gardes explicites. Une proposition ne contient aucun champ
d'actionnement.

Progression, chaque tranche étant vérifiée avant la suivante :

- **LIFE-001 et LIFE-002** — raccord sensation → signal → choix sûr → persistance. Les événements
  publics sont réduits en erreur, incertitude, couverture, exposition aux butées et coût
  moteur, avec une preuve SHA-256 par candidate ; aucun payload brut n'entre dans SQLite.
- **LIFE-003** — schéma v2. Une exécution relie une proposition unique à une session J0
  unique ; `begin`, `complete` et `abort` sont transactionnels. Le noyau refuse toute
  divergence de session, de digest ou de valeur agrégée.
- **LIFE-004** — `sim3d/life_executor.py` ne connaît que deux plans gelés et n'accepte
  aucune cible libre. Arrêt d'urgence, primitive inconnue et proposition falsifiée sont
  refusés avant journal ; une panne MuJoCo injectée annule journal, exécution et
  proposition.
- **LIFE-005** — schéma v3, évaluation de `bounded_servo_tracking` sur tout le plan,
  transitoire compris. Validation `≤ 9°`, régression `> 15°` ; le seuil initial `8°` a été
  rectifié avant clôture, le nominal déterministe valant `8,1884765625°`.
- **LIFE-006** — `cognitive/needs.py`. Les besoins régressés préemptent les inconnus ; une
  suspension est toujours exclue. Sans historique, un `cold_start_prior` est persisté.
- **LIFE-007** — `cognitive/supervisor.py` et journal de cycles, schéma v4. Reprise après
  sélection, après exécution J0 ou après application, sans dupliquer les effets. Une
  session ne peut plus être close avec un cycle actif.
- **LIFE-008** — endurance réelle sur 64 cycles et cinq régimes périodiques : 64
  exécutions complètes, 63 évaluations, 51 redémarrages, 12 arrêts d'urgence refusés, zéro
  résidu. SQLite+WAL `1 609 856` octets, J0 `356 910`, moyenne `30 730,71875` octets par
  cycle, intégrité `ok`. Une seconde invocation saute 64/64 cycles et retrouve le digest
  `3cab7044228bb20ec512f67e32d3de44cac7a292c51d03311c7b815d3ccf2616`.

La plomberie déterministe est qualifiée. Elle est conçue par l'ingénieur et ne démontre
aucune politique apprise.

Spécifications : `docs/research/kernel_001_spec.md`,
`docs/research/kernel_001_implementation.md`, `docs/research/life_001_recovery.md`.

### LIFE-009 à LIFE-012 — choix d'expérience et plasticité (D-035 à D-046)

Quatre tentatives de faire apprendre à un mécanisme *quel essai réduit son erreur*. Les
quatre sont mortes sur une porte de faisabilité ou de marge, **avant d'ouvrir la moindre
banque réservée**.

- **LIFE-009** (D-037) — le smoke 17991 passe intégrité, replay, comptes, reproductibilité
  et durée, mais l'oracle n'améliore greedy que de `2,383 %` au lieu des `10 %` exigés.
  Non-résultat de conception. Aucune graine 17901..17940 ou 18001..18024 ouverte.
- **LIFE-010** (D-040) — après son propre historique, `probe_step_hold` porte
  `predicted_risk = 0,75`, au-dessus de la limite catalogue `0,50`. La garde l'a
  correctement bloqué et le professeur ne pouvait plus rejouer son carré latin. Clos sans
  métrique, reprise ni banque.
- **LIFE-011** (D-043) — les 18 préflights 18491..18496 sont verts (`risk = 0`,
  `motor_cost = 0,09375`) et la porte 5 est verte, mais la porte 6 ferme la campagne :
  médiane oracle `16,8853 %`, minimum settling `4,4039 % < 5 %` sur 18496. Le professeur,
  la plaque de chronométrage et 18501..18624 n'ont jamais été ouverts.
- **LIFE-012** (D-046) — coût commun porté à 240°, taxonomie rampe/plateau/temps mort. La
  plaque 18791..18796 passe les trois portes d'intégrité et échoue aux trois portes
  scientifiques : 18793 refuse 24/24 mises à jour, marge oracle médiane `4,9404 %`, et
  l'oracle myope perd contre round-robin sur certains organismes. Ferme la famille LIFE.

Diagnostic transversal : la compétence n'est plastique nulle part sur ce banc, et l'oracle
myope n'est pas un majorant.

### BODY-SCHEMA-001 et 002 — prévision corporelle (D-047 à D-053)

**BODY-SCHEMA-001** (D-049) — excitation fixe identique, baselines persistance/prior/ridge
et ensemble probabiliste de ridges ARX bootstrapé par trial. Le smoke 19091..19096 rend
huit portes vertes et deux rouges : M atteint une MAE `0,3476..0,6910°`, accepte
`14..17/24` mises à jour et corrige le cas 18793, mais les petites cellules
conditionnelles sortent de `[0,80 ; 0,98]` sur quatre organismes, et le détecteur par
transition ne bat pas le mouvement trivial sur toutes les fautes. Clos sans ouvrir 19201+.

**BODY-SCHEMA-002** (D-053) — F est la ridge simple B2', E ne porte que l'incertitude, A
agrège causalement les innovations sur quatre pas. La revue r2 a été rédigée par Codex à la
demande d'Anthony, en remplacement de Claude ; C1–C6 intégrées sous D-052. La v1 a arrêté
un vérificateur de reprise à liste partagée ; la v2 corrige avec test et relance complète.
Aucun réglage n'a utilisé la validation.

Résultat conservé : six organismes de développement et six de validation neufs, F
validation **0,435° à un pas** et **0,579° à 0,5 s**, portes prévision / déroulement /
persistance vertes, prévisions et prochaine mise à jour reproduites dans un autre
processus. Calibration E et agence A **non qualifiées** par paquet ; validation sur formes
connues, sans confirmation statistique ni essai d'oubli.

Rapport : `docs/research/body_schema_002_results.md`.

### CUMULATIVE-001 — apprentissage cumulatif A→B→A→C (D-054, D-055)

Mandat d'Anthony : poursuivre jusqu'à des avancées prometteuses, en documentant aussi les
échecs. Six vies de développement puis 12 vies de validation complètes, recette gelée.

Réseau avec rejeu : MAE finale A/B/C `0,079515°`, −53,19 % contre le réseau naïf et
−77,92 % contre la ridge cumulative ; toutes les portes acquisition, rétention,
récupération et reprise passent ; retour en A avec un gain relatif moyen de `69,93 %` par
vie face au réseau neuf ; reprise interprocessus exacte sur 18 vies et les deux réseaux.
Choix v2 validé sur 192 situations neuves : 190 réussites, utilité `47,031°` contre prior
prudent `38,125°` et ridge `41,667°`, avec deux échecs `speed_dominant/1` et une prudence
excessive `settling_dominant/2`.

Négatifs conservés : le contrôle d'orientation v1 ne rend aucun gain de trajectoire et
davantage de commandes ; l'oubli naïf reste généralement faible, donc aucun oubli
catastrophique n'a été corrigé ; le gain comportemental n'est pas attribuable au seul
rejeu. Le candidat neuronal est persistant et qualifié sur ce banc, pas intégré au registre
actif de `CognitiveKernel`.

Publication reproductible sans rejouer les vies : `learning.cumulative_001_publish`.
Rapport : `docs/research/cumulative_001_results.md`.

### RESILIENCE-001 — récupération après rupture (D-056, D-057)

Cadrage D-056 appliqué : résilience, apprentissage intrinsèque et développement incarné
sont la direction ; la précision motrice reste une sonde locale.

V1 arrêt technique (alias Adam, corrigé et testé), sources archivées. V2 six vies
complètes, **non promue** : récupération fonctionnelle `−9,78 %` contre naïf, validation v2
non lancée. V3 six vies de développement puis 12 vies de validation neuves, toutes les
portes prévues passent : 24 changements détectés au premier essai, zéro fausse alarme
initiale, 24 sous-objectifs clos, 12 rappels, 12 reprises interprocessus exactes.
Post-rupture, utilité `16,782°` contre naïf `16,100°` (+4,24 %) et mémoire récente
`11,354°` (+47,81 %) ; réussite `93,52 %` pendant la récupération et `95,14 %` au dernier
checkpoint.

Limite prioritaire : en validation, life-04 ne réussit que `50 %` des choix après 12 essais
malgré une MAE de `0,0815°`. **Une clôture de sous-objectif prédictif ne prouve pas une
compétence fonctionnelle retrouvée.**

Rapport : `docs/research/resilience_001_results.md`.

### RESILIENCE-002 — besoin fonctionnel et choix d'expériences (D-058, D-059)

Cycle complet : prédiction terminale, promesses avant action, résultats vécus, besoin et
sélection de catégorie persistés atomiquement dans le noyau ; 18 reprises exactes. V1
stoppée après deux commits sur un score NumPy non relisible de façon sécurisée, sources et
vie partielle conservées ; v2 convertit le score en float natif sans modifier les règles
d'apprentissage.

Résultat négatif, le plus instructif de la série : gain actif `+17,77 %` contre cycle en
développement, **inversé à `−15,20 %`** sur douze vies de validation. Réussite finale
`143/144`, pire vie `91,67 %`, mais seulement `71,18 %` de l'oracle contre le seuil de
`80 %`. Cycle fixe `100 %` / `80,56 %`, uniforme `100 %` / `74,00 %`. Le sélecteur actif
n'est pas promu. Le moniteur d'honnêteté est contredit sur `22/57` états clos, `4/39` après
apprentissage ; couverture `54,17 %`. Life-03 montre le couplage fragile : alarme tardive
sans nouveau changement physique, marge globale `3,515°` et repli vers `5°` alors que
`23,333°` étaient disponibles, malgré `12/12` réussites — un succès d'action ne suffit pas
à prouver la résilience.

Rapport : `docs/research/resilience_002_results.md`.

### D-060 et D-061 — changement de substrat, et l'incident d'audit (10 septembre 2026)

D-060 acte que le banc lui-même était le problème et ouvre le substrat visuel à deux axes.
Voir `PILOTAGE.md` pour la décision active et `CODEX_TASK_BRIEF.md` pour le prompt.

D-061 acte un incident interne sans conséquence scientifique. Le dépôt déclarait
`*.py text eol=lf` alors que les manifestes gèlent des SHA-256 des octets bruts : un commit
a réécrit onze sources `.py` en LF et cassé 566 références d'empreintes dans 113
manifestes. La cause racine est fermée par `* -text`, et les onze sources ont été
restaurées à l'octet près — six depuis les archives `source_v1`, cinq reconstruites et
certifiées par les empreintes gelées elles-mêmes. Aucune empreinte n'a été réécrite, aucune
garde assouplie, aucun résultat modifié et aucun niveau de preuve déplacé.
