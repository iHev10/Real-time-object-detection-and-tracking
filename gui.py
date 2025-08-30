# from password import PasswordDialog
from mon_main_app import MainApp
import sys

from PyQt6.QtWidgets import QApplication, QDialog


def main():
    app = QApplication(sys.argv)
    # password_dialog = PasswordDialog()
    # if password_dialog.exec() == QDialog.DialogCode.Accepted:
    window = MainApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
