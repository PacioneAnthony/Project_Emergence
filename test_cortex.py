import time
from core.cortex import Cortex

print("Initialisation du Cortex (Chargement Llama 3.2)...")
brain = Cortex()

# Scénario 1 : Tout va bien
print("\n--- TEST 1 : Situation Calme ---")
situation = "Batterie 80%. Je vois un mur blanc. Pas de mouvement."
decision = brain.think(situation)
print(f"Pensée : {brain.last_thought}")
print(f"Vecteur généré (extrait) : {brain.get_intention()[:5]}...")

# Scénario 2 : Danger
print("\n--- TEST 2 : Urgence ---")
situation = "ALERTE ! Batterie 5%. Choc détecté à gauche."
decision = brain.think(situation)
print(f"Pensée : {brain.last_thought}")

# Scénario 3 : Humain
print("\n--- TEST 3 : Social ---")
situation = "Batterie 60%. Humain détecté au centre. Visage reconnu."
decision = brain.think(situation)
print(f"Pensée : {brain.last_thought}")