import sys
import threading
import time
import json
import PySimpleGUI as sg
import serial
from serial import SerialException
from serial.tools import list_ports
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

def find_usb_port():
    """Funkcja do automatycznego wykrywania dostępnego portu USB."""
    ports = list_ports.comports()
    for port in ports:
        if "USB" in port.description or "ACM" in port.device:
            return port.device
    return None

def read_usb_data(serial_port, data_queue):
    while True:
        if serial_port and serial_port.in_waiting > 0:
            try:
                line = serial_port.readline().decode('utf-8').strip()
                data = json.loads(line)  # Parsowanie danych JSON
                data_queue.append(data)  # Dodanie danych do kolejki
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")  # Błąd parsowania JSON
            except Exception as e:
                print(f"USB Read Error: {e}")  # Inne błędy
        time.sleep(0.1)

def send_usb_command(serial_port, command):
    if serial_port:
        try:
            serial_port.write(f"{command}\n".encode('utf-8'))
        except Exception as e:
            print(f"USB Write Error: {e}")

#Ustawienie portu do symulacji
port = 'socket://127.0.0.1:7000'
try:
    serial_port = serial.serial_for_url(port, baudrate=9600, timeout=1)
    print(f"Connected to virtual port: {port}")
except SerialException as e:
    print(f"Failed to connect to virtual port: {e}")
    serial_port = None

# Automatyczne wykrywanie portu USB
"""
port = find_usb_port()
if port:
    try:
        serial_port = serial.Serial(
            port=port,
            baudrate=9600,
            timeout=1
        )
        print(f"Connected to USB port: {port}")
    except SerialException as e:
        print(f"Failed to connect to USB port: {e}")
        serial_port = None
else:
    print("No USB port detected.")
    serial_port = None
"""

# Kolejka danych z USB
data_queue = []

# Uruchom wątek do odczytu USB tylko jeśli port został otwarty
if serial_port:
    usb_thread = threading.Thread(target=read_usb_data, args=(serial_port, data_queue), daemon=True)
    usb_thread.start()

# Layout GUI
layout = [
    [
        sg.Column([
            [sg.Text("Battery LV Monitor", font=("Helvetica", 24))]
        ], justification="left", pad=((20, 0), (20, 0))),
        sg.Image("putm_logo.png", size=(130, 130), pad=((20, 0), (0, 0)))
    ],
    [
        sg.Text("Battery State:", font=("Helvetica", 14)), sg.Text("-", size=(10, 1), key="-BATTERY-STATE-", font=("Helvetica", 14))
    ],
    [
        sg.Text("SOC:", font=("Helvetica", 14)), sg.Text("-", size=(10, 1), key="-SOC-", font=("Helvetica", 14)), sg.Text("%", font=("Helvetica", 14))
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
window = sg.Window("Battery LV Monitor", layout, resizable=True)

try:
    while True:
        event, values = window.read(timeout=100)

        if event in (sg.WIN_CLOSED, "Exit"):
            break

        elif event == "BB_Start":
            send_usb_command(serial_port, "BB_Start\n")

        elif event == "BB_Stop":
            send_usb_command(serial_port, "BB_Stop\n")

        elif event == "ED_ON":
            send_usb_command(serial_port, "ED_ON\n")

        elif event == "ED_OFF":
            send_usb_command(serial_port, "ED_OFF\n")

        # Aktualizacja danych z USB
        if data_queue:
            latest_data = data_queue.pop(0)
            window["-SOC-"].update(f"{latest_data.get('state_of_charge', '-'):.2f}")  # state_of_charge zamiast soc
            window["-BATTERY-STATE-"].update(latest_data.get('battery_state', '-'))
            window["-CURRENT-"].update(f"{latest_data.get('output_current', '-'):.2f}")  # output_current zamiast current
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