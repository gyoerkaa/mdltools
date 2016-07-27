
def mdl(mdlFile, mdl, nodeList, animList):
    '''
    Splits the mdl file into:
      - header
      - geometry
      - animations
    '''
    if 'beginmodelgeom' in mdlFile:
        headerBlock, geomBlock = mdlFile.split('beginmodegeom', maxsplit = 1)
        if 'anim' in geomBlock:
            geomBlock, animBlock = geomBlock.split('anim', maxsplit = 1)
    else:
        pass #TODO: Raise an error


def geometry(geomBlock, nodeList):
    '''
    Splits geometry block into nodes
    '''
    nodes = asciiBlock.split('node').strip().split()
    #tng = re.split('(\[TILES\].+\[GROUPS\])', contents, flags=re.DOTALL)
    #blocks = re.split('(\[.+\])', contents)


def anim(animBlock, animList):
    '''
    Splits animation block into animations
    Splits animations into header and nodes
    '''
    anims = asciiBlock.split('anim').strip().split()
    anim_nodes = []
    for a in anims:
        anim_nodes.append(a.split('node'))


def f1(asciiBlock, floatList):
    '''
    Parses a series on floats into a list
    '''
    #floatList = [float(l[0]) for l in asciiBlock]
    l_float = float
    for line in asciiBlock:
        floatList.append(l_float(line[0]))


def f2(asciiBlock, floatList):
    '''
    Parses a series on float tuples into a list
    '''
    #floatList = [(float(l[0]), float(l[1])) for l in asciiBlock]
    l_float = float
    for line in asciiBlock:
        floatList.append( (l_float(line[0]),
                           l_float(line[1])) )


def f3(asciiBlock, floatList):
    '''
    Parses a series on float 3-tuples into a list
    '''
    #floatList = [(float(l[0]), float(l[1]), float(l[2])) for l in asciiBlock]
    l_float = float
    for line in asciiBlock:
        floatList.append( (l_float(line[0]),
                           l_float(line[1]),
                           l_float(line[2])) )


def f4(asciiBlock, floatList):
    '''
    Parses a series on float 4-tuples into a list
    '''
    #floatList = [(float(l[0]), float(l[1]), float(l[2]), float(l[3])) for l in asciiBlock]
    l_float = float
    for line in asciiBlock:
        floatList.append( (l_float(line[0]),
                           l_float(line[1]),
                           l_float(line[2]),
                           l_float(line[3])) )


def f5(asciiBlock, floatList):
    '''
    Parses a series on float 5-tuples into a list
    '''
    #floatList = [(float(l[0]), float(l[1]), float(l[2]), float(l[3]), float(l[4])) for l in asciiBlock]
    l_float = float
    for line in asciiBlock:
        floatList.append( (l_float(line[0]),
                           l_float(line[1]),
                           l_float(line[2]),
                           l_float(line[3]),
                           l_float(line[4])) )


def txt(asciiBlock, txtBlock):
    '''
    Return a block of text joined with newline (used for emitters)
    '''
    #txtBlock = ['\n'+' '.join(l) for l in aciiBlock]
    for line in asciiBlock:
        txtBlock = txtBlock + '\n' + ' '.join(line)

