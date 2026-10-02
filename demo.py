#!/usr/bin/env python3
"""Non-interactive demo of Vexlore Quantumproof Chain."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "dilithium_src"))

from vexlore_chain import VexloreChain, Wallet, print_banner

def main():
    print_banner()
    print("=== Running automatic demo ===\n")

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
    print("\nDemo finished successfully. Run `python3 vexlore_chain.py` for the interactive CLI.")

if __name__ == "__main__":
    main()
