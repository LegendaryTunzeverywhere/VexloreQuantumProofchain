#!/usr/bin/env python3
"""
Vexlore Quantumproof Chain
A free, educational post-quantum blockchain prototype.

Uses ML-DSA (FIPS 204 / Dilithium) for quantum-resistant signatures.
Not production-ready — for learning and experimentation only.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add pure-Python ML-DSA implementation
sys.path.insert(0, str(Path(__file__).parent / "dilithium_src"))
from dilithium_py.ml_dsa import ML_DSA_44  # type: ignore

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CHAIN_NAME = "Vexlore Quantumproof Chain"
VERSION = "0.1.0-quantum"
DIFFICULTY = 3          # leading zero hex digits for PoW (demo level)
DATA_DIR = Path(__file__).parent / "data"
CHAIN_FILE = DATA_DIR / "vexlore_chain.json"
WALLETS_DIR = Path(__file__).parent / "wallet"

DATA_DIR.mkdir(exist_ok=True)
WALLETS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Crypto helpers (post-quantum)
# ---------------------------------------------------------------------------
def pq_keygen() -> Tuple[bytes, bytes]:
    """Generate ML-DSA-44 keypair (public, secret)."""
    return ML_DSA_44.keygen()


def pq_sign(secret_key: bytes, message: bytes) -> bytes:
    return ML_DSA_44.sign(secret_key, message)


def pq_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    return ML_DSA_44.verify(public_key, message, signature)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def address_from_pubkey(pubkey: bytes) -> str:
    """Simple address: VEX + first 20 hex chars of hash of pubkey."""
    h = sha256(pubkey)
    return "VEX" + h[:20]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class Transaction:
    tx_id: str
    sender: str          # address
    recipient: str       # address
    amount: float
    timestamp: float
    public_key: str      # hex of ML-DSA public key
    signature: str       # hex of ML-DSA signature
    memo: str = ""

    def message_to_sign(self) -> bytes:
        payload = {
            "tx_id": self.tx_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "memo": self.memo,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Transaction":
        return cls(**d)

    def verify(self) -> bool:
        try:
            pk = bytes.fromhex(self.public_key)
            sig = bytes.fromhex(self.signature)
            return pq_verify(pk, self.message_to_sign(), sig)
        except Exception:
            return False


@dataclass
class Block:
    index: int
    timestamp: float
    transactions: List[Transaction]
    previous_hash: str
    nonce: int = 0
    hash: str = ""
    miner: str = "genesis"

    def compute_hash(self) -> str:
        tx_data = [t.to_dict() for t in self.transactions]
        block_string = json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "transactions": tx_data,
                "previous_hash": self.previous_hash,
                "nonce": self.nonce,
                "miner": self.miner,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(block_string.encode())

    def mine(self, difficulty: int = DIFFICULTY) -> None:
        target = "0" * difficulty
        while True:
            self.hash = self.compute_hash()
            if self.hash.startswith(target):
                break
            self.nonce += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [t.to_dict() for t in self.transactions],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
            "miner": self.miner,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Block":
        txs = [Transaction.from_dict(t) for t in d["transactions"]]
        return cls(
            index=d["index"],
            timestamp=d["timestamp"],
            transactions=txs,
            previous_hash=d["previous_hash"],
            nonce=d.get("nonce", 0),
            hash=d.get("hash", ""),
            miner=d.get("miner", ""),
        )


# ---------------------------------------------------------------------------
# Wallet
# ---------------------------------------------------------------------------
class Wallet:
    def __init__(self, name: str = "default"):
        self.name = name
        self.path = WALLETS_DIR / f"{name}.json"
        self.public_key: bytes = b""
        self.secret_key: bytes = b""
        self.address: str = ""

        if self.path.exists():
            self._load()
        else:
            self._generate()

    def _generate(self) -> None:
        print(f"[*] Generating quantum-resistant keypair for wallet '{self.name}' ...")
        self.public_key, self.secret_key = pq_keygen()
        self.address = address_from_pubkey(self.public_key)
        self._save()
        print(f"[+] Wallet ready")
        print(f"    Address : {self.address}")
        print(f"    PK size : {len(self.public_key)} bytes (ML-DSA-44)")
        print(f"    SK size : {len(self.secret_key)} bytes")

    def _save(self) -> None:
        data = {
            "name": self.name,
            "address": self.address,
            "public_key": self.public_key.hex(),
            "secret_key": self.secret_key.hex(),
            "algo": "ML-DSA-44",
            "created": time.time(),
        }
        self.path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        data = json.loads(self.path.read_text())
        self.public_key = bytes.fromhex(data["public_key"])
        self.secret_key = bytes.fromhex(data["secret_key"])
        self.address = data["address"]
        print(f"[+] Loaded wallet '{self.name}' → {self.address}")

    def create_transaction(
        self, recipient: str, amount: float, memo: str = ""
    ) -> Transaction:
        tx = Transaction(
            tx_id=str(uuid.uuid4()),
            sender=self.address,
            recipient=recipient,
            amount=amount,
            timestamp=time.time(),
            public_key=self.public_key.hex(),
            signature="",  # filled next
            memo=memo,
        )
        sig = pq_sign(self.secret_key, tx.message_to_sign())
        tx.signature = sig.hex()
        return tx


# ---------------------------------------------------------------------------
# Blockchain
# ---------------------------------------------------------------------------
class VexloreChain:
    def __init__(self):
        self.chain: List[Block] = []
        self.pending: List[Transaction] = []
        self.balances: Dict[str, float] = {}
        self._load_or_create()

    def _load_or_create(self) -> None:
        if CHAIN_FILE.exists():
            raw = json.loads(CHAIN_FILE.read_text())
            self.chain = [Block.from_dict(b) for b in raw["chain"]]
            self.balances = raw.get("balances", {})
            print(f"[+] Loaded chain with {len(self.chain)} blocks")
        else:
            self._create_genesis()

    def _create_genesis(self) -> None:
        print("[*] Creating Genesis block of Vexlore Quantumproof Chain ...")
        genesis_tx = Transaction(
            tx_id="genesis",
            sender="VEXLORE_NETWORK",
            recipient="VEXLORE_NETWORK",
            amount=0.0,
            timestamp=time.time(),
            public_key="",
            signature="",
            memo="Genesis of Vexlore – Quantumproof by design",
        )
        block = Block(
            index=0,
            timestamp=time.time(),
            transactions=[genesis_tx],
            previous_hash="0" * 64,
            miner="genesis",
        )
        block.hash = block.compute_hash()
        self.chain.append(block)
        self._save()
        print(f"[+] Genesis block created: {block.hash[:16]}...")

    def _save(self) -> None:
        data = {
            "name": CHAIN_NAME,
            "version": VERSION,
            "algo": "ML-DSA-44 (FIPS 204)",
            "chain": [b.to_dict() for b in self.chain],
            "balances": self.balances,
        }
        CHAIN_FILE.write_text(json.dumps(data, indent=2))

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, tx: Transaction) -> bool:
        if not tx.verify():
            print("[-] Invalid quantum signature – transaction rejected")
            return False
        # simple balance check (except faucet-style)
        sender_bal = self.balances.get(tx.sender, 0.0)
        if tx.sender != "VEXLORE_NETWORK" and sender_bal < tx.amount:
            print(f"[-] Insufficient balance: {sender_bal} < {tx.amount}")
            return False
        self.pending.append(tx)
        print(f"[+] Pending tx {tx.tx_id[:8]}... {tx.amount} VEX → {tx.recipient[:12]}...")
        return True

    def mine_pending(self, miner_address: str) -> Optional[Block]:
        if not self.pending:
            print("[-] No pending transactions to mine")
            return None

        # reward the miner
        reward = Transaction(
            tx_id=str(uuid.uuid4()),
            sender="VEXLORE_NETWORK",
            recipient=miner_address,
            amount=10.0,  # block reward
            timestamp=time.time(),
            public_key="",
            signature="",
            memo="Block reward",
        )
        txs = self.pending + [reward]

        block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            transactions=txs,
            previous_hash=self.last_block.hash,
            miner=miner_address,
        )
        print(f"[*] Mining block #{block.index} (difficulty {DIFFICULTY}) ...")
        start = time.time()
        block.mine(DIFFICULTY)
        elapsed = time.time() - start
        print(f"[+] Block mined in {elapsed:.2f}s  hash={block.hash}")

        # apply balances
        for tx in txs:
            if tx.sender != "VEXLORE_NETWORK":
                self.balances[tx.sender] = self.balances.get(tx.sender, 0.0) - tx.amount
            self.balances[tx.recipient] = self.balances.get(tx.recipient, 0.0) + tx.amount

        self.chain.append(block)
        self.pending = []
        self._save()
        return block

    def get_balance(self, address: str) -> float:
        return self.balances.get(address, 0.0)

    def is_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current.hash != current.compute_hash():
                return False
            if current.previous_hash != previous.hash:
                return False
            if not current.hash.startswith("0" * DIFFICULTY):
                return False
            for tx in current.transactions:
                if tx.sender != "VEXLORE_NETWORK" and not tx.verify():
                    return False
        return True

    def faucet(self, address: str, amount: float = 100.0) -> None:
        """Give free test tokens (only for demo)."""
        tx = Transaction(
            tx_id=str(uuid.uuid4()),
            sender="VEXLORE_NETWORK",
            recipient=address,
            amount=amount,
            timestamp=time.time(),
            public_key="",
            signature="",
            memo="Faucet drop",
        )
        self.pending.append(tx)
        print(f"[+] Faucet: {amount} VEX queued for {address}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def print_banner():
    print(
        r"""
 __     __        _                 
 \ \   / /____  _| | ___  _ __ ___  
  \ \ / / _ \ \/ / |/ _ \| '__/ _ \ 
   \ V /  __/>  <| | (_) | | |  __/ 
    \_/ \___/_/\_\_|\___/|_|  \___| 
                                    
  Quantumproof Chain  v0.1
  Post-quantum signatures: ML-DSA-44 (FIPS 204)
"""
    )


def main():
    print_banner()
    chain = VexloreChain()
    wallet = Wallet("alice")

    while True:
        print(
            """
Commands:
  1) New wallet          2) Show balance
  3) Faucet (get coins)  4) Send transaction
  5) Mine block          6) Show chain
  7) Validate chain      8) Quit
"""
        )
        choice = input("Vexlore> ").strip()

        if choice == "1":
            name = input("Wallet name: ").strip() or "bob"
            w = Wallet(name)
            print(f"Address: {w.address}")

        elif choice == "2":
            addr = input(f"Address [{wallet.address}]: ").strip() or wallet.address
            bal = chain.get_balance(addr)
            print(f"Balance of {addr}: {bal} VEX")

        elif choice == "3":
            amount = float(input("Amount [100]: ") or 100)
            chain.faucet(wallet.address, amount)
            print("Mine a block (option 5) to receive the coins.")

        elif choice == "4":
            recipient = input("Recipient address: ").strip()
            amount = float(input("Amount: "))
            memo = input("Memo (optional): ").strip()
            tx = wallet.create_transaction(recipient, amount, memo)
            if chain.add_transaction(tx):
                print("Transaction added to mempool. Mine a block to confirm.")

        elif choice == "5":
            block = chain.mine_pending(wallet.address)
            if block:
                print(f"New balance: {chain.get_balance(wallet.address)} VEX")

        elif choice == "6":
            print(f"\n=== {CHAIN_NAME} ({len(chain.chain)} blocks) ===")
            for b in chain.chain:
                print(f"\nBlock #{b.index}  {b.hash[:20]}...")
                print(f"  Prev : {b.previous_hash[:20]}...")
                print(f"  Nonce: {b.nonce}  Miner: {b.miner[:16]}...")
                for t in b.transactions:
                    print(f"    TX {t.tx_id[:8]}  {t.amount} VEX  {t.sender[:12]} → {t.recipient[:12]}")

        elif choice == "7":
            valid = chain.is_valid()
            print(f"Chain valid: {valid}")

        elif choice in ("8", "q", "quit", "exit"):
            print("Goodbye from Vexlore.")
            break

        else:
            print("Unknown command")


if __name__ == "__main__":
    main()
