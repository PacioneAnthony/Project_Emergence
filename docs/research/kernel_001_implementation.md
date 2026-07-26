# KERNEL-001 — bilan d'implémentation

Date: 2026-07-26. Statut: tranche minimale implémentée, sans contrôle matériel et sans
revendication scientifique.

## Résultat

KERNEL-001 ajoute le paquet `cognitive/`, indépendant des modèles appris:

- `beliefs.py`: estimations scalaires avec variance, fraîcheur, qualité, calibration,
  version de modèle, provenance et domaine d'horloge; rejet déterministe des mises à
  jour hors ordre ou inter-domaines non autorisées;
- `memory.py`: base SQLite en WAL, clés étrangères, contrôle de version, sessions,
  épisodes, références d'événements, compétences, versions de modèles, propositions et
  snapshots;
- `boundaries.py`: frontières causales en ligne sur première observation, silence,
  durée maximale et événements explicites;
- `experiments.py`: catalogue déclaratif et sélection transparente sous gardes de
  sécurité, risque, coût, croyances requises, cadence et quota;
- `kernel.py`: orchestration, ingestion d'événements J0, replay idempotent, reprise
  après crash et fermeture atomique.

Le noyau ne contient ni réseau appris, ni LLM, ni thread matériel, ni méthode
d'actionnement. `ExperimentProposal` expose une primitive symbolique et une justification,
mais aucune vitesse, position ou consigne de servo.

## Persistance et causalité

Les payloads bruts restent dans `events.jsonl` et les blobs J0. SQLite conserve:

- la référence exacte, par exemple `events.jsonl#L42`;
- le SHA-256 canonique de l'événement;
- ses horodatages, identité et métadonnées de qualité;
- l'épisode causal et le marqueur `out_of_order`.

La rotation d'épisode, l'ajout de référence et le checkpoint du noyau forment une seule
transaction. Le début et la fin de session sont également atomiques avec leur snapshot.
Un replay répété ne duplique pas les événements; une identité réutilisée avec un digest
différent est refusée.

Les horodatages monotones de deux démarrages de l'OS ne sont pas supposés comparables.
Une croyance ne traverse un changement de domaine d'horloge que sur autorisation
explicite du coordinateur; le nouveau domaine est conservé dans son snapshot.

## États de compétence

Le graphe autorisé est:

`unknown → learning → candidate → validated → regressed → learning`

Chaque état peut être suspendu selon les transitions déclarées. Une validation directe
est impossible et `validated` exige un digest de preuve. L'historique est append-only.
La promotion d'un modèle exige l'état `candidate` et ne laisse qu'une version validée
par module.

## Gardes d'expérience

Une proposition motrice est impossible si l'une des conditions suivantes est vraie:

- arrêt d'urgence;
- matériel déclaré malsain;
- mise à jour de modèle en cours;
- quota de stockage bloquant;
- primitive non autorisée;
- croyance requise absente, périmée, trop incertaine ou de qualité insuffisante;
- risque ou coût prédit au-delà de la limite;
- cadence ou quota de session dépassé.

Les gains épistémiques et progrès d'apprentissage restent fournis par les modules
scientifiques. KERNEL-001 ne prétend pas définir une curiosité optimale.

## Vérification

`tests/test_cognitive_kernel.py` couvre notamment:

- snapshot bit-identique et version de schéma inconnue;
- rejet hors ordre et fusion gaussienne explicitement demandée;
- refus d'un changement implicite de domaine d'horloge après reboot;
- absence de colonne ou de contenu sensoriel brut dans SQLite;
- frontières silence/explicite et non-réécriture par événement tardif;
- transitions de compétence et promotions invalides;
- toutes les gardes de sécurité;
- cadence et quota persistants après redémarrage;
- crash avec session et épisode ouverts;
- replay J0 déterministe, idempotent et collision de digest;
- absence de champs de commande dans une proposition.
- smoke LIFE-001 réel sur MuJoCo: deux sessions J0, extinction/reprise, deux graines
  hors REF et validation auditée d'une primitive analytique bornée.

Les 22 tests KERNEL/LIFE et les 215 tests complets du dépôt passent avec
l'environnement `.venv`.

## Limites assumées

- Les croyances KERNEL-001 sont scalaires; une carte ou distribution structurée devra
  être référencée comme artefact versionné plutôt que sérialisée en blob SQLite.
- La segmentation est temporelle et événementielle, pas encore apprise.
- Le score d'expérience est une combinaison transparente de signaux externes, pas une
  politique intrinsèque validée.
- Aucun adaptateur ne convertit encore automatiquement les observations du simulateur
  en croyances; cette sémantique doit venir d'un module mesurable et testé.
- La base n'est pas encore soumise à charge longue ni à injection de panne au niveau
  processus/fichier.

## Suite recommandée

La prochaine tranche utile est LIFE-001: brancher KERNEL-001 à une boucle de simulation
continue, d'abord avec des estimateurs analytiques simples et des primitives symboliques.
Elle doit démontrer sur plusieurs sessions: acquisition d'une compétence, reprise après
arrêt, régression détectée, récupération et choix d'expérience sous contraintes.

Le premier smoke de câblage multi-session est désormais vert. Il certifie une primitive
analytique existante; il ne démontre ni apprentissage d'une nouvelle compétence, ni
régression/récupération, ni sélection autonome d'un curriculum.

REF-002 reste une voie scientifique séparée. Son code et ses calculs demeurent interdits
avant la revue pré-calcul de Claude Opus 5.
