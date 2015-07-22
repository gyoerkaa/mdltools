import bpy
import os
import collections
import enum
import warnings

import neverblender.nvb.mdl
import neverblender.nvb.node
import neverblender.nvb.presets
import neverblender.nvb.walkmesh


class MalformedMdlFile(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)


class Importer():
    __debug = True
        
    def __init__(self,
                 filepath,
                 imports,
                 uniqueTexture       = False,
                 importShadingGroups = False,
                 imageSearch         = False,
                 minimapMode         = False,
                 ): 
        self.filepath = os.fsencode(filepath)
        self.filename = os.path.splitext(os.path.basename(filepath))[0]
        self.filedir  = os.path.dirname(filepath)        
        
        self.imports = imports
        self.uniqueTexture       = uniqueTexture
        self.importShadingGroups = importShadingGroups
        self.imageSearch         = imageSearch
        self.minimapMode         = minimapMode
        
        self.scene = bpy.context.scene
        
        self.mdl      = nvb.mdl.Mdl()
        
    
    
    def parseMdl():
        lines = [line.strip().split() for line in open(filepath, 'r')]
        
        nodelist = collections.OrderedDict()
        animlist = dict() # No need to retain order
        
        State = enum.Enum('State', 'HEAD MDL GEOM GEOMNODE ANIM ANIMNODE')
        cs = State.HEAD
        for line in lines:
            if (cs == State.HEAD):
                if (line[0] == 'newmodel'):
                    try:
                        self.mdl.name = line[1]
                    except IndexError:
                        warnings.warn("WARNING: Unable to read model name. Default value: " + self.mdl.name)
                    cs = State.MDL
                
            elif (cs = State.MDL):
                if (line[0] == 'beginmodelgeom'):
                    cs = State.GEOM
                elif (line[0] == 'setsupermodel'): 
                    try:
                       self.mdl.supermodel = line[1]
                    except IndexError:
                       warnings.warn("WARNING: Unable to read supermodel. Default value: " + self.mdl.supermodel)
                elif (line[0] == 'classification'):
                    try:
                        self.mdl.classification = line[1]
                    except IndexError:
                        warnings.warn("WARNING: Unable to read classification. Default value: " + self.mdl.classification)
                elif (line[0] == 'setanimationscale'):
                    try:
                        self.mdl.animScale = line[1]
                    except IndexError:
                        warnings.warn("WARNING: Unable to read animationscale. Default value: " + self.mdl.animScale)
                        
            elif cs == State.GEOM:
                if (line[0] == 'endmodelgeom'):
                    cs = State.ANIM
                elif (line[0] == 'node'):
                    cs = State.GEOMNODE
                
            elif (cs == State.GEOMNODE):   
                if (line[0] == 'endmodegeom'):
                    cs = State.ANIM
                elif (line[0] == 'endnode'):
                    cs = State.GEOM 
                    
            elif cs == State.ANIM:
                if (line[0] == 'doneanim'):
                    cs = State.ANIM            
            
        
    
    def parseGeomNode(self, geomBlock):
        if asciiNode is None:
            raise MalformedMdlFile('Empty Node')
        
        type = ''
        try:
            type = asciiNode[0][1].lower()
        except IndexError, AttributeError:
            raise MalformedMdlFile('Invalid node type')
        
        switch={'dummy':      nvb.node.Dummy, 
                'trimesh':    nvb.node.Trimesh,
                'danglymesh': nvb.node.Danglymesh,
                'skin':       nvb.node.Skinmesh,
                'emitter':    nvb.node.Emitter,
                'light':      nvb.node.Light,
                'aabb':       nvb.node.Aabb}
        try:
            node = switch[type]()
        except KeyError:
            raise MalformedMdlFile('Invalid node type')
        
        node.from_ascii(asciiNode)
        return node
        
    def parseAnim(self, animBlock):
        pass
        
            
    
        

        
        
              
        
def import_(operator,
            context,
            filepath = '',
            imports = {'GEOMETRY', 'ANIMATION', 'WALKMESH', 'EMITTER'},
            uniqueTexture       = False,
            importShadingGroups = False,
            imageSearch         = False,
            minimapMode         = False,
            ):    
    '''
    Called by the user interface or another script.
    '''       
    importer = Importer(filepath, 
                        imports, 
                        uniqueTexture, 
                        importShadingGroups,
                        imageSearch,
                        minimapMode)
    
    return {'FINISHED'}