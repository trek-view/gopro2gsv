import sys, copy
from pathlib import Path
from spatialmedia import mpeg as mpeg4_container

sys.argv.append("/home/fqrious/Downloads/GS018423.360")
filename = sys.argv[1]

with open(filename, "rb") as f:
    m = mpeg4_container.load(f)
    print(m.moov_box)
    # m.print_structure()
    