# Émergence - Boîte de réception d'Anthony

Dernière mise à jour par Codex: 2026-06-12  
Décisions à arbitrer: **1**  
Informations à fournir: **0**  
Actions matérielles à effectuer: **1**

## Mode d'emploi

Ce document centralise uniquement les décisions et informations qui demandent une intervention d'Anthony.

- Codex ajoute les demandes, leur contexte et leur niveau de priorité.
- Anthony écrit directement sous **Réponse Anthony** et peut ajouter des remarques libres.
- Une réponse partielle est acceptable; Codex conservera les points encore ouverts.
- Après lecture, Codex intègre la réponse dans les spécifications, décisions ou protocoles concernés.
- L'entrée complète est ensuite déplacée dans **Historique des éléments traités**, sans supprimer ni reformuler la réponse originale d'Anthony.
- Codex signale également toute nouvelle demande dans la conversation; ce fichier n'a pas besoin d'être surveillé en continu.

Statuts utilisés: `à répondre`, `à arbitrer`, `à effectuer`, `réponse partielle`, `répondu`, `intégré`, `clos`.

## Décisions à arbitrer

### ANT-008 - Achat du kit AS5600

- Statut: `à arbitrer`
- Priorité: nécessaire pour J1a, non bloquante pour l'essai court J0
- Demandé le: 2026-06-11
- Question: valides-tu l'achat du kit officiel `AS5600-SO_EK_AB`, préfères-tu une alternative moins chère, ou souhaites-tu différer l'achat jusqu'après l'essai court J0 ?
- Recommandation Codex: kit officiel avec aimant diamétral de référence, autour de 19,40 USD hors port et taxes lors de la préparation.
- Détails: voir `HARDWARE_PURCHASES.md`, entrée P-001.

**Réponse Anthony:**

> 

**Remarques facultatives:**

> 

## Informations à fournir

Aucune information en attente.

## Actions matérielles à effectuer

### ANT-009 - Construction et réception du banc v1.0

- Statut: `en cours`
- Priorité: bloquante pour la session J0 de 30 minutes et J1a
- Demandé le: 2026-06-12
- Action: poursuivre avec Claude la conception, les mesures, le coupon de tolérances, l'impression et l'assemblage décrits dans `BENCH_DESIGN.md`.
- Sécurité: ne plus exécuter d'essai moteur sur le montage v0.1. Le firmware passif patch 2 sera flashé par la procédure Codex lorsque le nouveau banc sera prêt.
- Retour attendu: message « banc v1.0 prêt », écarts éventuels par rapport au dossier, jeu ou friction perçus et photo facultative si elle aide à comprendre la géométrie.

**Résultat Anthony:**

> 

**Remarques facultatives:**

> 

## Historique des éléments traités

### ANT-007 - Qualification physique courte de J0

- Statut: `clos`
- Demandé le: 2026-06-11
- Réponse reçue le: 2026-06-12
- Première tentative: `j0-20260612T122444.759901Z-e6395a2f`, avortée par le pilote audio WASAPI; cause corrigée.
- Session servo: `j0-20260612T123848.687322Z-afac9e86`, 10 719 événements, aucun CRC ni perte, blobs intègres, replay déterministe, servo 90/80/100/90 acquitté.
- Session de synchronisation: `j0-20260612T125102.028740Z-a0dc0f70`, vidéo `+12,69 ms`, IMU `-10,78 ms`, cible de 20 ms respectée.
- Réponse Anthony: « Les mouvements de l'essai de 60s semblaient un peu tremblant quand même. Mais je dois préciser que le banc d'essai actuel était ma version v0.1, la tête est directement posée sur l'axe du servomoteur, avec une vis pour les relier mais je sens que l'assemblage reste assez fragile. »
- Intégration: D-005, firmware passif patch 2, rapport `j0 mechanics`, critères de réception de `BENCH_DESIGN.md` et suspension des nouveaux essais moteur sur v0.1.

### ANT-H001 - Validation de D-002

- Statut: `intégré`
- Réponse reçue le: 2026-06-11
- Réponse Anthony: validation de l'avis conjoint de Codex et Claude concernant D-002.
- Intégration: `DECISIONS.md`, `SESSION_HANDOFF.md` et `COLLABORATION_PROTOCOL.md` mis à jour le 2026-06-11.

### ANT-001 - Position de l'IMU

- Statut: `intégré`
- Priorité: bloquante pour J0
- Demandé le: 2026-06-11
- Réponse reçue le: 2026-06-11
- Question: le MPU-9250/6500/9255 est-il fixé sur la tête mobile avec la webcam et l'ultrason, ou sur une partie fixe du banc ?
- Pourquoi: cette position détermine si l'IMU mesure directement le mouvement du cou ou celui du support.

**Réponse Anthony:**

> Il est fixé sur la tête mobile directement.

**Remarques facultatives:**

> Aucune.

- Intégration: position mobile inscrite dans `DEVELOPMENTAL_ARCHITECTURE.md`, `COLLABORATION_PROTOCOL.md` et `SESSION_HANDOFF.md`.

### ANT-002 - Microphone utilisé

- Statut: `intégré`
- Priorité: nécessaire pour cadrer l'audio de J0
- Demandé le: 2026-06-11
- Réponse reçue le: 2026-06-11
- Question: quel microphone sera utilisé au départ ? Préciser si possible le modèle, s'il est intégré à la webcam, et son interface avec le PC.
- Pourquoi: le choix influence la synchronisation, la fréquence d'échantillonnage et les futurs tests de familiarité vocale.

**Réponse Anthony:**

> Actuellement j'utilise le micro de ma webcam, une BRIO 100.

**Remarques facultatives:**

> Je pourrai éventuellement brancher un vrai micro, un TRUST GTX 232, mais il est gros donc serait positionné à côté du banc d'éssai.

- Intégration: BRIO 100 retenue pour J0 et Trust GXT 232 comme référence optionnelle pour F1.

### ANT-003 - Limites mécaniques du servomoteur

- Statut: `intégré`
- Priorité: bloquante avant les mouvements automatiques
- Demandé le: 2026-06-11
- Réponse reçue le: 2026-06-11
- Question: quelles limites d'angle considères-tu actuellement comme sûres pour le servomoteur MF90 et le montage du cou ? Indiquer aussi les zones où il force, vibre ou chauffe.
- Pourquoi: ces limites seront imposées par la couche de sécurité matérielle, indépendamment du contrôleur appris.

**Réponse Anthony:**

> Pour être large, on prendre de 10° à 170°. Je n'ai remarqué aucun comportement particulier en dehors de ça.

**Remarques facultatives:**

> Aucune.

- Intégration: limites 10 à 170 degrés inscrites dans la spécification et appliquées aux chemins moteurs actifs.

### ANT-004 - Vérité terrain de l'angle

- Statut: `intégré`
- Priorité: recommandée pour J0/J1a
- Demandé le: 2026-06-11
- Réponse reçue le: 2026-06-11
- Question: peux-tu ajouter temporairement une mesure indépendante de l'angle réel du cou, par exemple un rapporteur, des repères visuels exploitables par la webcam ou un capteur dédié ?
- Pourquoi: la consigne envoyée au servo n'est pas une mesure fiable de l'angle réellement atteint.

**Réponse Anthony:**

> J'ai un potentiomètre 10K 2PCS fourni avec "The Most Complete Starter Kit Mega Project ELEGOO", j'avais cru comprendre par Claude qu'on pourrait peut-être l'utiliser. Sinon je préfèrerais acheter le bon matériel directement.

**Remarques facultatives:**

> Aucune.

- Intégration: AS5600 retenu comme cible de vérité terrain; potentiomètre 10 kOhm conservé comme solution de prototypage.

### ANT-005 - Disponibilité d'une seconde personne

- Statut: `intégré`
- Priorité: non bloquante pour J0
- Demandé le: 2026-06-11
- Réponse reçue le: 2026-06-11
- Question: une seconde personne pourra-t-elle participer occasionnellement à de courtes sessions ultérieures de voix ou de présence ?
- Pourquoi: cela permettra de distinguer la familiarité avec Anthony d'une simple détection de présence humaine.

**Réponse Anthony:**

> Oui, je pourrai occasionnellement faire venir 2 à 3 autres personnes (séparément). Mais dans > 90% des cas ce sera moi uniquement.

**Remarques facultatives:**

> Aucune.

- Intégration: protocole J4 cadré pour au moins une autre personne réelle sur trois sessions et dix sessions au total.

### ANT-006 - Stockage et rétention des données

- Statut: `intégré`
- Priorité: nécessaire avant une collecte audio/vidéo prolongée
- Demandé le: 2026-06-11
- Réponse reçue le: 2026-06-11
- Question: quel volume de stockage local souhaites-tu consacrer au projet et combien de temps faut-il conserver les enregistrements audio/vidéo bruts ?
- Pourquoi: cela détermine la compression, la rotation des fichiers et la politique de suppression automatique.

**Réponse Anthony:**

> 200Go actuellement, avec possibilité d'ajouter un SSD dédié sur mon PC ultérieurement. Concernant la durée de conservation, étant donné que ça reste privé, je n'ai pas réellement de contraintes hormis l'espace de stockage et la pertinence des données.

**Remarques facultatives:**

> Aucune.

- Intégration: quota initial de 200 Go, revue à 160 Go, suspension des enregistrements bruts longs à 180 Go et aucune suppression silencieuse.
