# Revue contradictoire — sonde de marge C1

Date : 2026-09-12. Cette revue porte exclusivement sur la sonde de marge C1 du
12 septembre 2026, sur le substrat visuel à deux axes, et sur les commits `5be9c8b` à `738f0ad`.
Elle n'autorise ni C2, ni C3, ni une promotion, ni du matériel.

**Verdict : AUTORISER AVEC CORRECTIONS BLOQUANTES.**

Les chiffres publiés sont cohérents avec les données brutes et établissent une marge pour
les deux témoins effectivement pré-enregistrés, sur la distribution C1 v3 où la probabilité
de brassage vaut 0,5. Ils n'établissent pas encore la proposition plus forte nécessaire à
D-060 : que le témoin simple le plus fort disponible laisse lui aussi une marge. Le témoin
« mémoire, vérification de la cellule mémorisée, balayage seulement si la vérification
échoue » était simple, disponible et directement visé par la tâche ; il n'a pas été joué.
Cette omission est bloquante avant l'ouverture de la phase des mécanismes.

Je ne recommande pas une v4 de la tâche ni une nouvelle conception à l'aveugle. Je demande
une sonde complémentaire étroite, sur la tâche v3 inchangée et avec un nouvel espace de
graines. Si cette baseline n'est pas proche de l'oracle selon la règle durcie ci-dessous,
la phase peut s'ouvrir par le pré-enregistrement de C1. Si elle est proche, le critère
d'abandon de D-060 s'applique et la décision devient REFUSER.

## Périmètre de l'audit et constats matériels

Le dossier demandé a été lu en premier, puis le journal C1, D-060 à D-062, les sources des
trois versions, les manifestes, les résultats publiés et le résultat brut v3. Aucune banque
n'a été rejouée et aucune source gelée n'a été modifiée.

- L'ordre Git est conforme : seuils v3 dans `5be9c8b`, développement dans `0081425`, gel
  dans `b668872`, publication dans `738f0ad`.
- Les quinze empreintes du manifeste v3 correspondent à la fois aux sources présentes et à
  leur archive `source_v1`. L'empreinte du manifeste correspond à celle publiée.
- Le résultat brut contient 300 graines, 300 lignes et zéro rejet. Son résumé est identique
  au résumé publié : oracle 298/300, mémoire 148/300, balayage 265/300, 147 épisodes brassés.
- Les comparaisons sont bien appariées. Il n'existe aucun cas où la mémoire ou le balayage
  réussit alors que l'oracle échoue ; les écarts publiés et leurs signes sont cohérents.
- Les lectures diagnostiques postérieures à la banque n'ont pas changé le verdict gelé.
  Elles ne valent cependant pas nouvelle confirmation.

Une borne descriptive, calculable à partir des seules réponses déjà enregistrées, situe le
risque sans remplacer l'expérience manquante. Un commutateur privilégié qui garderait la
réponse mémoire lorsqu'elle est juste et prendrait sinon la réponse du balayage récupérerait
118 des 152 erreurs de mémoire : 266/300, soit 88,7 %. En reprenant la comptabilité du
balayage enregistré, son coût moyen indicatif est compris entre 8,58 mouvements si la visite
déjà faite est retranchée et 9,08 si elle est répétée ; l'ordre réel du repli doit recompter
le pointage final. Ce calcul post hoc n'est ni une politique réalisable ni une nouvelle
preuve ; il confirme seulement que l'estimation « autour de neuf mouvements » est plausible
et que l'espace utile est beaucoup plus étroit que le contraste 1 contre 16 mouvements.

## Examen des sept points contradictoires

### 1. La probabilité de brassage est bien un cadran, mais pas une fuite

Le résultat est conditionnel à une distribution conçue avec `p(brassage)=0,5`. Pour le
témoin mémoire, la composante mnésique de l'écart est donc largement créée par ce choix :
sur les 153 pièces stables, l'oracle et la mémoire font 151 et 132 succès, écart 12,4 points ;
sur les 147 pièces brassées, ils font 147 et 16, écart 89,1 points. Sur les 150 discordances
favorables à l'oracle, 131 se trouvent après brassage. Modifier la probabilité modifierait
presque linéairement l'écart agrégé.

Ce n'est pas une fuite si le brassage à 0,5 est la définition assumée de C1 : une tâche de
mémoire prospective doit contenir assez de mondes stables et modifiés pour rendre la
vérification utile. En revanche, la chute de la mémoire après brassage est en grande partie
une manipulation check attendue, pas une découverte indépendante. Le fait non tautologique
est que le balayage reste stable, 86,3 % contre 90,5 %, et que l'implémentation produit bien
la dissociation annoncée.

La phrase « la marge vient exactement du mécanisme » est donc trop forte. Une composante
perceptive subsiste déjà sans brassage, et la probabilité 0,5 règle l'amplitude de la
composante mnésique. La sonde autorise une conclusion sur C1 à 0,5, pas sur une famille de
fréquences de changement ni sur un environnement externe.

### 2. La baseline adaptative manquante est un défaut bloquant

Le témoin mémoire ne vérifie jamais ; le balayage vérifie partout. Leur disjonction laisse
vacante par construction la politique intermédiaire la plus évidente. Or D-060 exige le
témoin simple le plus fort disponible, et le journal décrit lui-même « se souvenir, et ne
vérifier que lorsque c'est utile » comme le comportement que C1 doit faire émerger.

La politique proposée n'annulera probablement pas le verdict binaire actuel, car tout repli
fréquent conserve une marge en coût et tout repli rare conserve une large marge en succès.
Mais « probablement » ne remplace pas la mesure exigée avant tout mécanisme. Elle peut aussi
réduire de moitié le budget de mouvements réellement disponible et devenir la vraie baseline
à battre. L'omettre jusqu'au pré-enregistrement du mécanisme ferait précisément construire
avant d'avoir mesuré la marge contre le meilleur témoin simple.

### 3. La porte portée par un seul témoin n'est valide que si l'ensemble est complet

La logique disjonctive de la porte n'est pas fautive en elle-même. Un balayage aussi juste
que l'oracle mais coûtant quinze mouvements laisse effectivement une opportunité de réduire
le coût. Il est donc normal que le balayage exhaustif ne puisse pas fermer la porte sur son
seul succès.

En revanche, cette logique rend la complétude des témoins essentielle. Avec seulement les
deux extrêmes, le verdict vert est presque programmé dès que le brassage fait échouer la
mémoire. Le témoin adaptatif est celui qui peut tester le front succès-coût entre ces
extrêmes. Tant qu'il manque, la règle ne « fabrique » pas arithmétiquement un faux résultat,
mais le protocole lui a présenté un ensemble insuffisant de contradicteurs.

### 4. L'oracle est une borne de faisabilité légitime, pas un point atteignable démontré

Le masque exact par différence avec la pièce nue et la localisation de chaque objet sont
des privilèges inaccessibles à une politique C1 normale. Ils conviennent à une borne
supérieure de lisibilité : si même cet oracle échoue, la tâche est mal construite. Ils ne
démontrent pas qu'une politique non privilégiée peut atteindre 99,3 % en un mouvement.

Les 33 succès propres à l'oracle face au balayage mesurent précisément l'avantage de
segmentation, non une capacité de mémoire. L'écart oracle-balayage ne doit donc pas être
présenté comme « la place disponible pour un mécanisme mnésique ». L'oracle reste utile pour
la faisabilité et le plafond ; la comparaison primaire d'un mécanisme doit être faite contre
une politique admissible recevant les mêmes observations, d'abord la baseline adaptative.

### 5. Les trois versions sont du développement de tâche, pas trois confirmations positives

Les v1 et v2 ont été rejetées sur la faisabilité, leurs résultats ont été conservés et leurs
seuils n'ont pas été déplacés. La v3 a été définie après diagnostic, mais sa palette et son
garde ont précédé une banque neuve. Cela établit honnêtement le résultat sur la tâche v3 ;
cela n'établit pas une robustesse aux palettes, aux lecteurs ou aux moteurs de rendu.

Il existe un jardin de chemins de conception, explicitement divulgué, mais pas une sélection
cachée du meilleur résultat parmi trois banques comparables : les deux premières ne
mesuraient pas une tâche jugée faisable. Une v4 conçue à l'aveugle n'est pas nécessaire pour
la décision présente. En revanche, toute modification supplémentaire de palette, de garde,
de lecteur, d'éclairage ou de fréquence de brassage créerait une nouvelle tâche et ferait
perdre à v3 sa fonction de porte pour cette nouvelle tâche.

### 6. La marge est propre au lecteur de la sonde

L'histogramme dur de teinte est une règle d'audit, pas un substitut prouvé aux représentations
qu'un agent apprendrait. Sa faiblesse protège partiellement la faisabilité parce que l'oracle
l'utilise aussi, mais le masque privilégié protège l'oracle de la pollution de cellule que
subissent les témoins. La protection n'est donc pas symétrique.

Les données montrent deux marges différentes : une marge mnésique, dominée par les épisodes
brassés, et une marge perceptive, visible dans les 33 erreurs propres au balayage. Elles ne
montrent ni que les traits appris conserveront ces écarts, ni qu'ils les fermeront. Le
pré-enregistrement devra séparer les deux causes et ne créditer un mécanisme mnésique que
pour un gain qui ne provient pas simplement d'un meilleur lecteur visuel.

### 7. Les teintes sur les frontières sont mineures seulement pour la tâche v3 inchangée

Deux échecs d'oracle sur 300 ne menacent pas la faisabilité observée ; pour cette banque et
ce substrat exact, le défaut est mineur. Il n'est pas pour autant neutre par principe : les
huit teintes sont toutes sur une frontière, et un décalage d'une demi-classe peut changer les
faux amis du balayage ainsi que l'oracle. L'effet sur la marge n'est pas connu.

La correction sûre n'est donc pas de déplacer maintenant la palette. Il faut conserver la
palette v3 pour la phase C1 autorisée conditionnellement. Si elle est décalée, une nouvelle
sonde de marge sur de nouvelles graines redevient obligatoire avant tout mécanisme. Les deux
échecs actuels restent rapportés ; ils ne doivent être ni filtrés ni « réparés » dans les
résultats.

## Corrections bloquantes avant l'ouverture de la phase des mécanismes

### B1 — Mesurer la baseline « mémoire, vérification, repli » sur une banque neuve

**Défaut concret.** Le jeu de témoins saute directement d'une réponse sans vérification à
un balayage de quinze cellules. Il ne contient pas la politique simple qui vérifie d'abord
la seule cellule suggérée par la mémoire et ne recherche qu'après réfutation.

**Portée.** Le défaut invalide la portée « aucun témoin simple n'est à la fois juste et
économe » et l'identification de la baseline à battre. Il n'invalide ni les 300 épisodes ni
les écarts contre les deux témoins joués.

**Texte normatif intégrable :**

> Avant tout pré-enregistrement de mécanisme C1 et avant toute ligne de mécanisme, exécuter
> une unique sonde complémentaire sous un nouvel espace de noms, proposé
> `c1-margin-hybrid/v1`, sur `C1EpisodeV3` strictement inchangé. La politique mémorise les
> quinze vues d'exploration, choisit avec le lecteur gelé la cellule la plus proche de la
> référence, revisite d'abord cette cellule, puis applique une règle de vérification
> déterministe. Si la vérification accepte, elle répond dans cette cellule. Si elle rejette,
> elle visite chacune des quatorze autres cellules au plus une fois, dans un ordre fixé,
> inclut la vue de vérification dans ses candidats frais et pointe finalement la meilleure
> cellule selon le même lecteur. La règle de vérification, ses éventuels seuils, l'ordre, le
> traitement des égalités et la comptabilité du pointage final sont choisis sur graines de
> développement seulement, puis gelés avant la banque. Si plusieurs seuils ou règles de
> vérification sont essayés, toutes les variantes non dominées en succès et en coût sur le
> développement sont emportées dans la même banque ; l'ouverture exige qu'aucune ne soit
> proche de l'oracle. Aucun accès à `moved_between_visits`, `target_cell`,
> `oracle_object_views`, au masque d'objet ou à la pièce nue n'est autorisé pour décider.
>
> La banque contient 100 graines neuves fixées avant exécution. Elle joue une fois l'oracle,
> les deux témoins historiques et la baseline adaptative sur les mêmes épisodes. Les
> métriques sont l'écart apparié de succès contre l'oracle et l'écart apparié de mouvements
> commandés après désignation. La marge en succès conserve la borne basse BCa à 95 %
> `>= 0,10`. Comme le coût de cette baseline varie par épisode, sa marge en coût n'est
> établie que si la borne basse à 95 % de l'écart moyen de coût est `>= 3`, méthode et graine
> de calcul gelées avant la banque. Une incertitude compte comme absence de marge. Les
> sources sont hachées et archivées selon D-061 avant la partie.
>
> Arrêt : aucune banque de rattrapage. Si la faisabilité historique n'est pas reproduite ou
> si la baseline adaptative n'établit de marge sur aucun axe, elle est proche de l'oracle :
> REFUSER sous D-060 et aucun mécanisme n'est construit. Si elle laisse une marge établie sur
> au moins un axe, B1 est levée et le pré-enregistrement C1 peut s'ouvrir. Les résultats de
> développement ne peuvent lever B1.

**Critère vérifiable.** Un commit antérieur au code de la sonde fixe le namespace, les
100 graines, la famille de politiques admissible, la procédure de sélection sur
développement, les métriques et l'arrêt. Après développement, un second commit fixe la ou
les règles exactes, puis le gel hache les sources et crée l'archive avant l'unique banque.
Le manifeste prouve l'identité de `C1EpisodeV3` et des lecteurs hérités. Le résultat
contient, pour chaque épisode et chaque variante conservée, acceptation ou repli, succès,
coût et accès utilisés. Le verdict suit mécaniquement le texte ci-dessus. Cent épisodes
restent une expérience de quelques dizaines de secondes au débit publié ; si la mesure
tombe près d'un seuil, la règle conservatrice arrête au lieu de réclamer plus de graines.

### B2 — Réduire explicitement la conclusion à la distribution C1 v3

**Défaut concret.** Le dossier passe de la dissociation brassé/stable à une attribution
générale au « mécanisme que C1 prétend isoler », sans rappeler que l'amplitude agrégée est
pilotée par la probabilité 0,5 et qu'une marge perceptive existe aussi dans les pièces
stables.

**Portée.** Le défaut touche l'interprétation et le transport du résultat, pas son calcul.
Sans correction, il permettrait de changer la fréquence de brassage ou le lecteur tout en
continuant à invoquer la porte v3.

**Texte normatif intégrable :**

> La marge publiée est une propriété de C1 v3 avec `p(brassage)=0,5`, la palette v3, le
> lecteur à 24 classes et le moteur gelé. La comparaison brassé/stable est un contrôle de
> manipulation ; elle ne prouve pas la robustesse à une autre fréquence de changement. Les
> taux agrégés et les taux conditionnels `brassé` et `stable` sont toujours publiés ensemble.
> Aucun résultat n'est extrapolé à une autre valeur de `p`. Changer `p`, la palette, le
> lecteur, le garde ou le rendu exige une nouvelle sonde de marge avant construction.

**Critère vérifiable.** Ce paragraphe figure dans l'addendum de marge qui précède B1 et la
sonde complémentaire conserve exactement `shuffle_probability=0.5`. Tout manifeste de C1
référence les empreintes de la tâche v3 ; un écart bloque l'exécution au lieu d'être traité
comme une variante équivalente.

## Corrections à intégrer dans le pré-enregistrement C1 avant construction

Ces corrections peuvent être écrites dans le pré-enregistrement après levée de B1 et B2.
Elles bloquent ensuite la construction tant que leur texte et leurs tests de réception ne
sont pas gelés.

### P1 — Faire de la baseline adaptative le comparateur primaire du mécanisme

**Défaut concret.** Le verdict de marge ne définit pas encore ce qu'un mécanisme doit battre.
Le comparer seulement à « dernier angle » ou au balayage exhaustif permettrait de déclarer
un gain tout en restant dominé par la politique adaptative.

**Portée.** Ce défaut concerne l'évaluation du futur mécanisme, non la sonde v3.

**Texte normatif intégrable :**

> La baseline primaire est la politique adaptative gelée par B1 ; mémoire seule et balayage
> exhaustif restent des repères secondaires. Avant le premier résultat de mécanisme, le
> pré-enregistrement fixe une règle de dominance appariée sur deux axes : succès C1 et
> mouvements après désignation. Il fixe séparément les marges de supériorité et de
> non-infériorité, leurs intervalles, la taille de banque et la règle d'arrêt. Un mécanisme
> n'est qualifié que s'il améliore un axe de la baseline primaire d'une marge établie sans
> dégrader l'autre au-delà de la non-infériorité pré-enregistrée. Le coût de calcul et le
> temps mur sont rapportés, mais ne sont pas confondus avec le coût sensorimoteur.

**Critère vérifiable.** Le manifeste antérieur au code du mécanisme nomme la baseline par
empreinte, les deux métriques, les marges numériques, les méthodes d'intervalle, les graines
et l'arrêt. Le rapport présente les différences appariées candidat-baseline. Aucune variante
plus complexe n'est ouverte sans défaut mesuré de cette baseline et sans ces mêmes champs.

### P2 — Séparer strictement information admissible, oracle et notation

**Défaut concret.** L'API de tâche expose des informations privilégiées utiles à l'oracle et
au score. Une future politique pourrait les consommer accidentellement, tandis que le masque
exact de l'oracle serait ensuite interprété comme une capacité atteignable.

**Portée.** Une telle fuite invaliderait entièrement un résultat de mécanisme. Le résultat
actuel n'est pas touché : ses politiques utilisent ces champs pour notation ou oracle selon
leur rôle déclaré.

**Texte normatif intégrable :**

> Une politique C1 admissible reçoit uniquement les images et proprioceptions de
> l'exploration et du délai, l'image de référence et les observations produites par ses
> propres actions après désignation. `moved_between_visits`, `target_cell`, le placement,
> `oracle_object_views`, les rendus nus, les masques par différence et la graine sont
> interdits à toute décision, feature, sélection, arrêt ou calibration. Ils restent confinés
> au juge et à l'oracle de faisabilité. L'oracle n'est jamais le comparateur primaire d'une
> revendication d'atteignabilité.

**Critère vérifiable.** Un test de dépendance remplace chaque champ privilégié par une valeur
contradictoire après avoir conservé les observations admissibles ; actions, états internes
et sorties de la politique restent identiques, alors que le score du juge peut changer.
L'interface de politique ne transporte aucun objet épisode donnant accès aux propriétés
interdites.

### P3 — Distinguer gain mnésique et gain perceptif

**Défaut concret.** Le lecteur de teinte et le masque privilégié produisent déjà un écart de
12,4 points entre oracle et mémoire dans les pièces stables et 33 erreurs propres au
balayage. Un meilleur encodeur visuel pourrait être crédité à tort comme mécanisme de
mémoire.

**Portée.** Le défaut touche l'attribution causale du futur résultat et sa généralisation ;
il ne retire pas la marge opérationnelle observée.

**Texte normatif intégrable :**

> Le rapport principal publie succès et coût globalement, puis séparément sur épisodes
> stables et brassés. Il publie aussi les discordances contre la baseline adaptative et
> contre le balayage. Une revendication mnésique exige un avantage candidat-baseline dans
> les épisodes brassés qui ne soit pas réductible à un gain comparable dans les épisodes
> stables. Toute modification du lecteur visuel est une composante expérimentale déclarée,
> avec une ablation conservant le lecteur de la baseline. La sonde à histogramme ne sert pas
> de preuve que les traits appris ont la même monnaie.

**Critère vérifiable.** Les quatre cellules `candidat/baseline × stable/brassé`, leurs
effectifs, succès et coûts appariés sont présentes avant toute interprétation. Une ablation
du composant mnésique à lecteur identique est rapportée. Si seul le lecteur change, le
résultat est attribué à la perception et non à la mémoire.

### P4 — Geler le défaut de frontière au lieu de corriger silencieusement la tâche

**Défaut concret.** Les huit teintes v3 sont sur des frontières de classes. Le déplacer
d'une demi-classe après lecture de la banque changerait à la fois la faisabilité et les faux
amis des témoins.

**Portée.** Le défaut est mineur pour la faisabilité v3 observée, mais toute correction
romprait la continuité entre la porte et le mécanisme.

**Texte normatif intégrable :**

> La phase C1 ouverte par cette revue utilise sans modification la palette v3 et les sources
> couvertes par le manifeste v3. Les deux échecs de l'oracle restent dans les résultats et
> la position sur frontière est une limite déclarée. Un décalage de palette, même présenté
> comme correctif mineur, définit une nouvelle version de tâche et remet la sonde de marge
> avant le mécanisme.

**Critère vérifiable.** Le manifeste du pré-enregistrement recalcule les quinze empreintes
v3 et refuse toute dérive. Aucun fichier gelé n'est modifié ou re-gelé. Une nouvelle palette
porte un nouvel identifiant, de nouvelles graines et son propre verdict de marge.

## Décision finale et arrêt

La v3 montre bien une tâche lisible et un contraste réel contre mémoire seule et balayage
exhaustif. Le paramètre de brassage n'est pas une fuite cachée ; c'est une manipulation
constitutive dont la portée doit rester conditionnelle. L'oracle est légitime comme plafond
de faisabilité, mais il ne prouve pas que le coin à 99,3 % et un mouvement est accessible.
Les itérations v1 à v3 sont acceptables comme développement transparent d'une tâche fixe à
partir de v3, et le défaut de frontière ne justifie pas une v4.

La conclusion actuelle reste toutefois incomplète au regard de D-060, car la baseline la
plus évidente occupe précisément le compromis revendiqué et n'a jamais été mesurée. B1 et
B2 doivent être levées avant d'ouvrir la phase des mécanismes. Si la sonde complémentaire
est verte, le pré-enregistrement de C1 peut être écrit avec P1 à P4, puis seulement la
construction peut commencer. Si elle est rouge, le substrat est refusé pour C1 et aucun
mécanisme n'est construit. Dans les deux cas, cette décision demeure sans effet sur C2,
C3, une promotion ou le matériel.
