import os
import json
import tempfile
from functools import partial
from Qt import (
    QtCore,
    QtGui,
    QtWidgets,
    _QtUiTools
)

import pymel.core as pm
from pymel.core.nodetypes import RenderLayer

from twa_maya.gui.workspace_control import SampleMayaUI
from helpers.utility import viewport_disabled, get_attr_in_layer
from helpers.screen_capture import ScreenCapture
from tools.render_settings import RenderSettingsManager as RSManager
from tools.render_settings import VrayRenderElements as VrayAov
from tools.render_settings import RenderLayers
from mongo_documents import DatabaseConnection, MayaJob, MayaRenderLayer

PROJECT = "Turbosaurs"
PROJECTS_PATH = os.path.abspath(os.getenv("PROJECTS_PATH", "Z:/Projects"))
RENDER_SCENES = os.path.join(PROJECTS_PATH, PROJECT, "Render_scenes")
MASTER_SCENES = os.path.join(PROJECTS_PATH, "RnD", "masterScene")

RENDERS = os.path.join(PROJECTS_PATH, PROJECT, "Render")
DBHOST = os.getenv("DB_HOST", "192.168.99.2")
UI_FILE = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "ui", "render_setup.ui"))


class TurbozRenderSetupWindow(SampleMayaUI):

    WINDOW_TITLE = "TWA Render Setup"

    settings_file = os.path.join(
        tempfile.gettempdir(), "__TWA_renderSetup_settings.json")
    default_settings = {
        "season": None,
        "episode": None,
    }

    @staticmethod
    def scene_saved():
        return os.path.abspath(pm.sceneName()).startswith(RENDER_SCENES)

    def __init__(self):
        super(TurbozRenderSetupWindow, self).__init__()

        self.__geometry = None

        self.render_layers = []
        self.script_jobs = []

        self.populate_seasons()
        self.populate_render_layers()
        self.load_settings()

    def create_widgets(self):
        self.ui_wgt = _QtUiTools.QUiLoader().load(UI_FILE)

        render_layers_list_wgt = QtWidgets.QWidget()
        self.render_layers_lyt = QtWidgets.QVBoxLayout(render_layers_list_wgt)
        self.render_layers_lyt.setContentsMargins(2, 2, 2, 2)
        self.render_layers_lyt.setSpacing(3)
        self.render_layers_lyt.setAlignment(QtCore.Qt.AlignTop)

        render_layers_scroll_area = QtWidgets.QScrollArea()
        render_layers_scroll_area.setWidgetResizable(True)
        render_layers_scroll_area.setWidget(render_layers_list_wgt)

        self.ui_wgt.render_layers_lyt.addWidget(render_layers_scroll_area)

        self.ui_wgt.prep_scene_btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui_wgt.prep_scene_btn.customContextMenuRequested.connect(self.on_context_menu)

        self.ms_context_menu = QtWidgets.QMenu(self)
        self.ms_context_menu.triggered.connect(self.ms_context_triggered)
        for ms in [f for f in os.listdir(MASTER_SCENES) if f.endswith(".ma")]:
            self.ms_context_menu.addAction(QtWidgets.QAction(ms, self))

    def create_layout(self):
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.ui_wgt)

        self.ui_wgt.save_scene_btn.setIcon(QtGui.QIcon(":save.png"))
        self.ui_wgt.make_screenshot_btn.setIcon(QtGui.QIcon(":snapshot.svg"))
        self.ui_wgt.cam_select_btn.setIcon(QtGui.QIcon(":camera.svg"))

        self.ui_wgt.refresh_layers_btn.setIcon(QtGui.QIcon(":refresh.png"))
        self.ui_wgt.remove_from_all_btn.setIcon(
            QtGui.QIcon(":deleteRenderPass.png"))

        self.ui_wgt.submite_scene_btn.setIcon(
            QtGui.QIcon(":greasePencilExport.png"))

    def create_connections(self):
        self.ui_wgt.save_scene_btn.clicked.connect(self.save_scene)
        self.ui_wgt.submite_scene_btn.clicked.connect(self.submitte_scene)
        self.ui_wgt.make_screenshot_btn.clicked.connect(self.make_screenshot)
        self.ui_wgt.cam_select_btn.clicked.connect(self.select_camera)
        self.ui_wgt.prep_scene_btn.clicked.connect(self.prep_scene)

        self.ui_wgt.refresh_layers_btn.clicked.connect(
            self.populate_render_layers)
        self.ui_wgt.remove_from_all_btn.clicked.connect(
            self.remove_from_all_layers)

        self.ui_wgt.season_cbx.currentIndexChanged.connect(
            self.populate_episodes)
        self.ui_wgt.episode_cbx.activated.connect(self.save_settings)
        self.ui_wgt.scene_name_led.returnPressed.connect(self.save_scene)
        self.ui_wgt.new_layer_name_led.returnPressed.connect(
            self.create_new_layer)

    @property
    def settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                return json.load(f)
        return self.default_settings

    @settings.setter
    def settings(self, value):
        if isinstance(value, dict):
            with open(self.settings_file, "w") as f:
                json.dump(value, f, indent=4)

    def save_settings(self):
        settings = {
            "season": self.ui_wgt.season_cbx.currentText(),
            "episode": self.ui_wgt.episode_cbx.currentText(),
        }
        self.settings = settings

    def populate_seasons(self):
        self.ui_wgt.season_cbx.clear()
        seasons = [s for s in os.listdir(
            RENDER_SCENES) if s.startswith("Season_")]
        self.ui_wgt.season_cbx.addItems(seasons)
        self.populate_episodes()

    def populate_episodes(self):
        self.ui_wgt.episode_cbx.clear()
        season = self.ui_wgt.season_cbx.currentText()
        episodes = [ep for ep in os.listdir(os.path.join(
            RENDER_SCENES, season)) if ep.startswith("s_")]
        self.ui_wgt.episode_cbx.addItems(episodes)

    def load_settings(self):
        if self.settings["season"]:
            self.set_season(self.settings["season"])
            self.set_episode(self.settings["episode"])

    def save_scene(self):
        shot = self.ui_wgt.scene_name_led.text()
        if shot:
            season = self.ui_wgt.season_cbx.currentText()
            ep = self.ui_wgt.episode_cbx.currentText()
            TurbozRenderSetup.save_scene(season, ep, shot)
            self.ui_wgt.scene_name_led.setText("")
            self.configure_widgets()

    def select_camera(self):
        cam = pm.selected()
        if cam:
            cam = cam[0]
            try:
                cam_node = cam.getShape()
                if cam_node.type() == "camera":
                    self.ui_wgt.camera_name_led.setText(cam.name())
                    TurbozRenderSetup.set_renderable(cam.name())
            except:
                return

    def prep_scene(self, ms=None):
        if not TurbozRenderSetup.master_scene_exists():
            if ms:
                TurbozRenderSetup.master_scene = ms
            TurbozRenderSetup.prep_scene()
            self.configure_widgets()

    def create_new_layer(self):
        layer_name = self.ui_wgt.new_layer_name_led.text()
        if layer_name:
            layer_empty = 1-self.ui_wgt.new_layer_global.isChecked()
            RenderLayers.create_layer(name=layer_name, empty=layer_empty)
            self.ui_wgt.new_layer_name_led.setText("")

    def populate_render_layers(self):
        self.clear_render_layers()
        for l in RenderLayers.list_layers():
            layer = TruebozRenderLayer(l)
            self.render_layers_lyt.addWidget(layer)

            self.render_layers.append(layer)

    def clear_render_layers(self):
        for layer in self.render_layers:
            layer.delete_script_jobs()

        self.render_layers = []

        while self.render_layers_lyt.count() > 0:
            light_item = self.render_layers_lyt.takeAt(0)
            if light_item.widget():
                light_item.widget().deleteLater()

    def remove_from_all_layers(self):
        for layer in self.render_layers:
            layer.remove_from_render_layer()

    def make_screenshot(self):
        directory, scene = os.path.split(pm.sceneName())
        scene = os.path.splitext(scene)[0]
        preview_dir = os.path.join(directory, "preview")
        TurbozRenderSetup.check_dir(preview_dir)
        screenshot = os.path.join(preview_dir, "{}_preview.png".format(scene))
        ScreenCapture.capture(screenshot)

        self.ui_wgt.screenshot_path_led.setText(screenshot)

    def get_scene_file(self):
        return os.path.abspath(str(pm.sceneName()))

    def get_output_dir(self):
        if self.scene_saved():
            scene_file = self.get_scene_file()
            render_dir = os.path.splitext(scene_file.replace(RENDER_SCENES, RENDERS))[0]
            TurbozRenderSetup.check_dir(render_dir)
            return render_dir

    def collect_layers(self):
        layers = []
        scene_file = self.get_scene_file()
        episode = self.ui_wgt.episode_cbx.currentText()
        comment = self.ui_wgt.comment_led.text()
        batch_name = "{}_{}".format(episode, os.path.splitext(os.path.split(scene_file)[-1])[0])
        for layer in self.render_layers:
            if layer.disable_cbx.isChecked():
                layer_frames = layer.frames
                layer_name = layer.layer.name()
                output_directory = os.path.join(self.get_output_dir(), layer_name)
                output_filename = "{}_{}.####.exr".format(batch_name, layer_name)
                lyr = MayaRenderLayer(
                    batch_name=batch_name,
                    layer_name=layer_name,
                    output_directory=output_directory,
                    output_filename=output_filename,
                    frames=layer_frames,
                    comment=comment,
                    )
                layers.append(lyr)
        return layers

    def submitte_maya_job(self, job_info):
        with DatabaseConnection("rendering", host=DBHOST):
            old_job = MayaJob.objects(scene_file=job_info["scene_file"])
            if old_job:
                self.update_maya_job(old_job, job_info)
                return
            job = MayaJob(
                        batch_name=job_info["batch_name"],
                        scene_file=job_info["scene_file"],
                        episode_name=job_info["episode_name"],
                        season=job_info["season"],
                        camera_name=job_info["camera_name"],
                        scene_preview=job_info["scene_preview"],
                        render_layers=job_info["render_layers"],
                        camera_list=job_info["camera_list"],
                    ).save()

            message = "Maya Job successfully submitted!\n\n\nName: {}".format(job_info["batch_name"])
            pm.confirmDialog(title='Submitted!', message=message, button=["Ok"])
            return

    def update_maya_job(self, job, job_info):
        job.update(**job_info)
        message = "Maya Job successfully updated!\n\n\nName: {}".format(job_info["batch_name"])
        pm.confirmDialog(title='Updated!', message=message, button=["Ok"])

    def submitte_scene(self):
        scene_file = self.get_scene_file()
        episode = self.ui_wgt.episode_cbx.currentText()
        if scene_file:
            job_info = {
            "batch_name": "{}_{}".format(episode, os.path.splitext(os.path.split(scene_file)[-1])[0]),
            "scene_file": scene_file,
            "episode_name": self.ui_wgt.episode_cbx.currentText(),
            "season": self.ui_wgt.season_cbx.currentText(),
            "camera_name": self.ui_wgt.camera_name_led.text(),
            "camera_list": TurbozRenderSetup.collect_cameras(),
            "scene_preview": self.ui_wgt.screenshot_path_led.text(),
            "render_layers": self.collect_layers(),
            }
            self.submitte_maya_job(job_info)
            return
        print("Scene is not saved!")

    def set_season(self, season):
        index = self.ui_wgt.season_cbx.findText(
            season, QtCore.Qt.MatchFixedString)
        if index:
            self.ui_wgt.season_cbx.setCurrentIndex(index)

    def set_episode(self, episode):
        index = self.ui_wgt.episode_cbx.findText(
            episode, QtCore.Qt.MatchFixedString)
        if index:
            self.ui_wgt.episode_cbx.setCurrentIndex(index)

    def set_screenshot(self):
        directory, scene = os.path.split(pm.sceneName())
        screenshot = os.path.join(directory, "preview", "{}_preview.png".format(os.path.splitext(scene)[0]))
        if os.path.isfile(screenshot):
            self.ui_wgt.screenshot_path_led.setText(screenshot)

    def configure_widgets(self):
        render_cam = TurbozRenderSetup.get_render_camera()
        self.ui_wgt.comment_led.setText("")
        if render_cam:
            self.ui_wgt.camera_name_led.setText(render_cam)
            TurbozRenderSetup.set_renderable(render_cam)

        if TurbozRenderSetup.master_scene_exists():
            self.ui_wgt.prep_scene_btn.setIcon(QtGui.QIcon(":confirm.png"))
            self.ui_wgt.prep_scene_btn.setEnabled(False)
        else:
            self.ui_wgt.prep_scene_btn.setIcon(QtGui.QIcon(":renderTarget.svg"))
            self.ui_wgt.prep_scene_btn.setEnabled(True)

        if self.scene_saved():
            self.ui_wgt.make_screenshot_btn.setEnabled(True)
            self.set_screenshot()
        else:
            self.ui_wgt.make_screenshot_btn.setEnabled(False)

    def create_script_jobs(self):
        self.script_jobs.append(pm.scriptJob(event=["renderLayerChange", partial(self.populate_render_layers)]))
        self.script_jobs.append(pm.scriptJob(event=["SceneOpened", partial(self.configure_widgets)]))

    def delete_script_jobs(self):
        for job_num in self.script_jobs:
            pm.scriptJob(kill=job_num)

        self.script_jobs = []

    def on_context_menu(self, point):
        self.ms_context_menu.exec_(self.ui_wgt.prep_scene_btn.mapToGlobal(point))

    def ms_context_triggered(self, action):
        if isinstance(action, QtWidgets.QAction):
            self.prep_scene(str(action.text()))

    def showEvent(self, e):
        super(TurbozRenderSetupWindow, self).showEvent(e)
        self.create_script_jobs()
        self.configure_widgets()
        if self.__geometry:
            self.restoreGeometry(self.__geometry)

    def closeEvent(self, e):
        if isinstance(self, TurbozRenderSetupWindow):
            super(TurbozRenderSetupWindow, self).closeEvent(e)
            self.save_settings()
            self.clear_render_layers()
            self.delete_script_jobs()
            self.__geometry = self.saveGeometry()


class EditableLabel(QtWidgets.QLineEdit):

    title_changed = QtCore.Signal(str)

    def __init__(self, title):
        super(EditableLabel, self).__init__()

        self._title = title
        self.setText(self.title)
        self.set_editable(False)

        self.returnPressed.connect(self.rename)

    def mouseDoubleClickEvent(self, e):
        super(EditableLabel, self).mouseDoubleClickEvent(e)
        self.set_editable(True)

    def rename(self):
        self.title = self.text()

    def set_editable(self, val):
        self.setReadOnly(1-val)
        if val:
            self.setStyleSheet("background-color: #668cb2; color: white")
        else:
            self.setStyleSheet("background-color: #2b2b2b; color: #48aab5")

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value
        self.title_changed.emit(value)
        self.set_editable(False)


class TruebozRenderLayer(QtWidgets.QWidget):
    def __init__(self, layer):
        super(TruebozRenderLayer, self).__init__()
        self._layer = layer
        self.script_jobs = []
        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.populate_frames()
        self.create_script_jobs()

    @property
    def layer(self):
        return self._layer

    @layer.setter
    def layer(self, layer):
        if layer.type() == "renderLayer":
            self._layer = layer

    @property
    def frames(self):
        return self.frames_led.text()

    def create_widgets(self):
        self.disable_cbx = QtWidgets.QCheckBox()
        self.disable_cbx.setChecked(self.layer.renderable.get())
        self.disable_cbx.setFixedSize(25, 25)
        self.disable_cbx.setToolTip("Renderable")

        self.view_layer = QtWidgets.QPushButton()
        self.view_layer.setIcon(QtGui.QIcon(":eye.png"))
        self.view_layer.setFixedSize(25, 25)
        self.view_layer.setFlat(True)

        self.to_rl_btn = QtWidgets.QPushButton()
        self.to_rl_btn.setIcon(QtGui.QIcon(":QR_add.png"))
        self.to_rl_btn.setFixedSize(25, 25)
        self.to_rl_btn.setFlat(True)
        self.to_rl_btn.setToolTip("Add selection to render layer")

        self.from_rl_btn = QtWidgets.QPushButton()
        self.from_rl_btn.setIcon(QtGui.QIcon(":nodeGrapherNext.png"))
        self.from_rl_btn.setFixedSize(25, 25)
        self.from_rl_btn.setFlat(True)
        self.from_rl_btn.setToolTip("Remove selection from render layer")

        self.delete_layer_btn = QtWidgets.QPushButton()
        self.delete_layer_btn.setIcon(QtGui.QIcon(":delete.png"))
        self.delete_layer_btn.setFixedSize(25, 25)
        self.delete_layer_btn.setFlat(True)
        self.delete_layer_btn.setToolTip("Delete render layer")

        self.layer_name = EditableLabel(self.layer.name())
        self.frames_lbl = QtWidgets.QLabel("Frames:")
        self.frames_led = QtWidgets.QLineEdit()
        self.frames_led.setPlaceholderText("Frames: 101-120, 130, 132")
        self.frames_led.setToolTip("List of frames to render.\n101-120, 130, 132")

    def create_layout(self):
        self.layout = QtWidgets.QHBoxLayout(self)
        # self.layout.addWidget(self.view_layer)
        self.layout.addWidget(self.disable_cbx)
        self.layout.addWidget(self.layer_name)
        self.layout.addWidget(self.frames_lbl)
        self.layout.addWidget(self.frames_led)
        self.layout.addWidget(self.to_rl_btn)
        self.layout.addWidget(self.from_rl_btn)
        self.layout.addWidget(self.delete_layer_btn)

    def create_connections(self):
        self.disable_cbx.stateChanged.connect(self.change_renderable)
        self.layer_name.title_changed.connect(self.rename_layer)
        self.frames_led.returnPressed.connect(self.frames_changed)

        self.to_rl_btn.clicked.connect(self.add_to_render_layer)
        self.from_rl_btn.clicked.connect(self.remove_from_render_layer)
        self.delete_layer_btn.clicked.connect(self.delete_layer)

    def rename_layer(self, title):
        if title:
            self.layer.rename(title)

    def change_renderable(self):
        self.layer.renderable.set(self.disable_cbx.isChecked())

    def populate_frames(self):
        try:
            frames = get_attr_in_layer(
                "vraySettings.animFrames", self.layer.name())
        except ValueError:
            frames = ""
        if frames:
            frames = str(frames)
        else:
            frames = ""
        self.frames_led.setText(frames)

    def frames_changed(self):
        if self.frames:
            settings_dict = {"animFrames": self.frames}
            RSManager.apply_settings_to_layer(settings_dict, self.layer.name())

    def find_layer(self, name):
        try:
            layer = RenderLayer.findLayerByName(name)
        except RuntimeError:
            layer = None
        finally:
            return layer

    def add_to_rl_bg(self, objects):
        for layer in ["BG", "CH", "FLOOR_AO", "WATER"]:
            layer = self.find_layer(layer)
            if layer:
                pm.editRenderLayerMembers(layer, objects)
        op = TurbozRenderSetup.find_vray_op("BG_OP")
        if op:
            op.addMembers(objects)

    def add_to_rl_ch(self, objects):
        for layer in ["CH", "FLOOR_AO", "Test"]:
            layer = self.find_layer(layer)
            if layer:
                pm.editRenderLayerMembers(layer, objects)
        op = TurbozRenderSetup.find_vray_op("CH_OP")
        if op:
            op.addMembers(objects)

    def add_to_rl_water(self, objects):
        for layer in ["CH", "WATER"]:
            layer = self.find_layer(layer)
            if layer:
                pm.editRenderLayerMembers(layer, objects)
        op = TurbozRenderSetup.find_vray_op("water_OP")
        if op:
            op.addMembers(objects)

    def add_to_render_layer(self):
        name = self.layer.name()
        objects = pm.selected()
        if objects:
            if name == "BG":
                self.add_to_rl_bg(objects)
            elif name == "CH":
                self.add_to_rl_ch(objects)
            elif name == "WATER":
                self.add_to_rl_water(objects)
            else:
                pm.editRenderLayerMembers(self.layer,  objects)

    def remove_from_render_layer(self):
        objects = pm.selected()
        if objects:
            pm.editRenderLayerMembers(self.layer,  objects, remove=True)

    def delete_layer(self):
        RenderLayers.delete_layer(self.layer.name())
        self.hide()
        self.setParent(None)
        self.deleteLater()
        self.delete_script_jobs()

    def on_renderable_changed(self):
        self.disable_cbx.setChecked(self.layer.renderable.get())

    def on_name_changed(self):
        self.layer_name.setText(self.layer.name())

    def create_script_jobs(self):
        self.delete_script_jobs()

        self.script_jobs.append(pm.scriptJob(attributeChange=[self.layer.renderable, partial(self.on_renderable_changed)]))
        self.script_jobs.append(pm.scriptJob(nodeNameChanged=[self.layer, partial(self.on_name_changed)]))

    def delete_script_jobs(self):
        for job_num in self.script_jobs:
            pm.evalDeferred("if pm.scriptJob(exists={0}):\tpm.scriptJob(kill={0}, force=True)".format(job_num))

        self.script_jobs = []


class TurbozRenderSetup(object):

    master_scene = "masterScene.ma"
    BUILTIN_RS = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "rs_built_in"))

    turboz_aov_list = [
        "diffuseChannel",
        "reflectChannel",
        "refractChannel",
        "specularChannel",
        "matteShadowChannel",
        "rawShadowChannel",
        "normalsChannel",
        "giChannel",
        "z_depth",
        "position",
        "ambient_occlusion",
        "UV",
        "light_select",
        "faceing_ratio",
        "crypto_object",
        "crypto_material",
        "crypto_asset",
    ]

    @staticmethod
    def check_dir(path):
        if not os.path.isdir(path):
            os.makedirs(path)

    @staticmethod
    def get_render_camera():
        for cam in pm.ls(type="camera"):
            if "cam_" in cam.name().lower():
                return cam.getTransform().name()
        return None

    @staticmethod
    def set_renderable(cam_name):
        for cam in pm.ls(type="camera"):
            if cam.getTransform().name() == cam_name:
                cam.renderable.set(1)
                continue
            cam.renderable.set(0)

    @staticmethod
    def set_actview_vis(value, attrs=list):
        flags = { i : value for i in attrs }
        pm.modelEditor("modelPanel4", e=True, **flags)

    @staticmethod
    def clear_lights():
        supported_lights = [
            "ambientLight",
            "directionalLight",
            "pointLight",
            "spotLight",
            "areaLight",
            "VRayLightRectShape",
            "VRayLightDomeShape",
            "VRayLightSphereShape",
        ]

        for lgt in pm.ls(type=supported_lights):
            if pm.referenceQuery(lgt, isNodeReferenced=True):
                lgt.visibility.set(0)
                lgt = lgt.getTransform()
                lgt.visibility.set(0)
                lgt.useOutlinerColor.set(1)
                lgt.outlinerColor.set((1,0,0))
            else:
                pm.delete(lgt.getTransform())

    @staticmethod
    def collect_cameras():
        cameras = pm.ls(type="camera", l=True)
        startup_cameras = [cam for cam in cameras if pm.camera(cam, startupCamera=True, q=True)]
        return [str(cam.parent(0).name()) for cam in cameras if cam not in startup_cameras]

    @staticmethod
    def find_vray_op(op_name):
        for op in pm.ls(type='VRayObjectProperties'):
            if op.name()==op_name:
                return op

    @classmethod
    def save_scene(cls, season, ep, shot):
        if str(shot).isdigit():
            shot = format(int(shot), '03')
        shot = "sc_{}".format(shot)
        scene_file = os.path.join(RENDER_SCENES, season, ep, "{}.ma".format(shot))
        if os.path.exists(scene_file):
            msg = pm.confirmDialog(title="Confirm", message="File exists, overwrite?", button=["Yes","No"], defaultButton="No", cancelButton="No", dismissString="No")
            if msg == "No":
                return
        pm.saveAs(scene_file)

    @classmethod
    def clear_scene(cls):
        cls.clear_lights()
        VrayAov.clear_aovs()
        RenderLayers.clear_layers()

    @classmethod
    def prep_scene(cls):
        RSManager.set_renderer("vray")
        cls.set_actview_vis(0, ["alo"])
        cls.set_actview_vis(1, ["ca", "pm", "lt"])
        RSManager.apply_settings(RSManager.defaults())
        pm.colorManagementPrefs(edit=True, cmEnabled=False)
        pm.setAttr("vraySettings.animFrames", "{}-{}".format(
            int(pm.playbackOptions(q=True, min=True)),
            int(pm.playbackOptions(q=True, max=True))
        ))
        pm.setAttr("defaultRenderGlobals.preMel", "evaluationManager -mode \"off\";")
        cls.clear_scene()
        RenderLayers.disable_master_layer()
        pm.importFile(os.path.join(MASTER_SCENES, cls.master_scene), defaultNamespace=True)
        pm.createNode("network", n="MasterSteneCreated")

    @classmethod
    def prep_scene_light(cls):
        RSManager.set_renderer("vray")
        cls.set_actview_vis(0, ["alo"])
        cls.set_actview_vis(1, ["ca", "pm", "lt"])
        RSManager.apply_settings(RSManager.defaults())
        pm.colorManagementPrefs(edit=True, cmEnabled=False)
        pm.delete(pm.ls(type=["imagePlane", "audio"]))

    @classmethod
    def master_scene_exists(cls):
        return "MasterSteneCreated" in [n.name() for n in pm.ls(type="network")]

    @classmethod
    @viewport_disabled
    def turboz_aovs(cls):
        VrayAov.clear_aovs()
        for aov in cls.turboz_aov_list:
            if aov == "crypto_object":
                VrayAov.crypto_object()
            elif aov == "crypto_material":
                VrayAov.crypto_material()
            elif aov == "crypto_asset":
                VrayAov.crypto_asset()
            elif aov == "ambient_occlusion":
                VrayAov.ambient_occlusion()
            elif aov == "position":
                VrayAov.position()
            elif aov == "z_depth":
                VrayAov.z_depth()
            elif aov == "UV":
                VrayAov.obj_uv()
            elif aov == "faceing_ratio":
                VrayAov.faceing_ratio()
            elif aov == "light_select":
                VrayAov.light_select()
            else:
                VrayAov.create_aov(aov)
        pm.select(None)

    @classmethod
    def create_object_properties(cls, sets=["BG_OP", "CH_OP"]):
        ops = [op.name() for op in pm.ls(type="VRayObjectProperties")]
        for s in sets:
            if not s in ops:
                pm.createNode("VRayObjectProperties", n=s)

    @classmethod
    def get_object_properties(cls, name):
        for op in pm.ls(type="VRayObjectProperties"):
            if op.name() == name:
                return op

    @classmethod
    def load_settings_dict(cls, name):
        settings_file = os.path.join(cls.BUILTIN_RS, name)
        if os.path.isfile(settings_file):
            with open(settings_file, "r") as rs:
                return json.load(rs)
