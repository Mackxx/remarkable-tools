# reMarkable Merger
Tool to merge the annotations of a pdf file, created on a reMarkable reader into a
new pdf-file. Focusing at pen/pencil annotations made on a pdf-document. Position
is important but not its appearance.

# Status
The current status (March 2019) is that there is only a spike that works on already
extracted data (using e.g. scp/WinScp) and merges a single file (name fixed in code).
All annotations will result into simple lines (with a fixed width). Tested only on
Win10 with a few files.

# Installation
Install the required python modules (it assumes you already have python installed):

    pip install -r requirements.txt

# Execution
Modify the script to use your file and run the script:

    cd merge/spike
    python merge_document.py

# How does it works
- Data from the rm-file is extracted using the struct-modules. Based on the rM2svg-tool
from [maxio] and the notes from [ninja]
- reportlab is used to create a new pdf file with only the annotations.
- PyPDF2 is used to merge the original with the annotataion file into a new pdf-file.
- The create and merge approach came from a script I wrote for the iRex-reader, but
I am not sure anymore how I came to that code.

# Why another tool to merge?
- I want to preserve the orginal pdf-data as much as possible, only adding a new 'layer'
with the annotations.
- I want to keep the generated files small.
- I (want to) use this tool only to extract/merge the comments that I made when reading
documents, so I am not interested in the exact appearance as on the reader, but the
position should be correct.

[maxio]:https://github.com/reHackable/maxio/blob/master/tools/rM2svg
[ninja]:https://plasma.ninja/blog/devices/remarkable/binary/format/2017/12/26/reMarkable-lines-file-format.html