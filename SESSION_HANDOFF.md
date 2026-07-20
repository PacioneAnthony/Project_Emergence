# Émergence - Handoff de session

Date: 2026-06-12

## Instruction de reprise impérative

Une nouvelle session Codex doit lire `PILOTAGE.md`, ce fichier, `ANTHONY_INBOX.md` et `COLLABORATION_PROTOCOL.md`. Si ANT-007 contient un chemin de session, elle analyse immédiatement les artefacts. Sinon, elle indique brièvement que l'essai physique du runbook reste l'action attendue d'Anthony, sans réinventer le plan.

Anthony a délégué les choix logiciels et architecturaux à Codex, avec revue Claude aux portes importantes. Codex ne doit donc pas demander à Anthony de choisir comment pré-enregistrer J0, quelle architecture logicielle employer ou quelle baseline implémenter. Si le travail est réalisable dans le dépôt, il doit l'exécuter plutôt que s'arrêter à une explication.

## Objectif actif

Valider physiquement l'instrumentation J0 par une session courte avant d'autoriser la session de 30 minutes.

## État valide

- La navigation 2D est conservée comme branche historique, plus comme objectif principal.
- `DEVELOPMENTAL_ARCHITECTURE.md` définit la vision développementale.
- `DEVELOPMENTAL_ARCHITECTURE_REVIEW.md` recommande de simplifier avant implémentation.
- `COLLABORATION_PROTOCOL.md` répartit le travail entre Anthony, Codex et Claude.
- `PILOTAGE.md` est le tableau de bord humain et contient les prompts de reprise.
- Anthony a validé D-002: LNN, JEPA, motivation apprise et LMM deviennent des branches expérimentales conditionnelles jusqu'à ce qu'ils battent leurs baselines pré-enregistrées.
- D-004 délègue les décisions logicielles, architecturales et expérimentales à Codex; Claude intervient comme contradicteur technique, Anthony comme technicien et validateur matériel.
- Les six informations matérielles ANT-001 à ANT-006 ont été reçues et intégrées le 2026-06-11.
- L'IMU est sur la tête mobile; le microphone initial est celui de la BRIO 100; la plage servo initiale est 10 à 170 degrés.
- Le quota de données initial est de 200 Go, sans suppression silencieuse ni durée fixe de rétention.
- Deux à trois autres personnes peuvent participer occasionnellement aux futurs tests de familiarité.
- J0 est le prochain jalon bloquant.
- `J0_PROTOCOL.md` pré-enregistre les hypothèses, formats, seuils et stop-loss de J0.
- Le paquet `j0/` implémente protocole EMG1, événements, recorder append-only, replay, qualité, synchronisation et capture multimodale.
- `peripheral/brain_stem/brain_stem.ino` compile pour Arduino Mega et publie IMU 100 Hz, ultrason/piézo 20 Hz, état servo et réponses de synchronisation.
- Le firmware EMG1 a été flashé avec succès après connexion de la Mega sur le bon port USB.
- La première capture physique, session `j0-20260612T122444.759901Z-e6395a2f`, a été analysée comme tentative avortée: WASAPI refusait l'ouverture de la BRIO 100 et l'ouverture série enregistrait des octets antérieurs au redémarrage automatique de la Mega.
- La capture audio essaie désormais DirectSound, MME, WASAPI puis WDM-KS avec la fréquence native de chaque périphérique. DirectSound à 44,1 kHz a été ouvert et enregistré avec succès sur ce PC.
- La CLI attend désormais 2,5 secondes après ouverture série, purge les buffers de démarrage et ne lance le chrono qu'une fois la caméra et le microphone prêts.
- La session complète courte `j0-20260612T123848.687322Z-afac9e86` contient 10 719 événements sur 61,9 s, sans perte, erreur CRC, corruption de blob ni divergence de replay. Les quatre commandes servo 90/80/100/90 ont été acquittées.
- Le triple tapotement est détecté comme trois impacts. Il a révélé que `time.monotonic_ns()` reposait ici sur `GetTickCount64` à 15,625 ms, insuffisant pour certifier la cible de 20 ms.
- Tous les horodatages J0 utilisent désormais `perf_counter_ns()` (`QueryPerformanceCounter`, résolution annoncée 100 ns). L'audio est ancré sur l'heure ADC PortAudio puis avancé par compteur exact d'échantillons; le smoke test réel produit des blocs espacés exactement de 50 ms.
- La session corrective `j0-20260612T125102.028740Z-a0dc0f70` valide la synchronisation: vidéo `+12,69 ms`, IMU `-10,78 ms`, maximum `12,69 ms`, sous la cible de 20 ms. Elle contient 3 743 événements sans perte ni corruption.
- Anthony signale que la tête v0.1 repose directement sur l'axe du servo et reste fragile; les mouvements de la session 60 s semblaient tremblants.
- `j0 mechanics` mesure sur v0.1 des ratios de stabilisation gyroscopique de `5,22`, `13,45` et `9,72` après les déplacements, contre une limite comparative provisoire de `3,0`.
- D-005 interdit tout nouvel essai moteur sur v0.1. Le firmware patch 2 compile et laisse le servo détaché au démarrage comme en failsafe; il n'est pas encore flashé.
- `BENCH_DESIGN.md`, produit avec Claude, est la référence du banc successeur v1.0: la structure porte la tête et le servo ne transmet que le couple.
- `windows_client/flash_j0_firmware.ps1` détecte automatiquement la Mega, refuse `COM1` et n'exécute aucun flash si la carte n'est pas visible.
- Le logiciel est prêt pour la qualification physique de `J0_RUNBOOK.md`.

## Fichiers à lire en premier

1. `PILOTAGE.md`
2. `SESSION_HANDOFF.md`
3. `ANTHONY_INBOX.md`
4. `COLLABORATION_PROTOCOL.md`
5. `DEVELOPMENTAL_ARCHITECTURE_REVIEW.md`
6. `DEVELOPMENTAL_ARCHITECTURE.md`
7. `DECISIONS.md`
8. `peripheral/brain_stem/brain_stem.ino`
9. `BENCH_DESIGN.md`

## Informations et actions attendues d'Anthony

- ANT-009: terminer avec Claude les mesures, la modélisation, l'impression et l'assemblage du banc v1.0 décrit dans `BENCH_DESIGN.md`.
- ANT-008: valider, remplacer ou différer l'achat du kit AS5600 décrit dans `HARDWARE_PURCHASES.md`.

## Prochaine action Codex

Lorsque Anthony signale que le banc v1.0 est prêt, Codex doit:

- relire les écarts apportés à `BENCH_DESIGN.md` et mettre à jour les paramètres mécaniques;
- faire flasher le firmware patch 2 passif;
- exécuter une qualification courte 90/80/100/90 et produire `quality`, `clap-sync`, `replay` et `mechanics`;
- exiger un ratio de stabilisation inférieur ou égal à 3,0, sans jeu ni tremblement persistant observé;
- autoriser ensuite la session J0 de 30 minutes, estimée à environ 2 Go au débit actuel;
- intégrer ANT-008 et préparer le support AS5600 pour J1a.

## Actions par acteur

Action Codex: logiciel J0 court, firmware passif et métrique mécanique prêts; attendre le nouveau banc avant toute commande moteur.  
Action Anthony: poursuivre avec Claude le banc v1.0 et signaler lorsqu'il est assemblé; arbitrer ANT-008 quand le choix AS5600 doit être commandé.  
Action Claude: poursuivre la conception mécanique de `BENCH_DESIGN.md` avec Anthony.  
Blocage: banc v1.0 non construit; firmware patch 2 non flashé; session J0 de 30 minutes suspendue.

## Modifications de cette session

- création de `PILOTAGE.md` comme tableau de bord humain et point d'entrée du projet;
- ajout de D-004 dans `DECISIONS.md` pour formaliser la délégation technique;
- révision de `COLLABORATION_PROTOCOL.md` afin d'attribuer clairement les responsabilités;
- ajout du prompt de reprise autonome et des actions par acteur dans ce handoff;
- ajout du lien vers `PILOTAGE.md` dans `README.md`.
- création de `J0_PROTOCOL.md`, `J0_RUNBOOK.md` et `HARDWARE_PURCHASES.md`;
- implémentation du paquet `j0/`, de la CLI et du point d'entrée Windows;
- remplacement du firmware texte par le protocole binaire EMG1;
- installation de `sounddevice` dans `env_windows` et détection des périphériques;
- ajout des tests J0 ciblés.
- ajout du repli automatique des pilotes audio Windows, de l'attente de redémarrage série et de la synchronisation du début effectif des captures;
- analyse et conservation de la première session physique avortée comme artefact de diagnostic.
- validation de l'intégrité de la session physique complète de 60 secondes;
- remplacement de l'horloge hôte par `perf_counter_ns()`, ancrage audio par compteur d'échantillons et analyse multi-impact.
- nettoyage du dépôt avant commit: tests regroupés dans `tests/`, runners dans `scripts/research/`, rapports historiques dans `docs/research/` et ancien agent dans `archive/legacy_agent/`;
- suppression des ponts Windows, firmwares texte, scripts de test matériel et diagnostics ponctuels remplacés par EMG1;
- ajout de `.gitattributes`, `pytest.ini`, `requirements/dev.txt` et renforcement de `.gitignore` pour les données, modèles, mémoires, caches et environnements locaux.

## Vérifications de cette session

- cohérence des actions Codex, Anthony et Claude contrôlée entre `PILOTAGE.md`, ce handoff et le protocole de collaboration;
- `git diff --check` ciblé sur les documents modifiés: réussi.
- `python -m pytest -q`: 81 tests réussis, 2 ignorés après réorganisation;
- compilation Python ciblée: réussie;
- enregistrement synthétique, rapport qualité et replay déterministe: réussis;
- smoke test CLI de bout en bout (`demo-record`, `quality --allow-short`, `replay`): réussi;
- compilation Arduino Mega patch 2: réussie, 9 702 octets de programme et 661 octets de RAM globale;
- BRIO 100 DirectSound 44,1 kHz: ouverture de flux réussie;
- smoke test réel de `AudioCapture`: enregistrement temporaire réussi avec sélection DirectSound;
- horloge `perf_counter`: `QueryPerformanceCounter`, résolution annoncée 100 ns;
- flux audio réel corrigé: timestamps d'origine ADC espacés exactement de 50 ms par compteur d'échantillons;
- synchronisation physique corrigée: maximum absolu `12,69 ms`, cible de 20 ms réussie;
- firmware patch 2 compilé: 9 702 octets de programme, 661 octets de RAM globale;
- rapport mécanique v0.1 produit dans `reports/mechanics.json`: critère provisoire échoué;
- aucun mouvement servo ni nouvelle capture complète n'a été déclenché par Codex pendant la correction.

## Prompt de reprise recommandé

```text
Continue le projet Emergence. Lis PILOTAGE.md et SESSION_HANDOFF.md, puis exécute
la prochaine action Codex jusqu'au prochain besoin réel d'intervention matérielle
ou de validation d'achat. Mets à jour les documents de reprise avant de terminer.
```

## Risques connus

- ancien prototype cognitif conservé sous `archive/legacy_agent/`, explicitement hors chemin actif;
- AS5600 de vérité terrain d'angle pas encore acheté ni monté;
- banc v0.1 mécaniquement fragile et instable; aucun nouvel essai moteur autorisé;
- banc v1.0 encore en conception/impression;
- firmware passif patch 2 compilé mais pas encore flashé;
- encodeurs vision/audio placeholders dans la boucle historique;
- capacité du microphone BRIO 100 à préserver l'identité vocale encore non mesurée; comparaison prévue avec le Trust GXT 232;
- usure et jeu mécanique possibles du MF90.

## Processus en cours

Aucun calcul ou serveur nécessaire à cette transition n'est en cours.

## Addendum 2026-07-15 - Branche simulation 3D (session Claude Code avec Anthony)

Pendant que la modélisation du banc v1.0 reste en cours côté Anthony, une piste parallèle de simulation a été livrée (voir D-006):

- `sim3d/` est un backend MuJoCo au contrat strictement identique à `sim2d` (mêmes mondes par graine, mêmes bruits, même schéma CSV);
- `python -m scripts.research.simulate3d --render` ouvre un viewer 3D interactif; `learning/rollout_lnn.py` accepte `--backend sim3d`;
- validation: `dagger_002` entraîné en 2D fait `1,20%` de ticks de collision en 3D nominal contre `1,21%` re-mesuré en 2D; détails dans `docs/research/SIMULATION.md`, section sim3d;
- dépendance ajoutée: `requirements/research.txt` (mujoco); les tests `tests/test_sim3d.py` se désactivent sans MuJoCo;
- constat annexe: `env_windows` ne contient pas pytest sur la machine actuelle alors que le README documente `env_windows ... -m pytest`; la suite complète (91 tests) passe dans `.venv`.

Ceci ne modifie ni J0, ni le firmware, ni le chemin critique développemental.

Sonde d'exploration active terminée le 2026-07-17 (20 min): **H-A1 et H-A2 REJETÉES** - le learning progress régional minimal ne bat pas le babbling uniforme sur le jumeau (ratio k=3 `0.747` contre `0.732`, MAE angle `22.8°` contre `20.8°`), l'environnement homogène ne lui donnant rien de différentiel à exploiter. Conséquence D-002: le module motivation par learning progress reste hors chemin critique. Deux enseignements consignés dans `docs/research/active_exploration_probe.md`: le test discriminant exigerait un environnement hétérogène (région bruitée inapprenable vs régions structurées), et les deux conditions montrent une dérive en U sur juge externe (buffer on-policy croissant) à corriger dans toute future sonde itérative.

Suite conçue et implémentée le 2026-07-17 sous D-007, sans lancement de campagne longue:
`learning/developmental_curiosity.py` remplace les niveaux/bins annotés par un descripteur
continu état-action, une incertitude bootstrap, un progrès local, une habituation, une
pénalité d'imprévisibilité persistante et une frontière qui s'élargit avec la maîtrise.
La condition `developmental` est raccordée à `learning/active_exploration.py`; l'ancien
runner à deux conditions reste inchangé pour reproductibilité. Tests synthétiques ciblés
verts. Plan et limites dans `docs/research/developmental_curiosity_probe.md`. La branche
reste hors chemin critique tant qu'elle ne bat pas babbling et round-robin+habituation sur
un protocole pré-enregistré.

DC-001 a été pré-enregistré puis exécuté le 2026-07-17 (20 graines, 1 200 décisions, 41 s
CPU): **DC-H1 et DC-H3 rejetées, DC-H2 validée, garde-fou couverture validé**. La curiosité
continue évite nettement le bruit (`4.66%` contre `22.74%` pour babbling) mais apprend mal
le domaine structuré (`0.253` contre `0.113`) et retourne parfois vers le familier; 11/20
graines seulement suivent la séquence attendue. Cause: l'ensemble bootstrap apprend que
l'erreur élevée est stable et la classe trop tôt comme irréductible, alors qu'une
intervention d'apprentissage supplémentaire pourrait encore la réduire. Aucune promotion;
une suite éventuelle est DC-002 avec ancres avant/après entraînement ou désaccord entre
modèles de conséquences, jamais une retouche post hoc des poids DC-001. Résultats dans
`data/processed/experiments/developmental_curiosity_001/summary.md`.

Décision D-008 (2026-07-20): Anthony suspend le chemin matériel jusqu'à obtention de
résultats simulés probants et prometteurs. Aucune action physique, achat ou flash n'est
attendu; la simulation devient le chemin actif.

DC-002 (ancres fixes avant/après) est rejeté: H2 et couverture passent, mais erreur
structurée `0.172` contre `0.113` pour babbling, seulement 7/20 signatures et forte
variance. DC-003 corrige ensuite par gain fractionnel absolu, pression de couverture et
vingt mondes cachés randomisés. Résultat prometteur: erreur `0.1067` contre `0.1298`
babbling et `0.1199` round-robin, gains appariés sur 20/20 mondes face aux deux, bruit
`4.90%`, progression 19/20, couverture et stabilité validées. DC3-H1 reste formellement
rejetée car les intervalles min-max bruts de mondes hétérogènes se chevauchent; aucune
réplication lancée conformément au protocole. Prochaine étape: revue statistique et nouveau
pré-enregistrement apparié, sans retuning de DC-003.

Campagne v3 terminée le 2026-07-17 (252 min, protocole horizon conditionné arbitré par Anthony): **H1-v3 VALIDÉE** - sur les paires en mouvement, la variante conditionnée par la commande servo bat le contrôle sans action avec intervalles disjoints sur 3 graines à tous les horizons (0.1/0.3/0.5 s), avantage maximal à 0.3 s; effet représentationnel répliqué (MAE angle 11.7° contre 24.9°). Critère secondaire de monotonie non satisfait (pic à 0.3 s, interprétation mécanique consignée). H2/H3 toujours rejetées. Première hypothèse pré-enregistrée validée de la branche; détails dans `docs/research/visual_bench_probe.md`, résultats dans `data/processed/experiments/visual_night_003/`. Suites candidates consignées (H2, exploration active, réplication sur banc réel), aucune lancée sans arbitrage.

Campagne v2 terminée le 2026-07-17 (246 min, v2 après amendement documenté): H1 globale rejetée; H1-mouvement favorable en moyenne (`0.907` contre `0.932`) mais non validée au critère strict (léger chevauchement à n=3); résultat exploratoire net: l'action motrice améliore fortement la lisibilité de la pose dans le latent (MAE angle `14.6°` avec action contre `23.0°` sans, intervalles disjoints); H2 et H3 rejetées. Détails et suites candidates dans `docs/research/visual_bench_probe.md`. Aucune nouvelle expérience lancée sans arbitrage d'Anthony.

Protocole d'origine: sonde pré-enregistrée de contingence sensorimotrice visuelle sur le jumeau du banc - `docs/research/visual_bench_probe.md` (H1: l'action motrice améliore la prédiction latente; H2: pose lisible; H3: distance lisible), corpus babbling 120 pièces x 90 s via `sim3d/bench_corpus.py`, 2 variantes x 3 graines de `learning/train_visual_jepa.py`, orchestré par `scripts/research/run_visual_night.py` (résumable, keep-awake). Résultats attendus dans `data/processed/experiments/visual_night_001/summary.md`. Conforme D-002: branche recherche, aucune promotion sans battre les baselines pré-enregistrées.

Phase C livrée le 2026-07-16: campagnes d'épisodes multi-processus (`sim3d/parallel.py`, `scripts/research/rollout_parallel.py`). Résultats identiques bit à bit au série sur mêmes graines et même device (testé); 48 x 6000 pas en 6,6 s murales avec 12 workers (~44 000 pas/s, ~870x temps réel). Avertissement de reproductibilité consigné: le device d'inférence LNN fait partie du protocole (dagger_002 nominal: 361 ticks en CUDA contre 416 en CPU). Le vec-env pas-à-pas RL est volontairement différé vers MJX/WSL.

Phase B livrée le 2026-07-16: jumeau numérique de la tête du banc v1.0 (`sim3d/bench_model.py`, `sim3d/bench_env.py`, `sim3d/bench_mechanics.py`, `scripts/research/bench_head_sim.py`):

- géométrie de `BENCH_DESIGN.md` (caméra sur l'axe à z=100, HC-SR04 à z=130, AS5600, tête ~250 g), servo MG90S 10-170° à ~600°/s, dans une pièce meublée re-tirée par graine;
- qualification J0 (90-80-100-90) notée par le même code que `j0.mechanics`: ratios `[1.00, 0.99, 0.99]` en corps rigide = plancher idéal du design v1.0 (v0.1 réel: 5.22-13.45); outil comparatif, pas critère de réception;
- corpus visuel caméra + index CSV pour un futur JEPA visuel (`bench_head_sim corpus`);
- constat transférable au banc réel: la plage gyro MPU par défaut ±250 dps sature pendant les panoramiques ~600°/s; prévoir ±1000 dps dans le firmware ou limiter la vitesse de consigne (la qualification J0 à pas de ±10-20° n'est pas affectée);
- suite de tests: 98 verts dans `.venv` (`tests/test_bench_sim.py` inclus, skip propre sans MuJoCo).

## Addendum 2026-07-20 - DC-003R et DC-004 (session Claude Code avec Anthony)

Après la revue contradictoire de DC-003 (`docs/research/dc003_statistical_review.md`),
la session a exécuté les deux campagnes qu'elle prescrivait, chacune gelée par
pré-enregistrement avant implémentation:

- **DC-003R VALIDÉE INTÉGRALEMENT** (`dc003r_preregistration.md`, graines vierges
  6301..6320): R-H1 20/20 face aux deux baselines (permutation exacte p `9.5e-07`,
  Holm, IC BCa positifs), non-infériorité face à regional_lp dans la marge gelée,
  bruit `4.97%`, signatures `20/20`, couverture et stabilité passées. Nouveau module
  `learning/paired_stats.py` (permutation exacte par signes, BCa, Holm,
  non-infériorité, Monte-Carlo) testé sur cas de référence; runner
  `scripts/research/run_fractional_replication.py`.
- **DC-004 REJETÉE** (`dc004_preregistration.md`, 40 mondes 7301..7340, 20 permutés,
  ancres bruitées): à σ=0.05 l'ordonnanceur fractionnel s'effondre (erreur `0.386`
  contre `0.121` babbling, 0/40 signes); biais du clip confirmé (gain fantôme croissant
  avec σ); géométrie permutée seule indolore (0.1065 à σ=0); contrôle informationnel
  `regional_lp_gain` quasi immunisé (`0.1105`). Banc durci dans
  `learning/hardened_curiosity_benchmark.py` + `scripts/research/run_hardened_curiosity.py`.
- Suite de tests: 155 verts. Artefacts sous
  `data/processed/experiments/developmental_curiosity_003R/` et `_004/`.

Lecture d'ensemble, conforme à la prédiction de la revue: la **mesure interventionnelle
avant/après est validée** (regional_lp_gain l'exploite robustement), l'**ordonnanceur à
gain fractionnel ne survit pas au bruit d'évaluation** — le clip `max(gain, 0)` et le
gain instantané non moyenné sont les suspects gelés. La décision pré-enregistrée
interdit la simulation visuelle tant qu'un ordonnanceur n'a pas passé des ancres
bruitées.

Action Codex: conduire la revue de conception de l'ordonnanceur (clip, normalisation,
moyennage fenêtré du gain), proposer une variante et son pré-enregistrement sur graines
vierges; aucune campagne avant gel.
Action Anthony: aucune action matérielle (D-008); arbitrer si la revue de conception
propose plusieurs pistes.
Action Claude: revue contradictoire du prochain pré-enregistrement avant exécution.
Blocage: aucun blocage technique; blocage de protocole sur la simulation visuelle tant
que la robustesse au bruit d'ancre n'est pas démontrée.

## Addendum 2026-07-20 (suite) - DC-005 et arrêt de la famille fractionnelle

Après le rejet DC-004, la même session a conduit la revue de conception
(`docs/research/dc005_design_review.md`: le clip par observation transforme le bruit en
signal fantôme; le dénominateur bruité l'amplifie en zone base) et la campagne DC-005
pré-enregistrée (`dc005_preregistration.md`, graines vierges 8301..8340):

- variante `PooledFractionalCuriosity` (`learning/pooled_curiosity.py`): gains signés,
  agrégation régionale, clip après moyennage — seule modification face au gel DC-003;
- **D5-H3 validée** (aucune régression à σ=0), biais fantôme éliminé au niveau unitaire,
  effondrement du témoin `fractional` reproduit (contrôle positif);
- **D5-H1 et D5-H2 rejetées**: à σ=0.05, pooled (`0.1415`) reste derrière babbling
  (`0.1151`) et loin de `regional_lp_gain` (`0.1088`, marge `0.0054`);
- **décision pré-enregistrée exécutée: arrêt de la famille développementale à gain
  fractionnel; `regional_lp_gain` devient l'ordonnanceur de référence.**
- Suite de tests: 160 verts. Artefacts: `developmental_curiosity_005/`.

Bilan de la branche sur cinq campagnes (DC-001..005): la mesure interventionnelle
avant/après est l'acquis scientifique durable; aucun ordonnanceur développemental
continu n'a battu un mécanisme fenêtré simple recevant la même information, dans un
protocole équitable et durci. Toute reprise de la famille exigera une hypothèse
nouvelle pré-enregistrée, pas un réglage.

Action Codex: préparer, selon l'arbitrage d'Anthony, le pré-enregistrement suivant —
(a) promotion de `regional_lp_gain` comme ordonnanceur de la future simulation visuelle,
ou (b) cadrage d'une hypothèse nouvelle; aucune campagne avant gel et revue.
Action Anthony: arbitrer entre (a) et (b) (voir PILOTAGE.md, tableau de situation).
Action Claude: revue contradictoire du pré-enregistrement retenu avant exécution.
Blocage: arbitrage humain requis sur la direction; aucun blocage technique.
