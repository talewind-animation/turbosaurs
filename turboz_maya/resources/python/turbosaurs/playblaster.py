import os
import re

from Qt import (
    QtCore,
    QtGui,
    QtWidgets,
)


import pymel.core as pm
import maya.mel as mel

from twa_maya.gui.workspace_control import SampleMayaUI
from twa_maya.util.log_to_maya import MayaQtLogger
from helpers.ffmpeg_playblast import HrPlayblast


ICONPATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "icons")

class PlayblasterWindow(SampleMayaUI):

    WINDOW_TITLE = "TWA Playblast"
    PLAYBLASTER = HrPlayblast(logging_enabled=True)

    def __init__(self):
        super(PlayblasterWindow, self).__init__()
        self.logger = MayaQtLogger(sender="TWA-Playblast", log_to_maya=True)
        self.settings = QtCore.QSettings("twa_playblaster", "twa_playblaster")

        self.__geometry = None

        PlayblasterWindow.PLAYBLASTER.set_resolution("HD 1080")

    def create_widgets(self):
        self.name_lbl = QtWidgets.QLabel("Artist Name:")

        self.name_led = QtWidgets.QLineEdit()
        self.name_led.setPlaceholderText("Enter your name")

        self.image_plane_chb = QtWidgets.QCheckBox("Image Planes")
        self.image_plane_chb.setMaximumWidth(100)

        self.help_img = QtWidgets.QLabel()
        pixmap = QtGui.QPixmap(os.path.join(ICONPATH, "help_smooth.png"))
        self.help_img.setPixmap(pixmap)

        self.playblast_btn = QtWidgets.QPushButton("Playblast")
        self.playblast_btn.setStyleSheet("background-color: #1198fb; font-size: 25px;")
        self.playblast_btn.setMinimumHeight(80)

    def create_layout(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)

        name_row = QtWidgets.QHBoxLayout()
        name_row.addWidget(self.name_lbl)
        name_row.addWidget(self.name_led)
        name_row.addWidget(self.image_plane_chb)

        blast_row = QtWidgets.QHBoxLayout()
        blast_row.addWidget(self.playblast_btn)

        self.main_layout.addLayout(name_row)
        self.main_layout.addWidget(self.help_img)
        self.main_layout.addLayout(blast_row)

    def create_connections(self):
        self.name_led.returnPressed.connect(self.set_artist_name)
        self.playblast_btn.clicked.connect(self.playblast)

    def configure_widgets(self):
        self.name_led.setText(PlayblasterWindow.PLAYBLASTER.get_artist_name())

        img_planes_checked = self.settings.value("img_planes")
        if img_planes_checked:
            self.image_plane_chb.setChecked(img_planes_checked=="true")

    def save_settings(self):
        self.settings.setValue("img_planes", self.image_plane_chb.isChecked())

    def set_artist_name(self):
        name = self.name_led.text()
        if bool(re.match('[A-Za-z]{2,25}( [A-Za-z]{2,25})?', name)):
            PlayblasterWindow.PLAYBLASTER.set_artist_name(name)
        else:
            self.logger.log_error("Invalid artist name!")
            self.name_led.setText(PlayblasterWindow.PLAYBLASTER.get_artist_name())

    def playblast(self):
        if self.image_plane_chb.isChecked():
            PlayblasterWindow.PLAYBLASTER.set_visibility("Blast_lyt")
        else:
            PlayblasterWindow.PLAYBLASTER.set_visibility("Blast")

        self.save_settings()

        textures = pm.modelEditor('modelPanel4', q=True, dtx=True)
        if not textures:
            pm.modelEditor('modelPanel4', e=True, dtx=True)

        render_globs = pm.PyNode("hardwareRenderingGlobals")
        ssao = render_globs.ssaoEnable.get()
        if ssao == 0:
            render_globs.ssaoEnable.set(1)

        msaa = render_globs.multiSampleEnable.get()
        if msaa == 0:
            render_globs.multiSampleEnable.set(1)

        PlayblasterWindow.PLAYBLASTER.execute("{scene}", "{scene}_playblast", overwrite=True)

        pm.modelEditor('modelPanel4', e=True, dtx=textures)
        render_globs.ssaoEnable.set(ssao)
        render_globs.multiSampleEnable.set(msaa)

    def showEvent(self, e):
        super(PlayblasterWindow, self).showEvent(e)
        self.configure_widgets()
        if self.__geometry:
            self.restoreGeometry(self.__geometry)

    def closeEvent(self, e):
        if isinstance(self, PlayblasterWindow):
            super(PlayblasterWindow, self).closeEvent(e)
            self.__geometry = self.saveGeometry()
