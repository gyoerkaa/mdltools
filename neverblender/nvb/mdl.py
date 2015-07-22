import os
import math
import collections

import bpy

import neverblender.nvb.walkmesh
import neverblender.nvb.node

class Mdl():
    __debug = True

    def __init__(self):
        self.nodelist = collections.OrderedDict()
        self.animlist = dict() # No need to retain order
        
        self.name           = 'UNNAMED'
        self.supermodel     = 'NULL'
        self.animScale      = 1.0
        self.classification = 'UNKNOWN'
        
    def addNode(self, node):
        pass
                  
    def addAnim(self, anim):
        pass