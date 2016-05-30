import os
import sys

import bpy
import bgl
import blf

import neverblender

# Globals
minimap_size   = 32
z_offset       = 10.0
input_path     = 'in'
output_path    = 'out'
emtpy_filename = 'empty.blend'
empty_path     = os.path.join(os.path.dirname(__file__), emtpy_filename)
light_color    = (1.0, 1.0, 1.0)
fading_obj_imp = True
alpha_mode     = 'SKY'

def processfile(filepath):
    '''
    Process a single mdl file:
     - Set up cameras & lights
     - Render minimap
    '''
    # Import mdl file
    bpy.ops.nvb.mdlimport(filepath = mdlfile, 
                          importGeometry = True, 
                          importWalkmesh = False,
                          importSmoothGroups = False,
                          importAnim = 'NON',
                          importSupermodel = False,
                          materialMode = 'SIN',
                          textureSearch = False,
                          minimapMode = True)

    # Get mdl root
    mdlRoot = None
    for obj in bpy.data.objects:
        if nvb_utils.isRootDummy(obj, nvb_def.Dummytype.MDLROOT):
            mdlRoot = obj
            break

    # Render minimap
    if mdlRoot:
        filename = 'mi_' + mdlRoot.name
        scene    = bpy.context.scene
        scene.render.filepath = os.fsencode(os.path.join(output_path, filename))
        mdlRoot.nvb.minimapsize    = minimap_size
        mdlRoot.nvb.minimapzoffset = z_offset
        neverblender.nvb_utils.setupMinimapRender(mdlRoot, scene, light_color, alpha_mode)
        bpy.ops.render.render(write_still=True)
    else:
        print('NEVERBLENDER - ERROR: No rootdummy')


for arg in sys.argv:
    words=arg.split('=')
    if (words[0] == 'nvb_msize'):
        try:
            minimap_size = int(words[1])
        except:
            print('ERROR: Could not read MINIMAP_SIZE from generator.ini')
            minimap_size = 32
    if (words[0] == 'nvb_zoff'):
        try:
            z_offset = float(words[1])
        except:
            print('ERROR: Could not read Z_OFFSET from generator.ini')
            z_offset = 0.0
    elif (words[0] == 'nvb_input'):
        input_path = words[1]
    elif (words[0] == 'nvb_output'):
        output_path = words[1]
    elif (words[0] == 'nvb_impfade'):
        try:
            fading_obj_imp = (int(words[1]) >= 1)
        except:
            print('ERROR: Could not read IMPORT_FADING_OBJ from generator.ini')
            fading_obj_imp = True
    elif (words[0] == 'nvb_lcolor'):
        print(words[1])
        cval_string = words[1].split(',')
        try:
            cval_list = [ float(cval_string[0]),
                          float(cval_string[1]),
                          float(cval_string[2]) ]
        except:
            print('ERROR: Could not read LIGHT_COLOR from generator.ini')
            cval_list = [1.0,1.0,1.0]
        # Make sure the light colors are in [0.0,1.0]
        for idx, cval in enumerate(cval_list):
            if cval < 0.0:
                cval_list[idx] = 0.0
            elif cval > 1.0:
                cval_list[idx] = 1.0
        light_color = tuple(cval_list)


# Get all mdl files in the input directory
for filename in os.listdir(input_path):
    if filename.endswith('.mdl'):
        mdlfile = os.fsencode(os.path.join(input_path, filename))
        print('Processing ' + filename)
        # Load an empty file
        bpy.ops.wm.open_mainfile(filepath=empty_path)
        processfile(mdlfile)
