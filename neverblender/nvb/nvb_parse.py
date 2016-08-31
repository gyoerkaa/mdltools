def weights(self, asciiBlock):
    lfloat = float
    lchunker = nvb_utils.chunker
    for line in asciiBlock:
        # A line looks like this
        # [group_name, vertex_weight, group_name, vertex_weight]
        # We create a list looking like this:
        # [[group_name, vertex_weight], [group_name, vertex_weight]]
        memberships = []
        for chunk in lchunker(line, 2):
            memberships.append( [chunk[0], lfloat(chunk[1])] )

        self.weights.append(memberships)


def faces(asciiFaces, faceList):
    l_int = int
    for line in asciiFaces:
        facelist.faces.append( (l_int(line[0]), l_int(line[1]), l_int(line[2])) )
        facelist.shdgr.append(l_int(line[3]))
        facelist.uvIdx.append( (l_int(line[4]), l_int(line[5]), l_int(line[6])) )
        facelist.matId.append(l_int(line[7]))


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

