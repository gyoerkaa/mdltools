"""TODO: DOC."""


def faces(asciiFaces, faceList):
    """TODO: DOC."""
    l_int = int
    for line in asciiFaces:
        faceList.faces.append((l_int(line[0]),
                               l_int(line[1]),
                               l_int(line[2])))
        faceList.shdgr.append(l_int(line[3]))
        faceList.uvIdx.append((l_int(line[4]),
                               l_int(line[5]),
                               l_int(line[6])))
        faceList.matId.append(l_int(line[7]))


def f1(asciiBlock, floatList):
    """Parse a series on floats into a list."""
    # floatList = [float(l[0]) for l in asciiBlock]
    l_float = float
    for line in asciiBlock:
        floatList.append(l_float(line[0]))


def f2(asciiBlock, floatList):
    """Parse a series on float tuples into a list."""
    # floatList = [(float(l[0]), float(l[1])) for l in asciiBlock]
    l_float = float
    for line in asciiBlock:
        floatList.append((l_float(line[0]),
                          l_float(line[1])))


def f3(asciiBlock, floatList):
    """Parse a series on float 3-tuples into a list."""
    l_float = float
    for line in asciiBlock:
        floatList.append((l_float(line[0]),
                          l_float(line[1]),
                          l_float(line[2])))


def f4(asciiBlock, floatList):
    """Parse a series on float 4-tuples into a list."""
    l_float = float
    for line in asciiBlock:
        floatList.append((l_float(line[0]),
                          l_float(line[1]),
                          l_float(line[2]),
                          l_float(line[3])))


def f5(asciiBlock, floatList):
    """Parse a series on float 5-tuples into a list."""
    l_float = float
    for line in asciiBlock:
        floatList.append((l_float(line[0]),
                          l_float(line[1]),
                          l_float(line[2]),
                          l_float(line[3]),
                          l_float(line[4])))
