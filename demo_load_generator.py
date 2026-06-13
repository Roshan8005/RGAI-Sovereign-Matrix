import os
import sys
import time
import random
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import generate_uid, ImplicitVRLittleEndian
from pynetdicom import AE, StoragePresentationContexts
from pynetdicom.sop_class import (
    CTImageStorage, 
    MRImageStorage, 
    XRayAngiographicImageStorage,
    NuclearMedicineImageStorage,
    PositronEmissionTomographyImageStorage
)

def create_synthetic_dicom():
    """Generates a randomized medical imaging DICOM dataset."""
    modalities = [
        ("CT", CTImageStorage), 
        ("MRI", MRImageStorage), 
        ("XA", XRayAngiographicImageStorage),
        ("NM", NuclearMedicineImageStorage),
        ("PT", PositronEmissionTomographyImageStorage)
    ]
    chosen_modality, sop_class = random.choice(modalities)
    
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = sop_class
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ImplicitVRLittleEndian

    ds = FileDataset(f"synthetic_{chosen_modality}.dcm", {}, file_meta=file_meta, preamble=b"\0" * 128)
    
    # Synthetic Identifiers
    names = ["Doe^John", "Smith^Jane", "Roe^Richard", "Skywalker^Luke", "Anderson^Neo"]
    ds.PatientName = random.choice(names)
    ds.PatientID = f"{random.randint(100000, 999999)}"
    ds.Modality = chosen_modality
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPClassUID = sop_class
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    
    # Random Matrix Size Simulation (128x128 to 512x512)
    matrix_size = random.choice([128, 256, 512])
    ds.Rows = matrix_size
    ds.Columns = matrix_size
    ds.BitsAllocated = 8
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    
    if chosen_modality in ["NM", "PT"]:
        # Simulate volumetric multi-frame payload
        frames = random.choice([16, 32, 64])
        ds.NumberOfFrames = frames
        ds.PixelData = os.urandom((matrix_size * matrix_size * frames) // 16) if 'os' in globals() else b"\x01" * ((matrix_size * matrix_size * frames) // 16)
    else:
        # Generate dummy pixel data based on matrix size
        ds.PixelData = os.urandom((matrix_size * matrix_size) // 16) if 'os' in globals() else b"\x01" * ((matrix_size * matrix_size) // 16)
    
    ds.is_little_endian = True
    ds.is_implicit_VR = True
    
    return ds, chosen_modality, matrix_size

def start_load_generator():
    import os
    print("==========================================================")
    print(" [RGAI] LIVE-DEMO SYNTHETIC LOAD GENERATOR")
    print("==========================================================")
    print("[Load Gen] Spinning up Service Class User (SCU) engine...")
    print("[Load Gen] Target: RGAI Ingestion Gateway (127.0.0.1:11112)")
    print("----------------------------------------------------------")
    
    ae = AE()
    ae.add_requested_context(CTImageStorage)
    ae.add_requested_context(MRImageStorage)
    ae.add_requested_context(XRayAngiographicImageStorage)
    ae.add_requested_context(NuclearMedicineImageStorage)
    ae.add_requested_context(PositronEmissionTomographyImageStorage)
    
    req_count = 0
    
    try:
        while True:
            # Continuous rapid-fire stress test mode (0.05s to 0.2s delay)
            delay = random.uniform(0.05, 0.2)
            time.sleep(delay)
            
            req_count += 1
            print(f"[{req_count}] Synthesizing DICOM...")
            
            ds, modality, size = create_synthetic_dicom()
            print(f"[{req_count}] Modality: {modality} | Matrix: {size}x{size} | Size: {len(ds.PixelData)} bytes")
            
            assoc = ae.associate('127.0.0.1', 11112)
            if assoc.is_established:
                start_time = time.time()
                status = assoc.send_c_store(ds)
                end_time = time.time()
                
                if status and status.Status == 0x0000:
                    print(f"[{req_count}] [OK] C-STORE Success! (Latency: {(end_time - start_time)*1000:.2f}ms)")
                else:
                    print(f"[{req_count}] [ERROR] C-STORE Failed: 0x{status.Status:04x}" if status else f"[{req_count}] [ERROR] C-STORE Failed (No Status)")
                assoc.release()
            else:
                print(f"[{req_count}] [WARN] Connection Refused. Is the gateway running?")
                
            print("----------------------------------------------------------")
            
    except KeyboardInterrupt:
        print("\n[Load Gen] Load generation terminated by user. Shutting down SCU engine.")

if __name__ == "__main__":
    start_load_generator()
