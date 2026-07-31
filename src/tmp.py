import os
from dicom_converter import get_meta_data, apply_img_operations, convert2dicom
from pprint import pprint

name = "00002649"
meta_data = get_meta_data("in", name)
study_instanceUID, pat_name = convert2dicom("in", "out", name, meta_data)
