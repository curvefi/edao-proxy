# pragma version 0.4.3

dao: public(address)
emergency_dao: public(address)

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


@deploy
def __init__(_dao: address, _emergency_dao: address):
    self.dao = _dao
    self.emergency_dao = _emergency_dao

@internal
def _check_authorized():
    assert msg.sender in [self.dao, self.emergency_dao], "Unauthorized"


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
    """
    @notice Emergency parameters for a pool.
    @dev Only accessible by emergency DAO.
    @param _pool The pool to update.
    @param _new_mid_fee The new mid fee.
    @param _new_out_fee The new out fee.
    @param _new_fee_gamma The new fee gamma.
    @param _new_allowed_extra_profit The new allowed extra profit.
    @param _new_adjustment_step The new adjustment step.
    @param _new_ma_time The new ma time.
    """
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
def set_emergency_dao(_new_emergency_dao: address):
    """
    @notice Set the emergency DAO address.
    @dev Only accessible by DAO.
    @param _new_emergency_dao The new emergency DAO address.
    """
    self._check_dao()

    self.emergency_dao = _new_emergency_dao
