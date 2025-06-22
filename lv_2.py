import json
import time
import threading
from dataclasses import dataclass

from dataclasses import dataclass
from typing import List


from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QHeaderView,
    
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import QTimer, Qt

IMAGE_PATH = "putm_logo.png"

# Słownik mapujący stany baterii na opisy
BATTERY_STATES = {
    0: "All good",
    1: "Charging",
    2: "Unbalanced (difference > 0.2V)",
    3: "Highest temperature > 48C",
    4: "Too low voltage",
    5: "Too high voltage",
    6: "Too high temperature",
    7: "Too high current",
    8: "Sleep mode"
}

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


def read_usb_data(serial_port, data_queue,exit_event):
    while not exit_event.is_set():
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
            print(f"LV Sending command: {command}")

        except Exception as e:
            print(f"LV write error: {e}")


class MainWindow(QMainWindow):
    def __init__(self,serial_port,read_queue,exit_event): 
        super().__init__()
        self.setWindowTitle("Battery LV Monitor")
        self.setFixedSize(500, 715) 

        self.serial_port = serial_port
        self.read_queue = read_queue
        self.exit_event = exit_event

        self.init_ui() 

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(100) 

    def feed_data(self, data):
        self.read_queue.clear()
        self.read_queue.append(data)


    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)


        image_label = QLabel()
        pixmap = QPixmap(IMAGE_PATH)
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(image_label)

        columns_layout = QHBoxLayout()
        main_layout.addLayout(columns_layout)

        centre_layout = QVBoxLayout()
        columns_layout.addLayout(centre_layout)


        battery_status_box = QGroupBox("")
        battery_status_layout = QGridLayout()
        battery_status_box.setLayout(battery_status_layout)

        battery_status_layout.addWidget(QLabel("Battery State:"), 0, 0)
        self.label_battery_state = QLabel("-")
        battery_status_layout.addWidget(self.label_battery_state, 0, 1)

        battery_status_layout.addWidget(QLabel("SOC:"), 1, 0)
        self.label_soc = QLabel("-")
        battery_status_layout.addWidget(self.label_soc, 1, 1)
        battery_status_layout.addWidget(QLabel("%"), 1, 2)

        centre_layout.addWidget(battery_status_box)

        #tabelka napięcia i temperatury
        table_box = QGroupBox("")
        table_layout = QVBoxLayout()
        table_box.setLayout(table_layout)

        self.table = QTableWidget()
        self.table.setRowCount(8)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Voltage (V)", "Temperature (°C)"])

        #wyrównanie
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers) 


        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, 25) #żeby nie takie wysokie te komórki były
        self.table.setVerticalHeaderLabels([str(i) for i in range(8)])


        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 120)

        table_layout.addWidget(self.table)
        centre_layout.addWidget(table_box)    

        #battery_status part 2   

        battery_status_2box = QGroupBox("")
        battery_status_2layout = QGridLayout()
        battery_status_2box.setLayout(battery_status_2layout)

        battery_status_2layout.addWidget(QLabel("Output Current:"), 2, 0)
        self.label_output_current = QLabel("-")
        battery_status_2layout.addWidget(self.label_output_current, 2, 1)
        battery_status_2layout.addWidget(QLabel("A"), 2, 2)

        battery_status_2layout.addWidget(QLabel("EFUSE state:"), 3, 0)
        self.label_efuse_state = QLabel("-")
        battery_status_2layout.addWidget(self.label_efuse_state, 3, 1)

        battery_status_2layout.addWidget(QLabel("Balance status:"), 4, 0)
        self.label_balance_status = QLabel("-")
        battery_status_2layout.addWidget(self.label_balance_status, 4, 1)

        battery_status_2layout.addWidget(QLabel("Error detection:"), 5, 0)
        self.label_eroor_detection = QLabel("-")
        battery_status_2layout.addWidget(self.label_eroor_detection, 5, 1)

        centre_layout.addWidget(battery_status_2box)

        #przyciski

        buttons_box = QGroupBox("")
        buttons_box_layout = QHBoxLayout() #QHBox jest zeby na dole w jednej linii QVBox zeby pod sobą się wyswietlały
        buttons_box.setLayout(buttons_box_layout)

        self.btn_BB_Start = QPushButton("BB Start")
        self.btn_BB_Start.clicked.connect(lambda: send_usb_command(self.serial_port, "BB_Start\n"))
        buttons_box_layout.addWidget(self.btn_BB_Start)

        self.btn_BB_Stop = QPushButton("BB Stop")
        self.btn_BB_Stop.clicked.connect(lambda: send_usb_command(self.serial_port, "BB_Stop\n"))
        buttons_box_layout.addWidget(self.btn_BB_Stop)

        self.btn_ED_on = QPushButton("ED on")
        self.btn_ED_on.clicked.connect(lambda: send_usb_command(self.serial_port, "ED_ON\n"))
        buttons_box_layout.addWidget(self.btn_ED_on)

        self.btn_ED_off = QPushButton("ED off")
        self.btn_ED_off.clicked.connect(lambda: send_usb_command(self.serial_port, "ED_OFF\n"))
        buttons_box_layout.addWidget(self.btn_ED_off)

        self.btn_exit = QPushButton("Exit")
        self.btn_exit.clicked.connect(self.handle_exit)
        buttons_box_layout.addWidget(self.btn_exit)

        centre_layout.addWidget(buttons_box)
    

    def handle_exit(self):
        self.exit_event.set()
        QApplication.instance().quit()

    def update_ui(self):
        """Aktualizuje dane UI na podstawie danych w kolejce."""
        if self.read_queue:
            latest_data = self.read_queue.pop(0) 

            self.label_battery_state.setText(BATTERY_STATES.get(latest_data.get('battery_state', 0), "Unknown state"))
            self.label_soc.setText(f"{latest_data.get('state_of_charge', '-'):.2f}")
            self.label_output_current.setText(f"{latest_data.get('output_current', '-'):.2f}")
            self.label_efuse_state.setText(f"{latest_data.get('efuse_state', '-')}")
            self.label_balance_status.setText(f"{latest_data.get('balance_status', '-')}")
            self.label_eroor_detection.setText(f"{latest_data.get('error_detection', '-')}")
            
            voltages = latest_data.get('voltages', [])
            temperatures = latest_data.get('temperatures', [])

            for i in range(8):
                voltage = voltages[i] if i < len(voltages) else 0.0
                temperature = temperatures[i] if i < len(temperatures) else 0.0

                self.table.setItem(i, 0, QTableWidgetItem(f"{voltage:.2f}"))
                self.table.setItem(i, 1, QTableWidgetItem(f"{temperature:.1f}"))
   

