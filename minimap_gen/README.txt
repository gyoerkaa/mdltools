################
# Requirements #
################
To use the minimap generator you need a blender installation with activated 
Neverblender add-on.


#########
# Setup #
#########
Before using the generator, you'll need to open the "generator.ini" and 
change the path to your blender executable:
[PATH]
BLENDER="C:\Program Files (x86)\Blender Foundation\Blender\blender.exe"


#########
# USAGE #
#########
Place the mdl files and textures in the "in" folder. After running "runme.bat", 
the generated minimaps will be saved in the 'out' folder. 
IMPORTANT: The textures need to be in tga format.

You can change the size of the generated minimaps by editing 
the "generator.ini":
[MINIMAP]
MINIMAP_SIZE=32

You may also need to set an z offset in the "generator.ini", 
in case your tileset contains very high buildings or is not 
at 0.0 level:
[MINIMAP]
Z_OFFSET=5.0

A single light source will be placed above the center of the tile. 
You can change the color of this light. The color has to be 
given in RGB format (values ranging from 0.0 to 1.0), separated by
colons (without whitespaces)
[MINIMAP]
LIGHT_COLOR=1.0,1.0,1.0

Whether to import the light sources from the models. It is not recommended
to do so. The color of the light sources may affect the render result, 
while in-game their color depends on the settings made by the builder.
1 = Light source will be imported
0 = No import (recommended)
[MINIMAP]
IMPORT_LIGHTS=0
