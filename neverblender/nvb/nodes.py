

class Dummy():
    def __init__(self, name):
        self.name   = name
        self.parent = 'null'
         
        self.position    = (0.0, 0.0, 0.0)
        self.orientation = (0.0, 0.0, 0.0, 0.0)
        self.scale       = 1.0
        
        self.wirecolor   = (0.0, 0.0, 0.0)
        
    def from_object(self, object):
        pass
        
    def to_ascii():
        lines = []
        return lines


class Trimesh(Dummy):
    def __init__(self, name):
        Dummy.__init__(self, name)
        
        self.center   = (0.0, 0.0, 0.0)
        
        self.tilefade = True
        self.render   = True
        self.shadow   = True
        self.beaming  = True
        
        self.inheritcolor     = 0       
        self.alpha            = 1.0
        self.transparencyhint = 0
    
        self.selfillumcolor = (0.0, 0.0, 0.0)
        self.ambient        = (0.0, 0.0, 0.0)
        self.diffuse        = (0.0, 0.0, 0.0)
        self.specular       = (0.0, 0.0, 0.0)
        self.shininess      = 0       
        self.bitmap         = 'null'
        self.rotatetexture  = 0
        
        self.verts           = []
        self.faces           = []
        self.tverts          = []


class Danglymesh(Trimesh):
    def __init__(self, name):
        Trimesh.__init__(self, name)
        
        self.period       = 1.0
        self.tightness    = 1.0
        self.displacement = 1.0


class Skinmesh(Trimesh):
    def __init__(self, name):
        Trimesh.__init__(self, name)
        
        self.weights = []


class Emitter(Dummy):
    def __init__(self, name):
        Dummy.__init__(self, name)


class Light(Dummy):
    def __init__(self, name):
        Dummy.__init__(self, name)
        
        self.radius           = 5.0
        self.multiplier       = 1
        self.color            = (0.0, 0.0, 0.0)
        self.ambientonly      = 1
        self.ndynamictype     = 0
        self.isdynamic        = 0
        self.affectdynamic    = 0
        self.lightpriority    = 5
        self.fadinglight      = 1
        self.flareradius      = 1

