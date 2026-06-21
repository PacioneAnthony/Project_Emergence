import time
import numpy as np
import torch
from core.reflex_policy import ReflexActor

print(f"Initialisation sur : {torch.cuda.get_device_name(0)}")

# 1. Configuration de l'anatomie
VISION_SIZE = 64   # Taille du vecteur latent visuel (fictif pour l'instant)
BODY_SIZE = 8      # Taille du vecteur état interne
ACTION_SIZE = 2    # Moteur Gauche, Moteur Droit

INPUT_SIZE = VISION_SIZE + BODY_SIZE

# 2. Naissance du cerveau
brain = ReflexActor(input_dim=INPUT_SIZE, action_dim=ACTION_SIZE)
print("Cerveau réflexe chargé en mémoire VRAM.")

# 3. Simulation d'une boucle perception-action rapide
print("\n--- DÉBUT DU TEST RÉFLEXE (10 itérations) ---")
latence_cumul = 0

for i in range(10):
    # Simulation d'une entrée capteur (Bruit aléatoire pour l'instant)
    fake_vision = np.random.randn(VISION_SIZE)
    fake_body = np.random.randn(BODY_SIZE)
    
    # Concaténation (C'est ce que l'agent "voit" globalement)
    full_state = np.concatenate((fake_vision, fake_body))
    
    # Chronométrage précis
    start = time.perf_counter()
    
    # DÉCISION (Inférence GPU)
    action = brain.get_action(full_state)
    
    end = time.perf_counter()
    duration_ms = (end - start) * 1000
    latence_cumul += duration_ms
    
    print(f"[Tick {i}] Action Moteurs : {action} | Latence : {duration_ms:.3f} ms")

print(f"\nLatence moyenne : {latence_cumul/10:.3f} ms")
print("Objectif < 20ms :", "SUCCÈS" if (latence_cumul/10) < 20 else "ÉCHEC")