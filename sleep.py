import torch
import os
from core.reflex_policy import ReflexActor, ReflexCritic
from core.memory import ReplayBuffer
from core.dreamer import Dreamer
from sensory.vision_brain import DeepVision # <--- Import du nouvel oeil

def night_cycle():
    print("--- DÉBUT DU SOMMEIL (CONSOLIDATION) ---")
    
    # 1. Configuration
    VISION_DIM = 128 # <--- MISE À JOUR : 128 (Deep Vision) au lieu de 64
    BODY_DIM = 8
    INTENTION_DIM = 32
    
    STATE_DIM = VISION_DIM + BODY_DIM + INTENTION_DIM # = 168 maintenant
    ACTION_DIM = 2
    BATCH_SIZE = 64
    EPOCHS = 200 
    
    # 2. Chargement du corps (Réseaux de neurones)
    actor = ReflexActor(STATE_DIM, ACTION_DIM)
    critic = ReflexCritic(STATE_DIM, ACTION_DIM)
    
    # Chargement de la Vision (Pour sauvegarder l'adaptateur)
    # Note : Cela va tenter une connexion ZMQ, qui échouera si windows n'est pas là,
    # mais ce n'est pas grave, on veut juste l'objet pour sauvegarder les poids.
    print("Chargement du Cortex Visuel...")
    try:
        vision = DeepVision()
        vision.load_adapter("vision_adapter.pth")
    except Exception as e:
        print(f"Note: Vision chargée sans réseau ({e})")

    # Chargement Cerveau Moteur
    try:
        actor.load_model("actor.pth")
        critic.load_model("critic.pth")
    except:
        print("Cerveau moteur neuf.")
    
    # 3. Chargement des souvenirs
    memory = ReplayBuffer(capacity=100_000, state_dim=STATE_DIM, action_dim=ACTION_DIM)
    
    mem_file = "memoire_vie_1.pkl"
    if os.path.exists(mem_file):
        memory.load(mem_file)
    else:
        print("ERREUR : Pas de souvenirs trouvés !")
        return

    if memory.size < BATCH_SIZE:
        print(f"Pas assez de souvenirs ({memory.size}) pour apprendre.")
        return

    print(f"Souvenirs chargés : {memory.size} expériences.")

    # 4. Le Rêve (Entraînement)
    dreamer = Dreamer(actor, critic, lr=3e-4)
    
    print(f"Lancement de {EPOCHS} cycles de rêve paradoxal (REM)...")
    
    initial_loss = dreamer.train_step(memory, BATCH_SIZE)
    final_loss = 0
    
    for i in range(EPOCHS):
        loss = dreamer.train_step(memory, BATCH_SIZE)
        final_loss = loss
        if i % 20 == 0:
            print(f"  Cycle {i}/{EPOCHS} - Erreur Critique : {loss:.5f}")

    print(f"--- RÉSULTAT ---")
    print(f"Erreur initiale : {initial_loss:.5f}")
    print(f"Erreur finale   : {final_loss:.5f}")
    
    if final_loss < initial_loss:
        print("Gain : L'agent a structuré ses souvenirs !")
    else:
        print("Stagnation : Données bruitées ou apprentissage difficile.")

    # 5. Réveil (Sauvegarde des acquis)
    actor.save_model("actor.pth")
    critic.save_model("critic.pth")
    
    # On sauvegarde aussi l'adaptateur visuel (même s'il n'a pas changé cette nuit, 
    # c'est une bonne pratique pour ne pas le perdre).
    vision.save_adapter("vision_adapter.pth")
    
    print("Sommeil terminé. L'agent est prêt pour une nouvelle journée.")

if __name__ == "__main__":
    night_cycle()