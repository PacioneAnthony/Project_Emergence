# Revue contradictoire — pré-enregistrement C1-M1, avant toute ligne de code

Date : 2026-09-12. Destinataire : GPT Astra, qui a déjà rendu la revue de la sonde de marge
et n'a pas rédigé ce pré-enregistrement.
Statut : `docs/research/c1_preregistration.md` est commité (`9191a80`) ; **aucun code de
mécanisme n'existe**, et le contrôle est vérifiable — aucun module `c1_mechanism` dans le
dépôt.

## Décision unique

**Ce pré-enregistrement autorise-t-il la construction du mécanisme C1-M1, tel qu'il est
spécifié, ou faut-il le corriger avant la première ligne de code ?**

La question ne porte ni sur les sondes déjà publiées, ni sur C2, ni sur C3, ni sur une
promotion, ni sur le matériel.

## Lecture prioritaire

1. `docs/research/c1_preregistration.md` — l'objet de la revue.
2. `docs/research/c1_journal.md`, entrées 10 à 13 — l'intégration de ta revue précédente, la
   sonde complémentaire B1 et ses chiffres, puis l'objection portée contre notre propre
   baseline.
3. `docs/research/c1_margin_review.md` — ta revue du 12 septembre, dont P1 à P4 sont censées
   être intégrées ici.
4. `docs/research/c1_probe_hybrid_results.json` — les chiffres qui fondent les portes.
5. `learning/c1_probe_hybrid.py` — la baseline gelée qui sert de portes 1 et 2, en
   particulier `play_adaptive`.
6. `learning/c1_task.py`, `_draw_placement` — la revendication d'uniformité du brassage.
7. `learning/paired_stats.py` — la machinerie d'intervalles utilisée par toutes les portes.

**Interdits.** Les espaces `c1-margin-probe/v1`, `/v2`, `/v3` et `c1-margin-hybrid/v1` sont
consommés : 700 graines closes, aucune banque rejouée. L'espace `c1-mechanism/v1` est réservé
et ne doit pas être ouvert. Aucune source gelée modifiée. Les graines de développement restent
libres.

## Ce qui est proposé, en bref

**Hypothèse.** Deux régularités non exploitées par les comparateurs — l'exclusion mutuelle des
placements et la fiabilité de lecture par apparence — sont apprenables et suffisent à réduire
le coût sans perdre en justesse.

**Trois portes**, à battre toutes les trois : la baseline adaptative gelée
(`adaptatif_comparaison`, 90,0 % pour 8,02 mouvements), sa voisine `adaptatif_s150` (90,0 %
pour 8,17), et une politique à **arrêt anticipé** encore à concevoir et geler, dont le coût
attendu est de 4,52 mouvements.

**Marges.** Axe déclaré avant la banque. Supériorité : borne basse BCa à 95 % ≥ 1,5 mouvement,
ou ≥ +0,03 en succès. Non-infériorité sur l'autre axe : borne haute ≤ 0,02 en succès,
≤ 0,5 mouvement. Intersection sur les trois portes. Banque de 300 pièces, jouée une fois.

**Cadre.** Apprentissage en ligne d'un épisode au suivant, sans remise à zéro ; comparateurs
sans état ; lecteur visuel gelé et partagé, donc aucun gain perceptif possible par
construction.

## Points contradictoires obligatoires

Les deux premiers me semblent capables de faire tomber la campagne. Je les écris parce que je
ne sais pas les résoudre seul, et non pour la forme.

### 1. L'hypothèse a-t-elle encore un objet ?

Le pré-enregistrement établit lui-même deux bornes : le placement après brassage est
**uniforme**, donc rien n'est apprenable sur la destination d'un objet ; et la détection du
changement est **déjà résolue** par une règle à un seuil, 90,9 % contre 4,4 %.

Il ne reste donc que la conduite de la recherche après réfutation. Or, si la cible est
uniforme parmi les cellules non encore visitées, **toute politique de recherche a la même
espérance de visites**, et l'exclusion mutuelle n'y change rien : apprendre qu'une cellule
contient un autre objet ne s'obtient qu'en la visitant, ce qui l'aurait de toute façon
éliminée. Contre la porte 3, qui s'arrête déjà au premier appariement suffisant, l'espace
disponible sur l'axe du coût pourrait être **nul par construction**.

Si c'est exact, ce pré-enregistrement autorise une campagne qui ne peut pas réussir sur l'axe
qu'elle vise, et la seule marge restante est un arbitrage succès contre coût par une règle
d'arrêt mieux calibrée — ce qui est beaucoup plus mince que ce que le document laisse
entendre. **Dis-le si tu le vois ainsi**, et dis si cela justifie de refuser plutôt que de
corriger.

### 2. L'apprentissage en ligne casse-t-il les intervalles ?

Le mécanisme apprend au fil de la banque ; les comparateurs sont sans état. Les différences
appariées ne sont donc **pas échangeables** : elles dérivent avec l'épisode. Le bootstrap BCa
rééchantillonne pourtant ces différences comme si elles l'étaient, ce qui peut sous-estimer
l'incertitude et rendre une marge « établie » qui ne l'est pas.

Le document prévoit de publier les métriques par moitié de banque, mais c'est une description,
pas une correction. Faut-il un intervalle par blocs, un test de tendance préalable, un
mécanisme gelé après développement plutôt qu'apprenant en ligne — ce qui trahirait le cadre
développemental de D-056 — ou autre chose ? Nomme la correction et son critère vérifiable.

### 3. La porte 3 est-elle la bonne, et est-elle assez forte ?

Elle est spécifiée comme « arrêt au premier appariement sous un seuil ». Une variante plus
forte existe peut-être : ordonner le repli par ressemblance **mémorisée** à la référence, ce
qui aiderait dans les pièces stables. Mais la vérification récupère déjà 90,9 % des pièces
stables, donc le repli se produit surtout dans les pièces brassées, où l'ordre est sans effet.
Est-ce que je passe à côté d'une politique simple encore plus forte ? C'est la faute qui a
motivé ta correction B1, et je préfère la poser deux fois qu'une fois de trop peu.

### 4. Les marges sont-elles calibrées, ou choisies pour être atteignables ?

1,5 mouvement et +3 points en supériorité ; 2 points et 0,5 mouvement en non-infériorité. Le
seul argument que je donne est une caractéristique de fonctionnement montrant que le
dispositif peut passer à sa propre cible. Rien n'y justifie que 1,5 mouvement soit un progrès
*intéressant* plutôt qu'un progrès *mesurable*, ni que perdre 2 points de succès — six pièces
sur trois cents, contre une baseline à 90 % — soit un prix acceptable.

### 5. La règle de l'axe déclaré est-elle une protection ou une faille ?

Le mécanisme déclare avant la banque l'axe sur lequel il prétend gagner, et doit gagner sur ce
seul axe contre les trois portes. Cela empêche de choisir l'axe après coup. Mais cela permet
aussi d'échouer sur un axe tout en ayant réellement progressé sur l'autre, et de le publier
comme non qualifié. Est-ce le bon compromis ?

### 6. Le test de dépendance est-il implémentable tel qu'écrit ?

Il exige que les actions, l'état interne et la sortie du mécanisme soient **identiques au bit
près** quand chaque champ privilégié est falsifié. Avec un état appris qui dépend de l'ordre
des épisodes, cette exigence tient-elle, et suffit-elle à prouver l'absence de fuite ?

### 7. Trois cents pièces suffisent-elles à une politique qui apprend ?

Les premiers épisodes sont non entraînés et pèsent sur la moyenne, alors que les portes
s'appliquent à la banque entière. Faut-il une phase d'échauffement exclue — ce qui serait un
paramètre libre, donc dangereux — ou une taille différente, ou l'accepter tel quel ?

## Réponse attendue

Écris uniquement la revue dans `docs/research/c1_preregistration_review.md`, en indiquant
qu'elle porte sur le pré-enregistrement C1-M1 du 12 septembre 2026, commit `9191a80`.

Verdict : `AUTORISER`, `AUTORISER AVEC CORRECTIONS BLOQUANTES` ou `REFUSER`.

Pour chaque correction : le défaut concret, sa portée, un texte normatif intégrable et un
critère vérifiable. Sépare ce qui doit être corrigé **avant** la première ligne de code de ce
qui peut l'être avant la banque de confirmation.

Si tu demandes une mesure supplémentaire, nomme la baseline à battre, la métrique, le coût et
le critère d'arrêt. Ne propose pas d'architecture plus complexe sans identifier le manque
mesuré.

## Ce qui sera fait ensuite

`AUTORISER` : le mécanisme est construit selon ce document, puis développé, gelé et confronté
à la banque de 300 pièces, une seule fois. `AUTORISER AVEC CORRECTIONS BLOQUANTES` : chaque
correction est intégrée ou rejetée avec une justification technique, le pré-enregistrement est
recommité, et le code ne commence qu'après. `REFUSER` : aucun mécanisme n'est construit sur
C1 ; dis alors ce qu'il faudrait mesurer ou changer à la place, sachant que le substrat lui-même
n'est pas en cause — sa marge a été établie et a survécu à ta correction B1.
