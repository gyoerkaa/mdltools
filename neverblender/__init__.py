#    BEGIN GPL LICENSE BLOCK
#
#    Neverblender, adds support for the mdl file format to blender
#    Copyright (C) 2018 Attila Gyoerkoes
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#    END GPL LICENSE BLOCK

"""TODO: DOC."""


import bpy

from . import nvb_def
from . import nvb_utils
from . import nvb_mdl
from . import nvb_node
from . import nvb_anim
from . import nvb_animnode
from . import nvb_mtr

from . import nvb_props
from . import nvb_ops
from . import nvb_ops_io
from . import nvb_ops_mtr
from . import nvb_ops_anim
from . import nvb_ops_set
from . import nvb_ops_amt
from . import nvb_ui

if 'bpy' in locals():
    import importlib
    if 'nvb_def' in locals():
        importlib.reload(nvb_def)
        importlib.reload(nvb_utils)
        importlib.reload(nvb_mdl)
        importlib.reload(nvb_node)
        importlib.reload(nvb_anim)
        importlib.reload(nvb_animnode)
        importlib.reload(nvb_mtr)

        importlib.reload(nvb_props)
        importlib.reload(nvb_ops)
        importlib.reload(nvb_ops_io)
        importlib.reload(nvb_ops_mtr)
        importlib.reload(nvb_ops_anim)
        importlib.reload(nvb_ops_set)
        importlib.reload(nvb_ops_amt)
        importlib.reload(nvb_ui)
        print('Neverblender: Ready')


bl_info = {
    "name": "Neverblender",
    "author": "Attila Gyoerkoes",
    'version': (2, 7, 228),
    "blender": (2, 7, 9),
    "location": "File > Import-Export, Object Properties",
    "description": "Import, export and edit Aurora mdl format",
    "warning": "",
    "wiki_url": "https://nwn.wiki/display/NWN1/Neverblender",
    "tracker_url": "https://github.com/gyoerkaa/mdltools",
    "category": "Import-Export"}


classes = (
    nvb_props.NVB_PG_animevent,
    nvb_props.NVB_PG_anim,
    nvb_props.NVB_PG_material,
    nvb_props.NVB_PG_flare,
    nvb_props.NVB_PG_lamp,
    nvb_props.NVB_PG_object,
    nvb_props.NVB_PG_bone,
    nvb_ui.NVB_UL_lensflares,
    nvb_ui.NVB_UL_anims,
    nvb_ui.NVB_UL_animevents,
    nvb_ui.NVB_UL_set_element,
    nvb_ui.NVB_PT_aurorabase,
    nvb_ui.NVB_PT_dummy,
    nvb_ui.NVB_PT_armature,
    nvb_ui.NVB_PT_material,
    nvb_ui.NVB_PT_set,
    nvb_ui.NVB_PT_mtr,
    nvb_ui.NVB_PT_lamp_data,
    nvb_ui.NVB_PT_lamp_object,
    nvb_ui.NVB_PT_lamp_lensflares,
    nvb_ui.NVB_PT_mesh_object,
    nvb_ui.NVB_MT_animlist_specials,
    nvb_ui.NVB_PT_animlist,
    nvb_ui.NVB_PT_utils,
)


def menu_func_export(self, context):
    """TODO:Doc."""
    self.layout.operator(nvb_ops_io.NVB_OT_mdlexport.bl_idname,
                         text="Aurora (.mdl)")


def menu_func_import(self, context):
    """TODO:Doc."""
    self.layout.operator(nvb_ops_io.NVB_OT_mdlimport.bl_idname,
                         text="Aurora (.mdl)")


def register():
    """TODO:Doc."""
    bpy.utils.register_module(__name__)
    """
    for cl in classes:
        bpy.utils.register_class(cl)
    """
    bpy.types.Object.nvb = \
        bpy.props.PointerProperty(type=nvb_props.NVB_PG_object)
    bpy.types.Material.nvb = \
        bpy.props.PointerProperty(type=nvb_props.NVB_PG_material)
    bpy.types.Lamp.nvb = \
        bpy.props.PointerProperty(type=nvb_props.NVB_PG_lamp)
    bpy.types.Scene.nvb = \
        bpy.props.PointerProperty(type=nvb_props.NVB_PG_scene)
    bpy.types.Particle.nvb = \
        bpy.props.PointerProperty(type=nvb_props.NVB_PG_emitter)
    bpy.types.Bone.nvb = \
        bpy.props.PointerProperty(type=nvb_props.NVB_PG_bone)

    bpy.types.INFO_MT_file_import.append(menu_func_import)
    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    """TODO:Doc."""
    bpy.types.INFO_MT_file_export.remove(menu_func_export)
    bpy.types.INFO_MT_file_import.remove(menu_func_import)
    """
    for cl in reversed(classes):
        bpy.utils.unregister_class(cl)
    """
    del bpy.types.Object.nvb
    del bpy.types.Material.nvb
    del bpy.types.Lamp.nvb
    del bpy.types.Scene.nvb

    bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
    register()
