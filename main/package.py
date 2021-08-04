name = "turbosaurs"
version = "0.1.1"

build_command = "python -m rezutil build {root}"
private_build_requires = ["rezutil-1"]

# Variables unrelated to Rez are typically prefixed with `_`
_data = {
    "label": "Turbosaurs",
    "icon": "{root}/resources/icon_{width}x{height}.png"
}

_requires = {
    "any": [
        "base-1",

        "~maya>=2017|<=2020",
        "~nuke==11.3.5",
    ],

    # Requirements relative a request
    # E.g. if `alita maya` is requested, the "maya"
    # requirements are added to the list.
    "maya": [
        "turboz_maya",
        "vray>=4.30.00|<=5.00.22"
    ],
    "nuke": [
        "turboz_nuke",
    ]
}

_environ = {
    "any": {
        "PROJECT_NAME": "Turbosaurs",
        "ROOT_PROD": "Z:/TZ",
        "PROJECT_PATH": "{env.PROJECTS_PATH}/Turbosaurs",
        "TZ_ROOT": "{env.PROJECTS_PATH}/Turbosaurs",
    },
    "maya": {
        "MAYA_ENABLE_LEGACY_RENDER_LAYERS": "Yes",
    },
}

# ---------
#
# Internal
#
# ---------

late = locals()["late"]


@late()
def requires():
    global this
    global request
    global in_context

    requires = this._requires
    result = requires["any"][:]

    # Add request-specific requirements
    if in_context():
        for name, reqs in requires.items():
            if name not in request:
                continue

            result += reqs

    return result


def commands():
    global env
    global this
    global request
    global expandvars

    env.PYTHONPATH.append("{root}/resources/python")

    environ = this._environ
    result = list(environ["any"].items())
    # Add request-specific environments
    for key, values in environ.items():
        if key not in request:
            continue

        result += list(values.items())

    for key, value in result:
        if isinstance(value, (tuple, list)):
            [env[key].append(expandvars(v)) for v in value]
        else:
            env[key] = expandvars(value)
