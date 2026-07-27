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
- `experiments.py`: catalogue déclaratif, proposition nominale et sélection
  transparente entre candidates sous gardes de sécurité, risque, coût, croyances
  requises, cadence et quota;
- `competence.py`: évaluation générique à hystérésis, preuves et digests pour les
  métriques dont une borne supérieure définit validation et régression;
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
- smoke LIFE-001 de récupération: validation, régression injectée, choix audité d'une
  recalibration, redémarrage et revalidation sur six graines hors REF.
- smoke LIFE-002: quatre sessions MuJoCo/J0, signaux dérivés des observations, preuves
  de toutes les candidates persistées et recalcul strictement identique après restart.
- smoke LIFE-003: attribution proposition→exécution→résultat, reprise d'une exécution,
  reconstruction des histoires depuis J0 et migration mémoire v1→v2.
- smoke LIFE-004: registre de primitives bornées, exécution MuJoCo automatique d'un
  choix observationnel, garde fraîche et abandon atomique sur panne.
- smoke LIFE-005: évaluation depuis résultats exécutés, acquisition, régression,
  redémarrage, récupération et replay d'assessment idempotent.
- smoke LIFE-006: activation des candidates depuis les compétences persistantes,
  prior froid explicite, remplacement par historique observé et préemption de régression.
- smoke LIFE-007: journal de cycle v4, sélection atomique, reprises après sélection,
  exécution et évaluation, abandon sûr d'un état MuJoCo perdu.
- campagne LIFE-008: 64 cycles, matrice de cinq régimes, idempotence globale, quotas,
  intégrité et croissance disque qualifiés.

Les 61 tests KERNEL/LIFE et les 282 tests complets du dépôt passent avec
l'environnement `.venv`.

## Limites assumées

- Les croyances KERNEL-001 sont scalaires; une carte ou distribution structurée devra
  être référencée comme artefact versionné plutôt que sérialisée en blob SQLite.
- La segmentation est temporelle et événementielle, pas encore apprise.
- Le score d'expérience est une combinaison transparente de signaux observationnels,
  pas une politique intrinsèque validée.
- LIFE-002 couvre la télémétrie servo; d'autres modalités demanderont leurs propres
  estimateurs mesurables et testés.
- La base n'est pas encore soumise à charge longue ni à injection de panne au niveau
  processus/fichier.

## Suite recommandée

LIFE-009 a raccordé une compétence et un sélecteur appris, puis s'est arrêtée au smoke
sous D-037: la marge oracle de `2,383 %` reste sous la porte `10 %`. Aucune banque
réservée n'a été ouverte. LIFE-010 est pré-enregistrée sous D-038 avec une compétence
résiduelle protégée et trois plans équicûteux; elle attend une nouvelle revue pré-calcul
avant toute implémentation.

Les smokes LIFE certifient le câblage persistant, la régression/récupération et le choix
à partir d'observations. Ils ne démontrent ni apprentissage d'une nouvelle compétence,
ni diagnostic causal autonome, ni curriculum appris.

REF-003 est close comme non-résultat technique. Toute REF-004 exigerait un protocole,
un monde, des graines et une revue pré-calcul neufs.
