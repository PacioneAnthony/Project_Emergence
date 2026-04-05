import torch
import torch.nn.functional as F
import torch.optim as optim

class Dreamer:
    def __init__(self, actor, critic, world_model=None, lr=1e-4):
        """
        Gère l'apprentissage (Mise à jour des poids).
        """
        self.actor = actor
        self.critic = critic
        self.world_model = world_model

        # Optimiseurs (Adam est le standard)
        self.actor_optimizer = optim.Adam(actor.parameters(), lr=lr)
        self.critic_optimizer = optim.Adam(critic.parameters(), lr=lr)

        if self.world_model is not None:
            self.wm_optimizer = optim.Adam(self.world_model.parameters(), lr=lr)

        self.gamma = 0.99 # Importance du futur (0.99 = on se soucie du long terme)
        self.device = actor.device

    def train_step(self, replay_buffer, batch_size=256):
        """
        Une étape d'entraînement (un rêve).
        """
        if replay_buffer.size < batch_size:
            if self.world_model is not None:
                return 0.0, 0.0
            return 0.0 # Pas assez de souvenirs pour apprendre

        # 1. On pioche des souvenirs au hasard
        state, action, reward, next_state, done = replay_buffer.sample(batch_size)

        # Conversion en Tenseurs GPU
        state = torch.FloatTensor(state).to(self.device)
        action = torch.FloatTensor(action).to(self.device)
        reward = torch.FloatTensor(reward).to(self.device)
        next_state = torch.FloatTensor(next_state).to(self.device)
        done = torch.FloatTensor(done).to(self.device)

        # --- MISE À JOUR DU CRITIQUE (Le Juge) ---
        # Le critique doit prédire la récompense réelle qu'on a eue

        with torch.no_grad():
            # Quelle action l'acteur ferait-il dans le futur ?
            next_action = self.actor(next_state)
            # Quelle note le critique donnerait-il à ce futur ?
            target_q = self.critic(next_state, next_action)
            # Objectif : Récompense immédiate + Futur (sauf si mort)
            target_q = reward + (1 - done) * self.gamma * target_q

        # Prédiction actuelle du critique
        current_q = self.critic(state, action)

        # Erreur du critique (MSE)
        critic_loss = F.mse_loss(current_q, target_q)

        # Rétropropagation (On corrige le critique)
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()

        # --- MISE À JOUR DE L'ACTEUR (L'Élève) ---
        # L'acteur doit choisir des actions qui plaisent au critique

        # L'acteur rejoue la scène
        new_action = self.actor(state)
        # Le critique note cette nouvelle action
        actor_loss = -self.critic(state, new_action).mean() # On veut maximiser la note (donc minimiser le négatif)

        # Rétropropagation (On corrige l'acteur)
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        self.actor_optimizer.step()

        # --- MISE À JOUR DU MODÈLE DU MONDE (Le Simulateur Mental) ---
        wm_loss_val = 0.0
        if self.world_model is not None:
            # Prédiction de l'état futur
            predicted_next_state = self.world_model(state, action)

            # Loss principale : MSE avec le vrai état futur
            mse_loss = F.mse_loss(predicted_next_state, next_state)

            # Régularisation Anti-Collapse (Hinge Loss sur la variance)
            # Force la variance sur la dimension du batch à s'approcher de 1 sans la dépasser
            std = torch.sqrt(torch.var(predicted_next_state, dim=0) + 1e-6)
            variance_loss = torch.mean(torch.relu(1.0 - std))

            # Loss totale du World Model
            loss_wm = mse_loss + 0.01 * variance_loss

            # Rétropropagation (On corrige le World Model)
            self.wm_optimizer.zero_grad()
            loss_wm.backward()
            self.wm_optimizer.step()

            wm_loss_val = loss_wm.item()

        if self.world_model is not None:
            return critic_loss.item(), wm_loss_val

        return critic_loss.item()