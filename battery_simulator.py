import socket
import time
import json
import random

HOST = '127.0.0.1'
PORT = 7000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    print("Symulator oczekuje na połączenie...")
    conn, addr = server_socket.accept()
    with conn:
        print(f"Nawiązano połączenie z {addr}")
        while True:
            battery_data = {
                "state_of_charge": round(random.uniform(0, 100), 2),  
                "battery_state": random.choice(["NORMAL", "WARNING", "ERROR", "CRITICAL"]),
                "output_current": round(random.uniform(0, 10), 2),  
                "efuse_state": random.randint(0, 1),
                "balance_status": random.randint(0, 5),
                "error_detection": random.randint(0, 3),
                "temperatures": [round(random.uniform(20, 40), 1) for _ in range(8)],
                "voltages": [round(random.uniform(3.0, 4.2), 3) for _ in range(8)]
            }
            message = json.dumps(battery_data) + "\n"
            conn.sendall(message.encode('utf-8'))
            time.sleep(1)
