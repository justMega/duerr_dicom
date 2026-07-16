from dicom_converter import convert2dicom
import os

path = "ref"
converted_path = "."
converted_name = "converted.txt"
with open(f"{converted_path}/{converted_name}", "r+") as f:
    converted_files = set(f.readlines())
    for file in os.listdir(path):
        if not file.endswith(".XTF"):
            continue
        name = file[:-4]
        if (name + "\n") not in converted_files:
            convert2dicom("ref", "out", name)
            f.writelines(name + "\n")
