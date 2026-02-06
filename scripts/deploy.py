import os

from eth_account import Account

import boa


CONTRACT_PATH = "contracts/TwoCryptoFactoryProxy.vy"

# Mainnet addresses (override via env)
DEFAULT_DAO = "0x40907540d8a6C65c637785e8f8B742ae6b0b9968"
DEFAULT_EMERGENCY = "0x467947EE34aF926cF1DCac093870f613C96B1E0c"
DEFAULT_FACTORY = "0x98ee851a00abee0d95d08cf4ca2bdce32aeaaf7f"


def _env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    if v is None or v.strip() == "":
        return default
    return v.strip()


def main() -> None:
    rpc_url = _env("RPC_URL", "https://ethereum-rpc.publicnode.com")
    private_key = _env("PRIVATE_KEY")
    if not private_key:
        raise ValueError("PRIVATE_KEY is required")

    dao = _env("DAO", DEFAULT_DAO)
    emergency = _env("EMERGENCY", DEFAULT_EMERGENCY)
    factory = _env("FACTORY", DEFAULT_FACTORY)

    if private_key.startswith("0x"):
        private_key = private_key[2:]

    deployer = Account.from_key(bytes.fromhex(private_key))
    print(f"RPC_URL: {rpc_url}")
    print(f"Deployer: {deployer.address}")
    print(f"DAO: {dao}")
    print(f"Emergency (eDAO): {emergency}")

    boa.set_network_env(rpc_url)
    boa.env.add_account(deployer)
    boa.env.eoa = deployer.address
    chain_id = boa.env.evm.patch.chain_id
    bal = boa.env.get_balance(deployer.address)
    print(f"Chain ID: {chain_id}")
    print(f"Balance: {bal / 1e18:.6f} ETH")

    proxy = boa.load(CONTRACT_PATH, dao, emergency, sender=deployer.address)
    print(f"Deployed TwoCryptoFactoryProxy at: {proxy.address}")

    # Print suggested calldata for DAO ownership transfer flow.
    # 1) DAO calls factory.commit_transfer_ownership(proxy)
    # 2) DAO calls proxy.execute(factory, factory.accept_transfer_ownership())
    #
    # This script does not attempt to perform these, since the DAO may be a multisig.
    try:
        abi = [
            {
                "type": "function",
                "name": "commit_transfer_ownership",
                "stateMutability": "nonpayable",
                "inputs": [{"name": "_addr", "type": "address"}],
                "outputs": [],
            },
            {
                "type": "function",
                "name": "accept_transfer_ownership",
                "stateMutability": "nonpayable",
                "inputs": [],
                "outputs": [],
            },
        ]
        factory_iface = boa.loads_abi(__import__("json").dumps(abi), name="Factory").at(
            factory, nowarn=True
        )
        commit_calldata = factory_iface.commit_transfer_ownership.prepare_calldata(proxy.address)
        accept_calldata = factory_iface.accept_transfer_ownership.prepare_calldata()
        execute_calldata = proxy.execute.prepare_calldata(factory, accept_calldata)

        print("\nOwnership transfer calldata (for DAO):")
        print(f"- factory.commit_transfer_ownership: 0x{commit_calldata.hex()}")
        print(f"- proxy.execute(factory, accept):   0x{execute_calldata.hex()}")
    except Exception as e:
        print(f"\nCould not build ownership transfer calldata: {e}")


if __name__ == "__main__":
    main()
