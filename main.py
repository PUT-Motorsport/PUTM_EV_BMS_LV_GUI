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
    voltages: List[float] = None
    temperatures: List[float] = None
    soc: float = 0.0
    efuse_state: int = 0
    balance_status: int = 0
    error_detection: int = 0

    def __post_init__(self):
        if self.temperatures is None:
            self.temperatures = [0.0] * 8
        if self.voltages is None:
            self.voltages = [0.0] * 8

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
    [
        sg.Image("putm_logo.png", size=(150, 150), pad=((0, 20), (0, 0))),
        sg.Text("Battery Monitoring System", font=("Helvetica", 24), pad=((50, 0), (0, 0)))
    ],
    [
        sg.Text("SOC:", font=("Helvetica", 14)), sg.Text("-", size=(10, 1), key="-SOC-", font=("Helvetica", 14)), sg.Text("%", font=("Helvetica", 14)),
        sg.Text("Battery State:", font=("Helvetica", 14)), sg.Text("-", size=(10, 1), key="-BATTERY-STATE-", font=("Helvetica", 14))
    ],
    [
        sg.Frame("Temperatures", [
            [sg.Text(f"T{i}", size=(5, 1), font=("Helvetica", 12)), sg.Text("-", size=(8, 1), key=f"-TEMP-{i}-", font=("Helvetica", 12))] for i in range(8)
        ], element_justification="center", title_color="blue", font=("Helvetica", 14)),
        sg.Frame("Voltages", [
            [sg.Text(f"V{i}", size=(5, 1), font=("Helvetica", 12)), sg.Text("-", size=(8, 1), key=f"-VOLT-{i}-", font=("Helvetica", 12))] for i in range(8)
        ], element_justification="center", title_color="blue", font=("Helvetica", 14))
    ],
    [sg.Text("Output current:", font=("Helvetica", 14)), sg.Text("-", size=(10, 1), key="-CURRENT-", font=("Helvetica", 14)), sg.Text("A", font=("Helvetica", 14))],
    [sg.Text("EFUSE state:", font=("Helvetica", 14)), sg.Text("-", size=(10, 1), key="-EFUSE-STATE-", font=("Helvetica", 14))],
    [sg.Text("Balance Status:", font=("Helvetica", 14)), sg.Text("-", size=(10, 1), key="-BALANCE-STATUS-", font=("Helvetica", 14))],
    [sg.Text("Error Detection:", font=("Helvetica", 14)), sg.Text("-", size=(10, 1), key="-ERROR-DETECTION-", font=("Helvetica", 14))],
    [
        sg.Button("BB_Start", font=("Helvetica", 12)), 
        sg.Button("BB_Stop", font=("Helvetica", 12)), 
        sg.Button("ED_ON", font=("Helvetica", 12)), 
        sg.Button("ED_OFF", font=("Helvetica", 12)), 
        sg.Button("Exit", font=("Helvetica", 12))
    ]
]

# Okno GUI
window = sg.Window("Battery Monitor", layout, resizable=True)

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
            window["-SOC-"].update(f"{latest_data.get('soc', '-'):.2f}")
            window["-BATTERY-STATE-"].update(latest_data.get('battery_state', '-'))
            window["-CURRENT-"].update(f"{latest_data.get('current', '-'):.2f}")
            window["-EFUSE-STATE-"].update(latest_data.get('efuse_state', '-'))
            window["-BALANCE-STATUS-"].update(latest_data.get('balance_status', '-'))
            window["-ERROR-DETECTION-"].update(latest_data.get('error_detection', '-'))

            for i in range(8):
                window[f"-TEMP-{i}-"].update(f"{latest_data['temperatures'][i]:.0f}")
                window[f"-VOLT-{i}-"].update(f"{latest_data['voltages'][i]:.3f}")

finally:
    window.close()
    if serial_port:
        serial_port.close()
