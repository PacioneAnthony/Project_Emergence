# Projet Emergence

Emergence explore une architecture développementale pour un organisme artificiel incarné.
Depuis D-008, le chemin actif exige d'abord des comportements probants et répliqués en
simulation avant toute reprise du banc physique.

## Reprise Du Projet

Commencer par [PILOTAGE.md](PILOTAGE.md), puis lire [SESSION_HANDOFF.md](SESSION_HANDOFF.md). Les demandes matérielles adressées à Anthony sont centralisées dans [ANTHONY_INBOX.md](ANTHONY_INBOX.md).

La vision technique est définie dans [DEVELOPMENTAL_ARCHITECTURE.md](DEVELOPMENTAL_ARCHITECTURE.md). Les décisions et responsabilités sont consignées dans [DECISIONS.md](DECISIONS.md) et [COLLABORATION_PROTOCOL.md](COLLABORATION_PROTOCOL.md).

## Jalon Actif

Deux voies complémentaires sont actives en simulation:

- REF-002 teste, après revue contradictoire pré-calcul, si un transport sensorimoteur
  spatial explicite permet enfin de séparer changement auto-produit et externe;
- KERNEL-001 fournit la mémoire cognitive persistante qui manquait entre les événements,
  modèles, compétences et expériences. La première tranche est implémentée et testée;
  LIFE-001 devra maintenant la brancher à une boucle de vie simulée multi-session.

REF-001 est close sans promotion: une concaténation de commande absolue au latent global
n'explique pas mieux le mouvement propre et n'établit pas la réafférence. Aucun calcul
REF-002 n'est autorisé avant la revue de Claude Opus 5.

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
