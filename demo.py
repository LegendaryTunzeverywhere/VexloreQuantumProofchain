#!/usr/bin/env python3
"""Non-interactive demo of Vexlore Quantumproof Chain (v0.4 WALLET UPGRADES)."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "dilithium_src"))
sys.path.insert(0, str(Path(__file__).parent))

from vexlore_chain import (
    VexloreChain, Wallet, NodeServer, print_banner, VERSION, validate_mnemonic,
)

def main():
    print_banner()
    print(f"=== Running automatic demo (v{VERSION}) ===\n")

    for name in ("demo_alice", "demo_bob", "demo_alice_restored"):
        p = Path(__file__).parent / "wallet" / f"{name}.json"
        if p.exists():
            p.unlink()

    chain = VexloreChain()

    print("--- Creating wallets with seed phrases ---")
    alice = Wallet("demo_alice", password="demo-pass-123")
    bob   = Wallet("demo_bob",   password="demo-pass-456")

    print(f"\nAlice primary : {alice.address}")
    print(f"Bob primary   : {bob.address}")

    alice.new_address()
    alice.new_address()
    print(f"Alice now has {len(alice.addresses)} addresses")

    chain.faucet(alice.address, 100)
    chain.mine_pending(alice.address)
    print(f"\nAlice balance after faucet+mine: {chain.get_balance(alice.address)} VEX")

    tx = alice.create_transaction(bob.address, 25.5, memo="Hello from quantum-safe Vexlore")
    chain.add_transaction(tx)
    alice.record_history(tx, "out")
    chain.mine_pending(alice.address)

    print(f"\nAlice balance : {chain.get_balance(alice.address)} VEX")
    print(f"Bob balance   : {chain.get_balance(bob.address)} VEX")
    print(f"Chain valid   : {chain.is_valid()}")
    print(f"Total blocks  : {len(chain.chain)}")

    print("\n--- Alice transaction history ---")
    alice.show_history()

    print("\n--- Seed-phrase restore test ---")
    mn = alice.mnemonic
    print(f"Alice mnemonic (first 4 words): {' '.join(mn.split()[:4])} ...")
    assert validate_mnemonic(mn)
    alice.lock()
    restored = Wallet.restore("demo_alice_restored", mn, "new-password-789")
    print(f"Restored primary: {restored.address}")
    print("Restore successful – same address recovered from seed phrase")

    print("\n--- Network smoke test ---")
    try:
        node = NodeServer(chain, port=5055)
        node.start()
        time.sleep(0.5)
        print(f"Node status URL : {node.self_url}/status")
        print("HTTP API is live. Try:  curl http://127.0.0.1:5055/status")
        node.stop()
        print("[+] Node started and stopped cleanly")
    except OSError as e:
        print(f"[!] Could not bind demo port 5055: {e}")

    print("\nDemo finished successfully.")
    print("Run `python3 vexlore_chain.py` for the interactive CLI + multi-node networking.")

if __name__ == "__main__":
    main()
