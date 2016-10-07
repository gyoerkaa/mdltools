"""TODO: DOC."""

import bpy
import bpy_extras

from . import nvb_def
from . import nvb_utils
from . import nvb_io


class NVB_OP_Anim_Clone(bpy.types.Operator):
    """Clone an animation and append it to the animation list."""

    bl_idname = 'nvb.anim_clone'
    bl_label = 'Clone an animation and append it to the animation list.'

    @classmethod
    def poll(cls, context):
        """TODO:DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 0)
        return False

    def execute(self, context):
        """TODO:DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        anim = rootDummy.nvb.animList[rootDummy.nvb.animListIdx]
        # Adds a new animation to the end of the list
        clone = nvb_utils.createAnimListItem(rootDummy)
        # Copy keyframes
        actionList = []
        nvb_utils.getActionList(rootDummy, actionList)
        cloneStart = clone.frameStart
        kfOptions = {'FAST'}  # insertion options
        for action in actionList:
            for fcurve in action.fcurves:
                # Get the keyframe points of the selected animation
                kfp = [p for p in fcurve.keyframe_points
                       if anim.frameStart <= p.co[0] <= anim.frameEnd]
                for p in kfp:
                    frame = p.co[0] + cloneStart - anim.frameStart
                    fcurve.keyframe_points.insert(frame, p.co[1], kfOptions)
        # Copy data
        clone.frameEnd = cloneStart + (anim.frameEnd-anim.frameStart)
        clone.ttime = anim.ttime
        clone.root = anim.root
        clone.name = anim.name + '.copy'
        # Copy events
        for event in anim.eventList:
            clonedEvent = clone.eventList.add()
            clonedEvent.frame = event.frame + cloneStart - anim.frameStart
            clonedEvent.name = event.name

        return {'FINISHED'}


class NVB_OP_Anim_Resize(bpy.types.Operator):
    """Open a dialog to resize (pad) or scale a single animation."""

    bl_idname = 'nvb.anim_resize'
    bl_label = 'Resize or scale a single animation without affecting others.'

    currentStart = bpy.props.IntProperty('animStart', min=0)
    currentEnd = bpy.props.IntProperty('animEnd', min=0)

    padFront = bpy.props.IntProperty('padFront', min=0)
    padBack = bpy.props.IntProperty('padBack', min=0)

    scale = bpy.props.FloatProperts('scale', min=0.0)

    @classmethod
    def poll(cls, context):
        """TODO:DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 0)
        return False

    def execute(self, context):
        """TODO:DOC."""
        return {'FINISHED'}

    def draw(self, context):
        """TODO:DOC."""
        pass

    def invoke(self, context, event):
        """TODO:DOC."""
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class NVB_OP_Anim_Show(bpy.types.Operator):
    """Set the Start and end frames of the timeline."""

    bl_idname = 'nvb.anim_show'
    bl_label = 'Set start and end frame of the timeline to the animation'

    @classmethod
    def poll(self, context):
        """Prevent execution if animation list is empty."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 0)
        return False

    def execute(self, context):
        """TODO: DOC."""
        obj = nvb_utils.findObjRootDummy(context.object)
        animList = obj.nvb.animList
        animIdx = obj.nvb.animListIdx

        anim = animList[animIdx]
        scene = context.scene
        if (scene.frame_start == anim.frameStart) and \
           (scene.frame_end == anim.frameEnd):
            # Set timeline to all current animation
            scene.frame_start = 1
            lastFrame = 1
            for anim in animList:
                if lastFrame < anim.frameEnd:
                    lastFrame = anim.frameEnd
            scene.frame_end = lastFrame
        else:
            # Set timeline to the current animation
            scene.frame_start = anim.frameStart
            scene.frame_end = anim.frameEnd

        scene.frame_current = scene.frame_start

        return {'FINISHED'}


class NVB_OP_Anim_New(bpy.types.Operator):
    """Add a new animation to the animation list."""

    bl_idname = 'nvb.anim_new'
    bl_label = 'Create new animation'

    @classmethod
    def poll(self, context):
        """Prevent execution if no object is selected."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        return (rootDummy is not None)

    def execute(self, context):
        """TODO: DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        nvb_utils.createAnimListItem(rootDummy)

        return {'FINISHED'}


class NVB_OP_Anim_Delete(bpy.types.Operator):
    """Delete the selected animation from the animation list."""

    bl_idname = 'nvb.anim_delete'
    bl_label = 'Delete an animation'

    @classmethod
    def poll(self, context):
        """Prevent execution if animation list is empty."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 0)
        return False

    def execute(self, context):
        """TODO: DOC."""
        obj = nvb_utils.findObjRootDummy(context.object)
        animList = obj.nvb.animList
        animIdx = obj.nvb.animListIdx

        animList.remove(animIdx)
        if animIdx > 0:
            animIdx = animIdx - 1

        return {'FINISHED'}


class NVB_OP_Anim_Move(bpy.types.Operator):
    """Move an item in the animation list."""

    bl_idname = 'nvb.anim_move'
    bl_label = 'Move an animation in the list'

    direction = bpy.props.EnumProperty(items=(
                                       ('UP', 'Up', ''),
                                       ('DOWN', 'Down', ''),
                                       ('END', 'End', '')))

    @classmethod
    def poll(self, context):
        """Prevent execution if animation list is empty."""
        obj = nvb_utils.findObjRootDummy(context.object)
        return len(obj.nvb.animList) > 0

    def execute(self, context):
        """TODO: DOC."""
        obj = nvb_utils.findObjRootDummy(context.object)
        animList = obj.nvb.animList

        currentIdx = obj.nvb.animListIdx
        newIdx = 0
        maxIdx = len(animList) - 1
        if self.direction == 'DOWN':
            newIdx = currentIdx + 1
        elif self.direction == 'UP':
            newIdx = currentIdx - 1
        elif self.direction == 'END':
            newIdx = maxIdx
        else:
            return {'CANCELLED'}

        newIdx = max(0, min(newIdx, maxIdx))
        animList.move(currentIdx, newIdx)
        obj.nvb.animListIdx = newIdx
        # TODO: Move whole animation, i.e. keyframes
        return {'FINISHED'}


class NVB_OP_LightFlare_New(bpy.types.Operator):
    """Add a new item to the flare list."""

    bl_idname = 'nvb.lightflare_new'
    bl_label = 'Add a new flare to a light'

    def execute(self, context):
        """TODO: DOC."""
        if (context.object.type == 'LAMP'):
            context.object.nvb.flareList.add()

        return {'FINISHED'}


class NVB_OP_LightFlare_Delete(bpy.types.Operator):
    """Delete the selected item from the flare list."""

    bl_idname = 'nvb.lightflare_delete'
    bl_label = 'Deletes a flare from the light'

    @classmethod
    def poll(self, context):
        """Enable only if the list isn't empty."""
        return len(context.object.nvb.flareList) > 0

    def execute(self, context):
        """TODO: DOC."""
        flareList = context.object.nvb.flareList
        flareIdx = context.object.nvb.flareListIdx

        flareList.remove(flareIdx)
        if flareIdx > 0:
            flareIdx = flareIdx - 1

        return {'FINISHED'}


class NVB_OP_LightFlare_Move(bpy.types.Operator):
    """Move an item in the flare list."""

    bl_idname = 'nvb.lightflare_move'
    bl_label = 'Move an item in the flare list'

    direction = bpy.props.EnumProperty(items=(('UP', 'Up', ''),
                                              ('DOWN', 'Down', '')))

    @classmethod
    def poll(self, context):
        """TODO: DOC."""
        return len(context.object.nvb.flareList) > 0

    def execute(self, context):
        """TODO: DOC."""
        obj = context.object
        flareList = obj.nvb.flareList

        currentIdx = obj.nvb.flareListIdx
        newIdx = 0
        maxIdx = len(flareList) - 1
        if self.direction == 'DOWN':
            newIdx = currentIdx + 1
        elif self.direction == 'UP':
            newIdx = currentIdx - 1
        else:
            return {'CANCELLED'}

        newIdx = max(0, min(newIdx, maxIdx))
        flareList.move(currentIdx, newIdx)
        obj.nvb.flareListIdx = newIdx
        return {'FINISHED'}


class NVB_OP_AnimEvent_New(bpy.types.Operator):
    """Add a new item to the event list."""

    bl_idname = 'nvb.animevent_new'
    bl_label = 'Add a new event to an animation'

    @classmethod
    def poll(self, context):
        """Enable only if there is an animation."""
        obj = context.object
        animList = obj.nvb.animList

        return len(animList) > 0

    def execute(self, context):
        """TODO: DOC."""
        obj = context.object
        anim = obj.nvb.animList[obj.nvb.animListIdx]

        eventList = anim.eventList
        newEvent = eventList.add()
        newEvent.frame = anim.frameStart

        return {'FINISHED'}


class NVB_OP_AnimEvent_Delete(bpy.types.Operator):
    """Delete the selected item from the event list."""

    bl_idname = 'nvb.animevent_delete'
    bl_label = 'Deletes an event from an animation'

    @classmethod
    def poll(self, context):
        """Enable only if the list isn't empty."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            animList = rootDummy.nvb.animList
            if len(animList) > 0:
                anim = animList[rootDummy.nvb.animListIdx]
                eventList = anim.eventList
                return len(eventList) > 0
        return False

    def execute(self, context):
        """TODO: DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        anim = rootDummy.nvb.animList[rootDummy.nvb.animListIdx]
        eventList = anim.eventList
        eventIdx = anim.eventListIdx

        eventList.remove(eventIdx)
        if eventIdx > 0:
            eventIdx = eventIdx - 1

        return{'FINISHED'}


class NVB_OP_AnimEvent_Move(bpy.types.Operator):
    """Move an item in the event list."""

    bl_idname = 'nvb.animevent_move'
    bl_label = 'Move an item in the event  list'

    direction = bpy.props.EnumProperty(items=(('UP', 'Up', ''),
                                              ('DOWN', 'Down', '')))

    @classmethod
    def poll(self, context):
        """Enable only if the list isn't empty."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            animList = rootDummy.nvb.animList
            if len(animList) > 0:
                anim = animList[rootDummy.nvb.animListIdx]
                eventList = anim.eventList
                return len(eventList) > 0
        return False

    def execute(self, context):
        """TODO: DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        anim = rootDummy.nvb.animList[rootDummy.nvb.animListIdx]
        eventList = anim.eventList

        currentIdx = anim.eventListIdx
        newIdx = 0
        maxIdx = len(eventList) - 1
        if self.direction == 'DOWN':
            newIdx = currentIdx + 1
        elif self.direction == 'UP':
            newIdx = currentIdx - 1
        else:
            return {'CANCELLED'}

        newIdx = max(0, min(newIdx, maxIdx))
        eventList.move(currentIdx, newIdx)
        anim.eventListIdx = newIdx
        return {'FINISHED'}


class NVB_OP_Import(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Import Aurora Engine model (.mdl)."""

    bl_idname = 'nvb.mdlimport'
    bl_label = 'Import Aurora MDL'
    bl_options = {'UNDO'}

    filename_ext = '.mdl'
    filter_glob = bpy.props.StringProperty(default='*.mdl',
                                           options={'HIDDEN'})

    importGeometry = bpy.props.BoolProperty(
            name='Import Geometry',
            description='Disable if only animations are needed',
            default=True)

    importWalkmesh = bpy.props.BoolProperty(
            name='Import Walkmesh',
            description='Attempt to load placeable and door walkmeshes',
            default=True)

    importSmoothGroups = bpy.props.BoolProperty(
            name='Import smooth groups',
            description='Import smooth groups as sharp edges',
            default=True)

    importAnim = bpy.props.EnumProperty(
            name='Animations',
            items=(('NON', 'None', 'Don\'t import animations', 0),
                   ('STD', 'Standard', 'Import animations', 1)),
            # ('ADV', 'Advanced', 'Single action for each animation
            # and object', 2)),
            default='STD')

    importSupermodel = bpy.props.BoolProperty(
            name='Import supermodel',
            description='Import animations from supermodel',
            default=False,
            options={'HIDDEN'})

    materialMode = bpy.props.EnumProperty(
            name='Materials',
            items=(('NON', 'None',
                    'Don\'t create materials or import textures', 0),
                   ('SIN', 'Single',
                    'Create only one material per texture, \
                     shared between objects', 1),
                   ('MUL', 'Multiple',
                    'Create a seperate material for each object', 2)),
            default='SIN')

    textureSearch = bpy.props.BoolProperty(
            name='Image search',
            description='Search for images in subdirectories'
                        '(Warning, may be slow)',
            default=False)

    # Hidden option, only used for batch minimap creation
    minimapMode = bpy.props.BoolProperty(
            name='Minimap Mode',
            description='Ignore lights and fading objects',
            default=False,
            options={'HIDDEN'})

    minimapSkipFade = bpy.props.BoolProperty(
            name='Minimap Mode: Import Fading Objects',
            description='Ignore fading objects',
            default=False,
            options={'HIDDEN'})

    def execute(self, context):
        """TODO: DOC."""
        keywords = self.as_keywords(ignore=('filter_glob',
                                            'check_existing',
                                            ))
        return nvb_io.loadMdl(self, context, **keywords)


class NVB_OP_Export(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    """Export Aurora Engine model (.mdl)."""

    bl_idname = 'nvb.mdlexport'
    bl_label = 'Export Aurora MDL'

    filename_ext = '.mdl'
    filter_glob = bpy.props.StringProperty(
            default='*.mdl',
            options={'HIDDEN'})

    exportAnimations = bpy.props.BoolProperty(
            name='Export animations',
            description='Export animations',
            default=True)

    exportWalkmesh = bpy.props.BoolProperty(
            name='Export a walkmesh',
            description='Export a walkmesh',
            default=True)

    exportSmoothGroups = bpy.props.BoolProperty(
            name='Export Smooth groups',
            description='Generate smooth groups from sharp edges'
                        '(When disabled every face belongs to the same group)',
            default=True)

    applyModifiers = bpy.props.BoolProperty(
            name='Apply Modifiers',
            description='Apply Modifiers before exporting',
            default=True)

    def execute(self, context):
        """TODO: DOC."""
        keywords = self.as_keywords(ignore=('filter_glob',
                                            'check_existing',
                                            ))
        return nvb_io.saveMdl(self, context, **keywords)


class LoadWokMaterials(bpy.types.Operator):
    """Load all materials for aabb walkmeshes for the selected object."""

    bl_idname = "nvb.load_wok_mats"
    bl_label = "Load walkmesh materials"

    def execute(self, context):
        """Delete all current materials and add walkmesh materials."""
        selected_object = context.object
        if (selected_object) and (selected_object.type == 'MESH'):
            object_mesh = selected_object.data

            # Remove all current material slots
            for i in range(len(selected_object.material_slots)):
                bpy.ops.object.material_slot_remove()

            # Create materials
            for matDef in nvb_def.wok_materials:
                matName = matDef[0]

                # Walkmesh materials should be shared across multiple
                # walkmeshes, as they always identical
                if matName in bpy.data.materials.keys():
                    mat = bpy.data.materials[matName]
                else:
                    mat = bpy.data.materials.new(matName)

                    mat.diffuse_color = matDef[1]
                    mat.diffuse_intensity = 1.0
                    mat.specular_color = (0.0, 0.0, 0.0)
                    mat.specular_intensity = matDef[2]

                object_mesh.materials.append(mat)
        else:
            self.report({'INFO'}, 'A mesh must be selected')
            return {'CANCELLED'}

        return {'FINISHED'}


class NVB_OBJECT_OT_RenderMinimap(bpy.types.Operator):
    """TODO: DOC."""

    bl_idname = "nvb.render_minimap"
    bl_label = "Render Minimap"

    def execute(self, context):
        """Create camera + lamp and Renders Minimap."""
        obj = context.object
        scene = bpy.context.scene
        if obj and (obj.type == 'EMPTY'):
            if (obj.nvb.dummytype == nvb_def.Dummytype.MDLROOT):
                nvb_utils.setupMinimapRender(obj, scene)
                bpy.ops.render.render(use_viewport=True)
                # bpy.ops.render.view_show()

                self.report({'INFO'}, 'Ready to render')
            else:
                self.report({'INFO'}, 'A MDLROOT must be selected')
                return {'CANCELLED'}
        else:
            self.report({'INFO'}, 'An Empty must be selected')
            return {'CANCELLED'}

        return {'FINISHED'}


class NVB_OBJECT_OT_SkingroupAdd(bpy.types.Operator):
    """TODO: DOC."""

    bl_idname = "nvb.skingroup_add"
    bl_label = "Add new Skingroup"

    def execute(self, context):
        """TODO: DOC."""
        obj = context.object
        skingrName = obj.nvb.skingroup_obj
        # Check if there is already a vertex group with this name
        if skingrName:
            if (skingrName not in obj.vertex_groups.keys()):
                # Create the vertex group
                # vertGroup = obj.vertex_groups.new(skingrName)
                obj.vertex_groups.new(skingrName)
                obj.nvb.skingroup_obj = ''

                self.report({'INFO'}, 'Created vertex group ' + skingrName)
                return{'FINISHED'}
            else:
                self.report({'INFO'}, 'Duplicate Name')
                return {'CANCELLED'}
        else:
            self.report({'INFO'}, 'Empty Name')
            return {'CANCELLED'}
