# Vexlore Quantumproof Chain

**Free educational post-quantum blockchain** named **Vexlore**.

Uses real **ML-DSA-44** (NIST FIPS 204 / Dilithium) signatures — resistant to known quantum attacks (Shor’s algorithm).

> Not production-ready. This is a clean, runnable prototype you can study, extend, and play with locally.

## Features

- Post-quantum digital signatures (ML-DSA-44)
- Proof-of-Work mining (adjustable difficulty)
- Wallets with quantum-resistant keypairs
- Transactions with signature verification
- Simple balances + faucet for testing
- Persistent chain stored as JSON
- Fully offline / free — no paid services

## Quick Start

```bash
cd vexlore
python3 vexlore_chain.py
```

### First-time flow (recommended)

1. The program auto-creates an **alice** wallet with an ML-DSA keypair.
2. Choose **3** → Faucet → get free test coins.
3. Choose **5** → Mine a block (this confirms the faucet + gives mining reward).
4. Choose **2** → See your balance.
5. Create another wallet (option 1) and send coins (option 4).
6. Mine again (option 5) to confirm the transfer.
7. Option 6 shows the full chain. Option 7 validates it.

## Project Layout

```
vexlore/
├── vexlore_chain.py      # Main blockchain + CLI
├── dilithium_src/        # Pure-Python ML-DSA (FIPS 204)
├── wallet/               # Generated wallets (JSON)
├── data/
│   └── vexlore_chain.json
└── README.md
```

## Cryptography Notes

| Component          | Algorithm              | Notes                          |
|--------------------|------------------------|--------------------------------|
| Signatures         | ML-DSA-44 (Dilithium)  | NIST standard, lattice-based   |
| Hashing / PoW      | SHA-256                | Still strong against quantum   |
| Address format     | `VEX` + hash prefix    | Simple demo format             |

Public key ≈ 1312 bytes, signature ≈ 2420 bytes (much larger than ECDSA — normal for post-quantum).

## Next Steps You Can Take

- Increase `DIFFICULTY` in the code for harder mining
- Add more nodes + simple P2P (Flask + requests)
- Switch to ML-DSA-65 / ML-DSA-87 for higher security levels
- Replace PoW with a simple PoS or round-robin for a “quantum-friendly” consensus
- Build a web UI or Telegram bot on top of it
- Later migrate to a real framework (Cosmos SDK / Substrate) and keep the same quantum signature design

## Disclaimer

This is an educational prototype. Do **not** use it to store real value. Production blockchains need audits, proper networking, consensus research, economic design, and legal consideration.

---

Made for the Vexlore quantumproof vision — free and open.
