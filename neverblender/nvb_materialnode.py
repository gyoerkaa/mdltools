"""TODO: DOC."""

import os
import collections

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
        """Get the socket from which to take the height map. May be None."""
        if node:
            # There are two options for finding a heightmap:
            # 1. Material output (Displacement Socket) => Displacement Node (Height socket)
            # 2. Material output (Surface Socket) => Shader (Normal socket) => Bump Node (Height socket)
            # We prefer 1. over 2.
            if node.type == 'OUTPUT_MATERIAL':
                # Try going down the diplacement socket first (option 1)
                socket = node.inputs['Displacement']
                if socket.is_linked:
                    linked_node = Materialnode.find_height_socket(socket.links[0].from_node)
                    # Might not be present
                    if linked_node:
                        return linked_node
                # If displacement didn't work look for the shader connected to surface socket (option 2)
                socket = node.inputs['Surface']
                if socket.is_linked:
                    return Materialnode.find_height_socket(socket.links[0].from_node)
            elif node.type in ['EEVEE_SPECULAR', 'BSDF_PRINCIPLED']:
                socket = node.inputs['Normal']
                if socket.is_linked:
                    return Materialnode.find_height_socket(socket.links[0].from_node)
            elif node.type == 'DISPLACEMENT':
                return node.inputs['Height']
            elif node.type == 'BUMP':
                return node.inputs['Height']
            elif node.type == 'MIX_SHADER':
                # Try socket 1 (socket 0 is a factor) 
                socket = node.inputs[1]
                if socket.is_linked:
                    sub_node = Materialnode.find_height_socket(socket.links[0].from_node) 
                    # Can't return None yet, we need to try the other socket
                    if sub_node:
                        return sub_node
                # Socket 1 doesn't contain anything, try 2
                socket = node.inputs[2]
                if socket.is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_height_socket(socket.links[0].from_node) 
                # Nothing here
                return None
            elif node.type == 'ADD_SHADER':
                # Try socket 0
                socket = node.inputs[0]
                if socket.is_linked:
                    sub_node = Materialnode.find_height_socket(socket.links[0].from_node) 
                    # Can't return None yet, we need to try the other socket
                    if sub_node:
                        return sub_node
                # Socket 0 doesn't contain anything, try 1
                socket = node.inputs[1]
                if socket.is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_height_socket(socket.links[0].from_node) 
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
            elif node.type == 'BUMP':
                # Bump node have their own normal socket
                socket = node.inputs['Normal']
                if socket.is_linked:
                    return Materialnode.find_normal_socket(socket.links[0].from_node)
            elif node.type == 'MIX_SHADER':
                # Can't go by socket name here, both input sockets are named the same!
                # Try socket 1 (socket 0 is a factor) 
                socket = node.inputs[1]
                if socket.is_linked:
                    sub_node = Materialnode.find_normal_socket(socket.links[0].from_node) 
                    # Can't return None yet, we need to try the other socket
                    if sub_node:
                        return sub_node
                # Socket 1 doesn't contain anything, try 2
                socket = node.inputs[2]
                if socket.is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_normal_socket(socket.links[0].from_node) 
                # Nothing here
                return None
            elif node.type == 'ADD_SHADER':
                # Can't go by socket name here, both input sockets are named the same!
                # Try socket 0
                socket = node.inputs[0]
                if socket.is_linked:
                    sub_node = Materialnode.find_normal_socket(socket.links[0].from_node) 
                    # Can't return None yet, we need to try the other socket
                    if sub_node:
                        return sub_node
                # Socket 0 doesn't contain anything, try 1
                socket = node.inputs[1]
                if sock.is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_normal_socket(socket.links[0].from_node) 
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
        """Get a texture node using DFS. May be none."""
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
    def get_texture_node_nearest(socket):
        """Get the nearest texture node using BFS. May be none."""
        if not socket or not socket.is_linked:
            return None

        # The socket is valid and linked to anther node, we need to follow it
        # Since its an input socket only one node is connected
        root_node = socket.links[0].from_node
        visited, queue = set(), collections.deque([root_node])

        # BFS over connected nodes
        while queue:
            node = queue.popleft()
            if node and node not in visited:
                visited.add(node)
                # Return texture node
                if Materialnode.is_texture_node(node):  
                    return node
                # Mix RGB node, two color sockets (1 and 2), always add to queue
                elif node.type == 'MIX_RGB':
                    if node.inputs["Color1"].is_linked:
                        neighbour_node = node.inputs["Color1"].links[0].from_node
                        queue.append(neighbour_node)
                    if node.inputs["Color2"].is_linked:
                        neighbour_node = node.inputs["Color2"].links[0].from_node
                        queue.append(neighbour_node)
                # Separate RGB node, single image socket (0), always add to queue
                elif node.type == 'SEPRGB':
                    if node.inputs[0].is_linked:
                        neighbour_node = node.inputs[0].links[0].from_node
                        queue.append(neighbour_node)
                # Invert, single color socket (0), always add to queue
                elif node.type == 'INVERT':
                    if node.inputs[0].is_linked:
                        neighbour_node = node.inputs[0].links[0].from_node
                        queue.append(neighbour_node)
        return None

    @staticmethod
    def get_color_socket(socket):
        """Get a color socket connected to this socket using DFS. May be none or the socket itself."""
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
    def get_color_socket_nearest(socket):
        """Get the nearest color socket connected to this socket using BFS. May be none or the socket itself."""
        if not socket:
            return None

        if not socket.is_linked:
            if socket.type == 'RGBA':
                # Unlinked color socket, return it directly
                return socket
            else: 
                # Unlinked an not a color socket, can't use this one
                return None
        
        # The socket is valid and linked to anther node, we need to follow it
        # Since its an input socket only one node is connected
        root_node = socket.links[0].from_node
        visited, queue = set(), collections.deque([root_node])

        # BFS over connected nodes
        while queue:
            # Dequeue a vertex from queue
            node = queue.popleft()
            if node and node not in visited:
                visited.add(node)

                if node.type == 'MIX_RGB':
                    # Mix node, return unlinked socket
                    if node.inputs["Color1"].is_linked:
                        neighbour_node = node.inputs["Color1"].links[0].from_node
                        queue.append(neighbour_node)
                    else:  # Unlinked socket
                        return node.inputs[1]
                    if node.inputs["Color2"].is_linked:
                        neighbour_node = node.inputs["Color2"].links[0].from_node
                        queue.append(neighbour_node)
                    else:  # Unlinked socket
                        return node.inputs[2]                        
                elif node.type == 'SEPRGB':
                    # RGB Separation, follow input 0 (Image)
                    if node.inputs[0].is_linked:
                        neighbour_node = node.inputs[0].links[0].from_node
                        queue.append(neighbour_node)
                    else:  # Unlinked socket
                        return node.inputs[0]                        
                elif node.type == 'RGB':  # Return the output socket
                    return node.outputs[0]
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

            color_socket = Materialnode.get_color_socket_nearest(input_socket)
            color = default_color
            if color_socket:
                color = list(Materialnode.get_color_value(color_socket, default_color))
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
            texture_list[0], color_list[0] = get_data_tuple(input_socket, (1.0, 1.0, 1.0, 1.0))

            # Normal (1)
            input_socket = Materialnode.find_normal_socket(node_out)
            texture_list[1], _ = get_data_tuple(input_socket)

            # Specular (2)
            input_socket = Materialnode.find_specular_socket(node_out)
            texture_list[2], color_list[2] = get_data_tuple(input_socket, (0.0, 0.0, 0.0, 1.0))

            # Roughness (3)
            input_socket = Materialnode.find_roughness_socket(node_out)
            texture_list[3], color_list[3] = get_data_tuple(input_socket, (1.0, ))

            # Height/Ambient Occlusion (4)
            input_socket = Materialnode.find_height_socket(node_out)
            texture_list[4], _ = get_data_tuple(input_socket)

            # Emissive/Illumination (5)
            input_socket = Materialnode.find_emissive_socket(node_out)
            texture_list[5], color_list[5] = get_data_tuple(input_socket, (0.0, 0.0, 0.0, 1.0))
        return texture_list, color_list, alpha

    @staticmethod
    def add_node_data_bsdf(material, output_label, texture_list, color_list, alpha, options):
        """Setup up material nodes for Principled BSDF Shader."""
        # Cache because lazy
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        # Create an output and shaders
        node_out = nodes.new('ShaderNodeOutputMaterial')
        node_out.label = output_label
        node_out.location = (930.0, 595.0)

        node_shd_bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        node_out.name = 'shader_bsdf'
        node_shd_bsdf.location = (20.0, 570.0)

        links.new(node_out.inputs[0], node_shd_bsdf.outputs[0])

        # Add a math node to incorporate aurora alpha from mdl file
        node_math_alpha = nodes.new('ShaderNodeMath')
        node_math_alpha.label = "Aurora Alpha"
        node_math_alpha.name = "math_aurora_alpha"
        node_math_alpha.location = (-1075.0, -255.0)
        node_math_alpha.operation = 'MULTIPLY'
        node_math_alpha.use_clamp = True
        node_math_alpha.inputs[0].default_value = 1.0
        node_math_alpha.inputs[1].default_value = alpha

        links.new(node_shd_bsdf.inputs['Alpha'], node_math_alpha.outputs[0])

        # Add texture maps
        # 0 = Diffuse
        if color_list[0]:
            node_shd_bsdf.inputs['Base Color'].default_value = color_list[0]
        if texture_list[0]:
            # Setup: Image Texture (Color) => Principled BSDF
            # Setup: Image Texture (Alpha) => Mix Transparent (Factor)
            node_tex_diff = nodes.new('ShaderNodeTexImage')
            node_tex_diff.label = "Texture: Diffuse"
            node_tex_diff.name = "texture_diffuse"
            node_tex_diff.location = (-1460.0, 795.0)
            node_tex_diff.image = nvb_utils.create_image(texture_list[0], options.filepath, options.tex_search)
            node_tex_diff.image.colorspace_settings.name = 'sRGB'

            # node_tex_diff.color_space = 'COLOR'
            links.new(node_math_alpha.inputs['Value'], node_tex_diff.outputs['Alpha'])
            links.new(node_shd_bsdf.inputs['Base Color'], node_tex_diff.outputs['Color'])

            # Add an extra mix rgb node and link it (if set in the options)
            if color_list[0] and options.mat_extra_color_nodes:
                node_mix_diff = nodes.new('ShaderNodeMixRGB')
                node_mix_diff.label = "Color: Diffuse"
                node_mix_diff.name = "mix_diffuse"
                node_mix_diff.blend_type = 'MULTIPLY'
                node_mix_diff.location = (-1090.0, 905.0)
                node_mix_diff.use_clamp = True
                node_mix_diff.inputs['Fac'].default_value = 1.0
                node_mix_diff.inputs['Color1'].default_value = color_list[0]

                links.new(node_mix_diff.inputs['Color2'], node_tex_diff.outputs['Color'])
                links.new(node_shd_bsdf.inputs['Base Color'], node_mix_diff.outputs['Color'])


        # 1 = Normal
        if texture_list[1]:
            # Setup: Image Texture => Normal Map => Principled BSDF
            node_tex_norm = nodes.new('ShaderNodeTexImage')
            node_tex_norm.label = "Texture: Normal"
            node_tex_norm.name = "texture_normal"
            node_tex_norm.location = (-795.0, -570.0)
            node_tex_norm.image = nvb_utils.create_image(texture_list[1], options.filepath, options.tex_search)
            node_tex_norm.image.colorspace_settings.name = 'Non-Color'
            # node_tex_norm.color_space = 'NONE'

            node_norm = nodes.new('ShaderNodeNormalMap')
            node_norm.name = "vector_normal_map"
            node_norm.location = (-445.0, -470.0)

            links.new(node_norm.inputs['Color'], node_tex_norm.outputs['Color'])
            links.new(node_shd_bsdf.inputs['Normal'], node_norm.outputs['Normal'])

        # 2 = Specular
        if color_list[2]:
            node_shd_bsdf.inputs['Specular'].default_value = color_list[2][0]
        if texture_list[2]:
            # Setup: Image Texture => Principled BSDF
            node_tex_spec = nodes.new('ShaderNodeTexImage')
            node_tex_spec.label = "Texture: Specular"
            node_tex_spec.name = "texture_specular"
            node_tex_spec.location = (-1080.0, 445.0)
            node_tex_spec.image = nvb_utils.create_image(texture_list[2], options.filepath, options.tex_search)
            node_tex_spec.image.colorspace_settings.name = 'Non-Color'

            links.new(node_shd_bsdf.inputs['Specular'], node_tex_spec.outputs[0])

            # Add an extra mix rgb node and link it (if set in the options)
            if color_list[2] and options.mat_extra_color_nodes:
                node_mix_spec = nodes.new('ShaderNodeMixRGB')
                node_mix_spec.label = "Color: Specular"
                node_mix_spec.name = "mix_specular"
                node_mix_spec.blend_type = 'MULTIPLY'
                node_mix_spec.location = (-800.0, 570.0)
                node_mix_spec.use_clamp = True
                node_mix_spec.inputs['Fac'].default_value = 1.0
                node_mix_spec.inputs['Color1'].default_value = color_list[2]

                links.new(node_mix_spec.inputs['Color2'], node_tex_spec.outputs['Color'])
                links.new(node_shd_bsdf.inputs['Specular'], node_mix_spec.outputs['Color'])

        # 3 = Roughness
        if color_list[3]:
            node_shd_bsdf.inputs['Roughness'].default_value = color_list[3]
        if texture_list[3]:
            # Setup: Image Texture => Principled BSDF
            node_tex_rough = nodes.new('ShaderNodeTexImage')
            node_tex_rough.label = "Texture: Roughness"
            node_tex_rough.name = "texture_roughness"
            node_tex_rough.location = (-725.0, 345.0)
            node_tex_rough.image = nvb_utils.create_image(texture_list[3], options.filepath, options.tex_search)
            node_tex_rough.image.colorspace_settings.name = 'Non-Color'

            links.new(node_shd_bsdf.inputs['Roughness'], node_tex_rough.outputs['Color'])

        # 4 = Height/AO/Parallax/Displacement
        if texture_list[4]:
            # Setup, 2 options: 
            if options.mat_displacement_mode == 'DISPLACEMENT':
                # 1. Image Texture => Displacement => Material Output
                node_tex_height = nodes.new('ShaderNodeTexImage')
                node_tex_height.label = "Texture: Height"
                node_tex_height.name = "texture_height"
                node_tex_height.location = (360.0, 415.0)
                node_tex_height.image = nvb_utils.create_image(texture_list[4], options.filepath, options.tex_search)
                node_tex_height.image.colorspace_settings.name = 'Non-Color'

                node_displ = nodes.new('ShaderNodeDisplacement')
                node_tex_height.name = "vector_displacement"
                node_displ.location = (655.0, 470.0)

                links.new(node_displ.inputs['Height'], node_tex_height.outputs['Color'])
                links.new(node_out.inputs['Displacement'], node_displ.outputs['Displacement'])
            else:  # options.mat_displacement_mode == 'BUMP'
                # 2. Image Texture => Bump Node => Shader
                node_bump = nodes.new('ShaderNodeBump')
                node_bump.name = "vector_bump"
                node_bump.location = (-200.0, -165.0)

                node_tex_height = nodes.new('ShaderNodeTexImage')
                node_tex_height.label = "Texture: Height"
                node_tex_height.name = "texture_height"
                node_tex_height.location = (-795.0, -310.0)
                node_tex_height.image = nvb_utils.create_image(texture_list[4], options.filepath, options.tex_search)
                node_tex_height.image.colorspace_settings.name = 'Non-Color'

                links.new(node_bump.inputs['Height'], node_tex_height.outputs['Color'])
                links.new(node_shd_bsdf.inputs['Normal'], node_bump.outputs['Normal'])

                # Re-link normal node to bump node (previouly linked directly to shader)
                if node_norm:
                    links.new(node_bump.inputs['Normal'], node_norm.outputs['Normal'])

        # 5 = Illumination, Emission, Glow
        if color_list[5]:
            node_shd_bsdf.inputs['Emission'].default_value = color_list[5]
        if texture_list[5]:
            # Setup: Image Texture => Shader (Emission socket)
            node_tex_emit = nodes.new('ShaderNodeTexImage')
            node_tex_emit.label = "Texture: Emission"
            node_tex_emit.name = "texture_emission"
            node_tex_emit.location = (-1020.0, 40.0)
            node_tex_emit.image = nvb_utils.create_image(texture_list[5], options.filepath, options.tex_search)
            node_tex_emit.image.colorspace_settings.name = 'sRGB'

            links.new(node_shd_bsdf.inputs['Emission'], node_tex_emit.outputs[0])

            # Add an extra mix rgb node and link it (if set in the options)
            if color_list[5]:
                pass
                """
                node_color_emit = nodes.new('ShaderNodeRGB')
                node_color_emit.label = "Color: MDL Self-Illumination"
                node_color_emit.name = "color_mdl_selfillum"
                node_color_emit.location = (-1090.0, 905.0)
                node_color_emit.factor = 1.0

                # TODO: set color

                node_mix_emit1 = nodes.new('ShaderNodeMixRGB')
                node_mix_emit1.label = "Mix: Multiply Self-Illumination"
                node_mix_emit1.name = "mix_selfillum_mul"
                node_mix_emit1.blend_type = 'MULTIPLY'
                node_mix_emit1.location = (-1090.0, 905.0)
                node_mix_emit1.factor = 1.0
                node_mix_emit1.use_clamp = True
                node_mix_emit1.inputs['Fac'].default_value = 1.0
                node_mix_emit1.inputs['Color1'].default_value = color_list[5] 

                node_mix_emit2 = nodes.new('ShaderNodeMixRGB')
                node_mix_emit2.label = "Mix: Add Self-Illumination"
                node_mix_emit2.name = "mix_selfillum_add"
                node_mix_emit2.blend_type = 'ADD'
                node_mix_emit2.location = (-1090.0, 905.0)
                node_mix_emit2.factor = 1.0
                node_mix_emit2.use_clamp = True
                node_mix_emit2.inputs['Fac'].default_value = 1.0
                node_mix_emit2.inputs['Color1'].default_value = color_list[5]  

                # TODO: Link                              
                """

    @staticmethod
    def add_node_data_spec(material, output_label, texture_list, color_list, alpha, options):
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

        links.new(node_out.inputs['Surface'], node_shader_spec.outputs['BSDF'])

        # Add texture maps

        # 0 = Diffuse = Base Color
 
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
        
        if color_list[0]:
            node_shader_spec.inputs['Base Color'].default_value = color_list[0]  
        if texture_list[0]:
            # Setup: Image Texture (Color) => Eevee Specular (Base Color)
            node_tex_diff = nodes.new('ShaderNodeTexImage')
            node_tex_diff.label = "Texture: Diffuse"
            node_tex_diff.name = "texture_diffuse"
            node_tex_diff.location = (-1125.0, 715.0)
            node_tex_diff.image = nvb_utils.create_image(texture_list[0], options.filepath, options.tex_search)
            node_tex_diff.image.colorspace_settings.name = 'sRGB'

            links.new(node_math.inputs[0], node_tex_diff.outputs[1])
            links.new(node_shader_spec.inputs['Base Color'], node_tex_diff.outputs[0])

            # Add an extra mix rgb node and link it (if set in the options)
            if color_list[0] and options.mat_extra_color_nodes:
                node_color_diff = nodes.new('ShaderNodeMixRGB')
                node_color_diff.label = "Color: Diffuse"
                node_color_diff.name = "color_diffuse"
                node_color_diff.blend_type = 'MULTIPLY'
                node_color_diff.location = (-538.0, 925.0)
                
                node_color_diff.inputs['Fac'].default_value = 1.0
                node_color_diff.inputs['Color1'].default_value = color_list[0]

                links.new(node_color_diff.inputs['Color2'], node_tex_diff.outputs[0])
                links.new(node_shader_spec.inputs['Base Color'], node_color_diff.outputs['Color'])            

        # 1 = Normal
        if texture_list[1]:
            # Setup: Image Texture => Normal Map => Eevee Specular
            node_tex_norm = nodes.new('ShaderNodeTexImage')
            node_tex_norm.label = "Texture: Normal"
            node_tex_norm.name = "texture_normal"
            node_tex_norm.location = (-179.0, -174.0)

            node_tex_norm.image = nvb_utils.create_image(texture_list[1], options.filepath, options.tex_search)
            node_tex_norm.image.colorspace_settings.name = 'Non-Color'

            node_normal = nodes.new('ShaderNodeNormalMap')
            node_normal.location = (191.0, -71.0)

            links.new(node_normal.inputs[1], node_tex_norm.outputs[0])
            links.new(node_shader_spec.inputs['Normal'], node_normal.outputs[0])

        # 2 = Specular
        if color_list[2]:
            node_shader_spec.inputs['Specular'].default_value = color_list[2]
        if texture_list[2]:
            # Setup: Image Texture => Eevee Specular
            node_tex_spec = nodes.new('ShaderNodeTexImage')
            node_tex_spec.label = "Texture: Specular"
            node_tex_spec.name = "texture_specular"
            node_tex_spec.location = (-675.0, 530.0)

            node_tex_spec.image = nvb_utils.create_image(texture_list[2], options.filepath, options.tex_search)
            node_tex_spec.image.colorspace_settings.name = 'sRGB'

            links.new(node_shader_spec.inputs['Specular'], node_tex_spec.outputs[0])

        # 3 = Roughness
        if color_list[3]:
            node_shader_spec.inputs['Roughness'].default_value = color_list[3]
        if texture_list[3]:
            # Setup: Image Texture => Eevee Specular (Roughness)
            node_tex_rough = nodes.new('ShaderNodeTexImage')
            node_tex_rough.label = "Texture: Roughness"
            node_tex_rough.name = "texture_roughness"
            node_tex_rough.location = (-369.0, 376.0)

            node_tex_rough.image = nvb_utils.create_image(texture_list[3], options.filepath, options.tex_search)
            node_tex_rough.image.colorspace_settings.name = 'Non-Color'

            links.new(node_shader_spec.inputs['Roughness'], node_tex_rough.outputs[0])

        # 4 = Height/Parallax/Displacement
        if texture_list[4]:
            # Setup, 2 options: 
            if options.mat_displacement_mode == 'DISPLACEMENT':
                # 1. Image Texture => Displacement (Height socket) => Material Output (Displacement socket)
                node_tex_height = nodes.new('ShaderNodeTexImage')
                node_tex_height.label = "Texture: Height"
                node_tex_height.name = "texture_height"
                node_tex_height.location = (360.0, 415.0)
                node_tex_height.image = nvb_utils.create_image(texture_list[4], options.filepath, options.tex_search)
                node_tex_height.image.colorspace_settings.name = 'Non-Color'

                node_displ = nodes.new('ShaderNodeDisplacement')
                node_tex_height.name = "vector_displacement"
                node_displ.location = (655.0, 470.0)

                links.new(node_displ.inputs['Height'], node_tex_height.outputs['Color'])
                links.new(node_out.inputs['Displacement'], node_displ.outputs['Displacement'])
            else:  # options.mat_displacement_mode == 'BUMP'
                # 2. Image Texture => Bump Node (height socket) => Shader
                node_bump = nodes.new('ShaderNodeBump')
                node_bump.name = "vector_bump"
                node_bump.location = (-200.0, -165.0)

                node_tex_height = nodes.new('ShaderNodeTexImage')
                node_tex_height.label = "Texture: Height"
                node_tex_height.name = "texture_height"
                node_tex_height.location = (-795.0, -310.0)
                node_tex_height.image = nvb_utils.create_image(texture_list[4], options.filepath, options.tex_search)
                node_tex_height.image.colorspace_settings.name = 'Non-Color'

                links.new(node_bump.inputs['Height'], node_tex_height.outputs['Color'])
                links.new(node_shader_spec.inputs['Normal'], node_bump.outputs['Normal'])

                # Re-link normal node to bump node (previouly linked directly to shader)
                if node_normal:
                    links.new(node_bump.inputs['Normal'], node_normal.outputs['Normal'])

        # 5 = Illumination/ Emission/ Glow
        if color_list[5]:
            node_shader_spec.inputs['Emissive Color'].default_value = color_list[5]        
        if texture_list[5]:
            # Setup: Image Texture => Eevee Specular (Emissive)
            node_tex_emit = nodes.new('ShaderNodeTexImage')
            node_tex_emit.label = "Texture: Emissive"
            node_tex_emit.name = "texture_emissive"
            node_tex_emit.location = (-63.0, 267.0)

            node_tex_emit.image = nvb_utils.create_image(texture_list[5], options.filepath, options.tex_search)
            node_tex_emit.image.colorspace_settings.name = 'Non-Color'

            links.new(node_shader_spec.inputs['Emissive Color'], node_tex_emit.outputs[0])

    @staticmethod
    def add_node_data(material, output_name, texture_list, color_list, alpha, options):
        """Select shader nodes based on options."""
        if (options.mat_shader == 'ShaderNodeEeveeSpecular'):
            Materialnode.add_node_data_spec(material, output_name,
                                            texture_list, color_list, alpha,
                                            options)
        else:
            Materialnode.add_node_data_bsdf(material, output_name,
                                            texture_list, color_list, alpha,
                                            options)
