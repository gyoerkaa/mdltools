# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


bl_info = {
    "name": "Neverblender",
    "author": "Attila Györkös",
    "blender": (2, 6, 3),
    "location": "File > Import-Export, Object Properties",
    "description": "Import, Export and edit Neverwinter Nights models"
                   "and effects",
    "warning": "",
    "wiki_url": ""
                "",
    "tracker_url": "",
    "category": "Game Engine"}


if "bpy" in locals():
    import imp
    imp.reload(nvb_importmdl)
    imp.reload(nvb_exportmdl)
else:
    from . import nvb_importmdl
    from . import nvb_exportmdl

    
import bpy
from bpy.props import StringProperty, FloatProperty, BoolProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper


def nvb_update_shadow_prop(self, context):
    '''
    Set the lamps shadow to match the aurora shadow property
    '''  
    object = context.object
    if (object):
        if (object.type == 'LAMP'):
            if (object.auroraprops.shadow):
                object.data.shadow_method = 'RAY_SHADOW'
            else:
                object.data.shadow_method = 'NOSHADOW'


def nvb_update_lighttype_prop(self, context):
    '''
    Renames lamp acording to match selected light type
    '''
    object = context.object
    if (object):    
        if (object.type == 'LAMP'):
            if (object.auroraprops.lighttype == 'NONE'):
                pass
            elif (object.auroraprops.lighttype == 'MAINLIGHT1'):
                pass         
            elif (object.auroraprops.lighttype == 'MAINLIGHT2'):
                pass
            elif (object.auroraprops.lighttype == 'SOURCELIGHT1'):
                pass                
            elif (object.auroraprops.lighttype == 'SOURCELIGHT2'):
                pass 


def nvb_update_lifeexp_prop(self, context):
    pass

    
class NVBOBJECT_OT_LoadWokMaterials(bpy.types.Operator):
    bl_idname = "nvb.load_wok_mats"
    bl_label  = "Load walkmesh materials"
    
    def execute(self, context):
        '''
        - Deletes all current materials
        - adds walkmesh materials
        '''
        walkmesh_object = context.object
        if (walkmesh_object):
            object_mesh = walkmesh_object.data
            
            # Remove all current material slots
            for i in range(len(walkmesh_object.material_slots)):
                bpy.ops.object.material_slot_remove()
                
            # Create walkmesh materials
            for i in range(len(nvb_presets.wok_materials)):
                mat_name = nvb_presets.wok_materials[i][0] +'.mat'
        
                # Walkmesh materials should be shared across multiple walkmesh objects
                if mat_name in bpy.data.materials.keys():
                    walkmesh_mat = bpy.data.materials[mat_name]
                else:
                    walkmesh_mat = bpy.data.materials.new(mat_name)
        
                    walkmesh_mat.diffuse_color      = nvb_presets.wok_materials[i][1]
                    walkmesh_mat.diffuse_intensity  = 1.0 
                    walkmesh_mat.specular_color     = (0.0,0.0,0.0)
                    walkmesh_mat.specular_intensity = nvb_presets.wok_materials[i][2]
        
                object_mesh.materials.append(walkmesh_mat)
                       

        return{'FINISHED'}
        

class NVBOBJECT_OT_RenderMinimap(bpy.types.Operator):
    bl_idname = "nvb.render_minimap"
    bl_label  = "Render Minimap"
    
    def execute(self, context):
        '''
        - Creates an camera and a lamp
        - Renders Minimap 
        '''
        mdlbase = context.object
        if (mdlbase):
            if (mdlbase.type == 'EMPTY') and (mdlbase.auroraprops.dummytype == 'MDLBASE'):          
                nvb_utils.nvb_minimap_render_setup(mdlbase, bpy.context.scene)
                bpy.ops.render.render()            

        return{'FINISHED'}

        
class NVBOBJECT_OT_AnimsceneRename(bpy.types.Operator):
    bl_idname = "nvb.animscene_rename"
    bl_label  = "Rename animation scene"
    
    def execute(self, context):
        object = context.object
        scene  = context.scene
        
        current_name = object.auroraprops.animname
        new_name     = object.auroraprops.newanimname
        print(object.name)

        return{'FINISHED'}

        
class NVBOBJECT_OT_SkingroupAdd(bpy.types.Operator):
    bl_idname = "nvb.skingroup_add"
    bl_label  = "Add new Skingroup"
    
    def execute(self, context):
        object      = context.object       
        skingr_name = object.auroraprops.new_skingroupname
        # Check if there is already a vertex group with this name
        if (skingr_name != '') and (skingr_name not in object.vertex_groups.keys()):
            # Create the vertex group
            vert_group = object.vertex_groups.new(skingr_name)
            
        return{'FINISHED'}
        
        
class NVBOBJECT_OT_AnimsceneAdd(bpy.types.Operator):
    bl_idname = "nvb.animscene_add"
    bl_label  = "Add animation scene"
    
    def execute(self, context):
        object        = context.object
        anim_name     = object.auroraprops.newanimname
        source_scene  = context.scene
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

        
class NVBAuroraMDLImport(bpy.types.Operator, ImportHelper):
    '''Import from Neverwinter Nights file format (.mdl)'''
    
    bl_idname  = 'nvb.importmdl'
    bl_label   = 'Import NwN MDL'
    bl_options = {'UNDO'}
    
    filename_ext = '.mdl'
    filter_glob = StringProperty(
            default = '*.mdl', 
            options = {'HIDDEN'},
            )
           
    import_items = EnumProperty(
            name = 'Import',
            options = {'ENUM_FLAG'},
            items = (('GEOMETRY', 'Geometry', ''),
                     ('ANIMATIONS', 'Animations', ''),
                     ),
            default = {'GEOMETRY', 'ANIMATIONS'},
            )
    
    import_walkmesh = BoolProperty(
            name='Import walkmesh',
            description='Import walkmesh, if applicable' \
                        '(.pwk, .dwk or .mdl depending on classification)',
            default=True,
            ) 
    
    import_shading_groups = BoolProperty(
            name='Import Shading Groups',
            description='Import shading groups as vertex groups ' \
                        '(Unused by blender)',
            default=False,
            )
    
    use_image_search = BoolProperty(
            name='Image Search',
            description='Search subdirectories for any associated images ' \
                        '(Warning, may be slow)',
            default=False,
            )
            
    one_texture_per_image = BoolProperty(
            name='One Texture per Image',
            description='Create only one texture per Image' \
                        '(Will result in one texture for every node)',
            default=True,
            )
            
    import_lights = BoolProperty(
            name='Import Light',
            description='Wether to import lights' \
                        '(Useful for rendering minmaps)',
            default=True,
            options={'HIDDEN'},
            )
            
    def execute(self, context):
        from . import nvb_importmdl
        
        keywords = self.as_keywords(ignore=('filter_glob',
                                            'check_existing',
                                            ))
        
        return nvb_importmdl.load(self, context, **keywords)


class NVBAuroraMDLExport(bpy.types.Operator, ExportHelper):
    '''Export to Neverwinter Nights file format (.mdl)'''
    bl_idname = 'nvb.exportmdl'
    bl_label  = 'Export NwN MDL'
    
    filename_ext = '.mdl'
    filter_glob = StringProperty(
            default='*.mdl',
            options={'HIDDEN'},
            )
    
    export_selection = EnumProperty(
            name='Export',
            items=(('ALL', 'All', ''),
                   ('SELECTION', 'Selection only', ''),
                   ('LAYER','Active layers', ''),
                   ),
            default='ALL',
            )
    
    export_walkmesh = BoolProperty(
            name='Export walkmesh',
            description='Export walkmesh, if applicable' \
                        '(.pwk, .dwk or .wok depending on classification)',
            default=True,
            )
    
    export_shading_groups = BoolProperty(
            name='Export Shading groups',
            description='Export Shading Groups' \
                        '(When disabled, every face belongs to the same group)',
            default=False,
            )
            
    def execute(self, context):
        from . import nvb_exportmdl

        keywords = self.as_keywords(ignore=('filter_glob',
                                            'check_existing',
                                            ))
        
        return nvb_exportmdl.save(self, context, **keywords)


class NVBAuroraParticlePropertyGroup(bpy.types.PropertyGroup):
    # For Emitters 
        
    birthrate     = bpy.props.IntProperty(name = 'Birthrate', description = '???', default = 10, min = 0)
        
    # Inheritance props
    inherit       = bpy.props.BoolProperty(name = 'Inherit', description = '???', default = False)
    inherit_vel   = bpy.props.BoolProperty(name = 'Velocity', description = 'Inherit Velocity', default = False)    
    inherit_local = bpy.props.BoolProperty(name = 'Local', description = '???', default = False)    
    inherit_part  = bpy.props.BoolProperty(name = 'Part', description = '???', default = False)
       
    # Blast props
    blastradius = bpy.props.FloatProperty(name = 'Radius', description = '???', default = 0.0, min = 0.0)
    blastlength = bpy.props.FloatProperty(name = 'Length', description = '???', default = 0.0, min = 0.0)
    
    # Particle props
    colorstart  = bpy.props.FloatVectorProperty(name = 'Color start',
                                                description = 'Start color',
                                                subtype = 'COLOR_GAMMA', 
                                                default = (1.0, 1.0, 1.0), 
                                                min = 0.0, max = 1.0, 
                                                soft_min = 0.0, soft_max = 1.0)
    colorend    = bpy.props.FloatVectorProperty(name = 'Color end',
                                                description = 'End Color',
                                                subtype = 'COLOR_GAMMA', 
                                                default = (1.0, 1.0, 1.0), 
                                                min = 0.0, max = 1.0, 
                                                soft_min = 0.0, soft_max = 1.0)
    alphastart  = bpy.props.FloatProperty(name = 'Alpha start', default = 1.0, min = 0.0, max = 1.0)
    alphaend    = bpy.props.FloatProperty(name = 'Alpha end', default = 1.0, min = 0.0, max = 1.0)   
    sizestart   = bpy.props.FloatProperty(name = 'Size start', default = 1.0, min = 0.0)
    sizeend     = bpy.props.FloatProperty(name = 'Size end', default = 1.0, min = 0.0)    
    sizestart_y = bpy.props.FloatProperty(name = 'Sizestart_y', default = 0.0, min = 0.0)
    sizeend_y   = bpy.props.FloatProperty(name = 'Sizeend_y', default = 0.0, min = 0.0)
    
    # Misc props
    lifeexp     = bpy.props.FloatProperty(name = 'Life Exp.', description = 'Life Expectancy', default = 1.0, min = 0.0, update=nvb_update_lifeexp_prop)
    istinted    = bpy.props.BoolProperty(name = 'Tinted', description = 'Tint texture with start- and end color', default = False)
    bounce      = bpy.props.BoolProperty(name = 'Bounce type', description = '???', default = False)
    random      = bpy.props.BoolProperty(name = 'Random', description = '???', default = False)    
    splat       = bpy.props.BoolProperty(name = 'Splat', description = '???', default = False) 
    renderorder = bpy.props.IntProperty(name = 'Render order', description = '???', default = 0, min = 0)
    chunkname   = bpy.props.StringProperty(name = 'Name', description = 'Chunk Name', default = '')
    loop        = bpy.props.BoolProperty(name = 'Loop', description = '???', default = False)
    deadspace   = bpy.props.FloatProperty(name = 'Dead space', description = '???', default = 0.0, min = 0.0)
    twosidedtex = bpy.props.BoolProperty(name = 'Two Sided Texture', description = '???', default = False)    
    bounce_co   = bpy.props.FloatProperty(name = 'Coeff.', description = 'Bounce coefficient', default = 0.0, min = 0.0)
    spread      = bpy.props.FloatProperty(name = 'Spread', description = '???', default = 0.0, min = 0.0)
    particlerot = bpy.props.FloatProperty(name = 'Rotation', description = 'Particle Rotation', default = 0.0, min = -360.0, max = 360.0)
    fps         = bpy.props.IntProperty(name = 'Fps', description = '???', default = 24, min = 0)
    blurlength  = bpy.props.FloatProperty(name = 'Blur Length', description = '???', default = 10.0)
    
    # Lighting props
    lightningdelay  = bpy.props.FloatProperty(name = 'Delay', description = '???', default = 0.0, min = 0.0, max = 1000.0)
    lightningradius = bpy.props.FloatProperty(name = 'Radius', description = '???', default = 0.0, min = 0.0, max = 1000.0)
    lightningsubdiv = bpy.props.IntProperty(name = 'Subdivs.', description = '???', default = 0, min = 0, max = 12)
    lightningscale  = bpy.props.FloatProperty(name = 'Scale', description = '???', default = 1.0, min = 0.0, max = 1.0)
    
    # Emitter Style
    blend       = bpy.props.EnumProperty(name  = 'Blend',
                                         description = 'Blend type',    
                                         items = [('NORMAL', 'Normal', 'Normal', 1), 
                                                  ('PUNCH-THROUGH', 'Punch-Through', 'Punch-Through',2), 
                                                  ('LIGHTEN', 'Lighten', 'Lighten', 3)], 
                                         default = 'NORMAL')    
    update      = bpy.props.EnumProperty(name  = 'Update', 
                                         description = 'Update type',     
                                         items = [('FOUNTAIN', 'Fountain', 'Fountain', 0), 
                                                  ('SINGLE', 'Single', 'Single', 1),
                                                  ('EXPLOSION', 'Explosion', 'Explosion', 2),
                                                  ('LIGHTNING', 'Lightning', 'Lightning', 3)], 
                                         default = 'FOUNTAIN')    
    render      = bpy.props.EnumProperty(name  = 'Render',
                                         description = 'Render type',     
                                         items = [('NORMAL', 'Normal', 'Normal', 1), 
                                                  ('LINKED', 'Linked', 'Linked', 2), 
                                                  ('BB2LZ', 'Billboard to local Z', 'Billboard to local Z', 3),
                                                  ('BB2WZ', 'Billboard to world Z', 'Billboard to world Z', 4),
                                                  ('AL2WZ', 'Aligned to world Z', 'Aligned  to world Z', 5),
                                                  ('AL2PD', 'Aligned to particle dir.', 'Aligned to particle direction', 6),
                                                  ('MOBLUR', 'Motion Blur', 'Motion Blur', 7)],
                                         default = 'NORMAL')
    spawntype   = bpy.props.EnumProperty(name = 'Spawn', 
                                         description = 'Spawn type',     
                                         items = [('NORMAL', 'Normal', 'Normal', 0), 
                                                  ('TRAIL', 'Trail', 'Trail', 1)], 
                                         default = 'NORMAL')
    
    #p2p props
    p2p         = bpy.props.IntProperty(name = 'p2p', description = '???', default = 0, min = 0)    
    p2p_type    = bpy.props.EnumProperty(name = 'Type', 
                                         description = '???',
                                         items = [('BEZIER', 'Bezier', 'Bezier', 0), 
                                                  ('GRAVITY', 'Gravity', 'Gravity', 1)], 
                                         default = 'BEZIER')
    p2p_bezier2 = bpy.props.FloatProperty(name = 'Bezier 2', description = '???', default = 0.0)
    p2p_bezier3 = bpy.props.FloatProperty(name = 'Bezier 3', description = '???', default = 0.0)
    threshold   = bpy.props.FloatProperty(name = 'Threshold', description = '???', default = 0.0)    
    combinetime = bpy.props.FloatProperty(name = 'Combinetime', description = '???', default = 0.0)
    

class NVBAuroraPropertyPanelParticleSystem(bpy.types.Panel):
    bl_idname      = 'nvb.propertypanel.particlesystem'
    bl_label       = 'Aurora Particle Properties'
    bl_space_type  = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    #bl_context = 'particle'    

    @classmethod
    def poll(cls, context):
        if context.particle_system:
            partsys_settings = context.particle_system.settings
            if partsys_settings is None:
                return False
            else:
                return True
        else:
            return False

    
    def draw(self, context):
    
        def factor_but(layout, target, toggle, factor, name):
            row = layout.row(align=True)
            row.prop(target, toggle, text="")
            sub = row.row()
            sub.active = getattr(target, toggle)
            sub.prop(target, factor, text=name, slider=True)
            return sub 
        
        if context.particle_system:
            partsys_settings = context.particle_system.settings
        
            layout = self.layout
            
            row = layout.row()
            row.label(text='Emitter properties')  
            
            row = layout.row()
            row.prop(partsys_settings.auroraprops, 'blend')
            
            row = layout.row()
            row.prop(partsys_settings.auroraprops, 'update')
            
            row = layout.row()
            row.prop(partsys_settings.auroraprops, 'render')
            
            row = layout.row()
            row.prop(partsys_settings.auroraprops, 'spawntype')
            
            row = layout.row()
            row.prop(partsys_settings.auroraprops, 'birthrate')
        
            split = layout.split()
            col = split.column(align=True)
            col.prop(partsys_settings, 'frame_start')
            col.prop(partsys_settings, 'frame_end')
            
            col = split.column(align=True)
            col.prop(partsys_settings, 'normal_factor')
            col.prop(partsys_settings, 'factor_random')            
            
            split = layout.split()
            col = split.column(align=True)
            col.prop(partsys_settings.auroraprops, 'lifeexp')
            
            col = split.column(align=True)
            col.prop(partsys_settings, 'mass')
            
            row = layout.row()
            col = row.column()
            col.prop(partsys_settings.effector_weights, 'wind')
            col.prop(partsys_settings.effector_weights, 'drag')
            col.prop(partsys_settings.effector_weights, 'gravity')
            
            layout.separator()
            row = layout.row()
            row.label(text='Chunk')             
            row = layout.row()
            row.prop(partsys_settings.auroraprops, 'chunkname', text = 'Name')
            
            # Particle properties
            layout.separator()
            row = layout.row()
            row.label(text='Animation')            
            split = layout.split()
            col = split.column(align=True)
            col.prop(partsys_settings.auroraprops, 'colorstart', text='')
            col.prop(partsys_settings.auroraprops, 'colorend', text='')
            
            col = split.column(align=True)
            col.prop(partsys_settings.auroraprops, 'alphastart')
            col.prop(partsys_settings.auroraprops, 'alphaend')

            split = layout.split()
            col = split.column(align=True)
            col.prop(partsys_settings.auroraprops, 'sizestart')
            col.prop(partsys_settings.auroraprops, 'sizeend')
            
            col = split.column(align=True)
            col.prop(partsys_settings.auroraprops, 'sizestart_y')
            col.prop(partsys_settings.auroraprops, 'sizeend_y')
  
            # Blast props
            layout.separator()
            row = layout.row()
            row.label(text='Blast properties')
            row = layout.row()
            row.prop(partsys_settings.auroraprops, 'blastradius')
            row.prop(partsys_settings.auroraprops, 'blastlength')
            
            # Misc props
            layout.separator()
            row = layout.row()
            row.label(text='Misc. properties')                     
            split = layout.split()
            col = split.column()
            col.prop(partsys_settings.auroraprops, 'spread')
            col.prop(partsys_settings.auroraprops, 'particlerot')
            col.prop(partsys_settings.auroraprops, 'blurlength')
            col = split.column()
            col.prop(partsys_settings.auroraprops, 'deadspace')
            col.prop(partsys_settings.auroraprops, 'renderorder')
            col.prop(partsys_settings.auroraprops, 'fps')
            
            split = layout.split()
            col = split.column()
            col.prop(partsys_settings.auroraprops, 'istinted')
            col.prop(partsys_settings.auroraprops, 'twosidedtex')
            col = split.column()
            col.prop(partsys_settings.auroraprops, 'splat')
            col.prop(partsys_settings.auroraprops, 'loop')
            col.prop(partsys_settings.auroraprops, 'random')
            
            # Inheritance
            layout.separator()
            row = layout.row()
            row.label(text='Inheritance')            
            split = layout.split()
            col = split.column()            
            col.prop(partsys_settings.auroraprops, 'inherit')
            col.prop(partsys_settings.auroraprops, 'inherit_vel') 
            col = split.column()
            col.prop(partsys_settings.auroraprops, 'inherit_local')
            col.prop(partsys_settings.auroraprops, 'inherit_part')
            
            # p2p settings
            layout.separator()
            row = layout.row()
            row.label(text='p2p Settings')            
            split = layout.split()
            col = split.column()            
            col.prop(partsys_settings.auroraprops, 'p2p')
            col.prop(partsys_settings.auroraprops, 'p2p_type') 
            col = split.column()
            col.prop(partsys_settings.auroraprops, 'p2p_bezier2')
            col.prop(partsys_settings.auroraprops, 'p2p_bezier3')
            
            row = layout.row()
            row.prop(partsys_settings.auroraprops, 'threshold')
            row = layout.row()
            row.prop(partsys_settings.auroraprops, 'combinetime')
    
            # Lightning
            layout.separator()
            row = layout.row()
            row.label(text='Lightning')            
            split = layout.split()
            col = split.column()            
            col.prop(partsys_settings.auroraprops, 'lightningdelay')
            col.prop(partsys_settings.auroraprops, 'lightningradius') 
            col = split.column()
            col.prop(partsys_settings.auroraprops, 'lightningsubdiv')
            col.prop(partsys_settings.auroraprops, 'lightningscale')
            
            # Bounce
            layout.separator()
            row = layout.row()
            row.label(text='Bounce') 
            factor_but(layout, partsys_settings.auroraprops, 'bounce', 'bounce_co', 'Coeff.')


class NVBAuroraObjectPropertyGroup(bpy.types.PropertyGroup):

    # For all objects
    wirecolor = bpy.props.FloatVectorProperty(name = 'Wirecolor',
                                              description = 'Color of the wireframe',
                                              subtype = 'COLOR_GAMMA', 
                                              default = (1.0, 1.0, 1.0), 
                                              min = 0.0, max = 1.0, 
                                              soft_min = 0.0, soft_max = 1.0
                                              )
    shadow = bpy.props.BoolProperty(name = 'Shadow', description = 'Whether to cast shadows', default = True, update=nvb_update_shadow_prop)                                              
    
    # For emptys
    dummytype        = bpy.props.EnumProperty(name = 'Type', items=[('NONE', 'None', 'Simple dummy object', 0), ('MDLBASE', 'Mdl Base', 'All objects have to parented to this', 1), ('PWKBASE', 'Pwk Base', 'Placeable walkmesh', 2), ('DWKBASE', 'Dwk Base', 'Door walkmesh', 3)], default = 'NONE')
    
    
    # For mdl base
    supermodel       = bpy.props.StringProperty(name = 'Supermodel', description = 'Name of the supermodel', default = 'NULL')
    classification   = bpy.props.EnumProperty(name = 'Classification', items=[('UNKNOWN', 'Unknown', 'Unknown classification', 0),('TILE', 'Tile', 'Tile for a tileset', 1), ('CHARACTER', 'Character', 'Creature, Character', 2), ('DOOR', 'Door', 'Door Desc.', 3), ('EFFECT', 'Effect', 'Effect Desc.', 4), ('GUI', 'Gui', 'Gui Icons, etc.', 5), ('ITEM', 'Item', 'Items', 6)], default = 'UNKNOWN' )
    animationscale   = bpy.props.FloatProperty(name = 'Animationscale', default = 1.00, min = 0.0)
    
    # Minimap generation
    minimapzoffset   = bpy.props.FloatProperty(name = 'Minimap Z Offset', default = 0.00, min = 0.00)
    minimapsize      = bpy.props.IntProperty(name = 'Size', default = 32, min = 16) 

    # Creation and renaming of animation scenes
    newanimname      = bpy.props.StringProperty(name = 'newanimname', description = 'Name of the new animation', default = '')
    
    # For mdl bases in animation scenes
    in_animscene     = bpy.props.BoolProperty(name = 'In Anim. Scene', description = 'Wether this dummy is in an animationscene', default = False)
    transtime        = bpy.props.FloatProperty(name = 'Transistiontime', description = 'Used for for animations only. \n Set it for each Scene individually', default = 1.00, min = 0.0)   
    animname         = bpy.props.StringProperty(name = 'Animationname', description = 'Name of the animation', default = '')
        
    # For meshes
    meshtype         = bpy.props.EnumProperty(name = 'Type', items=[('TRIMESH', 'Trimesh', '0 desc', 0), ('DANGLYMESH', 'Danglymesh', '1 desc', 1), ('SKIN', 'Skinmesh', '2 desc', 2), ('AABB', 'aabb Walkmesh', '3 desc', 3), ('EMITTER', 'Emitter', '4 desc', 4)], default = 'TRIMESH' )
    tilefade         = bpy.props.BoolProperty(name = 'Tilefade', default = False)
    render           = bpy.props.BoolProperty(name = 'Render', description = 'Whether to render this object in the scene', default = True)    
    beaming          = bpy.props.BoolProperty(name = 'beaming', description = 'Object casts beams (see forest tileset)', default = False)
    inheritcolor     = bpy.props.BoolProperty(name = 'Inheritcolor', description = '(Unused by NWN)', default = False)
    rotatetexture    = bpy.props.BoolProperty(name = 'Rotatetexture', description = 'Automatically rotates texture to prevent seams', default = False)
    transparencyhint = bpy.props.IntProperty(name = 'Transparency Hint', default = 0, min = 0, max = 32)
    selfillumcolor   = bpy.props.FloatVectorProperty(name = 'Selfilluminationcolor',
                                                     description = 'Self illumination color',
                                                     subtype = 'COLOR_GAMMA', 
                                                     default = (0.0, 0.0, 0.0), 
                                                     min = 0.0, max = 1.0, 
                                                     soft_min = 0.0, soft_max = 1.0)
    ambientcolor     = bpy.props.FloatVectorProperty(name = 'Ambientcolor',
                                                     description = 'Ambient color',
                                                     subtype = 'COLOR_GAMMA', 
                                                     default = (1.0, 1.0, 1.0), 
                                                     min = 0.0, max = 1.0, 
                                                     soft_min = 0.0, soft_max = 1.0)    
    shininess        = bpy.props.IntProperty(name = 'Shininess', default = 1, min = 0, max = 32)
    
    # For danglymeshes (are also meshes)
    period           = bpy.props.FloatProperty(name = 'Period', default = 1.0, min = 0.0, max = 32.0)
    tightness        = bpy.props.FloatProperty(name = 'Tightness', default = 1.0, min = 0.0, max = 32.0)
    displacement     = bpy.props.FloatProperty(name = 'Displacement', default = 0.5, min = 0.0, max = 32.0)
    danglegroup      = bpy.props.StringProperty(name = 'Danglegroup', description = 'Name of the vertex group to use for the danglymesh', default = '')

    # For skingroups (are also meshes)
    new_skingroupname = bpy.props.StringProperty(name = 'Skingroup', description = 'Bone to create the skingroup for', default = '')
    
    # For lamps
    tilelight       = bpy.props.EnumProperty(name = 'Tilelight', items=[('NONE', 'None', 'Simple light', 0), ('MAINLIGHT1', 'Mainlight 1', 'Accessible from toolset', 1), ('MAINLIGHT2', 'Mainlight 2', 'Accessible from toolset', 2), ('SOURCELIGHT1', 'Sourcelight 1', 'Accessible from toolset', 3), ('SOURCELIGHT2', 'Sourcelight 2', 'Accessible from toolset', 4)], default = 'NONE', update=nvb_update_lighttype_prop)
    lightpriority   = bpy.props.IntProperty(name = 'Lightpriority', default = 5, min = 0, max = 5)
    fadinglight     = bpy.props.BoolProperty(name = 'Fading light', default = False)
    isdynamic       = bpy.props.BoolProperty(name = 'Is Dynamic', default = False)
    affectdynamic   = bpy.props.BoolProperty(name = 'Affect Dynamic', description = 'Affect dynamic objects', default = False)
    

class NVBAuroraPropertyPanelEmpty(bpy.types.Panel):

    bl_idname = 'nvb.propertypanel.dummy'
    bl_label = 'Aurora Dummy Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'
    
    @classmethod
    def poll(cls, context):
        return (context.object and context.object.type == 'EMPTY')
    
    def draw(self, context):
        object      = context.object        
        object_type = object.type
        
        layout = self.layout
        
        if (object.auroraprops.in_animscene):
            # This MDLBASE is in an animation scene
            
            row = layout.row()
            row.prop(object.auroraprops, 'transtime', text = 'Transition Time')
            
            row = layout.row()
            box = row.box()
            box.label(text = 'Rename animation: ')
            row = box.row(align = True)
            row.prop(object.auroraprops, 'newanimname', text = '')
            row.operator('nvb.animscene_rename', text = '', icon='FILE_REFRESH')
        
        else:
            row = layout.row()
            row.prop(object.auroraprops, 'dummytype', text='Type')#, expand=True)
            
            if (object.auroraprops.dummytype == 'MDLBASE'):
                row = layout.row()
                row.prop(object.auroraprops, 'classification', text='Classification')
                
                row = layout.row()
                row.prop(object.auroraprops, 'supermodel', text='Supermodel')
                
                row = layout.row()
                row.prop(object.auroraprops, 'animationscale', text = 'Animationscale')
                
                row = layout.row()
                box = row.box()
                box.label(text = 'Create animation: ')
                row = box.row(align = True)
                row.prop(object.auroraprops, 'newanimname', text='')
                row.operator('nvb.animscene_add', text = '', icon='ZOOMIN')
                 
                row = layout.row()
                box = row.box()
                box.label(text = 'Minimap: ')
                row = box.row()
                row.prop(object.auroraprops, 'minimapzoffset', text = 'z Offset')
                row = box.row()
                row.prop(object.auroraprops, 'minimapsize', text = 'Minimap size')                
                row = box.row()
                row.operator('nvb.render_minimap', text = 'Render Minimap', icon='NONE')
                
            elif (object.auroraprops.dummytype in {'PWKBASE', 'DWKBASE'}):
                pass
            
            else:
                row = layout.row()
                row.prop(object.auroraprops, 'wirecolor', text = 'Wirecolor')            


class NVBAuroraPropertyPanelLight(bpy.types.Panel):

    bl_idname = 'nvb.propertypanel.light'
    bl_label = 'Aurora Light Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'
    
    @classmethod
    def poll(cls, context):
        return context.lamp
    
    def draw(self, context):
        object      = context.object        
        object_type = object.type
        
        layout = self.layout
        
        row = layout.row()
        row.prop(object.auroraprops, 'wirecolor', text='Wirecolor')
        
        split = layout.split()
        
        col = split.column()
        col.prop(object.data, 'use_negative', text='Negative Light')
        col.prop(object.data, 'use_diffuse', text='Use Diffuse')
        col.prop(object.auroraprops, 'shadow', text='Shadows')
        
        col = split.column() 
        col.prop(object.auroraprops, 'fadinglight', text='Fading')
        col.prop(object.auroraprops, 'isdynamic', text='Is dynamic')
        col.prop(object.auroraprops, 'affectdynamic', text='Affect dynamic')      
        
        row = layout.row()
        row.prop(object.auroraprops, 'lightpriority', text='Priority')        
        
        row = layout.row()        
        row.prop(object.auroraprops, 'tilelight', text='Tilelight')
    

class NVBAuroraPropertyPanelMesh(bpy.types.Panel):

    bl_idname = 'nvb.propertypanel.mesh'
    bl_label = 'Aurora Mesh Properties'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'
    
    @classmethod
    def poll(cls, context):        
        return (context.mesh and context.object.type != 'EMPTY')
    
    def draw(self, context):
        object      = context.object        
        object_type = object.type
        
        layout = self.layout
        
        row = layout.row()    
        row.prop(object.auroraprops, 'meshtype', text='Type')
        
        if (object.auroraprops.meshtype == 'EMITTER'):
            pass
        else: # Trimesh, danglymesh, skin
            
            row = layout.row()
            row.prop(object.auroraprops, 'wirecolor', text='Wirecolor')        
        
            row = layout.row()
            row.prop(object.auroraprops, 'selfillumcolor', text='Selfillum. color')
            
            row = layout.row()
            row.prop(object.auroraprops, 'ambientcolor', text='Ambient')        
            
            row = layout.row()
            row.prop(object.auroraprops, 'shininess', text='Shininess')        
        
            split = layout.split()
        
            col = split.column()        
            col.prop(object.auroraprops, 'tilefade', text='Tilefade')       
            col.prop(object.auroraprops, 'render', text='Render')
            col.prop(object.auroraprops, 'shadow', text='Shadow')
        
            col = split.column() 
            col.prop(object.auroraprops, 'beaming', text='Beaming')
            col.prop(object.auroraprops, 'inheritcolor', text='Inherit Color')
            col.prop(object.auroraprops, 'rotatetexture', text='Rotate Texture')
        
            row = layout.row()
            row.prop(object.auroraprops, 'transparencyhint', text='Transparency Hint')

            # Additional props for danlymeshes
            if (object.auroraprops.meshtype == 'DANGLYMESH'):
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
                row.prop_search(object.auroraprops, 'danglegroup', context.object, 'vertex_groups')
                row = box.row()
                row.prop(object.auroraprops, 'period', text='Period')
                row = box.row()
                row.prop(object.auroraprops, 'tightness', text='Tightness')
                row = box.row()
                row.prop(object.auroraprops, 'displacement', text='Displacement')
                
            # Additional props for skins
            elif (object.auroraprops.meshtype == 'SKIN'):
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
                row.prop_search(object.auroraprops, 'new_skingroupname', context.scene, 'objects')
                row.operator('nvb.skingroup_add', text = '', icon='ZOOMIN')           
            
            # Additional props for asabb walkmeshes
            elif (object.auroraprops.meshtype == 'AABB'):
                row = layout.row()
                box = row.box()
                row = box.row()
                row.operator('nvb.load_wok_mats', text = 'Load walkmesh materials', icon='NONE')
                row = box.row()
                row.label(text = '(Warning: Removes current materials)')               

# Add to a menu
def menu_func_export(self, context):
    self.layout.operator(NVBAuroraMDLExport.bl_idname, text="Neverwinter Nights (.mdl)")


def menu_func_import(self, context):
    self.layout.operator(NVBAuroraMDLImport.bl_idname, text="Neverwinter Nights (.mdl)")


def register():
    bpy.utils.register_module(__name__)
    
    bpy.types.Object.auroraprops           = bpy.props.PointerProperty(type=NVBAuroraObjectPropertyGroup)
    bpy.types.ParticleSettings.auroraprops = bpy.props.PointerProperty(type=NVBAuroraParticlePropertyGroup)
    
    bpy.types.INFO_MT_file_import.append(menu_func_import)
    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.INFO_MT_file_export.remove(menu_func_export)   
    bpy.types.INFO_MT_file_import.remove(menu_func_import)
    
    del bpy.types.Object.auroraprops
    
    bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
    register()
