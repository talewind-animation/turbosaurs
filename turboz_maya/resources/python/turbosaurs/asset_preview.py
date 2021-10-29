import os
from Qt import (
    QtCore,
    QtGui,
    QtWidgets,
    _QtUiTools
)

import maya.cmds as cmds
from twa_maya.gui.workspace_control import SampleMayaUI
from twa_maya.util.log_to_maya import MayaQtLogger
from Deadline.DeadlineConnect import DeadlineCon

FFMPEG_LOCATION = "Z:\\Projects\\RnD\\ffmpeg\\ffmpeg.exe"
WORKING_ROOT = "Z:\\Projects\\RnD\\asset_preview"
LD_SCENE = os.path.join(WORKING_ROOT, "preview_scene.ma")
POST_JOB_SCRIPT = os.path.join(WORKING_ROOT, "post_job.py")
PREVIEW_SCENES = os.path.join(WORKING_ROOT, "scenes")
PREVIEW_RENDERS = os.path.join(WORKING_ROOT, "render")

PULSE_NAME = "dell"

DEADLINE_PORT = 8082
DEADLINE_LOGIN = "admin"
DEADLINE_PASSWORD = "123"

deadline_connection = DeadlineCon(PULSE_NAME, DEADLINE_PORT)
deadline_connection.SetAuthenticationCredentials(
    DEADLINE_LOGIN, DEADLINE_PASSWORD)


class AssetPreviewWindow(SampleMayaUI):

    WINDOW_TITLE = "TWA Asset Preview"

    cam_name = "renderCam"
    frame_range = "1-36"
    square_aspect = (1024, 1024)
    hd_aspect = (1280, 720)

    formats = {
            "Square": {
                        "1k": (1024, 1024, 1.0, 1.0),
                        "2k": (2048, 2048, 1.0, 1.0),
                        "4k": (4096, 4096, 1.0, 1.0),
                        },
            "Wide": {
                        "1k": (1280, 720, 1.778, 1.0),
                        "2k": (1920, 1080, 1.778, 1.0),
                        "4k": (3840, 2160, 1.778, 1.0),
                        },
        }

    def __init__(self):
        self.__geometry = None
        self.logger = MayaQtLogger(sender="TWA-Asset Preview", log_to_maya=True)
        super(AssetPreviewWindow, self).__init__()

        self._asset = None
        self._scene_name = None
        self._scene_file = None

        self.populate_resolutions()

    def create_widgets(self):
        self.aspect_cbx = QtWidgets.QComboBox()
        self.aspect_lbl = QtWidgets.QLabel("Aspect Reatio: ")
        self.resolution_cbx = QtWidgets.QComboBox()
        self.resolution_lbl = QtWidgets.QLabel("Render Resolution: ")
        self.asset_lbl = QtWidgets.QLabel("Asset Path: ")
        self.asset_lbl = QtWidgets.QLabel("Asset Path: ")
        self.asset_led = QtWidgets.QLineEdit()
        self.browse_asset_btn = QtWidgets.QPushButton("...")
        self.create_scene_btn = QtWidgets.QPushButton("Create Scene")
        self.submitte_btn = QtWidgets.QPushButton("Submitte")

    def create_layout(self):
        self.master_layout = QtWidgets.QVBoxLayout(self)
        self.asset_path_lyt = QtWidgets.QHBoxLayout()
        self.resolution_lyt = QtWidgets.QHBoxLayout()

        self.asset_path_lyt.addWidget(self.asset_lbl)
        self.asset_path_lyt.addWidget(self.asset_led)
        self.asset_path_lyt.addWidget(self.browse_asset_btn)

        self.resolution_lyt.addWidget(self.aspect_lbl)
        self.resolution_lyt.addWidget(self.aspect_cbx)
        self.resolution_lyt.addWidget(self.resolution_lbl)
        self.resolution_lyt.addWidget(self.resolution_cbx)
        self.resolution_lyt.addWidget(self.submitte_btn)

        self.master_layout.addLayout(self.asset_path_lyt)
        self.master_layout.addWidget(self.create_scene_btn)
        self.master_layout.addLayout(self.resolution_lyt)
        # self.master_layout.addWidget(self.submitte_btn)

    def create_connections(self):
        self.browse_asset_btn.clicked.connect(self.browse_asset)
        self.create_scene_btn.clicked.connect(self.create_scene)
        self.aspect_cbx.activated.connect(self.change_render_res)
        self.resolution_cbx.activated.connect(self.change_render_res)
        self.submitte_btn.clicked.connect(self.submitte_job)

    def populate_resolutions(self):
        self.aspect_cbx.clear()
        self.resolution_cbx.clear()
        self.aspect_cbx.addItems(AssetPreviewWindow.formats.keys())
        self.aspect_cbx.setCurrentIndex(1)
        self.resolution_cbx.addItems(AssetPreviewWindow.formats["Square"].keys())

    @property
    def asset(self):
        return self._asset

    @asset.setter
    def asset(self, asset_path):
        if os.path.isfile(asset_path) and asset_path.endswith(".ma"):
            self._asset = os.path.normpath(asset_path)
        else:
            self.logger.log_error("Asset path is not valid!")

    @property
    def scene_name(self):
        return self._scene_name

    @scene_name.setter
    def scene_name(self, value):
        self._scene_name = value

    @property
    def scene_file(self):
        return self._scene_file

    @scene_file.setter
    def scene_file(self, value):
        self._scene_file = value

    @staticmethod
    def get_top_level_ref(ref):
        for node in cmds.referenceQuery(ref, nodes=True):
            if cmds.objectType(node, isType="transform") and not cmds.listRelatives(node, parent=True):
                return node

    @staticmethod
    def center_cam(obj):
        bbox = cmds.exactWorldBoundingBox(obj)

        cmds.setAttr("__scene__.center_point", bbox[3]/2)
        cmds.setAttr("__scene__.camera_Y", bbox[3]/1.2)
        cmds.setAttr("__scene__.camera_Z", bbox[4]*3)

    def change_render_res(self):
        aspect = self.aspect_cbx.currentText()
        res = self.resolution_cbx.currentText()

        width, height, daspect, paspect = AssetPreviewWindow.formats[aspect][res]

        cmds.setAttr("defaultResolution.width", width)
        cmds.setAttr("defaultResolution.height", height)
        cmds.setAttr("defaultResolution.deviceAspectRatio", daspect)
        cmds.setAttr("defaultResolution.pixelAspect", paspect)

        cmds.setAttr("vraySettings.width", width)
        cmds.setAttr("vraySettings.height", height)
        cmds.setAttr("vraySettings.aspectRatio", daspect)
        cmds.setAttr("vraySettings.pixelAspect", paspect)

    def browse_asset(self):
        asset_text = self.asset_led.text()
        if asset_text:
            if os.path.isdir(asset_text):
                start_path = asset_text
            elif os.path.isfile(asset_text):
                start_path = os.path.dirname(asset_text)
            else:
                start_path = os.environ["PROJECT_PATH"]
        else:
            start_path = os.environ["PROJECT_PATH"]

        asset = QtWidgets.QFileDialog.getOpenFileName(self, "Select Asset", start_path, "Maya Files (*.ma *.mb)")
        asset = asset[0]
        if asset and os.path.isfile(asset):
            self.asset_led.setText(str(asset))

    def create_scene(self):
        self.asset = self.asset_led.text()
        if not self.asset:
            self.logger.log_error("Asset path is not valid!")
            return

        self.__create_scene()

    def submitte_job(self):
        if self.asset and self.scene_file:
            cmds.file(save=True, type="mayaAscii")

            job_info, plugin_info = self.deadline_info()
            deadline_connection.Jobs.SubmitJob(job_info, plugin_info)
            self.logger.log_output("Successfully submitted job {}!".format(self.scene_name))
        else:
            self.logger.log_error("Scene is not created, or wrong asset name!")

        self.asset_led.setText("")

    def __create_scene(self):
        cmds.file(LD_SCENE, open=True, force=True)

        _, asset_name = os.path.split(self.asset)

        asset_name = asset_name[:-3]
        self.scene_name = "{}_preview.ma".format(asset_name)
        self.scene_file = os.path.join(PREVIEW_SCENES, self.scene_name)

        cmds.file(rename=self.scene_file)
        cmds.file(save=True, type="mayaAscii")

        ref = cmds.file(self.asset, reference=True, namespace=asset_name)

        ref_root = self.get_top_level_ref(ref)
        self.center_cam(ref_root)
        self.change_render_res()

    def deadline_info(self):
        job_info = {
            "BatchName": "AssetPreview",
            "Group": "preview",
            "Department": "lookdev",
            "Frames": self.frame_range,
            "Name": self.scene_name[:-3].lower(),
            "Priority": 80,
            "OutputDirectory0": PREVIEW_RENDERS,
            "OutputFilename0": self.scene_name,
            "OutputFilename1": self.asset,
            "OutputFilename2": FFMPEG_LOCATION,
            "PostJobScript": POST_JOB_SCRIPT,
            "OverrideTaskExtraInfoNames": "False",
            "Plugin": "MayaBatch",
            "UserName": "admin",
            "ChunkSize": "1",
        }

        plugin_info = {
            "Animation": 1,
            "Build": "64bit",
            "Camera": self.cam_name,
            "SceneFile": self.scene_file,
            "OutputFilePath": PREVIEW_RENDERS,
            "RenderLayer": "masterLayer",
            "FrameNumberOffset": 0,
            "IgnoreError211": 0,
            "ImageHeight": cmds.getAttr("defaultResolution.height"),
            "ImageWidth": cmds.getAttr("defaultResolution.width"),
            "OutputFilePrefix": "<Scene>\\<Scene>",
            "RenderSetupIncludeLights": "1",
            "Renderer": "vray",
            "StrictErrorChecking": "0",
            "UseLegacyRenderLayers": "1",
            "UseLocalAssetCaching": "0",
            "UsingRenderLayers": "1",
            "VRayAutoMemoryBuffer": "500",
            "VRayAutoMemoryEnabled": "0",
            "Version": "2020",
        }

        return (job_info, plugin_info)

    def showEvent(self, e):
        super(AssetPreviewWindow, self).showEvent(e)
        if self.__geometry:
            self.restoreGeometry(self.__geometry)

    def closeEvent(self, e):
        if isinstance(self, AssetPreviewWindow):
            super(AssetPreviewWindow, self).closeEvent(e)
            self.__geometry = self.saveGeometry()
