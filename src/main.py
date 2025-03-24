import sys
import os
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QStandardPaths, QLockFile
from mainwindow import MainWindow

def main():
    app = QtWidgets.QApplication(sys.argv)
    
    # 임시 폴더에 락 파일 생성
    temp_dir = QStandardPaths.writableLocation(QStandardPaths.TempLocation)
    lock_file_path = os.path.join(temp_dir, "ECyberDownloader.lock")
    lock_file = QLockFile(lock_file_path)
    lock_file.setStaleLockTime(10000)  # 10초 이상 락이 유지되면 stale로 간주
    
    # 락 획득 시도 (100ms)
    if not lock_file.tryLock(100):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setWindowTitle("경고")
        msg.setText("이미 프로그램이 실행 중입니다.")
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg.exec_()
        sys.exit(0)
    
    window = MainWindow()
    window.show()
    window.raise_()         # 창을 최상위로 올림
    window.activateWindow() # 창에 포커스 강제 적용
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
