# Revue ciblée — BODY-SCHEMA-002, contrat révisé et prévision persistante

Date : 2026-09-09. Destinataire : Claude.  
Statut : préparation documentaire terminée ; aucun code r2, calcul ni banque nouvelle.

## Décision unique

Peut-on autoriser le développement borné de la révision 2 pour livrer une prévision
corporelle causale et persistante, avec qualification séparée de F, E et A ?

La demande porte sur le développement et l'intégration au noyau. Elle ne demande
ni ouverture de la confirmation ni qualification anticipée de J1. La revue du futur
manifeste confirmatoire sera distincte et fondée sur le dispositif effectivement testé.

## Lecture prioritaire

1. `docs/research/body_schema_002_preregistration.md` — contrat r2 complet.
2. `docs/research/body_schema_002_persistence_plan.md` — interfaces et réception.
3. `DIAGNOSTIC_ET_PLAN_DE_DEBLOCAGE.md` — §3, §4 et étapes 0–1 du §7.
4. `DECISIONS.md` — D-049 à D-051.

Vérifications ciblées dans le code historique, sans exécuter de simulation :

- `learning/body_schema_001.py` : `execute_plan`, `ProtectedFullRidge`, `calibration` ;
- `learning/body_schema_001_campaign.py` : `_metrics`, `_smoke_gates` ;
- `cognitive/memory.py` : `register_model`, `promote_model`, `apply_competence_assessment` ;
- `cognitive/supervisor.py` : `PersistentDevelopmentSupervisor.advance`.

Pour la traçabilité seulement : `body_schema_002_proposal_20260727.md` conserve la v1
et `body_schema_001_technical_stop.md` décrit l'arrêt historique. Ces deux fichiers
sont dans `docs/research/`. L'ancien protocole v1 n'est pas à autoriser tel quel.
Ne lancer aucun calcul et n'ouvrir aucune banque réservée ni campagne close.

## Faits et changements à examiner

La moyenne ridge a progressé en développement BODY-SCHEMA-001. L'audit montre aussi
une métrique dupliquée, une dépendance postérieure au limiteur pour l'incertitude et
une porte d'absence de fuite écrite en dur. Les 300 tests verts rapportés par l'audit
ne vérifiaient pas ces propriétés. Aucun nouveau résultat n'est revendiqué ici.

La r2 propose une entrée causale dédiée, une calibration globale initiale, un contrôle
entraîné sans commandes, des déroulements libres et des statuts de capacité distincts.
Le candidat apprend indépendamment de l'actif ; sa promotion utilise une marge utile
et un contrôle de dérive cumulative, à fixer sur développement avant validation.

## Points contradictoires obligatoires

1. Le contrat couvre-t-il les fuites dans moyenne, sigma, décision, calibration et
   restauration, avec une séquence temporelle non ambiguë ?
2. Le comparateur sans action est-il équitable ? Examiner sa base polynomiale proposée
   à treize termes, son prior et ses bornes ; préciser les corrections nécessaires.
3. Le développement réutilisable, la validation à lecture unique et le futur gel
   confirmatoire empêchent-ils une qualification post hoc ? Les réserves historiques
   restent-elles clairement fermées ?
4. Les empreintes sans métadonnées et les diagnostics cinématiques vérifient-ils la
   diversité et la validité de mirrored, sans confondre un tick commun avec un trial ?
5. Le candidat indépendant et la promotion par fenêtre évitent-ils blocage complet,
   dérive cumulative et confusion entre sélection répétée et preuve indépendante ?
6. Les horizons à 50 Hz, origines communes, unités indépendantes et futures familles
   statistiques sont-ils appropriés ? Quelles décisions doivent rester gelées avant
   validation ou confirmation plutôt qu'être imposées sans données maintenant ?
7. Les qualifications séparées préservent-elles les acquis sans présenter la moyenne
   seule comme une agence, une incertitude calibrée ou un J1 intégralement validé ?
8. L'artefact et l'activation proposée permettent-ils reprise exacte et apprentissage
   idempotent sans confondre mémoire de statuts et mémoire de paramètres ?
9. Les plafonds de 15 minutes par invocation et 60 minutes cumulées de première
   itération, incluant génération/évaluation, suffisent-ils à borner le développement ?

## Réponse attendue

Écrire uniquement la revue dans `docs/research/body_schema_002_review.md`.
Indiquer explicitement qu'elle porte sur la révision 2 du 9 septembre 2026.

Verdict : `AUTORISER`, `AUTORISER AVEC CORRECTIONS BLOQUANTES` ou `REFUSER`.
Pour chaque correction : défaut concret, portée, texte normatif intégrable et critère
vérifiable. Séparer corrections nécessaires avant développement, champs à fixer par
Codex dans le manifeste de développement et exigences du futur gel confirmatoire.

Terminer par une autorisation ou interdiction explicite du code r2, des tests et du
développement borné, puis de son intégration persistante. La confirmation, les graines
historiques 19201..19224, 19391..19396, 19501..19524 et J5 restent interdits.
Ne pas transformer cette revue en autorisation du smoke v1 ni demander un nouveau
modèle complexe sans identifier le manque mesuré.
