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


class ReferenceRemoveWindow(SampleMayaUI):

    WINDOW_TITLE = "TWA Reference Remove"

    def __init__(self):
        super(ReferenceRemoveWindow, self).__init__()
        self.references = {}
        self.__geometry = None
        self.resize(300, 600)
        self.populate()

    def create_widgets(self):
        self.refs_list_wgt = QtWidgets.QListWidget()
        self.remove_btn = QtWidgets.QPushButton("Remove Reference")
        self.remove_btn.setIcon(QtGui.QIcon(":removeRenderable.png"))
        self.reload_btn = QtWidgets.QPushButton()
        self.reload_btn.setMaximumWidth(30)
        self.reload_btn.setIcon(QtGui.QIcon(":refresh.png"))

    def create_layout(self):
        self.master_layout = QtWidgets.QVBoxLayout(self)
        self.btn_layout = QtWidgets.QHBoxLayout()
        self.btn_layout.addWidget(self.remove_btn)
        self.btn_layout.addWidget(self.reload_btn)
        self.master_layout.addWidget(self.refs_list_wgt)
        self.master_layout.addLayout(self.btn_layout)

    def create_connections(self):
        self.remove_btn.clicked.connect(self.remove_reference)
        self.reload_btn.clicked.connect(self.refresh)

    def remove_reference(self):
        selection = self.refs_list_wgt.currentItem().text()
        ref = self.references[selection]
        ref.remove()
        log_output("Removed reference {}".format(selection))
        self.populate()

    def refresh(self):
        self.populate()

    def populate(self):
        self.references = {}
        self.refs_list_wgt.clear()
        for ref in pm.listReferences():
            name = ref.namespace
            self.references[name] = ref
            self.refs_list_wgt.addItem(name)

    def showEvent(self, e):
        super(ReferenceRemoveWindow, self).showEvent(e)
        if self.__geometry:
            self.restoreGeometry(self.__geometry)

    def closeEvent(self, e):
        if isinstance(self, ReferenceRemoveWindow):
            super(ReferenceRemoveWindow, self).closeEvent(e)
            self.__geometry = self.saveGeometry()
