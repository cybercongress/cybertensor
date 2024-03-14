# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
# Copyright © 2022 Opentensor Foundation
# Copyright © 2023 Opentensor Technologies Inc
# Copyright © 2024 cyber~Congress

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
from typing import Union, Optional

from cosmpy.aerial.client import Coin
from cosmpy.crypto.address import Address

from cybertensor import __chain_address_prefix__


def is_valid_cybertensor_address_or_public_key(
    address: Union[str, bytes, Address]
) -> bool:
    """
    Checks if the given address is a valid destination address.

    Args:
        address(Union[str, bytes, cosmpy.crypto.address.Address]): The address to check.

    Returns:
        True if the address is a valid destination address, False otherwise.
    """
    if address is not None:
        return is_valid_address(address)
    # TODO  add public key validation
    return False


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
        if address.startswith(__chain_address_prefix__):
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


def create_identity_dict(
    display: str = "",
    legal: str = "",
    web: str = "",
    riot: str = "",
    email: str = "",
    pgp_fingerprint: Optional[str] = None,
    image: str = "",
    info: str = "",
    twitter: str = "",
) -> dict:
    """
    Creates a dictionary with structure for identity extrinsic. Must fit within 64 bits.
    Args:
        display (str): String to be converted and stored under 'display'.
        legal (str): String to be converted and stored under 'legal'.
        web (str): String to be converted and stored under 'web'.
        riot (str): String to be converted and stored under 'riot'.
        email (str): String to be converted and stored under 'email'.
        pgp_fingerprint (str): String to be converted and stored under 'pgp_fingerprint'.
        image (str): String to be converted and stored under 'image'.
        info (str): String to be converted and stored under 'info'.
        twitter (str): String to be converted and stored under 'twitter'.
    Returns:
        dict: A dictionary with the specified structure and byte string conversions.
    Raises:
        ValueError: If pgp_fingerprint is not exactly 20 bytes long when encoded.
    """
    if pgp_fingerprint and len(pgp_fingerprint.encode()) != 20:
        raise ValueError("pgp_fingerprint must be exactly 20 bytes long when encoded")

    return {
        "info": {
            "additional": [[]],
            "display": {f"Raw{len(display.encode())}": display.encode()},
            "legal": {f"Raw{len(legal.encode())}": legal.encode()},
            "web": {f"Raw{len(web.encode())}": web.encode()},
            "riot": {f"Raw{len(riot.encode())}": riot.encode()},
            "email": {f"Raw{len(email.encode())}": email.encode()},
            "pgp_fingerprint": pgp_fingerprint.encode() if pgp_fingerprint else None,
            "image": {f"Raw{len(image.encode())}": image.encode()},
            "info": {f"Raw{len(info.encode())}": info.encode()},
            "twitter": {f"Raw{len(twitter.encode())}": twitter.encode()},
        }
    }


def decode_hex_identity_dict(info_dictionary):
    for key, value in info_dictionary.items():
        if isinstance(value, dict):
            item = list(value.values())[0]
            if isinstance(item, str) and item.startswith("0x"):
                try:
                    info_dictionary[key] = bytes.fromhex(item[2:]).decode()
                except UnicodeDecodeError:
                    print(f"Could not decode: {key}: {item}")
            else:
                info_dictionary[key] = item
    return info_dictionary
