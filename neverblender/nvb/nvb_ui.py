"""TODO: DOC."""

import bpy

from . import nvb_def
from . import nvb_utils


class NVB_UILIST_LENSFLARES(bpy.types.UIList):
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


class NVB_UILIST_ANIMS(bpy.types.UIList):
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


class NVB_UILIST_ANIMEVENTS(bpy.types.UIList):
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


class NVB_PANEL_ROOTDUMMY(bpy.types.Panel):
    """Property panel for additional properties needed for the mdl file.

    This is only available for EMPTY objects without a parent.
    It is located under the object panel in the properties window,
    """

    bl_idname = 'nvb.propertypanel.rootdummy'
    bl_label = 'Aurora Root Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        """TODO: DOC."""
        obj = context.object
        if not obj:
            return False
        rd = nvb_utils.findObjRootDummy(obj)
        return rd is not None

    def draw(self, context):
        """TODO: DOC."""
        layout = self.layout
        obj = nvb_utils.findObjRootDummy(context.object)

        row = layout.row()
        box = row.box()
        split = box.split()
        col = split.column()
        col.label(text='Classification:')
        col.label(text='Supermodel:')
        col.label(text='Animation Scale:')
        col = split.column()
        col.prop(obj.nvb, 'classification', text='')
        col.prop(obj.nvb, 'supermodel', text='')
        col.prop(obj.nvb, 'animscale', text='')


class NVB_PANEL_DUMMY(bpy.types.Panel):
    """Property panel for additional properties needed for the mdl file.

    This is only available for EMPTY objects with a parent.
    It is located under the object panel in the properties window,
    """

    bl_idname = 'nvb.propertypanel.dummy'
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

        row = layout.row()
        box = row.box()
        box.prop(obj.nvb, 'emptytype', text='Type')
        row = box.row()
        row.prop(obj.nvb, 'wirecolor')
        layout.separator()

        # Display properties depending on type of the empty
        if (obj.nvb.emptytype == nvb_def.Emptytype.REFERENCE):
            row = layout.row()
            box = row.box()

            row = box.row()
            row.prop(obj.nvb, 'refmodel')
            row = box.row()
            row.prop(obj.nvb, 'reattachable')
        elif (obj.nvb.emptytype == nvb_def.Emptytype.DUMMY):
            row = layout.row()
            box = row.box()

            row = box.row(align=True)
            row.prop(obj.nvb, 'dummytype')
            row.operator('nvb.dummy_generatename',
                         icon='SORTALPHA', text='')


class NVB_PANEL_ARMATURE(bpy.types.Panel):
    """Property panel for armature properties.

    Tools for auto-generating armatures from a models skinmesh and copying
    animation from a models meshes.
    """

    bl_idname = 'nvb.propertypanel.armature'
    bl_label = 'Aurora Armature Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        """TODO: DOC."""
        return (context.object and context.object.type == 'ARMATURE')

    def draw(self, context):
        """TODO: DOC."""
        # obj = context.object
        layout = self.layout

        # Armature Helper
        row = layout.row()
        box = row.box()
        row = box.row()
        row.operator('nvb.armature_topseudo',
                     text='Generate Pseudo Bones',
                     icon='BONE_DATA')


class NVB_PANEL_LIGHT(bpy.types.Panel):
    """Property panel for additional light or lamp properties.

    This holds all properties not supported by blender,
    but used by the aurora engine. This is only available for LAMP objects.
    It is located under the object panel in the properties window.
    """

    bl_idname = 'nvb.propertypanel.light'
    bl_label = 'Aurora Light Properties'
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

        row = layout.row(align=True)
        row.prop(obj.nvb, 'lighttype', text='Type')
        row.operator('nvb.light_generatename',
                     icon='SORTALPHA', text='')
        layout.separator()

        row = layout.row()
        box = row.box()

        row = box.row()
        row.prop(obj.nvb, 'wirecolor', text='Wirecolor')
        row = box.row()
        row.prop(obj.nvb, 'lightpriority', text='Priority')

        split = box.split()
        col = split.column(align=True)
        col.prop(obj.nvb, 'ambientonly', text='Ambient Only')
        col.prop(obj.nvb, 'shadow', text='Shadows')
        col = split.column(align=True)
        col.prop(obj.nvb, 'fadinglight', text='Fading')
        col.prop(obj.nvb, 'isdynamic', text='Is dynamic')
        col.prop(obj.nvb, 'affectdynamic', text='Affect dynamic')

        layout.separator()

        # Lens flares
        row = layout.row()
        row.enabled = (obj.nvb.lighttype == nvb_def.Lighttype.DEFAULT)
        box = row.box()
        row = box.row()
        row.prop(obj.nvb, 'lensflares')
        sub = row.row(align=True)
        sub.active = obj.nvb.lensflares
        sub.prop(obj.nvb, 'flareradius', text='Radius')
        row = box.row()
        row.active = obj.nvb.lensflares
        row.template_list('NVB_UILIST_LENSFLARES', 'The_List',
                          obj.nvb, 'flareList',
                          obj.nvb, 'flareListIdx')
        col = row.column(align=True)
        col.operator('nvb.lightflare_new', icon='ZOOMIN', text='')
        col.operator('nvb.lightflare_delete', icon='ZOOMOUT', text='')
        col.separator()
        col.operator('nvb.lightflare_move',
                     icon='TRIA_UP', text='').direction = 'UP'
        col.operator('nvb.lightflare_move',
                     icon='TRIA_DOWN', text='').direction = 'DOWN'
        if obj.nvb.flareListIdx >= 0 and len(obj.nvb.flareList) > 0:
            item = obj.nvb.flareList[obj.nvb.flareListIdx]
            row = box.row()
            row.active = obj.nvb.lensflares
            row.prop(item, 'texture')
            row = box.row()
            row.active = obj.nvb.lensflares
            row.prop(item, 'colorshift')
            row = box.row()
            row.active = obj.nvb.lensflares
            row.prop(item, 'size')
            row.prop(item, 'position')


class NVB_PANEL_MESH(bpy.types.Panel):
    """Property panel for additional mesh properties.

    This holds all properties not supported by blender,
    but used by the aurora engine. This is only available for MESH objects.
    It is located under the object panel in the properties window.
    """

    bl_idname = 'nvb.propertypanel.mesh'
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

        row = layout.row()
        box = row.box()
        box.prop(obj.nvb, 'meshtype', text='Type')
        row = box.row()
        row.prop(obj.nvb, 'wirecolor')
        layout.separator()

        if (obj.nvb.meshtype == nvb_def.Meshtype.EMITTER):
            row = layout.row()
            box = row.box()

            row = box.row()
            row.prop_search(obj.nvb, 'rawascii',
                            bpy.data, 'texts',
                            text='Emitter Data')

        # Additional props for aabb walkmeshes
        elif obj.nvb.meshtype == nvb_def.Meshtype.AABB:
            row = layout.row()
            box = row.box()
            row = box.row()
            row.operator('nvb.load_wok_mats',
                         text='Setup Materials', icon='NONE')
            row = box.row()
            row.label(text='(Warning: Removes current materials)')

        else:  # Trimesh, danglymesh, skin
            row = layout.row()
            box = row.box()
            box.label(text='Trimesh Properties')

            row = box.row()
            row.prop(obj.nvb, 'selfillumcolor', text='Selfillum. color')
            row = box.row()
            row.prop(obj.nvb, 'ambientcolor', text='Ambient')

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

                row = layout.row()
                box = row.box()
                box.label(text='Danglymesh Properties')
                row = box.row()
                row.prop_search(obj.nvb, 'constraints',
                                obj, 'vertex_groups',
                                text='Constraints')
                row = box.row()
                row.prop(obj.nvb, 'period', text='Period')
                row = box.row()
                row.prop(obj.nvb, 'tightness', text='Tightness')
                row = box.row()
                row.prop(obj.nvb, 'displacement', text='Displacement')

            # Additional props for skins
            elif (obj.nvb.meshtype == nvb_def.Meshtype.SKIN):
                layout.separator()

                row = layout.row()
                box = row.box()
                box.label(text='Skinmesh Properties')
                row = box.row()
                row.label(text='Create vertex group: ')
                row = box.row(align=True)
                row.prop_search(obj.nvb, 'skingroup_obj',
                                context.scene, 'objects')
                row.operator('nvb.skingroup_add', text='', icon='ZOOMIN')

            # Additional props for Animmeshes
            elif (obj.nvb.meshtype == nvb_def.Meshtype.ANIMMESH):
                row = layout.row()
                box = row.box()
                row = box.row()
                row.label(text='Animmesh Properties')
                row = box.row()
                if obj.data and obj.data.shape_keys:
                    row.prop_search(obj.nvb, 'aurorashapekey',
                                    obj.data.shape_keys, 'key_blocks',
                                    text='Shapekey')
                else:
                    row.prop(obj.nvb, 'aurorashapekey', text='Shapekey')


class NVB_MENU_ANIMLIST_SPECIALS(bpy.types.Menu):
    """Animation List Specials."""

    bl_idname = 'nvb.menu.animspecials'
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


class NVB_PANEL_ANIMLIST(bpy.types.Panel):
    """Property panel for animationslist.

    Property panel for additional properties needed for the mdl file
    format. This is only available for EMPTY objects.
    It is located under the object data panel in the properties window
    """

    bl_idname = 'nvb.propertypanel.anim'
    bl_label = 'Aurora Animations'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        """TODO: DOC."""
        obj = context.object
        if not obj:
            return False
        rd = nvb_utils.findObjRootDummy(obj)
        return rd is not None

    def draw(self, context):
        """TODO: DOC."""
        layout = self.layout
        obj = nvb_utils.findObjRootDummy(context.object)
        if obj:
            # Anim Helper. Display and add/remove events.
            row = layout.row()
            row.template_list('NVB_UILIST_ANIMS', 'TheAnimList',
                              obj.nvb, 'animList', obj.nvb, 'animListIdx',
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
            col.menu('nvb.menu.animspecials',
                     icon='DOWNARROW_HLT', text="")
            if obj.nvb.animListIdx >= 0 and len(obj.nvb.animList) > 0:
                anim = obj.nvb.animList[obj.nvb.animListIdx]
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
                row.template_list('NVB_UILIST_ANIMEVENTS', 'TheEventList',
                                  anim, 'eventList', anim, 'eventListIdx')
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


class NVB_PANEL_UTILS(bpy.types.Panel):
    """Property panel for minimap render.

    Property panel with utilities to render minimaps
    """

    bl_idname = 'nvb.propertypanel.utils'
    bl_label = 'Aurora Utilities'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context):
        """TODO: DOC."""
        if not context.object:
            return False
        rd = nvb_utils.findObjRootDummy(context.object)
        return rd is not None

    def draw(self, context):
        """TODO: DOC."""
        layout = self.layout
        obj = nvb_utils.findObjRootDummy(context.object)
        if obj:
            # Minimap Helper
            row = layout.row()
            box = row.box()
            box.label(text='Minimap Helper')
            box.prop(obj.nvb, 'minimapzoffset', text='z Offset')
            box.prop(obj.nvb, 'minimapsize', text='Minimap Size')
            box.operator('nvb.helper_minimap_setup',
                         text='Render Minimap',
                         icon='RENDER_STILL')
            layout.separator()
            # Armature Helper
            row = layout.row()
            box = row.box()
            box.label(text='Armature Helper')
            row = box.row()
            row.label(text='Source: ')
            row.prop(obj.nvb, 'helper_amt_source', expand=True)
            row = box.row()
            row.prop(obj.nvb, 'helper_amt_connect', text='Connect')
            row = box.row()
            row.prop(obj.nvb, 'helper_amt_copyani', text='Copy Animations')
            box.operator('nvb.helper_amt_frompseudo',
                         text='Generate Armature',
                         icon='BONE_DATA')
            layout.separator()
            # Walkmesh & Dummy Helper
            row = layout.row()
            box = row.box()
            box.label(text='Walkmesh Helper')
            row = box.row()
            row.label(text='Type: ')
            row.prop(obj.nvb, 'helper_wkm_type', expand=True)
            box.operator('nvb.helper_wkm_setup',
                         text='Generate Walkmesh',
                         icon='OOPS')
            layout.separator()
