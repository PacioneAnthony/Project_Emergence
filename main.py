import time
import numpy as np
import torch
import cv2
import threading
import sys

# Import des organes
from sensory.vision import VisionModule
from sensory.audio_brain import AudioEar
from core.biological_reward import RewardSystem
from core.reflex_policy import ReflexActor
from core.memory import ReplayBuffer
from core.motor import MotorCortex
from core.cortex import Cortex

# --- CONTEXTE PARTAGÉ (Thread Safe) ---
shared_context = {
    "battery": 1.0,
    "vision_status": "Rien",
    "audio_status": "Silence",
    "last_action": "Aucune",
    "intention_vector": np.zeros(32)
}

def cortex_process(cortex_brain):
    """
    Le Système 2 (Lent - LLM).
    Il observe le monde via le texte et oriente le Système 1 via l'intention.
    """
    print("  [V] Cortex (Llama 3) : Démarré en arrière-plan")

    while True:
        # 1. Lire la situation
        situation_text = (
            f"Batterie: {int(shared_context['battery']*100)}%. "
            f"Vue: {shared_context['vision_status']}. "
            f"Ouïe: {shared_context['audio_status']}. "
            f"Action: {shared_context['last_action']}."
        )

        # 2. Réfléchir (Lent)
        strategy = cortex_brain.think(situation_text)

        # 3. Orienter
        shared_context["intention_vector"] = cortex_brain.get_intention()

        time.sleep(0.1)

def life_cycle():
    print("--- EVOLUTION : ARCHITECTURE MULTIMODALE ---")

    # 1. Connexions Sensorielles
    try:
        # A. Vision (128 dims)
        eye = VisionModule(output_dim=128)
        eye.load_adapter("vision_adapter.pth")
        print("  [V] Vision : OK")

        # B. Ouïe (64 dims)
        ear = AudioEar(model_size="base", output_dim=64)
        ear.load_adapter("ear_adapter.pth")
        print("  [V] Ouïe : OK")

    except Exception as e:
        print(f"  [X] Erreur Sensorielle : {e}")
        return

    # 2. Connexion Motrice (Mock=False pour le vrai robot)
    muscles = MotorCortex(mock=False)

    # 3. Configuration des Dimensions Neuronales
    VISION_DIM = 128
    AUDIO_DIM = 64
    BODY_DIM = 8   # Batterie, Choc, Temp, Proprioception(5)
    INTENTION_DIM = 32

    STATE_DIM = VISION_DIM + AUDIO_DIM + BODY_DIM + INTENTION_DIM # 128+64+8+32 = 232
    ACTION_DIM = 2

    print(f"  [i] Dimension Vectorielle Totale : {STATE_DIM}")

    # 4. Organes Cognitifs (Cervelet RL)
    brain = ReflexActor(STATE_DIM, ACTION_DIM)
    try:
        brain.load_model("actor.pth")
        print("  [V] Cervelet : Chargé (Attention aux dimensions !)")
    except:
        print("  [i] Cervelet : Nouveau né (Entraînement à zéro)")

    heart = RewardSystem({})
    memory = ReplayBuffer(capacity=100_000, state_dim=STATE_DIM, action_dim=ACTION_DIM)

    # 5. Cortex (LLM)
    cortex = Cortex()

    print("--- NAISSANCE ---")

    mind_thread = threading.Thread(target=cortex_process, args=(cortex,), daemon=True)
    mind_thread.start()

    # État corporel initial
    body_state = {
        "battery_level": 1.0,
        "collision_impact": 0.0,
        "gpu_temp": 0.4,
        "last_servo_pos": 0.5 # Milieu (0.0 - 1.0)
    }

    step = 0

    # Mémoire court-terme pour la curiosité
    long_term_vision = np.zeros(VISION_DIM)
    long_term_audio = np.zeros(AUDIO_DIM)

    # Fake audio buffer (silence) pour l'instant si pas de micro physique
    # Dans une vraie implémentation, il faudrait un thread qui record le micro en boucle
    # Pour ce MVP, on passe des zéros ou on suppose que 'ear.listen' gère l'audio entrant
    fake_audio_buffer = np.zeros(16000)

    try:
        while True:
            # --- BOUCLE RAPIDE (60Hz visé, réaliste 10-20Hz avec Vision+Audio) ---

            # 1. PERCEPTION
            # A. Vision
            latent_vision, frame, brightness, detection_list = eye.get_latent_vector()

            # B. Audio (Ici on simule un buffer vide ou on capture si implementé)
            # TODO: Brancher le vrai flux audio micro ici.
            latent_audio, volume, speech_text = ear.listen(fake_audio_buffer)

            # Mise à jour Contexte Sémantique (pour le LLM)
            vis_txt = ", ".join(detection_list) if detection_list else "Rien"
            aud_txt = f"Volume {int(volume*100)}%" + (f" ('{speech_text}')" if speech_text else "")

            shared_context["vision_status"] = vis_txt
            shared_context["audio_status"] = aud_txt

            # --- MÉTABOLISME ---

            # On cherche "person" ou "cat" ou "dog" dans les tags YOLO pour la recharge sociale
            is_social = any("person" in d for d in detection_list)
            current_strategy = cortex.active_strategy

            if is_social and current_strategy == "FOCUS":
                body_state["battery_level"] += 0.002
                energy_status = "++ CHARGE ++"
            else:
                body_state["battery_level"] -= 0.0001
                energy_status = "-- DRAIN --"

            body_state["battery_level"] = max(0.0, min(1.0, body_state["battery_level"]))
            shared_context["battery"] = body_state["battery_level"]

            # 2. CONSTRUCTION DE L'ÉTAT (PROPRIOCEPTION)

            # Proprioception : Où sont mes moteurs ?
            # Slot 4 (index 3) du vecteur corps
            proprio_val = body_state["last_servo_pos"]

            body_vector = np.array([
                body_state["battery_level"],
                body_state["collision_impact"],
                body_state["gpu_temp"],
                proprio_val, # <--- JE SAIS OÙ JE REGARDE
                0,0,0,0
            ])

            current_intention = shared_context["intention_vector"]

            # Concaténation Multimodale
            state_vector = np.concatenate((latent_vision, latent_audio, body_vector, current_intention))

            # 3. DÉCISION & ACTION
            action = brain.get_action(state_vector)

            # L'action est entre -1 et 1.
            # On met à jour la proprioception estimée (car on n'a pas de retour codeur sur les servos bon marché)
            # Nouvelle pos = Ancienne pos + Vitesse
            cmd_speed = action[0] * 0.1 # Vitesse max par tick
            body_state["last_servo_pos"] = np.clip(body_state["last_servo_pos"] + cmd_speed, 0.0, 1.0)

            # Commande moteur réelle (On map 0.0-1.0 vers -1.0-1.0 pour le MotorCortex existant)
            # Rappel: MotorCortex attend -1..1 pour mapper vers 10°..170°
            motor_cmd = (body_state["last_servo_pos"] * 2) - 1.0
            real_angle = muscles.move(motor_cmd)

            # Coût énergétique du mouvement
            body_state["battery_level"] -= (np.abs(cmd_speed) * 0.001)

            shared_context["last_action"] = f"Angle {real_angle}°"

            # 4. CURIOSITÉ & RÉCOMPENSE
            # On est curieux si la Vision OU l'Audio change
            vis_change = np.linalg.norm(latent_vision - long_term_vision)
            aud_change = np.linalg.norm(latent_audio - long_term_audio)

            long_term_vision = (long_term_vision * 0.9) + (latent_vision * 0.1)
            long_term_audio = (long_term_audio * 0.9) + (latent_audio * 0.1)

            total_surprise = vis_change + aud_change

            reward, _ = heart.get_reward(body_state, world_model_error=total_surprise, social_signal=0.0)

            # 5. MÉMOIRE
            done = 0
            memory.add(state_vector, action, reward, state_vector, done)

            # AFFICHAGE
            if step % 10 == 0:
                thought = cortex.last_thought.split("->")[-1].strip()
                bat_pct = int(body_state['battery_level'] * 100)
                bat_bar = "█" * (bat_pct // 10)

                print(f"\r[{step}] Vie:{bat_bar} ({bat_pct}%) | {energy_status} | Pensée:[{thought}] | Angle:{real_angle} | Rwd:{reward:.2f} | Vis:{vis_txt}", end="")

            step += 1
            # time.sleep(0.01) # La boucle est déjà ralentie par les inférences deep

    except KeyboardInterrupt:
        print("\n\n--- SOMMEIL FORCÉ ---")
        memory.save("memoire_vie_multimodale.pkl")
    finally:
        eye.release()

if __name__ == "__main__":
    life_cycle()
