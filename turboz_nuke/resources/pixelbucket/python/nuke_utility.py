import os
import json

import nuke
import nukescripts

def axis_on_point():
    VertSel = nukescripts.snap3d.getSelection()
    axis = nuke.nodes.Axis()
    if VertSel.length:
        nukescripts.snap3d.translateToPoints(axis)
    return axis

def extract_2d():
    selection = nuke.selectedNodes()
    if len(selection)>1:
        cam, axis = selection
    else:
        cam = selection[0]
        axis = axis_on_point()
    rec = nuke.nodes.Reconcile3D()

    root = nuke.Root()
    start, end = (int(root['first_frame'].getValue()), int(root['last_frame'].getValue()))

    rec.setInput(1, cam)
    rec.setInput(2, axis)

    nuke.execute(rec, start, end)

    transform = nuke.nodes.Transform(name='trackedPoint')

    transform['translate'].fromScript(rec['output'].toScript())
    nuke.delete(rec)
    nuke.delete(axis)

    [n.setSelected(False) for n in nuke.selectedNodes()]
    transform.setSelected(True)

def toggle_bypass(node):
    knob = node['disable']
    dis = knob.getValue()
    if knob.hasExpression():
        knob.clearAnimated()
        knob.setValue(0)
    elif dis == 0:
        knob.setValue(1)
    elif dis == 1:
        knob.setExpression('$gui')

def bypass(node):
    knob = node['disable']
    dis = knob.getValue()
    if knob.hasExpression():
        knob.clearAnimated()
        knob.setValue(0)
    elif dis == 0:
        knob.setExpression('$gui')

def bypass_selection():
    for node in nuke.selectedNodes():
        toggle_bypass(node)

def toggle_noises():
    for denoise in nuke.allNodes('Denoise2'):
        bypass(denoise)

def clear_tz_path():
    tz_root = 'Z:/Projects/Turbosaurs/'
    wrong = []
    for node in nuke.allNodes('Read') + nuke.allNodes('ReadGeo2') + nuke.allNodes('Camera2') + nuke.allNodes('Write'):
        file_knob = node.knob('file')
        filename = file_knob.getValue()
        if filename != '' and filename.startswith(tz_root) and os.path.isabs(filename):
            file_knob.setValue(filename.replace(tz_root, ''))
        elif filename == '':
            continue
        elif os.path.isabs(filename):
            node['tile_color'].setValue(4278190335)
            wrong.append(node.name())
    if wrong:
        nuke.message('You have filenames with local path:\n{}'.format('\n'.join(wrong)))

def make_sumbission():
    root = nuke.root()
    comp_file = root.knob('name').value()

    compdir, compname = os.path.split(comp_file)

    shot_dir = os.path.dirname(compdir)
    epname = os.path.split(os.path.dirname(shot_dir))[1]
    output_dir = os.path.abspath(os.path.join(shot_dir, 'render'))
    output_file = '{}.####.exr'.format(os.path.splitext(compname)[0])

    frames = '{}-{}'.format(int(root.knob('first_frame').value()), int(root.knob('last_frame').value()))

    job_info = {
        'Filename': os.path.abspath(comp_file),
        'BatchName': epname,
        'Frames': frames,
        'Name': compname,
        'OutputDirectory0': output_dir,
        'OutputFilename0': output_file
    }

    submite_file = os.path.abspath(os.path.join(compdir, os.path.splitext(compname)[0]+'.sbmit'))
    with open(submite_file, 'w') as f:
        json.dump(job_info, f, indent=4)

    nuke.message("Successfully created nuke job!")
