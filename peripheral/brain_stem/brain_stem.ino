#include <Wire.h>

const int MPU_ADDR = 0x68; // Adresse I2C du MPU-6050
const int PIEZO_PIN = A0;  // Broche analogique du Piezo
const int TRIG_PIN = 8;    // Broche Trig du HC-SR04
const int ECHO_PIN = 9;    // Broche Echo du HC-SR04
const unsigned long ULTRASONIC_TIMEOUT = 15000; // Timeout de 15ms (environ 2.5m)

void setup() {
  Serial.begin(115200);

  // Initialisation I2C et réveil du MPU-6050
  Wire.begin();
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); // Registre PWR_MGMT_1
  Wire.write(0);    // Mettre à zéro pour réveiller le capteur
  Wire.endTransmission(true);

  // Configuration des broches pour l'ultrason
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
}

void loop() {
  // 1. Lecture du Piezo
  int piezoValue = analogRead(PIEZO_PIN);

  // 2. Lecture de l'Ultrason (HC-SR04)
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, ULTRASONIC_TIMEOUT);
  // Calcul de la distance en cm, si duration == 0 c'est un timeout
  int distance = (duration == 0) ? -1 : duration * 0.034 / 2;

  // 3. Lecture des registres bruts du MPU-6050
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B); // On commence au registre 0x3B (ACCEL_XOUT_H)
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 14, true); // On demande 14 registres (Accel, Temp, Gyro)

  int16_t ax = Wire.read() << 8 | Wire.read(); // 0x3B & 0x3C
  int16_t ay = Wire.read() << 8 | Wire.read(); // 0x3D & 0x3E
  int16_t az = Wire.read() << 8 | Wire.read(); // 0x3F & 0x40
  int16_t temp = Wire.read() << 8 | Wire.read(); // 0x41 & 0x42 (on ignore temp)
  int16_t gx = Wire.read() << 8 | Wire.read(); // 0x43 & 0x44
  int16_t gy = Wire.read() << 8 | Wire.read(); // 0x45 & 0x46
  int16_t gz = Wire.read() << 8 | Wire.read(); // 0x47 & 0x48

  // 4. Formatage et envoi sur le port série
  Serial.print("P:"); Serial.print(piezoValue);
  Serial.print("|D:"); Serial.print(distance);
  Serial.print("|AX:"); Serial.print(ax);
  Serial.print("|AY:"); Serial.print(ay);
  Serial.print("|AZ:"); Serial.print(az);
  Serial.print("|GX:"); Serial.print(gx);
  Serial.print("|GY:"); Serial.print(gy);
  Serial.print("|GZ:"); Serial.println(gz);

  // Petit délai pour ne pas saturer le port série
  delay(10);
}
