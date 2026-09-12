# Pré-enregistrement C1-M1 — un mécanisme pour retrouver un objet désigné

Date : 2026-09-12. Capacité C1, premier mécanisme. Écrit sous D-060, après que la sonde de
marge a rendu **MARGE EXPLOITABLE** et que la revue contradictoire de GPT Astra a levé ses
corrections bloquantes B1 et B2.

Ce document est commité **avant la première ligne de code du mécanisme**. Rien de ce qu'il
fixe ne bouge ensuite : ni les comparateurs, ni les métriques, ni les marges, ni les graines,
ni la règle d'arrêt.

## 1. Ce qui autorise ce document, et ce qui ne l'autorise pas

D-060 interdisait tout mécanisme, tout pré-enregistrement et toute banque de confirmation
« avant que la marge existe ». Quatre sondes l'ont mesurée, chacune avec ses seuils écrits
avant ses chiffres :

| Sonde | Pièces | Faisabilité | Verdict |
|---|---|---|---|
| v1 | 60 | 90,0 %, Wilson 79,9 % | REJETÉE — faisabilité |
| v2 | 200 | 89,0 % | REJETÉE — faisabilité |
| v3 | 300 | 99,3 % | MARGE EXPLOITABLE |
| B1, complémentaire | 100 | 99,0 % | MARGE EXPLOITABLE |

Ce qui est autorisé : construire **un** mécanisme et le confronter, sur cette tâche gelée, aux
comparateurs de la section 4. Ce qui ne l'est pas : C2, C3, une promotion, une qualification
universelle, ou la moindre action matérielle (D-008).

## 2. La marge réelle, y compris ce qui la réduit

La meilleure politique simple mesurée est `adaptatif_comparaison` : **90,0 % de succès pour
8,02 mouvements**, contre un oracle perceptif à 99,0 % pour 1 mouvement. Le coin disponible
vaut donc **+9 points de succès et −7,02 mouvements**.

**Ce coin est plus étroit que ce chiffre ne le dit, et il faut l'écrire ici plutôt que de le
découvrir après.** Le repli de la baseline gelée visite les quatorze cellules restantes sans
jamais s'arrêter, puis choisit la meilleure. Une politique qui s'arrête au premier appariement
suffisant visiterait 7,5 cellules en moyenne, pour un coût total attendu de **4,52 mouvements**
— la marge en coût contre l'oracle tomberait de 7,02 à 3,52. Cette politique n'a pas été
jouée ; elle est ajoutée en section 4 comme **troisième comparateur, et comme porte**. La
protéger en la classant simple référence serait exactement la faute qui a rendu REF-001 non
informative, et que la revue vient de sanctionner.

Deux autres faits mesurés bornent ce qu'un mécanisme peut viser.

**Le placement après brassage est uniforme.** `_draw_placement` tire les cellules sans remise
et sans structure : rien n'est apprenable sur *où* un objet est parti. Une politique ne peut
donc pas gagner en devinant la destination.

**La détection du changement est déjà résolue.** Une règle de vérification à un seuil accepte
la réponse mémorisée dans 90,9 % des pièces stables et 4,4 % des pièces brassées. Savoir
*quand* vérifier ne demande aucun apprentissage.

Ce qui reste réellement exploitable, et sur quoi porte l'hypothèse : **la conduite de la
recherche après réfutation**, où la baseline dépense l'essentiel de son coût.

## 3. Question et hypothèse

**Question.** Un mécanisme qui apprend d'un épisode à l'autre peut-il retrouver l'objet
désigné à moindre coût que la meilleure politique simple, sans perdre en justesse ?

**Hypothèse H1.** Deux régularités de la tâche, non exploitées par les comparateurs, sont
apprenables et suffisent à réduire le coût :

1. **l'exclusion mutuelle** — les huit objets occupent huit cellules distinctes, donc
   reconnaître un objet non désigné dans une cellule élimine cette cellule *et* réduit
   l'ensemble des placements possibles pour les autres ;
2. **la fiabilité de lecture, par apparence** — certaines apparences sont lues moins
   sûrement que d'autres par le lecteur gelé, et cette fiabilité s'estime sur les épisodes
   passés. Elle indique quand un appariement médiocre justifie de continuer à chercher et
   quand il suffit à s'arrêter.

**Ce que H1 n'affirme pas.** Ni que le mécanisme améliorera la justesse — le plafond de
succès des politiques simples est fixé par la **perception**, et la mémoire ne le déplacera
pas. Ni que le gain, s'il existe, se transportera à une autre fréquence de brassage, une autre
palette ou un autre lecteur.

**Famille de mécanismes admissible.** Toute politique qui conserve un état entre épisodes et
décide, à chaque instant, quelle cellule regarder ensuite et quand répondre. Elle utilise le
**lecteur gelé sans aucune modification** — c'est la garantie structurelle que P3 exige : un
gain perceptif est impossible par construction, donc tout gain mesuré est attribuable à la
conduite de la recherche.

## 4. Comparateurs — correction P1

Le comparateur primaire n'est plus l'oracle. Il est nommé par empreinte, et non par nom :

| Rôle | Politique | Succès | Coût | Empreinte de la source |
|---|---|---|---|---|
| **Porte 1, primaire** | `adaptatif_comparaison` | 90,0 % | 8,02 | `learning/c1_probe_hybrid.py` `b335c1f5…` |
| **Porte 2** | `adaptatif_s150` | 90,0 % | 8,17 | idem |
| **Porte 3** | arrêt anticipé, à geler | à mesurer | ~4,5 attendu | à figer avant la banque |
| Référence | balayage exhaustif | 90,0 % | 15,93 | `learning/c1_probe_v2.py` |
| Référence | dernier angle vu | 50,0 % | 1,00 | idem |
| Plafond | oracle perceptif | 99,0 % | 1,00 | `learning/c1_probe.py` `93fbaae6…` |

Manifeste de référence : `docs/research/c1_probe_hybrid_manifest.json`, empreinte
`ae58e46f536e02feb30179327709e7d70733126278e265b01d6f613067dcbaf0`.

**La porte 3 se conçoit et se gèle avant la banque.** Elle reprend la politique adaptative en
remplaçant son repli exhaustif par un arrêt au premier appariement dont la distance passe un
seuil, ce seuil étant choisi **sur graines de développement uniquement**. Comme pour B1,
**toutes ses variantes non dominées en succès et en coût sur le développement partent dans la
banque**, et le mécanisme doit battre **chacune** d'elles : sans cette clause, il suffirait de
retenir la variante la plus chère pour se ménager une marge par sélection.

Les références et le plafond sont rapportés à chaque fois, et n'ouvrent ni ne ferment aucune
porte.

## 5. Information admissible — correction P2

Une politique C1 admissible reçoit **uniquement** : les images et proprioceptions de
l'exploration et du délai, l'image de référence, et les observations produites par ses propres
actions après la désignation. Elle peut conserver entre épisodes ce qu'elle a elle-même
observé.

Sont **interdits** à toute décision, tout trait, toute sélection, tout arrêt et toute
calibration : `moved_between_visits`, `target_cell`, `placement`, `oracle_object_views`, les
rendus nus, les masques par différence, `object_visibility`, `usable`, et la graine. Ces
champs restent confinés au juge et à l'oracle de faisabilité.

**Test de dépendance, bloquant.** Après chaque désignation, chaque champ privilégié est
remplacé par une valeur contradictoire, les observations admissibles restant identiques. Les
actions, l'état interne et la réponse du mécanisme doivent être **identiques au bit près** ;
le score du juge, lui, peut changer. Le test échoue, la campagne s'arrête.

L'interface de politique ne transporte aucun objet d'épisode donnant accès à ces propriétés.

## 6. Métriques et portes

**Unité indépendante** : la pièce. Toutes les comparaisons sont **appariées** — le mécanisme
et chaque comparateur jouent le même épisode.

**Deux métriques, et deux seulement.** Le **succès C1** : la cellule répondue est celle de la
cible. Le **coût** : le nombre de mouvements de tête commandés après la désignation. Le temps
de calcul et le temps mur sont rapportés, et ne sont jamais confondus avec le coût
sensorimoteur.

**Axe revendiqué, déclaré avant la banque.** À l'issue du développement, le mécanisme déclare
l'axe sur lequel il prétend gagner — coût ou succès. Ce choix est gelé avec les sources. Il
n'est pas permis de gagner sur le coût contre un comparateur et sur le succès contre un autre.

**Supériorité**, sur l'axe déclaré, contre **chacune** des trois portes :

- axe coût : borne basse BCa à 95 % de la réduction appariée de mouvements **≥ 1,5** ;
- axe succès : borne basse BCa à 95 % du gain apparié de succès **≥ +0,03**.

**Non-infériorité**, sur l'autre axe, contre **chacune** des trois portes :

- perte de succès : borne **haute** BCa à 95 % **≤ 0,02** ;
- augmentation de coût : borne **haute** BCa à 95 % **≤ 0,5** mouvement.

Tous les intervalles : `learning.paired_stats.bca_bootstrap_ci`, 10 000 rééchantillonnages,
graine 0. **Une marge non établie compte comme absente ; l'incertitude ne profite jamais à
l'acceptation.** Le test est une intersection sur les trois portes : conservateur par
construction, il ne demande pas de correction pour comparaisons multiples.

**Précondition de faisabilité.** Sur la banque de confirmation, l'oracle perceptif doit
atteindre ≥ 0,90 avec une borne de Wilson ≥ 0,80, et au plus 10 % des pièces écartées par les
gardes. Sinon la tâche ne s'est pas reproduite : arrêt, et aucun résultat de mécanisme n'est
lu.

**Caractéristique de fonctionnement, calculée avant de jouer** — la leçon de la v1, dont le
dispositif ne pouvait pas passer à sa propre cible. Le coût par épisode de la baseline a un
écart-type de 7,49. Pour établir une borne basse de 1,5 sur 300 pièces, il faut une réduction
moyenne de 1,73 si l'écart-type des différences appariées vaut 2, de 1,95 s'il vaut 4, et de
2,18 s'il vaut 6. Les différences appariées étant fortement corrélées entre politiques qui
partagent le même lecteur, le régime attendu est le bas de cette plage. **Le dispositif peut
donc passer à sa propre cible, et il peut aussi échouer.**

## 7. Attribution du gain — correction P3

Le rapport publie succès et coût **globalement**, puis **séparément sur épisodes stables et
brassés**, ainsi que les discordances appariées contre chaque porte. Les quatre cellules
`mécanisme / baseline × stable / brassé`, avec leurs effectifs, sont présentes **avant toute
interprétation**.

**Une revendication mnésique exige un avantage dans les épisodes brassés qui ne se réduise pas
à un avantage comparable dans les épisodes stables.** Le lecteur visuel étant gelé et partagé,
aucun gain perceptif n'est possible ; si un écart apparaissait malgré tout dans les pièces
stables, il serait déclaré et non crédité au mécanisme.

La sonde à histogramme ne prouve rien sur ce que vaudraient des traits appris. Toute
modification du lecteur définirait une autre expérience.

## 8. Tâche gelée — correction P4

La campagne utilise **sans modification** `C1EpisodeV3` et les quinze sources couvertes par le
manifeste v3, avec la palette v3, `p(brassage) = 0,5`, huit objets, six mouvements de délai,
images 96 × 96 et le garde de visibilité mesurant dans les termes du lecteur. Le manifeste de
la campagne recalcule ces empreintes et **refuse l'exécution** en cas de dérive.

Les deux échecs d'oracle de la v3 restent dans les résultats. La position des huit teintes sur
des frontières de classes est une **limite déclarée**, non corrigée : décaler la palette
définirait une nouvelle tâche et redemanderait sa propre sonde de marge.

## 9. Apprentissage, déterminisme et reprise

Le mécanisme **apprend en ligne**, d'un épisode au suivant, dans l'ordre des graines, sans
remise à zéro : c'est le cadre développemental de D-056. Les comparateurs sont sans état, donc
l'appariement par pièce reste valide.

Le rapport publie les métriques sur la **première et la seconde moitié** de la banque, pour
que l'apprentissage se voie ou que son absence se voie.

**Reprise et déterminisme, bloquants.** Rejouer la banque avec les mêmes graines reproduit la
trajectoire du mécanisme à l'identique. Son état est persistable et restaurable dans un autre
processus, et une reprise à mi-banque donne les mêmes résultats qu'une exécution continue.
Ces contrôles se passent sur graines de développement.

## 10. Graines et budget

Espace de noms `c1-mechanism/v1`, recette du projet : les quatre premiers octets,
gros-boutistes, du SHA-256 du JSON compact `["c1-mechanism/v1", sous-espace, i]`.
Développement : sous-espace `"dev"`, i de 0 à 9. Confirmation : sous-espace `"bank"`, i de 0 à
299, soit **300 pièces**, jouées **une seule fois** après le gel.

Vérifié à l'écriture : 310 graines distinctes, toutes supérieures à 100 000, minimum
`14688807` ; **aucune réutilisation des 700 graines** déjà dépensées par les quatre sondes ; et
aucune collision avec les littéraux entiers du dépôt — ni les 1 697 825 de 6 667 fichiers, ni
les 26 207 des seules sources du projet. Première graine de développement `434294645` ;
première de banque `4094253351`, dernière `2242256186`.

Budget attendu : quelques minutes. Le calcul n'est pas la contrainte.

## 11. Ce que chaque issue voudra dire

- **La supériorité est établie sur l'axe déclaré contre les trois portes, sans infériorité sur
  l'autre** — le mécanisme est qualifié **sur cette tâche**, avec ses limites déclarées. Ce
  n'est ni une qualification universelle ni une promotion vers `CognitiveKernel`.
- **La supériorité échoue contre au moins une porte** — le mécanisme n'est pas qualifié. Le
  résultat négatif est conservé et publié tel quel, avec ses chiffres. Aucune banque de
  rattrapage, aucun réglage a posteriori, aucune seconde partie.
- **La non-infériorité échoue** — le mécanisme achète un axe en dégradant l'autre. Non
  qualifié, et le compromis est publié.
- **La faisabilité ne se reproduit pas** — arrêt technique, aucun chiffre de mécanisme n'est
  lu, et c'est la tâche qu'on réexamine.

## 12. Gel et archive

Avant la banque, toutes les sources dont elle dépend — celles du mécanisme, les trois portes,
et les dix-sept du manifeste hybride — sont hachées dans
`docs/research/c1_mechanism_manifest.json` et copiées octet pour octet sous
`data/processed/experiments/c1_mechanism/source_v1`, selon la convention `source_v1` de D-061.

Le lanceur refuse la banque si une empreinte a bougé, si l'axe revendiqué n'est pas figé, si
les variantes de la porte 3 ne sont pas figées, ou si la banque a déjà été jouée.

## 13. Revue contradictoire

Sous D-062, ce pré-enregistrement est un document à fort impact : il engage la construction.
Il est soumis à contradiction par un agent qui ne l'a pas rédigé, **avant** la première ligne
de code du mécanisme. Dossier : ce fichier, le journal C1 entrées 1 à 13, et
`docs/research/c1_margin_review.md`.
