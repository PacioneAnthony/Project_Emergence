import cv2
import zmq
import time
import serial
import serial.tools.list_ports
import threading

# --- CONFIGURATION ---
ARDUINO_PORT = 'COM3' # <--- REMPLACEZ PAR VOTRE PORT (vérifiez dans l'IDE Arduino)
BAUD_RATE = 9600

print("--- CORPS (WINDOWS) : INITIALISATION ---")

# 1. Connexion Arduino
arduino = None
try:
    arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    time.sleep(2) # Attendre le reboot de l'arduino
    print(f"[V] Arduino connecté sur {ARDUINO_PORT}")
except serial.SerialException:
    print(f"[X] Impossible d'ouvrir le port {ARDUINO_PORT}.")
    print("    Ports disponibles :")
    ports = serial.tools.list_ports.comports()
    for port in ports:
        print(f"    - {port.device} ({port.description})")
    print("    -> Modifiez ARDUINO_PORT dans ce fichier si nécessaire.")
except Exception as e:
    print(f"[X] ERREUR ARDUINO GÉNÉRALE : {e}")

# 2. Réseau ZMQ
context = zmq.Context()

# CANAL VIDEO (PUB - Sortant vers Linux) - Port 5555
video_socket = context.socket(zmq.PUB)
video_socket.bind("tcp://0.0.0.0:5555")

# CANAL MOTEUR (SUB - Entrant depuis Linux) - Port 5556
motor_socket = context.socket(zmq.SUB)
motor_socket.bind("tcp://0.0.0.0:5556") # On écoute ce port
motor_socket.setsockopt_string(zmq.SUBSCRIBE, '')

print("[V] Réseau prêt (Vidéo:5555, Moteur:5556)")

# 3. Thread pour écouter les ordres moteurs (en parallèle de la vidéo)
def motor_listener():
    while True:
        try:
            # On reçoit un angle (string bytes) ex: b'90'
            command = motor_socket.recv(flags=zmq.NOBLOCK)
            angle_str = command.decode('utf-8')

            if arduino:
                # On envoie à l'Arduino avec un saut de ligne
                msg = f"{angle_str}\n"
                arduino.write(msg.encode())
                print(f"Moteur -> {angle_str}°")
        except zmq.Again:
            time.sleep(0.001) # Rien reçu, on attend un peu
        except Exception as e:
            print(f"Erreur Moteur: {e}")

# Lancement du thread moteur
t = threading.Thread(target=motor_listener, daemon=True)
t.start()

# 4. Boucle Vidéo (Main Thread)
cap = cv2.VideoCapture(0) # Vérifiez si c'est 0 ou 1 selon votre config précédente
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

try:
    while True:
        ret, frame = cap.read()
        if not ret: continue

        # Compression et envoi
        encoded, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        video_socket.send(buffer)

        cv2.imshow("CORPS (Vue + Moteurs)", frame)
        if cv2.waitKey(1) == ord('q'): break

except KeyboardInterrupt:
    pass
finally:
    if arduino: arduino.close()
    cap.release()
    cv2.destroyAllWindows()
