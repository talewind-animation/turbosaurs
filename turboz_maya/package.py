name = 'turboz_maya'

version = '1.0.2'

authors = ['har8unyan@gmail.com']

build_command = "python -m rezutil build {root}"
private_build_requires = ["rezutil-1",]

requires = [
    'maya',
    'twacore_maya',
    'mongoengine',
    'ffmpeg',
    'Pillow-1.1.7',
    'Qt.py',
    'deadlineapi',
]

def commands():
    global env


    env.XBMLANGPATH.prepend("{root}/resources/icons")
    env.MAYA_MODULE_PATH.append("{root}/resources/modules")

    # aleksey shit
    # needs to be removed or replaced
    projects_path = env.PROJECTS_PATH.value()

    env.MAYA_SCRIPT_PATH.append("{}\\RnD\\Maya2020\\scripts".format(projects_path))
    env.MAYA_SHELF_PATH.append("{}\\RnD\\Maya2020\\shelves".format(projects_path))
    env.PYTHONPATH.append("{}\\RnD\\Maya2020\\scripts".format(projects_path))
