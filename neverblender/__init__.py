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
    "blender": (2, 7, 0),
    "location": "File > Import-Export, Object Properties",
    "description": "Import, export and edit Aurora mdl format",
    "warning": "",
    "wiki_url": ""
                "",
    "tracker_url": "",
    "category": "Import-Export"}


if 'bpy' in locals():
    import imp
    imp.reload(neverblender.nvb.props)
    imp.reload(neverblender.nvb.ops)
    imp.reload(neverblender.nvb.panels)
else:
    import neverblender.nvb.props
    import neverblender.nvb.ops
    import neverblender.nvb.panels

import bpy
import bpy_extras
"""
import xml.etree.ElementTree
import os
import re  
"""

class NVBAuroraMDLImport(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    '''Import Aurora Engine model (.mdl)'''
    
    bl_idname  = 'nvb.importmdl'
    bl_label   = 'Import Aurora MDL'
    bl_options = {'UNDO'}
    
    filename_ext = '.mdl'
    filter_glob = bpy.props.StringProperty(
            default = '*.mdl', 
            options = {'HIDDEN'},
            )
           
    imports = bpy.props.EnumProperty(
            name = 'Import',
            options = {'ENUM_FLAG'},
            items = (('GEOMETRY', 'Geometry', 'Import dummys and meshes'),
                     ('ANIMATION', 'Animations', 'Import animations'),
                     ('WALKMESH', 'Walkmesh', 'Import walkmeshes'),
                     ('LIGHT', 'Light', 'Import lights'),
                     ('EMITTER', 'Emitter', 'Import emitters'),
                     ),
            default = {'GEOMETRY', 'ANIMATION', 'WALKMESH', 'LIGHT', 'EMITTER'},
            )

    shadingGroups = bpy.props.BoolProperty(
            name = 'Import shading groups',
            description = 'Import shading groups as vertex groups ' \
                          '(Unused by blender)',
            default = True,
            )
           
    uniqueTexture = bpy.props.BoolProperty(
            name = 'One texture per image',
            description = 'Create only one texture for each image',
            default = True,
            )
    
    imageSearch = bpy.props.BoolProperty(
            name='Image search',
            description='Search for images in subdirectories' \
                        '(Warning, may be slow)',
            default=False,
            )
            
    # Hidden option, only used for minimap creation        
    minimapMode = bpy.props.BoolProperty(
            name = 'Minimap Mode',
            description = 'Ignore lights and fading objects',
            default = False,
            options = {'HIDDEN'},
            )
            
    def execute(self, context):
        import neverblender.nvb.importer
        
        keywords = self.as_keywords(ignore=('filter_glob',
                                            'check_existing',
                                            ))
        
        return nvb.importer.import_(self, context, **keywords)


class NVBAuroraMDLExport(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    '''Export Aurora Engine model (.mdl)'''

    bl_idname = 'nvb.exportmdl'
    bl_label  = 'Export Aurora MDL'
    
    filename_ext = '.mdl'
    filter_glob = bpy.props.StringProperty(
            default = '*.mdl',
            options = {'HIDDEN'},
            )
    
    selection = bpy.props.EnumProperty(
            name = 'Export',
            items = (('ALL', 'All', ''),
                     ('SELECTION', 'Selection only', ''),
                     ('LAYER','Active layers', ''),
                    ),
            default = 'ALL',
            )
            
    shadingGroups = bpy.props.BoolProperty(
            name='Export Shading groups',
            description='Export Shading Groups' \
                        '(When disabled, every face belongs to the same group)',
            default=True,
            )
                
    createWalkmesh = bpy.props.BoolProperty(
            name='Create walkmesh',
            description='Create walkmesh, if applicable' \
                        '(.pwk, .dwk or .wok depending on classification)',
            default=True,
            )
           
    applyModifiers = bpy.props.BoolProperty(
            name='Apply Modifiers',
            description='Apply Modifiers before exporting.' \
                        '(When disabled, every face belongs to the same group)',
            default=True,
            )            
            
    def execute(self, context):
        import neverblender.nvb.exporter

        keywords = self.as_keywords(ignore=('filter_glob',
                                            'check_existing',
                                            ))
        
        return nvb.exporter.export_(self, context, **keywords)


def menu_func_export(self, context):
    self.layout.operator(NVBAuroraMDLExport.bl_idname, text="Aurora (.mdl)")


def menu_func_import(self, context):
    self.layout.operator(NVBAuroraMDLImport.bl_idname, text="Aurora (.mdl)")

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
