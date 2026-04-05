import time
import numpy as np
import torch
import cv2
import threading
import sys

import serial
import serial.tools.list_ports

# Import des organes
from sensory.vision import VisionModule
from sensory.audio_brain import AudioEar
from core.biological_reward import RewardSystem
from core.reflex_policy import ReflexActor
from core.world_model import WorldModel
from core.memory import ReplayBuffer
from core.motor import MotorCortex
from core.cortex import Cortex
from core.models import SomatosensoryEncoder, VisionEncoder, AudioEncoder, IntentionEncoder

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

def find_arduino_port():
    """Tries to automatically detect an Arduino or CH340 port."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        description = port.description.lower()
        if "arduino" in description or "ch340" in description:
            return port.device
    return "COM3" # Fallback

def life_cycle():
    print("--- EVOLUTION : ARCHITECTURE MODULAIRE (ENCODEURS SENSORIELS) ---")

    # 1. Connexions Sensorielles Périphériques (Brain Stem)
    arduino_port = find_arduino_port()
    arduino_serial = None
    try:
        arduino_serial = serial.Serial(arduino_port, 115200, timeout=1)
        print(f"  [V] Brain Stem : Connecté sur {arduino_port}")
        time.sleep(2) # Attendre reset
    except Exception as e:
        print(f"  [X] Brain Stem : Impossible de se connecter à {arduino_port} ({e}). Simulation activée.")

    # 2. Initialisation des Encodeurs Modulaires
    somatosensory = SomatosensoryEncoder(input_dim=7, output_dim=64) # P, D, Proprio, etc... On peut adapter selon besoin
    somatosensory.eval()

    vision_enc = VisionEncoder(output_dim=64)
    audio_enc = AudioEncoder(output_dim=64)
    intention_enc = IntentionEncoder(input_dim=32, output_dim=64)
    intention_enc.eval()

    # 3. Connexion Motrice (Mock=True pour bypasser les moteurs cassés / par défaut)
    muscles = MotorCortex(mock=True)

    # 4. Configuration des Dimensions Neuronales
    EMBEDDING_DIM = 64
    NUM_LOBES = 4 # Somato, Vision, Audio, Intention
    STATE_DIM = EMBEDDING_DIM * NUM_LOBES # 64 * 4 = 256
    ACTION_DIM = 2

    print(f"  [i] Dimension Vectorielle Totale : {STATE_DIM}")

    print(f"  [i] Dimension Vectorielle Totale : {STATE_DIM}")

    # 5. Organes Cognitifs (Cervelet RL et Modèle du Monde)
    brain = ReflexActor(STATE_DIM, ACTION_DIM)
    brain.load_model("actor.pth")
    brain.eval() # On s'assure d'être en mode évaluation pour ne pas gaspiller de VRAM

    world_model = WorldModel(STATE_DIM, ACTION_DIM)
    world_model.load_model("world_model.pth")
    world_model.eval()

    heart = RewardSystem({})
    memory = ReplayBuffer(capacity=100_000, state_dim=STATE_DIM, action_dim=ACTION_DIM)

    # 6. Cortex (LLM)
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
    previous_embedding_state = None

    try:
        while True:
            # --- BOUCLE RAPIDE ---

            # 1. LECTURE DES CAPTEURS BRUTS (Brain Stem)
            raw_piezo = 0
            raw_dist = -1
            proprio_val = body_state["last_servo_pos"]

            if arduino_serial and arduino_serial.in_waiting > 0:
                try:
                    # Clear backlog so we only read the freshest data
                    arduino_serial.reset_input_buffer()
                    line = arduino_serial.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        parts = line.split('|')
                        data = {}
                        for part in parts:
                            if ':' in part:
                                key, val = part.split(':')
                                data[key] = float(val) # On cast en float

                        raw_piezo = data.get('P', 0)
                        raw_dist = data.get('D', -1)
                        # On pourrait extraire gyro ici
                except Exception as e:
                    pass

            # Nociception directe pour le métabolisme
            body_state["collision_impact"] = min(1.0, raw_piezo / 1023.0)

            # 2. ENCODAGE MODULAIRE

            # Somatosensoriel (Piezo, Dist, Proprio, + padding pour arriver à 7 ou autre dim choisie)
            # On met 7 valeurs pour coller au input_dim=7 de l'encodeur
            raw_somato = np.array([raw_piezo, raw_dist, proprio_val, body_state["battery_level"], body_state["gpu_temp"], 0.0, 0.0], dtype=np.float32)

            with torch.no_grad():
                # Encodage des 4 lobes
                emb_somato = somatosensory(raw_somato).cpu().numpy().flatten()
                emb_vision = vision_enc(None).cpu().numpy().flatten() # Placeholder
                emb_audio = audio_enc(None).cpu().numpy().flatten()   # Placeholder

                # Intention du cortex
                current_intention = shared_context["intention_vector"]
                emb_intention = intention_enc(current_intention).cpu().numpy().flatten()

                # Concaténation des embeddings (4 * 64 = 256)
                current_embedding_state = np.concatenate((emb_somato, emb_vision, emb_audio, emb_intention))

            # --- MÉTABOLISME ---
            body_state["battery_level"] -= 0.0001
            energy_status = "-- DRAIN --"
            body_state["battery_level"] = max(0.0, min(1.0, body_state["battery_level"]))
            shared_context["battery"] = body_state["battery_level"]

            # 3. DÉCISION & ACTION
            action = brain.get_action(current_embedding_state)

            cmd_speed = action[0] * 0.1
            body_state["last_servo_pos"] = np.clip(body_state["last_servo_pos"] + cmd_speed, 0.0, 1.0)

            motor_cmd = (body_state["last_servo_pos"] * 2) - 1.0
            real_angle = muscles.move(motor_cmd)

            body_state["battery_level"] -= (np.abs(cmd_speed) * 0.001)
            shared_context["last_action"] = f"Angle {real_angle}°"
            
            # 4. CURIOSITÉ & RÉCOMPENSE (Basée sur l'erreur du World Model)
            wm_error = 0.0
            if previous_embedding_state is not None:
                with torch.no_grad():
                    # Quelle était la prédiction du prochain état faite à l'étape t-1 ?
                    pred_next_state_tensor = world_model(
                        torch.tensor(previous_embedding_state, dtype=torch.float32).to(world_model.device),
                        torch.tensor(action, dtype=torch.float32).to(world_model.device)
                    )
                    pred_next_state = pred_next_state_tensor.cpu().numpy().flatten()

                    # L'erreur est la distance entre la réalité d'aujourd'hui et la prédiction d'hier
                    wm_error = float(np.linalg.norm(current_embedding_state - pred_next_state))

            reward, rwd_details = heart.get_reward(body_state, world_model_error=wm_error, social_signal=0.0)

            # 5. MÉMOIRE
            done = 0
            memory.add(current_embedding_state, action, reward, current_embedding_state, done)
            previous_embedding_state = current_embedding_state
            
            # AFFICHAGE
            if step % 10 == 0:
                thought = cortex.last_thought.split("->")[-1].strip()
                bat_pct = int(body_state['battery_level'] * 100)
                bat_bar = "█" * (bat_pct // 10)

                print(f"\r[{step}] Vie:{bat_bar} ({bat_pct}%) | Nociception:{body_state['collision_impact']:.2f} | Surprise:{wm_error:.2f} | Pensée:[{thought}] | Angle:{real_angle}", end="")

            step += 1
            # time.sleep(0.01) # La boucle est déjà ralentie par les inférences deep

    except KeyboardInterrupt:
        print("\n\n--- SOMMEIL FORCÉ ---")
        memory.save("memoire_vie_modulaire.pkl")
    finally:
        if arduino_serial:
            arduino_serial.close()

if __name__ == "__main__":
    life_cycle()
