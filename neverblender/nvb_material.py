import math
import os
import itertools

import mathutils
import bpy

from . import nvb_mtr
from . import nvb_def
from . import nvb_utils
from . import nvb_parse


class Nodes(object):
    """Collection of function for dealing with shader nodes."""

    @staticmethod
    def get_texture_name(texture_node):
        
        tex_name = "ERROR"
        # Try reading an image from the texture node
        try:
            img = texture_node.image
        except AttributeError:
            # No image, simply use the node label
            tex_name = texture_node.label
        else:
            if img.filepath:
                tex_name = os.path.splitext(os.path.basename(img.filepath))[0]
            elif img.name:
                tex_name = os.path.splitext(os.path.basename(img.name))[0]
        return tex_name
    
    @staticmethod
    def get_texture_map(node_input):
        """Get the name of the texture of there is one. None otherwise."""
        texture_name = None
        mixin_color = (1.0, 1.0, 1.0, 1.0)

        if node_input.links:
            linked_node = node_input.links[0].from_node
            
            if linked_node.type == 'TEX_IMAGE':
                # texture node, grab image
                texture_name = Nodes.get_texture_name(linked_node)
            elif linked_node.type == 'MIX_RGB':
                # Mix node, set color value and keep looking for texture
                if linked_node.inputs[1].links:
                    tex_node = linked_node.inputs[1].links[0].from_node
                    if tex_node.type == 'TEX_IMAGE':
                        texture_name = Nodes.get_texture_name(tex_node)
                    mixin_color = linked_node.inputs[2].default_value
                elif linked_node.inputs[2].links:
                    tex_node = linked_node.inputs[1].links[0].from_node
                    if tex_node.type == 'TEX_IMAGE':
                        texture_name = Nodes.get_texture_name(tex_node)
                    mixin_color = linked_node.inputs[1].default_value
                else:
                    # No texture on either side
                    mixin_color = linked_node.outputs[0].default_value
            elif linked_node.type == 'RGB':
                # Color node, set output color
                mixin_color = linked_node.outputs[0].default_value
        else:
            mixin_color = list(node_input.default_value)
        return texture_name, mixin_color

    @staticmethod
    def get_normal_map(node_input):
        """Get the name of the normal map of there is one. None otherwise."""
        texture_name = None
        mixin_color = (1.0, 1.0, 1.0, 1.0)  # for consitency

        if node_input.links:
            node_normal = node_input.links[0].from_node
            if node_normal and node_normal.inputs['Normal'].links:
                node_tex = node_normal.inputs['Normal'].links[0].from_node
                texture_name = Nodes.get_texture_name(node_tex)
        return texture_name, mixin_color
   
    @staticmethod
    def get_height_map(node_input):
        """Get the name of the height map of there is one. None otherwise."""
        texture_name = None
        mixin_color = (1.0, 1.0, 1.0, 1.0)  # for consitency

        if node_input.links:
            linked_node = node_input.inputs[0].links[0].from_node 
            texture_name = Nodes.get_texture_name(linked_node)
        return texture_name, mixin_color

    @staticmethod
    def get_alpha_value(node_input):
        """Search for an alpha value from this socket."""
        def get_alpha_recursive(node):
            """Read the alpha value from the first connected math node."""
            if node.type == 'MATH':
                # Use the value from the first unconnected socket
                if not node.input[0].links:
                    return node.input[0].default_value
                elif not node.input[1].links:
                    return node.input[1].default_value
                else:
                    return 1.0  # No unconnected sockets
            else:
                # Go down the node tree
                for ni in node.inputs:
                    if ni.type in ['VALUE', 'SHADER', 'RGBA'] and ni.links:
                        alpha = get_alpha_recursive(ni.links[0].from_node)
                        if alpha is not None:
                            return alpha
            return None
      
        alpha_value = None
        if not node_input.links:
            alpha_value = get_alpha_recursive(node_input.links[0])
        # Check for none (=no alpha value found) and return 1.0 instead
        if alpha_value is None:
            alpha_value = 1.0
        return alpha_value

    @staticmethod
    def get_node_data_bsdf(node_out, node_shader_main):
        """Get the list of texture names for Principled BSDF shaders."""
        tex_list = [None] * 15 
        color_list = [None] * 15
        alpha_val = 1.0

        # Alpha should be inverted and plugged into transparency
        shader_input = node_shader_main.inputs[4]  # Transparency
        alpha_val = Nodes.get_alpha_value(shader_input)

        # Diffuse 
        # NWN = 0, Principled BSDF = 0
        shader_input = node_shader_main.inputs[0]  # 'Base Color'
        tex_list[0], color_list[0] = Nodes.get_texture_map(shader_input)

        # Normal 
        # NWN = 1, Principled BSDF = 17
        shader_input = node_shader_main.inputs[17]  # 'Normal'
        tex_list[1], color_list[1] = Nodes.get_normal_map(shader_input)

        # Specular
        # NWN = 2, Principled BSDF = 5
        shader_input = node_shader_main.inputs[5]  # 'Specular'
        tex_list[2], color_list[2] = Nodes.get_texture_map(shader_input)           

        # Roughness 
        # NWN = 3, Principled BSDF = 7
        shader_input = node_shader_main.inputs[7]  # 'Roughness'
        tex_list[3], color_list[3] = Nodes.get_texture_map(shader_input)

        # Emissive/Illumination
        # # NWN = 4, Emissive Shader mixed into Principled BSDF
        shader_input = node_shader_main.inputs[3]
        tex_list[4], color_list[4] = Nodes.get_texture_map(shader_input)

        # Height/Ambient Occlusion 
        # Plugged directly into material output

        return tex_list, color_list, alpha_val           

    @staticmethod
    def get_node_data_spec(node_out, node_shader_main):
        """Get the list of texture names from Eevee Specular shaders."""
        
        tex_list = [None] * 15 
        color_list = [None] * 15
        alpha_val = 1.0

        # Alpha should be inverted and plugged into transparency
        shader_input = node_shader_main.inputs[4]  # Transparency
        alpha_val = Nodes.get_alpha_value(shader_input)
        
        # Diffuse (NWN = 0, Eevee Specular = 0)
        shader_input = node_shader_main.inputs[0]  # Base Color
        tex_list[0], color_list[0] = Nodes.get_texture_map(shader_input)

        # Normal (NWN = 1, Eevee Specular = 5)
        shader_input = node_shader_main.inputs[5]  # Normal
        tex_list[1], color_list[1] = Nodes.get_normal_map(shader_input)

        # Specular (NWN = 2, Eevee Specular = 1)
        shader_input = node_shader_main.inputs[1]  # Specular
        tex_list[2], color_list[2] = Nodes.get_texture_map(shader_input)           

        # Roughness (NWN = 3, Eevee Specular = 2)
        shader_input = node_shader_main.inputs[2]  # Roughness
        tex_list[3], color_list[3] = Nodes.get_texture_map(shader_input)

        # Emissive/Illumination (NWN = 4, Eevee Specular = 3)
        shader_input = node_shader_main.inputs[3]  # Emissive Color
        tex_list[4], color_list[4] = Nodes.get_texture_map(shader_input)

        # Height/Ambient Occlusion (NWN = 5, Eevee Specular = 9)
        shader_input = node_shader_main.inputs[9]  # Ambient Occlusion
        tex_list[5], color_list[5] = Nodes.get_texture_map(shader_input)

        return tex_list, color_list, alpha_val
    
    @staticmethod
    def get_node_data(material):
        """Get the list of texture names for this material."""
        def get_main_shader(node):
            """Return the first connected Specular or BSDF node."""  
            if node.type in ['BSDF_PRINCIPLED', 'EEVEE_SPECULAR']:
                return node
            # Go down the node tree
            for ni in node.inputs:
                if ni.type == 'SHADER' and ni.links:
                    input_node = get_main_shader(ni.links[0].from_node)
                    if input_node is not None:
                        return input_node
            return None

        tex_list = [None] * 15

        # Only nodes are supported
        if not material.use_nodes: 
            return tex_list  # still empty         
               
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        # No nodes or no links == no textures
        if ((len(nodes) <= 0) or (len(links) <= 0)):
            return tex_list  # still empty  

        output_node_list = [n for n in nodes if n.type == 'OUTPUT_MATERIAL']

        # No output node == no textures
        if not output_node_list:
            return tex_list  # still empty  

        # If there are multiple output nodes we have to choose one
        # We'll pick the one with the most input links
        output_node_list.sort(
            key=(lambda n: len([i for i in n.inputs if i.is_linked])), 
            reverse=True)
        node_out = output_node_list[0]

        # Try reading height map (5) and normal map (1)
        # from displacement socket of output_node.
        # These may be overwritten later from shader node values
        if node_out.inputs[2].links:
            node_displ = node_out.inputs[2].links[0].from_node
            if node_displ.type == 'DISPLACEMENT':
                # Height map (5)
                tex_list[5], _ = Nodes.get_height_map(node_displ.inputs[0])
                # Normal map (1)
                tex_list[1], _ = Nodes.get_normal_map(node_displ.inputs[3])
        
        # Surface is not linked to anything == no other textures
        if not node_out.inputs[0].links:
            return tex_list

        node_main_shader = get_main_shader(node_out)
        if node_main_shader.type == 'BSDF_PRINCIPLED':
            Nodes.get_node_data_bsdf(node_out, node_main_shader)
        elif node_main_shader.type == 'EEVEE_SPECULAR':
            Nodes.get_node_data_spec(node_out, node_main_shader)

        return tex_list
     
    @staticmethod
    def add_node_data_bsdf(material, 
                           texture_list, color_list, alpha,
                           img_filepath, img_search = False):
        """Setup up material nodes for Principled BSDF Shader."""
        # Cache because lazy
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        # Create an output and shaders
        node_out = nodes.new('ShaderNodeOutputMaterial')
        node_out.location = (400.0, 400.0)

        node_shd_bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        node_shd_bsdf.location = (-75.0, 306.0)

        node_shd_trans = nodes.new('ShaderNodeBsdfTransparent')
        node_shd_trans.label = "Shader: Transparent"
        node_shd_trans.name = "shd_transparent"
        node_shd_trans.location = (22.0, 440.0)

        node_shd_mix_trans = nodes.new('ShaderNodeMixShader')
        node_shd_mix_trans.label = "Mix: Transparency"
        node_shd_mix_trans.name = "mix_transparency"
        node_shd_mix_trans.location = (225.0, 375.0)
        node_shd_mix_trans.inputs[0].default_value = 1.0

        node_shd_emit = nodes.new('ShaderNodeEmission')
        node_shd_emit.label = "Shader: Emission"
        node_shd_emit.name = "shd_emission"

        node_shd_mix_emit = nodes.new('ShaderNodeMixShader')
        node_shd_mix_emit.label = "Mix: Emission"
        node_shd_mix_emit.name = "mix_emission"
        node_shd_mix_emit.location = (225.0, 375.0)
        node_shd_mix_emit.inputs[0].default_value = 0.5

        # Setup: 
        #                     Transparent BSDF =>
        #                                         Mix Transp => Output 
        # Emission         =>               
        #                     Mix Emit         =>
        # Principled BSDF  =>
        links.new(node_out.inputs[0], node_shd_mix_trans.outputs[0])

        links.new(node_shd_mix_trans.inputs[1], node_shd_trans.outputs[0])
        links.new(node_shd_mix_trans.inputs[2], node_shd_mix_emit.outputs[0])

        links.new(node_shd_mix_emit.inputs[1], node_shd_emit.outputs[0])
        links.new(node_shd_mix_emit.inputs[2], node_shd_bsdf.outputs[0])

        # Add texture maps
        # 0 = Diffuse
        if texture_list[0]:
            # Setup: Image Texture (Color) => Principled BSDF
            # Setup: Image Texture (Alpha) => Mix Transparent (Factor)
            node_tex_diff = nodes.new('ShaderNodeTexImage')
            node_tex_diff .label = "Texture: Diffuse"
            node_tex_diff .name = "tex_diffuse"
            node_tex_diff .location = (-460.0, 373.0)

            links.new(node_shd_bsdf.inputs[0], node_tex_diff .outputs[0])
            links.new(node_shd_mix_trans.inputs[0], node_tex_diff .outputs[1])

         # 1 = Normal
        if texture_list[1]:
            # Setup: Image Texture => Normal Map => Principled BSDF
            node_tex_norm = nodes.new('ShaderNodeTexImage')   
            node_tex_norm.label = "Texture: Normal"
            node_tex_norm.name = "tex_normal"
            node_tex_norm.location = (-560.0, -241.0)
            node_tex_norm.color_space = 'NONE'

            node_norm = nodes.new('ShaderNodeNormalMap')
            node_norm.location = (-280.0, -140.0)

            links.new(node_norm.inputs[1], node_tex_norm.outputs[0])
            links.new(node_shd_bsdf.inputs[17], node_norm.outputs[0])

         # 2 = Specular
        if texture_list[2]:
            # Setup: Image Texture => Principled BSDF
            node_tex_spec = nodes.new('ShaderNodeTexImage')
            node_tex_spec.label = "Texture: Specular"
            node_tex_spec.name = "tex_specular"

            links.new(node_shd_bsdf.inputs[5], node_tex_spec.outputs[0])

        # 3 = Roughness
        if texture_list[3]:
            # Setup: Image Texture => Principled BSDF
            node_tex_rough = nodes.new('ShaderNodeTexImage')
            node_tex_rough.label = "Texture: Roughness"
            node_tex_rough.name = "tex_roughness"

            links.new(node_shd_bsdf.inputs[7], node_tex_rough.outputs[0])

        # 4 = Illumination/ Emission/ Glow
        if texture_list[4]:
            # Setup: 
            # Image Texture => Emission Shader => 
            #                                     Mix Shader => Material Output
            #                  Principled BSDF => 
            node_tex_emit = nodes.new('ShaderNodeTexImage')
            node_tex_emit.label = "Texture: Emission"
            node_tex_emit.name = "tex_emission"

        # 5 = Height/AO/Parallax
        if texture_list[5]:
            # Setup: Image Texture => Displacement => Material Output
            node_tex_height = nodes.new('ShaderNodeTexImage')
            node_tex_height.label = "Texture: Height"
            node_tex_height.name = "tex_height"
            node_tex_height.label = (-560.0, -241.0)

            node_displ = nodes.new('ShaderNodeDisplacement')
            node_displ.location = (-280.0, -140.0)  

            links.new(node_displ.inputs[0], node_tex_height.outputs[0])
            links.new(node_out.inputs[2], node_displ.outputs[0])
    
    @staticmethod
    def add_node_data_spec(material, 
                           texture_list, color_list, alpha,
                           img_filepath, img_search = False):
        """Setup up material nodes for Eevee Specular Shader."""
        # Cache because lazy
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        # Create an output and shaders
        node_out = nodes.new('ShaderNodeOutputMaterial')
        node_out.location = (400.0, 400.0)

        node_shader_spec = nodes.new('ShaderNodeEeveeSpecular')
        node_shader_spec.location = (-75.0, 306.0)

        links.new(node_out.inputs['Surface'], 
                  node_shader_spec.outputs['BSDF'])
        
        # Add texture maps
        # 0 = Diffuse = Base Color
        node_shader_spec.inputs[0].default_value = color_list[0]
        if texture_list[0]:           
            # Setup: Image Texture (Color) => Eevee Specular (Base Color)           
            node_tex_diff = nodes.new('ShaderNodeTexImage')
            node_tex_diff.label = "Texture: Diffuse"
            node_tex_diff.name = "tex_diffuse"
            node_tex_diff.location = (-460.0, 373.0)

            node_tex_diff.image = nvb_utils.create_image(
                texture_list[0], img_filepath, img_search)
            node_tex_diff.color_space = 'COLOR'

            links.new(node_shader_spec.inputs[0], node_tex_diff.outputs[0])

            # Setup: Image Texture (Alpha) => Math (Multiply mdl alpha)
            #        => Invert => Eevee Specular (Tranparency)
            node_invert = nodes.new('ShaderNodeInvert')
            node_invert.label = "Alpha to Transparency"
            node_invert.name = "math_aurora_alpha"

            node_math = nodes.new('ShaderNodeMath')
            node_math.label = "Aurora Alpha"
            node_math.name = "math_aurora_alpha"
            node_math.operation = 'MULTIPLY'
            node_math.use_clamp = True
            node_math.inputs[1].default_value = alpha

            links.new(node_math.inputs[0], node_tex_diff.outputs[1])
            links.new(node_invert.inputs[1], node_math.outputs[0])                     
            links.new(node_shader_spec.inputs[4], node_invert.outputs[0])

        else: # No diffuse map, plug in (1-alpha) directly into transparency
            node_shader_spec.inputs['Transparency'].default_value = 1.0 - alpha

        # 1 = Normal
        if texture_list[1]:
            # Setup: Image Texture => Normal Map => Eevee Specular
            node_tex_norm = nodes.new('ShaderNodeTexImage')      
            node_tex_norm.label = "Texture: Normal"
            node_tex_norm.name = "tex_normal"
            node_tex_norm.location = (-560.0, -241.0)

            node_tex_norm.image = nvb_utils.create_image(
                texture_list[1], img_filepath, img_search)
            node_tex_norm.color_space = 'NONE'  # Not rgb data

            node_normal = nodes.new('ShaderNodeNormalMap')
            node_normal.location = (-280.0, -140.0)

            links.new(node_normal.inputs[0], node_tex_norm.outputs[0])
            links.new(node_shader_spec.inputs[5], node_normal.outputs[0])

        # 2 = Specular
        node_shader_spec.inputs[1].default_value = color_list[2]
        if texture_list[2]:
            # Setup: Image Texture => Eevee Specular
            node_tex_spec = nodes.new('ShaderNodeTexImage')
            node_tex_spec.label = "Texture: Specular"
            node_tex_spec.name = "tex_specular"

            node_tex_spec.image = nvb_utils.create_image(
                texture_list[2], img_filepath, img_search)
            node_tex_spec.color_space = 'COLOR'

            links.new(node_shader_spec.inputs[1], node_tex_spec.outputs[0])

        # 3 = Roughness
        if texture_list[3]:
            # Setup: Image Texture => Eevee Specular (Roughness)
            node_tex_rough = nodes.new('ShaderNodeTexImage')
            node_tex_rough.label = "Texture: Roughness"
            node_tex_rough.name = "tex_roughness"
            
            node_tex_rough.image = nvb_utils.create_image(
                texture_list[3], img_filepath, img_search)
            node_tex_rough.color_space = 'NONE'  # Single channel

            links.new(node_shader_spec.inputs[2], node_tex_rough.outputs[0])

        # 4 = Illumination/ Emission/ Glow
        if texture_list[4]:
            # Setup: Image Texture => Eevee Specular (Emissive)
            node_tex_emit = nodes.new('ShaderNodeTexImage') 
            node_tex_emit.label = "Texture: Illumination"
            node_tex_emit.name = "tex_illumination"

            node_tex_emit.image = nvb_utils.create_image(
                texture_list[4], img_filepath, img_search)
            node_tex_emit.color_space = 'NONE'  # Single channel

            links.new(node_shader_spec.inputs[3], node_tex_emit.outputs[0]) 

        # 5 = Height (use as Ambient Occlusion)
        if texture_list[5]:
            # Setup: Image Texture => Eevee Specular (Ambient Occlusion)
            node_tex_height = nodes.new('ShaderNodeTexImage')
            node_tex_height.label = "Texture: Height"
            node_tex_height.name = "tex_height"
            node_tex_height.location = (-560.0, -241.0)

            node_tex_height.image = nvb_utils.create_image(
                texture_list[5], img_filepath, img_search)
            node_tex_height.color_space = 'NONE'  # Single channel

            links.new(node_shader_spec.inputs[9], node_tex_height.outputs[0])   
    
    @staticmethod
    def add_node_data(material, shader_type, 
                      texture_list, color_list, alpha,
                      img_filepath, img_search = False):
        """Select shader nodes based on options."""
        if (shader_type == 'ShaderNodeEeveeSpecular'):
            Nodes.add_node_data_spec(material, 
                                     texture_list, color_list, alpha,
                                     img_filepath, img_search)
        else:
            Nodes.add_node_data_bsdf(material, 
                                     texture_list, color_list, alpha,
                                     img_filepath, img_search)
         
  

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
        self.color_list[3] = (0.0, 0.0, 0.0, 1.0)  # Illumiation/Emission
        self.renderhints = set()
        self.mtr_name = None
        self.mtr = None

    @staticmethod
    def colorisclose(a, b, tol=0.05):
        return (sum([math.isclose(v[0], v[1]) for v in zip(a, b)]) == len(a))
 
    def generate_material_name(self):
        """Generates a material name for use in blender.""" 
        
        # 'materialname' over 'texture0'/'bitmap' over Default
        if self.materialname:
            mat_name = self.materialname
        elif (self.texture_list[0]) and \
                (self.texture_list[0] is not nvb_def.null):
            mat_name = self.texture_list[0].lower()
        else:
            mat_name = ""  # Blender will a default name
        return mat_name
    
    def find_blender_material(self, options):
        """TODO: Doc."""

        matching_mat = None
        for mat in bpy.data.materials:
            pass
        return matching_mat

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
                mtr_path = os.path.join(os.path.split(options.filepath), 
                                        mtr_filename)
                mtr = nvb_mtr.Mtr(self.mtr_name)
                if mtr.read_mtr(mtr_path):
                    options.mtrdb[self.mtr_name] = mtr
                    self.mtr = mtr
    
    def mtr_merge(self, options):
        """Merges the contents of the mtr file into this material."""            
        # Merge values from mtr into this material
        if self.mtr:
            self.renderhints = self.renderhints.union(self.mtr.renderhints)
            mtr_texture_list = mtr.get_texture_list()
            for idx, txname in enumerate(self.mtr.textures):
                if txname:  # null value in mtr overwrites existing in mdl
                    self.texture_list[idx] = txname

            mtr_color_list = mtr.get_color_list()
                
              
    def create_blender_material(self, options, use_existing=True):
        """Returns a blender material with the stored values."""
        # Load mtr values into this material
        if options.mtr_import:
            self.mtr_read(options)
            self.mtr_merge(options)
        # Look for similar materials to avoid duplicates
        material = None
        if use_existing:
            material = self.find_blender_material(options)
        # Create new material if necessary
        if not material:
            material_name = self.generate_material_name()
            material = bpy.data.materials.new(material_name)
            material.blend_method = 'BLEND'

            material.use_nodes = True
            material.node_tree.nodes.clear()
            Nodes.add_node_data(material, options.mat_shader,
                                self.texture_list, self.color_list,
                                options.filepath ,options.tex_search)

        return material

    @staticmethod
    def generateDefaultValues(asciiLines):
        """Write default material values to ascii."""
        asciiLines.append('  ambient 1.00 1.00 1.00')
        asciiLines.append('  diffuse 1.00 1.00 1.00')
        asciiLines.append('  specular 0.00 0.00 0.00')
        asciiLines.append('  bitmap ' + nvb_def.null)

    @staticmethod
    def generateAscii(obj, asciiLines, options):
        """Write Ascii lines from the objects material for a MDL file."""
        material = obj.active_material
        txlist = []
        if obj.nvb.render and material:
            # Write Color Values
            fstr = '  ambient {:3.2f} {:3.2f} {:3.2f}'
            asciiLines.append(fstr.format(*material.nvb.ambient_color))
            fstr = '  diffuse {:3.2f} {:3.2f} {:3.2f}'
            asciiLines.append(fstr.format(*material.diffuse_color))
            fstr = '  specular {:3.2f} {:3.2f} {:3.2f}'
            asciiLines.append(fstr.format(*material.specular_color))
            # Get textures for this material
            txlist = nvb_utils.get_textures(material)
            if material.nvb.usemtr:
                mtrname = material.nvb.mtrname
                asciiLines.append('  ' + options.mtr_ref + ' ' + mtrname)
                options.mtrdb.add(material.name)  # export later on demand
            else:
                # Add Renderhint
                if (material.nvb.renderhint == 'NASM') or \
                   (material.nvb.renderhint == 'AUTO' and len(txlist) > 1):
                    asciiLines.append('  renderhint NormalAndSpecMapped')
                # Export texture[0] as "bitmap", not "texture0"
                if len(txlist) > 0:
                    asciiLines.append('  bitmap ' + txlist[0][1])
                else:
                    asciiLines.append('  bitmap ' + nvb_def.null)
                # Export texture1 and texture2
                fs = '  texture{:d} {:s}'
                asciiLines.extend([fs.format(i, n) for i, n, _ in txlist[1:3]])
            # Alpha value:
            # 1. Texture slots present: get alpha from 1st slot
            # 2. No texture slots: get alpha from material
            if material.use_transparency:
                if len(txlist) > 0:
                    _, _, alpha = txlist[0]
                else:
                    alpha = material.alpha
                if not math.isclose(alpha, 1.0, rel_tol=0.01):  # Omit 1.0
                    asciiLines.append('  alpha {: 3.2f}'.format(alpha))
        else:
            Material.generateDefaultValues(asciiLines)
        return len(txlist) > 0  # Needed later to decide whether to add UVs

