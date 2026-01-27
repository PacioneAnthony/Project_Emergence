import torch
import os
import glob
from core.reflex_policy import ReflexActor, ReflexCritic
from core.memory import ReplayBuffer
from core.dreamer import Dreamer

# On a besoin d'instancier les modules sensoriels pour sauver leurs adaptateurs
from sensory.vision import VisionModule
from sensory.audio_brain import AudioEar

def night_cycle():
    print("--- DÉBUT DU SOMMEIL (CONSOLIDATION END-TO-END) ---")

    # 1. Configuration (Doit matcher main.py)
    VISION_DIM = 128
    AUDIO_DIM = 64
    BODY_DIM = 8
    INTENTION_DIM = 32

    STATE_DIM = VISION_DIM + AUDIO_DIM + BODY_DIM + INTENTION_DIM # 232
    ACTION_DIM = 2
    BATCH_SIZE = 32 # On réduit un peu car les vecteurs sont plus gros
    EPOCHS = 500 # Plus long car plus de choses à apprendre

    # 2. Chargement du corps (Réseaux de neurones)
    actor = ReflexActor(STATE_DIM, ACTION_DIM)
    critic = ReflexCritic(STATE_DIM, ACTION_DIM)

    # Chargement des adaptateurs sensoriels (partie "Deep")
    # Note : Le 'Dreamer' ne met pas encore à jour les couches convolutions (Whisper/Yolo sont gelés)
    # mais si on avait un adaptateur trainable, c'est ici qu'on le chargerait.
    # Pour l'instant, on se contente de charger l'Actor/Critic.
    # TODO futur: Backpropager l'erreur du Critic jusque dans l'adaptateur Visuel/Audio.

    try:
        actor.load_model("actor.pth")
        critic.load_model("critic.pth")
        print("[V] Cerveaux chargés.")
    except:
        print("[!] Nouveaux cerveaux (Reset ou 1ère fois).")

    # 3. Chargement des souvenirs
    memory = ReplayBuffer(capacity=100_000, state_dim=STATE_DIM, action_dim=ACTION_DIM)

    # On cherche le fichier mémoire le plus récent
    # Pattern : memoire_vie_*.pkl
    list_of_files = glob.glob('memoire_vie*.pkl')
    if list_of_files:
        latest_file = max(list_of_files, key=os.path.getctime)
        print(f"Chargement du fichier : {latest_file}")
        try:
            memory.load(latest_file)
        except Exception as e:
            print(f"Erreur chargement mémoire ({e}). Dimensions incompatibles ?")
            return
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
        if i % 50 == 0:
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

    # On sauvegarde aussi les adaptateurs sensoriels si on les avait entraînés (ici placeholder)
    # eye.save_adapter("vision_adapter.pth")
    # ear.save_adapter("ear_adapter.pth")

    print("Sommeil terminé. L'agent est prêt pour une nouvelle journée.")

if __name__ == "__main__":
    night_cycle()
