# Émergence — proposition de changement de substrat

**Date : 10 septembre 2026.** Rédigé par Claude Opus 5 à la demande d'Anthony.

**Statut : proposition.** Aucune campagne n'est lancée, aucune décision antérieure n'est
modifiée, aucune banque close n'est réouverte. Ce document demande un arbitrage.

---

## 1. La thèse

> Les mécanismes cognitifs du projet n'échouent pas parce qu'ils sont mal conçus. Ils
> échouent parce qu'ils sont évalués sur un problème qui ne leur laisse rien à résoudre.
> Il faut changer le substrat avant de changer les mécanismes.

## 2. Ce que dit le dossier des neuf dernières campagnes

Depuis LIFE-009 (juillet) jusqu'à RESILIENCE-002 (aujourd'hui), neuf campagnes ont été
menées sur le même banc : un cou à un axe, observé par cinq scalaires.

| Campagne | Ce qui a été mesuré | Verdict |
|---|---|---|
| LIFE-009 | Marge de l'oracle contre baseline | Fermée au smoke : 2,383 % < 10 % |
| LIFE-010 | Éligibilité du plan | Fermée au démarrage : risque 0,75 > 0,50 |
| LIFE-011 | Marge d'établissement | Fermée : 4,4039 % < 5 % |
| LIFE-012 | Plateaux et borne séquentielle | Fermée : portes 4–6 rouges |
| BODY-SCHEMA-001 | Prévision, incertitude, faute | Prévision **oui**, incertitude et faute **non** |
| BODY-SCHEMA-002 | Prévision F, calibration E, agence A | F **oui**, E et A **non** |
| CUMULATIVE-001 | Rétention, choix avant échéance, contrôle | Rétention et choix **oui**, contrôle **non** |
| RESILIENCE-001 | Détection, récupération, reprise | Portes **oui**, mais life-04 à 50 % de réussite |
| RESILIENCE-002 | Récupération, choix actif, moniteur | **Aucune des trois portes** |

Le motif est net et il n'est pas aléatoire :

**Tout ce qui relève de la régression réussit. Tout ce qui demande au système de savoir
quelque chose sur lui-même ou de choisir correctement échoue, ou ne se réplique pas.**

La prévision d'angle progresse campagne après campagne, jusqu'à 0,0795° — une précision
qui n'a plus d'usage. En face : l'incertitude n'est jamais qualifiée, la détection de
faute échoue contre « il y a moins de mouvement », le contrôleur d'orientation n'améliore
aucune trajectoire, le moniteur d'honnêteté est contredit sur 22 clôtures sur 57, et le
choix actif d'expériences gagne +17,77 % en développement puis perd −15,20 % en validation.

C'est la signature d'un substrat où prédire est facile et où choisir ne sert à rien.

Le code le confirme. L'agent de RESILIENCE-002 (`learning/resilience_002_agent.py:21`) est
un MLP `14→64→64→1` qui ne prédit qu'un **résidu** autour d'un prior analytique faisant
déjà l'essentiel du travail (`learning/resilience_002_agent.py:12`). Son monde tient en
cinq scalaires (`learning/body_schema_002.py:24`). Sur ce problème, une ridge est presque
optimale — et le dossier le dit déjà : « la ridge simple est légèrement meilleure sur cinq
cas sur six ».

Quatre campagnes sont mortes sur une porte de faisabilité ou de marge **avant même de
tourner**. Le projet mesure donc déjà correctement la marge disponible. Il l'applique
seulement à la variante proposée, jamais au banc lui-même. Or c'est le banc qui est vide.

## 3. Ce qu'un substrat doit fournir

Un mécanisme ne peut démontrer sa valeur que si le monde contient le problème qu'il
prétend résoudre. Quatre propriétés suffisent, et le banc actuel n'en offre aucune.

| Mécanisme | Propriété nécessaire | Banc actuel |
|---|---|---|
| Mémoire | Observabilité partielle : on ne peut pas tout voir à la fois | Non — l'état tient dans l'observation |
| Résilience | Non-stationnarité non annoncée, aux conséquences visibles | Partiel — une rupture, un seul paramètre |
| Consolidation, rejeu | Interférence entre acquis | Non — l'oubli naïf est « généralement faible » |
| Exploration active | Budget d'action très inférieur à l'espace à connaître | Non — trois catégories, tout est visitable |
| Formation de sous-objectifs | Une tâche qui se décompose | Non — un seul angle à atteindre |

Il manque aussi une cinquième chose, transversale : **une réussite comportementale
mesurable qui ne soit pas une erreur de régression déguisée.**

## 4. La proposition : le cou qui voit, à deux axes

L'essentiel existe déjà et n'a jamais été assemblé. Le jumeau MuJoCo du banc
(`sim3d/bench_model.py`) contient une pièce meublée, des panneaux muraux contrastés, un
éclairage, un objet externe mobile sur rail, une caméra embarquée de 30° de champ, un
télémètre et une centrale inertielle. `sim3d/bench_env.py` sait déjà rendre cette caméra.
`learning/visual_jepa.py` fournit un encodeur convolutif conditionné par l'action.
Le noyau persistant, le `FunctionalStore`, les statistiques appariées et l'infrastructure
de reprise sont qualifiés et réutilisables tels quels.

Deux changements seulement :

**(a) La vision entre dans la boucle.** L'observation n'est plus cinq scalaires, mais une
image plus la proprioception. L'angle du cou cesse d'être l'état du monde : il devient un
pointeur vers une portion du monde. La mémoire acquiert immédiatement un travail réel.

**(b) Un second axe : l'inclinaison.** Le champ de la caméra est de 30° sur une course de
160°, soit environ **5,3 vues distinctes** : trop peu pour une mémoire spatiale digne de ce
nom. Ajouter une articulation d'inclinaison porte l'espace à une quinzaine de cellules et
donne un vrai schéma corporel bidimensionnel, où la commande n'est plus un scalaire
monotone. Le coût est faible : le modèle est généré en XML, il s'agit d'imbriquer un corps
portant la caméra avec une charnière d'axe `0 1 0` et un second actionneur de position —
une trentaine de lignes dans `sim3d/bench_model.py`, plus la mise à jour du contrat
d'observation.

**Point d'honnêteté :** cela s'éloigne du banc physique, qui n'a qu'un servo. C'est sans
conséquence aujourd'hui — le matériel est suspendu sous D-008, le banc v1.0 (ANT-009) n'est
pas construit depuis juin, et un second servo est un composant à quelques euros si le
retour au matériel se décide un jour. Si tu préfères garder l'équivalence stricte avec le
matériel, la proposition reste valable à un seul axe, avec une mémoire spatiale plus pauvre.

## 5. Trois capacités, et pourquoi une baseline bête y échoue

Chaque capacité est décrite avec le témoin simple le plus fort que je puisse lui opposer.
C'est la règle du dépôt et c'est elle qui a permis de conclure honnêtement sur DC-001..005.

### C1 — Retrouver ce qu'on a vu

Pendant une phase d'exploration, la tête balaie la pièce ; plusieurs objets distincts sont
visibles dans différentes cellules. Après un délai occupé par d'autres mouvements, une
requête désigne un objet **par son apparence** (une image de référence) et la tête doit
s'orienter vers lui. Entre deux visites, les objets peuvent avoir changé de place.

*Témoin simple :* revenir au dernier angle où quelque chose a été vu. *Pourquoi il
échoue :* la requête ne porte pas sur le dernier objet vu, mais sur un objet parmi
plusieurs. Il faut une association apparence → lieu, pas un scalaire.

*Mesure :* taux de réussite d'orientation et coût en mouvements, contre balayage exhaustif.

### C2 — Trouver ce qui a changé, sous budget

Entre deux sessions, la pièce change : un objet se déplace, apparaît ou disparaît, et
l'éclairage varie indépendamment. Avec un budget de mouvements très inférieur au nombre de
cellules, la tête doit localiser le changement.

*Témoin simple :* balayage uniforme et différence de pixels contre une image de référence
mémorisée par cellule. Ce témoin est **fort** — il faut le dire, et le battre. *Pourquoi il
échoue :* il confond le changement d'éclairage avec le changement de scène, il est trompé
par une source de bruit visuel, et surtout il ne sait pas **choisir où regarder** : sous
budget serré, il dépense ses mouvements uniformément.

C'est ici, et seulement ici, que l'exploration active a enfin un problème à résoudre : le
budget est la contrainte, et l'allocation change le résultat. C'est aussi le « test de la
télévision » correctement posé, parce que le témoin pixel est précisément celui que le
bruit visuel piège.

*Mesure :* cellules correctement identifiées par mouvement dépensé, séparément selon que
le changement est une vraie modification de scène ou une simple nuisance photométrique.

### C3 — Garder C1 en apprenant C2

La même instance apprend C1, puis C2, et doit rester capable sur C1. Puis la pièce change
de nouveau et elle doit retrouver C1 plus vite qu'une instance neuve.

C'est la démonstration décisive que réclame le diagnostic du 9 septembre. Sur le banc
actuel elle n'a pas de sens, puisque l'oubli naïf y est « généralement faible » : il n'y a
rien à consolider. Sur deux capacités visuelles distinctes portant sur les mêmes cellules,
l'interférence est réelle et l'on peut enfin mesurer si le rejeu paie.

## 6. Le budget, mesuré aujourd'hui et non estimé

J'ai chronométré le simulateur et l'entraînement sur ta machine avant d'écrire ceci.

| Mesure | Résultat |
|---|---|
| Physique seule | 9 242 pas/s — 185× le temps réel |
| Physique + rendu 128×128 | 1 878 pas/s — **37,6× le temps réel** |
| Physique + rendu 64×64 | 1 915 pas/s (le rendu est dominé par un coût fixe) |
| Entraînement VisualJEPA 128×128, RTX 5080 | **18 720 images/s** (1,22 M paramètres) |

Conséquences directes :

- **Le goulot est le simulateur, pas le GPU** — d'un facteur dix. Agrandir le réseau ne
  coûte quasiment rien ; collecter l'expérience coûte tout. C'est l'inverse de l'intuition
  habituelle, et cela oriente toute la conception.
- Vingt vies de trente minutes simulées chacune représentent 1,8 million de pas, soit
  **environ 16 minutes de collecte réelle** avec la vision activée, et autant en
  entraînement. Une campagne complète tient dans l'heure.
- La consigne du brief de juillet — « les campagnes visuelles sont longues, ~250 min » —
  ne décrit plus la machine actuelle.

Rappel de proportion : RESILIENCE-002 a consommé **618 secondes sur les 5 400 autorisées**,
soit 11 %. Le calcul n'a jamais été la contrainte de ce projet. Le facteur limitant est le
nombre de questions intéressantes qu'on pose par semaine.

## 7. Ce qui doit changer dans la méthode, en même temps

Le substrat seul ne suffit pas. Trois corrections, toutes déductibles du dossier :

**Sonde de marge avant pré-enregistrement, appliquée au banc et non à la variante.** La
règle existe déjà — quatre campagnes sont mortes dessus — mais elle est appliquée trop
tard et au mauvais objet. Avant de concevoir un mécanisme, mesurer l'écart entre le témoin
trivial et une borne supérieure sur la tâche. Si l'écart est faible, **la tâche est
rejetée avant qu'un seul mécanisme ne soit écrit**. Appliquée au banc actuel en juillet,
cette règle aurait épargné LIFE-009 à LIFE-012 et RESILIENCE-002.

**Un document par capacité, pas huit par campagne.** RESILIENCE-002 a produit vingt fichiers
dans `docs/research` pour dix minutes de calcul. La rigueur est réelle et a évité de
fausses conclusions ; son volume est calibré pour des campagnes de quatre heures. Un
pré-enregistrement, un rapport, un journal — le reste est un artefact machine.

**Le développement redevient libre.** Déboguer, essayer, jeter, sans rebaptiser chaque
correction en nouvelle hypothèse ni consommer une banque confirmatoire. La confirmation
devient rare et réservée à une capacité dont la marge est déjà établie.

## 8. Ce que cette proposition ne fait pas

- Elle ne démontre aucune émergence, aucune compréhension humaine, aucune autonomie
  ouverte. Elle vise une tête qui associe une apparence à un lieu, remarque un changement
  et conserve les deux. C'est le minimum indispensable avant toute reconnaissance de
  présence humaine — pas un substitut.
- Elle ne garantit pas de réussir. La vision a déjà consommé du temps sur ce projet
  (sondes v1–v3, TV-001, REF-001..003). La différence est qu'on ne demande plus au latent
  de prouver quoi que ce soit par sa propre perte, mais de servir une réussite
  comportementale mesurable.
- **Critère d'abandon, à fixer maintenant :** si la sonde de marge de C1 ne montre pas
  d'écart exploitable entre le témoin simple et la borne supérieure, ce substrat est
  déclaré épuisé lui aussi, et aucun mécanisme n'est conçu dessus. Deux jours de travail,
  pas deux mois.
- Le matériel reste suspendu sous D-008. Rien ici ne demande d'achat ni de manipulation.

## 9. La décision demandée

| Option | Ce que ça implique |
|---|---|
| **(a) Adopter, deux axes** — recommandé | Vision dans la boucle, articulation d'inclinaison ajoutée, C1 → C2 → C3. Écart assumé avec le banc physique à un servo. |
| **(b) Adopter, un seul axe** | Identique, sans toucher au modèle ; équivalence stricte avec le matériel conservée, mais mémoire spatiale limitée à ~5 cellules. |
| **(c) Refuser** | Poursuivre sur le banc actuel. Il faut alors dire quelle question y reste ouverte, sachant que la prévision d'angle est à 0,0795°. |

Je recommande **(a)**.

**Première action si (a) est retenue**, dans l'ordre, et en s'arrêtant à la première porte
rouge : ajouter l'axe d'inclinaison et son contrat d'observation ; construire la tâche C1 ;
exécuter la **sonde de marge** — témoin trivial contre borne supérieure, quelques dizaines
de vies, moins d'une heure de calcul ; publier ce seul chiffre. Aucun mécanisme cognitif,
aucun pré-enregistrement et aucune banque de confirmation avant que cette marge existe.

**Action Anthony :** arbitrer entre (a), (b) et (c). Aucune manipulation, aucun achat.
