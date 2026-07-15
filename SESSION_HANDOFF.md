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

Ceci ne modifie ni J0, ni le firmware, ni le chemin critique développemental. Phases suivantes proposées (non lancées): B - jumeau numérique de la tête v1.0 avec rendu caméra; C - vectorisation massive.
