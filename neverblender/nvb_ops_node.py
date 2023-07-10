"""Contains  Blender operators to help set up mdls."""

import math
import sys
import re
import itertools
# import array

import bpy
import bmesh
import mathutils

from . import nvb_def
from . import nvb_utils


class NVB_OT_util_genwok(bpy.types.Operator):
    """Load all materials for aabb walkmeshes for the selected object"""

    bl_idname = 'nvb.util_genwok'
    bl_label = 'Load walkmesh materials'

    @classmethod
    def poll(self, context):
        """Enable only if a Mesh is selected."""
        return (context.object and context.object.type == 'MESH')

    def execute(self, context):
        """Delete all current materials and add walkmesh materials."""
        # We can't move around material indices directly. Instead we have
        # to remove all materials an re-create them.
        # That will delete face material indices as well however.
        obj = context.object

        # Save old material indices
        # This will only work, if the Operator is called with ALL wok materials
        # already present (User re-adds materials)
        face_mats = [0]*len(obj.data.polygons)
        obj.data.polygons.foreach_get('material_index', face_mats)

        # Fix material indices so they match the ones in the wok definition
        # This will only work if wok materials are at least partially present
        wok_indices = {wm[0]: wm_idx for wm_idx, wm in
                       enumerate(nvb_def.wok_materials)}
        for ms_idx, ms in enumerate(obj.material_slots):
            wok_idx = wok_indices[ms.material.name]
            if wok_idx != ms_idx:
                face_mats = [-1*wok_idx if f_idx == ms_idx else f_idx for f_idx in face_mats]
        face_mats = [abs(f_idx) for f_idx in face_mats]

        # Remove all material (slots)
        for _ in range(len(obj.material_slots)):
            bpy.ops.object.material_slot_remove()
        obj.material_slots.update()

        # Add wok materials (and update existing ones)
        nvb_utils.create_wok_materials(obj.data, True)
        obj.material_slots.update()

        # Restore face material indices
        obj.data.polygons.foreach_set('material_index', face_mats)
        obj.data.update()

        test = [0]*len(obj.data.polygons)
        obj.data.polygons.foreach_get('material_index', test)

        context.view_layer.update()

        return {'FINISHED'}


class NVB_OT_util_nodes_pwk(bpy.types.Operator):
    """Helper to add missing nodes and walkmeshes for placeables"""

    bl_idname = 'nvb.util_nodes_pwk'
    bl_label = "Setup Placeable"
    bl_options = {'UNDO'}

    @staticmethod
    def chulls_collide(chull1, chull2):
        """Detects collision between two convex hulls."""

        def get_edges(point_list):
            """Returns tuples representing edges between the polygon verts."""
            return zip(*[point_list[i:]+point_list[:i] for i in range(2)])

        def is_separating_axis(axis, vlist1, vlist2):
            """Checks if axis separates the vertices from the lists."""
            min1, max1 = sys.maxsize, -1*sys.maxsize
            min2, max2 = sys.maxsize, -1*sys.maxsize
            for v in vlist1:
                projection = v.dot(axis)
                min1 = min(min1, projection)
                max1 = max(max1, projection)
            for v in vlist2:
                projection = v.dot(axis)
                min2 = min(min2, projection)
                max2 = max(max2, projection)
            if max1 >= min2 and max2 >= min1:  # not separating
                return False
            return True

        def separating_axis_distance(axis, vlist1, vlist2):
            """Checks if axis separates the vertices from the lists."""
            min1, max1 = sys.maxsize, -1*sys.maxsize
            min2, max2 = sys.maxsize, -1*sys.maxsize
            for v in vlist1:
                projection = v.dot(axis)
                min1 = min(min1, projection)
                max1 = max(max1, projection)
            for v in vlist2:
                projection = v.dot(axis)
                min2 = min(min2, projection)
                max2 = max(max2, projection)
            if max1 >= min2 and max2 >= min1:  # not separating
                dist = -1 * min(max1 - min2, max2 - min1) / axis.dot(axis)
            else:  # separating
                dist = min(min2 - max1, min1 - max2) / axis.dot(axis)
            return dist
        # Compute edges
        edges = [v2 - v1 for v1, v2 in get_edges(chull1)]
        edges.extend([v2 - v1 for v1, v2 in get_edges(chull2)])
        # 90° orthogonal to convex hull edges
        orthogonals = [mathutils.Vector([-1*vec[1], vec[0]]) for vec in edges]
        # Check distances of all separating axes
        for ortho in orthogonals:
            if is_separating_axis(ortho, chull1, chull2):
                return False
        return True

    @staticmethod
    def get_pwk_shape(island_list, pwk_mode):
        """Merge intersecting mesh parts."""
        def merge_intersecting(idx, idx_dict, merged):
            """TODO: Doc."""
            if idx in idx_dict:
                intersecting = idx_dict.pop(idx)
                for new_idx in intersecting:
                    merge_intersecting(new_idx, idx_dict, merged)
                merged.add(idx)
        # Calculate pwk shapes (2D shape + height)
        pwk_shapes = []
        if pwk_mode == 'chull':  # Convex hull
            pwk_shapes = [(NVB_OT_util_nodes_pwk.get_convex_hull_2D(isl), h)
                          for isl, h in island_list]
        elif pwk_mode == 'mabr':  # Minimum area bounding rectangle
            pwk_shapes = [(NVB_OT_util_nodes_pwk.get_mabr(isl), h)
                          for isl, h in island_list]
        else:  # Axis aligned bounding rectangle
            pwk_shapes = [(NVB_OT_util_nodes_pwk.get_aabr(isl), h)
                          for isl, h in island_list]
        if not pwk_shapes:
            return []
        # Detect intersecting shapes
        combinations = itertools.combinations(enumerate(pwk_shapes), 2)
        intersections = {k: set() for k in range(len(pwk_shapes))}
        for (idx_a, (pwk_a, _)), (idx_b, (pwk_b, _)) in combinations:
            if NVB_OT_util_nodes_pwk.chulls_collide(pwk_a, pwk_b):
                intersections[idx_a].add(idx_b)
        # Merge intersecting
        merged_islands = []
        for pwk_id in range(len(pwk_shapes)):
            ids_to_merge = set()
            merge_intersecting(pwk_id, intersections, ids_to_merge)
            if ids_to_merge:
                merged_shapes = [pwk_shapes[id] for id in ids_to_merge]
                new_height = max([ms[1] for ms in merged_shapes])
                new_verts = [point for ms in merged_shapes for point in ms[0]]
                merged_islands.append((new_verts, new_height))
        # Recalulate shapes
        if pwk_mode == 'chull':  # Convex hull
            pwk_shapes = [(NVB_OT_util_nodes_pwk.get_convex_hull_2D(isl), h)
                          for isl, h in merged_islands]
        elif pwk_mode == 'mabr':  # Minimum area bounding rectangle
            pwk_shapes = [(NVB_OT_util_nodes_pwk.get_mabr(isl), h)
                          for isl, h in merged_islands]
        else:  # Axis aligned bounding rectangle
            pwk_shapes = [(NVB_OT_util_nodes_pwk.get_aabr(isl), h)
                          for isl, h in merged_islands]

        return pwk_shapes

    @staticmethod
    def build_pwk_mesh(pwk_data, mesh_name, min_vert_dist=0.1, min_area=0.1):
        """Extrudes planes to height in order to generate a mesh."""
        if not pwk_data:
            return None
        bm = bmesh.new()
        # Loop over islands = (vertex list, height) pairs
        for plane_vertices, height in pwk_data:
            plane_vertices_3d = [mathutils.Vector((pv.x, pv.y, 0.0))
                                 for pv in plane_vertices]
            bm_plane_vertices = [bm.verts.new(pv) for pv in plane_vertices_3d]
            if len(bm_plane_vertices) > 2:
                # Create a single face
                bottom_face = bm.faces.new(bm_plane_vertices)
                # Remove duplicate (or close) vertices
                bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts], dist=min_vert_dist)
                # There may not be anything left after removing doubles
                if bottom_face and bottom_face.is_valid and bottom_face.calc_area() > min_area:
                    # Extrude and translate
                    top_face = bmesh.ops.extrude_face_region(bm, geom=[bottom_face])
                    bmesh.ops.translate(
                        bm,
                        vec=mathutils.Vector((0, 0, max(0.1, height))),
                        verts=[v for v in top_face['geom']
                            if isinstance(v, bmesh.types.BMVert)])
                    # scale top mesh dow a little to prevent overlap
                    bmesh.ops.scale(bm,
                                    vec=mathutils.Vector((0.9, 0.9, 1.0)),
                                    space=mathutils.Matrix.Translation(-bottom_face.calc_center_median()),
                                    verts=[v for v in top_face['geom']if isinstance(v, bmesh.types.BMVert)])
                    bm.normal_update()
                    # Remove the bottom plane (face only, we don't actually need it)
                    bmesh.ops.delete(bm, geom=[bottom_face], context='FACES_ONLY')

        # Create mesh from bmesh, if thera are any faces:
        if bm.faces:
            me = bpy.data.meshes.new(mesh_name)
            bm.to_mesh(me)
            return me
        return None

    @staticmethod
    def get_mabr(vertex_list):
        """Get the minimum area bounding rectangle (rotating calipers)."""
        if not vertex_list:  # No geometry
            return []
        chull = NVB_OT_util_nodes_pwk.get_convex_hull_2D(vertex_list)
        # Compute edges v2 - v1
        edges = [v2 - v1 for v1, v2 in zip(chull[::2], chull[1::2])]
        angles = [abs(math.atan2(e[1], e[0]) % (math.pi/2)) for e in edges]
        # TODO: Remove duplicate angles
        # rot_angle, area, min_x, max_x, min_y, max_y
        min_bbox = (0, sys.maxsize, 0, 0, 0, 0)
        for a in angles:
            R = mathutils.Matrix.Rotation(a, 2)
            rotated_hull = [R @ p for p in chull]
            # Get bounding box for rotated hull
            x_vals = [p.x for p in rotated_hull]
            min_x, max_x = min(x_vals), max(x_vals)
            y_vals = [p.y for p in rotated_hull]
            min_y, max_y = min(y_vals), max(y_vals)
            # Calculate area
            width = max_x - min_x
            height = max_y - min_y
            area = width * height
            if (area < min_bbox[1]):
                min_bbox = (a, area, min_x, max_x, min_y, max_y)
        # Calculate corner points in orignal space
        R = mathutils.Matrix.Rotation(min_bbox[0], 2)
        min_x = min_bbox[2]
        max_x = min_bbox[3]
        min_y = min_bbox[4]
        max_y = min_bbox[5]
        mabr = [None] * 4
        mabr[3] = mathutils.Vector([max_x, min_y]) @ R
        mabr[2] = mathutils.Vector([min_x, min_y]) @ R
        mabr[1] = mathutils.Vector([min_x, max_y]) @ R
        mabr[0] = mathutils.Vector([max_x, max_y]) @ R
        return mabr

    @staticmethod
    def get_aabr(vertex_list):
        """Get axis aligned bounding rectangle."""
        if not vertex_list:  # No geometry
            return []
        coords = [v.x for v in vertex_list]
        min_x, max_x = min(coords), max(coords)
        coords = [v.y for v in vertex_list]
        min_y, max_y = min(coords), max(coords)
        aabr = [None] * 4
        aabr[3] = mathutils.Vector([max_x, min_y])
        aabr[2] = mathutils.Vector([min_x, min_y])
        aabr[1] = mathutils.Vector([min_x, max_y])
        aabr[0] = mathutils.Vector([max_x, max_y])
        return aabr

    @staticmethod
    def get_convex_hull_2D(vertex_list):
        """Get 2D convex hull from a list of vertices (omits z-coordinate)."""
        def uv_split(u, v, points):
            """ Get Points on left side of UV."""
            return [p for p in points if (p - u).cross(v - u) < 0]

        def uv_search(u, v, points):
            if not points:
                return []
            # find furthest point W, and split search to WV, UW
            w = min(points, key=lambda p: (p - u).cross(v - u))
            p1, p2 = uv_split(w, v, points), uv_split(u, w, points)
            return uv_search(w, v, p1) + [w] + uv_search(u, w, p2)

        def convex_hull(points):
            """Quickhull algorithm to compute convex hull."""
            # find two hull points, U, V, and split to left and right search
            u = min(points, key=lambda p: p[0])
            v = max(points, key=lambda p: p[0])
            left, right = uv_split(u, v, points), uv_split(v, u, points)
            # find convex hull on each side
            return [v] + uv_search(u, v, left) + [u] + uv_search(v, u, right)

        if not vertex_list:  # No geometry
            return []
        vertex_list_2D = [mathutils.Vector(v[:2]) for v in vertex_list]
        return convex_hull(vertex_list_2D)

    @staticmethod
    def get_bm_islands(bm):
        """Get a list of islands in the bmesh with a minimum of 2 vertices."""
        def walk_island(vert):
            """Walk linked verts without tag"""
            vert.tag = True
            yield(vert)
            linked_verts = [e.other_vert(vert) for e in vert.link_edges
                            if not e.other_vert(vert).tag]
            for v in linked_verts:
                if v.tag:
                    continue
                yield from walk_island(v)

        def set_tag(vertices, tag_value):
            for v in vertices:
                v.tag = tag_value
        vertex_list = bm.verts
        set_tag(bm.verts, True)
        set_tag(vertex_list, False)
        island_list = []
        vertices = set(vertex_list)
        while vertices:
            v = vertices.pop()
            vertices.add(v)
            island = set(walk_island(v))
            if len(island) > 2:  # Can't create a polygon from 2 verts
                island_list.append(list(island))
            set_tag(island, False)  # remove tag = True
            vertices -= island
        return island_list

    @staticmethod
    def get_mdl_islands(mdl_base, min_height=-0.1, max_height=2.0):
        """Return the vertex islands of all visible objects in the mdl."""
        # Get visible objects for this mdl
        obj_list = []
        nvb_utils.get_children_recursive(mdl_base, obj_list)
        obj_list = [o for o in obj_list
                    if o.type == 'MESH' and
                    o.nvb.render and
                    o.nvb.meshtype == nvb_def.Meshtype.TRIMESH and
                    not nvb_utils.is_wkm_base(o.parent)]
        # Disregard (undo) mdl_base transformations
        mdl_mwi = mdl_base.matrix_world.inverted()
        # Get vertex islands for the objects
        mdl_islands = []
        for obj in obj_list:
            obj_mw = obj.matrix_world
            obj_mwi = obj_mw.inverted()
            # Bisecting planes in local coordinates
            plane_bot_co = obj_mwi @ mathutils.Vector((0.0, 0.0, min_height))
            plane_bot_no = mathutils.Vector((0.0, 0.0, -1.0))
            plane_bot_no.rotate(obj_mwi)
            plane_top_co = obj_mwi @ mathutils.Vector((0.0, 0.0, max_height))
            plane_top_no = mathutils.Vector((0.0, 0.0, 1.0))
            plane_top_no.rotate(obj_mwi)
            # Bisect mesh
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            # Disregard mdl_base transformations
            bmesh.ops.transform(bm,
                                matrix=mdl_mwi,
                                space=obj_mw,
                                verts=bm.verts)
            # Cut bottom plane
            bm.verts.ensure_lookup_table()
            res = bmesh.ops.bisect_plane(
                bm,
                geom=bm.verts[:]+bm.edges[:]+bm.faces[:],
                plane_co=plane_bot_co,
                plane_no=plane_bot_no,
                clear_outer=True, dist=0.001)
            # Cut top plane
            res = bmesh.ops.bisect_plane(
                bm,
                geom=bm.verts[:]+bm.edges[:]+bm.faces[:],
                plane_co=plane_top_co,
                plane_no=plane_top_no,
                clear_outer=True, dist=0.001)
            del res
            # Detect islands
            obj_islands = NVB_OT_util_nodes_pwk.get_bm_islands(bm)
            for isl in obj_islands:
                isl_verts = [obj_mw @ v.co for v in isl]
                # Determine height
                if isl_verts:
                    isl_height = max(0.1, max([v.z for v in isl_verts]))
                else:
                    isl_height = 0.2
                mdl_islands.append([isl_verts, isl_height])
            # mdl_islands.extend([[obj_mw @ v.co for v in isl]
            #                     for isl in obj_islands])
        return mdl_islands

    @staticmethod
    def get_mdl_vertices(mdl_base, min_height=-0.1, max_height=2.0):
        """Get a list of relevant vertices for this mdl."""
        # Get visible objects for this mdl
        obj_list = []
        nvb_utils.get_children_recursive(mdl_base, obj_list)
        obj_list = [o for o in obj_list
                    if o.type == 'MESH' and
                    o.nvb.render and
                    o.nvb.meshtype == nvb_def.Meshtype.TRIMESH and
                    not nvb_utils.is_wkm_base(o.parent)]
        # Disregard (undo) mdl_base transformations
        mdl_mwi = mdl_base.matrix_world.inverted()
        # Collect vertices from all objects
        vertex_list = []
        vertex_height = 0.2
        for obj in obj_list:
            obj_mw = obj.matrix_world
            obj_mwi = obj_mw.inverted()
            # Create bisecting planes in local coordinates
            plane_bot_co = obj_mwi @ mathutils.Vector((0.0, 0.0, min_height))
            plane_bot_no = mathutils.Vector((0.0, 0.0, -1.0))
            plane_bot_no.rotate(obj_mwi)
            plane_top_co = obj_mwi @ mathutils.Vector((0.0, 0.0, max_height))
            plane_top_no = mathutils.Vector((0.0, 0.0, 1.0))
            plane_top_no.rotate(obj_mwi)
            # Bisect mesh
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            # Disregard mdl_base transformations
            bmesh.ops.transform(bm,
                                matrix=mdl_mwi,
                                space=obj_mw,
                                verts=bm.verts)
            # Cut bottom plane
            bm.verts.ensure_lookup_table()
            res = bmesh.ops.bisect_plane(
                bm,
                geom=bm.verts[:]+bm.edges[:]+bm.faces[:],
                plane_co=plane_bot_co,
                plane_no=plane_bot_no,
                clear_outer=True, dist=0.001)
            # Cut top plane
            res = bmesh.ops.bisect_plane(
                bm,
                geom=bm.verts[:]+bm.edges[:]+bm.faces[:],
                plane_co=plane_top_co,
                plane_no=plane_top_no,
                clear_outer=True, dist=0.001)
            del res
            obj_verts = [obj_mw @ v.co for v in bm.verts]
            vertex_list.extend(obj_verts)

        if vertex_list:
            vertex_height = max([v.z for v in vertex_list])

        return [vertex_list, vertex_height]

    @staticmethod
    def create_pwk_mesh(mdl_base, pwk_base, mesh_name, layer,
                        pwk_mode, detect_islands=True):
        """Create the placeable walkmesh for this mdl."""
        pwk_obj = None
        # Get vertex islands from all visible objects
        island_list = []
        if detect_islands:
            island_list = NVB_OT_util_nodes_pwk.get_mdl_islands(mdl_base)
        else:  # Single island
            island_list = [NVB_OT_util_nodes_pwk.get_mdl_vertices(mdl_base)]
        # Generate plane shapes based on options
        pwk_data = NVB_OT_util_nodes_pwk.get_pwk_shape(island_list, pwk_mode)
        # Generate Mesh from pwk data (plane vertices + height)
        mesh = NVB_OT_util_nodes_pwk.build_pwk_mesh(pwk_data, mesh_name)
        if mesh:
            pwk_obj = bpy.data.objects.new(mesh_name, mesh)
            pwk_obj.parent = pwk_base
            for collection in pwk_base.users_collection:
                collection.objects.link(pwk_obj)
            layer.update()
            # Use modifier to dissolve faces/verts along straight lines
            modifier = pwk_obj.modifiers.new(name='Decimate', type='DECIMATE')
            modifier.decimate_type = 'DISSOLVE'
            modifier.angle_limit = 0.267  # about 15°
            modifier.use_dissolve_boundaries = True
            # Apply modifier
            ctx = bpy.context.copy()
            ctx['object'] = pwk_obj
            ctx['modifier'] = modifier
            bpy.ops.object.modifier_apply(ctx, modifier=ctx['modifier'].name)
        return pwk_obj

    @staticmethod
    def create_empties(empty_data, prefix, parent, layer, obj_list=[]):
        """Create empty objects if not already existing."""
        if not obj_list:
            return
        for suffix, loc in empty_data:
            dummy_name = prefix + suffix
            existing = [o for o in obj_list if o.name.endswith(suffix)]
            if existing:  # Adjust name and parent for existing objects
                for obj in existing:
                    if obj.name != dummy_name:
                        # Avoid renaming to same name (results in .001 suffix)
                        obj.name = dummy_name
                    obj.parent = parent
            else:  # Create missing dummies
                obj = bpy.data.objects.new(dummy_name, None)
                obj.location = loc
                obj.parent = parent
                for collection in parent.users_collection:
                    collection.objects.link(obj)
        layer.update()

    @staticmethod
    def create_mdl_dummys(mdl_base, name_prefix, layer):
        """Create necessary empties/dummies for the mdl."""
        mdl_objects = [mdl_base]
        nvb_utils.get_children_recursive(mdl_base, mdl_objects)
        # Get relevant vertices
        vertices = []
        for obj in mdl_objects:
            if obj.type == 'MESH' and \
               obj.nvb.meshtype == nvb_def.Meshtype.TRIMESH:
                mat = mdl_base.matrix_world.inverted() @ obj.matrix_world
                vertices.extend([mat @ v.co for v in obj.data.vertices])
        # Calculate needed values
        if vertices:
            vec = sum(vertices, mathutils.Vector([0.0, 0.0, 0.0])) / len(vertices)
            mdl_center = [round(co, 2) for co in vec]
            mdl_height = round(max(max([v.z for v in vertices]), 0.1), 2)
            mdl_max_y = round(max([v.y for v in vertices]), 2)
        else:
            mdl_center = mathutils.Vector([0.0, 0.0, 0.5])
            mdl_height = 1.0
            mdl_max_y = 0.5
        # Create dummys or check existing - all parented to mdl base
        dummy_data = [['_hand', (mdl_center[0], mdl_max_y, mdl_center[2])],
                      ['_head_hit', (*mdl_center[:2], mdl_height)],
                      ['_impact', mdl_center],
                      ['_ground', (*mdl_center[:2], 0.0)]]
        NVB_OT_util_nodes_pwk.create_empties(dummy_data, name_prefix, mdl_base, layer, mdl_objects)

    @staticmethod
    def create_pwk_dummys(mdl_base, name_prefix, layer, pwk_base, pwk_mesh):
        """Create necessary empties/dummies for the pwk."""
        objects_to_check = [mdl_base]
        nvb_utils.get_children_recursive(mdl_base, objects_to_check)
        # Get relevant vertices
        if pwk_mesh and pwk_mesh.data.vertices:
            mat = mdl_base.matrix_world.inverted() @ pwk_mesh.matrix_world
            vertices = [mat @ v.co for v in pwk_mesh.data.vertices]
            pwk_x_center = round(sum([v.x for v in vertices])
                                 / len(vertices), 2)
            y_coords = [v.y for v in vertices]
            pwk_y_min = round(min(y_coords), 2)
            pwk_y_max = round(max(y_coords), 2)
        else:
            pwk_x_center = 0.0
            pwk_y_min = -1.0
            pwk_y_max = 1.0
        # Create dummys or check existing - all parented to mdl base
        dummy_data = [['pwk_use01', (pwk_x_center, pwk_y_min - 0.5, 0.0)],
                      ['pwk_use02', (pwk_x_center, pwk_y_max + 0.5, 0.0)]]
        NVB_OT_util_nodes_pwk.create_empties(dummy_data, name_prefix, pwk_base, layer, objects_to_check)

    def setup_placeable(self, mdl_base, layer, pwk_mode, detect_islands):
        """Adds necessary (walkmesh) objects to mdlRoot."""
        def get_pwk_base(mdl_base, pwk_base_name):
            """Find or create pwk base."""
            pwk_base = nvb_utils.get_wkm_base(mdl_base,
                                              nvb_def.Walkmeshtype.PWK)
            if pwk_base:  # Adjust existing walkmesh base
                # renaming to same name results in trailing numbers
                if pwk_base.name != pwk_base_name:
                    pwk_base.name = pwk_base_name
            else:  # Create new walkmesh base
                pwk_base = bpy.data.objects.new(pwk_base_name, None)
                pwk_base.nvb.emptytype = nvb_def.Emptytype.PWK
                for collection in mdl_base.users_collection:
                    collection.objects.link(pwk_base)
            pwk_base.parent = mdl_base
            pwk_base.location = (0.0, 0.0, 0.0)  # at mdl_base
            return pwk_base

        mdl_base_name = nvb_utils.strip_trailing_numbers(mdl_base.name)

        # Get a name prefix from the mdl base name
        name_prefix = mdl_base_name[-3:]

        # Find or create walkmesh base
        pwk_base_name = mdl_base_name + '_pwk'
        pwk_base = get_pwk_base(mdl_base, pwk_base_name)

        # Find or create (pwk) walkmesh
        pwk_mesh_list = [c for c in pwk_base.children if c.type == 'MESH']
        pwk_mesh = None
        if len(pwk_mesh_list) == 1:  # Rename single existing
            pwk_mesh = pwk_mesh_list.pop(0)
            pwk_mesh.name = name_prefix + '_wg'
        elif len(pwk_mesh_list) > 1:   # Add number if multiple
            fstr = name_prefix + '{:02d}_wg'
            for idx, wkm in enumerate(pwk_mesh_list):
                wkm.name = fstr.format(idx)
        else:  # create new
            pwk_mesh_name = name_prefix + '_wg'
            pwk_mesh = NVB_OT_util_nodes_pwk.create_pwk_mesh(
                mdl_base, pwk_base, pwk_mesh_name, layer,
                pwk_mode, detect_islands)

        # Object for PWK file
        # The prefix for placeable PWK dummies are four arbitratrily chosen characters, but
        # We'll use the last three character of the model name + an underscore
        name_prefix = mdl_base_name[-3:]+"_"
        # if not long enough: make something up
        if len(name_prefix) < 4:
            name_prefix = "plc_"
        # First character should be a letter
        if not str.isalpha(name_prefix[0]):
            name_prefix = "p" + name_prefix[1:]
        # Create dummys or check existing - all parented to pwk base
        NVB_OT_util_nodes_pwk.create_pwk_dummys(mdl_base, name_prefix, layer, pwk_base, pwk_mesh)
        # Objects for mDL file
        # The prefix for placeable MODEL dummies the mdl base name with the first four characters cropped
        name_prefix = mdl_base_name[4:]
        # Create dummys or check existing - all parented to mdl base
        NVB_OT_util_nodes_pwk.create_mdl_dummys(mdl_base, name_prefix, layer)

    @classmethod
    def poll(self, context):
        """Prevent execution if no object is selected."""
        return context.object is not None

    def execute(self, context):
        """Create Walkmesh root and objects."""
        mdl_base = nvb_utils.get_obj_mdl_base(context.object)
        addon = context.preferences.addons[__package__]
        layer = context.view_layer
        if not mdl_base:
            self.report({'ERROR'}, 'No Aurora Base')
            return {'CANCELLED'}
        pwk_mode = addon.preferences.util_nodes_pwk_mode
        detect_islands = addon.preferences.util_nodes_pwk_detect_islands
        self.setup_placeable(mdl_base, layer, pwk_mode, detect_islands)
        self.report({'INFO'}, 'Created objects')
        return {'FINISHED'}


class NVB_OT_util_nodes_dwk(bpy.types.Operator):
    """Helper to add missing nodes and walkmeshes for doors"""

    bl_idname = 'nvb.util_nodes_dwk'
    bl_label = "Setup Door"
    bl_options = {'UNDO'}

    @staticmethod
    def create_dwk_mesh(mdl_base, dwk_base, name_prefix, layer, dwk_mode):
        """Create the door walkmesh for this mdl."""
        def get_default_mesh(meshname, dim=mathutils.Vector((0.1, 2.0, 3.0))):
            """Generate the default (walk)mesh for a generic door."""
            vertices = [(dim.y, -1*dim.x, 0.0),
                        (0.0,   -1*dim.x, 0.0),
                        (dim.y, -1*dim.x, dim.z),
                        (0.0,   -1*dim.x, dim.z),
                        (dim.y,    dim.x, 0.0),
                        (0.0,      dim.x, 0.0),
                        (dim.y,    dim.x, dim.z),
                        (0.0,      dim.x, dim.z)]
            faces = [(3, 7, 5), (3, 5, 1),
                     (7, 3, 2), (7, 2, 6),
                     (7, 6, 4), (7, 4, 5),
                     (2, 0, 4), (2, 4, 6),
                     (1, 0, 2), (1, 2, 3)]
            mesh = nvb_utils.build_mesh(vertices, faces, 'sam')
            return mesh

        objects_to_check = [mdl_base]
        nvb_utils.get_children_recursive(mdl_base, objects_to_check)
        # Create (walk)meshes
        if dwk_mode == 'gen_swing1':
            dimensions = mathutils.Vector((0.1, 2.0, 3.0))
            mesh_data = [['DWK_wg_closed', (0.0, 0.0, 0.0),
                          dimensions],
                         ['DWK_wg_open1', (0.0, 0.0, -1.3962633609771729),
                          dimensions],
                         ['DWK_wg_open2', (0.0, 0.0, 1.3962633609771729),
                          dimensions]]
        elif dwk_mode == 'gen_slide1':
            mesh_data = [['DWK_wg_closed', (0.0, 0.0, 0.0),
                          mathutils.Vector((0.1, 2.0, 3.0))],
                         ['DWK_wg_open1', (0.0, 0.0, 0.0),
                          mathutils.Vector((0.15, 0.05, 3.0))]]
        for suffix, rotation, dimensions in mesh_data:
            newname = name_prefix + suffix  # the correct name
            # Adjust existing objects
            existing = [o for o in objects_to_check if o.name.endswith(suffix)]
            for obj in existing:
                if obj.name != newname:
                    obj.name = newname
                obj.parent = dwk_base
            # Create missing objects
            if newname not in bpy.data.objects:
                mesh = get_default_mesh(newname, dimensions)
                dwk_obj = bpy.data.objects.new(newname, mesh)
                dwk_obj.location = (-1.0, 0.0, 0.0)
                dwk_obj.rotation_euler = mathutils.Euler(rotation)
                dwk_obj.parent = dwk_base
                for collection in dwk_base.users_collection:
                    collection.objects.link(dwk_obj)

    @staticmethod
    def create_empties(empty_data, prefix, parent, layer, obj_list=[]):
        """Create empty objects if not already existing."""
        for suffix, loc in empty_data:
            dummy_name = prefix + suffix
            existing = [o for o in obj_list if o.name.endswith(suffix)]
            if existing:  # Adjust name and parent for existing objects
                for obj in existing:
                    if obj.name != dummy_name:
                        # Avoid renaming to same name (results in .001 suffix)
                        obj.name = dummy_name
                    obj.parent = parent
            else:  # Create missing dummies
                obj = bpy.data.objects.new(dummy_name, None)
                obj.location = loc
                obj.parent = parent
                for collection in parent.users_collection:
                    collection.objects.link(obj)
        layer.update()

    @staticmethod
    def create_mdl_dummys(mdl_base, name_prefix, layer):
        """Create necessary empties/dummies for the mdl."""
        objects_to_check = [mdl_base]
        nvb_utils.get_children_recursive(mdl_base, objects_to_check)
        dummy_data = [['_hand', (0.0, 0.0, 1.0)],
                      ['_head', (0.0, 0.0, 2.5)],
                      ['_hhit', (0.0, 0.0, 3.0)],
                      ['_impc', (0.0, 0.0, 1.5)],
                      ['_grnd', (0.0, 0.0, 0.0)]]
        NVB_OT_util_nodes_dwk.create_empties(
            dummy_data, name_prefix, mdl_base, layer, objects_to_check)

    @staticmethod
    def create_dwk_dummys(mdl_base, dwk_base, name_prefix, layer, dwk_mode):
        """Create necessary empties/dummies for the dwk."""
        objects_to_check = [mdl_base]
        nvb_utils.get_children_recursive(mdl_base, objects_to_check)
        dummy_data = []
        if dwk_mode == 'gen_swing1':
            dummy_data = [['DWK_dp_open1_01', (+0.2, -2.0, 0.0)],
                          ['DWK_dp_open1_02', (-0.7, -2.2, 0.0)],  # optional
                          ['DWK_dp_open2_01', (+0.2, +2.0, 0.0)],
                          ['DWK_dp_open2_02', (-0.7, +2.2, 0.0)],  # optional
                          ['DWK_dp_closed_01', (0.3, -0.7, 0.0)],
                          ['DWK_dp_closed_02', (0.3, +0.7, 0.0)]]
        elif dwk_mode == 'gen_slide1':
            dummy_data = [['DWK_dp_open1_01', (0.2, -0.7, 0.0)],
                          ['DWK_dp_open2_01', (0.2, +0.7, 0.0)],
                          ['DWK_dp_closed_01', (0.3, -0.7, 0.0)],
                          ['DWK_dp_closed_02', (0.3, +0.7, 0.0)]]
        NVB_OT_util_nodes_dwk.create_empties(
            dummy_data, name_prefix, dwk_base, layer, objects_to_check)

    @staticmethod
    def create_sam_mesh(mdl_base):
        """Generate a SAM mesh for a generic door."""
        objects_to_check = [mdl_base]
        nvb_utils.get_children_recursive(mdl_base, objects_to_check)
        # Check fo existing sam object
        sam_list = [o for o in objects_to_check if o.name.startswith("sam")]
        if sam_list:
            return sam_list.pop(0)
        # Create Mesh
        vertices = [(-1.0, 0.0, 0.0),
                    (+1.0, 0.0, 0.0),
                    (-1.0, 0.0, 3.0),
                    (+1.0, 0.0, 3.0)]
        faces = [(0, 2, 3),
                 (3, 1, 0)]
        sam_mesh = nvb_utils.build_mesh(vertices, faces, 'sam')
        # Create object
        sam_obj = bpy.data.objects.new('sam', sam_mesh)
        sam_obj.location = (0.0, 0.0, 0.0)
        sam_obj.parent = mdl_base
        for collection in mdl_base.users_collection:
            collection.objects.link(sam_obj)
        sam_obj.nvb.shadow = False
        return sam_obj

    def setup_door(self, mdl_base, layer, dwk_mode):
        """Add necessary (walkmesh) objects to mdlRoot."""
        # Find or create dwk base (walkmesh base)
        dwk_base = nvb_utils.get_wkm_base(mdl_base, nvb_def.Walkmeshtype.DWK)
        dwk_base_name = mdl_base.name + '_dwk'
        if dwk_base:
            # Adjust existing
            if dwk_base.name != dwk_base_name:
                # Avoid renaming to same name (results in '.001' suffix)
                dwk_base.name = dwk_base_name
            dwk_base.parent = mdl_base
        else:
            # Make a new one
            dwk_base = bpy.data.objects.new(dwk_base_name, None)
            dwk_base.nvb.emptytype = nvb_def.Emptytype.DWK
            dwk_base.parent = mdl_base
            for collection in mdl_base.users_collection:
                collection.objects.link(dwk_base)
        # Create recessary dummy nodes (emtpies) for dwk
        # The prefix for dwk dummies are two abritratry alphanumeric characters followed by an underscore
        # We'll use the last two characters from the model name
        name_prefix = nvb_utils.strip_trailing_numbers(mdl_base.name)[-2:]+"_"
        NVB_OT_util_nodes_dwk.create_dwk_dummys(mdl_base, dwk_base, name_prefix, layer, dwk_mode)
        # Create recessary (walk)meshes for dwk
        NVB_OT_util_nodes_dwk.create_dwk_mesh(mdl_base, dwk_base, name_prefix, layer, dwk_mode)
        # Create recessary dummy nodes (emtpies) for mdl
        # The prefix for model dummies is the model name
        name_prefix = nvb_utils.strip_trailing_numbers(mdl_base.name)
        NVB_OT_util_nodes_dwk.create_mdl_dummys(mdl_base, name_prefix, layer)
        # Create SAM object for mdl
        NVB_OT_util_nodes_dwk.create_sam_mesh(mdl_base)

    @classmethod
    def poll(self, context):
        """Prevent execution if no object is selected."""
        return context.object is not None

    def execute(self, context):
        """Create Walkmesh root and objects."""
        mdl_base = nvb_utils.get_obj_mdl_base(context.object)
        addon = context.preferences.addons[__package__]
        layer = context.view_layer
        if not mdl_base:
            self.report({'ERROR'}, 'No Aurora Base')
            return {'CANCELLED'}
        dwk_mode = addon.preferences.util_nodes_dwk_mode
        self.setup_door(mdl_base, layer, dwk_mode)
        self.report({'INFO'}, 'Created objects')
        return {'FINISHED'}


class NVB_OT_util_nodes_tile(bpy.types.Operator):
    """Helper to add missing nodes and walkmeshes for tilesets"""

    bl_idname = 'nvb.util_nodes_tile'
    bl_label = "Setup Tile"
    bl_options = {'UNDO'}

    direct_target: bpy.props.StringProperty(
        name='Target',
        description="Override target",
        options={'HIDDEN'},
        default="")

    @staticmethod
    def create_wok_mesh(mdl_base, layer, existing_objects, name_prefix,
                        wok_mode=None):
        """Adds necessary (walkmesh) objects to mdlRoot."""
        def get_default_mesh(mesh_name, dim=mathutils.Vector((5.0, 5.0, 0.0))):
            vertices = [(+dim.x, +dim.y, dim.z),
                        (+dim.x, -dim.y, dim.z),
                        (-dim.x, +dim.y, dim.z),
                        (-dim.x, -dim.y, dim.z)]
            faces = [(0, 2, 3),
                     (3, 1, 0)]
            mesh = nvb_utils.build_mesh(vertices, faces, mesh_name)
            return mesh

        wok_name = name_prefix + '_wok'
        # Check for existing aabb nodes in the mdl
        existing_aabb = [o for o in existing_objects
                         if o.nvb.meshtype == nvb_def.Meshtype.AABB]
        if existing_aabb:
            wok_obj = existing_aabb.pop(0)
            wok_obj.name = wok_name
        else:    # Add a new plane for the wok
            mesh = get_default_mesh(wok_name)

            nvb_utils.create_wok_materials(mesh)
            wok_obj = bpy.data.objects.new(wok_name, mesh)
            wok_obj.nvb.meshtype = nvb_def.Meshtype.AABB
            wok_obj.location = (0.0, 0.0, 0.0)
            wok_obj.parent = mdl_base
            for collection in mdl_base.users_collection:
                collection.objects.link(wok_obj)

    @staticmethod
    def create_main_lights(mdl_base, layer, existing_objects, name_prefix,
                           cnt=2):
        """Add lights (source and main) to the tile mdl."""
        # Check main lights
        reg_name = re.compile(r'[\w\-\.]+(ml[0-9]+)', re.IGNORECASE)
        existing = [(o, reg_name.match(o.name).group(1))
                    for o in existing_objects
                    if o.type == 'LIGHT' and reg_name.match(o.name)]

        if existing:
            for obj, suffix in existing:
                obj.name = name_prefix + suffix
        else:
            loc_list = [(0.0, 0.0, 5.0),
                        (+2.23, -2.23, 2.0),
                        (+2.23, +2.23, 2.0),
                        (-2.23, +2.23, 2.0),
                        (-2.23, -2.23, 2.0)]
            max_cnt = max(0, min(len(loc_list), cnt))
            for i in range(1, max_cnt+1):
                obj_name = name_prefix + 'ml' + str(i)
                lamp_data = bpy.data.lights.new(obj_name, 'POINT')
                # Tile light should always be black
                lamp_data.color = (0.0, 0.0, 0.0)
                # nwn multiplier property
                lamp_data.energy = 1.0
                # nwn radius property
                lamp_data.use_custom_distance = True
                lamp_data.cutoff_distance = 14.0
                lamp_data.shadow_soft_size = 14.0  # legacy
                # Create new object with the lamp data
                obj = bpy.data.objects.new(obj_name, lamp_data)
                obj.hide_render = True  # Mainlights should not be rendered
                obj.parent = mdl_base
                obj.location = loc_list[i-1]
                for collection in mdl_base.users_collection:
                    collection.objects.link(obj)

    @staticmethod
    def create_source_lights(mdl_base, layer, existing_objects, name_prefix,
                             cnt=2):
        """Add lights (source and main) to the tile mdl."""
        # Check main lights
        reg_name = re.compile(r'[\w\-\.]+(sl[0-9]+)', re.IGNORECASE)
        existing = [(o, reg_name.match(o.name).group(1))
                    for o in existing_objects
                    if o.type == 'EMPTY' and reg_name.match(o.name)]

        if existing:
            for obj, suffix in existing:
                obj.name = name_prefix + suffix
        else:
            loc_list = [(+3.0, -3.0, 4.0),
                        (+3.0, +3.0, 4.0),
                        (-3.0, +3.0, 4.0),
                        (-3.0, -3.0, 4.0)]
            max_cnt = max(0, min(len(loc_list), cnt))
            for i in range(1, max_cnt+1):
                obj_name = name_prefix + 'sl' + str(i)
                obj = bpy.data.objects.new(obj_name, None)
                obj.parent = mdl_base
                obj.location = loc_list[i-1]
                for collection in mdl_base.users_collection:
                    collection.objects.link(obj)

    def setup_tile(self, mdl_base, layer):
        """Add necessary (walkmesh) objects to mdlRoot."""
        def get_prefix(mdl_base):
            mdl_name = mdl_base.name
            dpos = mdl_name[::-1].find('_')
            if dpos >= 0:
                return mdl_name[-1*dpos:]
            return mdl_name[-3:]

        name_prefix = get_prefix(mdl_base)
        existing_objects = [mdl_base]
        nvb_utils.get_children_recursive(mdl_base, existing_objects)
        NVB_OT_util_nodes_tile.create_wok_mesh(
            mdl_base, layer, existing_objects, name_prefix)
        NVB_OT_util_nodes_tile.create_main_lights(
            mdl_base, layer, existing_objects, mdl_base.name)
        NVB_OT_util_nodes_tile.create_source_lights(
            mdl_base, layer, existing_objects, mdl_base.name)

    @classmethod
    def poll(self, context):
        """Prevent execution if no object is selected."""
        return context.object is not None

    def execute(self, context):
        """Create Walkmesh root and objects."""

        # Need to do it that way for cross compatibility (2.8-3.3)
        if self.direct_target:
            target = bpy.data.objects[self.direct_target]
        else:
            target = context.object

        if not target:
            self.report({'ERROR'}, 'No target')
            return {'CANCELLED'}

        mdl_base = nvb_utils.get_obj_mdl_base(target)
        layer = context.view_layer
        if not mdl_base:
            self.report({'ERROR'}, 'No MDL root')
            return {'CANCELLED'}
        self.setup_tile(mdl_base, layer)
        self.report({'INFO'}, 'Created objects')
        return {'FINISHED'}


class NVB_OT_util_tileslicer(bpy.types.Operator):
    """Helper to slice objects into 10x10 tile"""

    bl_idname = 'nvb.util_tileslicer'
    bl_label = "Tileslicer"
    bl_options = {'UNDO'}

    target_mode: bpy.props.EnumProperty(
        name="Target Mode",
        description="Select the objects to slice",
        items=[('SCENE', "Scene",
                "All Objects in current scene", 0),
               ('COLLECTION', "Active Collection",
                "All Objects in active collection", 1),
               ('SELECTED', "Selected",
                "All selected objects", 2),
               ],
        default='SCENE')
    destructive: bpy.props.BoolProperty(
        name="Destructive", default=False,
        description="Modify target object directly instead of creating new ones")
    walkmesh_only: bpy.props.BoolProperty(
        name="Walkmesh Only", default=False,
        description="Operate on walkmeshes only")
    optimize_splits: bpy.props.BoolProperty(
        name="Optimize Splits", default=False,
        description="Try to add object to a tile if the overlap is small")
    adjust_origins: bpy.props.BoolProperty(
        name="Adjust Origins", default=True,
        description="Moves object x-y location to mdl base")
    add_tile_features: bpy.props.BoolProperty(
        name="Add Tile Features", default=False,
        description="Add walkmesh and tile lights if missing")

    group_origin: bpy.props.FloatVectorProperty(name="Origin",
                                                description="Origin to start slicing at",
                                                size=3,
                                                subtype='TRANSLATION',
                                                default=(0.0, 0.0, 0.0),
                                                step=100)
    tile_count: bpy.props.IntVectorProperty(name="Tiles",
                                             description="Number of Tiles in X and Y direction",
                                             default = (2,2), min=1, soft_max=16, step=1,
                                             size=2, options=set())
    tile_prefix: bpy.props.StringProperty(name="Prefix",
                                          description="Prefix for the generated tiles.",
                                          default="test",
                                          options=set())

    ignore_objects = []  # don't proccess these objects

    def create_mdl_base(self, context, location, tile_idx):
        """Create the mdl base for a tile."""
        # Generate the name
        next_idx = max(1, tile_idx)
        tile_name = self.tile_prefix+"{0:02d}".format(next_idx)
        while tile_name in bpy.data.objects:
            next_idx = next_idx + 1
            tile_name = self.tile_prefix+"{0:02d}".format(next_idx)

        new_empty = bpy.data.objects.new(tile_name, None)
        new_empty.location = location
        context.collection.objects.link(new_empty)
        return new_empty

    def find_targets(self, context, aabb_min, aabb_max, tile_count):
        """Returns a list of target objects to operate on, parents before children."""
        def get_tile_affinity(obj, aabb_min, aabb_max, depsgraph, optimize_ratio = 0.0):
            """Determines how tje object belongt to tile, 0 = outside, 1 partial, 2 = inside."""
            if obj.type == 'MESH':
                 # For meshes we need to check vertices
                mesh = obj.evaluated_get(depsgraph).to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
                obj_mw = obj.matrix_world
                verts_to_test = [obj_mw @ v.co for v in mesh.vertices]
                # Only check the lower parts of a mesh
                if optimize_ratio > 0.0:
                    vert_max_z = min(v.z for v in verts_to_test) + 2.0
                    verts_to_test = [v for v in verts_to_test if v.z <= vert_max_z]
                    # Check how many verts are inside and outside
                    vert_count_within = sum(1 for v in verts_to_test if (aabb_min.x <= v.x <= aabb_max.x and aabb_min.y <= v.y <= aabb_max.y) )
                    vert_ratio_within = vert_count_within/len(verts_to_test)
                    if (vert_ratio_within >= optimize_ratio):
                        # Take the whole object
                        return 2
                    else:
                        # Always partially in
                        return 1
                else:
                    return 1
            else:
                # For all the rest we only check coordinates (can't slice them anyways)
                loc_global = obj.matrix_world.to_translation()
                if (aabb_min.x <= loc_global.x <= aabb_max.x and aabb_min.y <= loc_global.y <= aabb_max.y):
                    return 1
                else:
                    return 0

        def add_children(obj, obj_list):
            if obj not in self.ignore_objects:
                obj_list.append(obj)
            for child in obj.children:
                add_children(child, obj_list)

        # Valid object depend on target mode
        if self.target_mode == 'COLLECTION':
            potential_targets = nvb_utils.get_active_collection(context)
        elif self.target_mode == 'SELECTED':
            potential_targets = context.selected_objects
        else:  # Current Scene
            potential_targets = context.scene.collection.all_objects

        if self.walkmesh_only:
            # In this case we don't care about parenting
            potential_targets = [obj for obj in potential_targets if obj.nvb.meshtype == nvb_def.Meshtype.AABB]
        else:
            # Ensure parents come before children
            tmp_list = []
            for obj in potential_targets:
                if not obj.parent:
                    add_children(obj, tmp_list)
            potential_targets = tmp_list
            del tmp_list

        # Check wether we need to split at all
        depsgraph = context.evaluated_depsgraph_get()
        # Only keep object that are at least partially within the tile
        if self.optimize_splits:
            optimize_ratio = 0.1
        else:
            optimize_ratio = 0.0

        tile_affinities = [get_tile_affinity(obj, aabb_min, aabb_max, depsgraph, optimize_ratio) for obj in potential_targets]
        return [[obj, aff] for obj, aff in zip(potential_targets, tile_affinities) if aff > 0]

    def box_bisect(self, context, obj, aabb_min, aabb_max):
        # We can only slice meshes
        if (obj.type != "MESH"):
            new_obj = obj.copy()
            context.collection.objects.link(new_obj)
            return new_obj

        # Get a mesh with all applied modifiers
        depsgraph = context.evaluated_depsgraph_get()
        old_mesh = obj.evaluated_get(depsgraph).to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)

        # Use bmesh for bisecting
        bm = bmesh.new()
        bm.from_mesh(old_mesh)
        bm.verts.ensure_lookup_table()

        # Need this to transform to onject local space
        obj_mwi = obj.matrix_world.inverted()
        obj_mwi_rot = obj_mwi.to_quaternion().to_matrix().to_4x4()  # slice plane normals only

        # Normals and coordinates for slicing planes
        slice_planes = [[aabb_max, mathutils.Vector(( 0,  1, 0))],
                        [aabb_max, mathutils.Vector(( 1,  0, 0))],
                        [aabb_min, mathutils.Vector(( 0, -1, 0))],
                        [aabb_min, mathutils.Vector((-1,  0, 0))] ]

        # Transform planes to object local coordinates
        slice_planes = [[obj_mwi @ co, obj_mwi_rot @ no] for co, no in slice_planes]

        # Perform the slice
        for coord, norm in slice_planes:
            _ = bmesh.ops.bisect_plane(bm,
                                       geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                       plane_co=coord,
                                       plane_no=norm,
                                       clear_outer=True, dist=0.01)

        # Check if any geometry remains
        if bm.verts and bm.faces:
            # Use the bmesh to create a new mesh
            new_mesh = bpy.data.meshes.new(name=obj.name)
            bm.to_mesh(new_mesh)
            bm.free()
            new_mesh.update()

            # Create the newly sliced object at old location
            new_obj = bpy.data.objects.new(obj.name, new_mesh)
            new_obj.matrix_world = obj.matrix_world
            for mat_slot in obj.material_slots:
                if mat_slot.material:
                    new_obj.data.materials.append(mat_slot.material)
                else:
                    new_obj.data.materials.append(None)

            new_obj.nvb.meshtype = obj.nvb.meshtype

            return new_obj

        # Empty slice, nothing remains of the old mesh
        return None

    @classmethod
    def poll(self, context):
        """Can always be executed."""
        return True

    def execute(self, context):
        self.ignore_objects = []
        origin = mathutils.Vector(self.group_origin)
        tile_count = self.tile_count[0] * self.tile_count[1]

        # Get List of valid targets for each tile
        tile_idx = 0
        valid_targets = [[] for _ in range(tile_count)]
        for y in range(0, self.tile_count[1]):
            for x in range(0, self.tile_count[0]):
                aabb_min = origin + mathutils.Vector((x*10, y*10, 0))
                aabb_max = origin + mathutils.Vector(((x+1)*10, (y+1)*10, 0))
                valid_targets[tile_idx] = self.find_targets(context, aabb_min, aabb_max, tile_count)
                # object fully belonging to a tile should not be processed again
                self.ignore_objects.extend(obj for obj, aff in valid_targets[tile_idx] if aff == 2)
                tile_idx += 1

        # Loop over all tiles and bisect all of its valid targets
        tile_idx = 0
        mdl_base_list = []
        for y in range(0, self.tile_count[1]):
            for x in range(0, self.tile_count[0]):
                # Define box bounds to slice to
                # We'll need a new mdl base, but don't create it yet, there may be nothing to add to it
                mdl_base = None
                copied_targets = dict()  # necessary for re-parenting
                for obj, tile_affinity in valid_targets[tile_idx]:
                    # Only split the object, if necessary
                    if (obj.type == "MESH"):
                        if tile_affinity == 2:
                            # Bisect with  group bounds (all tiles)
                            tile_part = self.box_bisect(context, obj, origin, mathutils.Vector((self.tile_count[0]*10, self.tile_count[1]*10, 0)))
                        else:
                            # Bisect with tile bounds
                            aabb_min = origin + mathutils.Vector((x*10, y*10, 0))
                            aabb_max = origin + mathutils.Vector(((x+1)*10, (y+1)*10, 0))
                            tile_part = self.box_bisect(context, obj, aabb_min, aabb_max)
                    else:
                         tile_part = obj.copy()

                    if tile_part:
                        context.collection.objects.link(tile_part)
                        context.view_layer.update()
                        # Save for re-parenting
                        copied_targets[obj.name] = tile_part

                        # Create mdl base on demand
                        if not mdl_base:
                            mdl_base = self.create_mdl_base(context, origin + mathutils.Vector((5+x*10, 5+y*10, 0)), tile_idx)
                            context.view_layer.update()
                            if mdl_base:
                                mdl_base_list.append(mdl_base)
                                mdl_base.nvb.classification = nvb_def.Classification.TILE
                            tile_idx += 1

                        if self.adjust_origins:
                            # Adjust location to be within the tile bounds
                            new_origin = mdl_base.location
                            local_origin = tile_part.matrix_world.inverted() @ new_origin
                            if tile_part.data:
                                if tile_part.type == "MESH":
                                    tile_part.data.transform(mathutils.Matrix.Translation(-local_origin))
                                tile_part.matrix_world.translation += (new_origin - tile_part.matrix_world.translation)
                            context.view_layer.update()

                        # Restore parent-child relation if the parent was also copied
                        if obj.parent and obj.parent.name in copied_targets:
                            tile_part.parent = copied_targets[obj.parent.name]
                            tile_part.matrix_parent_inverse = tile_part.parent.matrix_world.inverted()
                        else:
                            tile_part.parent = mdl_base
                            tile_part.matrix_parent_inverse = tile_part.parent.matrix_world.inverted()
                        context.view_layer.update()

        if self.add_tile_features:
            for mb in mdl_base_list:
                if mb:
                    bpy.ops.nvb.util_nodes_tile(direct_target=mb.name)

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        res = wm.invoke_props_dialog(self)
        return res
