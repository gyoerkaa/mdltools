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
            """Return a list of terrain names."""
            reg = re.compile('Name=([\w\-]+)\s?', re.IGNORECASE)
            terrains = []
            for block in ascii_block.strip().split('[TERRAIN'):
                if block:
                    match = reg.search(block)
                    if match:
                        terrains.append(match[1])
            return terrains

        def parse_crosser_names(ascii_block):
            """Return a list of crosser names."""
            reg = re.compile('Name=([\w\-]+)\s?', re.IGNORECASE)
            crossers = []
            for block in ascii_block.strip().split('[CROSSER'):
                if block:
                    match = reg.search(block)
                    if match:
                        crossers.append(match[1])
            return crossers

        def parse_tiles(ascii_block, terrain_names=[], crosser_names=[]):
            """Return two lists with tile counts for each crosser/ terrain."""
            reg_model = re.compile(r'Model=([\w\-]+)\s?', re.IGNORECASE)
            print(terrain_names)
            print(crosser_names)
            reg_terrains = [(n, re.compile('=' + n + '\s?', re.IGNORECASE))
                            for n in terrain_names]
            reg_crossers = [(n, re.compile('=' + n + '\s?', re.IGNORECASE))
                            for n in crosser_names]
            terrains = {key: 0 for key in terrain_names}
            crossers = {key: 0 for key in crosser_names}
            for block in ascii_block.strip().split('[TILE'):
                if block:
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
            """Return a list of groups and their row/ column counts."""
            reg_name = re.compile(r'Name=([\w\- ]+)\n', re.IGNORECASE)
            reg_rows = re.compile(r'Rows=(\d+)\s?', re.IGNORECASE)
            reg_cols = re.compile(r'Columns=(\d+)\s?', re.IGNORECASE)
            groups = []
            for block in ascii_block.strip().split('[GROUP'):
                if block:
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
            element.el_size = str(r)
        # Load Crossers
        while len(scene.nvb.set_crosser_list) > 0:
            scene.nvb.set_crosser_list.remove(0)
        scene.nvb.set_crosser_list_idx = 0
        for n, r in crossers:
            element = scene.nvb.set_crosser_list.add()
            element.el_name = n
            element.el_size = str(r)
        # Load Groups
        while len(scene.nvb.set_group_list) > 0:
            scene.nvb.set_group_list.remove(0)
        scene.nvb.set_group_list_idx = 0
        for n, r, c in groups:
            element = scene.nvb.set_group_list.add()
            element.el_name = n
            element.el_size = str(r) + 'x' + str(c)

    @classmethod
    def poll(self, context):
        """Enable only if there a valid file path."""
        scene = bpy.context.scene
        return (scene and scene.nvb.set_filepath)

    def execute(self, context):
        """Reload the set file."""
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

    def get_mdl_list(self, set_path, set_mode, lookup_name):

        def get_tiles(ascii_block, terrain_name=''):
            """Returns a list of tile model as list of strings."""
            reg_model = re.compile(r'Model=([\w\-]+)\s?', re.IGNORECASE)
            reg_terrain = re.compile('=' + terrain_name + '\s?', re.IGNORECASE)
            tiles = []
            for block in ascii_block.strip().split('[TILE'):
                if block:
                    model_match = reg_model.search(block)
                    if model_match:
                        if terrain_name:
                            if reg_terrain.search(block):
                                tiles.append(model_match[1])
                        else:
                            tiles.append(model_match[1])
            return tiles

        def get_group_tiles(ascii_block, group_name):
            """Returns rows, columns and a list of tile ids for the group."""
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
                            return rows, cols, tiles
            return 0, 0, []

        mdl_names = []
        rows = 1
        cols = 1
        with open(os.fsencode(set_path), 'r') as f:
            ascii_data = f.read()

            tl_start = ascii_data.find('[TILE0]')
            gp_start = ascii_data.find('[GROUP0]')

            if set_mode == 'GP':  # Get all tiles of a group
                tiles = get_tiles(ascii_data[tl_start:gp_start-1])
                rows, cols, tile_ids = get_group_tiles(ascii_data[gp_start:],
                                                       lookup_name)
                mdl_names = [tiles[i] if i >= 0 else '' for i in tile_ids]
            else:  # Get all tiles associated with a terrain or crosser
                tiles = get_tiles(ascii_data[tl_start:gp_start-1], lookup_name)
                mdl_names = [t for t in tiles]
                rows = len(mdl_names)
        return rows, cols, mdl_names

    def mass_load_mdl(self, mdl_dir, mdl_list, row_cnt, col_cnt):
        """Import all mdl in list."""
        def get_location(idx, row_cnt, col_cnt):
            """Generate a location for the tile from its row and column."""
            row = idx % row_cnt
            col = idx % col_cnt
            return (10.0 * col, 10.0 * row, 0.0)

        for i, mdl_name in enumerate(mdl_list):
            if mdl_name:  # '' == don't import
                filename = mdl_name + '.mdl'
                mdl_loc = get_location(i, row_cnt, col_cnt)
                filepath = os.path.join(mdl_dir, filename)
                if os.path.isfile(os.fsencode(filepath)):
                    bpy.ops.nvb.mdlimport(filepath=filepath,
                                          import_walkmesh=True,
                                          import_smoothgroups=True,
                                          import_normals=True,
                                          mat_import=True,
                                          mat_automerge=True,
                                          mtr_import=True,
                                          tex_search=False,
                                          anim_import=True,
                                          anim_fps_use=False,
                                          anim_fps=30,
                                          anim_restpose=True,
                                          rotmode='XYZ',
                                          mdl_location=mdl_loc)
                else:
                    self.report({'INFO'}, filename + ' not found')

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
        if not os.path.isfile(os.fsencode(set_path)):
            self.report({'ERROR'}, 'Error: Unable to open file.')
            return {'CANCELLED'}

        if set_mode == 'GP':  # Groups
            itm = scene.nvb.set_group_list[scene.nvb.set_group_list_idx]
        elif set_mode == 'TR':  # Terrain
            itm = scene.nvb.set_terrain_list[scene.nvb.set_terrain_list_idx]
        elif set_mode == 'CR':  # Crosser
            itm = scene.nvb.set_crosser_list[scene.nvb.set_crosser_list_idx]

        rows, cols, mdl_list = \
            self.get_mdl_list(set_path, set_mode, itm.el_name)
        self.mass_load_mdl(os.path.dirname(set_path), mdl_list, rows, cols)
        return {'FINISHED'}
