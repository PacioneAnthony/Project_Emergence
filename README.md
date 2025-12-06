# 🌱 Projet Emergence

**Emergence** est une tentative de création d'un organisme artificiel autonome, inspiré par la robotique développementale et la biologie.

Contrairement aux IA classiques (Chatbots, Agents scriptés), Emergence ne cherche pas à résoudre une tâche précise. Son but est de **survivre, explorer et se développer** en maintenant son homéostasie (énergie, intégrité ..) et en maximisant sa curiosité.

## 🧠 Philosophie

L'agent est conçu comme un organisme bicaméral :
1.  **Le Cervelet (Système 1) :** Un réseau de neurones rapide, responsable de la survie, de la motricité et des réflexes (< 20ms).
2.  **Le Cortex (Système 2) :** Un LLM qui observe, raisonne et "parle" au cervelet en temps réel pour orienter la stratégie globale ou résoudre des problèmes complexes.
3.  **Intrinsèquement Motivé :** Il agit pour réduire sa "douleur" (batterie faible, chocs) et augmenter sa "joie" (découverte visuelle, surprise).

## ⚡ Architecture Hardware

Le projet tourne sur une infrastructure hybride locale haute performance :
* **Cerveau (Linux/WSL2) :** Héberge l'intelligence, la mémoire et l'entraînement. Utilise PyTorch sur une **NVIDIA RTX 5080**.
* **Corps (Windows) :** Gère les périphériques physiques (Webcam, Arduino/Servos) pour contourner les limitations de virtualisation.
* **Système Nerveux :** Communication ultra-rapide via **ZeroMQ** entre les deux environnements.

## 🚀 Installation & Démarrage

### Pré-requis
* Windows 11 avec WSL2 (Ubuntu).
* Python 3.10+.
* Une Webcam et un Arduino avec Servo (pour la motricité).
* GPU NVIDIA (Série 40/50 recommandée).

### 1. Côté Corps (Windows)
Lancer le script qui gère les yeux et les muscles :
```powershell
python windows_client/windows_body.py

2. Côté Cerveau (Linux)

Lancer le cycle de vie de l'agent :
Bash

python main.py

3. Le Sommeil (Apprentissage)

Une fois que l'agent a accumulé de l'expérience, lancez la consolidation :
Bash

python sleep.py

📂 Structure

    core/ : Le noyau cognitif (Cerveau réflexe, Système de récompense, Mémoire).

    sensory/ : Traitement des sens (Vision YOLO, Audio).

    windows_client/ : Scripts ponts pour le matériel Windows.

    main.py : Boucle de vie principale (Éveil).

    sleep.py : Boucle d'entraînement (Sommeil).

Projet en phase Alpha - Développement actif.