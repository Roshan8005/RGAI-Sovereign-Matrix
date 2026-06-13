import socket
import time
import os
import random
import hashlib
from fractal_nexus import FractalNexusEngine
from ternary_mesh_router import TernaryMeshRouter
import local_ledger

def generate_mock_mri_kspace(size=128):
    """Generates a mock 2D binary pixel array simulating MRI k-space data."""
    print(f"[Radiology Agent] Generating {size}x{size} high-density mock MRI k-space matrix...")
    # Generating a deterministic patterned byte array instead of random noise 
    # to simulate actual structured data that can compress.
    pixel_bytes = bytearray()
    for i in range(size):
        for j in range(size):
            val = (i ^ j) % 256
            pixel_bytes.append(val)
    return bytes(pixel_bytes)

def deploy_pacs_workload():
    print("==========================================================")
    print("🩺 RGAI DECENTRALIZED RADIOLOGY PACS AGENT                ")
    print("==========================================================")
    
    # 1. Generate the heavy image data
    image_bytes = generate_mock_mri_kspace(128) # 16,384 bytes
    image_id = f"MRI_BRAIN_AXIAL_{int(time.time())}"
    
    # 2. Slice into MTU-safe chunks
    CHUNK_SIZE = 1024 # well within 1400 byte UDP limit
    total_chunks = (len(image_bytes) + CHUNK_SIZE - 1) // CHUNK_SIZE
    
    print(f"[Radiology Agent] Image ID: {image_id}")
    print(f"[Radiology Agent] Total Size: {len(image_bytes)} bytes")
    print(f"[Radiology Agent] Slicing into {total_chunks} UDP-safe chunks of {CHUNK_SIZE} bytes...")
    
    # 3. Instantiate Nexus Engine and pure UDP Socket
    nexus_engine = FractalNexusEngine()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    time.sleep(1)
    
    print("[Radiology Agent] Dispatching chunks to the sovereign mesh on port 9999...")
    node_id = "Roshan_Sah_Primary_Core"
    
    from ternary_math_compressor import SahTernaryCompressor
    compressor = SahTernaryCompressor()
    
    for i in range(total_chunks):
        start_idx = i * CHUNK_SIZE
        end_idx = start_idx + CHUNK_SIZE
        chunk_data = image_bytes[start_idx:end_idx]
        
        # Pack binary chunk
        packed_chunk = nexus_engine.pack_image_chunk(
            node_id=node_id,
            image_id=image_id,
            chunk_index=i,
            total_chunks=total_chunks,
            pixel_bytes=chunk_data
        )
        
        if packed_chunk:
            # Broadcast raw binary directly to mesh
            sock.sendto(packed_chunk, ('255.255.255.255', 9999))
            sock.sendto(packed_chunk, ('127.0.0.1', 9999))
            print(f"[Radiology Agent] Dispatched chunk {i} ({len(packed_chunk)} bytes)")
            
            # Log dispatch in local ledger
            local_ledger.add_task(
                task_id=f"{image_id}_chunk_{i}",
                goal=f"Store MRI PACS Chunk ({len(chunk_data)} bytes)",
                executor_id="Pending",
                status="Pending",
                payout=0.015
            )
            
            time.sleep(0.5) # Prevent UDP flooding
            
    print("==========================================================")
    print("[Radiology Agent] All PACS chunks dispatched successfully!")
    print("==========================================================")

if __name__ == "__main__":
    deploy_pacs_workload()
