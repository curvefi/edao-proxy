import os

import boa
from voting import vote, OWNERSHIP, CustomEnv, vote_test

from getpass import getpass
from eth_account import account

import json

RPC_URL = os.environ["RPC_URL"]
boa.fork(RPC_URL)
# boa.set_network_env(RPC_URL)
boa.env.eoa = "0x71F718D3e4d1449D1502A6A7595eb84eBcCB1683"

factory = boa.from_etherscan("0x98EE851a00abeE0d95D08cF4CA2BdCE32aeaAF7F",
                             name="TwocryptoFactory",
                             api_key=os.environ["ETHERSCAN_V2_TOKEN"])
edao = "0x467947EE34aF926cF1DCac093870f613C96B1E0c"
proxy = boa.load("contracts/TwoCryptoFactoryProxy.vy", OWNERSHIP.agent, edao)

def account_load(fname):
    path = os.path.expanduser(os.path.join("~", ".brownie", "accounts", fname + ".json"))
    with open(path, "r") as f:
        pkey = account.decode_keyfile_json(json.load(f), getpass())
        return account.Account.from_key(pkey)

def apy(rate):
    return 100 * ((1 + rate/10**18)**(365*24*60*60) - 1)


with vote(
    OWNERSHIP,
    "[twocrypto] Add emergency role to Twocrypto pools.",
    # live_env=CustomEnv(rpc=RPC_URL, account=account_load("curve")),
):
    factory.commit_transfer_ownership(proxy)
    assert factory.future_admin() == proxy.address

    with vote_test():
        with boa.env.prank(edao):
            proxy.accept_transfer_ownership(factory)
            assert factory.admin() == proxy.address

            pool = boa.from_etherscan("0x83f24023d15d835a213df24fd309c47dab5beb32",  # cbBTC
                                      name="TwocryptoFactory",
                                      api_key=os.environ["ETHERSCAN_V2_TOKEN"])

            # Turn off
            initial_parameters = [pool.mid_fee(), pool.out_fee(), pool.fee_gamma(), pool.allowed_extra_profit(), pool.adjustment_step(), pool.ma_time()]
            proxy.emergency_parameters(
                pool,
                10 ** 10,
                10 ** 10,
                2 ** 256 - 1,
                2 ** 256 - 1,
                2 ** 256 - 1,
                2 ** 256 - 1,
            )
            assert pool.mid_fee() == 10**10
            assert pool.out_fee() == 10**10
            new_parameters = [pool.mid_fee(), pool.out_fee(), pool.fee_gamma(), pool.allowed_extra_profit(),
                              pool.adjustment_step(), pool.ma_time()]
            assert initial_parameters[2:] == new_parameters[2:]

            # Turn on
            proxy.emergency_parameters(
                pool,
                *initial_parameters[:-1],
                2 ** 256 - 1,  # ma_time needs calculations
            )
            new_parameters = [pool.mid_fee(), pool.out_fee(), pool.fee_gamma(), pool.allowed_extra_profit(),
                              pool.adjustment_step(), pool.ma_time()]
            assert initial_parameters == new_parameters
