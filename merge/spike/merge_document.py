import os
import struct
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from PyPDF2 import PdfFileWriter, PdfFileReader
import os

"""
This code is experimental code to merge the annotations to a pdf-document by adding 'overlays' to the original document.
I use the reMarkablemainly to make annotations to (pdf) documents, so my primary focus will be getting my annotations
at the correct place and not getting them the same as a export from the device.
TODO:
- Handle scaled annotations
- Handle Notebooks, no original pdf to merge to
- Check behavior for different sizes (and aspect ratios) of the original document
- Add more features of lines, like setLineWidth(unit:1/72 inch)
- Scale output to screen ratio, to show all drawings
- Do better error handling
- See also the svg file extracted by Remarkable windows app! Can these be re-created? or used to merge with pdf?
"""

DEVICE_WIDTH = 1404
DEVICE_HEIGHT = 1872
COLOR = colors.red
LINE_WIDTH = 0.5 * mm


class Page(object):
    def __init__(self, nr):
        self.nr = nr # page number in document
        self.layers = []

    def addLayer(self, layer):
        self.layers.append(layer)

class Layer(object):
    def __init__(self, nr):
        self.nr = nr
        self.lines = []

    def addLine(self, line):
        self.lines.append(line)

class Line(object):
    def __init__(self, brushType, colour, i_unk, brushSize):
        self.brushType = brushType
        self.colour = colour
        self.i_unk = i_unk
        self.brushSize = brushSize
        self.segments = []

    def addSegment(self, segment):
        self.segments.append(segment)


class Segment(object):
    def __init__(self, x, y, speed, direction, width, pressure):
        self.x = x
        self.y = y
        self.speed = speed
        self.direction = direction
        self.width = width
        self.pressure = pressure
        
def processPageFile(linesFile, pageNr, verbose=False):
    """ Extract the page-data from the lines-file (.rm).
        Returns a Page-class with the extracted data.
        Extraction based on: https://plasma.ninja/blog/devices/remarkable/binary/format/2017/12/26/reMarkable-lines-file-format.html
    """
    page = Page(pageNr)
    with open(linesFile, 'rb') as f:
        lines = f.read()
    offset = 0

    # The file starts with a header, indicating the version of the format
    expected_header=b'reMarkable .lines file, version=3          '

    fmt = '<43s' # 43 characters
    data = struct.unpack_from(fmt, lines, offset)
    offset += struct.calcsize(fmt)
    header = data[0]

    if header != expected_header:
        print('Unexpected header:{}'.format(header))

    if verbose: print('Header:{}'.format(header))

    # The number of layers
    fmt = '<I'
    data = struct.unpack_from(fmt, lines, offset)
    offset += struct.calcsize(fmt)
    nrLayers = data[0]
    if verbose: print('Layers:{}'.format(nrLayers))

    for layerNr in range(nrLayers):
        layer = Layer(layerNr)
        page.addLayer(layer)

        # The number of lines
        fmt = '<I'
        data = struct.unpack_from(fmt, lines, offset)
        offset += struct.calcsize(fmt)
        nrLines = data[0]
        if verbose: print('Lines:{}'.format(nrLines))

        for _l in range(nrLines):
            # line header
            fmt = '<IIIfI'
            data = struct.unpack_from(fmt, lines, offset)
            offset += struct.calcsize(fmt)
            brushType, colour, i_unk, brushSize, nrSegments = data
            line = Line(brushType, colour, i_unk, brushSize)
            layer.addLine(line)
            if verbose: print('LineInfo:{}, {}, {}, {}, {}'.format(brushType, colour, i_unk, brushSize, nrSegments))
            # brushType: 2 (pen),3 (pen),4 (fine liner),7 (pencil sharp),1 (pencil wide),0 (brush),
            #            5 (marker/highlighter: always color 0),6 :(erase?)
            # i_unk: (The value is different for strokes coming from the "Move, scale, rotate & copy" tool)
            # color (0: black, 1: grey, 2: white)
            # brush base size: 1.875, 2.0, 2.125

            for _s in range(nrSegments):
                # line segment
                fmt = '<ffffff'
                data = struct.unpack_from(fmt, lines, offset)
                offset += struct.calcsize(fmt)
                x, y, speed, direction, width, pressure = data
                segment = Segment(x, y, speed, direction, width, pressure)
                line.addSegment(segment)
                if verbose: print('  SegmentInfo:{}, {}, {}, {}, {}, {}'.format(x, y, speed, direction, width, pressure))
    return page

def createPdfDocument(basename, annoFileName, mergedFileName):
    inputName = '%s.pdf'%basename
    inputOrg = PdfFileReader(open(inputName, "rb"))
    pagesWithContent = []

    nrPages = inputOrg.getNumPages()
    print('Pages:%d'%nrPages)
    # do not use the first page, it can have a different size
    # TODO: Create a canvas per page?
    if nrPages > 4:
        pageNr = 4
    else:
        pageNr = nrPages-1
    pageInfo = inputOrg.getPage(pageNr)
    width = float(pageInfo.mediaBox.getWidth())
    height = float(pageInfo.mediaBox.getHeight())
    ratioPdf = height/width
    ratioDevice = float(DEVICE_HEIGHT)/float(DEVICE_WIDTH)
    # The device will try to show the complete document, so it will scale differently
    if ratioPdf > ratioDevice:
        factorX = ratioPdf/ratioDevice
        factorY = 1.0
    else:
        # TODO: test this ratio
        factorY = ratioPdf/ratioDevice
        factorX = 1.0
    print( 'Page {} size {} x {}\n'.format(pageNr, width, height))
    print(ratioPdf, ratioDevice, ratioPdf/ratioDevice)

    
    print( 'Generating: %s\n' % annoFileName)
    pdf = Canvas(annoFileName, pagesize=(width, height), bottomup = 0)

    for ip in range(nrPages):
        filename = '{}/{}.rm'.format(basename, ip)
        if not os.path.exists(filename): continue
        print('Processing page:%d'%ip)
        pagesWithContent.append(ip)
        pageData = processPageFile(filename, ip, verbose=False)
        for layer in pageData.layers:
            for line in layer.lines:
                pdf.setStrokeColor(COLOR)
                pdf.setFillColor(COLOR)

                # round line joints and endings
                pdf.setLineJoin(1)
                pdf.setLineCap(1)
                pdf.setLineWidth(LINE_WIDTH)
                path = pdf.beginPath()
                for i, segment in enumerate(line.segments):
                    # input is in pixels, canvas is in inch, with 72DPI
                    x = ((segment.x * width) / float(DEVICE_WIDTH)) * factorX
                    y = ((segment.y * height) / float(DEVICE_HEIGHT)) * factorY
                    #print('  {} {} - {} {}'.format(segment.x, segment.y, x, y))
                    if i == 0:
                        path.moveTo(x, y)
                    else:
                        path.lineTo(x, y)

                if len(line.segments) > 1:
                    pdf.drawPath(path, True, False)
        # finish page
        pdf.showPage()
    # and save
    pdf.save()

    # next step is to merge new file with existing
    print('  MERGING Annotations')

    # create the output and open the input files
    output = PdfFileWriter()
    inputAnno = PdfFileReader(open(annoFileName, "rb"))
    inputOrg = PdfFileReader(open(inputName, "rb"))

    print( "%s has %d pages.\n" % (inputName, inputOrg.getNumPages()))
    annoPageNr = 0
    for pageNr in range(inputOrg.getNumPages()):
        page = inputOrg.getPage(pageNr)
        print( 'Copying page %d size %d x %d\n' %(pageNr+1, page.mediaBox.getWidth(), page.mediaBox.getHeight()))
        # Check if this page has annotations
        if pageNr in pagesWithContent:
            page2 = inputAnno.getPage(annoPageNr)
            print( '  Merging Page %d size %d x %d\n' %(annoPageNr+1, page2.mediaBox.getWidth(), page2.mediaBox.getHeight()))
            annoPageNr += 1
            page.mergePage(page2)
        output.addPage(page)

    # finally, write "output" to document-output.pdf
    outputStream = open(mergedFileName, "wb")
    output.write(outputStream)
    outputStream.close()

    
def dumpPage(page):
    print('Layers:{}'.format(len(page.layers)))
    for layer in page.layers:
        print('Lines:{}'.format(len(layer.lines)))
        for line in layer.lines:
            print('LineInfo:{}, {}, {}, {}, {}'.format(line.brushType, line.colour, line.i_unk, line.brushSize, len(line.segments)))
            for segment in line.segments:
                print('  SegmentInfo:{}, {}, {}, {}, {}, {}'.format(segment.x, segment.y, segment.speed, segment.direction, segment.width, segment.pressure))
                
if __name__ == "__main__":
    basename = '../../../FromRemarkable/xochitl/efe0bb22-d7cb-4ff0-b910-6a3fd71a48e7'
    generated = 'generated'
    annoFileName = os.path.join(generated, 'annotations.pdf')
    mergedFileName = os.path.join(generated, 'merged.pdf')
    if not os.path.exists(generated):
        os.mkdir(generated)
    createPdfDocument(basename, annoFileName, mergedFileName)
