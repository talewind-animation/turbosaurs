import os
import json
from mongoengine.errors import NotUniqueError

import pymel.core as pm
from mongo_documents import DatabaseConnection, MayaLight, MayaLightPreset
from twa_maya.util.log_to_maya import *

DBHOST = os.getenv("DB_HOST", "192.168.99.2")


class LightPresetQuery(object):
    """
    CRUD light presets from db.
    """

    @classmethod
    def make_preset_dict(cls, preset_name, lights, scene=None, episode=None):
        """
        Return a light preset dictionary.
        Based on MayaLightPreset document

        Parameters
        ----------
        preset_name (str) : preset_name
        lights (list) : list of maya lights. LightPresetManager.collect_lights()
        scene (str) : scene name
        episode (str) : episode name

        Returns
        -------
        dict : light preset
        """
        preset_dict = {
                "name": preset_name,
                "lights": [MayaLight(**light) for light in lights],
            }
        if scene:
            preset_dict["scene"] = scene
        if episode:
            preset_dict["episode"] = episode

        return preset_dict

    @classmethod
    def save_preset(cls, preset_name, lights, scene=None, episode=None, update=True):
        """
        Save light preset to database by creating preset dictionary, and unpacking
        it to MayaLightPreset dockument. Update preset if it exists and update parameter is True

        Parameters
        ----------
        preset_name (str) : preset_name
        lights (list) : list of maya lights. LightPresetManager.collect_lights()
        scene (str) : scene name
        episode (str) : episode name
        update (bool) : if true update object if it already exists
        """
        preset = cls.make_preset_dict(preset_name, lights, scene, episode)

        with DatabaseConnection("rendering", host=DBHOST):
            try:
                MayaLightPreset(**preset).save()
                log_output("Light preset {} saved!".format(preset_name))
            except NotUniqueError:
                if update:
                    lgt_preset = MayaLightPreset.objects(name=preset_name).first()
                    lgt_preset.update(**preset)
                    log_output("Light preset {} updated!".format(preset_name))
                else:
                    log_error("Light preset name must be unique.")

    @classmethod
    def delete_preset(cls, preset_name):
        """
        Delete light preset if it exists.

        Parameters
        ----------
        preset_name (str) : preset_name
        """
        with DatabaseConnection("rendering", host=DBHOST):
            preset = MayaLightPreset.objects(name=preset_name).first()
            if preset:
                preset.delete()
                log_output("Light preset {} deleted!".format(preset_name))
                return

            log_warning("No preset named {}!".format(preset_name))


class LightPresetManager(object):
    """
    Export lights and attributes as dictionary.
    Load light presets to existing or create lights from preset dict.
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
        "shadowColor",
        "emitDiffuse",
        "emitSpecular",
    ]

    @staticmethod
    def make_xform_matrix(xform_list):
        """
        Converts the list of transformations to pymel.core.datatypes.TransformationMatrix

        Parameters
        ----------
        list : List of transformations

        Returns
        -------
        pymel.core.datatypes.TransformationMatrix : TransformationMatrix
        """
        return pm.datatypes.TransformationMatrix(xform_list)

    @staticmethod
    def get_rotation(xform):
        """
        Returns rotation in degrees from TransformationMatrix.
        Using pymel.core.datatypes.TransformationMatrix.getRotation

        Parameters
        ----------
        pymel.core.datatypes.TransformationMatrix : TransformationMatrix

        Returns
        -------
        list : List of roations in degrees
        """
        return [pm.datatypes.degrees(rot) for rot in xform.getRotation()]

    @classmethod
    def list_lights(cls):
        """
        Return list of all the supported lights in the scene.

        Returns
        -------
        list : List of supported lights
        """
        return pm.ls(type=cls.supported_lights)

    @classmethod
    def collect_light_attributes(cls, light):
        """
        Collect all the supported attributes from a light.

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
    def get_light_xform(cls, light):
        """
        Get transform node from the light. Return list of light transformations.
        Converting TransformationMatrix to list to make it json compatible.

        Parameters
        ----------
        light (light node) : A light to get xform from

        Returns
        -------
        list : light TransformationMatrix as list
        """
        return [list(transform) for transform in light.getTransform().getTransformation()]

    @classmethod
    def get_light_info(cls, light):
        """
        Return a dictionary with light name, type, attributes and xform

        Parameters
        ----------
        light (light node) : A light to get info from

        Returns
        -------
        dict : light info
        """
        return {
                    "name": light.getTransform().name(),
                    "light_type": light.type(),
                    "attributes": cls.collect_light_attributes(light),
                    "xform": cls.get_light_xform(light),
                }

    @classmethod
    def collect_lights(cls):
        """
        Return a list with all lights and their infos

        Returns
        -------
        list : list of light infos
                ex. [{"name": 'directionalLight2',
                    'attributes': {'color': (1.0), 'intensity': 1.0},
                    'xform': [1.50488544412, -6.83323748282, -5.21150706185, 0.0]}]
        """
        return [cls.get_light_info(light) for light in cls.list_lights()]
