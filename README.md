# Vet-Exam Plus to DICOM Converter

This is a small application that allows converting images taken with **Vet-Exam Plus** software into the **DICOM** format.

During investigation of the Vet-Exam Plus export format, the following was discovered:

- The software saves image metadata in `.im0` files.
  - These files are normal text files containing metadata about the image and patient.
- The actual image data is stored in `.XTF` files.
  - The `.XTF` files appear to be standard TIFF image files.

The converter reads the metadata from the `.im0` files and combines it with the image data from the corresponding `.XTF` files to generate valid DICOM files.

## Study grouping

Vet-Exam Plus groups images taken within a short time interval for the same patient into the same study instance.

The converter follows the same approach by assigning images from the same patient and acquisition session to the same DICOM **Study Instance UID** while creating separate image instances for individual images.

## Purpose

The goal of this application is to make images produced by Vet-Exam Plus compatible with standard medical imaging systems by converting them into the DICOM format, allowing them to be stored, viewed, and managed using DICOM-compatible software such as PACS systems.

## Configuration

The folder where Vet-Exem Plus saves exported images can be changed in `settings.json`.

Open `settings.json` and update the image export path:

```json
{
  "imagePath": "C:/path/to/VetExem/export/folder"
}
```
You will also have to create `converted.txt` file before running the app.

## Disclaimer

This software is provided **as-is** and should be used at your own risk.

This project is not affiliated with, endorsed by, or supported by Vet-Exem Plus or its developers. The conversion process is based on observations of exported files and may not reproduce all functionality provided by the official licensed DICOM export module.

Always verify converted images before using them in a clinical workflow.
