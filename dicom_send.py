from pynetdicom import AE
from pynetdicom.sop_class import DigitalXRayImageStorageForPresentation
from pydicom import dcmread


def dicom_send(pacs_ip, pacs_port, pacs_ae_title, dicom_file):
    # Create application entity
    ae = AE()

    # Add storage presentation context
    ae.add_requested_context(
        DigitalXRayImageStorageForPresentation
    )

    # Read DICOM
    ds = dcmread(dicom_file)

    # Connect to PACS
    assoc = ae.associate(
        pacs_ip,
        pacs_port,
        ae_title=pacs_ae_title
    )

    success = True
    if assoc.is_established:
        status = assoc.send_c_store(ds)
        if status:
            print("C-STORE status:", hex(status.Status))
        else:
            print("C-STORE failed")
            success = False
        assoc.release()
    else:
        print("Could not connect to PACS")
        success = False
    return success

