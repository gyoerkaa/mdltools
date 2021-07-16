"""TODO: DOC."""

import os
import tempfile
import subprocess
import shutil
from datetime import datetime

import bpy
import addon_utils

from . import nvb_node
from . import nvb_anim
from . import nvb_def
from . import nvb_utils


class Mdl():
    """TODO: DOC."""

    # Helper to create nodes of matching type
    nodelookup = {nvb_def.Nodetype.DUMMY:      nvb_node.Dummy,
                  nvb_def.Nodetype.PATCH:      nvb_node.Patch,
                  nvb_def.Nodetype.REFERENCE:  nvb_node.Reference,
                  nvb_def.Nodetype.TRIMESH:    nvb_node.Trimesh,
                  nvb_def.Nodetype.ANIMMESH:   nvb_node.Animmesh,
                  nvb_def.Nodetype.DANGLYMESH: nvb_node.Danglymesh,
                  nvb_def.Nodetype.SKIN:       nvb_node.Skinmesh,
                  nvb_def.Nodetype.EMITTER:    nvb_node.Emitter,
                  nvb_def.Nodetype.LIGHT:      nvb_node.Light,
                  nvb_def.Nodetype.AABB:       nvb_node.Aabb}

    def __init__(self):
        """TODO: DOC."""
        # Header Data
        self.name = 'UNNAMED'
        self.supermodel = nvb_def.null
        self.animscale = 1.0
        self.classification = nvb_def.Classification.UNKNOWN
        # Geometry
        self.mdlnodes = []
        self.pwknodes = []
        self.dwknodes = []
        # Animations
        self.animations = []

    def read_ascii_header(self, ascii_block):
        """TODO: DOC."""
        ascii_lines = [l.strip().split() for l in ascii_block.splitlines()]
        for line in ascii_lines:
            try:
                label = line[0].lower()
            except (IndexError, AttributeError):
                continue  # Probably empty line, skip it
            if label == 'newmodel':
                try:
                    self.name = line[1]
                except (ValueError, IndexError):
                    print("Neverblender: WARNING - Unable to read model name.")
            elif label == 'setsupermodel':
                try:  # should be ['setsupermodel', modelname, supermodelname]
                    self.supermodel = line[2].lower()
                except (ValueError, IndexError):
                    print("Neverblender: WARNING - Unable to read supermodel. \
                           Using default value " + self.supermodel)
            elif label == 'classification':
                try:
                    self.classification = line[1].lower()
                except (ValueError, IndexError):
                    print("Neverblender: WARNING - Unable to read \
                           classification. \
                           Using Default value " + self.classification)
                if self.classification not in nvb_def.Classification.ALL:
                    print("Neverblender: WARNING - Invalid classification \
                           '" + self.classification + "'")
                    self.classification = nvb_def.Classification.UNKNOWN
            elif label == 'setanimationscale':
                try:
                    self.animscale = float(line[1])
                except (ValueError, IndexError):
                    print("Neverblender: WARNING - Unable to read \
                           animationscale. \
                           Using default value " + self.animscale)

    def read_ascii_wkm(self, ascii_block, wkmtype, options):
        """TODO: DOC."""
        if options.geom_walkmesh:
            geom_start = ascii_block.find('node ')
            if (geom_start < 0):  # Most likely empty walkmesh file
                print("Neverblender: WARNING: Unable to read walkmesh data")
                return
            if wkmtype == 'pwk':
                Mdl.read_ascii_geom(ascii_block[geom_start:], self.pwknodes)
            elif wkmtype == 'dwk':
                Mdl.read_ascii_geom(ascii_block[geom_start:], self.dwknodes)

    @staticmethod
    def read_ascii_geom(ascii_block, nodelist):
        """Read the geometry block of ascii mdl."""
        dlm = 'node '
        ascii_node_list = [dlm + b for b in ascii_block.split(dlm) if b]
        for idx, ascii_node in enumerate(ascii_node_list):
            ascii_lines = [l.strip().split() for l in ascii_node.splitlines()]
            node = None
            node_type = ''
            node_name = 'UNNAMED'
            try:  # Read node type
                node_type = ascii_lines[0][1].lower()
            except (IndexError, AttributeError):
                raise nvb_def.MalformedMdlFile('Unable to read node type')
            try:  # Read node name
                node_name = ascii_lines[0][2].lower()
            except (IndexError, AttributeError):
                raise nvb_def.MalformedMdlFile('Unable to read node name')
            try:  # Create (node) object
                node = Mdl.nodelookup[node_type](node_name)
            except KeyError:
                raise nvb_def.MalformedMdlFile('Invalid node type')
            # Parse and add to node list
            node.loadAscii(ascii_lines, idx)
            nodelist.append(node)

    def read_ascii_anims(self, ascii_block):
        """Load all animations from an ascii mdl block."""
        def read_anim(ascii_anim):
            """Load a single animation from an ascii animation block."""
            anim = nvb_anim.Animation()
            anim.loadAscii(ascii_anim)
            return anim
        dlm = 'newanim '  # Split animations using 'newanim' as delimiter
        animList = [dlm + b for b in ascii_block.split(dlm) if b]
        self.animations = list(map(read_anim, animList))

    def read_ascii_mdl(self, ascii_block, options):
        """Parse an ascii mdl file."""
        geom_start = ascii_block.find('node ')
        anim_start = ascii_block.find('newanim ')

        if (anim_start > 0) and (geom_start > anim_start):
            raise nvb_def.MalformedMdlFile('Animations before geometry')
        if (geom_start < 0):
            raise nvb_def.MalformedMdlFile('Unable to find geometry')

        self.read_ascii_header(ascii_block[:geom_start-1])
        # Import Geometry
        if (anim_start > 0):
            # Animations present, exclude them for geometry loading
            Mdl.read_ascii_geom(ascii_block[geom_start:anim_start],
                                self.mdlnodes)
        else:
            Mdl.read_ascii_geom(ascii_block[geom_start:], self.mdlnodes)
        # Import Animations
        if options.anim_import and (anim_start > 0):
            self.read_ascii_anims(ascii_block[anim_start:])

    @staticmethod
    def is_binary(filepath):
        """Check wether an mdl file is compiled/binary format"""
        with open(os.fsencode(filepath), 'rb') as f:
            return bytes(f.read(4)) == b'\x00\x00\x00\x00'

    @staticmethod
    def build_external_decompile_cmd(mdl_path, compiler_path, compiler_command):
        """TODO: Doc"""
        # References to customize the compile command (Make sure these are lower case, just in case)
        ref_compiler = "%compiler%" # optional, will prepend compiler path if missing
        ref_in_path = "%in_path%"
        ref_in_dir = "%in_dir%"
        ref_in_file = "%in_filename%"
        ref_out_path = "%out_path%"
        ref_out_dir = "%out_dir%"
        ref_out_file = "%out_filename%"
        
        run_cmd = []
        if compiler_command:
            mdl_dir, mdl_filename = os.path.split(mdl_path)
            # Lower case all references
            ref_all = (ref_compiler, ref_in_path, ref_in_dir, ref_in_file, ref_out_path, ref_out_dir, ref_out_file)
            run_cmd[:] = [op.lower() if op.lower() in ref_all else op for op in compiler_command.split()]
            # Make sure command options are unique (NO, not out problem)
            #run_cmd[:] = list(dict.fromkeys(run_cmd))
            # Replace the compiler path reference, prepend, if not present
            if ref_compiler in run_cmd:
                run_cmd[:] = [compiler_path if ro == ref_compiler else ro for ro in run_cmd]
            else:
                run_cmd[:] = [compiler_path] + run_cmd
            # Replace compiler options. We do an in-place decompilation overwriting the old (temp) file
            # Therefore input=output
            run_cmd[:] = [mdl_path if ro in (ref_in_path, ref_out_path) else ro for ro in run_cmd]
            run_cmd[:] = [mdl_dir if ro in (ref_in_dir, ref_out_dir) else ro for ro in run_cmd]
            run_cmd[:] = [mdl_filename if ro in (ref_in_file, ref_out_file) else ro for ro in run_cmd]

        return run_cmd

    def parse_mdl(self, mdl_filepath, options):
        """Parse a single mdl file."""
        if Mdl.is_binary(mdl_filepath):
            # Binary modles have to be decompiled
            if not options.compiler_use:
                print("Neverblender: WARNING - Detected binary MDL with disabled external compiler.")
            elif not os.path.isfile(options.compiler_path):
                print("Neverblender: WARNING - Detected binary MDL with invalid path to external compiler.")
            else:
                # - Create named temporay file (named because we'll need full access for subprocesses)
                # - Windows issue: Can't use auto-delete. It will lock the file when copyfile() closes it, making it inaccessible
                # - Windows issue: Can't use Windows default tempfile directory as working dir, cleanmodels doesn't have permissions for wirting there 
                #                  (nwnmdlcomp works fine though?). Use compiler dir as working dir instead.
                working_dir = os.path.split(options.compiler_path)[0]
                tf = tempfile.NamedTemporaryFile(mode="r+", delete=False)  # dir=working_dir not necessary yet, only for subprocess
                try:
                    tmp_filepath = tf.name
                    # Try getting a decompile command based on user options, make it overwrite the input file
                    run_cmd = Mdl.build_external_decompile_cmd(tmp_filepath, options.compiler_path, options.compiler_command)
                    #print(run_cmd)
                    if run_cmd:
                        # copy the file we want to import to tempfile
                        shutil.copyfile(mdl_filepath, tmp_filepath)
                        # Let the compiler do its work
                        result = subprocess.run(run_cmd, stdout=subprocess.PIPE, cwd=working_dir)
                        if result.returncode == 0:
                            # If succesful pass the resulting file to the ascii parser
                            self.read_ascii_mdl(tf.read(), options)
                        else:
                            print("Neverblender: ERROR - Could not decompile file.")
                finally:
                    tf.close()
                    os.remove(tf.name)
                """
                # Does only work with nwnmdlcomp, not cleanmodels
                # We need to prevent auto-deletion and delete manually ourselves, 
                # (on Windows access to the tempfile will be blocked after running the decompiler)
                tf = tempfile.NamedTemporaryFile(mode="r+", delete=False)
                try:
                    run_cmd = Mdl.build_external_decompile_cmd(mdl_filepath, tf.name, options)
                    result = subprocess.run(run_cmd, stdout=subprocess.PIPE)
                    if result.returncode == 0:
                        self.read_ascii_mdl(tf.read(), options)
                    else:
                        print("Neverblender: ERROR - Could not decompile file.")
                finally:
                    tf.close()
                    os.remove(tf.name)
                """
                """
                # Does not work on Windows, auto deletion prevents access
                with tempfile.NamedTemporaryFile(mode="w+") as tf:
                    run_cmd = Mdl.build_external_decompile_cmd(mdl_filepath, tf.name, options)
                    result = subprocess.run(run_cmd, stdout=subprocess.PIPE)
                    if result.returncode == 0:
                        self.read_ascii_mdl(tf.read(), options)  
                """              
        else:
            # ASCII model, parse directly
            with open(os.fsencode(mdl_filepath), 'r') as f:
                self.read_ascii_mdl(f.read(), options)

    def parse_wkm(self, wkm_filepath, wkm_type, options):
        """Parse a single walkmesh file."""
        if Mdl.is_binary(wkm_filepath):
            # Binary modles have to be decompiled
            if not options.decompiler_use_external:
                print("Neverblender: WARNING - Detected binary MDL with no decompiler avaible.")
            else:
                # Write the output of the external decompiler to a temp file and feed it into the ascii parser
                # We need to prevent auto-deletion and delete manually ourselves, 
                # (on Windows access to the tempfile will be blocked after running the decompiler)
                tf = tempfile.NamedTemporaryFile(mode="r+", delete=False)
                try:
                    run_cmd = Mdl.build_external_decompile_cmd(mdl_filepath, tf.name, options)
                    result = subprocess.run(run_cmd, stdout=subprocess.PIPE)
                    if result.returncode == 0:
                        self.read_ascii_mdl(tf.read(), options)
                    else:
                        print("Neverblender: ERROR - Could not decompile file.")
                finally:
                    tf.close()
                    os.remove(tf.name)             
        else:
            # ASCII model, parse directly
            with open(os.fsencode(wkm_filepath), 'r') as f:
                self.read_ascii_wkm(f.read(), wkm_type, options)

    @staticmethod
    def generate_ascii_header(mdl_base, ascii_lines, options):
        """TODO: DOC."""
        mdlname = mdl_base.name
        mdlclass = mdl_base.nvb.classification.upper()
        mdlsuper = mdl_base.nvb.supermodel
        mdlanimscale = mdl_base.nvb.animscale

        ascii_lines.append('newmodel ' + mdlname)
        if mdlsuper:
            ascii_lines.append('setsupermodel ' + mdlname + ' ' + mdlsuper)
        else:
            ascii_lines.append('setsupermodel ' + mdlname + ' null')
        ascii_lines.append('classification ' + mdlclass)
        ascii_lines.append('setanimationscale ' + str(round(mdlanimscale, 2)))

    @staticmethod
    def generate_ascii_geometry(obj, ascii_lines, options):
        """TODO: DOC."""
        if nvb_utils.is_wkm_base(obj):
            return
        node_type = nvb_utils.getNodeType(obj)
        try:
            node = Mdl.nodelookup[node_type]
        except KeyError:
            print("Neverblender: WARNING - Unsupported node type.")

        node.generateAscii(obj, ascii_lines, options, False)
        # Sort children to restore original order before import
        # (important for supermodels/animations to work)
        children = [c for c in obj.children]
        children.sort(key=lambda c: c.name)
        children.sort(key=lambda c: c.nvb.imporder)
        for c in children:
            Mdl.generate_ascii_geometry(c, ascii_lines, options)

    @staticmethod
    def generate_ascii_animations(mdl_base, ascii_lines, options):
        """TODO: DOC."""
        if mdl_base.nvb.animList:
            ascii_lines.append('')
            ascii_lines.append('# ANIM ASCII')
            for anim in mdl_base.nvb.animList:
                nvb_anim.Animation.generateAscii(mdl_base, anim,
                                                 ascii_lines, options)

    @staticmethod
    def generate_ascii_meta(mdl_base, ascii_lines, options):
        """Add creation time and name of source file."""
        blend_file = "unknown"
        time_str = ""
        if options.export_metadata:
            # Add current date
            ct = datetime.now()
            time_str = ct.strftime(" - %A, %Y-%m-%d")
            # filedependancy (blend file name)
            blend_file = os.path.basename(bpy.data.filepath)
            if not blend_file:
                blend_file = "unknown"

        # Get Addon Version
        try:
            nvbVersion = [addon.bl_info.get('version', (-1,-1,-1)) for addon in addon_utils.modules() if addon.bl_info['name'] == 'Neverblender'][0]
            nvbVersion = '.'.join([str(s) for s in nvbVersion])
        except (KeyError, ValueError):
            nvbVersion = "-1"

        ascii_lines.append("# Exported from NeverBlender " + nvbVersion + time_str)
        ascii_lines.append("filedependancy " + blend_file)

    @staticmethod
    def generate_ascii(mdl_base, ascii_lines, options):
        """TODO: DOC."""
        mdl_name = mdl_base.name
        # Creation time, etc
        Mdl.generate_ascii_meta(mdl_base, ascii_lines, options)
        # Header
        Mdl.generate_ascii_header(mdl_base, ascii_lines, options)
        # Geometry
        ascii_lines.append('beginmodelgeom ' + mdl_name)
        Mdl.generate_ascii_geometry(mdl_base, ascii_lines, options)
        ascii_lines.append('endmodelgeom ' + mdl_name)
        # Animations
        if options.anim_export:
            Mdl.generate_ascii_animations(mdl_base, ascii_lines, options)
        # The End
        ascii_lines.append('donemodel ' + mdl_name)
        ascii_lines.append('')

    @staticmethod
    def generate_ascii_wkm(mdl_base, ascii_lines, wkmtype, options):
        """TODO: DOC."""
        mdl_name = mdl_base.name
        wkmObjects = []
        if wkmtype == nvb_def.Walkmeshtype.WOK:
            # Walkmesh for tiles: Append only AABB mesh
            wok = nvb_utils.get_aabb(mdl_base)
            if wok:
                wkmObjects.append(wok)
        else:
            # Walkmesh for doors: Append all children of the walkmesh root
            wkmRoot = nvb_utils.get_wkm_base(mdl_base, wkmtype)
            if wkmRoot:
                wkmObjects = [c for c in wkmRoot.children]
        # Abort if there is nothing to write
        if not wkmObjects:
            return
        # Extra data for wok files
        if wkmtype == nvb_def.Walkmeshtype.WOK:
            ascii_lines.append("beginwalkmeshgeom " + mdl_name)
        # Write objects
        for obj in wkmObjects:
            nodeType = nvb_utils.getNodeType(obj)
            try:
                node = Mdl.nodelookup[nodeType]
            except KeyError:
                print("Neverblender: WARNING - Unable to get node type.")
            else:
                node.generateAscii(obj, ascii_lines, options, True)
        # Extra data for wok files
        if wkmtype == nvb_def.Walkmeshtype.WOK:
            ascii_lines.append("endwalkmeshgeom " + mdl_name)

    def link_objects(self, nodelist, noderesolver, collection):
        """Handles parenting and linking of objects to a scene."""
        obj = None
        for node in nodelist:
            obj = noderesolver.get_obj(node.name, node.nodeidx)
            if obj:
                if node.parent:
                    parentobj = noderesolver.get_obj_parent(node.parent,
                                                            node.nodeidx)
                    obj.parent = parentobj
                else:  # potential mdl base
                    obj.parent = None
                    obj.nvb.supermodel = self.supermodel
                    obj.nvb.classification = self.classification
                    obj.nvb.animscale = self.animscale
                # options.scene.objects.link(obj)
                collection.objects.link(obj)
            else:
                print('Neverblender: WARNING - Invalid object ' + node.name)
        # Return the base
        while obj:
            if obj.parent is None:
                return obj
            obj = obj.parent
        return None

    @staticmethod
    def create_objects(nodelist, noderesolver, options):
        """TODO: DOC."""
        for node in nodelist:
            obj = node.createObject(options)
            if obj:  # Save the imported objects for animation import
                noderesolver.insert_obj(node.name, node.nodeidx, obj.name)
            else:
                print('Neverblender: WARNING - Invalid node: ' + node.name)

    @staticmethod
    def create_animations(animationlist, mdl_base, noderesolver, options):
        """TODO: DOC."""
        # Load the 'default' animation first, so it is at the front
        anims = [a for a in animationlist if a.name == 'default']
        for a in anims:
            a.create(mdl_base, noderesolver, options)
        # Load the rest of the anims
        anims = [a for a in animationlist if a.name != 'default']
        for a in anims:
            a.create(mdl_base, noderesolver, options)

    def create(self, options):
        """Create objects and animations for a parsed MDL."""
        def create_wkm_base(mdlnodes, wkmnodes, wkmtype, options):
            """Generate a base node as parent for all walkmesh objects."""
            if wkmtype not in nvb_def.Walkmeshtype.IMPORT:
                print('Neverblender: WARNING - Invalid walkmesh type: '
                      + wkmtype)
                return
            # Generate name
            parent_names = set([n.parent for n in wkmnodes])
            base_name = ''
            if len(parent_names) >= 1:
                # All nodes in the walkmesh SHOULD have the same parent
                base_name = next(iter(parent_names))
                if len(parent_names) > 1:
                    # Multiple parents (Walkmesh is technically invalid)
                    # Try to solve the issue by re-parenting
                    for node in wkmnodes:
                        node.parent = base_name
            else:
                # This shouldn't happen really
                base_name = options.mdlname + '_' + wkmtype
                for node in wkmnodes:
                    node.parent = base_name
            wkmroot = nvb_node.Dummy(base_name)
            if wkmtype == nvb_def.Walkmeshtype.DWK:
                wkmroot.emptytype = nvb_def.Emptytype.DWK
            else:
                wkmroot.emptytype = nvb_def.Emptytype.PWK
            wkmnodes.insert(0, wkmroot)

        def create_wkm_collection(mdl_collection, wkm_name, create_new=True):
            wkm_collection = None
            if not create_new:
                wkm_collection = mdl_collection
            elif wkm_name in mdl_collection.children:
                wkm_collection = mdl_collection.children[wkm_name]
            else:
                wkm_collection = bpy.data.collections.new(name=wkm_name)
                mdl_collection.children.link(wkm_collection)
            return wkm_collection

        # Create mdl objects
        mdl_base = None
        if self.mdlnodes:
            mdl_resolver = nvb_utils.NodeResolver()
            Mdl.create_objects(self.mdlnodes, mdl_resolver, options)
            mdl_base = self.link_objects(self.mdlnodes,
                                        mdl_resolver,
                                        options.collection)
            bpy.context.evaluated_depsgraph_get().update()
            bpy.context.view_layer.update()
            # Create animations
            if options.anim_import:
                if options.anim_fps_use:
                    options.scene.render.fps = options.anim_fps
                self.create_animations(self.animations,
                                    mdl_base, mdl_resolver, options)
            bpy.context.evaluated_depsgraph_get().update()
            bpy.context.view_layer.update()

        # Create pwk objects
        if self.pwknodes:
            wkm_resolver = nvb_utils.NodeResolver()
            wkm_collection = create_wkm_collection(options.collection,
                                                   mdl_base.name + "_pwk",
                                                   options.collections_use)
            create_wkm_base(self.mdlnodes, self.pwknodes,
                            nvb_def.Walkmeshtype.PWK, options)
            Mdl.create_objects(self.pwknodes, wkm_resolver, options)
            wkm_base = self.link_objects(self.pwknodes,
                                         wkm_resolver,
                                         wkm_collection)
            wkm_base.parent = mdl_base
            del wkm_resolver

        # Create dwk objects
        if self.dwknodes:
            wkm_resolver = nvb_utils.NodeResolver()
            wkm_collection = create_wkm_collection(options.collection,
                                                   mdl_base.name + "_dwk",
                                                   options.collections_use)
            create_wkm_base(self.mdlnodes, self.dwknodes,
                            nvb_def.Walkmeshtype.DWK, options)
            Mdl.create_objects(self.dwknodes, wkm_resolver, options)
            wkm_base = self.link_objects(self.dwknodes,
                                         wkm_resolver,
                                         wkm_collection)
            wkm_base.parent = mdl_base
            del wkm_resolver

        # Set mdl base position
        if mdl_base:
            mdl_base.location = options.mdl_location
            # Set mdl base as active
            bpy.context.view_layer.objects.active = mdl_base

    def create_super(self, mdl_base, options):
        """Import animation onto existing MDL."""
        def setup_resolver(resolver, obj):
            node_name = nvb_utils.strip_trailing_numbers(obj.name)
            resolver.insert_obj(node_name, obj.nvb.imporder, obj.name)
            for c in obj.children:
                setup_resolver(resolver, c)

        # (Re)build name resolver for the mdl_base
        node_resolver = nvb_utils.NodeResolver()
        setup_resolver(node_resolver, mdl_base)
        # Create animations
        if options.anim_fps_use:
            options.scene.render.fps = options.anim_fps
        self.create_animations(self.animations, mdl_base, node_resolver,
                               options)
