# 🏗️ Architecture Technique

Ce document détaille les choix techniques pour assurer une latence minimale (< 20ms) et une modularité maximale.

## 1. Topologie Distribuée (Client-Serveur Local)

Pour palier aux problèmes de latence USB et d'accès matériel sous WSL2, nous avons adopté une architecture découplée via **ZeroMQ (ZMQ)**.

### Le Corps (Windows - `windows_body.py`)
* **Rôle :** Driver matériel "dumb" (bête).
* **Vision :** Capture OpenCV native (30 FPS stables). Compression JPG à la volée. Diffusion sur port `5555` (PUB).
* **Moteur :** Écoute sur port `5556` (SUB). Reçoit des angles bruts et les transmet à l'Arduino via `pyserial`. L'Arduino traduit ces angles en pas pour le moteur Stepper (transparent pour le cerveau).
* **Avantage :** Stabilité totale des drivers Windows, pas de crash graphique WSL.

### Le Cerveau (Linux - `main.py`)
* **Rôle :** Prise de décision et perception.
* **Vision Module :** Client ZMQ (SUB). Décode le JPG et injecte dans YOLOv8.
* **Motor Cortex :** Client ZMQ (PUB). Transforme l'intention neuronale (-1.0 à 1.0) en commande physique (10° à 170°).

## 2. Pipeline Cognitif

La boucle de vie (`life_cycle`) tourne à ~60Hz :

1.  **Perception (YOLOv8 Nano) :**
    * Modèle : `yolov8n.pt` (chargé sur GPU).
    * Sortie : Vecteur latent (64 floats) représentant la confiance des classes détectées (Humain, Objet...).
    * Optimisation : Utilisation de `half=True` (FP16) sur TensorRT/CUDA.

2.  **État Interne (Proprioception) :**
    * Vecteur concaténé : `[Vision (64) + Corps (8)]` = État (72).
    * Variables corps : Niveau batterie, Température, Intégrité physique.

3.  **Décision (Reflex Policy) :**
    * Architecture : MLP (Multi-Layer Perceptron) 2 couches cachées de 256 neurones.
    * Activation : GELU.
    * Sortie : `Tanh` (pour borner l'action entre -1 et 1).
    * Latence d'inférence : < 0.5 ms sur RTX 5080.

4.  **Récompense Biologique :**
    * Formule : $R_t = w_h \cdot H_t + w_c \cdot C_t$
    * $H_t$ (Homéostasie) : Pénalité quadratique si la batterie baisse ou choc.
    * $C_t$ (Curiosité) : Distance euclidienne entre la vision actuelle et la mémoire visuelle court-terme (détection de changement).

## 3. Apprentissage (Reinforcement Learning Offline)

L'agent n'apprend pas en temps réel (trop risqué/instable). Il apprend la nuit.

* **Algorithme :** Actor-Critic (Inspiré de SAC/TD3).
* **Replay Buffer :** Stocke jusqu'à 100,000 transitions `(état, action, récompense, état_suivant)`.
* **Optimiseur :** Adam (Learning rate 3e-4).
* **Processus :**
    * Le **Critique** apprend à prédire la récompense future (minimise l'erreur MSE).
    * L'**Acteur** apprend à maximiser la note donnée par le Critique.

## 4. Architecture Cognitive Hybride (Dual Process Theory)

Pour permettre au LLM d'intervenir pendant l'éveil sans briser le temps réel, nous utilisons une architecture asynchrone :

### Le Cervelet (Fast Loop - 60 Hz)
* C'est le `ReflexActor` actuel.
* **Entrées :** Vision + Corps + **Vecteur de Contexte (venant du LLM)**.
* Il décide de l'action motrice précise à chaque milliseconde.
* Il peut envoyer des "Signaux d'Interruption" au LLM si une surprise (Reward Curiosité > Seuil) survient.

### Le Cortex (Slow Loop - Llama 3.2)
* C'est un LLM local.
* **Entrées :** Résumé textuel ou sémantique de la situation (ex: "Batterie faible, objet rouge détecté").
* **Sortie :** Ne contrôle PAS les moteurs directement. Il génère un **Vecteur d'Intention** (Embedding) ou modifie des variables globales (ex: `fear_level`, `curiosity_gain`).
* Ce vecteur est injecté en temps réel dans l'input du Cervelet.

**Exemple de dialogue interne :**
1.  *Cervelet* : "Je vois un mur, je recule." (Action réflexe)
2.  *Cervelet* : Envoie signal "Bloqué" au Cortex.
3.  *Cortex* : Analyse... "On est bloqué depuis 10s. Essaie de tourner à 90°."
4.  *Cortex* : Envoie vecteur [Intention: Rotation] au Cervelet.
5.  *Cervelet* : Reçoit l'intention + Vision du mur -> Exécute la rotation.
