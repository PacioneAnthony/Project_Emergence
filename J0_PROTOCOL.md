# J0 - Protocole pré-enregistré d'instrumentation fiable

Statut: actif; version 1.0 pré-enregistrée, amendements techniques documentés après essais courts  
Version: 1.2  
Date: 2026-06-12  
Responsable technique: Codex

### Amendement technique 1.1 du 2026-06-12

La session courte `j0-20260612T123848.687322Z-afac9e86` a révélé que Python utilisait `GetTickCount64` avec une résolution de 15,625 ms pour `time.monotonic_ns()` sur ce poste. Les seuils, hypothèses et critères de passage restent inchangés. L'implémentation est corrigée comme suit avant toute décision sur le critère de 20 ms:

- horloge hôte commune remplacée par `perf_counter_ns()` / `QueryPerformanceCounter`;
- origine audio ancrée sur l'heure ADC PortAudio, puis progression calculée par le nombre exact d'échantillons;
- analyse du geste étendue aux impacts multiples et à la position intra-bloc du pic audio;
- la session courte reste valide pour l'intégrité, les débits, le servo et le replay, mais pas pour certifier la synchronisation intermodale.

### Amendement de sécurité 1.2 du 2026-06-12

La synchronisation haute résolution a été validée par la session `j0-20260612T125102.028740Z-a0dc0f70`: vidéo `+12,69 ms`, IMU `-10,78 ms`, maximum absolu `12,69 ms`. L'observation physique et le rapport mécanique de la session servo montrent toutefois une stabilisation insuffisante du montage v0.1.

- le firmware patch 2 laisse le servo détaché au démarrage;
- seule une commande `SET_SERVO` explicite attache et déplace le servo;
- un arrêt d'urgence ou une perte de communication détache immédiatement le servo sans mouvement automatique vers le neutre;
- aucun nouvel essai moteur n'est autorisé sur le montage v0.1;
- la session de 30 minutes attend le banc successeur décrit dans `BENCH_DESIGN.md` et sa qualification mécanique.

## 1. Question

Le banc peut-il produire pendant 30 minutes un enregistrement multimodal local, causal, contrôlable et rejouable, sans trou silencieux non signalé?

J0 ne cherche pas à démontrer une capacité cognitive. Il valide l'instrument de mesure qui sera utilisé par les jalons suivants.

## 2. Hypothèses testées

- H0.1: le protocole série binaire transporte IMU, ultrason, piézo et état servo sans perte soutenue à 115200 bauds.
- H0.2: chaque source conserve une séquence monotone et un horodatage d'acquisition distinct de l'heure de réception.
- H0.3: une session interrompue reste lisible jusqu'au dernier événement complet.
- H0.4: le replay reproduit exactement l'ordre enregistré et le contenu logique des événements.
- H0.5: l'écart temporel entre Arduino, vidéo et audio peut être mesuré; il n'est jamais supposé nul.
- H0.6: le quota de stockage arrête proprement une collecte longue avant saturation du disque.

## 3. Périmètre

Inclus:

- firmware unique pour servo, IMU, ultrason et piézo;
- protocole série binaire versionné avec CRC;
- événements asynchrones horodatés;
- enregistrement append-only et blobs séparés;
- replay déterministe;
- rapport automatique de pertes, débits, trous et synchronisation;
- vidéo BRIO 100 et audio BRIO 100 lors de la validation physique;
- limites servo 10 à 170 degrés.

Exclus:

- apprentissage, embeddings, JEPA, LNN ou LLM;
- estimation absolue fiable de l'angle, reportée à J1a avec vérité terrain;
- interprétation du piézo comme contact tant qu'il n'est pas mécaniquement couplé;
- suppression automatique de données brutes.

## 4. Protocole série EMG1

Transport: USB série, 115200 bauds, 8N1, little-endian.  
Magic: octets `A5 5A`.  
Version de protocole: `1`.  
Taille maximale de payload: 512 octets côté hôte, 32 octets côté firmware.

En-tête fixe de 16 octets:

| Offset | Type | Champ |
|---:|---|---|
| 0 | `u8[2]` | magic `A5 5A` |
| 2 | `u8` | version |
| 3 | `u8` | type de message |
| 4 | `u8` | flags |
| 5 | `u8` | réservé, zéro |
| 6 | `u16` | longueur du payload |
| 8 | `u32` | numéro de séquence de l'émetteur |
| 12 | `u32` | `micros()` source, avec débordement autorisé |

Le payload est suivi d'un CRC-16/CCITT-FALSE little-endian calculé depuis `version` jusqu'à la fin du payload. Le magic et le CRC lui-même sont exclus.

Types version 1:

| Type | Nom | Direction | Payload |
|---:|---|---|---|
| `0x01` | `DEVICE_HELLO` | Arduino vers hôte | capacités, fréquences, limites, WHO_AM_I |
| `0x10` | `IMU_SAMPLE` | Arduino vers hôte | accel XYZ et gyro XYZ bruts, statut |
| `0x11` | `RANGE_SAMPLE` | Arduino vers hôte | distance mm, piézo brut, cible servo, statut |
| `0x12` | `SERVO_STATE` | Arduino vers hôte | séquence commande, demandé, appliqué, statut |
| `0x20` | `SYNC_REPLY` | Arduino vers hôte | jeton, heure hôte émise, réception et émission Arduino |
| `0x7F` | `ERROR` | Arduino vers hôte | code et contexte |
| `0x80` | `SET_SERVO` | hôte vers Arduino | angle demandé en centi-degrés |
| `0x81` | `SYNC_REQUEST` | hôte vers Arduino | jeton et heure monotone hôte en ns |
| `0x82` | `E_STOP` | hôte vers Arduino | aucun |

Les conversions IMU sont enregistrées avec leur calibration. Configuration initiale: accéléromètre +/-4 g et gyroscope +/-500 degrés/s. Les valeurs brutes restent conservées.

## 5. Contrat d'événement

Chaque ligne de `events.jsonl` est un objet JSON UTF-8 contenant au minimum:

```text
schema_version
session_id
event_type
source_id
sequence_id
source_timestamp_ns
host_receive_timestamp_ns
payload
quality
calibration_version
```

Les octets vidéo et audio ne sont pas inclus dans JSONL. Ils sont écrits dans `blobs/video/` et `blobs/audio/`; l'événement contient le chemin relatif, la taille et le SHA-256.

Ordre causal de référence: ordre append-only de `events.jsonl`. Les horodatages servent à mesurer et expliquer l'ordre, pas à réordonner silencieusement les données après collecte.

## 6. Structure d'une session

```text
data/j0/sessions/<session_id>/
  manifest.json
  events.jsonl
  blobs/video/
  blobs/audio/
  reports/quality.json
```

`manifest.json` contient les versions logiciel/firmware, le matériel déclaré, les paramètres d'acquisition, les calibrations, les personnes présentes et les heures de début/fin. Il est remplacé atomiquement; `events.jsonl` n'est jamais réécrit.

## 7. Fréquences et seuils pré-enregistrés

Valeurs cibles:

- IMU: 100 Hz; avertissement si débit < 95 Hz ou trou > 50 ms;
- ultrason/piézo: 20 Hz; avertissement si débit < 18 Hz ou trou > 250 ms;
- vidéo: 30 Hz; avertissement si débit < 27 Hz ou trou > 250 ms;
- audio: chunks de 20 à 100 ms; avertissement si trou > 200 ms;
- servo et commandes: aucun saut de séquence silencieux;
- désalignement intermodal F3: cible < 20 ms, soit un pas de boucle rapide;
- requête de synchronisation hôte: toutes les 500 ms; elle sert aussi de heartbeat de communication;
- durée de qualification: au moins 1800 secondes.

Un trou est acceptable uniquement s'il est accompagné d'un événement explicite `source_status`, `drop_notice` ou d'une fermeture de session.

## 8. Quota et rétention

- budget nominal: 200 Go;
- avertissement: 160 Go utilisés;
- interdiction de démarrer une session brute longue: 180 Go utilisés;
- aucune suppression automatique ou silencieuse;
- chaque suppression future devra être explicite et journalisée hors du flux append-only supprimé;
- le rapport J0 mesure les octets par minute et extrapole les Go par semaine.

## 9. Baselines et contrôles

- protocole texte historique: conservé uniquement comme point de comparaison de bande passante, jamais comme solution de repli active;
- replay baseline: lecture séquentielle sans temporisation;
- replay temporisé: même ordre et mêmes contenus, seule l'attente change;
- corruption contrôlée d'un octet: le CRC doit rejeter la trame et le décodeur doit retrouver la suivante;
- interruption contrôlée en milieu de ligne JSON: le replay ignore uniquement la dernière ligne incomplète et signale l'incident;
- simulation de quota: le démarrage doit être refusé au seuil d'arrêt.

## 10. Critères de passage J0

Tous les critères sont nécessaires:

1. une session physique d'au moins 30 minutes contient IMU, ultrason, état servo, vidéo et audio;
2. chaque perte de séquence, corruption, indisponibilité ou trou dépassant les seuils est compté ou signalé;
3. aucun trou silencieux critique n'est détecté;
4. le replay séquentiel produit le même nombre d'événements et le même SHA-256 logique que l'enregistrement;
5. le test du clap fournit une distribution d'offsets audio/vidéo et le test de mouvement fournit une relation IMU/commande;
6. le désalignement mesuré est inférieur à 20 ms, ou J0 reste ouvert avec fenêtres d'incertitude explicites;
7. le rapport contient bande passante série, taux par modalité, max-gap, pertes, CRC, volume/minute et projection hebdomadaire;
8. une perte de communication place le servo au neutre ou désactive ses impulsions selon la politique firmware validée;
9. la session reste rejouable après arrêt normal et après interruption simulée.

## 11. Stop-loss et décisions

- si 115200 bauds dépasse 70 % d'occupation mesurée, réduire les payloads ou augmenter le débit avant toute collecte multimodale;
- si le décodeur ne se resynchronise pas après corruption, aucun essai physique long n'est autorisé;
- si le jitter intermodal est non stationnaire ou >20 ms, ajouter une synchronisation active et propager une incertitude temporelle;
- si l'audio BRIO 100 ne peut pas être acquis sans traitement opaque acceptable, comparer au Trust GXT 232 avant J3;
- si le volume projeté dépasse 200 Go avant quatre semaines, ajuster compression et politique de sélection, sans suppression silencieuse;
- aucun apprentissage J1+ n'est lancé sur une session qui échoue au contrôle qualité J0.

## 12. Intervention humaine prévue

Codex prépare le logiciel, les tests à blanc et la commande exacte. Anthony n'intervient qu'après réussite des tests sans matériel, pour:

- flasher le firmware préparé;
- vérifier le câblage et autoriser les mouvements;
- exécuter une courte qualification guidée, puis la session de 30 minutes;
- produire les événements manuels demandés, notamment le clap;
- signaler bruit, vibration, chauffe ou jeu.
