import zmq
import time

class MotorCortex:
    def __init__(self, mock=False):
        self.mock = mock
        if not self.mock:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.PUB)

            # Trouver l'IP Windows (comme pour la vision)
            windows_ip = "127.0.0.1"
            try:
                import os
                stream = os.popen("ip route list default | awk '{print $3}'")
                host_ip = stream.read().strip()
                if host_ip: windows_ip = host_ip
            except: pass

            # On force l'IP manuelle si vous aviez dû le faire pour la vision !
            # windows_ip = "172.xx.xx.xx"

            print(f"Connexion aux muscles sur {windows_ip}:5556")
            self.socket.connect(f"tcp://{windows_ip}:5556")
        else:
            print("MotorCortex: Mode MOCK activé (Pas de connexion hardware)")

    def move(self, action_value):
        """
        Transforme l'action du réseau de neurones (-1.0 à 1.0) en angle Moteur (10° à 170°).
        Note: L'Arduino traduit ces angles en pas (Stepper) de façon transparente.
        """
        # Mapping : -1 -> 10°, 0 -> 90°, 1 -> 170°
        angle = int(90 + (action_value * 80))

        # Clamp par sécurité
        angle = max(10, min(170, angle))

        if not self.mock:
            # Envoi
            self.socket.send_string(str(angle))

        return angle