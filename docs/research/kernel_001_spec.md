# Spécification KERNEL-001 — noyau cognitif persistant minimal

Date: 2026-07-26. Infrastructure logicielle sous D-004 et D-008; aucune revendication
scientifique et aucun contrôle matériel direct.

Statut: implémenté et vérifié sous D-018. Cette spécification reste le contrat gelé de
la première tranche; le bilan d'implémentation est dans `kernel_001_implementation.md`.

## Objectif

Relier les flux J0 et les futurs modèles dans une boucle persistante qui sait:

1. maintenir un état de croyance versionné avec incertitude, fraîcheur et provenance;
2. délimiter causalement des épisodes à partir des événements déjà observés;
3. mémoriser uniquement des références vers les données brutes immuables;
4. suivre l'état et l'historique des compétences;
5. proposer une expérience sûre sans jamais envoyer elle-même une commande moteur;
6. reprendre le même état après arrêt ou crash.

KERNEL-001 reste utile avec des modèles simples. JEPA, LNN, encodeurs sensoriels et LLM
sont des producteurs ou consommateurs remplaçables, jamais des dépendances du noyau.

## Invariants

- Toute horloge est en nanosecondes, porte un domaine comparable explicite et tout état
  dérivé conserve sa provenance.
- Un événement hors ordre peut être archivé, mais ne remplace jamais silencieusement
  une croyance plus récente.
- Un changement de domaine d'horloge, notamment après reboot, exige une autorisation
  explicite du coordinateur de session.
- Une frontière d'épisode dépend seulement du présent et du passé.
- Les données vidéo/audio restent dans les sessions J0; SQLite stocke références,
  digests, métadonnées et résumés.
- Une compétence ne devient jamais `validated` sans passer par `candidate`.
- Une proposition d'expérience n'est pas une commande. Le tronc cérébral et la couche
  de sécurité restent souverains.
- Arrêt d'urgence, matériel malsain, mise à jour de modèle ou quota bloquant interdisent
  toute proposition motrice.
- Les écritures multi-tables sont transactionnelles; SQLite utilise clés étrangères,
  journal WAL et contrôle d'intégrité.
- Les snapshots sont JSON canoniques et versionnés. Une version de schéma inconnue
  arrête la reprise au lieu d'être interprétée approximativement.

## Composants

### BeliefState

Une croyance numérique contient `mean`, `variance`, timestamp observé/reçu, source,
qualité, calibration et version de modèle. Le registre expose fraîcheur, contraintes
de variance/qualité et snapshots déterministes. La fusion gaussienne n'est disponible
que par appel explicite supposant l'indépendance des sources.

### EpisodicMemory

SQLite conserve sessions, épisodes, références d'événements, transitions de
compétence, versions de modèles, propositions d'expériences et snapshots du noyau.
Les épisodes ouverts sont récupérables après redémarrage.

### CausalBoundaryPolicy

Une frontière est créée par:

- première observation;
- événement explicite configuré;
- silence supérieur au seuil;
- durée maximale d'épisode;
- fin de session.

Les événements tardifs restent référencés avec un indicateur `out_of_order`, sans
réécrire les frontières historiques.

### CompetenceRegistry

États: `unknown`, `learning`, `candidate`, `validated`, `regressed`, `suspended`.
Chaque transition possède timestamp, preuve structurée, version de modèle et digest de
validation. Les transitions impossibles sont rejetées.

### SafeExperimentCatalog

Le catalogue déclare primitives autorisées, croyances requises, limites de risque,
coût, cadence et quota par session. Le sélecteur produit une proposition transparente
à partir de gains fournis par les modules scientifiques. Il ne calcule pas lui-même
une curiosité et ne commande aucun actionneur.

### CognitiveKernel

L'orchestrateur relie les composants, reçoit les événements J0, persiste chaque
snapshot important et fournit des propositions. Il ne contient ni modèle appris, ni
thread matériel, ni LLM.

## Critères de réception

- reprise bit-identique des croyances après réouverture de la base;
- reprise d'une session et d'un épisode laissés ouverts par un crash;
- rejet démontré des mises à jour de croyance hors ordre;
- segmentation déterministe sur silence, durée et événements explicites;
- zéro blob sensoriel dans SQLite;
- historique complet et transitions de compétence contrôlées;
- aucune proposition si une garde de sécurité échoue;
- cadence et quota d'expérience persistants après redémarrage;
- migrations refusées sur version de schéma inconnue;
- suite existante sans régression.

## Hors portée

- apprendre automatiquement les poids du score d'expérience;
- décider de la vérité d'une interprétation sémantique;
- exécuter une primitive motrice;
- compresser ou supprimer les données brutes;
- attribuer une émotion, une identité ou une intention;
- remplacer la revue et la promotion des checkpoints.
