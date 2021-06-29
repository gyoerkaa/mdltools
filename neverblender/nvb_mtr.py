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
                elif param_name.lower() == "metallicness":
                    self.metallicness = nvb_parse.ascii_float(param_value[0])                    
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
    def generate_ascii(material, options):
        """Generate a mtr file as asciilines."""
        ascii_lines = []
        tex_list, col_list, _ = Materialnode.get_node_data(material)
        # Clean up texture list, delete trailing "null"
        tex_list = [t if t else nvb_def.null for t in tex_list]
        while tex_list and tex_list[-1] == nvb_def.null:
            _ = tex_list.pop()
        # Add shader specification
        if material.nvb.mtr.shader_vs or material.nvb.mtr.shader_fs:
            # Custom Shaders
            ascii_lines.append('// Shaders')
            if material.nvb.shadervs:
                ascii_lines.append('customshaderVS ' + material.nvb.mtr.shader_vs)
            if material.nvb.shaderfs:
                ascii_lines.append('customshaderFS ' + material.nvb.mtr.shader_fs)
            ascii_lines.append('')
        elif tex_list and (tex_list[:3].count(nvb_def.null) <= 1):
            # Add Renderhint
            ascii_lines.append('// Renderhint')
            ascii_lines.append('renderhint NormalAndSpecMapped')
            ascii_lines.append('')
        # Add list of textures
        if len(tex_list) > 0:
            ascii_lines.append('// Textures')
            fstr = 'texture{:d} {:s}'
            ascii_lines.extend([fstr.format(i, t)
                                for i, t in enumerate(tex_list)])
            ascii_lines.append('')
        # Add parameters
        if len(material.nvb.mtr.param_list) > 0:
            ascii_lines.append('// Parameters')
            existing_params = []
            for pa in material.nvb.mtr.param_list:
                if pa.pname.lower() not in existing_params:  # Keep unique
                    existing_params.append(pa.pname.lower())
                    vals = Mtr.parse_ascii_param_value(pa.pvalue.strip().split())
                    line = ''
                    if len(vals) > 0:
                        if pa.ptype == 'int':  # a single int
                            sv = str(int(vals[0]))
                            line = 'parameter int ' + pa.pname + ' ' + sv
                        elif pa.ptype == 'float':  # up to 4 floats
                            sv = ' '.join([str(v) for v in vals[:4]])
                            line = 'parameter float ' + pa.pname + ' ' + sv
                    ascii_lines.append(line)
        return ascii_lines
