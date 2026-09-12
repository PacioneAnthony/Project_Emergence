# Revue contradictoire du pré-enregistrement C1-M1

12 septembre 2026. Cette revue porte sur **le pré-enregistrement C1-M1 du
12 septembre 2026, commit `9191a80`**, fichier `docs/research/c1_preregistration.md`.
Elle est distincte de la revue de la sonde de marge et ne réexamine pas ses verdicts.

**Verdict : AUTORISER AVEC CORRECTIONS BLOQUANTES. Le texte actuel n'autorise pas la
première ligne de code du mécanisme.**

Deux prémisses de H1 ne sont pas établies, son attribution causale est insuffisante et
ses intervalles ne correspondent pas à son expérience apprenante. Ajouter une porte
d'arrêt anticipé est nécessaire, mais reporter sa mesure après la construction laisse
entière la question de l'utilité de construire. Les corrections ci-dessous précèdent
donc le mécanisme, dont certaines exigent un diagnostic de développement portant
uniquement sur des témoins simples. Aucun mécanisme plus complexe n'est proposé.

Je ne recommande pas REFUSER immédiatement : l'argument d'impossibilité sous uniformité
est juste dans son modèle, mais ce modèle n'est pas exactement celui du générateur
gelé. Cela constitue une question discriminante peu coûteuse, pas une preuve de marge.
Si le diagnostic ne fournit aucun manque mesuré d'un témoin simple compatible avec
les portes, **ne pas construire C1-M1**. Cette issue n'annule pas B1, ne déclare pas le
substrat épuisé et n'autorise aucune modification de tâche.

## Périmètre et preuves consultées

Le dossier `c1_preregistration_review_request.md` a été lu en premier, puis les sept
sources prioritaires, les entrées 10 à 13 du journal, les classes parentes v2/v3,
le lecteur, le contrôle moteur et D-056, D-060 à D-062. L'arbre était propre sur `main`,
à `ac1a719`. Le pré-enregistrement présent est identique à celui de `9191a80` ; aucun
fichier de mécanisme `c1_mechanism` n'a été trouvé. Les dix-sept sources du manifeste
hybride correspondent à leurs empreintes ; le SHA-256 du manifeste est bien
`ae58e46f536e02feb30179327709e7d70733126278e265b01d6f613067dcbaf0`.

Le JSON publié confirme 99/100 pour l'oracle et, pour `adaptatif_comparaison`, 90/100,
8,02 mouvements et un écart de coût à l'oracle de 7,02, BCa [5,53 ; 8,49]. Ces nombres
portent sur les témoins joués. Ils n'estiment ni le succès de la porte 3 ni la marge
du mécanisme contre elle. Aucune banque n'a été rejouée, aucun épisode nouveau généré,
aucune graine de `c1-mechanism/v1` calculée pour cette revue. Seul ce fichier est ajouté.

## Corrections avant la première ligne de code du mécanisme

### C1 — Objet de H1 : distinguer le théorème d'impossibilité de la tâche réelle

**Point obligatoire 1. Défaut concret.** L'uniformité de `_draw_placement` ne démontre
pas celle de la distribution jouée, encore moins celle du posterior après réfutation.

Dans le modèle idéal de l'objection, après exclusion correcte d'une première cellule,
la cible est uniforme parmi les quatorze autres. Une visite ne révèle que sa cellule,
la reconnaissance est parfaite et une visite coûte une unité. Conditionnellement aux
échecs précédents, chaque cellule restante a probabilité `1/(14-k)` de contenir la
cible. Le rang de découverte est donc uniforme sur 1 à 14 pour toute politique
adaptative sans information latérale : **7,5 visites en espérance**. Reconnaître un
autre objet dans une cellule déjà visitée n'améliore pas le classement des cellules
restantes. L'exclusion mutuelle ne crée aucune marge d'ordre de recherche dans ce
modèle. Une politique qui arrête correctement à la découverte en occupe déjà l'optimum.

Ce résultat ne couvre pas une politique autorisée à sacrifier du succès, la
reconnaissance ambiguë, des observations portant sur plusieurs cellules, ni un mélange
stable/brassé dont le régime est inconnu. Le « premier bon appariement » d'un seuil
bruité n'est pas la première découverte certaine de la cible.

Trois détails du dépôt empêchent surtout de transformer ce théorème en verdict
d'impossibilité sur C1 v3 :

- `C1Episode.__init__` construit `usable` selon l'occlusion de la pièce ;
  `_draw_placement` tire dans **cet ensemble**, pas uniformément dans les quinze cellules.
- `_place_and_verify` conserve les objets valides et déplace les objets défaillants
  vers des cellules libres. `C1EpisodeV3._measure` ajoute un garde de lisibilité dépendant
  de l'apparence. La loi finale peut donc dépendre de la cellule, du fond, de l'objet et
  des autres placements. Le brassage réutilise exactement cette procédure.
- La réfutation est un événement sélectionné par les distances visuelles. Elle ne
  garantit ni un brassage ni l'absence de cible dans la cellule vérifiée. Les images
  d'exploration peuvent renseigner sur la géométrie persistante et la lisibilité, même
  quand elles ne renseignent plus sur la destination d'un objet.

Ces dépendances sont des **possibilités identifiées dans le code**, sans amplitude
mesurée ici. Apprendre un biais de placement induit par le garde serait exploiter une
régularité de ce banc ; ce ne serait pas découvrir une règle générale de déplacement.
`usable` demeure interdit : on ne peut utiliser que ce qui en est inférable des vues.

La « détection déjà résolue » est également trop forte. Le journal donne 90,9 % et
4,4 % d'acceptation pour `s150`, mais **90,9 % et 6,7 % pour `comparaison`**. Ce sont des
taux de vérification, pas une identification parfaite du régime ; un objet peut rester
dans sa cellule après un brassage. La marge résiduelle de détection n'est donc ni
nulle démontrée, ni un besoin d'apprentissage démontré.

**Portée.** H1 ne justifie pas encore la construction. Son volet « ordre par exclusion »
est sans objet sous ses propres simplifications ; son volet fiabilité peut avoir un
objet, mais une table ou une règle d'arrêt calibrée peut l'épuiser.

**Texte normatif intégrable :**

> Retirer l'affirmation d'uniformité de la loi finale et celle de détection résolue.
> Énoncer l'invariance des ordres sous échangeabilité comme hypothèse nulle analytique.
> Avant tout code de mécanisme, mesurer séparément le manque d'ordre de recherche et
> le manque d'arrêt/reconnaissance des témoins simples, sur C1 v3 inchangé. Ne conserver
> dans H1 que le manque observé à information admissible. Une marge contre l'oracle
> privilégié ne démontre pas une marge apprenable. Aucun gain limité aux biais du garde
> n'est extrapolé hors de la distribution gelée. Sans manque mesuré compatible avec
> l'objectif numérique, arrêter C1-M1 avant construction.

**Critère vérifiable.** Le diagnostic décrit plus bas produit une comparaison à arrêt
identique entre ordres, puis à ordre identique entre règles d'arrêt. Le nouvel H1 nomme
le résultat qui le motive, son comparateur, son axe, son amplitude et ses limites.
Une supposition de biais exploitable ou le seul écart à l'oracle ne lève pas C1.

### C2 — Remplacer le BCa des lignes par une inférence sur une trajectoire apprenante

**Point obligatoire 2. Défaut concret.** `bca_bootstrap_ci` tire des indices de lignes
avec remise, puis fait un jackknife en supprimant chaque différence déjà calculée.
Il ne reconstruit pas les états qui auraient résulté d'un autre passé. L'appariement
par pièce demeure utile, mais **n'implique pas l'indépendance des différences**.
Un premier épisode peut modifier les décisions de tous les suivants. Une dérive seule
ne prouve pas une sous-estimation systématique ; le sens de l'erreur peut varier.
En revanche, la couverture annoncée n'est pas justifiée pour la famille admissible.
Le BCa retourne même un intervalle ponctuel lorsque toutes les différences observées
sont égales : l'absence de variation observée n'est pas une preuve d'absence de risque.

Des blocs arbitraires ne réparent pas une mémoire sans horizon ni hypothèse de mélange.
Un test de tendance non significatif n'établit pas l'échangeabilité. Rejouer la banque
réordonnée serait à la fois une autre trajectoire et une violation de la consommation.
Geler la politique après développement permettrait une autre expérience, mais ne
testerait plus l'apprentissage pendant ces 300 épisodes. D-056 fixe une direction
développementale ; il ne contient pas lui-même un théorème d'indépendance ni une
obligation statistique d'utiliser une seule vie de 300 pièces.

**Portée.** Toutes les portes inférentielles sont touchées, y compris celles de
non-infériorité. Leur intersection ne répare aucun intervalle individuel invalide.

**Correction recommandée.** Conserver l'apprentissage en ligne et **restreindre
l'estimand à la moyenne des avantages conditionnels le long de la vie observée**.
Pour une porte `j`, poser `D_t = C_j,t - C_M,t` pour le coût et
`D_t = S_M,t - S_j,t` pour le succès. La cible devient
`mu_n = (1/n) sum_t E[D_t | F_(t-1)]`, où `F_(t-1)` est l'histoire avant la pièce
suivante, incluant l'état appris. Elle n'est ni la performance finale à l'épisode 300,
ni une garantie sur la moyenne de toutes les vies d'apprentissage possibles.
Pour cette dernière revendication, il faudrait des vies indépendantes avec remise
à zéro entre vies et une nouvelle taille justifiée, décidées avant toute banque.

Une construction explicite suffit à rendre la correction implémentable. Imposer les
bornes de coût de C6 ; prendre `b=15` pour le coût, `b=1` pour le succès,
`X_t=D_t/b`, `V_n=sum_t X_t^2`, et fixer `0<lambda<1` avant confirmation. Poser :

```text
psi(lambda) = -log(1-lambda) - lambda
r_n = b * [log(40) + psi(lambda)*V_n] / (lambda*n)
IC_95 = [moyenne(D)-r_n, moyenne(D)+r_n] intersecté avec [-b,b]
```

Cette spécialisation à prédiction nulle utilise `|X_t|<=1`. Pour chaque signe,
`exp(lambda*sum(X_t-E[X_t|F_(t-1)])-psi(lambda)*sum(X_t^2))` est une
surmartingale ; la borne de franchissement vaut 0,025. Les deux queues donnent 95 %.
La preuve ne demande pas de moyenne conditionnelle constante. C'est l'argument
d'auto-normalisation de l'annexe A.8 de
[Howard et al., théorème 4](https://arxiv.org/pdf/1810.08240), ici avec résidu `X_t`
et prédiction zéro. Cette borne simple peut être conservatrice ; sa puissance doit
être mesurée, jamais supposée à partir du BCa.

**Texte normatif intégrable :**

> Les pièces sont neuves, mais les différences d'une politique apprenante ne sont pas
> déclarées indépendantes. La qualification porte sur `mu_n` défini ci-dessus, sur une
> vie entière. Employer l'intervalle martingale spécifié, sans rééchantillonnage des
> lignes. Choisir lambda séparément par métrique et comparateur sur développement,
> dans `{0,1 ; 0,25 ; 0,5 ; 0,75 ; 0,9 ; 0,99}`, en minimisant le rayon projeté à
> n=300 avec le second moment de développement ; départager par le plus petit lambda.
> Geler ces choix avant confirmation ; ne jamais minimiser le rayon sur la banque.
> Le juge calcule les statistiques sans rétroaction vers l'apprenant. Les graines
> suivantes et leurs observations ne sont pas accessibles à l'état courant.
> Appliquer les marges aux bornes de ces intervalles avec les signes déclarés.

Le coût peut garder la borne basse pour la supériorité ; une hausse tolérée de 0,5
équivaut à une borne basse de `D_coût` au moins égale à −0,5. Pour le succès, la
non-infériorité équivaut à une borne basse de `D_succès` au moins égale à −0,02.
Conserver aussi les bornes hautes et les estimations, afin de distinguer inconclusion
et dégradation établie. Le code historique `paired_stats.py` reste gelé ; la nouvelle
méthode appartient à un module distinct et audité.

**Critère vérifiable.** Avant code, formule, estimand, signes, bornes et sélection de
lambda sont committés. Avant banque, tests sur suites synthétiques bornées : différences
nulles, discordances rares, dérive et effet persistant du premier épisode ; audit
analytique de la couverture et vérification numérique des formules. Une simulation
verte complète la preuve, elle ne la remplace pas. La garantie suppose les tirages
neufs du modèle génératif, traités comme aléatoires : le hachage des graines et leur
absence de collision ne prouvent pas à eux seuls une représentativité universelle.

### C3 — Construire la porte 3 avant le mécanisme et contrôler la faisabilité du front

**Point obligatoire 3. Défaut concret.** 4,52 n'est pas le coût d'une politique mesurée.
Il correspond à `1 + 0,47*7,5 = 4,525`, en combinant les 47 % de replis de
`comparaison` avec un rang uniforme et un arrêt correct. Il néglige notamment les
faux appariements, les cibles rejetées lors de la vérification et le pointage final
si aucun seuil ne passe. Son succès n'est pas connu. La phrase du journal « B1 survit
car 3,52 > 3 » ne peut pas certifier cette nouvelle politique : B1 exigeait une
**borne basse**, pas un coût idéal moyen. Les résultats historiques de B1 restent valides.

L'ordre par ressemblance mémorisée doit être inclus : la réfutation conserve des
pièces stables mal lues. Une calibration fixe par apparence doit aussi pouvoir
concurrencer une calibration apprise en ligne. Une règle simple peut utiliser la
distance du meilleur candidat, son écart au second, le nombre de cellules déjà vues
et les descripteurs mémorisés, sans nouvel encodeur. Ces variables ne prouvent pas
qu'une variante soit meilleure ; elles définissent une famille bornée à examiner.

Autre risque : un front non dominé n'est pas un ensemble de témoins simultanément
battables. Avec un coût minimal de 1, une porte dont le vrai coût est inférieur à
2,5 rend une supériorité en coût de 1,5 impossible. Une porte de succès supérieur à
97 % rend +3 points impossible. Plus généralement, sur l'axe coût, le candidat doit
satisfaire simultanément `C_M <= min_j C_j - 1,5` et
`S_M >= max_j S_j - 0,02`. Sur l'axe succès, il faut
`S_M >= max_j S_j + 0,03` et `C_M <= min_j C_j + 0,5`.
Ce sont des conditions sur les vraies moyennes, plus faibles que les portes à
intervalles. Un coin vide ne devient pas pertinent parce que l'intersection est
statistiquement conservatrice.

**Portée.** Une baseline faible ferait attribuer une optimisation triviale au
mécanisme ; un front incompatible rendrait sa qualification impossible par définition.

**Texte normatif intégrable :**

> Spécifier et mesurer la famille simple avant la construction du mécanisme :
> vérification, ordre raster ou par distance mémorisée, arrêt, égalités, cas vide et
> retour final. Inclure un témoin à calibration fixe par apparence pour toute
> revendication correspondante. Les règles utilisent le même contrat d'observation
> et de coût. Publier toutes les variantes essayées ; conserver toutes les non dominées
> selon le protocole de développement fixé avant leurs chiffres. Évaluer la faisabilité
> du coin commun sur l'axe déclaré. Ne retirer aucune variante pour rendre ce coin
> accessible. S'il est incompatible, ne pas ouvrir la banque : arrêter ce candidat
> ou soumettre une autre question explicitement pré-enregistrée avant construction.

**Critère vérifiable.** Tableau complet des variantes et de leurs paramètres, résultats
du diagnostic, calcul des contraintes communes et absence d'élagage après connaissance
des résultats du mécanisme. La porte 3 ne reste pas « à concevoir » lorsque ce dernier
commence. Les portes 1 et 2 et leurs sources historiques restent inchangées.

### C4 — Les marges définissent un compromis, pas l'absence de perte

**Point obligatoire 4. Défaut concret.** Une caractéristique de fonctionnement justifie
éventuellement une taille, pas la valeur d'un progrès. Contre 4,52 mouvements, 1,5
représenterait environ 33 % de réduction, contre seulement 19 % de 8,02 : l'objection
sur la baseline change substantiellement l'effort demandé. À 90 % de succès, accepter
88 % augmente le taux d'échec de 10 % à 12 %, soit **20 % relativement**. Six sur
trois cents est une perte nette attendue, pas un plafond de six nouvelles erreurs :
des réussites récupérées peuvent masquer davantage d'erreurs introduites.

**Portée.** Ni 1,5 ni +3 points ne sont justifiés comme utiles ; « sans perdre en
justesse » contredit la tolérance de 2 points. Aucune fraude de calibration n'est
démontrée, mais la justification présentée ne répond pas à la question.

**Texte normatif intégrable :**

> Justifier séparément l'utilité des quatre marges, puis la capacité à les établir.
> Si 0,02 est conservé, formuler la question comme une réduction de coût avec perte
> moyenne de succès tolérée jusqu'à deux points, et assumer explicitement ce prix
> dans cette simulation. Publier erreurs introduites et récupérées séparément.
> Les seuils 1,5, 0,03, 0,02 et 0,5 ne sont pas abaissés pour compenser une faible
> puissance ou un témoin plus fort. Tout changement motivé de cible précède le code
> du mécanisme et constitue une révision explicite de la question.

**Critère vérifiable.** Le pré-enregistrement révisé contient une justification de
décision pour chaque seuil, distincte des calculs d'incertitude. Le rapport prévu
exprime le compromis en mouvements et en erreurs, sans assimiler non-infériorité et
égalité. Une justification fondée seulement sur « cela peut passer » ne lève pas C4.

### C5 — Garder l'axe déclaré, corriger le sens des issues

**Point obligatoire 5. Défaut concret.** Le gel de l'axe est une protection valable.
Il peut laisser non qualifié un progrès sur l'autre axe : c'est le prix explicite
d'une question confirmatoire unique. Ce n'est pas un faux négatif dissimulé si les
deux axes sont publiés. En revanche, « la non-infériorité échoue — le mécanisme achète
un axe en dégradant l'autre » est faux : une borne trop large suffit à échouer.

**Portée.** L'axe déclaré protège la décision ; l'interprétation actuelle suraffirme
les résultats négatifs. L'absence de correction multiplicative n'est défendable que
pour **une qualification conjonctive**, avec chaque test valide et candidat/axe fixés.
Elle ne garantit pas une couverture simultanée de tous les intervalles et n'autorise
pas la sélection d'un gagnant parmi plusieurs mécanismes sur la banque.
H1 promet actuellement une réduction de coût : une qualification sur le succès
ne confirmerait donc pas cette H1, même avec un axe honnêtement déclaré avant banque.

**Texte normatif intégrable :**

> Un seul mécanisme et un seul axe sont confirmés contre toutes les portes gelées.
> Distinguer dès le pré-enregistrement l'objectif opérationnel à deux axes et H1 sur
> le coût ; un succès sur l'autre axe ne constitue pas une confirmation de H1.
> Un progrès sur l'autre axe est publié comme résultat exploratoire, sans sauver la
> qualification et sans banque de rattrapage. Distinguer : marge établie ; marge
> non établie par manque de précision ; dégradation au-delà de la tolérance établie.
> Ne conclure à un compromis dégradant que dans ce dernier cas. L'intersection contrôle
> l'acceptation globale ; les intervalles individuels ne sont pas annoncés simultanés.

**Critère vérifiable.** Table de décision incluant les trois cas et les deux axes,
testée sur exemples numériques avant la banque. Aucun changement d'axe, de candidat
ou de liste des portes après ouverture.

### C6 — Fermer les voies de fuite et rendre la mesure exécutable

**Point obligatoire 6. Défaut concret.** Falsifier après désignation peut arriver trop
tard : l'état a pu absorber un champ privilégié pendant la construction, l'exploration,
le délai ou un épisode précédent. `observer.on_phase` reçoit notamment l'épisode,
le placement et l'identité cible ; `Outcome` et `answer()` transportent le succès.
Ces accès sont légitimes pour le juge, mais ne doivent pas revenir dans l'apprenant.
La « fiabilité par apparence » n'a aucun signal de vérité admissible défini : apprendre
une probabilité d'avoir raison n'est pas la même chose qu'accumuler des auto-étiquettes.

La liste des actions n'est pas fermée non plus. `look_at` accepte des angles continus,
`answer` note des arguments sans déplacer la tête, et le pré-enregistrement ne borne
ni les revisites ni les images reçues pendant un mouvement. Un mécanisme pourrait
donc gagner en changeant la résolution des regards, en répondant sans pointer, ou en
obtenant des vues intermédiaires gratuites. Ce seraient des changements du contrat.

Enfin, jouer toutes les politiques à la suite dans le même objet simulateur laisse
un état moteur hérité. `settle_at` s'arrête à une tolérance finie. Un monde sans
déplacement d'objets ne garantit pas des images identiques au bit près pour une même
commande issue d'un autre état initial. Ce risque est à tester, pas à déclarer avéré.

**Portée.** Une fuite ou une comptabilité asymétrique invaliderait la qualification.
L'égalité bit à bit reste parfaitement implémentable avec un état apprenant, à
condition de comparer deux clones du **même passé complet**.

**Texte normatif intégrable :**

> La politique reçoit une interface à liste blanche sans épisode, callbacks du juge,
> accès aux fichiers de graines/résultats, ni rendu privilégié. Tout traitement visuel
> passe par les sorties du lecteur et du fenêtrage gelés ; aucun second lecteur,
> masque adaptatif ou voie brute parallèle n'est autorisé. Définir le signal
> d'apprentissage observable et son instant d'utilisation. Succès, cible et diagnostics
> du juge ne sont jamais des retours d'apprentissage. Les scores agrégés de développement
> peuvent sélectionner extérieurement des variantes déclarées ; cette exception ne
> transmet pas les étiquettes par épisode à l'état ou à une table de calibration.
> Une calibration supervisée par vérité terrain requerrait un autre contrat explicite.
>
> Les actions après désignation pointent uniquement les quinze cellules ; chaque
> commande compte, même une revisite ou une commande vers la cellule actuelle. Une
> réponse exige un pointage compté vers la cellule répondue. Coût total entre 1 et 16,
> retour final inclus ; à la limite, répondre à la cellule courante sans commande
> supplémentaire. Définir les observations d'exploration et de délai communes et leur
> chronologie, puis une seule vue stabilisée par commande, sans flux intermédiaire gratuit.
>
> Tester sur développement deux processus isolés initialisés avec les mêmes octets
> d'état et de générateur aléatoire. Falsifier les champs privilégiés, séparément puis
> conjointement, dès le début de l'histoire et à toutes les transitions, y compris
> les retours de score après réponse. Utiliser un fournisseur d'observations admissibles
> inchangé : modifier le placement du simulateur sans figer les vues ne serait pas
> ce test. Comparer actions, état persistant, état aléatoire et réponses sur plusieurs
> épisodes et après reprise. Aucune mutation ne rejoint l'état de production.
>
> Chaque politique commence la pièce depuis le même état initial du simulateur,
> compteurs et observations. Ses vues suivantes résultent de ses propres actions.
> Restaurer cet état par une enveloppe indépendante sans modifier les sources gelées.

**Critère vérifiable.** Matrice des champs et des moments testés, comparaison bit à
bit incluant l'état appris et sa reprise interprocessus, audit des dépendances et
test négatif avec un faux apprenant qui lit volontairement le score ou un callback.
Le test doit détecter ce faux apprenant. Tests du retour final, de la borne 16 et de
l'isolation des politiques. Ces contrôles sont des preuves sur les chemins testés ;
ils ne constituent pas à eux seuls une preuve universelle d'absence de fuite.

### C7 — Définir la vie de 300 pièces et vérifier sa puissance complète

**Point obligatoire 7. Défaut concret.** Trois cents lignes ne sont pas trois cents
réplications indépendantes de l'apprentissage. La moyenne entière évalue une vie avec
son coût d'acquisition, pas sa compétence terminale. Le document ne fixe pas si l'état
initial conserve l'expérience de développement. Dix pièces de développement ne
justifient ni une courbe d'apprentissage, ni le second moment de ses différences.
Le calcul actuel estime une largeur sur le seul coût ; il ignore la puissance de la
non-infériorité en succès et celle de l'intersection avec toutes les variantes.
La corrélation pertinente est celle des **résultats appariés**, pas le simple partage
d'un lecteur. Une vraie réduction de 1,5 ne donne pas une forte probabilité que sa
borne basse dépasse 1,5 : il faut distinguer seuil et alternative de puissance.

**Portée.** La puissance annoncée n'est pas démontrée. Un échauffement exclu ou une
augmentation après examen des premiers résultats rendrait la règle d'arrêt adaptable.

**Texte normatif intégrable :**

> Conserver une vie de 300 pièces tentées, sans échauffement exclu, ni remise à zéro
> de l'apprenant, ni rallonge. Fixer avant code si l'état initial est vierge ou issu
> du développement, et ce que « vierge » contient ; hacher ses octets avant banque.
> Définir l'ordre par l'indice i de dérivation, pas par une expression ambiguë comme
> « ordre des graines ». Les rejets de construction, décidés avant politique, ne sont
> ni remplacés ni utilisés pour apprendre ; publier tentatives et effectif effectivement
> joué, appliquer les intervalles à ce dernier. Après plus de 10 % de rejets, arrêt
> selon la précondition gelée. Une erreur du mécanisme n'est jamais un rejet de tâche.
> Les deux moitiés sont descriptives ; aucune ne remplace la moyenne entière.
>
> Avant code, fixer une grille de scénarios de puissance incluant les frontières des
> portes, une alternative utile strictement au-delà des marges, des discordances rares,
> plusieurs vitesses d'apprentissage et un effet persistant d'un épisode initial.
> Avant banque, calculer la probabilité de franchissement de l'intersection entière
> avec la méthode C2, pour tous les témoins gelés et jusqu'à 10 % de rejets. Exiger
> au moins 80 % à l'alternative utile déclarée, et contrôler les faux passages aux
> frontières. Si le dispositif n'y parvient pas, ne pas ouvrir la banque de 300.
> Ne changer ni sa taille ni ses marges après ouverture.

**Critère vérifiable.** Contrat d'initialisation et de rejet committé avant construction ;
état initial archivé, courbes de développement et étude de puissance complète avant
confirmation. Des suites synthétiques ne consomment aucune pièce et peuvent tester
l'inférence. Si une autre taille ou des vies indépendantes deviennent nécessaires,
il faut une révision préalable explicite, sans toucher à l'espace réservé dans cette
revue. Aucun résultat ne permet aujourd'hui d'affirmer que 300 suffisent.

### C8 — Lecteur gelé : contrôle nécessaire, attribution insuffisante

**Défaut concret.** P3 n'est pas intégrée complètement. Sa revue demandait une ablation
mnésique ; elle a disparu au profit de « aucun gain perceptif possible ». Or conserver
un histogramme et changer sa calibration, son appariement global ou l'accumulation
des vues peut améliorer la reconnaissance effective. Un gain de succès reste possible
à encodeur identique. Inversement, une amélioration dans les pièces stables n'est pas
automatiquement étrangère à la mémoire. La différence stable/brassé ne suffit pas
à attribuer l'effet à l'apprentissage inter-épisodes.

**Portée.** Les portes pourraient établir un avantage opérationnel sans établir H1
ni la nécessité de l'état persistant.

**Texte normatif intégrable :**

> Distinguer qualification opérationnelle et attribution. Conserver le lecteur gelé
> et publier les quatre cellules stable/brassé, sans en déduire une attribution par
> construction. Pré-enregistrer une ablation qui réinitialise uniquement l'état appris
> entre épisodes, avec la même mémoire intra-épisode, le même état initial et les mêmes
> paramètres ; la comparer à la version apprenante sur les mêmes pièces. Pour toute
> revendication d'exclusion mutuelle, prévoir en plus sa suppression isolée. Une table
> fixe de calibration développée sous le même contrat sert d'explication alternative.
> Sans avantage de l'état appris établi sur l'axe revendiqué, ne pas conclure que
> l'apprentissage cause le gain, même si les portes opérationnelles passent.

**Critère vérifiable.** Ablation et contraste signés avant code ; implémentations et
états isolés gelés avant la banque. Une revendication causale exige une borne basse
strictement positive de son contraste pré-enregistré, avec une méthode valide pour
la trajectoire. Sans cela : attribution non établie. Toute ablation est jouée dans
l'unique exécution prévue, jamais en rejouant une banque consommée.

## Expérience discriminante minimale demandée

**Proposition seulement : rien n'est exécuté dans cette revue.** Le manque à mesurer
est le coût évitable d'une recherche avec arrêt anticipé, à succès comparable,
au-delà d'une règle simple fixe. L'expérience ne cherche pas une nouvelle marge
oracle et ne prétend pas confirmer un mécanisme inexistant.

1. Avant mesures, committer un protocole de développement distinct, proposé sous
   `c1-prereg-audit-dev/2026-09-12`, avec recette SHA-256 habituelle et contrôle des
   collisions. Prévoir **40 pièces de réglage puis 60 pièces de diagnostic**, indices
   disjoints, une seule collecte chacune. Aucun accès aux espaces consommés ou à
   `c1-mechanism/v1`, y compris son sous-espace dev, dans ce diagnostic.
2. La baseline à battre est l'adaptatif à vérification `comparaison` puis arrêt anticipé,
   avec repli raster, cas d'absence d'arrêt et pointage final entièrement définis.
   Comparer aussi la vérification `s150`. Fixer avant chiffres une grille finie de
   seuils d'arrêt, incluant l'absence d'arrêt ; comparer, à seuil égal, raster et
   distance mémorisée croissante. Pour isoler l'arrêt, comparer à ordre égal le seuil
   global et une règle fixe par classe apparente du lecteur. Définir cette dernière
   uniquement à partir d'un signal admissible ; si aucun signal ne peut calibrer sa
   fiabilité, c'est un résultat négatif sur cette composante de H1. Aucune recherche
   non bornée de règles, aucun nouvel encodeur.
3. Sélectionner les variantes sur les 40 pièces seulement et rapporter toutes les
   survivantes sur les 60 sans nouveau réglage. Le juge publie succès, mouvements,
   replis, fausses acceptations, cibles rejetées à la vérification et rang de première
   visite de la vraie cible ; stable/brassé et apparence servent seulement à l'analyse.
   Il peut ajouter un arrêt idéal au premier passage sur la cible **comme diagnostic
   privilégié du rang**, jamais comme témoin admissible ni marge atteignable prouvée.
4. Les métriques de décision restent les différences appariées de coût et de succès.
   Une amélioration d'ordre à règle d'arrêt identique contredit le modèle de recherche
   échangeable pour cette distribution ; une amélioration limitée à l'arrêt motive
   une hypothèse de calibration plus étroite. Un résultat des 60 pièces demeure du
   développement : ne pas transformer ses sous-groupes ou son meilleur résultat en
   confirmation indépendante.

**Coût.** Au plus 100 pièces neuves de développement, politiques simples et statistiques
seulement. Le résultat hybride rapporte 79,3 secondes pour 100 pièces et plusieurs
témoins ; c'est un repère, pas une garantie pour cette famille. Plafond proposé :
10 minutes de simulation. Dépasser ce plafond arrête le diagnostic et se publie ;
aucune banque de mécanisme n'est débloquée par un diagnostic incomplet.

**Critère d'arrêt et décision.** À l'issue des 60 pièces, aucun élargissement de la
grille ou des graines pour sauver H1. Le rapport doit identifier un manque observable
non déjà absorbé par les règles simples, puis vérifier qu'il laisse une possibilité
quantitativement compatible avec le coin de C3 et les marges de C4. Un gain de la
seule règle fixe améliore la baseline ; il ne justifie pas un mécanisme apprenant.
Un gain minuscule, une seule borne privilégiée optimiste ou un diagnostic inconclusif
ne lève pas le blocage. Dans ces cas, arrêter C1-M1, conserver ce résultat et laisser
la confirmation fermée. Ce diagnostic est une autorisation conditionnelle d'étudier
le manque, pas une garantie que l'apprentissage saura le combler.

## Ordre des levées et gel final

| Échéance | Ce qui doit être acquis |
|---|---|
| **Avant toute ligne du mécanisme** | C1 : diagnostic et H1 restreinte ; C2 : estimand et formule ; C3 : famille simple mesurée et coin compatible ; C4 : sens des marges ; C5 : règle des issues ; C6 : information, signal d'apprentissage, actions et coût ; C7 : état initial, ordre, rejets et plan de puissance ; C8 : ablations et règles d'attribution. Pré-enregistrement révisé committé. |
| **Avant l'unique banque** | Réalisation des tests C2/C6, reprise sur développement, sources et variantes finales hachées, lambda gelés, état initial archivé, étude de puissance C7 satisfaisante, axe déclaré, ablations intégrées au même lancement et manifeste complet. |

Les détails d'implémentation et leurs résultats de réception peuvent attendre le gel
final ; les contrats, le manque mesuré et les critères ne le peuvent pas. Les nouvelles
sources, le lanceur, l'adaptateur d'information et l'analyse doivent être archivés en
plus des dix-sept sources historiques. Le lanceur vérifie aussi l'état initial, les
paramètres, l'environnement numérique pertinent et la consommation de la banque.

Ni une correction rejetée sans solution équivalente, ni un test reporté à la
confirmation ne lèvent un blocage. La revue n'autorise aucune modification des
sources gelées, aucune réouverture des 700 graines closes, ni C2, C3, promotion ou
matériel. Elle autorise la construction de C1-M1 **uniquement après** ces corrections
et la démonstration préalable d'un objet expérimental encore mesurable.
