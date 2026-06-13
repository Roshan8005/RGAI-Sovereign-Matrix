# RGAI Swarm Network: Physical P2P Testing Guide

This manual provides step-by-step instructions to configure and execute the RGAI decentralized peer-to-peer (P2P) mesh network across multiple physical devices on a local subnet.

---

## 📡 Core Network Requirements
1. **Shared Subnet:** All testing laptops/devices MUST be connected to the same local network router (either via the same WiFi network or plugged into the same local network switch).
2. **Standard Subnet Mask:** Typically `255.255.255.0` (with local IPs looking like `192.168.1.X` or `10.0.0.X`).
3. **UDP Broadcast Permission:** Port `9999` must be open for sending and receiving connectionless balanced ternary packages.

---

## 🛠️ Step 1: Hardened Windows Firewall Rule Setup

By default, Windows Defender Firewall blocks inbound UDP broadcasts from unrecognized standalone executables. Rather than opening your system to public threats, run this hardened PowerShell command as **Administrator** on all testing laptops to allow Port 9999 traffic only from your local IP subnet:

```powershell
New-NetFirewallRule -DisplayName "RGAI Swarm Hardened UDP Port 9999" -Direction Inbound -Protocol UDP -LocalPort 9999 -RemoteAddress LocalSubnet -Action Allow
```

This blocks any public internet scanning and limits connectionless balanced ternary packet handshakes to devices sharing your physical subnet router.

---

## 📦 Step 2: Preparing and Copying the USB Assets

On your primary development machine:
1. Copy the compiled folder **`E:\VirtualUniverse\dist\RGAI_Universe`** onto a physical USB Drive (Pendrive).
2. Copy the following database directories next to `RGAI_Universe.exe` inside the pendrive folder:
   * `core_32_architects/`
   * `native_infrastructure/`
   * `network_users/`
3. Safely eject the pendrive and plug it into **Laptop B** (and Laptop C if available).
4. Extract/Copy the folder onto the desktop of the target physical laptops.

---

## 🚀 Step 3: Launching the Network Swarm

### On Laptop A (Master Core - Roshan Sah)
1. Run the local swarm launcher (either by double-clicking **`run_server.bat`** or executing **`RGAI_Universe.exe`**).
2. Confirm the terminal displays:
   * `[Launcher] Spin-up: Ternary Peer Discovery UDP Network active on Port 9999...`
   * `[Mesh Router] Compressed Packet (Ternary Code): ...`
3. Open your browser and navigate to the operations center:
   * 👉 **[http://127.0.0.1:5000/master-control](http://127.0.0.1:5000/master-control)**

### On Laptop B (Peer Node - Ankit or Rahul)
1. Open the user profile json in `network_users/` on Laptop B (e.g. `ankit_kumar_node.json` or `rahul_sharma_node.json`).
2. Run the swarm engine executable (`RGAI_Universe.exe`) on Laptop B.
3. Target terminal logs will print:
   * `[Mesh Router] Broadcasting local signal presence token: Ankit_Core_Node`
   * ` -> [Mesh Router] Decrypted Sah Ternary package from 192.168.1.X successfully.`

---

## 🕸️ Step 4: Verification of the Active Mesh Discovery Graph

Once both machines are running:
* Look at the browser window of **Laptop A** (`http://127.0.0.1:5000/master-control`).
* Within 10 seconds, Laptop B's custom ID (e.g., `Ankit_Core_Node` or `Rahul_Swarm_Node`) will **automatically spawn inside the Active Peer Mesh Discovery Graph**.
* The newly spawned node card will display the target IP address and its live net capital USD values, pulsing green synchronously with the master core node!

---

## 💡 Troubleshooting Grid
* **No Peers Showing?** Verify that both devices are connected to the same subnet gateway. Ensure that public/private firewall rules on Port `9999` are active on BOTH machines.
* **Lagging Updates?** The discovery beacon broadcasts every 10 seconds. Wait at least 15-20 seconds for the initial handshake to register in the UI grids.
