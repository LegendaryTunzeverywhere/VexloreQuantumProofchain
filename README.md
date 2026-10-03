# Vexlore Quantumproof Chain

**Free educational post-quantum blockchain** named **Vexlore**.

Uses real **ML-DSA-44** (NIST FIPS 204 / Dilithium) signatures — resistant to known quantum attacks (Shor’s algorithm).

> Not production-ready. This is a clean, runnable prototype you can study, extend, and play with locally.

## Version History

| Version | Focus |
|---------|--------|
| **v0.1** | Core chain, wallets, PoW, ML-DSA signatures |
| **v0.2** | NETWORK — multi-node, peer list, block/tx gossip, auto-sync |
| **v0.3** | BETTER CHAIN — adaptive difficulty, bigger blocks, better mempool, atomic saves, faster validation |

## Features

- Post-quantum digital signatures (ML-DSA-44)
- Proof-of-Work mining with **adaptive difficulty**
- Wallets with quantum-resistant keypairs
- Transactions with signature verification
- Simple balances + faucet for testing
- Persistent chain stored as JSON (atomic / crash-safe)
- Better mempool (waiting transactions)
- Bigger blocks (up to 50 transactions)
- Faster chain validation
- **Networking (from v0.2)**
  - HTTP peer API
  - Peer list + auto-sync
  - Block & transaction gossip

## Quick Start

```bash
pip install requests
python vexlore_chain.py