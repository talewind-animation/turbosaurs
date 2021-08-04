import os
from PIL import ImageGrab
from Qt import QtWidgets, QtCore, QtGui


class ScreenCapture(QtWidgets.QWidget):

    dlg_instance = None

    @classmethod
    def capture(cls, filename):
        if not cls.dlg_instance:
            cls.dlg_instance = ScreenCapture(filename)

        if cls.dlg_instance.isHidden():
            cls.dlg_instance.show()
        else:
            cls.dlg_instance.raise_()
            cls.dlg_instance.activateWindow()

    def __init__(self, screenshot_path):
        super(ScreenCapture, self).__init__()
        self.screenshot_path = screenshot_path

        screen_width = 1920
        screen_height = 1080

        self.setGeometry(0, 0, screen_width, screen_height)
        self.setWindowTitle(' ')
        self.setWindowOpacity(0.3)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)

        self.begin = QtCore.QPoint()
        self.end = QtCore.QPoint()

        self.show()

    @property
    def screenshot_path(self):
        return self._screenshot_path

    @screenshot_path.setter
    def screenshot_path(self, value):
        if os.path.isdir(os.path.split(value)[0]):
            self._screenshot_path = value

    def showEvent(self, e):
        super(ScreenCapture, self).showEvent(e)

        self.begin = QtCore.QPoint()
        self.end = QtCore.QPoint()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setPen(QtGui.QPen(QtGui.QColor('black'), 2))
        qp.setBrush(QtGui.QColor(128, 128, 255, 128))
        qp.drawRect(QtCore.QRect(self.begin, self.end))

    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = self.begin
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        self.close()

        if self._screenshot_path:
            x1 = min(self.begin.x(), self.end.x())
            y1 = min(self.begin.y(), self.end.y())
            x2 = max(self.begin.x(), self.end.x())
            y2 = max(self.begin.y(), self.end.y())

            img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            img.save(self._screenshot_path)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
        event.accept()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    screenshot_path = "D:\\screen\\screenshots\\test.png"
    window = ScreenCapture(screenshot_path)
    window.show()
    app.aboutToQuit.connect(app.deleteLater)
    sys.exit(app.exec_())
