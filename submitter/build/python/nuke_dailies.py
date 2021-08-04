import os

NK_SCRIPTS_ROOT = "\\\\dell\\StudioRepository\\DeadlineRepository\\nk_dailies"
DAILIES_TEMPLATE = os.path.join(NK_SCRIPTS_ROOT, "template")


def load_template():
    with open(DAILIES_TEMPLATE, "r") as f:
        return f.read()


def write_nk_file(text, filename):
    with open(filename, "w") as f:
        f.write(text)


def build_daily(info):
    first_frame, last_frame = info["frames"].split("-")
    template_text = load_template()
    template_text = template_text.replace(
        "___SHOTNAME___", "shot_{}".format(info["batch_name"].split("sc_")[-1]))
    template_text = template_text.replace("___FIRST_FRAME___", first_frame)
    template_text = template_text.replace("___LAST_FRAME___", last_frame)

    render_dir = info["render_dir"].replace("Render_scenes", "Render")
    render_dir = render_dir.replace("Z:\\Projects\\Turbosaurs", "//dell/nas/Projects/Turbosaurs")
    output_filename = os.path.join(
        render_dir, "dailies", "{}.mov".format(info["batch_name"]))

    template_text = template_text.replace(
        "___RENDER_OUTPUT___", output_filename.replace("\\", "/"))
    render_layers = info["render_layers"]
    for layer, filename in render_layers.items():
        template_text = template_text.replace(
            "___{}_IN___filename".format(layer), filename.replace("\\", "/"))

    filename = os.path.join(NK_SCRIPTS_ROOT, "dailies",
                            info["batch_name"]+".nk")
    write_nk_file(template_text, filename)
    return (filename, output_filename)
