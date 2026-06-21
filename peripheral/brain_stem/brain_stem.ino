#include <Servo.h>
#include <Wire.h>

// EMG1 protocol constants. The matching host implementation is j0/protocol.py.
const uint8_t MAGIC_0 = 0xA5;
const uint8_t MAGIC_1 = 0x5A;
const uint8_t PROTOCOL_VERSION = 1;
const unsigned long SERIAL_BAUD = 115200;
const uint8_t MAX_RX_PAYLOAD = 32;

const uint8_t TYPE_DEVICE_HELLO = 0x01;
const uint8_t TYPE_IMU_SAMPLE = 0x10;
const uint8_t TYPE_RANGE_SAMPLE = 0x11;
const uint8_t TYPE_SERVO_STATE = 0x12;
const uint8_t TYPE_SYNC_REPLY = 0x20;
const uint8_t TYPE_ERROR = 0x7F;
const uint8_t TYPE_SET_SERVO = 0x80;
const uint8_t TYPE_SYNC_REQUEST = 0x81;
const uint8_t TYPE_E_STOP = 0x82;

const uint16_t STATUS_VALID = 1 << 0;
const uint16_t STATUS_TIMEOUT = 1 << 1;
const uint16_t STATUS_SATURATED = 1 << 2;
const uint16_t STATUS_IMU_PRESENT = 1 << 3;
const uint16_t STATUS_FAILSAFE = 1 << 4;

const uint32_t CAP_IMU = 1UL << 0;
const uint32_t CAP_ULTRASONIC = 1UL << 1;
const uint32_t CAP_PIEZO = 1UL << 2;
const uint32_t CAP_SERVO = 1UL << 3;
const uint32_t CAP_TIME_SYNC = 1UL << 4;

const uint8_t TRIG_PIN = 8;
const uint8_t ECHO_PIN = 9;
const uint8_t PIEZO_PIN = A0;
const uint8_t SERVO_PIN = 10;
const uint8_t IMU_ADDRESS = 0x68;

const uint16_t SERVO_MIN_CDEG = 1000;
const uint16_t SERVO_MAX_CDEG = 17000;
const uint16_t SERVO_NEUTRAL_CDEG = 9000;
const unsigned long COMMAND_TIMEOUT_MS = 1000;

const unsigned long IMU_PERIOD_US = 10000;   // 100 Hz
const unsigned long RANGE_PERIOD_US = 50000; // 20 Hz
const unsigned long HELLO_PERIOD_US = 5000000;
const unsigned long ECHO_TIMEOUT_US = 25000;

Servo neckServo;
bool servoAttached = false;
bool failsafeActive = true;
unsigned long lastCommandMs = 0;
uint16_t servoTargetCdeg = SERVO_NEUTRAL_CDEG;

bool imuPresent = false;
uint8_t imuWhoAmI = 0;
unsigned long lastImuUs = 0;
unsigned long lastHelloUs = 0;

enum RangeState { RANGE_IDLE, RANGE_TRIGGER_HIGH, RANGE_WAIT_RISE, RANGE_WAIT_FALL };
RangeState rangeState = RANGE_IDLE;
unsigned long rangeCycleStartedUs = 0;
unsigned long echoRiseUs = 0;
unsigned long lastRangeStartedUs = 0;

uint32_t helloSequence = 0;
uint32_t imuSequence = 0;
uint32_t rangeSequence = 0;
uint32_t servoSequence = 0;
uint32_t syncSequence = 0;
uint32_t errorSequence = 0;

uint8_t rxFrame[16 + MAX_RX_PAYLOAD + 2];
uint8_t rxIndex = 0;
uint8_t rxExpected = 0;

uint16_t crc16Update(uint16_t crc, uint8_t value) {
  crc ^= ((uint16_t)value) << 8;
  for (uint8_t bit = 0; bit < 8; ++bit) {
    crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
  }
  return crc;
}

uint16_t crc16(const uint8_t* data, uint16_t length) {
  uint16_t crc = 0xFFFF;
  for (uint16_t index = 0; index < length; ++index) {
    crc = crc16Update(crc, data[index]);
  }
  return crc;
}

void putU16(uint8_t* target, uint16_t value) {
  target[0] = (uint8_t)(value & 0xFF);
  target[1] = (uint8_t)(value >> 8);
}

void putI16(uint8_t* target, int16_t value) {
  putU16(target, (uint16_t)value);
}

void putU32(uint8_t* target, uint32_t value) {
  for (uint8_t index = 0; index < 4; ++index) target[index] = (uint8_t)(value >> (8 * index));
}

void putU64(uint8_t* target, uint64_t value) {
  for (uint8_t index = 0; index < 8; ++index) target[index] = (uint8_t)(value >> (8 * index));
}

uint16_t getU16(const uint8_t* source) {
  return (uint16_t)source[0] | ((uint16_t)source[1] << 8);
}

uint32_t getU32(const uint8_t* source) {
  uint32_t value = 0;
  for (uint8_t index = 0; index < 4; ++index) value |= ((uint32_t)source[index]) << (8 * index);
  return value;
}

uint64_t getU64(const uint8_t* source) {
  uint64_t value = 0;
  for (uint8_t index = 0; index < 8; ++index) value |= ((uint64_t)source[index]) << (8 * index);
  return value;
}

void sendPacket(uint8_t type, uint8_t flags, uint32_t sequence, uint32_t sourceTimeUs,
                const uint8_t* payload, uint16_t payloadLength) {
  uint8_t header[16];
  header[0] = MAGIC_0;
  header[1] = MAGIC_1;
  header[2] = PROTOCOL_VERSION;
  header[3] = type;
  header[4] = flags;
  header[5] = 0;
  putU16(header + 6, payloadLength);
  putU32(header + 8, sequence);
  putU32(header + 12, sourceTimeUs);

  uint16_t crc = 0xFFFF;
  for (uint8_t index = 2; index < sizeof(header); ++index) crc = crc16Update(crc, header[index]);
  for (uint16_t index = 0; index < payloadLength; ++index) crc = crc16Update(crc, payload[index]);

  Serial.write(header, sizeof(header));
  if (payloadLength) Serial.write(payload, payloadLength);
  uint8_t crcBytes[2];
  putU16(crcBytes, crc);
  Serial.write(crcBytes, sizeof(crcBytes));
}

void attachServoIfNeeded() {
  if (!servoAttached) {
    neckServo.attach(SERVO_PIN);
    servoAttached = true;
  }
}

void applyServoCdeg(uint16_t targetCdeg) {
  attachServoIfNeeded();
  servoTargetCdeg = targetCdeg;
  neckServo.write((int)((targetCdeg + 50) / 100));
}

void sendServoState(uint32_t commandSequence, uint16_t requestedCdeg, uint16_t status) {
  uint8_t payload[10];
  putU32(payload, commandSequence);
  putU16(payload + 4, requestedCdeg);
  putU16(payload + 6, servoTargetCdeg);
  putU16(payload + 8, status);
  sendPacket(TYPE_SERVO_STATE, 0, servoSequence++, micros(), payload, sizeof(payload));
}

void sendError(uint16_t code, uint16_t context) {
  uint8_t payload[4];
  putU16(payload, code);
  putU16(payload + 2, context);
  sendPacket(TYPE_ERROR, 0, errorSequence++, micros(), payload, sizeof(payload));
}

void sendHello() {
  uint8_t payload[18];
  putU32(payload, 0x31474D45UL); // "EMG1" in little-endian.
  uint32_t capabilities = CAP_ULTRASONIC | CAP_PIEZO | CAP_SERVO | CAP_TIME_SYNC;
  if (imuPresent) capabilities |= CAP_IMU;
  putU32(payload + 4, capabilities);
  putU16(payload + 8, 100);
  putU16(payload + 10, 20);
  putU16(payload + 12, SERVO_MIN_CDEG);
  putU16(payload + 14, SERVO_MAX_CDEG);
  payload[16] = imuWhoAmI;
  payload[17] = 2; // Firmware patch version.
  sendPacket(TYPE_DEVICE_HELLO, 0, helloSequence++, micros(), payload, sizeof(payload));
}

bool writeImuRegister(uint8_t address, uint8_t value) {
  Wire.beginTransmission(IMU_ADDRESS);
  Wire.write(address);
  Wire.write(value);
  return Wire.endTransmission(true) == 0;
}

bool readImuBytes(uint8_t address, uint8_t* target, uint8_t length) {
  Wire.beginTransmission(IMU_ADDRESS);
  Wire.write(address);
  if (Wire.endTransmission(false) != 0) return false;
  uint8_t received = Wire.requestFrom(IMU_ADDRESS, length, (uint8_t)true);
  if (received != length) return false;
  for (uint8_t index = 0; index < length; ++index) target[index] = Wire.read();
  return true;
}

void initializeImu() {
  uint8_t who = 0;
  imuPresent = readImuBytes(0x75, &who, 1);
  imuWhoAmI = who;
  if (!imuPresent) return;

  imuPresent = writeImuRegister(0x6B, 0x01); // Wake, PLL with X gyro.
  imuPresent = imuPresent && writeImuRegister(0x1A, 0x03); // DLPF.
  imuPresent = imuPresent && writeImuRegister(0x19, 0x09); // 100 Hz from 1 kHz.
  imuPresent = imuPresent && writeImuRegister(0x1B, 0x08); // Gyro +/-500 dps.
  imuPresent = imuPresent && writeImuRegister(0x1C, 0x08); // Accel +/-4 g.
}

void sampleImu(unsigned long nowUs) {
  uint8_t raw[14];
  int16_t values[6] = {0, 0, 0, 0, 0, 0};
  uint16_t status = 0;
  if (imuPresent && readImuBytes(0x3B, raw, sizeof(raw))) {
    values[0] = (int16_t)(((uint16_t)raw[0] << 8) | raw[1]);
    values[1] = (int16_t)(((uint16_t)raw[2] << 8) | raw[3]);
    values[2] = (int16_t)(((uint16_t)raw[4] << 8) | raw[5]);
    values[3] = (int16_t)(((uint16_t)raw[8] << 8) | raw[9]);
    values[4] = (int16_t)(((uint16_t)raw[10] << 8) | raw[11]);
    values[5] = (int16_t)(((uint16_t)raw[12] << 8) | raw[13]);
    status = STATUS_VALID | STATUS_IMU_PRESENT;
  }

  uint8_t payload[14];
  for (uint8_t index = 0; index < 6; ++index) putI16(payload + index * 2, values[index]);
  putU16(payload + 12, status);
  sendPacket(TYPE_IMU_SAMPLE, 0, imuSequence++, nowUs, payload, sizeof(payload));
}

void sendRangeSample(uint16_t distanceMm, uint16_t status, unsigned long nowUs) {
  uint8_t payload[8];
  putU16(payload, distanceMm);
  putU16(payload + 2, analogRead(PIEZO_PIN));
  putU16(payload + 4, servoTargetCdeg);
  if (failsafeActive) status |= STATUS_FAILSAFE;
  putU16(payload + 6, status);
  sendPacket(TYPE_RANGE_SAMPLE, 0, rangeSequence++, nowUs, payload, sizeof(payload));
}

void updateRangeSensor(unsigned long nowUs) {
  switch (rangeState) {
    case RANGE_IDLE:
      if ((unsigned long)(nowUs - lastRangeStartedUs) >= RANGE_PERIOD_US) {
        lastRangeStartedUs = nowUs;
        rangeCycleStartedUs = nowUs;
        digitalWrite(TRIG_PIN, HIGH);
        rangeState = RANGE_TRIGGER_HIGH;
      }
      break;
    case RANGE_TRIGGER_HIGH:
      if ((unsigned long)(nowUs - rangeCycleStartedUs) >= 10) {
        digitalWrite(TRIG_PIN, LOW);
        rangeState = RANGE_WAIT_RISE;
      }
      break;
    case RANGE_WAIT_RISE:
      if (digitalRead(ECHO_PIN) == HIGH) {
        echoRiseUs = nowUs;
        rangeState = RANGE_WAIT_FALL;
      } else if ((unsigned long)(nowUs - rangeCycleStartedUs) >= ECHO_TIMEOUT_US) {
        sendRangeSample(0xFFFF, STATUS_TIMEOUT, nowUs);
        rangeState = RANGE_IDLE;
      }
      break;
    case RANGE_WAIT_FALL:
      if (digitalRead(ECHO_PIN) == LOW) {
        unsigned long pulseUs = nowUs - echoRiseUs;
        uint32_t distanceMm = (pulseUs * 343UL) / 2000UL;
        if (distanceMm > 0xFFFEUL) distanceMm = 0xFFFEUL;
        sendRangeSample((uint16_t)distanceMm, STATUS_VALID, nowUs);
        rangeState = RANGE_IDLE;
      } else if ((unsigned long)(nowUs - echoRiseUs) >= ECHO_TIMEOUT_US) {
        sendRangeSample(0xFFFF, STATUS_TIMEOUT, nowUs);
        rangeState = RANGE_IDLE;
      }
      break;
  }
}

void processCommand(const uint8_t* frame, uint8_t length) {
  uint8_t type = frame[3];
  uint16_t payloadLength = getU16(frame + 6);
  uint32_t commandSequence = getU32(frame + 8);
  const uint8_t* payload = frame + 16;
  unsigned long receivedUs = micros();

  if (type == TYPE_SET_SERVO && payloadLength == 2) {
    uint16_t requested = getU16(payload);
    uint16_t applied = requested;
    uint16_t status = STATUS_VALID;
    if (applied < SERVO_MIN_CDEG) {
      applied = SERVO_MIN_CDEG;
      status |= STATUS_SATURATED;
    }
    if (applied > SERVO_MAX_CDEG) {
      applied = SERVO_MAX_CDEG;
      status |= STATUS_SATURATED;
    }
    failsafeActive = false;
    lastCommandMs = millis();
    applyServoCdeg(applied);
    sendServoState(commandSequence, requested, status);
    return;
  }

  if (type == TYPE_SYNC_REQUEST && payloadLength == 12) {
    lastCommandMs = millis();
    uint32_t token = getU32(payload);
    uint64_t hostSendNs = getU64(payload + 4);
    uint8_t reply[20];
    putU32(reply, token);
    putU64(reply + 4, hostSendNs);
    putU32(reply + 12, receivedUs);
    putU32(reply + 16, micros());
    sendPacket(TYPE_SYNC_REPLY, 0, syncSequence++, micros(), reply, sizeof(reply));
    return;
  }

  if (type == TYPE_E_STOP && payloadLength == 0) {
    failsafeActive = true;
    if (servoAttached) {
      neckServo.detach();
      servoAttached = false;
    }
    sendServoState(commandSequence, servoTargetCdeg, STATUS_FAILSAFE);
    return;
  }

  sendError(1, type);
}

void consumeSerialByte(uint8_t value) {
  if (rxIndex == 0) {
    if (value == MAGIC_0) rxFrame[rxIndex++] = value;
    return;
  }
  if (rxIndex == 1) {
    if (value == MAGIC_1) {
      rxFrame[rxIndex++] = value;
    } else {
      rxIndex = (value == MAGIC_0) ? 1 : 0;
      if (rxIndex == 1) rxFrame[0] = MAGIC_0;
    }
    return;
  }

  rxFrame[rxIndex++] = value;
  if (rxIndex == 16) {
    uint16_t payloadLength = getU16(rxFrame + 6);
    if (payloadLength > MAX_RX_PAYLOAD) {
      rxIndex = 0;
      rxExpected = 0;
      return;
    }
    rxExpected = (uint8_t)(16 + payloadLength + 2);
  }

  if (rxExpected && rxIndex == rxExpected) {
    uint16_t expectedCrc = getU16(rxFrame + rxExpected - 2);
    uint16_t actualCrc = crc16(rxFrame + 2, rxExpected - 4);
    if (rxFrame[2] == PROTOCOL_VERSION && rxFrame[5] == 0 && expectedCrc == actualCrc) {
      processCommand(rxFrame, rxExpected);
    }
    rxIndex = 0;
    rxExpected = 0;
  }
}

void processSerial() {
  while (Serial.available() > 0) consumeSerialByte((uint8_t)Serial.read());
}

void updateFailsafe(unsigned long nowMs) {
  if (!failsafeActive && (unsigned long)(nowMs - lastCommandMs) > COMMAND_TIMEOUT_MS) {
    failsafeActive = true;
    if (servoAttached) {
      neckServo.detach();
      servoAttached = false;
    }
    sendServoState(0xFFFFFFFFUL, servoTargetCdeg, STATUS_FAILSAFE);
  }
}

void setup() {
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);

  Serial.begin(SERIAL_BAUD);
  Wire.begin();
  Wire.setClock(400000UL);
  initializeImu();

  // Startup is passive: the servo remains detached until an explicit command.
  failsafeActive = true;
  lastCommandMs = millis();
  lastImuUs = micros();
  lastRangeStartedUs = micros() - RANGE_PERIOD_US;
  delay(50);
  sendHello();
  lastHelloUs = micros();
}

void loop() {
  processSerial();
  unsigned long nowUs = micros();
  unsigned long nowMs = millis();

  if ((unsigned long)(nowUs - lastImuUs) >= IMU_PERIOD_US) {
    lastImuUs += IMU_PERIOD_US;
    sampleImu(nowUs);
  }
  if ((unsigned long)(nowUs - lastHelloUs) >= HELLO_PERIOD_US) {
    lastHelloUs = nowUs;
    sendHello();
  }
  updateRangeSensor(nowUs);
  updateFailsafe(nowMs);
}
