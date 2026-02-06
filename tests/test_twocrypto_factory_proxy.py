import boa


DAO_MAINNET = "0x40907540d8a6C65c637785e8f8B742ae6b0b9968"
EDAO_MAINNET = "0x467947EE34aF926cF1DCac093870f613C96B1E0c"


def _deploy_system(dao: str | None = None, emergency: str | None = None):
    if dao is None:
        dao = boa.env.generate_address()
    if emergency is None:
        emergency = boa.env.generate_address()
    alice = boa.env.generate_address()

    factory = boa.load("contracts/mocks/MockTwocryptoFactory.vy", dao)
    proxy = boa.load("contracts/TwoCryptoFactoryProxy.vy", dao, emergency)

    pool_old = boa.load("contracts/mocks/MockTwocryptoPoolOld.vy", factory.address)
    pool_new = boa.load("contracts/mocks/MockTwocryptoPoolNew.vy", factory.address)

    return dao, emergency, alice, factory, proxy, pool_old, pool_new


def _transfer_factory_admin_to_proxy(dao: str, factory, proxy):
    # DAO (current admin) commits.
    with boa.env.prank(dao):
        factory.commit_transfer_ownership(proxy.address)

    # Proxy must accept; DAO triggers it via proxy.execute.
    calldata = factory.accept_transfer_ownership.prepare_calldata()
    with boa.env.prank(dao):
        proxy.execute(factory.address, calldata)

    assert factory.admin() == proxy.address


def test_emergency_cannot_execute():
    dao, emergency, _, factory, proxy, _, _ = _deploy_system()
    _transfer_factory_admin_to_proxy(dao, factory, proxy)

    calldata = factory.set_fee_receiver.prepare_calldata(boa.env.generate_address())
    with boa.reverts("Only DAO"):
        with boa.env.prank(emergency):
            proxy.execute(factory.address, calldata)


def test_dao_execute_admin_calls_on_factory():
    dao, _, alice, factory, proxy, _, _ = _deploy_system()
    _transfer_factory_admin_to_proxy(dao, factory, proxy)

    # Direct call from DAO must fail (factory admin is proxy now).
    with boa.reverts("admin only"):
        with boa.env.prank(dao):
            factory.set_fee_receiver(alice)

    # DAO can still perform admin actions via proxy.execute.
    calldata = factory.set_fee_receiver.prepare_calldata(alice)
    with boa.env.prank(dao):
        proxy.execute(factory.address, calldata)
    assert factory.fee_receiver() == alice


def test_emergency_parameters_full_control_old_and_new_pools():
    dao, emergency, _, factory, proxy, pool_old, pool_new = _deploy_system()

    # Before takeover, proxy is not factory admin so pool admin calls revert.
    with boa.reverts():
        with boa.env.prank(emergency):
            proxy.emergency_parameters(pool_old.address, 1_500_000, 2_500_000, 123, 456, 789, 1000)

    _transfer_factory_admin_to_proxy(dao, factory, proxy)

    with boa.env.prank(emergency):
        proxy.emergency_parameters(pool_old.address, 1_500_000, 2_500_000, 123, 456, 789, 1000)

    assert pool_old.mid_fee() == 1_500_000
    assert pool_old.out_fee() == 2_500_000
    assert pool_old.fee_gamma() == 123
    assert pool_old.allowed_extra_profit() == 456
    assert pool_old.adjustment_step() == 789
    assert pool_old.ma_time() == 1000

    with boa.env.prank(emergency):
        proxy.emergency_parameters(pool_new.address, 3_500_000, 4_500_000, 234, 567, 890, 1100)

    assert pool_new.mid_fee() == 3_500_000
    assert pool_new.out_fee() == 4_500_000
    assert pool_new.fee_gamma() == 234
    assert pool_new.allowed_extra_profit() == 567
    assert pool_new.adjustment_step() == 890
    assert pool_new.ma_time() == 1100
