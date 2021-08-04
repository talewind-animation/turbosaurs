import os

import nuke

from mongo_documents import NukeJob, DatabaseConnection

DB_NAME = "rendering"
DB_HOST = "192.168.99.2"


def get_nuke_version():
    return "{}.{}".format(nuke.NUKE_VERSION_MAJOR, nuke.NUKE_VERSION_MINOR)

def make_sumbission2():
    root = nuke.root()
    comp_file = os.path.abspath(root.knob('name').value())

    compdir, compname = os.path.split(comp_file)

    shot_dir = os.path.dirname(compdir)
    epname = os.path.split(os.path.dirname(shot_dir))[1]
    output_dir = os.path.abspath(os.path.join(shot_dir, 'render'))
    output_file = '{}.####.exr'.format(os.path.splitext(compname)[0])

    rez_resolve = os.environ["REZ_USED_RESOLVE"]

    frames = '{}-{}'.format(int(root.knob('first_frame').value()), int(root.knob('last_frame').value()))

    with DatabaseConnection(DB_NAME, host=DB_HOST, port=27017):
        job = NukeJob.objects(scene_file=comp_file).first()
        if job:
            job.update(
                batch_name=epname,
                scene_file=comp_file,
                frames=frames,
                rez_env=rez_resolve,
                group="nuke",
                output_directory=output_dir,
                nuke_version=get_nuke_version()
                )
            nuke.message("Successfully updated nuke job!")
            return

        try:
            job = NukeJob(
                batch_name=epname,
                scene_file=comp_file,
                frames=frames,
                rez_env=rez_resolve,
                group="nuke",
                output_directory=output_dir,
                nuke_version=get_nuke_version()
            )

            job.save()

            nuke.message("Successfully created nuke job!")
        except:
            nuke.message("Failed to submitte...")
