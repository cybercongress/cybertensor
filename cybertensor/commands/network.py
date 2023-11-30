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

import time
import argparse
import cybertensor
from . import defaults
from rich.prompt import Prompt
from rich.table import Table
from typing import List, Optional, Dict
# from .utils import get_delegates_details, DelegatesDetails, check_netuid_set

console = cybertensor.__console__


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
    This command is intended for advanced users of the Bittensor network who wish to contribute by adding new subnetworks.
    It requires a clear understanding of the network's functioning and the roles of subnetworks. Users should ensure
    that they have secured their wallet and are aware of the implications of adding a new subnetwork to the cybertensor
    ecosystem.
    """

    @staticmethod
    def run(cli):
        r"""Register a subnetwork"""
        config = cli.config.copy()
        wallet = cybertensor.wallet(config=cli.config)
        cwtensor: cybertensor.cwtensor = cybertensor.cwtensor(config=config)
        # Call register command.
        cwtensor.register_subnetwork(
            wallet=wallet,
            prompt=not cli.config.no_prompt,
        )

    @classmethod
    def check_config(cls, config: "cybertensor.config"):
        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser):
        parser = parser.add_parser(
            "create",
            help="""Create a new cybertensor subnetwork on this chain.""",
        )

        cybertensor.wallet.add_args(parser)
        cybertensor.cwtensor.add_args(parser)