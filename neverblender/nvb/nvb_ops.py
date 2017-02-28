"""TODO: DOC."""

import math

import bpy
import bpy_extras

from . import nvb_def
from . import nvb_utils
from . import nvb_io


class NVB_OP_Anim_Clone(bpy.types.Operator):
    """Clone animation and add it to the animation list"""

    bl_idname = 'nvb.anim_clone'
    bl_label = 'Clone animation'

    @classmethod
    def poll(cls, context):
        """TODO:DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 0)
        return False

    def cloneEmitter(self, target, cloneStart):
        """TODO:DOC."""
        pass

    def cloneFrames(self, target, animStart, animEnd, cloneStart):
        """TODO:DOC."""
        if target.animation_data and target.animation_data.action:
            insertionOptions = {'FAST'}
            action = target.animation_data.action
            for fcurve in action.fcurves:
                # Get the keyframe points of the selected animation
                kfp = [p for p in fcurve.keyframe_points
                       if animStart <= p.co[0] <= animEnd]
                for p in kfp:
                    frame = cloneStart + (p.co[0] - animStart)
                    fcurve.keyframe_points.insert(frame, p.co[1],
                                                  insertionOptions)
                fcurve.update()

    def execute(self, context):
        """TODO:DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        anim = rootDummy.nvb.animList[rootDummy.nvb.animListIdx]
        # Adds a new animation to the end of the list
        clone = nvb_utils.createAnimListItem(rootDummy)
        # Grab some data for speed
        animStart = anim.frameStart
        animEnd = anim.frameEnd
        cloneStart = clone.frameStart
        # Get a list of affected objects
        objList = []
        nvb_utils.getAllChildren(rootDummy, objList)
        # Copy keyframes
        for obj in objList:
            # Copy the objects animation
            self.cloneFrames(obj, animStart, animEnd, cloneStart)
            # Copy the object's material animation
            if obj.active_material:
                self.cloneFrames(obj.active_material,
                                 animStart, animEnd, cloneStart)
            # Copy the object's shape key animation
            if obj.data and obj.data.shape_keys:
                self.cloneFrames(obj.data.shape_keys,
                                 animStart, animEnd, cloneStart)
            self.cloneEmitter(obj, cloneStart)
        # Copy data
        clone.frameEnd = cloneStart + (animEnd - animStart)
        clone.ttime = anim.ttime
        clone.root = anim.root
        clone.name = anim.name + '.copy'
        # Copy events
        for e in anim.eventList:
            clonedEvent = clone.eventList.add()
            clonedEvent.frame = cloneStart + (e.frame - animStart)
            clonedEvent.name = e.name

        return {'FINISHED'}


class NVB_OP_Anim_Scale(bpy.types.Operator):
    """Open a dialog to scale a single animation"""

    bl_idname = 'nvb.anim_scale'
    bl_label = 'Scale animation'

    scaleFactor = bpy.props.FloatProperty(name='scale',
                                          description='Scale the animation',
                                          min=0.1,
                                          default=1.0)

    @classmethod
    def poll(cls, context):
        """TODO:DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 0)
        return False

    def scaleFramesUp(self, target, animStart, animEnd, scaleFactor):
        """TODO:DOC."""
        if target.animation_data and target.animation_data.action:
            oldSize = animEnd - animStart + 1
            newSize = scaleFactor * oldSize
            padding = newSize - oldSize
            action = target.animation_data.action
            for fcurve in action.fcurves:
                # Move keyframes back to create enough space
                for p in reversed(fcurve.keyframe_points):
                    if (p.co[0] > animEnd):
                        p.co[0] += padding
                        p.handle_left.x += padding
                        p.handle_right.x += padding
                # Now scale the animation
                for p in fcurve.keyframe_points:
                    if (animStart < p.co[0] <= animEnd):
                        oldFrame = p.co[0]
                        newFrame = (oldFrame - animStart + 1) * \
                            scaleFactor + animStart - 1
                        p.co[0] = newFrame
                        p.handle_left.x = newFrame - \
                            (oldFrame - p.handle_left.x)
                        p.handle_right.x = newFrame + \
                            (p.handle_right.x - oldFrame)
                fcurve.update()

    def scaleFramesDown(self, target, animStart, animEnd, scaleFactor):
        """TODO:DOC."""
        if target.animation_data and target.animation_data.action:
            oldSize = animEnd - animStart + 1
            newSize = scaleFactor * oldSize
            padding = newSize - oldSize
            action = target.animation_data.action
            for fcurve in action.fcurves:
                    # Scale the animation down first
                    for p in fcurve.keyframe_points:
                        if (animStart < p.co[0] <= animEnd):
                            oldFrame = p.co[0]
                            newFrame = (oldFrame - animStart + 1) * \
                                scaleFactor + animStart - 1
                            p.co[0] = newFrame
                            p.handle_left.x = newFrame - \
                                (oldFrame - p.handle_left.x)
                            p.handle_right.x = newFrame + \
                                (p.handle_right.x - oldFrame)
                    # Move keyframes forward to close gaps
                    for p in fcurve.keyframe_points:
                        if (p.co[0] > animEnd):
                            p.co[0] += padding
                            p.handle_left.x += padding
                            p.handle_right.x += padding
                    fcurve.update()

    def scaleFrames(self, target, animStart, animEnd, scaleFactor):
        """TODO:DOC."""
        if target.animation_data and target.animation_data.action:
            if scaleFactor > 1.0:
                self.scaleFramesUp(target, animStart, animEnd, scaleFactor)
            elif scaleFactor < 1.0:
                self.scaleFramesDown(target, animStart, animEnd, scaleFactor)

    def execute(self, context):
        """TODO:DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if not nvb_utils.checkAnimBounds(rootDummy):
            self.report({'INFO'}, 'Failure: Convoluted animations.')
            return {'CANCELLED'}
        ta = rootDummy.nvb.animList[rootDummy.nvb.animListIdx]
        # Check resulting length (has to be >= 1)
        oldSize = ta.frameEnd - ta.frameStart + 1
        newSize = self.scaleFactor * oldSize
        if (newSize < 1):
            self.report({'INFO'}, 'Failure: Resulting size < 1.')
            return {'CANCELLED'}
        if (math.fabs(oldSize - newSize) < 1):
            self.report({'INFO'}, 'Failure: Same size.')
            return {'CANCELLED'}
        # Get a list of affected objects
        objList = []
        nvb_utils.getAllChildren(rootDummy, objList)
        # Adjust keyframes
        for obj in objList:
            # Adjust the objects animation
            self.scaleFrames(obj, ta.frameStart, ta.frameEnd, self.scaleFactor)
            # Adjust the object's material animation
            if obj.active_material:
                self.scaleFrames(obj.active_material,
                                 ta.frameStart, ta.frameEnd, self.scaleFactor)
            # Adjust the object's shape key animation
            if obj.data and obj.data.shape_keys:
                self.scaleFrames(obj.data.shape_keys,
                                 ta.frameStart, ta.frameEnd, self.scaleFactor)
        # Adjust the bounds of animations coming after the
        # target (scaled) animation
        padding = newSize - oldSize
        for a in reversed(rootDummy.nvb.animList):
            if a.frameStart > ta.frameEnd:
                a.frameStart += padding
                a.frameEnd += padding
                for e in a.eventList:
                    e.frame += padding
        # Adjust the target (scaled) animation itself
        ta.frameEnd += padding
        for e in ta.eventList:
            e.frame = (e.frame - ta.frameStart + 1) * \
                self.scaleFactor + ta.frameStart - 1
        # Re-adjust the timeline to the new bounds
        nvb_utils.toggleAnimFocus(context.scene, rootDummy)
        return {'FINISHED'}

    def draw(self, context):
        """TODO:DOC."""
        layout = self.layout

        row = layout.row()
        row.label('Scaling: ')
        row = layout.row()
        row.prop(self, 'scaleFactor', text='Factor')

        layout.separator()

    def invoke(self, context, event):
        """TODO:DOC."""
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class NVB_OP_Anim_Crop(bpy.types.Operator):
    """Open a dialog to crop a single animation"""

    bl_idname = 'nvb.anim_crop'
    bl_label = 'Crop animation'

    cropFront = bpy.props.IntProperty(
                    name='cropFront',
                    min=0,
                    description='Insert Frames before the first keyframe')
    cropBack = bpy.props.IntProperty(
                    name='cropBack',
                    min=0,
                    description='Insert Frames after the last keyframe')

    @classmethod
    def poll(cls, context):
        """TODO:DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 0)
        return False

    def cropFrames(self, target, animStart, animEnd):
        """TODO:DOC."""
        if target.animation_data and target.animation_data.action:
            # Grab some values for speed
            cf = self.cropFront
            cb = self.cropBack
            # Find out which frames to delete
            action = target.animation_data.action
            framesToDelete = []
            # Find out which ones to delete
            for fcurve in target.animation_data.action.fcurves:
                for p in fcurve.keyframe_points:
                    if (animStart <= p.co[0] < animStart + cf) or \
                       (animEnd - cb < p.co[0] <= animEnd):
                        framesToDelete.append((fcurve.data_path, p.co[0]))
            # Delete the frames by accessing them from the object.
            # (Can't do it directly)
            for dp, f in framesToDelete:
                target.keyframe_delete(dp, frame=f)
            # Move the keyframes to the front to remove gaps
            for fcurve in action.fcurves:
                for p in fcurve.keyframe_points:
                    if (p.co[0] >= animStart):
                        p.co[0] -= cf
                        p.handle_left.x -= cf
                        p.handle_right.x -= cf
                        if (p.co[0] >= animEnd):
                            p.co[0] -= cb
                            p.handle_left.x -= cb
                            p.handle_right.x -= cb
                fcurve.update()

    def execute(self, context):
        """TODO:DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if not nvb_utils.checkAnimBounds(rootDummy):
            self.report({'INFO'}, 'Failure: Convoluted animations.')
            return {'CANCELLED'}
        animList = rootDummy.nvb.animList
        currentAnimIdx = rootDummy.nvb.animListIdx
        anim = animList[currentAnimIdx]
        # Grab some values for speed
        cf = self.cropFront
        cb = self.cropBack
        animStart = anim.frameStart
        animEnd = anim.frameEnd
        totalCrop = cf + cb
        # Resulting length has to be at lest 1 frame
        if totalCrop > (animEnd - animStart + 1):
            self.report({'INFO'}, 'Failure: Resulting length < 1.')
            return {'CANCELLED'}
        # Get a list of affected objects
        objList = []
        nvb_utils.getAllChildren(rootDummy, objList)
        # Pad keyframes
        for obj in objList:
            # Copy the objects animation
            self.cropFrames(obj, animStart, animEnd)
            # Copy the object's material animation
            if obj.active_material:
                self.cropFrames(obj.active_material, animStart, animEnd)
            # Copy the object's shape key animation
            if obj.data and obj.data.shape_keys:
                self.cropFrames(obj.data.shape_keys, animStart, animEnd)
        # Update the animations in the list
        for a in rootDummy.nvb.animList:
            if a.frameStart > animStart:
                a.frameStart -= totalCrop
                a.frameEnd -= totalCrop
                for e in a.eventList:
                    e.frame -= totalCrop
        # Adjust the target animation itself
        for idx, e in enumerate(anim.eventList):
            if (animStart <= e.frame < animStart + cf) or \
               (animEnd - cb < e.frame <= animEnd):
                anim.eventList.remove(idx)
                anim.eventListIdx = 0
            else:
                e.frame -= totalCrop
        anim.frameEnd -= totalCrop
        # Re-adjust the timeline to the new bounds
        nvb_utils.toggleAnimFocus(context.scene, rootDummy)
        return {'FINISHED'}

    def draw(self, context):
        """TODO:DOC."""
        layout = self.layout

        row = layout.row()
        row.label('Crop: ')
        row = layout.row()
        split = row.split()
        col = split.column(align=True)
        col.prop(self, 'cropFront', text='Front')
        col.prop(self, 'cropBack', text='Back')

        layout.separator()

    def invoke(self, context, event):
        """TODO:DOC."""
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class NVB_OP_Anim_Pad(bpy.types.Operator):
    """Open a dialog to pad a single animation"""

    bl_idname = 'nvb.anim_pad'
    bl_label = 'Pad animation'

    padFront = bpy.props.IntProperty(
                    name='padFront',
                    min=0,
                    description='Insert Frames before the first keyframe')
    padBack = bpy.props.IntProperty(
                    name='padBack',
                    min=0,
                    description='Insert Frames after the last keyframe')

    @classmethod
    def poll(cls, context):
        """TODO:DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 0)
        return False

    def padFrames(self, target, animStart, animEnd):
        """TODO:DOC."""
        if target.animation_data and target.animation_data.action:
            action = target.animation_data.action
            for fcurve in action.fcurves:
                for p in reversed(fcurve.keyframe_points):
                    if p.co[0] > animEnd:
                        p.co[0] += self.padBack
                        p.handle_left.x += self.padBack
                        p.handle_right.x += self.padBack
                    if p.co[0] >= animStart:
                        p.co[0] += self.padFront
                        p.handle_left.x += self.padFront
                        p.handle_right.x += self.padFront
                fcurve.update()

    def execute(self, context):
        """TODO:DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if not nvb_utils.checkAnimBounds(rootDummy):
            self.report({'INFO'}, 'Failure: Convoluted animations.')
            return {'CANCELLED'}
        ta = rootDummy.nvb.animList[rootDummy.nvb.animListIdx]
        # Cancel if padding is 0
        if (self.padFront + self.padBack) <= 0:
            self.report({'INFO'}, 'Failure: No changes.')
            return {'CANCELLED'}
        # Get a list of affected objects
        objList = []
        nvb_utils.getAllChildren(rootDummy, objList)
        # Copy keyframes
        for obj in objList:
            # Copy the objects animation
            self.padFrames(obj, ta.frameStart, ta.frameEnd)
            # Copy the object's material animation
            if obj.active_material:
                self.padFrames(obj.active_material, ta.frameStart, ta.frameEnd)
            # Copy the object's shape key animation
            if obj.data and obj.data.shape_keys:
                self.padFrames(obj.data.shape_keys, ta.frameStart, ta.frameEnd)
        # Update the animations in the list
        totalPadding = self.padBack + self.padFront
        for a in rootDummy.nvb.animList:
            if a.frameStart > ta.frameEnd:
                a.frameStart += totalPadding
                a.frameEnd += totalPadding
                for e in a.eventList:
                    e.frame += totalPadding
        # Update the target animation itself
        ta.frameEnd += totalPadding
        for e in ta.eventList:
            e.frame += self.padFront
        # Re-adjust the timeline to the new bounds
        nvb_utils.toggleAnimFocus(context.scene, rootDummy)
        return {'FINISHED'}

    def draw(self, context):
        """TODO:DOC."""
        layout = self.layout

        row = layout.row()
        row.label('Padding: ')
        row = layout.row()
        split = row.split()
        col = split.column(align=True)
        col.prop(self, 'padFront', text='Front')
        col.prop(self, 'padBack', text='Back')

        layout.separator()

    def invoke(self, context, event):
        """TODO:DOC."""
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class NVB_OP_Anim_Focus(bpy.types.Operator):
    """Set the Start and end frames of the timeline"""

    bl_idname = 'nvb.anim_focus'
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
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        scene = context.scene

        nvb_utils.toggleAnimFocus(scene, rootDummy)
        return {'FINISHED'}


class NVB_OP_Anim_New(bpy.types.Operator):
    """Add a new animation to the animation list"""

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
    """Delete the selected animation from the animation list"""

    bl_idname = 'nvb.anim_delete'
    bl_label = 'Delete an animation'

    @classmethod
    def poll(self, context):
        """Prevent execution if animation list is empty."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 0)
        return False

    def deleteFrames(self, target, frameStart, frameEnd):
        """TODO: DOC."""
        if target.animation_data and target.animation_data.action:
            # Find out which frames to delete
            action = target.animation_data.action
            framesToDelete = []
            for fcurve in action.fcurves:
                for p in fcurve.keyframe_points:
                    if (frameStart <= p.co[0] <= frameEnd):
                        framesToDelete.append((fcurve.data_path, p.co[0]))
            # Delete them by accessing them from the object.
            # (Can't do it directly)
            for dp, f in framesToDelete:
                target.keyframe_delete(dp, frame=f)

    def execute(self, context):
        """TODO: DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        animList = rootDummy.nvb.animList
        animListIdx = rootDummy.nvb.animListIdx
        anim = animList[animListIdx]
        # Grab some data for speed
        frameStart = anim.frameStart
        frameEnd = anim.frameEnd
        # Get a list of affected objects
        objList = []
        nvb_utils.getAllChildren(rootDummy, objList)
        # Remove keyframes
        for obj in objList:
            # Delete the objects animation
            self.deleteFrames(obj, frameStart, frameEnd)
            # Delete the object's material animation
            if obj.active_material:
                self.deleteFrames(obj.active_material, frameStart, frameEnd)
            # Delete the object's shape key animation
            if obj.data and obj.data.shape_keys:
                self.deleteFrames(obj.data.shape_keys, frameStart, frameEnd)
        # Remove animation from List
        animList.remove(animListIdx)
        if animListIdx > 0:
            rootDummy.nvb.animListIdx = animListIdx - 1
        return {'FINISHED'}


class NVB_OP_Anim_Moveback(bpy.types.Operator):
    """Move an animation and its keyframes to the end of the animation list"""

    bl_idname = 'nvb.anim_moveback'
    bl_label = 'Move an animation and its keyframes to the end.'

    @classmethod
    def poll(self, context):
        """Prevent execution if animation list is empty."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 1)
        return False

    def moveFrames(self, target, oldStart, oldEnd, newStart):
        """TODO: DOC."""
        if target.animation_data and target.animation_data.action:
            insertionOptions = {'FAST'}
            action = target.animation_data.action
            framesToDelete = []
            for fcurve in action.fcurves:
                for p in fcurve.keyframe_points:
                    if (oldStart <= p.co[0] <= oldEnd):
                        framesToDelete.append((fcurve.data_path, p.co[0]))
                        newFrame = p.co[0] + newStart - oldStart
                        fcurve.keyframe_points.insert(newFrame, p.co[1],
                                                      insertionOptions)
                fcurve.update()
            # Delete the frames by accessing them from the object.
            # (Can't do it directly)
            for dp, f in framesToDelete:
                target.keyframe_delete(dp, frame=f)

    def execute(self, context):
        """TODO: DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if not nvb_utils.checkAnimBounds(rootDummy):
            self.report({'INFO'}, 'Failure: Convoluted animations.')
            return {'CANCELLED'}
        animList = rootDummy.nvb.animList
        currentAnimIdx = rootDummy.nvb.animListIdx
        anim = animList[currentAnimIdx]
        # Grab some data for speed
        oldStart = anim.frameStart
        oldEnd = anim.frameEnd
        # Get the end of the timeline
        newStart = 0
        for a in rootDummy.nvb.animList:
            if a.frameEnd > newStart:
                newStart = a.frameEnd
        newStart = newStart + nvb_def.anim_offset
        # Get a list of affected objects
        objList = [rootDummy]
        for o in objList:
            for c in o.children:
                objList.append(c)
        # Move keyframes
        for obj in objList:
            # Delete the objects animation
            self.moveFrames(obj, oldStart, oldEnd, newStart)
            # Delete the object's material animation
            if obj.active_material:
                self.moveFrames(obj.active_material,
                                oldStart, oldEnd, newStart)
            # Delete the object's shape key animation
            if obj.data and obj.data.shape_keys:
                self.moveFrames(obj.data.shape_keys,
                                oldStart, oldEnd, newStart)

        # Adjust animations in the list
        for e in anim.eventList:
            e.frame = newStart + (e.frame - oldStart)
        anim.frameStart = newStart
        anim.frameEnd = newStart + (oldEnd - oldStart)
        # Set index
        newAnimIdx = len(animList) - 1
        animList.move(currentAnimIdx, newAnimIdx)
        rootDummy.nvb.animListIdx = newAnimIdx
        # Re-adjust the timeline to the new bounds
        nvb_utils.toggleAnimFocus(context.scene, rootDummy)
        return {'FINISHED'}


class NVB_OP_Anim_Move(bpy.types.Operator):
    """Move an item in the animation list, without affecting keyframes"""

    bl_idname = 'nvb.anim_move'
    bl_label = 'Move an animation in the list, without affecting keyframes'

    direction = bpy.props.EnumProperty(items=(('UP', 'Up', ''),
                                              ('DOWN', 'Down', '')))

    @classmethod
    def poll(self, context):
        """Prevent execution if animation list has less than 2 elements."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if rootDummy is not None:
            return (len(rootDummy.nvb.animList) > 1)
        return False

    def execute(self, context):
        """TODO: DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        animList = rootDummy.nvb.animList

        currentIdx = rootDummy.nvb.animListIdx
        newIdx = 0
        maxIdx = len(animList) - 1
        if self.direction == 'DOWN':
            newIdx = currentIdx + 1
        elif self.direction == 'UP':
            newIdx = currentIdx - 1
        else:
            return {'CANCELLED'}

        newIdx = max(0, min(newIdx, maxIdx))
        if newIdx == currentIdx:
            return {'CANCELLED'}
        animList.move(currentIdx, newIdx)
        rootDummy.nvb.animListIdx = newIdx
        return {'FINISHED'}


class NVB_OP_LightFlare_New(bpy.types.Operator):
    """Add a new item to the flare list"""

    bl_idname = 'nvb.lightflare_new'
    bl_label = 'Add a new flare to a light'

    def execute(self, context):
        """TODO: DOC."""
        if (context.object.type == 'LAMP'):
            context.object.nvb.flareList.add()

        return {'FINISHED'}


class NVB_OP_LightFlare_Delete(bpy.types.Operator):
    """Delete the selected item from the flare list"""

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
    """Move an item in the flare list"""

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
    """Add a new item to the event list"""

    bl_idname = 'nvb.animevent_new'
    bl_label = 'Add a new event to an animation'

    @classmethod
    def poll(self, context):
        """Enable only if there is an animation."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        animList = rootDummy.nvb.animList

        return len(animList) > 0

    def execute(self, context):
        """TODO: DOC."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        anim = rootDummy.nvb.animList[rootDummy.nvb.animListIdx]

        eventList = anim.eventList
        newEvent = eventList.add()
        if anim.frameStart <= bpy.context.scene.frame_current <= anim.frameEnd:
            newEvent.frame = bpy.context.scene.frame_current
        else:
            newEvent.frame = anim.frameStart

        return {'FINISHED'}


class NVB_OP_AnimEvent_Delete(bpy.types.Operator):
    """Delete the selected item from the event list"""

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
    """Move an item in the event list"""

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


class NVB_OP_LightGenerateName(bpy.types.Operator):
    """Generate an appropriate name for the light"""

    bl_idname = 'nvb.light_generatename'
    bl_label = 'Generate a name for the light'

    @classmethod
    def poll(self, context):
        """Enable only if a Lamp is selected."""
        return (context.object and context.object.type == 'LAMP')

    def execute(self, context):
        """TODO: DOC."""
        obj = context.object
        rootDummy = nvb_utils.findObjRootDummy(obj)
        if not rootDummy:
            self.report({'INFO'}, 'Failure: No rootdummy.')
            return {'CANCELLED'}
        currentSuffix = nvb_def.Lighttype.getSuffix(obj)
        newSuffix = nvb_def.Lighttype.generateSuffix(obj)
        baseName = rootDummy.name
        if newSuffix:
            # Remove old suffix first
            if currentSuffix:
                baseName = obj.name[:-1*len(currentSuffix)]
            newName = baseName + '' + newSuffix
            if newName in bpy.data.objects:
                self.report({'INFO'}, 'Failure: Name already exists.')
                return {'CANCELLED'}
            elif obj.name.endswith(newSuffix):
                self.report({'INFO'}, 'Failure: Suffix already exists.')
                return {'CANCELLED'}
            else:
                obj.name = newName
                return {'FINISHED'}
        self.report({'INFO'}, 'Failure: No suffix found.')
        return {'CANCELLED'}


class NVB_OP_DummyGenerateName(bpy.types.Operator):
    """Generate an appropriate name for the dummy"""

    bl_idname = 'nvb.dummy_generatename'
    bl_label = 'Generate a name for the dummy'

    @classmethod
    def poll(self, context):
        """Enable only if a Empty is selected."""
        return (context.object and context.object.type == 'EMPTY')

    def execute(self, context):
        """TODO: DOC."""
        obj = context.object
        rootDummy = nvb_utils.findObjRootDummy(obj)
        if not rootDummy:
            self.report({'INFO'}, 'Failure: No rootdummy.')
            return {'CANCELLED'}
        currentSuffix = nvb_def.Dummytype.getSuffix(obj)
        newSuffix = nvb_def.Dummytype.generateSuffix(
                        obj,
                        rootDummy.nvb.classification)
        baseName = rootDummy.name
        if newSuffix:
            # Remove old suffix first
            if currentSuffix:
                baseName = obj.name[:-1*len(currentSuffix)]
            newName = baseName + '_' + newSuffix
            if newName in bpy.data.objects:
                self.report({'INFO'}, 'Failure: Name already exists.')
                return {'CANCELLED'}
            elif obj.name.endswith(newSuffix):
                self.report({'INFO'}, 'Failure: Suffix already exists.')
                return {'CANCELLED'}
            else:
                obj.name = newName
                return {'FINISHED'}
        self.report({'INFO'}, 'Failure: No suffix found.')
        return {'CANCELLED'}


class NVB_OP_Import(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    """Import Aurora Engine model (.mdl)"""

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
            name='Import Smooth Groups',
            description='Import smooth groups as sharp edges',
            default=True)
    importAnimations = bpy.props.BoolProperty(
            name='Import Animations',
            description='Import animations',
            default=True)
    importSupermodel = bpy.props.BoolProperty(
            name='Import Supermodel',
            description='Import animations from supermodel',
            default=False,
            options={'HIDDEN'})
    materialMode = bpy.props.EnumProperty(
            name='Materials',
            items=(('NON', 'None',
                    'Don\'t create materials or import textures', 0),
                   ('SIN', 'Single',
                    'Create only one material per texture \
                     (shared between objects)', 1),
                   ('MUL', 'Multiple',
                    'Always create a seperate material for each object', 2)),
            default='SIN')
    textureSearch = bpy.props.BoolProperty(
            name='Image Search',
            description='Search for images in subdirectories'
                        ' (Warning, may be slow)',
            default=False)
    # Hidden options, only used for batch minimap creation
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
    """Export Aurora Engine model (.mdl)"""

    bl_idname = 'nvb.mdlexport'
    bl_label = 'Export Aurora MDL'

    filename_ext = '.mdl'
    filter_glob = bpy.props.StringProperty(
            default='*.mdl',
            options={'HIDDEN'})
    exportAnimations = bpy.props.BoolProperty(
            name='Export Animations',
            description='Export animations',
            default=True)
    exportWalkmesh = bpy.props.BoolProperty(
            name='Export Walkmesh',
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
    """Load all materials for aabb walkmeshes for the selected object"""

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
    """TODO: DOC"""

    bl_idname = "nvb.render_minimap"
    bl_label = "Render Minimap"

    @classmethod
    def poll(self, context):
        """Prevent execution if no object is selected."""
        return (context.object is not None)

    def execute(self, context):
        """Create camera + lamp and Renders Minimap."""
        rootDummy = nvb_utils.findObjRootDummy(context.object)
        if not rootDummy:
            return {'CANCELLED'}
        scene = bpy.context.scene

        nvb_utils.setupMinimapRender(rootDummy, scene)
        bpy.ops.render.render(use_viewport=True)
        # bpy.ops.render.view_show()

        self.report({'INFO'}, 'Ready to render')
        return {'FINISHED'}


class NVB_OBJECT_OT_SkingroupAdd(bpy.types.Operator):
    """TODO: DOC"""

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
