# ##### BEGIN GPL LICENSE BLOCK #####
#
# Neverblender. Copyright 2012-2018 Attila Gyoerkoes
#
# Neverblender is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Neverblender is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Neverblender.  If not, see <http://www.gnu.org/licenses/>.
#
# ##### END GPL LICENSE BLOCK #####

"""TODO: DOC."""


import bpy

from .nvb import nvb_def
from .nvb import nvb_utils
from .nvb import nvb_io
from .nvb import nvb_mdl
from .nvb import nvb_node
from .nvb import nvb_anim
from .nvb import nvb_animnode

from .nvb import nvb_props
from .nvb import nvb_ops
from .nvb import nvb_ui

if 'bpy' in locals():
    import importlib
    if 'nvb_def' in locals():
        importlib.reload(nvb_def)
        importlib.reload(nvb_utils)
        importlib.reload(nvb_io)
        importlib.reload(nvb_mdl)
        importlib.reload(nvb_node)
        importlib.reload(nvb_anim)
        importlib.reload(nvb_animnode)

        importlib.reload(nvb_props)
        importlib.reload(nvb_ops)
        importlib.reload(nvb_ui)
        print('Neverblender: Ready')


bl_info = {
    "name": "Neverblender",
    "author": "Attila Gyoerkoes",
    'version': (2, 10),
    "blender": (2, 7, 4),
    "location": "File > Import-Export, Object Properties",
    "description": "Import, export and edit Aurora mdl format",
    "warning": "",
    "wiki_url": ""
                "",
    "tracker_url": "",
    "category": "Import-Export"}


classes = [
    nvb_props.NVB_PG_animevent,
    nvb_props.NVB_PG_anim,
    nvb_props.NVB_PG_material,
    nvb_props.NVB_PG_flare,
    nvb_props.NVB_PG_lamp,
    nvb_props.NVB_PG_object,
    nvb_ui.NVB_UL_lensflares,
    nvb_ui.NVB_UL_anims,
    nvb_ui.NVB_UL_animevents,
    nvb_ui.NVB_PT_rootdummy,
    nvb_ui.NVB_PT_dummy,
    nvb_ui.NVB_PT_armature,
    nvb_ui.NVB_PT_material,
    nvb_ui.NVB_PT_mtr,
    nvb_ui.NVB_PT_lamp_data,
    nvb_ui.NVB_PT_lamp_object,
    nvb_ui.NVB_PT_lensflares,
    nvb_ui.NVB_PT_mesh_object,
    nvb_ui.NVB_MT_animlist_specials,
    nvb_ui.NVB_PT_animlist,
    nvb_ui.NVB_PT_utils
]


def menu_func_export(self, context):
    """TODO:Doc."""
    self.layout.operator(nvb_ops.NVB_OT_mdlexport.bl_idname,
                         text="Aurora (.mdl)")


def menu_func_import(self, context):
    """TODO:Doc."""
    self.layout.operator(nvb_ops.NVB_OT_mdlimport.bl_idname,
                         text="Aurora (.mdl)")


def register():
    """TODO:Doc."""
    bpy.utils.register_module(__name__)
    """
    from bpy.utils import register_class
    for cl in classes:
        register_class(cl)
    """
    bpy.types.Object.nvb = \
        bpy.props.PointerProperty(type=nvb_props.NVB_PG_object)
    bpy.types.Material.nvb = \
        bpy.props.PointerProperty(type=nvb_props.NVB_PG_material)
    bpy.types.Lamp.nvb = \
        bpy.props.PointerProperty(type=nvb_props.NVB_PG_lamp)
    bpy.types.INFO_MT_file_import.append(menu_func_import)
    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    """TODO:Doc."""
    bpy.types.INFO_MT_file_export.remove(menu_func_export)
    bpy.types.INFO_MT_file_import.remove(menu_func_import)
    """
    from bpy.utils import unregister_class
    for cl in reversed(classes):
        unregister_class(cl)
    """
    del bpy.types.Object.nvb

    bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
    register()
