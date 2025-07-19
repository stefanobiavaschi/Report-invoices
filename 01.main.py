from lib.postprocess import postprocess
from lib.processxml import XMLProcessing

xmlproc = XMLProcessing()

# Update the input directories as needed
input_dirs = [
    "data/raw/25_02_01-25_03_31",
    "data/raw/25_04_01-25_05_30",
    "data/raw/25_05_31-25_06_25",
    "data/raw/25_06_26-25_07_12",
]


xmlproc.process_xml(input_dirs)

# Select date in the format "yymmdd"
postprocess(data_string="250713")
