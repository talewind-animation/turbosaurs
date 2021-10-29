import os
import json
import tempfile
import subprocess

from PySide2 import QtCore, QtGui, QtWidgets

import nuke
import nukescripts

TZ_ROOT = os.getenv('TZ_ROOT')
TZ_COMP = os.path.join(TZ_ROOT, 'Compositing')

# root = 'S:\\harutyun\\nuke'
# sheet_updater = os.path.join(root, 'update_google_sheets.exe')
sheet_updater = os.getenv('SHEET_UPDATER')

def _load_config():
    configfile = os.path.join(TZ_COMP, "elemenets", "loader_config.json")
    if os.path.exists(configfile):
        with open(configfile, "r") as f:
            return json.load(f)
    return None

USERCONFIG = _load_config()

class ChangeShot(QtWidgets.QDialog):
    """ChangeShot dialog"""

    dlg_instance = None

    @classmethod
    def display(cls):
        """
        Creates instance of the dialog if not existing and displays it.
        Moves dialog under mouse cursor
        """
        if not cls.dlg_instance:
            cls.dlg_instance = ChangeShot()

        cls.dlg_instance.move(
            QtGui.QCursor().pos() - QtCore.QPoint((cls.dlg_instance.width() / 2),
                                                  (cls.dlg_instance.height() / 2)))  # move dlg under cursor
        if cls.dlg_instance.isHidden():
            cls.dlg_instance.show()
        else:
            cls.dlg_instance.raise_()
            cls.dlg_instance.activateWindow()

    def __init__(self):
        super(ChangeShot, self).__init__()
        self.setParent(QtWidgets.QApplication.instance().activeWindow())

        self.configure_window()
        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.populate_seasons()
        self.update_completer()

        self.read_last_shot()

    @staticmethod
    def set_cbox_text(cbox, text):
        index = cbox.findText(text, QtCore.Qt.MatchFixedString)
        if index >= 0:
             cbox.setCurrentIndex(index)

    def configure_window(self):
        self.setWindowFlags(
            QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint
            )
        self.setWindowTitle('change shot')
        self.setFixedSize(350, 100)

    def create_widgets(self):
        self.shot_label = QtWidgets.QLabel('Shot Name')

        self.season_lbl = QtWidgets.QLabel('Season:')
        self.season_cbx = QtWidgets.QComboBox()
        self.season_cbx.setFixedWidth(120)

        self.shot_name_led = QtWidgets.QLineEdit()

        self.ok_btn = QtWidgets.QPushButton('Ok')

    def create_layout(self):
        self.main_lyt = QtWidgets.QVBoxLayout(self)
        self.season_row = QtWidgets.QHBoxLayout()
        self.shot_row = QtWidgets.QHBoxLayout()
        self.btn_row = QtWidgets.QHBoxLayout()

        self.main_lyt.addLayout(self.season_row)
        self.main_lyt.addLayout(self.shot_row)
        self.main_lyt.addLayout(self.btn_row)

        self.season_row.addWidget(self.season_lbl)
        self.season_row.addWidget(self.season_cbx)
        self.shot_row.addWidget(self.shot_label)
        self.shot_row.addWidget(self.shot_name_led)
        self.btn_row.addWidget(self.ok_btn)

    def create_connections(self):
        self.ok_btn.clicked.connect(self.load_shot)
        self.season_cbx.currentTextChanged.connect(self.update_completer)

    def populate_seasons(self):
        self.season_cbx.clear()
        blasklist = []
        if USERCONFIG:
            blasklist = USERCONFIG["season_blacklist"]
        self.seasons = [s for s in os.listdir(TZ_COMP) if 'season' in s.lower() and not s in blasklist]
        self.season_cbx.addItems(self.seasons)

    def shot_completer_list(self, season="season_03"):
        blasklist = []
        print(season)
        print(os.path.join(TZ_COMP, season))
        if USERCONFIG:
            blasklist = USERCONFIG["episode_blacklist"]
        return ["{}_shot_0".format(e) for e in os.listdir(os.path.join(TZ_COMP, season)) if not e in blasklist]

    def update_completer(self):
        completer = QtWidgets.QCompleter(self.shot_completer_list(season=self.season_cbx.currentText()))
        self.shot_name_led.setCompleter(completer)

    def temp_file(self):
        tempdir = tempfile.gettempdir()
        temp_file = os.path.join(tempdir, 'tz_shotname.json')
        if os.path.exists(temp_file):
            return temp_file
        else:
            self.write_shotname(filename=temp_file)
            return temp_file

    def write_shotname(self, filename=None, season='', shname=''):
        if not filename:
            filename = self.temp_file()
        with open(filename, 'w') as f:
            json.dump([shname, season], f)

    def read_last_shot(self):
        with open(self.temp_file(), 'r') as f:
            shot_info = json.load(f)
        self.shot_name_led.setText(shot_info[0])
        if len(shot_info)>1:
            self.set_cbox_text(self.season_cbx, shot_info[1])

    def load_shot(self):
        self.shot_name = self.shot_name_led.text()
        self.season_name = self.season_cbx.currentText()
        self.handle_shot()
        self.write_shotname(season=self.season_name, shname=self.shot_name)
        self.close()

    def find_ep(self, epname, season_name):
        season_dir = os.path.join(TZ_COMP, season_name)
        for ep in os.listdir(season_dir):
            if epname in ep:
                return os.path.join(season_dir, ep)
        return None

    def make_folder(self, name):
        if not os.path.isdir(name):
            os.mkdir(name)

    def reset_cam(self, cam):
        cam['read_from_file'].setValue(False)
        cam['file'].setValue('')

        for k in ['translate', 'rotate', 'scaling', 'uniform_scale', 'focal',
        'haperture', 'vaperture', 'focal_point', 'fstop',
        'skew', 'pivot', 'win_translate', 'win_scale']:
            knob = cam.knob(k)
            if knob.isAnimated():
                knob.clearAnimated()
            knob.setValue(knob.defaultValue())

    def handle_camera(self, cam_path):
        cam = nuke.toNode('__shotcam__')
        if not cam_path:
            self.reset_cam(cam)
            return

        knob = cam.knob('file')

        cam['read_from_file'].setValue(True)
        knob.setValue(cam_path.replace('\\', '/'))

    def handle_shot(self):
        try:
            epname, sh, num = self.shot_name.rsplit('_', 2)
        except:
            return

        num = int(num)
        shotname = '{}_{}'.format(sh, '%03d' % num)

        ep_path = self.find_ep(epname, self.season_name)
        if not ep_path:
            return

        shot_dir = os.path.join(ep_path, self.shot_name)
        shot_comp_dir = os.path.join(shot_dir, 'comp')
        shot_rend_dir = os.path.join(shot_dir, 'render')
        shot_precomp_dir = os.path.join(shot_dir, 'precomp')
        [self.make_folder(f) for f in [shot_dir, shot_comp_dir, shot_rend_dir, shot_precomp_dir]]

        comp_name = '{}_{}_comp_v01.nk'.format(epname, shotname)
        comp_path = os.path.join(shot_comp_dir, comp_name)

        cam_dir = os.path.join(ep_path, 'cam')
        cam_name = '{}_cam.abc'.format(self.shot_name)
        cam_path = os.path.join(cam_dir, cam_name)
        cam_path = cam_path if os.path.exists(cam_path) else None
        self.handle_camera(cam_path)

        render_name = '{}_{}_comp_v01.%04d.exr'.format(epname, shotname)
        write = nuke.toNode('__COMP_OUT__')
        knob = write.knob('file')
        knob.setValue(os.path.join(shot_rend_dir, render_name).replace('\\', '/'))

        nuke.Root()['name'].setValue(comp_path.replace('\\', '/'))
        nuke.scriptSaveAs(comp_path)

        s, n = self.season_name.split("_")
        subprocess.Popen("{} -s \"{}\" -ep {} -sc {} -m {} -t {}".format(sheet_updater, "{} {}".format(s.capitalize(), int(n)), epname, num, 'nuke', shotname))

class LoadShot(QtWidgets.QDialog):
    """LoadShot dialog"""

    dlg_instance = None

    @classmethod
    def display(cls):
        """
        Creates instance of the dialog if not existing and displays it.
        Moves dialog under mouse cursor
        """
        if not cls.dlg_instance:
            cls.dlg_instance = LoadShot()

        cls.dlg_instance.move(
            QtGui.QCursor().pos() - QtCore.QPoint((cls.dlg_instance.width() / 2),
                                                  (cls.dlg_instance.height() / 2)))  # move dlg under cursor
        if cls.dlg_instance.isHidden():
            cls.dlg_instance.show()
        else:
            cls.dlg_instance.raise_()
            cls.dlg_instance.activateWindow()

    @staticmethod
    def set_cbox_text(cbox, text):
        index = cbox.findText(text, QtCore.Qt.MatchFixedString)
        if index >= 0:
             cbox.setCurrentIndex(index)

    def __init__(self):
        super(LoadShot, self).__init__()
        self.setParent(QtWidgets.QApplication.instance().activeWindow())

        self.settings = QtCore.QSettings("shot_loader", "shot_loader")
        self.user_config = USERCONFIG
        self.configure_window()
        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.populate_seasons()
        self.load_settings()

    def configure_window(self):
        self.setWindowFlags(
            QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint
            )
        self.setWindowTitle('Load Shot')
        self.setFixedSize(370, 150)

    def create_widgets(self):
        self.season_lbl = QtWidgets.QLabel('Season:')
        self.season_cbx = QtWidgets.QComboBox()
        self.season_cbx.setFixedWidth(120)

        self.ep_lbl = QtWidgets.QLabel('Episode:')
        self.ep_cbx = QtWidgets.QComboBox()
        self.ep_cbx.setFixedWidth(120)

        self.shot_lbl = QtWidgets.QLabel('Shot:')
        self.shot_cbx = QtWidgets.QComboBox()
        self.shot_cbx.setFixedWidth(300)

        self.load_btn = QtWidgets.QPushButton('Load')
        self.cancel_btn = QtWidgets.QPushButton('Cancel')

    def create_layout(self):
        self.main_lyt = QtWidgets.QVBoxLayout(self)

        self.season_ep_lyt = QtWidgets.QHBoxLayout()
        self.season_ep_lyt.addWidget(self.season_lbl)
        self.season_ep_lyt.addWidget(self.season_cbx)
        self.season_ep_lyt.addWidget(self.ep_lbl)
        self.season_ep_lyt.addWidget(self.ep_cbx)

        self.shot_lyt = QtWidgets.QHBoxLayout()
        self.shot_lyt.addWidget(self.shot_lbl)
        self.shot_lyt.addWidget(self.shot_cbx)


        self.button_lyt = QtWidgets.QHBoxLayout()
        self.button_lyt.addWidget(self.load_btn)
        self.button_lyt.addWidget(self.cancel_btn)

        self.main_lyt.addLayout(self.season_ep_lyt)
        self.main_lyt.addLayout(self.shot_lyt)
        self.main_lyt.addLayout(self.button_lyt)

    def create_connections(self):
        self.load_btn.clicked.connect(self.load_shot)
        self.cancel_btn.clicked.connect(self.close)

        self.season_cbx.currentTextChanged.connect(self.populate_episodes)
        self.ep_cbx.currentTextChanged.connect(self.populate_shots)

    def get_shot_path(self):
        season = self.season_cbx.currentText()
        episode = self.ep_cbx.currentText()
        shot = self.shot_cbx.currentText()
        comp_path = os.path.join(TZ_COMP, season, episode, shot, 'comp')
        if not os.path.isdir(comp_path):
            return None

        nk_files = [n for n in os.listdir(comp_path) if n.endswith('.nk') and shot in n]
        # TODO: versions
        comp_file = os.path.join(comp_path, nk_files[0])
        return comp_file

    def load_shot(self):
        script = self.get_shot_path()
        if script:
            nuke.scriptOpen(script)
        self.close()

    def populate_seasons(self):
        self.season_cbx.clear()
        blasklist = []
        if self.user_config:
            blasklist = self.user_config["season_blacklist"]
        self.seasons = [s for s in os.listdir(TZ_COMP) if 'season' in s.lower() and not s in blasklist]
        self.season_cbx.addItems(self.seasons)
        self.populate_episodes()

    def populate_episodes(self):
        self.ep_cbx.clear()
        season = self.season_cbx.currentText()
        blasklist = []
        if self.user_config:
            blasklist = self.user_config["episode_blacklist"]

        episodes = [e for e in os.listdir(os.path.join(TZ_COMP, season)) if not e in blasklist]
        self.ep_cbx.addItems(episodes)
        self.populate_shots()

    def populate_shots(self):
        self.shot_cbx.clear()
        season = self.season_cbx.currentText()
        episode = self.ep_cbx.currentText()
        shots = [s for s in os.listdir(os.path.join(TZ_COMP, season, episode)) if '_shot_' in s.lower()]
        self.shot_cbx.addItems(shots)

    def load_settings(self):
        try:
            self.set_cbox_text(self.season_cbx, self.settings.value("season"))
            self.set_cbox_text(self.ep_cbx, self.settings.value("episode"))
            self.set_cbox_text(self.shot_cbx, self.settings.value("shot"))
        except:
            print("can't load settings!")

    def save_settings(self):
        self.settings.setValue("season", self.season_cbx.currentText())
        self.settings.setValue("episode", self.ep_cbx.currentText())
        self.settings.setValue("shot", self.shot_cbx.currentText())

    def closeEvent(self, e):
        super(LoadShot, self).closeEvent(e)
        self.save_settings()
