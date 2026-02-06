# pragma version 0.4.3

dao: public(address)
emergency: public(address)

interface IFactory:
    def accept_transfer_ownership(): nonpayable

interface ITwocrypto:
    def apply_new_parameters(
        _new_mid_fee: uint256,
        _new_out_fee: uint256,
        _new_fee_gamma: uint256,
        _new_allowed_extra_profit: uint256,
        _new_adjustment_step: uint256,
        _new_ma_time: uint256,
    ): nonpayable

MAX_CALLDATA_SIZE: constant(uint256) = 1024
MAX_OUTSIZE: constant(uint256) = 1024

MAX_LEN: constant(uint256) = 8

MAX_FEE: constant(uint256) = 100 * 10**8  # 100%
DEFAULT_FEE: constant(uint256) = 10 ** 8  # 1%


@deploy
def __init__(_dao: address, _emergency: address):
    self.dao = _dao
    self.emergency = _emergency

@internal
def _check_authorized():
    assert msg.sender in [self.dao, self.emergency], "Unauthorized"


@internal
def _check_dao():
    assert msg.sender == self.dao, "Only DAO"

@external
def emergency_parameters(
    _pool: ITwocrypto,
    _new_mid_fee: uint256,
    _new_out_fee: uint256,
    _new_fee_gamma: uint256,
    _new_allowed_extra_profit: uint256,
    _new_adjustment_step: uint256,
    _new_ma_time: uint256,
):
    self._check_authorized()

    extcall _pool.apply_new_parameters(
        _new_mid_fee,
        _new_out_fee,
        _new_fee_gamma,
        _new_allowed_extra_profit,
        _new_adjustment_step,
        _new_ma_time,
    )

@external
@payable
def execute(_target: address, _calldata: Bytes[MAX_CALLDATA_SIZE]) -> Bytes[MAX_OUTSIZE]:
    self._check_dao()

    return raw_call(
        _target,
        _calldata,
        value=msg.value,
        max_outsize=MAX_OUTSIZE
    )

@external
def set_emergency(_new_emergency: address):
    self._check_dao()

    self.emergency = _new_emergency

@external
def accept_transfer_ownership(_factory: IFactory):
    extcall _factory.accept_transfer_ownership()
