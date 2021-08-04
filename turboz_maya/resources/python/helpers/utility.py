from functools import wraps
from maya import mel
import maya.cmds as cmds


def viewport_disabled(func):
    """
    Decorator - turn off Maya display while func is running.
    if func will fail, the error will be raised after.
    """

    @wraps(func)
    def wrap(*args, **kwargs):
        mel.eval("paneLayout -e -manage false $gMainPane")
        try:
            return func(*args, **kwargs)
        except Exception:
            raise
        finally:
            mel.eval("paneLayout -e -manage true $gMainPane")

    return wrap

def get_attr_in_layer(attr=None, layer=None):

    """
    Same as cmds.getAttr but this gets the attribute's value in a given render layer without having to switch to it

    Parameters
    ----------
    attr (str) : Attribute name ex: "node.attribute"
    layer (str) : Layer name ex: "layer_name"

    Returns
    -------
    True : Can return any objects
    """

    connection_list = cmds.listConnections(attr, plugs=True)
    if connection_list is None:
        return cmds.getAttr(attr)
    for connection in connection_list:
        attr_component_list = connection.split(".")
        if attr_component_list[0] == layer:
            attr = ".".join(attr_component_list[0:-1])
            return cmds.getAttr("%s.value" % attr)
    return get_attr_in_layer(attr, "defaultRenderLayer")
