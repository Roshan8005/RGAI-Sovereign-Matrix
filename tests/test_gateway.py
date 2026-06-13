import sys
import os
import unittest.mock
from pydicom.dataset import Dataset, FileMetaDataset

# Add root directory to sys.path to import root modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dicom_proxy_gateway import handle_store
from ternary_math_compressor import SahTernaryCompressor

class MockEvent:
    def __init__(self, dataset):
        self.dataset = dataset
        self.file_meta = FileMetaDataset()
        # Mocking the association requestor AE title for logging
        self.assoc = unittest.mock.MagicMock()
        self.assoc.requestor.ae_title = b"TEST_AE"

@unittest.mock.patch("dicom_proxy_gateway.requests.post")
def test_phi_strip_handle_store(mock_post):
    """Test 1: Validate PHI stripping in DICOM Gateway"""
    # Create mock DICOM dataset with PHI
    ds = Dataset()
    ds.PatientName = "John^Doe"
    ds.PatientID = "123456"
    ds.Modality = "CT"
    
    mock_event = MockEvent(ds)
    
    # Execute handle_store
    result = handle_store(mock_event)
    
    # Assert network request was called (preventing actual HTTP post)
    mock_post.assert_called_once()
    
    # Assert PHI was successfully stripped
    assert mock_event.dataset.PatientName == "ANONYMIZED^RGAI"
    assert mock_event.dataset.PatientID == "000000"
    assert result == 0x0000  # Success status

def test_ternary_compression_roundtrip():
    """Test 2: Validate Ternary Mathematical Compression integrity"""
    original = b"RGAI_SOVEREIGN_MATRIX_TEST_PAYLOAD_2025"
    compressor = SahTernaryCompressor()
    
    # Compress
    matrix = compressor.string_to_ternary_stream(original)
    serialized = compressor.serialize_matrix_to_string(matrix)
    
    # Decompress
    deserialized = compressor.deserialize_string_to_matrix(serialized)
    recovered = compressor.ternary_stream_to_bytes(deserialized)
    
    # Assert absolute data integrity
    assert recovered == original

def test_ternary_compression_transformation():
    """Test 3: Validate Ternary Compression output transformation"""
    original = b"TEST_DATA"
    compressor = SahTernaryCompressor()
    
    matrix = compressor.string_to_ternary_stream(original)
    
    assert len(matrix) > 0  # Compression produced output
    assert matrix != original  # Actual transformation happened
