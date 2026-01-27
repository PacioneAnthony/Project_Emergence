import time
import numpy as np
import torch
import cv2
import threading

# Import des organes
from sensory.vision import VisionModule
from core.biological_reward import RewardSystem
from core.reflex_policy import ReflexActor
from core.memory import ReplayBuffer
from core.motor import MotorCortex
from core.cortex import Cortex

# Variables partagées entre les deux cerveaux (Thread Safe)
shared_context = {
    "battery": 1.0,
    "vision_status": "Rien",
    "last_action": "Aucune",
    "intention_vector": np.zeros(32) # Le canal de communication
}

def cortex_process(cortex_brain):
    """
    Le Système 2 (Lent). Tourne dans son propre thread.
    Il observe le contexte partagé et décide d'une stratégie.
    """
    print("  [V] Cortex (Llama 3) : Démarré en arrière-plan")

    while True:
        # 1. Lire la situation (depuis le corps)
        situation_text = (
            f"Batterie: {int(shared_context['battery']*100)}%. "
            f"Vue: {shared_context['vision_status']}. "
            f"Dernière action: {shared_context['last_action']}."
        )

        # 2. Réfléchir (Prend 1 à 2 secondes)
        strategy = cortex_brain.think(situation_text)

        # 3. Mettre à jour l'intention (La commande pour le Cervelet)
        shared_context["intention_vector"] = cortex_brain.get_intention()

        # Petite pause pour laisser respirer le GPU
        time.sleep(0.1)

def life_cycle():
    print("--- INITIALISATION DE L'ORGANISME BICAMÉRAL ---")

    # 1. Connexions Hardware
    try:
        eye = VisionModule(model_size='n')
        print("  [V] Vision : OK")
    except:
        print("  [X] Vision : Erreur (Verifiez windows_body.py)")
        return

    # On active le vrai moteur (connecté via ZeroMQ au client Windows)
    muscles = MotorCortex(mock=False)

    # 2. Configuration Dimensions
    VISION_DIM = 64
    BODY_DIM = 8
    INTENTION_DIM = 32 # L'espace pour le LLM
    STATE_DIM = VISION_DIM + BODY_DIM + INTENTION_DIM
    ACTION_DIM = 2

    # 3. Organes Cognitifs
    brain = ReflexActor(STATE_DIM, ACTION_DIM)
    try: brain.load_model("actor.pth")
    except: pass

    heart = RewardSystem({})
    memory = ReplayBuffer(capacity=100_000, state_dim=STATE_DIM, action_dim=ACTION_DIM)

    # Le Cortex (LLM)
    cortex = Cortex()

    print("--- NAISSANCE ---")

    # Démarrage du Thread Cortex (Esprit parallèle)
    mind_thread = threading.Thread(target=cortex_process, args=(cortex,), daemon=True)
    mind_thread.start()

    # État initial du corps
    body_state = {
        "battery_level": 1.0,
        "collision_impact": 0.0,
        "gpu_temp": 0.4,
        "light_brightness": 0.0 # <--- NOUVEAU
    }

    step = 0
    last_latent = np.zeros(VISION_DIM)
    long_term_vision = np.zeros(VISION_DIM)

    try:
        while True:
            # --- BOUCLE RAPIDE (CERVELET - 60Hz) ---

            # 1. PERCEPTION
            # Récupération de la luminosité pour la "Douleur Sursaturée"
            latent_vision, frame, brightness = eye.get_latent_vector()

            if np.sum(latent_vision) == 0 and frame is None:
                current_vision = last_latent
                vision_text = "Rien (Noir)"
            else:
                current_vision = latent_vision
                last_latent = latent_vision

                # Analyse pour le LLM
                if current_vision[0] > 0.5: vision_text = "HUMAIN (Source Energie)"
                elif np.sum(current_vision) > 0.1: vision_text = "OBJET"
                else: vision_text = "VIDE"

            # Mise à jour de l'état sensoriel
            body_state["light_brightness"] = brightness

            # --- MÉTABOLISME (Fatigue vs Recharge Sociale Consciente) ---

            is_human_visible = current_vision[0] > 0.5

            # On récupère la stratégie active du Cortex pour vérifier l'intention
            current_strategy = cortex.active_strategy

            # CONDITION STRICTE : L'humain doit être visible ET le Cortex doit être en mode "FOCUS"
            if is_human_visible and current_strategy == "FOCUS":
                # RECHARGE
                recharge_rate = 0.002
                body_state["battery_level"] += recharge_rate
                energy_status = "++ CHARGE (FOCUS) ++"
            else:
                # DÉCHARGE
                decay_rate = 0.0001
                body_state["battery_level"] -= decay_rate
                energy_status = "-- DRAIN --"

            # On borne la batterie
            body_state["battery_level"] = max(0.0, min(1.0, body_state["battery_level"]))

            # MISE À JOUR DU CONTEXTE PARTAGÉ
            shared_context["battery"] = body_state["battery_level"]
            shared_context["vision_status"] = vision_text

            # 2. CONSTRUCTION DE L'ÉTAT
            body_vector = np.array([
                body_state["battery_level"],
                body_state["collision_impact"],
                body_state["gpu_temp"],
                0,0,0,0,0
            ])

            current_intention = shared_context["intention_vector"]
            state_vector = np.concatenate((current_vision, body_vector, current_intention))

            # 3. DÉCISION & ACTION
            action = brain.get_action(state_vector)
            real_angle = muscles.move(action[0])

            movement_cost = np.abs(action[0]) * 0.001
            body_state["battery_level"] -= movement_cost

            shared_context["last_action"] = f"Angle {real_angle}°"

            # 4. CURIOSITÉ & RÉCOMPENSE
            visual_change = np.linalg.norm(current_vision - long_term_vision)
            long_term_vision = (long_term_vision * 0.9) + (current_vision * 0.1)

            reward, _ = heart.get_reward(body_state, world_model_error=visual_change, social_signal=0.0)

            # 5. MÉMOIRE
            done = 0
            memory.add(state_vector, action, reward, state_vector, done)

            # AFFICHAGE
            if step % 10 == 0:
                thought = cortex.last_thought.split("->")[-1].strip()
                bat_pct = int(body_state['battery_level'] * 100)
                bat_bar = "█" * (bat_pct // 10)

                print(f"\r[{step}] Vie:{bat_bar} ({bat_pct}%) | {energy_status} | Pensée:[{thought}] | Angle:{real_angle} | Lum:{brightness:.2f} | Rwd:{reward:.2f}", end="")

            step += 1
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\n--- SOMMEIL FORCÉ ---")
        memory.save("memoire_vie_1.pkl")
    finally:
        eye.release()

if __name__ == "__main__":
    life_cycle()