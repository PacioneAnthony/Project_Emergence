#include <Servo.h>

Servo myServo;  // Création de l'objet servo
const int SERVO_PIN = 9; // Pin PWM où est branché le fil Orange/Jaune du servo
String inputString = "";         // Une chaîne pour stocker les données reçues
boolean stringComplete = false;  // Indique si la chaîne est complète

void setup() {
  // Initialisation Série
  Serial.begin(9600);

  // Attachement du servo
  myServo.attach(SERVO_PIN);

  // Position initiale (milieu)
  myServo.write(90);

  // Réserver de la mémoire pour la chaîne
  inputString.reserve(200);

  // Petit signal de vie (aller-retour rapide)
  delay(500);
  myServo.write(110);
  delay(200);
  myServo.write(70);
  delay(200);
  myServo.write(90);
}

void loop() {
  // Si on a reçu une commande complète (terminée par \n)
  if (stringComplete) {
    // Conversion en entier
    int angle = inputString.toInt();

    // Sécurité : bornes du servo (souvent 0-180, mais on peut limiter pour éviter de forcer)
    if (angle < 0) angle = 0;
    if (angle > 180) angle = 180;

    // Application de l'angle
    myServo.write(angle);

    // Reset pour la prochaine commande
    inputString = "";
    stringComplete = false;
  }
}

/*
  SerialEvent se déclenche automatiquement quand des données arrivent
  sur le port série matériel.
*/
void serialEvent() {
  while (Serial.available()) {
    // Récupérer le nouveau byte:
    char inChar = (char)Serial.read();

    // Si c'est une nouvelle ligne, on marque la fin
    if (inChar == '\n') {
      stringComplete = true;
    } else {
      // Sinon on ajoute au buffer
      inputString += inChar;
    }
  }
}
