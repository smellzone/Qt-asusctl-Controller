import subprocess
import sys
import ast
import glob
from PySide6.QtGui import (
    QIcon,
    QAction
)
from PySide6.QtWidgets import (
    QApplication, 
    QWidget,
    QComboBox,
    QVBoxLayout,
    QLabel,
    QSlider,
    QSystemTrayIcon,
    QMenu,
    QTabWidget,
    QMainWindow
)
from PySide6.QtCore import (
    Qt,
    QTimer,
    QSize
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        #Power State Poller
        self.dgpu_poller = QTimer(self)
        self.dgpu_poller.setInterval(500)
        self.dgpu_poller.timeout.connect(self.dgpu_poller_tick)
        self.dgpu_poller.start()

        self.setWindowTitle("Qt asusctl Controller")

        self.tabs = QTabWidget()

        self.tabs.addTab(self.createMainTab(), 'Main')
        self.tabs.addTab(self.createDataTab(), 'Data')

        #System Tray Stuff/Actions
        quit_action = QAction('Quit', self)
        show_action = QAction('Show Window', self)
        quit_action.triggered.connect(QApplication.instance().quit)
        show_action.triggered.connect(self.show)    
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_menu = QMenu()
        self.tray_menu.addAction(quit_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(show_action)
        self.tray_icon.setContextMenu(self.tray_menu)

        self.setCentralWidget(self.tabs)

    def createMainTab(self) -> QWidget: 
        def on_profile_changed(index):
            set_profile_current(profileCombo.currentText())
            print(f"Selected index: {index}, Text: {profileCombo.currentText()}")

        def on_charge_limit_change():
            set_battery_charge_limit(set_battery_charge_limit(chargeLimitSlider.value()))
            currentChargeLimit.setText(f'Charge Limit {get_battery_charge_limit()}%')
            print(f'Charge Limit Set to {self.chargeLimitSlider.value()}')

        def on_led_changed():
            set_led_current(ledCombo.currentText())
            print(f'Led setting now: {get_led_current()}')

        tab = QWidget()
        layout = QVBoxLayout(tab)

        #Labels
        currentProfileLabel = QLabel('Current Profile:')
        currentChargeLimitLabel = QLabel('Charge Limit:')
        currentLEDLabel = QLabel('Current LED Level:')

        #Actionable Items
        profileCombo = QComboBox()
        chargeLimitSlider = QSlider(Qt.Horizontal)
        ledCombo = QComboBox()
        
        #Setup Pulldowns
        for profile in get_profile_list():
            profileCombo.addItem(profile)
        for led_setting in ['off', 'low', 'med', 'high']:
            ledCombo.addItem(led_setting)
        profileCombo.currentIndexChanged.connect(on_profile_changed)
        
        #Get current state for profile pulldown
        profileIndex = profileCombo.findText(get_profile_current())
        profileCombo.setCurrentIndex(profileIndex)
        ledCombo.currentIndexChanged.connect(on_led_changed)
        
        #Get current state for led pulldown
        ledIndex = ledCombo.findText(get_led_current())
        ledCombo.setCurrentIndex(ledIndex)

        #Setup Charge Limit Slider
        chargeLimitSlider.setRange(0, 100)
        #Get current setting and set slider to position
        chargeLimitSlider.setValue(int(get_battery_charge_limit()))
        chargeLimitSlider.valueChanged.connect(on_charge_limit_change)

        #Apply Layout
        layout.addWidget(currentProfileLabel)
        layout.addWidget(profileCombo)
        layout.addWidget(currentChargeLimitLabel)
        layout.addWidget(chargeLimitSlider)
        layout.addWidget(currentLEDLabel)
        layout.addWidget(ledCombo)
        return tab
    
    def createDataTab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        powerState = QLabel()
        gpuTemp = QLabel()
        cpuTemp = QLabel()

        powerState.setObjectName('StateData')
        gpuTemp.setObjectName('GPUTemp')
        cpuTemp.setObjectName('CPUTemp')

        layout.addWidget(powerState)
        layout.addWidget(gpuTemp)
        layout.addWidget(cpuTemp)
        return tab


    def dgpu_poller_tick(self):
        #Update Data Tab
        target_powerState = self.tabs.findChild(QLabel, 'StateData')
        target_gpuTemp = self.tabs.findChild(QLabel, 'GPUTemp')
        target_cpuTemp = self.tabs.findChild(QLabel, 'CPUTemp')
        if target_powerState:
            target_powerState.setText(f'GPU Raw State: {get_dgpu_status()[1]}')
        if target_gpuTemp:
            target_gpuTemp.setText(f'GPU Temp: {get_dgpu_temp().strip()}°C')
        if target_cpuTemp:
            target_cpuTemp.setText(f'CPU Temp: {get_cpu_pack_temp()}°C')
        #Update Icon/State for Main
        if get_dgpu_status()[0] == 'Active':
            app.setWindowIcon(active_icon)
            self.tray_icon.setIcon(active_icon)
            self.tray_icon.setToolTip('Active')
            self.tray_icon.show()
        if get_dgpu_status()[0] == 'Unknown':
            app.setWindowIcon(confused_icon)
            self.tray_icon.setIcon(confused_icon)
            self.tray_icon.setToolTip('Unknown')
            self.tray_icon.show()            
        if get_dgpu_status()[0] == 'Idle':
            app.setWindowIcon(idle_icon)
            self.tray_icon.setIcon(idle_icon)
            self.tray_icon.setToolTip('Idle')
            self.tray_icon.show()
        if get_dgpu_status()[0] == 'Low Power':
            app.setWindowIcon(low_power_icon)
            self.tray_icon.setIcon(low_power_icon)
            self.tray_icon.setToolTip('Low Power')
            self.tray_icon.show()

def run_cmd(cmd: list, **kwargs) -> str:
    return subprocess.run(cmd, capture_output=True, text=True).stdout

def get_help():
    cmd = 'asusctl --help'
    print(run_cmd(cmd.split()))

def get_profile_list() -> list[str]:
    cmd = 'asusctl profile list'
    profile_list = run_cmd(cmd.split()).split('\n')
    del profile_list[-1]
    return profile_list

def get_profile_current():
    cmd = 'asusctl profile get'
    text = run_cmd(cmd.split())
    profile = text.partition('Active profile:')[2].splitlines()[0].strip()
    return profile

def set_profile_current(profile: str) -> None:
    cmd = f'asusctl profile set {profile.lower()}'
    run_cmd(cmd.split())

def get_battery_charge_limit() -> str:
    cmd = 'asusctl battery info'
    text = run_cmd(cmd.split())
    profile = text.partition('Current battery charge limit:')[2].splitlines()[0].strip()[:-1]
    return profile

def set_battery_charge_limit(limit: int) -> None:
    cmd = f"asusctl battery limit {str(limit)}"
    run_cmd(cmd.split())

def get_led_current() -> str:
    cmd = 'asusctl leds get'
    text = run_cmd(cmd.split())
    profile = text.partition('Current keyboard led brightness:')[2].splitlines()[0].strip().lower()
    return profile

def set_led_current(led: str) -> None:
    cmd = f'asusctl leds set {led}'
    run_cmd(cmd.split())

def get_cpu_pack_temp() -> int:
    files = glob.glob('/sys/class/hwmon/hwmon*/temp1_input')
    res = subprocess.run(['cat', files[0]], capture_output=True, text=True)
    return int(int(res.stdout.strip())/1000)

def get_dgpu_temp() -> str:
    cmd = 'nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader'
    text = f'{run_cmd(cmd.split())}'
    return text
    
def get_dgpu_status() -> str:
    cmd = "nvidia-smi --query-gpu=pstate --format=csv,noheader"
    text = run_cmd(cmd.split()).strip()
    match text:
        case 'P0':
            return ('Active', text)
        case 'P1':
            return ('Active', text)
        case 'P2':
            return ('Active', text)
        case 'P3':
            return ('Active', text)
        case 'P4':
            return ('Low Power', text)
        case 'P5':
            return ('Low Power', text)
        case 'P6':
            return ('Low Power', text)
        case 'P7':
            return ('Low Power', text)
        case 'P8':
            return ('Idle', text)
        case 'P9':
            return ('Idle', text)
        case 'P10':
            return ('Idle', text)
        case _:
            return ('Unknown', text)

if __name__ == "__main__":   
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    active_icon = QIcon('icons/active.png')
    confused_icon = QIcon('icons/confused.png')
    idle_icon = QIcon('icons/idle.png')
    low_power_icon = QIcon('icons/low_power.png')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())