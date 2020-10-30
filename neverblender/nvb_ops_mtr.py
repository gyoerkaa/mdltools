"""Contains Blender Operators for manipulating MTR files and properties."""

import os

import bpy

from . import nvb_def
from . import nvb_mtr


class NVB_OT_mtrparam_new(bpy.types.Operator):
    """Add a new item to the parameter list"""

    bl_idname = 'nvb.mtrparam_new'
    bl_context = "material"
    bl_label = 'Add a new parameter'

    @classmethod
    def poll(self, context):
        """Enable only if there is a material."""
        mat = context.material
        return mat is not None and mat.nvb.mtr.use

    def execute(self, context):
        """TODO: DOC."""
        mat = context.material

        param = mat.nvb.mtr.param_list.add()
        if param.ptype == 'int':
            param.pvalue = '1'
        elif param.ptype == 'float':
            param.pvalue = '1.0 1.0 1.0'
        return {'FINISHED'}


class NVB_OT_mtrparam_delete(bpy.types.Operator):
    """Delete the selected parameter from the parameter list"""

    bl_idname = 'nvb.mtrparam_delete'
    bl_context = "material"
    bl_label = 'Delete a parameter'

    @classmethod
    def poll(self, context):
        """Enable only if the list isn't empty."""
        mat = context.material
        if mat and mat.nvb.mtr.use:
            return len(mat.nvb.mtr.param_list) > 0
        return False

    def execute(self, context):
        """TODO: DOC."""
        mat = context.material
        list_idx = mat.nvb.mtr.param_list_idx

        mat.nvb.mtr.param_list.remove(list_idx)
        if list_idx > 0:
            list_idx -= 1
        return {'FINISHED'}
