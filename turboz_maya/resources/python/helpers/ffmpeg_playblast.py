import os
import sys
import copy
import tempfile
import traceback
import datetime

from Qt import (
    QtCore,
    QtGui
)

import pymel.core as pm
import maya.cmds as cmds

from twa_maya.util.log_to_maya import MayaQtLogger
import maya.mel as mel

class HrPlayblast(QtCore.QObject):

    VERSION = "0.0.1"

    DEFAULT_FFMPEG_PATH = os.path.abspath(os.getenv("FFMPEG_PATH", "Z:\\Projects\\RnD\\ffmpeg\\ffmpeg.exe"))

    RESOLUTION_LOOKUP = {
        "HD 1080": (1920, 1080),
        "HD 720": (1280, 720),
        "HD 540": (960, 540),
    }

    FRAME_RANGE_PRESETS = [
        "Playback",
        "Animation",
    ]

    VIDEO_ENCODER_LOOKUP = {
        "mov": ["h264"],
        "mp4": ["h264"],
        "Image": ["jpg", "png", "tif"],
    }

    H264_QUALITIES = {
        "Very High": 18,
        "High": 20,
        "Medium": 23,
        "Low": 26,
    }

    H264_PRESETS = [
        "veryslow",
        "slow",
        "medium",
        "fast",
        "faster",
        "ultrafast",
    ]

    VIEWPORT_VISIBILITY_LOOKUP = [
        # ["Controllers", "controllers"],
        ["NURBS Curves", "nurbsCurves"],
        ["NURBS Surfaces", "nurbsSurfaces"],
        ["NURBS CVs", "cv"],
        ["NURBS Hulls", "hulls"],
        ["Polygons", "polymeshes"],
        ["Subdiv Surfaces", "subdivSurfaces"],
        ["Planes", "planes"],
        ["Lights", "lights"],
        ["Cameras", "cameras"],
        ["Image Planes", "imagePlane"],
        ["Joints", "joints"],
        ["IK Handles", "ikHandles"],
        ["Deformers", "deformers"],
        ["Dynamics", "dynamics"],
        ["Particle Instancers", "particleInstancers"],
        ["Fluids", "fluids"],
        ["Hair Systems", "hairSystems"],
        ["Follicles", "follicles"],
        ["nCloths", "nCloths"],
        ["nParticles", "nParticles"],
        ["nRigids", "nRigids"],
        ["Dynamic Constraints", "dynamicConstraints"],
        ["Locators", "locators"],
        ["Dimensions", "dimensions"],
        ["Pivots", "pivots"],
        ["Handles", "handles"],
        ["Texture Placements", "textures"],
        ["Strokes", "strokes"],
        ["Motion Trails", "motionTrails"],
        ["Plugin Shapes", "pluginShapes"],
        ["Clip Ghosts", "clipGhosts"],
        ["Grease Pencil", "greasePencils"],
        ["Grid", "grid"],
        ["HUD", "hud"],
        ["Hold-Outs", "hos"],
        ["Selection Highlighting", "sel"],
    ]

    VIEWPORT_VISIBILITY_PRESETS = {
        "Viewport": [],
        "Geo": ["NURBS Surfaces", "Polygons"],
        "Blast": ["NURBS Surfaces", "Polygons", "Plugin Shapes"],
        "Dynamics": ["NURBS Surfaces", "Polygons", "Dynamics", "Fluids", "nParticles"],
    }

    DEFAULT_CAMERA = None
    DEFAULT_RESOLUTION = "HD 720"
    DEFAULT_FRAME_RANGE = "Playback"
    DEFAULT_CONTAINER = "mp4"
    DEFAULT_ENCODER = "h264"
    DEFAULT_H264_QUALITY = "High"
    DEFAULT_H264_PRESET = "fast"
    DEFAULT_IMAGE_QUALITY = 100

    DEFAULT_PADDING = 4

    DEFAULT_VISIBILITY = "Geo"

    USE_LOCAL_TEMPDIR = True
    USING_SHOTMASK = True

    def __init__(self, ffmpeg_path=None, logging_enabled=True):
        super(HrPlayblast, self).__init__()

        self.logger = MayaQtLogger(sender="TWA-Playblast", log_to_maya=logging_enabled)

        self.set_ffmpeg_path(ffmpeg_path)

        self._shotmask_loaded = True
        if HrPlayblast.USING_SHOTMASK:
            self.load_shotmask()

        self.set_camera(HrPlayblast.DEFAULT_CAMERA)
        self.set_resolution(HrPlayblast.DEFAULT_RESOLUTION)
        self.set_frame_range(HrPlayblast.DEFAULT_FRAME_RANGE)

        self.set_encoding(HrPlayblast.DEFAULT_CONTAINER, HrPlayblast.DEFAULT_ENCODER)
        self.set_h264_settings(HrPlayblast.DEFAULT_H264_QUALITY, HrPlayblast.DEFAULT_H264_PRESET)
        self.set_image_settings(HrPlayblast.DEFAULT_IMAGE_QUALITY)

        self.set_visibility(HrPlayblast.DEFAULT_VISIBILITY)

        self.initialize_ffmpeg_process()

    def get_ffmpeg_path(self):

        return self._ffmpeg_path

    def set_ffmpeg_path(self, ffmpeg_path):

        self._ffmpeg_path = ffmpeg_path if ffmpeg_path else HrPlayblast.DEFAULT_FFMPEG_PATH

    def load_shotmask(self):
        shotmask = "shotmask.py"
        if not cmds.pluginInfo(shotmask, query=True, loaded=True):
            try:
                cmds.loadPlugin(shotmask)
            except:
                self.logger.log_warning("Shotmask plugin is not installed. Will continue without it.")
                self._shotmask_loaded = False
                return

    def _create_shotmask(self, camera):

        self.delete_shotmask()
        shotmask = pm.createNode("hshotmask")
        shotmask.textPadding.set(20)
        shotmask.fontScale.set(0.8)
        shotmask.borderAlpha.set(0.8)

        artist = self.get_artist_name()
        shotmask.topCenterText.set("Artist: {}".format(artist))

        shotmask.topRightText.set(self.get_date())
        shotmask.topLeftText.set(self.get_scene_name())
        shotmask.bottomRightText.set("")
        shotmask.bottomLeftText.set(camera)
        shotmask.bottomCenterText.set("Duration: {}".format(self.get_duration()))

    def delete_shotmask(self):

        pm.delete([sm.parent(0) for sm in pm.ls(type="hshotmask")])

    def set_camera(self, camera):
        if camera and camera not in cmds.listCameras():
            self.logger.log_error("Camera does not exist: {}".format(camera))
            camera = None

        self._camera = camera

    def set_resolution(self, resolution):
        self._resolution_preset = None
        try:
            width_height = self.preset_to_resolution(resolution)
            self._resolution_preset = resolution
        except:
            width_height = resolution

        valid_resolution = True
        try:
            if not (isinstance(width_height[0], int) and isinstance(width_height[1], int)):
                valid_resolution = False
        except:
            valid_resolution = False

        if valid_resolution:
            if width_height[0] <=0 or width_height[1] <= 0:
                self.logger.log_error("Invalid resolution: {}. Values must be greater than zero.".format(width_height))
                return
        else:
            presets = ["'{}'".format(preset) for preset in HrPlayblast.RESOLUTION_LOOKUP]

            self.logger.log_error("Invalid resoluton: {}. Expected one of [int, int], {}".format(width_height, ", ".join(presets)))
            return

        self._width_height = (width_height[0], width_height[1])

    def get_resolution_width_height(self):
        if self._resolution_preset:
            return self.preset_to_resolution(self._resolution_preset)

        return self._width_height

    def preset_to_resolution(self, resolution_preset):
        if resolution_preset in HrPlayblast.RESOLUTION_LOOKUP.keys():
            return HrPlayblast.RESOLUTION_LOOKUP[resolution_preset]
        else:
            raise RuntimeError("Invalid resolution preset {}".format(resolution_preset))

    def set_frame_range(self, frame_range):
        resolved_frame_range = self.resolve_frame_range(frame_range)
        if not resolved_frame_range:
            return

        self._frame_range_preset = None
        if frame_range in HrPlayblast.FRAME_RANGE_PRESETS:
            self._frame_range_preset = frame_range

        self._start_frame = resolved_frame_range[0]
        self._end_frame = resolved_frame_range[1]

    def get_start_end_frame(self):
        if self._frame_range_preset:
            return self.preset_to_frame_range(self._frame_range_preset)

        return (self._start_frame, self._end_frame)

    def resolve_frame_range(self, frame_range):
        try:
            if type(frame_range) in [list, tuple]:
                start_frame = frame_range[0]
                end_frame = frame_range[1]
            else:
                start_frame, end_frame = self.preset_to_frame_range(frame_range)

            return (start_frame, end_frame)
        except:
            presets = ["'{}'".format(preset) for preset in HrPlayblast.FRAME_RANGE_PRESETS]

            self.logger.log_error("Invalid frame range. Expected one of (start_frame, end_frame), {}".format(", ".join(presets)))

    def preset_to_frame_range(self, frame_range_preset):
        if frame_range_preset == "Playback":
            start_frame = int(cmds.playbackOptions(q=True, minTime=True))
            end_frame = int(cmds.playbackOptions(q=True, maxTime=True))
        elif frame_range_preset == "Animation":
            start_frame = int(cmds.playbackOptions(q=True, animationStartTime=True))
            end_frame = int(cmds.playbackOptions(q=True, animationEndTime=True))
        else:
            raise RuntimeError("Invalid frame range preset {}".format(frame_range_preset))

        return (start_frame, end_frame)

    def set_visibility(self, visibility_data):
        if not visibility_data:
            visibility_data = []

        if not type(visibility_data) in [list, tuple]:
            visibility_data = self.preset_to_visibility(visibility_data)

            if visibility_data is None:
                return

        self._visibility = copy.copy(visibility_data)

    def get_visibility(self):
        if not self._visibility:
            return self.get_viewport_visibility()

        return self._visibility

    def preset_to_visibility(self, visibility_preset):
        if not visibility_preset in HrPlayblast.VIEWPORT_VISIBILITY_PRESETS.keys():
            self.logger.log_error("Invalid visibility preset: {}".format(visibility_preset))
            return None

        preset_name = HrPlayblast.VIEWPORT_VISIBILITY_PRESETS[visibility_preset]

        visibility_data = []

        if preset_name:
            for lookup_item in HrPlayblast.VIEWPORT_VISIBILITY_LOOKUP:
                visibility_data.append(lookup_item[0] in preset_name)

        return visibility_data

    def get_viewport_visibility(self):
        model_panel = self.get_viewport_panel()
        if not model_panel:
            self.logger.log_error("Failed to get viewport visibility. A viewport is not active.")
            return None

        viewport_visibility = []
        try:
            for item in HrPlayblast.VIEWPORT_VISIBILITY_LOOKUP:
                kwargs = {item[1]: True}
                viewport_visibility.append(cmds.modelEditor(model_panel, q=True, **kwargs))
        except:
            traceback.print_exc()
            self.logger.log_error("Failed to get active viewport visibility.")
            return

        return viewport_visibility

    def set_viewport_visibility(self, model_editor, visibility_flags):

        cmds.modelEditor(model_editor, e=True, **visibility_flags)

    def create_viewport_visibility_flags(self, visibility_data):
        visibility_flags = {}

        data_index = 0
        for item in HrPlayblast.VIEWPORT_VISIBILITY_LOOKUP:
            visibility_flags[item[1]] = visibility_data[data_index]
            data_index += 1

        return visibility_flags

    def set_encoding(self, container_format, encoder):
        if container_format not in HrPlayblast.VIDEO_ENCODER_LOOKUP.keys():
            self.logger.log_error("Invalid container: {}. Expected one of {}".format(container_format, HrPlayblast.VIDEO_ENCODER_LOOKUP.keys()))
            return

        if encoder not in HrPlayblast.VIDEO_ENCODER_LOOKUP[container_format]:
            self.logger.log_error("Invalid encoder: {}. Expected one of {}".format(encoder, HrPlayblast.VIDEO_ENCODER_LOOKUP[container_format]))
            return

        self._container_format = container_format
        self._encoder = encoder

    def set_h264_settings(self, quality, preset):
        if not quality in HrPlayblast.H264_QUALITIES.keys():
            self.logger.log_error("Invalid h264 quality: {}. Expected one of {}".format(quality, HrPlayblast.H264_QUALITIES.keys()))
            return

        if not preset in HrPlayblast.H264_PRESETS:
            self.logger.log_error("Invalid h264 preset: {}. Expected one of {}".format(preset, HrPlayblast.H264_PRESETS))
            return

        self._h264_quality = quality
        self._h264_preset = preset

    def get_h264_settings(self):
        return {
            "quality": self._h264_quality,
            "preset": self._h264_preset,
        }

    def set_image_settings(self, quality):
        if quality > 0 and quality <= 100:
            self._image_quality = quality
        else:
            self.logger.log_error("Invalid image quality: {}. Expected value between 1-100")

    def get_image_settings(self):
        return {
            "quality": self._image_quality,
        }

    def set_output_tempdir(self, output_dir, filename):

        if HrPlayblast.USE_LOCAL_TEMPDIR:
            return os.path.normpath(os.path.join(tempfile.gettempdir(), "{}_playblast_temp".format(filename)))
        return "{}/playblast_temp".format(output_dir)

    def execute(self, output_dir, filename, padding=4, show_ornaments=True, overscan=False, show_in_viewer=True, overwrite=False):

        if self.requires_ffmpeg() and not self.validate_ffmpeg():
            self.logger.log_output("ffmpeg executable is not configured.")
            return

        viewport_model_panel = self.get_viewport_panel()
        if not viewport_model_panel:
            self.logger.log_error("An active viewport is not selected. Select a viewport and retry.")

        if not output_dir:
            self.logger.log_error("Output directory not set")
            return
        output_dir = self.resolve_output_directory_path(output_dir)

        if not filename:
            self.logger.log_error("Output filename not set")
            return
        filename = self.resolve_output_filename(filename)

        if padding <= 0:
            padding = HrPlayblast.DEFAULT_PADDING

        if self.requires_ffmpeg():
            output_path = os.path.normpath(os.path.join(output_dir, "{}.{}".format(filename, self._container_format)))

            if not overwrite and os.path.exists(output_path):
                self.logger.log_error("Output file already exists. Eanble overwrite to ignore.")
                return

            playblast_output_dir = self.set_output_tempdir(output_dir, filename)
            playblast_output = os.path.normpath(os.path.join(playblast_output_dir, filename))
            force_overwrite = True
            compression = "png"
            image_quality = 100
            index_from_zero = True
            viewer = False
        else:
            playblast_output = os.path.normpath(os.path.join(output_dir, filename))
            force_overwrite = overwrite
            compression = self._encoder
            image_quality = self._image_quality
            index_from_zero = False
            viewer = show_in_viewer

        width_height = self.get_resolution_width_height()
        start_frame, end_frame = self.get_start_end_frame()

        options = {
            "filename": playblast_output,
            "widthHeight": width_height,
            "percent": 100,
            "startTime": start_frame,
            "endTime": end_frame,
            "clearCache": True,
            "forceOverwrite": force_overwrite,
            "format": "image",
            "compression": compression,
            "quality": image_quality,
            "indexFromZero": index_from_zero,
            "framePadding": padding,
            "showOrnaments": show_ornaments,
            "viewer": viewer,
        }

        self.logger.log_output("Playblast options: {}".format(options))

        # Store original viewport settings
        orig_camera = self.get_active_camera()

        camera = self._camera
        if not camera:
            camera = orig_camera

        if not camera in cmds.listCameras():
            self.logger.log_error("Camera does not exist: {}".format(camera))
            return

        self.set_active_camera(camera)

        if HrPlayblast.USING_SHOTMASK and self._shotmask_loaded:
            self._create_shotmask(camera)

        orig_visibility_flags = self.create_viewport_visibility_flags(self.get_viewport_visibility())
        playblast_visibility_flags = self.create_viewport_visibility_flags(self.get_visibility())

        model_editor = cmds.modelPanel(viewport_model_panel, q=True, modelEditor=True)
        self.set_viewport_visibility(model_editor, playblast_visibility_flags)

        # Store original camera settings
        if not overscan:
            overscan_attr = "{0}.overscan".format(camera)
            orig_overscan = cmds.getAttr(overscan_attr)
            cmds.setAttr(overscan_attr, 1.0)

        playblast_failed = False
        try:
            cmds.playblast(**options)
        except:
            traceback.print_exc()
            self.logger.log_error("Failed to create playblast. See script editor for details.")
            playblast_failed = True
        finally:
            # Restore original camera settings
            if not overscan:
                cmds.setAttr(overscan_attr, orig_overscan)

            # Restore original viewport settings
            self.set_active_camera(orig_camera)
            self.set_viewport_visibility(model_editor, orig_visibility_flags)

            if HrPlayblast.USING_SHOTMASK and self._shotmask_loaded:
                self.delete_shotmask()

        if playblast_failed:
            return

        if self.requires_ffmpeg():
            source_path = "{}/{}.%0{}d.png".format(playblast_output_dir, filename, padding)

            if self._encoder == "h264":
                self.encode_h264(source_path, output_path, start_frame)
            else:
                self.logger.log_error("Encoding failed. Unsupported encoder {} for container {}".format(self._encoder, self._container_format))
                self.remove_temp_dir(playblast_output_dir)
                return

            self.remove_temp_dir(playblast_output_dir)

            if show_in_viewer:
                self.open_in_viewer(output_path)

    def remove_temp_dir(self, temp_dir_path):
        playblast_dir = QtCore.QDir(temp_dir_path)
        playblast_dir.setNameFilters(["*.png"])
        playblast_dir.setFilter(QtCore.QDir.Files)
        for f in playblast_dir.entryList():
            playblast_dir.remove(f)

        if not playblast_dir.rmdir(temp_dir_path):
            self.logger.log_warning("Failed to remove temp directory: {}".format(temp_dir_path))

    def open_in_viewer(self, path):
        if not os.path.exists(path):
            self.logger.log_error("Failed to open in viewer. File does not exist: {}".format(path))
            return

        if self._container_format in ("mov", "mp4") and cmds.optionVar(exists="PlayblastCmdQuicktime"):
            executable_path = cmds.optionVar(q="PlayblastCmdQuicktime")
            if executable_path:
                QtCore.QProcess.startDetached(executable_path, [path])
                return

        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))

    def requires_ffmpeg(self):

        return self._container_format != "Image"

    def validate_ffmpeg(self):
        if not self._ffmpeg_path:
            self.logger.log_error("ffmpeg executable path not set")
            return False
        elif not os.path.exists(self._ffmpeg_path):
            self.logger.log_error("ffmpeg executable path does not exist: {}".format(self._ffmpeg_path))
            return False
        elif os.path.isdir(self._ffmpeg_path):
            self.logger.log_error("invalid ffmpeg path:: {}".format(self._ffmpeg_path))
            return False

        return True

    def initialize_ffmpeg_process(self):
        self._ffmpeg_process = QtCore.QProcess()
        self._ffmpeg_process.readyReadStandardError.connect(self.process_ffmpeg_output)

    def execute_ffmpeg_command(self, command):
        self._ffmpeg_process.start(command)
        if self._ffmpeg_process.waitForStarted():
            while self._ffmpeg_process.state() != QtCore.QProcess.NotRunning:
                QtCore.QCoreApplication.processEvents()
                QtCore.QThread.usleep(10)

    def process_ffmpeg_output(self):
        byte_array_output = self._ffmpeg_process.readAllStandardError()

        if sys.version_info.major < 3:
            output = str(byte_array_output)
        else:
            output = str(byte_array_output, "utf-8")

        self.logger.log_output(output)

    def encode_h264(self, source_path, output_path, start_frame):

        framerate = self.get_frame_rate()

        audio_file_path, audio_frame_offset = self.get_audio_attributes()
        if audio_file_path:
            audio_offset = self.get_audio_offset_in_sec(start_frame, audio_frame_offset, framerate)

        crf = HrPlayblast.H264_QUALITIES[self._h264_quality]
        preset = self._h264_preset

        ffmpeg_cmd = self._ffmpeg_path
        ffmpeg_cmd += " -y -framerate {} -i \"{}\"".format(framerate, source_path)

        if audio_file_path:
            ffmpeg_cmd += " -ss {} -i \"{}\"".format(audio_offset, audio_file_path)

        ffmpeg_cmd += ' -c:v libx264 -crf:v {} -preset:v {} -profile high -level 4.0 -pix_fmt yuv420p'.format(crf, preset)

        if audio_file_path:
            ffmpeg_cmd += "  -filter_complex \"[1:0] apad\" -shortest"

        ffmpeg_cmd += " \"{}\"".format(output_path)

        self.logger.log_output(ffmpeg_cmd)
        self.execute_ffmpeg_command(ffmpeg_cmd)

    def get_frame_rate(self):
        rate_str = cmds.currentUnit(q=True, time=True)

        if rate_str == "game":
            frame_rate = 15.0
        elif rate_str == "film":
            frame_rate = 24.0
        elif rate_str == "pal":
            frame_rate = 25.0
        elif rate_str == "ntsc":
            frame_rate = 30.0
        elif rate_str == "show":
            frame_rate = 48.0
        elif rate_str == "palf":
            frame_rate = 50.0
        elif rate_str == "ntscf":
            frame_rate = 60.0
        elif rate_str.endswith("fps"):
            frame_rate = float(rate_str[0:-3])
        else:
            raise RuntimeError("Unsupported frame rate: {0}".format(rate_str))

        return frame_rate

    def get_audio_attributes(self):
        sound_node = mel.eval("timeControl -q -sound $gPlayBackSlider;")
        if sound_node:
            sound_node = pm.PyNode(sound_node)
            file_path = sound_node.filename.get()
            file_info = QtCore.QFileInfo(file_path)
            if file_info.exists():
                offset = sound_node.offset.get()

                return (file_path, offset)

        return (None, None)

    def get_audio_offset_in_sec(self, start_frame, audio_frame_offset, framerate):

        return (start_frame - audio_frame_offset) / framerate

    def resolve_output_directory_path(self, dir_path):
        if "{project}" in dir_path:
            dir_path = dir_path.replace("{project}", self.get_project_dir_path())
        if "{scene}" in dir_path:
            dir_path = dir_path.replace("{scene}", self.get_scene_dir_path())

        return dir_path

    def resolve_output_filename(self, filename):
        if "{scene}" in filename:
            filename = filename.replace("{scene}", self.get_scene_name())
        if "{camera}" in filename:
            filename = filename.replace("{camera}", self._camera if self._camera else self.get_active_camera())

        return filename

    def get_project_dir_path(self):

        return cmds.workspace(q=True, rootDirectory=True)

    def get_scene_dir_path(self):
        scene_dir = pm.sceneName().dirname()

        return scene_dir if scene_dir else self.get_project_dir_path()

    def get_scene_name(self):
        scene_name = pm.sceneName().basename().splitext()[0]

        return scene_name if scene_name else "untitled"

    def get_viewport_panel(self):
        model_panel = cmds.getPanel(withFocus=True)
        try:
            cmds.modelPanel(model_panel, q=True, modelEditor=True)
        except:
            self.logger.log_error("Failed to get active view.")
            return None

        return model_panel

    def get_active_camera(self):
        model_panel = self.get_viewport_panel()
        if not model_panel:
            self.logger.log_error("Failed to get active camera. A viewport is not active.")
            return None

        return cmds.modelPanel(model_panel, q=True, camera=True)

    def set_active_camera(self, camera):
        model_panel = self.get_viewport_panel()
        if model_panel:
            mel.eval("lookThroughModelPanel {0} {1}".format(camera, model_panel))
        else:
            self.logger.log_error("Failed to set active camera. A viewport is not active.")

    def get_user(self):
        import getpass
        return getpass.getuser().capitalize()

    def get_artist_name(self):
        if cmds.optionVar(exists="ArtistName"):
            return cmds.optionVar(q="ArtistName")
        else:
            return self.get_user()

    def set_artist_name(self, name):
        cmds.optionVar(sv=("ArtistName", name))
        self.logger.log_warning("Changed artist name to {}!".format(name))

    def get_date(self):

        return datetime.datetime.now().strftime("%H:%M %d.%m.%Y")

    def get_duration(self):
        start, end = self.get_start_end_frame()
        return (end-start)+1
