import os
import json

import pymel.core as pm
from pymel.core.nodetypes import RenderLayer
import maya.mel as mel

from helpers.utility import viewport_disabled


class RenderSettingsManager(object):

    DEFAULTS = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "vray_defaults.json"))

    @staticmethod
    def settings_node():
        return pm.PyNode("vraySettings")

    @staticmethod
    def set_renderer(renderer="vray"):
        if not pm.getAttr("defaultRenderGlobals.currentRenderer") == renderer:
            if renderer == "vray":
                mel.eval("vrayCreateVRaySettingsNode();")
            pm.setAttr("defaultRenderGlobals.currentRenderer", l=False)
            pm.setAttr("defaultRenderGlobals.currentRenderer",
                       renderer, type="string")
            if pm.window("unifiedRenderGlobalsWindow", q=True, exists=True):
                pm.deleteUI("unifiedRenderGlobalsWindow")
                mel.eval('unifiedRenderGlobalsWindow;')

    @staticmethod
    def compare_colors(a, b):
        return True in [a[i] == b[i] for i in range(len(a))]

    @classmethod
    def defaults(cls):
        with open(cls.DEFAULTS, "r") as f:
            return json.load(f)

    @classmethod
    def modified_settings(cls):
        modified = {}
        default_settings = cls.defaults()
        for attribute in default_settings.keys():
            value = cls.settings_node().attr(attribute).get()
            if isinstance(value, tuple):
                if not cls.compare_colors(value, default_settings[attribute]):
                    modified[attribute] = value
                continue
            if value != default_settings[attribute]:
                modified[attribute] = value
        return modified

    @classmethod
    def all_settings(cls):
        settings = {}
        default_settings = cls.defaults()
        for attribute in default_settings.keys():
            value = cls.settings_node().attr(attribute).get()
            settings[attribute] = value
        return settings

    @classmethod
    def apply_settings(cls, settings_dict):
        for attribute, value in settings_dict.iteritems():
            cls.settings_node().attr(attribute).set(value)

    @classmethod
    @viewport_disabled
    def apply_settings_to_layer(cls, settings_dict, render_layer):
        current_layer = pm.editRenderLayerGlobals(
            query=True, currentRenderLayer=True)
        pm.editRenderLayerGlobals(currentRenderLayer=render_layer)
        for attribute, value in settings_dict.iteritems():
            attribute = cls.settings_node().attr(attribute)
            pm.editRenderLayerAdjustment(attribute, layer=render_layer)
            attribute.set(value)
        pm.editRenderLayerGlobals(currentRenderLayer=current_layer)


class VrayRenderElements(object):
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

    @classmethod
    def list_aovs(cls, sc=False):
        """
        List all vray render elements

        Parameters
        ----------
        sc (bool) : List only elements in current scene

        Returns
        -------
        list : List of vray render element nodes
        """

        if sc:
            return pm.vray("getRenderElementsInScene", 0)
        return pm.vray("getRenderElements")

    @classmethod
    def create_aov(cls, aov_type):
        """
        Create a vray render element

        Parameters
        ----------
        aov_type (str) : render element name

        Returns
        -------
        vrayRenderElement node
        """

        aov = mel.eval("vrayAddRenderElement {}".format(aov_type))
        return pm.PyNode(aov)

    @classmethod
    def clear_aovs(cls):
        """
        Delete all vray render elements from the scene.
        Also delete all the connections to "vray_texture_extratex" attribute
        """

        for aov in cls.list_aovs(sc=True):
            aov = pm.PyNode(aov)
            if aov.hasAttr("vray_texture_extratex"):
                pm.delete(aov.listHistory())
            else:
                pm.delete(aov)

    @classmethod
    def crypto_object(cls):
        aov = cls.create_aov("cryptomatteChannel")
        aov.vray_name_cryptomatte.set("crypto_object")
        aov.vray_idtype_cryptomatte.set(2)
        aov.vray_add_root_name_cryptomatte.set(1)

    @classmethod
    def crypto_asset(cls):
        aov = cls.create_aov("cryptomatteChannel")
        aov.vray_name_cryptomatte.set("crypto_asset")
        aov.vray_idtype_cryptomatte.set(4)
        aov.vray_add_root_name_cryptomatte.set(2)

    @classmethod
    def crypto_material(cls):
        aov = cls.create_aov("cryptomatteChannel")
        aov.vray_name_cryptomatte.set("crypto_material")
        aov.vray_idtype_cryptomatte.set(1)
        aov.vray_add_root_name_cryptomatte.set(2)

    @classmethod
    def ambient_occlusion(cls):
        occlusion = cls.create_aov("ExtraTexElement")
        occlusion.rename("AmbientOcclusion")

        occlusion.vray_explicit_name_extratex.set("AmbientOcclusion")
        occlusion.vray_affectmattes_extratex.set(0)

        vray_dirt = pm.shadingNode("VRayDirt", n="occ_dirt", asTexture=True)
        vray_dirt.subdivs.set(3)

        vray_dirt.outColor >> occlusion.vray_texture_extratex

    @classmethod
    def position(cls):
        p_pos = cls.create_aov("ExtraTexElement")
        p_pos.rename("P_World")

        p_pos.vray_explicit_name_extratex.set("PWorld")
        p_pos.vray_affectmattes_extratex.set(0)
        p_pos.vray_considerforaa_extratex.set(0)
        p_pos.vray_filtering_extratex.set(0)

        sampler_info_p = pm.shadingNode(
            "samplerInfo", n="p_world_samplerInfo", asUtility=True)

        sampler_info_p.pointWorldX >> p_pos.vray_texture_extratexR
        sampler_info_p.pointWorldY >> p_pos.vray_texture_extratexG
        sampler_info_p.pointWorldZ >> p_pos.vray_texture_extratexB

    @classmethod
    def obj_uv(cls):
        uv = cls.create_aov("ExtraTexElement")
        uv.rename("UV")
        uv.vray_explicit_name_extratex.set("UV")

        uv.vray_considerforaa_extratex.set(0)
        uv.vray_affectmattes_extratex.set(0)
        uv.vray_filtering_extratex.set(0)

        place2d = pm.shadingNode(
            "place2dTexture", n="UV_placer", asUtility=True)

        place2d.outU >> uv.vray_texture_extratexR
        place2d.outV >> uv.vray_texture_extratexG

    @classmethod
    def faceing_ratio(cls):
        faceing = cls.create_aov("ExtraTexElement")
        faceing.rename("faceingRatio")
        faceing.vray_explicit_name_extratex.set("faceingRatio")
        faceing.vray_affectmattes_extratex.set(0)

        sampler_info_fr = pm.shadingNode(
            "samplerInfo", n="faceingRatio_samplerInfo", asUtility=True)

        sampler_info_fr.facingRatio >> faceing.vray_texture_extratexR

    @classmethod
    def z_depth(cls):
        z = cls.create_aov("zdepthChannel")
        z.vray_depthFromCamera_zdepth.set(1)
        z.vray_depthClamp.set(0)
        z.vray_filtering_zdepth.set(0)

    @classmethod
    def __light_select(cls, lgt_list, name):
        lgt_aov = cls.create_aov("LightSelectElement")
        lgt_aov.rename("{}_Light_Select".format(name))
        lgt_aov.vray_name_lightselect.set("{}_light".format(name))
        lgt_aov.vray_considerforaa_lightselect.set(1)
        lgt_aov.vray_type_lightselect.set(1)
        lgt_aov.addMembers(lgt_list)

    @classmethod
    def collect_lights(cls):
        return [lgt for lgt in pm.ls(type=cls.supported_lights)
                if not lgt.name().startswith("default") and len(lgt.name().split("_", 1)) > 1]

    @classmethod
    def sort_lights_by_aovname(cls):
        light_dict = {}
        for lgt in cls.collect_lights():
            name = lgt.name().split("_", 1)[0]
            if name in light_dict.keys():
                light_dict[name].append(lgt)
            else:
                light_dict[name] = [lgt]
        return light_dict

    @classmethod
    def light_select(cls):
        for name, lgt_list in cls.sort_lights_by_aovname().iteritems():
            cls.__light_select(lgt_list, name)


class RenderLayers(object):

    @classmethod
    def create_layer(cls, name="renderLayer", empty=True):
        """
        Create render layer

        Parameters
        ----------
        name (str) : Name of layer to be created
        empty (bool) : Determines if layer is global or just an empty layer

        Returns
        -------
        RenderLayer : Newly created layer
        """

        if not name in [l.name() for l in pm.ls(type="renderLayer")]:
            return pm.createRenderLayer(n=name, empty=True, g=1-empty)

    @classmethod
    def clear_layers(cls):
        """
        Clear all layer in the scene
        """

        for layer in cls.list_layers():
            cls.delete_layer(layer)

    @classmethod
    def delete_layer(cls, layer_name):
        """
        Delete layer by name.

        Parameters
        ----------
        layer_name (str) : Name of layer to delete
        """

        if RenderLayer.currentLayer().name() == layer_name:
            pm.editRenderLayerGlobals(
                currentRenderLayer=RenderLayer.defaultRenderLayer())
        pm.delete(RenderLayer.findLayerByName(layer_name))

    @classmethod
    def toggle_layer(cls, layer_name):
        """
        Toggle renderable state of a layer

        Parameters
        ----------
        layer_name (str) : Name of layer to set renderable flag
        """

        renderable = RenderLayer.findLayerByName(layer_name).renderable
        renderable.set(1-renderable.get())

    @classmethod
    def disable_layer(cls, layer_name):
        """
        Disable a layer

        Parameters
        ----------
        layer_name (str) : Name of layer to disable
        """

        render_layer = RenderLayer.findLayerByName(layer_name)
        render_layer.renderable.set(0)

    @classmethod
    def disable_master_layer(cls):
        cls.disable_layer(RenderLayer.defaultRenderLayer().name())

    @classmethod
    def list_layers(cls):
        """
        List all render layers except master layer

        Returns
        -------
        list : List of render layers
        """
        return [layer for layer in reversed(RenderLayer.listAllRenderLayers()) if layer.renderable.get()==1 and layer != RenderLayer.defaultRenderLayer()]
