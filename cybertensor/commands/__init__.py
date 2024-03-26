# The MIT License (MIT)
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

from munch import Munch, munchify

defaults: Munch = munchify(
    {
        "netuid": 1,
        "cwtensor": {"network": "space-pussy", "_mock": False},
        "pow_register": {
            "num_processes": None,
            "update_interval": 50000,
            "output_in_place": True,
            "verbose": False,
            "cuda": {"dev_id": [0], "use_cuda": False, "tpb": 256},
        },
        "axon": {
            "port": 8091,
            "ip": "[::]",
            "external_port": None,
            "external_ip": None,
            "max_workers": 10,
            "maximum_concurrent_rpcs": 400,
        },
        "priority": {"max_workers": 5, "maxsize": 10},
        "prometheus": {"port": 7091, "level": "INFO"},
        "wallet": {
            "name": "default",
            "hotkey": "default",
            "path": "~/.cybertensor/wallets/",
        },
        "dataset": {
            "batch_size": 10,
            "block_size": 20,
            "num_workers": 0,
            "dataset_names": "default",
            "data_dir": "~/.cybertensor/data/",
            "save_dataset": False,
            "max_datasets": 3,
            "num_batches": 100,
        },
        "logging": {
            "debug": False,
            "trace": False,
            "record_log": False,
            "logging_dir": "~/.cybertensor/miners",
        },
    }
)

from cybertensor.commands.overview import OverviewCommand
from cybertensor.commands.stake import StakeCommand, StakeShow
from cybertensor.commands.unstake import UnStakeCommand
from cybertensor.commands.register import (
    PowRegisterCommand,
    RegisterCommand,
    # RunFaucetCommand,
    # SwapHotkeyCommand,
)
from cybertensor.commands.delegates import (
    NominateCommand,
    ListDelegatesCommand,
    DelegateStakeCommand,
    DelegateUnstakeCommand,
    MyDelegatesCommand,
    # GetWalletHistoryCommand,
)
from cybertensor.commands.wallets import (
    NewColdkeyCommand,
    NewHotkeyCommand,
    RegenColdkeyCommand,
    RegenColdkeypubCommand,
    RegenHotkeyCommand,
    UpdateWalletCommand,
    WalletCreateCommand,
    WalletBalanceCommand,
)
from cybertensor.commands.transfer import TransferCommand
from cybertensor.commands.inspect import InspectCommand
from cybertensor.commands.metagraph import MetagraphCommand
from cybertensor.commands.list import ListCommand
# from cybertensor.commands.misc import UpdateCommand, AutocompleteCommand
from cybertensor.commands.network import (
    RegisterSubnetworkCommand,
    SubnetLockCostCommand,
    SubnetListCommand,
    SubnetSudoCommand,
    SubnetHyperparamsCommand,
    SubnetGetHyperparamsCommand,
)
from cybertensor.commands.root import (
    RootRegisterCommand,
    RootList,
    RootSetWeightsCommand,
    RootGetWeightsCommand,
    # RootSetBoostCommand,
    # RootSetSlashCommand,
)
# from .identity import GetIdentityCommand, SetIdentityCommand
