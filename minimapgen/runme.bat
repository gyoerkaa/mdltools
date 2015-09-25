@ECHO off 
:: This batch file reads parameters from generator.ini 
:: and starts blender with the generator.py script
:: (and the passes the parameters)
:: Read from generator.ini
FOR /f "tokens=1,2 delims==" %%a IN (generator.ini) DO (
IF %%a==BLENDER SET BLENDER_EXE=%%b
IF %%a==MINIMAP_SIZE SET MSIZE=%%b
IF %%a==Z_OFFSET SET ZOFF=%%b
IF %%a==LIGHT_COLOR SET LCOLOR=%%b
IF %%a==IMPORT_LIGHTS SET IMPLIGHT=%%b
IF %%a==IMPORT_FADING_OBJ SET IMPFADE=%%b
)
:: Set input/output path
SET INPUT=%~dp0%in
SET OUTPUT=%~dp0%out
:: Start blender with the generator script and values from generator.ini
%BLENDER_EXE% -b -P generator.py -- nvb_input=%INPUT% nvb_output=%OUTPUT% nvb_msize=%MSIZE% nvb_zoff=%ZOFF% nvb_lcolor=%LCOLOR% nvb_implight=%IMPLIGHT% nvb_impfade=%IMPFADE%
