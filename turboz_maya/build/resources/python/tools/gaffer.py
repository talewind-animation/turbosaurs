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
from shiboken2 import wrapInstance, getCppPointer

from maya.OpenMayaUI import MQtUtil
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

import pymel.core as pm
import maya.cmds as cmds

UI_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "gaffer.ui"))

class GafferWindow(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):

    UI_NAME = "TWA_GafferWindow_UI"
    dlg_instance = None
    prefix = "__gfr_"
    settings_file = os.path.join(tempfile.gettempdir(), "__TWA_gaffer_settings.json")
    default_settings = {
        "preset_paths": {
        # name: path
        },
        "root": None
    }

    @classmethod
    def display(cls):
        if not cls.dlg_instance:
            cls.dlg_instance = GafferWindow()

        if cls.dlg_instance.isHidden():
            uiScript="from tools.gaffer import GafferWindow\n\
            dlg = GafferWindow()"

            cls.dlg_instance.show(dockable=True, uiScript=uiScript)
        else:
            cls.dlg_instance.raise_()
            cls.dlg_instance.activateWindow()

    def __init__(self):
        super(GafferWindow, self).__init__()

        self.setObjectName(self.UI_NAME)

        self.__geometry = None

        self.configure_window()
        self.create_widgets()
        self.create_layout()
        self.create_connections()

        self.load_settings()
        self.populate_preset_paths()
        self.populate_presets()
        self.set_gaffer_status()

        self.to_maya_lyt()

    def configure_window(self):
        self.setWindowTitle("TWA Light Create")
        self.resize(650, 400)

    def create_widgets(self):
        self.menu_bar = QtWidgets.QMenuBar()
        self.menu_bar.setNativeMenuBar(False)
        self.file_menu = QtWidgets.QMenu("File")
        self.exit_action = QtWidgets.QAction("Exit")
        self.set_path_menu = QtWidgets.QMenu("Set preset path")
        self.del_path_menu = QtWidgets.QMenu("Delete preset path")

        self.wgt = _QtUiTools.QUiLoader().load(UI_FILE)
        self.wgt.lgt_preset_dlg_btn.setIcon(QtGui.QIcon(":openScript.png"))
        self.wgt.remove_gfr_btn.setIcon(QtGui.QIcon(":delete.png"))
        self.wgt.delete_lgt_preset_btn.setIcon(QtGui.QIcon(":delete.png"))
        self.wgt.create_rect_btn.setIcon(QtGui.QIcon(":arealight.png"))
        self.wgt.create_spot_btn.setIcon(QtGui.QIcon(":spotlight.png"))
        self.wgt.create_dir_btn.setIcon(QtGui.QIcon(":directionallight.png"))
        self.wgt.create_ambient_btn.setIcon(QtGui.QIcon(":ambientlight.png"))

        self.wgt.presets_paths_led.setEnabled(False)

    def create_layout(self):
        self.file_menu.addMenu(self.set_path_menu)
        self.file_menu.addMenu(self.del_path_menu)
        self.file_menu.addAction(self.exit_action)
        self.menu_bar.addMenu(self.file_menu)
        self.setMenuBar(self.menu_bar)
        self.setCentralWidget(self.wgt)

    def load_settings(self):
        if not os.path.exists(self.settings_file):
            return
        try:
            self.root = self.settings["preset_paths"][self.settings["root"]]
        except KeyError:
            self.root = ""

    def create_connections(self):
        self.exit_action.triggered.connect(self.close)
        self.set_path_menu.triggered.connect(self.set_path_triggered)
        self.del_path_menu.triggered.connect(self.del_path_triggered)

        self.wgt.lgt_preset_dlg_btn.clicked.connect(self.chenge_root_dir)
        self.wgt.gaffer_btn.clicked.connect(self.create_gaffer)
        self.wgt.remove_gfr_btn.clicked.connect(self.delete_gaffer)
        self.wgt.lgt_preset_export_btn.clicked.connect(self.export_light_preset)
        self.wgt.lgt_preset_name_led.returnPressed.connect(self.export_light_preset)
        self.wgt.delete_lgt_preset_btn.clicked.connect(self.delete_light_preset)

        self.wgt.lgt_presets_list.itemDoubleClicked.connect(self.load_light_preset)

        self.wgt.create_rect_btn.clicked.connect(partial(Gaffer.create_light, "VRayLightRectShape"))
        self.wgt.create_spot_btn.clicked.connect(partial(Gaffer.create_light, "spotLight"))
        self.wgt.create_dir_btn.clicked.connect(partial(Gaffer.create_light, "directionalLight"))
        self.wgt.create_ambient_btn.clicked.connect(partial(Gaffer.create_light, "ambientLight"))

    @property
    def root(self):
        root = self.wgt.presets_paths_led.text()
        if os.path.isdir(root):
            return root
        return ""

    @root.setter
    def root(self, value):
        if value:
            if os.path.isdir(value):
                self.wgt.presets_paths_led.setText(value)
            else:
                self.wgt.presets_paths_led.setText(self.root)
            self.populate_presets()

    @property
    def preset_name(self):
        text = self.wgt.lgt_preset_name_led.text()
        return text.replace(" ", "_") if text else None

    @preset_name.setter
    def preset_name(self, value):
        self.wgt.lgt_preset_name_led.setText(value)
        self.populate_presets()

    @property
    def preset(self):
        item = self.wgt.lgt_presets_list.currentItem()
        if item:
            name = item.text()
            preset_file = os.path.join(self.root, "{}{}".format(self.prefix, name), "{}.gfr".format(name))
            if os.path.exists(preset_file):
                return preset_file

        return None

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

    def chenge_root_dir(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory", self.root)
        if directory:
            self.root = directory
            name = os.path.split(directory)[-1]
            temp_settings = self.settings
            temp_settings["preset_paths"][name] = directory
            temp_settings["root"] = name
            self.settings = temp_settings
            self.populate_preset_paths()

    def populate_presets(self):
        self.wgt.lgt_presets_list.clear()
        if self.root:
            presets = [p.replace(self.prefix, "") for p in os.listdir(self.root) if p.startswith(self.prefix)]
            self.wgt.lgt_presets_list.addItems(presets)

    def populate_preset_paths(self):
        self.set_path_menu.clear()
        self.del_path_menu.clear()
        paths = self.settings["preset_paths"].keys()
        if paths:
            for p in paths:
                self.set_path_menu.addAction(p)
                self.del_path_menu.addAction(p)

    def set_gaffer_status(self):
        if Gaffer.gaffer_exists():
            self.wgt.gaffer_btn.setEnabled(False)
            self.wgt.lgt_preset_export_btn.setEnabled(True)
            self.wgt.lgt_preset_name_led.setEnabled(True)
            self.wgt.gaffer_btn.setIcon(QtGui.QIcon(":confirm.png"))
        else:
            self.wgt.gaffer_btn.setEnabled(True)
            self.wgt.lgt_preset_export_btn.setEnabled(False)
            self.wgt.lgt_preset_name_led.setEnabled(False)
            self.wgt.gaffer_btn.setIcon(QtGui.QIcon(":error.png"))

    def create_gaffer(self):
        Gaffer.create_gaffer()
        self.set_gaffer_status()

    def delete_gaffer(self):
        Gaffer.delete_gaffer()
        self.set_gaffer_status()

    def export_light_preset(self):
        if Gaffer.gaffer_exists():
            preset_dir = os.path.join(self.root, "{}{}".format(self.prefix, self.preset_name))
            preset_file = os.path.join(preset_dir, "{}.gfr".format(self.preset_name))
            self.create_folder(preset_dir)

            with open(preset_file, "w") as f:
                json.dump(Gaffer.collect_lights(), f, indent=4)

            self.preset_name=""

    def load_light_preset(self):
        if self.preset:
            with open(self.preset, "r") as f:
                Gaffer.parse_lights(json.load(f))
                Gaffer.rename(os.path.splitext(os.path.split(self.preset)[-1])[0])

    def delete_light_preset(self):
        if self.preset:
            preset_dir = os.path.dirname(self.preset)
            for file in os.listdir(preset_dir):
                os.remove(os.path.join(preset_dir, file))
            os.rmdir(preset_dir)
        self.populate_presets()

    def create_folder(self, path):
        if not os.path.isdir(path):
            os.makedirs(path)

    def set_path_triggered(self, action):
        paths = self.settings["preset_paths"].keys()
        if not paths:
            return
        if isinstance(action, QtWidgets.QAction):
            action_name = action.text()
            if action_name in paths:
                self.root = self.settings["preset_paths"][action_name]
                temp_settings = self.settings
                temp_settings["root"] = action_name
                self.settings = temp_settings

    def del_path_triggered(self, action):
        paths = self.settings["preset_paths"].keys()
        if not paths:
            return
        if isinstance(action, QtWidgets.QAction):
            action_name = action.text()
            if action_name in paths:
                temp_settings = self.settings
                temp_settings["preset_paths"].pop(action_name, None)
                if temp_settings["preset_paths"].keys():
                    temp_settings["root"] = temp_settings["preset_paths"].keys()[0]
                else:
                    temp_settings["root"] = ""
                self.settings = temp_settings

                if self.settings["preset_paths"].keys():
                    self.root = self.settings["preset_paths"][self.settings["root"]]
                else:
                    self.wgt.presets_paths_led.setText("")
                    self.root = "text"
                self.populate_preset_paths()

    def to_maya_lyt(self):
        workspace_control_name = "{}WorkspaceControl".format(self.UI_NAME)
        if cmds.workspaceControl(workspace_control_name, q=True, exists=True):
            workspace_control_ptr = long(MQtUtil.findControl(workspace_control_name))
            widget_ptr = long(getCppPointer(self)[0])

            MQtUtil.addWidgetToMayaLayout(widget_ptr, workspace_control_ptr)

    def showEvent(self, e):
        super(GafferWindow, self).showEvent(e)
        self.set_gaffer_status()
        self.preset_name = cmds.file(query=True, sceneName=True, shortName=True)
        if self.__geometry:
            self.restoreGeometry(self.__geometry)

    def closeEvent(self, e):
        if isinstance(self, GafferWindow):
            super(GafferWindow, self).closeEvent(e)

            self.__geometry = self.saveGeometry()


class Gaffer(object):
    """
    Create and store maya lights in dictionary.
    """
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

    supported_attributes = [
        "color",
        "intensity",
        "ambientShade",
        "emitDiffuse",
        "emitSpecular",
        "decayRate",
        "coneAngle",
        "penumbraAngle",
        "dropoff",
        "shadowColor",
        "colorMode",
        "lightColor",
        "temperature",
        "intensityMult",
        "units",
        "shapeType",
        "uSize",
        "vSize",
        "directional",
        "directionalPreviewLength",
        "directionalPreview",
        "useRectTex",
        "multiplyByTheLightColor",
        "rectTex",
        "rectTexA",
        "texResolution",
        "texAdaptive",
        "showTex",
        "noDecay",
        "doubleSided",
        "invisible",
        "skylightPortal",
        "simpleSkylightPortal",
        "storeWithIrradianceMap",
        "affectDiffuse",
        "affectSpecular",
        "affectReflections",
        "affectAlpha",
        "diffuseContrib",
        "specularContrib",
        "cutoffThreshold",
        "shadows",
        "shadowBias",
        "shadowColor",
        "causticsSubdivs",
        "causticMult",
        "domeSpherical",
        "domeAdaptive",
        "useDomeTex",
        "domeTex",
        "domeTexA",
        "domeTargetRadius",
        "domeEmitDistance",
        "radius",
        "sphereSegments",
        ]

    node_name = 'LightCreate'
    name_attribute = "{}_name".format(node_name)

    @classmethod
    def create_gaffer(cls):
        """
        Greate a Gaffer. Creates a network node(Gaffer)
        and connects an empty transform node to it(gaffer rig).
        Gaffer rig will be exported as preset or replaced by a preset.

        Returns
        -------
        List: gaffer root(network node), gaffer rig(transform node)
        """

        if cls.gaffer_exists():
            return cls.get_gaffer()

        gaffer = pm.createNode("network", n="{}_root".format(cls.node_name))
        gaffer.addAttr(cls.name_attribute, dt="string")
        gaffer.attr(cls.name_attribute).set(cls.node_name)

        gaffer_rig = pm.createNode("transform", n="{}_rig".format(cls.node_name))
        gaffer_rig.addAttr(cls.name_attribute, dt="string")
        gaffer_rig.useOutlinerColor.set(1)
        gaffer_rig.outlinerColor.set((1,.55,0))

        gaffer.attr(cls.name_attribute) >> gaffer_rig.attr(cls.name_attribute)

        pm.select(None)

        return [gaffer, gaffer_rig]

    @classmethod
    def gaffer_exists(cls):
        """
        Check if gaffer exists in the scene buy finding the gaffer root(network node)
        """

        for network in pm.ls(type="network"):
            if (network.hasAttr(cls.name_attribute) and
            network.attr(cls.name_attribute).listConnections()):
                return True

        return False

    @classmethod
    def get_gaffer(cls):
        """
        Find gaffer root(network node).
        If gaffer exists and valid retrun root and rig. If Theres no gaffer in the scene create one.

        Returns
        -------
        List: gaffer root(network node), gaffer rig(transform node)
        """

        for network in pm.ls(type="network"):
            if network.hasAttr(cls.name_attribute):
                gaffer = network
                gaffer_rig = gaffer.attr(cls.name_attribute).listConnections()
                if gaffer_rig:
                    gaffer_rig = gaffer_rig[0]
                    return [gaffer, gaffer_rig]
                else:
                    pm.delete(gaffer)

        return cls.create_gaffer()

    @classmethod
    def delete_gaffer(cls):
        """
        Deletes gaffer root, rig and all children if it exists.
        """
        if cls.gaffer_exists():
            gr, gt = cls.get_gaffer()
            cls.clear_children(gt)
            pm.delete([gr, gt])

    @classmethod
    def clear_children(cls, parent):
        """
        Crear all the children under a parent directory

        Parameters
        ----------
        parent (transform) : group which children ill be deleted
        """

        for child in parent.listRelatives(ad=True):
            for node in child.listHistory():
                pm.delete(node)

    @classmethod
    def create_light(cls, lgt_type="directionalLight"):
        """
        Create a light and place it under gaffer rig.

        Parameters
        ----------
        lgt_type (str) : Light type to create
        """
        if cls.gaffer_exists() and lgt_type in cls.supported_lights:
            gr, gt = cls.get_gaffer()
            lgt = pm.shadingNode(lgt_type, asLight=True)
            pm.parent(lgt, gt)

    @classmethod
    def __collect_lights(cls, root_node, tree):
        name = root_node.name()
        tree[name] = {}

        light = root_node.getShape()

        # light attrs
        if light and light.type() in cls.supported_lights:
            tree[name]["type"] = light.type()
            tree[name]["light_attr"] = cls.__collect_light_attributes(light)
        else:
            tree[name]["type"] = "transform"
            tree[name]["light_attr"] = None

        # transformations
        tree[name]["xform"] = [list(t) for t in root_node.getTransformation()]

        # child nodes
        children = pm.listRelatives(root_node, c=True, type="transform")
        if children:
            tree[name]["children"] = {}
            for child in children:
                cls.__collect_lights(child, tree[name]['children'])
        else:
            tree[name]['children'] = None

    @classmethod
    def __collect_light_attributes(cls, light):
        """
        Collect all the supported attributes from a light in a dictionary.

        Parameters
        ----------
        light (light node) : A light to collect attributes from

        Returns
        -------
        dict : Dictionary with all the light attributes
        """

        return {attribute:light.getAttr(attribute) for attribute
                in cls.supported_attributes if light.hasAttr(attribute)}

    @classmethod
    def apply_light_attributes(cls, light, attributes_dict):
        """
        Apply attributes to light from light attribute dictionary

        Parameters
        ----------
        light (light node) : A light to apply attributes to.
        attributes_dict (dict) : A gictionary ex: {"attribute_name": "value"}
        """

        for attribute, value in attributes_dict.items():
            if light.hasAttr(attribute):
                light.attr(attribute).set(value)

    @classmethod
    def collect_lights(cls):
        if cls.gaffer_exists():
            gr, gt = cls.get_gaffer()
            gaffer_hierarchy = {}
            cls.__collect_lights(gt, gaffer_hierarchy)
            return gaffer_hierarchy

        return None

    @classmethod
    def __parse_lights(cls, light_dict, parent_node=None):
        for root_node, data in light_dict.iteritems():
            # Node creation
            if data["type"] == "transform":
                node = pm.createNode("transform", n=root_node)
            else:
                node = pm.shadingNode(data["type"], asLight=True, n='{}Shape'.format(root_node))
                pm.rename(node, root_node)

            # parenting
            if parent_node:
                pm.parent(node, parent_node, relative=True)

            # xform
            node.setTransformation(data["xform"])

            if data["light_attr"]:
                cls.apply_light_attributes(node.getShape(), data["light_attr"])

            # build nodes recursively for all children
            if data["children"]:
                for child, data in data["children"].items():
                    cls.__parse_lights({child: data}, node)

    @classmethod
    def parse_lights(cls, light_dict):
        if cls.gaffer_exists():
            gr, gt = cls.get_gaffer()
            cls.clear_children(gt)
            gt_param = light_dict[light_dict.keys()[0]]
            gt.setTransformation(gt_param["xform"])
            gt_children = gt_param["children"]
            if gt_children:
                for child, data in gt_children.items():
                    cls.__parse_lights({child: data}, gt)

        pm.select(None)

    @classmethod
    def rename(cls, name):
        """
        Rename gaffer rig

        Parameters
        ----------
        name (str) : New name
        """

        if cls.gaffer_exists():
            gr, gt = cls.get_gaffer()
            pm.rename(gt, name)
