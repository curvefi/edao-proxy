# pragma version 0.4.3

"""Minimal factory mock with commit/accept ownership transfer."""


event TransferOwnership:
    old_admin: address
    new_admin: address


admin: public(address)
future_admin: public(address)
fee_receiver: public(address)


@deploy
def __init__(_admin: address):
    assert _admin != empty(address), "admin=0"
    self.admin = _admin


@external
def set_fee_receiver(_fee_receiver: address):
    assert msg.sender == self.admin, "admin only"
    self.fee_receiver = _fee_receiver


@external
def commit_transfer_ownership(_addr: address):
    assert msg.sender == self.admin, "admin only"
    self.future_admin = _addr


@external
def accept_transfer_ownership():
    assert msg.sender == self.future_admin, "future admin only"
    old_admin: address = self.admin
    self.admin = msg.sender
    log TransferOwnership(old_admin=old_admin, new_admin=msg.sender)
