# 🪐 RGAI COGNITIVE SWARM NETWORK
## 👥 REAL USER & NODE ONBOARDING FRAMEWORK (BETA MANUAL)

This framework details the operational protocols for onboarding, registering, and syncing beta-test client nodes within the **Roshan Global Advanced Intelligence (RGAI)** connection mesh. Follow this sequence to scale your swarm to 5–10 real physical nodes safely.

---

## 📋 SECTION 1: PRE-FLIGHT NODE CHECKLIST

Before onboarding a new user node, verify the target machine meets these core standard parameters:
1.  **OS Bound:** Microsoft Windows 10 or 11 (64-bit).
2.  **Network Scope:** Must reside within the same local IP subnet (e.g. `192.168.0.0/16` or `10.0.0.0/8`).
3.  **Firewall Policy:** UDP Port `9999` must be open for local subnet unicast/broadcast packets.
4.  **Hardware Class:** Minimum 4GB RAM & dual-core CPU processing architecture.

---

## ⚙️ SECTION 2: FIREWALL HARDENING RULES (LOCAL SUBNET ONLY)

To prevent external internet DDoS threats or malicious port scanning, **DO NOT** open Port 9999 to public networks. Run this hardened PowerShell command as Administrator on the client machine to allow only local subnet communication:

```powershell
New-NetFirewallRule -DisplayName "RGAI Swarm Hardened UDP Port 9999" -Direction Inbound -Protocol UDP -LocalPort 9999 -RemoteAddress LocalSubnet -Action Allow
```

This ensures that only devices on your local Wi-Fi/Ethernet network can transmit balanced ternary data waves to the node.

---

## 💾 SECTION 3: STEP-BY-STEP CLIENT PROVISIONING

### Step A: Dynamic Node Registration Mapping
Every new node must have a unique identifier and ledger file. Create a new JSON file inside the `network_users/` folder on your primary laptop, named precisely as `{username}_node.json`.

**Example: `network_users/ankit_kumar_node.json`**
```json
{
    "owner": "Ankit_Kumar",
    "user_ledger": {
        "operations_completed": 0,
        "balance_usd": 0.00,
        "crypto_monitored_balance_btc": 0.00,
        "crypto_valuation_usd": 0.00
    },
    "primary_allocation": "Swarm_Computational_Scraping",
    "assigned_hardware_node": "RGAI_Swarm_Device_Beta_V2",
    "status": "Awaiting_Peer_Mesh_Handshake",
    "transactions": []
}
```

### Step B: The Portable Swarm Deployment Pack
1.  On your primary machine, compile the secure matrix using `build_exe.bat`.
2.  Copy the compiled stand-alone wrapper directory `dist\RGAI_Universe` to your USB pendrive.
3.  Ensure these dynamic database folders are copied **next to the executable** in your pendrive:
    *   `core_32_architects/`
    *   `native_infrastructure/`
    *   `network_users/`
4.  Plug the pendrive into the client laptop and run `RGAI_Universe.exe`.

---

## 📡 SECTION 4: THE PHYSICAL MESH HANDSHAKE

Once the client node is running:
1.  Ensure your primary machine has triggered the local Flask server (`run_server.bat`).
2.  Navigate to your Master Control Admin interface: 👉 **[http://127.0.0.1:5000/master-control](http://127.0.0.1:5000/master-control)**
3.  The client node will start broadcasting its presence token encrypted in balanced ternary trit waves (`T`, `0`, `1`).
4.  Your dashboard will detect the broadcast, decompress the packet, and **auto-spawn** the new node on your visual connection grid with a pulsing cyan link line!

---

## 🎁 SECTION 5: DISCORD COMMUNITY BONUS & COMMUNITY MATRIX

To expand your community meshes and reward top-contributing nodes:
*   **Active Peer Rewards:** Nodes maintaining a 100% heartbeat uptime over a 24-hour cycle receive a virtual balance bonus credited directly to their ledger.
*   **The Discord Swarm Channel:** Coordinate physical multi-PC testing locations, share log files, and invite new members to register their specific machine IDs to the sovereign network vault registers!

---

**Beta Swarm Deployment Standard: Signed and Seared for Physical Mesh Onboarding.** 👥🛸🛰️🪐🚀
