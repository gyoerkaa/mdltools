"""TODO: DOC."""

import os
from datetime import datetime

import bpy

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

    def readAsciiHeader(self, asciiBlock):
        """TODO: DOC."""
        asciiLines = [l.strip().split() for l in asciiBlock.splitlines()]
        for line in asciiLines:
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

    def readAsciiWalkmesh(self, asciiBlock, wkmtype, options):
        """TODO: DOC."""
        if options.import_walkmesh:
            geomStart = asciiBlock.find('node ')  # Look for the first 'node'
            if (geomStart < 0):  # Most likely empty walkmesh file
                print("Neverblender: WARNING: Unable to read walkmesh data")
                return
            if wkmtype == 'pwk':
                Mdl.readAsciiGeometry(asciiBlock[geomStart:], self.pwknodes)
            elif wkmtype == 'dwk':
                Mdl.readAsciiGeometry(asciiBlock[geomStart:], self.dwknodes)

    @staticmethod
    def readAsciiGeometry(asciiBlock, nodelist):
        """TODO: DOC."""
        dlm = 'node '
        asciiNodeList = [dlm+block for block in asciiBlock.split(dlm) if block]
        for idx, asciiNode in enumerate(asciiNodeList):
            asciiLines = [l.strip().split() for l in asciiNode.splitlines()]
            node = None
            nodeType = ''
            nodeName = 'UNNAMED'
            try:  # Read node type
                nodeType = asciiLines[0][1].lower()
            except (IndexError, AttributeError):
                raise nvb_def.MalformedMdlFile('Unable to read node type')
            try:  # Read node name
                nodeName = asciiLines[0][2].lower()
            except (IndexError, AttributeError):
                raise nvb_def.MalformedMdlFile('Unable to read node name')
            try:  # Create (node) object
                node = Mdl.nodelookup[nodeType](nodeName)
            except KeyError:
                raise nvb_def.MalformedMdlFile('Invalid node type')
            # Parse and add to node list
            node.loadAscii(asciiLines, idx)
            nodelist.append(node)

    @staticmethod
    def readAsciiAnimation(asciiBlock):
        """Load a single animation from an ascii animation block."""
        anim = nvb_anim.Animation()
        anim.loadAscii(asciiBlock)
        return anim

    def readAsciiAnimations(self, asciiBlock):
        """Load all animations from an ascii mdl block."""
        dlm = 'newanim '  # Split animations using 'newanim' as delimiter
        animList = [dlm+block for block in asciiBlock.split(dlm) if block]
        self.animations = list(map(Mdl.readAsciiAnimation, animList))

    def readAscii(self, asciiBlock, options):
        """Load an mdl from an ascii mfl file."""
        geomStart = asciiBlock.find('node ')  # Look for the first 'node'
        animStart = asciiBlock.find('newanim ')  # Look for the first 'newanim'

        if (animStart > 0) and (geomStart > animStart):
            raise nvb_def.MalformedMdlFile('Animations before geometry')
        if (geomStart < 0):
            raise nvb_def.MalformedMdlFile('Unable to find geometry')

        self.readAsciiHeader(asciiBlock[:geomStart-1])
        # Import Geometry
        if (animStart > 0):
            # Animations present, exclude them for geometry loading
            Mdl.readAsciiGeometry(asciiBlock[geomStart:animStart],
                                  self.mdlnodes)
        else:
            Mdl.readAsciiGeometry(asciiBlock[geomStart:], self.mdlnodes)
        # Import Animations
        if options.anim_import and (animStart > 0):
            self.readAsciiAnimations(asciiBlock[animStart:])

    @staticmethod
    def generateAsciiHeader(mdl_base, ascii_lines, options):
        """TODO: DOC."""
        mdlname = mdl_base.name
        mdlclass = mdl_base.nvb.classification.upper()
        mdlsuper = mdl_base.nvb.supermodel
        mdlanimscale = mdl_base.nvb.animscale

        ascii_lines.append('newmodel ' + mdlname)
        ascii_lines.append('setsupermodel ' + mdlname + ' ' + mdlsuper)
        ascii_lines.append('classification ' + mdlclass)
        ascii_lines.append('setanimationscale ' + str(round(mdlanimscale, 2)))

    @staticmethod
    def generateAsciiGeometry(obj, ascii_lines, options):
        """TODO: DOC."""
        if nvb_utils.is_wkm_root(obj):
            return
        node_type = nvb_utils.getNodeType(obj)
        try:
            node = Mdl.nodelookup[node_type]
        except KeyError:
            raise nvb_def.MalformedMdlFile('Invalid node type')

        node.generateAscii(obj, ascii_lines, options, False)
        # Sort children to restore original order before import
        # (important for supermodels/animations to work)
        children = [c for c in obj.children]
        children.sort(key=lambda c: c.name)
        children.sort(key=lambda c: c.nvb.imporder)
        for c in children:
            Mdl.generateAsciiGeometry(c, ascii_lines, options)

    @staticmethod
    def generateAsciiAnimations(mdl_base, ascii_lines, options):
        """TODO: DOC."""
        if mdl_base.nvb.animList:
            ascii_lines.append('')
            ascii_lines.append('# ANIM ASCII')
            for anim in mdl_base.nvb.animList:
                nvb_anim.Animation.generateAscii(mdl_base, anim,
                                                 ascii_lines, options)

    @staticmethod
    def generateAsciiMeta(mdl_base, ascii_lines, options):
        """Add creation time to a list of ascii lines."""
        ct = datetime.now()
        ascii_lines.append(ct.strftime('# Exported from blender %A, %Y-%m-%d'))
        blend = os.path.basename(bpy.data.filepath)
        if not blend:
            blend = 'unknown'
        ascii_lines.append('filedependancy ' + blend)

    @staticmethod
    def generateAscii(mdl_base, ascii_lines, options):
        """TODO: DOC."""
        # The Names of exported geometry nodes. We'll need this for skinmeshes
        # and animations
        mdlname = mdl_base.name
        # Creation time, etc
        Mdl.generateAsciiMeta(mdl_base, ascii_lines, options)
        # Header
        Mdl.generateAsciiHeader(mdl_base, ascii_lines, options)
        # Geometry
        ascii_lines.append('beginmodelgeom ' + mdlname)
        Mdl.generateAsciiGeometry(mdl_base, ascii_lines, options)
        ascii_lines.append('endmodelgeom ' + mdlname)
        # Animations
        if options.export_animations:
            Mdl.generateAsciiAnimations(mdl_base, ascii_lines, options)
        # The End
        ascii_lines.append('donemodel ' + mdlname)
        ascii_lines.append('')

    @staticmethod
    def generateAsciiWalkmesh(mdl_base, ascii_lines, wkmtype, options):
        """TODO: DOC."""
        wkmObjects = []
        if wkmtype == nvb_def.Walkmeshtype.WOK:
            # Walkmesh for tiles: Append only AABB mesh
            wok = nvb_utils.get_aabb(mdl_base)
            if wok:
                wkmObjects.append(wok)
        else:
            # Walkmesh for doors: Append all children of the walkmesh root
            wkmRoot = nvb_utils.find_wkm_root(mdl_base, wkmtype)
            if wkmRoot:
                wkmObjects = [c for c in wkmRoot.children]
        if not wkmObjects:  # Abort if there is nothing to write
            return
        Mdl.generateAsciiMeta(mdl_base, ascii_lines, options)
        # Write Data
        for obj in wkmObjects:
            nodeType = nvb_utils.getNodeType(obj)
            try:
                node = Mdl.nodelookup[nodeType]
            except KeyError:
                print("Neverblender: WARNING - Unable to get node type.")
            else:
                node.generateAscii(obj, ascii_lines, options, True)

    def link_objects(self, nodelist, noderesolver, options):
        """Handles parenting and linking of objects to a scene."""
        obj = None
        for node in nodelist:
            obj = noderesolver.get_obj(node.name, node.nodeidx)
            if obj:
                if node.parent:
                    parentobj = noderesolver.get_obj_parent(node.parent,
                                                            node.nodeidx)
                    obj.parent = parentobj
                else:  # potential mdl root
                    obj.parent = None
                    obj.nvb.supermodel = self.supermodel
                    obj.nvb.classification = self.classification
                    obj.nvb.animscale = self.animscale
                options.scene.objects.link(obj)
            else:
                print('Neverblender: WARNING - Invalid object ' + node.name)
        # Return the root
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
            """Generate a root node as parent for all walkmesh objects."""
            # Get root node
            if wkmtype not in nvb_def.Walkmeshtype.IMPORT:
                print('Neverblender: WARNING - Invalid walkmesh type: '
                      + wkmtype)
                return
            # Generate name
            parentNames = set([n.parent for n in wkmnodes])
            rootName = ''
            if len(parentNames) >= 1:
                # All nodes in the walkmesh SHOULD have the same parent
                rootName = next(iter(parentNames))
                if len(parentNames) > 1:
                    # Multiple parents (Walkmesh is technically invalid)
                    # Try to solve the issue by re-parenting
                    for node in wkmnodes:
                        node.parent = rootName
            else:
                # This shouldn't happen really
                rootName = options.mdlname + '_' + wkmtype
                for node in wkmnodes:
                    node.parent = rootName
            wkmroot = nvb_node.Dummy(rootName)
            if wkmtype == nvb_def.Walkmeshtype.DWK:
                wkmroot.emptytype = nvb_def.Emptytype.DWK
            else:
                wkmroot.emptytype = nvb_def.Emptytype.PWK
            wkmnodes.insert(0, wkmroot)

        # Create mdl objects
        mdlresolver = nvb_utils.NodeResolver()
        Mdl.create_objects(self.mdlnodes, mdlresolver, options)
        mdl_base = self.link_objects(self.mdlnodes, mdlresolver, options)
        # Create pwk objects
        if self.pwknodes:
            wkmresolver = nvb_utils.NodeResolver()
            create_wkm_base(self.mdlnodes, self.pwknodes,
                            nvb_def.Walkmeshtype.PWK, options)
            Mdl.create_objects(self.pwknodes, wkmresolver, options)
            wkm_base = self.link_objects(self.pwknodes, wkmresolver, options)
            wkm_base.parent = mdl_base
            del wkmresolver
        # Create dwk objects
        if self.dwknodes:
            wkmresolver = nvb_utils.NodeResolver()
            create_wkm_base(self.mdlnodes, self.dwknodes,
                            nvb_def.Walkmeshtype.DWK, options)
            Mdl.create_objects(self.dwknodes, wkmresolver, options)
            wkm_base = self.link_objects(self.dwknodes, wkmresolver, options)
            wkm_base.parent = mdl_base
            del wkmresolver
        # Create animations
        if options.anim_import:
            if options.anim_fps_use:
                options.scene.render.fps = options.anim_fps
            self.create_animations(self.animations,
                                   mdl_base, mdlresolver, options)
        # Set mdl root position
        mdl_base.location = options.mdl_location

    def create_supermodel(self, mdl_base, options):
        """Import animation onto existing (imported) MDL."""
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
