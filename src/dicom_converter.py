import datetime

import numpy as np
from PIL import Image
from pydicom import Dataset, FileDataset
from pydicom.uid import (
    DigitalXRayImageStorageForPresentation,
    ExplicitVRLittleEndian,
    SecondaryCaptureImageStorage,
    generate_uid,
)


def get_meta_data(path, file_name):
    meta_data = dict()
    with open(f"{path}/{file_name}.im0", errors="replace") as f:
        lines = f.readlines()
        current_dict = dict()
        for line in lines:
            line = line.strip()
            if line[0] == "[" and line[-1] == "]":
                current_dict = dict()
                meta_data[line[1:-1]] = current_dict
            else:
                tmp = line.split("=", 1)
                current_dict[tmp[0]] = tmp[1]
    return meta_data


def get_datetime(meta_data):
    return datetime.datetime.strptime(
        meta_data["ImageUserData"]["ImgCreateDateTimeString"]
        .replace(". ", ".")
        .replace("/", "."),
        "%d.%m.%Y %H:%M:%S",
    )


def convert2dicom(path, out_path, file_name, meta_data, study_instanceUID=None):
    # pprint.pprint(meta_data)
    # pprint.pprint(meta_data["ImageOperations"])

    image = Image.open(f"{path}/{file_name}.XTF")
    image = np.array(image)
    image = np.max(image) - image

    # File Meta Information
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()

    # Create dataset
    ds = FileDataset(
        "example.dcm",
        {},
        file_meta=file_meta,
        preamble=b"\0" * 128,
    )

    # Patient Information
    patient = meta_data["ImageUserData"]
    name = f"{patient['PatNName']}^{patient['PatVName']}"
    ds.PatientName = name
    ds.PatientID = patient["PatPNR"]
    ds.PatientSex = patient["PatSex"]

    # Study information
    if study_instanceUID is None:
        study_instanceUID = generate_uid()
    ds.StudyInstanceUID = study_instanceUID
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.SOPClassUID = DigitalXRayImageStorageForPresentation
    ds.StudyDescription = "Dental Examination"
    ds.Modality = "DX"
    ds.ImageType = ["ORIGINAL", "PRIMARY", "DENTAL"]
    ds.InstitutionName = patient["PracName"]

    # Date and Time
    dt = get_datetime(meta_data)
    ds.StudyDate = dt.strftime("%Y%m%d")
    ds.StudyTime = dt.strftime("%H%M%S")

    # Image attributes
    h, w = image.shape
    ds.Rows = h
    ds.Columns = w
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0

    # Pixel spacing
    if "RawImageCreationInfo" in meta_data:
        raw = meta_data["RawImageCreationInfo"]
        pixel_size_mm = int(raw["PixelSize"]) / 1_000_000
        ds.PixelSpacing = [pixel_size_mm, pixel_size_mm]
    else:
        ds.PixelSpacing = [1, 1]

    # Windowing
    pixels = image[image > 0]
    low = np.percentile(pixels, 1)
    high = np.percentile(pixels, 99)
    window_center = (high + low) / 2
    window_width = high - low

    ds.WindowCenter = window_center
    ds.WindowWidth = window_width

    # Pixel data
    ds.PixelData = image.tobytes()

    # Endianness
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # Save
    ds.save_as(f"{out_path}/{file_name}.dcm")
    return study_instanceUID, name
