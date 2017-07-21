#!/bin/sh

BLENDER=blender

INPUT=in
OUTPUT=out

MSIZE=32
ZOFF=10.0
LCOLOR="1.0,1.0,1.0"
IMPFADE=0

MSIZE=$(grep MINIMAP_SIZE generator.ini | cut -d= -f2)
ZOFF=$(grep Z_OFFSET generator.ini | cut -d= -f2)
LCOLOR=$(grep LIGHT_COLOR generator.ini | cut -d= -f2)
IMPFADE=$(grep IMPORT_FADING_OBJ generator.ini | cut -d= -f2)

$BLENDER -b -P generator.py -- nvb_input=$INPUT nvb_output=$OUTPUT nvb_msize=$MSIZE nvb_zoff=$ZOFF nvb_lcolor=$LCOLOR nvb_impfade=$IMPFADE
