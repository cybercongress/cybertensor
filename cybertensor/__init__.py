# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
# Copyright © 2022-2023 Opentensor Foundation
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

from pathlib import Path

# Install and apply nest asyncio to allow the async functions
# to run in a .ipynb
import nest_asyncio
from cosmpy.aerial.config import NetworkConfig
from rich.console import Console
from rich.traceback import install

nest_asyncio.apply()

# Cybertensor code and protocol version.
__version__ = "0.1.0"
version_split = __version__.split(".")
__version_as_int__ = (
    (100 * int(version_split[0]))
    + (10 * int(version_split[1]))
    + (1 * int(version_split[2]))
)
__new_signature_version__ = 360

# Rich console.
__console__ = Console()
__use_console__ = True

# Remove overdue locals in debug training.
install(show_locals=False)


def turn_console_off():
    global __use_console__
    global __console__
    from io import StringIO

    __use_console__ = False
    __console__ = Console(file=StringIO(), stderr=False)


def turn_console_on():
    global __use_console__
    global __console__
    __use_console__ = True
    __console__ = Console()


turn_console_off()


# Logging helpers.
def trace(on: bool = True):
    logging.set_trace(on)


def debug(on: bool = True):
    logging.set_debug(on)


# Substrate chain block time (seconds).
__blocktime__ = 6

# Pip address for versioning
__pipaddress__ = "https://pypi.org/pypi/cybertensor/json"

# Raw github url for delegates registry file
#  TODO add data to github
__delegates_details_url__: str = "https://raw.githubusercontent.com/cybercongress/cybertensor/main/public/delegates.json"

# Bostrom network address prefix
__chain_address_prefix__ = "bostrom"

__networks__ = ["local", "bostrom"]

__contracts__ = [
    "bostrom14hj2tavq8fpesdwxxcu44rty3hh90vhujrvcmstl4zr3txmfvw9sww4mxt",
    "bostrom14hj2tavq8fpesdwxxcu44rty3hh90vhujrvcmstl4zr3txmfvw9sww4mxt"
]

__local_network__ = NetworkConfig(
    chain_id="localbostrom",
    url="grpc+http://localhost:9090",
    fee_minimum_gas_price=0.1,
    fee_denomination="boot",
    staking_denomination="boot",
    faucet_url="",
)

__bostrom_network__ = NetworkConfig(
    chain_id="bostrom",
    url="grpc+http://localhost:9090",
    fee_minimum_gas_price=0.1,
    fee_denomination="boot",
    staking_denomination="boot",
    faucet_url="",
)

__contract_path__ = Path(__file__).home() / ".cybertensor/contract/cybernet.wasm"
__contract_schema_path__ = Path(__file__).home() / ".cybertensor/contract/schema"

__token__ = "boot"

__default_gas__ = 1_000_000
__default_transfer_gas__ = 100_000

__boot_symbol__: str = "BOOT"
__giga_boot_symbol__: str = "GBOOT"

# change to emoji here
# __boot_symbol__: str = chr(0x03C4)
# __oxygen_symbol__: str = chr(0x03C4)

# Block Explorers map network to explorer url
# TODO update explorer presets
__network_explorer_map__ = {
    "local": "https://cyb.ai",
    "bostrom": "https://cyb.ai",
    "space-pussy": "https://cyb.ai",
}

from .errors import *
from .config import *
from .keyfile import *
from .keypair import *
from .wallet import *
from .utils import *
from .utils.balance import Balance as Balance
from .chain_data import *
from .cwtensor import cwtensor as cwtensor
from .cli import cli as cli, COMMANDS as ALL_COMMANDS
from .ctlogging import logging as logging
from .metagraph import metagraph as metagraph
from .threadpool import PriorityThreadPoolExecutor as PriorityThreadPoolExecutor

from .synapse import *
from .stream import *
from .tensor import *
from .axon import axon as axon
from .dendrite import dendrite as dendrite

configs = [
    axon.config(),
    cybertensor.config(),
    PriorityThreadPoolExecutor.config(),
    wallet.config(),
    logging.config(),
]
defaults = config.merge_all(configs)
