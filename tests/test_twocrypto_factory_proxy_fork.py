import os

import boa
import pytest


DAO = "0x40907540d8a6C65c637785e8f8B742ae6b0b9968"
EDAO = "0x467947EE34aF926cF1DCac093870f613C96B1E0c"

FACTORY = "0x98ee851a00abee0d95d08cf4ca2bdce32aeaaf7f"
POOL = "0xD9FF8396554A0d18B2CFbeC53e1979b7ecCe8373"


def _rpc_url() -> str:
    return os.environ.get("MAINNET_RPC_URL", "https://ethereum-rpc.publicnode.com")


@pytest.mark.fork
def test_mainnet_fork_edao_cannot_then_can_after_proxy_takeover():
    api_key = os.environ.get("ETHERSCAN_API_KEY")
    assert api_key, "ETHERSCAN_API_KEY is required for fork test"

    # Fork mainnet. We allow forking even if previous tests dirtied the env.
    with boa.fork(_rpc_url(), allow_dirty=True):
        # Ensure impersonated addresses have balance for tx execution.
        boa.env.set_balance(DAO, 10**20)
        boa.env.set_balance(EDAO, 10**20)

        # Use Etherscan ABI so we can call factory/pool methods directly.
        with boa.set_etherscan(api_key=api_key, chain_id=1):
            factory = boa.from_etherscan(FACTORY)
            pool = boa.from_etherscan(POOL)

        assert factory.admin() == DAO

        # eDAO cannot change parameters directly (not factory admin).
        with boa.reverts():
            with boa.env.prank(EDAO):
                pool.apply_new_parameters(
                    pool.mid_fee() + 1,
                    pool.out_fee() + 1,
                    pool.fee_gamma(),
                    pool.allowed_extra_profit(),
                    pool.adjustment_step(),
                    pool.ma_time(),
                )

        # Deploy proxy (deployer doesn't matter; DAO/emergency are stored).
        deployer = boa.env.generate_address()
        boa.env.set_balance(deployer, 10**20)
        with boa.env.prank(deployer):
            proxy = boa.load("contracts/TwoCryptoFactoryProxy.vy", DAO, EDAO)

        # Before takeover, eDAO calling through proxy still fails (proxy not admin).
        with boa.reverts():
            with boa.env.prank(EDAO):
                proxy.emergency_parameters(
                    pool.address,
                    pool.mid_fee() + 1,
                    pool.out_fee() + 1,
                    pool.fee_gamma(),
                    pool.allowed_extra_profit(),
                    pool.adjustment_step(),
                    pool.ma_time(),
                )

        # Transfer factory admin to proxy.
        with boa.env.prank(DAO):
            factory.commit_transfer_ownership(proxy.address)

        accept_calldata = factory.accept_transfer_ownership.prepare_calldata()
        with boa.env.prank(DAO):
            proxy.execute(factory.address, accept_calldata)

        assert factory.admin() == proxy.address

        # Now eDAO can change *all* apply_new_parameters fields through the proxy.
        old_mid = pool.mid_fee()
        old_out = pool.out_fee()
        old_fee_gamma = pool.fee_gamma()
        old_allowed = pool.allowed_extra_profit()
        old_step = pool.adjustment_step()
        old_ma_seconds = pool.ma_time()

        new_mid = old_mid + 1
        new_out = max(old_out + 1, new_mid)
        new_fee_gamma = min(old_fee_gamma + 1, 10**18 - 1)
        new_allowed = min(old_allowed + 1, 10**18)
        new_step = min(old_step + 1, 10**18)

        # IMPORTANT: pool.apply_new_parameters expects `ma_exp_time` (seconds / ln(2)).
        # `pool.ma_time()` returns seconds, so we need to convert.
        # In Twocrypto pools, the view is approximately: ma_seconds = ma_exp_time * 694 // 1000.
        old_ma_exp_approx = (old_ma_seconds * 1000 + 693) // 694  # ceil(seconds / 0.694)
        new_ma_exp = min(old_ma_exp_approx + 1, 872541)
        assert new_ma_exp > 86
        expected_ma_seconds = new_ma_exp * 694 // 1000

        with boa.env.prank(EDAO):
            proxy.emergency_parameters(
                pool.address,
                new_mid,
                new_out,
                new_fee_gamma,
                new_allowed,
                new_step,
                new_ma_exp,
            )

        assert pool.mid_fee() == new_mid
        assert pool.out_fee() == new_out
        assert pool.fee_gamma() == new_fee_gamma
        assert pool.allowed_extra_profit() == new_allowed
        assert pool.adjustment_step() == new_step
        assert pool.ma_time() == expected_ma_seconds

        # eDAO still cannot use DAO-only execute.
        with boa.reverts("Only DAO"):
            with boa.env.prank(EDAO):
                proxy.execute(factory.address, accept_calldata)
