


class Dummy():
    def __init__(self, name):
        self.wirecolor   = (0.0, 0.0, 0.0)
        self.position    = (0.0, 0.0, 0.0)
        self.orientation = (0.0, 0.0, 0.0)
        self.scale       = (0.0, 0.0, 0.0)
        
        self.name   = name
        self.parent = None
        
     def set_scale(self, scale = (0.0, 0.0, 0.0)):
        self.scale = pos
        
    def set_position(self, pos = (0.0, 0.0, 0.0)):
        self.position = pos
        
    def set_orientation(self, ori = (0.0, 0.0, 0.0)):
        self.orientation = ori
        
    def set_wirecolor(self, color = (0.0, 0.0, 0.0)):
        self.wirecolor = color
       
    def from_object(self, object):
        pass
        
    def to_ascii():
        lines = []
        return lines
        
        
class Trimesh(Dummy):
    def __init__(self):
        pass
 
 
class Danglymesh(Trimesh):
    def __init__(self):
        pass

        
class Skinmesh(Trimesh):
    def __init__(self):
        pass