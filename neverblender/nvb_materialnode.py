"""TODO: DOC."""

import os

from . import nvb_utils


class Materialnode(object):
    """Collection of function for dealing with shader nodes."""

    @staticmethod
    def is_texture_node(node):
        """Return true if this socket is a texture socket."""
        return node.type.startswith('TEX_')

    @staticmethod
    def get_node_identifier(node, fallback_to_name=False):
        """Return node label if specified or the (unique) node name."""
        if node.label:
            return node.label
        elif fallback_to_name:
            return node.name
        return "ERROR"

    @staticmethod
    def find_alpha_socket(node):
        """Get the socket from which to take alpha. May be None."""
        if node:
            if node.type == 'OUTPUT_MATERIAL':
                sock = node.inputs['Surface']
                if sock.is_linked:
                    return Materialnode.find_alpha_socket(sock.links[0].from_node)
            elif node.type == 'MATH':
                # Use the value from the first unconnected! socket
                if not node.inputs[0].is_linked:
                    return node.inputs[0]
                if not node.inputs[1].is_linked:
                    return node.inputs[1]
                else:
                    return None  # No unconnected sockets
            elif node.type == 'EEVEE_SPECULAR':
                # This will need to be inverted
                sock = node.inputs['Transparency']
                if sock.is_linked:
                    return Materialnode.find_alpha_socket(sock.links[0].from_node)
            elif node.type == 'BSDF_PRINCIPLED':
                # If nothing is connected to this, we can use the default value as well
                sock = node.inputs['Alpha']
                if sock.is_linked:
                    return Materialnode.find_alpha_socket(sock.links[0].from_node)
                else:
                    return sock
            elif node.type == 'INVERT':
                sock = node.inputs['Color']
                if sock.is_linked:
                    return Materialnode.find_alpha_socket(sock.links[0].from_node)
        return None

    @staticmethod
    def find_diffuse_socket(node):
        """Get the socket from which to take diffuse data. May be None."""
        if node:
            if node.type == 'OUTPUT_MATERIAL':  # Go down the node tree
                socket = node.inputs['Surface']
                if socket.is_linked:
                    return Materialnode.find_diffuse_socket(socket.links[0].from_node)
            elif node.type in ['EEVEE_SPECULAR', 'BSDF_PRINCIPLED']:
                return node.inputs['Base Color']
            elif node.type == 'MIX_SHADER':
                # Try socket 1 (socket 0 is a factor) 
                sock = node.inputs[1]
                if sock.is_linked:
                    sub_node = Materialnode.find_diffuse_socket(sock.links[0].from_node) 
                    # Can't return None yet, we need to try the other socket
                    if sub_node:
                        return sub_node
                # Socket 1 doesn't contain anything, try 2
                sock = node.inputs[2]
                if sock.is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_diffuse_socket(sock.links[0].from_node) 
                # Nothing here
                return None
            elif node.type == 'ADD_SHADER':
                # Try socket 0
                sock = node.inputs[0]
                if sock.is_linked:
                    sub_node = Materialnode.find_diffuse_socket(sock.links[0].from_node) 
                    # Can't return None yet, we need to try the other socket
                    if sub_node:
                        return sub_node
                # Socket 0 doesn't contain anything, try 1
                sock = node.inputs[1]
                if sock.is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_diffuse_socket(sock.links[0].from_node) 
                # Nothing here
                return None

        return None

    @staticmethod
    def find_emissive_socket(node):
        """Get the socket from which to take emissive data. May be None."""
        if node:
            if node.type == 'OUTPUT_MATERIAL':
                sock = node.inputs['Surface']
                if sock.is_linked:
                    return Materialnode.find_emissive_socket(sock.links[0].from_node)
            elif node.type == 'EMISSION':
                return node.inputs['Color']
            elif node.type == 'EEVEE_SPECULAR':
                return node.inputs['Emissive Color']
            elif node.type == 'BSDF_PRINCIPLED':
                return node.inputs['Emission']
            elif node.type == 'MIX_SHADER':
                # Try socket 1 (socket 0 is a factor) 
                sock = node.inputs[1]
                if sock.is_linked:
                    sub_node = Materialnode.find_emissive_socket(sock.links[0].from_node) 
                    # Can't return None yet, we need to try the other socket
                    if sub_node:
                        return sub_node
                # Socket 1 doesn't contain anything, try 2
                sock = node.inputs[2]
                if sock.is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_emissive_socket(sock.links[0].from_node) 
                # Nothing here
                return None
            elif node.type == 'ADD_SHADER':
                # Try socket 0
                sock = node.inputs[0]
                if sock.is_linked:
                    sub_node = Materialnode.find_emissive_socket(sock.links[0].from_node) 
                    # Can't return None yet, we need to try the other socket
                    if sub_node:
                        return sub_node
                # Socket 0 doesn't contain anything, try 1
                sock = node.inputs[1]
                if sock.is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_emissive_socket(sock.links[0].from_node) 
                # Nothing here
                return None

        return None

    @staticmethod
    def find_height_socket(node):
        """Get the socket from which to take height data. May be None. """
        if node:
            # There are two options for finding a heightmap:
            # 1. Output (Displacement Socket) => Displacement Node
            # 2. Output (Surface Socket) => Specular Shader => Ambient Occlusion Node
            # We prefer 1. over 2.
            if node.type == 'OUTPUT_MATERIAL':
                # Try going down the diplacement socket first
                sock_displacement = node.inputs['Displacement']
                if sock_displacement.is_linked:
                    node_displacement = Materialnode.find_height_socket(sock_displacement.links[0].from_node)
                    # Might not be present
                    if node_displacement:
                        return node_displacement
                # If displacement didn't work try looking for Ambiet Occlusion
                sock_surface = node.inputs['Surface']
                if sock_surface.is_linked:
                    # Can safely return None, nothing left to try
                    return Materialnode.find_height_socket(sock_surface.links[0].from_node)
            elif node.type == 'EEVEE_SPECULAR':
                sock = node.inputs['Ambient Occlusion']
                if sock.is_linked:
                    # Return this socket if linked directly to a texture
                    linked_node = sock.links[0].from_node
                    if Materialnode.is_texture_node(linked_node):
                        return sock
                    else:
                        return Materialnode.find_height_socket(linked_node)
            elif node.type == 'DISPLACEMENT':
                return node.inputs[0]  # 0 = Height
            elif node.type == 'AMBIENT_OCCLUSION':
                return node.inputs[1]  # 0 = Distance
            elif node.type == 'MIX_SHADER':
                # Try socket 1 (socket 0 is a factor) 
                sock = node.inputs[1]
                if sock.is_linked:
                    sub_node = Materialnode.find_height_socket(sock.links[0].from_node) 
                    # Can't return None yet, we need to try the other socket
                    if sub_node:
                        return sub_node
                # Socket 1 doesn't contain anything, try 2
                sock = node.inputs[2]
                if sock.is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_height_socket(sock.links[0].from_node) 
                # Nothing here
                return None
            elif node.type == 'ADD_SHADER':
                # Try socket 0
                sock = node.inputs[0]
                if sock.is_linked:
                    sub_node = Materialnode.find_height_socket(sock.links[0].from_node) 
                    # Can't return None yet, we need to try the other socket
                    if sub_node:
                        return sub_node
                # Socket 0 doesn't contain anything, try 1
                sock = node.inputs[1]
                if sock.is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_height_socket(sock.links[0].from_node) 
                # Nothing here
                return None

        return None

    @staticmethod
    def find_normal_socket(node):
        """Get the socket from which to take normal data. May be None."""
        if node:
            if node.type == 'OUTPUT_MATERIAL':  # Go down the node tree
                # If displacement didn't work try looking for Ambiet Occlusion
                sock_surface = node.inputs['Surface']
                if sock_surface.is_linked:
                    sock_surface = Materialnode.find_normal_socket(sock_surface.links[0].from_node)
                     # Might not be present
                    if sock_surface:
                        return sock_surface  
                # Try going down the diplacement socket first
                sock_displacement = node.inputs['Displacement']
                if sock_displacement.is_linked:
                    # Can safely return None, nothing left to try
                    return Materialnode.find_normal_socket(sock_displacement.links[0].from_node)
            elif node.type in ['EEVEE_SPECULAR', 'BSDF_PRINCIPLED', 'DISPLACEMENT']:
                socket = node.inputs['Normal']
                if socket.is_linked:
                    return Materialnode.find_normal_socket(socket.links[0].from_node)
            elif node.type == 'NORMAL_MAP':
                return node.inputs['Color']
            elif node.type == 'MIX_SHADER':
                # Try socket 1 (socket 0 is a factor) 
                sock = node.inputs[1]
                if sock.is_linked:
                    sub_node = Materialnode.find_normal_socket(sock.links[0].from_node) 
                    # Can't return None yet, we need to try the other socket
                    if sub_node:
                        return sub_node
                # Socket 1 doesn't contain anything, try 2
                sock = node.inputs[2]
                if sock.is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_normal_socket(sock.links[0].from_node) 
                # Nothing here
                return None
            elif node.type == 'ADD_SHADER':
                # Try socket 0
                sock = node.inputs[0]
                if sock.is_linked:
                    sub_node = Materialnode.find_normal_socket(sock.links[0].from_node) 
                    # Can't return None yet, we need to try the other socket
                    if sub_node:
                        return sub_node
                # Socket 0 doesn't contain anything, try 1
                sock = node.inputs[1]
                if sock.is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_normal_socket(sock.links[0].from_node) 
                # Nothing here
                return None

        return None

    @staticmethod
    def find_roughness_socket(node):
        """Get the socket from which to take roughness data. May be None."""
        if node:
            if node.type == 'OUTPUT_MATERIAL':  # Go down the node tree
                socket = node.inputs['Surface']
                if socket.is_linked:
                    return Materialnode.find_roughness_socket(socket.links[0].from_node)
            elif node.type in ['EEVEE_SPECULAR', 'BSDF_PRINCIPLED']:
                return node.inputs['Roughness']
            elif node.type == 'MIX_SHADER':
                # Try socket 1 (socket 0 is a factor) 
                sock = node.inputs[1]
                if sock.is_linked:
                    sub_node = Materialnode.find_roughness_socket(sock.links[0].from_node) 
                    # Can't return None yet, we need to try the other socket
                    if sub_node:
                        return sub_node
                # Socket 1 doesn't contain anything, try 2
                sock = node.inputs[2]
                if sock.is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_roughness_socket(sock.links[0].from_node) 
                # Nothing here
                return None
            elif node.type == 'ADD_SHADER':
                # Try socket 0
                sock = node.inputs[0]
                if sock.is_linked:
                    sub_node = Materialnode.find_roughness_socket(sock.links[0].from_node) 
                    # Can't return None yet, we need to try the other socket
                    if sub_node:
                        return sub_node
                # Socket 0 doesn't contain anything, try 1
                sock = node.inputs[1]
                if sock.is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_roughness_socket(sock.links[0].from_node) 
                # Nothing here
                return None

        return None

    @staticmethod
    def find_specular_socket(node):
        """Get the socket from which to take specular data. May be None."""
        if node:
            if node.type == 'OUTPUT_MATERIAL':  # Go down the node tree
                socket = node.inputs['Surface']  # 0 = Surface
                if socket.is_linked:
                    return Materialnode.find_specular_socket(socket.links[0].from_node)
            elif node.type in ['EEVEE_SPECULAR', 'BSDF_PRINCIPLED']:
                return node.inputs['Specular']
            elif node.type == 'MIX_SHADER':
                # Try socket 1 (socket 0 is a factor) 
                sock = node.inputs[1]
                if sock.is_linked:
                    sub_node = Materialnode.find_specular_socket(sock.links[0].from_node) 
                    # Can't return None yet, we need to try the other socket
                    if sub_node:
                        return sub_node
                # Socket 1 doesn't contain anything, try 2
                sock = node.inputs[2]
                if sock.is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_specular_socket(sock.links[0].from_node) 
                # Nothing here
                return None
            elif node.type == 'ADD_SHADER':
                # Try socket 0
                sock = node.inputs[0]
                if sock.is_linked:
                    sub_node = Materialnode.find_specular_socket(sock.links[0].from_node) 
                    # Can't return None yet, we need to try the other socket
                    if sub_node:
                        return sub_node
                # Socket 0 doesn't contain anything, try 1
                sock = node.inputs[1]
                if sock.is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_specular_socket(sock.links[0].from_node) 
                # Nothing here
                return None

        return None

    @staticmethod
    def get_output_node(material):
        """Search for the output node in this node list."""
        # Material has to use nodes
        if not (material.use_nodes and material.node_tree):
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

        if Materialnode.is_texture_node(node):  # Return this node
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
        """Get the color socket connected to this socket. May be none."""
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
    def get_alpha_value(socket, fail_value=1.0):
        """Get tha alpha value from the socket."""
        if socket:
            # Transparency needs to be inverted
            if socket.name == 'Transparency':
                return (1.0 - socket.default_value)
            else:  
                return socket.default_value
        return fail_value

    @staticmethod
    def get_color_value(socket, fail_value=(1.0, 1.0, 1.0, 1.0)):
        """Get tha color value from the socket."""
        if socket:
            return socket.default_value
        return fail_value

    @staticmethod
    def get_texture_name(texture_node, fail_value="ERROR"):
        """Get a texture from a texture node."""
        # No texture node: None=Null
        if texture_node and texture_node.image:
            img = texture_node.image
            # Get name from filepath or (Blender's) image name
            tex_name = None
            # Try image.filepath first (it may return a unusable path)
            if img.filepath:
                tex_name = os.path.splitext(os.path.basename(img.filepath))[0]
            # Check if the name from filepath is present and useable
            # If not try the image name directly instead
            if not tex_name and img.name:
                tex_name = os.path.splitext(os.path.basename(img.name))[0]
            return tex_name

        # No image, use node identifier (either node label or node name)
        return Materialnode.get_node_identifier(texture_node, True)

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
                color = list(Materialnode.get_color_value(color_socket,
                                                          default_color))
            return texture, color

        texture_list = [None] * 15
        color_list = [None] * 15
        alpha = 1.0

        node_out = Materialnode.get_output_node(material)
        if node_out:
            # Alpha value
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
            texture_list[3], color_list[3] = get_data_tuple(input_socket,
                                                            (1.0, ))

            # Height/Ambient Occlusion (4)
            input_socket = Materialnode.find_height_socket(node_out)
            texture_list[4], _ = get_data_tuple(input_socket)

            # Emissive/Illumination (5)
            input_socket = Materialnode.find_emissive_socket(node_out)
            texture_list[5], color_list[5] = get_data_tuple(input_socket,
                                                            (0.0, 0.0, 0.0, 1.0))
        return texture_list, color_list, alpha

    @staticmethod
    def add_node_data_bsdf(material, output_label,
                           texture_list, color_list, alpha,
                           img_filepath, img_search=False):
        """Setup up material nodes for Principled BSDF Shader."""
        # Cache because lazy
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        # Create an output and shaders
        node_out = nodes.new('ShaderNodeOutputMaterial')
        node_out.label = output_label
        node_out.location = (801.8, 610.1)

        node_shd_bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        node_shd_bsdf.location = (-16.2, 583.6)

        links.new(node_out.inputs[0], node_shd_bsdf.outputs[0])

        # Add a math node to incorporate aurora alpha
        node_math_alpha = nodes.new('ShaderNodeMath')
        node_math_alpha.label = "Aurora Alpha"
        node_math_alpha.name = "math_aurora_alpha"
        node_math_alpha.location = (-1130.7, 112.4)
        node_math_alpha.operation = 'MULTIPLY'
        node_math_alpha.use_clamp = True
        node_math_alpha.inputs[0].default_value = 1.0
        node_math_alpha.inputs[1].default_value = alpha

        links.new(node_shd_bsdf.inputs['Alpha'], node_math_alpha.outputs[0])

        # Add texture maps
        # 0 = Diffuse
        node_shd_bsdf.inputs['Base Color'].default_value = color_list[0]
        if texture_list[0]:
            # Setup: Image Texture (Color) => Principled BSDF
            # Setup: Image Texture (Alpha) => Mix Transparent (Factor)
            node_tex_diff = nodes.new('ShaderNodeTexImage')
            node_tex_diff.label = "Texture: Diffuse"
            node_tex_diff.name = "tex_diffuse"
            node_tex_diff.location = (-1563.0, 792.6)

            node_tex_diff.image = nvb_utils.create_image(
                texture_list[0], img_filepath, img_search)
            node_tex_diff.image.colorspace_settings.name = 'sRGB'
            # node_tex_diff.color_space = 'COLOR'

            links.new(node_math_alpha.inputs[0], node_tex_diff.outputs[1])
            links.new(node_shd_bsdf.inputs['Base Color'], node_tex_diff.outputs[0])

        # 1 = Normal
        if texture_list[1]:
            # Setup: Image Texture => Normal Map => Principled BSDF
            node_tex_norm = nodes.new('ShaderNodeTexImage')
            node_tex_norm.label = "Texture: Normal"
            node_tex_norm.name = "tex_normal"
            node_tex_norm.location = (-791.4, -97.7)

            node_tex_norm.image = nvb_utils.create_image(
                texture_list[1], img_filepath, img_search)
            node_tex_norm.image.colorspace_settings.name = 'Non-Color'
            # node_tex_norm.color_space = 'NONE'

            node_norm = nodes.new('ShaderNodeNormalMap')
            node_norm.location = (-468.8, 5.3)

            links.new(node_norm.inputs[1], node_tex_norm.outputs[0])
            links.new(node_shd_bsdf.inputs['Normal'], node_norm.outputs[0])

        # 2 = Specular
        node_shd_bsdf.inputs['Specular'].default_value = color_list[2][0]
        if texture_list[2]:
            # Setup: Image Texture => Principled BSDF
            node_tex_spec = nodes.new('ShaderNodeTexImage')
            node_tex_spec.label = "Texture: Specular"
            node_tex_spec.name = "tex_specular"
            node_tex_spec.location = (-1132.8, 591.3)

            node_tex_spec.image = nvb_utils.create_image(
                texture_list[2], img_filepath, img_search)
            node_tex_spec.image.colorspace_settings.name = 'Non-Color'

            links.new(node_shd_bsdf.inputs['Specular'], node_tex_spec.outputs[0])

        # 3 = Roughness
        node_shd_bsdf.inputs['Roughness'].default_value = color_list[3][0]
        if texture_list[3]:
            # Setup: Image Texture => Principled BSDF
            node_tex_rough = nodes.new('ShaderNodeTexImage')
            node_tex_rough.label = "Texture: Roughness"
            node_tex_rough.name = "tex_roughness"
            node_tex_rough.location = (-842.3, 459.3)

            node_tex_rough.image = nvb_utils.create_image(
                texture_list[3], img_filepath, img_search)
            node_tex_rough.image.colorspace_settings.name = 'Non-Color'

            links.new(node_shd_bsdf.inputs['Roughness'], node_tex_rough.outputs[0])

        # 4 = Height/AO/Parallax
        if texture_list[4]:
            # Setup: Image Texture => Displacement => Material Output
            node_tex_height = nodes.new('ShaderNodeTexImage')
            node_tex_height.label = "Texture: Height"
            node_tex_height.name = "tex_height"
            node_tex_height.location = (284.0, 356.0)

            node_tex_height.image = nvb_utils.create_image(
                texture_list[4], img_filepath, img_search)
            node_tex_height.image.colorspace_settings.name = 'Non-Color'

            node_displ = nodes.new('ShaderNodeDisplacement')
            node_displ.location = (587.0, 412.0)

            links.new(node_displ.inputs[0], node_tex_height.outputs[0])
            links.new(node_out.inputs['Displacement'], node_displ.outputs[0])

        # 5 = Illumination, Emission, Glow
        node_shd_bsdf.inputs['Emission'].default_value = color_list[5]
        if texture_list[5]:
            # Setup: Image Texture => Principled BSDF (Emission socket)
            node_tex_emit = nodes.new('ShaderNodeTexImage')
            node_tex_emit.label = "Texture: Emissive"
            node_tex_emit.name = "tex_emissive"
            node_tex_emit.location = (-551.1, 344.9)

            node_tex_emit.image = nvb_utils.create_image(
                texture_list[5], img_filepath, img_search)
            node_tex_emit.image.colorspace_settings.name = 'sRGB'

            links.new(node_shd_bsdf.inputs['Emission'], node_tex_emit.outputs[0])

    @staticmethod
    def add_node_data_spec(material, output_label,
                           texture_list, color_list, alpha,
                           img_filepath, img_search=False):
        """Setup up material nodes for Eevee Specular Shader."""
        # Cache because lazy
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        # Create an output and shaders
        node_out = nodes.new('ShaderNodeOutputMaterial')
        node_out.label = output_label
        node_out.location = (790.0, 384.0)

        node_shader_spec = nodes.new('ShaderNodeEeveeSpecular')
        node_shader_spec.location = (564.0, 359.0)

        links.new(node_out.inputs['Surface'],
                  node_shader_spec.outputs['BSDF'])

        # Add texture maps

        # 0 = Diffuse = Base Color
        node_shader_spec.inputs[0].default_value = color_list[0]

        # Setup: Image Texture (Alpha) => Math (Multiply mdl alpha)
        #        => Invert => Eevee Specular (Transparency)
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

        links.new(node_invert.inputs[0], node_math.outputs[0])
        links.new(node_shader_spec.inputs['Transparency'], node_invert.outputs[0])
        if texture_list[0]:
            # Setup: Image Texture (Color) => Eevee Specular (Base Color)
            node_tex_diff = nodes.new('ShaderNodeTexImage')
            node_tex_diff.label = "Texture: Diffuse"
            node_tex_diff.name = "tex_diffuse"
            node_tex_diff.location = (-1125.0, 715.0)

            node_tex_diff.image = nvb_utils.create_image(
                texture_list[0], img_filepath, img_search)
            node_tex_diff.image.colorspace_settings.name = 'sRGB'

            links.new(node_math.inputs[0], node_tex_diff.outputs[1])
            links.new(node_shader_spec.inputs['Base Color'], node_tex_diff.outputs[0])

        # 1 = Normal
        if texture_list[1]:
            # Setup: Image Texture => Normal Map => Eevee Specular
            node_tex_norm = nodes.new('ShaderNodeTexImage')
            node_tex_norm.label = "Texture: Normal"
            node_tex_norm.name = "tex_normal"
            node_tex_norm.location = (-179.0, -174.0)

            node_tex_norm.image = nvb_utils.create_image(
                texture_list[1], img_filepath, img_search)
            node_tex_norm.image.colorspace_settings.name = 'Non-Color'

            node_normal = nodes.new('ShaderNodeNormalMap')
            node_normal.location = (191.0, -71.0)

            links.new(node_normal.inputs[1], node_tex_norm.outputs[0])
            links.new(node_shader_spec.inputs['Normal'], node_normal.outputs[0])

        # 2 = Specular
        node_shader_spec.inputs['Specular'].default_value = color_list[2]
        if texture_list[2]:
            # Setup: Image Texture => Eevee Specular
            node_tex_spec = nodes.new('ShaderNodeTexImage')
            node_tex_spec.label = "Texture: Specular"
            node_tex_spec.name = "tex_specular"
            node_tex_spec.location = (-675.0, 530.0)

            node_tex_spec.image = nvb_utils.create_image(
                texture_list[2], img_filepath, img_search)
            node_tex_spec.image.colorspace_settings.name = 'sRGB'

            links.new(node_shader_spec.inputs['Specular'], node_tex_spec.outputs[0])

        # 3 = Roughness
        node_shader_spec.inputs['Roughness'].default_value = color_list[3][0]
        if texture_list[3]:
            # Setup: Image Texture => Eevee Specular (Roughness)
            node_tex_rough = nodes.new('ShaderNodeTexImage')
            node_tex_rough.label = "Texture: Roughness"
            node_tex_rough.name = "tex_roughness"
            node_tex_rough.location = (-369.0, 376.0)

            node_tex_rough.image = nvb_utils.create_image(
                texture_list[3], img_filepath, img_search)
            node_tex_rough.image.colorspace_settings.name = 'Non-Color'

            links.new(node_shader_spec.inputs['Roughness'], node_tex_rough.outputs[0])

        # 4 = Height (use as Ambient Occlusion)
        if texture_list[4]:
            # Setup: Image Texture => AO => Eevee Specular (Ambient Occlusion)
            node_tex_height = nodes.new('ShaderNodeTexImage')
            node_tex_height.label = "Texture: Height"
            node_tex_height.name = "tex_height"
            node_tex_height.location = (105.0, -267.0)

            node_tex_height.image = nvb_utils.create_image(
                texture_list[4], img_filepath, img_search)
            node_tex_height.image.colorspace_settings.name = 'Non-Color'

            node_ao = nodes.new('ShaderNodeAmbientOcclusion')
            node_ao.location = (372.0, -119.0)

            links.new(node_ao.inputs[1], node_tex_height.outputs[0])
            links.new(node_shader_spec.inputs['Ambient Occlusion'], node_ao.outputs[1])

        # 5 = Illumination/ Emission/ Glow
        node_shader_spec.inputs['Emissive Color'].default_value = color_list[5]
        if texture_list[5]:
            # Setup: Image Texture => Eevee Specular (Emissive)
            node_tex_emit = nodes.new('ShaderNodeTexImage')
            node_tex_emit.label = "Texture: Emissive"
            node_tex_emit.name = "tex_emissive"
            node_tex_emit.location = (-63.0, 267.0)

            node_tex_emit.image = nvb_utils.create_image(
                texture_list[5], img_filepath, img_search)
            node_tex_emit.image.colorspace_settings.name = 'Non-Color'

            links.new(node_shader_spec.inputs['Emissive Color'], node_tex_emit.outputs[0])

    @staticmethod
    def add_node_data(material, shader_type, output_name,
                      texture_list, color_list, alpha,
                      img_filepath, img_search=False):
        """Select shader nodes based on options."""
        if (shader_type == 'ShaderNodeEeveeSpecular'):
            Materialnode.add_node_data_spec(material, output_name,
                                            texture_list, color_list, alpha,
                                            img_filepath, img_search)
        else:
            Materialnode.add_node_data_bsdf(material, output_name,
                                            texture_list, color_list, alpha,
                                            img_filepath, img_search)
