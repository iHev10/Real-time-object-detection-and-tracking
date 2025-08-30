import sys
import serial
import time
from PyQt6.QtWidgets import QDialog, QMainWindow, QWidget
from PyQt6.uic import loadUi
from PyQt6.QtCore import Qt
from PyQt6 import QtCore



try:
    from PyQt6.uic import loadUiType
    cam_settings_ui, _ = loadUiType("ui/camera_settings.ui")
except Exception as e:
    print(f"Error loading UI: {e}")
    sys.exit(1)


class FCB7317Controller:
    def __init__(self, port='COM3', baudrate=9600):
        try:
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            print(f"Successfully connected to {port}")
        except serial.SerialException as e:
            print(f"Error: Could not connect to {port}. {str(e)}")
            raise

    def send_command(self, command):
        cmd = bytearray.fromhex('81' + command + 'FF')
        try:
            self.ser.write(cmd)
            print(f"Sent command: {cmd.hex()}")
            time.sleep(0.1)
            response = self.ser.read(10)
            if response:
                print(f"Response: {response.hex()}")
                return response
            else:
                print("No response from camera")
            return cmd
        except serial.SerialException as e:
            print(f"Error sending command: {str(e)}")
            raise

    def zoom_1x(self):
        self.send_command("01044700000000")

    def zoom_2x(self):
        self.send_command('01044701080501')

    def zoom_3x(self):
        self.send_command('01044702020B0E')

    def zoom_4x(self):
        self.send_command('01044702080F06')

    def zoom_5x(self):
        self.send_command('010447020D0405')

    def zoom_6x(self):
        self.send_command('01044703000806')

    def zoom_7x(self):
        self.send_command('01044703030200')

    def zoom_8x(self):
        self.send_command('01044703050409')

    def zoom_9x(self):
        self.send_command('0104470307010E')

    def zoom_10x(self):
        self.send_command('01044703080B03')

    def zoom_11x(self):
        self.send_command("010447030A0102")

    def zoom_12x(self):
        self.send_command('010447030B0402')

    def zoom_13x(self):
        self.send_command('010447030C0407')

    def zoom_14x(self):
        self.send_command('010447030D0205')

    def zoom_15x(self):
        self.send_command('010447030D0D0F')

    def zoom_16x(self):
        self.send_command('010447030E070B')

    def zoom_17x(self):
        self.send_command('010447030E0F0B')

    def zoom_18x(self):
        self.send_command('010447030F0604')

    def zoom_19x(self):
        self.send_command('010447030F0B0A')

    def zoom_20x(self):
        self.send_command('01044704000000')

    def defog_on(self):
        self.send_command('0104370203')
    def defog_off(self):
        self.send_command('0104370300')

    # def Gamma(self):
    #     self.send_command('01045B01')
    # def Gamma_off(self):
    #     self.send_command('01045B00')

    def ICR_on(self):
        self.send_command('01040102')
    def ICR_off(self):
        self.send_command('01040103')

    def VE_on(self):
        self.send_command('01043D06')
    def VE_off(self):
        self.send_command('01043D03')
    def VE_bright(self):
        self.send_command('01042D0006030200000000')
    def VE_dark(self):
        self.send_command('01042D0003000000000000')


    def AF_auto(self):
        self.send_command('01043900')
    def AF_manual(self):
        self.send_command('01043903')

    def shutter_up(self):
        self.send_command('01040A02')
    def shutter_down(self):
        self.send_command('01040A03')
    def shutter_reset(self):
        self.send_command('01040A00')

    def iris_up(self):
        self.send_command('01040B02')
    def iris_down(self):
        self.send_command('01040B03')
    def iris_reset(self):
        self.send_command('01040B00')

    def bright_up(self):
        self.send_command('01040D02')
    def bright_down(self):
        self.send_command('01040D03')
    def bright_reset(self):
        self.send_command('01040D00')

    def expose(self):
        self.send_command('01043E02')
    def expose_off(self):
        self.send_command('01043E03')
    def expose_high(self):
        self.send_command('01044E0000000E')
    def expose_normal(self):
        self.send_command('01044E00000007')
    def expose_low(self):
        self.send_command('01044E00000000')

    def focus_auto(self):
        self.send_command('01043802')
    def focus_far(self):
        self.send_command('01043803')
    def focus_near(self):
        self.send_command('01040802')
    
    def defult(self):
        self.send_command('01043802')     
        self.send_command('01043E03')
        self.send_command('01043900')
        self.send_command('01043D03')
        self.send_command('01040103')
        self.send_command('0104370300')
        self.send_command("01044700000000")
        
    # def update_temperature(self):
    #     return self.send_command('090468')        
        
    def close(self):
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()
            print("Serial connection closed")


class CameraSettingsUI(QWidget, cam_settings_ui):
    def __init__(self, parent=None):  
        super().__init__(parent)
        self.setupUi(self)
        self.camera=None
        
    #     # Initialize camera controller
    #     try:
    #         self.camera = FCB7317Controller(port='COM3')
    #     except serial.SerialException:
    #         print("Failed to connect to camera. Exiting.")
    #         sys.exit(1)

    #     # Initialize values
    #     self.shutter_value = 10
    #     self.iris_value = 7
    #     self.bright_value = 14
    #     self.active_focus = "auto"
    #     self.active_expose = "normal"

    #     # Connect signals
    #     self.zoomSlider.valueChanged.connect(self.update_zoom)
    #     self.zoomReset.clicked.connect(self.reset_zoom)
    #     self.defogCheck.stateChanged.connect(self.toggle_defog)
    #     self.icrCheck.stateChanged.connect(self.toggle_icr)
    #     self.camera.defult()
    #     self.veCheck.stateChanged.connect(self.toggle_ve)
    #     self.veModeCombo.currentIndexChanged.connect(self.update_ve_mode)
    #     self.aeModeCombo.currentIndexChanged.connect(self.toggle_ae_mode)
    #     self.exposeCheck.stateChanged.connect(self.toggle_expose)
    #     self.shutterMinus.clicked.connect(lambda: self.update_shutter(-1))
    #     self.shutterPlus.clicked.connect(lambda: self.update_shutter(1))
    #     self.shutterReset.clicked.connect(self.reset_shutter)
    #     self.irisMinus.clicked.connect(lambda: self.update_iris(-1))
    #     self.irisPlus.clicked.connect(lambda: self.update_iris(1))
    #     self.irisReset.clicked.connect(self.reset_iris)
    #     self.brightMinus.clicked.connect(lambda: self.update_bright(-1))
    #     self.brightPlus.clicked.connect(lambda: self.update_bright(1))
    #     self.brightReset.clicked.connect(self.reset_bright)
    #     self.focusNear.clicked.connect(lambda: self.set_focus_mode("near"))
    #     self.focusFar.clicked.connect(lambda: self.set_focus_mode("far"))
    #     self.focusAuto.clicked.connect(lambda: self.set_focus_mode("auto"))
    #     self.exposeHigh.clicked.connect(lambda: self.set_expose_mode("high"))
    #     self.exposeNormal.clicked.connect(
    #         lambda: self.set_expose_mode("normal"))
    #     self.exposeLow.clicked.connect(lambda: self.set_expose_mode("low"))
    #     # self.updateTemperatureButton.clicked.connect(self.update_temperature)


    #     # Initialize states
    #     self.veModeCombo.setEnabled(False)
    #     self.manualAeFrame.setEnabled(False)
    #     self.exposeFrame.setEnabled(False)
    #     self.set_focus_mode("auto")
    #     self.set_expose_mode("normal")

    # def update_zoom(self):
    #     zoom_value = self.zoomSlider.value()
    #     self.zoomLabel.setText(f"Zoom: {zoom_value}x")
    #     zoom_methods = {
    #         1: self.camera.zoom_1x, 2: self.camera.zoom_2x, 3: self.camera.zoom_3x,
    #         4: self.camera.zoom_4x, 5: self.camera.zoom_5x, 6: self.camera.zoom_6x,
    #         7: self.camera.zoom_7x, 8: self.camera.zoom_8x, 9: self.camera.zoom_9x,
    #         10: self.camera.zoom_10x, 11: self.camera.zoom_11x, 12: self.camera.zoom_12x,
    #         13: self.camera.zoom_13x, 14: self.camera.zoom_14x, 15: self.camera.zoom_15x,
    #         16: self.camera.zoom_16x, 17: self.camera.zoom_17x, 18: self.camera.zoom_18x,
    #         19: self.camera.zoom_19x, 20: self.camera.zoom_20x
    #     }
    #     zoom_methods.get(zoom_value, self.camera.zoom_1x)()

    # def reset_zoom(self):
    #     self.zoomSlider.setValue(1)
    #     self.zoomLabel.setText("Zoom: 1x")
    #     self.camera.zoom_1x()

    # def toggle_defog(self, state):
    #     if self.defogCheck.isChecked():
    #         self.camera.defog_on()
    #     else:
    #         self.camera.defog_off()

    # def toggle_icr(self):
    #     if self.icrCheck.isChecked():
    #         self.camera.ICR_on()
    #     else:
    #         self.camera.ICR_off()
            
    # def toggle_ve(self, state):
    #     self.veModeCombo.setEnabled(state == QtCore.Qt.CheckState.Checked.value)
    #     if state == QtCore.Qt.CheckState.Checked.value:
    #         self.camera.VE_on()
    #         self.update_ve_mode(self.veModeCombo.currentIndex())
    #     else:
    #         self.camera.VE_off()

    # def update_ve_mode(self, index):
    #     if self.veCheck.isChecked():
    #         if index == 0:  # Dark
    #             self.camera.VE_dark()
    #         elif index == 1:  # Bright
    #             self.camera.VE_bright()

    # def toggle_ae_mode(self, index):
    #     self.manualAeFrame.setEnabled(index == 1)
    #     if index == 0:
    #         self.camera.AF_auto()
    #     elif index == 1:
    #         self.camera.AF_manual()

        
    # def update_shutter(self, delta):
    #     print("in")

    #     self.shutter_value = max(1, min(22, self.shutter_value + delta))
    #     self.shutterLabel.setText(f"Shutter: {self.shutter_value}")
    #     if delta > 0:
    #         self.camera.shutter_up()
    #     elif delta < 0:
    #         self.camera.shutter_down()

    # def reset_shutter(self):
    #     self.shutter_value = 5
    #     self.shutterLabel.setText(f"Shutter: {self.shutter_value}")
    #     self.camera.shutter_reset()
    
    
    # def update_iris(self, delta):
    #     self.iris_value = max(1, min(14, self.iris_value + delta))
    #     self.irisLabel.setText(f"Iris: {self.iris_value}")
    #     if delta > 0:
    #         self.camera.iris_up()
    #     elif delta < 0:
    #         self.camera.iris_down()

    # def reset_iris(self):
    #     self.iris_value = 12
    #     self.irisLabel.setText(f"Iris: {self.iris_value}")
    #     self.camera.iris_reset()

    # def update_bright(self, delta):
    #     self.bright_value = max(1, min(28, self.bright_value + delta))
    #     self.brightLabel.setText(f"Bright: {self.bright_value}")
    #     if delta > 0:
    #         self.camera.bright_up()
    #     elif delta < 0:
    #         self.camera.bright_down()

    # def reset_bright(self):
    #     self.bright_value = 14
    #     self.brightLabel.setText(f"Bright: {self.bright_value}")
    #     self.camera.bright_reset()
        
        
    # def toggle_expose(self, state):
    #     if self.exposeCheck.isChecked():
    #         self.exposeFrame.setEnabled(True)

    #         self.camera.expose()
    #         self.set_expose_mode(self.active_expose)
    #         # self.set_expose_mode()
    #     else:
    #         self.camera.expose_off()
        

    # def set_expose_mode(self, mode):
    #     self.active_expose = mode
    #     self.exposeHigh.setProperty("active", mode == "high")
    #     self.exposeNormal.setProperty("active", mode == "normal")
    #     self.exposeLow.setProperty("active", mode == "low")
    #     self.exposeHigh.style().unpolish(self.exposeHigh)
    #     self.exposeHigh.style().polish(self.exposeHigh)
    #     self.exposeNormal.style().unpolish(self.exposeNormal)
    #     self.exposeNormal.style().polish(self.exposeNormal)
    #     self.exposeLow.style().unpolish(self.exposeLow)
    #     self.exposeLow.style().polish(self.exposeLow)
    #     if self.exposeCheck.isChecked():
    #         if self.active_expose == "high":
    #             self.camera.expose_high()
    #         elif self.active_expose == "normal":
    #             self.camera.expose_normal()
    #         elif self.active_expose == "low":
    #             self.camera.expose_low()

    # def set_focus_mode(self, mode):
    #     self.active_focus = mode
    #     self.focusNear.setProperty("active", mode == "near")
    #     self.focusFar.setProperty("active", mode == "far")
    #     self.focusAuto.setProperty("active", mode == "auto")
    #     self.focusNear.style().unpolish(self.focusNear)
    #     self.focusNear.style().polish(self.focusNear)
    #     self.focusFar.style().unpolish(self.focusFar)
    #     self.focusFar.style().polish(self.focusFar)
    #     self.focusAuto.style().unpolish(self.focusAuto)
    #     self.focusAuto.style().polish(self.focusAuto)
    #     if mode == "near":
    #         self.camera.focus_near()
    #     elif mode == "far":
    #         self.camera.focus_far()
    #     elif mode == "auto":
    #         self.camera.focus_auto()
            
            
    # # def update_temperature(self):
    # #     response = self.camera.update_temperature()

    # #     if not response:
    # #         self.temperatureLabel.setText("Temperature: No response")
    # #         return

    # #     hex_value = response.hex()[-4:]
    # #     hex_value = hex_value.lstrip('0').upper()

    # #     temp_map = {
    # #         'FB': '−8 to −2',
    # #         '00': '−3 to +3',
    # #         '0A': '7 to 13',
    # #         '14': '17 to 23',
    # #         '1E': '27 to 33',
    # #         '28': '37 to 43',
    # #         '32': '47 to 53',
    # #         '3C': '57 to 63'
    # #     }

    #     # temperature_range = temp_map.get(hex_value, 'Unknown')
    #     # self.temperatureLabel.setText(f"Temperature: {temperature_range} °C")


    # def closeEvent(self, event):
    #     self.camera.close()
    #     event.accept()
