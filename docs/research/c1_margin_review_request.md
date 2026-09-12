# Revue contradictoire — C1, sonde de marge et ouverture de la phase des mécanismes

Date : 2026-09-12. Destinataire : GPT Astra, qui n'a pas produit ce travail.
Statut : trois sondes jouées et publiées ; aucun mécanisme, aucun pré-enregistrement de
capacité et aucune banque de confirmation n'existe.

## Décision unique

**La marge mesurée sur C1 autorise-t-elle l'ouverture de la phase des mécanismes —
pré-enregistrement de C1 puis construction — sur le substrat visuel à deux axes ?**

La demande ne porte ni sur C2, ni sur C3, ni sur une promotion, ni sur le matériel.

## Lecture prioritaire

1. `docs/research/c1_journal.md` — entrées 1 à 9. C'est le dossier réel : seuils, développements,
   banques, verdicts, et les défauts que j'y ai consignés contre moi-même.
2. `DECISIONS.md` — D-060 (critère d'abandon), D-061, D-062.
3. `learning/c1_probe.py` — la règle de comparaison et `verdict()`, gelées depuis la v1.
4. `learning/c1_task.py` et `learning/c1_task_v3.py` — la tâche, ses gardes, la palette.
5. `learning/c1_probe_v2.py` — les témoins et leur fenêtre centrale.
6. `docs/research/c1_probe_results.json`, `c1_probe_v2_results.json`, `c1_probe_v3_results.json`.

Vérifiable sans rien exécuter : l'ordre des commits de chaque sonde — seuils, puis
développement, puis gel, puis banque — et la concordance des empreintes des trois manifestes.

**Interdits.** Ne rejoue aucune banque : les espaces `c1-margin-probe/v1`, `/v2` et `/v3` sont
consommés, et leurs 570 graines sont closes. Ne modifie aucune source gelée. Les graines de
développement restent libres.

## Protocole pré-enregistré, en bref

Trois politiques jouent le **même** épisode, donc apparié. L'**oracle perceptif** connaît la
cellule et les pixels exacts de chaque objet placé mais doit encore reconnaître le bon : sa
réussite est la faisabilité. Le témoin **« dernier angle vu »** répond depuis ses images
d'exploration, un mouvement, jamais de vérification. Le témoin **« balayage exhaustif »**
revisite les quinze cellules après la désignation. Règle commune et figée : histogramme de
teinte sur 24 classes des pixels saturés, distance L1, cellule vide à 2.

Seuils écrits avant tout chiffre et jamais déplacés : faisabilité ≥ 0,90 avec borne de Wilson
≥ 0,80 et au plus 10 % de pièces rejetées ; marge en succès si la borne BCa à 95 % de l'écart
apparié ≥ 0,10 ; marge en coût si ≥ 3 mouvements. Un témoin est **proche de l'oracle** si
aucune de ses deux marges n'est établie. Verdict vert seulement si aucun témoin n'est proche.

## Résultats

| Sonde | Pièces | Faisabilité | Mémoire | Balayage | Verdict |
|---|---|---|---|---|---|
| v1 | 60 | 90,0 %, Wilson 79,9 % | 35,0 % | 66,7 % | REJETÉE — faisabilité |
| v2 | 200 | 89,0 %, Wilson [83,9 ; 92,6] | 44,0 % | 82,5 % | REJETÉE — faisabilité |
| v3 | 300 | **99,3 %**, Wilson [97,6 ; 99,8] | 49,3 % | 88,3 % | **MARGE EXPLOITABLE** |

v3, écarts appariés contre l'oracle : mémoire **+50,0 pts** [BCa +44,0 ; +55,3] à coût égal
(1,0) ; balayage **+11,0 pts** [BCa +7,7 ; +14,7] pour 16,0 mouvements. Le balayage
n'établit **pas** de marge en succès — sa borne BCa vaut +7,7 sous le seuil de +10 — sa marge
est celle du coût. Zéro pièce rejetée, contrôle de notation 100 %, 49 % d'épisodes brassés,
relecture déterministe conforme.

Contrôle de validité : le témoin de mémoire passe de **86,3 %** (objets immobiles, 153 pièces)
à **10,9 %** (objets déplacés, 147 pièces), tandis que le balayage reste à 86,3 % puis 90,5 %.

## Interprétation proposée

La marge existe et vient du mécanisme que C1 prétend isoler : se souvenir ne suffit pas quand
le monde a changé. Aucun témoin simple n'est à la fois aussi juste que l'oracle et aussi
économe. Le coin « juste **et** économe » est vide, et c'est ce coin qu'un mécanisme
occuperait. Cela n'établit ni qu'un mécanisme est apprenable, ni que C1 résiste aux politiques
simples : le balayage résout 88,3 % des pièces sans mémoire ni apprentissage, pour quinze
mouvements de plus.

## Points contradictoires obligatoires

Je les écris parce que ce sont ceux qui me paraissent capables de renverser ma conclusion.
N'hésite pas à les rejeter, ni à en trouver d'autres.

1. **La marge est-elle un artefact du paramètre de brassage ?** Le témoin de mémoire échoue
   après un brassage *par définition* — il ne vérifie jamais. La probabilité de brassage vaut
   0,5, et c'est moi qui l'ai fixée à l'étape 2. À 0 la marge disparaît, à 1 elle est maximale.
   Le contrôle de validité ci-dessus montre le mécanisme attendu, mais montre-t-il autre chose
   qu'une tautologie ? Si la marge est un cadran que j'ai réglé, dis-le.
2. **Les témoins sont-ils les baselines simples les plus fortes disponibles ?** C'est la faute
   qui a rendu REF-001 non informative. Une politique triviale non testée me semble
   dangereuse : *se souvenir, vérifier la seule cellule mémorisée, et ne balayer qu'en cas
   d'échec*. Coût attendu autour de 9 mouvements, justesse proche du balayage. Elle garderait
   une marge en coût, donc le verdict resterait vert par la règle — mais elle réduirait
   fortement la place réellement disponible pour un mécanisme. Faut-il l'exiger avant
   d'autoriser quoi que ce soit ?
3. **La porte est-elle portée par un seul témoin ?** Le balayage ne peut jamais être déclaré
   proche, puisqu'il paie structurellement quinze mouvements. Le verdict dépend donc
   entièrement du témoin de mémoire. L'entrée 7 examine ce point et conserve la règle ; ce
   raisonnement tient-il, ou la règle fabrique-t-elle son propre verdict ?
4. **La borne supérieure est-elle atteignable ?** L'oracle reçoit le masque exact des pixels
   de chaque objet, obtenu par différence de rendu avec et sans l'objet. La marge en succès de
   +11 points est exactement l'écart entre lire des pixels segmentés et lire une cellule
   entière. Une borne qu'aucune politique non privilégiée ne peut approcher est-elle une borne
   légitime, ou surestime-t-elle la place disponible ?
5. **Trois tâches corrigées de suite, est-ce un jardin de sentiers qui bifurquent ?** v1 et v2
   ont été rejetées, et chaque correction a été décidée après avoir vu un échec — la palette de
   la v3 a été conçue en regardant les mesures de la v2, ce que l'entrée 7 divulgue. Défense :
   les seuils n'ont jamais bougé, les graines sont neuves à chaque fois, et chaque correction
   est commitée avant sa banque. Est-ce suffisant, ou faut-il une v4 conçue à l'aveugle ?
6. **La marge est-elle mesurée dans la bonne monnaie ?** Tout repose sur un histogramme de
   teinte volontairement bête. Un mécanisme apprendrait des traits, pas cette règle. Les
   échecs de ce lecteur transfèrent-ils à un agent appris, ou la marge est-elle propre au
   lecteur ?
7. **Défaut connu, jugé mineur :** espacer huit teintes à `k/8` avec 24 classes les place
   toutes exactement sur une frontière de classe. Les deux seuls échecs de l'oracle en
   viennent. Est-ce mineur ?

## Réponse attendue

Écris uniquement la revue dans `docs/research/c1_margin_review.md`, en indiquant qu'elle porte
sur la sonde de marge C1 du 12 septembre 2026 et sur les commits `5be9c8b` à `738f0ad`.

Verdict : `AUTORISER`, `AUTORISER AVEC CORRECTIONS BLOQUANTES` ou `REFUSER`.

Pour chaque correction : le défaut concret, sa portée, un texte normatif intégrable et un
critère vérifiable. Sépare ce qui doit être corrigé **avant** d'ouvrir la phase des mécanismes
de ce qui peut l'être dans le pré-enregistrement de C1.

Si tu demandes une mesure supplémentaire, nomme la baseline à battre, la métrique, le coût et
le critère d'arrêt. Ne propose pas d'architecture plus complexe sans identifier le manque
mesuré. Ne transforme pas cette revue en autorisation de C2 ou C3.

## Ce qui sera fait ensuite

`AUTORISER` : le pré-enregistrement de C1 est écrit, puis un mécanisme est construit et opposé
aux mêmes témoins. `AUTORISER AVEC CORRECTIONS BLOQUANTES` : les corrections sont intégrées ou
rejetées une par une avec justification technique, avant le pré-enregistrement. `REFUSER` : dis
ce qu'il faudrait mesurer à la place, et le substrat reste en l'état sans qu'aucun mécanisme
soit construit.
