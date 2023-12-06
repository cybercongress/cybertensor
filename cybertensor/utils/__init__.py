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

from .wallet_utils import *
import cybertensor
import requests
from .formatting import get_human_readable, millify


GIGA = 1e9
U16_MAX = 65535
U64_MAX = 18446744073709551615

def version_checking(timeout: int = 15):
    try:
        cybertensor.logging.debug(
            f"Checking latest Cybertensor version at: {cybertensor.__pipaddress__}"
        )

        # TODO update when will be released
        # response = requests.get(cybertensor.__pipaddress__, timeout=timeout)
        # latest_version = response.json()["info"]["version"]
        # version_split = latest_version.split(".")
        # latest_version_as_int = (
        #     (100 * int(version_split[0]))
        #     + (10 * int(version_split[1]))
        #     + (1 * int(version_split[2]))
        # )
        #
        # if latest_version_as_int > cybertensor.__version_as_int__:
        #     print(
        #         "\u001b[33mCybertensor Version: Current {}/Latest {}\nPlease update to the latest version at your earliest convenience. "
        #         "Run the following command to upgrade:\n\n\u001b[0mpython -m pip install --upgrade cybertensor".format(
        #             cybertensor.__version__, latest_version
        #         )
        #     )

    except requests.exceptions.Timeout:
        cybertensor.logging.error("Version check failed due to timeout")
    except requests.exceptions.RequestException as e:
        cybertensor.logging.error(f"Version check failed due to request failure: {e}")

def U16_NORMALIZED_FLOAT(x: int) -> float:
    return float(x) / float(U16_MAX)


def U64_NORMALIZED_FLOAT(x: int) -> float:
    return float(x) / float(U64_MAX)