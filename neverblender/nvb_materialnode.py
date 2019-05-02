"""TODO: DOC."""

import os

from . import nvb_utils
from . import nvb_def

class Materialnode(object):
    """Collection of function for dealing with shader nodes."""

    @staticmethod
    def find_alpha_socket(node):
        """Get the socket from which to take alpha. May be None."""
        if not node:
            return None
        if node.type == 'OUTPUT_MATERIAL':  # Go down the node tree
            socket = node.inputs[0]  # 0 = Surface
            if socket.is_linked:
                return Materialnode.find_alpha_socket(socket.links[0].from_node)
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
                return Materialnode.find_alpha_socket(socket.links[0].from_node)
        elif node.type == 'INVERT':  # Go down the node tree
            socket = node.inputs[1]  # 1 = Color
            if socket.is_linked:
                return Materialnode.find_alpha_socket(socket.links[0].from_node)
        elif node.type == 'MIX_SHADER':  # Go down the node tree
            socket = node.inputs[0]  # 0 = Factor
            if socket.is_linked:
                return Materialnode.find_alpha_socket(socket.links[0].from_node)
        return None

    @staticmethod
    def find_diffuse_socket(node):
        """Get the socket from which to take diffuse data. May be None."""
        if not node:
            return None
        if node.type == 'OUTPUT_MATERIAL':  # Go down the node tree
            socket = node.inputs[0]  # 0 = Surface
            if socket.is_linked:
                return Materialnode.find_diffuse_socket(socket.links[0].from_node)
        elif node.type == 'EEVEE_SPECULAR':  # Return this sockett
            return node.inputs[0]  # 0 = Base Color
        elif node.type == 'BSDF_PRINCIPLED':  # Return this socket
            return node.inputs[0]  #  0 = Base Color
        elif node.type == 'MIX_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[1]
            nodeA = None
            if socketA.is_linked:
                nodeA = Materialnode.find_diffuse_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[2]
            nodeB = None
            if socketB.is_linked:
                nodeB = Materialnode.find_diffuse_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'ADD_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[0]
            nodeA = None
            if socketA.is_linked:
                nodeA = Materialnode.find_diffuse_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[1]
            nodeB = None
            if socketB.is_linked:
                nodeB = Materialnode.find_diffuse_socket(socketB.links[0].from_node)
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
                return Materialnode.find_emissive_socket(socket.links[0].from_node)
        elif node.type == 'EMISSION':  # # Return this socket
            return node.inputs[0]  # Color
        elif node.type == 'EEVEE_SPECULAR':  # # Return this socket
            return node.inputs[3]  # Emissive Color
        elif node.type == 'MIX_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[1]
            nodeA = None
            if socketA.is_linked:
                nodeA = Materialnode.find_emissive_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[2]
            nodeB = None
            if socketB.is_linked:
                nodeB = Materialnode.find_emissive_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'ADD_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[0]
            nodeA = None
            if socketA.is_linked:
                nodeA = Materialnode.find_emissive_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[1]
            nodeB = None
            if socketB.is_linked:
                nodeB = Materialnode.find_emissive_socket(socketB.links[0].from_node)
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
                nodeA = Materialnode.find_height_socket(socketA.links[0].from_node)
            socketB = node.inputs[2]  # Displacement
            nodeB = None
            if socketB.is_linked:
                nodeB = Materialnode.find_height_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'EEVEE_SPECULAR':  # Go down the node tree
            socket = node.inputs[9]  # Ambient Occlusion
            if socket.is_linked:
                return Materialnode.find_height_socket(socket.links[0].from_node)
        elif node.type == 'DISPLACEMENT':  # Return this socket
            return node.inputs[0]  # 0 = Height
        elif node.type == 'MIX_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[1]
            nodeA = None
            if socketA.is_linked:
                nodeA = Materialnode.find_height_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[2]
            nodeB = None
            if socketB.is_linked:
                nodeB = Materialnode.find_height_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'ADD_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[0]
            nodeA = None
            if socketA.is_linked:
                nodeA = Materialnode.find_height_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[1]
            nodeB = None
            if socketB.is_linked:
                nodeB = Materialnode.find_height_socket(socketB.links[0].from_node)
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
                nodeA = Materialnode.find_normal_socket(socketA.links[0].from_node)
            # Displacement
            socketB = node.inputs[2]
            nodeB = None
            if socketB.is_linked:
                nodeB = Materialnode.find_normal_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'EEVEE_SPECULAR':  # Go down the node tree
            socket = node.inputs[5]  # 5 = Normal
            if socket.is_linked:
                return Materialnode.find_normal_socket(socket.links[0].from_node)
        elif node.type == 'BSDF_PRINCIPLED':  # Go down the node tree
            socket = node.inputs[17]  # 17 = Normal
            if socket.is_linked:
                return Materialnode.find_normal_socket(socket.links[0].from_node)
        elif node.type == 'DISPLACEMENT':  # Go down the node tree
            socket = node.inputs[3]  # 3 = Normal
            if socket.is_linked:
                return Materialnode.find_normal_socket(socket.links[0].from_node)
        elif node.type == 'NORMAL_MAP':  # Return this socket
            return node.inputs[1]  # 1 = Color
        elif node.type == 'MIX_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[1]
            nodeA = None
            if socketA.is_linked:
                nodeA = Materialnode.find_normal_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[2]
            nodeB = None
            if socketB.is_linked:
                nodeB = Materialnode.find_normal_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'ADD_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[0]
            nodeA = None
            if socketA.is_linked:
                nodeA = Materialnode.find_normal_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[1]
            nodeB = None
            if socketB.is_linked:
                nodeB = Materialnode.find_normal_socket(socketB.links[0].from_node)
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
                return Materialnode.find_roughness_socket(socket.links[0].from_node)
        elif node.type == 'EEVEE_SPECULAR':  # Return this sockett
            return node.inputs[2]  # 2 = Roughness
        elif node.type == 'BSDF_PRINCIPLED':  # Return this socket
            return node.inputs[7]  # 7 = Roughness
        elif node.type == 'MIX_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[1]
            nodeA = None
            if socketA.is_linked:
                nodeA = Materialnode.find_roughness_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[2]
            nodeB = None
            if socketB.is_linked:
                nodeB = Materialnode.find_roughness_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'ADD_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[0]
            nodeA = None
            if socketA.is_linked:
                nodeA = Materialnode.find_roughness_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[1]
            nodeB = None
            if socketB.is_linked:
                nodeB = Materialnode.find_roughness_socket(socketB.links[0].from_node)
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
                return Materialnode.find_specular_socket(socket.links[0].from_node)
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
                nodeA = Materialnode.find_specular_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[2]
            nodeB = None
            if socketB.is_linked:
                nodeB = Materialnode.find_specular_socket(socketB.links[0].from_node)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'ADD_SHADER':  # Go down the node tree
            # Shader A
            socketA = node.inputs[0]
            nodeA = None
            if socketA.is_linked:
                nodeA = Materialnode.find_specular_socket(socketA.links[0].from_node)
            # Shader B
            socketB = node.inputs[1]
            nodeB = None
            if socketB.is_linked:
                nodeB = Materialnode.find_specular_socket(socketB.links[0].from_node)
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
                nodeA = Materialnode.get_texture_node(socketA)
            # Color B
            socketB = node.inputs[2]
            nodeB = None
            if socketB.is_linked:
                nodeB = Materialnode.get_texture_node(socketB)
            # Prefer A over B
            if nodeA:
                return nodeA
            return nodeB
        elif node.type == 'SEPRGB':  # Go down the node tree
            socket = node.inputs[0]  # 0 = Image
            if socket.is_linked:
                return Materialnode.get_texture_node(socket)
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
                    socketA = Materialnode.get_color_socket(node.inputs[1])
                    socketB = Materialnode.get_color_socket(node.inputs[2])
                    if socketA:
                        return socketA
                    return socketB
            elif node.type == 'SEPRGB':
                # RGB Separation, follow input 0 (Image)
                return Materialnode.get_color_socket(node.inputs[0])
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
            texture_node = Materialnode.get_texture_node(input_socket)
            texture = None
            if texture_node:
                texture = Materialnode.get_texture_name(texture_node)

            color_socket = Materialnode.get_color_socket(input_socket)
            color = default_color
            if color_socket:
                color = Materialnode.get_color_value(color_socket, default_color)
            return texture, color

        texture_list = [None] * 15
        color_list = [None] * 15
        alpha = 1.0

        node_out = Materialnode.get_output_node(material)
        if not node_out:
            return texture_list, color_list, alpha  # still empty

        # Alpha should be inverted and plugged into transparency
        input_socket = Materialnode.find_alpha_socket(node_out)
        alpha = Materialnode.get_alpha_value(input_socket)

        # Diffuse (0)
        input_socket = Materialnode.find_diffuse_socket(node_out)
        texture_list[0], color_list[0] = get_data_tuple(input_socket,
                                                        (1.0, 1.0, 1.0, 1.0))

        # Normal (1)
        input_socket = Materialnode.find_normal_socket(node_out)
        texture_list[1], _ = get_data_tuple(input_socket)

        # Specular (2)
        input_socket = Materialnode.find_specular_socket(node_out)
        texture_list[2], color_list[2] = get_data_tuple(input_socket,
                                                        (0.0, 0.0, 0.0, 1.0))

        # Roughness (3)
        input_socket = Materialnode.find_roughness_socket(node_out)
        texture_list[3], _ = get_data_tuple(input_socket)

        # Height/Ambient Occlusion (4)
        input_socket = Materialnode.find_height_socket(node_out)
        texture_list[4], _ = get_data_tuple(input_socket)

        # Emissive/Illumination (5)
        input_socket = Materialnode.find_emissive_socket(node_out)
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
            Materialnode.add_node_data_spec(material,
                                     texture_list, color_list, alpha,
                                     img_filepath, img_search)
        else:
            Materialnode.add_node_data_bsdf(material,
                                     texture_list, color_list, alpha,
                                     img_filepath, img_search)

