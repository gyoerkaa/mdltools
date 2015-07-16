import neverblender.nvb.node
import neverblender.nvb.presets
import neverblender.nvb.walkmesh


class MalformedMdlFile(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)


def openAsciiMdlFile(filepath = '')
    lines = []
    try:
        lines = [line.strip().split() for line in open(filepath, 'r')]
    except IOError:
        print('ERROR: Could not open file ' + str(filepath))

    return lines

    
def parseAsciiMdl(filepath = ''):
    
    lines = getAsciiLines(filepath)
    
            


def import_(operator,
            context,
            filepath = '',
            import_items = {'GEOMETRY', 'ANIMATION', 'WALKMESH', 'LIGHT', 'EMITTER'},
            import_shading_groups = False,
            use_image_search = False,
            one_texture_per_image = True,
            one_mesh_per_object = True,
            import_lights = True,
            import_fading_obj = True,
         ):    
    '''
    Called by the user interface or another script.
    '''
    
    global glob_mdl_filepath
    global glob_mdl_filename
    global glob_mdl_filedir
    global glob_import_items
    global glob_glob_mdl_filename
    global glob_import_shading_groups
    global glob_use_image_search
    global glob_import_scene
    global glob_one_tex_per_image
    global glob_one_mesh_per_obj
    global glob_import_lights
    global glob_import_fading_obj
    
    glob_mdl_filepath          = os.fsencode(filepath)
    glob_mdl_filename          = os.path.splitext(os.path.basename(filepath))[0]
    glob_mdl_filedir           = os.path.dirname(filepath)
    glob_import_items          = import_items
    glob_import_shading_groups = import_shading_groups
    glob_use_image_search      = use_image_search
    glob_one_tex_per_image     = one_texture_per_image
    glob_one_mesh_per_obj      = one_mesh_per_object
    glob_import_lights         = import_lights
    glob_import_fading_obj     = import_fading_obj
    
    glob_import_scene = bpy.context.scene
    
    load_mdl()
    
    return {'FINISHED'}