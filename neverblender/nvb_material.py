import math
import os

import bpy

from . import nvb_mtr
from . import nvb_def
from . import nvb_parse
from .nvb_materialnode import Materialnode


class Material(object):
    """A material read from an mdl node."""

    def __init__(self, name='unnamed'):
        """TODO: DOC."""
        self.name = name
        self.ambient = (1.0, 1.0, 1.0, 1.0)
        self.alpha = 1.0
        self.texture_list = [None] * 15
        self.color_list = [(1.0, 1.0, 1.0, 1.0)] * 15
        self.color_list[2] = (0.0, 0.0, 0.0, 1.0)  # Specular
        self.color_list[3] = (0.2, )  # Roughness
        self.color_list[5] = (0.0, 0.0, 0.0, 1.0)  # Illumination/Emission
        self.renderhints = set()
        self.mtr_name = None
        self.mtr_data = None

    @staticmethod
    def colorisclose(a, b, tol=0.05):
        return (sum([math.isclose(v[0], v[1]) for v in zip(a, b)]) == len(a))

    def generate_material_name(self):
        """Generates a material name for use in blender."""

        # 'materialname' over 'texture0'/'bitmap' over Default
        if self.mtr_name:
            mat_name = self.mtr_name
        elif (self.texture_list[0]) and \
                (self.texture_list[0] is not nvb_def.null):
            mat_name = self.texture_list[0].lower()
        else:
            mat_name = ""  # Blender will a default name
        return mat_name

    def find_blender_material(self, options):
        """Finds a material in blender with the same settings as this one."""
        for blen_mat in bpy.data.materials:
            tex_list, col_list, alpha = Materialnode.get_node_data(blen_mat)
            # Compare textures, emissive color(5) and alpha
            if (tex_list == self.texture_list) and \
               Material.colorisclose(col_list[5], self.color_list[5]) and \
               math.isclose(alpha, self.alpha):
                return blen_mat
        return None

    def isdefault(self):
        """Return True if the material contains only default values"""
        d = True
        # d = d and Material.colorisclose(self.diffuse, (1.0, 1.0, 1.0))
        # d = d and Material.colorisclose(self.specular, (0.0, 0.0, 0.0))
        d = d and math.isclose(self.alpha, 1.0, abs_tol=0.03)
        d = d and self.texture_list.count(nvb_def.null) == len(self.texture_list)
        d = d and self.mtr_name == ''
        return d

    def parse_ascii_line(self, line):
        """TODO: Doc."""
        label = line[0].lower()
        if label == 'ambient':
            self.ambient = nvb_parse.ascii_color(line[1:])
        elif label == 'diffuse':
            self.color_list[0] = nvb_parse.ascii_color(line[1:])
        elif label == 'specular':
            self.color_list[2] = nvb_parse.ascii_color(line[1:])
        elif label in ['selfillumcolor', 'setfillumcolor']:
            self.color_list[4] = nvb_parse.ascii_color(line[1:])
        elif label == 'alpha':
            self.alpha = nvb_parse.ascii_float(line[1])
        elif label == 'materialname':
            self.mtr_name = nvb_parse.ascii_identifier(line[1])
        elif label == 'renderhint':
            self.renderhints.add(nvb_parse.ascii_identifier(line[1]))
        elif label == 'bitmap':
            # bitmap as texture0, texture0 takes precedence
            if self.texture_list[0] is None:
                self.texture_list[0] = nvb_parse.ascii_texture(line[1])
        elif label.startswith('texture'):
            if label[7:]:  # 'texture' is followed by a number
                idx = int(label[7:])
                self.texture_list[idx] = nvb_parse.ascii_texture(line[1])

    def mtr_read(self, options):
        """Read the contents of the mtr file specified in the mdl file."""
        def get_mtr_path(mtr_name, mtr_dir):
            mtr_filename = mtr_name + '.mtr'
            mtr_dir, _ = os.path.split(mtr_dir)
            return os.path.join(mtr_dir, mtr_filename)

        # if an mtr_name has been specified try opening it
        # but nothing else!
        if self.mtr_name:
            if self.mtr_name in options.mtrdb:
                self.mtr_data = options.mtrdb[self.mtr_name]
            else:
                mtr_path = get_mtr_path(self.mtr_name, options.filepath)
                if os.path.isfile(mtr_path):
                    mtr = nvb_mtr.Mtr(self.mtr_name)
                    if mtr.read_mtr(mtr_path):
                        options.mtrdb[self.mtr_name] = mtr
                        self.mtr_data = mtr
        # Try opening "bitmap" = "texture0"
        elif self.texture_list[0]:
            if self.texture_list[0] in options.mtrdb:
                self.mtr_data = options.mtrdb[self.texture_list[0]]
            else:
                mtr_path = get_mtr_path(self.texture_list[0], options.filepath)
                if os.path.isfile(mtr_path):
                    mtr = nvb_mtr.Mtr(self.texture_list[0])
                    if mtr.read_mtr(mtr_path):
                        options.mtrdb[self.texture_list[0]] = mtr
                        self.mtr_data = mtr

    def mtr_merge(self):
        """Merges the contents of the mtr file into this material."""
        # Merge values from mtr into this material
        if self.mtr_data:
            self.renderhints = self.renderhints.union(self.mtr_data.renderhints)
            # Load all existing textures from the mtr into the material
            self.texture_list = \
                [t2 if t2 else t1 for t1, t2 in
                 zip(self.texture_list, self.mtr_data.texture_list)]
            # Load all existing colors from the mtr into the material
            # self.color_list = \
            #     [c2 if c2 else c1 for c1, c2 in
            #      zip(self.color_list, self.mtr_data.color_list)]

    def create_blender_material(self, options, reuse_existing=True):
        """Returns a blender material with the stored values."""
        # Load mtr values into this material
        if options.mtr_import:
            self.mtr_read(options)
            self.mtr_merge()
        # Look for similar materials to avoid duplicates
        blender_mat = None
        if reuse_existing:
            blender_mat = self.find_blender_material(options)
        # Create new material if necessary
        if not blender_mat:
            new_name = self.generate_material_name()
            blender_mat = bpy.data.materials.new(new_name)
            blender_mat.blend_method = 'BLEND'
            blender_mat.show_transparent_back = False

            blender_mat.nvb.use_mtr = bool(self.mtr_name) or \
                self.mtr_data is not None

            blender_mat.use_nodes = True
            blender_mat.node_tree.nodes.clear()
            Materialnode.add_node_data(
                blender_mat, options.mat_shader,
                self.texture_list, self.color_list, self.alpha,
                options.filepath, options.tex_search)
        return blender_mat

    @staticmethod
    def generate_ascii(obj, ascii_lines, options):
        """Write Ascii lines from the objects material for a MDL file."""
        blen_material = obj.active_material

        fstr_col = '  {:s}' + 3 * ' {:3.2f}'
        fstr_tex0 = '  ' + options.mat_diffuse_ref + ' {:s}'
        if obj.nvb.render and blen_material:
            tex_list, col_list, alpha = \
                Materialnode.get_node_data(blen_material)
            # Clean up texture list, delete trailing "null"
            tex_list = [t if t else nvb_def.null for t in tex_list]
            while tex_list and tex_list[-1] == nvb_def.null:
                _ = tex_list.pop()
            # Clean up color list
            default_colors = [[1.0]*4] + [[0.0] * 4] * 14
            col_list = [c1[:3] if c1 else c2[:3] for c1, c2 in
                        zip(col_list, default_colors)]
            # Write colors
            ascii_lines.append(fstr_col.format('ambient', *[1.0] * 3))
            ascii_lines.append(fstr_col.format('diffuse', *col_list[0]))
            ascii_lines.append(fstr_col.format('specular', *col_list[2]))
            ascii_lines.append(fstr_col.format('selfillumcolor', *col_list[5]))
            # Write Alpha
            if not math.isclose(alpha, 1.0, rel_tol=0.01):  # Omit 1.0
                fstr = '  alpha {: 3.2f}'
                ascii_lines.append(fstr.format(alpha))
            # Write textures
            if options.export_mtr and blen_material.nvb.use_mtr:
                # MTRs are exported in a second pass
                mtr_name = nvb_mtr.Mtr.get_mtr_name(blen_material)
                ascii_lines.append('  ' + options.mtr_ref + ' ' + mtr_name)
                options.mtr_list.add((mtr_name, blen_material.name))
            else:
                # Write to MDL: Can only export the first three textures
                tex_list = tex_list[:3]
                # Add Renderhint if normal or specular texture is present
                if (tex_list[1:].count(nvb_def.null) < len(tex_list[1:])):
                    ascii_lines.append('  renderhint NormalAndSpecMapped')
                # Export textures
                fstr_list = [fstr_tex0, '  texture1 {:s}', '  texture2 {:s}']
                for i, tex in enumerate(tex_list):
                    ascii_lines.append(fstr_list[i].format(tex))

        else:
            ascii_lines.append(fstr_col.format('ambient', *[1.0] * 3))
            ascii_lines.append(fstr_col.format('diffuse', *[1.0] * 3))
            ascii_lines.append(fstr_col.format('specular', *[0.0] * 3))
            ascii_lines.append(fstr_tex0.format(nvb_def.null))
