import os
import sys
import re

import bpy
import bgl
import blf

import neverblender


# Settings from ini file:
minimap_size = 32
z_offset     = 10.0
light_color  = (1.0, 1.0, 1.0)
skip_fading  = False
input_path   = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'in')
output_path  = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'out')


# Some globals
emtpy_filename = 'empty.blend'
empty_path     = os.path.join(os.path.dirname(__file__), emtpy_filename)
logfile_name   = 'log.txt'
logfile        = None


def log(message):
    '''
    Writes messages to logfile and the console
    '''
    print(message)
    try:
        logfile.write(message + '\n')
    except:
        pass


def load_settings():
    '''
    Loads settings from command line arguments
    '''
    log('##### Options #####')

    for arg in sys.argv:
        words=arg.split('=')
        if (words[0] == 'nvb_msize'):
            try:
                minimap_size = int(words[1])
            except:
                log('WARNING: Could not read MINIMAP_SIZE. Using Default value.')

        if (words[0] == 'nvb_zoff'):
            try:
                z_offset = float(words[1])
            except:
                log('WARNING: Could not read Z_OFFSET. Using Default value.')

        elif (words[0] == 'nvb_impfade'):
            try:
                skip_fading = (int(words[1]) < 1)
            except:
                log('WARNING: Could not read IMPORT_FADING_OBJ. Using Default value.')

        elif (words[0] == 'nvb_lcolor'):
            cval_string = words[1].split(',')
            try:
                cval = [float(cval_string[0]),
                        float(cval_string[1]),
                        float(cval_string[2]) ]
            except:
                log('WARNING: Could not read LIGHT_COLOR. Using Default value.')

            # Make sure the light colors are in [0.0,1.0]
            for i in range(3):
                if cval[i] < 0.0:
                    cval[i] = 0.0
                elif cval[i] > 1.0:
                    cval[i] = 1.0
            light_color = tuple(cval)

        elif (words[0] == 'nvb_input'):
            input_path = words[1]

        elif (words[0] == 'nvb_output'):
            output_path = words[1]

    log('Minimap Size: ' + str(minimap_size))
    log('Z-Offset: ' + str(z_offset))
    if skip_fading:
        log('Fading Objects: Ignore')
    else:
        log('Fading Objects:  Import')
    log('Light color: (' + str(cval[0]) + ', ' + str(cval[1]) + ', ' + str(cval[2]) + ')')
    log('Input path:  ' + input_path)
    log('Output path: ' + output_path)


def process_files():
    '''
    If a set tile was found parse it an process mdls accordingly
    If no set file is present just process all mdl in the input dir
    '''
    log('##### Processing #####')

    found_set = False
    for filename in os.listdir(input_path):
        if filename.endswith('.set'):
            found_set = True
            process_set(filename)

    if not found_set:
        process_all()


def process_set(setfile_name):

    log('Processing set file: ' + setfile_name)
    tiles  = []
    groups = []

    filepath = os.fsencode(os.path.join(input_path, setfile_name))
    with open(filepath, 'r') as fp:
        contents = fp.read()

    tiles_start  = contents.find('[TILES]')
    groups_start = contents.find('[GROUPS]')

    tiles_block  = contents[tiles_start:groups_start-1].strip().split()
    for b in tiles_block:
        b.strip().slpit()

    groups_block = contents[groups_start:].strip().split()
    for g in groups_block:
        g.strip().slpit()


def process_all():
    '''
    Processes all mdl files in the input directory
    '''
    # Load an empty file
    try:
        bpy.ops.wm.open_mainfile(filepath = empty_path,
                                 load_ui = False)
    except:
        log('ERROR: Unable to load empty.blend')
        return

    for filename in os.listdir(input_path):
        if filename.endswith('.mdl'):
            log('Processing ' + filename)

            # Import mdl file
            mdlfile = os.fsencode(os.path.join(input_path, filename))
            try:
                bpy.ops.nvb.mdlimport(filepath = mdlfile,
                                      importGeometry = True,
                                      importWalkmesh = False,
                                      importSmoothGroups = False,
                                      importAnim = False,
                                      materialMode = 'MUL',
                                      textureSearch = False,
                                      minimapMode = True,
                                      minimapSkipFade = skip_fading)
            except RuntimeError as ex:
                error_report = '\n'.join(ex.args)
                print('    ERROR: ', error_report)

            # Get mdl root
            mdlRoot = None
            for obj in bpy.data.objects:
                if neverblender.nvb.nvb_utils.isRootDummy(obj, neverblender.nvb.nvb_def.Dummytype.MDLROOT):
                    mdlRoot = obj
                    break

            # Render minimap
            if mdlRoot:
                filename = 'mi_' + mdlRoot.name
                scene    = bpy.context.scene
                scene.render.filepath = os.fsencode(os.path.join(output_path, filename))
                mdlRoot.nvb.minimapsize    = minimap_size
                mdlRoot.nvb.minimapzoffset = z_offset
                neverblender.nvb.nvb_utils.setupMinimapRender(mdlRoot, scene, light_color, 'SKY')
                bpy.ops.render.render(write_still = True)
                log('   DONE: Exported to ' + filename)
            else:
                log('   ERROR: No rootdummy')

            # Load empty blend for next mdl file
            bpy.ops.wm.open_mainfile(filepath = empty_path,
                                     load_ui = False)


logfile = open(os.fsencode(logfile_name), 'w')
load_settings()
process_all()
logfile.close()
