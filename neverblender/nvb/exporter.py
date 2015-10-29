class Exporter():
    __debug = True

    def __init__(self,
                 exports,
                 selection = {'ALL'},
                 shadingGroups,
                 createWalkmesh,
                 applyModifiers):
        self.imports = imports
        self.shadingGroups  = shadingGroups
        self.createWalkmesh = createWalkmesh
        self.minimapMode    = minimapMode

        self.scene = bpy.context.scene
        self.mdl   = nvb.mdl.Mdl()

    def save(self, filepath):
        self.filepath = os.fsencode(filepath)
        self.filename = os.path.splitext(os.path.basename(filepath))[0]
        self.filedir  = os.path.dirname(filepath)
        
        
def export_(operator,
            context,
            filepath = '',
            selection = {'ALL'},
            shadingGroups  = True,
            createWalkmesh = True,
            applyModifiers = True):
    '''
    Called from blender ui
    '''
    exporter = Exporter(exports,
                        selection = {'ALL'},
                        shadingGroups,
                        createWalkmesh,
                        applyModifiers)
    exporter.save(filepath)

    return {'FINISHED'}
