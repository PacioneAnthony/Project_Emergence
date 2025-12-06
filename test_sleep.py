import numpy as np
import torch
from core.reflex_policy import ReflexActor, ReflexCritic
from core.memory import ReplayBuffer
from core.dreamer import Dreamer

# Config
STATE_DIM = 72
ACTION_DIM = 2

print("--- INITIALISATION ---")
actor = ReflexActor(STATE_DIM, ACTION_DIM)
critic = ReflexCritic(STATE_DIM, ACTION_DIM)
memory = ReplayBuffer(capacity=1000, state_dim=STATE_DIM, action_dim=ACTION_DIM)
dreamer = Dreamer(actor, critic)

print("Modules chargés sur", actor.device)

# 1. Phase Éveil (Remplissage rapide de la mémoire avec du bruit)
print("\n--- PHASE 1 : ÉVEIL (Collecte de données) ---")
for i in range(300): # On génère 300 souvenirs fictifs
    s = np.random.randn(STATE_DIM)
    a = np.random.uniform(-1, 1, ACTION_DIM)
    r = np.random.randn(1) # Récompense aléatoire
    ns = np.random.randn(STATE_DIM)
    d = 0
    memory.add(s, a, r, ns, d)
print(f"Mémoire remplie : {memory.size} expériences.")

# 2. Phase Sommeil (Entraînement)
print("\n--- PHASE 2 : SOMMEIL (Entraînement) ---")
print("Lancement des rêves (Gradient Descent sur GPU)...")

# On fait 50 cycles d'apprentissage (epochs)
losses = []
for epoch in range(50):
    loss = dreamer.train_step(memory, batch_size=32)
    losses.append(loss)
    if epoch % 10 == 0:
        print(f"  Rêve {epoch} : Critic Loss = {loss:.6f}")

print("\n--- RÉSULTAT ---")
print(f"Perte initiale : {losses[0]:.6f}")
print(f"Perte finale   : {losses[-1]:.6f}")

if losses[-1] < losses[0]:
    print("SUCCESS : L'agent apprend (l'erreur diminue) !")
else:
    print("NOTE : L'erreur peut varier sur des données aléatoires, mais le code tourne.")