import os

import nuke
import nuke_utility

import animatedSnap3D

try:
    import job_submite
except:
    pass

from turboz import change_shot
from turboz import cam_from_meta
from turboz import tz_callbacks

menu = nuke.menu("Nuke")
menu.addCommand("TurboZ/Deadline Submission", lambda: job_submite.make_sumbission2())
tz = menu.findItem('TurboZ')
tz.addSeparator()
menu.addCommand("TurboZ/Axis on Point", lambda: nuke_utility.axis_on_point())
menu.addCommand('TurboZ/LoadShot', lambda: change_shot.LoadShot.display(), 'shift+L')
menu.addCommand('TurboZ/ChangeShot', lambda: change_shot.ChangeShot.display(), 'shift+E')
tz.addSeparator()
menu.addCommand('TurboZ/Bake/Cam from EXR', lambda: cam_from_meta.bake(False))
menu.addCommand('TurboZ/Bake/Cam from EXR(animated)', lambda: cam_from_meta.bake())
menu.findItem('TurboZ/Bake').addSeparator()
menu.addCommand("TurboZ/Bake/Bake 2D Transform", lambda: nuke_utility.extract_2d())
menu.addCommand('TurboZ/Bypass/Selected', lambda: nuke_utility.bypass_selection(), 'alt+D')
menu.addCommand('TurboZ/Bypass/Denoisers', lambda: nuke_utility.toggle_noises())

# gizmos

h_gizmos = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gizmo")
h_gizmos = h_gizmos.replace('\\', '/')

toolbar = nuke.toolbar("Nodes")
k = toolbar.addMenu("h_gizmos")
for gizmo in os.listdir(h_gizmos):
    name, ext = os.path.splitext(gizmo)
    if ext == '.gizmo':
        k.addCommand(name, "nuke.createNode(\"{}\")".format(name))

# knob defaults
nuke.knobDefault("Read.postage_stamp", "False")
nuke.knobDefault("CheckerBoard.postage_stamp", "False")
nuke.knobDefault("Constant.postage_stamp", "False")
nuke.knobDefault("ColorWheel.postage_stamp", "False")
nuke.knobDefault("ColorBars.postage_stamp", "False")
nuke.knobDefault("Root.format", "HD_1080")
nuke.knobDefault("Views.views_colours true")
nuke.knobDefault("Blur.label", "[value size]")
if int(nuke.NUKE_VERSION_MAJOR) > 12:
    nuke.knobDefault("Cryptomatte.removeChannels", "True")
    nuke.toolbar('Nodes').addCommand('Channel/Shuffle', 'nuke.createNode("Shuffle")', icon='Shuffle.png')
    nuke.toolbar('Nodes').addCommand('Channel/ShuffleCopy', 'nuke.createNode("ShuffleCopy")', icon='ShuffleCopy.png')
