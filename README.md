# Vexlore Quantumproof Chain

**Free educational post-quantum blockchain** named **Vexlore**.

Uses real **ML-DSA-44** (NIST FIPS 204 / Dilithium) signatures — resistant to known quantum attacks (Shor’s algorithm).

> Not production-ready. This is a clean, runnable prototype you can study, extend, and play with locally.

## Version History

| Version | Focus |
|---------|--------|
| **v0.1** | Core chain, wallets, PoW, ML-DSA signatures |
| **v0.2** | **NETWORK** — multi-node, peer list, block/tx gossip, auto-sync |

## Features

- Post-quantum digital signatures (ML-DSA-44)
- Proof-of-Work mining (adjustable difficulty)
- Wallets with quantum-resistant keypairs
- Transactions with signature verification
- Simple balances + faucet for testing
- Persistent chain stored as JSON
- **v0.2 Networking**
  - HTTP peer API (`/chain`, `/block`, `/transaction`, `/peers`, `/status`)
  - Basic peer list (persisted in `data/peers.json`)
  - Broadcast new blocks & transactions to peers
  - Auto-sync: periodically pull longer valid chains
  - Longest-valid-chain rule

## Quick Start

```bash
pip install requests
python vexlore_chain.py