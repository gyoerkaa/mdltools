import bpy
import bpy_extras

from . import nvb_def
from . import nvb_io


class NVB_LIST_OT_LightFlare_New(bpy.types.Operator):
    ''' Add a new item to the flare list '''

    bl_idname = 'nvb.lightflare_new'
    bl_label  = 'Add a new flare to a light'

    def execute(self, context):
        if (context.object.type == 'LAMP'):
            context.object.nvb.flareList.add()

        return{'FINISHED'}


class NVB_LIST_OT_LightFlare_Delete(bpy.types.Operator):
    ''' Delete the selected item from the flare list '''

    bl_idname = 'nvb.lightflare_delete'
    bl_label = 'Deletes a flare from the light'

    @classmethod
    def poll(self, context):
        ''' Enable only if the list isn't empty '''
        return len(context.object.nvb.flareList) > 0

    def execute(self, context):
        flareList = context.object.nvb.flareList
        flareIdx  = context.object.nvb.flareListIdx

        flareList.remove(flareIdx)
        if flareIdx > 0:
            flareIdx =flareIdx - 1

        return{'FINISHED'}


class NVB_LIST_OT_LightFlare_Move(bpy.types.Operator):
    ''' Move an item in the flare list '''

    bl_idname = 'nvb.lightflare_move'
    bl_label  = 'Move an item in the flare list'

    direction = bpy.props.EnumProperty(items=(('UP', 'Up', ''), ('DOWN', 'Down', '')))

    @classmethod
    def poll(self, context):
        return len(context.object.nvb.flareList) > 0


    def move_index(self, context):
        flareList = context.object.nvb.flareList
        flareIdx  = context.object.nvb.flareListIdx

        listLength = len(flareList) - 1 # (index starts at 0)
        newIdx = 0
        if self.direction == 'UP':
            newIdx = flareIdx - 1
        elif self.direction == 'DOWN':
            newIdx = flareIdx + 1

        newIdx   = max(0, min(newIdx, listLength))
        context.object.nvb.flareListIdx = newIdx


    def execute(self, context):
        flareList = context.object.nvb.flareList
        flareIdx  = context.object.nvb.flareListIdx

        if self.direction == 'DOWN':
            neighbour = flareIdx + 1
            flareList.move(flareIdx, neighbour)
            self.move_index(context)
        elif self.direction == 'UP':
            neighbour = flareIdx - 1
            flareList.move(neighbour, flareIdx)
            self.move_index(context)
        else:
            return{'CANCELLED'}

        return{'FINISHED'}


class NVB_LIST_OT_AnimEvent_New(bpy.types.Operator):
    ''' Add a new item to the event list '''

    bl_idname = 'nvb.animevent_new'
    bl_label  = 'Add a new event to an animation'

    def execute(self, context):
        context.object.nvb.eventList.add()

        return{'FINISHED'}


class NVB_LIST_OT_AnimEvent_Delete(bpy.types.Operator):
    ''' Delete the selected item from the event list '''

    bl_idname = 'nvb.animevent_delete'
    bl_label = 'Deletes an event from an animation'

    @classmethod
    def poll(self, context):
        ''' Enable only if the list isn't empty '''
        return len(context.object.nvb.eventList) > 0

    def execute(self, context):
        eventList = context.object.nvb.eventList
        eventIdx  = context.object.nvb.eventListIdx

        eventList.remove(eventIdx)
        if eventIdx > 0:
            eventIdx = eventIdx - 1

        return{'FINISHED'}


class NVB_LIST_OT_AnimEvent_Move(bpy.types.Operator):
    ''' Move an item in the event list '''

    bl_idname = 'nvb.animevent_move'
    bl_label  = 'Move an item in the event  list'

    direction = bpy.props.EnumProperty(items=(('UP', 'Up', ''), ('DOWN', 'Down', '')))

    @classmethod
    def poll(self, context):
        return len(context.object.nvb.eventList) > 0


    def move_index(self, context):
        eventList = context.object.nvb.eventList
        eventIdx  = context.object.nvb.eventListIdx

        listLength = len(eventList) - 1 # (index starts at 0)
        newIdx = 0
        if self.direction == 'UP':
            newIdx = eventIdx - 1
        elif self.direction == 'DOWN':
            newIdx = eventIdx + 1

        newIdx   = max(0, min(newIdx, listLength))
        context.object.nvb.eventListIdx = newIdx


    def execute(self, context):
        eventList = context.object.nvb.eventList
        eventIdx  = context.object.nvb.eventListIdx

        if self.direction == 'DOWN':
            neighbour = eventIdx + 1
            eventList.move(eventIdx, neighbour)
            self.move_index(context)
        elif self.direction == 'UP':
            neighbour = eventIdx - 1
            eventList.move(neighbour, eventIdx)
            self.move_index(context)
        else:
            return{'CANCELLED'}

        return{'FINISHED'}


class MdlImport(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    '''Import Aurora Engine model (.mdl)'''

    bl_idname  = 'nvb.mdlimport'
    bl_label   = 'Import Aurora MDL'
    bl_options = {'UNDO'}

    filename_ext = '.mdl'
    filter_glob = bpy.props.StringProperty(
            default = '*.mdl',
            options = {'HIDDEN'},
            )

    imports = bpy.props.EnumProperty(
            name = 'Import',
            options = {'ENUM_FLAG'},
            items = (('GEOMETRY', 'Geometry', 'Import dummys and meshes'),
                     ('ANIMATION', 'Animations', 'Import animations'),
                     ('WALKMESH', 'Walkmesh', 'Import walkmeshes'),
                     ),
            default = {'GEOMETRY', 'ANIMATION', 'WALKMESH'},
            )

    useShadingGroups = bpy.props.BoolProperty(
            name = 'Import shading groups',
            description = 'Import shading groups as vertex groups ' \
                          '(Unused by blender)',
            default = True,
            )

    textureSingle = bpy.props.BoolProperty(
            name = 'One texture per image',
            description = 'Create only one texture for each image',
            default = True,
            )

    textureSearch = bpy.props.BoolProperty(
            name='Image search',
            description='Search for images in subdirectories' \
                        '(Warning, may be slow)',
            default=False,
            )

    # Hidden option, only used for batch minimap creation
    minimapMode = bpy.props.BoolProperty(
            name = 'Minimap Mode',
            description = 'Ignore lights and fading objects',
            default = False,
            options = {'HIDDEN'},
            )

    def execute(self, context):
        keywords = self.as_keywords(ignore=('filter_glob',
                                            'check_existing',
                                            ))
        return nvb_io.loadMdl(self, context, **keywords)


class MdlExport(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    '''Export Aurora Engine model (.mdl)'''

    bl_idname = 'nvb.mdlexport'
    bl_label  = 'Export Aurora MDL'

    filename_ext = '.mdl'
    filter_glob = bpy.props.StringProperty(
            default = '*.mdl',
            options = {'HIDDEN'},
            )

    exports = bpy.props.EnumProperty(
            name = 'Export',
            options = {'ENUM_FLAG'},
            items = (('ANIMATION', 'Animations', 'Export animations'),
                     ('WALKMESH', 'Walkmesh', 'Create walkmesh file (.pwk, .dwk or .wok depending on classification)'),
                     ),
            default = {'ANIMATION', 'WALKMESH'},
            )

    shadingGroups = bpy.props.BoolProperty(
            name='Export Shading groups',
            description='Export Shading Groups' \
                        '(When disabled, every face belongs to the same group)',
            default=True,
            )

    applyModifiers = bpy.props.BoolProperty(
            name='Apply Modifiers',
            description='Apply Modifiers before exporting.',
            default=True,
            )

    def execute(self, context):
        keywords = self.as_keywords(ignore=('filter_glob',
                                            'check_existing',
                                            ))
        return nvb_io.saveMdl(self, context, **keywords)


class LoadWokMaterials(bpy.types.Operator):
    '''
    Load all materials for aabb walkmeshes for the selected object. Current
    material slots will be deleted.
    '''
    bl_idname = "nvb.load_wok_mats"
    bl_label  = "Load walkmesh materials"

    def execute(self, context):
        '''
        - Deletes all current materials
        - adds walkmesh materials
        '''
        selected_object = context.object
        if (selected_object) and (selected_object.type == 'MESH'):
            object_mesh = selected_object.data

            # Remove all current material slots
            for i in range(len(selected_object.material_slots)):
                bpy.ops.object.material_slot_remove()

            # Create materials
            for i in range(len(neverblender.nvb.presets.wok_materials)):
                mat_name = neverblender.nvb.presets.wok_materials[i][0] +'.mat'

                # Walkmesh materials should be shared across multiple
                # walkmeshes, as they always identical
                if mat_name in bpy.data.materials.keys():
                    walkmesh_mat = bpy.data.materials[mat_name]
                else:
                    walkmesh_mat = bpy.data.materials.new(mat_name)

                    walkmesh_mat.diffuse_color      = neverblender.nvb.presets.wok_materials[i][1]
                    walkmesh_mat.diffuse_intensity  = 1.0
                    walkmesh_mat.specular_color     = (0.0,0.0,0.0)
                    walkmesh_mat.specular_intensity = neverblender.nvb.presets.wok_materials[i][2]

                object_mesh.materials.append(walkmesh_mat)
        else:
            self.report({'INFO'}, 'A mesh must be selected')
            return {'CANCELLED'}

        return {'FINISHED'}


class NVBOBJECT_OT_RenderMinimap(bpy.types.Operator):
    bl_idname = "nvb.render_minimap"
    bl_label  = "Render Minimap"

    def execute(self, context):
        '''
        - Creates an camera and a lamp
        - Renders Minimap
        '''
        selected_object = context.object
        if (selected_object) and (selected_object.type == 'EMPTY'):
            if (selected_object.auroraprops.dummytype == 'MDLBASE'):
                nvb_utils.nvb_minimap_render_setup(selected_object, bpy.context.scene)
                bpy.ops.render.render()
            else:
                self.report({'INFO'}, 'A MDLBASE must be selected')
                return {'CANCELLED'}
        else:
            self.report({'INFO'}, 'An Empty must be selected')
            return {'CANCELLED'}

        return {'FINISHED'}


class NVBOBJECT_OT_AnimsceneRename(bpy.types.Operator):
    bl_idname = "nvb.animscene_rename"
    bl_label  = "Rename animation scene"

    def execute(self, context):
        obj   = context.object
        scene = context.scene

        current_name = obj.auroraprops.animname
        new_name     = obj.auroraprops.newanimname
        print(obj.name)

        return{'FINISHED'}


class NVBOBJECT_OT_SkingroupAdd(bpy.types.Operator):
    bl_idname = "nvb.skingroup_add"
    bl_label  = "Add new Skingroup"

    def execute(self, context):
        obj      = context.object
        skingr_name = obj.auroraprops.select_object
        # Check if there is already a vertex group with this name
        if (skingr_name != '') and (skingr_name not in obj.vertex_groups.keys()):
            # Create the vertex group
            vert_group = obj.vertex_groups.new(skingr_name)

        return{'FINISHED'}


class NVBOBJECT_OT_AnimsceneAdd(bpy.types.Operator):
    bl_idname = "nvb.animscene_add"
    bl_label  = "Add animation scene"

    def execute(self, context):
        obj          = context.object
        anim_name    = obj.auroraprops.newanimname
        source_scene = context.scene
        # Check if there is already a scene with this animation name
        scene_list = bpy.data.scenes
        if (anim_name != '') and (anim_name not in scene_list.keys()):
            # Create the scene
            anim_scene = bpy.data.scenes.new(anim_name)

            # Set fps
            anim_scene.render.fps = 30

            # Now we create copies the objects in this scene
            anim_objects_parent = {}
            anim_objects        = {}
            for source_object in source_scene.objects:
                object_copy        = source_object.copy()
                object_copy.parent = None
                object_copy.name   = source_object.name + '.' + anim_name
                if source_object.parent:
                    object_copy_parent_name = source_object.parent.name + '.' + anim_name
                else:
                    object_copy_parent_name = 'null'

                # We have just copied a MDL Base, so set some additional data
                if (source_object.type == 'EMPTY') and (source_object.auroraprops.dummytype == 'MDLBASE'):
                    object_copy.auroraprops.in_animscene = True
                    object_copy.auroraprops.animname     = anim_name
                    object_copy.auroraprops.transtime    = 0.25

                anim_scene.objects.link(object_copy)
                # Save the copies for parenting
                anim_objects_parent[source_object.name] = object_copy_parent_name
                anim_objects[source_object.name]        = object_copy

            # Set the parents
            for source_object_name, object_copy in anim_objects.items():
                parent_name = anim_objects_parent[source_object_name]

                if (parent_name.lower() != 'null'):
                    if parent_name in anim_scene.objects:
                        object_copy.parent = anim_scene.objects[parent_name]
                    else:
                        print('WARNING: Object ' + object_copy.name + ' has no parent ' +  parent_name)

            anim_scene.update()

        return{'FINISHED'}
