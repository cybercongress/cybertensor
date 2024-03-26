# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
# Copyright © 2022 Opentensor Foundation
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

from rich.prompt import Prompt

import cybertensor
from cybertensor import __console__ as console
from cybertensor.commands import defaults
from cybertensor.config import Config
from cybertensor.wallet import Wallet


class TransferCommand:
    """
    Executes the 'transfer' command to transfer GBOOT tokens from one account to another on the cybertensor network.
    This command is used for transactions between different accounts, enabling users to send tokens to other
    participants on the network.

    Usage:
    The command requires specifying the destination address (public key) and the amount of GBOOT to be transferred.
    It checks for sufficient balance and prompts for confirmation before proceeding with the transaction.

    Optional arguments:
    - --dest (str): The destination address for the transfer. This can be in the form of an SS58 or ed2519 public key.
    - --amount (float): The amount of GBOOT tokens to transfer.

    The command displays the user's current balance before prompting for the amount to transfer, ensuring transparency
    and accuracy in the transaction.

    Example usage:
    >>> ctcli wallet transfer --dest bostrom1... --amount 100

    Note:
    This command is crucial for executing token transfers within the cybertensor network. Users should verify
    the destination address and amount before confirming the transaction to avoid errors or loss of funds.
    """

    @staticmethod
    def run(cli: "cybertensor.cli") -> None:
        r"""Transfer token of amount to destination."""
        try:
            cwtensor = cybertensor.cwtensor(config=cli.config, log_verbose=False)
            TransferCommand._run(cli, cwtensor)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def _run(cli: "cybertensor.cli", cwtensor: "cybertensor.cwtensor"):
        wallet = Wallet(config=cli.config)
        cwtensor.transfer(
            wallet=wallet,
            dest=cli.config.dest,
            amount=cli.config.amount,
            prompt=not cli.config.no_prompt,
        )

    @staticmethod
    def check_config(config: "Config"):
        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

        # Get destination.
        if not config.dest and not config.no_prompt:
            dest = Prompt.ask("Enter destination address")
            if not cybertensor.utils.is_valid_address(dest):
                sys.exit()
            else:
                config.dest = str(dest)

        # Get current balance and print to user.
        if not config.no_prompt:
            wallet = Wallet(config=config)
            cwtensor = cybertensor.cwtensor(config=config, log_verbose=False)
            with console.status(":satellite: Checking Balance..."):
                account_balance = cwtensor.get_balance(wallet.coldkeypub.address)
                console.print(
                    "Balance: [green]{}[/green]".format(account_balance)
                )

        # Get amount.
        if not config.get("amount"):
            if not config.no_prompt:
                amount = Prompt.ask(f"Enter {cwtensor.giga_token_symbol} amount to transfer")
                try:
                    config.amount = float(amount)
                    if config.amount <= 0:
                        raise ValueError("Zero or negative amount")
                except ValueError:
                    console.print(
                        f":cross_mark:[red] Invalid {cwtensor.giga_token_symbol} amount[/red] [bold white]{amount}[/bold white]"
                    )
                    sys.exit()
            else:
                console.print(
                    f":cross_mark:[red] Invalid {cybertensor.__giga_boot_symbol__} amount[/red] [bold white]{None}[/bold white]"
                )
                sys.exit(1)

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        transfer_parser = parser.add_parser(
            "transfer", help=f"""Transfer {cybertensor.__giga_boot_symbol__} between accounts."""
        )
        transfer_parser.add_argument("--dest", dest="dest", type=str, required=False)
        transfer_parser.add_argument(
            "--amount", dest="amount", type=float, required=False
        )

        Wallet.add_args(transfer_parser)
        cybertensor.cwtensor.add_args(transfer_parser)
