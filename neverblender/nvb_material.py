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
    def find_alpha_socket(node):
        """Get the socket from which to take alpha. May be None."""
        if not node:
            return None
        if node.type == 'OUTPUT_MATERIAL':  # Go down the node tree
            socket = node.inputs[0]  # 0 = Surface
            if socket.is_linked:
                return Nodes.find_alpha_socket(socket.links[0].from_node)
        elif node.type == 'MATH':  # Return one of these
            # Use the value from the first unconnected socket
            if not node.inputs[0].links:
                return node.inputs[0]
            if not node.inputs[1].links:
                return node.inputs[1]
            else:
                return None  # No unconnected sockets
        elif node.type == 'EEVEE_SPECULAR':  # Go down the node tree
            socket = node.inputs[4]  # 4 = Transparency
            if socket.is_linked:
                return Nodes.find_alpha_socket(socket.links[0].from_node)
        elif node.type == 'INVERT':  # Go down the node tree
            socket = node.inputs[1]  # 1 = Color
            if socket.is_linked:
                return Nodes.find_alpha_socket(socket.links[0].from_node)
        elif node.type == 'MIX_SHADER':  # Go down the node tree
            socket = node.inputs[0]  # 0 = Factor
            if socket.is_linked:
                return Nodes.find_alpha_socket(socket.links[0].from_node)
        return None

    @staticmethod
    def find_diffuse_socket(node):
        """Get the socket from which to take diffuse data. May be None."""
        if not node:
            return None
        if node.type == 'OUTPUT_MATERIAL':  # Go down the node tree
            socket = node.inputs[0]  # 0 = Surface
            if socket.is_linked:
                return Nodes.find_diffuse_socket(socket.links[0].from_node)
        elif node.type == 'EEVEE_SPECULAR':  # Return this sockett
            return node.inputs[0]  # 0 = Base Color
        elif node.type == 'BSDF_PRINCIPLED':  # Return this socket
            return node.inputs[0]  #  0 = Base Color
        elif node.type == 'MIX_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[1]
            nodeA = None
            if socketA.is_linked:
                nodeA = Nodes.find_diffuse_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[2]
            nodeB = None
            if socketB.is_linked:
                nodeB = Nodes.find_diffuse_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'ADD_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[0]
            nodeA = None
            if socketA.is_linked:
                nodeA = Nodes.find_diffuse_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[1]
            nodeB = None
            if socketB.is_linked:
                nodeB = Nodes.find_diffuse_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB

        return None

    @staticmethod
    def find_emissive_socket(node):
        """Get the socket from which to take emissive data. May be None."""
        if not node:
            return None
        if node.type == 'OUTPUT_MATERIAL':  # Go down the node tree
            socket = node.inputs[0]  # Surface
            if socket.is_linked:
                return Nodes.find_emissive_socket(socket.links[0].from_node)
        elif node.type == 'EMISSION':  # # Return this socket
            return node.inputs[0]  # Color
        elif node.type == 'EEVEE_SPECULAR':  # # Return this socket
            return node.inputs[3]  # Emissive Color
        elif node.type == 'MIX_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[1]
            nodeA = None
            if socketA.is_linked:
                nodeA = Nodes.find_emissive_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[2]
            nodeB = None
            if socketB.is_linked:
                nodeB = Nodes.find_emissive_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'ADD_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[0]
            nodeA = None
            if socketA.is_linked:
                nodeA = Nodes.find_emissive_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[1]
            nodeB = None
            if socketB.is_linked:
                nodeB = Nodes.find_emissive_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB

        return None

    @staticmethod
    def find_height_socket(node):
        """Get the socket from which to take height data. May be None."""
        if not node:
            return None
        if node.type == 'OUTPUT_MATERIAL':  # Go down the node tree
            socketA = node.inputs[0]  # Surface
            nodeA = None
            if socketA.is_linked:
                nodeA = Nodes.find_height_socket(socketA.links[0].from_node)
            socketB = node.inputs[2]  # Displacement
            nodeB = None
            if socketB.is_linked:
                nodeB = Nodes.find_height_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'EEVEE_SPECULAR':  # Go down the node tree
            socket = node.inputs[9]  # Ambient Occlusion
            if socket.is_linked:
                return Nodes.find_height_socket(socket.links[0].from_node)
        elif node.type == 'DISPLACEMENT':  # Return this socket
            return node.inputs[0]  # 0 = Height
        elif node.type == 'MIX_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[1]
            nodeA = None
            if socketA.is_linked:
                nodeA = Nodes.find_height_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[2]
            nodeB = None
            if socketB.is_linked:
                nodeB = Nodes.find_height_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'ADD_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[0]
            nodeA = None
            if socketA.is_linked:
                nodeA = Nodes.find_height_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[1]
            nodeB = None
            if socketB.is_linked:
                nodeB = Nodes.find_height_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB

        return None

    @staticmethod
    def find_normal_socket(node):
        """Get the socket from which to take normal data. May be None."""
        if not node:
            return None
        if node.type == 'OUTPUT_MATERIAL':  # Go down the node tree
            # Surface
            socketA = node.inputs[0]
            nodeA = None
            if socketA.is_linked:
                nodeA = Nodes.find_normal_socket(socketA.links[0].from_node)
            # Displacement
            socketB = node.inputs[2]
            nodeB = None
            if socketB.is_linked:
                nodeB = Nodes.find_normal_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'EEVEE_SPECULAR':  # Go down the node tree
            socket = node.inputs[5]  # 5 = Normal
            if socket.is_linked:
                return Nodes.find_normal_socket(socket.links[0].from_node)
        elif node.type == 'BSDF_PRINCIPLED':  # Go down the node tree
            socket = node.inputs[17]  # 17 = Normal
            if socket.is_linked:
                return Nodes.find_normal_socket(socket.links[0].from_node)
        elif node.type == 'DISPLACEMENT':  # Go down the node tree
            socket = node.inputs[3]  # 3 = Normal
            if socket.is_linked:
                return Nodes.find_normal_socket(socket.links[0].from_node)
        elif node.type == 'NORMAL_MAP':  # Return this socket
            return node.inputs[1]  # 1 = Color
        elif node.type == 'MIX_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[1]
            nodeA = None
            if socketA.is_linked:
                nodeA = Nodes.find_normal_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[2]
            nodeB = None
            if socketB.is_linked:
                nodeB = Nodes.find_normal_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'ADD_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[0]
            nodeA = None
            if socketA.is_linked:
                nodeA = Nodes.find_normal_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[1]
            nodeB = None
            if socketB.is_linked:
                nodeB = Nodes.find_normal_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB

        return None

    @staticmethod
    def find_roughness_socket(node):
        """Get the socket from which to take roughness data. May be None."""
        if not node:
            return None
        if node.type == 'OUTPUT_MATERIAL':  # Go down the node tree
            socket = node.inputs[0]  # 0 = Surface
            if socket.is_linked:
                return Nodes.find_roughness_socket(socket.links[0].from_node)
        elif node.type == 'EEVEE_SPECULAR':  # Return this sockett
            return node.inputs[2]  # 2 = Roughness
        elif node.type == 'BSDF_PRINCIPLED':  # Return this socket
            return node.inputs[7]  # 7 = Roughness
        elif node.type == 'MIX_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[1]
            nodeA = None
            if socketA.is_linked:
                nodeA = Nodes.find_roughness_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[2]
            nodeB = None
            if socketB.is_linked:
                nodeB = Nodes.find_roughness_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'ADD_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[0]
            nodeA = None
            if socketA.is_linked:
                nodeA = Nodes.find_roughness_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[1]
            nodeB = None
            if socketB.is_linked:
                nodeB = Nodes.find_roughness_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB

        return None

    @staticmethod
    def find_specular_socket(node):
        """Get the socket from which to take specular data. May be None."""
        if not node:
            return None
        if node.type == 'OUTPUT_MATERIAL':  # Go down the node tree
            socket = node.inputs[0]  # 0 = Surface
            node = None
            if socket.is_linked:
                return Nodes.find_specular_socket(socket.links[0].from_node)
        elif node.type == 'EEVEE_SPECULAR':  # Return this socket
            socket = node.inputs[1]  # 1 = Specular
            return socket
        elif node.type == 'BSDF_PRINCIPLED':  # Return socket
            socket = node.inputs[5]  # 5 = Specular
            return socket
        elif node.type == 'MIX_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[1]
            nodeA = None
            if socketA.is_linked:
                nodeA = Nodes.find_specular_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[2]
            nodeB = None
            if socketB.is_linked:
                nodeB = Nodes.find_specular_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'ADD_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[0]
            nodeA = None
            if socketA.is_linked:
                nodeA = Nodes.find_specular_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[1]
            nodeB = None
            if socketB.is_linked:
                nodeB = Nodes.find_specular_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB

        return None

    @staticmethod
    def get_output_node(material):
        """Search for the output node in this node list."""
        # Material has to use nodes
        if not material.use_nodes:
            return None

        nodes = material.node_tree.nodes
        # No nodes or no links
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
    def get_texture_node(socket):
        """Get texture node. May be none."""
        if not socket or not socket.is_linked:
            return None
        node = socket.links[0].from_node

        if node.type.startswith('TEX_'):  # Return this node
            return node
        elif node.type == 'MIX_RGB':  # Go down the node tree
            # Color A
            socketA = node.inputs[1]
            nodeA = None
            if socketA.is_linked:
                nodeA = Nodes.get_texture_node(socketA)
            # Color B
            socketB = node.inputs[2]
            nodeB = None
            if socketB.is_linked:
                nodeB = Nodes.get_texture_node(socketB)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'SEPRGB':  # Go down the node tree
            socket = node.inputs[0]  # 0 = Image
            if socket.is_linked:
                return Nodes.get_texture_node(socket)
        return None

    @staticmethod
    def get_color_socket(socket):
        """Get ta color socket connected to this socket. May be none."""
        if not socket:
            return None

        if socket.is_linked:
            node = socket.links[0].from_node

            if node.type == 'MIX_RGB':
                # Mix node, grab color from first unlinked node
                if not node.inputs[1].is_linked:
                    return node.inputs[1]
                elif not node.inputs[2].is_linked:
                    return node.inputs[2]
                else:  # Both sockets are linked
                    socketA = Nodes.get_color_socket(node.inputs[1])
                    socketB = Nodes.get_color_socket(node.inputs[2])
                    if socketA:
                        return socketA
                    return socketB
            elif node.type == 'SEPRGB':
                # RGB Separation, follow input 0 (Image)
                return Nodes.get_color_socket(node.inputs[0])
            elif node.type == 'RGB':  # Return the output socket
                return node.outputs[0]
        elif socket.type == 'RGBA':
            return socket
        return None

    @staticmethod
    def get_alpha_value(alpha_socket, fail_value=1.0):
        """Get tha alpha value from the socket."""
        if alpha_socket:
            return alpha_socket.default_value
        return fail_value

    @staticmethod
    def get_color_value(color_socket, fail_value=(1.0, 1.0, 1.0, 1.0)):
        """Get tha alpha value from the socket."""
        if color_socket:
            return color_socket.default_value
        return fail_value

    @staticmethod
    def get_texture_name(texture_node, fail_value="ERROR"):
        """Get a texture from a texture node."""
        # No texture node: None=Null
        if not texture_node:
            return None
        # texture node has no image: Use node label
        img = texture_node.image
        if not img:
            if texture_node.label:
                return texture_node.label
            else:
                return fail_value
        # Get name from filepath or (Blender's) image name
        if img.filepath:
            return os.path.splitext(os.path.basename(img.filepath))[0]
        elif img.name:
            return os.path.splitext(os.path.basename(img.name))[0]
        return fail_value

    @staticmethod
    def get_node_data(material):
        """Get the list of texture names for this material."""
        def get_data_tuple(input_node, default_color=(1.0, 1.0, 1.0, 1.0)):
            """Get texture and color from an input name."""
            texture_node = Nodes.get_texture_node(input_socket)
            texture = None
            if texture_node:
                texture = Nodes.get_texture_name(texture_node)

            color_socket = Nodes.get_color_socket(input_socket)
            color = default_color
            if color_socket:
                color = Nodes.get_color_value(color_socket, default_color)
            return texture, color

        texture_list = [None] * 15
        color_list = [None] * 15
        alpha = 1.0

        node_out = Nodes.get_output_node(material)
        if not node_out:
            return texture_list, color_list, alpha  # still empty

        # Alpha should be inverted and plugged into transparency
        input_socket = Nodes.find_alpha_socket(node_out)
        alpha = Nodes.get_alpha_value(input_socket)

        # Diffuse (0)
        input_socket = Nodes.find_diffuse_socket(node_out)
        texture_list[0], color_list[0] = get_data_tuple(input_socket,
                                                        (1.0, 1.0, 1.0, 1.0))

        # Normal (1)
        input_socket = Nodes.find_normal_socket(node_out)
        texture_list[1], _ = get_data_tuple(input_socket)

        # Specular (2)
        input_socket = Nodes.find_specular_socket(node_out)
        texture_list[2], color_list[2] = get_data_tuple(input_socket,
                                                        (0.0, 0.0, 0.0, 1.0))

        # Roughness (3)
        input_socket = Nodes.find_roughness_socket(node_out)
        texture_list[3], _ = get_data_tuple(input_socket)

        # Height/Ambient Occlusion (4)
        input_socket = Nodes.find_height_socket(node_out)
        texture_list[4], _ = get_data_tuple(input_socket)

        # Emissive/Illumination (5)
        input_socket = Nodes.find_emissive_socket(node_out)
        texture_list[5], color_list[5] = get_data_tuple(input_socket,
                                                        (0.0, 0.0, 0.0, 1.0))

        return texture_list, color_list, alpha

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
        node_shd_mix_trans.name = "shd_transparency_mix"
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

        node_shd_add_emit = nodes.new('ShaderNodeAddShader')
        node_shd_add_emit.label = "Add: Emission"
        node_shd_add_emit.name = "shd_emission_add"
        node_shd_add_emit.location = (251, 400.0)

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
        links.new(node_shd_mix_trans.inputs[2], node_shd_add_emit.outputs[0])

        links.new(node_shd_add_emit.inputs[0], node_shd_emit.outputs[0])
        links.new(node_shd_add_emit.inputs[1], node_shd_bsdf.outputs[0])

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

        # 4 = Height/AO/Parallax
        if texture_list[4]:
            # Setup: Image Texture => Displacement => Material Output
            node_tex_height = nodes.new('ShaderNodeTexImage')
            node_tex_height.label = "Texture: Height"
            node_tex_height.name = "tex_height"
            node_tex_height.label = (243.0, 154.0)

            node_tex_norm.image = nvb_utils.create_image(
                texture_list[4], img_filepath, img_search)
            node_tex_norm.color_space = 'NONE'  # Not rgb data

            node_displ = nodes.new('ShaderNodeDisplacement')
            node_displ.location = (546.0, 210.0)

            links.new(node_displ.inputs[0], node_tex_height.outputs[0])
            links.new(node_out.inputs[2], node_displ.outputs[0])

        # 5 = Illumination/ Emission/ Glow
        node_shd_emit.inputs[0].default_value = color_list[5]
        if texture_list[5]:
            # Setup:
            # Image Texture => Emission Shader =>
            #                                     Mix Shader => Material Output
            #                  Principled BSDF =>
            node_tex_emit = nodes.new('ShaderNodeTexImage')
            node_tex_emit.label = "Texture: Emissive"
            node_tex_emit.name = "tex_emissive"
            node_tex_emit.location = (-510.0, 420.0)

            node_tex_norm.image = nvb_utils.create_image(
                texture_list[5], img_filepath, img_search)
            node_tex_norm.color_space = 'COLOR'

            links.new(node_shd_emit.inputs[0], node_tex_emit.outputs[0])

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

        # 4 = Height (use as Ambient Occlusion)
        if texture_list[4]:
            # Setup: Image Texture => Eevee Specular (Ambient Occlusion)
            node_tex_height = nodes.new('ShaderNodeTexImage')
            node_tex_height.label = "Texture: Height"
            node_tex_height.name = "tex_height"
            node_tex_height.location = (105.0, -267.0)

            node_tex_height.image = nvb_utils.create_image(
                texture_list[4], img_filepath, img_search)
            node_tex_height.color_space = 'NONE'  # Single channel

            links.new(node_shader_spec.inputs[9], node_tex_height.outputs[0])

        # 5 = Illumination/ Emission/ Glow
        node_shader_spec.inputs[3].default_value = color_list[5]
        if texture_list[5]:
            # Setup: Image Texture => Eevee Specular (Emissive)
            node_tex_emit = nodes.new('ShaderNodeTexImage')
            node_tex_emit.label = "Texture: Emissive"
            node_tex_emit.name = "tex_emissive"
            node_tex_emit.location = (-63.0, 267.0)

            node_tex_emit.image = nvb_utils.create_image(
                texture_list[5], img_filepath, img_search)
            node_tex_emit.color_space = 'NONE'  # Single channel

            links.new(node_shader_spec.inputs[3], node_tex_emit.outputs[0])

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
        for blender_mat in bpy.data.materials:
            tex_list, col_list, alpha = Nodes.get_node_data(blender_mat)
            # Compare textures, emissive color(5) and alpha
            if ( (tex_list == self.texture_list) and
                 Material.colorisclose(col_list[5], self.color_list[5]) and
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
    def generate_ascii(obj, ascii_lines, options):
        """Write Ascii lines from the objects material for a MDL file."""
        material = obj.active_material
        if obj.hide_render and material:
            tex_list = [None] * 15
            col_list = [None] * 15
            alpha = 1.0
            tex_list, col_list, alpha = Nodes.get_node_data(material)
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
                if (len(tex_list) > 1):
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
