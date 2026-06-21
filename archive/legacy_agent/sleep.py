import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import os
import time

# Import des organes cognitifs
from core.memory import ReplayBuffer
from core.world_model import WorldModel
from core.reflex_policy import ReflexActor

# --- CONFIGURATION ---
STATE_DIM = 256
ACTION_DIM = 2
BATCH_SIZE = 64
EPOCHS = 1000  # Nombre de "cycles de sommeil"
LEARNING_RATE = 0.001

def sleep_cycle():
    print("=== DÉMARRAGE DU CYCLE DE SOMMEIL (OFFLINE RL) ===")

    # 1. Chargement de la Mémoire (L'Hippocampe)
    memory = ReplayBuffer(capacity=100_000, state_dim=STATE_DIM, action_dim=ACTION_DIM)
    if os.path.exists("memoire_vie_modulaire.pkl"):
        memory.load("memoire_vie_modulaire.pkl")
        print(f"[i] Mémoire chargée : {memory.size} expériences rappelées.")
    else:
        print("[X] Erreur : Aucune mémoire trouvée. Laisse Jumbo vivre un peu d'abord !")
        return

    if memory.size < BATCH_SIZE:
        print("[X] Pas assez d'expériences pour dormir profondément (minimum 64).")
        return

    # 2. Réveil des Réseaux de Neurones
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[i] Rêves calculés sur : {device}")

    world_model = WorldModel(STATE_DIM, ACTION_DIM).to(device)
    actor = ReflexActor(STATE_DIM, ACTION_DIM).to(device)

    if os.path.exists("world_model.pth"):
        world_model.load_model("world_model.pth")
    if os.path.exists("actor.pth"):
        actor.load_model("actor.pth")

    # 3. Optimiseurs (Les architectes des synapses)
    wm_optimizer = optim.Adam(world_model.parameters(), lr=LEARNING_RATE)
    actor_optimizer = optim.Adam(actor.parameters(), lr=LEARNING_RATE)
    
    wm_criterion = nn.MSELoss() # Pour réduire l'erreur de prédiction

    print("\n--- PHASE DE SOMMEIL PROFOND ---")
    start_time = time.time()

    for epoch in range(1, EPOCHS + 1):
        # --- ÉCHANTILLONNAGE DES RÊVES ---
        # On pioche un souvenir au hasard
        state, action, reward, next_state, _ = memory.sample(BATCH_SIZE)
        
        state = torch.FloatTensor(state).to(device)
        action = torch.FloatTensor(action).to(device)
        reward = torch.FloatTensor(reward).to(device)
        next_state = torch.FloatTensor(next_state).to(device)

        # ---------------------------------------------------------
        # PHASE 1 : Entraînement du Modèle du Monde (Comprendre la Physique)
        # ---------------------------------------------------------
        predicted_next_state = world_model(state, action)
        wm_loss = wm_criterion(predicted_next_state, next_state)

        wm_optimizer.zero_grad()
        wm_loss.backward()
        wm_optimizer.step()

        # ---------------------------------------------------------
        # PHASE 2 : Entraînement de l'Acteur (Behavioral Cloning sur les succès)
        # ---------------------------------------------------------
        # On ne veut renforcer l'Actor que sur les souvenirs "positifs"
        # On trie le batch pour ne garder que les 25% des meilleures expériences
        reward_threshold = torch.quantile(reward, 0.75)
        good_experiences_idx = (reward >= reward_threshold).flatten()

        if good_experiences_idx.sum() > 0:
            good_states = state[good_experiences_idx]
            good_actions_real = action[good_experiences_idx]

            # Qu'aurait fait le Cervelet aujourd'hui dans cette situation ?
            predicted_actions = actor.forward(good_states)
            
            # On le force à imiter les bonnes actions du passé
            actor_loss = nn.MSELoss()(predicted_actions, good_actions_real)

            actor_optimizer.zero_grad()
            actor_loss.backward()
            actor_optimizer.step()
        else:
            actor_loss = torch.tensor(0.0)

        # --- AFFICHAGE DU RYTHME CÉRÉBRAL ---
        if epoch % 100 == 0:
            print(f"Cycle [{epoch}/{EPOCHS}] | Erreur du Monde: {wm_loss.item():.4f} | Ajustement Moteur: {actor_loss.item():.4f}")

    # 4. Fin du sommeil : Sauvegarde
    print("\n=== RÉVEIL DE JUMBO ===")
    print(f"Sommeil terminé en {time.time() - start_time:.2f} secondes.")
    
    world_model.save_model("world_model.pth")
    actor.save_model("actor.pth")
    print("[V] Nouvelles connexions synaptiques sauvegardées.")

if __name__ == "__main__":
    sleep_cycle()