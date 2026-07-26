# Revue contradictoire pré-calcul REF-001 — réafférence visuelle

Date: 2026-07-20. Revue demandée avant implémentation, smoke et tout calcul. Fichiers
audités intégralement: `docs/research/reafference_001_preregistration.md`,
`docs/research/j6_adaptive_replay_001_review.md`,
`docs/research/j6_adaptive_replay_001_technical_stop.md`, `DECISIONS.md` (D-012, D-013),
`DEVELOPMENTAL_ARCHITECTURE.md`, `CODEX_TASK_BRIEF.md` (étape 3),
`learning/paired_stats.py`; en complément: balayage du dépôt pour les graines et le code,
`docs/research/visual_bench_probe.md` et `learning/train_visual_jepa.py` (infrastructure
`no_action` v3 préexistante). Aucun calcul, smoke, rendu, entraînement ni graine lancé;
aucun fichier autre que la présente revue modifié.

## Verdict

**AUTORISER AVEC CORRECTIONS BLOQUANTES.** La clôture de J6-AR001 est propre, REF-001
est réellement neuf et pré-calcul, le contraste expérimental opérationnalise la
réafférence sans sur-revendication, l'équité entre les deux JEPA est bien construite et
les portes ferment les principales issues post hoc. Cinq corrections bloquantes —
textuelles, additives, sans aucune valeur choisie sur des données réservées — sont
nécessaires: une baseline simple recevant réellement la même information (C1), la
définition de la garde d'indépendance sous tête tenue (C2), le traitement du régime
dégénéré petit-changement du score borné (C3), des assertions smoke d'équité et de
reproductibilité (C4) et une règle gelée de faisabilité du plafond, leçon directe de
l'arrêt D-012 (C5).

## 0. Clôture J6-AR001 — vérifiée, aucun résultat déguisé

- Le plafond gelé de 75 minutes a été atteint pendant `adaptive_replay` de 11313, avec
  12 triplets complets sur les 16 exigés. `j6_adaptive_replay_001_technical_stop.md` et
  D-012 le traitent correctement: **non-résultat technique**, aucune porte calculée,
  aucune analyse à n=12, aucune extension du plafond, aucune reprise sur 11301..11316,
  aucune promotion ni rejet. La formulation décisive est juste: l'hypothèse adaptative
  demeure « **non testée**, pas rejetée ».
- Aucune formulation fautive détectée dans D-012, le constat d'arrêt, D-013 ou le
  pré-enregistrement REF-001: les seules données J6-AR001 citées sont des métadonnées
  d'audit technique (comptes de runs, temps mural), aucune métrique scientifique
  partielle n'est publiée ni utilisée, et D-013 motive la réafférence par le brief
  (étape 3) et la campagne v3 déjà consignée, pas par les artefacts partiels.
- La porte de reprise est propre: D-012 ne rouvre rien pour J6-AR001 lui-même et exige
  hypothèse, pré-enregistrement et graines neufs pour toute reprise de consolidation.
  REF-001 ne contredit rien de cela.
- Leçon à retenir explicitement (voir C5): le plafond de J6-AR001 était crédible sur le
  papier — ma propre revue pré-calcul l'avait jugé « large » sur la base des
  0,75 min/run de J6-R001 — mais le débit réel a été d'environ 1,9 min/run et la
  campagne est morte au plafond. La projection temporelle ne peut plus être une
  recommandation non bloquante.

## Nouveauté et statut pré-calcul de REF-001 — vérifiés

- **Graines.** Balayage du dépôt: `12301`, `12316`, `12991` n'apparaissent que dans le
  pré-enregistrement, la demande de revue et les documents de pilotage; les occurrences
  dans `j6_replay_001_runs.json` (lignes 8173, 14257, 14923) sont des sous-chaînes de
  flottants (`0.5797412991…`), sans rapport. Graines vierges, smoke 12991 disjoint.
- **Code.** Aucun code REF-001 n'existe. Les seules correspondances `no_action` du
  dépôt sont l'infrastructure v3 préexistante (`learning/train_visual_jepa.py`,
  `tests/test_visual_jepa.py`, campagne `visual_bench_probe.md`), antérieure à REF-001
  et validée — c'est précisément « l'action-JEPA existe déjà » de D-013, pas une
  implémentation anticipée. Aucun `pixel_change` ni runner REF n'existe.
- **Monde.** La pièce REF est neuve, sans ceinture D/E/F; l'objet mobile sur rail est
  une manipulation nouvelle. Le substrat commun (jumeau de tête, JEPA v3, score borné,
  bins servo) est de la méthodologie gelée, pas un réemploi décisionnel. Les constantes
  TPR/FPR (0,75 / 0,70 / 0,05 / 0,07 / 0,10) et les marges 0,05 / 0,10 sont fixées ici,
  sans dérivation possible des résultats J6 (échelles sans rapport). La graine
  statistique `2026072002` est neuve.

## 1. Le contraste opérationnalise la réafférence sans sur-revendication

La revendication est explicitement opérationnelle — résidu faible sur mouvement propre
seul, résidu discriminant sur mouvement externe, au seuil tenu à part — et le
pré-enregistrement désavoue nommément segmentation, agentivité et causalité générale.
Les quatre hypothèses couvrent les quatre faces du phénomène: expliquer l'ego-motion
(H1), détecter l'externe pur (H2), détecter sous mouvement mixte (H3), ne pas confondre
(H4, spécificité sur une banque distincte de la calibration). C'est le « critère tenu à
part » exigé par D-013, et une AUC descriptive ne peut pas se substituer aux portes.
Conforme au point 2 de la définition du succès de `DEVELOPMENTAL_ARCHITECTURE.md` §2 et
§12.2 (« séparation entre changement auto-produit et externe »).

## 2. Objet externe — physique, visible, indépendant, non fuité

Vrai geom/joint MJCF sur rail, trajectoire par RNG distinct du babbling, jamais fonction
de l'action de tête; drapeau, position, vitesse et RNG confinés au manifeste d'audit;
le smoke asserte l'absence de toute colonne objet/label dans les tenseurs des modèles,
le mouvement objet bit-identique entre conditions et la visibilité contrefactuelle
normalisée `≥0,05` face à l'objet figé dans chacun des six bins. Le corpus à 50 %
d'épisodes objet-immobile tirés avant collecte donne au modèle l'occasion d'apprendre
les deux régimes sans jamais voir le drapeau. Structure conforme; la seule faiblesse
est la définition de la garde d'indépendance sur `external_only` (C2), où la tête est
tenue: une corrélation avec une action constante est mathématiquement indéfinie.

## 3. Équité action_jepa / no_action_jepa — bien construite

Même architecture, capacité, initialisation par graine, images, actions disponibles,
ordre de batchs, 4 500 pas, batch 256 et banques; l'unique différence est la mise à
zéro du vecteur d'action dans un prédicteur de capacité identique. Ce dispositif reprend
exactement la variante `no_action` validée en v2/v3 (`train_visual_jepa.py`,
`test_no_action_variant_ignores_action`), ce qui réduit le risque d'implémentation.
L'ablation est la bonne: toute différence H1–H4 entre les deux JEPA est attribuable à
l'usage de l'action, à calcul strictement égal. Les digests d'équité doivent être
assertés au smoke, pas seulement consignés (C4).

## 4. pixel_change — nécessaire mais insuffisante comme unique baseline simple

`pixel_change` est une bonne borne basse analytique et la règle anti-biomimétisme
(« pixel égale ou bat action → aucune promotion ») est correctement bloquante. Mais en
l'état, **aucune baseline ne reçoit l'information d'action**: `no_action_jepa` et
`pixel_change` en sont toutes deux privées. Or la règle 2 du brief exige une baseline
simple « recevant la même information ». Si `action_jepa` gagne, on ne pourra pas
distinguer « le résidu JEPA conditionné par l'action est nécessaire » de « n'importe
quelle correction analytique de l'ego-motion par l'amplitude d'action suffit ». Une
baseline analytique action-consciente, gratuite en calcul, ferme cette échappatoire
(C1). Sans elle, la conclusion « complexité payée » du point 7 de la demande serait
sur-revendiquée.

## 5. Séparation des banques et seuil — conformes

Cinq banques par graine, issues de pièces, trajectoires et espaces de graines disjoints
du corpus et entre eux, 128 paires par bin équilibrées 64/64 par contexte, jamais
entraînées; labels simulateur réservés au calcul final des métriques. Le seuil est
défini par méthode, graine et bin comme le plus petit score tel qu'au plus 5 % des 128
observations `self_calibration` le dépassent, égalités classées non-externes, puis figé
— définition déterministe, sans degré de liberté, avec FPR de calibration `≤ 4,69 %`
par construction (6/128) rapportée sans réutilisation. `self_test` distincte de la
calibration fait de H4 un vrai test de généralisation du seuil. La seule imprécision à
geler est l'agrégation « bins favorables » de H2/H3 (C4-iv).

## 6. Scores et régimes dégénérés — un risque réel à instrumenter

- **Unités.** Le score JEPA `pred/(pred+copy)` est sans dimension et borné; le score
  `pixel_change` divisé par 255 suppose des trames uint8 — à préciser (R2), mais toute
  transformation monotone est neutralisée par la calibration par quantile propre à
  chaque méthode, donc aucune porte n'est sensible à ce choix.
- **Régime dégénéré du score borné.** Quand le changement réel d'une paire est quasi
  nul (`MSE(copie)` → 0), le score JEPA tend vers 1 quel que soit le modèle (plancher
  de bruit de la prédiction au numérateur). Des paires à mouvement de tête minuscule
  dans `self_calibration` peuvent donc pousser le seuil du 95e percentile vers 1 et
  écraser mécaniquement la TPR sur les banques externes, où un changement imprévisible
  donne un score proche de 0,5 (prédiction ≈ copie). Ce biais est **conservateur** — il
  ne peut pas fabriquer une promotion — mais il peut produire un échec H2/H3/H4
  inattribuable: « le résidu ne sépare pas » alors que c'est la métrique qui dégénère.
  Le pré-enregistrement exige que chaque échec soit non ambigu; il faut donc un filtre
  structurel de construction des banques self et des diagnostics gelés (C3).
- `pixel_change` dégénère dans l'autre sens (score → 0 sur paire immobile), sans danger
  pour ses portes.

## 7. Hypothèses, directions, agrégations et statistiques

- **Directions correctes**: H1 = `no_action − action` sur l'erreur `self_test` (positif
  favorable); H2/H3 = différences de TPR `action − baseline` (positif favorable); H4 =
  plafonds absolus de FPR. Aucun ratio, donc aucun analogue B2 nécessaire.
- **Famille Holm**: les quatre comparaisons de supériorité (action−no_action et
  action−pixel, sur external puis mixed) partagent une correction Holm commune —
  cohérent, et conservateur pour chaque revendication puisque la promotion est
  conjonctive. H1 est un test unique hors famille; H4 est déterministe sans p. Ce
  découpage est acceptable et `holm_correction` s'y applique directement.
- **Exactitude à n=16**: `exact_sign_flip_pvalue` énumère 2^16 assignations (sous la
  limite `n ≤ 20` du module), p minimale ≈ 1,5e-5, largement sous le 0,0125 requis par
  Holm à quatre membres. IC BCa à 10 000 rééchantillonnages disponibles; la graine
  `2026072002` doit être passée explicitement (défaut 0 du module, R1). Aucun test de
  non-infériorité n'est requis ici; aucune fonctionnalité manquante dans
  `learning/paired_stats.py`.
- **Portes absolues** (TPR moyennes ≥ 0,75 / 0,70; FPR ≤ 0,07 et max de bin ≤ 0,10):
  des seuils de point sans test — choix strict et gelé, défendable pour un détecteur.
- **À geler (C4-iv)**: « ≥5/6 bins favorables face à chaque baseline » doit être défini
  comme dans H1 — différence moyenne de bin sur les 16 graines strictement positive —
  et le plafond « aucune FPR de bin > 0,10 » comme moyenne inter-graines par bin.

## 8. Budgets, arithmétique et plafond

- Arithmétique exacte: 20×600 = 12 000 images; 2 400 décisions (une pour cinq images à
  10 Hz, cohérent avec les campagnes antérieures); 4 500×256 = 1 152 000
  exemples-gradient; 2 conditions × 16 graines = 32 runs. `pixel_change` est analytique
  et hors budget d'entraînement, ce qui est correct.
- **Le plafond de 60 minutes est le point le plus risqué du protocole.** J6-AR001 vient
  de mesurer ≈ 1,93 min/run réels (73,22 min / 38 runs) sur le même substrat et le même
  budget de pas; 32 runs à ce débit font ≈ 62 minutes, au-dessus du plafond, avant même
  la génération du corpus et l'évaluation des cinq banques. REF-001 est plus léger
  (pas d'évaluations par bloc), mais personne ne l'a mesuré. Répéter l'erreur de
  dimensionnement qui a produit D-012 serait cette fois une faute évitable: la
  faisabilité doit être prouvée au smoke par une règle gelée avant ouverture des
  graines (C5). La reprise au niveau run et l'arrêt technique sans dépassement
  silencieux sont conformes.

## 9. Gardes et fermeture des issues post hoc

Garde apprenant (−20 % sur `learner_validation` pour les deux JEPA), garde action utile
(variance d'action non nulle par bin là où la tête bouge — `external_only` en est
logiquement exclue), visibilité objet jamais calibrée sur les graines réservées,
non-fuite, équité et budget: chaque échec a un statut désigné (non interprétable ou
arrêt technique) et aucune correction sur les graines n'est permise. Les règles de
décision couvrent toutes les issues sans zone grise, y compris le rejet quand pixel
égale ou bat le candidat. Deux compléments nécessaires: la garde d'indépendance doit
être définie là où elle est calculable (C2), et l'attribution des échecs de détection
doit être protégée du régime dégénéré du score (C3). Une clause de clôture explicite de
la variante, sur le modèle de J6-AR001, manque (R3).

## 10. Suffisance du smoke 12991

Le smoke demandé couvre déjà: vrai geom/joint, mouvement objet bit-identique entre
conditions et indépendant des actions, visibilité contrefactuelle par bin, disjonction
des espaces de graines et des images, 128 paires/bin, budgets exacts, absence de
colonnes objet/label dans les tenseurs. Pour prouver la parité bit à bit et la
reproductibilité **avant** campagne, il doit aussi asserter l'identité d'initialisation
et d'ordre de batchs entre conditions, l'identité de capacité des deux prédicteurs, la
recomputabilité des seuils et la faisabilité temporelle (C4, C5). Avec ces ajouts, le
smoke prouve tout ce que le point 10 de la demande exige.

## Corrections bloquantes (amendements pré-calcul, aucune valeur issue de données réservées)

- **C1 — Baseline analytique action-consciente.** Ajouter `pixel_change_action`:
  par graine et bin, ajustement des moindres carrés de `pixel_change` sur l'amplitude
  d'action appliquée, ajusté **uniquement** sur `self_calibration`; le score est le
  résidu positif de cette régression, seuillé par la même procédure de quantile que les
  autres méthodes. Coût nul (analytique, aucun entraînement). Étendre la règle
  anti-biomimétisme: si `pixel_change_action` égale ou bat `action_jepa` sur les portes
  H2/H3, aucune promotion. Sans cette baseline, aucune méthode simple ne reçoit
  l'information d'action et la conclusion « complexité payée » serait invalide au sens
  de la règle 2 du brief.
- **C2 — Garde d'indépendance calculable.** Restreindre la corrélation absolue
  action–déplacement objet `≤ 0,05` aux ensembles où la variance d'action est non nulle
  (corpus et `mixed`); pour `external_only`, remplacer par l'assertion structurelle au
  smoke: commande de tête constante conforme au protocole et flux RNG objet disjoint du
  RNG d'actions. En l'état, la garde est indéfinie (corrélation avec une constante) et
  son interprétation serait laissée à l'implémentation.
- **C3 — Régime dégénéré petit-changement.** (a) Construction: les paires des banques
  `self_calibration` et `self_test` proviennent exclusivement de transitions où une
  commande de mouvement non nulle a été appliquée (critère structurel, aucun seuil
  nouveau). (b) Diagnostics gelés, descriptifs et non décisionnels: distribution de
  `MSE(copie)` par banque, méthode et bin, et relation score–`MSE(copie)`, consignées
  dans l'export d'audit afin qu'un échec H2/H3/H4 soit attribuable à la séparation
  elle-même et non à la saturation du score borné sur paires quasi immobiles.
- **C4 — Assertions smoke d'équité et de gel des définitions.** Ajouter au smoke 12991:
  (i) digests identiques d'initialisation et d'ordre de batchs entre `action_jepa` et
  `no_action_jepa` par graine; (ii) identité de capacité: à l'initialisation, la passe
  avant d'`action_jepa` avec actions mises à zéro est bit-identique à celle de
  `no_action_jepa`; (iii) seuils recomputables hors ligne au chiffre près depuis les
  scores `self_calibration` consignés. (iv) Dans le pré-enregistrement, geler
  l'agrégation: « bin favorable » = différence moyenne de bin sur les 16 graines
  strictement positive (parallèle exact de H1), et plafonds de FPR par bin entendus en
  moyenne inter-graines.
- **C5 — Règle gelée de faisabilité du plafond.** Le smoke 12991 exécute une répétition
  temporelle complète d'un run par condition (génération de corpus, entraînement,
  évaluation des cinq banques) et consigne le temps mural. Règle gelée: si
  `32 × temps_mesuré_par_run` dépasse le plafond de 60 minutes, le plafond est amendé
  **avant** l'ouverture de toute graine réservée, avec la projection documentée dans le
  manifeste; aucune ouverture de graine tant que la projection ne tient pas sous le
  plafond en vigueur. Cette règle n'utilise que des métadonnées techniques (smoke et
  audit D-012), jamais des données scientifiques réservées. C'est la conversion en
  porte bloquante de la leçon exacte qui a coûté J6-AR001.

## Recommandations non bloquantes

- **R1.** Passer explicitement la graine statistique `2026072002` à `bca_bootstrap_ci`
  (défaut 0 dans le module) et consigner que tous les tests sont exacts à n=16.
- **R2.** Préciser le domaine des trames pour `pixel_change` (uint8, division par 255)
  afin d'éviter une double normalisation — sans effet sur les portes grâce à la
  calibration par quantile propre à chaque méthode.
- **R3.** Ajouter la clause de clôture explicite: quel que soit le verdict, REF-001
  clôt cette variante; toute reprise exige hypothèse, fichier et graines neufs — comme
  J6-AR001 l'avait fait, ce qui a rendu D-012 mécanique et incontestable.
- **R4.** Rapporter l'AUC descriptive par bin en plus de l'agrégat, et la corrélation
  amplitude d'action–score déjà prévue, pour éclairer la lecture sans peser sur les
  portes.
- **R5.** Préparer le rapport de résultats pour distinguer explicitement « détection
  externe démontrée » (H2–H4) de « explication de l'ego-motion démontrée » (H1): les
  deux peuvent échouer indépendamment et la revendication de réafférence exige les
  deux, conformément aux règles de décision gelées.

## Autorisation

Une fois les corrections C1–C5 intégrées au pré-enregistrement comme amendements
pré-calcul datés et additifs, **l'implémentation peut commencer, puis le smoke 12991
peut être exécuté**. Les graines `12301..12316` restent interdites jusqu'à intégration
de toutes les corrections bloquantes, un smoke vert — y compris la règle de
faisabilité temporelle C5 — et un manifeste concordant avec le pré-enregistrement
amendé. Toute promotion future reste interdite avant une seconde revue contradictoire
des résultats.
