from dicom_converter import convert2dicom, get_datetime, get_meta_data
from dicom_send import dicom_send
import os
import datetime
import json

with open("settings.json", "r") as f:
    settings = json.load(f)

search_path = settings["paths"]["search_path"]
out_path = settings["paths"]["out_path"]
converted_name = settings["paths"]["converted_name"]

with open(f"./{converted_name}", "r+") as f:
    names2data = dict() 
    converted_files = set()
    for line in f.readlines():
        tmp = line.split("\t")
        converted_files.add(tmp[0])
        if tmp[3] not in names2data:
            names2data[tmp[3]] = []
        names2data[tmp[3]].append([float(tmp[1]), tmp[2]])

    for file in os.listdir(search_path):
        if not file.endswith(".XTF"):
            continue
        name = file[:-4]
        if name not in converted_files:
            meta_data = get_meta_data(search_path, name)
            dt = get_datetime(meta_data)
            timestamp = (dt - datetime.datetime(2000, 1, 1)) / datetime.timedelta(seconds=1)
            patient = meta_data["ImageUserData"]
            pat_name = f"{patient['PatNName']}^{patient['PatVName']}"
            uid = None
            if pat_name in names2data:
                for scan_timestamp, scan_uid in names2data[pat_name]:
                    if abs(timestamp - scan_timestamp) < 3600:
                        uid = scan_uid
                        break

            study_instanceUID, pat_name = convert2dicom(search_path, out_path, name, meta_data, study_instanceUID=uid)
            f.write(f"{name}\t{timestamp}\t{study_instanceUID}\t{pat_name}\n")
            f.flush()
            if pat_name not in names2data:
                names2data[pat_name] = []
            names2data[pat_name].append([timestamp, study_instanceUID])

for file in os.listdir(out_path):
    success = dicom_send(**settings["pacs"], dicom_file=f"{out_path}/{file}")
    if success:
        os.remove(f"{out_path}/{file}")