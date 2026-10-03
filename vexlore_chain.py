#!/usr/bin/env python3
"""
Vexlore Quantumproof Chain  v0.3 — BETTER CHAIN
A free educational post-quantum blockchain prototype.

Uses ML-DSA (FIPS 204 / Dilithium) for quantum-resistant signatures.
v0.3: adaptive difficulty, better mempool, bigger blocks, faster validation, atomic saves.

Not production-ready — for learning and experimentation only.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, asdict, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("[-] 'requests' package required:  pip install requests")
    sys.exit(1)

# Add pure-Python ML-DSA implementation
sys.path.insert(0, str(Path(__file__).parent / "dilithium_src"))
try:
    from dilithium_py.ml_dsa import ML_DSA_44  # type: ignore
except ImportError:
    print("[-] dilithium_src not found. Place the pure-Python ML-DSA package next to this file.")
    print("    Expected: dilithium_src/dilithium_py/ml_dsa.py")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants  (v0.3)
# ---------------------------------------------------------------------------
CHAIN_NAME = "Vexlore Quantumproof Chain"
VERSION = "0.3.0-better-chain"

# Mining / difficulty
INITIAL_DIFFICULTY = 3
TARGET_BLOCK_TIME = 20          # seconds we want between blocks
DIFFICULTY_ADJUST_EVERY = 5     # adjust every N blocks
MIN_DIFFICULTY = 2
MAX_DIFFICULTY = 6

# Block limits
MAX_TX_PER_BLOCK = 50           # bigger blocks support

# Network
DEFAULT_PORT = 5000
SYNC_INTERVAL = 15

DATA_DIR = Path(__file__).parent / "data"
CHAIN_FILE = DATA_DIR / "vexlore_chain.json"
PEERS_FILE = DATA_DIR / "peers.json"
WALLETS_DIR = Path(__file__).parent / "wallet"

DATA_DIR.mkdir(exist_ok=True)
WALLETS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Crypto helpers (post-quantum)
# ---------------------------------------------------------------------------
def pq_keygen() -> Tuple[bytes, bytes]:
    return ML_DSA_44.keygen()


def pq_sign(secret_key: bytes, message: bytes) -> bytes:
    return ML_DSA_44.sign(secret_key, message)


def pq_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    return ML_DSA_44.verify(public_key, message, signature)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def address_from_pubkey(pubkey: bytes) -> str:
    h = sha256(pubkey)
    return "VEX" + h[:20]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class Transaction:
    tx_id: str
    sender: str
    recipient: str
    amount: float
    timestamp: float
    public_key: str
    signature: str
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
    difficulty: int = INITIAL_DIFFICULTY
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
                "difficulty": self.difficulty,
                "nonce": self.nonce,
                "miner": self.miner,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(block_string.encode())

    def mine(self) -> None:
        target = "0" * self.difficulty
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
            "difficulty": self.difficulty,
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
            difficulty=d.get("difficulty", INITIAL_DIFFICULTY),
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
            signature="",
            memo=memo,
        )
        sig = pq_sign(self.secret_key, tx.message_to_sign())
        tx.signature = sig.hex()
        return tx


# ---------------------------------------------------------------------------
# Blockchain  (v0.3 improvements)
# ---------------------------------------------------------------------------
class VexloreChain:
    def __init__(self):
        self.chain: List[Block] = []
        self.pending: List[Transaction] = []   # mempool
        self.balances: Dict[str, float] = {}
        self.current_difficulty = INITIAL_DIFFICULTY
        self._load_or_create()

    def _load_or_create(self) -> None:
        if CHAIN_FILE.exists():
            try:
                raw = json.loads(CHAIN_FILE.read_text())
                self.chain = [Block.from_dict(b) for b in raw["chain"]]
                self.balances = raw.get("balances", {})
                self.current_difficulty = raw.get("difficulty", INITIAL_DIFFICULTY)
                print(f"[+] Loaded chain with {len(self.chain)} blocks (diff={self.current_difficulty})")
            except Exception as e:
                print(f"[!] Failed to load chain: {e}")
                self._create_genesis()
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
            difficulty=INITIAL_DIFFICULTY,
            miner="genesis",
        )
        block.hash = block.compute_hash()
        self.chain.append(block)
        self.current_difficulty = INITIAL_DIFFICULTY
        self._save()
        print(f"[+] Genesis block created: {block.hash[:16]}...")

    def _atomic_save(self, data: dict) -> None:
        """Safe write – never corrupts the file even if power is lost."""
        fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, CHAIN_FILE)  # atomic on most systems
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def _save(self) -> None:
        data = {
            "name": CHAIN_NAME,
            "version": VERSION,
            "algo": "ML-DSA-44 (FIPS 204)",
            "difficulty": self.current_difficulty,
            "chain": [b.to_dict() for b in self.chain],
            "balances": self.balances,
        }
        self._atomic_save(data)

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def _adjust_difficulty(self) -> int:
        """Adaptive difficulty – tries to keep block time near TARGET_BLOCK_TIME."""
        if len(self.chain) < DIFFICULTY_ADJUST_EVERY + 1:
            return self.current_difficulty

        # look at the last N blocks
        recent = self.chain[-DIFFICULTY_ADJUST_EVERY:]
        time_taken = recent[-1].timestamp - recent[0].timestamp
        expected = TARGET_BLOCK_TIME * (DIFFICULTY_ADJUST_EVERY - 1)

        new_diff = self.current_difficulty
        if time_taken < expected * 0.7:          # too fast → harder
            new_diff = min(MAX_DIFFICULTY, self.current_difficulty + 1)
        elif time_taken > expected * 1.4:        # too slow → easier
            new_diff = max(MIN_DIFFICULTY, self.current_difficulty - 1)

        if new_diff != self.current_difficulty:
            print(f"[*] Difficulty adjusted: {self.current_difficulty} → {new_diff}")
        return new_diff

    def add_transaction(self, tx: Transaction) -> bool:
        if not tx.verify() and tx.sender != "VEXLORE_NETWORK":
            print("[-] Invalid quantum signature – transaction rejected")
            return False

        sender_bal = self.balances.get(tx.sender, 0.0)
        if tx.sender != "VEXLORE_NETWORK" and sender_bal < tx.amount:
            print(f"[-] Insufficient balance: {sender_bal} < {tx.amount}")
            return False

        # dedup
        if any(p.tx_id == tx.tx_id for p in self.pending):
            return False

        # mempool size limit
        if len(self.pending) >= MAX_TX_PER_BLOCK * 3:
            print("[-] Mempool full – try mining first")
            return False

        self.pending.append(tx)
        print(f"[+] Pending tx {tx.tx_id[:8]}... {tx.amount} VEX → {tx.recipient[:12]}...  (mempool: {len(self.pending)})")
        return True

    def mine_pending(self, miner_address: str) -> Optional[Block]:
        if not self.pending:
            print("[-] No pending transactions to mine")
            return None

        # take up to MAX_TX_PER_BLOCK transactions
        txs_to_include = self.pending[:MAX_TX_PER_BLOCK]
        remaining = self.pending[MAX_TX_PER_BLOCK:]

        # reward
        reward = Transaction(
            tx_id=str(uuid.uuid4()),
            sender="VEXLORE_NETWORK",
            recipient=miner_address,
            amount=10.0,
            timestamp=time.time(),
            public_key="",
            signature="",
            memo="Block reward",
        )
        txs = txs_to_include + [reward]

        # decide difficulty for this block
        self.current_difficulty = self._adjust_difficulty()

        block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            transactions=txs,
            previous_hash=self.last_block.hash,
            difficulty=self.current_difficulty,
            miner=miner_address,
        )

        print(f"[*] Mining block #{block.index} (difficulty {block.difficulty}, {len(txs)-1} txs) ...")
        start = time.time()
        block.mine()
        elapsed = time.time() - start
        print(f"[+] Block mined in {elapsed:.2f}s  hash={block.hash}")

        # apply balances
        for tx in txs:
            if tx.sender != "VEXLORE_NETWORK":
                self.balances[tx.sender] = self.balances.get(tx.sender, 0.0) - tx.amount
            self.balances[tx.recipient] = self.balances.get(tx.recipient, 0.0) + tx.amount

        self.chain.append(block)
        self.pending = remaining   # keep the rest in mempool
        self._save()
        return block

    def get_balance(self, address: str) -> float:
        return self.balances.get(address, 0.0)

    def is_valid(self, chain: Optional[List[Block]] = None) -> bool:
        """Faster validation – early exits + only full check when needed."""
        blocks = chain if chain is not None else self.chain
        if not blocks:
            return False

        # quick genesis check
        if blocks[0].index != 0 or blocks[0].previous_hash != "0" * 64:
            return False

        for i in range(1, len(blocks)):
            current = blocks[i]
            previous = blocks[i - 1]

            # fast structural checks first
            if current.index != previous.index + 1:
                return False
            if current.previous_hash != previous.hash:
                return False
            if not current.hash.startswith("0" * current.difficulty):
                return False

            # expensive hash check
            if current.hash != current.compute_hash():
                return False

            # signature checks (skip network rewards)
            for tx in current.transactions:
                if tx.sender != "VEXLORE_NETWORK" and not tx.verify():
                    return False
        return True

    def faucet(self, address: str, amount: float = 100.0) -> None:
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
        print(f"[+] Faucet: {amount} VEX queued for {address}  (mempool: {len(self.pending)})")

    def replace_chain(self, new_blocks: List[Block]) -> bool:
        if len(new_blocks) <= len(self.chain):
            return False
        if not self.is_valid(new_blocks):
            print("[-] Received chain failed validation – ignored")
            return False
        print(f"[+] Adopting longer chain ({len(self.chain)} → {len(new_blocks)} blocks)")
        self.chain = new_blocks
        # rebuild balances
        self.balances = {}
        for block in self.chain:
            for tx in block.transactions:
                if tx.sender != "VEXLORE_NETWORK":
                    self.balances[tx.sender] = self.balances.get(tx.sender, 0.0) - tx.amount
                self.balances[tx.recipient] = self.balances.get(tx.recipient, 0.0) + tx.amount
        self.pending = []
        self.current_difficulty = self.chain[-1].difficulty
        self._save()
        return True

    def add_block_from_peer(self, block: Block) -> bool:
        if block.index != len(self.chain):
            return False
        if block.previous_hash != self.last_block.hash:
            return False
        if block.hash != block.compute_hash():
            return False
        if not block.hash.startswith("0" * block.difficulty):
            return False
        for tx in block.transactions:
            if tx.sender != "VEXLORE_NETWORK" and not tx.verify():
                return False

        for tx in block.transactions:
            if tx.sender != "VEXLORE_NETWORK":
                self.balances[tx.sender] = self.balances.get(tx.sender, 0.0) - tx.amount
            self.balances[tx.recipient] = self.balances.get(tx.recipient, 0.0) + tx.amount

        confirmed_ids = {t.tx_id for t in block.transactions}
        self.pending = [t for t in self.pending if t.tx_id not in confirmed_ids]

        self.chain.append(block)
        self.current_difficulty = block.difficulty
        self._save()
        print(f"[+] Accepted block #{block.index} from peer  hash={block.hash[:16]}...")
        return True


# ---------------------------------------------------------------------------
# Networking  (same as v0.2, small cleanups)
# ---------------------------------------------------------------------------
class PeerManager:
    def __init__(self, self_url: str = ""):
        self.self_url = self_url.rstrip("/")
        self.peers: Set[str] = set()
        self._load()

    def _load(self) -> None:
        if PEERS_FILE.exists():
            try:
                data = json.loads(PEERS_FILE.read_text())
                self.peers = set(data.get("peers", []))
            except Exception:
                self.peers = set()

    def _save(self) -> None:
        PEERS_FILE.write_text(
            json.dumps({"peers": sorted(self.peers), "updated": time.time()}, indent=2)
        )

    def add(self, url: str) -> bool:
        url = url.rstrip("/")
        if not url.startswith("http"):
            url = "http://" + url
        if url == self.self_url or url in self.peers:
            return False
        self.peers.add(url)
        self._save()
        print(f"[+] Peer added: {url}")
        return True

    def remove(self, url: str) -> bool:
        url = url.rstrip("/")
        if url in self.peers:
            self.peers.discard(url)
            self._save()
            print(f"[+] Peer removed: {url}")
            return True
        return False

    def list(self) -> List[str]:
        return sorted(self.peers)

    def broadcast_block(self, block: Block) -> None:
        payload = block.to_dict()
        for peer in list(self.peers):
            try:
                r = requests.post(f"{peer}/block", json=payload, timeout=5)
                if r.status_code == 200:
                    print(f"    → block sent to {peer}")
                else:
                    print(f"    → {peer} rejected block ({r.status_code})")
            except Exception as e:
                print(f"    → {peer} unreachable ({e.__class__.__name__})")

    def broadcast_tx(self, tx: Transaction) -> None:
        payload = tx.to_dict()
        for peer in list(self.peers):
            try:
                requests.post(f"{peer}/transaction", json=payload, timeout=5)
            except Exception:
                pass

    def fetch_chain(self, peer: str) -> Optional[List[Block]]:
        try:
            r = requests.get(f"{peer}/chain", timeout=8)
            if r.status_code != 200:
                return None
            data = r.json()
            return [Block.from_dict(b) for b in data.get("chain", [])]
        except Exception:
            return None

    def fetch_peers(self, peer: str) -> List[str]:
        try:
            r = requests.get(f"{peer}/peers", timeout=5)
            if r.status_code == 200:
                return r.json().get("peers", [])
        except Exception:
            pass
        return []


class NodeHTTPHandler(BaseHTTPRequestHandler):
    chain: VexloreChain
    peers: PeerManager

    def log_message(self, fmt: str, *args) -> None:
        print(f"  [HTTP] {self.address_string()} {fmt % args}")

    def _json_response(self, code: int, obj: Any) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Optional[Dict]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return None
        try:
            return json.loads(self.rfile.read(length))
        except Exception:
            return None

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"

        if path == "/":
            self._json_response(200, {
                "name": CHAIN_NAME,
                "version": VERSION,
                "blocks": len(self.chain.chain),
                "difficulty": self.chain.current_difficulty,
                "mempool": len(self.chain.pending),
                "peers": len(self.peers.peers),
            })
        elif path == "/chain":
            self._json_response(200, {
                "length": len(self.chain.chain),
                "chain": [b.to_dict() for b in self.chain.chain],
            })
        elif path == "/status":
            self._json_response(200, {
                "version": VERSION,
                "blocks": len(self.chain.chain),
                "difficulty": self.chain.current_difficulty,
                "last_hash": self.chain.last_block.hash,
                "mempool": len(self.chain.pending),
                "peers": self.peers.list(),
            })
        elif path == "/peers":
            self._json_response(200, {"peers": self.peers.list()})
        elif path == "/pending" or path == "/mempool":
            self._json_response(200, {
                "count": len(self.chain.pending),
                "pending": [t.to_dict() for t in self.chain.pending]
            })
        else:
            self._json_response(404, {"error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        data = self._read_json()

        if path == "/block":
            if not data:
                self._json_response(400, {"error": "no body"})
                return
            try:
                block = Block.from_dict(data)
            except Exception:
                self._json_response(400, {"error": "invalid block"})
                return
            ok = self.chain.add_block_from_peer(block)
            if ok:
                self.peers.broadcast_block(block)
                self._json_response(200, {"status": "accepted"})
            else:
                self._json_response(409, {"status": "rejected"})

        elif path == "/transaction":
            if not data:
                self._json_response(400, {"error": "no body"})
                return
            try:
                tx = Transaction.from_dict(data)
            except Exception:
                self._json_response(400, {"error": "invalid tx"})
                return
            ok = self.chain.add_transaction(tx)
            self._json_response(200 if ok else 409, {"status": "ok" if ok else "rejected"})

        elif path == "/peers":
            url = (data or {}).get("url", "")
            if url:
                self.peers.add(url)
                self._json_response(200, {"status": "added", "peers": self.peers.list()})
            else:
                self._json_response(400, {"error": "url required"})

        else:
            self._json_response(404, {"error": "not found"})


class NodeServer:
    def __init__(self, chain: VexloreChain, port: int = DEFAULT_PORT, host: str = "0.0.0.0"):
        self.chain = chain
        self.port = port
        self.host = host
        local_ip = self._guess_local_ip()
        self.self_url = f"http://{local_ip}:{port}"
        self.peers = PeerManager(self.self_url)
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._sync_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    @staticmethod
    def _guess_local_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def start(self) -> None:
        handler = type(
            "Handler",
            (NodeHTTPHandler,),
            {"chain": self.chain, "peers": self.peers},
        )
        self._server = HTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        print(f"[+] Node listening on http://{self.host}:{self.port}")
        print(f"    Self URL : {self.self_url}")

        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
        print(f"[+] Background sync every {SYNC_INTERVAL}s")

    def stop(self) -> None:
        self._stop.set()
        if self._server:
            self._server.shutdown()

    def _sync_loop(self) -> None:
        while not self._stop.is_set():
            self.sync_with_peers()
            self._stop.wait(SYNC_INTERVAL)

    def sync_with_peers(self) -> None:
        if not self.peers.peers:
            return
        best_chain: Optional[List[Block]] = None
        best_len = len(self.chain.chain)

        for peer in list(self.peers.peers):
            remote = self.peers.fetch_chain(peer)
            if remote and len(remote) > best_len and self.chain.is_valid(remote):
                best_chain = remote
                best_len = len(remote)

            for p in self.peers.fetch_peers(peer):
                self.peers.add(p)

            try:
                requests.post(f"{peer}/peers", json={"url": self.self_url}, timeout=4)
            except Exception:
                pass

        if best_chain:
            self.chain.replace_chain(best_chain)

    def add_peer(self, url: str) -> None:
        if self.peers.add(url):
            try:
                requests.post(f"{url.rstrip('/')}/peers", json={"url": self.self_url}, timeout=5)
            except Exception as e:
                print(f"    (handshake failed: {e})")
            self.sync_with_peers()


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
                                    
  Quantumproof Chain  v0.3  — BETTER CHAIN
  Adaptive difficulty • Bigger blocks • Safe saves
  Post-quantum signatures: ML-DSA-44 (FIPS 204)
"""
    )


def main():
    print_banner()
    chain = VexloreChain()
    wallet = Wallet("alice")
    node: Optional[NodeServer] = None

    try:
        node = NodeServer(chain, port=DEFAULT_PORT)
        node.start()
    except OSError as e:
        print(f"[!] Could not bind port {DEFAULT_PORT}: {e}")
        print("    Network features disabled until you free the port or change it.")
        node = None

    while True:
        print(
            f"""
Commands:
  1) New wallet          2) Show balance
  3) Faucet (get coins)  4) Send transaction
  5) Mine block          6) Show chain
  7) Validate chain      8) Quit

Network:
  9)  List peers         10) Add peer
  11) Remove peer        12) Sync now
  13) Node status        14) Start node (custom port)

Current: {len(chain.chain)} blocks | difficulty {chain.current_difficulty} | mempool {len(chain.pending)}
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
                if node:
                    node.peers.broadcast_tx(tx)

        elif choice == "5":
            block = chain.mine_pending(wallet.address)
            if block:
                print(f"New balance: {chain.get_balance(wallet.address)} VEX")
                if node:
                    print("[*] Broadcasting block to peers ...")
                    node.peers.broadcast_block(block)

        elif choice == "6":
            print(f"\n=== {CHAIN_NAME} ({len(chain.chain)} blocks) ===")
            for b in chain.chain:
                print(f"\nBlock #{b.index}  {b.hash[:20]}...  (diff={b.difficulty})")
                print(f"  Prev : {b.previous_hash[:20]}...")
                print(f"  Nonce: {b.nonce}  Miner: {b.miner[:16]}...")
                for t in b.transactions:
                    print(f"    TX {t.tx_id[:8]}  {t.amount} VEX  {t.sender[:12]} → {t.recipient[:12]}")

        elif choice == "7":
            start = time.time()
            valid = chain.is_valid()
            elapsed = time.time() - start
            print(f"Chain valid: {valid}  (checked in {elapsed:.3f}s)")

        elif choice in ("8", "q", "quit", "exit"):
            if node:
                node.stop()
            print("Goodbye from Vexlore.")
            break

        elif choice == "9":
            if not node:
                print("[-] Node not running")
                continue
            peers = node.peers.list()
            if not peers:
                print("No peers yet. Use option 10 to add one.")
            else:
                print(f"Known peers ({len(peers)}):")
                for p in peers:
                    print(f"  • {p}")

        elif choice == "10":
            if not node:
                print("[-] Node not running – start it first (option 14)")
                continue
            url = input("Peer URL (e.g. http://192.168.1.10:5000): ").strip()
            if url:
                node.add_peer(url)

        elif choice == "11":
            if not node:
                print("[-] Node not running")
                continue
            url = input("Peer URL to remove: ").strip()
            node.peers.remove(url)

        elif choice == "12":
            if not node:
                print("[-] Node not running")
                continue
            print("[*] Syncing with peers ...")
            node.sync_with_peers()
            print(f"[+] Local chain now has {len(chain.chain)} blocks")

        elif choice == "13":
            if not node:
                print("[-] Node not running")
                continue
            print(f"Self URL     : {node.self_url}")
            print(f"Blocks       : {len(chain.chain)}")
            print(f"Difficulty   : {chain.current_difficulty}")
            print(f"Last hash    : {chain.last_block.hash[:24]}...")
            print(f"Mempool      : {len(chain.pending)} txs")
            print(f"Peers        : {len(node.peers.peers)}")
            print(f"Version      : {VERSION}")

        elif choice == "14":
            if node:
                print(f"[!] Node already running on port {node.port}")
                continue
            try:
                port = int(input(f"Port [{DEFAULT_PORT}]: ").strip() or DEFAULT_PORT)
            except ValueError:
                print("Invalid port")
                continue
            try:
                node = NodeServer(chain, port=port)
                node.start()
            except OSError as e:
                print(f"[-] Could not start: {e}")
                node = None

        else:
            print("Unknown command")


if __name__ == "__main__":
    main()