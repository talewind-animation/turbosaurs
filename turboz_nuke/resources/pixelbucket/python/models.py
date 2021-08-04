import os
import mongoengine
from mongoengine.errors import ValidationError
from mongoengine.queryset.manager import queryset_manager


def _file_exists(filename):
    if not os.path.exists(filename):
        raise ValidationError("File does not exists")


class NukeJob(mongoengine.Document):

    batch_name = mongoengine.StringField()
    scene_file = mongoengine.StringField(
        required=True, unique=True, validation=_file_exists)
    frames = mongoengine.StringField(required=True)
    group = mongoengine.StringField()
    department = mongoengine.StringField(default="compositing")
    output_directory = mongoengine.StringField()
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
