import math
import os
import itertools

import mathutils
import bpy

from . import nvb_mtr
from . import nvb_def
from . import nvb_utils
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
        self.color_list[5] = (0.0, 0.0, 0.0, 1.0)  # Illumination/Emission
        self.renderhints = set()
        self.mtr_name = None
        self.mtr = None

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
            if ( (tex_list == self.texture_list) and
                 Material.colorisclose(col_list[5], self.color_list[5]) and
                 math.isclose(alpha, self.alpha) ):
                return blen_mat
        return None

    def isdefault(self):
        """Return True if the material contains only default values"""
        d = True
        # d = d and Material.colorisclose(self.diffuse, (1.0, 1.0, 1.0))
        # d = d and Material.colorisclose(self.specular, (0.0, 0.0, 0.0))
        d = d and math.isclose(self.alpha, 1.0, abs_tol=0.03)
        d = d and self.texture_list.count(nvb_def.null) == len(self.texture_list)
        d = d and self.materialname == ''
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
            self.materialname = nvb_parse.ascii_identifier(line[1])
        elif label == 'renderhint':
            self.renderhints.add(nvb_parse.ascii_identifier(line[1]))
        elif label == 'bitmap':
            # bitmap as texture0, texture0 takes precedence
            if self.texture_list[0] is None:
                self.texture_list[0] = nvb_parse.ascii_texture(line[1])
            # bitmap as materialname, materialname takes precedence
            if self.mtr_name is None:
                self.mtr_name = nvb_parse.ascii_identifier(line[1])
        elif label.startswith('texture'):
            if label[7:]:  # 'texture' is followed by a number
                idx = int(label[7:])
                self.texture_list[idx] = nvb_parse.ascii_texture(line[1])

    def mtr_read(self, options):
        """Read the contents of the mtr file specified in the mdl file."""
        if not self.mtr and self.mtr_name:
            if self.mtr_name in options.mtrdb:
                self.mtr_data = options.mtrdb[self.mtr_name]
            else:
                mtr_filename = self.mtr_name + '.mtr'
                mtr_dir, _ = os.path.split(options.filepath)
                mtr_path = os.path.join(mtr_dir, mtr_filename)
                mtr = nvb_mtr.Mtr(self.mtr_name)
                if mtr.read_mtr(mtr_path):
                    options.mtrdb[self.mtr_name] = mtr
                    self.mtr = mtr

    def mtr_merge(self):
        """Merges the contents of the mtr file into this material."""
        # Merge values from mtr into this material
        if self.mtr:
            self.renderhints = self.renderhints.union(self.mtr.renderhints)
            # Load all existing textures from the mtr into the material
            self.texture_list = [t2 if t2 is not None else t1
                                 for t1, t2 in zip(self.texture_list,
                                                   self.mtr.texture_list)]
            # Load all existing colors from the mtr into the material
            self.color_list = [c2 if c2 is not None else c1
                               for c1, c2 in zip(self.color_list,
                                                 self.mtr.color_list)]

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
        material = obj.active_material
        if not obj.hide_render and material:
            tex_list, col_list, alpha = Materialnode.get_node_data(material)
            # Clean up texture list, delete trailing "null"
            tex_list = [t if t else nvb_def.null for t in tex_list]
            while tex_list[-1] == nvb_def.null:
                _ = tex_list.pop()
            # Write colors
            fstr = '  ambient' + 3 * ' {:3.2f}'
            ascii_lines.append(fstr.format([1.0] * 3))
            fstr = '  diffuse' + 3 * ' {:3.2f}'
            ascii_lines.append(fstr.format(*col_list[0]))
            fstr = '  specular' + 3 * ' {:3.2f}'
            ascii_lines.append(fstr.format(*col_list[2]))
            # Write textures
            if options.mtr_export:
                mtr_name = material.name
                ascii_lines.append('  ' + options.mtr_ref + ' ' + mtr_name)
                options.mtrdb.add(material.name)  # export later on demand
            else:
                # Add Renderhint
                if (tex_list and (tex_list[:3].count(nvb_def.null) <= 1)):
                    ascii_lines.append('  renderhint NormalAndSpecMapped')
                # Export texture 0 (diffuse) as "bitmap" or "texture0"
                fstr = '  ' + options.mat_diffuse_ref + ' {:s}'
                if tex_list[0]:
                    ascii_lines.append(fstr.format(tex_list[0]))
                else:
                    ascii_lines.append(fstr.format(nvb_def.null))
                # Export texture 1 (normal) and 2 (specular)
                fstr = '  texture{:d} {:s}'
                for idx, tex_name in enumerate(tex_list[1:3]):
                    if tex_name:
                        ascii_lines.append(fstr.format(idx, tex_name))
            # Write Alpha
            if not math.isclose(alpha, 1.0, rel_tol=0.01):  # Omit 1.0
                fstr = '  alpha {: 3.2f}'
                ascii_lines.append(fstr.format(alpha))
        else:
            ascii_lines.append('  ambient 1.00 1.00 1.00')
            ascii_lines.append('  diffuse 1.00 1.00 1.00')
            ascii_lines.append('  specular 0.00 0.00 0.00')
            ascii_lines.append('  bitmap ' + nvb_def.null)
