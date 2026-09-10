# Projet Emergence

Emergence explore une architecture développementale pour un organisme artificiel incarné.
Depuis D-008, le chemin actif exige d'abord des comportements probants et répliqués en
simulation avant toute reprise du banc physique.

## Reprise Du Projet

Commencer par [PILOTAGE.md](PILOTAGE.md), puis lire [SESSION_HANDOFF.md](SESSION_HANDOFF.md). Les demandes matérielles adressées à Anthony sont centralisées dans [ANTHONY_INBOX.md](ANTHONY_INBOX.md).

La vision technique est définie dans [DEVELOPMENTAL_ARCHITECTURE.md](DEVELOPMENTAL_ARCHITECTURE.md). Les décisions et responsabilités sont consignées dans [DECISIONS.md](DECISIONS.md) et [COLLABORATION_PROTOCOL.md](COLLABORATION_PROTOCOL.md).

## Jalon Actif

**D-060 — Changement de substrat : la vision dans la boucle, cou à deux axes.** Décidé le
10 septembre 2026 sur la base de [PROPOSITION_SUBSTRAT.md](PROPOSITION_SUBSTRAT.md). Le
banc à un axe observé par cinq scalaires n'est plus le substrat des travaux cognitifs :
neuf campagnes y ont montré le même motif, où la régression réussit toujours et où la
connaissance de soi et la qualité des choix échouent toujours. L'observation devient image
plus proprioception ; une articulation d'inclinaison est ajoutée au jumeau MuJoCo. Trois
capacités enchaînées : retrouver un objet par son apparence, localiser un changement sous
budget de mouvements, conserver la première en apprenant la seconde. Une sonde de marge
sur le banc précède toute conception de mécanisme, et son échec suffirait à déclarer ce
substrat épuisé à son tour. Le jalon suivant est l'historique conservé.

## État Et Historique

L'état courant — décision active, règles permanentes, acquis avec leurs limites, campagnes
closes avec leur cause — est dans [PILOTAGE.md](PILOTAGE.md). L'historique campagne par
campagne, avec les verdicts et ce qui reste interdit, est dans
[SESSION_HANDOFF.md](SESSION_HANDOFF.md). Ce README ne les recopie pas.

En deux phrases : neuf campagnes de LIFE-009 à RESILIENCE-002 ont montré le même motif sur
le banc à un axe — la régression réussit toujours, la connaissance de soi et la qualité des
choix échouent toujours. D-060 en conclut que le banc était le problème et ouvre le
substrat visuel à deux axes.

## Rapports De Campagne

| Campagne | Résultat | Journal |
|---|---|---|
| BODY-SCHEMA-002 | [rapport](docs/research/body_schema_002_results.md) · [contrat](docs/research/body_schema_002_preregistration.md) · [plan de persistance](docs/research/body_schema_002_persistence_plan.md) | [développement](docs/research/body_schema_002_development_log.md) |
| CUMULATIVE-001 | [rapport](docs/research/cumulative_001_results.md) | [avancées et échecs](docs/research/cumulative_001_log.md) |
| RESILIENCE-001 | [rapport](docs/research/resilience_001_results.md) | [avancées et échecs](docs/research/resilience_001_log.md) |
| RESILIENCE-002 | [rapport](docs/research/resilience_002_results.md) | [avancées et échecs](docs/research/resilience_002_log.md) |
| REF-001 à REF-003 | [résultats REF-001](docs/research/reafference_001_results.md) · arrêts techniques [REF-002](docs/research/reafference_002_technical_stop.md) et [REF-003](docs/research/reafference_003_technical_stop.md) | — |
| J6-AR001 | [arrêt technique](docs/research/j6_adaptive_replay_001_technical_stop.md) | — |

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
