import time
import numpy as np
import torch
import cv2

# Import des organes
from sensory.vision import VisionModule
from core.biological_reward import RewardSystem
from core.reflex_policy import ReflexActor
from core.memory import ReplayBuffer
from core.motor import MotorCortex

def life_cycle():
    print("--- INITIALISATION DE L'ORGANISME ---")
    
    # 1. Connexion des sens et du cerveau
    try:
        eye = VisionModule(model_size='n')
        print("  [V] Vision : OK (Mode Réseau)")
    except Exception as e:
        print(f"  [X] Vision : ERREUR ({e})")
        return

    # Configuration des dimensions
    VISION_DIM = 64
    BODY_DIM = 8
    INTENTION_DIM = 32
    STATE_DIM = VISION_DIM + BODY_DIM + INTENTION_DIM
    ACTION_DIM = 2 # Moteur Gauche, Moteur Droit

    # Création des organes internes
    brain = ReflexActor(STATE_DIM, ACTION_DIM)
    brain.load_model("actor.pth") # <--- AJOUT : On charge l'expérience précédente
    heart = RewardSystem({}) # Config par défaut
    memory = ReplayBuffer(capacity=100_000, state_dim=STATE_DIM, action_dim=ACTION_DIM)
    muscles = MotorCortex()
    
    print(f"  [V] Cerveau : OK ({torch.cuda.get_device_name(0)})")
    print(f"  [V] Mémoire : OK")
    print("--- NAISSANCE ---")

    # État initial du corps
    body_state = {
        "battery_level": 1.0,
        "collision_impact": 0.0,
        "gpu_temp": 0.4
    }
    
    # Variables de boucle
    step = 0
    start_time = time.time()
    last_latent = np.zeros(VISION_DIM) # Mémoire visuelle court-terme
    long_term_vision = np.zeros(VISION_DIM)
    current_intention = np.zeros(INTENTION_DIM)

    try:
        while True:
            loop_start = time.perf_counter()
            
            # --- 1. PERCEPTION (SENS) ---
            # L'agent regarde
            latent_vision, frame = eye.get_latent_vector()
            
            # Si pas de nouvelle image, on utilise le souvenir rétinien (Persistance rétinienne)
            if np.sum(latent_vision) == 0 and frame is None:
                current_vision = last_latent
                vision_status = "." # Pas de nouveauté
            else:
                current_vision = latent_vision
                last_latent = latent_vision
                vision_status = "O" # Nouvelle image !
                
            # On simule la fatigue (Batterie baisse doucement)
            body_state["battery_level"] -= 0.0001
            if body_state["battery_level"] < 0: body_state["battery_level"] = 0

            # Construction de l'ÉTAT COMPLET (Vision + Corps)
            # On transforme le dict du corps en vecteur
            body_vector = np.array([
                body_state["battery_level"],
                body_state["collision_impact"],
                body_state["gpu_temp"],
                0,0,0,0,0 # Padding pour arriver à 8
            ])
            
            state_vector = np.concatenate((current_vision, body_vector, current_intention))
            
            # --- 2. DÉCISION (CERVEAU) ---
            # Le réseau de neurones décide quoi faire
            action = brain.get_action(state_vector)
            
            # --- 3. ACTION (CORPS) ---
            # action[0] est la sortie du neurone (entre -1 et 1)
            # On l'utilise pour piloter le servo
            real_angle = muscles.move(action[0])
            
            # Coût énergétique réel
            movement_cost = np.abs(action[0]) * 0.001 
            body_state["battery_level"] -= movement_cost
            
            # --- 4. RESSENTI (RÉCOMPENSE) ---
            # L'agent évalue si ce qui vient de se passer est bon
            reward, details = heart.get_reward(body_state, world_model_error=0.0, social_signal=0.0)
            
            # --- 5. MÉMORISATION (HIPPOCAMPE) ---
            # On stocke : État actuel -> Action -> Récompense -> État Suivant (simplifié ici)
            # (Dans une vraie boucle RL, on stockerait next_state au tour suivant, 
            # ici on simplifie pour le prototype)
            done = 0
            memory.add(state_vector, action, reward, state_vector, done)
            
            # --- AFFICHAGE DE VIE (CONSOLE) ---
            # On rafraîchit la ligne toutes les 100ms pour pas spammer
            if step % 5 == 0:
                # Barre de vie (Batterie)
                bat_bar = "█" * int(body_state['battery_level'] * 10)
                
                # Que voit-il ? (Le détecteur de personne est souvent l'index 0)
                see_human = "HUMAIN" if current_vision[0] > 0.5 else "......"
                
                print(f"\r[{step}] Vie:{bat_bar} | Vue:[{vision_status}] {see_human} | Action:{action[:2]} | Humeur (Reward):{reward:.3f}", end="")
            
            step += 1
            
            # Cadence (On essaie de tourner à ~60Hz)
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\n--- MORT (ARRÊT MANUEL) ---")
        print(f"Expérience totale : {step} cycles")
        print(f"Souvenirs stockés : {memory.size}")
        memory.save("memoire_vie_1.pkl")
    finally:
        eye.release()

if __name__ == "__main__":
    life_cycle()