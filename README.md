# Projet Emergence

Emergence explore une architecture développementale pour un organisme artificiel incarné.
Depuis D-008, le chemin actif exige d'abord des comportements probants et répliqués en
simulation avant toute reprise du banc physique.

## Reprise Du Projet

Commencer par [PILOTAGE.md](PILOTAGE.md), puis lire [SESSION_HANDOFF.md](SESSION_HANDOFF.md). Les demandes matérielles adressées à Anthony sont centralisées dans [ANTHONY_INBOX.md](ANTHONY_INBOX.md).

La vision technique est définie dans [DEVELOPMENTAL_ARCHITECTURE.md](DEVELOPMENTAL_ARCHITECTURE.md). Les décisions et responsabilités sont consignées dans [DECISIONS.md](DECISIONS.md) et [COLLABORATION_PROTOCOL.md](COLLABORATION_PROTOCOL.md).

## Jalon Actif

**D-059 — Résultats vécus et choix d'expériences persistants.** RESILIENCE-002
est terminé : 358 tests, 18 reprises exactes sur six vies dev et douze nouvelles
vies de validation. L'avantage actif du développement ne se reproduit pas :
−15,20 % d'utilité contre cycle fixe en validation. L'heuristique active et le
moniteur global ne sont pas promus ; les acquis de persistance sont conservés.
Le but reste un noyau résilient qui apprend de nouvelles situations.
[Bilan et graphique](docs/research/resilience_002_results.md) ·
[Avancées et échecs](docs/research/resilience_002_log.md).
Les jalons suivants sont historiques.

**D-057 — Première récupération résiliente, avec une limite explicite.** Le service
neuronal est intégré à la mémoire du noyau. Après six vies de développement,
12 nouvelles vies valident la recette v3 : changements détectés dès le premier essai,
reprises exactes, utilité après rupture +4,24 % contre le meilleur témoin simple.
**345 tests verts**. Un corps reste à 50 % de réussite malgré sa bonne prédiction :
la clôture du besoin d'apprentissage doit désormais dépendre du fonctionnement réel.
Le cadrage D-056 reste prioritaire : noyau résilient, apprentissage intrinsèque et
futur développement incarné avec un humain ; la précision motrice est secondaire.
[Bilan, graphique et limites](docs/research/resilience_001_results.md) ·
[Journal des avancées et échecs](docs/research/resilience_001_log.md).
Les jalons suivants sont l'historique conservé.

**D-055 — CUMULATIVE-001 livré le 9 septembre 2026.** Après six vies de développement,
12 nouvelles vies A→B→A→C valident un réseau à rejeu sur RTX 5080 : erreur finale
0,079515°, −53,19 % contre réseau naïf et −77,92 % contre ridge cumulative.
Son choix d'orientation réussit 190/192 situations, avec utilité +23,36 % contre
le meilleur témoin simple. Reprises interprocessus exactes ; **336 tests verts**.
Le premier contrôleur n'améliorait pas les trajectoires : cet échec est conservé.
Poids expérimentaux persistants, intégration neuronale au noyau encore à faire.
Voir le [bilan, le graphique et les limites](docs/research/cumulative_001_results.md)
et le [journal des avancées et échecs](docs/research/cumulative_001_log.md).
Les paragraphes suivants retracent les acquis et décisions antérieurs.

La voie active est KERNEL/LIFE en simulation. KERNEL-001 fournit la mémoire persistante
entre événements, croyances, modèles, compétences et expériences. LIFE-001 valide la
régression, le choix sûr et la récupération; LIFE-002 calcule maintenant les signaux de
choix depuis des observations MuJoCo/J0 et en persiste les preuves reproductibles.
LIFE-003 relie chaque proposition à une exécution et à un résultat J0, puis reconstruit
automatiquement les histoires après redémarrage. LIFE-004 ferme la boucle avec un
exécuteur exclusivement MuJoCo, limité à des primitives symboliques bornées. LIFE-005
fait maintenant dépendre acquisition, régression et récupération de compétence des
résultats J0 vérifiés. LIFE-006 dérive les candidates des besoins inconnus ou régressés
et remplace automatiquement les priors froids par les signaux observés disponibles.
LIFE-007 supervise et reprend le cycle complet aux frontières transactionnelles sûres.
LIFE-008 qualifie 64 cycles avec reprises, refus de sécurité et idempotence globale.

REF-001 est close sans promotion: une concaténation de commande absolue au latent global
n'explique pas mieux le mouvement propre et n'établit pas la réafférence. REF-002 est
close comme non-résultat technique après la découverte d'une manipulation externe
parfois hors champ; ses 12 triplets complets ne seront pas analysés. La revue pré-calcul
REF-003 a autorisé l'implémentation après huit corrections bloquantes, mais la campagne
s'est arrêtée sur deux paires externes photométriquement trop faibles pendant 14303.
REF-003 est également close sans résultat ni analyse partielle.

Le pré-enregistrement LIFE-009 propose une première politique adaptative reliant
expériences et progrès réel d'un modèle sensorimoteur. Claude Opus 5 l'a autorisé avec
sept corrections bloquantes, intégrées sous D-036. Le smoke 17991 a ensuite fermé
LIFE-009 sous D-037: l'oracle ne gagne que 2,383 % sur la baseline principale, sous les
10 % exigés. Aucune banque réservée n'a été ouverte. La prochaine tentative devra être
LIFE-010, avec une tâche plastique et une marge démontrée avant campagne. Son
pré-enregistrement est prêt sous D-038 et attend la revue Claude Opus 5 avant tout code
ou calcul. Claude l'a autorisé avec B1–B7, intégrées sous D-039; l'implémentation et les
six smokes ont été autorisés. Le début de 18191 a toutefois fermé LIFE-010 sous D-040:
`probe_step_hold` devient inéligible avec un risque observationnel `0,75 > 0,50`.
Aucune métrique scientifique ou banque réservée n'a été ouverte.

La revue LIFE-011 a imposé des plans v3 à excitation réalisée distincte et une plaque de
marge avant professeur. Les 18 préflights sont verts, mais D-043 ferme LIFE-011:
l'oracle atteint 16,8853 % en médiane face à greedy, tandis que son minimum settling
reste `4,4039 % < 5 %`. Aucun professeur ni banque réservée n'a été ouvert.

LIFE-012 est pré-enregistrée sous D-044 sans relâcher ce seuil. Ses plans à coût 240°
créent de vrais plateaux d'établissement pour distinguer rampe, renversement et maintien.
Après intégration de la revue, sa plaque 18791..18796 ferme toutefois la famille sous
D-046: une graine refuse 24/24 mises à jour et l'oracle myope ne constitue pas une borne
séquentielle. Aucun professeur ni banque réservée n'a été ouvert.

BODY-SCHEMA-001 est revenu au jalon J1 avant toute reprise de J5. Son smoke apprend bien
la conséquence immédiate du cou et corrige le verrou 18793, mais échoue sur la couverture
conditionnelle et la détection de faute face au mouvement trivial. D-049 le clôt sans
ouvrir 19201+.

BODY-SCHEMA-002 a maintenant livré une prévision corporelle persistante sous D-053.
La recette passe six organismes de développement puis six neufs de validation :
erreur moyenne **0,435° à un pas et 0,579° à 0,5 s**. Les modèles et leur prochaine
mise à jour se restaurent à l'identique ; six paquets F de développement sont activés
dans le registre du noyau. **327 tests verts**. Voir le
[rapport](docs/research/body_schema_002_results.md), le
[contrat révisé](docs/research/body_schema_002_preregistration.md) et le
[plan de persistance](docs/research/body_schema_002_persistence_plan.md).
La calibration et la détection restent non qualifiées, la confirmation et le futur
protocole cumulatif restent à préparer. Aucun J5 ni retour matériel autorisé.

Le matériel J0 est conservé mais suspendu:

J0 valide le protocole EMG1, l'enregistrement multimodal, le replay, la synchronisation et la sécurité du servo :

- protocole et critères : [J0_PROTOCOL.md](J0_PROTOCOL.md) ;
- procédure physique : [J0_RUNBOOK.md](J0_RUNBOOK.md) ;
- conception du nouveau banc : [BENCH_DESIGN.md](BENCH_DESIGN.md).

Le montage v0.1 ne doit plus recevoir de commande moteur. Le firmware patch 2 compilé laisse le servo détaché au démarrage et en failsafe.

## Installation J0

```powershell
python -m venv env_windows
.\env_windows\Scripts\python.exe -m pip install -r requirements\dev.txt
```

Vérifications sans matériel :

```powershell
.\env_windows\Scripts\python.exe -m pytest -q
python -m j0.cli demo-record --duration 2 --output data/j0-demo
.\env_windows\Scripts\python.exe -m j0.cli devices
```

La capture physique passe uniquement par `windows_client/j0_capture.py` et les commandes documentées dans le runbook.

## Arborescence

- `j0/` : acquisition, protocole, recorder, replay et rapports J0 ;
- `cognitive/` : croyances, mémoire épisodique, compétences, propositions sûres et reprise ;
- `peripheral/brain_stem/` : firmware Arduino Mega EMG1 unique ;
- `windows_client/` : flash et point d'entrée de capture Windows ;
- `tests/` : suite de tests active ;
- `requirements/` : dépendances par sous-système ;
- `common/`, `sim2d/`, `sim3d/`, `learning/` : branche de recherche reproductible (`sim3d` = backend MuJoCo, même contrat que `sim2d`) ;
- `scripts/research/` : runners des expériences historiques ;
- `docs/research/` : résultats JEPA/LNN et simulation ayant motivé D-002 ;
- `archive/legacy_agent/` : ancien prototype cognitif, conservé hors chemin actif.

Les répertoires `data/`, `models/`, les mémoires, médias générés et environnements Python restent locaux et sont exclus par `.gitignore`.
