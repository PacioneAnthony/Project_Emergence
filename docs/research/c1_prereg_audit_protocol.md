# Protocole du diagnostic C1 — reste-t-il un objet expérimental ?

Date : 2026-09-12. Exigé par la correction **C1** de `docs/research/c1_preregistration_review.md`
(commit `184612a`), qui bloque toute ligne de code du mécanisme tant qu'aucun manque n'est
mesuré. Ce protocole est commité **avant la première mesure**. Rien de ce qu'il fixe ne bouge
ensuite : ni les variantes, ni la grille, ni les graines, ni la règle d'arrêt.

Ce n'est pas une campagne. Aucun mécanisme n'y est construit, aucune banque de confirmation
n'y est ouverte, et son résultat ne qualifie rien.

## 1. La question, et pourquoi elle se pose

Le pré-enregistrement C1-M1 vise l'axe du coût : faire mieux que la meilleure politique simple
en mouvements, à justesse comparable. La revue objecte que cet objet pourrait ne pas exister.

Si, après réfutation de la cellule mémorisée, la cible est échangeable parmi les cellules non
visitées, **tout ordre de recherche a la même espérance de rang** — 7,5 visites sur quatorze —
et l'exclusion mutuelle n'apporte rien, puisqu'on n'apprend qu'une cellule est occupée qu'en
la visitant, ce qui l'aurait de toute façon éliminée. Une politique qui s'arrête correctement
à la découverte occupe alors déjà l'optimum.

Ce théorème vaut dans son modèle. Il ne vaut pas nécessairement pour C1 v3, pour trois raisons
identifiées dans le code et **non mesurées** : `_draw_placement` tire dans `usable` et non dans
les quinze cellules ; `_place_and_verify` relocalise les objets défaillants et
`C1EpisodeV3._measure` ajoute un garde de lisibilité dépendant de l'apparence ; et la
réfutation est un événement sélectionné par les distances visuelles, qui ne garantit ni un
brassage ni l'absence de cible dans la cellule vérifiée.

**Question du diagnostic.** Existe-t-il, à information admissible, un manque de coût que les
règles simples n'absorbent pas déjà — et si oui, vient-il de l'**ordre** de la recherche ou de
sa **règle d'arrêt** ?

## 2. Ce que le diagnostic sépare

Deux comparaisons croisées, et c'est tout leur intérêt :

- **à règle d'arrêt identique, deux ordres** — raster contre distance mémorisée croissante à
  la référence. Un écart contredit le modèle échangeable **pour cette distribution** ;
- **à ordre identique, deux règles d'arrêt** — un seuil global contre une table fixe par
  classe apparente du lecteur. Un écart isole un manque de calibration plutôt que d'ordre.

## 3. Politiques mesurées

Toutes partagent le contrat de la porte 1 : mémoriser les quinze vues d'exploration, choisir
la cellule dont l'image mémorisée est la plus proche de la référence, la revisiter — un
mouvement —, puis appliquer la vérification. Acceptation : répondre là. Réfutation : parcourir
les quatorze autres selon l'**ordre**, s'arrêter selon la **règle d'arrêt**, et pointer la
meilleure cellule vue si l'on ne s'arrête pas dessus. Toutes lisent par le lecteur gelé sur la
fenêtre centrale, et aucune ne touche un champ privilégié.

**Vérification** — `comparaison` (sans paramètre) et `s150` (seuil 1,50), toutes deux gelées
par B1.

**Ordre** — `raster`, l'ordre de balayage des cellules ; `memoire`, distance mémorisée
croissante à la référence.

**Règle d'arrêt**, grille finie fixée ici :

| Nom | Règle |
|---|---|
| `sans_arret` | ne s'arrête jamais ; visite les quatorze et choisit la meilleure. C'est le comportement des portes 1 et 2. |
| `a025` … `a150` | s'arrête à la première cellule dont la distance à la référence est ≤ 0,25 / 0,50 / 0,75 / 1,00 / 1,25 / 1,50 |
| `table` | s'arrête au premier passage sous un seuil **propre à la classe apparente** de la référence — sa classe de teinte dominante — la table étant calibrée sur les 40 pièces de réglage seulement |

**Plan factoriel.** Sur `comparaison` : 2 ordres × 8 règles d'arrêt = **16 variantes**. Sur
`s150` : 2 ordres × {`sans_arret`, `a075`} = **4 variantes**. Vingt au total, toutes jouées sur
les mêmes épisodes, donc appariées.

**Signal admissible de la table.** La classe apparente se lit dans la référence, qui est
admissible. Les seuils sont choisis sur les scores **agrégés** des 40 pièces de réglage, ce que
la correction C6 autorise comme sélection externe de variantes déclarées ; **aucune étiquette
par épisode ne rejoint un état ou une table**. Si aucun signal admissible ne permet de calibrer
la fiabilité par apparence, c'est un **résultat négatif** sur cette composante de H1, et il se
publie comme tel.

**Diagnostic privilégié, jamais un témoin.** Un « arrêt idéal » qui s'arrête au premier passage
sur la vraie cible mesure le rang que l'ordre atteint réellement. Il utilise la vérité terrain,
n'est pas une politique admissible, et sa valeur **ne constitue pas une marge atteignable**.

## 4. Graines

Espace de noms `c1-prereg-audit/v1`, recette du projet. Sous-espace `"tune"`, i de 0 à 39 —
**40 pièces de réglage**. Sous-espace `"diag"`, i de 0 à 59 — **60 pièces de diagnostic**. Une
seule collecte chacune.

*Écart déclaré :* la revue proposait `c1-prereg-audit-dev/2026-09-12` ; j'emploie
`c1-prereg-audit/v1` pour rester conforme à la recette du projet. Le changement porte sur le
nom, pas sur la méthode.

Vérifié à l'écriture : 100 graines distinctes, sous-espaces disjoints, toutes supérieures à
100 000, minimum `26432318` ; aucune collision avec les littéraux entiers du dépôt — ni les
1 697 825 de 6 667 fichiers, ni les 26 207 des seules sources du projet ; et **aucune
réutilisation des 1 010 graines déjà dépensées ou réservées**, y compris les 310 de
`c1-mechanism/v1`, que la revue interdit d'ouvrir. Première graine de réglage `3870390072` ;
première de diagnostic `3787161888`.

## 5. Conduite

Les vingt variantes sont mesurées sur les **40 pièces de réglage**. La table par classe y est
calibrée. Les variantes non dominées en succès et en coût y sont retenues — **toutes**, sans
élagage — et rejouées sur les **60 pièces de diagnostic** sans aucun nouveau réglage.

La tâche est `C1EpisodeV3` strictement inchangée, `p(brassage) = 0,5`, palette v3, lecteur
gelé. Le manifeste recalcule les dix-sept empreintes du gel hybride et refuse l'exécution en
cas de dérive.

**Ce que le juge publie**, par variante et par pièce : succès, mouvements, repli ou
acceptation, fausses acceptations, cibles rejetées à la vérification, et rang de première
visite de la vraie cible. Les conditions `stable`/`brassée` et l'apparence de la cible servent
à l'analyse seulement.

**Métriques de décision** : les différences appariées de coût et de succès entre variantes.

**Plafond** : dix minutes de simulation, tout compris. Le dépasser arrête le diagnostic, et
l'arrêt se publie. Estimation à partir du débit mesuré de la banque hybride — 79,3 s pour
100 pièces et six politiques — de l'ordre de trois à quatre minutes.

## 6. Lecture, fixée avant les chiffres

- **Un écart d'ordre à règle d'arrêt identique** contredit le modèle échangeable pour cette
  distribution, et rouvre le volet « ordre » de H1 — restreint à ce qui est mesuré, sans
  extrapolation hors de la distribution gelée.
- **Un écart limité à la règle d'arrêt** motive une hypothèse plus étroite, sur la calibration
  seule.
- **Un gain de la seule table fixe** améliore la baseline ; il ne justifie **pas** un mécanisme
  apprenant, puisqu'une table calibrée hors ligne l'obtient déjà.
- **L'arrêt idéal privilégié** borne ce que l'ordre peut rapporter au mieux. S'il ne laisse
  presque rien au-dessus de la meilleure règle simple, l'axe du coût est clos.

## 7. Critère d'arrêt, et ce que chaque issue décide

Après les 60 pièces, **aucun élargissement** de la grille, des ordres ou des graines pour
sauver H1.

Le rapport doit identifier un manque observable **non déjà absorbé par les règles simples**,
puis vérifier qu'il laisse une possibilité quantitativement compatible avec le coin de la
correction C3 et les marges de C4. Rappel de la contrainte : sur l'axe du coût, le candidat
devra satisfaire `C_M ≤ min_j C_j − 1,5`. Si la meilleure règle simple descend sous **2,50
mouvements**, la supériorité en coût de 1,5 devient impossible par construction, quel que soit
le mécanisme.

- **Manque mesuré et compatible** → C1 est levée ; les sept autres corrections s'exécutent,
  puis le pré-enregistrement révisé, puis seulement le code.
- **Gain minuscule, borne privilégiée optimiste seule, ou diagnostic inconclusif** → le blocage
  n'est pas levé.
- **Aucun manque compatible** → **C1-M1 s'arrête avant construction.** B1 reste valide, la
  tâche n'est pas modifiée, le substrat n'est pas déclaré épuisé, et le résultat est que la
  marge de C1 est réelle mais déjà prise par des politiques simples. Il se publie comme
  résultat négatif, et l'arbitrage sur la suite revient à Anthony.

## 8. Gel

Les sources du diagnostic sont hachées et archivées avant la première mesure sur les 60 pièces,
selon la convention `source_v1` de D-061, avec les dix-sept sources du manifeste hybride. Le
lanceur refuse la phase de diagnostic tant que les variantes retenues ne sont pas figées, et
refuse de la rejouer.
