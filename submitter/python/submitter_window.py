import sys
import os
import subprocess
from PyQt5 import QtCore, QtWidgets, QtGui, uic

from Deadline.DeadlineConnect import DeadlineCon
from mongo_documents import MayaRenderLayer, MayaJob, DatabaseConnection, frame_list

import nuke_dailies

SMBT_ROOT = os.path.abspath(os.path.dirname(__file__))
ICONDIR = os.path.join(SMBT_ROOT, "icons")

PROJECT = "Turbosaurs"
PROJECTS_PATH = os.getenv("PROJECTS_PATH", "Z:\\Projects")
RENDER_SCENES = os.path.join(PROJECTS_PATH, PROJECT, "Render_scenes")
RENDERS = os.path.join("\\\\dell\\Projects", PROJECT, "Render")

DBHOST = os.getenv("DB_HOST", "192.168.99.2")
PULSE_NAME = "dell"
DBPORT = 27017

DEADLINE_PORT = 8082
DEADLINE_LOGIN = "admin"
DEADLINE_PASSWORD = "123"

deadline_connection = DeadlineCon(PULSE_NAME, DEADLINE_PORT)
deadline_connection.SetAuthenticationCredentials(
    DEADLINE_LOGIN, DEADLINE_PASSWORD)


class SubmitterWindow(QtWidgets.QWidget):
    UI_FILE = os.path.join(SMBT_ROOT, "submitter.ui")
    FILE_FILTERS = "Maya (*.ma *.mb);;Maya ASCII (*.ma);;Maya Binary (*.mb);;All Files (*.*)"

    JOB_STATUSES = {
        "new": QtGui.QColor("#2d2d2d"),
        "rendering": QtGui.QColor("#6D562E"),
        "error": QtGui.QColor("#690000"),
        "done": QtGui.QColor("#1F684D"),
    }

    @staticmethod
    def set_icon(widget, icon_name):
        widget.setIcon(QtGui.QIcon(os.path.join(ICONDIR, icon_name)))

    @staticmethod
    def get_frame_list(frames):
        return [int(i) for i in frames.replace(
                ",", "-").split("-") if i.isdigit()]

    def __init__(self):
        super(SubmitterWindow, self).__init__()
        self.settings = QtCore.QSettings("submitter", "submitter")

        self.render_layers = []
        self.current_job = None

        self.configure_window()
        self.create_widgets()
        self.create_layout()
        self.create_connections()

        self.load_settings()

        self.configure_widgets()

        self.search_jobs()

    def show_message(self, icon="information", title="Submitter", text="", info=""):
        icons = {
            "question": QtWidgets.QMessageBox.Question,
            "information": QtWidgets.QMessageBox.Information,
            "warning": QtWidgets.QMessageBox.Warning,
            "critical": QtWidgets.QMessageBox.Critical,
        }
        msg = QtWidgets.QMessageBox()
        msg.setIcon(icons[icon])
        msg.setText(text)
        if info:
            msg.setInformativeText(info)
        msg.setWindowTitle(title)

        msg.exec_()

    def configure_window(self):
        self.setWindowTitle("Maya Job Submitter")
        self.setWindowIcon(QtGui.QIcon(
            os.path.join(ICONDIR, "deadline_icon.png")))
        self.setMinimumSize(800, 600)

        self.ui_wgt = uic.loadUi(self.UI_FILE)

    def create_widgets(self):
        groups = deadline_connection.Groups.GetGroupNames()
        self.ui_wgt.deadline_group_cbx.addItems(groups)
        self.ui_wgt.jobs_lyt.setSpacing(3)
        self.ui_wgt.scrollArea.setWidgetResizable(True)
        self.set_icon(self.ui_wgt.search_btn, "search_solid.png")
        self.set_icon(self.ui_wgt.refresh_btn, "refresh.png")
        self.set_icon(self.ui_wgt.delete_job_btn, "trash_bin.png")
        self.set_icon(self.ui_wgt.update_job_btn, "pen_square.png")
        self.set_icon(self.ui_wgt.preview_image_btn, "image_solid.png")
        self.set_icon(self.ui_wgt.submitte_daily_btn, "nuke.png")

        self.ui_wgt.jobs_list.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)

    def create_layout(self):
        self.ui_wgt.layout().setContentsMargins(0, 0, 0, 0)
        self.ui_wgt.splitter.setStretchFactor(1, 1)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.addWidget(self.ui_wgt)

    def create_connections(self):
        self.ui_wgt.search_btn.clicked.connect(self.search_jobs)
        self.ui_wgt.refresh_btn.clicked.connect(self.search_jobs)
        self.ui_wgt.search_text_led.returnPressed.connect(self.search_jobs)

        self.ui_wgt.jobs_list.itemDoubleClicked.connect(
            self.job_double_clicked)
        self.ui_wgt.submitte_btn.clicked.connect(self.submitte)
        self.ui_wgt.submitte_daily_btn.clicked.connect(self.submite_daily)
        self.ui_wgt.job_status_cbx.activated.connect(
            self.change_status)
        self.ui_wgt.new_jobs_check.stateChanged.connect(
            self.search_jobs)
        self.ui_wgt.delete_job_btn.clicked.connect(self.delete_job)
        self.ui_wgt.update_job_btn.clicked.connect(self.update_job)
        self.ui_wgt.preview_image_btn.clicked.connect(self.show_preview)

        self.ui_wgt.camera_name_led.returnPressed.connect(
            self.camera_list_complete)

        self.ui_wgt.set_scene_file_btn.clicked.connect(self.set_scene_file)

    def camera_list_complete(self):
        self.ui_wgt.camera_name_led.completer().complete()

    def load_settings(self):
        window_geometry = self.settings.value("window_geometry")
        show_new = self.settings.value("show_new")
        search_string = self.settings.value("search_string")

        if window_geometry:
            self.restoreGeometry(window_geometry)

        if show_new:
            self.ui_wgt.new_jobs_check.setChecked(show_new == u"true")

        if search_string:
            self.ui_wgt.search_text_led.setText(str(search_string))

    def save_settings(self):
        self.settings.setValue("window_geometry", self.saveGeometry())
        self.settings.setValue(
            "show_new", self.ui_wgt.new_jobs_check.isChecked())
        self.settings.setValue(
            "search_string", self.ui_wgt.search_text_led.text())

    def change_status(self, st=2):
        items = self.ui_wgt.jobs_list.selectedItems()
        if not items:
            return
        status = self.ui_wgt.job_status_cbx.itemText(st)
        for item in items:
            item.setBackground(self.JOB_STATUSES[status])
            with DatabaseConnection("rendering", DBHOST, DBPORT):
                job = MayaJob.objects(id=item.data(5))
                job.update(status=status)

    def update_layer(self, job_id, layer):
        MayaJob.objects(id=job_id, render_layers__layer_name=layer["layer_name"]).update(
            set__render_layers__S__priority=layer["priority"],
            set__render_layers__S__frames=layer["frames"],
            set__render_layers__S__output_directory=layer["output_directory"],
            set__render_layers__S__comment=layer["comment"],
            set__render_layers__S__renderable=layer["renderable"],
            set__render_layers__S__job_id=layer["job_id"],
        )

    def update_job(self, no_layers=False):
        if not self.current_job:
            return

        _id = self.current_job.id
        info = self.collect_info()
        layers = info.pop("render_layers")

        with DatabaseConnection("rendering", DBHOST, DBPORT):
            self.current_job.update(**info)
            if no_layers:
                return

            for layer in layers:
                self.update_layer(_id, layer)

        self.show_message(title="Updated!", text="Successfully updated job {}".format(
            info["batch_name"]), info="Job ID {}".format(_id))

    def submitte(self):
        if not self.current_job:
            return

        _id = self.current_job.id
        info = self.collect_info()
        layers = info.pop("render_layers")

        submitted_text = []
        daily_dependencies = []
        with DatabaseConnection("rendering", DBHOST, DBPORT):
            for layer in layers:
                if layer["renderable"]:
                    job_info, plugin_info = self.create_submission_requiroments(
                        info, layer)

                    try:
                        deadline_job = deadline_connection.Jobs.SubmitJob(
                            job_info, plugin_info)
                        layer["job_id"] = deadline_job["_id"]
                        daily_dependencies.append(layer["job_id"])
                        submitted_text.append(
                            "{}".format(layer["name"]))
                    except Exception as e:
                        self.show_message(
                            icon="critical", title="Oops!", text="Sorry, There was an error!", info="Error:\n\n   {}".format(str(e)))
                        break
                    finally:
                        self.update_layer(_id, layer)
                else:
                    self.update_layer(_id, layer)

        self.update_job(no_layers=True)
        self.change_status(st=1)
        if submitted_text:
            self.show_message(title="Success!", text="Successfully submitted job {}".format(
                info["batch_name"]), info="   \n".join(submitted_text))
        self.submite_daily(daily_dependencies, msg=False)
        self.search_jobs()

    def create_submission_requiroments(self, info, layer):
        job_info = {
            "BatchName": info["batch_name"],
            "Group": self.ui_wgt.deadline_group_cbx.currentText(),
            "Department": self.current_job.department,
            "Frames": layer["frames"],
            "Name": layer["name"],
            "Priority": layer["priority"],
            "OutputDirectory0": layer["output_directory"],
            "OutputFilename0": layer["output_filename"],
            "Comment": layer["comment"],
            "EnvironmentKeyValue0": "MAYA_MODULE_PATH=\\\\dell\\StudioRepository\\twa_pipeline\\render",
            "OverrideTaskExtraInfoNames": "False",
            "Plugin": "MayaBatch",
            "UserName": "admin",
            "ChunkSize": "1",
        }

        plugin_info = {
            "Animation": 1,
            "Build": "64bit",
            "Camera": info["camera_name"],
            "SceneFile": info["scene_file"],
            "OutputFilePath": layer["output_directory"],
            "RenderLayer": layer["layer_name"],
            "FrameNumberOffset": 0,
            "IgnoreError211": 0,
            "ImageHeight": 1080,
            "ImageWidth": 1920,
            "OutputFilePrefix": "<Scene>_<Layer>",
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

    def submite_daily(self, dependencies=None, msg=True):
        if self.current_job["has_daily"] and deadline_connection.Jobs.GetJob(self.current_job["daily"]):
            deadline_connection.Jobs.RequeueJob(self.current_job["daily"])
            return

        info = self.info_for_daily()
        if dependencies:
            info["dependencies"] = dependencies
        job_info, plugin_info = self.create_daily_requiroments(info)

        try:
            daily_job = deadline_connection.Jobs.SubmitJob(
                job_info, plugin_info)

            with DatabaseConnection("rendering", DBHOST, DBPORT):
                self.current_job.update(daily=daily_job["_id"], has_daily=True)
        except Exception as e:
            self.show_message(
                icon="critical", title="Oops! Problem with Daily!", text="Sorry, Daily was not submitted properly!", info="Error:\n\n   {}".format(str(e)))
            return

        if msg:
            self.show_message(
                title="Success!", text="Successfully submitted daily for {}".format(info["batch_name"]))

    def create_daily_requiroments(self, info):
        dependencies = info["dependencies"]
        if None in dependencies:
            self.show_message(
                icon="warning", text="You need to submitte job to be able to create dailiy.")
            return

        scene_file, output_filename = nuke_dailies.build_daily(info)
        output_filename = output_filename.replace("Render_scenes", "Render")
        job_info = {
            "BatchName": info["batch_name"],
            "Name": "{} - Daily".format(info["batch_name"]),
            "ChunkSize": "1000",
            "Department": "lighting",
            "EventOptIns": "",
            "Frames": info["frames"],
            "OutputFilename0": output_filename,
            "Group": "nuke",
            "OverrideTaskExtraInfoNames": "False",
            "Plugin": "Nuke",
            "Priority": "80",
            "UserName": "admin",
        }
        for n, d in enumerate(dependencies):
            job_info["JobDependency{}".format(n)] = d
        plugin_info = {
            "BatchMode": "True",
            "BatchModeIsMovie": "True",
            "ContinueOnError": "True",
            "EnforceRenderOrder": "False",
            "GpuOverride": "0",
            "NukeX": "True",
            "PerformanceProfiler": "False",
            "RamUse": "0",
            "RenderMode": "Use Scene Settings",
            "SceneFile": scene_file,
            "StackSize": "0",
            "Threads": "0",
            "UseGpu": "False",
            "Version": "11.3",
            "Views": "",
            "WriteNode": "COMP_OUT",
        }
        return (job_info, plugin_info)

    def info_for_daily(self):
        info = self.collect_info()
        layers = info.pop("render_layers")
        render_layers = dict()
        frames_list = []
        dependencies = []
        for layer in layers:
            frame_list = self.get_frame_list(layer["frames"])
            frames_list.append([frame_list[0], frame_list[-1]])
            dependencies.append(layer["job_id"])
            scene_name = os.path.split(
                os.path.dirname(layer["output_directory"]))[-1]
            layer_name = layer["layer_name"]
            write_name = layer["layer_name"]

            if layer_name == "FLOOR_AO":
                for fp in ["AO_Pass", "matteShadow"]:
                    write_name = fp
                    output_filename = "{}_{}.{}.####.exr".format(
                        scene_name, layer_name, fp)
                    output_filename = os.path.join(
                        layer["output_directory"], fp, output_filename)
                    render_layers[write_name] = output_filename
            else:
                output_filename = "{}_{}.####.exr".format(
                    scene_name, layer_name)
                output_filename = os.path.join(
                    layer["output_directory"], output_filename)
                render_layers[write_name] = output_filename

        info["frames"] = "{}-{}".format(min([min(x) for x in frames_list]),
                                        max([max(x) for x in frames_list]))
        info["render_layers"] = render_layers
        info["dependencies"] = dependencies
        info["render_dir"] = os.path.dirname(
            info["scene_file"].replace(RENDER_SCENES, RENDERS))
        return info

    def collect_info(self):
        return {
            "batch_name": self.ui_wgt.batch_name_led.text(),
            "scene_file": self.ui_wgt.scene_file_led.text(),
            "camera_name": self.ui_wgt.camera_name_led.text(),
            "render_layers": self.collect_layers(),
        }

    def collect_layers(self):
        layers = []
        for layer in self.render_layers:
            info = layer.info
            info["batch_name"] = self.ui_wgt.batch_name_led.text()
            layers.append(layer.info)

        return layers

    def configure_widgets(self):
        if self.current_job:
            batch_name = self.current_job.batch_name
            scene_file = self.current_job.scene_file
            camera_name = self.current_job.camera_name
            cam_completer = QtWidgets.QCompleter(self.current_job.camera_list)
            self.ui_wgt.camera_name_led.setCompleter(cam_completer)
            self.ui_wgt.preview_image_btn.setEnabled(
                self.current_job.scene_preview != "")
        else:
            batch_name = ""
            scene_file = ""
            camera_name = ""
        self.ui_wgt.batch_name_led.setText(batch_name)
        self.ui_wgt.scene_file_led.setText(scene_file)
        self.ui_wgt.camera_name_led.setText(camera_name)

    def search_jobs(self):
        QtCore.QCoreApplication.processEvents()

        search_text = self.ui_wgt.search_text_led.text()
        with DatabaseConnection("rendering", DBHOST, DBPORT):
            jobs = MayaJob.objects().order_by("batch_name")

        if search_text:
            jobs = jobs(batch_name__icontains=search_text)

        if self.ui_wgt.new_jobs_check.isChecked():
            jobs = jobs(status__exact="new")

        self.populate_jobs(jobs)

    def populate_jobs(self, jobs=None):
        self.ui_wgt.jobs_list.clear()

        if not jobs:
            return

        for job in jobs:
            item = QtWidgets.QListWidgetItem(job.batch_name)
            item.setData(5, job.id)
            item.setSizeHint(QtCore.QSize(25, 25))
            item.setBackground(self.JOB_STATUSES[job.status])
            self.ui_wgt.jobs_list.addItem(item)

    def clear_render_layers(self):
        self.render_layers = []
        while self.ui_wgt.jobs_lyt.count() > 0:
            layer_item = self.ui_wgt.jobs_lyt.takeAt(0)
            if layer_item.widget():
                layer_item.widget().deleteLater()

    def clear_job_wgts(self):
        self.current_job = None
        self.clear_render_layers()
        self.ui_wgt.batch_name_led.setText(""),
        self.ui_wgt.scene_file_led.setText(""),
        self.ui_wgt.camera_name_led.setText(""),

    def delete_job(self):
        item = self.ui_wgt.jobs_list.currentItem()
        items = self.ui_wgt.jobs_list.selectedItems()
        if not items:
            return
        with DatabaseConnection("rendering", DBHOST, DBPORT):
            for item in items:
                job_id = item.data(5)
                if self.current_job and job_id == self.current_job.id:
                    self.clear_job_wgts()

                job = MayaJob.objects(id=job_id)
                job.delete()

        self.search_jobs()

    def show_preview(self):
        if not self.current_job:
            return

        preview = os.path.abspath(self.current_job.scene_preview)
        if os.path.isfile(preview):
            subprocess.call("explorer {}".format(preview))
        else:
            self.show_message(title="No Preview",
                              icon="warning", text="Can't find preview.")
            with DatabaseConnection("rendering", DBHOST, DBPORT):
                self.current_job.update(scene_preview="")

    def job_double_clicked(self):
        self.clear_render_layers()

        _id = self.ui_wgt.jobs_list.currentItem().data(5)
        with DatabaseConnection("rendering", DBHOST, DBPORT):
            job = MayaJob.objects(id=_id).first()

        self.current_job = job
        for layer in self.current_job.render_layers:
            lyr_wgt = JobRenderLayer(layer)
            self.render_layers.append(lyr_wgt)
            self.ui_wgt.jobs_lyt.addWidget(lyr_wgt)

        self.configure_widgets()

    def set_scene_file(self):
        if self.current_job:
            file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Select a File", "", self.FILE_FILTERS)
            if file_path:
                self.ui_wgt.scene_file_led.setText(file_path)

    def closeEvent(self, e):
        super(SubmitterWindow, self).closeEvent(e)

        self.save_settings()


class JobRenderLayer(QtWidgets.QWidget):

    UI_FILE = os.path.join(SMBT_ROOT, "submitter_layer.ui")

    def __init__(self, layer):
        super(JobRenderLayer, self).__init__()

        self._layer = layer
        self.layer_name = self.layer.name()

        self.create_widgets()
        self.create_layout()
        self.create_connections()

    @property
    def layer(self):
        return self._layer

    @layer.setter
    def job(self, maya_render_layer):
        if isinstance(maya_render_layer, MayaRenderLayer):
            self._layer = maya_render_layer

    @property
    def info(self):
        layer_info = {}
        layer_info["name"] = self.layer.name()
        layer_info["layer_name"] = self.layer.layer_name
        layer_info["renderable"] = self.lyr_wgt.renderableCheck.isChecked()
        layer_info["output_directory"] = self.lyr_wgt.outptuDirLine.text()
        layer_info["output_filename"] = self.layer.output_filename
        layer_info["comment"] = self.lyr_wgt.commentLineEdit.text()
        layer_info["priority"] = self.lyr_wgt.prioritySpinBox.value()
        layer_info["job_id"] = self.layer.job_id
        if self.lyr_wgt.qcCheck.isChecked():
            layer_info["frames"] = frame_list(
                str(self.lyr_wgt.framesLineEdit.text()))
        else:
            layer_info["frames"] = self.lyr_wgt.framesLineEdit.text()
        return layer_info

    def create_widgets(self):
        self.lyr_wgt = uic.loadUi(self.UI_FILE)

        self.lyr_wgt.jobNameLbl.setText(self.layer_name)
        self.lyr_wgt.framesLineEdit.setText(self.layer.frames)
        self.lyr_wgt.outptuDirLine.setText(self.layer.output_directory)
        self.lyr_wgt.commentLineEdit.setText(self.layer.comment)
        self.lyr_wgt.prioritySpinBox.setValue(self.layer.priority)
        self.lyr_wgt.renderableCheck.setChecked(self.layer.renderable)

    def create_layout(self):
        self.lyr_wgt.layout().setContentsMargins(0, 0, 0, 0)
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.addWidget(self.lyr_wgt)

    def create_connections(self):
        self.lyr_wgt.set_dir_btn.clicked.connect(self.set_output_dir)

    def set_output_dir(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Directory")
        if directory:
            self.lyr_wgt.outptuDirLine.setText(directory)

    def delete(self):
        self.hide()
        self.setParent(None)
        self.deleteLater()


def dark_theme():
    dark_palette = QtGui.QPalette()
    dark_palette.setColor(QtGui.QPalette.Window, QtGui.QColor(45, 45, 45))
    dark_palette.setColor(QtGui.QPalette.WindowText,
                          QtGui.QColor(208, 208, 208))
    dark_palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
    dark_palette.setColor(QtGui.QPalette.AlternateBase,
                          QtGui.QColor(208, 208, 208))
    dark_palette.setColor(QtGui.QPalette.ToolTipBase,
                          QtGui.QColor(208, 208, 208))
    dark_palette.setColor(QtGui.QPalette.ToolTipBase,
                          QtGui.QColor(208, 208, 208))
    dark_palette.setColor(QtGui.QPalette.Text, QtGui.QColor(208, 208, 208))
    dark_palette.setColor(QtGui.QPalette.Button, QtGui.QColor(45, 45, 48))
    dark_palette.setColor(QtGui.QPalette.ButtonText,
                          QtGui.QColor(208, 208, 208))
    dark_palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
    dark_palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(252, 180, 52))

    return dark_palette


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle(QtWidgets.QStyleFactory.create("fusion"))

    app.setPalette(dark_theme())

    window = SubmitterWindow()
    window.show()

    app.exec_()
