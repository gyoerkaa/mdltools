"""TODO: DOC."""

import bpy

from . import nvb_ops
from . import nvb_ops_set
from . import nvb_ops_anim

from . import nvb_def
from . import nvb_utils


class NVB_UL_lensflares(bpy.types.UIList):
    """UI List for displaying lensflares."""

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        """Draw a single lensflare."""

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.texture, icon='NONE')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text='', icon='PARTICLE_DATA')


class NVB_UL_anims(bpy.types.UIList):
    """UI List for displaying animations."""

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        """Draw a single animation."""

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, 'name', text='', emboss=False)
            icn = 'CHECKBOX_DEHLT' if item.mute else 'CHECKBOX_HLT'
            layout.prop(item, 'mute', text='', icon=icn, emboss=False)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text='', icon='POSE_DATA')


class NVB_UL_anim_events(bpy.types.UIList):
    """UI List for displaying animation events."""

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        """Draw a single animation event."""

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            split = layout.split(factor=0.7)
            split.prop(item, 'name', text='', emboss=False)
            row = split.row(align=True)
            row.prop(item, 'frame', text='', emboss=False)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text='', icon='LIGHT')


class NVB_UL_amt_events(bpy.types.UIList):
    """UI List for displaying (armature) animation events."""

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        """TODO: DOC."""

        # Supports all 3 layout types
        icn = 'LIGHT'
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if index < len(nvb_def.animation_event_names):
                layout.label(text=item.name, translate=False, icon='NONE')
            else:
                layout.prop(item, 'name', text='', emboss=False)
            layout.prop(item, 'fire', text='', icon=icn, emboss=False)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.prop(item, 'fire', text='', icon=icn, emboss=False)


class NVB_UL_mtr_params(bpy.types.UIList):
    """TODO: DOC."""

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        """TODO: DOC."""
        custom_icon = 'NONE'

        # Supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.pname, icon=custom_icon)
            layout.label(text=item.ptype)
            layout.label(text=item.pvalue)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text='', icon=custom_icon)


class NVB_UL_set_element(bpy.types.UIList):
    """TODO: DOC."""

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        """TODO: DOC."""
        custom_icon = 'NONE'

        # Supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.el_name, icon=custom_icon)
            layout.label(text=item.el_size)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text='', icon=custom_icon)


class NVB_PT_aurorabase(bpy.types.Panel):
    """Property panel for additional properties needed for the mdl file.

    This is only visible if there is an aurora base present.
    """

    bl_label = 'Aurora Base Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        """Only visible if there is an aurora base present."""
        mdl_base = nvb_utils.get_obj_mdl_base(context.object)
        return mdl_base is not None

    def draw(self, context):
        """Drwa the panel."""
        layout = self.layout
        mdl_base = nvb_utils.get_obj_mdl_base(context.object)

        split = layout.split(factor=0.33)
        col = split.column()
        col.label(text='Classification:')
        col.label(text='Supermodel:')
        col.label(text='Animation Scale:')
        col = split.column()
        col.prop(mdl_base.nvb, 'classification', text='')
        row = col.row(align=True)
        row.prop(mdl_base.nvb, 'supermodel', text='')
        row.operator('scene.nvb_superimport', icon='FILEBROWSER', text='')
        col.prop(mdl_base.nvb, 'animscale', text='')


class NVB_PT_dummy(bpy.types.Panel):
    """Property panel for additional properties needed for the mdl file.

    This is only available for EMPTY objects with a parent.
    It is located under the object panel in the properties window,
    """

    bl_label = 'Aurora Dummy Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        """Render only when of EMTPY-type and has parent."""
        obj = context.object
        return (obj and (obj.type == 'EMPTY') and obj.parent is not None)

    def draw(self, context):
        """TODO: DOC."""
        obj = context.object
        layout = self.layout

        # Common properties for all types of Dummies
        box = layout.box()
        box.prop(obj.nvb, 'emptytype', text='Type')
        box.row().prop(obj.nvb, 'imporder')

        # Display properties depending on type of the empty
        if (obj.nvb.emptytype == nvb_def.Emptytype.REFERENCE):
            layout.separator()
            box = layout.box()
            box.prop(obj.nvb, 'refmodel')
            box.prop(obj.nvb, 'reattachable')


class NVB_PT_bone(bpy.types.Panel):
    """Property panel for bone properties.

    Holds additional bone properties used by the pseudo bone helper.
    """

    bl_label = 'Aurora Bone Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'bone'

    @classmethod
    def poll(cls, context):
        """only visible if a bone is selected."""
        return context.object and (context.bone or context.edit_bone)

    def draw(self, context):
        """Draw the panel."""
        layout = self.layout
        obj = context.object
        bone = context.bone
        # Disabled in edit mode: Property is not properly saved
        layout.enabled = context.bone is not None
        # Get bone - independent of mode
        if not bone:
            edit_bone = context.edit_bone
            bone = obj.data.bones[edit_bone.name]
        # Settings for conversion to pseudo-bones
        box = layout.box()
        box.label(text='Conversion Settings')
        row = box.row()
        row.prop(bone.nvb, 'psd_bone_shape')


class NVB_PT_armature(bpy.types.Panel):
    """Property panel for armature properties.

    Tools for auto-generating armatures from a models skinmesh and copying
    animation from a models meshes.
    """

    bl_label = 'Aurora Armature Utilities'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        """Only visible for armatures."""
        return (context.object and context.object.type == 'ARMATURE')

    def draw(self, context):
        """Draw the panel."""
        obj = context.object
        addon = context.preferences.addons[__package__]
        layout = self.layout

        # Armature Helper
        box = layout.box()
        box.label(text='Generate Pseudo Bones')
        row = box.row()
        row.prop(addon.preferences, 'util_psb_anim_mode')
        row = box.row()
        sub = row.row()
        sub.enabled = (addon.preferences.util_psb_anim_mode == 'NONE') or \
                      (addon.preferences.util_psb_anim_mode == 'ACTION')
        sub.prop(addon.preferences, 'util_psb_insert_base')
        row.prop(addon.preferences, 'util_psb_insert_root')

        box.operator('nvb.amt_amt2psb', icon='BONE_DATA').use_existing = False
        layout.separator()

        box = layout.box()
        box.label(text='Apply Restpose')
        box.operator('nvb.amt_apply_pose', icon='POSE_DATA')
        layout.separator()

        box = layout.box()
        box.label(text='Animation Transfer')
        box.prop(addon.preferences, 'util_psb_anim_mode')
        box.prop(obj.nvb, 'util_psb_anim_target')
        box.operator('nvb.amt_amt2psb', text='Copy Animations',
                     icon='NODETREE').use_existing = True
        layout.separator()


class NVB_PT_set(bpy.types.Panel):
    """Property panel for loading set files.

    Tools for batch loading models with the data from a set file
    """

    bl_label = 'Aurora Set File'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'

    @classmethod
    def poll(cls, context):
        """Draw panel in the scene properties."""
        return context.scene is not None

    def draw(self, context):
        """Draw the panel."""
        scene = context.scene
        layout = self.layout

        row = layout.row(align=True)
        row.prop(scene.nvb, 'set_filepath', text='')
        row.operator(nvb_ops_set.NVB_OT_set_open.bl_idname,
                     icon='FILEBROWSER', text='')
        row.operator(nvb_ops_set.NVB_OT_set_reload.bl_idname,
                     icon='NDOF_TURN', text='')

        layout.separator()
        row = layout.row()
        row.prop(scene.nvb, 'set_mode', expand=True)

        layout.separator()
        box = layout.box()
        row = box.row()
        if scene.nvb.set_mode == 'GP':
            row.template_list('NVB_UL_set_element', 'TheGroupList',
                              scene.nvb, 'set_group_list',
                              scene.nvb, 'set_group_list_idx')
        elif scene.nvb.set_mode == 'TR':
            row.template_list('NVB_UL_set_element', 'TheTerrainList',
                              scene.nvb, 'set_terrain_list',
                              scene.nvb, 'set_terrain_list_idx')
        elif scene.nvb.set_mode == 'CR':
            row.template_list('NVB_UL_set_element', 'TheCrosserList',
                              scene.nvb, 'set_crosser_list',
                              scene.nvb, 'set_crosser_list_idx')
        row = box.row()
        row.operator(nvb_ops_set.NVB_OT_set_massimport.bl_idname,
                     icon='IMPORT', text='Mass Import')


class NVB_PT_mtr(bpy.types.Panel):
    """Property panel for additional material properties (mtr files).


    """
    bl_label = 'Aurora MTR File'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'material'

    @classmethod
    def poll(cls, context):
        """TODO: DOC."""
        return (context.object and context.material is not None)

    def draw_header(self, context):
        mat = context.material

        self.layout.prop(mat.nvb, 'usemtr', text='')

    def draw(self, context):
        """TODO: DOC."""
        layout = self.layout
        mat = context.material

        layout.enabled = mat.nvb.usemtr

        layout.prop(mat.nvb, 'mtrname')

        layout.separator()
        row = layout.row()
        row.prop(mat.nvb, 'mtrsrc', expand=True)
        layout.separator()
        if mat.nvb.mtrsrc == 'FILE':
            row = layout.row(align=True)
            row.operator('nvb.mtr_embed', icon='UGLYPACKAGE', text='')
            row.prop(mat.nvb, 'mtrpath', text='')
            row.operator('nvb.mtr_open', icon='FILEBROWSER', text='')
            row.operator('nvb.mtr_reload', icon='NDOF_TURN', text='')
        elif mat.nvb.mtrsrc == 'TEXT':
            row = layout.row(align=True)
            row.prop_search(mat.nvb, 'mtrtext', bpy.data, 'texts', text='')
            row.operator('nvb.mtr_generate', icon='IMPORT', text='')
            row.operator('nvb.mtr_reload', icon='NDOF_TURN', text='')

        layout.separator()
        box = layout.box()
        box.prop(mat.nvb, 'shadervs')
        box.prop(mat.nvb, 'shaderfs')

        layout.separator()
        box = layout.box()
        box.label(text='Parameters')
        row = box.row()
        row.template_list('NVB_UL_mtr_params', 'TheParamList',
                          mat.nvb, 'mtrparam_list',
                          mat.nvb, 'mtrparam_list_idx')
        col = row.column(align=True)
        col.operator('nvb.mtrparam_new', icon='ADD', text='')
        col.operator('nvb.mtrparam_delete', icon='REMOVE', text='')
        col.separator()
        if mat.nvb.mtrparam_list_idx >= 0 and \
           len(mat.nvb.mtrparam_list) > 0:
            plist = mat.nvb.mtrparam_list[mat.nvb.mtrparam_list_idx]
            row = box.row(align=True)
            row.prop(plist, 'pname', text='')
            row.prop(plist, 'ptype', text='')
            row = box.row()
            row.prop(plist, 'pvalue')


class NVB_PT_lamp_data(bpy.types.Panel):
    """Property panel for additional light or lamp properties.

    This holds all properties not supported by blender,
    but used by the aurora engine. This is only available for LIGHT objects.
    It is located under the object panel in the properties window.
    """

    bl_label = 'Aurora Light Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        """Draw only ia a lamp object is selected."""
        return (context.object and context.object.type == 'LIGHT')

    def draw(self, context):
        """Draw the panel."""
        obj = context.object
        data = obj.data
        layout = self.layout
        layout.prop(data.nvb, 'lightpriority', text='Lightpriority')
        split = layout.split()
        col = split.column(align=True)
        col.prop(data.nvb, 'ambientonly', text='Ambient Only')
        col.prop(data.nvb, 'shadow', text='Shadows')
        col = split.column(align=True)
        col.prop(data.nvb, 'fadinglight', text='Fading')
        col.prop(data.nvb, 'isdynamic', text='Is dynamic')
        col.prop(data.nvb, 'affectdynamic', text='Affect dynamic')


class NVB_PT_lamp_lensflares(bpy.types.Panel):
    """Property panel for additional light or lamp properties.

    This holds all properties not supported by blender,
    but used by the aurora engine. This is only available for LIGHT objects.
    It is located under the object panel in the properties window.
    """

    bl_label = 'Aurora Lensflares'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        """Draw only ia a lamp object is selected."""
        return (context.object and context.object.type == 'LIGHT')

    def draw(self, context):
        """Draw the panel."""
        obj = context.object
        data = obj.data
        layout = self.layout
        # Lens flares
        row = layout.row()
        row.prop(data.nvb, 'uselensflares')
        sub = row.row(align=True)
        sub.enabled = data.nvb.uselensflares
        sub.prop(data.nvb, 'flareradius', text='Radius')

        row = layout.row()
        row.enabled = data.nvb.uselensflares
        row.template_list('NVB_UL_lensflares', 'TheFlareList',
                          data.nvb, 'flareList',
                          data.nvb, 'flareListIdx')
        col = row.column(align=True)
        col.operator('nvb.lightflare_new', icon='ADD', text='')
        col.operator('nvb.lightflare_delete', icon='REMOVE', text='')
        col.separator()
        col.operator('nvb.lightflare_move',
                     icon='TRIA_UP', text='').direction = 'UP'
        col.operator('nvb.lightflare_move',
                     icon='TRIA_DOWN', text='').direction = 'DOWN'
        flare_idx = data.nvb.flareListIdx
        if flare_idx >= 0 and len(data.nvb.flareList) > flare_idx:
            item = data.nvb.flareList[flare_idx]
            sub = layout.column()
            sub.enabled = data.nvb.uselensflares
            sub.prop(item, 'texture')
            sub.row().prop(item, 'colorshift')
            row = sub.row()
            row.prop(item, 'size')
            row.prop(item, 'position')


class NVB_PT_lamp_object(bpy.types.Panel):
    """Property panel for additional light or lamp properties.

    This holds all properties not supported by blender,
    but used by the aurora engine. This is only available for LIGHT objects.
    It is located under the object panel in the properties window.
    """

    bl_label = 'Aurora Lamp Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        """Draw only ia a lamp object is selected."""
        return False
        return (context.object and context.object.type == 'LIGHT')

    def draw(self, context):
        """Draw the panel."""
        obj = context.object
        layout = self.layout

        box = layout.box()
        row = box.row(align=True)
        row.prop(obj.nvb, 'lighttype', text='Type')
        row.operator('nvb.light_generatename', icon='SORTALPHA', text='')


class NVB_PT_mesh_object(bpy.types.Panel):
    """Property panel for additional mesh properties.

    This holds all properties not supported by blender,
    but used by the aurora engine. This is only available for MESH objects.
    It is located under the object panel in the properties window.
    """

    bl_label = 'Aurora Mesh Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        """Draw only ia a mesh object is selected."""
        return (context.object and context.object.type == 'MESH')

    def draw(self, context):
        """Draw the panel."""
        obj = context.object
        layout = self.layout
        # Common properties for all types of meshes
        box = layout.box()
        split = box.split(factor=0.33)
        col = split.column()
        col.label(text='Type:')
        col.label(text='Wirecolor:')
        col = split.column()
        col.prop(obj.nvb, 'meshtype', text='')
        col.prop(obj, 'color', text='')
        box.row().prop(obj.nvb, 'imporder')

        # Additional props for emitters
        if (obj.nvb.meshtype == nvb_def.Meshtype.EMITTER):
            layout.separator()

        # Additional props for aabb walkmeshes
        elif obj.nvb.meshtype == nvb_def.Meshtype.AABB:
            layout.separator()
            box = layout.box()
            box.label(text='AABB Properties')

            box.operator('nvb.util_genwok',
                         text='Setup Materials', icon='MATERIAL')
            box.label(text='(Warning: Removes current materials)')
        # Trimesh, danglymesh, skin
        else:
            layout.separator()
            box = layout.box()
            box.label(text='Trimesh Properties')

            row = box.row()
            box.prop(obj.nvb, 'shininess', text='Shininess')
            box.prop(obj.nvb, 'tilefade', text='Tilefade')
            split = box.split()
            col = split.column()
            col.prop(obj, 'hide_render', text='Render')
            col.prop(obj.nvb, 'shadow', text='Shadow')
            col = split.column()
            col.prop(obj.nvb, 'beaming', text='Beaming')
            col.prop(obj.nvb, 'inheritcolor', text='Inherit Color')
            col.prop(obj.nvb, 'rotatetexture', text='Rotate Texture')

            box.prop(obj.nvb, 'transparencyhint', text='Transparency Hint')
            row = box.row()
            row.label(text='Smoothgroups')
            row.prop(obj.nvb, 'smoothgroup', text='Smooth Group', expand=True)

            # Additional props for danglymeshes
            if (obj.nvb.meshtype == nvb_def.Meshtype.DANGLYMESH):
                layout.separator()
                box = layout.box()
                box.label(text='Danglymesh Properties')

                box.prop_search(obj.nvb, 'constraints', obj, 'vertex_groups',
                                text='Constraints')
                box.prop(obj.nvb, 'period', text='Period')
                box.prop(obj.nvb, 'tightness', text='Tightness')
                box.prop(obj.nvb, 'displacement', text='Displacement')

            # Additional props for skins
            elif (obj.nvb.meshtype == nvb_def.Meshtype.SKIN):
                pass

            # Additional props for Animmeshes
            elif (obj.nvb.meshtype == nvb_def.Meshtype.ANIMMESH):
                layout.separator()
                box = layout.box()
                box.label(text='Animmesh Properties')

                # obj.data.shape_keys is not always present
                if obj.data and obj.data.shape_keys:
                    box.prop_search(obj, 'nvb.aurorashapekey',
                                    obj.data.shape_keys, 'key_blocks',
                                    text='Shapekey')
                else:
                    box.prop(obj, 'nvb.aurorashapekey', text='Shapekey')


class NVB_MT_animlist_specials(bpy.types.Menu):
    """Animation List Specials."""

    bl_label = "Animation List Specials"

    def draw(self, context):
        """Draw the panel."""
        layout = self.layout
        layout.operator(nvb_ops_anim.NVB_OT_anim_moveback.bl_idname,
                        icon='LOOP_FORWARDS')
        layout.operator(nvb_ops_anim.NVB_OT_anim_pad.bl_idname,
                        icon='FULLSCREEN_ENTER')
        layout.operator(nvb_ops_anim.NVB_OT_anim_crop.bl_idname,
                        icon='FULLSCREEN_EXIT')
        layout.operator(nvb_ops_anim.NVB_OT_anim_scale.bl_idname,
                        icon='SORTSIZE')
        layout.operator(nvb_ops_anim.NVB_OT_anim_clone.bl_idname,
                        icon='NODETREE')


class NVB_PT_animlist(bpy.types.Panel):
    """Property panel for animationslist.

    Property panel for additional properties needed for the mdl file
    format. This is only available for EMPTY objects.
    It is located under the object data panel in the properties window
    """

    bl_label = 'Aurora Animations'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        """Draw only if part of a valid mdl is selected."""
        mdl_base = nvb_utils.get_obj_mdl_base(context.object)
        return mdl_base is not None

    def draw(self, context):
        """Draw the panel."""
        layout = self.layout
        mdl_base = nvb_utils.get_obj_mdl_base(context.object)
        if mdl_base:
            # Display and add/remove animations
            row = layout.row()
            row.template_list('NVB_UL_anims', 'TheAnimList',
                              mdl_base.nvb, 'animList',
                              mdl_base.nvb, 'animListIdx',
                              rows=7)
            col = row.column(align=True)
            col.operator('nvb.anim_new', icon='ADD', text='')
            col.operator('nvb.anim_delete', icon='REMOVE', text='')
            col.separator()
            col.operator('nvb.anim_move',
                         icon='TRIA_UP', text='').direction = 'UP'
            col.operator('nvb.anim_move',
                         icon='TRIA_DOWN', text='').direction = 'DOWN'
            col.separator()
            col.operator('nvb.anim_focus',
                         icon='PREVIEW_RANGE', text='')
            col.menu('NVB_MT_animlist_specials',
                     icon='PLUS', text="")
            anim_list = mdl_base.nvb.animList
            anim_list_idx = mdl_base.nvb.animListIdx
            if anim_list_idx >= 0 and len(anim_list) > anim_list_idx:
                anim = anim_list[anim_list_idx]
                row = layout.row()
                row.prop(anim, 'name')
                row = layout.row()
                row.prop(anim, 'root_obj')
                row = layout.row()
                row.prop(anim, 'transtime')
                row = layout.row()
                split = row.split()
                col = split.column(align=True)
                col.prop(anim, 'frameStart')
                col.prop(anim, 'frameEnd')

                # Event Helper. Display and add/remove events.
                box = layout.box()
                box.label(text='Events')

                row = box.row()
                row.template_list('NVB_UL_anim_events', 'TheEventList',
                                  anim, 'eventList',
                                  anim, 'eventListIdx')
                col = row.column(align=True)
                col.operator('nvb.anim_event_new', text='', icon='ADD')
                col.operator('nvb.anim_event_delete', text='', icon='REMOVE')
                col.separator()
                col.operator('nvb.anim_event_move',
                             icon='TRIA_UP', text='').direction = 'UP'
                col.operator('nvb.anim_event_move',
                             icon='TRIA_DOWN', text='').direction = 'DOWN'
            layout.separator()


class NVB_PT_amt_events(bpy.types.Panel):
    """Property panel for armature animation events.

    Property panel for additional properties needed for the mdl file
    format.
    """

    bl_label = 'Aurora Armature Events'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        """Draw only if an armature is selected."""
        return context.object and context.object.type == 'ARMATURE'

    def draw_header(self, context):
        """Draw a header with integrated activate button."""
        amt = context.object
        self.layout.prop(amt.nvb, 'use_amt_events', text='')

    def draw(self, context):
        """Draw the panel."""
        layout = self.layout
        amt = context.object

        layout.enabled = amt.nvb.use_amt_events

        # Display and add/remove events.
        row = layout.row()
        row.template_list('NVB_UL_amt_events', 'TheAmtEventList',
                          amt.nvb, 'amt_event_list',
                          amt.nvb, 'amt_event_list_idx',
                          rows=7)
        col = row.column(align=True)
        col.operator('nvb.amt_event_new', icon='ADD', text='')
        col.operator('nvb.amt_event_delete', icon='REMOVE', text='')


class NVB_PT_utils(bpy.types.Panel):
    """Property panel for Tools.

    Property panel with utilities
    """

    bl_label = 'Aurora Utilities'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        """Draw only if part of a valid mdl is selected."""
        mdl_base = nvb_utils.get_obj_mdl_base(context.object)
        return mdl_base is not None

    def draw(self, context):
        """Draw the panel."""
        layout = self.layout
        mdl_base = nvb_utils.get_obj_mdl_base(context.object)
        addon = context.preferences.addons[__package__]
        addon_prefs = addon.preferences
        render = context.scene.render
        if mdl_base:
            # Armature Helper
            box = layout.box()
            box.label(text='Armature Helper')

            split = box.split(factor=0.33)
            col = split.column()
            col.label(text='Source: ')
            col.label(text='Animations: ')
            col = split.column()
            row = col.row()
            row.prop(addon_prefs, 'util_amt_src', expand=True)
            col.prop(addon_prefs, 'util_amt_anim_mode', text='')
            row = box.row()
            row.prop(addon_prefs, 'util_amt_connect')
            row.prop(addon_prefs, 'util_amt_strip_name')
            box.operator('nvb.amt_psb2amt', icon='BONE_DATA')
            layout.separator()

            # Transform Helper
            box = layout.box()
            box.label(text='Transform Helper')

            row = box.row()
            row.column().prop(mdl_base, 'location')
            row.column().prop(mdl_base, 'scale')
            box.operator('nvb.util_transform', icon='SORTSIZE')
            layout.separator()

            # Node Setup Helper
            box = layout.box()
            box.label(text='Node Setup Helper')

            row = box.row()
            row.prop(addon_prefs, 'util_nodes_type', expand=True)
            if addon_prefs.util_nodes_type == nvb_def.Walkmeshtype.PWK:
                box.prop(addon_prefs, 'util_nodes_pwk_mode')
                split = box.split(factor=0.33)
                col = split.column()
                col = split.column()
                col.row().prop(addon_prefs, 'util_nodes_pwk_detect_islands')
                box.operator('nvb.util_nodes_pwk', icon='QUESTION')
            elif addon_prefs.util_nodes_type == nvb_def.Walkmeshtype.DWK:
                box.prop(addon_prefs, 'util_nodes_dwk_mode')
                box.label(text='')
                box.operator('nvb.util_nodes_dwk', icon='QUESTION')
            elif addon_prefs.util_nodes_type == nvb_def.Walkmeshtype.WOK:
                box.label(text='')
                box.label(text='')
                box.operator('nvb.util_nodes_tile', icon='QUESTION')
            layout.separator()

            # Minimap Helper
            box = layout.box()
            box.label(text='Minimap Helper')

            split = box.split(factor=0.33)
            col = split.column()
            col.label(text='Size:')
            col.label(text='Display:')
            col = split.column()
            col.prop(render, 'resolution_y', text='')
            row = col.row(align=True)
            row.prop(render, 'display_mode', text='')
            row.prop(render, 'use_lock_interface', icon_only=True)

            row = box.row(align=True)
            row.operator(nvb_ops.NVB_OT_util_minimap.bl_idname,
                         text='Setup Scene',
                         icon='SCENE_DATA').batch_mode = False
            row.operator('render.render', text='Render', icon='RENDER_STILL')
            layout.separator()


class NVB_PT_emitter(bpy.types.Panel):
    """Property panel for emitter properties.

    Property holding additional propeties for particle systems
    """
    bl_label = 'Aurora Emitter'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'particle'
    COMPAT_ENGINES = {'BLENDER_RENDER'}

    @classmethod
    def particle_panel_poll(cls, context):
        """Get particle settings status."""
        psys = context.particle_system
        engine = context.scene.render.engine
        settings = 0

        if psys:
            settings = psys.settings
        elif isinstance(context.space_data.pin_id, bpy.types.ParticleSettings):
            settings = context.space_data.pin_id

        if not settings:
            return False
        return settings.is_fluid is False and (engine in cls.COMPAT_ENGINES)

    @classmethod
    def particle_get_settings(cls, context):
        """Get particle settings from context."""
        if context.particle_system:
            return context.particle_system.settings
        elif isinstance(context.space_data.pin_id, bpy.types.ParticleSettings):
            return context.space_data.pin_id
        return None

    @classmethod
    def particle_panel_enabled(cls, context, psys):
        """Determine if the particle panel is enabled."""
        if psys is None:
            return True
        phystype = psys.settings.physics_type
        if psys.settings.type in {'EMITTER', 'REACTOR'} and \
           phystype in {'NO', 'KEYED'}:
            return True
        else:
            return (psys.point_cache.is_baked is False) and \
                   (not psys.is_edited) and \
                   (not context.particle_system_editable)

    @classmethod
    def poll(cls, context):
        """Draw only if a particle system is selected."""
        part = NVB_PT_emitter.particle_get_settings(context)
        if part:
            return not part.is_fluid
        return False

    def draw(self, context):
        """Draw the panel."""
        layout = self.layout
        part_system = context.particle_system
        part_settings = NVB_PT_emitter.particle_get_settings(context)

        layout.enabled = \
            NVB_PT_emitter.particle_panel_enabled(context, part_system) and \
            (part_system is None or not part_system.has_multiple_caches) and \
            part_settings.type == 'EMITTER'

        box = layout.box()
        box.label("Particle Style")
        split = box.split(factor=0.25)
        col = split.column()
        col.label("Update:")
        col.label("")
        col.label("Render:")
        col.label("Blend:")
        col.label("Spawn:")
        col = split.column()
        col.prop(part_settings.nvb, "update", text="")
        sub = col.row()
        sub.enabled = part_settings.nvb.update == 'single'
        sub.prop(part_settings.nvb, "loop")
        col.prop(part_settings.nvb, "render", text="")
        col.prop(part_settings.nvb, "blend", text="")
        col.prop(part_settings.nvb, "spawntype", text="")
        box.prop(part_settings.nvb, "renderorder")
        layout.separator()

        box = layout.box()
        box.label("Particle Settings")
        split = box.split()
        col = split.column()
        col.prop(part_settings.nvb, "birthrate")
        col.prop(part_settings.nvb, "lifeexp")
        col.prop(part_settings.nvb, "spread")
        col.prop(part_settings, "mass")
        col = split.column()
        col.prop(part_settings, "normal_factor", text="Velocity")
        col.prop(part_settings, "factor_random", text="Rand. Velocity")
        col.label("")
        col.prop(part_settings, "angular_velocity_factor", text="Rotation")

        row = box.row()
        row.prop(part_settings.nvb, "affectedbywind")
        row.prop(part_settings.nvb, "splat")

        split = box.split(factor=0.25)
        col = split.column()
        col.label("Color:")
        col.label("Alpha:")
        col.label("Size X:")
        col.label("Size Y:")
        col.separator()
        col.label("Bounce:")
        col = split.column()
        row = col.row(align=True)
        row.prop(part_settings.nvb, "colorstart", text="")
        row.prop(part_settings.nvb, "colorend", text="")
        row = col.row(align=True)
        row.prop(part_settings.nvb, "alphastart", text="Start")
        row.prop(part_settings.nvb, "alphaend", text="End")
        row = col.row(align=True)
        row.prop(part_settings.nvb, "sizestart", text="Start")
        row.prop(part_settings.nvb, "sizeend", text="End")
        row = col.row(align=True)
        row.prop(part_settings.nvb, "sizestart_y", text="Start")
        row.prop(part_settings.nvb, "sizeend_y", text="End")
        col.separator()
        row = col.row(align=True)
        row.prop(part_settings.nvb, "bounce", text="")
        sub = row.row()
        sub.enabled = part_settings.nvb.bounce is True
        sub.prop(part_settings.nvb, "bounce_co", text="")
        box.prop(part_settings.nvb, "blurlength")
        box.prop(part_settings.nvb, "deadspace")
        layout.separator()

        box = layout.box()
        box.label("Texture")
        box.row().prop(part_settings.nvb, "particletype", expand=True)
        if part_settings.nvb.particletype == 'chunk':
            split = box.split(factor=0.25)
            col = split.column()
            col.label("Chunk:")
            col = split.column()
            col.prop(part_settings.nvb, "chunk", text="")
        else:
            split = box.split(factor=0.25)
            col = split.column()
            col.label("Texture:")
            col.label()
            col.label()
            col.separator()
            col.label("Grid:")
            col.label("Frame:")

            col = split.column()
            col.prop(part_settings.nvb, "texture", text="")
            col.prop(part_settings.nvb, "twosidedtex")
            col.prop(part_settings.nvb, "m_istinted")
            col.separator()
            row = col.row(align=True)
            row.prop(part_settings.nvb, "xgrid", text="X")
            row.prop(part_settings.nvb, "ygrid", text="Y")
            row = col.row(align=True)
            row.prop(part_settings.nvb, "framestart", text="Start")
            row.prop(part_settings.nvb, "frameend", text="End")
            col.prop(part_settings.nvb, "random")
            col.prop(part_settings.nvb, "fps")
        layout.separator()

        box = layout.box()
        box.prop(part_settings.nvb, "p2p", text="Point to Point")
        sub = box.column()
        sub.enabled = part_settings.nvb.p2p is True
        sub.row().prop(part_settings.nvb, "p2p_sel", expand=True)
        sub.separator()
        if part_settings.nvb.p2p_sel == '2':  # Gravity type p2p
            sub.prop(part_settings.nvb, "grav")
            sub.prop(part_settings.nvb, "drag")
            sub.prop(part_settings.nvb, "threshold")
        else:  # Bezier type p2p
            sub.prop(part_settings.nvb, "p2p_bezier2")
            sub.prop(part_settings.nvb, "p2p_bezier3")
            sub.prop(part_settings.nvb, "combinetime")
        layout.separator()

        box = layout.box()
        box.label("Blast Properties")
        box.enabled = part_settings.nvb.update == 'explosion'
        row = box.row()
        row.prop(part_settings.nvb, "blastradius")
        row.prop(part_settings.nvb, "blastlength")
        layout.separator()

        box = layout.box()
        box.label("Lightning Properties")
        box.enabled = part_settings.nvb.update == 'lightning'
        box.prop(part_settings.nvb, "lightningdelay")
        box.prop(part_settings.nvb, "lightningradius")
        box.prop(part_settings.nvb, "lightningscale")
        layout.separator()

        box = layout.box()
        box.label("Inheritance")
        split = box.split()
        col = split.column()
        col.prop(part_settings.nvb, "inherit")
        col.prop(part_settings.nvb, "inheritvel")
        col = split.column()
        col.prop(part_settings.nvb, "inherit_local")
        col.prop(part_settings.nvb, "inherit_part")
        layout.separator()
