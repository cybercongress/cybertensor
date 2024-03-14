# The MIT License (MIT)
# Copyright © 2023 OpenTensor Foundation
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
import os
import sys
from typing import List, Dict, Optional

from rich.console import Text
from rich.prompt import Prompt
from rich.table import Table
from tqdm import tqdm

import cybertensor
from cybertensor import __console__ as console
from cybertensor.commands import defaults
from cybertensor.commands.utils import DelegatesDetails
from cybertensor.config import Config
from cybertensor.utils.balance import Balance
from cybertensor.wallet import Wallet
# from cybertensor.commands.identity import SetIdentityCommand


def _get_coldkey_wallets_for_path(path: str) -> List["Wallet"]:
    try:
        wallet_names = next(os.walk(os.path.expanduser(path)))[1]
        return [Wallet(path=path, name=name) for name in wallet_names]
    except StopIteration:
        # No wallet files found.
        wallets = []
    return wallets


# Uses rich console to pretty print a table of delegates.
def show_delegates(
    # TODO revisit
    config: "Config",
    delegates: List["cybertensor.DelegateInfo"],
    prev_delegates: Optional[List["cybertensor.DelegateInfo"]],
    width: Optional[int] = None,
):
    """
    Displays a formatted table of Cybertensor network delegates with detailed statistics
    to the console. The table is sorted by total stake in descending order and provides
    a snapshot of delegate performance and status, helping users make informed decisions
    for staking or nominating.

    This is a helper function that is called by the 'list_delegates' and 'my_delegates'
    and not intended to be used directly in user code unless specifically required.

    Parameters:
    - delegates (List[cybertensor.DelegateInfo]): A list of delegate information objects
      to be displayed.
    - prev_delegates (Optional[List[cybertensor.DelegateInfo]]): A list of delegate
      information objects from a previous state, used to calculate changes in stake.
      Defaults to None.
    - width (Optional[int]): The width of the console output table. Defaults to None,
      which will make the table expand to the maximum width of the console.

    The output table includes the following columns:
    - INDEX: The numerical index of the delegate.
    - DELEGATE: The name of the delegate.
    - ADDR: The truncated address of the delegate.
    - NOMINATORS: The number of nominators supporting the delegate.
    - DELEGATE STAKE(τ): The stake that is directly delegated to the delegate.
    - TOTAL STAKE(τ): The total stake held by the delegate, including nominators' stake.
    - CHANGE/(4h): The percentage change in the delegate's stake over the past 4 hours.
    - SUBNETS: A list of subnets the delegate is registered with.
    - VPERMIT: Validator permits held by the delegate for the subnets.
    - NOMINATOR/(24h)/kτ: The earnings per 1000 τ staked by nominators in the last 24 hours.
    - DELEGATE/(24h): The earnings of the delegate in the last 24 hours.
    - Desc: A brief description provided by the delegate.

    Usage:
    This function is typically used within the Cybertensor CLI to show current delegate
    options to users who are considering where to stake their tokens.

    Example usage:
    >>> show_delegates(current_delegates, previous_delegates, width=80)

    Note:
    This function is primarily for display purposes within a command-line interface and does
    not return any values. It relies on the 'rich' Python library to render the table in the
    console.
    """

    delegates.sort(key=lambda delegate: delegate.total_stake, reverse=True)
    prev_delegates_dict = {}
    if prev_delegates is not None:
        for prev_delegate in prev_delegates:
            prev_delegates_dict[prev_delegate.hotkey] = prev_delegate

    # TODO revisit
    # registered_delegate_info: Optional[
    #     Dict[str, DelegatesDetails]
    # ] = get_delegates_details(url=cybertensor.__delegates_details_url__)

    cwtensor = cybertensor.cwtensor(config=config)
    registered_delegate_info: Optional[
        Dict[str, DelegatesDetails]
    ] = cwtensor.get_delegates()

    if registered_delegate_info is None:
        console.print(
            ":warning:[yellow]Could not get delegate info from chain.[/yellow]"
        )
        registered_delegate_info = {}

    table = Table(show_footer=True, width=width, pad_edge=False, box=None, expand=True)
    table.add_column(
        "[overline white]INDEX",
        str(len(delegates)),
        footer_style="overline white",
        style="bold white",
    )
    table.add_column(
        "[overline white]DELEGATE",
        style="rgb(50,163,219)",
        no_wrap=True,
        justify="left",
    )
    table.add_column(
        "[overline white]ADDR",
        str(len(delegates)),
        footer_style="overline white",
        style="bold yellow",
    )
    table.add_column(
        "[overline white]NOMINATORS", justify="center", style="green", no_wrap=True
    )
    table.add_column(
        f"[overline white]DELEGATE STAKE({cwtensor.giga_token_symbol})", justify="right", no_wrap=True
    )
    table.add_column(
        f"[overline white]TOTAL STAKE({cwtensor.giga_token_symbol})",
        justify="right",
        style="green",
        no_wrap=True,
    )
    table.add_column("[overline white]CHANGE/(4h)", style="grey0", justify="center")
    table.add_column("[overline white]VPERMIT", justify="right", no_wrap=False)
    table.add_column("[overline white]TAKE", style="white", no_wrap=True)
    table.add_column(
        f"[overline white]NOMINATOR/(24h)/k{cwtensor.giga_token_symbol}", style="green", justify="center"
    )
    table.add_column("[overline white]DELEGATE/(24h)", style="green", justify="center")
    table.add_column("[overline white]Desc", style="rgb(50,163,219)")

    for i, delegate in enumerate(delegates):
        owner_stake = next(
            map(
                lambda x: x[1],  # get stake
                filter(
                    lambda x: x[0] == delegate.owner, delegate.nominators
                ),  # filter for owner
            ),
            Balance.from_boot(0),  # default to 0 if no owner stake.
        )
        if delegate.hotkey in registered_delegate_info:
            delegate_name = registered_delegate_info[delegate.hotkey].name
            delegate_url = registered_delegate_info[delegate.hotkey].url
            delegate_description = registered_delegate_info[
                delegate.hotkey
            ].description
        else:
            delegate_name = ""
            delegate_url = ""
            delegate_description = ""

        if delegate.hotkey in prev_delegates_dict:
            prev_stake = prev_delegates_dict[delegate.hotkey].total_stake
            if prev_stake == 0:
                rate_change_in_stake_str = "[green]100%[/green]"
            else:
                rate_change_in_stake = (
                    100
                    * (float(delegate.total_stake) - float(prev_stake))
                    / float(prev_stake)
                )
                if rate_change_in_stake > 0:
                    rate_change_in_stake_str = "[green]{:.2f}%[/green]".format(
                        rate_change_in_stake
                    )
                elif rate_change_in_stake < 0:
                    rate_change_in_stake_str = "[red]{:.2f}%[/red]".format(
                        rate_change_in_stake
                    )
                else:
                    rate_change_in_stake_str = "[grey0]0%[/grey0]"
        else:
            rate_change_in_stake_str = "[grey0]NA[/grey0]"

        table.add_row(
            str(i),
            Text(delegate_name, style=f"link {delegate_url}"),
            f"{delegate.hotkey[:16]}...{delegate.hotkey[-8:]}",
            # f"{delegate.hotkey}",
            str(len([nom for nom in delegate.nominators if nom[1].boot > 0])),
            f"{owner_stake!s:13.13}",
            f"{delegate.total_stake!s:13.13}",
            rate_change_in_stake_str,
            str(delegate.registrations),
            f"{delegate.take * 100:.1f}%",
            f"{Balance.from_gboot(delegate.total_daily_return.gboot * (1000 / (0.001 + delegate.total_stake.gboot)))!s:6.6}",
            f"{Balance.from_gboot(delegate.total_daily_return.gboot * (0.18)) !s:6.6}",
            str(delegate_description),
            end_section=True,
        )
    console.print(table)


class DelegateStakeCommand:
    """
    Executes the 'delegate' command, which stakes GBOOT to a specified delegate on the
    Cybertensor network. This action allocates the user's GBOOT to support a delegate,
    potentially earning staking rewards in return.

    Optional Arguments:
    - wallet.name: The name of the wallet to use for the command.
    - delegatekey: The address of the delegate to stake to.
    - amount: The amount of GBOOT to stake.
    - all: If specified, the command stakes all available GBOOT.

    The command interacts with the user to determine the delegate and the amount of GBOOT
    to be staked. If the '--all' flag is used, it delegates the entire available balance.

    Usage:
    The user must specify the delegate's address and the amount of GBOOT to stake. The
    function sends a transaction to the cwtensor network to delegate the specified amount
    to the chosen delegate. These values are prompted if not provided.

    Example usage:
    >>> ctcli delegate --delegatekey <ADDRESS> --amount <AMOUNT>
    >>> ctcli delegate --delegatekey <ADDRESS> --all

    Note:
    This command modifies the blockchain state and may incur transaction fees. It requires
    user confirmation and interaction, and is designed to be used within the Cybertensor CLI
    environment. The user should ensure the delegate's address and the amount to be staked
    are correct before executing the command.
    """

    @staticmethod
    def run(cli: "cybertensor.cli"):
        """Delegates stake to a chain delegate."""
        try:
            config = cli.config.copy()
            wallet = Wallet(config=config)
            cwtensor = cybertensor.cwtensor(config=config, log_verbose=False)
            cwtensor.delegate(
                wallet=wallet,
                delegate=config.get("delegatekey"),
                amount=config.get("amount"),
                wait_for_finalization=True,
                prompt=not config.no_prompt,
            )
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        delegate_stake_parser = parser.add_parser(
            "delegate", help="""Delegate Stake to an account."""
        )
        delegate_stake_parser.add_argument(
            "--delegatekey",
            "--delegate",
            dest="delegatekey",
            type=str,
            required=False,
            help="""The address of the chosen delegate""",
        )
        delegate_stake_parser.add_argument(
            "--all", dest="stake_all", action="store_true"
        )
        delegate_stake_parser.add_argument(
            "--amount", dest="amount", type=float, required=False
        )
        Wallet.add_args(delegate_stake_parser)
        cybertensor.cwtensor.add_args(delegate_stake_parser)

    @staticmethod
    def check_config(config: "Config"):
        if not config.get("delegatekey"):
            # Check for delegates.
            with console.status(":satellite: Loading delegates..."):
                cwtensor = cybertensor.cwtensor(config=config, log_verbose=False)
                delegates: List[cybertensor.DelegateInfo] = cwtensor.get_delegates()
                try:
                    prev_delegates = cwtensor.get_delegates(
                        max(0, cwtensor.block - 1200)
                    )
                except RuntimeError:
                    prev_delegates = None

            if prev_delegates is None:
                console.print(
                    ":warning: [yellow]Could not fetch delegates history[/yellow]"
                )

            if len(delegates) == 0:
                console.print(
                    f":cross_mark: [red]There are no delegates on {cwtensor.network}[/red]"
                )
                sys.exit(1)

            delegates.sort(key=lambda delegate: delegate.total_stake, reverse=True)
            show_delegates(config, delegates, prev_delegates=prev_delegates)
            delegate_index = Prompt.ask("Enter delegate index")
            config.delegatekey = str(delegates[int(delegate_index)].hotkey)
            console.print(
                "Selected: [yellow]{}[/yellow]".format(config.delegatekey)
            )

        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

        # Get amount.
        if not config.get("amount") and not config.get("stake_all"):
            amount = Prompt.ask(f"Enter {cwtensor.giga_token_symbol} amount to stake")
            try:
                config.amount = float(amount)
            except ValueError:
                console.print(
                    f":cross_mark: [red]Invalid {cwtensor.giga_token_symbol} amount[/red] "
                    f"[bold white]{amount}[/bold white]"
                )
                sys.exit()


class DelegateUnstakeCommand:
    """
    Executes the 'undelegate' command, allowing users to withdraw their staked GBOOT from
    a delegate on the Cybertensor network. This process is known as "undelegating" and it
    reverses the delegation process, freeing up the staked tokens.

    Optional Arguments:
    - wallet.name: The name of the wallet to use for the command.
    - delegatekey: The address of the delegate to undelegate from.
    - amount: The amount of GBOOT to undelegate.
    - all: If specified, the command undelegates all staked GBOOT from the delegate.

    The command prompts the user for the amount of GBOOT to undelegate and the address
    of the delegate from which to undelegate. If the '--all' flag is used, it will attempt
    to undelegate the entire staked amount from the specified delegate.

    Usage:
    The user must provide the delegate's address and the amount of GBOOT to undelegate.
    The function will then send a transaction to the Cybertensor network to process the
    undelegation.

    Example usage:
    >>> ctcli undelegate --delegatekey <ADDRESS> --amount <AMOUNT>
    >>> ctcli undelegate --delegatekey <ADDRESS> --all

    Note:
    This command can result in a change to the blockchain state and may incur transaction
    fees. It is interactive and requires confirmation from the user before proceeding. It
    should be used with care as undelegating can affect the delegate's total stake and
    potentially the user's staking rewards.
    """

    @staticmethod
    def run(cli: "cybertensor.cli"):
        """Undelegates stake from a chain delegate."""
        try:
            config = cli.config.copy()
            wallet = Wallet(config=config)
            cwtensor = cybertensor.cwtensor(config=config, log_verbose=False)
            cwtensor.undelegate(
                wallet=wallet,
                delegate=config.get("delegatekey"),
                amount=config.get("amount"),
                wait_for_finalization=True,
                prompt=not config.no_prompt,
            )
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")


    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        undelegate_stake_parser = parser.add_parser(
            "undelegate", help="""Undelegate Stake from an account."""
        )
        undelegate_stake_parser.add_argument(
            "--delegatekey",
            "--delegate",
            dest="delegatekey",
            type=str,
            required=False,
            help="""The address of the choosen delegate""",
        )
        undelegate_stake_parser.add_argument(
            "--all", dest="unstake_all", action="store_true"
        )
        undelegate_stake_parser.add_argument(
            "--amount", dest="amount", type=float, required=False
        )
        Wallet.add_args(undelegate_stake_parser)
        cybertensor.cwtensor.add_args(undelegate_stake_parser)

    @staticmethod
    def check_config(config: "Config"):
        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

        if not config.get("delegatekey"):
            # Check for delegates.
            with console.status(":satellite: Loading delegates..."):
                cwtensor = cybertensor.cwtensor(config=config, log_verbose=False)
                delegates: List[cybertensor.DelegateInfo] = cwtensor.get_delegates()
                try:
                    prev_delegates = cwtensor.get_delegates(
                        max(0, cwtensor.block - 1200)
                    )
                except RuntimeError:
                    prev_delegates = None

            if prev_delegates is None:
                console.print(
                    ":warning: [yellow]Could not fetch delegates history[/yellow]"
                )

            if len(delegates) == 0:
                console.print(
                    f":cross_mark: [red]There are no delegates on {cwtensor.network}[/red]"
                )
                sys.exit(1)

            delegates.sort(key=lambda delegate: delegate.total_stake, reverse=True)
            show_delegates(config, delegates, prev_delegates=prev_delegates)
            delegate_index = Prompt.ask("Enter delegate index")
            config.delegatekey = str(delegates[int(delegate_index)].hotkey)
            console.print(f"Selected: [yellow]{config.delegatekey}[/yellow]")

        # Get amount.
        if not config.get("amount") and not config.get("unstake_all"):
            amount = Prompt.ask(f"Enter {cwtensor.giga_token_symbol} amount to unstake")
            try:
                config.amount = float(amount)
            except ValueError:
                console.print(
                    f":cross_mark: [red]Invalid {cwtensor.giga_token_symbol} amount[/red] "
                    f"[bold white]{amount}[/bold white]"
                )
                sys.exit()


class ListDelegatesCommand:
    """
    Displays a formatted table of Cybertensor network delegates, providing a comprehensive
    overview of delegate statistics and information. This table helps users make informed
    decisions on which delegates to allocate their GBOOT stake.

    Optional Arguments:
    - wallet.name: The name of the wallet to use for the command.
    - cwtensor.network: The name of the network to use for the command.

    The table columns include:
    - INDEX: The delegate's index in the sorted list.
    - DELEGATE: The name of the delegate.
    - ADDR: The delegate's unique address (truncated for display).
    - NOMINATORS: The count of nominators backing the delegate.
    - DELEGATE STAKE(τ): The amount of delegate's own stake (not the GBOOT delegated from any nominators).
    - TOTAL STAKE(τ): The delegate's cumulative stake, including self-staked and nominators' stakes.
    - CHANGE/(4h): The percentage change in the delegate's stake over the last four hours.
    - SUBNETS: The subnets to which the delegate is registered.
    - VPERMIT: Indicates the subnets for which the delegate has validator permits.
    - NOMINATOR/(24h)/kτ: The earnings per 1000 τ staked by nominators in the last 24 hours.
    - DELEGATE/(24h): The total earnings of the delegate in the last 24 hours.
    - DESCRIPTION: A brief description of the delegate's purpose and operations.

    Sorting is done based on the 'TOTAL STAKE' column in descending order. Changes in stake
    are highlighted: increases in green and decreases in red. Entries with no previous data
    are marked with 'NA'. Each delegate's name is a hyperlink to their respective URL, if available.

    Example usage:
    >>> ctcli root list_delegates
    >>> ctcli root list_delegates --wallet.name my_wallet
    >>> ctcli root list_delegates --cwtensor.network space-pussy # can also be `test` or `local`

    Note:
    This function is part of the Cybertensor CLI tools and is intended for use within a console
    application. It prints directly to the console and does not return any value.
    """

    @staticmethod
    def run(cli: "cybertensor.cli"):
        r"""
        List all delegates on the network.
        """
        try:
            # TODO revisit
            # cli.config.cwtensor.network = "archive"
            # cli.config.cwtensor.chain_endpoint = "wss://archive.chain.opentensor.ai:443"
            cwtensor = cybertensor.cwtensor(config=cli.config, log_verbose=False)
            with console.status(":satellite: Loading delegates..."):
                # TODO added list, check get_deletates
                delegates: List[cybertensor.DelegateInfo] = cwtensor.get_delegates()
                try:
                    prev_delegates = cwtensor.get_delegates(max(0, cwtensor.block - 1200))
                except RuntimeError:
                    prev_delegates = None

            if prev_delegates is None:
                console.print(
                    ":warning: [yellow]Could not fetch delegates history[/yellow]"
                )

            show_delegates(
                cli.config,
                delegates,
                prev_delegates=prev_delegates,
                width=cli.config.get("width", None),
            )
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        list_delegates_parser = parser.add_parser(
            "list_delegates", help="""List all delegates on the network"""
        )
        cybertensor.cwtensor.add_args(list_delegates_parser)

    @staticmethod
    def check_config(config: "Config"):
        pass


class NominateCommand:
    """
    Executes the 'nominate' command, which facilitates a wallet to become a delegate
    on the Cybertensor network. This command handles the nomination process, including
    wallet unlocking and verification of the hotkey's current delegate status.

    The command performs several checks:
    - Verifies that the hotkey is not already a delegate to prevent redundant nominations.
    - Tries to nominate the wallet and reports success or failure.

    Upon success, the wallet's hotkey is registered as a delegate on the network.

    Optional Arguments:
    - wallet.name: The name of the wallet to use for the command.
    - wallet.hotkey: The name of the hotkey to use for the command.

    Usage:
    To run the command, the user must have a configured wallet with both hotkey and
    coldkey. If the wallet is not already nominated, this command will initiate the
    process.

    Example usage:
    >>> ctcli root nominate
    >>> ctcli root nominate --wallet.name my_wallet --wallet.hotkey my_hotkey

    Note:
    This function is intended to be used as a CLI command. It prints the outcome directly
    to the console and does not return any value. It should not be called programmatically
    in user code due to its interactive nature and side effects on the network state.
    """

    @staticmethod
    def run(cli: "cybertensor.cli"):
        r"""Nominate wallet."""
        try:
            wallet = Wallet(config=cli.config)
            cwtensor = cybertensor.cwtensor(config=cli.config)

            # Unlock the wallet.
            wallet.hotkey
            wallet.coldkey

            # Check if the hotkey is already a delegate.
            if cwtensor.is_hotkey_delegate(wallet.hotkey.address):
                console.print(
                    "Aborting: Hotkey {} is already a delegate.".format(
                        wallet.hotkey.address
                    )
                )
                return

            result: bool = cwtensor.nominate(wallet)
            if not result:
                console.print(
                    "Could not became a delegate on [white]{}[/white]".format(
                        cwtensor.network
                    )
                )
            else:
                # Check if we are a delegate.
                is_delegate: bool = cwtensor.is_hotkey_delegate(wallet.hotkey.address)
                if not is_delegate:
                    console.print(
                        "Could not became a delegate on [white]{}[/white]".format(
                            cwtensor.network
                        )
                    )
                    return
                console.print(
                    "Successfully became a delegate on [white]{}[/white]".format(
                        cwtensor.network
                    )
                )
            # # Prompt use to set identity on chain.
            # if not cli.config.no_prompt:
            #     do_set_identity = Prompt.ask(
            #         f"Subnetwork registered successfully. Would you like to set your identity? [y/n]",
            #         choices=["y", "n"],
            #     )
            #
            #     if do_set_identity.lower() == "y":
            #         cwtensor.close()
            #         config = cli.config.copy()
            #         SetIdentityCommand.check_config(config)
            #         cli.config = config
            #         SetIdentityCommand.run(cli)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")


    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        nominate_parser = parser.add_parser(
            "nominate", help="""Become a delegate on the network"""
        )
        Wallet.add_args(nominate_parser)
        cybertensor.cwtensor.add_args(nominate_parser)

    @staticmethod
    def check_config(config: "Config"):
        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

        if not config.is_set("wallet.hotkey") and not config.no_prompt:
            hotkey = Prompt.ask("Enter hotkey name", default=defaults.wallet.hotkey)
            config.wallet.hotkey = str(hotkey)


class MyDelegatesCommand:
    """
    Executes the 'my_delegates' command within the Cybertensor CLI, which retrieves and
    displays a table of delegated stakes from a user's wallet(s) to various delegates
    on the Cybertensor network. The command provides detailed insights into the user's
    staking activities and the performance of their chosen delegates.

    Optional Arguments:
    - wallet.name: The name of the wallet to use for the command.
    - all: If specified, the command aggregates information across all wallets.

    The table output includes the following columns:
    - Wallet: The name of the user's wallet.
    - OWNER: The name of the delegate's owner.
    - ADDR: The truncated address of the delegate.
    - Delegation: The amount of GBOOT staked by the user to the delegate.
    - τ/24h: The earnings from the delegate to the user over the past 24 hours.
    - NOMS: The number of nominators for the delegate.
    - OWNER STAKE(τ): The stake amount owned by the delegate.
    - TOTAL STAKE(τ): The total stake amount held by the delegate.
    - SUBNETS: The list of subnets the delegate is a part of.
    - VPERMIT: Validator permits held by the delegate for various subnets.
    - 24h/kτ: Earnings per 1000 GBOOT staked over the last 24 hours.
    - Desc: A description of the delegate.

    The command also sums and prints the total amount of GBOOT delegated across all wallets.

    Usage:
    The command can be run as part of the Cybertensor CLI suite of tools and requires
    no parameters if a single wallet is used. If multiple wallets are present, the
    --all flag can be specified to aggregate information across all wallets.

    Example usage:
    >>> ctcli root my_delegates
    >>> ctcli root my_delegates --all
    >>> ctcli root my_delegates --wallet.name my_wallet

    Note:
    This function is typically called by the CLI parser and is not intended to be used
    directly in user code.
    """

    @staticmethod
    def run(cli: "cybertensor.cli"):
        """Delegates stake to a chain delegate."""
        try:
            config = cli.config.copy()
            cwtensor = cybertensor.cwtensor(config=config, log_verbose=False)
            MyDelegatesCommand._run(cli, cwtensor)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    def _run(cli: "cybertensor.cli", cwtensor: "cybertensor.cwtensor"):
        """Delegates stake to a chain delegate."""
        config = cli.config.copy()
        if config.get("all", d=None) is True:
            wallets = _get_coldkey_wallets_for_path(config.wallet.path)
        else:
            wallets = [Wallet(config=config)]

        table = Table(show_footer=True, pad_edge=False, box=None, expand=True)
        table.add_column(
            "[overline white]Wallet", footer_style="overline white", style="bold white"
        )
        table.add_column(
            "[overline white]OWNER",
            style="rgb(50,163,219)",
            no_wrap=True,
            justify="left",
        )
        table.add_column(
            "[overline white]ADDR", footer_style="overline white", style="bold yellow"
        )
        table.add_column(
            "[overline green]Delegation",
            footer_style="overline green",
            style="bold green",
        )
        table.add_column(
            f"[overline green]{cwtensor.giga_token_symbol}/24h",
            footer_style="overline green",
            style="bold green",
        )
        table.add_column(
            "[overline white]NOMS", justify="center", style="green", no_wrap=True
        )
        table.add_column(
            f"[overline white]OWNER STAKE({cwtensor.giga_token_symbol})", justify="right", no_wrap=True
        )
        table.add_column(
            f"[overline white]TOTAL STAKE({cwtensor.giga_token_symbol})",
            justify="right",
            style="green",
            no_wrap=True,
        )
        table.add_column(
            "[overline white]SUBNETS", justify="right", style="white", no_wrap=True
        )
        table.add_column("[overline white]VPERMIT", justify="right", no_wrap=True)
        table.add_column(f"[overline white]24h/k{cwtensor.giga_token_symbol}", style="green", justify="center")
        table.add_column("[overline white]Desc", style="rgb(50,163,219)")
        total_delegated = 0

        for wallet in tqdm(wallets):
            if not wallet.coldkeypub_file.exists_on_device():
                continue
            delegates = cwtensor.get_delegated(
                delegatee=wallet.coldkeypub.address
            )

            my_delegates = {}  # hotkey, amount
            for delegate in delegates:
                for coldkey_addr, staked in delegate[0].nominators:
                    if (
                        coldkey_addr == wallet.coldkeypub.address
                        and staked.gboot > 0
                    ):
                        my_delegates[delegate[0].hotkey] = staked

            delegates.sort(key=lambda _delegate: _delegate[0].total_stake, reverse=True)
            total_delegated += sum(my_delegates.values())

            # TODO revisit
            # registered_delegate_info: Optional[
            #     DelegatesDetails
            # ] = get_delegates_details(url=cybertensor.__delegates_details_url__)

            registered_delegate_info: Optional[
                DelegatesDetails
            ] = cwtensor.get_delegates()

            if registered_delegate_info is None:
                console.print(
                    ":warning:[yellow]Could not get delegate info from chain.[/yellow]"
                )
                registered_delegate_info = {}

            for i, delegate in enumerate(delegates):
                owner_stake = next(
                    map(
                        lambda x: x[1],  # get stake
                        filter(
                            lambda x: x[0] == delegate[0].owner,
                            delegate[0].nominators,
                        ),  # filter for owner
                    ),
                    Balance.from_boot(0),  # default to 0 if no owner stake.
                )
                if delegate[0].hotkey in registered_delegate_info:
                    delegate_name = registered_delegate_info[
                        delegate[0].hotkey
                    ].name
                    delegate_url = registered_delegate_info[delegate[0].hotkey].url
                    delegate_description = registered_delegate_info[
                        delegate[0].hotkey
                    ].description
                else:
                    delegate_name = ""
                    delegate_url = ""
                    delegate_description = ""

                if delegate[0].hotkey in my_delegates:
                    table.add_row(
                        wallet.name,
                        Text(delegate_name, style=f"link {delegate_url}"),
                        f"{delegate[0].hotkey[:16]}...{delegate[0].hotkey[-8:]}",
                        f"{my_delegates[delegate[0].hotkey]!s:16.16}",
                        f"{delegate[0].total_daily_return.gboot * (my_delegates[delegate[0].hotkey] / delegate[0].total_stake.gboot)!s:6.6}",
                        str(len(delegate[0].nominators)),
                        f"{owner_stake!s:13.13}",
                        f"{delegate[0].total_stake!s:13.13}",
                        str(delegate[0].registrations),
                        str(
                            [
                                "*" if subnet in delegate[0].validator_permits else ""
                                for subnet in delegate[0].registrations
                            ]
                        ),
                        # f'{delegate.take * 100:.1f}%',s
                        f"{delegate[0].total_daily_return.gboot * (1000 / (0.001 + delegate[0].total_stake.gboot))!s:6.6}",
                        str(delegate_description),
                        # f'{delegate_profile.description:140.140}',
                    )

        console.print(table)
        console.print(f"Total delegated {cwtensor.giga_token_symbol}: {total_delegated}")

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        delegate_stake_parser = parser.add_parser(
            "my_delegates",
            help="""Show all delegates where I am delegating a positive amount of stake""",
        )
        delegate_stake_parser.add_argument(
            "--all",
            action="store_true",
            help="""Check all coldkey wallets.""",
            default=False,
        )
        Wallet.add_args(delegate_stake_parser)
        cybertensor.cwtensor.add_args(delegate_stake_parser)

    @staticmethod
    def check_config(config: "Config"):
        if (
            not config.get("all", d=None)
            and not config.is_set("wallet.name")
            and not config.no_prompt
        ):
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)
