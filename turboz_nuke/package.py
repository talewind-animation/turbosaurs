name = "turboz_nuke"
version = "1.0.1"

build_command = "python -m rezutil build {root}"
private_build_requires = ["rezutil-1",]

requires = [
    "mongoengine",
    "nukepedia",
    "~nuke>=11,<=13",
]

_environ = {
    "NUKE_PATH": [
        "{root}/resources",
    ],
    "PYTHONPATH": [
        "{root}/resources/pixelbucket/python",
    ],
}


def commands():
    global env
    global this
    global expandvars

    env.SHEET_UPDATER = "{root}/resources/sheet_updater/sheet_updater.exe"
    env.UPDATER_CLIENT_SECRET = "{root}/resources/sheet_updater/client_secret.json"
    env.UPDATER_CONFIG = "{root}/resources/sheet_updater/sheet_updater_config.json"
    _environ = this._environ

    for key, value in _environ.items():
        if isinstance(value, (tuple, list)):
            [env[key].append(expandvars(v)) for v in value]
        else:
            env[key] = expandvars(value)
