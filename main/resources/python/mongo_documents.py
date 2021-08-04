import os
import datetime
import collections
import mongoengine
from mongoengine.errors import ValidationError
from mongoengine.queryset.manager import queryset_manager


PROJECT_ROOT = os.getenv("PROJECT_ROOT", "Z:\\Projects\\Turbosaurs")


def _file_exists(filename):
    if not os.path.isfile(filename):
        raise ValidationError("File does not exists")


def _file_exists_relative(filename):
    _file_exists(os.path.join(PROJECT_ROOT, filename))


def _reorder(seq):
    '''Yield items from seq reordered to http://stackoverflow.com/q/33372753/
    seq can be any sequence, eg. a list or a Python 3 range object.
    '''
    # output first and last element before all the middles
    if seq:
        yield seq[0]
    if len(seq) > 1:
        yield seq[-1]

    # a queue of range indices (start, stop)
    queue = collections.deque([(1, len(seq)-1)])
    while queue:
        start, stop = queue.popleft()
        if start < stop:
            middle = (start + stop) // 2
            yield seq[middle]
            queue.append((start, middle))
            queue.append((middle+1, stop))


def frame_list(frames_string):
    frames_string = frames_string.replace(" ", "").split(",")
    flist = []
    for f in frames_string:
        if "-" in f:
            fr = [int(n) for n in f.split("-")]
            flist += [str(i) for i in (_reorder(range(fr[0], fr[1]+1)))]
        else:
            flist.append(f)
    return ", ".join(flist)


class NukeJob(mongoengine.Document):

    batch_name = mongoengine.StringField()
    scene_file = mongoengine.StringField(
        required=True, unique=True, validation=_file_exists)
    frames = mongoengine.StringField(required=True)
    group = mongoengine.StringField()
    department = mongoengine.StringField(default="compositing")
    output_directory = mongoengine.StringField()
    rez_env = mongoengine.StringField(default="")
    priority = mongoengine.IntField(min_value=1, max_value=100, default=100)
    nuke_version = mongoengine.StringField(default="11.3")
    render_extension = mongoengine.StringField(default="exr")
    job_id = mongoengine.StringField()

    def __str__(self):
        return self.comp_name()

    def comp_name(self):
        return os.path.splitext(os.path.split(self.scene_file)[-1])[0]

    def output_filename(self):
        return "{0}.####.{1}".format(self.comp_name(), self.render_extension)

    def shot_number(self):
        name_split = self.comp_name().split("shot_")[-1].split("_comp")[0]
        if name_split.isdigit():
            return int(name_split)

    @queryset_manager
    def by_shotnum(doc_cls, queryset, num):
        return [j for j in queryset() if j.shot_number() == num]

class MayaRenderLayer(mongoengine.EmbeddedDocument):
    layer_name = mongoengine.StringField(required=True)
    batch_name = mongoengine.StringField(required=True)
    output_directory = mongoengine.StringField()
    output_filename = mongoengine.StringField()
    priority = mongoengine.IntField(min_value=1, max_value=100, default=50)
    comment = mongoengine.StringField(default="")
    frames = mongoengine.StringField()
    job_id = mongoengine.StringField(default=None)
    renderable = mongoengine.BooleanField(default=True)

    def qc_frames(self):
        return frame_list(self.frames)

    def __str__(self):
        return "Maya Render Layer - {}".format(self.layer_name)

    def name(self):
        return "{} - {}".format(self.batch_name, self.layer_name)


class MayaJob(mongoengine.Document):
    batch_name = mongoengine.StringField()
    scene_file = mongoengine.StringField(
        required=True, unique=True, validation=_file_exists)
    episode_name = mongoengine.StringField()
    camera_name = mongoengine.StringField()
    camera_list = mongoengine.ListField()
    season = mongoengine.StringField()
    scene_preview = mongoengine.StringField()
    department = mongoengine.StringField(default="lighting")
    rez_env = mongoengine.StringField(default="")
    status = mongoengine.StringField(choices=("new", "rendering", "error", "done"), default="new")
    has_daily = mongoengine.BooleanField(default=False)
    daily = mongoengine.StringField()
    date_created = mongoengine.DateTimeField(default=datetime.datetime.utcnow)
    date_updated = mongoengine.DateTimeField(default=datetime.datetime.utcnow)
    render_layers = mongoengine.ListField(
        mongoengine.EmbeddedDocumentField(MayaRenderLayer))

    def __str__(self):
        return "Maya Job - {}".format(self.batch_name)

    def layer(self, name):
        lyr = [l for l in self.render_layers if l.layer_name == name]
        return lyr[0] if lyr else None

    def layers(self):
        return {layer.layer_name: {"frames": layer.frames, "job_id": layer.job_id} for layer in self.render_layers}

    def submitted_layers(self):
        return {layer: info["job_id"] for layer, info in self.layers().items() if info["job_id"]}


class MayaLight(mongoengine.EmbeddedDocument):

    name = mongoengine.StringField()
    light_type = mongoengine.StringField()
    attributes = mongoengine.DictField()
    xform = mongoengine.ListField()
    meta = {
            "strict": False
            }

    def __str__(self):
        return "LGT - {}".format(self.name)


class MayaLightPreset(mongoengine.Document):
    name = mongoengine.StringField(required=True, unique=True)
    scene = mongoengine.StringField()
    episode = mongoengine.StringField()
    lights = mongoengine.ListField(mongoengine.EmbeddedDocumentField(MayaLight))
    meta = {
            "strict": False
            }

    def __str__(self):
        return "Light Preset - {}".format(self.name)


class DatabaseConnection(object):
    def __init__(self, db_name, host="localhost", port=27017, alias="default"):
        self._db_name = db_name
        self._alias = alias
        self._host = host
        self._port = port

    def __enter__(self):
        self.connection = mongoengine.connect(
            self._db_name, host=self._host, port=self._port, alias=self._alias)

    def __exit__(self, type, value, traceback):
        mongoengine.connection.disconnect(alias=self._alias)
