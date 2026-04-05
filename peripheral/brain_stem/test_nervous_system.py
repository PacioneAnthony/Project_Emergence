import serial
import serial.tools.list_ports
import time
import sys

DEFAULT_PORT = "COM3"
BAUD_RATE = 115200

def find_arduino_port():
    """Tries to automatically detect an Arduino or CH340 port."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        description = port.description.lower()
        if "arduino" in description or "ch340" in description:
            print(f"Auto-detected Arduino/CH340 on port: {port.device}")
            return port.device
    return None

def main():
    print("--- Emergence Peripheral Nervous System Test ---")
    port = find_arduino_port()

    if not port:
        print(f"Arduino not auto-detected. Falling back to DEFAULT_PORT: {DEFAULT_PORT}")
        port = DEFAULT_PORT

    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=1)
        print(f"Successfully connected to {port} at {BAUD_RATE} baud.")
        time.sleep(2) # Wait for Arduino to reset after serial connection
    except serial.SerialException as e:
        print(f"Failed to connect to {port}: {e}")
        print("Please check your connection or modify DEFAULT_PORT.")
        sys.exit(1)

    print("\nListening for sensory data... (Press Ctrl+C to stop)\n")
    print(f"{'PIEZO':<10} | {'DIST (cm)':<10} | {'ACCEL (X, Y, Z)':<25} | {'GYRO (X, Y, Z)':<25}")
    print("-" * 75)

    try:
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if not line:
                    continue

                # Expected format: P:10|D:45|AX:100|AY:-50|AZ:4000|GX:12|GY:-5|GZ:0
                try:
                    parts = line.split('|')
                    data = {}
                    for part in parts:
                        key, val = part.split(':')
                        data[key] = int(val)

                    p = data.get('P', 'N/A')
                    d = data.get('D', 'N/A')
                    ax, ay, az = data.get('AX', 'N/A'), data.get('AY', 'N/A'), data.get('AZ', 'N/A')
                    gx, gy, gz = data.get('GX', 'N/A'), data.get('GY', 'N/A'), data.get('GZ', 'N/A')

                    dist_str = "Timeout" if d == -1 else str(d)

                    accel_str = f"{ax}, {ay}, {az}"
                    gyro_str = f"{gx}, {gy}, {gz}"

                    print(f"{p:<10} | {dist_str:<10} | {accel_str:<25} | {gyro_str:<25}")

                except ValueError:
                    # Ignore malformed lines
                    pass

    except KeyboardInterrupt:
        print("\nTest stopped by user.")
    finally:
        ser.close()
        print("Serial connection closed.")

if __name__ == "__main__":
    main()
