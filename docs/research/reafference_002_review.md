# Revue contradictoire pré-calcul REF-002 — transport sensorimoteur spatial

Date: 2026-07-26. Revue demandée avant implémentation, smoke `13991` et toute graine
`13301..13316`. Fichiers audités intégralement:
`docs/research/reafference_002_preregistration.md`,
`docs/research/reafference_001_results_review.md`, `CODEX_TASK_BRIEF.md`,
`DEVELOPMENTAL_ARCHITECTURE.md`, `DECISIONS.md` (D-015 à D-018) et `PILOTAGE.md`; en
complément, balayage du dépôt pour les graines et le code REF-002, puis lecture de
`learning/visual_jepa.py`, `learning/reafference.py`, `learning/paired_stats.py`,
`sim3d/bench_model.py` et `sim3d/bench_env.py` pour juger l'implémentabilité du
transport, de `yaw_warp` et du plafond.

Aucun calcul, smoke, rendu, entraînement ni graine n'a été lancé. Aucun fichier autre
que la présente revue n'a été modifié.

## Verdict

**AUTORISER AVEC CORRECTIONS BLOQUANTES.**

REF-002 est une hypothèse réellement neuve, correctement séparée de REF-001, et son
noyau — la strate `mixed` avec calendriers moteurs appariés bit à bit et une baseline
géométrique forte — est le meilleur dispositif que ce projet ait produit sur la question
réafférente. Les cinq corrections de la revue des résultats REF-001 ont toutes été
intégrées de façon vérifiable.

Mais le protocole contient un **défaut fatal et démontrable**: la strate de calibration
statique rend `REF2-H2` mathématiquement impossible à franchir pour les trois conditions
apprenantes, et fait passer `REF2-H4` à vide sur sa moitié statique. Ce n'est pas un
risque, c'est une conséquence arithmétique du score borné choisi. Il réimporte
exactement le régime dégénéré que l'amendement C3 de REF-001 avait été écrit pour
exclure. Sept autres corrections sont nécessaires: la vacuité scientifique de H2 même
réparé, la source du déplacement de `yaw_warp`, l'absence d'assertion d'équité sur le
couple décisif, la construction non fuitée de l'entrée motrice, le contenu de la strate
statique, l'ambiguïté de H5, et le périmètre de la projection temporelle.

Toutes sont corrigeables par amendements additifs pré-calcul, sans aucune valeur issue
de données réservées.

## 0. Nouveauté et statut pré-calcul — vérifiés

- **Graines.** Balayage du dépôt: `13991` et `13301..13316` n'apparaissent que dans les
  documents de pilotage, `DECISIONS.md`, `CLAUDE_REVIEW_REQUEST.md`, `SESSION_HANDOFF.md`
  et le pré-enregistrement. Les correspondances dans `j6_replay_001_runs.json` sont des
  sous-chaînes de flottants et de digests (`…eb13307e3e…`, `0.13300910…`), sans rapport —
  même motif que celui déjà constaté pour REF-001. **Graines vierges.**
- **Code.** Aucun `transport_jepa`, `concat_relative_jepa`, `no_command_jepa`,
  `yaw_warp`, `grid_sample` ni `reafference_002` n'existe dans le dépôt. Statut
  pré-calcul confirmé.
- **Réglage par REF-001.** Aucun seuil, budget ou hyperparamètre REF-002 n'est une
  fonction d'une valeur `12301..12316`. Les budgets (12 000 images, 2 400 décisions,
  4 500 pas, batch 256) sont repris à l'identique de REF-001 comme méthodologie gelée,
  pas comme réglage; les portes (`0,85`, `0,70`, `0,07`, `0,10`, `0,03`) sont posées ici.
  Voir toutefois R1 sur la justification de `0,03`.
- **Hypothèse réellement distincte.** REF-001 testait « concaténer une commande absolue
  à un latent global ». REF-002 teste « imposer un biais inductif spatial de transport à
  une carte de caractéristiques via une commande relative ». Le mécanisme, l'entrée
  motrice, l'architecture du prédicteur et la métrique changent. **Ce n'est pas un
  retuning**, et D-017 le motive sur la conclusion *qualitative* auditée de REF-001, ce
  qui est la seule réutilisation permise par D-016.

## 1. Ce que REF-002 corrige correctement

À porter au crédit du protocole, car ces points étaient les faiblesses réelles de
REF-001:

| Correction REF-001 (D-016) | Traitement dans REF-002 |
|---|---|
| 1. décalage de domaine des baselines | Calibration par strate; seuils `mixed`/`moving_self_test` issus de `moving_self_calibration`, seuils `external_only` issus de `static_calibration`. Une baseline n'est plus jamais évaluée hors de sa strate |
| 2. instabilité inter-graines de la FPR | Partiellement: H4 porte sur deux banques tenues à part; voir R2 pour l'export de la dispersion |
| 3. collision d'image | Garde renforcée: zéro collision corpus↔banques **et** entre banques, sur le smoke **et les graines réservées**, SHA-256 exporté par graine |
| 4. garde « action utile » non exportée | Explicitement exportée: minimum, moyenne et maximum de la variance intra-bin |
| 5. évaluation hors du plafond | Le plafond inclut désormais préparation, entraînement **et** évaluation, chaque phase chronométrée |

L'appariement bit à bit des calendriers moteurs entre `moving_self_calibration`,
`moving_self_test` et `mixed` — même multiensemble de départ, amplitude, signe et
horizon par bin, redistribué sur des pièces et RNG objet disjoints — est la bonne
réponse structurelle au problème que j'avais identifié. Il garantit que `pixel_change`
et `yaw_warp` sont évaluées **dans leur domaine de calibration** sur la strate mobile.
C'est ce qui rend H3 scientifiquement valide, et H3 est le cœur de REF-002.

## 2. C1 (bloquante) — la strate statique rend H2 impossible et H4-statique vide

C'est la correction décisive de cette revue.

### Le mécanisme

Le score JEPA gelé est

```text
score = pred / max(pred + copie, 1e-8)
       où pred  = mean_MSE(pred_map, target_map)
          copie = mean_MSE(current_map, target_map)
```

`static_calibration` est définie comme « tête et objet immobiles ». Le rendu MuJoCo de
`BenchHeadEnv.render_camera` est **déterministe** à état égal: aucun bruit n'est injecté.
Donc, pour chaque paire de cette banque, la trame de départ et la trame d'arrivée sont
bit-identiques, et `copie = 0` **exactement**.

Il en découle, pour toute paire de la strate statique et pour n'importe quel modèle:

```text
score = pred / max(pred + 0, 1e-8) = 1,0   dès que pred > 1e-8
```

Or `pred` est l'erreur résiduelle d'un réseau convolutionnel réel sur une carte
8×8×128: elle est très supérieure à `1e-8`. Les 128 contrôles valent donc **tous
exactement `1,0`**, et la règle de seuil gelée (« plus petit score laissant au plus 5 %
des contrôles strictement au-dessus », égalités non externes) renvoie un seuil de
**`1,0`**.

Enfin, le score est borné supérieurement par `1` et ne peut valoir `1` que si
`copie = 0`. Dans `external_only`, l'objet bouge, donc `copie > 0`, donc `score < 1`
strictement.

### Les conséquences, vérifiées numériquement

| Grandeur | Valeur forcée |
|---|---|
| Seuil JEPA issu de `static_calibration` | `1,0` |
| TPR `external_only` de `transport_jepa` | **`0,0`** |
| TPR `external_only` de `concat_relative_jepa` | **`0,0`** |
| TPR `external_only` de `no_command_jepa` | **`0,0`** |
| Seuil `pixel_change` issu de `static_calibration` | `0,0` |
| TPR `external_only` de `pixel_change` | **`1,0`** |
| TPR `external_only` de `yaw_warp` (warp identité à déplacement nul) | **`≈1,0`** |
| FPR `static_test` de `transport_jepa` (H4, moitié statique) | **`0,0`** |

`REF2-H2` exige `TPR ≥0,85` et un dépassement de `≥0,10` sur chaque contrôle. Le
candidat obtiendra `0,0` contre `1,0`. **H2 n'est pas difficile: il est
mathématiquement infranchissable**, et il est trivialement remporté par la baseline la
plus grossière du protocole. Symétriquement, la moitié statique de H4 sera franchie avec
une FPR de `0,0` qui ne mesure rien: elle constate seulement que le score sature à sa
borne.

### Pourquoi c'est grave au-delà de H2

Ce régime est **exactement** celui que la revue pré-calcul de REF-001 avait décrit au
point 6 et que l'amendement C3 avait été écrit pour exclure: « Quand le changement réel
d'une paire est quasi nul (`MSE(copie) → 0`), le score JEPA tend vers 1 quel que soit le
modèle ». C3 avait imposé que les paires des banques propres proviennent
« exclusivement de transitions où une commande de mouvement non nulle est appliquée ».
Les diagnostics de la campagne REF-001 ont ensuite montré que la garde fonctionnait
(médianes de `MSE(copie)` entre `1,63` et `1,73`, minimum `0,075`, seuils autour de
`0,49`), ce qui a permis d'attribuer l'échec à une absence réelle de séparation.

REF-002 abandonne cette garde et en fait une strate de calibration entière. La leçon la
plus chèrement acquise du dossier précédent serait perdue, et un échec H2 serait de
nouveau **inattribuable** — alors que REF-001 avait précisément été sauvé par
l'attribuabilité de ses échecs.

### Correction exigée

Au choix de Codex, mais explicitement gelée avant tout code:

- **(a)** supprimer la strate strictement statique et la remplacer par une strate de
  **micro-mouvement** à commande non nulle mais faible, en conservant l'exigence C3
  (`copie > 0` par construction), en documentant que la strate n'est alors plus appariée
  à `external_only` sur le mouvement de tête; **ou**
- **(b)** conserver la strate statique mais **changer de score pour cette strate**, en
  utilisant l'erreur de prédiction non normalisée `pred` plutôt que le rapport borné, ce
  qui supprime la division par zéro — au prix d'une métrique différente entre H2 et H3,
  à assumer explicitement; **ou**
- **(c)** appliquer la correction C2 ci-dessous, qui rend le problème sans objet.

Dans tous les cas, le smoke doit **asserter** que la distribution de `MSE(copie)` de
toute banque servant de calibration est strictement positive, avec minimum exporté. Une
`copie` nulle dans une banque de calibration doit être un arrêt d'intégrité.

## 3. C2 (bloquante) — H2 est scientifiquement vide, même réparé

Même en corrigeant la dégénérescence, il faut regarder ce que H2 mesure.

Dans `external_only`, la tête est **structurellement immobile**. Le seul changement
visuel de la paire est celui produit par l'objet. Détecter un changement externe quand
rien d'autre ne bouge n'est pas un problème de réafférence: c'est une soustraction
d'images. N'importe quel détecteur de changement le résout, et c'est bien ce que montre
le tableau ci-dessus, où `pixel_change` atteint `1,0`.

Il n'y a donc, dans cette strate, **aucune séparation auto-produit/externe à faire**, et
donc rien qui puisse départager `transport_jepa` de `concat_relative_jepa`. Exiger un
dépassement de `≥0,10` sur quatre contrôles dans un régime où le contrôle trivial est au
plafond est une porte qui ne peut structurellement pas être informative: soit tout le
monde est à `1,0` et les différences sont nulles, soit le candidat est en dessous.

C'est le miroir exact du défaut REF-001 que D-016 vient d'interdire de citer. REF-001
calibrait le pixel en régime tête mobile et le testait tête tenue, d'où une TPR pixel
nulle et une victoire vide du candidat. REF-002 calibre en régime immobile et teste tête
tenue, d'où une TPR pixel maximale et une défaite vide du candidat. Dans les deux cas,
la comparaison ne mesure pas de compétence.

### Correction exigée

Rétrograder `REF2-H2` en **contrôle de sanité descriptif**:

- conserver la TPR absolue de `transport_jepa` sur `external_only` comme vérification
  que la manipulation est visible et que le détecteur n'est pas mort;
- **retirer ses quatre tests de supériorité** de la famille Holm, qui passe de **douze à
  huit** tests (H1: 2, H3: 4, H5: 2);
- écrire explicitement que `external_only` ne peut pas soutenir une revendication de
  réafférence et ne sera jamais cité comme soutien partiel;
- faire de **`REF2-H3` (`mixed`) l'unique porte de détection**, ce qu'elle est déjà en
  substance: c'est la seule banque où mouvement propre et mouvement externe coexistent,
  donc la seule où la séparation est un vrai problème.

Cette correction *renforce* le protocole: elle concentre la revendication sur le seul
régime qui la porte, et elle supprime quatre tests dont l'issue était connue d'avance.

## 4. C3 (bloquante) — la source du déplacement de `yaw_warp` est contradictoire

Le pré-enregistrement dit, dans le même paragraphe, deux choses incompatibles:

- « Deux baselines analytiques reçoivent les mêmes trames et **la même information
  motrice** »;
- `yaw_warp` utilise « les intrinsics gelés et **le déplacement prédit par le modèle
  servo connu** ».

Or le servo du banc n'est pas un modèle en forme close: `BenchServoConfig` décrit une
boucle PD (`position_gain=10.0`, `velocity_damping=0.15`), avec limite de vitesse
(`max_speed_deg_s=600`), `forcerange`, `joint_frictionloss=0.0147` et
`joint_armature=2.0e-4`, intégrée par MuJoCo. Le déplacement réellement réalisé entre
deux trames **n'est pas une fonction analytique simple** de (angle courant, commande
cible).

Deux implémentations sont donc possibles, et elles ne donnent pas la même campagne:

- **(a) déplacement mesuré** (`as5600_fin − as5600_début`). C'est un **angle futur**,
  interdit aux apprenants par le pré-enregistrement lui-même. `yaw_warp` deviendrait une
  baseline **oracle** disposant du déplacement réalisé exact plus les intrinsics exacts.
  Elle dominerait `moving_self_test` et `mixed`, la règle « `yaw_warp` égale ou bat
  transport → complexité non payée » se déclencherait mécaniquement, et **le verdict de
  la campagne serait décidé avant de la lancer**.
- **(b) approximation analytique gelée** de la boucle servo. Alors la fidélité de cette
  approximation est un **paramètre libre de l'implémenteur** qui fixe à lui seul la force
  de la baseline la plus contraignante du protocole — donc une issue post hoc.

### Correction exigée

Geler avant code, dans le pré-enregistrement:

1. la forme exacte du prédicteur de déplacement de `yaw_warp`, ses coefficients et leur
   provenance (constantes de `BenchServoConfig`, jamais un ajustement sur une banque);
2. l'interdiction explicite d'utiliser toute mesure postérieure à la transition —
   `yaw_warp` ne reçoit que ce que les apprenants reçoivent: angle courant et séquence de
   commandes;
3. une assertion smoke que le tenseur d'entrée de `yaw_warp` est bit-indépendant de
   `as5600` post-transition;
4. la recomputabilité hors ligne du warp, du masque et de l'erreur photométrique, déjà
   prévue par la garde « Warp », étendue au déplacement prédit.

## 5. C4 (bloquante) — aucune assertion d'équité sur le couple décisif

La seule assertion d'équité forte offerte est: « sortie bit-identique entre
`concat_relative_jepa` alimenté par commandes nulles et `no_command_jepa` à
l'initialisation ». Elle est bonne, et c'est le pendant exact de ce qui avait rendu
l'ablation REF-001 irréprochable.

Mais **elle ne couvre pas le couple qui décide de l'hypothèse**. H1, H2 et H3 se jouent
sur `transport_jepa` contre `concat_relative_jepa`, et ces deux modèles sont des graphes
de calcul différents: réseau moteur + `grid_sample` + résidu convolutionnel d'un côté,
diffusion en canaux constants + même résidu de l'autre. Pour ce couple, le
pré-enregistrement n'offre qu'une phrase: « les branches inutilisées sont conservées de
façon à rendre les nombres de paramètres strictement identiques ».

C'est de la **parité de comptage**, pas de la parité de capacité. Une branche conservée
mais non utilisée ne reçoit aucun gradient: ce sont des paramètres morts qui gonflent le
compte sans rien apporter au contrôle. Si `transport_jepa` gagne, on ne pourra pas
exclure qu'il gagne parce qu'il dispose de paramètres *effectifs* supplémentaires, ce qui
est précisément la faille que la règle 2 du brief interdit.

### Correction exigée

Assertions smoke supplémentaires, par graine:

1. digest d'initialisation **de l'encodeur** identique entre les trois conditions;
2. corpus, banques, ordre de batchs, budget et graine d'optimiseur identiques;
3. nombre de paramètres identique **et** nombre de paramètres recevant un gradient non
   nul identique après un pas, condition par condition — c'est cette seconde égalité qui
   fait la parité réelle;
4. coût de calcul déclaré: FLOPs par pas, ou à défaut temps mural par pas mesuré au
   smoke, avec une tolérance gelée; si `transport_jepa` coûte sensiblement plus cher par
   pas, l'égalité de budget en pas ne suffit plus et il faut le consigner;
5. **assertion constructive**: à déplacement commandé nul, le transport doit se réduire à
   l'identité (`grid_sample` identité) de sorte que le résidu convolutionnel reçoive le
   même tenseur d'entrée que `concat_relative_jepa` à canaux nuls. Si l'architecture le
   permet, exiger la bit-identité dans ce cas; sinon, l'écart maximal doit être exporté.

## 6. C5 (bloquante) — la construction de l'entrée motrice doit être assertée non fuitée

Le pré-enregistrement définit l'entrée relative comme « angle courant de tête et séquence
des erreurs signées `commande_cible − angle_courant`, normalisées par 160° », et affirme
« Aucun angle futur ni état objet n'entre dans le modèle ». La définition est correcte:
les deux termes sont connus avant la transition.

Le risque est à l'implémentation, et il est élevé. Dans les banques tenues à part, la
tentation naturelle est de construire le déplacement comme
`as5600_fin − as5600_début`, c'est-à-dire le déplacement **réalisé**. C'est un angle
futur, et il livrerait au modèle la vérité terrain du mouvement propre — une fuite qui
ferait passer H1 et une partie de H3 sans aucun apprentissage. REF-001 stockait
d'ailleurs `head_delta_deg` comme la différence des `as5600` mesurés dans ses banques: la
structure de données qui produirait la fuite existe déjà dans le dépôt et sera
naturellement reprise.

### Correction exigée

Assertion smoke, sur **chacune des sept banques**: le tenseur moteur fourni au modèle est
bit-indépendant de toute mesure postérieure à la transition. Concrètement, recalculer le
tenseur moteur à partir des seuls `angle_courant` et `commande_cible` consignés, et
exiger l'égalité bit à bit avec celui effectivement passé au modèle. Les champs mesurés
(`as5600` final, delta réalisé) restent au manifeste d'audit, comme l'état objet.

## 7. C6 (bloquante) — contenu de la strate statique et collisions entre banques

Deux points non spécifiés, qui interagissent avec la nouvelle garde de fuite.

**Contenu.** Que varie-t-il entre les 128 paires d'un bin de `static_calibration`? Si
tête et objet sont immobiles et que la pièce est fixe, les 128 paires sont **la même
paire répétée**, et le seuil ne mesure plus rien. REF-001 faisait varier la position
statique de l'objet entre paires (`object_start = object_end = rng.uniform(−0,12; 0,12)`);
REF-002 doit dire explicitement ce qui varie: position statique de l'objet, angle de tête
dans le bin, instance de pièce, ou combinaison.

**Collisions.** `static_calibration` et `static_test` partagent « la strate zéro ». Si
elles partagent aussi les pièces, leurs trames seront largement identiques et la garde
« zéro collision entre banques », désormais exigée sur les graines réservées, provoquera
un **arrêt d'intégrité parfaitement spurieux** — la campagne mourrait sur une garde que
le protocole lui-même a rendue insatisfiable. Le pré-enregistrement précise les pièces
disjointes pour le trio mobile, mais reste muet pour le trio statique.

### Correction exigée

1. Spécifier ce qui varie entre paires dans `static_calibration` et `static_test`, de
   sorte que les 128 contrôles par bin soient réellement distincts.
2. Spécifier que les deux banques statiques utilisent des espaces de pièces et de RNG
   disjoints, comme le trio mobile.
3. Étendre la garde de fuite à l'unicité **intra-banque**: aucune paire dupliquée à
   l'intérieur d'une banque, et exporter le compte de trames distinctes par banque.

## 8. C7 (bloquante) — H5: ensemble de permutation ambigu, interprétation tautologique

**Ambiguïté.** « permuter les séquences de commandes entre paires du même bin **et de
même amplitude** ». Si « amplitude » est signée, les commandes permutées sont
quasi identiques aux commandes d'origine et le test est **nul par construction**: H5
échouerait sans rien dire du modèle. Si elle est absolue, la permutation inverse le signe
pour la moitié des paires et se confond partiellement avec le second test. À
désambiguïser avant code.

**Interprétation.** Pour une architecture qui warpe la carte par `grid_sample`, « inverser
le signe de la commande augmente l'erreur » est **mécaniquement forcé**: cela démontre que
`grid_sample` utilise son argument, pas que le modèle a appris un modèle direct causal.
H5 est donc, pour `transport_jepa`, un test de **non-dégénérescence** — il détecte le cas
réellement intéressant où le réseau moteur aurait appris à sortir un déplacement nul,
faisant du transport une identité déguisée. C'est utile, mais ce n'est pas « utilisation
causale de la commande » au sens fort que le titre suggère.

### Correction exigée

1. Désambiguïser « même amplitude » (signée ou absolue) et geler l'ensemble de
   permutation.
2. Renommer/reformuler H5 en **garde de non-dégénérescence du transport**, et interdire
   qu'elle soit citée comme preuve d'un modèle direct appris.
3. Exécuter H5 sur les **trois** conditions — le coût est nul, les modèles sont gelés — car
   sur `concat_relative_jepa` le test est authentiquement informatif: il dit si un modèle
   sans biais de transport a malgré tout appris à utiliser la commande.

## 9. C8 (bloquante) — périmètre de la projection temporelle

Le passage du plafond à 75 minutes **incluant l'évaluation** est la bonne application de
la correction 5 de D-016, et la formule

```text
48 × (temps_partagé_smoke / 3 + moyenne_des_temps_condition_complets)
```

est arithmétiquement juste: 48 runs = 16 graines × 3 conditions, donc la préparation
partagée par graine s'amortit bien sur trois runs.

Mais « répétition complète de chaque condition » ne dit pas si le temps mesuré inclut les
**deux passes contrefactuelles de H5** et la notation des **sept** banques (contre cinq
en REF-001). Ce sont des coûts réels et non négligeables, et REF-002 est plus lourd que
REF-001 sur trois axes simultanés: trois conditions au lieu de deux, sept banques au lieu
de cinq, et une prédiction sur carte 8×8×128 au lieu d'un MLP sur latent 128 — cette
dernière pouvant à elle seule multiplier le coût du pas d'optimisation.

L'ordre de grandeur mérite d'être posé: REF-001 tenait en `31,80` minutes pour 32 runs
d'un modèle nettement plus léger, avec un plafond de 60 minutes. REF-002 demande 48 runs
d'un modèle plus lourd sous 75 minutes. La clause d'amendement existe et fonctionnera,
mais c'est exactement le scénario de D-012 et la marge est mince.

### Correction exigée

1. Écrire que le temps par condition mesuré au smoke inclut **préparation, 4 500 pas,
   notation des sept banques et les deux passes contrefactuelles H5**.
2. Chronométrer et exporter séparément chacune de ces quatre phases, comme le
   pré-enregistrement le prévoit déjà pour les trois premières.
3. Confirmer que l'amendement du plafond, s'il se déclenche, est écrit dans le manifeste
   du smoke **avant** l'ouverture de `13301`, avec digest du protocole — la règle C5 de
   REF-001, qui a fonctionné du premier coup, doit être reprise telle quelle.

## 10. Points audités et jugés conformes

- **Directions et agrégations.** H1 sur `contrôle − transport` (positif favorable), H2/H3
  sur `transport − contrôle` en TPR, H5 sur `erreur permutée − erreur normale`, H4 en
  plafonds absolus: toutes correctes. « Bin favorable » = différence moyenne
  inter-graines strictement positive, plafonds de bin en moyenne inter-graines —
  définitions reprises de C4 de REF-001, sans ambiguïté résiduelle.
- **Famille Holm.** Douze tests annoncés = H1 (2) + H2 (4) + H3 (4) + H5 (2). Le compte
  est exact. Après la correction C2, huit. À `n=16`, la p exacte minimale vaut `2⁻¹⁶ =
  1,526e-05`; corrigée à douze membres elle vaut `1,83e-04`, très en dessous de `0,05`.
  La puissance reste suffisante dans les deux cas. Correction commune et conjonctive:
  conservateur, correct.
- **Statistiques.** `learning/paired_stats.py` réutilisé conformément à la règle 3 du
  brief, tests exacts à `n=16`, BCa 10 000 rééchantillonnages, graine `2026072601`
  neuve et passée explicitement, signes, `dz`, rank-bisériale. Rien à redire.
- **Information disponible avant transition.** La définition de l'entrée relative
  (angle courant + erreurs signées vers les commandes cibles) est correcte et
  n'introduit ni angle futur ni état objet. Sous réserve de C5 pour son implémentation.
- **Indépendance et visibilité.** Corrélation `≤0,05` sur corpus et `mixed`, RNG
  disjoints, tête constante dans `external_only`, effet contrefactuel `≥0,05` par bin au
  smoke: reprise exacte du dispositif REF-001 amendé par C2, qui a tenu (`|r| ≤ 0,0448`,
  visibilité `≥0,211`).
- **Garde de domaine.** L'égalité exacte des multiensembles moteurs par bin, traitée
  comme arrêt d'intégrité et non comme covariable post hoc, est la bonne discipline.
- **Faisabilité du transport et du warp.** L'encodeur existant
  (`4` convolutions stride 2 sur 64×64 → 4×4, puis `AdaptiveAvgPool2d(2)`) expose
  naturellement une carte 8×8 après la troisième convolution: le tap est implémentable
  sans changer la philosophie du modèle. `camera_fovy_deg = 30,0` est gelé dans
  `BenchSensorConfig`, donc les intrinsics de `yaw_warp` sont disponibles et
  recomputables. Les deux mécanismes sont réalisables.
- **Règles de clôture.** « Quel que soit le verdict, REF-002 clôt cette variante » et
  l'exigence d'hypothèse, fichier, monde et graines neufs pour toute suite: conforme au
  modèle J6-AR001/REF-001 qui a rendu D-012 et D-015 mécaniques. Bien.
- **Limites de revendication.** « opérationnelle et limitée à ce monde », sans
  segmentation, causalité générale ni agentivité: conforme à `DEVELOPMENTAL_ARCHITECTURE`
  §2 point 2 et §12.2.

## 11. Recommandations non bloquantes

- **R1 — justifier `0,03`.** REF-001 exigeait `0,05` sur l'erreur d'un latent global;
  REF-002 exige `0,03` sur l'erreur d'une carte spatiale. Les deux quantités ne sont pas
  commensurables et `0,03` n'est dérivable d'aucune valeur `12301..12316` — ce n'est donc
  pas un retuning. Mais l'apparence est mauvaise et doit être désamorcée par écrit: dire
  explicitement que l'échelle du nouveau score est inconnue avant calcul, que `0,03` et
  `0,10` sont posés a priori, et qu'aucun ajustement post hoc n'est permis quel que soit
  l'écart observé.
- **R2 — exporter la dispersion de la FPR.** La correction 2 de D-016 a montré qu'une
  FPR globale conforme peut masquer `5/16` graines hors plafond et une cellule à
  `0,5234`. Exporter, pour les deux portes H4, la FPR par graine et par graine×bin, et
  la consigner dans le rapport final même si la porte passe.
- **R3 — nommer l'asymétrie de `yaw_warp`.** Sous la correction C3 option (b), cette
  baseline dispose des intrinsics exacts et d'un modèle servo gelé que les apprenants
  doivent apprendre en 4 500 pas. C'est une asymétrie **en sa faveur**, donc conservatrice
  vis-à-vis de la promotion — ce qui est bien. Mais si `yaw_warp` gagne, la conclusion
  correcte est « un modèle direct analytique exact bat un modèle appris à ce budget », et
  non « le transport spatial est sans valeur ». À écrire dans les limites de revendication.
- **R4 — définir la régularisation sur la carte.** « variance/covariance inchangées » est
  sous-spécifié dès lors que la prédiction se fait avant pooling: dire si les termes
  VICReg portent sur le latent agrégé 128 ou sur la carte 8×8, et avec quelle réduction.
- **R5 — `193+ tests` est périmé.** Le dépôt est à `215` tests verts depuis KERNEL-001
  (D-018). Mettre la séquence à jour pour éviter une porte de vérification plus faible que
  l'état réel.
- **R6 — apparier aussi les masques.** Ajouter à la garde « Domaine » l'égalité des
  multiensembles de **fraction de pixels valides** du warp entre
  `moving_self_calibration`, `moving_self_test` et `mixed`. L'appariement bit à bit des
  calendriers moteurs devrait l'impliquer; l'asserter le prouve, et protège `yaw_warp`
  d'un biais de dénominateur entre calibration et test.

## 12. Synthèse et autorisation

REF-002 pose la bonne question et, sur `mixed`, la pose bien. L'appariement bit à bit des
calendriers moteurs, la calibration par strate, la garde de fuite étendue aux graines
réservées et l'inclusion de l'évaluation dans le plafond répondent une par une aux
faiblesses de REF-001. Le contraste `transport_jepa` / `concat_relative_jepa` à
information motrice identique est exactement l'ablation qu'il faut pour isoler le biais
inductif spatial, et `yaw_warp` est une baseline géométrique honnête et exigeante.

Mais le protocole ne peut pas être lancé en l'état: sa strate de calibration statique
force `H2` à `0,0` pour les trois apprenants et à `1,0` pour la baseline la plus
triviale, par pure arithmétique du score borné, en réimportant le régime dégénéré que C3
avait éliminé. Et même réparée, cette strate ne pose aucun problème de réafférence.

**Autorisation.** Une fois les corrections **C1 à C8** intégrées au pré-enregistrement
comme amendements pré-calcul datés et additifs, **l'implémentation peut commencer, puis
le smoke `13991` peut être exécuté**. Les graines `13301..13316` restent interdites
jusqu'à: intégration de toutes les corrections bloquantes, smoke entièrement vert incluant
la projection temporelle et les nouvelles assertions d'équité, de non-fuite motrice et de
`copie > 0` en calibration, et manifeste concordant avec le protocole amendé. Toute
promotion reste interdite avant une seconde revue contradictoire des résultats.

Si Codex retient la correction C2, le protocole amendé revendiquera moins — une seule
porte de détection au lieu de deux — mais ce qu'il revendiquera sera vrai. C'est le bon
échange, et c'est la leçon que REF-001 a déjà payée une fois.
