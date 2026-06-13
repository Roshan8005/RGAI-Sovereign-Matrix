# Contributing to RGAI Sovereign Matrix

Thank you for considering contributing to the RGAI Sovereign Matrix framework! Our mission is to democratize clinical AI edge inference, and we welcome contributions from the global open-source and medical-tech community.

## ⚖️ Open Source vs. Enterprise
This repository operates under the **AGPLv3** license. 
- If you are building academic or open-source solutions, you may use and modify the code provided you open-source your modifications under the same license.
- If you are building a commercial enterprise application that cannot comply with the AGPLv3 copyleft provisions, please reach out for a Commercial Enterprise License.

## 🚀 Getting Started

1. **Fork & Clone:** Fork the repository to your own GitHub account and clone it locally.
2. **Setup Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Environment Variables:** Copy `.env.example` to `.env` and set up your secure key paths. Do **not** commit actual keys.

## 🛠️ Development Standards & Pull Requests

When submitting a Pull Request (PR), ensure your code adheres to the following strict guidelines:

- **Testing is Mandatory:** Any new feature or bug fix must be accompanied by relevant `pytest` coverage in the `tests/` directory.
- **CI/CD Passing:** We use GitHub Actions for continuous integration. Your PR must pass all linting (`flake8`) and unit tests (`pytest`).
- **Code Style:** Follow PEP-8 standards. Keep functions modular and stateless where possible, especially in the mesh networking logic.

## 🔴 CRITICAL: Medical Data Privacy Policy (HIPAA / ABDM)

> **Never commit real DICOM files. All test fixtures must use synthetically generated `pydicom.Dataset` objects only.**

Under no circumstances should actual Protected Health Information (PHI) or genuine patient scans be uploaded to this repository. The RGAI Sovereign Matrix is designed to protect patient data; we enforce absolute zero-tolerance for PHI leakage in our codebase. If you need to test volumetric extraction, generate programmatic pixel arrays using `numpy`.

---
*By contributing to this repository, you agree that your contributions will be licensed under its AGPLv3 License.*
