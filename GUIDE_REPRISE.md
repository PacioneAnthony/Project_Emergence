# 📘 Guide de Reprise - Projet Emergence

Ce guide t'aidera à relancer le robot après une pause, en tenant compte du nouveau servo moteur MF90.

## 🛠️ 1. Matériel & Câblage (Côté Windows)

Tu as un servo moteur **MF90** (équivalent SG90/MG90S) avec 3 fils. Voici comment le brancher sur ton **Arduino** (Uno/Nano) :

| Couleur du Fil (Servo) | Pin Arduino | Rôle |
| :--- | :--- | :--- |
| **Marron** (ou Noir) | **GND** | Masse |
| **Rouge** | **5V** | Alimentation |
| **Orange** (ou Jaune/Blanc) | **Pin 9** | Signal (PWM) |

> ⚠️ **Attention** : Assure-toi que l'Arduino est bien connecté en USB à ton PC Windows. Note le port COM (ex: `COM3`, `COM4`) qui apparaît dans le Gestionnaire de Périphériques.

---

## 💾 2. Mise à jour de l'Arduino

1. Ouvre l'IDE Arduino.
2. Ouvre le fichier situé dans le projet : `windows_client/emergence_servo.ino`.
3. Sélectionne le bon modèle de carte (Tools > Board) et le bon port (Tools > Port).
4. Clique sur **Téléverser (Upload)** (La flèche vers la droite).
5. Une fois "Done uploading" affiché, ferme l'IDE Arduino (sinon le port COM sera occupé).

---

## 🧠 3. Démarrage de l'IA (Côté WSL/Linux)

Ouvre ton terminal WSL (Ubuntu) à la racine du projet.

### Étape A : Lancer le "Subconscient" (Ollama)
Assure-toi que le serveur de modèle est lancé.
```bash
ollama serve
```
*(Laisse ce terminal ouvert ou lance-le en tâche de fond)*.
Vérifie que tu as le modèle : `ollama list`. Il te faut `llama3.2`.

### Étape B : Préparer l'environnement
Assure-toi d'être dans ton environnement Python (venv ou conda) si tu en as un.

---

## 🚀 4. Lancement du Système (Ordre Strict)

Il faut lancer le "Corps" avant le "Cerveau" pour que les connexions réseaux s'établissent bien.

### 1. Démarrer le Corps (Windows)
Ouvre un **PowerShell** ou un **CMD** sous Windows (pas dans WSL).
Va dans le dossier du projet :
```powershell
cd chemin\vers\Emergence\windows_client
python windows_body.py
```
* Tu devrais voir ta webcam s'allumer.
* Le message `[V] Arduino connecté sur COMx` doit apparaître. Si ça échoue, il te listera les ports dispos. Modifie `windows_body.py` si besoin.

### 2. Démarrer le Cerveau (Linux/WSL)
Dans ton terminal WSL :
```bash
python main.py
```

---

## ✅ Vérification

1. **Vision** : La fenêtre Windows doit afficher ce que voit le robot.
2. **Réflexe** : Si tu bouges devant la caméra, le robot doit réagir (texte qui change dans le terminal Linux).
3. **Moteur** : Le servo doit bouger (probablement trembler ou chercher une position) en fonction des décisions du réseau de neurones.
4. **Pensée** : Toutes les quelques secondes, tu verras la "Pensée" du Cortex (Llama) s'afficher dans le terminal Linux.

Bon retour parmi nous ! 🤖
