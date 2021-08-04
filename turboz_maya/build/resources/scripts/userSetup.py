import maya.OpenMaya as om
import pymel.core as pm
from twa_maya.util.mayamenu import MayaMenu


def on_save(*args):
    master_layer = pm.nodetypes.RenderLayer.defaultRenderLayer()
    pm.editRenderLayerGlobals(currentRenderLayer=master_layer.name())

    hwr = pm.PyNode("hardwareRenderingGlobals")
    hwr.multiSampleEnable.set(0)
    hwr.motionBlurEnable.set(0)
    hwr.ssaoEnable.set(0)

    pm.modelEditor("modelPanel4", e=True, dtx=0, sdw=False, udm=False, da="smoothShaded", dl="default")

def create_twa_menu():
    twa_menu = MayaMenu.add_menu("TaleWind")
    twa_menu.add_command("Animation/CameraManager", "from tools.camera_tools import CameraManagerWindow\nCameraManagerWindow.display()", "Camera Manager", "CameraDown.png")
    twa_menu.add_command("Layout/PrepScene", "from turbosaurs.render_setup import TurbozRenderSetup\nTurbozRenderSetup.prep_scene_light()", "Prepare Scene")
    twa_menu.add_command("Layout/RemoveRef", "from tools.reference_remove import ReferenceRemoveWindow\nReferenceRemoveWindow.display()", "Remove Reference")
    twa_menu.add_command("Lighting/RenderSetup", "from turbosaurs.render_setup import TurbozRenderSetupWindow\nTurbozRenderSetupWindow.display()", "Render Setup", "deadline.png")
    twa_menu.add_command("Lighting/LightCreate", "from tools.gaffer import GafferWindow\nGafferWindow.display()", "Light Create", "gaffer.png")
    twa_menu.separator()
    twa_menu.add_command("About", "print(\"Hello!\")", icon="info.png")


pm.evalDeferred("om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeSave, on_save)")
pm.evalDeferred("create_twa_menu()")
