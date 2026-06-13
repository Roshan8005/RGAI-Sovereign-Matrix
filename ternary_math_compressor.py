import os
import sys
import json

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure stdout/stderr to use UTF-8 to prevent emoji encoding crashes on Windows console/logs
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

class SahTernaryCompressor:
    def __init__(self):
        # Character map representation for balanced ternary string
        self.val_to_trit = { -1: 'T', 0: '0', 1: '1' }
        self.trit_to_val = { 'T': -1, '0': 0, '1': 1 }
        
        # Precomputed lookup tables for byte values 0 to 255
        self.byte_to_trits = []
        self._precompute_lookup_tables()

    def _precompute_lookup_tables(self):
        """Precomputes uniform 6-trit balanced ternary representations for values 0 to 255."""
        for n in range(256):
            if n == 0:
                self.byte_to_trits.append([0, 0, 0, 0, 0, 0])
                continue
            
            val = n
            trits = []
            while val > 0:
                remainder = val % 3
                val = val // 3
                if remainder == 2:
                    remainder = -1
                    val += 1
                trits.append(remainder)
                
            # Pad to 6 trits
            trit_sequence = trits[::-1]
            while len(trit_sequence) < 6:
                trit_sequence.insert(0, 0)
            self.byte_to_trits.append(trit_sequence)

    def integer_to_balanced_ternary(self, n):
        """Standard integer value ko Balanced Ternary list me convert karna (-1, 0, 1)"""
        if 0 <= n < 256:
            return self.byte_to_trits[n]
            
        if n == 0:
            return [0]
        
        val = abs(n)
        trits = []
        while val > 0:
            remainder = val % 3
            val = val // 3
            if remainder == 2:
                remainder = -1
                val += 1
            trits.append(remainder)
            
        trit_sequence = trits[::-1]
        if n < 0:
            # Negate all trits for negative numbers
            trit_sequence = [-x for x in trit_sequence]
        return trit_sequence

    def balanced_ternary_to_integer(self, trits):
        """Balanced Ternary list ko standard Integer me reconstruct karna"""
        val = 0
        multipliers = [243, 81, 27, 9, 3, 1]
        
        # If the input list is exactly 6 trits (common path), use static multipliers
        if len(trits) == 6:
            for i in range(6):
                val += trits[i] * multipliers[i]
            return val
            
        # Fallback for dynamic length arrays
        power = 1
        for trit in reversed(trits):
            val += trit * power
            power *= 3
        return val

    def string_to_ternary_stream(self, data_string):
        """Raw JSON text arrays or raw bytes ko structured Sah Protocol multi-state stream me wrap karna"""
        try:
            # Step 1: Converting text characters or raw bytes to integer arrays
            if isinstance(data_string, bytes) or isinstance(data_string, bytearray):
                byte_array = list(data_string)
            else:
                byte_array = [ord(char) for char in data_string]
                
            ternary_matrix = []
            for byte in byte_array:
                if 0 <= byte < 256:
                    ternary_matrix.append(self.byte_to_trits[byte])
                else:
                    trit_sequence = self.integer_to_balanced_ternary(byte)
                    while len(trit_sequence) < 6:
                        trit_sequence.insert(0, 0)
                    ternary_matrix.append(trit_sequence)
                
            return ternary_matrix
        except Exception as e:
            print(f"[Math Error] Compression fault in string conversion: {e}")
            return []

    def serialize_matrix_to_string(self, matrix):
        """Compressed matrix sequence into highly compact network string characters"""
        flat_stream = ""
        for sequence in matrix:
            for val in sequence:
                flat_stream += self.val_to_trit[val]
        return flat_stream

    def deserialize_string_to_matrix(self, serialized_stream):
        """Serialized trit string ko back to 6-trit matrices convert karna"""
        matrix = []
        sequence = []
        for char in serialized_stream:
            if char in self.trit_to_val:
                sequence.append(self.trit_to_val[char])
                if len(sequence) == 6:
                    matrix.append(sequence)
                    sequence = []
        return matrix

    def ternary_stream_to_string(self, matrix):
        """Ternary matrix sequences ko text arrays me decompress karna"""
        try:
            chars = []
            for sequence in matrix:
                unicode_val = self.balanced_ternary_to_integer(sequence)
                chars.append(chr(unicode_val))
            return "".join(chars)
        except Exception as e:
            print(f"[Math Error] Decompression fault in dynamic decoding: {e}")
            return ""

    def ternary_stream_to_bytes(self, matrix):
        """Ternary matrix sequences ko raw bytes arrays me decompress karna"""
        try:
            return bytes(self.balanced_ternary_to_integer(sequence) for sequence in matrix)
        except Exception as e:
            print(f"[Math Error] Decompression fault in binary decoding: {e}")
            return b""

if __name__ == "__main__":
    print("==========================================================")
    print("[Antahkarana Kernel] INITIALIZING SAH TERNARY COMPRESSOR   ")
    print("==========================================================")
    
    compressor = SahTernaryCompressor()
    test_payload = json.dumps({"node_id": "Roshan_Sah_Primary_Core", "balance": 76.0})
    
    print(f"[Input String]: {test_payload}")
    print(f"[Input Weight]: {len(test_payload)} characters")
    
    matrix = compressor.string_to_ternary_stream(test_payload)
    serialized_stream = compressor.serialize_matrix_to_string(matrix)
    
    print(f"\n[Compressed Sah Ternary Stream]: {serialized_stream}")
    print(f"[Ternary Matrix Word Count]: {len(matrix)} blocks processed successfully.")
    
    # Verify Bidirectional decompression integrity
    deserialized_matrix = compressor.deserialize_string_to_matrix(serialized_stream)
    decompressed_string = compressor.ternary_stream_to_string(deserialized_matrix)
    print(f"\n[Decompressed Verification String]: {decompressed_string}")
    print("==========================================================")
