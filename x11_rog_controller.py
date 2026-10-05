import subprocess
import sys
import ast
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QApplication, QWidget, QComboBox, QVBoxLayout, QLabel, QSlider, QSystemTrayIcon, QMenu
from PySide6.QtCore import Qt, QTimer, QSize

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Qt asusctl Controller")

        layout = QVBoxLayout(self)
        self.currentProfile = QLabel(f'Current Profile: {get_profile_current()}', self)
        self.currentChargeLimit = QLabel(f'Charge Limit: {get_battery_charge_limit()}%')
        self.chargeLimitSlider = QSlider(Qt.Horizontal)
        self.profileCombo = QComboBox()
        self.currentLed = QLabel(f'Keyboard Brightness: {get_led_current()}')
        self.ledCombo = QComboBox()
        self.dgpu_poller = QTimer(self)
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_menu = QMenu()
        quit_action = QAction('Quit', self)
        show_action = QAction('Show Window', self)

        quit_action.triggered.connect(QApplication.instance().quit)
        show_action.triggered.connect(self.show)

        self.tray_menu.addAction(quit_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(show_action)

        self.tray_icon.setContextMenu(self.tray_menu)

        for profile in get_profile_list():
            self.profileCombo.addItem(profile)
        for led_setting in ['off', 'low', 'med', 'high']:
            self.ledCombo.addItem(led_setting)
        self.profileCombo.currentIndexChanged.connect(self.on_profile_changed)
        profileIndex = self.profileCombo.findText(get_profile_current())
        self.profileCombo.setCurrentIndex(profileIndex)
        self.ledCombo.currentIndexChanged.connect(self.on_led_changed)
        ledIndex = self.ledCombo.findText(get_led_current())
        self.ledCombo.setCurrentIndex(ledIndex)
        self.chargeLimitSlider.setRange(0, 100)
        self.chargeLimitSlider.setValue(int(get_battery_charge_limit()))
        self.chargeLimitSlider.valueChanged.connect(self.on_charge_limit_change)
        self.dgpu_poller.setInterval(500)
        self.dgpu_poller.timeout.connect(self.dgpu_poller_tick)
        self.dgpu_poller.start()

        layout.addWidget(self.currentProfile)
        layout.addWidget(self.profileCombo)
        layout.addWidget(self.currentChargeLimit)
        layout.addWidget(self.chargeLimitSlider)
        layout.addWidget(self.currentLed)
        layout.addWidget(self.ledCombo)

    def on_profile_changed(self, index):
        set_profile_current(self.profileCombo.currentText())
        self.currentProfile.setText(f'Current Profile: {get_profile_current()}')
        print(f"Selected index: {index}, Text: {self.profileCombo.currentText()}")

    def on_charge_limit_change(self):
        set_battery_charge_limit(set_battery_charge_limit(self.chargeLimitSlider.value()))
        self.currentChargeLimit.setText(f'Charge Limit {get_battery_charge_limit()}%')
        print(f'Charge Limit Set to {self.chargeLimitSlider.value()}')

    def on_led_changed(self):
        set_led_current(self.ledCombo.currentText())
        print(f'Led setting now: {get_led_current()}')
        self.currentLed.setText(f'Keyboard Brightness: {get_led_current()}')

    def dgpu_poller_tick(self):
        print(get_dgpu_status())
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

def run_cmd(cmd: list) -> str:
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

def get_dgpu_status() -> str:
    cmd = "nvidia-smi --query-gpu=pstate --format=csv,noheader"
    text = run_cmd(cmd.split()).strip()
    if text == 'P0' or text ==  'P3':
        return ("Active", 'P0')
    elif text == 'P8':
        return ("Idle", 'P8')
    elif text == 'P5':
        return ("Low Power", 'P5')
    else:
        return ("Unknown", text)

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