import numpy as np
import pickle
import os

class ReplayBuffer:
    def __init__(self, capacity=100000, state_dim=72, action_dim=2):
        """
        Mémoire tampon circulaire (FIFO).
        capacity : nombre max de souvenirs (ex: 100 000 pas de temps)
        """
        self.capacity = capacity
        self.ptr = 0
        self.size = 0

        # On pré-alloue des tableaux numpy pour éviter la fragmentation mémoire
        self.state = np.zeros((capacity, state_dim))
        self.action = np.zeros((capacity, action_dim))
        self.reward = np.zeros((capacity, 1))
        self.next_state = np.zeros((capacity, state_dim))
        self.dead = np.zeros((capacity, 1)) # 1 si l'épisode est fini (mort/échec), 0 sinon

    def add(self, state, action, reward, next_state, dead):
        """
        Ajoute une expérience à la mémoire.
        """
        # On remplace les vieux souvenirs si la mémoire est pleine (pointeur circulaire)
        self.state[self.ptr] = state
        self.action[self.ptr] = action
        self.reward[self.ptr] = reward
        self.next_state[self.ptr] = next_state
        self.dead[self.ptr] = dead

        self.ptr = (self.ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, batch_size=256):
        """
        Pioche des souvenirs au hasard pour le rêve (entraînement).
        """
        ind = np.random.randint(0, self.size, size=batch_size)

        return (
            self.state[ind],
            self.action[ind],
            self.reward[ind],
            self.next_state[ind],
            self.dead[ind]
        )

    def save(self, filename="memory.pkl"):
        """Sauvegarde la mémoire sur le disque (pour ne pas tout oublier si on éteint le PC)"""
        with open(filename, 'wb') as f:
            pickle.dump({
                'state': self.state[:self.size],
                'action': self.action[:self.size],
                'reward': self.reward[:self.size],
                'next_state': self.next_state[:self.size],
                'dead': self.dead[:self.size],
                'ptr': self.ptr
            }, f)
        print(f"Mémoire sauvegardée : {self.size} expériences.")

    def load(self, filename="memory.pkl"):
        if not os.path.exists(filename):
            print("Aucune sauvegarde mémoire trouvée.")
            return
        
        with open(filename, 'rb') as f:
            data = pickle.load(f)
            
        load_size = len(data['state'])
        self.state[:load_size] = data['state']
        self.action[:load_size] = data['action']
        self.reward[:load_size] = data['reward']
        self.next_state[:load_size] = data['next_state']
        self.dead[:load_size] = data['dead']
        
        self.size = load_size
        self.ptr = data['ptr']
        print(f"Mémoire chargée : {self.size} expériences.")