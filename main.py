import sys
import threading
import time
import json
import PySimpleGUI as sg
import serial
from serial import SerialException
from dataclasses import dataclass
from typing import List

# Ustawienia GUI i portu szeregowego
sg.theme("Material2")

@dataclass
class BatteryData:
    current: float = 0.0
    voltage: float = 0.0
    temperature: float = 0.0
    soc: float = 0.0
    error_status: str = "No Errors"
    error_detection: bool = False

def read_uart_data(serial_port, data_queue):
    while True:
        if serial_port and serial_port.in_waiting > 0:
            try:
                line = serial_port.readline().decode('utf-8').strip()
                data = json.loads(line)
                data_queue.append(data)
            except Exception as e:
                print(f"UART Read Error: {e}")
        time.sleep(0.1)

def send_uart_command(serial_port, command):
    if serial_port:
        try:
            serial_port.write(f"{command}\n".encode('utf-8'))
        except Exception as e:
            print(f"UART Write Error: {e}")

# Próba inicjalizacji portu szeregowego
try:
    serial_port = serial.Serial(
        port="/dev/ttyACM0",  # Ustaw właściwy port
        baudrate=9600,
        timeout=1
    )
except SerialException as e:
    print(f"Serial port not available: {e}")
    serial_port = None

# Kolejka danych z UART
data_queue = []

# Uruchom wątek do odczytu UART tylko jeśli port został otwarty
if serial_port:
    uart_thread = threading.Thread(target=read_uart_data, args=(serial_port, data_queue), daemon=True)
    uart_thread.start()

# Layout GUI
layout = [
    [sg.Text("Battery Monitoring System", font=("Helvetica", 16))],
    [sg.Text("Current:"), sg.Text("-", size=(10, 1), key="-CURRENT-"), sg.Text("A")],
    [sg.Text("Voltage:"), sg.Text("-", size=(10, 1), key="-VOLTAGE-"), sg.Text("V")],
    [sg.Text("Temperature:"), sg.Text("-", size=(10, 1), key="-TEMPERATURE-"), sg.Text("°C")],
    [sg.Text("SOC:"), sg.Text("-", size=(10, 1), key="-SOC-"), sg.Text("%")],
    [sg.Text("Error Status:"), sg.Text("-", size=(20, 1), key="-ERROR-")],
    [sg.Text("Error Detection:"), sg.Text("-", size=(10, 1), key="-ERROR-DETECTION-")],
    [sg.Button("BB_Start"), sg.Button("BB_Stop"), sg.Button("ED_ON"), sg.Button("ED_OFF"), sg.Button("Exit")]
]

# Okno GUI
window = sg.Window("Battery Monitor", layout)

try:
    while True:
        event, values = window.read(timeout=100)

        if event in (sg.WIN_CLOSED, "Exit"):
            break

        elif event == "BB_Start":
            send_uart_command(serial_port, "BB_Start")

        elif event == "BB_Stop":
            send_uart_command(serial_port, "BB_Stop")

        elif event == "ED_ON":
            send_uart_command(serial_port, "ED_ON")

        elif event == "ED_OFF":
            send_uart_command(serial_port, "ED_OFF")

        # Aktualizacja danych z UART
        if data_queue:
            latest_data = data_queue.pop(0)
            window["-CURRENT-"].update(f"{latest_data.get('current', '-'):.2f}")
            window["-VOLTAGE-"].update(f"{latest_data.get('voltage', '-'):.2f}")
            window["-TEMPERATURE-"].update(f"{latest_data.get('temperature', '-'):.2f}")
            window["-SOC-"].update(f"{latest_data.get('soc', '-'):.2f}")
            window["-ERROR-"].update(latest_data.get('error_status', '-'))
            window["-ERROR-DETECTION-"].update("On" if latest_data.get('error_detection', False) else "Off")

finally:
    window.close()
    if serial_port:
        serial_port.close()
