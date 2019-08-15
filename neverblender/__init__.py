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
from . import nvb_material

from . import nvb_ops
from . import nvb_ops_io
from . import nvb_ops_mtr
from . import nvb_ops_anim
from . import nvb_ops_set
from . import nvb_ops_amt
from . import nvb_ops_node

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
        importlib.reload(nvb_material)

        importlib.reload(nvb_ops)
        importlib.reload(nvb_ops_io)
        importlib.reload(nvb_ops_mtr)
        importlib.reload(nvb_ops_anim)
        importlib.reload(nvb_ops_set)
        importlib.reload(nvb_ops_amt)
        importlib.reload(nvb_ops_node)

        importlib.reload(nvb_ui)
        print('Neverblender: Ready')


bl_info = {
    "name": "Neverblender",
    "author": "Attila Gyoerkoes",
    'version': (2, 8, 8),
    "blender": (2, 81, 0),
    "location": "File > Import-Export, Object Properties",
    "description": "Import, export and edit Aurora mdl format",
    "warning": "",
    "wiki_url": "https://nwn.wiki/display/NWN1/Neverblender",
    "tracker_url": "https://github.com/gyoerkaa/mdltools",
    "category": "Import-Export"}


classes = (
    nvb_props.NVB_addon_properties,

    nvb_props.NVB_PG_set_element,
    nvb_props.NVB_PG_animevent,
    nvb_props.NVB_PG_amt_event,
    nvb_props.NVB_PG_mtrparameter,
    nvb_props.NVB_PG_anim,
    nvb_props.NVB_PG_material,
    nvb_props.NVB_PG_scene,
    nvb_props.NVB_PG_flare,
    nvb_props.NVB_PG_lamp,
    nvb_props.NVB_PG_object,
    nvb_props.NVB_PG_bone,
    nvb_props.NVB_PG_emitter,

    nvb_ops_io.NVB_OT_mdlexport,
    nvb_ops_io.NVB_OT_mdlimport,
    nvb_ops_io.NVB_OT_mdl_superimport,

    nvb_ops_set.NVB_OT_set_reload,
    nvb_ops_set.NVB_OT_set_open,
    nvb_ops_set.NVB_OT_set_massimport,

    nvb_ops.NVB_OT_lensflare_new,
    nvb_ops.NVB_OT_lensflare_delete,
    nvb_ops.NVB_OT_lensflare_move,

    nvb_ops.NVB_OT_util_minimap,
    nvb_ops.NVB_OT_util_transform,

    nvb_ops_node.NVB_OT_util_genwok,
    nvb_ops_node.NVB_OT_util_nodes_pwk,
    nvb_ops_node.NVB_OT_util_nodes_dwk,
    nvb_ops_node.NVB_OT_util_nodes_tile,

    nvb_ops_amt.NVB_OT_amt_apply_pose,
    nvb_ops_amt.NVB_OT_amt_amt2psb,
    nvb_ops_amt.NVB_OT_amt_psb2amt,

    nvb_ops_mtr.NVB_OT_mtrparam_new,
    nvb_ops_mtr.NVB_OT_mtrparam_delete,

    nvb_ops_anim.NVB_OT_anim_clone,
    nvb_ops_anim.NVB_OT_anim_scale,
    nvb_ops_anim.NVB_OT_anim_crop,
    nvb_ops_anim.NVB_OT_anim_pad,
    nvb_ops_anim.NVB_OT_anim_focus,
    nvb_ops_anim.NVB_OT_anim_new,
    nvb_ops_anim.NVB_OT_anim_delete,
    nvb_ops_anim.NVB_OT_anim_moveback,
    nvb_ops_anim.NVB_OT_anim_move,
    nvb_ops_anim.NVB_OT_anim_event_new,
    nvb_ops_anim.NVB_OT_anim_event_delete,
    nvb_ops_anim.NVB_OT_anim_event_move,
    nvb_ops_anim.NVB_OT_amt_event_new,
    nvb_ops_anim.NVB_OT_amt_event_delete,

    nvb_ui.NVB_UL_set_element,
    nvb_ui.NVB_UL_lensflares,
    nvb_ui.NVB_UL_anims,
    nvb_ui.NVB_UL_anim_events,
    nvb_ui.NVB_UL_mtr_params,

    nvb_ui.NVB_PT_aurorabase,
    nvb_ui.NVB_PT_dummy,
    nvb_ui.NVB_PT_armature,
    nvb_ui.NVB_PT_set,
    nvb_ui.NVB_PT_mtr,
    nvb_ui.NVB_PT_lamp_data,
    nvb_ui.NVB_PT_lamp_lensflares,
    nvb_ui.NVB_PT_mesh_object,
    nvb_ui.NVB_MT_animlist_specials,
    nvb_ui.NVB_PT_animlist,
    nvb_ui.NVB_PT_utils,
    nvb_ui.NVB_PT_emitter,
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
    # bpy.utils.register_module(__name__)

    for cl in classes:
        bpy.utils.register_class(cl)

    bpy.types.Object.nvb = \
        bpy.props.PointerProperty(type=nvb_props.NVB_PG_object)
    bpy.types.Material.nvb = \
        bpy.props.PointerProperty(type=nvb_props.NVB_PG_material)
    bpy.types.Light.nvb = \
        bpy.props.PointerProperty(type=nvb_props.NVB_PG_lamp)
    bpy.types.Scene.nvb = \
        bpy.props.PointerProperty(type=nvb_props.NVB_PG_scene)
    bpy.types.ParticleSettings.nvb = \
        bpy.props.PointerProperty(type=nvb_props.NVB_PG_emitter)
    bpy.types.Bone.nvb = \
        bpy.props.PointerProperty(type=nvb_props.NVB_PG_bone)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    """TODO:Doc."""
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

    for cl in reversed(classes):
        bpy.utils.unregister_class(cl)

    del bpy.types.Object.nvb
    del bpy.types.Material.nvb
    del bpy.types.Light.nvb
    del bpy.types.Scene.nvb
    del bpy.types.ParticleSettings.nvb
    del bpy.types.Bone.nvb

    # bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
    register()
