# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
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

import argparse
import sys
from copy import deepcopy

from rich.prompt import Prompt, Confirm

import cybertensor
from cybertensor import __console__ as console
from cybertensor.commands import defaults
from cybertensor.commands.utils import check_netuid_set, check_for_cuda_reg_config
from cybertensor.config import Config
from cybertensor.wallet import Wallet


class RegisterCommand:
    """
    Executes the 'register' command to register a neuron on the cybertensor network by recycling some GBOOT (the network's native token).
    This command is used to add a new neuron to a specified subnet within the network, contributing to the decentralization and robustness of cybertensor.

    Usage:
    Before registering, the command checks if the specified subnet exists and whether the user's balance is sufficient to cover the registration cost.
    The registration cost is determined by the current recycle amount for the specified subnet. If the balance is insufficient or the subnet does not exist,
    the command will exit with an appropriate error message.

    If the preconditions are met, and the user confirms the transaction (if 'no_prompt' is not set), the command proceeds to register the neuron by burning the required amount of GBOOT.

    The command structure includes:
    - Verification of subnet existence.
    - Checking the user's balance against the current recycle amount for the subnet.
    - User confirmation prompt for proceeding with registration.
    - Execution of the registration process.

    Columns Displayed in the Confirmation Prompt:
    - Balance: The current balance of the user's wallet in GBOOT.
    - Cost to Register: The required amount of GBOOT needed to register on the specified subnet.

    Example usage:
    >>> ctcli subnets register --netuid 1

    Note:
    This command is critical for users who wish to contribute a new neuron to the network. It requires careful consideration of the subnet selection and
    an understanding of the registration costs. Users should ensure their wallet is sufficiently funded before attempting to register a neuron.
    """

    @staticmethod
    def run(cli: "cybertensor.cli"):
        r"""Register neuron by recycling some GBOOT."""
        try:
            cwtensor = cybertensor.cwtensor(config=cli.config, log_verbose=False)
            RegisterCommand._run(cli, cwtensor)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def _run(cli: "cybertensor.cli", cwtensor: "cybertensor.cwtensor"):

        wallet = Wallet(config=cli.config)

        # Verify subnet exists
        if not cwtensor.subnet_exists(netuid=cli.config.netuid):
            console.print(
                f"[red]Subnet {cli.config.netuid} does not exist[/red]"
            )
            sys.exit(1)

        # Check current recycle amount
        current_recycle = cwtensor.recycle(netuid=cli.config.netuid)
        balance = cwtensor.get_balance(wallet.coldkeypub.address)

        # Check balance is sufficient
        if balance < current_recycle:
            console.print(
                f"[red]Insufficient balance {balance} to register neuron. Current recycle is {current_recycle}[/red]"
            )
            sys.exit(1)

        if not cli.config.no_prompt:
            if (
                Confirm.ask(
                    f"Your balance is: [bold green]{balance}[/bold green]\n"
                    f"The cost to register by recycle is [bold red]{current_recycle}[/bold red]\n"
                    f"Do you want to continue?",
                    default=False,
                )
                is False
            ):
                sys.exit(1)

        cwtensor.burned_register(
            wallet=wallet, netuid=cli.config.netuid, prompt=not cli.config.no_prompt
        )

    @classmethod
    def check_config(cls, config: "Config"):
        check_netuid_set(config, cwtensor=cybertensor.cwtensor(config=config, log_verbose=False))

        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

        if not config.is_set("wallet.hotkey") and not config.no_prompt:
            hotkey = Prompt.ask("Enter hotkey name", default=defaults.wallet.hotkey)
            config.wallet.hotkey = str(hotkey)

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser):
        register_parser = parser.add_parser(
            "register", help="""Register a wallet to a network."""
        )
        register_parser.add_argument(
            "--netuid",
            type=int,
            help="netuid for subnet to serve this neuron on",
            default=argparse.SUPPRESS,
        )

        Wallet.add_args(register_parser)
        cybertensor.cwtensor.add_args(register_parser)


class PowRegisterCommand:
    """
    Executes the 'pow_register' command to register a neuron on the cybertensor network using Proof of Work (PoW).
    This method is an alternative registration process that leverages computational work for securing a neuron's place on the network.

    Usage:
    The command starts by verifying the existence of the specified subnet. If the subnet does not exist, it terminates with an error message.
    On successful verification, the PoW registration process is initiated, which requires solving computational puzzles.

    Optional arguments:
    - --netuid (int): The netuid for the subnet on which to serve the neuron. Mandatory for specifying the target subnet.
    - --pow_register.num_processes (int): The number of processors to use for PoW registration. Defaults to the system's default setting.
    - --pow_register.update_interval (int): The number of nonces to process before checking for the next block during registration.
      Affects the frequency of update checks.
    - --pow_register.no_output_in_place (bool): When set, disables the output of registration statistics in place. Useful for cleaner logs.
    - --pow_register.verbose (bool): Enables verbose output of registration statistics for detailed information.
    - --pow_register.cuda.use_cuda (bool): Enables the use of CUDA for GPU-accelerated PoW calculations. Requires a CUDA-compatible GPU.
    - --pow_register.cuda.no_cuda (bool): Disables the use of CUDA, defaulting to CPU-based calculations.
    - --pow_register.cuda.dev_id (int): Specifies the CUDA device ID, useful for systems with multiple CUDA-compatible GPUs.
    - --pow_register.cuda.tpb (int): Sets the number of Threads Per Block for CUDA operations, affecting the GPU calculation dynamics.

    The command also supports additional wallet and cwtensor arguments, enabling further customization of the registration process.

    Example usage:
    >>> ctcli subnets pow_register --netuid 1 --pow_register.num_processes 4 --cuda.use_cuda

    Note:
    This command is suited for users with adequate computational resources to participate in PoW registration. It requires a sound understanding
    of the network's operations and PoW mechanics. Users should ensure their systems meet the necessary hardware and software requirements,
    particularly when opting for CUDA-based GPU acceleration.

    This command may be disabled according on the subnet owner's directive. For example, on netuid 1 this is permanently disabled.
    """

    @staticmethod
    def run(cli: "cybertensor.cli") -> None:
        r"""Register neuron."""
        try:
            cwtensor = cybertensor.cwtensor(config=cli.config, log_verbose=False)
            PowRegisterCommand._run(cli, cwtensor)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def _run(cli: "cybertensor.cli", cwtensor: "cybertensor.cwtensor"):

        wallet = Wallet(config=cli.config)

        # Verify subnet exists
        if not cwtensor.subnet_exists(netuid=cli.config.netuid):
            console.print(
                f"[red]Subnet {cli.config.netuid} does not exist[/red]"
            )
            sys.exit(1)

        cwtensor.register(
            wallet=wallet,
            netuid=cli.config.netuid,
            prompt=not cli.config.no_prompt,
            tpb=cli.config.pow_register.cuda.get("tpb", None),
            update_interval=cli.config.pow_register.get("update_interval", None),
            num_processes=cli.config.pow_register.get("num_processes", None),
            cuda=cli.config.pow_register.cuda.get(
                "use_cuda", defaults.pow_register.cuda.use_cuda
            ),
            dev_id=cli.config.pow_register.cuda.get("dev_id", None),
            output_in_place=cli.config.pow_register.get(
                "output_in_place", defaults.pow_register.output_in_place
            ),
            log_verbose=cli.config.pow_register.get(
                "verbose", defaults.pow_register.verbose
            ),
        )

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        register_parser = parser.add_parser(
            "pow_register", help="""Register a wallet to a network using PoW."""
        )
        register_parser.add_argument(
            "--netuid",
            type=int,
            help="netuid for subnet to serve this neuron on",
            default=argparse.SUPPRESS,
        )
        register_parser.add_argument(
            "--pow_register.num_processes",
            "-n",
            dest="pow_register.num_processes",
            help="Number of processors to use for POW registration",
            type=int,
            default=defaults.pow_register.num_processes,
        )
        register_parser.add_argument(
            "--pow_register.update_interval",
            "--pow_register.cuda.update_interval",
            "--cuda.update_interval",
            "-u",
            help="The number of nonces to process before checking for next block during registration",
            type=int,
            default=defaults.pow_register.update_interval,
        )
        register_parser.add_argument(
            "--pow_register.no_output_in_place",
            "--no_output_in_place",
            dest="pow_register.output_in_place",
            help="Whether to not ouput the registration statistics in-place. Set flag to disable output in-place.",
            action="store_false",
            required=False,
            default=defaults.pow_register.output_in_place,
        )
        register_parser.add_argument(
            "--pow_register.verbose",
            help="Whether to ouput the registration statistics verbosely.",
            action="store_true",
            required=False,
            default=defaults.pow_register.verbose,
        )

        ## Registration args for CUDA registration.
        register_parser.add_argument(
            "--pow_register.cuda.use_cuda",
            "--cuda",
            "--cuda.use_cuda",
            dest="pow_register.cuda.use_cuda",
            default=defaults.pow_register.cuda.use_cuda,
            help="""Set flag to use CUDA to register.""",
            action="store_true",
            required=False,
        )
        register_parser.add_argument(
            "--pow_register.cuda.no_cuda",
            "--no_cuda",
            "--cuda.no_cuda",
            dest="pow_register.cuda.use_cuda",
            default=not defaults.pow_register.cuda.use_cuda,
            help="""Set flag to not use CUDA for registration""",
            action="store_false",
            required=False,
        )

        register_parser.add_argument(
            "--pow_register.cuda.dev_id",
            "--cuda.dev_id",
            type=int,
            nargs="+",
            default=defaults.pow_register.cuda.dev_id,
            help="""Set the CUDA device id(s). Goes by the order of speed. (i.e. 0 is the fastest).""",
            required=False,
        )
        register_parser.add_argument(
            "--pow_register.cuda.tpb",
            "--cuda.tpb",
            type=int,
            default=defaults.pow_register.cuda.tpb,
            help="""Set the number of Threads Per Block for CUDA.""",
            required=False,
        )

        Wallet.add_args(register_parser)
        cybertensor.cwtensor.add_args(register_parser)

    @staticmethod
    def check_config(config: "Config"):
        # if (
        #     not config.is_set("cwtensor.network")
        #     and not config.no_prompt
        # ):
        #     config.cwtensor.network = Prompt.ask(
        #         "Enter cwtensor network",
        #         choices=cybertensor.__networks__,
        #         default=defaults.cwtensor.network,
        #     )
        #     _, network_config, contract_address = cybertensor.cwtensor.determine_chain_endpoint_and_network(
        #         config.cwtensor.network
        #     )
        #     config.cwtensor.network_config = network_config
        #     config.cwtensor.contract_address = contract_address

        check_netuid_set(config, cwtensor=cybertensor.cwtensor(config=config))  # , log_verbose=False)

        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

        if not config.is_set("wallet.hotkey") and not config.no_prompt:
            hotkey = Prompt.ask("Enter hotkey name", default=defaults.wallet.hotkey)
            config.wallet.hotkey = str(hotkey)

        if not config.no_prompt:
            check_for_cuda_reg_config(config)


class SwapHotkeyCommand:
    @staticmethod
    def run(cli: "cybertensor.cli"):
        r"""Swap your hotkey for all registered axons on the network."""
        try:
            cwtensor: "cybertensor.cwtensor" = cybertensor.cwtensor(
                config=cli.config, log_verbose=False
            )
            SwapHotkeyCommand._run(cli, cwtensor)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def _run(cli: "cybertensor.cli", cwtensor: "cybertensor.cwtensor"):
        r"""Swap your hotkey for all registered axons on the network."""
        wallet = cybertensor.wallet(config=cli.config)

        # This creates an unnecessary amount of extra data, but simplifies implementation.
        new_config = deepcopy(cli.config)
        new_config.wallet.hotkey = new_config.wallet.hotkey_b
        new_wallet = cybertensor.wallet(config=new_config)

        cwtensor.swap_hotkey(
            wallet=wallet,
            new_wallet=new_wallet,
            wait_for_finalization=False,
            prompt=False,
        )
        
    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        swap_hotkey_parser = parser.add_parser(
            "swap_hotkey", help="""Swap your associated hotkey."""
        )

        swap_hotkey_parser.add_argument(
            "--wallet.hotkey_b",
            type=str,
            default=defaults.wallet.hotkey,
            help="""Name of the new hotkey""",
            required=False,
        )

        cybertensor.wallet.add_args(swap_hotkey_parser)
        cybertensor.cwtensor.add_args(swap_hotkey_parser)

    @staticmethod
    def check_config(config: "cybertensor.config"):
        if (
            not config.is_set("cwtensor.network")
            and not config.is_set("cwtensor.chain_endpoint")
            and not config.no_prompt
        ):
            config.cwtensor.network = Prompt.ask(
                "Enter cwtensor network",
                choices=cybertensor.__networks__,
                default=defaults.cwtensor.network,
            )
            _, endpoint = cybertensor.cwtensor.determine_chain_endpoint_and_network(
                config.cwtensor.network
            )
            config.cwtensor.chain_endpoint = endpoint

        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

        if not config.is_set("wallet.hotkey") and not config.no_prompt:
            hotkey = Prompt.ask("Enter old hotkey name", default=defaults.wallet.hotkey)
            config.wallet.hotkey = str(hotkey)

        if not config.is_set("wallet.hotkey_b") and not config.no_prompt:
            hotkey = Prompt.ask("Enter new hotkey name", default=defaults.wallet.hotkey)
            config.wallet.hotkey_b = str(hotkey)
