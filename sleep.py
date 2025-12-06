import torch
import os
from core.reflex_policy import ReflexActor, ReflexCritic
from core.memory import ReplayBuffer
from core.dreamer import Dreamer

def night_cycle():
    print("--- DÉBUT DU SOMMEIL (CONSOLIDATION) ---")
    
    # 1. Configuration
    VISION_DIM = 64
    BODY_DIM = 8
    INTENTION_DIM = 32
    
    STATE_DIM = VISION_DIM + BODY_DIM + INTENTION_DIM # = 104
    ACTION_DIM = 2
    BATCH_SIZE = 64
    EPOCHS = 200 # Nombre de fois qu'il va "repenser" à sa journée
    
    # 2. Chargement du corps (Réseaux de neurones)
    actor = ReflexActor(STATE_DIM, ACTION_DIM)
    critic = ReflexCritic(STATE_DIM, ACTION_DIM)
    
    # On essaie de charger les cerveaux existants pour continuer l'apprentissage
    actor.load_model("actor.pth")
    critic.load_model("critic.pth")
    
    # 3. Chargement des souvenirs
    memory = ReplayBuffer(capacity=100_000, state_dim=STATE_DIM, action_dim=ACTION_DIM)
    
    # On cherche le fichier mémoire le plus récent ou spécifique
    mem_file = "memoire_vie_1.pkl"
    if os.path.exists(mem_file):
        memory.load(mem_file)
    else:
        print("ERREUR : Pas de souvenirs trouvés ! L'agent doit vivre avant de dormir.")
        return

    if memory.size < BATCH_SIZE:
        print(f"Pas assez de souvenirs ({memory.size}) pour apprendre. Il faut au moins {BATCH_SIZE}.")
        return

    print(f"Souvenirs chargés : {memory.size} expériences.")

    # 4. Le Rêve (Entraînement)
    dreamer = Dreamer(actor, critic, lr=3e-4) # lr = learning rate
    
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
        print("Stagnation : Données trop bruitées ou apprentissage difficile.")

    # 5. Réveil (Sauvegarde des acquis)
    actor.save_model("actor.pth")
    critic.save_model("critic.pth")
    print("Sommeil terminé. L'agent est prêt pour une nouvelle journée.")

if __name__ == "__main__":
    night_cycle()