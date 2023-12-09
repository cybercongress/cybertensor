# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
# Copyright © 2022 Opentensor Foundation
# Copyright © 2023 Opentensor Technologies Inc
# Copyright © 2023 cyber~Congress

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import re
from typing import Union

from cosmpy.aerial.client import Coin
from cosmpy.crypto.address import Address

import cybertensor


def is_valid_cybertensor_address_or_public_key(address: Union[str, bytes, Address]) -> bool:
    """
    Checks if the given address is a valid destination address.

    Args:
        address(Union[str, bytes, cosmpy.crypto.address.Address]): The address to check.

    Returns:
        True if the address is a valid destination address, False otherwise.
    """

    # TODO
    return True


def is_valid_address(address: Union[str, Address]) -> bool:
    """
    Checks if the given address is a valid address.

    Args:
        address(str, cosmpy.crypto.address.Address): The address to check.

    Returns:
        True if the address is a valid address for Cybertensor, False otherwise.
    """
    try:
        Address(address)
        if address.startswith(cybertensor.__chain_address_prefix__):
            return True
    except RuntimeError:
        pass
    return False


def coin_from_str(string: str) -> Coin:
    """Creates a new :class:`cosmpy.aerial.client.Coin` from a coin-format string. Must match the format:
    ``10000boot`` (``int``-Coin)

    >>> int_coin = coin_from_str("10000boot")
    >>> int_coin.denom
    'boot'
    >>> int_coin.amount
    10000

    Args:
        string (str): string to convert

    Raises:
        ValueError: if string is in wrong format

    Returns:
        cosmpy.aerial.client.Coin: converted string
    """
    pattern = r"^(\-?[0-9]+(\.[0-9]+)?)([0-9a-zA-Z/]+)$"
    match = re.match(pattern, string)
    if match is None:
        raise ValueError(f"failed to parse Coin: {string}")
    else:
        return Coin(match.group(3), match.group(1))
