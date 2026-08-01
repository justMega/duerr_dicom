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
from scipy.ndimage import median_filter
from skimage.exposure import rescale_intensity


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


def gauss_fd(
    img,
    al0=0.0,
    al1=1.0,
    ftp=4.0,
    ah0=0.25,
    ah1=1.0,
    fhp=0.125,
):
    """
    Approximation of Dürr Vet-Exam Gauss_FD filter.

    Parameters:
        al0 : low frequency offset
        al1 : low frequency amplitude
        ftp : low frequency transition frequency

        ah0 : high frequency offset
        ah1 : high frequency amplitude
        fhp : high pass frequency

    """

    img = img.astype(np.float32)

    h, w = img.shape

    # Fourier transform
    F = np.fft.fftshift(np.fft.fft2(img))

    # normalized frequency coordinates
    # fy = np.fft.fftshift(np.fft.fftfreq(h))
    # fx = np.fft.fftshift(np.fft.fftfreq(w))
    # FX, FY = np.meshgrid(fx, fy)

    # radial frequency
    # f = np.sqrt(FX**2 + FY**2)
    u = np.arange(w) - w // 2
    v = np.arange(h) - h // 2
    U, V = np.meshgrid(u, v)
    f = np.sqrt(U**2 + V**2)
    # f /= f.max()

    # avoid divide by zero
    ftp = max(ftp, 1e-9)
    fhp = max(fhp, 1e-9)

    G_low = np.exp(-((f / ftp) ** 2))
    G_high = np.exp(-((f / fhp) ** 2))

    A_l = al0 + (al1 - al0) * G_low
    A_h = ah0 + (ah1 - ah0) * (1 - G_high)

    H = 1 + (A_h - A_l)
    H /= H[h // 2, w // 2]
    # H = 1 + (H - dc)
    # H = 1 + (ah1 - ah0) * (1 - np.exp(-((f / fhp) ** 2)))
    filtered = np.real(np.fft.ifft2(np.fft.ifftshift(F * H)))
    filtered = rescale_intensity(filtered, in_range="image", out_range=(0, 65535))
    return filtered.astype(np.uint16)


def apply_img_operations(img, operation):
    if "Invert" in operation:
        return np.max(img) - img
    if "DDIP" not in operation:
        return img
    operation = operation.split(" ")[4:]
    operation = " ".join(operation)
    operation = operation.replace("ddipparam=", "")
    operation = operation.replace('"', "")
    op_type, params = operation.split(" ", 1)
    op_type = op_type.replace("Type=", "")
    params = params.split(" ")
    match op_type:
        case "Gauss_FD2" | "Gauss_FD":
            # print("GAUSS")
            vm = dict()
            for p in params:
                pp = p.split("=")
                vm[pp[0]] = float(pp[1])
            # print(vm)
            img = gauss_fd(img, **vm)
        case "HISTOGRAMM_EQUAL3":
            img = img.astype(np.float32)
            mask = img > 0
            values = img[mask]
            p_low = np.percentile(values, 0.5)
            p_high = np.percentile(values, 99.5)
            img = (img - p_low) / (p_high - p_low)
            img = np.clip(img, 0, 1)
            img = (img * 65535).astype(np.uint16)
        case "Median_Filter":
            size = params[0].replace("size=", "")
            img = median_filter(img, size=int(size))
    return img


def convert2dicom(path, out_path, file_name, meta_data, study_instanceUID=None):
    # pprint.pprint(meta_data)
    # pprint.pprint(meta_data["ImageOperations"])

    image = Image.open(f"{path}/{file_name}.XTF")
    image = np.array(image)

    if "ImageOperations" in meta_data:
        for op, value in meta_data["ImageOperations"].items():
            image = apply_img_operations(image, value)

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
    low = np.percentile(pixels, 10)
    high = np.percentile(pixels, 90)
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
