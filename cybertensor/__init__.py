# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
# Copyright © 2022-2023 Opentensor Foundation
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

from typing import Optional, Union

# Install and apply nest asyncio to allow the async functions
# to run in a .ipynb
import nest_asyncio
from cosmpy.aerial.config import NetworkConfig
from rich.console import Console
from rich.traceback import install

nest_asyncio.apply()

# Cybertensor code and protocol version.
__version__ = "0.1.6"
version_split = __version__.split(".")
__version_as_int__ = (
    (100 * int(version_split[0]))
    + (10 * int(version_split[1]))
    + (1 * int(version_split[2]))
)

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


turn_console_on()


# Logging helpers.
def trace(on: bool = True):
    logging.set_trace(on)


def debug(on: bool = True):
    logging.set_debug(on)


class NetworkConfigCwTensor(NetworkConfig):
    def __init__(
        self,
        chain_id: str,
        fee_minimum_gas_price: Union[int, float],
        fee_denomination: str,
        staking_denomination: str,
        url: str,
        token: str,
        token_symbol: str,
        giga_token_symbol: str,
        network_explorer: str,
        address_prefix: str,
        contract_address: str,
        faucet_url: Optional[str] = None,
    ):
        super().__init__(
            chain_id,
            fee_minimum_gas_price,
            fee_denomination,
            staking_denomination,
            url,
            faucet_url,
        )
        self.token = token
        self.token_symbol = token_symbol
        self.giga_token_symbol = giga_token_symbol
        self.network_explorer = network_explorer
        self.address_prefix = address_prefix
        self.contract_address = contract_address


# Chain block time (seconds).
__blocktime__ = 6

# Pip address for versioning
__pipaddress__ = "https://pypi.org/pypi/cybertensor/json"

# Raw github url for delegates registry file
#  TODO add data to github
__delegates_details_url__: str = "https://raw.githubusercontent.com/cybercongress/cybertensor/main/public/delegates.json"

#  TODO move to NetworkConfigCwTensor
__chain_address_prefix__ = "pussy"
__boot_symbol__: str = "PUSSY"
__giga_boot_symbol__: str = "GPUSSY"

__networks__ = ["local", "bostrom", "space-pussy"]

__default_network__ = "space-pussy"

__local_network__ = NetworkConfigCwTensor(
    chain_id="localbostrom",
    url="grpc+http://localhost:9090",
    fee_minimum_gas_price=0.1,
    fee_denomination="boot",
    staking_denomination="boot",
    faucet_url="",
    token="boot",
    token_symbol="BOOT",
    giga_token_symbol="GBOOT",
    network_explorer="http://localhost:3000",
    address_prefix="bostrom",
    contract_address="bostrom14hj2tavq8fpesdwxxcu44rty3hh90vhujrvcmstl4zr3txmfvw9sww4mxt",
)

__bostrom_network__ = NetworkConfigCwTensor(
    chain_id="bostrom",
    url="grpc+http://grpc.bostrom.cybernode.ai:1443",
    fee_minimum_gas_price=0.01,
    fee_denomination="boot",
    staking_denomination="boot",
    faucet_url="",
    token="boot",
    token_symbol="BOOT",
    giga_token_symbol="GBOOT",
    network_explorer="https://cyb.ai",
    address_prefix="bostrom",
    contract_address="bostrom14hj2tavq8fpesdwxxcu44rty3hh90vhujrvcmstl4zr3txmfvw9sww4mxt",
)

__space_pussy_network__ = NetworkConfigCwTensor(
    chain_id="space-pussy",
    url="grpc+https://grpc.space-pussy.cybernode.ai:1443",
    fee_minimum_gas_price=0.01,
    fee_denomination="pussy",
    staking_denomination="pussy",
    faucet_url="",
    token="pussy",
    token_symbol="PUSSY",
    giga_token_symbol="GPUSSY",
    network_explorer="https://cyb.ai",
    address_prefix="pussy",
    contract_address="pussy1ddwq8rxgdsm27pvpxqdy2ep9enuen6t2yhrqujvj9qwl4dtukx0s8hpka9",
)

__contract_path__ = None
__contract_schema_path__ = "contract/schema"

__default_gas__ = None
__default_transfer_gas__ = 100_000

from cybertensor.errors import *
from cybertensor.keyfile import keyfile, serialized_keypair_to_keyfile_data
from cybertensor.keypair import Keypair
from cybertensor.wallet import Wallet
from cybertensor.utils import *
from cybertensor.utils.balance import Balance
from cybertensor.chain_data import AxonInfo, NeuronInfo, NeuronInfoLite, PrometheusInfo, StakeInfo, SubnetInfo, SubnetHyperparameters
from cybertensor.cwtensor import cwtensor
from cybertensor.cli import cli, COMMANDS as ALL_COMMANDS
from cybertensor.ctlogging import logging
from cybertensor.metagraph import metagraph
from cybertensor.threadpool import PriorityThreadPoolExecutor

from cybertensor.synapse import TerminalInfo, Synapse
from cybertensor.stream import StreamingSynapse
from cybertensor.tensor import tensor, Tensor
from cybertensor.axon import axon
from cybertensor.dendrite import dendrite
from cybertensor.config import Config
from cybertensor.mock import MockCwtensor, MockWallet
# from .subnets import SubnetsAPI

configs = [
    axon.config(),
    Config(),
    PriorityThreadPoolExecutor.config(),
    Wallet.config(),
    logging.config(),
    cwtensor.config(),
]
defaults = Config.merge_all(configs)
