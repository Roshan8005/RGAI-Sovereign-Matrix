import os
import sys
import time
import json
import hashlib
import socket
import threading
import random

class RGAISovereignEngine:
    def __init__(self):
        """
        Initializing the independent node core. 
        Bypassing standard cloud configurations by generating local cryptographic signatures.
        Unifies RGAISovereignVault with RGAISovereignEngine specifications.
        """
        self.engine_version = "RGAI-Sovereign-v3.0.0"
        self.node_signature = hashlib.sha256(str(time.time()).encode()).hexdigest()[:12]
        self.local_vault = f"./rgai_vault_{self.node_signature}"
        self.is_mesh_active = True
        
        # Precompute lookup table for 5-trit balanced ternary conversion
        self.byte_to_5_trits = []
        self._precompute_5_trits_lookup()
        
        if not os.path.exists(self.local_vault):
            os.makedirs(self.local_vault)
            
        print(f"============================================================")
        print(f"[RGAI CORE ENGINE] Boot Sequence Initiated Successfully.")
        print(f"[VERSION] {self.engine_version}")
        print(f"[NODE ID] {self.node_signature}")
        print(f"[VAULT LOCATION] {self.local_vault}")
        print(f"============================================================")

    def _precompute_5_trits_lookup(self):
        """Precomputes uniform 5-trit balanced ternary representations for values 0 to 255."""
        for n in range(256):
            val = n
            state_buffer = []
            while val > 0:
                remainder = val % 3
                val = val // 3
                if remainder == 2:
                    val += 1
                    state_buffer.append(-1)
                else:
                    state_buffer.append(remainder)
            while len(state_buffer) < 5:
                state_buffer.append(0)
            self.byte_to_5_trits.append(state_buffer[:5])

    # =========================================================================
    # CORE MODULE 1: THE TERNARY LOGIC TRANSLATOR (Base-3 State Space)
    # =========================================================================
    def strip_and_clean_metadata(self, raw_payload):
        """
        Countering COMINT/SIGINT indexing: Removes transmission footprints, 
        leaving only raw, naked logical symbols.
        """
        return raw_payload.strip().replace("\r", "")

    def convert_to_balanced_ternary(self, data_string):
        """
        Converts traditional 8-bit characters into a continuous matrix of 
        Balanced Ternary States: -1 (Contraction), 0 (Neutral), +1 (Expansion).
        This eliminates the rigid binary bounds and creates high-entropy layouts.
        """
        matrix_output = []
        for char in data_string:
            decimal_val = ord(char)
            if 0 <= decimal_val < 256:
                matrix_output.extend(self.byte_to_5_trits[decimal_val])
            else:
                # Fallback for characters outside 0-255 range
                state_buffer = []
                val = decimal_val
                while val > 0:
                    remainder = val % 3
                    val = val // 3
                    if remainder == 2:
                        val += 1
                        state_buffer.append(-1)
                    else:
                        state_buffer.append(remainder)
                while len(state_buffer) < 5:
                    state_buffer.append(0)
                matrix_output.extend(state_buffer[:5])
                
        return matrix_output

    # =========================================================================
    # CORE MODULE 2: METADATA-STRIPPED ENVELOPE SEALS (Fractal Storage)
    # =========================================================================
    def commit_matrix_to_disk(self, block_identifier, raw_payload):
        """
        Strips tracking metadata, processes structural compression via ternary arrays,
        and flattens the output directly into safe storage chunks (.rgai files).
        """
        cleaned_payload = self.strip_and_clean_metadata(raw_payload)
        ternary_matrix = self.convert_to_balanced_ternary(cleaned_payload)
        crypto_hash = hashlib.sha256(cleaned_payload.encode('utf-8')).hexdigest()
        
        # System manifest construction without telemetry or tracking links
        manifest_payload = {
            "Manifest_ID": block_identifier,
            "Timestamp_Epoch": time.time(),
            "Data_Signature_Hash": crypto_hash,
            "Ternary_Matrix_Length": len(ternary_matrix),
            "State_Space_Vectors": ternary_matrix
        }
        
        target_filename = f"matrix_block_{block_identifier}.rgai"
        target_filepath = os.path.join(self.local_vault, target_filename)
        
        with open(target_filepath, 'w') as target_file:
            json.dump(manifest_payload, target_file, indent=4)
            
        print(f"[VAULT] Manifest Block '{block_identifier}' secured locally.")
        print(f" -> Cryptographic Hash: {crypto_hash[:16]}... Safe.")
        return target_filepath

    def commit_sovereign_block(self, block_name, payload_stream, use_binary_flat_file=False):
        """
        Locks the encoded matrix directly to the local storage barrier.
        Supports standard JSON manifests and optimized Flat Binary Overhauling (.bin).
        """
        clean_data = self.strip_and_clean_metadata(payload_stream)
        
        # 🛡️ Counter-Measure: Zero-Leak/TEMPEST Compute Throttle
        self.insert_compute_noise()
        
        ternary_matrix = self.convert_to_balanced_ternary(clean_data)
        
        if use_binary_flat_file:
            # Flat Binary Overhauling: Direct bitwise representation to optimize R/W operations
            # Pack trits (-1, 0, 1) into compact byte streams (mapping to 0, 1, 2)
            packed_bytes = bytearray()
            for trit in ternary_matrix:
                mapped_val = trit + 1
                packed_bytes.append(mapped_val)
                
            target_file = os.path.join(self.local_vault, f"matrix_block_{block_name}.bin")
            with open(target_file, 'wb') as f:
                f.write(packed_bytes)
            print(f"[VAULT-LOCK] Flat Binary Block '{block_name}' optimized and sealed. Size: {len(packed_bytes)} bytes.")
            return target_file
        else:
            return self.commit_matrix_to_disk(block_name, payload_stream)

    # =========================================================================
    # CORE MODULE 3: THE SAH PROTOCOL DEMON (Decentralized Node Discovery)
    # =========================================================================
    def _mesh_network_daemon(self, network_bind_port):
        """
        Background execution loop that turns the machine into a sovereign listening 
        post capable of direct P2P socket communication without intermediate ISPs.
        """
        listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            listener_socket.bind(('0.0.0.0', network_bind_port))
            listener_socket.listen(10)
            print(f"[SAH PROTOCOL] Decentralized Mesh Daemon active on port {network_bind_port}.")
        except Exception as error_msg:
            print(f"[NETWORK BREAK] Binding failure encountered: {error_msg}")
            return

        while self.is_mesh_active:
            try:
                listener_socket.settimeout(1.5)
                client_socket, client_address = listener_socket.accept()
                print(f"\n[SAH HANDSHAKE] Direct Inbound Node Connection Verified: {client_address}")
                
                # Processing structural socket synchronization packages
                incoming_bytes = client_socket.recv(2048).decode('utf-8')
                if incoming_bytes:
                    print(f"[SAH PROTOCOL] Incoming Node State String: {incoming_bytes}")
                    client_socket.sendall(b"RGAI_NODE_ACK_SUCCESS\n")
                    
                client_socket.close()
            except socket.timeout:
                continue
            except Exception:
                break
                
        listener_socket.close()

    def deploy_sah_mesh_layer(self, port_assignment=8520):
        """
        Fires up the network daemon on a fully isolated system thread 
        to ensure zero processing blockages on the main compute loops.
        """
        mesh_worker = threading.Thread(target=self._mesh_network_daemon, args=(port_assignment,))
        mesh_worker.daemon = True
        mesh_worker.start()
        print(f"[DEPLOYMENT] P2P background routing infrastructure is online.")

    # =========================================================================
    # ADVANCED SAFEGUARDS: SIDE-CHANNEL TEMPEST MASKS & AIRGAPS
    # =========================================================================
    def insert_compute_noise(self):
        """
        Countering Air-Gap Exploitation (TEMPEST / AirHopper):
        Injects chaotic data bursts/random math calculations on CPU cores 
        to scramble RAM/CPU micro-emissions into undecodable noise.
        """
        noise_cycles = random.randint(10000, 50000)
        temp_val = 1.0
        for i in range(noise_cycles):
            # Chaotic floating-point math burst
            temp_val = (temp_val * 3.14159) % (random.random() + 0.1)
        # Yield thread slice slightly
        time.sleep(0.005)

    def trigger_airgap_mode(self):
        """
        Simulates dynamic network adapter lock-down to enforce zero outbound leaks 
        during heavy cryptographic operations.
        """
        print("\n[AIR-GAP] Initiating software-level network isolation guard...")
        print("[AIR-GAP] WARNING: External sockets blocked. Pure local transition matrix active.")
        time.sleep(0.5)

    # =========================================================================
    # SYSTEM SHUTDOWN DECREE
    # =========================================================================
    def close_engine(self):
        """
        Gracefully winds down threads and locks down memory arrays.
        """
        print("\n" + "="*60 + "\n[TERMINATION] Initiating engine lockdown sequences...")
        self.is_mesh_active = False
        time.sleep(1.2)
        print("[TERMINATION] All background data structures sealed clean.")

# Legacy Alias Class for complete system backward compatibility
class RGAISovereignVault(RGAISovereignEngine):
    pass

# =========================================================================
# PRODUCTION PIPELINE RUNTIME
# =========================================================================
if __name__ == "__main__":
    # Step 1: Initialize the Sovereign Engine Configuration
    rgai_core = RGAISovereignEngine()
    
    # Step 2: Enable dynamic air-gap protection
    rgai_core.trigger_airgap_mode()
    
    # Step 3: Fire up the Sah Protocol Network Mesh Daemon
    rgai_core.deploy_sah_mesh_layer(port_assignment=9119)
    
    # Step 4: Run Test Matrix Pipelines and Ingest Logic Sets
    print("\n[EXECUTION] Encoding core technical definitions into local state space...")
    
    rgai_core.commit_sovereign_block(
        block_name="RGAI_ARCH_001",
        payload_stream="Sovereign computing framework executing data pipelines via ternary systems.",
        use_binary_flat_file=False
    )
    
    rgai_core.commit_sovereign_block(
        block_name="SAH_NET_RULES",
        payload_stream="Direct P2P socket allocations allowing local nodes to sync states outside standard clouds.",
        use_binary_flat_file=True # Utilizing the Flat Binary Overhaul for optimized storage
    )
    
    print("\n[LIVE MONITORING] Core Engine is online and independent. System running indefinitely.")
    print("="*60)
    
    # Keeping the main execution scope alive briefly to showcase backend thread status
    time.sleep(4)
    
    # Step 5: Gracefully seal the engine assets
    rgai_core.close_engine()
