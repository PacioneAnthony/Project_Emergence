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
