
def f1(asciiBlock, floatList):
    l_float = float
    for line in asciiBlock:
        floatList.append(l_float(line[0]))


def f2(asciiBlock, floatList):
    l_float = float
    for line in asciiBlock:
        floatList.append( (l_float(line[0]),
                           l_float(line[1])) )


def f3(asciiBlock, floatList):
    l_float = float
    for line in asciiBlock:
        floatList.append( (l_float(line[0]),
                           l_float(line[1]),
                           l_float(line[2])) )


def f4(asciiBlock, floatList):
    l_float = float
    for line in asciiBlock:
        floatList.append( (l_float(line[0]),
                           l_float(line[1]),
                           l_float(line[2]),
                           l_float(line[3])) )


def f5(asciiBlock, floatList):
    l_float = float
    for line in asciiBlock:
        floatList.append( (l_float(line[0]),
                           l_float(line[1]),
                           l_float(line[2]),
                           l_float(line[3]),
                           l_float(line[4])) )


def txt(asciiBlock, txtBlock):
    for line in asciiBlock:
        txtBlock = txtBlock + '\n' + ' '.join(line)
