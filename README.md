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
| **v0.4** | WALLET UPGRADES — seed phrase backup, encrypted wallet files, multiple addresses, transaction history, fast balance |

## Features (v0.4)

- Post-quantum digital signatures (ML-DSA-44)
- Proof-of-Work mining with **adaptive difficulty**
- **Seed-phrase wallets** (12-word BIP-39 style mnemonic)
- **Encrypted wallet files** (password + PBKDF2 + Fernet)
- **Multiple addresses** from one seed (HD-style derivation)
- Transaction history (local + full-chain scan)
- Fast O(1) balance checks
- Simple balances + faucet for testing
- Persistent chain stored as JSON (atomic / crash-safe)
- Better mempool + bigger blocks (up to 50 txs)
- **Networking** — HTTP peer API, peer list, auto-sync, block & tx gossip

## Quick Start

```bash
pip install requests cryptography
python3 vexlore_chain.py
```

### First-time walkthrough

1. Choose **1** → create a new wallet  
   - Type a name (or just press Enter for “alice”)  
   - Choose a password  
   - **Write down the 12 words** that appear! This is your only backup.

2. Choose **4** → Faucet → get free test coins  
3. Choose **6** → Mine a block → coins arrive  
4. Choose **3** → See your balance (instant)  
5. Choose **10** → Create extra addresses anytime  
6. Choose **5** → Send coins  
7. Choose **11** → See transaction history  

### Restore from seed phrase

```
1 → (r)estore
Paste your 12 words
Choose a new password
```

## Folder layout

```
vexlore/
├── vexlore_chain.py      ← main program (v0.4)
├── demo.py               ← non-interactive demo
├── README.md
├── dilithium_src/        ← pure-Python ML-DSA
├── wallet/               ← encrypted wallet files
└── data/                 ← chain + peers
```

## Security notes (educational)

- Seed phrase = full control of the wallet. Never share it.
- Wallet file is encrypted; without the password the secrets stay safe.
- This is **not** production software. Do not put real money on it.

Have fun exploring post-quantum crypto!
