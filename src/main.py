import datetime
import json
import os

from dicom_converter import convert2dicom, get_datetime, get_meta_data
from dicom_send import dicom_send

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

    files = os.listdir(search_path)
    for file in files:
        if not file.endswith(".XTF"):
            continue
        name = file[:-4]
        print(name)
        if name + ".im0" not in files:
            continue
        if name not in converted_files:
            meta_data = get_meta_data(search_path, name)
            dt = get_datetime(meta_data)
            cutoff_dt = datetime.datetime(2024, 1, 1)
            if dt < cutoff_dt:
                f.write(f"{name}\t0\tNone\tNone\n")
                f.flush()
                continue
            timestamp = (dt - datetime.datetime(2000, 1, 1)) / datetime.timedelta(
                seconds=1
            )
            patient = meta_data["ImageUserData"]
            pat_name = f"{patient['PatNName']}^{patient['PatVName']}"
            uid = None
            if pat_name in names2data:
                for scan_timestamp, scan_uid in names2data[pat_name]:
                    if abs(timestamp - scan_timestamp) < 3600:
                        uid = scan_uid
                        break

            study_instanceUID, pat_name = convert2dicom(
                search_path, out_path, name, meta_data, study_instanceUID=uid
            )
            f.write(f"{name}\t{timestamp}\t{study_instanceUID}\t{pat_name}\n")
            f.flush()
            if pat_name not in names2data:
                names2data[pat_name] = []
            names2data[pat_name].append([timestamp, study_instanceUID])
exit()
for file in os.listdir(out_path):
    print("sending", file)
    success = dicom_send(**settings["pacs"], dicom_file=f"{out_path}/{file}")
    if success:
        os.remove(f"{out_path}/{file}")
