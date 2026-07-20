# Revue contradictoire pré-calcul J6-AR001 — replay adaptatif

Date: 2026-07-20. Revue demandée avant implémentation, smoke et tout calcul (état main
`e2ef324`). Fichiers audités intégralement:
`docs/research/j6_adaptive_replay_001_preregistration.md`,
`docs/research/j6_replay_001_results_review.md`, `DECISIONS.md` (D-010, D-011),
`learning/paired_stats.py`; en complément pour l'audit de nouveauté:
`docs/research/j6_replay_001_preregistration.md` (avec amendements B1/B2/B3),
`docs/research/j6_replay_001_results.md` (temps mural uniquement) et un balayage du
dépôt. Aucun calcul lancé, aucun smoke, aucune graine ouverte, aucun fichier autre que
la présente revue modifié.

## Verdict

**AUTORISER AVEC CORRECTIONS BLOQUANTES.** Le protocole est réellement neuf, équitable
entre conditions, causal dans sa formule, correctement dimensionné et verrouillé par
des portes qui empêchent les trois échappatoires principales (abandonner la rétention,
masquer une région, promouvoir un calendrier inactif). Quatre ambiguïtés de gel doivent
être levées par amendements pré-calcul **textuels et additifs** — aucune ne propose de
valeur réglée sur J6-R001 — faute de quoi elles deviendraient des degrés de liberté
post hoc au moment de l'analyse.

## 0. Nouveauté de la campagne — vérifiée

- **Mondes.** D/E/F remplacent le champ visuel structuré entier (ceinture de six
  secteurs: damiers carmin/blanc, barres verticales cyan/bleu nuit, barres horizontales
  ambre/violet) au lieu du landmark unique déplacé de A/B/C. Aucun réemploi des mondes
  A/B/C; corps, télévision `[130°,170°]` et distribution de babbling sont le substrat
  commun légitime, pas une réutilisation de la manipulation.
- **Graines.** Balayage du dépôt: `11301`, `11316`, `11991` n'apparaissent que dans le
  pré-enregistrement, `CLAUDE_REVIEW_REQUEST.md` et les documents de pilotage. Les
  occurrences de « 11316 » dans `j6_replay_001_runs.json` (lignes 10289, 14822, 16342)
  sont des sous-chaînes de flottants (`0.42678019404411316`, etc.), sans rapport. Les
  graines de campagne sont vierges; le smoke `11991` est disjoint de `11301..11316` et
  des graines historiques `10301..10312`, `10991`.
- **Code.** Aucun code J6-AR001 n'existe: `learning/` ne contient que `j6_replay.py`
  (J6-R001) et `scripts/research/` ne contient aucun runner adaptatif. La séquence
  « gel → revue → implémentation » est respectée.
- **Retuning.** Les seuils `0,05` (B1, H1, H3a), `5 %` et `10 %` (H3b) sont hérités du
  gel J6-R001 **antérieur** aux résultats, pas des résultats. La marge `0,02` de H2 est
  nouvelle mais justifiée structurellement (40 % de l'effet minimal exigé d'uniform).
  Les constantes de la formule sont toutes structurelles (voir §3). Le passage n=12→16
  est une décision de puissance motivée par le quasi-échec Holm de H3 dans J6-R001:
  c'est un usage légitime et déclaré des résultats antérieurs (dimensionnement), qui ne
  touche ni seuils ni marges et précède toute donnée J6-AR001.

## 1. Mondes D/E/F et crédibilité de l'oubli

Le défaut diagnostiqué sur A dans J6-R001 (landmark unique → oubli naïf `0,0397`,
sous le seuil B1) est directement corrigé: la ceinture physique couvre les six bins
structurés, donc chaque compétence de décision subit la non-stationnarité. Les
transitions D→E et E→F changent à la fois le motif entier, la palette et l'éclairage —
des changements plus étendus que A→B de J6-R001, qui avait produit un oubli naïf de
`0,1414` avec un seul landmark déplacé plus une baisse de lumière. E ne subit qu'une
session d'interférence (F), exactement comme B dans J6-R001 où B1 est passée. La
probabilité que B1 passe sur D et E est donc crédible sans être garantie — et c'est le
rôle de la garde, pas un défaut.

Le smoke ne vérifie que la construction (vrai geom par secteur, distances visuelles
pairées `≥ 0,08` dans chaque bin, luminance E `≤ 0,75×D`, chroma F ≠ D `≥ 5 %`); il ne
mesure ni ne calibre l'oubli, et la garde B1 n'est jamais calibrée sur lui. Le
calendrier de graines de pièces indépendant du domaine neutralise le confondant des
objets de fond. Conforme.

## 2. Équité d'information et de calcul

- Les trois conditions évaluent la **banque de suivi complète avant chaque bloc de
  100 pas** et consignent les mêmes erreurs; le candidat ne gagne donc ni information
  ni calcul d'évaluation. C'est la fermeture correcte de l'échappatoire classique.
- Mêmes corpus bit à bit, mêmes 1 500 pas par session, batch 256, mêmes banques,
  mêmes évaluations finales; les baselines gardent le corpus ancien en lecture seule.
- Les banques finales ne pilotent jamais `rho` (garde de construction + assertion
  smoke); aucune fuite vers la décision n'est possible si le smoke asserte réellement
  la disjonction des espaces de graines et les digests — voir C3 pour l'enforcement.

Aucune asymétrie détectée dans le texte. Le point faible n'est pas la règle mais sa
vérifiabilité: le pré-enregistrement ne liste pas d'assertion smoke sur la parité du
nombre d'évaluations ni sur la composition exacte des batchs adaptatifs (C3).

## 3. Formule `d_old`/`d_current`/`q`/`rho`

- **Causalité.** Toutes les grandeurs sont mesurées avant le bloc; `e_acquisition` est
  figée à la fin de la session du domaine ancien, `e_session_start_current` immédiatement
  avant le premier pas de la session. Aucun lookahead, aucune mise à jour intra-bloc.
- **Unités.** `d_old` et `d_current` sont tous deux des excès relatifs sans dimension;
  `q` est un partage borné par 0,5; pas d'incohérence d'unités.
- **Quantification.** `rho = floor(16q+0,5)/16 ∈ {0, 1/16, …, 1/2}` donne `256×rho`
  entier: la composition de batch est exacte, sans arrondi caché. `q < 0,5` par
  construction, le clip est redondant mais inoffensif.
- **Constantes.** Toutes structurelles: `0,5` = référence uniform (plafond), `0,80` =
  garde apprenant gelée de 20 % antérieure à J6-R001, `1e-3` = amortisseur numérique,
  `1/16` = granularité du batch. Aucune n'est réglée sur J6-R001.
- **Comportement aux bords.** Au premier bloc de E: `d_old ≈ 0`, `d_current = 0,20`
  exactement (ratio 1 − 0,80) → `rho = 0`; la rampe est saine (apprendre d'abord,
  consolider ensuite). `rho = 0` explicite quand rien n'est mesuré. Noter que dès que le
  domaine courant est acquis (`d_current = 0`), `rho` sature rapidement vers 0,5 même
  pour une dette ancienne faible (`d_old = 0,01` → `rho = 7/16`) à cause de l'amortisseur
  `1e-3`: comportement gelé et cohérent, à décrire dans le rapport (R4), pas un défaut.
- **Pas de priorité cachée.** L'échantillonnage des anciennes paires reste celui
  d'uniform_50 (épisode uniforme puis paire uniforme); seule la fraction change. En F,
  le mécanisme ne peut pas cibler le domaine ancien endetté — c'est le minimalisme
  revendiqué, pas une fuite.
- **Ambiguïté à lever (C2).** Le texte ne dit pas explicitement que `e_t`,
  `e_acquisition` et `e_session_start_current` de la formule proviennent exclusivement
  de la banque de suivi. La garde de construction l'implique (les banques finales ne
  pilotent jamais `rho`), mais une formule gelée ne doit laisser aucune lecture double.

## 4. Séparation des banques, B3, budgets, plafond, reprise

- **Trois ensembles disjoints** par graine et domaine, espaces de graines non
  recouvrants, 32 ancres par cellule (64 par compétence), assertion smoke sur digests
  et absence d'image commune. Conforme et plus strict que J6-R001 (qui n'avait pas de
  banque de suivi séparée).
- **B3 renforcé:** checkpoint post-D unique réutilisé par les trois conditions —
  l'identité bit à bit est garantie par construction et assertée au smoke (poids,
  optimiseur, sondes, évaluations). Supérieur à la simple assertion d'égalité de
  J6-R001.
- **Budgets exacts:** 20×200×3 = 12 000 images; 800×3 = 2 400 décisions; 3×1 500 =
  4 500 pas; 4 500×256 = 1 152 000 exemples-gradient; 16×3 = 48 runs. Tout concorde.
- **Plafond crédible:** J6-R001 a mesuré 26,9 minutes pour 36 runs (~0,75 min/run);
  48 runs ≈ 36 minutes, plus le surcoût des évaluations par bloc (~1 150 ancres × 15
  blocs × 3 sessions ≈ 4–5 % du calcul d'entraînement par condition). La marge sous
  75 minutes est large; l'arrêt technique sans dépassement silencieux est conforme.
- **Reprise** au niveau run avec manifeste et digests: conforme, avec la précision que
  la reprise d'un triplet doit repasser par le checkpoint post-D partagé (couvert par
  l'arrêt technique sur digest divergent).

## 5. Hypothèses, statistiques et compatibilité avec `paired_stats.py`

- **n=16 ≤ 20:** l'énumération exacte de `exact_sign_flip_pvalue` (2^16 = 65 536
  assignations, chunkées) s'applique; p minimale 2^-16 ≈ 1,5e-5, très en dessous du
  0,025 exigé par Holm à deux membres. Aucun recours Monte Carlo nécessaire.
- **Non-infériorité:** `noninferiority_sign_flip_pvalue(diffs, margin)` teste
  H0: moyenne ≥ marge contre l'infériorité; rejeter ⇒ non-inférieur. Compatible avec
  AR-H2 (diffs = `regression_adaptive − regression_uniform_50`, positif = perte, marge
  `0,02`) et AR-H3b (diffs absolues `e_adaptive_F − e_naive_F`, marge scalaire = 5 % de
  la grand-moyenne naïve F — même construction data-dépendante mais formulaire que le
  H3 de J6-R001). Directions vérifiées, y compris `gain_F` positif = candidat meilleur
  pour H3a (test « greater »).
- **Familles Holm:** {D,E} pour H1, {D,E} pour H2, {H3a,H3b} pour H3 — structure
  identique au précédent J6-R001. La règle de promotion étant conjonctive (tout doit
  passer), ce découpage ne gonfle pas le risque de promotion erronée; il est
  conservateur pour chaque revendication individuelle. `holm_correction` s'applique
  directement.
- **B1** sans p-value (moyenne ≥ 0,05 et borne BCa basse > 0): supporté par
  `bca_bootstrap_ci`. **Attention d'implémentation:** la graine statistique gelée
  `2026072001` doit être passée explicitement aux fonctions (`seed` par défaut 0 dans
  `paired_stats.py`) — voir R1.
- **B2** conservée avec test primaire relatif et accord de signe absolu: adéquate pour
  les revendications directionnelles (B1, H1). Pour la non-infériorité AR-H2, l'accord
  de signe strict est indéfini en pratique: le résultat espéré est une différence
  proche de zéro, où le signe des moyennes relative et absolue est un tirage au sort —
  la porte telle qu'écrite peut rejeter un candidat valide sur du bruit ou, pire,
  laisser l'analyste choisir sa lecture. À geler maintenant (C1).
- **AR-H3a sous-spécifiée:** la formule `gain_F` ne dit pas si `e_*_F` est la moyenne
  des six bins par graine (agrégat puis ratio) ou si le gain est calculé par bin puis
  moyenné — les deux diffèrent numériquement. AR-H1 et AR-H2 précisent leur ordre
  (« moyenne des six différences », « différence entre les moyennes des six bins »);
  H3a doit faire de même, ainsi que la moyenne inter-graines implicite de son plafond
  par bin (C2).

## 6. Règles de promotion et d'arrêt — les trois échappatoires sont fermées

- **« Résoudre » H3 en abandonnant la rétention:** impossible. AR-H2 impose la
  non-infériorité à marge `0,02` (40 % de l'effet minimal exigé d'uniform), un plafond
  de perte moyenne `0,05` par bin et l'accord B2; H2 échoue ⇒ rejet. Un `rho` effondré
  vers 0 (candidat ≈ naïf) échoue H2 dès que H1 passe (l'écart naïf−uniform ≥ 0,05
  excède la marge 0,02) et échoue la garde d'activation.
- **Masquer une région défaillante:** impossible. Interdiction explicite des moyennes
  compensatoires inter-domaines et inter-bins, plafonds par bin dans H2 (`0,05`), H3a
  (`0,05`) et H3b (`10 %` — exactement la porte régionale qui a tué uniform à 14,25 %
  dans J6-R001). Le candidat doit passer la porte même qui a causé l'échec précédent.
- **Promouvoir un calendrier non activé:** impossible. La garde d'activation exige au
  moins deux valeurs de `rho` dont une strictement intérieure, sur ≥ 12/16 graines,
  dans **chacune** des sessions E et F; sinon non interprétable. Un `rho` saturé à 0,5
  (candidat ≈ uniform) échoue H3a par construction et la garde d'activation.
- Les branches B1/H1/H2/H3/gardes couvrent toutes les issues sans zone grise, la
  clôture « quel que soit le verdict, la réafférence redevient la suite » élimine
  l'incitation à prolonger, et la promotion reste conditionnée à une seconde revue.

## 7. Complexité payée

Le candidat ne reçoit aucune information ni calcul refusés aux baselines; son unique
ajout est une règle scalaire par bloc, de coût négligeable. Pour être promu il doit
simultanément battre uniform en plasticité (supériorité stricte H3a), égaler sa
rétention à 40 % près de l'effet minimal (H2) et rester non inférieur à naïf (H3b).
La complexité est payée. Réserve honnête à consigner d'avance: une fraction statique
basse (non testée, et D-011 fige trois conditions sans quatrième) pourrait en principe
suffire; une promotion ne pourra donc pas revendiquer que l'**adaptativité** per se est
nécessaire, seulement que ce calendrier minimal résout le compromis (R3).

## Corrections bloquantes (amendements pré-calcul textuels, aucun seuil réglé)

- **C1 — Définir B2 pour la non-infériorité AR-H2.** Remplacer l'accord de signe
  strict par: « Pour AR-H2, B2 est violée uniquement si la porte relative passe alors
  que la différence absolue appariée `adaptive − uniform_50` montre une perte
  significative: moyenne > 0 **et** borne BCa 95 % basse > 0. Un simple désaccord de
  signe autour de zéro ne viole pas B2. » Cela préserve l'intention (détecter un
  artefact de dénominateur contredisant la revendication) sans rendre la porte
  aléatoire au voisinage de zéro, qui est précisément le résultat espéré.
- **C2 — Geler l'ordre d'agrégation d'AR-H3a et la source des grandeurs de la
  formule.** (a) Préciser: l'agrégat par graine est la moyenne des six erreurs de bin
  sur la banque finale F; `gain_F` est calculé sur ces agrégats; le critère « 5/6 bins
  favorables » utilise la réduction relative par bin moyennée sur les 16 graines, et le
  plafond « aucun bin pire de plus de 0,05 relatif » s'entend en moyenne inter-graines
  (parallèle exact d'AR-H2). (b) Préciser que `e_t`, `e_acquisition` et
  `e_session_start_current` de la formule `rho` proviennent exclusivement de la banque
  de suivi, jamais des banques finales.
- **C3 — Assertions smoke d'équité et de composition.** Ajouter aux assertions du
  smoke 11991: (i) chaque batch d'`adaptive_replay` contient exactement `256×rho`
  anciennes paires et `256×(1−rho)` courantes; (ii) `rho` est recomputable hors ligne
  au chiffre près depuis les `d_old`/`d_current` consignés; (iii) les trois conditions
  exécutent le même nombre d'évaluations de suivi, aux mêmes pas, sur des banques de
  même taille (parité de calcul effective, pas seulement déclarée).
- **C4 — Définir la fraction TV de la garde.** Préciser, conformément à J6-R001, que
  la « fraction effective de replay télévision » est la part des **paires rejouées**
  dont l'angle cible est télévision (échelle invariante à `rho`), et que les blocs à
  `rho = 0` sont exclus du dénominateur; si une session entière a `rho = 0`, la garde
  TV y est vide et la garde d'activation statue. Sans cette précision, une lecture
  « masse TV sur tout le batch » ferait passer trivialement la garde à faible `rho`.

## Recommandations non bloquantes

- **R1.** Passer explicitement la graine statistique gelée `2026072001` à
  `bca_bootstrap_ci` (le défaut du module est 0) et consigner dans l'analyse que les
  tests sont exacts (aucun Monte Carlo à n=16).
- **R2.** Consigner le temps mural par run dès le smoke pour confirmer la marge sous le
  plafond de 75 minutes (attendu ≈ 36–40 minutes au rythme mesuré de J6-R001), sans en
  faire un seuil.
- **R3.** Inscrire dès maintenant dans le pré-enregistrement la limite de portée: une
  promotion ne revendiquera pas la nécessité de l'adaptativité face à une fraction
  statique basse non testée; toute sonde de simplification exigerait son propre
  pré-enregistrement.
- **R4.** Décrire dans le rapport la dynamique attendue de la formule (rampe `rho = 0`
  en début de session, saturation rapide vers 0,5 une fois le domaine courant acquis)
  pour que la lecture des trajectoires `rho` ne soit pas improvisée post hoc.
- **R5.** Consigner par bloc un digest des évaluations de suivi de chaque condition
  afin que l'audit de parité d'information soit vérifiable depuis les artefacts, comme
  l'a été B3 dans J6-R001.

## Autorisation

Une fois les corrections C1–C4 intégrées au pré-enregistrement comme amendements
pré-calcul datés (aucune autre modification), **l'implémentation peut commencer, puis
le smoke 11991 peut être exécuté**; les graines `11301..11316` restent interdites
jusqu'à un smoke vert dont le manifeste concorde avec le pré-enregistrement amendé, et
toute promotion reste conditionnée à une seconde revue contradictoire des résultats.
