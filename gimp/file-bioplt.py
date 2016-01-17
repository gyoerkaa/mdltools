# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
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


'''
Short plt File documentation:

P  L  T     V  1
50 4C 54 20 56 31 20 20
Random ? But this 8 byte always work
0A 00 00 00 00 00 00 00
width
00 00 00 00
height
00 00 00 00
The rest is data
AA 00 BB 01 ..., with AA 00 = (value, layer), BB 01 = (value, layer)
'''


import os
import struct

from gimpfu import *


# Don't change order, keep everything lowercase
plt_layernames   = ['skin', 'hair', 'metal1', 'metal2', 'cloth1', 'cloth2', \
                    'leather1', 'leather2', 'tattoo1', 'tattoo2']


def plt_load(filename, raw_filename):
    f = open(filename, 'rb')

    # First 16 bytes contain header
    header = struct.unpack('<16s', f.read(16))
    if header[0][0:7] == 'PLT V1  ':
        gimp.pdb.gimp_message('Not a valid plt file' + header[0][0:8])
        return 1
    num_layers = 10
    # Next 8 bytes contain width and height
    (width, height) = struct.unpack('<II', f.read(8))
    # The rest contains (color, layer) tuples (both unsigned char (?))
    raw = f.read()
    f.close()
    data = struct.unpack(str(len(raw))+'B', raw)
    px   = [list(t) for t in zip(*2*[iter(data)])]

    # Create a new image
    img          = gimp.Image(width, height, GRAY)
    img.filename = os.path.split(filename)[1]
    img.disable_undo()

    # Create Layers
    layerlist = []
    for pos, layername in enumerate(plt_layernames):
        lay = gimp.Layer(img, layername, width, height, GRAYA_IMAGE, 100, NORMAL_MODE)
        lay.fill(TRANSPARENT_FILL)
        img.insert_layer(layer = lay, position = pos)
        layerlist.append(lay)

    # Write data to layers
    numvals = len(px)
    gimp.progress_init("Progress ...")
    gimp.progress_update(0)

    # for speed
    l_int   = int
    l_float = float
    l_floor = math.floor

    for i, (value, layer_idx) in enumerate(px):
        x = l_int(i % width)
        y = height - l_int(l_floor(i / width)) - 1
        layerlist[layer_idx].set_pixel(x, y, [value, 255])
        gimp.progress_update(l_float(i)/l_float(numvals))

    img.enable_undo()
    return img


def plt_save(img, drawable, filename, raw_filename):
    pltfile = open(filename, 'wb')

    width  = img.width
    height = img.height

    pltdata = struct.pack('<8s', 'PLT V1  ')
    pltfile.write(pltdata)
    pltdata = struct.pack('<II', 10, 0)
    pltfile.write(pltdata)
    pltdata = struct.pack('<II', width, height)
    pltfile.write(pltdata)

    # Grab the top 10 layers and interpret them as
    # ['Skin', 'Hair', 'Metal1', 'Metal2', 'Cloth1', 'Cloth2', 'Leather1',
    #  'Leather2', 'Tattoo1', 'Tattoo2']
    data = []
    gimp.progress_init("Reading pixels from Gimp layers")
    gimp.progress_update(0)
    numpx = width * height

    # for speed
    l_int   = int
    l_float = float
    l_floor = math.floor

    if img.base_type == GRAY:
        for i in range(numpx):
            x = l_int(i % width)
            y = height - l_int(l_floor(i / width)) - 1
            layer = img.pick_correlate_layer(x, y)
            if layer >= 0:
                data.append(layer.get_pixel(x,y)[0])
                data.append(plt_layernames.index(layer.name.lower()))

            else:
                data.append(255)
                data.append(0)
            gimp.progress_update(l_float(i)/l_float(numpx))

    elif img.base_type == RGB:
        for i in range(numpx):
            x = l_int(i % width)
            y = height - l_int(l_floor(i / width)) - 1
            layer = img.pick_correlate_layer(x, y)
            if layer >= 0:
                data.append((layer.get_pixel(x,y)[0] + layer.get_pixel(x,y)[1] + layer.get_pixel(x,y)[2]) / 3)
                data.append(plt_layernames.index(layer.name.lower()))
            else:
                data.append(255)
                data.append(0)
            gimp.progress_update(l_float(i)/l_float(numpx))

    else: # Indexed, do nothing
        pltfile.close()
        return

    pltdata = struct.pack('<' + str(numpx*2) + 'B', *data)
    pltfile.write(pltdata)
    pltfile.close()


def plt_create_layers(img):
    layer_type = GRAYA_IMAGE
    if img.base_type == RGB:
        layer_type = RGBA_IMAGE
    elif img.base_type == INDEXED:
        layer_type = INDEXEDA_IMAGE
    # We don't want to create already existing plt layers

    # Get all layers from the current image
    img_layernames = []
    for layer in img.layers:
        img_layernames.append(layer.name.lower())

    for pos, layername in enumerate(plt_layernames):
        if layername not in img_layernames:
            lay = gimp.Layer(img, layername, img.width, img.height, layer_type, 100, NORMAL_MODE)
            lay.fill(TRANSPARENT_FILL)
            img.insert_layer(layer = lay, position = pos)


def register_load_handlers():
    gimp.register_load_handler('file-bioplt-load', 'plt', '')
    pdb['gimp-register-file-handler-mime']('file-bioplt-load', 'image/plt')
    # Too slow for python
    #pdb['gimp-register-thumbnail-loader']('file-bioplt-load', 'file-bioplt-load-thumb')


def register_save_handlers():
    gimp.register_save_handler('file-bioplt-save', 'plt', '')
    pdb['gimp-register-file-handler-mime']('file-bioplt-save', 'image/plt')


register(
    'file-bioplt-load', #name
    'load a Bioware Packed Layer Texture (.plt)', #description
    'load a Bioware Packed Layer Texture (.plt)',
    'Symmetric', #author
    'GPL v3', #copyright
    '2015', #year
    'Bioware Packed Layer Texture',
    None, #image type
    [   #input args (type, name, description, default [, extra])
        (PF_STRING, 'filename', 'The name of the file to load', None),
        (PF_STRING, 'raw_filename', 'The name entered', None),
    ],
    [(PF_IMAGE, 'image', 'Output image')], #results (type, name, description)
    plt_load, #callback
    on_query = register_load_handlers,
    menu = "<Load>",
)


register(
    'file-bioplt-save', #name
    'save a Bioware Packed Layer Texture (.plt)', #description
    'save a Bioware Packed Layer Texture (.plt)',
    'Symmetric', #author
    'GPL v3', #copyright
    '2015', #year
    'Bioware Packed Layer Texture',
    '*',
    [   #input args (type, name, description, default [, extra])
        (PF_IMAGE, "image", "Input image", None),
        (PF_DRAWABLE, "drawable", "Input drawable", None),
        (PF_STRING, "filename", "The name of the file", None),
        (PF_STRING, "raw-filename", "The name of the file", None),
    ],
    [], #results (type, name, description)
    plt_save, #callback
    on_query = register_save_handlers,
    menu = '<Save>'
)


register(
    'file-bioplt-createlayers', #name
    'Create Bioware Packed Layer Texture (.plt)', #description
    'Create the layers for a Bioware Packed Layer Texture (.plt)',
    'Symmetric', #author
    'GPL v3', #copyright
    '2015', #year
    'Plt: Create Layers',
    '*',
    [   #input args (type, name, description, default [, extra])
        (PF_IMAGE, "image", "Input image", None)
    ],
    [], #results (type, name, description)
    plt_create_layers, #callback
    #on_query = register_save_handlers,
    menu = '<Image>/Tools'
)


main()
