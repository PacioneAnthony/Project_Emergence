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
