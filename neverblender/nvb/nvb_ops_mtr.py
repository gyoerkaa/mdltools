"""Contains Blender Operators for manipulating MTR files and properties."""

import os

import bpy

from . import nvb_def
from . import nvb_mtr


class NVB_OT_mtr_generate(bpy.types.Operator):
    """Generate a new Text Block containing from the current material."""
    bl_idname = "nvb.mtr_generate"
    bl_label = "Generate MTR"

    @classmethod
    def poll(self, context):
        """Enable only if mtrs are used and in text mode."""
        mat = context.material
        return mat is not None and mat.nvb.usemtr and mat.nvb.mtrsrc == 'TEXT'

    def execute(self, context):
        """TODO: DOC."""
        material = context.material
        if not material:
            self.report({'ERROR'}, 'Error: No material.')
            return {'CANCELLED'}
        mtr = nvb_mtr.Mtr()
        # Either change existing or create new text block
        if material.nvb.mtrtext and material.nvb.mtrtext in bpy.data.texts:
            txtBlock = bpy.data.texts[material.nvb.mtrtext]
            mtr.loadTextBlock(txtBlock)
        else:
            if material.nvb.mtrname:
                txtname = material.nvb.mtrname + '.mtr'
            else:
                txtname = material.name + '.mtr'
            txtBlock = bpy.data.texts.new(txtname)
            material.nvb.mtrtext = txtBlock.name
        options = nvb_def.ExportOptions()
        asciiLines = nvb_mtr.Mtr.generateAscii(material, options)
        txtBlock.clear()
        txtBlock.write('\n'.join(asciiLines))
        # Report
        self.report({'INFO'}, 'Created ' + txtBlock.name)
        return {'FINISHED'}


class NVB_OT_mtr_embed(bpy.types.Operator):
    """Embed the MTR file into the blend file by creating a Text block"""
    bl_idname = "nvb.mtr_embed"
    bl_label = "Embed MTR"

    @classmethod
    def poll(self, context):
        """Enable only if mtrs are used and a path is set."""
        mat = context.material
        if mat is not None and mat.nvb.usemtr:
            return mat.nvb.mtrpath != ''
        return False

    def execute(self, context):
        """TODO: DOC."""
        material = context.material
        if not material:
            self.report({'ERROR'}, 'Error: No material.')
            return {'CANCELLED'}
        # Get the previously stored filepath
        if not material.nvb.mtrpath:
            self.report({'ERROR'}, 'Error: No path to file.')
            return {'CANCELLED'}
        bpy.ops.text.open(filepath=material.nvb.mtrpath, internal=True)
        return {'FINISHED'}


class NVB_OT_mtr_open(bpy.types.Operator):
    """Open material file"""
    bl_idname = "nvb.mtr_open"
    bl_label = "Open MTR"

    filename_ext = '.mtr'
    filter_glob = bpy.props.StringProperty(default='*.mtr', options={'HIDDEN'})
    filepath = bpy.props.StringProperty(subtype='FILE_PATH')

    @classmethod
    def poll(self, context):
        """Enable only if mtrs are used and in file mode."""
        mat = context.material
        if mat is not None:
            return mat.nvb.usemtr and mat.nvb.mtrsrc == 'FILE'
        return False

    def execute(self, context):
        material = context.material
        if not material:
            self.report({'ERROR'}, 'Error: No material.')
            return {'CANCELLED'}
        if material.nvb.mtrsrc != 'FILE':
            self.report({'ERROR'}, 'Error: Wrong MTR mode.')
            return {'CANCELLED'}
        if not self.filepath:
            self.report({'ERROR'}, 'Error: No path to file.')
            return {'CANCELLED'}
        mtrpath, mtrfilename = os.path.split(self.filepath)
        # Load mtr
        mtr = nvb_mtr.Mtr(material.name)
        if not mtr.loadFile(self.filepath):
            self.report({'ERROR'}, 'Error: Invalid file.')
            return {'CANCELLED'}
        options = nvb_def.ImportOptions()
        options.filepath = self.filepath
        mtr.create(material, options)
        self.report({'INFO'}, 'Loaded ' + mtrfilename)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        # Open browser, take reference to 'self'
        # read the path to selected file,
        # put path in declared string type data structure self.filepath

        return {'RUNNING_MODAL'}


class NVB_OT_mtr_reload(bpy.types.Operator):
    """Reload MTR, update current material"""
    bl_idname = "nvb.mtr_reload"
    bl_label = "Reload MTR"

    def reload_file(self, material):
        """Reload mtr file from disk."""
        if not material.nvb.mtrpath:
            self.report({'ERROR'}, 'Error: No path to file.')
            return {'CANCELLED'}
        mtrpath = material.nvb.mtrpath
        # Reload
        mtr = nvb_mtr.Mtr(material.name)
        if not mtr.loadFile(mtrpath):
            self.report({'ERROR'}, 'Error: No data.')
            return {'CANCELLED'}
        options = nvb_def.ImportOptions()
        options.filepath = material.nvb.mtrpath  # for image search
        mtr.create(material, options)
        self.report({'INFO'}, 'Reloaded ' + os.path.split(mtrpath)[1])
        return {'FINISHED'}

    def reload_text(self, material):
        """Reload mtr data from Blender text block."""
        if not material.nvb.mtrtext:
            self.report({'ERROR'}, 'Error: No text block.')
            return {'CANCELLED'}
        if material.nvb.mtrtext not in bpy.data.texts:
            self.report({'ERROR'}, 'Error: ' + material.nvb.mtrtext +
                        ' does not exist.')
            return {'CANCELLED'}
        txt_block = bpy.data.texts[material.nvb.mtrtext]
        # Reload data
        mtr = nvb_mtr.Mtr(material.name)
        if not mtr.loadTextBlock(txt_block):
            self.report({'ERROR'}, 'Error: No data.')
            return {'CANCELLED'}
        mtr.filepath = material.nvb.mtrpath  # Restore filepath
        options = nvb_def.ImportOptions()
        options.filepath = material.nvb.mtrpath  # for image search
        mtr.create(material, options)
        self.report({'INFO'}, 'Reloaded ' + txt_block.name)
        return {'FINISHED'}

    @classmethod
    def poll(self, context):
        """Enable only if mtrs are used."""
        mat = context.material
        if mat and mat.nvb.usemtr:
            return (mat.nvb.mtrsrc == 'FILE' and mat.nvb.mtrpath != '') or \
                   (mat.nvb.mtrsrc == 'TEXT' and mat.nvb.mtrtext != '')
        return False

    def execute(self, context):
        """TODO: DOC."""
        material = context.material
        if not material:
            self.report({'ERROR'}, 'Error: No material.')
            return {'CANCELLED'}
        if material.nvb.mtrsrc == 'FILE':
            return self.reload_file(material)
        elif material.nvb.mtrsrc == 'TEXT':
            return self.reload_text(material)


class NVB_OT_mtrparam_new(bpy.types.Operator):
    """Add a new item to the parameter list"""

    bl_idname = 'nvb.mtrparam_new'
    bl_label = 'Add a new parameter'

    @classmethod
    def poll(self, context):
        """Enable only if there is a material."""
        mat = context.material
        return mat is not None and mat.nvb.usemtr

    def execute(self, context):
        """TODO: DOC."""
        material = context.material
        plist = material.nvb.mtrparam_list

        param = plist.add()
        if param.ptype == 'int':
            param.pvalue = '1'
        elif param.ptype == 'float':
            param.pvalue = '1.0 1.0 1.0'
        return {'FINISHED'}


class NVB_OT_mtrparam_delete(bpy.types.Operator):
    """Delete the selected parameter from the parameter list"""

    bl_idname = 'nvb.mtrparam_delete'
    bl_label = 'Delete a parameter'

    @classmethod
    def poll(self, context):
        """Enable only if the list isn't empty."""
        mat = context.material
        if mat is not None and mat.nvb.usemtr:
            return len(mat.nvb.mtrparam_list) > 0
        return False

    def execute(self, context):
        """TODO: DOC."""
        mat = context.material
        plist = mat.nvb.mtrparam_list
        plist_idx = mat.nvb.mtrparam_list_idx

        plist.remove(plist_idx)
        if plist_idx > 0:
            plist_idx = plist_idx - 1
        return {'FINISHED'}
