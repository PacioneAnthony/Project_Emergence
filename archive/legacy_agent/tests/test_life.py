import time
import numpy as np
import torch
from core.biological_reward import RewardSystem
from core.reflex_policy import ReflexActor
from core.memory import ReplayBuffer

# --- CONFIGURATION ---
VISION_DIM = 64
BODY_DIM = 8
STATE_DIM = VISION_DIM + BODY_DIM
ACTION_DIM = 2

# 1. NAISSANCE
print("Initialisation des modules...")
brain_reflex = ReflexActor(STATE_DIM, ACTION_DIM) # Le Muscle
brain_bio = RewardSystem({})                      # Le Coeur
memory = ReplayBuffer(capacity=10000, state_dim=STATE_DIM, action_dim=ACTION_DIM) # La Mémoire

print("L'agent est vivant. Début du cycle éveil...")

# --- SIMULATION DE VIE (10 Ticks) ---
# État initial fictif
current_vision = np.random.randn(VISION_DIM)
current_body_sensors = {
    "battery_level": 1.0, 
    "collision_impact": 0.0, 
    "gpu_temp": 0.4
}

# On construit le vecteur d'état complet
current_state_vector = np.concatenate((current_vision, np.array(list(current_body_sensors.values()) + [0]*5))) # Padding pour arriver à 8

for t in range(10):
    start_time = time.perf_counter()
    
    # 1. ACTION (Le réseau décide)
    action = brain_reflex.get_action(current_state_vector)
    
    # 2. ENVIRONNEMENT (Simulation de la réponse du monde)
    # Dans la vraie vie, l'action ferait bouger les moteurs
    # Ici on simule juste que la batterie baisse et qu'on avance
    next_vision = np.random.randn(VISION_DIM) # La vue change
    
    # Simulation: Si on va trop vite (action > 0.8), on a une chance de collision
    collision = 0.5 if (np.abs(action[0]) > 0.8 and t > 5) else 0.0
    
    next_sensors = {
        "battery_level": 1.0 - (t * 0.05),
        "collision_impact": collision,
        "gpu_temp": 0.4
    }
    
    # 3. RÉCOMPENSE (Le corps juge l'action)
    reward, logs = brain_bio.get_reward(next_sensors, world_model_error=0.1, social_signal=0.0)
    
    # 4. MÉMOIRE (On enregistre l'expérience)
    # On doit reconstruire le vecteur "next_state"
    next_state_vector = np.concatenate((next_vision, np.array(list(next_sensors.values()) + [0]*5)))
    
    # Stockage : (s, a, r, s', done)
    done = 0 # Pas mort
    memory.add(current_state_vector, action, reward, next_state_vector, done)
    
    # Transition pour le tour suivant
    current_state_vector = next_state_vector
    current_body_sensors = next_sensors
    
    # Logs
    dt = (time.perf_counter() - start_time) * 1000
    print(f"[Tick {t}] Action={action[:2]} | Reward={reward:.2f} | Mémoire={memory.size} | Latence={dt:.2f}ms")
    if collision > 0:
        print("  >>> AIE ! COLLISION ENREGISTRÉE !")

print("\n--- TEST DE MÉMOIRE ---")
batch = memory.sample(batch_size=5)
print(f"Extraction de 5 souvenirs au hasard... Succès.")
print(f"Forme des états extraits : {batch[0].shape}")