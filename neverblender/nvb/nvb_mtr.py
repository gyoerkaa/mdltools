"""TODO: DOC."""

import os
import re

from . import nvb_utils
from . import nvb_def


class Mtr(object):
    """A material read from an mtr file."""
    def __init__(self, name='unnamed'):
        """TODO: DOC."""
        self.name = name

        self.filepath = ''
        self.textures = []
        self.renderhints = set()
        self.parameters = dict()
        self.customshaderVS = ''
        self.customshaderFS = ''

    @staticmethod
    def readParamValues(str_values):
        """Parses parameter values from list of strings."""
        values = []
        for sv in str_values:
            if not nvb_utils.isNumber(sv):
                break
            values.append(float(sv))
        return values

    def loadFile(self, filepath):
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
        self.loadAscii(ascii_data)
        mtrFile.close()
        return True

    def loadTextBlock(self, txt_block):
        """Load content of a blender text block."""
        if not txt_block:
            return False
        # Generate a name, strip trailing numbers (".001") and ".mtr"
        match = re.match('([\w\-]+)[\.mtr]?[\.\d+]*', txt_block.name)
        if match:
            self.name = match.group(1)
        ascii_data = txt_block.as_string()
        self.loadAscii(ascii_data)
        return True

    def loadAscii(self, asciiData):
        """TODO: DOC."""
        asciiLines = [l.strip().split() for l in asciiData.splitlines()]
        iterable = iter(asciiLines)
        line = True
        while line is not None:
            line = self.loadAsciiLine(iterable)

    def loadAsciiLine(self, itlines):
        """TODO: Doc."""
        line = None
        try:
            line = next(itlines)
        except StopIteration:
            return None
        label = ''
        try:
            label = line[0].lower()
        except (IndexError, AttributeError):
            return line  # Probably empty line or comment
        if label == 'renderhint':
            self.renderhints.add(nvb_utils.getAuroraIdentifier(line[1]))
        elif label == 'parameter':
            try:
                ptype = line[1].lower()
                pname = line[2]
                pvalues = line[3:7]
            except IndexError:
                return line
            pvalues = Mtr.readParamValues(pvalues)
            self.parameters[pname] = (ptype, pvalues)
        elif label == 'customshadervs':
            self.customshaderVS = line[1]
        elif label == 'customshaderfs':
            self.customshaderFS = line[1]
        elif label.startswith('texture'):
            if label[7:]:  # 'texture' is followed by a number
                idx = int(label[7:])
                cnt = len(self.textures)
                if idx+1 > cnt:
                    self.textures.extend(['' for _ in range(idx+1-cnt)])
                self.textures[idx] = nvb_utils.getAuroraTexture(line[1])
        return line

    @staticmethod
    def generateAscii(material, options):
        """Generate a mtr file as asciilines."""
        asciiLines = []
        txlist = nvb_utils.get_textures(material)
        # Add shader specification
        if material.nvb.shadervs or material.nvb.shaderfs:
            asciiLines.append('// Shaders')
            if material.nvb.shadervs:
                asciiLines.append('customshaderVS ' + material.nvb.shadervs)
            if material.nvb.shaderfs:
                asciiLines.append('customshaderFS ' + material.nvb.shaderfs)
            asciiLines.append('')
        # Add Renderhint
        if (material.nvb.renderhint == 'AUTO' and len(txlist) > 1 and
            not (material.nvb.shadervs or material.nvb.shaderfs)) or \
           (material.nvb.renderhint == 'NASM'):
            asciiLines.append('// Renderhints')
            asciiLines.append('renderhint NormalAndSpecMapped')
            asciiLines.append('')
        # Add list of textures
        if len(txlist) > 0:
            asciiLines.append('// Textures')
            fstr = 'texture{:d} {:s}'
            asciiLines.extend([fstr.format(i, n) for i, n, _ in txlist])
            asciiLines.append('')
        # Add parameters
        if len(material.nvb.mtrparam_list) > 0:
            asciiLines.append('// Parameters')
            existing_params = []
            for pa in material.nvb.mtrparam_list:
                if pa.pname.lower() not in existing_params:  # Keep unique
                    existing_params.append(pa.pname.lower())
                    vals = Mtr.readParamValues(pa.pvalue.strip().split())
                    if len(vals) > 0:
                        if pa.ptype == 'int':  # a single int
                            sv = str(int(vals[0]))
                            line = 'parameter int ' + pa.pname + ' ' + sv
                        elif pa.ptype == 'float':  # up to 4 floats
                            sv = ' '.join([str(v) for v in vals[:4]])
                            line = 'parameter float ' + pa.pname + ' ' + sv
                    asciiLines.append(line)
        return asciiLines

    @staticmethod
    def saveFile(material, options):
        if material.nvb.usemtr and options.exportMTR:
            asciiLines = Mtr.generateAscii(material, options)
            with open(os.fsencode(options.filepath), 'w') as f:
                f.write('\n'.join(asciiLines))

    def create(self, material, options):
        """Generate the values from the mtr for the material."""
        def setup_listitem(item, data):
            if data[0] == 'int':  # Only a single int
                item.ptype = 'int'
                item.pvalue = str(int(data[1][0]))
            elif data[0] == 'float':  # Up to four floats
                item.ptype = 'float'
                item.pvalue = ' '.join([str(v) for v in data[1][:4]])

        material.nvb.usemtr = True
        material.nvb.mtrname = self.name
        material.nvb.mtrpath = self.filepath
        material.nvb.shadervs = self.customshaderVS
        material.nvb.shaderfs = self.customshaderFS
        # Load renderhint and set up textures accordingly
        if nvb_def.Renderhint.NORMALANDSPECMAPPED in self.renderhints:
            material.nvb.renderhint = 'NASM'
        # Load parameters
        if self.parameters:
            existing_params = []
            # Adjust existing params
            for listitem in material.nvb.mtrparam_list:
                if listitem.pname in self.parameters:
                    setup_listitem(listitem, self.parameters[listitem.pname])
                    existing_params.append(listitem.pname)
            # Add new params
            for pname, pdata in self.parameters.items():
                if pname not in existing_params:
                    listitem = material.nvb.mtrparam_list.add()
                    listitem.pname = pname
                    setup_listitem(listitem, pdata)
        # Load textures
        for idx, txname in enumerate(self.textures):
            if txname:
                tslot = material.texture_slots[idx]
                if not tslot:
                    tslot = material.texture_slots.create(idx)
                tslot.texture = nvb_utils.create_texture(
                    txname, txname, options.filepath, options.tex_search)
