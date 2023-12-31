# The MIT License (MIT)
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

from typing import Dict, Optional

import requests

from .formatting import get_human_readable, millify
from .wallet_utils import *

GIGA = 1e9
U16_MAX = 65535
U64_MAX = 18446744073709551615


def version_checking(timeout: int = 15):
    try:
        cybertensor.logging.debug(
            f"Checking latest Cybertensor version at: {cybertensor.__pipaddress__}"
        )

        # TODO update when will be released
        response = requests.get(cybertensor.__pipaddress__, timeout=timeout)
        latest_version = response.json()["info"]["version"]
        version_split = latest_version.split(".")
        latest_version_as_int = (
            (100 * int(version_split[0]))
            + (10 * int(version_split[1]))
            + (1 * int(version_split[2]))
        )

        if latest_version_as_int > cybertensor.__version_as_int__:
            print(
                "\u001b[33mCybertensor Version: Current {}/Latest {}\nPlease update to the latest version at your earliest convenience. "
                "Run the following command to upgrade:\n\n\u001b[0mpython -m pip install --upgrade cybertensor".format(
                    cybertensor.__version__, latest_version
                )
            )

    except requests.exceptions.Timeout:
        cybertensor.logging.error("Version check failed due to timeout")
    except requests.exceptions.RequestException as e:
        cybertensor.logging.error(f"Version check failed due to request failure: {e}")


def U16_NORMALIZED_FLOAT(x: int) -> float:
    return float(x) / float(U16_MAX)


def U64_NORMALIZED_FLOAT(x: int) -> float:
    return float(x) / float(U64_MAX)


def get_explorer_root_url_by_network_from_map(
    network: str, network_map: Dict[str, str]
) -> Optional[str]:
    r"""
    Returns the explorer root url for the given network name from the given network map.

    Args:
        network(str): The network to get the explorer url for.
        network_map(Dict[str, str]): The network map to get the explorer url from.

    Returns:
        The explorer url for the given network.
        Or None if the network is not in the network map.
    """
    explorer_url: Optional[str] = None
    if network in network_map:
        explorer_url = network_map[network]

    return explorer_url


def get_explorer_url_for_network(
    network: str, tx_hash: str, network_map: Dict[str, str]
) -> Optional[str]:
    r"""
    Returns the explorer url for the given block hash and network.

    Args:
        network(str): The network to get the explorer url for.
        tx_hash(str): The transaction hash to get the explorer url for.
        network_map(Dict[str, str]): The network map to get the explorer url from.

    Returns:
        The explorer url for the given block hash and network.
        Or None if the network is not known.
    """

    explorer_url: Optional[str] = None
    # Will be None if the network is not known. i.e. not in network_map
    explorer_root_url: Optional[str] = get_explorer_root_url_by_network_from_map(
        network, network_map
    )

    if explorer_root_url is not None:
        # We are on a known network.
        # TODO add network in explorer_url
        explorer_url = f"{explorer_root_url}/network/bostrom/tx/{tx_hash}"

    return explorer_url
