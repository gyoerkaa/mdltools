"""TODO: DOC."""

import os

from . import nvb_utils
from . import nvb_def
from . import nvb_parse
from .nvb_materialnode import Materialnode


class Mtr(object):
    """A material read from an mtr file."""
    def __init__(self, name='unnamed'):
        """TODO: DOC."""
        self.name = name

        self.filepath = ''

        self.texture_list = [None] * 15
        self.color_list = [None] * 15
        self.renderhints = set()
        self.parameters = dict()
        self.alpha = None
        self.metallicness = None
        self.customVS = ''  # Vertex shader
        self.customGS = ''  # Geometry shader
        self.customFS = ''  # Fragment shader

    @staticmethod
    def parse_ascii_param_value(str_values):
        """Parses parameter values from list of strings."""
        values = []
        for sv in str_values:
            if not nvb_utils.isNumber(sv):
                break
            values.append(float(sv))
        return values

    @staticmethod
    def get_mtr_name(blen_material, from_out_node=False, strip_trailing=False):
        """Parses parameter values from list of strings."""
        mtr_name = ""
        if from_out_node:  # Read from output node first
            out_node = Materialnode.get_output_node(blen_material)
            mtr_name = Materialnode.get_node_identifier(out_node, False)
        if not mtr_name:  # Read from material name if no output node
            mtr_name = blen_material.name
        if strip_trailing:  # Strip trailing numbers
            mtr_name = nvb_utils.strip_trailing_numbers(mtr_name)
        return mtr_name

    @staticmethod
    def get_mtr_params(blen_material):
        """Parses parameter values from list of strings."""
        param_list = []
        for pa in blen_material.nvb.mtr.param_list:
            if pa.pname.lower() not in param_list:  # Keep unique
                param_name = pa.pname.lower()
                param_type = pa.ptype
                param_values = [float(v) for v in pa.pvalue.strip().split()]
                param = (param_name, param_type, param_values)
                param_list.append(param)
        return param_list

    def read_mtr(self, filepath):
        """Load contents of a mtr file."""
        if not filepath:
            return False

        self.filepath = filepath
        # Generate a name, strip file extension
        self.name = os.path.splitext(os.path.basename(filepath))[0]
        try:
            mtrFile = open(os.fsencode(filepath), 'r')
        except IOError:
            return False
        ascii_data = mtrFile.read()
        self.parse_ascii(ascii_data)
        mtrFile.close()
        return True

    def parse_ascii(self, ascii_data):
        """Parse the whole mtr file."""
        ascii_lines = [l.strip().split() for l in ascii_data.splitlines()]
        for line in ascii_lines:
            self.parse_ascii_line(line)

    def parse_ascii_line(self, line):
        """Parse a single line from the ascii mtr file."""
        label = ''
        try:
            label = line[0].lower()
        except (IndexError, AttributeError):
            return  # Probably empty line or comment
        if label == 'renderhint':
            self.renderhints.add(nvb_utils.str2identifier(line[1]))
        elif label == 'parameter':
            try:
                param_type = line[1].lower()
                param_name = line[2]
                param_value = line[3:7]
            except IndexError:
                return
            else:
                param_value = Mtr.parse_ascii_param_value(param_value)
                # Try to extract some know parameters for the standard shader
                if param_name.lower() == "specularity":
                    self.color_list[2] = [nvb_parse.ascii_float(param_value[0])]*3
                elif param_name.lower() == "roughness":
                    self.color_list[3] = nvb_parse.ascii_float(param_value[0])
                elif param_name.lower() == "displacementoffset":
                    self.color_list[4] = nvb_parse.ascii_float(param_value[0])                   
                else:  # Unknown parameter
                    self.parameters[param_name] = (param_type, param_value)
        elif label == 'customshadervs':
            self.customshaderVS = line[1]
        elif label == 'customshaderfs':
            self.customshaderFS = line[1]
        elif label == 'customshadergs':
            self.customshaderGS = line[1]
        elif label.startswith('texture'):
            if label[7:]:  # 'texture' is followed by a number
                idx = int(label[7:])
                self.texture_list[idx] = nvb_parse.ascii_texture(line[1])

    @staticmethod
    def generate_ascii(blen_material, options):
        """Generate a mtr file as asciilines."""
        ascii_lines = []
        tex_list, col_list, _, _ = Materialnode.get_node_data(blen_material)
        # Clean up texture list, delete trailing "null"
        tex_list = [t if t else nvb_def.null for t in tex_list]
        while tex_list and tex_list[-1] == nvb_def.null:
            _ = tex_list.pop()
        # Add shader specification
        if blen_material.nvb.mtr.shader_vs or blen_material.nvb.mtr.shader_fs:
            # Custom Shaders
            ascii_lines.append("// Shaders")
            if blen_material.nvb.shadervs:
                ascii_lines.append("customshaderVS " + blen_material.nvb.mtr.shader_vs)
            if blen_material.nvb.shaderfs:
                ascii_lines.append("customshaderFS " + blen_material.nvb.mtr.shader_fs)
            if blen_material.nvb.shadergs:
                ascii_lines.append("customshaderGS " + blen_material.nvb.mtr.shader_gs)                
            ascii_lines.append("")
        elif tex_list and (tex_list[:3].count(nvb_def.null) <= 1):
            # Add Renderhint
            ascii_lines.append("// Renderhint")
            ascii_lines.append("renderhint " + blen_material.nvb.mtr.renderhint)
            ascii_lines.append("")
        # Add list of textures
        if len(tex_list) > 0:
            ascii_lines.append("// Textures")
            fstr = 'texture{:d} {:s}'
            ascii_lines.extend([fstr.format(i, t)
                                for i, t in enumerate(tex_list)])
            ascii_lines.append("")
        # Add parameters
        # Convert blender param list to dict
        param_dict = dict()
        for param in blen_material.nvb.mtr.param_list:
            param_name = param.pname
            param_type = param.ptype
            param_values = Mtr.parse_ascii_param_value(param.pvalue.strip().split())
            param_id = param_name.lower()
            param_dict[param_id] = [param_name, param_type, param_values]
        # Manually add known paramters from Blenders shader node tree (overwrite manually added ones)
        if col_list[2] and (col_list[2][0] > 0.00001):
            param_dict['specularity'] = ['Specularity', 'float', [str(col_list[2][0])]]        
        if col_list[3] and (col_list[3][0] > 0.00001):
            param_dict['roughness'] = ['Roughness', 'float', [str(col_list[3][0])]]
        if col_list[4] and (col_list[4][0] > 0.00001):
            param_dict['displacementoffset'] = ['DisplacementOffset', 'float', [str(col_list[4][0])]]
        # Write the parameters to MTR
        if len(param_dict) > 0:
            ascii_lines.append("// Parameters")
            for _, [param_name, param_type, param_values] in param_dict.items():
                if len(param_values) > 0:
                    if param_type == "int":  # a single int
                        sv = str(int(param_values[0]))
                        ascii_lines.append("parameter int " + param_name + " " + sv)
                    elif param_type == "float":  # up to 4 floats
                        sv = ' '.join([str(v) for v in param_values[:4]])
                        ascii_lines.append("parameter float " + param_name + " " + sv)
        return ascii_lines
