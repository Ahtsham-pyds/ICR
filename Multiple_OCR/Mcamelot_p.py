import math
import os
os.chdir('./')
os.getcwd()

import pandas as pd 
print(pd.__version__)

import camelot
import pandas as pd
lattice_tables = camelot.read_pdf('c:\\Users\\hahtsham\\work\\ICR\\Multiple_OCR\sample_with_tables.pdf', pages='all', flavor='lattice', suppress_stdout=False)
stream_tables = camelot.read_pdf('c:\\Users\\hahtsham\\work\\ICR\\Multiple_OCR\sample_with_tables.pdf', pages='all', flavor='stream', suppress_stdout=False)



def extract_table(path):
    # Lattice -> looks for clearly defined borders / lines like a grid, visible ruling lines between rows and columns
    lattice_tables = camelot.read_pdf('c:\\Users\\hahtsham\\work\\ICR\\Multiple_OCR\sample_with_tables.pdf', pages='all', flavor='lattice', suppress_stdout=False)
    stream_tables = camelot.read_pdf('c:\\Users\\hahtsham\\work\\ICR\\Multiple_OCR\sample_with_tables.pdf', pages='all', flavor='stream', suppress_stdout=False)
    return lattice_tables

 
