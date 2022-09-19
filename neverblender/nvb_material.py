import math
import os

import bpy

from . import nvb_mtr
from . import nvb_def
from . import nvb_parse
from . import nvb_utils
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
        self.color_list[0] = (0.8, 0.8, 0.8, 1.0)  # Default diffuse color
        self.color_list[2] = (0.0, 0.0, 0.0, 1.0)  # Default specular color/value
        self.color_list[3] = (1.0, )  # Default roughness value (overridden by texture)
        self.color_list[4] = (0.0, )  # Default displacement offset
        self.color_list[5] = (0.0, 0.0, 0.0, 1.0)  # Default Illumination/Emission color
        self.renderhints = set()
        self.mtr_name = None
        self.mtr_data = None
        self.bitmap = None  # Only used for naming, textures are in texture_list

    @staticmethod
    def colorisclose(a, b, tol=0.05):
        return ((a is None) and (b is None)) or \
               (a and b and (sum([math.isclose(v[0], v[1]) for v in zip(a, b)]) == len(a)))

    def generate_material_name(self):
        """Generates a material name for use in blender."""
        # 'materialname' over 'texture0'/'bitmap' over Default
        if self.mtr_name:
            mat_name = self.mtr_name
        elif self.bitmap:
            mat_name = self.bitmap
        elif (self.texture_list[0]) and \
                (self.texture_list[0] is not nvb_def.null):
            mat_name = self.texture_list[0].lower()
        else:
            mat_name = ""  # Blender will a default name
        return mat_name

    def find_blender_material(self, options):
        """Finds a material in blender with the same settings as this one."""
        def check_colors(color_list1, color_list2, ambient1=None, ambient2=None):
            # Always check selfillumination
            same_colors = Material.colorisclose(color_list1[5], color_list2[5])
            if not options.mat_ignore_mdl_diffuse_color:
                same_colors = same_colors and Material.colorisclose(color_list1[0], color_list2[0])
            if not options.mat_ignore_mdl_ambient_color:
                same_colors = same_colors and Material.colorisclose(ambient1, ambient2)
            return same_colors

        def check_textures(texture_list1, texture_list2, ignore_case=True):
            """Check if the texture lists match."""
            if ignore_case:
                return ([t1.lower() if t1 else None for t1 in texture_list1] == [t2.lower() if t2 else None for t2 in texture_list2])
            else:
                return (texture_list1 == texture_list2)

        def check_shaders(blen_material, mtr_data):
            """Check if the shader from an MTR file match the ones in the blender material."""
            shader1_vs = ""
            shader1_fs = ""
            if blen_material:
                shader1_vs = blen_mat.nvb.mtr.shader_vs
                shader1_fs = blen_mat.nvb.mtr.shader_fs
            # MTR file may be undefined
            shader2_vs = ""
            shader2_fs = ""
            if mtr_data:
                shader2_vs = mtr_data.customshaderVS
                shader2_fs = mtr_data.customshaderFS
            return (shader1_vs == shader2_vs) and (shader1_fs == shader2_fs)

        #print("####################")
        #print("looking for: ")
        #print(self.texture_list)
        #print(self.color_list)
        #print(self.alpha)
        for blen_mat in bpy.data.materials:
            if not blen_mat.name.startswith("wok_"):
                #print("#")
                #print("Checking: " + blen_mat.name)
                tex_list, col_list, alpha, ambient = Materialnode.get_node_data(blen_mat)
                #print(tex_list)
                #print(col_list)
                #print(alpha)
            # Compare textures, colors and alpha
            if (check_textures(tex_list[:5], self.texture_list[:5], True) and
                check_colors(col_list, self.color_list, ambient, self.ambient) and
                check_shaders(blen_mat, self.mtr_data) and
                math.isclose(alpha, self.alpha)):
                #print("MATCH!")
                return blen_mat
        return None

    def isdefault(self):
        """Return True if the material contains only default values"""
        d = True
        d = d and math.isclose(self.alpha, 1.0, abs_tol=0.03)
        d = d and (self.texture_list.count(nvb_def.null) ==
                   len(self.texture_list))
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
            self.color_list[5] = nvb_parse.ascii_color(line[1:])
        elif label == 'alpha':
            self.alpha = nvb_parse.ascii_float(line[1])
        elif label == 'materialname':
            self.mtr_name = nvb_parse.ascii_identifier(line[1])
        elif label == 'renderhint':
            self.renderhints.add(nvb_parse.ascii_identifier(line[1]))
        elif label == 'bitmap':
            self.bitmap = nvb_parse.ascii_texture(line[1])
            if self.texture_list[0] == None:
                self.texture_list[0] = self.bitmap
        elif label.startswith('texture'):
            if label[7:]:  # 'texture' is followed by a number
                idx = int(label[7:])
                self.texture_list[idx] = nvb_parse.ascii_texture(line[1])

    def mtr_read(self, options):
        """Read the contents of the mtr file specified in the mdl file."""
        def get_mtr_path(mtr_name, mtr_dir):
            mtr_filename = mtr_name + '.mtr'
            mtr_dir, _ = os.path.split(mtr_dir)
            return nvb_utils.find_file_nocase(mtr_dir, mtr_filename)

        # if an mtr_name has been specified try opening it
        # but don't do anything else!
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
        # Try opening "bitmap"
        elif self.bitmap:
            if self.bitmap in options.mtrdb:
                self.mtr_data = options.mtrdb[self.bitmap]
            else:
                mtr_path = get_mtr_path(self.bitmap, options.filepath)
                if os.path.isfile(mtr_path):
                    # bitmap is an mtr file
                    mtr = nvb_mtr.Mtr(self.bitmap)
                    if mtr.read_mtr(mtr_path):
                        options.mtrdb[self.bitmap] = mtr
                        self.mtr_data = mtr
                else:
                    # bitmap is not an mtr file
                    pass

    def mtr_merge(self):
        """Merges the contents of the mtr file into this material."""
        # Merge values from mtr into this material
        if self.mtr_data:
            self.renderhints.update(self.mtr_data.renderhints)
            # Load all existing textures from the mtr into the material
            self.texture_list = \
                [t2 if t2 else t1 for t1, t2 in
                 zip(self.texture_list, self.mtr_data.texture_list)]
            # Load all existing colors from the mtr into the material
            # self.color_list = \
            #     [c2 if c2 else c1 for c1, c2 in
            #      zip(self.color_list, self.mtr_data.color_list)]

    def create_blender_material(self, options, always_create_new=True):
        """Returns a blender material with the stored values."""
        # Ignore ambient color parameter (ignored with the new PBR shaders in the EE)
        if options.mat_ignore_mdl_ambient_color:
            self.ambient = None
        # Ignore diffuse color parameter (will be multiplied with diffuse texture)
        if options.mat_ignore_mdl_diffuse_color:
            self.color_list[0] = None
        # Ignore specular color parameter (This is always ignored by the engine)
        if options.mat_ignore_mdl_specular_color:
            self.color_list[2] = None
        # Load mtr values into this material
        # This will override values from mdl, even the ones previously ignored (from the mdl)
        if options.mat_use_mtr:
            self.mtr_read(options)
            self.mtr_merge()
        # Sometimes, we don't want self illumination at all (e.g. interfering with rendering minimaps)
        if options.mat_ignore_selfillum_color:
            self.color_list[5] = (0.0, 0.0, 0.0, 1.0)
        if options.mat_ignore_selfillum_texture:
             self.texture_list[5] = None
        # Look for similar materials to avoid duplicates
        blender_mat = None
        if options.mat_automerge and not always_create_new:
            blender_mat = self.find_blender_material(options)
        # Create new material if necessary
        if not blender_mat:
            new_name = self.generate_material_name()
            blender_mat = bpy.data.materials.new(new_name)
            blender_mat.blend_method = 'HASHED'  # 'BLEND' doesn't play nice
            blender_mat.show_transparent_back = False
            blender_mat.use_backface_culling = True

            blender_mat.nvb.mtr.use = bool(self.mtr_name) or self.mtr_data is not None
            if blender_mat.nvb.mtr.use:
                blender_mat.nvb.mtr.renderhint = next(iter(self.mtr_data.renderhints or []), "")
                blender_mat.nvb.mtr.shader_vs = self.mtr_data.customshaderVS
                blender_mat.nvb.mtr.shader_gs = self.mtr_data.customshaderGS
                blender_mat.nvb.mtr.shader_fs = self.mtr_data.customshaderFS
            blender_mat.use_nodes = True
            blender_mat.node_tree.nodes.clear()
            Materialnode.add_node_data(blender_mat, new_name,
                                       self.texture_list, self.color_list, self.alpha, self.ambient,
                                       options)
        return blender_mat

    @staticmethod
    def generate_ascii(obj, ascii_lines, options):
        """Write Ascii lines from the objects material for a MDL file."""
        blen_material = obj.active_material

        # Format string for colors
        fstr_col = '  {:s}' + 3 * ' {:3.2f}'
        # Format string for first texture, depending on user preferences it
        # is either 'bitmap' or 'texture0'
        fstr_tex0 = '  ' + options.mat_diffuse_ref + ' {:s}'
        if obj.nvb.render and blen_material:
            tex_list, col_list, alpha, ambient = Materialnode.get_node_data(blen_material)

            # Clean up texture list, delete trailing "null"
            tex_list = [t if t else nvb_def.null for t in tex_list]
            while tex_list and tex_list[-1] == nvb_def.null:
                _ = tex_list.pop()
            # Clean up color list
            default_colors = [[1.0]*4] + [[0.0] * 4] * 14
            col_list = [c1[:3] if c1 else c2[:3] for c1, c2 in
                        zip(col_list, default_colors)]
            # Write colors
            if ambient:
                ascii_lines.append(fstr_col.format('ambient', *ambient[:3]))
            else:
                ascii_lines.append(fstr_col.format('ambient', *[1.0] * 3))
            if col_list[0]:
                ascii_lines.append(fstr_col.format('diffuse', *col_list[0][:3]))
            else:
                ascii_lines.append(fstr_col.format('diffuse', *[1.0] * 3))
            if col_list[2]:
                ascii_lines.append(fstr_col.format('specular', *col_list[2][:3]))
            else:
                ascii_lines.append(fstr_col.format('specular', *[0.0] * 3))
            if col_list[5]:
                ascii_lines.append(fstr_col.format('selfillumcolor', *col_list[5][:3]))
            # Write Alpha
            if alpha and not math.isclose(alpha, 1.0, rel_tol=0.01):  # Omit 1.0
                fstr = '  alpha {: 3.2f}'
                ascii_lines.append(fstr.format(alpha))
            # Write textures
            if blen_material.nvb.mtr.use:
                # MTRs are exported in a second pass
                mtr_name = nvb_mtr.Mtr.get_mtr_name(blen_material)
                ascii_lines.append('  ' + options.mat_mtr_ref + ' ' + mtr_name)
                # AddOn options specify whether to actually write material data to mtr file
                if options.mat_mtr_generate:
                    options.mtr_list.add((mtr_name, blen_material.name))
            else:
                # Write to MDL: Can only export the first three textures
                # Also fix texture name to ascii
                tex_list = [nvb_utils.generate_mdl_identifier(t) for t in tex_list[:3]]
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
