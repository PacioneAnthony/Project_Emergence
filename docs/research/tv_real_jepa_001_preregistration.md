# Pré-enregistrement TV-001 — exploration active avec JEPA réel

Date de gel: 2026-07-20, avant implémentation, avant calibration et avant tout calcul
sur les graines de campagne. Ce protocole exécute l'étape 1 de
`CODEX_TASK_BRIEF.md`. Les résultats DC-001..005 restent historiques et aucun composant
de la famille à gain fractionnel n'est réutilisé.

## Question et hypothèse

À budget sensorimoteur et budget d'optimisation strictement égaux, un ordonnanceur
`regional_lp_gain` nourri par le progrès tenu à part d'un **JEPA visuel réellement
entraîné** apprend-il mieux les régions visuelles structurées et gaspille-t-il moins
d'interactions sur une source visuelle inapprenable que le babbling uniforme?

- **TV-H1, primaire — apprentissage structuré:** à la fin du budget, l'erreur JEPA
  normalisée tenue à part dans les régions structurées est inférieure avec
  `regional_lp_gain`, avec une réduction relative appariée moyenne d'au moins 5 % face
  au babbling.
- **TV-H2, co-primaire — évitement du bruit:** `regional_lp_gain` alloue moins de 15 %
  des décisions à la télévision et moins que le babbling.

Une erreur brute élevée n'entre jamais dans le score. Seule une baisse signée d'erreur
tenue à part, agrégée avant tout clip de sélection, est utilisée.

## Graines, conditions et budgets gelés

- Calibration du bruit uniquement: graines `9201..9203`; elles ne participent à aucun
  test final.
- Campagne appariée: graines vierges `9301..9312` (12 paires).
- Conditions: `babbling` et `regional_lp_gain`. Il n'existe pas de troisième politique
  active: la référence survivante est précisément l'hypothèse active testée.
- Par run: 10 rounds, 800 images nouvelles par round, images 64×64 à 10 Hz, une
  décision de cible toutes les 5 images; total exact 8 000 images et 1 600 décisions.
- Apprentissage après chaque round sur le buffer cumulatif: 20 epochs, batch 256,
  AdamW (`lr=3e-4`, weight decay `1e-4`), poids variance `1.0`, covariance `0.1`.
- JEPA v3 inchangé dans ses éléments validés: encodeur convolutionnel largeur 32,
  latent 128, prédicteur caché 512, action et horizon conditionnés, horizons 1..5.
- Les deux conditions d'une paire partagent l'initialisation du modèle, les pièces,
  les ancres tenues à part, les réalisations de la télévision et le calendrier des
  mini-batchs de mesure. Seule la règle de choix des cibles diverge.

## Monde hétérogène et absence d'oracle

Le substrat est `BenchHeadEnv`. Les objets, panneaux et capteurs restent ceux du jumeau
3D validé. Une télévision simulée occupe le secteur d'angle réel `[130°, 170°]`: dans
ce secteur, un écran central bordé remplace 75 % environ des pixels par un bruit RGB
indépendant à chaque image. Le reste de l'image et tous les angles `[10°, 130°)` restent
la pièce structurée. Le bruit est reproductible par graine pour l'appariement, mais sa
réalisation suivante est indépendante des actions et des images précédentes.

La politique ne reçoit ni les bornes `[130°, 170°]`, ni un drapeau télévision, ni la
graine ou les paramètres de la pièce. Son espace régional est `8 bins d'angle × 2
contextes visuels`. Le contexte est le bit d'un hachage déterministe d'une vignette
8×8 en niveaux de gris de la première image neutre de l'épisode. Il est donc calculable
uniquement depuis les pixels observés; il ne code aucun paramètre caché. Les frontières
d'angle sont celles du servo, pas celles de la télévision.

Contrôle de construction obligatoire: sur les images de télévision de calibration,
la corrélation pixel à pixel moyenne entre deux réalisations successives du rectangle
bruité doit avoir une valeur absolue inférieure ou égale à `0.02`. Sinon la source n'est
pas déclarée inapprenable et la campagne ne démarre pas.

## Signal tenu à part et calibration du bruit

Chaque graine possède une banque d'ancres externe, issue de pièces jamais utilisées
pour l'entraînement. Elle contient au moins 64 transitions par cellule
`angle × contexte`; les actions et horizons sont fournis au JEPA exactement comme à
l'entraînement. L'erreur d'une transition est

```text
e = MSE(prediction, cible) / max(MSE(prediction, cible) + MSE(copie, cible), 1e-8)
```

donc `e` est bornée dans `[0, 1]` et résiste à une dérive d'échelle du latent. Avant et
après chaque intervention d'entraînement, des mini-batchs indépendants de 16 ancres par
cellule sont tirés selon un calendrier gelé. Le gain signé est `mean(e_before) -
mean(e_after)`. Les ancres ne sont jamais entraînées et le test final utilise toute la
banque, pas les seuls mini-batchs du score.

La calibration `9201..9203` mesure le bruit nul sans mise à jour de poids: 64 paires de
mini-batchs indépendants par cellule. Soit `s` l'écart-type groupé des différences et
`m` la médiane groupée des erreurs. Le nombre `B` de paires agrégées par estimation est
choisi dans `{4, 8, 16, 32}` par la règle entièrement fixée suivante:

1. prendre le plus petit `B` tel que `1.96 × s / sqrt(B) <= 0.02 × m`;
2. vérifier que la fréquence empirique des agrégats nuls supérieurs à `0.02 × m` est
   au plus `0.05`;
3. si aucun candidat ne satisfait les deux conditions, arrêter avant campagne et
   rédiger un nouveau pré-enregistrement; ne pas élargir la grille après observation.

Le résultat (`s`, `m`, `B`, taux de faux positifs par candidat) est écrit dans
`data/processed/experiments/tv_real_jepa_001/calibration.json` avant toute graine
`9301..9312`.

## Politiques

`babbling` tire une cible uniformément dans `[10°, 170°]` à chaque décision.

`regional_lp_gain` maintient, pour chaque cellule, les quatre dernières estimations de
gain agrégé. Une cellule ayant moins de deux estimations est optimiste et explorée en
priorité. Ensuite son score est `max(mean(gains_signés), 0)`; le clip a donc lieu
**après** l'agrégation des mini-batchs et de l'historique, jamais par observation.
Sélection epsilon-greedy avec `epsilon=0.10`; à score égal, tirage uniforme. Dans une
pièce donnée, seules les huit cellules du contexte visuel courant sont candidates. Une
cellule visitée pendant le round reçoit l'estimation avant/après tenue à part; une
cellule non visitée ne reçoit aucune information gratuite.

## Évaluation et statistiques

Métriques par graine, toutes calculées sans exposer les frontières à la politique:

- erreur externe structurée finale et initiale, moyenne sur toutes les ancres dont la
  cible réelle est `<130°`;
- erreur externe télévision finale et initiale, rapportée sans servir de récompense;
- fraction des 1 600 décisions dans `[130°, 170°]`;
- entropie normalisée des visites des six bins entièrement structurés et part minimale
  de chacun;
- courbes par round, gains régionaux signés, nombre d'ancres et diagnostic de contexte;
- temps mural, nombre exact d'images, décisions et pas d'optimisation.

Pour TV-H1, la différence appariée est la réduction relative
`(e_babbling - e_regional) / e_babbling`. Pour TV-H2, la différence est
`fraction_babbling - fraction_regional`. Tests exacts par retournement de signes via
`learning/paired_stats.py`, unilatéraux, correction de Holm sur les deux hypothèses,
alpha famille `0.05`. IC BCa 95 % (10 000 rééchantillonnages, graine `20260720`) et
comptages de signes obligatoires. `dz` et corrélation rank-bisériale sont descriptifs.

Garde-fous interprétatifs, tous obligatoires:

- apprenant réel: l'erreur structurée moyenne baisse d'au moins 10 % entre initial et
  final dans chacune des deux conditions;
- couverture: entropie structurée de `regional_lp_gain >= 0.75` et chaque bin
  entièrement structuré reçoit au moins 2 % des décisions;
- budget exact et aucune utilisation d'une ancre dans l'entraînement;
- contrôle télévision de corrélation passé pendant la calibration.

## Règles de décision gelées

- **Promotion:** TV-H1 et TV-H2 passent après Holm, leurs tailles minimales passent,
  et tous les garde-fous passent. `regional_lp_gain` devient alors l'ordonnanceur de
  référence sur apprenant réel; une revue contradictoire des résultats est préparée
  avant l'étape 2 (J6).
- **TV-H1 échoue:** l'exploration active n'a pas démontré de gain d'apprentissage face
  au babbling avec apprenant réel. Aucune retouche post hoc; résultat consigné et
  arbitrage de direction avant de modifier l'ordonnanceur.
- **TV-H2 échoue seule:** l'amélioration éventuelle ne démontre pas la résolution du
  piège de la télévision; aucune promotion.
- **Un garde-fou échoue:** campagne déclarée non interprétable pour la revendication
  correspondante. Toute reprise exige un nouveau fichier, des graines vierges et une
  cause technique explicite.

## Séquence et gel

1. Le présent fichier est gelé.
2. Le monde, la banque d'ancres, l'apprenant, les politiques, les tests et le runner
   résumable/keep-awake sont implémentés sans modifier les seuils ci-dessus.
3. Une revue contradictoire Claude du protocole et du code est requise avant la
   calibration et avant la campagne principale, conformément à `PILOTAGE.md`.
4. Après avis favorable (ou corrections gelées dans un amendement daté), calibration,
   campagne, analyse et verdict sont exécutés sans réglage intermédiaire.

Simulation uniquement sous D-008: aucune commande matérielle, aucun flash, aucun achat.

## Amendement du 2026-07-20 — corrections pré-calibration de la revue contradictoire

Amendement ajouté avant calibration et avant tout calcul sur graines réservées (revue
contradictoire, correction de description sans changement de seuil ni de code du
monde): (1) l'écran couvre les fractions `[1/8, 7/8]` de chaque dimension de l'image,
soit 56,25 % des pixels (75 % par dimension); la périphérie et le bezel restent visibles
et prédictibles, seul le contenu central est du bruit indépendant soumis à la porte de
corrélation. (2) Le secteur `[130°, 170°]` coïncide exactement avec les bins servo 6 et
7; les frontières des bins sont définies par le servo mais l'une d'elles tombe sur la
frontière de la télévision. La conclusion TV-H2 vaut pour ce cas aligné; la
généralisation à un secteur chevauchant plusieurs bins partiels n'est pas revendiquée.

Clarifications de lecture gelées à la même date, avant données: le seuil TV-H2 « moins
de 15 % » porte sur la moyenne des 12 graines, comme l'implémente le runner. Le partage
des réalisations télévision entre conditions vaut au sens des mêmes graines et lois
i.i.d., pas image par image après divergence des politiques. Le rapport final devra
rappeler que la calibration du bruit porte sur un JEPA non entraîné et consigner le
nombre d'ancres de bin visé inférieur ou égal à 5 dont l'angle réel atteint au moins
130°.
