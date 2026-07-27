# LIFE-008 — endurance multi-cycle et matrice de pannes

Date: 2026-07-27  
Statut: campagne complète et vérifiée, simulation uniquement

## But

Qualifier la boucle LIFE-007 sur une campagne assez longue pour détecter les erreurs de
reprise, duplications, fuites de cycles actifs et croissances anormales qui n'apparaissent
pas sur deux cycles.

Cette tranche ne change aucune politique. Elle répète le même système déterministe sous
interruptions contrôlées.

## Campagne

- identifiant: `life008-endurance-v1`;
- 64 cycles;
- graines 17801..17864;
- une session cognitive persistante;
- une primitive routée: `diagnose-servo`;
- critère LIFE-005 inchangé: métrique du plan complet, validation `≤9°`, régression
  `>15°`, fenêtre 2;
- aucun backend physique.

## Matrice périodique

Le cycle `i mod 5` utilise:

0. exécution directe;
1. arrêt après `selected`, fermeture brutale simulée, réouverture;
2. arrêt après `executed`, fermeture brutale simulée, réouverture;
3. arrêt après `assessment_applied`, fermeture brutale simulée, réouverture;
4. arrêt après `selected`, tentative avec `emergency_stop=true`, vérification que le
   cycle reste sélectionné, fermeture puis reprise sûre.

Les fermetures « brutales » appellent `close()` sans `end_session`; elles simulent la
perte du processus tout en laissant SQLite cohérente. LIFE-007 couvre séparément
l'abandon d'une exécution physique partielle.

## Runner

`run_endurance_campaign`:

- accepte un catalogue, un superviseur et une configuration gelée;
- utilise des identités de cycle/exécution/J0 dérivées de l'index;
- reprend une session ouverte ou retourne les cycles déjà complets;
- ne recrée jamais un cycle existant;
- ferme proprement la session seulement quand les 64 cycles sont terminés;
- écrit un rapport JSON canonique optionnel.

Relancer le runner avec le même identifiant, nombre de cycles et graines doit produire
zéro nouvelle proposition, exécution, session J0 ou assessment.

## Mesures et portes

Après la campagne:

- 64 cycles `complete`, zéro `selected/executed/aborted`;
- 64 propositions et 64 exécutions uniques;
- 64 sessions J0 complètes de 12 événements;
- 63 assessments LIFE-005: le premier cycle est `insufficient_history`;
- historique de compétence limité aux trois transitions initiales
  `learning,candidate,validated`;
- `PRAGMA integrity_check = ok`;
- zéro cycle actif et zéro exécution `running`;
- aucune identité dupliquée;
- aucun payload brut ou champ de cible dans SQLite;
- taille SQLite, WAL inclus, `< 4 MiB`;
- données J0 `< 4 MiB`;
- croissance moyenne combinée `< 128 KiB/cycle`;
- au moins une reprise de chaque frontière et un refus de sécurité temporaire;
- digest du rapport reproductible à contenu stable hors tailles physiques.

## Quota

Un test séparé utilise une politique de quota déjà saturée. LIFE-004 doit refuser avant
création de session J0; le cycle LIFE-007 reste `selected`. Avec une politique saine et
la même requête, il reprend et termine sans seconde proposition.

## Arrêt

Toute porte rouge arrête la campagne sans effacer la base ni les journaux. Le même
runner peut reprendre depuis les cycles complets et le cycle sélectionné restant. Il
n'existe ni remplacement de graine ni suppression automatique.

## Interprétation

Un succès qualifie l'endurance d'ingénierie de cette boucle déterministe. Il ne valide
toujours pas l'apprentissage autonome des besoins, seuils, plans ou priorités.

## Résultat

La campagne 17801..17864 termine:

- 64/64 cycles, propositions, exécutions et sessions J0 complètes;
- 63 assessments, le premier cycle étant `insufficient_history`;
- 51 redémarrages contrôlés et 12 refus temporaires d'arrêt d'urgence;
- zéro cycle actif, exécution running ou identité dupliquée;
- historique de compétence limité à `learning,candidate,validated`;
- `PRAGMA integrity_check=ok`;
- SQLite+WAL `1 609 856` octets et J0 `356 910` octets;
- croissance combinée moyenne `30 730,71875` octets/cycle;
- aucune clé de payload brut ou cible dans SQLite.

Toutes les portes sont vertes. Digest logique:
`3cab7044228bb20ec512f67e32d3de44cac7a292c51d03311c7b815d3ccf2616`.

Une seconde invocation saute les 64 cycles, produit zéro redémarrage/refus/effet,
conserve exactement les mêmes comptes et retrouve le même digest. Le rapport est
`data/processed/experiments/life_008_endurance/report.json`.

Les 57 tests KERNEL/LIFE ciblés et les 278 tests complets passent dans `.venv`.
LIFE-008 est close comme succès d'ingénierie sous D-034.
