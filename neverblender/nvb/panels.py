import bpy

class NVBAuroraPropertyPanelEmpty(bpy.types.Panel):
    '''
    Property panel for additional properties needed for the mdl file
    format. This is only available for EMPTY objects.
    It is located under the object data panel in the properties window
    '''
    bl_idname = 'nvb.propertypanel.dummy'
    bl_label = 'Aurora Dummy Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'EMPTY')

    def draw(self, context):
        obj    = context.object
        layout = self.layout

        row = layout.row()
        row.prop(obj.auroraprops, 'dummytype', text='Type')#, expand=True)

        if (obj.auroraprops.dummytype == 'MDLROOT'):
            row = layout.row()
            row.prop(obj.auroraprops, 'classification', text='Classification')

            row = layout.row()
            row.prop(obj.auroraprops, 'supermodel', text='Supermodel')

            row = layout.row()
            row.prop(obj.auroraprops, 'animationscale', text = 'Animationscale')

            row = layout.row()
            box = row.box()
            box.label(text = 'Create animation: ')
            row = box.row(align = True)
            row.prop(obj.auroraprops, 'newanim_name', text='')
            row.operator('nvb.animscene_add', text = '', icon='ZOOMIN')

            row = layout.row()
            box = row.box()
            box.label(text = 'Minimap: ')
            row = box.row()
            row.prop(obj.auroraprops, 'minimapzoffset', text = 'z Offset')
            row = box.row()
            row.prop(obj.auroraprops, 'minimapsize', text = 'Minimap size')
            row = box.row()
            row.operator('nvb.render_minimap', text = 'Setup Render', icon='NONE')

        elif (obj.auroraprops.dummytype == 'PWKROOT'):
            pass
        elif (obj.auroraprops.dummytype == 'DWKROOT'):
            pass
        elif (obj.auroraprops.dummytype == 'ANIROOT'):
            # This MDLBASE is in an animation scene
            row = layout.row()
            row.prop(object.auroraprops, 'transtime', text = 'Transition Time')

            row = layout.row()
            box = row.box()
            box.label(text = 'Rename animation: ')
            row = box.row(align = True)
            row.prop(obj.auroraprops, 'newanimname', text = '')
            row.operator('nvb.animscene_rename', text = '', icon='FILE_REFRESH')
        elif (obj.auroraprops.dummytype == 'SPECIAL'):
            row = layout.row()
            row.prop(obj.auroraprops, 'dummysubtype', text='Subtype')
        else:
            row = layout.row()
            row.prop(obj.auroraprops, 'wirecolor', text = 'Wirecolor')


class NVBAuroraPropertyPanelLight(bpy.types.Panel):
    '''
    Property panel for additional light or lamp properties. This
    holds all properties not supported by blender at the moment,
    but used by OpenGL and the aurora engine. This is only available
    for LAMP objects.
    It is located under the object data panel in the properties window
    '''
    bl_idname = 'nvb.propertypanel.light'
    bl_label = 'Aurora Light Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        return context.lamp

    def draw(self, context):
        obj    = context.object
        layout = self.layout

        row = layout.row()
        row.prop(obj.auroraprops, 'wirecolor', text='Wirecolor')

        split = layout.split()

        col = split.column()
        col.prop(obj.data, 'use_negative', text='Negative Light')
        col.prop(obj.data, 'use_diffuse', text='Use Diffuse')
        col.prop(obj.auroraprops, 'shadow', text='Shadows')

        col = split.column()
        col.prop(obj.auroraprops, 'fadinglight', text='Fading')
        col.prop(obj.auroraprops, 'isdynamic', text='Is dynamic')
        col.prop(obj.auroraprops, 'affectdynamic', text='Affect dynamic')

        row = layout.row()
        row.prop(obj.auroraprops, 'lightpriority', text='Priority')

        row = layout.row()
        row.prop(obj.auroraprops, 'tilelight', text='Tilelight')


class NVBAuroraPropertyPanelMesh(bpy.types.Panel):
    '''
    Property panel for additional mesh properties. This
    holds all properties not supported by blender at the moment,
    but used by OpenGL and the aurora engine. This is only available
    for MESH objects.
    It is located under the object data panel in the properties window
    '''
    bl_idname = 'nvb.propertypanel.mesh'
    bl_label = 'Aurora Mesh Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        return (context.mesh and context.object.type != 'EMPTY')

    def draw(self, context):
        obj      = context.object
        obj_type = obj.type
        layout   = self.layout

        row = layout.row()
        row.prop(obj.auroraprops, 'meshtype', text='Type')

        if (obj.auroraprops.meshtype == 'EMITTER'):
            #row = layout.row()
            #row.prop(obj.auroraprops, 'wirecolor', text='Wirecolor')

            row = layout.row()
            row.prop_search(obj.auroraprops, 'rawascii', bpy.data, 'texts')

        else: # Trimesh, danglymesh, skin
            row = layout.row()
            row.prop(obj.auroraprops, 'wirecolor', text='Wirecolor')

            row = layout.row()
            row.prop(obj.auroraprops, 'selfillumcolor', text='Selfillum. color')

            row = layout.row()
            row.prop(obj.auroraprops, 'ambientcolor', text='Ambient')

            row = layout.row()
            row.prop(obj.auroraprops, 'shininess', text='Shininess')

            split = layout.split()

            col = split.column()
            col.prop(obj.auroraprops, 'tilefade', text='Tilefade')
            col.prop(obj.auroraprops, 'render', text='Render')
            col.prop(obj.auroraprops, 'shadow', text='Shadow')

            col = split.column()
            col.prop(obj.auroraprops, 'beaming', text='Beaming')
            col.prop(obj.auroraprops, 'inheritcolor', text='Inherit Color')
            col.prop(obj.auroraprops, 'rotatetexture', text='Rotate Texture')

            row = layout.row()
            row.prop(obj.auroraprops, 'transparencyhint', text='Transparency Hint')

            # Additional props for danlymeshes
            if (obj.auroraprops.meshtype == 'DANGLYMESH'):
                '''
                row = layout.row()
                row.label(text='Danglymesh Properties')
                row = layout.row()
                row.prop_search(object.auroraprops, 'danglegroup', context.object, 'vertex_groups')
                row = layout.row()
                row.prop(object.auroraprops, 'period', text='Period')
                row = layout.row()
                row.prop(object.auroraprops, 'tightness', text='Tightness')
                row = layout.row()
                row.prop(object.auroraprops, 'displacement', text='Displacement')
                '''
                row = layout.row()
                box = row.box()
                box.label(text = 'Danglymesh Properties')
                row = box.row()
                row.prop_search(obj.auroraprops, 'constraints', obj, 'vertex_groups', text='Constraints')
                row = box.row()
                row.prop(obj.auroraprops, 'period', text='Period')
                row = box.row()
                row.prop(obj.auroraprops, 'tightness', text='Tightness')
                row = box.row()
                row.prop(obj.auroraprops, 'displacement', text='Displacement')

            # Additional props for skins
            elif (obj.auroraprops.meshtype == 'SKIN'):
                '''
                row = layout.row()
                row.label(text='Skinmesh Properties')
                row = layout.row()
                row.label(text='Vertex Group is a skin group, if there is a bone with a matching name.')
                '''
                row = layout.row()
                box = row.box()
                box.label(text = 'Create skingroup: ')
                row = box.row(align = True)
                row.prop_search(obj.auroraprops, 'select_object', context.scene, 'objects')
                row.operator('nvb.skingroup_add', text = '', icon='ZOOMIN')

            # Additional props for aabb walkmeshes
            elif (obj.auroraprops.meshtype == 'AABB'):
                row = layout.row()
                box = row.box()
                row = box.row()
                row.operator('nvb.load_wok_mats', text = 'Load walkmesh materials', icon='NONE')
                row = box.row()
                row.label(text = '(Warning: Removes current materials)')
