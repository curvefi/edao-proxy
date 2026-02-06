# pragma version 0.4.3

"""New-pool-like mock (same admin surface as poolnew.vy)."""


interface Factory:
    def admin() -> address: view


factory: public(immutable(address))

mid_fee: public(uint256)
out_fee: public(uint256)
fee_gamma: public(uint256)

allowed_extra_profit: public(uint256)
adjustment_step: public(uint256)
ma_time: public(uint256)

ramping: public(bool)


MIN_FEE: constant(uint256) = 5 * 10**5
MAX_FEE: constant(uint256) = 10 * 10**9


@deploy
def __init__(_factory: address):
    assert _factory != empty(address), "factory=0"
    factory = _factory

    # start with different defaults vs old mock
    self.mid_fee = 3_000_000
    self.out_fee = 4_000_000
    self.fee_gamma = 444
    self.allowed_extra_profit = 555
    self.adjustment_step = 666
    self.ma_time = 777


@internal
@view
def _check_admin():
    assert msg.sender == staticcall Factory(factory).admin(), "only owner"


@external
def ramp_A_gamma():
    self._check_admin()
    self.ramping = True


@external
def stop_ramp_A_gamma():
    self._check_admin()
    self.ramping = False


@external
def apply_new_parameters(
    _new_mid_fee: uint256,
    _new_out_fee: uint256,
    _new_fee_gamma: uint256,
    _new_allowed_extra_profit: uint256,
    _new_adjustment_step: uint256,
    _new_ma_time: uint256,
):
    self._check_admin()

    new_out_fee: uint256 = _new_out_fee
    if new_out_fee < MAX_FEE + 1:
        assert new_out_fee > MIN_FEE - 1, "!fee"
    else:
        new_out_fee = self.out_fee

    new_mid_fee: uint256 = _new_mid_fee
    if new_mid_fee > MAX_FEE:
        new_mid_fee = self.mid_fee
    assert new_mid_fee <= new_out_fee, "!mid-fee"

    new_fee_gamma: uint256 = _new_fee_gamma
    if new_fee_gamma < 10**18:
        assert new_fee_gamma > 0, "!fee_gamma"
    else:
        new_fee_gamma = self.fee_gamma

    self.mid_fee = new_mid_fee
    self.out_fee = new_out_fee
    self.fee_gamma = new_fee_gamma

    if _new_allowed_extra_profit <= 10**18:
        self.allowed_extra_profit = _new_allowed_extra_profit

    if _new_adjustment_step <= 10**18:
        self.adjustment_step = _new_adjustment_step

    if _new_ma_time < 872542:
        assert _new_ma_time > 86, "MA<60/ln(2)"
        self.ma_time = _new_ma_time
