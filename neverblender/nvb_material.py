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
        """Get a texture from a texture node."""
        # Try reading an image from the texture node
        try:
            img = texture_node.image
            if img.filepath:
                return os.path.splitext(os.path.basename(img.filepath))[0]
            elif img.name:
                return os.path.splitext(os.path.basename(img.name))[0]
        except AttributeError:
            pass  # Node does not have an image texture
        if texture_node.label:
            return texture_node.label
        else:
            return "ERROR"
    
    @staticmethod
    def get_texture_map(node_input):
        """Get the texture of there is one. None otherwise."""
        texture_name = None
        default_value = None

        if node_input.links:
            linked_node = node_input.links[0].from_node
            
            if linked_node.type == 'TEX_IMAGE':
                # texture node, grab image
                texture_name = Nodes.get_texture_name(linked_node)
            elif linked_node.type == 'MIX_RGB':
                # Mix node, grab default value and texture
                if linked_node.inputs[1].links:  # socket 1 is linked
                    tex_node = linked_node.inputs[1].links[0].from_node
                    if tex_node.type == 'TEX_IMAGE':
                        texture_name = Nodes.get_texture_name(tex_node)
                    default_value = linked_node.inputs[2].default_value
                elif linked_node.inputs[2].links:  # socket 2 is linked
                    tex_node = linked_node.inputs[1].links[0].from_node
                    if tex_node.type == 'TEX_IMAGE':
                        texture_name = Nodes.get_texture_name(tex_node)
                    default_value = linked_node.inputs[1].default_value
                else:  # No linked socket
                    default_value = linked_node.outputs[0].default_value
            elif linked_node.type == 'RGB':
                # Color node, set output color
                default_value = linked_node.outputs[0].default_value
        else:
            default_value = node_input.default_value
        # Convert default value to list
        if default_value:
            try:
                default_value = list(default_value)
            except TypeError:
                default_value = [default_value]
        return texture_name, default_value

    @staticmethod
    def get_normal_map(node_input):
        """Get the normal map of there is one. None otherwise."""
        texture_name = None
        default_value = None

        if node_input.links:
            node_normal = node_input.links[0].from_node
            if node_normal and node_normal.inputs[1].links:
                node_tex = node_normal.inputs[1].links[0].from_node
                texture_name = Nodes.get_texture_name(node_tex)
        return texture_name, default_value
   
    @staticmethod
    def get_height_map(node_input):
        """Get the height map of there is one. None otherwise."""
        texture_name = None
        default_value = None

        if node_input.links:
            linked_node = node_input.inputs[0].links[0].from_node 
            texture_name = Nodes.get_texture_name(linked_node)
        return texture_name, default_value
    
    @staticmethod
    def find_emissive_socket(node_input):
        """Read the socket from which to take emissive. May be None."""
        if node_input.links:
            node = node_input.links[0].from_node
            if node.type == 'EMISSION':
                return node.inputs[0]
            elif node.type == 'EEVEE_SPECULAR':
                return node.inputs[3]
            elif node.type == 'MIX_SHADER':
                # Go down both shader input slots
                tmp_node = Nodes.find_emissive_socket(node.inputs[1])
                if tmp_node is not None:
                    return tmp_node
                else:
                    return Nodes.find_emissive_socket(node.inputs[2])
        return None

    @staticmethod
    def get_emissive_map(node_input):
        """Get the emissive map if there is one. None otherwise."""
        texture_name = None
        default_value = None
        
        emissive_input = Nodes.find_emissive_socket(node_input)
        if emissive_input:
            texture_name, default_value = Nodes.get_texture_map(emissive_input)
        return texture_name, default_value
    
    @staticmethod
    def find_alpha_socket(node_input):
        """Read the socket from which to take alpha. May be None."""
        alpha_socket = None
        if node_input.links:
            node = node_input.links[0].from_node
            if node.type == 'MATH':
                # Use the value from the first unconnected socket
                if not node.inputs[0].links:
                    alpha_socket = node.inputs[0]
                if not node.inputs[1].links:
                    alpha_socket = node.inputs[1]
                else:
                    alpha_socket = None  # No unconnected sockets
            elif node.type == 'EEVEE_SPECULAR':
                # Follow socket 4 (transparency)
                alpha_socket = Nodes.find_alpha_socket(node.inputs[4])
            elif node.type == 'INVERT':
                # Follow socket 1 (color)
                alpha_socket = Nodes.find_alpha_socket(node.inputs[1])
            elif node.type == 'MIX_SHADER':
                # Follow socket 0 (factor)
                alpha_socket = Nodes.find_alpha_socket(node.inputs[0])
        return alpha_socket   

    @staticmethod 
    def get_output_node(nodes):
        """Search for the output node in this node list."""
        # No nodes or no links == no textures
        if (len(nodes) <= 0):
            return None 

        output_nodes = [n for n in nodes if n.type == 'OUTPUT_MATERIAL']

        # No output node == no textures
        if not output_nodes:
            return None 

        # If there are multiple output nodes we have to choose one
        # We'll pick the one with the most input links
        output_nodes.sort(
            key=(lambda n: len([i for i in n.inputs if i.is_linked])), 
            reverse=True)
        return output_nodes[0]

    @staticmethod
    def get_alpha_value(node_input):
        """Search for an alpha value from this socket."""
        alpha_input = Nodes.find_alpha_socket(node_input)
        if alpha_input:
            return alpha_input.default_value
        return 1.0

    @staticmethod
    def get_node_data_bsdf(node_out, node_shader_main):
        """Get the list of texture names for Principled BSDF shaders."""

        tex_list = [None] * 15 
        color_list = [None] * 15
        alpha_val = 1.0

        # Alpha should be mexed in from a math node
        shader_input = node_out.inputs[0]  # Transparency
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
        
        # Height/Ambient Occlusion 
        # NWN = 4, Plugged directly into material output

        # Emissive/Illumination
        # NWN = 5, Emissive Shader mixed into Principled BSDF
        shader_input = node_out.inputs[0]
        tex_list[5], color_list[5] = Nodes.get_emissive_map(shader_input)

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

        # Height/Ambient Occlusion (NWN = 4, Eevee Specular = 9)
        shader_input = node_shader_main.inputs[9]  # Ambient Occlusion
        tex_list[4], color_list[4] = Nodes.get_texture_map(shader_input)

        # Emissive/Illumination (NWN = 5, Eevee Specular = 3)
        shader_input = node_shader_main.inputs[3]  # Emissive Color
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

        node_out = Nodes.get_output_node(nodes)

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
            tex_list, col_list, alpha = Nodes.get_node_data_bsdf(
                node_out, node_main_shader)
        elif node_main_shader.type == 'EEVEE_SPECULAR':
            tex_list, col_list, alpha = Nodes.get_node_data_spec(
                node_out, node_main_shader)

        return tex_list, col_list, alpha
     
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
        node_out.location = (797.0, 623.0)

        node_shd_bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        node_shd_bsdf.location = (-123.0, 280.0)

        node_shd_trans = nodes.new('ShaderNodeBsdfTransparent')
        node_shd_trans.label = "Shader: Transparent"
        node_shd_trans.name = "shd_transparent"
        node_shd_trans.location = (-119.0, 541.0)

        node_shd_mix_trans = nodes.new('ShaderNodeMixShader')
        node_shd_mix_trans.label = "Mix: Transparency"
        node_shd_mix_trans.name = "mix_transparency"
        node_shd_mix_trans.location = (492.0, 646.0)
        node_shd_mix_trans.inputs[0].default_value = alpha

        node_math_trans = nodes.new('ShaderNodeMath')
        node_math_trans.label = "Aurora Alpha"
        node_math_trans.name = "math_aurora_alpha"
        node_math_trans.location = (-511.0, 621.0)
        node_math_trans.operation = 'MULTIPLY'
        node_math_trans.use_clamp = True
        node_math_trans.inputs[1].default_value = alpha

        node_shd_emit = nodes.new('ShaderNodeEmission')
        node_shd_emit.label = "Shader: Emission"
        node_shd_emit.name = "shd_emission"
        node_shd_emit.location = (-125.0, 442.0)

        node_shd_mix_emit = nodes.new('ShaderNodeMixShader')
        node_shd_mix_emit.label = "Mix: Emission"
        node_shd_mix_emit.name = "mix_emission"
        node_shd_mix_emit.location = (251, 400.0)
        node_shd_mix_emit.inputs[0].default_value = 0.5

        # Setup: 
        #                     Math Multiply    =>
        #                     Transparent BSDF =>
        #                                         Mix Transp => Output 
        # Emission         =>               
        #                     Mix Emit         =>
        # Principled BSDF  =>
        links.new(node_out.inputs[0], node_shd_mix_trans.outputs[0])
        
        links.new(node_shd_mix_trans.inputs[0], node_math_trans.outputs[0])
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
            node_tex_diff.label = "Texture: Diffuse"
            node_tex_diff.name = "tex_diffuse"
            node_tex_diff.location = (-1195.0, 205.0)

            node_tex_diff.image = nvb_utils.create_image(
                texture_list[0], img_filepath, img_search)
            node_tex_diff.color_space = 'COLOR'

            links.new(node_shd_bsdf.inputs[0], node_tex_diff.outputs[0])
            links.new(node_math_trans.inputs[0], node_tex_diff.outputs[1])

         # 1 = Normal
        if texture_list[1]:
            # Setup: Image Texture => Normal Map => Principled BSDF
            node_tex_norm = nodes.new('ShaderNodeTexImage')   
            node_tex_norm.label = "Texture: Normal"
            node_tex_norm.name = "tex_normal"
            node_tex_norm.location = (-668.0, -267.0)

            node_tex_norm.image = nvb_utils.create_image(
                texture_list[1], img_filepath, img_search)
            node_tex_norm.color_space = 'NONE'  # Not rgb data

            node_norm = nodes.new('ShaderNodeNormalMap')
            node_norm.location = (-328.0, -166.0)

            links.new(node_norm.inputs[1], node_tex_norm.outputs[0])
            links.new(node_shd_bsdf.inputs[17], node_norm.outputs[0])

         # 2 = Specular
        if texture_list[2]:
            # Setup: Image Texture => Principled BSDF
            node_tex_spec = nodes.new('ShaderNodeTexImage')
            node_tex_spec.label = "Texture: Specular"
            node_tex_spec.name = "tex_specular"
            node_tex_spec.location = (-894.0, 93.0)

            node_tex_spec.image = nvb_utils.create_image(
                texture_list[2], img_filepath, img_search)
            node_tex_norm.color_space = 'NONE'  # Not rgb data

            links.new(node_shd_bsdf.inputs[5], node_tex_spec.outputs[0])

        # 3 = Roughness
        if texture_list[3]:
            # Setup: Image Texture => Principled BSDF
            node_tex_rough = nodes.new('ShaderNodeTexImage')
            node_tex_rough.label = "Texture: Roughness"
            node_tex_rough.name = "tex_roughness"
            node_tex_rough.location = (-612.0, 46.0)

            node_tex_norm.image = nvb_utils.create_image(
                texture_list[3], img_filepath, img_search)
            node_tex_norm.color_space = 'NONE'  # Not rgb data

            links.new(node_shd_bsdf.inputs[7], node_tex_rough.outputs[0])

        # 4 = Illumination/ Emission/ Glow
        node_shd_emit.inputs[0].default_value = color_list[4]
        if texture_list[4]:
            # Setup: 
            # Image Texture => Emission Shader => 
            #                                     Mix Shader => Material Output
            #                  Principled BSDF => 
            node_tex_emit = nodes.new('ShaderNodeTexImage')
            node_tex_emit.label = "Texture: Emissive"
            node_tex_emit.name = "tex_emissive"
            node_tex_emit.location = (-510.0, 420.0)

            node_tex_norm.image = nvb_utils.create_image(
                texture_list[4], img_filepath, img_search)
            node_tex_norm.color_space = 'COLOR'

            links.new(node_shd_emit.inputs[0], node_tex_emit.outputs[0])

        # 5 = Height/AO/Parallax
        if texture_list[5]:
            # Setup: Image Texture => Displacement => Material Output
            node_tex_height = nodes.new('ShaderNodeTexImage')
            node_tex_height.label = "Texture: Height"
            node_tex_height.name = "tex_height"
            node_tex_height.label = (243.0, 154.0)

            node_tex_norm.image = nvb_utils.create_image(
                texture_list[5], img_filepath, img_search)
            node_tex_norm.color_space = 'NONE'  # Not rgb data

            node_displ = nodes.new('ShaderNodeDisplacement')
            node_displ.location = (546.0, 210.0)

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
        node_out.location = (790.0, 384.0)

        node_shader_spec = nodes.new('ShaderNodeEeveeSpecular')
        node_shader_spec.location = (564.0, 359.0)

        links.new(node_out.inputs['Surface'], 
                  node_shader_spec.outputs['BSDF'])
        
        # Add texture maps

        # 0 = Diffuse = Base Color
        node_shader_spec.inputs[0].default_value = color_list[0]

        # Setup: Image Texture (Alpha) => Math (Multiply mdl alpha)
        #        => Invert => Eevee Specular (Tranparency)
        node_invert = nodes.new('ShaderNodeInvert')
        node_invert.label = "Alpha to Transparency"
        node_invert.name = "invert_alpha2trans"
        node_invert.location = (19.0, -7.0)

        node_math = nodes.new('ShaderNodeMath')
        node_math.label = "Aurora Alpha"
        node_math.name = "math_aurora_alpha"
        node_math.location = (-532.0, -54.0)
        node_math.operation = 'MULTIPLY'
        node_math.use_clamp = True
        node_math.inputs[1].default_value = alpha

        links.new(node_invert.inputs[1], node_math.outputs[0])                     
        links.new(node_shader_spec.inputs[4], node_invert.outputs[0])
        if texture_list[0]:           
            # Setup: Image Texture (Color) => Eevee Specular (Base Color)           
            node_tex_diff = nodes.new('ShaderNodeTexImage')
            node_tex_diff.label = "Texture: Diffuse"
            node_tex_diff.name = "tex_diffuse"
            node_tex_diff.location = (-1125.0, 715.0)

            node_tex_diff.image = nvb_utils.create_image(
                texture_list[0], img_filepath, img_search)
            node_tex_diff.color_space = 'COLOR'

            links.new(node_shader_spec.inputs[0], node_tex_diff.outputs[0])
            links.new(node_math.inputs[0], node_tex_diff.outputs[1])

        # 1 = Normal
        if texture_list[1]:
            # Setup: Image Texture => Normal Map => Eevee Specular
            node_tex_norm = nodes.new('ShaderNodeTexImage')      
            node_tex_norm.label = "Texture: Normal"
            node_tex_norm.name = "tex_normal"
            node_tex_norm.location = (-179.0, -174.0)

            node_tex_norm.image = nvb_utils.create_image(
                texture_list[1], img_filepath, img_search)
            node_tex_norm.color_space = 'NONE'  # Not rgb data

            node_normal = nodes.new('ShaderNodeNormalMap')
            node_normal.location = (191.0, -71.0)

            links.new(node_normal.inputs[1], node_tex_norm.outputs[0])
            links.new(node_shader_spec.inputs[5], node_normal.outputs[0])

        # 2 = Specular
        node_shader_spec.inputs[1].default_value = color_list[2]
        if texture_list[2]:
            # Setup: Image Texture => Eevee Specular
            node_tex_spec = nodes.new('ShaderNodeTexImage')
            node_tex_spec.label = "Texture: Specular"
            node_tex_spec.name = "tex_specular"
            node_tex_spec.location = (-675.0, 530.0)

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
            node_tex_rough.location = (-369.0, 376.0)

            node_tex_rough.image = nvb_utils.create_image(
                texture_list[3], img_filepath, img_search)
            node_tex_rough.color_space = 'NONE'  # Single channel

            links.new(node_shader_spec.inputs[2], node_tex_rough.outputs[0])

        # 4 = Illumination/ Emission/ Glow
        node_shader_spec.inputs[3].default_value = color_list[4]
        if texture_list[4]:
            # Setup: Image Texture => Eevee Specular (Emissive)
            node_tex_emit = nodes.new('ShaderNodeTexImage') 
            node_tex_emit.label = "Texture: Emissive"
            node_tex_emit.name = "tex_emissive"
            node_tex_emit.location = (-63.0, 267.0)

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
            node_tex_height.location = (105.0, -267.0)

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
        for blender_mat in bpy.data.materials:
            tex_list, col_list, alpha = Nodes.get_node_data(blender_mat)
            #if ( (tex_list == self.texture_list) and
            #     (col_list == self.color_list) and 
            #     math.isclose(alpha, self.alpha) ):
            if ( (tex_list == self.texture_list) and
                 math.isclose(alpha, self.alpha) ):
                return blender_mat
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
            Nodes.add_node_data(blender_mat, options.mat_shader,
                                self.texture_list, self.color_list, self.alpha,
                                options.filepath, options.tex_search)
        return blender_mat

    @staticmethod
    def generate_default_values(ascii_lines):
        """Write default material values to ascii."""
        ascii_lines.append('  ambient 1.00 1.00 1.00')
        ascii_lines.append('  diffuse 1.00 1.00 1.00')
        ascii_lines.append('  specular 0.00 0.00 0.00')
        ascii_lines.append('  bitmap ' + nvb_def.null)

    @staticmethod
    def generate_ascii(obj, ascii_lines, options):
        """Write Ascii lines from the objects material for a MDL file."""
        material = obj.active_material
        if obj.nvb.render and material:
            tex_list, col_list, alpha = Nodes.get_node_data(material)
            # Write colors
            fstr = '  ambient {:3.2f} {:3.2f} {:3.2f}'
            ascii_lines.append(fstr.format([1.0] * 3))
            fstr = '  diffuse {:3.2f} {:3.2f} {:3.2f}'
            ascii_lines.append(fstr.format(*col_list[0]))
            fstr = '  specular {:3.2f} {:3.2f} {:3.2f}'
            ascii_lines.append(fstr.format(*col_list[2]))
            # Write textures
            if material.nvb.usemtr:
                mtrname = material.nvb.mtrname
                ascii_lines.append('  ' + options.mtr_ref + ' ' + mtrname)
                options.mtrdb.add(material.name)  # export later on demand
            else:
                # Add Renderhint
                if (len(tex_list) > 1):
                    ascii_lines.append('  renderhint NormalAndSpecMapped')
                # Export texture[0] as "bitmap", not "texture0"
                if len(tex_list) > 0:
                    ascii_lines.append('  bitmap ' + tex_list[0])
                else:
                    ascii_lines.append('  bitmap ' + nvb_def.null)
                # Export texture1 and texture2
                fstr = '  texture{:d} {:s}'
                ascii_lines.extend([fstr.format(i, t) for i, t in enumerate(tex_list[1:3])])
            # Write Alpha
            if not math.isclose(alpha, 1.0, rel_tol=0.01):  # Omit 1.0
                fstr = '  alpha {: 3.2f}'
                ascii_lines.append(fstr.format(alpha))
        else:
            Material.generate_default_values(ascii_lines)
