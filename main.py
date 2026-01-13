import time
import numpy as np
import torch
import cv2
import threading

# Import des organes
from sensory.vision_brain import DeepVision # <--- NOUVEL IMPORT
from core.biological_reward import RewardSystem
from core.reflex_policy import ReflexActor
from core.memory import ReplayBuffer
from core.motor import MotorCortex
from core.cortex import Cortex

shared_context = {
    "battery": 1.0,
    "vision_status": "Rien",
    "last_action": "Aucune",
    "intention_vector": np.zeros(32)
}

def cortex_process(cortex_brain):
    print("  [V] Cortex (Llama 3) : Démarré en arrière-plan")
    while True:
        situation_text = (
            f"Batterie: {int(shared_context['battery']*100)}%. "
            f"Vue: {shared_context['vision_status']}. "
            f"Dernière action: {shared_context['last_action']}."
        )
        strategy = cortex_brain.think(situation_text)
        shared_context["intention_vector"] = cortex_brain.get_intention()
        time.sleep(0.1)

def life_cycle():
    print("--- INITIALISATION DE L'ORGANISME (DEEP VISION) ---")
    
    # 1. Connexions Hardware
    try:
        eye = DeepVision() # <--- INSTANCE DEEP VISION
        # On essaie de charger l'entrainement visuel précédent s'il existe
        eye.load_adapter("vision_adapter.pth") 
        print("  [V] Vision : OK")
    except Exception as e:
        print(f"  [X] Vision : Erreur ({e})")
        return

    muscles = MotorCortex()
    
    # 2. Configuration Dimensions
    VISION_DIM = 128 # <--- C'EST MAINTENANT 128 (Sortie de l'adaptateur)
    BODY_DIM = 8
    INTENTION_DIM = 32
    STATE_DIM = VISION_DIM + BODY_DIM + INTENTION_DIM 
    ACTION_DIM = 2 

    # 3. Organes Cognitifs
    brain = ReflexActor(STATE_DIM, ACTION_DIM)
    try: brain.load_model("actor.pth")
    except: pass
    
    heart = RewardSystem({})
    memory = ReplayBuffer(capacity=100_000, state_dim=STATE_DIM, action_dim=ACTION_DIM)
    cortex = Cortex() 
    
    print("--- NAISSANCE ---")

    mind_thread = threading.Thread(target=cortex_process, args=(cortex,), daemon=True)
    mind_thread.start()

    body_state = { "battery_level": 1.0, "collision_impact": 0.0, "gpu_temp": 0.4 }
    
    step = 0
    last_latent = np.zeros(VISION_DIM)
    long_term_vision = np.zeros(VISION_DIM)
    
    try:
        while True:
            # 1. PERCEPTION HYBRIDE
            # vector = Pour le cerveau (128 floats)
            # human_info = (bool, x_pos) Pour la batterie et le cortex
            vector, human_info, frame = eye.see()
            
            is_human_visible, human_x = human_info

            if vector is None:
                current_vision = last_latent
                vision_text = "Rien (Noir)"
            else:
                current_vision = vector
                last_latent = vector
                
                # Traduction pour le Cortex (Language)
                if is_human_visible:
                    pos_str = "CENTRE"
                    if human_x < 0.4: pos_str = "GAUCHE"
                    elif human_x > 0.6: pos_str = "DROITE"
                    vision_text = f"HUMAIN ({pos_str})"
                elif np.std(current_vision) > 0.1: # Si le vecteur est complexe
                    vision_text = "OBJET/FORME"
                else:
                    vision_text = "VIDE"
            
            # --- MÉTABOLISME ---
            current_strategy = cortex.active_strategy

            if is_human_visible and current_strategy == "FOCUS":
                recharge_rate = 0.002 
                body_state["battery_level"] += recharge_rate
                energy_status = "++ CHARGE ++"
            else:
                decay_rate = 0.0001
                body_state["battery_level"] -= decay_rate
                energy_status = "-- DRAIN --"

            body_state["battery_level"] = max(0.0, min(1.0, body_state["battery_level"]))
            shared_context["battery"] = body_state["battery_level"]
            shared_context["vision_status"] = vision_text

            # 2. CONSTRUCTION DE L'ÉTAT (Avec le vecteur profond 128)
            body_vector = np.array([
                body_state["battery_level"],
                body_state["collision_impact"],
                body_state["gpu_temp"],
                0,0,0,0,0
            ])
            
            state_vector = np.concatenate((current_vision, body_vector, shared_context["intention_vector"]))
            
            # 3. ACTION
            action = brain.get_action(state_vector)
            real_angle = muscles.move(action[0])
            
            body_state["battery_level"] -= np.abs(action[0]) * 0.001
            shared_context["last_action"] = f"Angle {real_angle}°"
            
            # 4. RÉCOMPENSE & MÉMOIRE
            visual_change = np.linalg.norm(current_vision - long_term_vision)
            long_term_vision = (long_term_vision * 0.9) + (current_vision * 0.1)
            
            reward, _ = heart.get_reward(body_state, world_model_error=visual_change, social_signal=0.0)
            
            memory.add(state_vector, action, reward, state_vector, 0)
            
            if step % 10 == 0:
                thought = cortex.last_thought.split("->")[-1].strip()
                bat_pct = int(body_state['battery_level'] * 100)
                bat_bar = "█" * (bat_pct // 10)
                print(f"\r[{step}] Vie:{bat_bar} ({bat_pct}%) | {energy_status} | Pensée:[{thought}] | Angle:{real_angle} | Rwd:{reward:.2f}", end="")
            
            step += 1
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\n--- SOMMEIL FORCÉ ---")
        memory.save("memoire_vie_1.pkl")
    finally:
        # eye.release() # Pas nécessaire avec DeepVision zmq simple
        pass

if __name__ == "__main__":
    life_cycle()