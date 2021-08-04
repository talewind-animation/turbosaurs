import os
import nukescripts
import nuke


def all_reads():
    return nuke.allNodes(group=nuke.toNode("BG_crypto"), filter="Read")+nuke.allNodes(group=nuke.toNode("CH_crypto"), filter="Read")+nuke.allNodes("Read")

def replace_aovs(path, folder):
    for node in all_reads():
        name = node.name()
        folder_in = "{}_IN_".format(folder)
        if name.startswith(folder_in):
            aov = name.replace(folder_in, "")
            if aov == "beauty":
                aov = path
                files = [f for f in nuke.getFileNameList(aov) if ".exr" in f]
            else:
                aov = os.path.join(path, aov)
                files = nuke.getFileNameList(aov)
            if files:
                node.knob('file').fromUserText(os.path.join(aov, files[0]))

def shot_droped(droptype, dropped_data):
    if not os.path.isdir(dropped_data):
        return False
    folder = os.path.split(dropped_data)[-1]
    if not folder in ["BG", "CH", "FLOOR_AO", "WATER"]:
        print(folder)
        return False
    replace_aovs(dropped_data, folder)
    return True

def register():
    nukescripts.drop.addDropDataCallback(shot_droped)

register()
