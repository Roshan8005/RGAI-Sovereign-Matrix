import struct
import time
import sys
import os
import json
import hashlib

# Configure stdout/stderr to use UTF-8 to prevent emoji encoding crashes on Windows console/logs
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# Synchronization Epoch (June 1st, 2026)
EPOCH = 1780272000

class FractalNexusEngine:
    def __init__(self):
        self.header_single = 0xA3  # Single node telemetry identifier
        self.header_batch = 0xF0   # Batch telemetry identifier
        self.header_image_chunk = 0xD1 # PACS Diagnostic Image Chunk
        self.header_image_ack = 0xD2   # PACS Image Acknowledgement
        self.header_lam_task_dispatch = 0xE1 # OpenClaw Task Dispatch
        self.header_lam_task_result = 0xE2   # Kimi Agent Task Result

    def pack_single_node(self, payload):
        """Packs a single node telemetry payload dict into a compact binary format."""
        try:
            node_id = payload.get("node_id", "").encode('utf-8')
            node_id_len = len(node_id)
            if node_id_len > 255:
                node_id = node_id[:255]
                node_id_len = 255
                
            public_key_hex = payload.get("public_key", "0" * 64)
            # Ensure hex representation is correct length
            if len(public_key_hex) != 64:
                public_key_hex = hashlib.sha256(public_key_hex.encode()).hexdigest()
            public_key_bytes = bytes.fromhex(public_key_hex)
            
            # Pack numerical fields
            cpu_load = int(payload.get("cpu_load", 0.0) * 100)       # 2 bytes H
            ram_usage = int(payload.get("ram_usage", 0.0) * 100)     # 2 bytes H
            battery_level = int(payload.get("battery_level", 100))   # 1 byte B
            net_capital = float(payload.get("net_capital", 0.0))     # 4 bytes f
            cycle = int(payload.get("cycle", 0))                     # 4 bytes I
            processed_bytes = int(payload.get("processed_bytes", 0)) # 4 bytes I
            
            # Delta timestamp
            ts = float(payload.get("timestamp", time.time()))
            delta_ts = int(max(0.0, ts - EPOCH))                    # 4 bytes I
            
            # Pack format: 
            # Header (B), ID Len (B), NodeID (s), PublicKey (32s), CPU (H), RAM (H), Battery (B), Capital (f), Cycle (I), Bytes (I), DeltaTS (I), Signature (32s)
            signature_hex = payload.get("signature", "0" * 64)
            if len(signature_hex) != 64:
                signature_hex = hashlib.sha256(signature_hex.encode()).hexdigest()
            signature_bytes = bytes.fromhex(signature_hex)
            
            struct_format = f"!BB{node_id_len}s32sHHBfIII32s"
            binary_data = struct.pack(
                struct_format,
                self.header_single,
                node_id_len,
                node_id,
                public_key_bytes,
                cpu_load,
                ram_usage,
                battery_level,
                net_capital,
                cycle,
                processed_bytes,
                delta_ts,
                signature_bytes
            )
            return binary_data
        except Exception as e:
            print(f"[Fractal Error] Failed to pack telemetry: {e}")
            return None

    def unpack_single_node(self, binary_data):
        """Unpacks binary telemetry back into a standard RGAI MESH payload dictionary."""
        try:
            if not binary_data or binary_data[0] != self.header_single:
                return None
                
            node_id_len = binary_data[1]
            # Structure format based on variable node_id_len
            struct_format = f"!BB{node_id_len}s32sHHBfIII32s"
            
            unpacked = struct.unpack(struct_format, binary_data[:struct.calcsize(struct_format)])
            
            node_id = unpacked[2].decode('utf-8')
            public_key = unpacked[3].hex()
            cpu_load = unpacked[4] / 100.0
            ram_usage = unpacked[5] / 100.0
            battery_level = unpacked[6]
            net_capital = round(unpacked[7], 5)
            cycle = unpacked[8]
            processed_bytes = unpacked[9]
            timestamp = float(unpacked[10] + EPOCH)
            signature = unpacked[11].hex()
            
            payload = {
                "protocol": "RGAI_SAH_MESH",
                "node_id": node_id,
                "net_capital": net_capital,
                "cpu_load": cpu_load,
                "ram_usage": ram_usage,
                "battery_level": battery_level,
                "public_key": public_key,
                "cycle": cycle,
                "processed_bytes": processed_bytes,
                "timestamp": timestamp,
                "signature": signature
            }
            return payload
        except Exception as e:
            print(f"[Fractal Error] Failed to unpack telemetry: {e}")
            return None

    def pack_image_chunk(self, node_id, image_id, chunk_index, total_chunks, pixel_bytes):
        """Packs a raw binary image chunk into a compact Fractal Nexus UDP packet."""
        try:
            node_id_enc = node_id.encode('utf-8')[:255]
            node_id_len = len(node_id_enc)
            image_id_enc = image_id.encode('utf-8')[:255]
            image_id_len = len(image_id_enc)
            pixel_len = len(pixel_bytes)
            
            # Format: Header(B), NodeIDLen(B), NodeID(s), ImageIDLen(B), ImageID(s), ChunkIdx(H), TotalChunks(H), PixelLen(H), Pixels(s)
            struct_format = f"!BB{node_id_len}sB{image_id_len}sHHH{pixel_len}s"
            return struct.pack(
                struct_format,
                self.header_image_chunk,
                node_id_len, node_id_enc,
                image_id_len, image_id_enc,
                chunk_index, total_chunks,
                pixel_len, pixel_bytes
            )
        except Exception as e:
            print(f"[Fractal Error] Failed to pack image chunk: {e}")
            return None

    def unpack_image_chunk(self, binary_data):
        """Unpacks a Fractal Nexus UDP image chunk packet."""
        try:
            if not binary_data or binary_data[0] != self.header_image_chunk:
                return None
            
            node_id_len = binary_data[1]
            offset = 2
            node_id = binary_data[offset:offset+node_id_len].decode('utf-8')
            offset += node_id_len
            
            image_id_len = binary_data[offset]
            offset += 1
            image_id = binary_data[offset:offset+image_id_len].decode('utf-8')
            offset += image_id_len
            
            chunk_index, total_chunks, pixel_len = struct.unpack("!HHH", binary_data[offset:offset+6])
            offset += 6
            pixel_bytes = binary_data[offset:offset+pixel_len]
            
            return {
                "protocol": "RGAI_PACS_CHUNK",
                "node_id": node_id,
                "image_id": image_id,
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "pixel_bytes": pixel_bytes
            }
        except Exception as e:
            print(f"[Fractal Error] Failed to unpack image chunk: {e}")
            return None

    def pack_image_ack(self, node_id, image_id, chunk_index, chunk_hash):
        """Packs an acknowledgement proving the mobile node has stored/processed the chunk."""
        try:
            node_id_enc = node_id.encode('utf-8')[:255]
            node_id_len = len(node_id_enc)
            image_id_enc = image_id.encode('utf-8')[:255]
            image_id_len = len(image_id_enc)
            
            hash_bytes = bytes.fromhex(chunk_hash) if len(chunk_hash) == 64 else hashlib.sha256(chunk_hash.encode()).digest()
            
            # Format: Header(B), NodeIDLen(B), NodeID(s), ImageIDLen(B), ImageID(s), ChunkIdx(H), Hash(32s)
            struct_format = f"!BB{node_id_len}sB{image_id_len}sH32s"
            return struct.pack(
                struct_format,
                self.header_image_ack,
                node_id_len, node_id_enc,
                image_id_len, image_id_enc,
                chunk_index, hash_bytes
            )
        except Exception as e:
            print(f"[Fractal Error] Failed to pack image ack: {e}")
            return None

    def unpack_image_ack(self, binary_data):
        """Unpacks an Image Acknowledgement from a mobile worker node."""
        try:
            if not binary_data or binary_data[0] != self.header_image_ack:
                return None
                
            node_id_len = binary_data[1]
            offset = 2
            node_id = binary_data[offset:offset+node_id_len].decode('utf-8')
            offset += node_id_len
            
            image_id_len = binary_data[offset]
            offset += 1
            image_id = binary_data[offset:offset+image_id_len].decode('utf-8')
            offset += image_id_len
            
            chunk_index = struct.unpack("!H", binary_data[offset:offset+2])[0]
            offset += 2
            
            chunk_hash = binary_data[offset:offset+32].hex()
            
            return {
                "protocol": "RGAI_PACS_ACK",
                "node_id": node_id,
                "image_id": image_id,
                "chunk_index": chunk_index,
                "chunk_hash": chunk_hash
            }
        except Exception as e:
            print(f"[Fractal Error] Failed to unpack image ack: {e}")
            return None

    def pack_lam_task(self, target_node, task_id, matrix_size, iterations):
        """Packs a LAM OpenClaw automation task for broadcast."""
        try:
            target_node_enc = target_node.encode('utf-8')[:255]
            target_node_len = len(target_node_enc)
            task_id_enc = task_id.encode('utf-8')[:255]
            task_id_len = len(task_id_enc)
            
            # Format: Header(B), TargetNodeLen(B), TargetNode(s), TaskIDLen(B), TaskID(s), MatrixSize(H), Iterations(H)
            struct_format = f"!BB{target_node_len}sB{task_id_len}sHH"
            return struct.pack(
                struct_format,
                self.header_lam_task_dispatch,
                target_node_len, target_node_enc,
                task_id_len, task_id_enc,
                matrix_size, iterations
            )
        except Exception as e:
            print(f"[Fractal Error] Failed to pack LAM task: {e}")
            return None

    def unpack_lam_task(self, binary_data):
        """Unpacks a LAM OpenClaw automation task."""
        try:
            if not binary_data or binary_data[0] != self.header_lam_task_dispatch:
                return None
                
            offset = 1
            target_node_len = binary_data[offset]
            offset += 1
            target_node = binary_data[offset:offset+target_node_len].decode('utf-8')
            offset += target_node_len
            
            task_id_len = binary_data[offset]
            offset += 1
            task_id = binary_data[offset:offset+task_id_len].decode('utf-8')
            offset += task_id_len
            
            matrix_size, iterations = struct.unpack("!HH", binary_data[offset:offset+4])
            
            return {
                "protocol": "RGAI_LAM_TASK",
                "target_node": target_node,
                "task_id": task_id,
                "matrix_size": matrix_size,
                "iterations": iterations
            }
        except Exception as e:
            print(f"[Fractal Error] Failed to unpack LAM task: {e}")
            return None

    def pack_lam_result(self, node_id, task_id, execution_time_ms, result_hash):
        """Packs the result of a Kimi LAM task execution."""
        try:
            node_id_enc = node_id.encode('utf-8')[:255]
            node_id_len = len(node_id_enc)
            task_id_enc = task_id.encode('utf-8')[:255]
            task_id_len = len(task_id_enc)
            
            hash_bytes = bytes.fromhex(result_hash) if len(result_hash) == 64 else hashlib.sha256(result_hash.encode()).digest()
            
            # Format: Header(B), NodeIDLen(B), NodeID(s), TaskIDLen(B), TaskID(s), ExecTimeMs(I), Hash(32s)
            struct_format = f"!BB{node_id_len}sB{task_id_len}sI32s"
            return struct.pack(
                struct_format,
                self.header_lam_task_result,
                node_id_len, node_id_enc,
                task_id_len, task_id_enc,
                execution_time_ms, hash_bytes
            )
        except Exception as e:
            print(f"[Fractal Error] Failed to pack LAM result: {e}")
            return None

    def unpack_lam_result(self, binary_data):
        """Unpacks a Kimi LAM task execution result."""
        try:
            if not binary_data or binary_data[0] != self.header_lam_task_result:
                return None
                
            offset = 1
            node_id_len = binary_data[offset]
            offset += 1
            node_id = binary_data[offset:offset+node_id_len].decode('utf-8')
            offset += node_id_len
            
            task_id_len = binary_data[offset]
            offset += 1
            task_id = binary_data[offset:offset+task_id_len].decode('utf-8')
            offset += task_id_len
            
            exec_time_ms = struct.unpack("!I", binary_data[offset:offset+4])[0]
            offset += 4
            
            result_hash = binary_data[offset:offset+32].hex()
            
            return {
                "protocol": "RGAI_LAM_RESULT",
                "node_id": node_id,
                "task_id": task_id,
                "execution_time_ms": exec_time_ms,
                "result_hash": result_hash
            }
        except Exception as e:
            print(f"[Fractal Error] Failed to unpack LAM result: {e}")
            return None

    def pack_batch(self, payloads_list):
        """Packs multiple telemetry payloads recursively into a compound binary block."""
        try:
            packed_nodes = []
            for payload in payloads_list:
                packed = self.pack_single_node(payload)
                if packed:
                    packed_nodes.append(packed)
                    
            count = len(packed_nodes)
            batch_data = bytearray()
            batch_data.append(self.header_batch)
            batch_data.append(count)
            
            for packed in packed_nodes:
                length = len(packed)
                batch_data.extend(struct.pack("!H", length))
                batch_data.extend(packed)
                
            return bytes(batch_data)
        except Exception as e:
            print(f"[Fractal Error] Failed to pack batch: {e}")
            return None

    def unpack(self, binary_data):
        """Unpacks binary data automatically detecting if it is a single node or a recursive batch."""
        if not binary_data or len(binary_data) < 2:
            return None
            
        header = binary_data[0]
        if header == self.header_single:
            unpacked = self.unpack_single_node(binary_data)
            return [unpacked] if unpacked else []
            
        elif header == self.header_batch:
            try:
                count = binary_data[1]
                payloads = []
                offset = 2
                
                for _ in range(count):
                    if offset + 2 > len(binary_data):
                        break
                    length = struct.unpack("!H", binary_data[offset:offset+2])[0]
                    offset += 2
                    
                    if offset + length > len(binary_data):
                        break
                    node_data = binary_data[offset:offset+length]
                    offset += length
                    
                    # Recursively unpack nodes
                    unpacked_list = self.unpack(node_data)
                    if unpacked_list:
                        payloads.extend(unpacked_list)
                        
                return payloads
            except Exception as e:
                print(f"[Fractal Error] Failed to unpack batch data: {e}")
                return []
                
        elif header == self.header_image_chunk:
            unpacked = self.unpack_image_chunk(binary_data)
            return [unpacked] if unpacked else []
            
        elif header == self.header_image_ack:
            unpacked = self.unpack_image_ack(binary_data)
            return [unpacked] if unpacked else []
            
        elif header == self.header_lam_task_dispatch:
            unpacked = self.unpack_lam_task(binary_data)
            return [unpacked] if unpacked else []
            
        elif header == self.header_lam_task_result:
            unpacked = self.unpack_lam_result(binary_data)
            return [unpacked] if unpacked else []
            
        return []

if __name__ == "__main__":
    print("==========================================================")
    print("[Fractal Nexus] INITIALIZING COMPRESSION ENGINES           ")
    print("==========================================================")
    
    engine = FractalNexusEngine()
    test_node = {
        "node_id": "RGAI_MOBILE_ANDROID_9",
        "net_capital": 0.01091,
        "cpu_load": 22.99,
        "ram_usage": 62.6,
        "battery_level": 72,
        "public_key": "7be049c32ddf1e9538a7c2937be049c32ddf1e9538a7c2937be049c32ddf1e95",
        "cycle": 4,
        "processed_bytes": 2182,
        "timestamp": time.time()
    }
    
    print(f"[Input Telemetry Payload]:\n{json.dumps(test_node, indent=2)}")
    
    packed = engine.pack_single_node(test_node)
    print(f"\n[Packed Binary Size]: {len(packed)} bytes")
    
    unpacked_list = engine.unpack(packed)
    print(f"\n[Unpacked Telemetry Result]:\n{json.dumps(unpacked_list[0], indent=2)}")
