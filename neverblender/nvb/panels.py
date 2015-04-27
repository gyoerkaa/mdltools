import bpy


class NVBAuroraPropertyPanelParticleSystem(bpy.types.Panel):
    ''' 
    Property panel for additional properties needed for the mdl file
    format. This is only available for particle systems.
    It is located under the particle panel in the properties window 
    '''    
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
            
            row = layout.row()
            row.prop(partsys_settings.auroraprops, 'opacity')
            
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
            
            # Chunk
            row = layout.row()
            box = row.box()
            box.label(text='Chunk')             
            row = box.row()
            row.prop(partsys_settings.auroraprops, 'chunkname', text = 'Name')
            
            layout.separator()
            
            # Particle properties
            row = layout.row()
            box = row.box()            
            box.label(text='Animation: ')            
            split = box.split()
            col = split.column(align=True)
            col.prop(partsys_settings.auroraprops, 'colorstart', text='')
            col.prop(partsys_settings.auroraprops, 'colorend', text='')
            
            col = split.column(align=True)
            col.prop(partsys_settings.auroraprops, 'alphastart')
            col.prop(partsys_settings.auroraprops, 'alphaend')

            split = box.split()
            col = split.column(align=True)
            col.prop(partsys_settings.auroraprops, 'sizestart')
            col.prop(partsys_settings.auroraprops, 'sizeend')
            
            col = split.column(align=True)
            col.prop(partsys_settings.auroraprops, 'sizestart_y')
            col.prop(partsys_settings.auroraprops, 'sizeend_y')
  
            layout.separator()
            
            # Blast props
            row = layout.row()
            box = row.box()
            box.label(text='Blast properties: ')
            row =  box.row()
            row.prop(partsys_settings.auroraprops, 'blastradius')
            row =  box.row()
            row.prop(partsys_settings.auroraprops, 'blastlength')
            
            layout.separator()
            
            # Misc props
            row = layout.row()
            box = row.box()            
            box.label(text='Misc. properties: ')                     
            row = box.row()
            row.prop(partsys_settings.auroraprops, 'spread')
            row = box.row()
            row.prop(partsys_settings.auroraprops, 'particlerot')
            row = box.row()
            row.prop(partsys_settings.auroraprops, 'blurlength')
            row = box.row()
            row.prop(partsys_settings.auroraprops, 'deadspace')
            row = box.row()
            row.prop(partsys_settings.auroraprops, 'renderorder')
            row = box.row()
            row.prop(partsys_settings.auroraprops, 'fps')            
            split = box.split()
            col = split.column()
            col.prop(partsys_settings.auroraprops, 'istinted')
            col.prop(partsys_settings.auroraprops, 'twosidedtex')
            col = split.column()
            col.prop(partsys_settings.auroraprops, 'splat')
            col.prop(partsys_settings.auroraprops, 'loop')
            col.prop(partsys_settings.auroraprops, 'random')
            
            layout.separator()
            
            # Inheritance
            row = layout.row()
            box = row.box()
            box.label(text = 'Inheritance: ')
            row = box.row()
            row.prop(partsys_settings.auroraprops, 'inherit')
            row = box.row()
            row.prop(partsys_settings.auroraprops, 'inherit_vel') 
            row = box.row()
            row.prop(partsys_settings.auroraprops, 'inherit_local')
            row = box.row()
            row.prop(partsys_settings.auroraprops, 'inherit_part')
            
            layout.separator()
            
            # p2p settings
            row = layout.row()
            box = row.box()  
            box.label(text='p2p Settings')            
            row = box.row()           
            row.prop(partsys_settings.auroraprops, 'p2p')
            row = box.row()
            row.prop(partsys_settings.auroraprops, 'p2p_type') 
            row = box.row()
            row.prop(partsys_settings.auroraprops, 'p2p_bezier2')
            row = box.row()
            row.prop(partsys_settings.auroraprops, 'p2p_bezier3')           
            row = box.row()
            row.prop(partsys_settings.auroraprops, 'threshold')
            row = box.row()
            row.prop(partsys_settings.auroraprops, 'combinetime')
    
            layout.separator()
            
            # Lightning
            row = layout.row()
            box = row.box()            
            box.label(text='Lightning: ')            
            row = box.row()            
            row.prop(partsys_settings.auroraprops, 'lightningdelay')
            row = box.row()  
            row.prop(partsys_settings.auroraprops, 'lightningradius') 
            row = box.row()  
            row.prop(partsys_settings.auroraprops, 'lightningsubdiv')
            row = box.row()  
            row.prop(partsys_settings.auroraprops, 'lightningscale')
            
            layout.separator()
            
            # Bounce
            row = layout.row()
            box = row.box()
            box.label(text = 'Bounce: ')            
            factor_but(box, partsys_settings.auroraprops, 'bounce', 'bounce_co', 'Coeff.')


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
                row.operator('nvb.render_minimap', text = 'Setup Render', icon='NONE')
                
            elif (object.auroraprops.dummytype in {'PWKBASE', 'DWKBASE'}):
                pass
            
            else:
                row = layout.row()
                row.prop(object.auroraprops, 'wirecolor', text = 'Wirecolor')            


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
        object      = context.object        
        object_type = object.type
        
        layout = self.layout
        
        row = layout.row()    
        row.prop(object.auroraprops, 'meshtype', text='Type')
        
        if (object.auroraprops.meshtype == 'EMITTER'):
            row = layout.row()
            row.prop(object.auroraprops, 'wirecolor', text='Wirecolor')
            
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
            
            # Additional props for aabb walkmeshes
            elif (object.auroraprops.meshtype == 'AABB'):
                row = layout.row()
                box = row.box()
                row = box.row()
                row.operator('nvb.load_wok_mats', text = 'Load walkmesh materials', icon='NONE')
                row = box.row()
                row.label(text = '(Warning: Removes current materials)')              