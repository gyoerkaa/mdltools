# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
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


bl_info = {
    "name": "Neverblender",
    "author": "Attila Gyoerkoes",
    "blender": (2, 6, 0),
    "location": "File > Import-Export, Object Properties",
    "description": "Import, export and edit aurora mdl format",
    "warning": "",
    "wiki_url": ""
                "",
    "tracker_url": "",
    "category": "Import-Export"}


if "bpy" in locals():
    import imp
    imp.reload(neverblender.nvb.props)
    imp.reload(neverblender.nvb.ops)
    imp.reload(neverblender.nvb.panels)    
    imp.reload(nvb_importmdl)
    imp.reload(nvb_exportmdl)
else:

    import neverblender.nvb.props
    import neverblender.nvb.ops
    import neverblender.nvb.panels
    from . import nvb_importmdl
    from . import nvb_exportmdl  

import bpy
import bpy_extras
"""
import xml.etree.ElementTree
import os
import re  
"""

class NVBAuroraMDLImport(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    '''Import from Neverwinter Nights file format (.mdl)'''
    
    bl_idname  = 'nvb.importmdl'
    bl_label   = 'Import Aurora MDL'
    bl_options = {'UNDO'}
    
    filename_ext = '.mdl'
    filter_glob = bpy.props.StringProperty(
            default = '*.mdl', 
            options = {'HIDDEN'},
            )
           
    import_items = bpy.props.EnumProperty(
            name = 'Import',
            options = {'ENUM_FLAG'},
            items = (('GEOMETRY', 'Geometry', ''),
                     ('ANIMATIONS', 'Animations', ''),
                     ),
            default = {'GEOMETRY', 'ANIMATIONS'},
            )
    
    import_walkmesh = bpy.props.BoolProperty(
            name='Import walkmesh',
            description='Import walkmesh, if applicable' \
                        '(.pwk, .dwk or .mdl depending on classification)',
            default=True,
            ) 
    
    import_shading_groups = bpy.props.BoolProperty(
            name='Import Shading Groups',
            description='Import shading groups as vertex groups ' \
                        '(Unused by blender)',
            default=False,
            )
    
    use_image_search = bpy.props.BoolProperty(
            name='Image Search',
            description='Search subdirectories for any associated images ' \
                        '(Warning, may be slow)',
            default=False,
            )
            
    one_texture_per_image = bpy.props.BoolProperty(
            name='One Texture per Image',
            description='Create only one texture per Image' \
                        '(Will result in one texture for every node)',
            default=True,
            )
            
    # Hidden option, only used for minimap creation
    import_lights = bpy.props.BoolProperty(
            name='Import Light',
            description='Wether to import lights' \
                        '(Useful for rendering minmaps)',
            default=True,
            options={'HIDDEN'},
            )
            
    # Hidden option, only used for minimap creation        
    import_fading_obj = bpy.props.BoolProperty(
            name='Import Fading Objects',
            description='Wether to import objects with' \
                        'activated tilefade' \
                        '(Useful for rendering minmaps)',
            default=True,
            options={'HIDDEN'},
            )
            
    def execute(self, context):
        from . import nvb_importmdl
        
        keywords = self.as_keywords(ignore=('filter_glob',
                                            'check_existing',
                                            ))
        
        return nvb_importmdl.load(self, context, **keywords)


class NVBAuroraMDLExport(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    '''Export to Neverwinter Nights file format (.mdl)'''
    bl_idname = 'nvb.exportmdl'
    bl_label  = 'Export Aurora MDL'
    
    filename_ext = '.mdl'
    filter_glob = bpy.props.StringProperty(
            default='*.mdl',
            options={'HIDDEN'},
            )
    
    export_selection = bpy.props.EnumProperty(
            name='Export',
            items=(('ALL', 'All', ''),
                   ('SELECTION', 'Selection only', ''),
                   ('LAYER','Active layers', ''),
                   ),
            default='ALL',
            )
    
    export_walkmesh = bpy.props.BoolProperty(
            name='Export walkmesh',
            description='Export walkmesh, if applicable' \
                        '(.pwk, .dwk or .wok depending on classification)',
            default=True,
            )
    
    export_shading_groups = bpy.props.BoolProperty(
            name='Export Shading groups',
            description='Export Shading Groups' \
                        '(When disabled, every face belongs to the same group)',
            default=False,
            )
            
    apply_modifiers = bpy.props.BoolProperty(
            name='Apply Modifiers',
            description='Apply Modifiers before exporting.' \
                        '(When disabled, every face belongs to the same group)',
            default=True,
            )            
            
    def execute(self, context):
        from . import nvb_exportmdl

        keywords = self.as_keywords(ignore=('filter_glob',
                                            'check_existing',
                                            ))
        
        return nvb_exportmdl.save(self, context, **keywords)


def menu_func_export(self, context):
    self.layout.operator(NVBAuroraMDLExport.bl_idname, text="Aurora MDL (.mdl)")


def menu_func_import(self, context):
    self.layout.operator(NVBAuroraMDLImport.bl_idname, text="Aurora MDL (.mdl)")

"""    
def xmlTest():
    scriptDir = os.path.dirname(__file__)
    xmlFile = r"nvb/material_wok.xml"
    tree = xml.etree.ElementTree.parse(os.path.join(scriptDir, xmlFile))
    root = tree.getroot()
    for child in root:
        print(child.find('name').text)
        color = child.find('diffuse').get('color')
        print([float(x.group()) for x in re.finditer('\d.\d', color)])
"""
        
def register():
    bpy.utils.register_module(__name__)
    
    bpy.types.Object.auroraprops           = bpy.props.PointerProperty(type=nvb.props.ObjectPropertyGroup)
    bpy.types.ParticleSettings.auroraprops = bpy.props.PointerProperty(type=nvb.props.ParticlePropertyGroup)
    
    bpy.types.INFO_MT_file_import.append(menu_func_import)
    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.INFO_MT_file_export.remove(menu_func_export)   
    bpy.types.INFO_MT_file_import.remove(menu_func_import)
    
    del bpy.types.ParticleSettings.auroraprops
    del bpy.types.Object.auroraprops
      
    bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
    register()
