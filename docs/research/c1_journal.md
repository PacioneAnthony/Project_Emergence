# Journal C1 — retrouver un objet désigné par son apparence

2026-09-11 · D-060 · étape 3, sonde de marge.

## Entrée 1 — seuils de la sonde, écrits avant tout calcul

État au moment d'écrire : aucun témoin n'existe encore, et aucun chiffre de témoin n'a été
calculé. Le seul résultat vu est celui de l'oracle de démonstration de la vue en direct, qui
connaît la cellule de la cible et réussit donc à 100 % par construction. Cette entrée est
commitée avant la première ligne de code des témoins ; l'horodatage du commit en fait foi.
Ces seuils ne changent plus, quels que soient les chiffres de développement.

### Pourquoi l'oracle du brief ne suffit pas

Le brief définissait la faisabilité comme la performance d'un oracle qui connaît la cellule
de la cible. Avec la notation de C1 — succès si la cellule répondue est celle de la cible —,
cet oracle réussit à 100 % par construction. Il ne peut pas échouer, donc il ne peut pas
détecter ce que la faisabilité doit détecter : des objets indiscernables dans les images que
reçoit l'agent. C'est la faute qui a tué REF-002 et REF-003. La borne supérieure devient un
**oracle perceptif**, qui, lui, peut échouer.

### Les trois politiques

Toutes jouent le même épisode — même pièce, même placement, même brassage, même cible —, si
bien que les comparaisons sont appariées épisode par épisode. Aucune n'apprend, aucune n'a
de mécanisme cognitif.

- **Oracle perceptif, la borne supérieure.** Il connaît la cellule courante de chaque objet
  placé et ses pixels exacts, isolés par différence entre la vue de la cellule avec et sans
  l'objet — la définition même du garde de visibilité. Il doit encore reconnaître, parmi les
  huit objets, celui que désigne la référence, avec la règle de comparaison ci-dessous. Il
  répond en un mouvement. Il isole la reconnaissance : ni recherche, ni mémoire.
- **Témoin « dernier angle vu ».** Il garde les quinze images de l'exploration et répond
  depuis sa mémoire : la cellule dont l'image mémorisée ressemble le plus à la référence. Un
  mouvement, jamais de vérification. La lecture littérale du brief — revenir au dernier
  endroit où « quelque chose » a été vu — ignorerait la désignation dans une pièce à huit
  objets et resterait au niveau du hasard ; celle-ci est la forme la plus forte d'un témoin
  fondé sur la seule mémoire.
- **Témoin « balayage exhaustif ».** Sans mémoire : après la désignation, il revisite les
  quinze cellules, compare chaque image fraîche à la référence et répond sur la meilleure.
  Quinze visites, plus un pointage final s'il ne termine pas sur la cellule choisie.

L'oracle de démonstration, qui connaît la cellule, est rapporté comme contrôle de la
notation, avec 100 % attendus, et n'entre dans aucune porte.

### La règle de comparaison, commune et figée

Images converties en TSV. Pixels « objet » : saturation ≥ 0,45 et valeur ≥ 0,25.
Descripteur : histogramme de teinte sur 24 classes des pixels objet, normalisé à 1 ; moins
de 20 pixels objet, et la cellule compte comme vide. Distance : L1 entre histogrammes, dans
[0 ; 2] ; une cellule vide est à 2. En cas d'égalité, la première cellule dans l'ordre de
balayage l'emporte. Pour l'oracle perceptif, le même descripteur, calculé sur les seuls
pixels de l'objet.

Cette règle est simple par choix, et ce choix se protège lui-même : si elle est trop faible,
l'oracle perceptif échoue aussi, la faisabilité tombe, et la sonde s'arrête au lieu
d'accepter une marge fabriquée par des témoins trop bêtes — le piège inverse de celui de
REF-001, où des témoins mal posés gagnaient pour une raison vide. Sur les graines de
développement, seules des corrections de bogues sont permises, chacune consignée dans ce
journal ; aucun paramètre ne change après le premier chiffre de développement.

### Paramètres de la tâche, repris de l'étape 2

Huit objets ; probabilité de brassage 0,5 ; six mouvements de délai ; images 96 × 96 ;
exploration en balayage ; garde de visibilité à 2 % de la vue centrale. Le coût d'une
politique est le nombre de mouvements de tête commandés après la désignation.

### Les seuils

**Faisabilité.** Succès de l'oracle perceptif ≥ 0,90, avec une borne basse de Wilson à 95 %
≥ 0,80 ; et au plus 10 % des pièces de la banque rejetées par les gardes de construction,
avant que la moindre politique agisse. Sinon, la tâche telle que construite n'est pas
lisible : arrêt, aucune marge revendiquée, et c'est la tâche qu'on corrige, pas un mécanisme
qu'on conçoit.

**Marge, pour chaque témoin**, mesurée contre l'oracle perceptif :

- *en succès* — l'écart apparié par épisode, `d = succès(oracle) − succès(témoin)`, vaut −1,
  0 ou 1. La marge en succès est établie si la borne basse de l'intervalle BCa à 95 % de la
  moyenne de `d` est ≥ 0,10, calculée par `learning.paired_stats.bca_bootstrap_ci` avec
  10 000 rééchantillonnages et la graine 0.
- *en coût* — la marge en coût est établie si le témoin coûte en moyenne au moins trois
  mouvements de plus que l'oracle.

Un témoin est **proche de l'oracle** si aucune de ses deux marges n'est établie : il est
déjà presque aussi juste et presque aussi économe.

**Verdict.** MARGE EXPLOITABLE si la faisabilité passe et qu'aucun témoin n'est proche.
Sinon, REJETÉE : selon le critère d'abandon de D-060, ce substrat est déclaré épuisé pour C1
et aucun mécanisme n'y est construit. Une marge non établie compte comme absente :
l'incertitude ne profite jamais à l'acceptation. Le verdict exige que *tous* les témoins
laissent une marge ; c'est un test d'intersection, conservateur par construction, qui ne
demande pas de correction pour comparaisons multiples.

Ce que « exploitable » veut dire concrètement : le témoin de mémoire devrait être économe
mais faux après un brassage, le balayage juste mais coûteux. L'oracle perceptif montre qu'un
coin « juste et économe » existe. Une politique qui l'approcherait — se souvenir, et ne
vérifier que lorsque c'est utile — est exactement ce que C1 doit tester ensuite.

### Graines

Recette du projet : les quatre premiers octets, gros-boutistes, du SHA-256 du JSON compact
`["c1-margin-probe/v1", sous-espace, i]`. Développement : sous-espace `"dev"`, i de 0 à 9.
Banque : sous-espace `"bank"`, i de 0 à 59, soit 60 pièces, jouées une seule fois, après le
gel du code. Toutes supérieures à 100 000, toutes distinctes, aucune collision avec les
14 892 nombres littéraux de 346 fichiers du dépôt — vérifié à l'écriture de cette entrée.

Budget prévu : quelques minutes de calcul pour la banque, bien sous l'heure du brief.

### Défaut à corriger avant la sonde

Préparer la sonde a fait apparaître un trou dans la tâche de l'étape 2 : le brassage replace
les objets par `_draw_placement` sans repasser la vérification de visibilité par objet.
Après un brassage, un objet pourrait donc tomber dans une cellule qui ne le montre pas — la
faute même que ce garde existe pour empêcher. Le brassage passera par la même vérification
que la construction. C'est une correction de la tâche, pas un réglage des témoins, et elle
est décidée ici, avant d'avoir vu le moindre chiffre.

### Gel et archive

Avant la banque, les sources de la sonde sont gelées — empreintes SHA-256 dans un
manifeste — et copiées à côté des résultats, selon la convention `source_v1` de D-061.

## Entrée 2 — développement, avant la banque

2026-09-11. Dix pièces de développement, jouées pour déboguer. Les seuils de l'entrée 1 ne
bougent pas.

### Un bogue de rendu, trouvé par la sonde et corrigé

Premier passage : balayage 3 sur 10, en échec dans *chacune* des pièces brassées, alors qu'il
regarde des images fraîches après le brassage. Diagnostic sur la pièce `3647248449` : après
le brassage, toutes ses distances valaient 2,0 — ses images ne contenaient plus un seul pixel
coloré. La cause a été établie par une expérience minimale, pas supposée. Dans cette version
de MuJoCo, fermer un moteur de rendu libère ses ressources graphiques dans le contexte
OpenGL qui se trouve courant. La correction du brassage prévue à l'entrée 1 fermait l'ancien
monde *après* avoir construit le nouveau : elle libérait donc les ressources du nouveau, dont
l'image suivante sortait noire, luminance 154 → 0. Rendre courant le contexte du moteur avant
de le fermer laisse les autres intacts, écart 0.

Correctif : `release_renderer`, utilisé partout où un moteur est fermé — environnement, vue
en direct, rendu de référence. Trois tests de non-régression, dont celui qui aurait attrapé
le bogue : après un brassage, la tête doit voir le monde que le garde a mesuré. L'oracle et
le témoin de mémoire n'étaient pas touchés, puisqu'ils travaillent sur des images capturées
avant la fermeture. C'est une correction de bogue au sens de l'entrée 1 — le code ne faisait
pas ce qu'il devait faire — et aucun paramètre de la règle ni aucun seuil n'a changé.

### Second passage, après correction

Oracle perceptif 9 sur 10, témoin « dernier angle vu » 5 sur 10, balayage 7 sur 10 ; six
pièces brassées sur dix ; coûts de 1, 1 et 16 mouvements. Le témoin de mémoire échoue dans
quatre des six pièces brassées, et le balayage n'est plus pénalisé par le brassage. Ces
chiffres ne décident rien : dix pièces ne peuvent pas établir une borne de Wilson à 80 %.

### Une limite de reconnaissance, consignée et non corrigée

Dans la pièce `2563204882`, non brassée, les trois politiques échouent, oracle compris. La
cible est le cube orange. Sa référence tombe entièrement dans la classe de teinte 3 ; dans la
pièce, sous l'éclairage de la scène, elle tombe entièrement dans la classe 2. Avec un
histogramme sans tolérance, deux classes voisines sont à la distance maximale, 2,0, et la
sphère jaune, qui a de la masse en classe 3, l'emporte à 0,80.

Ce n'est pas un bogue. La règle fait exactement ce que l'entrée 1 écrit, et l'écart
d'éclairage entre la référence et la scène est une propriété de la tâche telle que
construite à l'étape 2. Corriger l'une ou l'autre maintenant, après avoir vu ce chiffre,
reviendrait à régler la porte en voyant les données. Rien n'est donc touché.

Ce que cela laisse prévoir, écrit ici pour que la banque ne surprenne personne : l'orange est
la cible dans environ une pièce sur huit. Si ces pièces échouent comme celle-ci, l'oracle
perceptif tombera vers 87 %, sous le seuil. Et le seuil est plus exigeant qu'il n'y paraît :
sur 60 pièces, 54 succès donnent 90 % mais une borne de Wilson de 79,9 %, sous 80 % ; il en
faut 55. Cette prévision ne change rien à la suite. La banque se joue telle que gelée, et si
la faisabilité échoue, l'entrée 1 dit déjà quoi faire : corriger la tâche dans une version 2,
avec de nouvelles graines, et non concevoir un mécanisme.

### Gel

Sources gelées dans `docs/research/c1_probe_manifest.json` et copiées octet pour octet sous
`data/processed/experiments/c1_probe/source_v1`, avant la banque.

## Entrée 3 — la banque, et son verdict

2026-09-11. Soixante pièces réservées, jouées une seule fois après le gel (`cc5d082`,
16:56:35), en 27 secondes. Aucune pièce écartée par les gardes ; contrôle de notation par
l'oracle de cellule à 100 % ; 53 % des épisodes brassés. Une seconde partie est refusée par
le lanceur, et c'est vérifié. Résultats complets : `docs/research/c1_probe_results.json`.

### Les deux chiffres

**Faisabilité : 54 sur 60, soit 90,0 %, borne de Wilson à 95 % de 79,9 %.** Le seuil
demandait 80 % : il manque une pièce, exactement le cas que l'entrée 2 avait écrit avant la
partie.

**Marge.** Le témoin « dernier angle vu » réussit 35,0 %, écart apparié de +55,0 points
[BCa +40,0 ; +66,7], pour le même coût que l'oracle. Le balayage exhaustif réussit 66,7 %,
écart de +23,3 points [BCa +11,7 ; +33,3], pour quinze mouvements de plus.

**Verdict : REJETÉE — FAISABILITÉ.** Selon l'entrée 1, aucune marge n'est revendiquée quand
la faisabilité échoue, si larges que paraissent les écarts ci-dessus : ils décrivent la
sonde, ils ne concluent rien. Et ce n'est *pas* le critère d'abandon de D-060, réservé à une
marge absente : le substrat n'est pas déclaré épuisé. C'est la tâche qu'on corrige.

### Ce qui a échoué — relecture diagnostique

Relecture déterministe des soixante pièces pour identifier les cibles. Elle reproduit tous
les choix enregistrés, zéro écart, et n'entre pas dans le verdict.

Les six échecs de l'oracle perceptif relèvent d'un seul mécanisme. Le cube orange est la
cible dans cinq pièces et l'oracle les manque toutes, 0 sur 5 : sa référence tombe en classe
de teinte 3, son image dans la pièce en classe 1 ou 2, à la distance maximale de sa propre
référence, et la sphère jaune l'emporte chaque fois. Le sixième échec est le même effet sur
le cube vert, référence en classe 9 et scène en classe 8. Toutes les autres cibles sont lues
à 100 %. La faisabilité ne bute donc pas sur des objets indiscernables : elle bute sur un
décalage de teinte entre la référence et la scène, que la règle sans tolérance traduit en
distance maximale.

### Ce que la version 2 doit corriger

Trois candidats, dont aucun n'est encore décidé :

- **rendre la référence sous l'éclairage de la scène**, fond neutre conservé — c'est la cause
  du décalage, et c'est bien la tâche qu'on corrige, comme l'entrée 1 le demande ;
- donner à la règle une tolérance aux petits décalages de teinte, par un histogramme
  circulaire et lissé — mais cela change aussi la force des témoins ;
- retirer de la palette les couleurs trop proches — au prix d'une tâche plus pauvre.

Recommandation : le premier, seul. Il corrige la tâche sans toucher à la règle.

Une seconde observation doit peser sur la v2 : le balayage manque quatorze pièces que
l'oracle lit. L'hypothèse la plus probable, non vérifiée ici, est le fouillis coloré de la
pièce, qui pollue l'histogramme de l'image entière alors que l'oracle ne voit que l'objet.
Si elle tient, une partie de la marge viendrait de témoins trop faibles — le piège de
REF-001. Une v2 honnête vérifiera cette hypothèse et, si elle tient, donnera aux témoins la
même fenêtre centrale que celle où se trouvent les objets.

La v2 prend de nouvelles graines et un nouvel espace de noms, et ses seuils s'écrivent avant
son premier chiffre, comme ceux-ci.

## Entrée 4 — seuils de la version 2, écrits avant tout chiffre

2026-09-12. Anthony autorise la v2. État au moment d'écrire : aucun code de v2 n'existe,
aucune graine de v2 n'a été jouée, et le seul résultat connu est celui de la v1, publié et
clos. Cette entrée est commitée avant la première ligne de code de la v2 ; l'horodatage du
commit en fait foi. Ces seuils ne changent plus, quels que soient les chiffres de
développement.

### Contrainte d'abord : les neuf sources de la v1 ne peuvent pas être touchées

`docs/research/c1_probe_manifest.json` gèle les octets de neuf fichiers, dont
`learning/c1_probe.py` et `learning/c1_task.py`. Les modifier maintenant casserait la piste
d'audit du résultat v1 déjà publié. La v2 étend donc par de nouveaux modules — exactement
comme `bench2_model.py` a étendu le banc gelé — et ne réécrit rien :
`learning/c1_task_v2.py`, `learning/c1_probe_v2.py`, `scripts/research/c1_probe_v2.py`.

Conséquence qui vaut mieux qu'une promesse : la règle de comparaison n'est pas recopiée,
elle est **importée** depuis `learning.c1_probe`. `descriptor`, `distance` et `closest`
s'exécutent octet pour octet comme dans la v1. Dire « la règle n'a pas changé » cesse
d'être une affirmation de ma part et devient une propriété du code.

### Correction 1 — la référence est rendue sous l'éclairage de la scène

C'est la recommandation de l'entrée 3, et la seule des trois qui soit retenue. Ni tolérance
ajoutée à l'histogramme, ni couleur retirée de la palette : la porte reste celle de
l'entrée 1.

**Mécanisme supposé, avec sa prédiction chiffrée.** La scène de référence est surexposée
par rapport à la pièce : phare `ambient 0,45 / diffuse 0,65` et une lampe à 0,7 contre
`0,35 / 0,60` et des lampes plus lointaines dans la pièce. Quand l'éclairement total
dépasse `1/0,95`, le canal rouge de l'orange `(0,95 ; 0,50 ; 0,10)` sature à 1,0 pendant
que le vert et le bleu continuent de monter — et **saturer un canal déplace la teinte**.
Arithmétique : sans saturation, teinte `(0,40/0,85)/6 = 0,0784`, classe 1 ; à un gain de
1,7, le rouge est écrêté et la teinte devient `(0,68/0,83)/6 = 0,1365`, classe 3. C'est
exactement le décalage mesuré à l'entrée 3, référence en classe 3 et scène en classe 1 ou
2. L'orange n'est donc pas une couleur ambiguë : la référence était trop éclairée.

Cette explication reste une **hypothèse tant qu'elle n'est pas mesurée**. Elle sera
vérifiée sur les graines de développement, avant le gel, et le résultat consigné à
l'entrée 5, qu'il la confirme ou la réfute.

**Mise en œuvre, sans paramètre libre.** La scène de référence reprend le bloc
`<visual><headlight>` de la pièce tel quel et ses deux lampes à leurs positions réelles ;
l'objet est placé à la position de la caméra du banc, avec le fond neutre immédiatement
derrière lui. Rien n'est réglé à la main : les valeurs sont celles de `BenchRoomConfig`.

L'éclairage de la pièce est déterministe — seuls les meubles et les panneaux sont tirés au
sort —, donc la référence reste identique d'une pièce à l'autre. C'est la propriété qui
l'empêche d'encoder le placement ; un test la verrouille déjà et continuera de la
verrouiller.

**Limite écrite d'avance, pour que la banque ne surprenne personne.** La correction traite
l'orange, dont l'échec vient de l'écrêtage. Elle ne traite pas le cube vert
`(0,10 ; 0,70 ; 0,25)`, dont la teinte vaut `0,375` — soit `0,375 × 24 = 9,000`, exactement
sur la frontière entre les classes 8 et 9. Une variation infime le fait basculer d'un côté
ou de l'autre, et c'est ce qui s'est produit une fois dans la banque v1. Cette fragilité
est une propriété de la règle à classes sans tolérance, pas de l'éclairage : la v2 ne la
corrige pas et peut donc encore perdre des pièces sur le vert.

### Correction 2 — les témoins reçoivent la fenêtre centrale

L'entrée 3 laissait une suspicion non vérifiée : le balayage manque quatorze pièces que
l'oracle lit, probablement parce que le fouillis coloré de la pièce pollue l'histogramme de
l'image entière alors que l'oracle ne voit que l'objet.

La v2 ne conditionne pas cette correction à un diagnostic : les deux témoins calculent leur
descripteur sur la **moitié centrale** de chaque image, pixels `[size//4 ; size − size//4]`
sur les deux axes. C'est la fenêtre que le garde de visibilité et `usable_cells` utilisent
déjà, et c'est celle où la tâche place tous ses objets par construction. Techniquement,
c'est le masque booléen que `descriptor` accepte depuis la v1 : la fonction gelée est
appelée telle quelle, seuls les pixels qu'on lui offre changent.

**Pourquoi cette décision est admissible après avoir vu la v1.** Elle *renforce* les
témoins, donc elle ne peut que réduire la marge revendiquée contre eux. Un changement qui
rend la porte plus dure à passer n'est pas un réglage de porte. C'est le sens de la
direction qui rend ce choix acceptable maintenant, et rien d'autre.

L'oracle garde son masque d'objet, inchangé. L'ampleur de l'effet sera mesurée sur les
graines de développement et rapportée à l'entrée 5 de façon descriptive ; elle ne décide
rien.

### Correction 3 — la banque passe de 60 à 200 pièces

**Le défaut, énoncé sans détour.** Le dispositif de la v1 ne pouvait pas passer à sa propre
cible. À 90,0 % exactement, 60 pièces donnent une borne de Wilson de 79,85 %, sous les 80 %
que le même dispositif exigeait. La plus petite taille où un 90 % observé franchit 80 % est
70. Les deux seuils de faisabilité étaient donc mutuellement incompatibles à n = 60 : c'est
un défaut de puissance dans la conception, pas une propriété de la tâche. Je ne l'ai
remarqué qu'en voyant la v1 échouer, et je l'écris ici parce que c'est le genre de chose
qu'on est tenté de corriger en silence.

**Ce qui change : n, et n seulement.** Le seuil ponctuel reste 0,90 et la borne basse de
Wilson reste 0,80. À n = 200, un 90 % observé donne une borne basse de 85,1 % et une
demi-largeur de ±4,2 points : la porte contraignante redevient l'estimation ponctuelle,
comme prévu, et l'intervalle redevient informatif au lieu d'être décisif par accident.

Et cela coupe dans les deux sens : à n = 200 les intervalles BCa sur les écarts de témoins
sont environ 1,8 fois plus serrés qu'à n = 60, donc une marge devient **plus difficile** à
établir, pas plus facile.

**Ce que cela concède.** Augmenter n rend un taux vrai de 0,90 exactement plus susceptible
de franchir la borne basse. C'est précisément la réparation voulue : cette borne existe
pour exclure les taux nettement inférieurs à 0,90, pas pour exclure 0,90 lui-même.

Coût : environ 90 secondes, au rythme mesuré de la v1 — 27 secondes pour 60 pièces.

### Ce qui ne change pas

- **La règle de comparaison**, importée et non recopiée : TSV, pixels objet à saturation
  ≥ 0,45 et valeur ≥ 0,25, histogramme de teinte sur 24 classes normalisé, moins de
  20 pixels objet et la cellule compte comme vide, distance L1 dans [0 ; 2], cellule vide à
  2, première cellule dans l'ordre de balayage en cas d'égalité.
- **Les trois politiques** et leur comptabilité de coût : oracle perceptif à un mouvement,
  témoin de mémoire à un mouvement, balayage à quinze visites plus un pointage éventuel.
- **Les seuils.** Faisabilité : succès ≥ 0,90, borne basse de Wilson à 95 % ≥ 0,80, au plus
  10 % des pièces rejetées par les gardes. Marge en succès : borne basse BCa à 95 % de
  l'écart apparié ≥ 0,10, par `learning.paired_stats.bca_bootstrap_ci`, 10 000
  rééchantillonnages, graine 0. Marge en coût : au moins trois mouvements de plus que
  l'oracle.
- **Les règles de verdict**, y compris qu'une marge non établie compte comme absente et que
  le verdict exige que *tous* les témoins laissent une marge.
- **Les paramètres de la tâche** : huit objets, brassage 0,5, six mouvements de délai,
  images 96 × 96, exploration en balayage, garde de visibilité à 2 % de la vue centrale.
- **La discipline de développement** : sur les graines de développement, seules des
  corrections de bogues sont permises, chacune consignée dans ce journal ; aucun paramètre
  ne change après le premier chiffre de développement. Gel des sources et archive
  `source_v1` sous `data/processed/experiments/c1_probe_v2/` avant la banque, qui se joue
  une seule fois.

### Graines

Même recette du projet, espace de noms neuf : les quatre premiers octets, gros-boutistes,
du SHA-256 du JSON compact `["c1-margin-probe/v2", sous-espace, i]`. Développement :
sous-espace `"dev"`, i de 0 à 9. Banque : sous-espace `"bank"`, i de 0 à 199.

Vérifié à l'écriture de cette entrée, et non supposé : 210 graines toutes distinctes,
toutes supérieures à 100 000, aucune collision avec les 1 696 557 littéraux entiers des
6 656 fichiers Python du dépôt, et **aucune réutilisation d'une graine de la v1**, dont la
banque est consommée et close. Première graine de développement `3848342225` ; première
graine de banque `2956972568`, dernière `1504345451`.

### Ce que chaque issue voudra dire, écrit avant de la connaître

- **Faisabilité échouée sur le même mécanisme de teinte** — la correction n'a pas marché.
  C'est alors un résultat sur la fragilité de la règle, et il justifierait de la
  reconsidérer dans une v3 dont les seuils s'écriraient d'abord.
- **Faisabilité échouée sur un autre mécanisme** — la tâche est moins lisible que
  construite. On corrige encore la tâche ; on ne conçoit toujours pas de mécanisme.
- **Faisabilité passée et un témoin proche de l'oracle** — c'est le critère d'abandon de
  D-060, cette fois pour de bon : le substrat est déclaré épuisé pour C1 et aucun mécanisme
  n'y est construit. Il est écrit ici pour ne pas pouvoir être réinterprété après coup.
- **Faisabilité passée et les deux témoins laissant une marge** — MARGE EXPLOITABLE, et le
  pré-enregistrement de C1 peut enfin s'écrire.

## Entrée 5 — développement de la v2, avant la banque

2026-09-12. Dix pièces de développement. Les seuils de l'entrée 4 ne bougent pas, et aucun
paramètre n'a été touché après le premier chiffre ci-dessous.

### L'hypothèse de surexposition : confirmée en direction, insuffisante en ampleur

Mesuré, et non supposé. Pour chaque objet de la palette, dans les dix pièces de
développement, la comparaison que fait l'oracle perceptif : sa référence désigne-t-elle bien
l'objet lui-même parmi les huit placés ?

| Objet | Référence v1 | Référence éclairée par la pièce |
|---|---|---|
| 6 cube orange `(0,95 ; 0,50 ; 0,10)` | 0/10 | **4/10** |
| 3 cube vert `(0,10 ; 0,70 ; 0,25)` | 8/10 | **10/10** |
| 4 cylindre magenta | 9/10 | 9/10 |
| les cinq autres | 10/10 | 10/10 |
| **total** | **67/80 = 83,8 %** | **73/80 = 91,2 %** |

La direction prédite à l'entrée 4 est confirmée : sous l'éclairage de la pièce, la référence
de l'orange passe de la classe de teinte 3 à la classe 2. Mais la scène le montre en
classe 1. Avec un histogramme sans tolérance, deux classes voisines sans recouvrement
restent à la distance maximale de 2,0, et la sphère jaune l'emporte encore. **La correction
est réelle et elle ne suffit pas.**

Rien ne se dégrade : aucun objet ne recule, et la sphère jaune passe d'une distance de 0,668
à 0,005. Le cube vert, dont l'entrée 4 annonçait qu'il resterait fragile parce que sa teinte
tombe exactement sur la frontière `0,375 × 24 = 9,000`, est lu 10/10 ici — ce qui ne retire
rien à la fragilité, seulement à sa fréquence sur dix pièces.

### La fenêtre centrale ne change rien, et cela doit être écrit

Les deux témoins, sur les mêmes dix pièces, chaque image décrite deux fois à partir des
mêmes pixels : témoin de mémoire 4/10 dans les deux cas, balayage 7/10 dans les deux cas.

L'hypothèse de l'entrée 3 — le fouillis coloré de la pièce polluant l'histogramme de l'image
entière — **n'est pas soutenue**. La fenêtre est conservée : elle est inoffensive, elle va
dans le sens conservateur, et elle supprime un facteur de confusion. Mais elle ne doit être
créditée de rien, et la marge de la v2 ne pourra pas s'en réclamer.

### La sonde de développement

Oracle perceptif 7/10, témoin « dernier angle vu » 4/10, balayage 7/10 ; quatre pièces
brassées sur dix ; coûts de 1, 1 et 15,9 mouvements. Dix pièces n'établissent rien : les
seuils de l'entrée 4 en demandent 200.

### Les trois échecs, attribués et non supposés

Relecture déterministe, nommant la cible et la réponse. Deux mécanismes, pas un.

- **Pièces `3583313364` et `1158679384`** — le cube orange, le mécanisme connu. Référence en
  classe 2, cible vue en classe 1, distance 2,000 ; la sphère jaune répond à 0,729 et 1,899.
- **Pièce `1064561201`**, brassée — le cylindre magenta, et **un mécanisme que la v1 n'a
  jamais consigné**. Son descripteur est *vide*. Le masque du garde isole 220 pixels et le
  garde a mesuré 8,7 % de la vue centrale changée, bien au-dessus de son seuil de 2 % — mais
  moins de vingt de ces pixels passent le filtre de saturation du lecteur. L'oracle lit donc
  une cellule vide là où la tâche vient de certifier un objet, se retrouve à égalité à 2,000
  avec les autres candidats vides, et répond au premier dans l'ordre de balayage.

### Un défaut trouvé, nommé, et non corrigé

Les deux gardes ne font pas le même test. Le garde de visibilité compte les pixels qui ont
*changé* de plus de 25 entre la pièce avec l'objet et la pièce sans lui. Le lecteur gelé
compte les pixels *saturés*, saturation ≥ 0,45 et valeur ≥ 0,25. Un objet à l'ombre, ou
délavé par la distance, passe le premier et échoue au second. C'est la leçon de REF-003 sous
une forme nouvelle : un garde qui ne mesure pas dans les termes qui comptent en aval.

Fréquence mesurée : **un objet illisible sur 80 placés, soit 1,2 %**, sur les dix pièces de
développement.

**Il n'est pas corrigé, et la raison importe plus que le défaut.** Le réparer rendrait
davantage de pièces lisibles, donc augmenterait la faisabilité — après qu'un chiffre de
développement a été vu. L'entrée 4 n'admet un changement décidé après avoir vu les données
que lorsqu'il rend la porte **plus dure** à passer ; celui-ci la rendrait plus facile. Cette
asymétrie est exactement ce qui rendait la fenêtre centrale admissible et qui rend
celui-ci inadmissible. Il est pré-enregistré ici comme la première correction d'une
éventuelle v3.

### Prédiction avant la banque

Écrite ici pour que la banque ne surprenne personne, comme l'entrée 2 l'avait fait.

L'orange est la cible dans environ une pièce sur huit et n'est lu que quatre fois sur dix :
environ 7 points de faisabilité perdus. Le magenta en coûte environ 1, et l'objet illisible
environ 1 de plus. La faisabilité attendue se situe donc **entre 85 et 91 %, contre un seuil
ponctuel de 90 %**. La banque peut très bien échouer de nouveau. Les 7/10 du développement
sont un tirage bas sous n'importe lequel de ces taux, mais pas un tirage impossible.

Si elle échoue sur le mécanisme de l'orange, l'entrée 4 dit déjà ce que cela voudra dire :
un résultat sur la fragilité d'un histogramme sans tolérance, et une v3 dont les seuils
s'écriront d'abord. Rien n'est réglé maintenant.

### Gel

Douze sources : les trois de la v2, et les neuf de la v1, hachées pour certifier qu'elles
n'ont pas bougé. Manifeste `docs/research/c1_probe_v2_manifest.json`, archive
`data/processed/experiments/c1_probe_v2/source_v1`, convention `source_v1` de D-061.

428 tests verts, dont onze nouveaux qui vérifient par identité d'objet — et non par égalité
de valeurs — que la v2 importe le lecteur, l'oracle perceptif, le verdict et chacun des
seuils depuis le module v1 gelé, au lieu d'en tenir une copie.

## Entrée 6 — la banque de la v2, et son verdict

2026-09-12. Deux cents pièces réservées, jouées une seule fois après le gel (`91cf236`,
gelé à 02:30:36), en 86 secondes. Aucune pièce écartée par les gardes ; contrôle de notation
par l'oracle de cellule à 100 % ; 51 % des épisodes brassés. Une seconde partie est refusée
par le lanceur, et c'est vérifié. Les douze sources gelées sont intactes après la banque, et
les neuf de la v1 aussi. Résultats : `docs/research/c1_probe_v2_results.json`.

### Le chiffre

**Faisabilité : 178 sur 200, soit 89,0 %, borne de Wilson à 95 % [83,9 % ; 92,6 %].** Le
seuil ponctuel demandait 90,0 % : **il manque deux pièces.**

La réparation de puissance décidée à l'entrée 4 a fait exactement ce qu'elle promettait, et
c'est la seule partie du dispositif qui se soit comportée comme annoncé : la borne de Wilson
franchit son seuil de près de quatre points, et c'est l'estimation ponctuelle qui décide. La
v1 avait échoué sur la borne à une pièce près ; la v2 échoue sur le taux lui-même. Ce n'est
plus un défaut de conception, c'est une mesure.

**La prédiction de l'entrée 5 était juste.** Elle annonçait une faisabilité entre 85 et 91 %
et disait que la banque pouvait très bien échouer de nouveau. Elle vaut 89,0 %.

### Ce qui a échoué — relecture déterministe

Relecture des deux cents pièces, reproduisant chaque choix enregistré : **zéro écart**. La
banque est reproductible, et rien de ce qui suit n'entre dans le verdict.

Les vingt-deux échecs tiennent à **deux objets, et à eux seuls**. Les six autres sont lus
sans une faute, 153 fois sur 153.

| Objet | Fois cible | Fois lue | Taux |
|---|---|---|---|
| 6 cube orange `(0,95 ; 0,50 ; 0,10)` | 21 | 6 | **28,6 %** |
| 4 cylindre magenta `(0,85 ; 0,35 ; 0,85)` | 26 | 19 | **73,1 %** |
| 0, 1, 2, 3, 5, 7 | 153 | 153 | **100 %** |

- **Le cube orange, quinze échecs, tous le même.** Référence en classe de teinte 2, objet vu
  dans la pièce en classe 1 — dans les quinze cas, sans une exception. Ce n'est pas du
  bruit : c'est un décalage d'exactement une classe, parfaitement systématique. L'éclairage
  de la pièce a rapproché la référence d'une classe, de 3 à 2, sans jamais la faire
  coïncider. La correction allait dans le bon sens et s'est arrêtée une classe trop tôt.
- **Le cylindre magenta, sept échecs, photométriques.** Cinq fois son descripteur est
  *vide* — le défaut que l'entrée 5 a nommé et délibérément laissé en place. Deux fois il
  survit, mais réparti dans des classes qui ne sont pas les siennes (56 % en classe 9 et
  42 % en classe 2 ; ailleurs 64 % en classe 7), signe qu'il ne reste qu'une poignée de
  pixels non représentatifs de sa couleur.

Arithmétique qui situe l'enjeu : la porte demandait 180 pièces sur 200. Réparer le seul cube
orange en aurait donné 193, soit 96,5 % ; réparer le seul cylindre magenta, 185, soit
92,5 %. **Chacune des deux corrections suffisait à passer, séparément.**

### Verdict

**REJETÉE — FAISABILITÉ.** Aucune marge n'est revendiquée, selon la règle de l'entrée 1
reprise par l'entrée 4. Ce n'est toujours pas le critère d'abandon de D-060, réservé à une
marge absente : le substrat n'est pas déclaré épuisé, et c'est encore la tâche qu'on corrige.

### Les témoins, en description seule

Le témoin « dernier angle vu » réussit 44,0 %, écart apparié de +45,0 points
[BCa +37,5 ; +51,5], au même coût que l'oracle. Le balayage exhaustif réussit 82,5 %, écart
de +6,5 points [BCa +3,5 ; +10,0], pour quinze mouvements de plus.

Un fait mérite d'être relevé, parce qu'il porte sur la question même que D-060 pose.
**L'écart de succès du balayage s'est effondré**, de +23,3 points en v1 à +6,5 ici, pendant
que la tâche devenait plus lisible : le balayage passe de 66,7 % à 82,5 %. C'est attendu —
un oracle et un balayage qui lisent mieux convergent — mais cela dit où se jouera la marge.
Si une v3 répare les deux objets restants, le balayage pourrait atteindre la parité en
succès et ne plus se distinguer que par le coût. Ce n'est pas un résultat et rien n'en est
conclu ; c'est ce qu'il faudra surveiller, et c'est la première fois que ce substrat donne
un signe sur la question de la marge plutôt que sur celle de la lisibilité.

### Ce que la v3 doit corriger

Deux corrections, une par mécanisme, toutes deux **nommées avant de connaître ce chiffre** :

1. **Le garde de visibilité doit mesurer dans les termes du lecteur.** Pré-enregistré à
   l'entrée 5 comme première correction d'une v3 : un objet n'est accepté dans une cellule
   que si son descripteur y existe. Aujourd'hui le garde compte des pixels changés et le
   lecteur exige des pixels saturés, et rien ne garantit le second quand le premier passe.
2. **La règle sans tolérance doit être reconsidérée.** Pré-enregistré à l'entrée 4 : un
   échec sur le mécanisme de teinte est « un résultat sur la fragilité d'un histogramme sans
   tolérance, et il justifierait de la reconsidérer dans une v3 dont les seuils s'écriraient
   d'abord ». Le décalage mesuré ici est d'exactement une classe et il est systématique ;
   l'éclairage l'a réduit sans le refermer. Une règle qui met deux classes voisines à la
   distance maximale ne mesure pas une différence d'apparence, elle mesure un arrondi.

Attention à ne pas se tromper de sens en corrigeant le second point : une règle tolérante
renforce aussi les témoins, et c'est la marge qui en paiera le prix. C'est précisément
pourquoi ses seuils doivent être écrits avant son premier chiffre.

La v3 prend de nouvelles graines et un nouvel espace de noms.

## Entrée 7 — seuils de la version 3, écrits avant tout chiffre

2026-09-12, dans la nuit. La v2 est publiée et close. Aucun code de v3 n'existe et aucune
graine de v3 n'a été jouée. Cette entrée est commitée avant la première ligne de code de la
v3 ; l'horodatage du commit en fait foi.

### Ce que la v2 a réfuté, et qu'il faut acter

L'entrée 4 pré-enregistrait qu'un échec sur le mécanisme de teinte justifierait de
reconsidérer, dans une v3, une règle qui met deux classes voisines à la distance maximale.
**Cette correction est réfutée par la mesure avant d'avoir été adoptée.** Trois règles
comparées sur les mêmes pixels, dix pièces de développement :

| Règle | Lecture par l'oracle |
|---|---|
| dure — L1 sur histogrammes durs, la règle gelée | 73/80 = 91,2 % |
| lissée — convolution circulaire (¼, ½, ¼) | 73/80 = **91,2 %** |
| circulaire — distance du transport optimal | 68/80 = **85,0 %** |

Le lissage ne change rien et le transport optimal dégrade. L'arithmétique dit pourquoi : le
cube orange tombe en classe 1,88 et la sphère jaune en 3,11, soit **1,23 classe d'écart**,
le même ordre de grandeur que le décalage de rendu d'une classe. La référence de l'orange
est à une classe de l'orange en scène *et* à une classe du jaune en scène. Aucune tolérance
ne sépare une cible d'un distracteur situé à la même distance ; elle les rapproche des deux
côtés à la fois.

Ce n'est donc pas la règle qui est fautive. **C'est la palette.**

### Correction 1 — une palette séparée en teinte et uniformément saturée

C'est le candidat restant de l'entrée 3, que j'avais écarté « au prix d'une tâche plus
pauvre ». Il n'appauvrit rien : huit teintes également réparties sur le cercle sont à trois
classes l'une de l'autre, et il y a toujours huit objets.

Mesuré sur les couleurs brutes : séparation minimale **1,23 classe** pour la palette
actuelle, **3,00 classes** pour la candidate. Rendues par le vrai moteur de référence, les
huit références de la candidate tombent en classes 0, 3, 6, 9, 12, 15, 18 et 20 — la
dernière décalée d'une classe, comme le rendu le fait — donc la séparation minimale *après
rendu* est de deux classes, encore le double du décalage.

Elle corrige aussi le second objet, et pour une raison également arithmétique. Le lecteur
exige une saturation ≥ 0,45 **après** rendu, et le rendu ajoute de la lumière blanche, ce
qui ne peut que faire baisser la saturation. Saturations brutes de la palette actuelle :
minimum **0,588**, le cylindre magenta, médiane 0,889. Le magenta dispose donc d'une marge
de +0,138 au-dessus du seuil là où les sept autres ont entre +0,32 et +0,50 — et c'est
exactement pourquoi lui seul devient illisible dans les cellules sombres ou lointaines. La
palette candidate donne les huit à S = 0,900, marge +0,45.

Mesure indépendante qui confirme, sur six pièces : chaque objet est lisible dans 13 à 14
cellules sur 15, **sauf le magenta, lisible dans 10**, alors qu'il est *visible* dans 14.

La palette de la v3, figée ici :

```python
("box",      (0.950, 0.095, 0.095, 1.0)),   ("cylinder", (0.950, 0.736, 0.095, 1.0)),
("sphere",   (0.522, 0.950, 0.095, 1.0)),   ("box",      (0.095, 0.950, 0.309, 1.0)),
("cylinder", (0.095, 0.950, 0.950, 1.0)),   ("sphere",   (0.095, 0.309, 0.950, 1.0)),
("box",      (0.522, 0.095, 0.950, 1.0)),   ("cylinder", (0.950, 0.095, 0.736, 1.0)),
```

### Correction 2 — le garde de visibilité mesure dans les termes du lecteur

Pré-enregistrée à l'entrée 5 et conservée : un objet n'est accepté dans une cellule que si
son descripteur y existe, et pas seulement si ses pixels y ont changé.

Vérifié avant adoption, parce qu'un garde plus strict peut rejeter des pièces et que le
seuil n'en tolère que 10 % : sur six pièces, le pire objet est lisible dans 10 cellules sur
15 et le garde doit en trouver 8 distinctes. La marge est suffisante et aucun rejet n'est
attendu. Avec la nouvelle palette ce garde devient un filet de sécurité plutôt que la
correction principale, ce qui est sa juste place.

### Ce qui ne change pas

La règle de comparaison reste celle de l'entrée 1, importée et jamais recopiée. La référence
reste rendue sous l'éclairage de la pièce. La fenêtre centrale des témoins reste, sans être
créditée de rien. Tous les seuils restent : faisabilité ≥ 0,90 avec borne de Wilson ≥ 0,80
et au plus 10 % de pièces rejetées ; marge en succès si la borne BCa ≥ 0,10 ; marge en coût
si ≥ 3 mouvements ; une marge non établie compte comme absente.

### La règle de verdict, examinée puis conservée

Le balayage exhaustif ne peut jamais être déclaré « proche de l'oracle », puisque son écart
de coût vaut toujours environ +15 et que sa marge en coût est donc toujours établie. J'ai
d'abord pris cela pour un défaut. Ce n'en est pas un, c'est le propos : un témoin juste mais
coûteux laisse effectivement la place à un mécanisme juste *et* économe. Et le témoin de
mémoire, lui, coûte exactement ce que coûte l'oracle, donc sa marge en coût n'est jamais
établie et il est « proche » précisément quand sa marge en succès échoue. La porte est donc
portée par le témoin de mémoire — celui qui occupe déjà le coût de l'oracle —, et c'est
correct. **Rien n'est touché.**

### Ce que la v3 teste réellement, et ce qu'elle ne teste plus

À écrire avant les chiffres, sans quoi le résultat se lira mal. **La v3 est construite pour
que la faisabilité passe.** Les deux mécanismes d'échec de la v2 sont traités à leur racine,
et une faisabilité élevée ne sera donc pas une découverte : ce sera une construction. Elle
reste une porte — si elle échoue, c'est qu'un troisième mécanisme existe que je n'ai pas vu
— mais elle cesse d'être informative.

**Ce que la v3 teste, c'est la marge**, et le signe que donne la v2 est défavorable :
l'écart de succès du balayage est tombé de +23,3 à +6,5 points pendant que la tâche devenait
plus lisible. Une palette encore plus lisible peut très bien porter le balayage à parité
avec l'oracle, et rapprocher aussi le témoin de mémoire. Si cela arrive, le critère
d'abandon de D-060 sera atteint pour de bon, et ce sera un résultat.

### Graines et banque

Espace de noms `c1-margin-probe/v3`, même recette. Développement : sous-espace `"dev"`, i de
0 à 9. Banque : sous-espace `"bank"`, i de 0 à 299, soit **300 pièces**. Trois cents et non
deux cents parce que la question est désormais la marge : à 200 pièces, l'intervalle BCa sur
l'écart de succès était large d'environ ±3,2 points, et c'est cette précision-là qui
décidera.

Vérifié à l'écriture : 310 graines toutes distinctes, toutes supérieures à 100 000, aucune
collision avec les 1 696 995 littéraux entiers des 6 660 fichiers Python du dépôt, et aucune
réutilisation des 280 graines déjà dépensées par la v1 et la v2. Première graine de
développement `3541371033` ; première de banque `2205167222`.

Budget attendu : environ 130 secondes.

### Divulgation

La palette de la v3 a été conçue en regardant les mesures de la v2 — ses dix pièces de
développement et la relecture de sa banque. C'est du développement légitime, et c'est aussi
exactement le genre de choix qui doit être daté plutôt que passé sous silence : cette entrée
est commitée avant la première ligne de code de la v3, et la banque de la v3 est neuve.

### Ce que chaque issue voudra dire

- **Faisabilité échouée** — un troisième mécanisme existe, que ni la v1 ni la v2 n'ont
  montré. On corrige encore la tâche ; on ne conçoit toujours pas de mécanisme.
- **Faisabilité passée et un témoin proche de l'oracle** — c'est le critère d'abandon de
  D-060. Le substrat est déclaré épuisé pour C1 et aucun mécanisme n'y est construit. C'est
  l'issue que la v2 rend la plus probable, et elle est écrite ici pour ne pas pouvoir être
  réinterprétée après coup.
- **Faisabilité passée et les deux témoins laissant une marge** — MARGE EXPLOITABLE, et le
  pré-enregistrement de C1 s'écrit enfin.

## Entrée 8 — développement de la v3, avant la banque

2026-09-12, dans la nuit. Dix pièces de développement. Les seuils de l'entrée 7 ne bougent
pas, et aucun paramètre n'a été touché après le premier chiffre ci-dessous.

### Les deux corrections font ce qu'elles promettaient

Sonde de développement : oracle perceptif 10/10, témoin « dernier angle vu » 5/10, balayage
9/10 ; sept pièces brassées sur dix. Le « ÉCHOUE » qu'affiche le lanceur est un artefact de
petit échantillon — à dix pièces, la borne de Wilson d'un 10/10 vaut 72,2 % — et l'entrée 7
dit déjà que dix pièces n'établissent rien.

Mesure bien plus informative, quatre-vingts lectures au lieu de dix tirages de cible :

| Version | Palette et référence | Lecture par objet |
|---|---|---|
| v1 | palette d'origine, référence surexposée | 67/80 = 83,8 % |
| v2 | palette d'origine, référence éclairée par la pièce | 73/80 = 91,2 % |
| v3 | teintes à 3 classes, saturation uniforme | **79/80 = 98,8 %** |

Sept objets sur huit sont lus 10/10 ; le huitième, le cube violet, 9/10. Aucune référence
n'est illisible.

La correction 2 tient elle aussi, et exactement : **zéro objet placé illisible** sur 80,
contre 1,2 % en v2, et **zéro pièce écartée** par le garde plus strict. C'est ce que la
carte de lisibilité annonçait en montrant que le pire objet disposait de 10 cellules sur 15
pour 8 à pourvoir.

438 tests verts, dont dix nouveaux.

### Ce que la règle de verdict renverra, démontré et non supposé

La règle gelée, appliquée à trois jeux de chiffres synthétiques du type attendu :

| Chiffres | Verdict |
|---|---|
| oracle 99 %, mémoire 50 %, balayage 95 % | MARGE EXPLOITABLE |
| oracle 99 %, mémoire 50 %, **balayage à parité, 99 %** | **MARGE EXPLOITABLE** |
| oracle 99 %, **mémoire à parité, 99 %**, balayage 95 % | REJETÉE — MARGE |

C'est la confirmation chiffrée de ce que l'entrée 7 avait établi en raisonnant : la porte est
portée par le seul témoin de mémoire. **Même un balayage exactement aussi juste que l'oracle
laisse le verdict au vert**, parce qu'il paie quinze mouvements.

L'entrée 7 a examiné ce point et conservé la règle, et je maintiens ce choix : un témoin
juste mais coûteux laisse effectivement la place à un mécanisme juste *et* économe. Mais la
conséquence doit être écrite avant la banque, sans quoi un verdict vert se lira pour plus
qu'il ne dit.

**Ce que MARGE EXPLOITABLE voudra dire :** aucun témoin simple n'est à la fois aussi juste
que l'oracle et aussi économe. La mémoire est économe et fausse après un brassage ; le
balayage est juste et paie quinze mouvements. Le coin « juste et économe » est vide, et
c'est ce coin qu'un mécanisme devrait occuper.

**Ce que cela ne voudra pas dire :** que C1 résiste aux politiques simples. Si le balayage
atteint la parité, alors une politique triviale résout bel et bien C1 — au prix de quinze
fois le coût. Cela ne voudra pas dire non plus qu'un mécanisme est apprenable, seulement
qu'il y a de la place pour un.

### Prédiction avant la banque

Écrite ici pour que la banque ne surprenne personne, comme aux entrées 2 et 5.

**Faisabilité : 97 à 100 % attendus sur 300 pièces.** À 98,8 % de lecture par objet, le
seuil ponctuel de 90 % passe avec une large marge. Ce n'est pas une découverte, c'est la
construction annoncée à l'entrée 7.

**Marge.** Le témoin de mémoire est vers 50 % avec un écart d'environ +50 points : sa marge
en succès devrait s'établir sans difficulté, donc il ne sera pas proche. Le balayage est à
90 % contre un oracle à 100 % en développement ; à 300 pièces son intervalle BCa vaudra
environ ±3 points, et j'attends son écart de succès entre 0 et +10 points — donc sa marge en
succès est incertaine, tandis que sa marge en coût, +15 mouvements, est structurelle.

**Le verdict attendu est donc MARGE EXPLOITABLE**, porté par le témoin de mémoire. Je
l'écris avant de jouer pour qu'il ne puisse pas être présenté ensuite comme une surprise, et
pour que sa limite ci-dessus se lise en même temps que lui.

Le chiffre qui méritera vraiment d'être lu n'est pas le verdict : c'est **l'écart de succès
du balayage**. Il valait +23,3 points en v1, +6,5 en v2. S'il atteint zéro en v3, la lecture
honnête est que C1 se résout par la force brute et que la seule monnaie restante est le coût
en mouvements.

### Gel

Quinze sources : les trois de la v3, les trois de la v2 et les neuf de la v1, ces douze
dernières hachées pour certifier qu'elles n'ont pas bougé. Manifeste
`docs/research/c1_probe_v3_manifest.json`, archive
`data/processed/experiments/c1_probe_v3/source_v1`, convention `source_v1` de D-061.

## Entrée 9 — la banque de la v3, et le premier verdict vert

2026-09-12. Trois cents pièces réservées, jouées une seule fois après le gel (`b668872`,
gelé à 02:51:42), en 132 secondes. Aucune pièce écartée par les gardes ; contrôle de
notation 100 % ; 49 % des épisodes brassés. Une seconde partie est refusée. Après la banque,
les quinze sources gelées sont intactes, ainsi que les manifestes de la v1 et de la v2.
Résultats : `docs/research/c1_probe_v3_results.json`.

### Les deux chiffres

**Faisabilité : 298 sur 300, soit 99,3 %**, borne de Wilson à 95 % [97,6 % ; 99,8 %], contre
un seuil ponctuel de 90 % et une borne de 80 %. **Elle passe.**

**Marge**, contre l'oracle perceptif :

| Témoin | Succès | Écart apparié | Coût | Marge |
|---|---|---|---|---|
| dernier angle vu | 49,3 % | +50,0 pts [BCa +44,0 ; +55,3] | 1,0 (+0,0) | en succès |
| balayage exhaustif | 88,3 % | +11,0 pts [BCa +7,7 ; +14,7] | 16,0 (+15,0) | en coût |

Le balayage n'établit **pas** de marge en succès : sa borne BCa vaut +7,7 points, sous le
seuil de +10. Sa marge est celle du coût, et elle est structurelle.

**VERDICT : MARGE EXPLOITABLE.** C'est le premier verdict vert du programme ouvert par
D-060.

### La prédiction de l'entrée 8, confrontée

| Écrit avant la banque | Mesuré |
|---|---|
| faisabilité 97 à 100 % | 99,3 % |
| mémoire vers 50 %, écart vers +50 points | 49,3 %, +50,0 |
| balayage : écart entre 0 et +10 points | **+11,0, au-dessus de la bande** |

Le seul écart à la prédiction va dans le sens qui compte. Je craignais, aux entrées 7 et 8,
que le balayage converge vers la parité à mesure que la tâche devenait lisible. **Il s'en
éloigne** : +23,3 points en v1, +6,5 en v2, +11,0 en v3. L'explication est mesurable : entre
la v2 et la v3 le balayage progresse, de 82,5 % à 88,3 %, mais l'oracle progresse davantage,
de 89,0 % à 99,3 %. La crainte est réfutée, et il faut le dire aussi nettement qu'elle avait
été écrite.

### La vérification qui pouvait tout invalider

Un verdict vert doit être lu plus sévèrement qu'un rouge. La question qui décide : **la marge
vient-elle du mécanisme que C1 prétend mesurer**, ou d'autre chose ?

| | Pièces | Oracle | Mémoire | Balayage |
|---|---|---|---|---|
| objets immobiles | 153 | 98,7 % | 86,3 % | 86,3 % |
| objets déplacés | 147 | 100 % | **10,9 %** | 90,5 % |

Le témoin de mémoire tombe de 86,3 % à **10,9 %** quand les objets ont bougé. Le balayage ne
bouge pas, de 86,3 % à 90,5 % : il n'a pas de mémoire à tromper. La marge vient donc
exactement de ce que la tâche affirme isoler — se souvenir ne suffit pas quand le monde a
changé — et non d'un artefact de lisibilité ou de coût.

Cohérence interne, gratuite et rassurante : dans les pièces stables, mémoire et balayage
marquent **exactement le même score, 132 sur 153**. C'est attendu — dans une pièce inchangée,
l'image mémorisée d'une cellule et une image fraîche de la même cellule mènent au même choix
— et cela confirme que les deux politiques lisent bien la même chose.

### Où le balayage perd ses pièces

Trente-cinq échecs sur 300, dont **deux seulement** partagés avec l'oracle : trente-trois lui
sont propres. Quand il échoue, la distance qu'il retient est *plus petite* que quand il
réussit — médiane 0,776 contre 0,995. Il ne manque donc pas d'information : **il trouve un
faux ami**, plus ressemblant que la vraie cible.

C'est précisément la différence entre lire les pixels exacts d'un objet, ce que l'oracle a le
droit de faire, et lire une cellule entière, ce qu'un agent doit faire. **Cette différence
est toute la marge en succès**, et elle est de nature perceptive, pas mnésique. Un mécanisme
qui voudrait la prendre devrait apprendre à isoler un objet de sa cellule.

### Les deux pièces manquées par l'oracle, et un défaut de ma palette

Relecture déterministe conforme. Les deux échecs sont le même objet, le cube vert
`(0,095 ; 0,950 ; 0,309)` : référence en classe 9, objet vu en classe 8.

En cherchant pourquoi, je trouve un défaut de conception que je n'avais pas vu en écrivant
l'entrée 7. Espacer huit teintes à `k/8` du cercle avec 24 classes place chaque teinte
exactement sur une **frontière** de classe, puisque `k/8 × 24 = 3k` est entier. Les huit
couleurs de la v3 sont donc toutes au plus mauvais endroit possible vis-à-vis de l'arrondi,
et le moindre décalage infra-classe les fait basculer. Le vert tombe à 9,0012.

Cela n'a coûté que deux pièces sur trois cents, parce que le décalage est le plus souvent
identique du côté de la référence et du côté de la scène. Mais c'était évitable : décaler la
palette d'une demi-classe mettrait les huit teintes au centre de leur classe. C'est ce qu'une
v4 corrigerait, et aucune v4 n'est nécessaire pour la marge.

### Ce que ce verdict autorise, et ce qu'il n'autorise pas

L'entrée 8 l'a écrit avant la banque ; il vaut maintenant.

**Il autorise le pré-enregistrement de C1.** D-060 interdisait tout mécanisme, tout
pré-enregistrement et toute banque de confirmation « avant que la marge existe ». Elle
existe, elle est chiffrée, et elle vient du bon mécanisme.

**Il n'autorise pas** d'affirmer que C1 résiste aux politiques simples. Le balayage exhaustif
résout 88,3 % des pièces sans mémoire, sans apprentissage et sans mécanisme ; il paie
seulement quinze mouvements au lieu d'un. Le coin vide est « juste **et** économe », et c'est
un coin étroit. Il ne dit rien non plus de l'apprenabilité : il dit qu'il y a de la place,
pas qu'un mécanisme saura l'occuper.

### Ce qui doit précéder la construction

Sous D-062, une décision à fort impact est contredite par un agent qui n'a pas produit le
travail, dans une session distincte. Ouvrir la phase des mécanismes sur C1 en est une : elle
engage le reste du programme sur ce substrat. Le dossier de revue est ce journal, entrées 1
à 9, et les trois résultats publiés.

## Entrée 10 — la revue contradictoire, et les seuils de la sonde complémentaire

2026-09-12. Revue rendue par GPT Astra, qui n'a pas produit ce travail, à la demande
d'Anthony. Dossier : `docs/research/c1_margin_review_request.md`, revue :
`docs/research/c1_margin_review.md`, commit `0bdb686`. **Verdict : AUTORISER AVEC CORRECTIONS
BLOQUANTES.** Cette entrée est commitée avant la première ligne de code de la sonde
complémentaire.

### Ce que j'ai vérifié avant d'intégrer quoi que ce soit

Une revue ne s'accepte pas sur sa signature. J'ai recalculé ses chiffres contre le résultat
brut de la banque v3 : oracle 298/300, mémoire 148/300, balayage 265/300, 147 pièces brassées ;
stable 151 et 132 sur 153, brassé 147 et 16 sur 147 ; 131 des 150 discordances favorables à
l'oracle se trouvent après brassage ; le commutateur privilégié qu'elle décrit récupère bien
118 des 152 erreurs de mémoire, soit 266/300. Son estimation de coût, 8,58 à 9,08 mouvements,
est cohérente avec la comptabilité enregistrée. Tout concorde. Son fichier est en UTF-8 sans
BOM ni CRLF, conforme à D-061.

**Aucune de ses recommandations n'est rejetée.** Je le note sans confort particulier : B1 vise
exactement l'angle que j'avais moi-même inscrit au dossier comme point contradictoire n° 2, et
la revue a raison de le faire passer de « à considérer » à « bloquant ». D-060 exige le témoin
simple **le plus fort disponible**, pas deux témoins commodes ; REF-001 est mort de baselines
mal posées, et une omission connue de son auteur reste une omission.

### Correction B2 — portée du résultat, resserrée

Intégrée telle quelle, et applicable dès maintenant. L'entrée 9 n'est pas réécrite : un
registre daté ne se corrige pas après coup, il se complète.

> La marge publiée est une propriété de **C1 v3 avec `p(brassage) = 0,5`**, la palette v3, le
> lecteur à 24 classes et le moteur gelé. La comparaison brassé/stable est un contrôle de
> manipulation ; elle ne prouve pas la robustesse à une autre fréquence de changement. Les
> taux agrégés et les taux conditionnels `brassé` et `stable` sont toujours publiés ensemble.
> Aucun résultat n'est extrapolé à une autre valeur de `p`. Changer `p`, la palette, le
> lecteur, le garde ou le rendu exige une nouvelle sonde de marge avant construction.

Ce que cela corrige dans mes propres mots : « la marge vient exactement du mécanisme que C1
prétend isoler » était trop fort. Le témoin de mémoire échoue après un brassage **par
construction**, et l'amplitude agrégée de l'écart est réglée par une probabilité que j'ai
fixée à l'étape 2. Un écart perceptif de 12,4 points subsiste d'ailleurs dans les pièces
stables. Le fait non tautologique est ailleurs : le balayage, lui, ne bouge pas (86,3 % puis
90,5 %), donc l'implémentation produit bien la dissociation annoncée.

### Correction B1 — la sonde complémentaire, pré-enregistrée ici

Un seul témoin manque, et c'est celui qui occupe le compromis revendiqué : **mémoriser,
vérifier la seule cellule mémorisée, ne balayer qu'après réfutation.**

**Tâche.** `C1EpisodeV3` strictement inchangé, `p(brassage) = 0,5`, palette v3, lecteur gelé.
Le manifeste recalcule les quinze empreintes de la v3 et refuse toute dérive.

**Politique admissible.** Elle mémorise les quinze vues d'exploration, choisit avec le lecteur
gelé la cellule dont l'image mémorisée est la plus proche de la référence, revisite cette
cellule, puis applique une règle de vérification déterministe. Si la vérification accepte,
elle répond dans cette cellule — un mouvement. Si elle rejette, elle visite chacune des
quatorze autres cellules au plus une fois dans l'ordre de balayage, inclut la vue de
vérification parmi ses candidats frais, et pointe la meilleure cellule selon le même lecteur.
Aucun accès à `moved_between_visits`, `target_cell`, `oracle_object_views`, au masque d'objet,
aux rendus nus ni à la graine.

**Famille de règles de vérification, fixée ici, avant tout chiffre.** Deux formes, toutes deux
calculées avec le lecteur gelé sur la fenêtre centrale, comme les témoins de la v2 :

1. **seuil absolu** — accepter si la distance entre la référence et la vue fraîche de la
   cellule mémorisée est ≤ τ, avec τ pris dans la grille fixe
   `{0,25 ; 0,50 ; 0,75 ; 1,00 ; 1,25 ; 1,50}` ;
2. **comparaison sans paramètre** — accepter si la vue fraîche de la cellule mémorisée est
   plus proche de la référence que la meilleure image *mémorisée* des quatorze autres cellules.

**Sélection.** Uniquement sur les dix graines de développement. **Toutes les variantes non
dominées en succès et en coût sur le développement partent dans la même banque, et l'ouverture
exige qu'aucune ne soit proche de l'oracle.** Cette clause de la revue n'est pas décorative :
sans elle, il suffirait de choisir une règle stricte — qui coûte cher et conserve donc une
marge en coût — pour garder la porte verte, en écartant la règle laxiste qui la ferait tomber.
Une règle laxiste et une règle stricte ne se dominent pas l'une l'autre ; les deux passeront
donc la banque.

**Seuils.** Marge en succès inchangée : borne basse BCa à 95 % de l'écart apparié ≥ 0,10,
10 000 rééchantillonnages, graine 0. Marge en coût **durcie par la revue** : le coût de cette
politique varie d'un épisode à l'autre, donc la marge en coût n'est établie que si la **borne
basse à 95 % de l'écart moyen de coût est ≥ 3**, et non plus la seule moyenne. Méthode et
graine gelées avant la banque. Une incertitude compte comme absence de marge.

**Caractéristique de fonctionnement, calculée avant de jouer.** C'est la leçon de la v1, dont
le dispositif ne pouvait pas passer à sa propre cible. Avec un coût de 1 mouvement en cas
d'acceptation et d'environ 15,5 en cas de repli, la marge en coût cesse d'être établie
au-delà de **70,4 % d'acceptation** à 100 pièces. La mémoire ayant raison dans 49,3 % des
pièces de la v3, une vérification honnête accepte autour de 50 à 60 % : la borne basse vaut
alors 5 à 6 mouvements, loin au-dessus de 3. Le dispositif peut donc passer à sa propre cible,
et il peut aussi échouer — ce qui est exactement ce qu'on attend d'une porte.

**Graines.** Espace de noms `c1-margin-hybrid/v1`, même recette du projet. Développement :
sous-espace `"dev"`, i de 0 à 9. Banque : sous-espace `"bank"`, i de 0 à 99, soit **100
pièces**, jouées une seule fois après le gel. Vérifié à l'écriture : 110 graines distinctes,
toutes supérieures à 100 000, minimum `8620304`, **aucune réutilisation des 590 graines déjà
dépensées** par les trois sondes C1, et aucune collision avec les littéraux entiers du dépôt —
ni avec les 1 697 413 de 6 664 fichiers, périmètre des entrées 1, 4 et 7, ni avec les 25 795
des seules sources du projet. Première graine de développement `3874359381` ; première de
banque `2159935764`, dernière `658077885`.

*Note de méthode, contre moi-même :* mon premier script de vérification excluait `env_windows`
et n'a scanné que 255 fichiers, là où ceux des entrées 1, 4 et 7 en scannaient 6 660. Les
graines sont les mêmes, mais la revendication n'était plus comparable. Les deux périmètres
sont donc rapportés ci-dessus.

**Gel.** Sources hachées et archivées selon D-061 avant la partie, convention `source_v1`.
Aucune banque de rattrapage.

### Ce que chaque issue voudra dire

- **La baseline adaptative n'établit de marge sur aucun axe** — elle est proche de l'oracle.
  Le critère d'abandon de D-060 s'applique : le substrat est déclaré épuisé pour C1, la
  décision devient **REFUSER**, et aucun mécanisme n'est construit. C'est l'issue que la revue
  juge possible, et elle est écrite ici pour ne pas pouvoir être réinterprétée après coup.
- **Elle laisse une marge établie sur au moins un axe, pour toutes les variantes conservées** —
  B1 est levée, et le pré-enregistrement de C1 peut s'écrire, avec P1 à P4 intégrées.
- **La faisabilité historique n'est pas reproduite sur ces 100 pièces neuves** — arrêt : la
  porte v3 ne se transporte pas, et c'est la tâche qu'on réexamine.

Les résultats de développement ne peuvent lever B1.

### P1 à P4, à intégrer au pré-enregistrement de C1 après levée de B1

Acceptées, non rejetées, et rappelées ici pour qu'elles ne se perdent pas : la baseline
adaptative devient le **comparateur primaire** d'un futur mécanisme, l'oracle cessant de
l'être ; l'information admissible, l'oracle et la notation sont séparés strictement, avec un
test de dépendance qui remplace chaque champ privilégié par une valeur contradictoire et
vérifie que la politique ne bouge pas ; le gain mnésique et le gain perceptif sont rapportés
séparément sur les quatre cellules `candidat/baseline × stable/brassé` ; et le défaut de
frontière de la palette v3 reste **gelé et déclaré**, une palette décalée définissant une
nouvelle tâche qui redemanderait sa propre sonde de marge.

## Entrée 11 — développement de la sonde complémentaire, avant la banque

2026-09-12. Dix pièces de développement, les sept variantes de la famille jouées. Les seuils
de l'entrée 10 ne bougent pas.

### Un décompte faux dans l'entrée 10, corrigé

Mon propre test l'a attrapé, et il vaut mieux l'écrire que le laisser passer : les graines déjà
dépensées par les trois sondes C1 sont **590**, et non 570 — 70, 210 et 310, graines de
développement comprises. Les scripts avaient bien vérifié l'absence de réutilisation contre les
590 ; seule ma prose comptait mal. L'entrée 10 est corrigée sur ce point, et sur lui seul.

### Ce que le développement donne

Oracle perceptif 10/10, témoin de mémoire 5/10, balayage 9/10 ; cinq pièces brassées sur dix.

| Variante | Succès | Coût moyen |
|---|---|---|
| `s025` | 90 % | 13,0 |
| `s050` | 90 % | 13,0 |
| `s075` | 80 % | 11,5 |
| `s100` | 80 % | 11,5 |
| `s125` | 80 % | 10,0 |
| **`s150`** | 80 % | **7,0** |
| **`comparaison`** | 80 % | **7,0** |

Trois variantes sont dominées : `s075`, `s100` et `s125` sont égalées en succès et battues en
coût par `s150`. **Les quatre non dominées partent dans la banque** — `s025`, `s050`, `s150` et
la règle sans paramètre — et le sous-ensemble est figé dans `BANK_RULES` par le commit qui
porte cette entrée, avant le gel des sources.

Deux d'entre elles, `s150` et la comparaison, ressortent déjà **« proche de l'oracle »** sur ces
dix pièces. Elles partent quand même. C'est précisément le point de la clause de la revue :
ne garder que les variantes chères conserverait une marge en coût **par sélection**, et ce
serait la manœuvre exacte que cette clause existe pour interdire.

### Pourquoi « proche de l'oracle » ne veut rien dire à dix pièces

La règle de coût durcie demande une borne basse d'intervalle, et un intervalle a besoin
d'épisodes.

| Variante | Écart de coût | Écart-type | BCa à n = 10 | Projection à n = 100 |
|---|---|---|---|---|
| balayage | +15,00 | 0,00 | 15,00 | 15,00 |
| `s025`, `s050` | +12,00 | 6,32 | 4,50 | 10,76 |
| `s150`, `comparaison` | +6,00 | 7,75 | **1,50** | **4,48** |

À dix pièces, la borne basse de `s150` vaut 1,50 pour un écart moyen de 6,0 : l'intervalle est
trop large pour établir quoi que ce soit contre un seuil de 3. Le même artefact se lit sur la
faisabilité, affichée « ÉCHOUE » sur un 10/10 parce que la borne de Wilson y vaut 72,2 %. **Ces
étiquettes de développement ne sont pas prédictives ; seuls les points le sont.** La projection
suppose le même taux d'acceptation sur cent pièces et n'est pas un résultat.

Le point, lui, valide le calcul pré-enregistré : `s150` accepte **60 %** du temps, sous la
bascule de 70,4 % calculée à l'entrée 10 avant de jouer, et la projection donne 4,48 — l'ordre
de 5 à 6 qui y était annoncé. Le modèle de coût se comporte comme écrit, ce qui est la seule
raison de lui accorder du crédit maintenant.

`s150` et la règle sans paramètre donnent des résultats identiques sur les dix pièces, succès
et coût. Elles pourraient se confondre en pratique ; les deux sont conservées, et la banque le
dira.

### Prédiction avant la banque

Écrite ici pour que la banque ne surprenne personne, comme aux entrées 2, 5 et 8.

Faisabilité proche de 100 %, et sans intérêt : elle est construite, l'entrée 7 l'a déjà dit.
`s025` et `s050` devraient établir largement leur marge en coût, borne basse autour de 10.

**Tout se joue sur `s150` et la règle sans paramètre.** Leur borne basse projetée vaut 4,5
contre un seuil de 3, donc la marge tiendrait. Mais elle dépend entièrement de leur taux
d'acceptation, mesuré à 60 % sur dix pièces seulement, alors que la marge en coût s'effondre
au-delà de 70,4 %. **Dix points d'écart sur ce taux renversent le verdict.**

**Verdict attendu : MARGE EXPLOITABLE, et sans confiance.** Si le taux d'acceptation monte, ces
deux variantes deviennent proches de l'oracle, le critère d'abandon de D-060 s'applique, C1 est
refusée et aucun mécanisme n'est construit. C'est l'issue que la revue jugeait possible, et
rien dans ce développement ne l'écarte.

### Gel

Dix-sept sources : les deux de la sonde complémentaire, et les quinze de la v3, hachées pour
certifier qu'elles n'ont pas bougé — la correction B1 exige un `C1EpisodeV3` strictement
inchangé. Manifeste `docs/research/c1_probe_hybrid_manifest.json`, archive
`data/processed/experiments/c1_probe_hybrid/source_v1`, convention `source_v1` de D-061.

## Entrée 12 — la banque de la sonde complémentaire : B1 est levée

2026-09-12. Cent pièces réservées, jouées une seule fois après le gel (`bb1b712`), en
79 secondes, avec les quatre variantes non dominées. Aucune pièce écartée ; contrôle de
notation 100 % ; 45 % des épisodes brassés. Seconde partie refusée. Après la banque, les
quatre manifestes sont intacts — hybride 17/17, v3 15/15, v2 12/12, v1 9/9 — et 456 tests
sont verts. Résultats : `docs/research/c1_probe_hybrid_results.json`.

### Les chiffres

**Faisabilité : 99 sur 100, soit 99,0 %**, Wilson [94,6 % ; 99,8 %]. Elle passe, et elle est
sans intérêt : l'entrée 7 avait annoncé qu'elle serait construite.

Marge, règle de coût durcie — borne basse à 95 % ≥ 3 :

| Témoin | Succès | Écart de succès | Coût | Écart de coût | Marge |
|---|---|---|---|---|---|
| dernier angle vu | 50,0 % | +49,0 [BCa +38,0] | 1,00 | +0,00 [BCa +0,00] | succès |
| balayage exhaustif | 90,0 % | +9,0 [BCa +4,0] | 15,93 | +14,93 [BCa +14,85] | coût |
| `adaptatif_s025` | 90,0 % | +9,0 [BCa +4,0] | 13,57 | +12,57 [BCa +11,24] | coût |
| `adaptatif_s050` | 90,0 % | +9,0 [BCa +4,0] | 13,27 | +12,27 [BCa +10,93] | coût |
| **`adaptatif_s150`** | 90,0 % | +9,0 [BCa +4,0] | **8,17** | +7,17 [BCa **+5,68**] | coût |
| **`adaptatif_comparaison`** | 90,0 % | +9,0 [BCa +4,0] | **8,02** | +7,02 [BCa **+5,53**] | coût |

**VERDICT : MARGE EXPLOITABLE.** Aucun témoin simple, adaptatif compris, n'est à la fois aussi
juste que l'oracle et aussi économe. **B1 est levée.**

### La prédiction de l'entrée 11, confrontée

| Écrit avant la banque | Mesuré |
|---|---|
| faisabilité proche de 100 % | 99,0 % |
| `s025` et `s050` : borne basse de coût autour de 10 | 11,24 et 10,93 |
| `s150` et la comparaison : borne projetée 4,5 contre un seuil de 3 | **5,68 et 5,53** |

Les trois tiennent. La borne des deux variantes pivots est même un peu meilleure que projetée,
parce que leur taux d'acceptation est descendu de 60 % en développement à 52 et 53 % ici, ce
qui creuse l'écart de coût. La bascule calculée avant de jouer, 70,4 %, n'a jamais été
approchée.

Contrairement au développement, `s150` et la règle sans paramètre **ne donnent pas les mêmes
résultats** : 8,17 contre 8,02 de coût, 52 % contre 53 % d'acceptation, 87,3 % contre 89,1 %
dans les pièces stables. Les emporter toutes les deux était le bon choix.

### Ce que la banque apprend vraiment, et qui n'est pas le verdict

**1. La baseline adaptative égale le balayage exhaustif pour la moitié du prix.** Les deux
atteignent 90,0 % ; l'un coûte 15,93 mouvements, l'autre 8,02. Le témoin simple le plus fort
disponible n'était donc pas celui que la v3 avait joué, et la revue avait raison de bloquer
là-dessus. Sa propre estimation, « autour de neuf mouvements », tombe à 8,0 : elle était juste.

Conséquence directe sur ce que la marge veut dire. Le coin laissé à un mécanisme n'est plus le
contraste 1 contre 16 que suggérait la v3 : il vaut **+9 points de succès et −7 mouvements**
contre une politique qui n'apprend rien. C'est réel, c'est mesuré, et c'est étroit.

**2. Une règle de vérification triviale est déjà un détecteur de changement quasi parfait.**
Taux d'acceptation de la vérification, par condition :

| Variante | Global | Pièces stables | Pièces brassées |
|---|---|---|---|
| `s025` | 16,0 % | 29,1 % | 0,0 % |
| `s050` | 18,0 % | 32,7 % | 0,0 % |
| `s150` | 52,0 % | **90,9 %** | **4,4 %** |
| `comparaison` | 53,0 % | **90,9 %** | **6,7 %** |

Un seuil sur une distance d'histogramme sait, neuf fois sur dix, si le monde a changé depuis
l'exploration. « Se souvenir, et ne vérifier que lorsque c'est utile » — la phrase de l'entrée 1
qui décrivait ce que C1 devait faire émerger — est donc déjà obtenue par une règle qu'on écrit
en trois lignes. Ce qu'un mécanisme appris pourrait ajouter s'en trouve resserré d'autant, et
il vaut mieux l'écrire maintenant qu'après avoir construit quelque chose.

**3. Les erreurs qui restent sont perceptives, pas mnésiques.** Taux conditionnels, publiés
ensemble comme la correction B2 l'exige :

| | Pièces | Oracle | Mémoire | Balayage | `s150` | `comparaison` |
|---|---|---|---|---|---|---|
| stables | 55 | 100 % | 87,3 % | 87,3 % | 87,3 % | 89,1 % |
| brassées | 45 | 97,8 % | 4,4 % | 93,3 % | 93,3 % | 91,1 % |

Les politiques adaptatives réussissent **mieux** quand les objets ont bougé (93,3 %) que quand
ils sont restés en place (87,3 %). Ce n'est pas un paradoxe : une pièce brassée fait échouer la
vérification, donc déclenche le balayage complet et récupère sa justesse ; une pièce stable
fait accepter la réponse mémorisée, avec les erreurs de lecture qu'elle contient déjà. Le
plafond de ces politiques est donc fixé par la **perception**, exactement ce que la correction
P3 demandera de distinguer d'un gain mnésique.

### Ce qui est autorisé maintenant

B1 et B2 sont levées. Le pré-enregistrement de C1 peut s'écrire, avec P1 à P4 intégrées, et
c'est la seule chose que ce verdict autorise. En particulier, P1 prend tout son sens : le
comparateur primaire d'un futur mécanisme est la **baseline adaptative gelée ici**, à 90,0 %
pour 8,02 mouvements — et non l'oracle, ni le balayage, ni le témoin de mémoire.

Ce que rien n'autorise encore à dire : qu'un mécanisme saura prendre ces neuf points et ces
sept mouvements. La marge existe, elle est étroite, et une part de ce qu'elle contient est un
problème de perception que la mémoire ne résoudra pas.

## Entrée 13 — le pré-enregistrement de C1, et une objection contre ma propre baseline

2026-09-12. `docs/research/c1_preregistration.md`, écrit et commité avant la première ligne de
code du mécanisme. Il fixe la question, l'hypothèse, les comparateurs, l'information
admissible, les métriques, les marges, les graines et la règle d'arrêt, et intègre les quatre
corrections non bloquantes P1 à P4 de la revue.

### Une objection que je porte contre mon propre travail

En rédigeant la section des comparateurs, j'ai relu l'implémentation du repli de la baseline
adaptative : elle visite les quatorze cellules restantes **sans jamais s'arrêter**, puis
choisit la meilleure. C'est ce que la correction B1 spécifiait, et je l'ai implémenté
fidèlement. Mais une politique qui s'arrête au premier appariement suffisant visiterait 7,5
cellules en moyenne, pour un coût total attendu de **4,52 mouvements au lieu de 8,02**.

Conséquence directe : **la marge en coût contre l'oracle tomberait de 7,02 à 3,52 mouvements**,
et la moitié de l'espace annoncé à l'entrée 12 est un artefact de ma baseline plutôt qu'une
place réelle pour un mécanisme.

Deux choses en découlent, et aucune n'est confortable.

B1 **survit** : 3,52 reste au-dessus du seuil durci de 3, donc aucune des conclusions publiées
n'est retirée. Mais le vrai concurrent d'un mécanisme se situe vers 4,5 mouvements, pas 8,0, et
le pré-enregistrement en fait sa **porte 3** — pas une référence. La classer référence pour la
mettre à l'abri serait la faute exacte qui a rendu REF-001 non informative, et que la revue
vient de me reprocher sur un témoin voisin. Elle se conçoit et se gèle sur graines de
développement, avec la même clause qu'en B1 : toutes ses variantes non dominées partent dans
la banque, et le mécanisme doit battre chacune d'elles.

### Deux bornes mesurées, écrites avant de concevoir

**Le placement après brassage est uniforme** — `_draw_placement` tire sans remise et sans
structure. Rien n'est apprenable sur *où* un objet est parti, donc aucun mécanisme ne gagnera
en devinant la destination.

**La détection du changement est déjà résolue** par une règle à un seuil, qui accepte dans
90,9 % des pièces stables et 4,4 % des brassées. Savoir *quand* vérifier ne demande aucun
apprentissage.

Ce qui reste exploitable est donc étroit et nommé : la conduite de la recherche après
réfutation, via l'exclusion mutuelle des placements et la fiabilité de lecture par apparence.
Le lecteur gelé étant partagé par toutes les politiques, **aucun gain perceptif n'est possible
par construction** — ce qui satisfait P3 structurellement plutôt que par déclaration.

### Ce qui vient ensuite

Le pré-enregistrement engage la construction, donc il est lui-même soumis à contradiction
sous D-062 avant la première ligne de code du mécanisme. Aucun mécanisme n'est écrit d'ici là.

## Entrée 14 — la revue du pré-enregistrement : le mécanisme n'est pas autorisé

2026-09-12. Revue rendue par GPT Astra (`docs/research/c1_preregistration_review.md`, commit
`184612a`). **Verdict : AUTORISER AVEC CORRECTIONS BLOQUANTES**, huit corrections C1 à C8,
toutes exigibles **avant la première ligne de code du mécanisme**, plus un diagnostic préalable
sur une centaine de pièces neuves de développement.

C'est la deuxième revue d'affilée où je n'ai rien à rejeter. Les deux ont trouvé des défauts
réels que j'avais introduits, et celle-ci en trouve davantage que la première.

### Ce que j'ai vérifié avant d'intégrer

- **Son arithmétique sur mon chiffre de 4,52.** Le taux de repli mesuré de `comparaison` vaut
  47 %, et `1 + 0,47 × 7,5 = 4,525`. Elle a raison sur le calcul, et raison de rappeler qu'il
  ignore les faux appariements, les cibles rejetées à la vérification et le pointage final
  quand aucun seuil ne passe.
- **Ses voies de fuite.** `_notify` transmet `target=self._target.index` à la désignation,
  `before` et `after` du placement complet au brassage, et `result` après notation. `answer()`
  ne déplace pas la tête. `look_at` accepte des angles continus. Les quatre points sont exacts.
- **Son objection sur l'uniformité.** `_draw_placement` tire dans `self.usable` et non dans les
  quinze cellules, puis `_place_and_verify` déplace les objets défaillants vers des cellules
  libres, et `C1EpisodeV3._measure` ajoute un garde de lisibilité dépendant de l'apparence.
  La loi finale du placement n'est donc pas celle du tirage.
- **Le taux d'acceptation en pièce brassée** vaut 4,4 % pour `s150` et **6,7 %** pour
  `comparaison`. J'ai cité 4,4 % comme s'il valait pour les deux.

Tout concorde. Le fichier de la revue est en UTF-8 sans BOM ni CRLF.

### Trois choses que j'ai affirmées trop vite, et qui sont corrigées ici

L'entrée 13 n'est pas réécrite — un registre daté se complète. Mais trois de ses formulations
ne tiennent pas.

1. **« Le placement après brassage est uniforme. »** Vrai du tirage, faux de la loi finale.
   L'invariance des ordres de recherche devient donc une *hypothèse nulle analytique*, pas un
   fait mesuré. Le volet « exclusion mutuelle » de H1 est sans objet **sous ses propres
   simplifications** ; il pourrait en retrouver un si la loi réelle s'écarte de l'échangeabilité,
   ce qui n'est pas mesuré.
2. **« La détection du changement est déjà résolue. »** Trop fort. Ce sont des taux de
   vérification, pas une identification du régime, et un objet peut rester dans sa cellule
   après un brassage.
3. **« B1 survit puisque 3,52 reste au-dessus de 3. »** Cette phrase ne peut pas certifier une
   politique qui n'a jamais été jouée : B1 exigeait une **borne basse** d'intervalle, pas un
   coût idéal moyen. Les résultats publiés de B1 restent valides ; c'est ma projection qui ne
   vaut rien tant que la porte 3 n'est pas mesurée.

### La contrainte qui peut fermer la campagne, calculée

La revue demande de vérifier que le coin visé est atteignable. Sur l'axe du coût, le candidat
doit satisfaire `C_M ≤ min_j C_j − 1,5` : avec les portes 1 et 2 à 8,02 et 8,17, et la porte 3
*estimée* à 4,52, la fenêtre praticable est **[1,00 ; 3,02]**, non vide mais étroite. **Si la
porte 3 mesurée tombe sous 2,50, la supériorité en coût de 1,5 devient impossible par
construction.** Sur l'axe du succès, la fenêtre `[0,93 ; 0,99]` reste ouverte.

C'est précisément pourquoi la revue refuse que la porte 3 reste « à concevoir » : la
faisabilité de la question dépend d'un chiffre que personne n'a mesuré.

### Ce qui est exigé, dans l'ordre

**Avant toute ligne de code du mécanisme** — C1 : un diagnostic sur pièces neuves de
développement, et une H1 restreinte au manque réellement observé. C2 : abandonner le BCa des
lignes, dont la couverture n'est pas justifiée pour une politique apprenante, au profit d'un
intervalle de type martingale sur la trajectoire, avec estimand explicite. C3 : spécifier,
mesurer et geler la porte 3, et contrôler la faisabilité du coin. C4 : justifier l'utilité de
chaque marge séparément de la capacité à l'établir. C5 : corriger le sens des issues — une
borne trop large suffit à faire échouer la non-infériorité. C6 : interface à liste blanche,
contrat d'actions fermé, signal d'apprentissage défini, isolation des politiques. C7 : contrat
d'état initial, d'ordre et de rejets, et une véritable étude de puissance. C8 : ablations
pré-enregistrées, l'attribution ne découlant pas du lecteur gelé.

**Le diagnostic vient en premier** et conditionne tout le reste : 40 pièces de réglage puis 60
de diagnostic, indices disjoints, une seule collecte chacune, grille de seuils fixée avant les
chiffres, comparaison à arrêt égal entre ordres puis à ordre égal entre règles d'arrêt.
Plafond de dix minutes de simulation.

### L'issue que cela rend possible

**Si le diagnostic ne montre aucun manque mesurable compatible avec les marges, C1-M1 s'arrête
avant construction.** Ce n'est ni un échec de la sonde de marge, ni l'épuisement du substrat :
B1 reste valide, la tâche n'est pas modifiée, et le résultat serait que la marge de C1 est
réelle mais déjà prise par des politiques simples. Cette issue est écrite ici avant le premier
chiffre du diagnostic.
