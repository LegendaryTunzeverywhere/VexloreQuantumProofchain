#!/usr/bin/env python3
"""Non-interactive demo of Vexlore Quantumproof Chain (v0.2 NETWORK)."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "dilithium_src"))
sys.path.insert(0, str(Path(__file__).parent))

from vexlore_chain import (
    VexloreChain,
    Wallet,
    NodeServer,
    print_banner,
    VERSION,
)


def main():
    print_banner()
    print(f"=== Running automatic demo (v{VERSION}) ===\n")

    chain = VexloreChain()
    alice = Wallet("alice")
    bob = Wallet("bob")

    print(f"\nAlice address : {alice.address}")
    print(f"Bob address   : {bob.address}")

    # Give Alice some coins
    chain.faucet(alice.address, 100)
    chain.mine_pending(alice.address)
    print(f"\nAlice balance after faucet+mine: {chain.get_balance(alice.address)} VEX")

    # Alice sends to Bob
    tx = alice.create_transaction(bob.address, 25.5, memo="Hello from quantum-safe Vexlore")
    chain.add_transaction(tx)
    chain.mine_pending(alice.address)

    print(f"\nAlice balance : {chain.get_balance(alice.address)} VEX")
    print(f"Bob balance   : {chain.get_balance(bob.address)} VEX")
    print(f"Chain valid   : {chain.is_valid()}")
    print(f"Total blocks  : {len(chain.chain)}")

    # ---- v0.2 network smoke test (single-node) ----
    print("\n--- Network smoke test ---")
    try:
        node = NodeServer(chain, port=5055)
        node.start()
        time.sleep(0.5)
        print(f"Node status URL : {node.self_url}/status")
        print(f"Peers file      : data/peers.json")
        print("HTTP API is live. Try:  curl http://127.0.0.1:5055/status")
        node.stop()
        print("[+] Node started and stopped cleanly")
    except OSError as e:
        print(f"[!] Could not bind demo port 5055: {e}")

    print("\nDemo finished successfully.")
    print("Run `python3 vexlore_chain.py` for the interactive CLI + multi-node networking.")


if __name__ == "__main__":
    main()