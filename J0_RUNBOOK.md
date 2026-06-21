# J0 - Procédure de qualification physique

Statut: qualification courte réussie; session longue en attente du banc v1.0  
Date: 2026-06-12

Cette procédure commence uniquement après validation logicielle sans matériel. Elle remplace les essais improvisés et indique exactement ce qui est attendu d'Anthony.

## 1. État préparé par Codex

- protocole pré-enregistré: `J0_PROTOCOL.md`;
- firmware compilé pour Arduino Mega 2560;
- capture série, vidéo BRIO 100 et audio BRIO 100;
- recorder append-only, replay et rapport qualité testés;
- firmware patch 1 flashé avec succès sur l'Arduino Mega; patch 2 passif compilé mais pas encore flashé;
- microphone BRIO 100 sélectionné automatiquement avec repli entre DirectSound, MME, WASAPI et WDM-KS;
- ouverture réelle de la BRIO 100 validée via DirectSound à 44,1 kHz;
- l'acquisition attend 2,5 secondes après l'ouverture série, puis purge les octets produits pendant le redémarrage de la Mega;
- limites servo: 10 à 170 degrés;
- le patch 2 laisse le servo détaché au démarrage et le détache immédiatement en cas de silence hôte ou d'arrêt d'urgence.

## 2. Attention avant flash

Le prochain flash remplacera le patch 1 par le patch 2 passif. Par prudence, considérer tout redémarrage de la carte actuellement flashée comme susceptible de commander brièvement la position neutre de 90 degrés. Il faut donc:

1. dégager le mouvement de la tête sur toute la plage 80 à 100 degrés;
2. vérifier qu'aucun câble ne peut être tiré;
3. placer si possible le cou près de 90 degrés avant alimentation;
4. garder l'accès immédiat au câble USB;
5. ne pas tenir les engrenages ou la tête pendant le démarrage.

## 3. Flash du firmware

Depuis PowerShell, à la racine du dépôt, utiliser le script de détection automatique:

```powershell
.\windows_client\flash_j0_firmware.ps1
```

Le script refuse `COM1`, qui est le port série système, et sélectionne uniquement un périphérique Arduino/USB série identifiable. Si aucun Arduino n'est visible, débrancher puis rebrancher le câble USB, essayer un autre port ou câble de données, attendre quelques secondes, puis relancer.

Pour lister les périphériques sans enregistrer:

```powershell
.\env_windows\Scripts\python.exe -m j0.cli devices
```

## 4. Essai court de 60 secondes

Cette commande active explicitement la caméra et le microphone pendant 60 secondes et exécute une petite séquence servo `90 -> 80 -> 100 -> 90`:

```powershell
$port = (Get-CimInstance Win32_SerialPort | Where-Object { $_.Name -match 'Arduino|Mega' }).DeviceID
.\env_windows\Scripts\python.exe windows_client\j0_capture.py `
  --port $port --duration 60 --servo-test
```

La première tentative du 2026-06-12 a échoué parce que PortAudio choisissait WASAPI, refusé par le pilote de la BRIO 100. La sélection est désormais automatique et commence par DirectSound, validé sur ce PC.

La seconde tentative `j0-20260612T123848.687322Z-afac9e86` a réussi pour les flux et le servo: 10 719 événements, aucune perte, aucune erreur CRC, vidéo à 29,93 Hz, IMU à 100 Hz, ultrason à 20 Hz, audio à 20 chunks/s et replay déterministe. Le triple tapotement a été exploitable et a mis en évidence une horloge hôte trop grossière pour certifier 20 ms. Ce défaut est corrigé; il n'est pas nécessaire de refaire la séquence servo de 60 secondes.

## 5. Contrôle correctif de synchronisation de 20 secondes

Lancer une capture sans `--servo-test`:

```powershell
$port = (Get-CimInstance Win32_SerialPort | Where-Object { $_.Name -match 'Arduino|Mega' }).DeviceID
.\env_windows\Scripts\python.exe windows_client\j0_capture.py `
  --port $port --duration 20
```

Effectuer **un seul tapotement léger** vers 10 secondes, visible dans l'image, audible et mécaniquement couplé au support mobile. Trois impacts sont désormais supportés par l'analyse, mais un impact unique simplifie cette mesure corrective.

Résultat obtenu dans `j0-20260612T125102.028740Z-a0dc0f70`: vidéo `+12,69 ms`, IMU `-10,78 ms`, cible de 20 ms respectée; 3 743 événements, aucune perte, blobs intègres et replay déterministe.

Pendant l'essai:

1. ne pas toucher le banc pendant les cinq premières secondes;
2. vers 10 secondes, effectuer un tapotement léger unique sur une partie non fragile du support mobile, sans toucher les capteurs;
3. ne pas produire d'autre mouvement ou bruit marqué pendant cinq secondes avant et après ce geste;
4. arrêter immédiatement avec `Ctrl+C` en cas de mouvement inattendu, câble tendu, bruit, vibration, blocage ou chauffe.

La commande affiche le dossier de session créé dans `data/j0/sessions/`.

## 6. Contrôles après l'essai

Remplacer `<session>` par le dossier affiché:

```powershell
.\env_windows\Scripts\python.exe -m j0.cli quality <session> --allow-short
.\env_windows\Scripts\python.exe -m j0.cli clap-sync <session>
.\env_windows\Scripts\python.exe -m j0.cli replay <session>
```

Anthony transmet seulement:

- l'identifiant ou le chemin de session;
- présence éventuelle de bruit, vibration, chauffe ou jeu;
- mouvement observé correct ou incorrect;
- interruption manuelle éventuelle.

Codex lit les artefacts et décide des corrections. Anthony n'a pas à interpréter le JSON du rapport.

## 7. Passage à la session de 30 minutes

La qualification logicielle courte est réussie. La session longue reste suspendue jusqu'aux conditions suivantes:

1. banc v1.0 de `BENCH_DESIGN.md` assemblé et inspecté;
2. firmware patch 2 flashé, avec servo passif au démarrage et détachement immédiat en failsafe;
3. séquence mécanique courte réussie avec `python -m j0.cli mechanics <session>`;
4. absence de jeu, tremblement persistant, câble tendu ou échauffement signalée par Anthony.

Codex fournira alors la commande exacte de 30 minutes. Aucun nouvel essai moteur ne doit être réalisé sur le montage v0.1.
