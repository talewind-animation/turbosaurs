import os
from functools import partial

from Qt import (
    QtCore,
    QtGui,
    QtWidgets,
    _QtUiTools
)


import pymel.core as pm
import maya.mel as mel

from twa_maya.gui.workspace_control import SampleMayaUI
from twa_maya.util.log_to_maya import *
from helpers.ffmpeg_playblast import HrPlayblast

PROJECTS_PATH = os.path.abspath(os.getenv("PROJECTS_PATH", "Z:/Projects"))

class CameraManagerWindow(SampleMayaUI):

    WINDOW_TITLE = "TWA Camera Manager"
    UI_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "CameraManager.ui"))

    def __init__(self):
        self._playblaster = HrPlayblast(logging_enabled=True)
        super(CameraManagerWindow, self).__init__()

        self.__geometry = None

        self.script_jobs = []
        self._image_plane = None
        self.cameras_list = []
        self.populate()

    def create_widgets(self):
        self.ui_wgt = _QtUiTools.QUiLoader().load(self.UI_FILE)

        cameras_list_wgt = QtWidgets.QWidget()
        self.cameras_lyt = QtWidgets.QVBoxLayout(cameras_list_wgt)
        self.cameras_lyt.setContentsMargins(2, 2, 2, 2)
        self.cameras_lyt.setSpacing(3)
        self.cameras_lyt.setAlignment(QtCore.Qt.AlignTop)

        cameras_scroll_area = QtWidgets.QScrollArea()
        cameras_scroll_area.setWidgetResizable(True)
        cameras_scroll_area.setWidget(cameras_list_wgt)

        self.ui_wgt.scroll_area_lyt.addWidget(cameras_scroll_area)

        self.ui_wgt.load_image_plane_btn.hide()
        self.ui_wgt.image_plane_led.hide()

        self.ui_wgt.load_image_plane_btn.setIcon(QtGui.QIcon(":openScript.png"))
        self.ui_wgt.lock_all_btn.setIcon(QtGui.QIcon(":lock.png"))
        self.ui_wgt.playblast_all_btn.setIcon(QtGui.QIcon(":nClothCacheReplace.png"))
        self.ui_wgt.reload_btn.setIcon(QtGui.QIcon(":refresh.png"))

        self.ui_wgt.artist_name_led.setText(self._playblaster.get_artist_name())

    def create_layout(self):
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.ui_wgt)

    def create_connections(self):
        self.ui_wgt.lock_all_btn.clicked.connect(self.lock_all_cameras)
        self.ui_wgt.reload_btn.clicked.connect(self.reload)
        self.ui_wgt.image_plane_icon.clicked.connect(self.select_image_plane)
        self.ui_wgt.artist_name_led.returnPressed.connect(self.set_artist_name)

    def configure_widgets(self):
        self.find_image_plane()
        if self.image_plane:
            self.ui_wgt.image_plane_icon.setIcon(QtGui.QIcon(":confirm.png"))
            self.ui_wgt.image_plane_led.setText(self.image_plane.imageName.get())
        else:
            self.ui_wgt.image_plane_icon.setIcon(QtGui.QIcon(":error.png"))
            self.ui_wgt.image_plane_led.setText("")

    @property
    def image_plane(self):
        return self._image_plane

    @image_plane.setter
    def image_plane(self, value):
        if value:
            self._image_plane = value
            CameraWidget.image_plane = value

    def set_artist_name(self):
        name = self.ui_wgt.artist_name_led.text()
        self._playblaster.set_artist_name(name)

    def reload(self):
        self.populate()
        self.configure_widgets()

    def find_image_plane(self):
        if not self.image_plane:
            self.image_plane = CameraUtils.find_image_plane()

    def select_image_plane(self):
        if self.image_plane:
            pm.select(self.image_plane)

    def clear_cameras_list(self):
        self.cameras_list = []

        while self.cameras_lyt.count() > 0:
            camera = self.cameras_lyt.takeAt(0)
            if camera.widget():
                camera.widget()._delete_ui()

    def populate(self):
        self.clear_cameras_list()
        for cam in CameraUtils.list_cameras():
            camera = CameraWidget(cam)
            self.cameras_lyt.addWidget(camera)

            self.cameras_list.append(camera)

    def lock_all_cameras(self):
        for camera in self.cameras_list:
            camera._lock()

    def create_script_jobs(self):
        self.script_jobs.append(pm.scriptJob(event=["SceneOpened", partial(self.populate)]))

    def delete_script_jobs(self):
        for job_num in self.script_jobs:
            pm.scriptJob(kill=job_num)

        self.script_jobs = []

    def showEvent(self, e):
        super(CameraManagerWindow, self).showEvent(e)
        self.configure_widgets()
        self.create_script_jobs()
        if self.__geometry:
            self.restoreGeometry(self.__geometry)

    def closeEvent(self, e):
        if isinstance(self, CameraManagerWindow):
            super(CameraManagerWindow, self).closeEvent(e)
            self.__geometry = self.saveGeometry()
            self.delete_script_jobs()

class CameraWidget(QtWidgets.QWidget):
    image_plane = None

    @staticmethod
    def rreplace(text, string, new_string):
        return new_string.join(text.rsplit(string, 1))

    def __init__(self, camera, playblaster=None):
        super(CameraWidget, self).__init__()

        self.playblaster=playblaster

        self.camera_transform = camera
        self.camera = camera.getShape()
        self.parse_camera()
        self.update_frames_attr()

        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.configure_widgets()

    def create_widgets(self):
        self.look_through_btn = QtWidgets.QPushButton()
        self.look_through_btn.setIcon(QtGui.QIcon(":camera.svg"))
        self.look_through_btn.setFlat(True)
        self.look_through_btn.setMaximumWidth(20)
        self.look_through_btn.setMaximumHeight(20)

        self.select_btn = QtWidgets.QPushButton()
        self.select_btn.setIcon(QtGui.QIcon(":aselect.png"))
        self.select_btn.setFlat(True)
        self.select_btn.setMaximumWidth(20)
        self.select_btn.setMaximumHeight(20)

        self.lock_btn = QtWidgets.QPushButton()
        self.lock_btn.setCheckable(True)
        self.lock_btn.setIcon(QtGui.QIcon(":CameraLock.png"))
        self.lock_btn.setFlat(True)
        self.lock_btn.setMaximumWidth(20)
        self.lock_btn.setMaximumHeight(20)

        self.playblast_btn = QtWidgets.QPushButton()
        self.playblast_btn.setIcon(QtGui.QIcon(":nClothCacheReplace.png"))
        self.playblast_btn.setFlat(True)
        self.playblast_btn.setMaximumWidth(20)
        self.playblast_btn.setMaximumHeight(20)

        self.show_notes_btn = QtWidgets.QPushButton()
        self.show_notes_btn.setIcon(QtGui.QIcon(":setEdEditMode.png"))
        self.show_notes_btn.setFlat(True)
        self.show_notes_btn.setMaximumWidth(20)
        self.show_notes_btn.setMaximumHeight(20)

        self.name_led = QtWidgets.QLineEdit()
        self.name_led.setReadOnly(True)
        self.name_led.setMinimumWidth(120)
        self.start_frame_led = QtWidgets.QLineEdit()
        self.start_frame_led.setValidator(QtGui.QIntValidator())
        self.start_frame_led.setMaximumWidth(40)
        self.end_frame_led = QtWidgets.QLineEdit()
        self.end_frame_led.setValidator(QtGui.QIntValidator())
        self.end_frame_led.setMaximumWidth(40)

    def create_layout(self):
        self.layout = QtWidgets.QHBoxLayout(self)

        self.layout.addWidget(self.look_through_btn)
        self.layout.addWidget(self.select_btn)
        self.layout.addWidget(self.lock_btn)

        self.layout.addWidget(self.name_led)
        self.layout.addWidget(QtWidgets.QLabel("Start"))
        self.layout.addWidget(self.start_frame_led)
        self.layout.addWidget(QtWidgets.QLabel("End"))
        self.layout.addWidget(self.end_frame_led)

        self.layout.addWidget(self.playblast_btn)
        self.layout.addWidget(self.show_notes_btn)

    def create_connections(self):
        self.look_through_btn.clicked.connect(self.look_through)
        self.select_btn.clicked.connect(self._select)
        self.lock_btn.clicked.connect(self.lock)
        self.playblast_btn.clicked.connect(self.playblast)
        self.show_notes_btn.clicked.connect(self.show_notes)

        self.start_frame_led.editingFinished.connect(self.frames_changed)
        self.end_frame_led.editingFinished.connect(self.frames_changed)

    def configure_widgets(self):
        self.lock_btn.setChecked(self.is_locked())
        self.name_led.setText(self.camera_transform.name())
        self.start_frame_led.setText(str(self.start_frame))
        self.end_frame_led.setText(str(self.end_frame))

    @property
    def camera_number(self):

        return self._camera_number

    @property
    def start_frame(self):

        return self._start_frame

    @start_frame.setter
    def start_frame(self, value):
        if isinstance(value, int) and value != self.start_frame:
            if value > self.end_frame:
                log_error("Start frame can't be greater than end frame")
                return
            new_name = self.rreplace(self.camera_transform.name(), str(self.start_frame), str(value))
            pm.rename(self.camera_transform, new_name)
            self._start_frame = int(value)

    @property
    def end_frame(self):

        return self._end_frame

    @end_frame.setter
    def end_frame(self, value):
        if isinstance(value, int) and value != self.start_frame:
            if value < self.start_frame:
                log_error("End frame can't be smaller than start frame")
                return
            new_name = self.rreplace(self.camera_transform.name(), str(self.end_frame), str(value))
            pm.rename(self.camera_transform, new_name)
            self._end_frame = int(value)

    @property
    def frames(self):
        if not self.camera.hasAttr("frames") or not self.camera.frames.get():
            if self.start_frame and self.end_frame:
                frames = "{}-{}".format(self.start_frame, self.end_frame)
            else:
                frames = "{}-{}".format(
                    int(pm.playbackOptions(q=True, min=True)),
                    int(pm.playbackOptions(q=True, max=True))
                    )
        else:
            frames = self.camera.frames.get()

        return frames

    @property
    def playblaster(self):
        return self._playblaster

    @playblaster.setter
    def playblaster(self, playblast):
        if playblast:
            self._playblaster = playblast
        else:
            self._playblaster = HrPlayblast(logging_enabled=True)

    def parse_camera(self):
        self._camera_number, self._start_frame, self._end_frame = CameraUtils.parse_camera_name(self.camera_transform.name())
        if self._start_frame == None:
            self._start_frame = int(pm.playbackOptions(q=True, min=True))
            self._end_frame = int(pm.playbackOptions(q=True, max=True))

    def create_frames_attr(self):
        if not self.camera.hasAttr("frames"):
            self.camera.addAttr("frames", dt="string")
            self.camera.attr("frames").set(self.frames)

    def update_frames_attr(self):
        if not self.camera.hasAttr("frames"):
            self.create_frames_attr()
        else:
            self.camera.attr("frames").set("{}-{}".format(str(self.start_frame), str(self.end_frame)))

    def frames_changed(self):
        self.start_frame = int(self.start_frame_led.text())
        self.end_frame = int(self.end_frame_led.text())
        self.update_frames_attr()
        self.name_led.setText(self.camera_transform.name())

    def look_through(self):
        CameraUtils.look_through(self.camera_transform.name(), self.start_frame, self.end_frame)
        if CameraWidget.image_plane:
            selection = pm.selected()
            pm.select(CameraWidget.image_plane)
            CameraUtils.attach_image_plane(self.camera_transform, CameraWidget.image_plane.name())
            self.fit_image_plane()
            pm.select(selection)

    def fit_image_plane(self):
        image_plane_node = CameraWidget.image_plane
        image_plane_node.sizeX.set(0.5)
        image_plane_node.offsetX.set(0.46)
        image_plane_node.offsetY.set(0.26)
        image_plane_node.depth.set(1)

    def playblast(self):
        self.playblaster.set_camera(self.camera_transform.name())
        self.playblaster.set_frame_range((self.start_frame, self.end_frame))
        self.playblaster.execute("{scene}", "{scene}_{camera}_playblast", overwrite=True)

    def show_notes(self):
        log_output("#TODO: show notes")

    def lock(self):
        if self.lock_btn.isChecked():
            self._lock()
        else:
            self._unlock()

    def is_locked(self):
        return self.camera.getLockTransform()

    def _lock(self):
        self.camera.setLockTransform(True)
        if not self.lock_btn.isChecked():
            self.lock_btn.setChecked(True)

    def _unlock(self):
        self.camera.setLockTransform(False)
        if self.lock_btn.isChecked():
            self.lock_btn.setChecked(False)

    def _select(self):
        pm.select(self.camera_transform)

    def _delete_ui(self):
        self.hide()
        self.setParent(None)
        self.deleteLater()

class CameraUtils(object):

    @classmethod
    def list_cameras(cls):
        """
        Return list of shot cameras. Cameras that have "cam_" in their name

        Returns
        -------
        list : list of shot cameras
        """
        return [cam.getTransform() for cam in pm.ls(type="camera") if "cam_" in cam.name()]

    @classmethod
    def parse_camera_name(cls, name):
        """
        split camera name into (number, start frame, end frame)
        each value may be None.

        Parameters
        ----------
        name (str) : camera name

        Returns
        -------
        tuple : (number, start frame, end frame)
        """
        name_splitted = [int(i) for i in name.split("_") if i.isdigit()]
        if not name_splitted:
            return (None, None, None)
        if len(name_splitted) == 1:
            return (name_splitted[0], None, None)
        elif len(name_splitted) == 2:
            return (None, name_splitted[0], name_splitted[1])
        elif len(name_splitted) >= 3:
            return (name_splitted[-3:])

    @classmethod
    def look_through(cls, camera_name, start_frame=None, end_frame=None):
        """
        look through the camera. Set start and end frame if any

        Parameters
        ----------
        camera_name (str) : camera name
        start_frame (int)
        end_frame (int)
        """
        panel_1 = pm.getPanel(withFocus=True)
        panel = pm.getPanel(visiblePanels=True)

        name_check = "modelPanel1"
        if name_check in panel:
            mel.eval("lookThroughModelPanel {} {};".format(camera_name, name_check))
        else:
            mel.eval("lookThroughModelPanel {} {};".format(camera_name, panel_1))

        if start_frame and end_frame:
            pm.playbackOptions(minTime=start_frame, maxTime=end_frame)

    @classmethod
    def attach_image_plane(cls, camera, image_plane_name="imagePlane1"):
        """
        Detack image plane from camera if connected.
        Attach it to provided camera

        Parameters
        ----------
        camera (Pymel camera node) : camera
        image_plane_name (int) : name of image plane imagePlane1 by default
        """
        pm.imagePlane(edit=True, detach=True, name=image_plane_name)
        pm.imagePlane(edit=True, camera=camera)

    @classmethod
    def find_image_plane(cls):
        """
        Find and return first image plane in the scene.

        Returns
        -------
        imagePlane node :
        """
        ip = pm.ls(type="imagePlane")
        return ip[0] if ip else None
