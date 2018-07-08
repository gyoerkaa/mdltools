"""TODO: DOC."""

import bpy

from . import nvb_def
from . import nvb_utils


class NVB_UL_lensflares(bpy.types.UIList):
    """TODO: DOC."""

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        """TODO: DOC."""
        custom_icon = 'NONE'

        # Supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(item.texture, icon=custom_icon)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label('', icon=custom_icon)


class NVB_UL_anims(bpy.types.UIList):
    """TODO: DOC."""

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        """TODO: DOC."""
        # Supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, translate=False, icon_value=icon)
            muteIcon = 'RESTRICT_VIEW_ON' if item.mute else 'RESTRICT_VIEW_OFF'
            layout.prop(item, 'mute', text='', icon=muteIcon, emboss=False)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label('', icon=icon)


class NVB_UL_animevents(bpy.types.UIList):
    """TODO: DOC."""

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        """TODO: DOC."""
        custom_icon = 'NONE'

        # Supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(item.name, icon=custom_icon)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label('', icon=custom_icon)


class NVB_UL_mtrparams(bpy.types.UIList):
    """TODO: DOC."""

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        """TODO: DOC."""
        custom_icon = 'NONE'

        # Supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(item.pname, icon=custom_icon)
            layout.label(item.ptype)
            layout.label(item.pvalue)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label('', icon=custom_icon)


class NVB_UL_set_element(bpy.types.UIList):
    """TODO: DOC."""

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        """TODO: DOC."""
        custom_icon = 'NONE'

        # Supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(item.el_name, icon=custom_icon)
            layout.label(item.el_size)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label('', icon=custom_icon)


class NVB_PT_aurorabase(bpy.types.Panel):
    """Property panel for additional properties needed for the mdl file.

    This is only available for EMPTY objects without a parent.
    It is located under the object panel in the properties window,
    """

    bl_label = 'Aurora Base Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        """TODO: DOC."""
        mdl_base = nvb_utils.get_obj_aurora_root(context.object)
        return mdl_base is not None

    def draw(self, context):
        """TODO: DOC."""
        layout = self.layout
        mdl_base = nvb_utils.get_obj_aurora_root(context.object)

        split = layout.split(percentage=0.33)
        col = split.column()
        col.label(text='Classification:')
        col.label(text='Supermodel:')
        col.label(text='Animation Scale:')
        col = split.column()
        col.prop(mdl_base.nvb, 'classification', text='')
        row = col.row(align=True)
        row.prop(mdl_base.nvb, 'supermodel', text='')
        row.operator('nvb.mdl_superimport', icon='IMPORT', text='')
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
    """Property panel for armature properties.

    Tools for auto-generating armatures from a models skinmesh and copying
    animation from a models meshes.
    """

    bl_label = 'Aurora Bone Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'bone'

    @classmethod
    def poll(cls, context):
        """TODO: DOC."""
        return False
        # return context.bone

    def draw(self, context):
        """TODO: DOC."""
        bone = context.bone
        layout = self.layout
        # Armature Helper
        box = layout.box()
        box.label(text='Armature Helper Settings')
        row = box.row()
        row.prop(bone.nvb, 'helper_amt_ctype', text='Conversion type')


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
        """TODO: DOC."""
        return (context.object and context.object.type == 'ARMATURE')

    def draw(self, context):
        """TODO: DOC."""
        obj = context.object
        addon = context.user_preferences.addons[__package__]
        layout = self.layout

        # Armature Helper
        box = layout.box()
        box.label(text='Generate Pseudo Bones')
        row = box.row()
        row.prop(addon.preferences, 'helper_psb_anicopy')
        row.prop(addon.preferences, 'helper_psb_insertroot')
        box.operator('nvb.amt_amt2psb', icon='BONE_DATA')
        layout.separator()

        box = layout.box()
        box.label(text='Apply Restpose')
        box.operator('nvb.amt_apply_pose', icon='POSE_DATA')
        layout.separator()

        box = layout.box()
        box.label(text='Animation Transfer')
        box.prop_search(obj.nvb, 'helper_psb_anitarget', bpy.data, 'objects')
        box.operator('nvb.amt_anims2psb', icon='NODETREE')
        layout.separator()


class NVB_PT_material(bpy.types.Panel):
    """Property panel for material properties.

    """

    bl_label = 'Aurora Material Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'material'

    @classmethod
    def poll(cls, context):
        """TODO: DOC."""
        return (context.object and context.material is not None)

    def draw(self, context):
        """TODO: DOC."""
        mat = context.material
        layout = self.layout

        # Ambient color parameters
        box = layout.box()
        box.label('Ambient')
        split = box.split(percentage=0.5)
        col = split.column()
        col.prop(mat.nvb, 'ambient_color', text='')
        sub = col.column()
        sub.active = (not mat.use_shadeless)
        sub.prop(mat.nvb, 'ambient_intensity')
        col = split.column()

        layout.separator()
        box = layout.box()
        box.prop(mat.nvb, 'renderhint')


class NVB_PT_set(bpy.types.Panel):
    bl_label = 'Aurora Set File'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'

    @classmethod
    def poll(cls, context):
        """TODO: DOC."""
        return context.scene is not None

    def draw(self, context):
        """TODO: DOC."""
        scene = context.scene
        layout = self.layout

        row = layout.row(align=True)
        row.prop(scene.nvb, 'set_filepath', text='')
        row.operator('nvb.set_open', icon='FILESEL', text='')
        row.operator('nvb.set_reload', icon='FILE_REFRESH', text='')

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
        row.operator('nvb.set_massimport', icon='IMPORT', text='Mass Import')


class NVB_PT_mtr(bpy.types.Panel):
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
        mat = context.material
        layout = self.layout

        sub = layout.column()
        sub.active = mat.nvb.usemtr

        sub.prop(mat.nvb, 'mtrname')

        sub.separator()
        row = sub.row()
        row.prop(mat.nvb, 'mtrsrc', expand=True)
        sub.separator()
        if mat.nvb.mtrsrc == 'FILE':
            row = sub.row(align=True)
            row.operator('nvb.mtr_embed', icon='UGLYPACKAGE', text='')
            row.prop(mat.nvb, 'mtrpath', text='')
            row.operator('nvb.mtr_open', icon='FILESEL', text='')
            row.operator('nvb.mtr_reload', icon='FILE_REFRESH', text='')
        elif mat.nvb.mtrsrc == 'TEXT':
            row = sub.row(align=True)
            row.prop_search(mat.nvb, 'mtrtext', bpy.data, 'texts', text='')
            row.operator('nvb.mtr_generate', icon='IMPORT', text='')
            row.operator('nvb.mtr_reload', icon='FILE_REFRESH', text='')

        sub.separator()
        box = sub.box()
        box.prop(mat.nvb, 'shadervs')
        box.prop(mat.nvb, 'shaderfs')

        sub.separator()
        box = sub.box()
        box.label('Parameters')
        row = box.row()
        row.template_list('NVB_UL_mtrparams', 'TheParamList',
                          mat.nvb, 'mtrparam_list',
                          mat.nvb, 'mtrparam_list_idx')
        col = row.column(align=True)
        col.operator('nvb.mtrparam_new', icon='ZOOMIN', text='')
        col.operator('nvb.mtrparam_delete', icon='ZOOMOUT', text='')
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
    but used by the aurora engine. This is only available for LAMP objects.
    It is located under the object panel in the properties window.
    """

    bl_label = 'Aurora Light Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        """TODO: DOC."""
        return (context.object and context.object.type == 'LAMP')

    def draw(self, context):
        """TODO: DOC."""
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
    but used by the aurora engine. This is only available for LAMP objects.
    It is located under the object panel in the properties window.
    """

    bl_label = 'Aurora Lensflares'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        """TODO: DOC."""
        return (context.object and context.object.type == 'LAMP')

    def draw(self, context):
        """TODO: DOC."""
        obj = context.object
        data = obj.data
        layout = self.layout
        # Lens flares
        row = layout.row()
        row.prop(data.nvb, 'uselensflares')
        sub = row.row(align=True)
        sub.active = data.nvb.uselensflares
        sub.prop(data.nvb, 'flareradius', text='Radius')

        row = layout.row()
        row.active = data.nvb.uselensflares
        row.template_list('NVB_UL_lensflares', 'TheFlareList',
                          data.nvb, 'flareList',
                          data.nvb, 'flareListIdx')
        col = row.column(align=True)
        col.operator('nvb.lightflare_new', icon='ZOOMIN', text='')
        col.operator('nvb.lightflare_delete', icon='ZOOMOUT', text='')
        col.separator()
        col.operator('nvb.lightflare_move',
                     icon='TRIA_UP', text='').direction = 'UP'
        col.operator('nvb.lightflare_move',
                     icon='TRIA_DOWN', text='').direction = 'DOWN'
        if data.nvb.flareListIdx >= 0 and len(data.nvb.flareList) > 0:
            item = data.nvb.flareList[data.nvb.flareListIdx]
            sub = layout.column()
            sub.active = data.nvb.uselensflares
            sub.prop(item, 'texture')
            sub.row().prop(item, 'colorshift')
            row = sub.row()
            row.prop(item, 'size')
            row.prop(item, 'position')


class NVB_PT_lamp_object(bpy.types.Panel):
    """Property panel for additional light or lamp properties.

    This holds all properties not supported by blender,
    but used by the aurora engine. This is only available for LAMP objects.
    It is located under the object panel in the properties window.
    """

    bl_label = 'Aurora Lamp Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        """TODO: DOC."""
        return (context.object and context.object.type == 'LAMP')

    def draw(self, context):
        """TODO: DOC."""
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
        """TODO: DOC."""
        return (context.object and context.object.type == 'MESH')

    def draw(self, context):
        """TODO: DOC."""
        obj = context.object
        layout = self.layout
        # Common properties for all types of meshes
        box = layout.box()
        split = box.split(percentage=0.33)
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
            box = layout.box()
            box.prop_search(obj.nvb, 'rawascii', bpy.data, 'texts',
                            text='Emitter Data')
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
            row.prop(obj.nvb, 'selfillumcolor', text='Selfillum. color')
            box.prop(obj.nvb, 'shininess', text='Shininess')
            box.prop(obj.nvb, 'tilefade', text='Tilefade')
            split = box.split()
            col = split.column()
            col.prop(obj.nvb, 'render', text='Render')
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
                    box.prop_search(obj.nvb, 'aurorashapekey',
                                    obj.data.shape_keys, 'key_blocks',
                                    text='Shapekey')
                else:
                    box.prop(obj.nvb, 'aurorashapekey', text='Shapekey')


class NVB_MT_animlist_specials(bpy.types.Menu):
    """Animation List Specials."""

    bl_label = "Animation List Specials"

    def draw(self, context):
        """TODO: Doc."""
        layout = self.layout
        layout.operator('nvb.anim_moveback',
                        icon='LOOP_FORWARDS')
        layout.operator('nvb.anim_pad',
                        icon='FULLSCREEN_ENTER')
        layout.operator('nvb.anim_crop',
                        icon='FULLSCREEN_EXIT')
        layout.operator('nvb.anim_scale',
                        icon='SORTSIZE')
        layout.operator('nvb.anim_clone',
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
        """TODO: DOC."""
        mdl_base = nvb_utils.get_obj_aurora_root(context.object)
        return mdl_base is not None

    def draw(self, context):
        """TODO: DOC."""
        layout = self.layout
        mdl_base = nvb_utils.get_obj_aurora_root(context.object)
        if mdl_base:
            # Anim Helper. Display and add/remove events.
            row = layout.row()
            row.template_list('NVB_UL_anims', 'TheAnimList',
                              mdl_base.nvb, 'animList',
                              mdl_base.nvb, 'animListIdx',
                              rows=7)
            col = row.column(align=True)
            col.operator('nvb.anim_new', icon='ZOOMIN', text='')
            col.operator('nvb.anim_delete', icon='ZOOMOUT', text='')
            col.separator()
            col.operator('nvb.anim_move',
                         icon='TRIA_UP', text='').direction = 'UP'
            col.operator('nvb.anim_move',
                         icon='TRIA_DOWN', text='').direction = 'DOWN'
            col.separator()
            col.operator('nvb.anim_focus',
                         icon='RENDER_ANIMATION', text='')
            col.menu('NVB_MT_animlist_specials',
                     icon='DOWNARROW_HLT', text="")
            anim_list = mdl_base.nvb.animList
            anim_list_idx = mdl_base.nvb.animListIdx
            if anim_list_idx >= 0 and len(anim_list) > 0:
                anim = anim_list[anim_list_idx]
                row = layout.row()
                row.prop(anim, 'name')
                row = layout.row()
                row.prop_search(anim, 'root', bpy.data, 'objects')
                row = layout.row()
                row.prop(anim, 'ttime')
                row = layout.row()
                split = row.split()
                col = split.column(align=True)
                col.prop(anim, 'frameStart')
                col.prop(anim, 'frameEnd')
                row = layout.row()
                row.prop_search(anim, 'rawascii',
                                bpy.data, 'texts',
                                text='Emitter Data')
                # col = split.column(align=True)
                # col.prop(anim, 'marker', text = '')
                # col.prop_search(anim, 'marker', bpy.context.scene,
                # 'timeline_markers', icon = 'MARKER')
                layout.separator()

                # Event Helper. Display and add/remove events.
                row = layout.row()
                sub = layout.box()
                row = sub.row()
                row.label(text='Animation Events')

                row = sub.row()
                row.template_list('NVB_UL_animevents', 'TheEventList',
                                  anim, 'eventList',
                                  anim, 'eventListIdx')
                col = row.column(align=True)
                col.operator('nvb.animevent_new', text='', icon='ZOOMIN')
                col.operator('nvb.animevent_delete', text='', icon='ZOOMOUT')
                col.separator()
                col.operator('nvb.animevent_move',
                             icon='TRIA_UP', text='').direction = 'UP'
                col.operator('nvb.animevent_move',
                             icon='TRIA_DOWN', text='').direction = 'DOWN'
                if anim.eventListIdx >= 0 and len(anim.eventList) > 0:
                    animEvent = anim.eventList[anim.eventListIdx]
                    row = sub.row()
                    row.prop(animEvent, 'name')
                    row.prop(animEvent, 'frame')

                layout.separator()


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
        """TODO: DOC."""
        mdl_base = nvb_utils.get_obj_aurora_root(context.object)
        return mdl_base is not None

    def draw(self, context):
        """TODO: DOC."""
        layout = self.layout
        mdl_base = nvb_utils.get_obj_aurora_root(context.object)
        add_on = context.user_preferences.addons[__package__]
        render = context.scene.render
        if mdl_base:
            # Armature Helper
            box = layout.box()
            box.label(text='Armature Helper')

            split = box.split(percentage=0.33)
            col = split.column()
            col.label(text='Source: ')
            col.label(text='Animations: ')
            col = split.column()
            col.row().prop(add_on.preferences, 'helper_amt_src', expand=True)
            col.prop(add_on.preferences, 'helper_amt_mode', text='')

            row = box.row()
            row.prop(add_on.preferences, 'helper_amt_connect')
            row.prop(add_on.preferences, 'helper_amt_strip')
            box.operator('nvb.amt_psb2amt', icon='BONE_DATA')
            layout.separator()

            # Scale Helper
            box = layout.box()
            box.label(text='Transform Helper')
            row = box.row()
            row.column().prop(mdl_base, 'location')
            row.column().prop(mdl_base, 'scale')
            box.operator('nvb.util_transform', icon='SORTSIZE')
            layout.separator()

            # Walkmesh & Dummy Helper
            box = layout.box()
            box.label(text='Walkmesh & Dummy Helper')
            row = box.row()
            row.label(text='Type: ')
            row.prop(add_on.preferences, 'helper_node_mdltype', expand=True)
            box.operator('nvb.util_nodes', text='Generate Objects',
                         icon='OOPS')
            layout.separator()

            # Minimap Helper
            box = layout.box()
            box.label(text='Minimap Helper')

            split = box.split(percentage=0.33)
            col = split.column()
            col.label(text='Size:')
            col.label(text='Display:')
            col = split.column()
            col.prop(render, 'resolution_y', text='')
            row = col.row(align=True)
            row.prop(render, 'display_mode', text='')
            row.prop(render, 'use_lock_interface', icon_only=True)

            row = box.row(align=True)
            row.operator('nvb.util_minimap', text='Setup Scene',
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
        if context.particle_system:
            return context.particle_system.settings
        elif isinstance(context.space_data.pin_id, bpy.types.ParticleSettings):
            return context.space_data.pin_id
        return None

    @classmethod
    def particle_panel_enabled(cls, context, psys):
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
        return False
        part = NVB_PT_emitter.particle_get_settings(context)
        if part:
            return not part.is_fluid
        return False

    def draw(self, context):
        layout = self.layout

        psys = context.particle_system
        part = NVB_PT_emitter.particle_get_settings(context)

        layout.enabled = \
            NVB_PT_emitter.particle_panel_enabled(context, psys) and \
            (psys is None or not psys.has_multiple_caches) and \
            part.type == 'EMITTER'

        row = layout.row()
        # row.active = part.emit_from == 'VERT' or part.distribution != 'GRID'
        # row.prop(part, "count")

        if part.type != 'HAIR':
            split = layout.split()

            col = split.column(align=True)
            col.prop(part, "frame_start")
            col.prop(part, "frame_end")

            col = split.column(align=True)
            col.prop(part, "lifetime")
            col.prop(part, "lifetime_random", slider=True)

        layout.label(text="Emit From:")
        layout.row().prop(part, "emit_from", expand=True)

        row = layout.row()
        if part.emit_from == 'VERT':
            row.prop(part, "use_emit_random")
        elif part.distribution == 'GRID':
            row.prop(part, "invert_grid")
            row.prop(part, "hexagonal_grid")
        else:
            row.prop(part, "use_emit_random")
            row.prop(part, "use_even_distribution")

        if part.emit_from == 'FACE' or part.emit_from == 'VOLUME':
            layout.row().prop(part, "distribution", expand=True)

            row = layout.row()
            if part.distribution == 'JIT':
                row.prop(part, "userjit", text="Particles/Face")
                row.prop(part, "jitter_factor", text="Jittering Amount",
                         slider=True)
            elif part.distribution == 'GRID':
                row.prop(part, "grid_resolution")
                row.prop(part, "grid_random", text="Random", slider=True)

        row = layout.row()
        row.prop(part, "use_modifier_stack")
