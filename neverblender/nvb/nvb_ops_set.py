"""Contains Blender Operators for manipulating SET files and properties."""

import os
import re

import bpy


class NVB_OT_set_open(bpy.types.Operator):
    """Open material file"""
    bl_idname = "nvb.set_open"
    bl_label = "Open SET"

    filename_ext = '.set'
    filter_glob = bpy.props.StringProperty(default='*.set', options={'HIDDEN'})
    filepath = bpy.props.StringProperty(subtype='FILE_PATH')

    @classmethod
    def poll(self, context):
        """Always enabled."""
        return bpy.context.scene is not None

    def execute(self, context):
        # Use the reload ops to actually do the loading
        bpy.context.scene.nvb.set_filepath = self.filepath
        return bpy.ops.nvb.set_reload()
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)

        return {'RUNNING_MODAL'}


class NVB_OT_set_reload(bpy.types.Operator):
    """Reload MTR, update current material"""
    bl_idname = "nvb.set_reload"
    bl_label = "Reload SET"

    def load_set(self, ascii_data):
        """Reload set file from disk."""
        def parse_terrain_names(ascii_block):
            reg = re.compile('Name=([\w\-]+)\s?', re.IGNORECASE)
            terrains = []
            for block in ascii_block.strip().split('[CROSSER'):
                if not block:
                    continue
                match = reg.search(block)
                if match:
                    terrain_name = match[1]
                    terrains.append(terrain_name)  # list_idx = terrain_id
            return terrains

        def parse_crosser_names(ascii_block):
            reg = re.compile('Name=([\w\-]+)\s?', re.IGNORECASE)
            crossers = []
            for block in ascii_block.strip().split('[TERRAIN'):
                if not block:
                    continue
                match = reg.search(block)
                if match:
                    crosser_name = match[1]
                    crossers.append(crosser_name)  # list_idx = crosser_id
            return crossers

        def parse_tiles(ascii_block, terrain_names=[], crosser_names=[]):
            reg_model = re.compile(r'Model=([\w\-]+)\s?', re.IGNORECASE)
            reg_terrains = [(n, re.compile('=' + n + '\s?'))
                            for n in terrain_names]
            reg_crossers = [(n, re.compile('=' + n + '\s?'))
                            for n in crosser_names]
            terrains = {key: 0 for key in terrain_names}
            crossers = {key: 0 for key in crosser_names}
            for block in ascii_block.strip().split('[TILE'):
                if not block:
                    continue
                model_match = reg_model.search(block)
                if model_match:
                    for trn_name, reg in reg_terrains:
                        if reg.search(block):
                            terrains[trn_name] += 1
                    for crs_name, reg in reg_crossers:
                        if reg.search(block):
                            crossers[crs_name] += 1
            return list(terrains.items()), list(crossers.items())

        def parse_groups(ascii_block):
            reg_name = re.compile(r'Name=([\w\- ]+)\n', re.IGNORECASE)
            reg_rows = re.compile(r'Rows=(\d+)\s?', re.IGNORECASE)
            reg_cols = re.compile(r'Columns=(\d+)\s?', re.IGNORECASE)
            groups = []
            for block in ascii_block.strip().split('[GROUP'):
                if not block:
                    continue
                match = reg_name.search(block)
                if match:
                    group_name = match[1]
                    rows = int(reg_rows.search(block)[1])
                    cols = int(reg_cols.search(block)[1])
                    # Add to group list, list_idx = actual group_id
                    groups.append([group_name, rows, cols])
            return groups

        tr_start = ascii_data.find('[TERRAIN0]')
        cr_start = ascii_data.find('[CROSSER0]')
        tl_start = ascii_data.find('[TILE0]')
        gp_start = ascii_data.find('[GROUP0]')

        terrain_names = parse_terrain_names(ascii_data[tr_start:cr_start-1])
        crosser_names = parse_crosser_names(ascii_data[cr_start:tl_start-1])

        terrains, crossers = parse_tiles(ascii_data[tl_start:gp_start-1],
                                         terrain_names, crosser_names)
        groups = parse_groups(ascii_data[gp_start:])

        scene = bpy.context.scene
        # Load Terrains
        while len(scene.nvb.set_terrain_list) > 0:
            scene.nvb.set_terrain_list.remove(0)
        scene.nvb.set_terrain_list_idx = 0
        for n, r in terrains:
            element = scene.nvb.set_terrain_list.add()
            element.el_name = n
            element.rows = r
        # Load Crossers
        while len(scene.nvb.set_crosser_list) > 0:
            scene.nvb.set_crosser_list.remove(0)
        scene.nvb.set_crosser_list_idx = 0
        for n, r in crossers:
            element = scene.nvb.set_crosser_list.add()
            element.el_name = n
            element.rows = r
        # Load Groups
        while len(scene.nvb.set_group_list) > 0:
            scene.nvb.set_group_list.remove(0)
        scene.nvb.set_group_list_idx = 0
        for n, r, c in groups:
            element = scene.nvb.set_group_list.add()
            element.el_name = n
            element.rows = r
            element.cols = c

    @classmethod
    def poll(self, context):
        """Enable only  if mtrs are used."""
        scene = bpy.context.scene
        return (scene and scene.nvb.set_filepath)

    def execute(self, context):
        """TODO: DOC."""
        scene = bpy.context.scene
        set_path = scene.nvb.set_filepath
        set_dir, set_filename = os.path.split(set_path)
        with open(os.fsencode(set_path), 'r') as f:
            self.load_set(f.read())
        return {'FINISHED'}


class NVB_OT_set_massimport(bpy.types.Operator):
    """Mass import specified MDLs based on set file"""

    bl_idname = 'nvb.set_massimport'
    bl_label = 'Mass import selected mdl from set'

    def load_mdl_from_set(self, ascii_data, terrain_name='', group_name=''):
        """Reload set file from disk."""
        def get_tiles(ascii_block, terrain_name=''):
            reg_model = re.compile(r'Model=([\w\-]+)\s?', re.IGNORECASE)
            reg_terrain = re.compile('=' + terrain_name + '\s?')
            tiles = []
            for block in ascii_block.strip().split('[TILE'):
                if not block:
                    continue
                model_match = reg_model.search(block)
                if model_match:
                    if terrain_name:
                        if reg_terrain.search(block):
                            tiles.append(model_match[1])  # list_idx = tile_id
                    else:
                        tiles.append(model_match[1])  # list_idx = tile_id
                else:
                    tiles.append('')
            return tiles

        def get_group(ascii_block, group_name):
            if group_name:
                reg_name = re.compile('Name=' + group_name + '\s?',
                                      re.IGNORECASE)
                reg_rows = re.compile(r'Rows=(\d+)\s?', re.IGNORECASE)
                reg_cols = re.compile(r'Columns=(\d+)\s?', re.IGNORECASE)
                reg_tiles = re.compile(r'tile(\d+)=(\d+)\s?', re.IGNORECASE)
                for block in ascii_block.strip().split('[GROUP'):
                    if block:
                        name_match = reg_name.search(block)
                        if name_match:
                            rows = int(reg_rows.search(block)[1])
                            cols = int(reg_cols.search(block)[1])
                            tiles = [-1] * rows * cols
                            for tile_match in reg_tiles.finditer(block):
                                tiles[int(tile_match[1])] = int(tile_match[2])
                            return tiles
            return []

        tl_start = ascii_data.find('[TILE0]')
        gp_start = ascii_data.find('[GROUP0]')

        mdl_names = []
        if group_name:
            tiles = get_tiles(ascii_data[tl_start:gp_start-1])
            group_tiles = get_group(ascii_data[gp_start:], group_name)
            mdl_names = [tiles[t] for t in group_tiles]
        else:
            tiles = get_tiles(ascii_data[tl_start:gp_start-1], terrain_name)
            mdl_names = [t for t in tiles]
        return mdl_names

    def get_mdl_list(self, itm_name, itm_size, set_mode, set_path):
        mdl_names = []
        with open(os.fsencode(set_path), 'r') as f:
            ascii_data = f.read()
            if set_mode == 'GP':
                mdl_names = self.load_mdl_from_set(ascii_data, '', itm_name)
            else:
                mdl_names = self.load_mdl_from_set(ascii_data, itm_name)
        mdl_paths = []
        return mdl_paths

    @classmethod
    def poll(self, context):
        """Enable only if there is a material."""
        scene = context.scene
        return scene and scene.nvb.set_filepath

    def execute(self, context):
        """TODO: DOC."""
        scene = context.scene

        set_mode = scene.nvb.set_mode
        set_path = scene.nvb.set_filepath

        if set_mode == 'GP':  # Groups
            itm = scene.nvb.set_group_list[scene.nvb.set_group_list_idx]
        elif set_mode == 'TR':  # Terrain
            itm = scene.nvb.set_terrain_list[scene.nvb.set_terrain_list_idx]
        elif set_mode == 'CR':  # Crosser
            itm = scene.nvb.set_crosser_list[scene.nvb.set_crosser_list_idx]
        itm_name = itm.el_name
        itm_size = (itm.rows, itm.cols)

        mdl_paths = self.get_mdl_list(itm_name, itm_size, set_mode, set_path)

        set_dir, set_filename = os.path.split(set_path)
        for path in mdl_paths:
            pass
        return {'FINISHED'}
