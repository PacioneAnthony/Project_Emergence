import serial
import time

# --- CONFIGURATION ---
# Vérifiez bien que c'est le même port que dans windows_body.py
ARDUINO_PORT = 'COM3' 
BAUD_RATE = 9600

print(f"--- TEST UNITAIRE SERVO SUR {ARDUINO_PORT} ---")

try:
    # 1. Ouverture de la connexion
    arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    
    # IMPORTANT : Quand on ouvre le port série, l'Arduino redémarre.
    # Il faut attendre 2 secondes qu'il soit prêt, sinon la première commande est perdue.
    print("Connexion établie. Attente initialisation Arduino (2s)...")
    time.sleep(2)
    
    print("Démarrage de la chorégraphie !")

    # 2. Boucle de test
    positions = [90, 10, 90, 170] # Milieu, Gauche, Milieu, Droite
    
    for angle in positions:
        print(f"Envoi ordre : {angle}°")
        
        # L'Arduino attend un texte suivi d'un saut de ligne (\n)
        command = f"{angle}\n"
        arduino.write(command.encode()) # On envoie les bytes
        
        time.sleep(1.0) # On laisse le temps au moteur de bouger

    print("Test terminé avec succès.")
    
except serial.SerialException:
    print(f"ERREUR : Impossible d'ouvrir {ARDUINO_PORT}.")
    print("Vérifiez que :'windows_body.py' est bien fermé et que le câble USB est branché.")
except Exception as e:
    print(f"Erreur : {e}")

finally:
    if 'arduino' in locals() and arduino.is_open:
        arduino.close()
        print("Connexion fermée.")