name = 'tz_submitter'

version = '0.1.4'

authors = ['har8unyan@gmail.com']

build_command = "python -m rezutil build {root}"
private_build_requires = ["rezutil-1",]

requires = [
    'python-2.7',
    'turbosaurs',
    'deadlineapi',
    'mongoengine',
    'python_qt5',
    'Qt.py',
    'ffmpeg',
]

def commands():
    global env
    global alias

    env.DB_HOST = "192.168.99.2"
    env.PYTHONPATH.append("{root}/python")

    alias("submitter", "python {root}/python/submitter_window.py")
