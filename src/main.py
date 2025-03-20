# --- 파일명: main.py ---
import sys
from PyQt5 import QtWidgets, QtCore
from mainwindow import MainWindow


if __name__ == "__main__":
    # 중복 실행 방지를 위한 고유 키 지정
    sharedMem = QtCore.QSharedMemory("ECyberDownloaderUniqueKey")
    if not sharedMem.create(1):
        QtWidgets.QMessageBox.warning(None, "경고", "이미 프로그램이 실행 중입니다.")
        sys.exit(0)
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
