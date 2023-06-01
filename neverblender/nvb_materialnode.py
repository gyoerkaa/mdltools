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
                # Use the value from the first unconnected socket
                if not node.inputs[0].is_linked:
                    return node.inputs[0]
                if not node.inputs[1].is_linked:
                    return node.inputs[1]
                else:
                    return None  # No unconnected sockets
            elif node.type == 'VALUE':
                # Return the output socket
                return node.outputs[0]
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
                if node.inputs[1].is_linked:
                    child_node = Materialnode.find_emissive_socket(node.inputs[1].links[0].from_node)
                    # Can't return None yet, we need to try the other socket
                    if child_node:
                        return child_node
                # Socket 1 doesn't contain anything, try 2
                if node.inputs[2].is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_emissive_socket(node.inputs[2].links[0].from_node)
                # Nothing here
                return None
            elif node.type == 'ADD_SHADER':
                # Try socket 0
                if node.inputs[0].is_linked:
                    child_node = Materialnode.find_emissive_socket(node.inputs[0].links[0].from_node)
                    # Can't return None yet, we need to try the other socket
                    if child_node:
                        return child_node
                # Socket 0 doesn't contain anything, try 1
                if node.inputs[1].is_linked:
                     # Can safely return None, nothing left to try
                    return Materialnode.find_emissive_socket(node.inputs[1].links[0].from_node)
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
    def get_num_links(socket):
        """Get number of outgoing links."""
        if socket.is_linked:
            return len(socket.links)
        return 0

    @staticmethod
    def get_texture_node_nearest(socket, max_depth=32, exclusive=False):
        """Get the nearest texture node using BFS. May be none."""
        if not socket or not socket.is_linked:
            return None

        # The socket is valid and linked to anther node, we need to follow it
        # Since its an input socket only one node is connected
        depth = 0
        root_node = socket.links[0].from_node
        visited, queue = set(), collections.deque([(root_node, depth)])

        # BFS over connected nodes
        while queue:
            # Get a vertex from queue
            node, depth = queue.popleft()
            if node and (node not in visited) and (depth <= max_depth):
                visited.add(node)
                depth += 1
                # Return texture node
                if Materialnode.is_texture_node(node):
                    if not exclusive or (Materialnode.get_num_links(node.outputs['Color']) <= 1):
                        return node
                # Mix RGB node
                # Two color sockets (1 and 2), always add to queue
                elif node.type == 'MIX_RGB':
                    if node.inputs['Color1'].is_linked:
                        neighbour_node = node.inputs['Color1'].links[0].from_node
                        queue.append((neighbour_node, depth))
                    if node.inputs['Color2'].is_linked:
                        neighbour_node = node.inputs['Color2'].links[0].from_node
                        queue.append((neighbour_node, depth))
                elif node.type == 'MIX':
                    if node.inputs['A'].is_linked:
                        neighbour_node = node.inputs['A'].links[0].from_node
                        queue.append((neighbour_node, depth))
                    if node.inputs['B'].is_linked:
                        neighbour_node = node.inputs['B'].links[0].from_node
                        queue.append((neighbour_node, depth))
                # Separate RGB nodew
                # Single image socket (0), always add to queue
                elif node.type == 'SEPRGB':
                    if node.inputs[0].is_linked:
                        neighbour_node = node.inputs[0].links[0].from_node
                        queue.append((neighbour_node, depth))
                # Clamp node
                # Single value socket (0), always add to queue
                elif node.type == 'CLAMP':
                    if node.inputs['Value'].is_linked:
                        neighbour_node = node.inputs['Value'].links[0].from_node
                        queue.append((neighbour_node, depth))
                # Math node
                #  2 value inputs (0 and 1, not refrenceable by name), may be grayscale
                elif node.type == 'MATH':
                    if node.inputs[0].is_linked:
                        neighbour_node = node.inputs[0].links[0].from_node
                        queue.append((neighbour_node, depth))
                    if node.inputs[1].is_linked:
                        neighbour_node = node.inputs[1].links[0].from_node
                        queue.append((neighbour_node, depth))
                # Invert, Bightness/Contrast, RGB curves, Gamma, Hue/saturation or RGB to BW node
                # All have a single color socket, always add to queue
                elif node.type in ['INVERT', 'BRIGHTCONTRAST', 'CURVE_RGB', 'GAMMA', 'HUE_SAT', 'RGBTOBW']:
                    if node.inputs['Color'].is_linked:
                        neighbour_node = node.inputs['Color'].links[0].from_node
                        queue.append((neighbour_node, depth))
        return None

    @staticmethod
    def get_color_socket_nearest(socket, max_depth=32, exclusive=False):
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
        depth = 0
        root_node = socket.links[0].from_node
        visited, queue = set(), collections.deque([(root_node, depth)])

        # BFS over connected nodes
        while queue:
            # Get a vertex from queue
            node, depth = queue.popleft()
            if node and (node not in visited) and (depth <= max_depth):
                visited.add(node)
                depth += 1
                # MixRGB node
                if node.type == 'MIX_RGB':
                    # Color2: Check for unlinked socket or directly linked color socket
                    if not node.inputs['Color2'].is_linked:
                        return node.inputs['Color2']
                    neighbour_node = node.inputs["Color2"].links[0].from_node
                    if neighbour_node.type == 'RGB':
                        return neighbour_node.outputs[0]
                    # Nothing useable, continue search
                    queue.append((neighbour_node, depth))
                    # Color1: Check for unlinked socket or directly linked color socket
                    if not node.inputs['Color1'].is_linked:
                        return node.inputs['Color1']
                    neighbour_node = node.inputs['Color1'].links[0].from_node
                    if neighbour_node.type == 'RGB':
                        return neighbour_node.outputs[0]
                    # Nothing useable, continue search
                    queue.append((neighbour_node, depth))
                elif node.type == 'MIX':
                    # Color2: Check for unlinked socket or directly linked color socket
                    if not node.inputs['A'].is_linked:
                        return node.inputs['A']
                    neighbour_node = node.inputs["A"].links[0].from_node
                    if neighbour_node.type == 'RGB':
                        return neighbour_node.outputs[0]
                    # Nothing useable, continue search
                    queue.append((neighbour_node, depth))
                    # Color2: Check for unlinked socket or directly linked color socket
                    if not node.inputs['B'].is_linked:
                        return node.inputs['B']
                    neighbour_node = node.inputs["B"].links[0].from_node
                    if neighbour_node.type == 'RGB':
                        return neighbour_node.outputs[0]
                    # Nothing useable, continue search
                    queue.append((neighbour_node, depth))
                # Separate RGB node
                elif node.type == 'SEPRGB':
                    # Image socket (socket 0): Check for unlinked socket or directly linked color socket
                    if not node.inputs[0].is_linked:
                        return node.inputs[0]
                    neighbour_node = node.inputs[0].links[0].from_node
                    if neighbour_node.type == 'RGB':
                        return neighbour_node.outputs[0]
                    # Nothing useable, continue search
                    queue.append((neighbour_node, depth))
                # Clamp node
                elif node.type == 'CLAMP':
                    # Value socket: Check for unlinked socket or directly linked color socket
                    if not node.inputs['Value'].is_linked:
                        return node.inputs['Value']
                    neighbour_node = node.inputs['Value'].links[0].from_node
                    if neighbour_node.type == 'RGB':
                        return neighbour_node.outputs[0]
                    # Nothing useable, continue search
                    queue.append((neighbour_node, depth))
                # Math node
                # 2 value inputs (0 and 1, not refrenceable by name), may be grayscale
                elif node.type == 'MATH':
                    # Value 0: Check for unlinked socket or directly linked color socket
                    if not node.inputs[0].is_linked:
                        return node.inputs[0]
                    neighbour_node = node.inputs[0].links[0].from_node
                    if neighbour_node.type == 'RGB':
                        return neighbour_node.outputs[0]
                    # Nothing useable, continue search
                    queue.append((neighbour_node, depth))
                    # Value 1: Check for unlinked socket or directly linked color socket
                    if not node.inputs[1].is_linked:
                        return node.inputs[1]
                    neighbour_node = node.inputs[1].links[0].from_node
                    if neighbour_node.type == 'RGB':
                        return neighbour_node.outputs[0]
                    # Nothing useable, continue search
                    queue.append((neighbour_node, depth))
                # Invert, Bightness/Contrast, RGB curves, Gamma, Hue/saturation or RGB to BW node
                # All have a single color socket
                elif node.type in ['INVERT', 'BRIGHTCONTRAST', 'CURVE_RGB', 'GAMMA', 'HUE_SAT', 'RGBTOBW']:
                    # Color socket: Check for unlinked socket or directly linked color socket
                    if not node.inputs['Color'].is_linked:
                        return node.inputs['Color']
                    neighbour_node = node.inputs['Color'].links[0].from_node
                    if neighbour_node.type == 'RGB':
                        return neighbour_node.outputs[0]
                    # Nothing useable, continue search
                    queue.append((neighbour_node, depth))
                # Input RGB node, should not be able to reach this, but return the output socket
                elif node.type == 'RGB':
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
    def get_ambient_color(blen_material):
        """Find an unconnected RGB node with ambient in its name."""
        for node in blen_material.node_tree.nodes:
            # We only need to check a single output for linkage
            if node.type == 'RGB' and not node.outputs[0].is_linked and "ambient" in node.name.lower():
                return node.outputs[0].default_value
        return None

    @staticmethod
    def get_node_data(material):
        """Get a list of relevant textures and colors for this material."""
        def get_connected_texture(input_socket, fail_value="", max_depth=32, exclusive=False):
            """Get texture from an input socket."""
            texture_node = Materialnode.get_texture_node_nearest(input_socket, max_depth, exclusive)
            if texture_node:
                return Materialnode.get_texture_name(texture_node)

            return fail_value

        def get_connected_color(input_socket, fail_value=(1.0, 1.0, 1.0, 1.0), max_depth=32, exclusive=False):
            """Get color from an input socket."""
            color_socket = Materialnode.get_color_socket_nearest(input_socket, max_depth, exclusive)
            if color_socket:
                # We don't know if we get a color (bpy.array) or a scalar (float)
                color = Materialnode.get_color_value(color_socket, fail_value)
                # If its not iterable we can just place the single value into a list
                try:
                    color = list(color)
                except TypeError:
                    color = [color]
                return color
            return fail_value

        texture_list = [None] * 15
        color_list = [None] * 15
        alpha = 1.0
        ambient = None  # Seperate for compatibility (unsupported by blender)

        node_out = Materialnode.get_output_node(material)
        if node_out:
            # Alpha value
            input_socket = Materialnode.find_alpha_socket(node_out)
            alpha = Materialnode.get_alpha_value(input_socket)
            # Ambient color is legacy (pre EE, or old shaders)
            ambient = Materialnode.get_ambient_color(material)

            # Diffuse (0)
            input_socket = Materialnode.find_diffuse_socket(node_out)
            texture_list[0] = get_connected_texture(input_socket)
            color_list[0] = get_connected_color(input_socket, (1.0, 1.0, 1.0, 1.0))

            # Normal (1)
            input_socket = Materialnode.find_normal_socket(node_out)
            texture_list[1] = get_connected_texture(input_socket)

            # Specular (2)
            input_socket = Materialnode.find_specular_socket(node_out)
            texture_list[2] = get_connected_texture(input_socket)
            color_list[2] = get_connected_color(input_socket, None)

            # Roughness (3)
            input_socket = Materialnode.find_roughness_socket(node_out)
            texture_list[3] = get_connected_texture(input_socket)
            color_list[3] = get_connected_color(input_socket, None)

            # Height/Ambient Occlusion (4)
            input_socket = Materialnode.find_height_socket(node_out)
            texture_list[4] = get_connected_texture(input_socket)
            color_list[4] = get_connected_color(input_socket, None)

            # Emissive/Illumination (5)
            input_socket = Materialnode.find_emissive_socket(node_out)
            texture_list[5] = get_connected_texture(input_socket, "", 1, True)
            color_list[5] = get_connected_color(input_socket, (0.0, 0.0, 0.0, 1.0), 2)

        return texture_list, color_list, alpha, ambient

    @staticmethod
    def add_node_data_bsdf(material, output_label, texture_list, color_list, alpha, ambient, options):
        """Setup up material nodes for Principled BSDF Shader."""
        # Cache because lazy
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        # Create an output and shaders
        node_out = nodes.new('ShaderNodeOutputMaterial')
        node_out.label = output_label
        node_out.location = (936, 577)

        node_shader = nodes.new('ShaderNodeBsdfPrincipled')
        node_shader.name = 'shader_bsdf'
        node_shader.location = (-81, 552)
        links.new(node_out.inputs[0], node_shader.outputs[0])

        # Alpha/Transparency from MDL
        # Use a math node to incorporate aurora alpha from MDL
        node_math_alpha = nodes.new('ShaderNodeMath')
        node_math_alpha.label = "Aurora Alpha"
        node_math_alpha.name = "math_aurora_alpha"
        node_math_alpha.location = (-1542, -456)
        node_math_alpha.operation = 'MULTIPLY'
        node_math_alpha.use_clamp = True
        node_math_alpha.inputs[0].default_value = 1.0
        node_math_alpha.inputs[1].default_value = alpha

        links.new(node_shader.inputs['Alpha'], node_math_alpha.outputs[0])

        # Add texture maps
        # 0 = Diffuse
        node_tex_diff = None
        node_mix_diff = None
        if color_list[0]:
            node_shader.inputs['Base Color'].default_value = color_list[0]
        if texture_list[0]:
            # Setup: Image Texture (Color) => Principled BSDF
            # Setup: Image Texture (Alpha) => Mix Transparent (Factor)
            node_tex_diff = nodes.new('ShaderNodeTexImage')
            node_tex_diff.label = "Texture: Diffuse"
            node_tex_diff.name = "texture_diffuse"
            node_tex_diff.location = (-1956, 763)
            node_tex_diff.image = nvb_utils.create_image(texture_list[0], options.filepath, options.tex_search)
            node_tex_diff.image.colorspace_settings.name = 'sRGB'
            # node_tex_diff.color_space = 'COLOR'

            links.new(node_math_alpha.inputs['Value'], node_tex_diff.outputs['Alpha'])

            # Add an extra mix rgb node and link it
            if color_list[0]:
                node_mix_diff = nodes.new('ShaderNodeMixRGB')
                node_mix_diff.label = "Color: Diffuse"
                node_mix_diff.name = "mix_diffuse"
                node_mix_diff.blend_type = 'MULTIPLY'
                node_mix_diff.location = (-1634, 881)
                node_mix_diff.use_clamp = True
                node_mix_diff.inputs['Fac'].default_value = 1.0
                node_mix_diff.inputs['Color1'].default_value = color_list[0]

                links.new(node_mix_diff.inputs['Color2'], node_tex_diff.outputs['Color'])
                links.new(node_shader.inputs['Base Color'], node_mix_diff.outputs['Color'])
            else:  # no diffuse color
                # link texture directly to shader
                links.new(node_shader.inputs['Base Color'], node_tex_diff.outputs['Color'])

        # 1 = Normal
        node_tex_norm = None
        node_norm = None
        if texture_list[1]:
            # Setup: Image Texture => Normal Map => Principled BSDF
            node_tex_norm = nodes.new('ShaderNodeTexImage')
            node_tex_norm.label = "Texture: Normal"
            node_tex_norm.name = "texture_normal"
            node_tex_norm.location = (-941, -693)
            node_tex_norm.image = nvb_utils.create_image(texture_list[1], options.filepath, options.tex_search)
            node_tex_norm.image.colorspace_settings.name = 'Non-Color'
            # node_tex_norm.color_space = 'NONE'

            node_norm = nodes.new('ShaderNodeNormalMap')
            node_norm.label = "Normal Map"
            node_norm.name = "vector_normal_map"
            node_norm.location = (-646, -591)

            links.new(node_norm.inputs['Color'], node_tex_norm.outputs['Color'])
            links.new(node_shader.inputs['Normal'], node_norm.outputs['Normal'])

        # 2 = Specular
        node_shader.inputs['Specular'].default_value = 0.0
        if color_list[2]:  # (specular color likely not present, ignored by the engine by default)
            node_shader.inputs['Specular'].default_value = color_list[2][0]
        if texture_list[2]:
            # Setup: Image Texture => Principled BSDF
            node_tex_spec = nodes.new('ShaderNodeTexImage')
            node_tex_spec.label = "Texture: Specular"
            node_tex_spec.name = "texture_specular"
            node_tex_spec.location = (-1373, 371)
            node_tex_spec.image = nvb_utils.create_image(texture_list[2], options.filepath, options.tex_search)
            node_tex_spec.image.colorspace_settings.name = 'Non-Color'

            links.new(node_shader.inputs['Specular'], node_tex_spec.outputs[0])

            # Add an extra mix rgb node and link it (if None => don't add at all)
            if color_list[2]:
                node_mix_spec = nodes.new('ShaderNodeMixRGB')
                node_mix_spec.label = "Color: Specular"
                node_mix_spec.name = "mix_specular"
                node_mix_spec.blend_type = 'MULTIPLY'
                node_mix_spec.location = (-1021, 495)
                node_mix_spec.use_clamp = True
                node_mix_spec.inputs['Fac'].default_value = 1.0
                node_mix_spec.inputs['Color1'].default_value = color_list[2]

                links.new(node_mix_spec.inputs['Color2'], node_tex_spec.outputs['Color'])
                links.new(node_shader.inputs['Specular'], node_mix_spec.outputs['Color'])

        # 3 = Roughness
        if color_list[3]:
            node_shader.inputs['Roughness'].default_value = color_list[3][0]
        if texture_list[3]:
            # Setup: Image Texture => Principled BSDF
            node_tex_rough = nodes.new('ShaderNodeTexImage')
            node_tex_rough.label = "Texture: Roughness"
            node_tex_rough.name = "texture_roughness"
            node_tex_rough.location = (-1022, 309)
            node_tex_rough.image = nvb_utils.create_image(texture_list[3], options.filepath, options.tex_search)
            node_tex_rough.image.colorspace_settings.name = 'Non-Color'

            links.new(node_shader.inputs['Roughness'], node_tex_rough.outputs['Color'])

        # 4 = Height/AO/Parallax/Displacement
        if texture_list[4]:
            # Setup, 2 options:
            if options.mat_displacement_mode == 'DISPLACEMENT':
                # 1. Image Texture => Displacement => Material Output
                node_tex_height = nodes.new('ShaderNodeTexImage')
                node_tex_height.label = "Texture: Height"
                node_tex_height.name = "texture_height"
                node_tex_height.location = (227, 353)
                node_tex_height.image = nvb_utils.create_image(texture_list[4], options.filepath, options.tex_search)
                node_tex_height.image.colorspace_settings.name = 'Non-Color'

                # Displacement offset (from mtr, 0.0 by default)
                node_displ_offset = nodes.new('ShaderNodeMath')
                node_displ_offset.label = "Displacement Offset"
                node_displ_offset.name = "math_displacement_offset"
                node_displ_offset.location = (515, 453)
                node_displ_offset.operation = 'ADD'
                node_displ_offset.use_clamp = True
                node_displ_offset.inputs[0].default_value = 0.0
                if color_list[4]:
                    node_displ_offset.inputs[0].default_value = color_list[4][0]
                node_displ_offset.inputs[1].default_value = 0.0

                node_displ = nodes.new('ShaderNodeDisplacement')
                node_displ.name = "vector_displacement"
                node_displ.location = (727, 508)

                # Links: height texture => displacement offset (1) => displacement (Height) => material output
                links.new(node_displ_offset.inputs[1], node_tex_height.outputs['Color'])
                links.new(node_displ.inputs['Height'], node_displ_offset.outputs['Value'])
                links.new(node_out.inputs['Displacement'], node_displ.outputs['Displacement'])
            else:  # options.mat_displacement_mode == 'BUMP'
                # 2. Image Texture => Bump Node => Shader
                node_tex_height = nodes.new('ShaderNodeTexImage')
                node_tex_height.label = "Texture: Height"
                node_tex_height.name = "texture_height"
                node_tex_height.location = (-940, -429)
                node_tex_height.image = nvb_utils.create_image(texture_list[4], options.filepath, options.tex_search)
                node_tex_height.image.colorspace_settings.name = 'Non-Color'

                # Displacement offset (from mtr, 0.0 by default)
                node_displ_offset = nodes.new('ShaderNodeMath')
                node_displ_offset.label = "Displacement Offset"
                node_displ_offset.name = "math_displacement_offset"
                node_displ_offset.location = (-638, -328)
                node_displ_offset.operation = 'ADD'
                node_displ_offset.use_clamp = True
                node_displ_offset.inputs[0].default_value = 0.0
                if color_list[4]:
                    node_displ_offset.inputs[0].default_value = color_list[4][0]
                node_displ_offset.inputs[1].default_value = 0.0

                node_bump = nodes.new('ShaderNodeBump')
                node_bump.name = "vector_bump"
                node_bump.location = (-384, -232)

                # Links: height texture => displacement offset (1) => bump (Height) => Shader (Normal)
                links.new(node_displ_offset.inputs[1], node_tex_height.outputs['Color'])
                links.new(node_bump.inputs['Height'], node_displ_offset.outputs['Value'])
                links.new(node_shader.inputs['Normal'], node_bump.outputs['Normal'])

                # Re-link normal node to bump node (previouly linked directly to shader)
                if node_norm:
                    links.new(node_bump.inputs['Normal'], node_norm.outputs['Normal'])

        # 5 = Illumination, Emission, Glow
        node_shader.inputs['Emission'].default_value = color_list[5]

        # Extra color node for MDL selfillum color
        node_color_emit = nodes.new('ShaderNodeRGB')
        node_color_emit.label = "Color: MDL Self-Illumination"
        node_color_emit.name = "color_mdl_selfillum"
        node_color_emit.location = (-1569, -115)
        node_color_emit.outputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
        if color_list[5]:
            node_color_emit.outputs[0].default_value = color_list[5]

        # 1st Mix node: Multiplies selfillum color from MDL with diffuse color
        node_mix_emit1 = nodes.new('ShaderNodeMixRGB')
        node_mix_emit1.label = "Mix: Multiply Self-Illumination"
        node_mix_emit1.name = "mix_selfillum_mul"
        node_mix_emit1.blend_type = 'MULTIPLY'
        node_mix_emit1.location = (-1358, 3)
        node_mix_emit1.use_clamp = True
        node_mix_emit1.inputs['Fac'].default_value = 1.0

        # Link 1st mix node inputs
        if node_color_emit:
            links.new(node_mix_emit1.inputs['Color2'], node_color_emit.outputs['Color'])
        elif color_list[5]:
            node_mix_emit1.inputs['Color2'].default_value = color_list[5]
        else:
            node_mix_emit1.inputs['Color2'].default_value = (0.0, 0.0, 0.0, 1.0)

        if node_mix_diff:
            links.new(node_mix_emit1.inputs['Color1'], node_mix_diff.outputs['Color'])
        elif node_tex_diff:
            links.new(node_mix_emit1.inputs['Color1'], node_tex_diff.outputs['Color'])
        elif color_list[0]:
            node_mix_emit1.inputs['Color1'].default_value = color_list[0]
        else:
            node_mix_emit1.inputs['Color1'].default_value = (0.0, 0.0, 0.0, 1.0)

        # Emissive/selfillum texture (only from mtr, may not be present)
        node_tex_emit = None
        if texture_list[5]:
            node_tex_emit = nodes.new('ShaderNodeTexImage')
            node_tex_emit.label = "Texture: Emission"
            node_tex_emit.name = "texture_emission"
            node_tex_emit.location = (-1192, -61)
            node_tex_emit.image = nvb_utils.create_image(texture_list[5], options.filepath, options.tex_search)
            node_tex_emit.image.colorspace_settings.name = 'sRGB'

            # 2nd mix node: Adds emissive texture to MDL selfillum color
            node_mix_emit2 = nodes.new('ShaderNodeMixRGB')
            node_mix_emit2.label = "Mix: Add Self-Illumination"
            node_mix_emit2.name = "mix_selfillum_add"
            node_mix_emit2.blend_type = 'ADD'
            node_mix_emit2.location = (-753, 98)
            node_mix_emit2.use_clamp = True
            node_mix_emit2.inputs['Fac'].default_value = 1.0
            node_mix_emit2.inputs['Color1'].default_value = color_list[5]
            node_mix_emit2.inputs['Color2'].default_value = (0.0, 0.0, 0.0, 1.0)

            # Link 1st mix node inputs
            links.new(node_mix_emit2.inputs['Color1'], node_mix_emit1.outputs['Color'])
            if node_tex_emit:
                links.new(node_mix_emit2.inputs['Color2'], node_tex_emit.outputs['Color'])

            # Finally link to shader
            links.new(node_shader.inputs['Emission'], node_mix_emit2.outputs[0])
        else:  # no emissive texture
            # link directly to shader
            links.new(node_shader.inputs['Emission'], node_mix_emit1.outputs[0])

        # Ambient color ad unconnected node for legacy reasons (may not be specified)
        if ambient:
            node_color_ambient = nodes.new('ShaderNodeRGB')
            node_color_ambient.label = "Color: Ambient (Legacy)"
            node_color_ambient.name = "color_mdl_ambient"
            node_color_ambient.location = (18, 877)
            node_color_ambient.width = 220
            if (len(ambient) > 3):
                node_color_ambient.outputs[0].default_value = ambient[:4]
            else:
                node_color_ambient.outputs[0].default_value = ambient[:3] + [1.0]

    @staticmethod
    def add_node_data_spec(material, output_label, texture_list, color_list, alpha, ambient, options):
        """Setup up material nodes for Principled BSDF Shader."""
        # Cache because lazy
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        # Create an output and shaders
        node_out = nodes.new('ShaderNodeOutputMaterial')
        node_out.label = output_label
        node_out.location = (936, 577)

        node_shader = nodes.new('ShaderNodeEeveeSpecular')
        node_shader.name = 'shader_specular'
        node_shader.location = (-81, 552)
        links.new(node_out.inputs[0], node_shader.outputs[0])

        # Alpha/Transparency from MDL
        # Setup: Image Texture (Alpha) => Math (Multiply mdl alpha) => Invert => Eevee Specular (Transparency)
        node_invert = nodes.new('ShaderNodeInvert')
        node_invert.label = "Alpha to Transparency"
        node_invert.name = "invert_alpha2trans"
        node_invert.location = (-881, -290)

        node_math_alpha = nodes.new('ShaderNodeMath')
        node_math_alpha.label = "Aurora Alpha"
        node_math_alpha.name = "math_aurora_alpha"
        node_math_alpha.location = (-1576, -337)
        node_math_alpha.operation = 'MULTIPLY'
        node_math_alpha.use_clamp = True
        node_math_alpha.inputs[1].default_value = alpha

        links.new(node_invert.inputs['Color'], node_math_alpha.outputs[0])
        links.new(node_shader.inputs['Transparency'], node_invert.outputs[0])

        # Add texture maps
        # 0 = Diffuse
        node_tex_diff = None
        node_mix_diff = None
        if color_list[0]:
            node_shader.inputs['Base Color'].default_value = color_list[0]
        if texture_list[0]:
            # Setup: Image Texture (Color) => Principled BSDF
            # Setup: Image Texture (Alpha) => Mix Transparent (Factor)
            node_tex_diff = nodes.new('ShaderNodeTexImage')
            node_tex_diff.label = "Texture: Diffuse"
            node_tex_diff.name = "texture_diffuse"
            node_tex_diff.location = (-1956, 763)
            node_tex_diff.image = nvb_utils.create_image(texture_list[0], options.filepath, options.tex_search)
            node_tex_diff.image.colorspace_settings.name = 'sRGB'
            # node_tex_diff.color_space = 'COLOR'

            # Link diffuse texture alpha to alpha node
            links.new(node_math_alpha.inputs['Value'], node_tex_diff.outputs['Alpha'])

            # Add an extra mix rgb node and link it
            if color_list[0]:
                node_mix_diff = nodes.new('ShaderNodeMixRGB')
                node_mix_diff.label = "Color: Diffuse"
                node_mix_diff.name = "mix_diffuse"
                node_mix_diff.blend_type = 'MULTIPLY'
                node_mix_diff.location = (-1634, 881)
                node_mix_diff.use_clamp = True
                node_mix_diff.inputs['Fac'].default_value = 1.0
                node_mix_diff.inputs['Color1'].default_value = color_list[0]

                links.new(node_mix_diff.inputs['Color2'], node_tex_diff.outputs['Color'])
                links.new(node_shader.inputs['Base Color'], node_mix_diff.outputs['Color'])
            else:  # no diffuse color
                # link texture directly to shader
                links.new(node_shader.inputs['Base Color'], node_tex_diff.outputs['Color'])

        # 1 = Normal
        node_tex_norm = None
        node_norm = None
        if texture_list[1]:
            # Setup: Image Texture => Normal Map => Principled BSDF
            node_tex_norm = nodes.new('ShaderNodeTexImage')
            node_tex_norm.label = "Texture: Normal"
            node_tex_norm.name = "texture_normal"
            node_tex_norm.location = (-941, -693)
            node_tex_norm.image = nvb_utils.create_image(texture_list[1], options.filepath, options.tex_search)
            node_tex_norm.image.colorspace_settings.name = 'Non-Color'
            # node_tex_norm.color_space = 'NONE'

            node_norm = nodes.new('ShaderNodeNormalMap')
            node_norm.label = "Normal Map"
            node_norm.name = "vector_normal_map"
            node_norm.location = (-646, -591)

            links.new(node_norm.inputs['Color'], node_tex_norm.outputs['Color'])
            links.new(node_shader.inputs['Normal'], node_norm.outputs['Normal'])

        # 2 = Specular
        node_shader.inputs['Specular'].default_value = (0.0, 0.0, 0.0)
        if color_list[2]:  # (specular color likely not present, ignored by the engine by default)
            node_shader.inputs['Specular'].default_value = color_list[2]
        if texture_list[2]:
            # Setup: Image Texture => Principled BSDF
            node_tex_spec = nodes.new('ShaderNodeTexImage')
            node_tex_spec.label = "Texture: Specular"
            node_tex_spec.name = "texture_specular"
            node_tex_spec.location = (-1373, 371)
            node_tex_spec.image = nvb_utils.create_image(texture_list[2], options.filepath, options.tex_search)
            node_tex_spec.image.colorspace_settings.name = 'Non-Color'

            links.new(node_shader.inputs['Specular'], node_tex_spec.outputs[0])

            # Add an extra mix rgb node and link it (if None => don't add at all)
            if color_list[2]:
                node_mix_spec = nodes.new('ShaderNodeMixRGB')
                node_mix_spec.label = "Color: Specular"
                node_mix_spec.name = "mix_specular"
                node_mix_spec.blend_type = 'MULTIPLY'
                node_mix_spec.location = (-1021, 495)
                node_mix_spec.use_clamp = True
                node_mix_spec.inputs['Fac'].default_value = 1.0
                node_mix_spec.inputs['Color1'].default_value = color_list[2]

                links.new(node_mix_spec.inputs['Color2'], node_tex_spec.outputs['Color'])
                links.new(node_shader.inputs['Specular'], node_mix_spec.outputs['Color'])

        # 3 = Roughness
        if color_list[3]:
            node_shader.inputs['Roughness'].default_value = color_list[3][0]
        if texture_list[3]:
            # Setup: Image Texture => Principled BSDF
            node_tex_rough = nodes.new('ShaderNodeTexImage')
            node_tex_rough.label = "Texture: Roughness"
            node_tex_rough.name = "texture_roughness"
            node_tex_rough.location = (-1022, 309)
            node_tex_rough.image = nvb_utils.create_image(texture_list[3], options.filepath, options.tex_search)
            node_tex_rough.image.colorspace_settings.name = 'Non-Color'

            links.new(node_shader.inputs['Roughness'], node_tex_rough.outputs['Color'])

        # 4 = Height/AO/Parallax/Displacement
        if texture_list[4]:
            # Setup, 2 options:
            if options.mat_displacement_mode == 'DISPLACEMENT':
                # 1. Image Texture => Displacement => Material Output
                node_tex_height = nodes.new('ShaderNodeTexImage')
                node_tex_height.label = "Texture: Height"
                node_tex_height.name = "texture_height"
                node_tex_height.location = (227, 353)
                node_tex_height.image = nvb_utils.create_image(texture_list[4], options.filepath, options.tex_search)
                node_tex_height.image.colorspace_settings.name = 'Non-Color'

                # Displacement offset (from mtr, 0.0 by default)
                node_displ_offset = nodes.new('ShaderNodeMath')
                node_displ_offset.label = "Displacement Offset"
                node_displ_offset.name = "math_displacement_offset"
                node_displ_offset.location = (515, 453)
                node_displ_offset.operation = 'ADD'
                node_displ_offset.use_clamp = True
                node_displ_offset.inputs[0].default_value = 0.0
                if color_list[4]:
                    node_displ_offset.inputs[0].default_value = color_list[4][0]
                node_displ_offset.inputs[1].default_value = 0.0

                node_displ = nodes.new('ShaderNodeDisplacement')
                node_displ.name = "vector_displacement"
                node_displ.location = (727, 508)

                # Links: height texture => displacement offset (1) => displacement (Height) => material output
                links.new(node_displ_offset.inputs[1], node_tex_height.outputs['Color'])
                links.new(node_displ.inputs['Height'], node_displ_offset.outputs['Value'])
                links.new(node_out.inputs['Displacement'], node_displ.outputs['Displacement'])
            else:  # options.mat_displacement_mode == 'BUMP'
                # 2. Image Texture => Bump Node => Shader
                node_tex_height = nodes.new('ShaderNodeTexImage')
                node_tex_height.label = "Texture: Height"
                node_tex_height.name = "texture_height"
                node_tex_height.location = (-940, -429)
                node_tex_height.image = nvb_utils.create_image(texture_list[4], options.filepath, options.tex_search)
                node_tex_height.image.colorspace_settings.name = 'Non-Color'

                # Displacement offset (from mtr, 0.0 by default)
                node_displ_offset = nodes.new('ShaderNodeMath')
                node_displ_offset.label = "Displacement Offset"
                node_displ_offset.name = "math_displacement_offset"
                node_displ_offset.location = (-638, -328)
                node_displ_offset.operation = 'ADD'
                node_displ_offset.use_clamp = True
                node_displ_offset.inputs[0].default_value = 0.0
                if color_list[4]:
                    node_displ_offset.inputs[0].default_value = color_list[4][0]
                node_displ_offset.inputs[1].default_value = 0.0

                node_bump = nodes.new('ShaderNodeBump')
                node_bump.name = "vector_bump"
                node_bump.location = (-384, -232)

                # Links: height texture => displacement offset (1) => bump (Height) => Shader (Normal)
                links.new(node_displ_offset.inputs[1], node_tex_height.outputs['Color'])
                links.new(node_bump.inputs['Height'], node_displ_offset.outputs['Value'])
                links.new(node_shader.inputs['Normal'], node_bump.outputs['Normal'])

                # Re-link normal node to bump node (previouly linked directly to shader)
                if node_norm:
                    links.new(node_bump.inputs['Normal'], node_norm.outputs['Normal'])

        # 5 = Illumination, Emission, Glow
        node_shader.inputs['Emissive Color'].default_value = color_list[5]

        # Extra color node for MDL selfillum color
        node_color_emit = nodes.new('ShaderNodeRGB')
        node_color_emit.label = "Color: MDL Self-Illumination"
        node_color_emit.name = "color_mdl_selfillum"
        node_color_emit.location = (-1569, -115)
        node_color_emit.outputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
        if color_list[5]:
            node_color_emit.outputs[0].default_value = color_list[5]

        # 1st Mix node: Multiplies selfillum color from MDL with diffuse color
        node_mix_emit1 = nodes.new('ShaderNodeMixRGB')
        node_mix_emit1.label = "Mix: Multiply Self-Illumination"
        node_mix_emit1.name = "mix_selfillum_mul"
        node_mix_emit1.blend_type = 'MULTIPLY'
        node_mix_emit1.location = (-1358, 3)
        node_mix_emit1.use_clamp = True
        node_mix_emit1.inputs['Fac'].default_value = 1.0

        # Link 1st mix node inputs
        if node_color_emit:
            links.new(node_mix_emit1.inputs['Color2'], node_color_emit.outputs['Color'])
        elif color_list[5]:
            node_mix_emit1.inputs['Color2'].default_value = color_list[5]
        else:
            node_mix_emit1.inputs['Color2'].default_value = (0.0, 0.0, 0.0, 1.0)

        if node_mix_diff:
            links.new(node_mix_emit1.inputs['Color1'], node_mix_diff.outputs['Color'])
        elif node_tex_diff:
            links.new(node_mix_emit1.inputs['Color1'], node_tex_diff.outputs['Color'])
        elif color_list[0]:
            node_mix_emit1.inputs['Color1'].default_value = color_list[0]
        else:
            node_mix_emit1.inputs['Color1'].default_value = (0.0, 0.0, 0.0, 1.0)

        # Emissive/selfillum texture (only from mtr, may not be present)
        node_tex_emit = None
        if texture_list[5]:
            node_tex_emit = nodes.new('ShaderNodeTexImage')
            node_tex_emit.label = "Texture: Emission"
            node_tex_emit.name = "texture_emission"
            node_tex_emit.location = (-1192, -61)
            node_tex_emit.image = nvb_utils.create_image(texture_list[5], options.filepath, options.tex_search)
            node_tex_emit.image.colorspace_settings.name = 'sRGB'

            # 2nd mix node: Adds emissive texture to MDL selfillum color
            node_mix_emit2 = nodes.new('ShaderNodeMixRGB')
            node_mix_emit2.label = "Mix: Add Self-Illumination"
            node_mix_emit2.name = "mix_selfillum_add"
            node_mix_emit2.blend_type = 'ADD'
            node_mix_emit2.location = (-753, 98)
            node_mix_emit2.use_clamp = True
            node_mix_emit2.inputs['Fac'].default_value = 1.0
            node_mix_emit2.inputs['Color1'].default_value = color_list[5]
            node_mix_emit2.inputs['Color2'].default_value = (0.0, 0.0, 0.0, 1.0)

            # Link 1st mix node inputs
            links.new(node_mix_emit2.inputs['Color1'], node_mix_emit1.outputs['Color'])
            if node_tex_emit:
                links.new(node_mix_emit2.inputs['Color2'], node_tex_emit.outputs['Color'])

            # Finally link to shader
            links.new(node_shader.inputs['Emissive Color'], node_mix_emit2.outputs[0])

        else:  # no emissive texture
            # link directly to shader
            links.new(node_shader.inputs['Emission'], node_mix_emit1.outputs[0])

        # Ambient color ad unconnected node for legacy reasons (may not be specified)
        if ambient:
            node_color_ambient = nodes.new('ShaderNodeRGB')
            node_color_ambient.label = "Color: Ambient (Legacy)"
            node_color_ambient.name = "color_mdl_ambient"
            node_color_ambient.location = (18, 877)
            node_color_ambient.width = 220
            if (len(ambient) > 3):
                node_color_ambient.outputs[0].default_value = ambient[:4]
            else:
                node_color_ambient.outputs[0].default_value = ambient[:3] + [1.0]

    @staticmethod
    def add_node_data(material, output_name, texture_list, color_list, alpha, ambient, options):
        """Select shader nodes based on options."""
        if (options.mat_shader == 'ShaderNodeEeveeSpecular'):
            Materialnode.add_node_data_spec(material, output_name,
                                            texture_list, color_list, alpha, ambient,
                                            options)
        else:
            Materialnode.add_node_data_bsdf(material, output_name,
                                            texture_list, color_list, alpha, ambient,
                                            options)
