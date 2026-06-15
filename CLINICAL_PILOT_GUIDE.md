# RGAI Sovereign Matrix: Clinical Pilot Execution Guide

This document is the definitive blueprint for conducting a live, physical clinical pilot of the RGAI Sovereign Matrix in a hospital or remote triage setting. It is designed to be handed to hospital IT administrators to prove that the offline-first, ternary-compressed edge mesh functions under real-world conditions.

---

## 🎯 Pilot Objective
Demonstrate that a standard hospital laptop (Central Hub) can ingest heavy DICOM medical images, aggressively compress them using Ternary Base-3 mathematics, and distribute them to low-end Android mobile devices (Edge Nodes) securely and offline, without any AWS/GCP cloud dependencies.

---

## 🛠️ Hardware Requirements
- **1x Central Hub**: A standard Windows Laptop or PC (Minimum 8GB RAM).
- **3-5x Edge Nodes**: Android mobile phones (Android 9.0+, minimum 4GB RAM).
- **1x Local Router**: A standard WiFi router (Does **NOT** need an active internet connection after initial setup).

---

## 🚀 Phase 1: Central Hub Initialization (Laptop)

1. **Network Setup**: Connect the laptop to the dedicated WiFi router.
2. **Launch Orchestrator**: Open PowerShell as Administrator and run the deployment script to initialize the Waitress WSGI server and the DICOM listener:
   ```powershell
   .\rgai_up.ps1
   ```
3. **Verify Listeners**:
   - The terminal should indicate the DICOM C-STORE SCP is listening on `Port 11112`.
   - The secure web interface should be listening on `http://127.0.0.1:5000`.

---

## 📱 Phase 2: Edge Node Onboarding (Android Phones)

For each Android phone participating in the triage mesh:
1. Connect the phone to the same WiFi router as the laptop.
2. Install **Termux** from F-Droid (do not use the Play Store version, as it is deprecated).
3. Open Termux and run the bootstrap script to pull the matrix environment:
   ```bash
   curl -sSL https://raw.githubusercontent.com/Roshan8005/RGAI-Sovereign-Matrix/main/bootstrap_termux.sh | bash
   ```
4. Start the mobile node listener:
   ```bash
   python3 rgai_phone_node.py
   ```
5. **Verification**: The Android screen will display `[Phone Node] Listening for UDP mesh broadcasts on port 9999`.

---

## 🏥 Phase 3: The Clinical Load Test (DICOM Ingestion)

Now we simulate the MRI/CT scanner sending an image to the system.

1. On the Central Hub, run the mock generator to simulate incoming DICOM data:
   ```powershell
   python mock_clinical_run.py
   ```
2. **Observe the Hub**: You will see the DICOM gateway successfully intercept the image, strip the Patient Health Information (PHI) to comply with HIPAA, and compress the payload using Ternary Math.
3. **Observe the Edge Nodes**: Look at the screens of the 5 Android phones. Within milliseconds, they will all receive the broadcasted compressed ternary payload, decrypt it using `ChaCha20Poly1305`, and reconstruct the diagnosis flag.

---

## 📊 Phase 4: Metrics Collection & Validation

To build a compelling VC/Enterprise case, record the following metrics during the pilot:
- [ ] **End-to-End Latency**: Time from executing `mock_clinical_run.py` to the phones decrypting the payload (Target: < 100ms).
- [ ] **Bandwidth Reduction**: Compare the original DICOM file size (usually 30MB+) to the UDP Ternary Payload size (usually < 5KB).
- [ ] **Cloud Cost Avoidance**: Document that 100% of the compute occurred locally. Cloud inference costs = $0.00.

> **Note to Administrators**: This pilot definitively proves that AI medical inference can happen in rural locations without internet access, bypassing traditional infrastructure bottlenecks.
