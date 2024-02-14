# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
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

import argparse
import re
from typing import List, Optional, Dict

import numpy as np
import torch
from rich.prompt import Prompt
from rich.table import Table

import cybertensor
from . import defaults
from .utils import DelegatesDetails, check_netuid_set
from .. import __console__ as console
from ..config import Config
from ..wallet import Wallet


class RegisterSubnetworkCommand:
    """
    Executes the 'register_subnetwork' command to register a new subnetwork on the cybertensor network.
    This command facilitates the creation and registration of a subnetwork, which involves interaction with the user's
    wallet and the cybertensor cw-tensor. It ensures that the user has the necessary credentials and configurations
    to successfully register a new subnetwork.

    Usage:
    Upon invocation, the command performs several key steps to register a subnetwork:
    1. It copies the user's current configuration settings.
    2. It accesses the user's wallet using the provided configuration.
    3. It initializes the cybertensor cw-tensor object with the user's configuration.
    4. It then calls the `register_subnetwork` function of the cw-tensor object, passing the user's wallet and a prompt
    setting based on the user's configuration.

    If the user's configuration does not specify a wallet name and 'no_prompt' is not set, the command will prompt
    the user to enter a wallet name. This name is then used in the registration process.

    The command structure includes:
    - Copying the user's configuration.
    - Accessing and preparing the user's wallet.
    - Initializing the cybertensor cw-tensor.
    - Registering the subnetwork with the necessary credentials.

    Example usage:
    >>> ctcli subnets create

    Note:
    This command is intended for advanced users of the Cybertensor network who wish to contribute by adding new subnetworks.
    It requires a clear understanding of the network's functioning and the roles of subnetworks. Users should ensure
    that they have secured their wallet and are aware of the implications of adding a new subnetwork to the cybertensor
    ecosystem.
    """

    @staticmethod
    def run(cli):
        r"""Register a subnetwork"""
        config = cli.config.copy()
        wallet = Wallet(config=cli.config)
        cwtensor = cybertensor.cwtensor(config=config)
        # Call register command.
        cwtensor.register_subnetwork(
            wallet=wallet,
            prompt=not cli.config.no_prompt,
        )

    @classmethod
    def check_config(cls, config: "Config"):
        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser):
        parser = parser.add_parser(
            "create",
            help="""Create a new cybertensor subnetwork on this chain.""",
        )

        Wallet.add_args(parser)
        cybertensor.cwtensor.add_args(parser)

class SubnetLockCostCommand:
    """
    Executes the 'lock_cost' command to view the locking cost required for creating a new subnetwork on the Cybertensor network. This command is designed to provide users with the current cost of registering a new subnetwork, which is a critical piece of information for anyone considering expanding the network's infrastructure.

    The current implementation anneals the cost of creating a subnet over a period of two days. If the cost is unappealing currently, check back in a day or two to see if it has reached an amenble level.

    Usage:
    Upon invocation, the command performs the following operations:
    1. It copies the user's current Cybertensor configuration.
    2. It initializes the Cybertensor cwtensor object with this configuration.
    3. It then retrieves the subnet lock cost using the `get_subnet_burn_cost()` method from the cwtensor object.
    4. The cost is displayed to the user in a readable format, indicating the amount of cryptocurrency required to lock for registering a new subnetwork.

    In case of any errors during the process (e.g., network issues, configuration problems), the command will catch these exceptions and inform the user that it failed to retrieve the lock cost, along with the specific error encountered.

    The command structure includes:
    - Copying and using the user's configuration for Cybertensor.
    - Retrieving the current subnet lock cost from the Cybertensor network.
    - Displaying the cost in a user-friendly manner.

    Example usage:
    >>> ctcli subnets lock_cost

    Note:
    This command is particularly useful for users who are planning to contribute to the Cybertensor network by adding new subnetworks. Understanding the lock cost is essential for these users to make informed decisions about their potential contributions and investments in the network.
    """

    @staticmethod
    def run(cli):
        r"""View locking cost of creating a new subnetwork"""
        config = cli.config.copy()
        cwtensor = cybertensor.cwtensor(config=config)
        try:
            console.print(
                f"Subnet lock cost: [green]{cybertensor.utils.balance.Balance( cwtensor.get_subnet_burn_cost() )}[/green]"
            )
        except Exception as e:
            console.print(
                f"Subnet lock cost: [red]Failed to get subnet lock cost[/red]"
                f"Error: {e}"
            )

    @classmethod
    def check_config(cls, config: "Config"):
        pass

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser):
        parser = parser.add_parser(
            "lock_cost",
            help=""" Return the lock cost to register a subnet""",
        )

        cybertensor.cwtensor.add_args(parser)


class SubnetListCommand:
    """
    Executes the 'list' command to list all subnets and their detailed information on the Cybertensor network.
    This command is designed to provide users with comprehensive information about each subnet within the
    network, including its unique identifier (netuid), the number of neurons, maximum neuron capacity,
    emission rate, tempo, recycle register cost (burn), proof of work (PoW) difficulty, and the name or
 address of the subnet owner.

    Usage:
    Upon invocation, the command performs the following actions:
    1. It initializes the Cybertensor cwtensor object with the user's configuration.
    2. It retrieves a list of all subnets in the network along with their detailed information.
    3. The command compiles this data into a table format, displaying key information about each subnet.

    In addition to the basic subnet details, the command also fetches delegate information to provide the
    name of the subnet owner where available. If the owner's name is not available, the owner's
    address is displayed.

    The command structure includes:
    - Initializing the Cybertensor cwtensor and retrieving subnet information.
    - Calculating the total number of neurons across all subnets.
    - Constructing a table that includes columns for NETUID, N (current neurons), MAX_N (maximum neurons),
        EMISSION, TEMPO, BURN, POW (proof of work difficulty), and SUDO (owner's name or address).
    - Displaying the table with a footer that summarizes the total number of subnets and neurons.

    Example usage:
    >>> ctcli subnets list

    Note:
    This command is particularly useful for users seeking an overview of the Cybertensor network's structure
    and the distribution of its resources and ownership information for each subnet.
    """

    @staticmethod
    def run(cli):
        r"""List all subnet netuids in the network."""
        cwtensor = cybertensor.cwtensor(config=cli.config)
        subnets: List[cybertensor.SubnetInfo] = cwtensor.get_all_subnets_info()

        rows = []
        total_neurons = 0
        # TODO revisist
        # delegate_info: Optional[Dict[str, DelegatesDetails]] = get_delegates_details(
        #     url=cybertensor.__delegates_details_url__
        # )

        delegate_info: Optional[Dict[str, DelegatesDetails]] = cwtensor.get_delegates()

        for subnet in subnets:
            total_neurons += subnet.max_n
            rows.append(
                (
                    str(subnet.netuid),
                    str(subnet.subnetwork_n),
                    str(cybertensor.utils.formatting.millify(subnet.max_n)),
                    f"{subnet.emission_value / cybertensor.utils.GIGA * 100:0.2f}%",
                    str(subnet.tempo),
                    f"{subnet.burn!s:8.8}",
                    str(cybertensor.utils.formatting.millify(subnet.difficulty)),
                    # TODO revisit
                    # f"{delegate_info[subnet.owner_ss58].name if subnet.owner_ss58 in delegate_info else subnet.owner_ss58}",
                    f"{delegate_info[subnet.owner].owner if subnet.owner in delegate_info else subnet.owner}",
                    f"{subnet.metadata}",
                )
            )
        table = Table(
            show_footer=True,
            width=cli.config.get("width", None),
            pad_edge=True,
            box=None,
            show_edge=True,
        )
        table.title = "[white]Subnets - {}".format(cwtensor.network)
        table.add_column(
            "[overline white]NETUID",
            str(len(subnets)),
            footer_style="overline white",
            style="bold green",
            justify="center",
        )
        table.add_column(
            "[overline white]N",
            str(total_neurons),
            footer_style="overline white",
            style="green",
            justify="center",
        )
        table.add_column("[overline white]MAX_N", style="white", justify="center")
        table.add_column("[overline white]EMISSION", style="white", justify="center")
        table.add_column("[overline white]TEMPO", style="white", justify="center")
        table.add_column("[overline white]BURN", style="white", justify="center")
        table.add_column("[overline white]POW", style="white", justify="center")
        table.add_column("[overline white]SUDO", style="white")
        table.add_column("[overline white]METADATA", style="white")
        for row in rows:
            table.add_row(*row)
        console.print(table)

    @staticmethod
    def check_config(config: "Config"):
        pass

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        list_subnets_parser = parser.add_parser(
            "list", help="""List all subnets on the network"""
        )
        cybertensor.cwtensor.add_args(list_subnets_parser)


HYPERPARAMS = {
    "serving_rate_limit": "sudo_set_serving_rate_limit",
    "weights_version_key": "sudo_set_weights_version_key",
    "weights_set_rate_limit": "sudo_set_weights_set_rate_limit",
    "max_weight_limit": "sudo_set_max_weight_limit",
    "immunity_period": "sudo_set_immunity_period",
    "min_allowed_weights": "sudo_set_min_allowed_weights",
    "activity_cutoff": "sudo_set_activity_cutoff",
    "max_allowed_validators": "sudo_set_max_allowed_validators",
}


class SubnetSudoCommand:
    """
    Executes the 'set' command to set hyperparameters for a specific subnet on the Cybertensor network.
    This command allows subnet owners to modify various hyperparameters of theirs subnet, such as its tempo,
    emission rates, and other network-specific settings.

    Usage:
    The command first prompts the user to enter the hyperparameter they wish to change and its new value.
    It then uses the user's wallet and configuration settings to authenticate and send the hyperparameter update
    to the specified subnet.

    Example usage:
    >>> ctcli sudo set --netuid 1 --param immunity_period --value 5000

    Note:
    This command requires the user to specify the subnet identifier (netuid) and both the hyperparameter
    and its new value. It is intended for advanced users who are familiar with the network's functioning
    and the impact of changing these parameters.
    """

    @staticmethod
    def run(cli):
        r"""Set subnet hyperparameters."""
        config = cli.config.copy()
        wallet = Wallet(config=cli.config)
        cwtensor = cybertensor.cwtensor(config=config)
        print("\n")
        SubnetHyperparamsCommand.run(cli)
        if not config.is_set("param") and not config.no_prompt:
            param = Prompt.ask("Enter hyperparameter", choices=HYPERPARAMS)
            config.param = str(param)
        if not config.is_set("value") and not config.no_prompt:
            value = Prompt.ask("Enter new value")
            config.value = value

        cwtensor.set_hyperparameter(
            wallet,
            netuid=cli.config.netuid,
            parameter=config.param,
            value=config.value,
            prompt=not cli.config.no_prompt,
        )

    @staticmethod
    def check_config(config: "Config"):
        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

        if not config.is_set("netuid") and not config.no_prompt:
            check_netuid_set(config, cybertensor.cwtensor(config=config))

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        parser = parser.add_parser("set", help="""Set hyperparameters for a subnet""")
        parser.add_argument(
            "--netuid", dest="netuid", type=int, required=False, default=False
        )
        parser.add_argument("--param", dest="param", type=str, required=False)
        parser.add_argument("--value", dest="value", type=str, required=False)

        Wallet.add_args(parser)
        cybertensor.cwtensor.add_args(parser)


class SubnetHyperparamsCommand:
    """
    Executes the 'hyperparameters' command to view the current hyperparameters of a specific subnet on
    the Cybertensor network. This command is useful for users who wish to understand the configuration and
    operational parameters of a particular subnet.

    Usage:
    Upon invocation, the command fetches and displays a list of all hyperparameters for the specified subnet.
    These include settings like tempo, emission rates, and other critical network parameters that define
    the subnet's behavior.

    Example usage:
    >>> ctcli subnets hyperparameters --netuid 1

    Subnet Hyperparameters - NETUID: 1 - finney
    HYPERPARAMETER            VALUE
    rho                       10
    kappa                     32767
    immunity_period           7200
    min_allowed_weights       8
    max_weight_limit          455
    tempo                     99
    min_difficulty            1000000000000000000
    max_difficulty            1000000000000000000
    weights_version           2013
    weights_rate_limit        100
    adjustment_interval       112
    activity_cutoff           5000
    registration_allowed      True
    target_regs_per_interval  2
    min_burn                  1000000000
    max_burn                  100000000000
    bonds_moving_avg          900000
    max_regs_per_block        1

    Note:
    The user must specify the subnet identifier (netuid) for which they want to view the hyperparameters.
    This command is read-only and does not modify the network state or configurations.
    """

    @staticmethod
    def run(cli):
        r"""View hyperparameters of a subnetwork."""
        cwtensor = cybertensor.cwtensor(config=cli.config)
        subnet: cybertensor.SubnetHyperparameters = cwtensor.get_subnet_hyperparameters(
            cli.config.netuid
        )

        table = Table(
            show_footer=True,
            width=cli.config.get("width", None),
            pad_edge=True,
            box=None,
            show_edge=True,
        )
        table.title = "[white]Subnet Hyperparameters - NETUID: {} - {}".format(
            cli.config.netuid, cwtensor.network
        )
        table.add_column("[overline white]HYPERPARAMETER", style="bold white")
        table.add_column("[overline white]VALUE", style="green")

        for param in subnet.__dict__:
            table.add_row("  " + param, str(subnet.__dict__[param]))

        console.print(table)

    @staticmethod
    def check_config(config: "Config"):
        if not config.is_set("netuid") and not config.no_prompt:
            check_netuid_set(config, cybertensor.cwtensor(config=config))

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        parser = parser.add_parser(
            "hyperparameters", help="""View subnet hyperparameters"""
        )
        parser.add_argument(
            "--netuid", dest="netuid", type=int, required=False, default=False
        )
        cybertensor.cwtensor.add_args(parser)


class SubnetGetHyperparamsCommand:
    """
    Executes the 'get' command to retrieve the hyperparameters of a specific subnet on the Cybertensor network.
    This command is similar to the 'hyperparameters' command but may be used in different contexts within the CLI.

    Usage:
    The command connects to the Cybertensor network, queries the specified subnet, and returns a detailed list
    of all its hyperparameters. This includes crucial operational parameters that determine the subnet's
    performance and interaction within the network.

    Example usage:
    >>> ctcli sudo get --netuid 1

    Subnet Hyperparameters - NETUID: 1 - finney
    HYPERPARAMETER            VALUE
    rho                       10
    kappa                     32767
    immunity_period           7200
    min_allowed_weights       8
    max_weight_limit          455
    tempo                     99
    min_difficulty            1000000000000000000
    max_difficulty            1000000000000000000
    weights_version           2013
    weights_rate_limit        100
    adjustment_interval       112
    activity_cutoff           5000
    registration_allowed      True
    target_regs_per_interval  2
    min_burn                  1000000000
    max_burn                  100000000000
    bonds_moving_avg          900000
    max_regs_per_block        1

    Note:
    Users need to provide the netuid of the subnet whose hyperparameters they wish to view. This command is
    designed for informational purposes and does not alter any network settings or configurations.
    """

    @staticmethod
    def run(cli):
        r"""View hyperparameters of a subnetwork."""
        cwtensor = cybertensor.cwtensor(config=cli.config)
        subnet: cybertensor.SubnetHyperparameters = cwtensor.get_subnet_hyperparameters(
            cli.config.netuid
        )

        table = Table(
            show_footer=True,
            width=cli.config.get("width", None),
            pad_edge=True,
            box=None,
            show_edge=True,
        )
        table.title = "[white]Subnet Hyperparameters - NETUID: {} - {}".format(
            cli.config.netuid, cwtensor.network
        )
        table.add_column("[overline white]HYPERPARAMETER", style="white")
        table.add_column("[overline white]VALUE", style="green")

        for param in subnet.__dict__:
            table.add_row(param, str(subnet.__dict__[param]))

        console.print(table)

    @staticmethod
    def check_config(config: "Config"):
        if not config.is_set("netuid") and not config.no_prompt:
            check_netuid_set(config, cybertensor.cwtensor(config=config))

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        parser = parser.add_parser("get", help="""View subnet hyperparameters""")
        parser.add_argument(
            "--netuid", dest="netuid", type=int, required=False, default=False
        )
        cybertensor.cwtensor.add_args(parser)


class SubnetSetWeightsCommand:
    """
    Optional arguments:
    - --uids (str): A comma-separated list of uids for which weights are to be set.
    - --weights (str): Corresponding weights for the specified netuids, in comma-separated format.
    - --netuid (str): Corresponding subnet for which weights are to be set.

    Example usage:
    >>> ctcli subnet weights --uids 0,1,2 --weights 0.3,0.3,0.4
    """

    @staticmethod
    def run(cli):
        r"""Set weights for subnetwork."""
        wallet = Wallet(config=cli.config)
        cwtensor = cybertensor.cwtensor(config=cli.config)

        # Get values if not set.
        example_uids = range(3)
        if not cli.config.is_set("uids"):
            example = ", ".join(map(str, example_uids)) + " ..."
            cli.config.uids = Prompt.ask(f"Enter uids (e.g. {example})")

        if not cli.config.is_set("weights"):
            example = (
                ", ".join(
                    map(str, ["{:.2f}".format(float(1 / len(example_uids))) for _ in example_uids])
                )
                + " ..."
            )
            cli.config.weights = Prompt.ask(f"Enter weights (e.g. {example})")

        # Parse from string
        uids = torch.tensor(
            list(map(int, re.split(r"[ ,]+", cli.config.uids))), dtype=torch.long
        )
        weights = torch.tensor(
            list(map(float, re.split(r"[ ,]+", cli.config.weights))),
            dtype=torch.float32,
        )

        # Run the set weights operation.
        cwtensor.set_weights(
            wallet=wallet,
            netuid=cli.config.netuid,
            uids=uids,
            weights=weights,
            version_key=0,
            prompt=not cli.config.no_prompt,
            wait_for_finalization=True,
        )

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        parser = parser.add_parser("weights", help="""Set weights for subnet.""")
        parser.add_argument("--uids", dest="uids", type=str, required=False)
        parser.add_argument("--weights", dest="weights", type=str, required=False)
        parser.add_argument(
            "--netuid", dest="netuid", type=int, required=False, default=False
        )

        Wallet.add_args(parser)
        cybertensor.cwtensor.add_args(parser)

    @staticmethod
    def check_config(config: "Config"):
        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

        if not config.is_set("wallet.hotkey") and not config.no_prompt:
            hotkey = Prompt.ask("Enter hotkey name", default=defaults.wallet.hotkey)
            config.wallet.hotkey = str(hotkey)

        if not config.is_set("netuid") and not config.no_prompt:
            check_netuid_set(config, cybertensor.cwtensor(config=config))

class SubnetGetWeightsCommand:
    """
    Executes the 'get_weights' command to retrieve the weights set for the subnet network on the Cybertensor network.
    This command provides visibility into how operator responsibilities and rewards are distributed among
    various operators.

    Usage:
    The command outputs a table listing the weights assigned to each operator within the subnet.
    This information is crucial for understanding the current influence and reward distribution among the operators.

    Optional arguments:
    - None. The command fetches weight information based on the cwtensor configuration.

    Example usage:
    >>> ctcli subnet get_weights

                                            Subnet Operators Weights
    UIDS        0        1        2       3        4        5       8        9       11     13      18       19
    1    100.00%        -        -       -        -        -       -        -        -      -       -        -
    2          -   40.00%    5.00%  10.00%   10.00%   10.00%  10.00%    5.00%        -      -  10.00%        -
    3          -        -   25.00%       -   25.00%        -  25.00%        -        -      -  25.00%        -
    4          -        -    7.00%   7.00%   20.00%   20.00%  20.00%        -    6.00%      -  20.00%        -
    5          -   20.00%        -  10.00%   15.00%   15.00%  15.00%    5.00%        -      -  10.00%   10.00%
    6          -        -        -       -   10.00%   10.00%  25.00%   25.00%        -      -  30.00%        -
    7          -   60.00%        -       -   20.00%        -       -        -   20.00%      -       -        -
    8          -   49.35%        -   7.18%   13.59%   21.14%   1.53%    0.12%    7.06%  0.03%       -        -
    9    100.00%        -        -       -        -        -       -        -        -      -       -        -
    ...

    Note:
    This command is essential for users interested in the governance and operational dynamics of the Cybertensor network.
    It offers transparency into how network rewards and responsibilities are allocated across different operators.
    """

    @staticmethod
    def run(cli):
        r"""Get weights for root network."""
        cwtensor = cybertensor.cwtensor(config=cli.config)
        weights = cwtensor.weights(cli.config.netuid)

        table = Table(show_footer=False)
        table.title = "[white]Subnet Operators Weights"
        table.add_column(
            "[white]UIDS",
            header_style="overline white",
            footer_style="overline white",
            style="rgb(50,163,219)",
            no_wrap=True,
        )

        # TODO refactor netuids to uids, copy-pasted from root command code, need refactoring with attention to naming
        uid_to_weights = {}
        netuids = set()
        for matrix in weights:
            [uid, weights_data] = matrix

            if not len(weights_data):
                uid_to_weights[uid] = {}
                normalized_weights = []
            else:
                normalized_weights = np.array(weights_data)[:, 1] / max(
                    np.sum(weights_data, axis=0)[1], 1
                )

            for weight_data, normalized_weight in zip(weights_data, normalized_weights):
                [netuid, _] = weight_data
                netuids.add(netuid)
                if uid not in uid_to_weights:
                    uid_to_weights[uid] = {}

                uid_to_weights[uid][netuid] = normalized_weight

        for netuid in netuids:
            table.add_column(
                f"[white]{netuid}",
                header_style="overline white",
                footer_style="overline white",
                justify="right",
                style="green",
                no_wrap=True,
            )

        for uid in uid_to_weights:
            row = [str(uid)]

            uid_weights = uid_to_weights[uid]
            for netuid in netuids:
                if netuid in uid_weights:
                    normalized_weight = uid_weights[netuid]
                    row.append("{:0.2f}%".format(normalized_weight * 100))
                else:
                    row.append("-")
            table.add_row(*row)

        table.show_footer = True

        table.box = None
        table.pad_edge = False
        table.width = None
        console.print(table)

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        parser = parser.add_parser(
            "get_weights", help="""Get weights for subnet network."""
        )
        parser.add_argument(
            "--netuid", dest="netuid", type=int, required=False, default=False
        )

        Wallet.add_args(parser)
        cybertensor.cwtensor.add_args(parser)

    @staticmethod
    def check_config(config: "Config"):
        if not config.is_set("netuid") and not config.no_prompt:
            check_netuid_set(config, cybertensor.cwtensor(config=config))
