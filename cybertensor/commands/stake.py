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

from rich.prompt import Confirm

from cybertensor.commands.utils import get_hotkey_wallets_for_wallet
from cybertensor.config import Config
from cybertensor.utils.balance import Balance


class StakeCommand:
    """
    Executes the 'add' command to stake tokens to one or more hotkeys from a user's coldkey on the Cybertensor network.
    This command is used to allocate tokens to different hotkeys, securing their position and influence on the network.

    Usage:
    Users can specify the amount to stake, the hotkeys to stake to (either by name or address),
    and whether to stake to all hotkeys. The command checks for sufficient balance and hotkey registration
    before proceeding with the staking process.

    Optional arguments:
    - --all (bool): When set, stakes all available tokens from the coldkey.
    - --uid (int): The unique identifier of the neuron to which the stake is to be added.
    - --amount (float): The amount of GBOOT tokens to stake.
    - --max_stake (float): Sets the maximum amount of GBOOT to have staked in each hotkey.
    - --hotkeys (list): Specifies hotkeys by name or address to stake to.
    - --all_hotkeys (bool): When set, stakes to all hotkeys associated with the wallet, excluding any specified in --hotkeys.

    The command prompts for confirmation before executing the staking operation.

    Example usage:
    >>> ctcli stake add --amount 100 --wallet.name <my_wallet> --wallet.hotkey <my_hotkey>

    Note:
    This command is critical for users who wish to distribute their stakes among different neurons (hotkeys) on the network.
    It allows for a strategic allocation of tokens to enhance network participation and influence.
    """

    @staticmethod
    def run(cli: "cybertensor.cli") -> None:
        r"""Stake token of amount to hotkey(s)."""
        try:
            cwtensor = cybertensor.cwtensor(config=cli.config, log_verbose=False)
            StakeCommand._run(cli, cwtensor)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def _run(cli: "cybertensor.cli", cwtensor: "cybertensor.cwtensor"):

        config = cli.config.copy()
        wallet = Wallet(config=config)

        # Get the hotkey_names (if any) and the hotkeys.
        hotkeys_to_stake_to: List[Tuple[Optional[str], str]] = []
        if config.get("all_hotkeys"):
            # Stake to all hotkeys.
            all_hotkeys: List[Wallet] = get_hotkey_wallets_for_wallet(
                wallet=wallet
            )
            # Get the hotkeys to exclude. (d)efault to no exclusions.
            hotkeys_to_exclude: List[str] = cli.config.get("hotkeys", d=[])
            # Exclude hotkeys that are specified.
            hotkeys_to_stake_to = [
                (wallet.hotkey_str, wallet.hotkey.address)
                for wallet in all_hotkeys
                if wallet.hotkey_str not in hotkeys_to_exclude
            ]  # definitely wallets

        elif config.get("hotkeys"):
            # Stake to specific hotkeys.
            for hotkey_or_hotkey_name in config.get("hotkeys"):
                if cybertensor.utils.is_valid_address(hotkey_or_hotkey_name):
                    # If the hotkey is a valid address, we add it to the list.
                    hotkeys_to_stake_to.append((None, hotkey_or_hotkey_name))
                else:
                    # If the hotkey is not a valid address, we assume it is a hotkey name.
                    #  We then get the hotkey from the wallet and add it to the list.
                    wallet_ = Wallet(
                        config=config, hotkey=hotkey_or_hotkey_name
                    )
                    hotkeys_to_stake_to.append(
                        (wallet_.hotkey_str, wallet_.hotkey.address)
                    )
        elif config.wallet.get("hotkey"):
            # Only config.wallet.hotkey is specified.
            #  so we stake to that single hotkey.
            hotkey_or_name = config.wallet.get("hotkey")
            if cybertensor.utils.is_valid_address(hotkey_or_name):
                hotkeys_to_stake_to = [(None, hotkey_or_name)]
            else:
                # Hotkey is not a valid address, so we assume it is a hotkey name.
                wallet_ = Wallet(config=config, hotkey=hotkey_or_name)
                hotkeys_to_stake_to = [
                    (wallet_.hotkey_str, wallet_.hotkey.address)
                ]
        else:
            # Only config.wallet.hotkey is specified.
            #  so we stake to that single hotkey.
            assert config.wallet.hotkey is not None
            hotkeys_to_stake_to = [
                (None, Wallet(config=config).hotkey.address)
            ]

        # Get coldkey balance
        wallet_balance: Balance = cwtensor.get_balance(wallet.coldkeypub.address)
        final_hotkeys: List[Tuple[str, str]] = []
        final_amounts: List[Union[float, Balance]] = []
        for hotkey in tqdm(hotkeys_to_stake_to):
            hotkey: Tuple[Optional[str], str]  # (hotkey_name (or None), hotkey)
            if not cwtensor.is_hotkey_registered_any(hotkey=hotkey[1]):
                # Hotkey is not registered.
                if len(hotkeys_to_stake_to) == 1:
                    # Only one hotkey, error
                    console.print(
                        f"[red]Hotkey [bold]{hotkey[1]}[/bold] is not registered. Aborting.[/red]"
                    )
                    return None
                else:
                    # Otherwise, print warning and skip
                    console.print(
                        f"[yellow]Hotkey [bold]{hotkey[1]}[/bold] is not registered. Skipping.[/yellow]"
                    )
                    continue

            stake_amount_boot: float = config.get("amount")
            if config.get("max_stake"):
                # Get the current stake of the hotkey from this coldkey.
                hotkey_stake: Balance = cwtensor.get_stake_for_coldkey_and_hotkey(
                    hotkey=hotkey[1], coldkey=wallet.coldkeypub.address
                )
                stake_amount_boot: float = config.get("max_stake") - hotkey_stake.boot

                # If the max_stake is greater than the current wallet balance, stake the entire balance.
                stake_amount_boot: float = min(stake_amount_boot, wallet_balance.boot)
                if (
                    stake_amount_boot <= 0.00001
                ):  # Threshold because of fees, might create a loop otherwise
                    # Skip hotkey if max_stake is less than current stake.
                    continue
                wallet_balance = Balance.from_boot(wallet_balance.boot - stake_amount_boot)

                if wallet_balance.boot < 0:
                    # No more balance to stake.
                    break

            final_amounts.append(stake_amount_boot)
            final_hotkeys.append(hotkey)  # add both the name and the address.

        if len(final_hotkeys) == 0:
            # No hotkeys to stake to.
            console.print(
                "Not enough balance to stake to any hotkeys or max_stake is less than current stake."
            )
            return None

        # Ask to stake
        if not config.no_prompt:
            if not Confirm.ask(
                f"Do you want to stake to the following keys from {wallet.name}:\n"
                + "".join(
                    [
                        f"    [bold white]- {hotkey[0] + ':' if hotkey[0] else ''}{hotkey[1]}: "
                        f"{f'{amount} {cwtensor.giga_token_symbol}' if amount else 'All'}[/bold white]\n"
                        for hotkey, amount in zip(final_hotkeys, final_amounts)
                    ]
                )
            ):
                return None

        if len(final_hotkeys) == 1:
            # do regular stake
            return cwtensor.add_stake(
                wallet=wallet,
                hotkey=final_hotkeys[0][1],
                amount=None if config.get("stake_all") else final_amounts[0],
                wait_for_finalization=True,
                prompt=not config.no_prompt,
            )

        cwtensor.add_stake_multiple(
            wallet=wallet,
            hotkeys=[hotkey for _, hotkey in final_hotkeys],
            amounts=None if config.get("stake_all") else final_amounts,
            wait_for_finalization=True,
            prompt=False,
        )

    @classmethod
    def check_config(cls, config: "Config"):

        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

        if (
            not config.is_set("wallet.hotkey")
            and not config.no_prompt
            and not config.wallet.get("all_hotkeys")
            and not config.wallet.get("hotkeys")
        ):
            hotkey = Prompt.ask("Enter hotkey name", default=defaults.wallet.hotkey)
            config.wallet.hotkey = str(hotkey)

        # Get amount.
        if (
            not config.get("amount")
            and not config.get("stake_all")
            and not config.get("max_stake")
        ):
            amount = Prompt.ask(f"Enter {cybertensor.__giga_boot_symbol__} amount to stake")
            try:
                config.amount = float(amount)
            except ValueError:
                console.print(
                    f":cross_mark:[red]Invalid {cybertensor.__giga_boot_symbol__} amount[/red] "
                    f"[bold white]{amount}[/bold white]"
                )
                sys.exit()

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser):
        stake_parser = parser.add_parser(
            "add", help="""Add stake to your hotkey accounts from your coldkey."""
        )
        stake_parser.add_argument("--all", dest="stake_all", action="store_true")
        stake_parser.add_argument("--uid", dest="uid", type=int, required=False)
        stake_parser.add_argument("--amount", dest="amount", type=float, required=False)
        stake_parser.add_argument(
            "--max_stake",
            dest="max_stake",
            type=float,
            required=False,
            action="store",
            default=None,
            help=f"""Specify the maximum amount of {cybertensor.__giga_boot_symbol__} to have staked in each hotkey.""",
        )
        stake_parser.add_argument(
            "--hotkeys",
            "--exclude_hotkeys",
            "--wallet.hotkeys",
            "--wallet.exclude_hotkeys",
            required=False,
            action="store",
            default=[],
            type=str,
            nargs="*",
            help="""Specify the hotkeys by name or address. (e.g. hk1 hk2 hk3)""",
        )
        stake_parser.add_argument(
            "--all_hotkeys",
            "--wallet.all_hotkeys",
            required=False,
            action="store_true",
            default=False,
            help="""To specify all hotkeys. Specifying hotkeys will exclude them from this all.""",
        )
        Wallet.add_args(stake_parser)
        cybertensor.cwtensor.add_args(stake_parser)


### Stake list.
import os
from typing import List, Tuple, Optional, Dict
import argparse
import cybertensor
from tqdm import tqdm
from rich.table import Table
from rich.prompt import Prompt
from typing import Union
from concurrent.futures import ThreadPoolExecutor

from cybertensor.commands.utils import DelegatesDetails
from cybertensor.commands import defaults
from cybertensor.wallet import Wallet
from cybertensor import __console__ as console


def _get_coldkey_wallets_for_path(path: str) -> List["Wallet"]:
    try:
        wallet_names = next(os.walk(os.path.expanduser(path)))[1]
        return [Wallet(path=path, name=name) for name in wallet_names]
    except StopIteration:
        # No wallet files found.
        wallets = []
    return wallets


def _get_hotkey_wallets_for_wallet(wallet) -> List["Wallet"]:
    hotkey_wallets = []
    hotkeys_path = wallet.path + "/" + wallet.name + "/hotkeys"
    try:
        hotkey_files = next(os.walk(os.path.expanduser(hotkeys_path)))[2]
    except StopIteration:
        hotkey_files = []
    for hotkey_file_name in hotkey_files:
        try:
            hotkey_for_name = Wallet(
                path=wallet.path, name=wallet.name, hotkey=hotkey_file_name
            )
            if (
                hotkey_for_name.hotkey_file.exists_on_device()
                and not hotkey_for_name.hotkey_file.is_encrypted()
            ):
                hotkey_wallets.append(hotkey_for_name)
        except Exception:
            pass
    return hotkey_wallets


class StakeShow:
    """
    Executes the 'show' command to list all stake accounts associated with a user's wallet on the Cybertensor network.
    This command provides a comprehensive view of the stakes associated with both hotkeys and delegates linked to the user's coldkey.

    Usage:
    The command lists all stake accounts for a specified wallet or all wallets in the user's configuration directory.
    It displays the coldkey, balance, account details (hotkey/delegate name), stake amount, and the rate of return.

    Optional arguments:
    - --all (bool): When set, the command checks all coldkey wallets instead of just the specified wallet.

    The command compiles a table showing:
    - Coldkey: The coldkey associated with the wallet.
    - Balance: The balance of the coldkey.
    - Account: The name of the hotkey or delegate.
    - Stake: The amount of GBOOT staked to the hotkey or delegate.
    - Rate: The rate of return on the stake, typically shown in GBOOT per day.

    Example usage:
    >>> ctcli stake show --all

    Note:
    This command is essential for users who wish to monitor their stake distribution and returns across various accounts on the Cybertensor network.
    It provides a clear and detailed overview of the user's staking activities.
    """

    @staticmethod
    def run(cli: "cybertensor.cli") -> None:
        r"""Show all stake accounts."""
        try:
            cwtensor = cybertensor.cwtensor(config=cli.config, log_verbose=False)
            StakeShow._run(cli, cwtensor)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def _run(cli: "cybertensor.cli", cwtensor: "cybertensor.cwtensor"):

        if cli.config.get("all", d=False) is True:
            wallets = _get_coldkey_wallets_for_path(cli.config.wallet.path)
        else:
            wallets = [Wallet(config=cli.config)]

        # TODO revisit
        # registered_delegate_info: Optional[
        #     Dict[str, DelegatesDetails]
        # ] = get_delegates_details(url=cybertensor.__delegates_details_url__)

        registered_delegate_info: Optional[
            Dict[str, DelegatesDetails]
        ] = cwtensor.get_delegates()

        def get_stake_accounts(
                wallet: "cybertensor.Wallet",
                cwtensor: "cybertensor.cwtensor"
        ) -> Dict[str, Dict[str, Union[str, Balance]]]:
            """Get stake account details for the given wallet.

            Args:
                wallet: The wallet object to fetch the stake account details for.
                cwtensor: The cwtensor object.

            Returns:
                A dictionary mapping addresses to their respective stake account details.
            """

            wallet_stake_accounts = {}

            # Get this wallet's coldkey balance.
            cold_balance = cwtensor.get_balance(wallet.coldkeypub.address)

            # Populate the stake accounts with local hotkeys data.
            wallet_stake_accounts.update(get_stakes_from_hotkeys(cwtensor=cwtensor, wallet=wallet))

            # Populate the stake accounts with delegations data.
            wallet_stake_accounts.update(get_stakes_from_delegates(cwtensor=cwtensor, wallet=wallet))

            return {
                "name": wallet.name,
                "balance": cold_balance,
                "accounts": wallet_stake_accounts,
            }

        def get_stakes_from_hotkeys(
                wallet: "cybertensor.Wallet",
                cwtensor: "cybertensor.cwtensor"
        ) -> Dict[str, Dict[str, Union[str, Balance]]]:
            """Fetch stakes from hotkeys for the provided wallet.

            Args:
                wallet: The wallet object to fetch the stakes for.
                cwtensor: The cwtensor object.

            Returns:
                A dictionary of stakes related to hotkeys.
            """
            hotkeys = get_hotkey_wallets_for_wallet(wallet)
            stakes = {}
            for hot in hotkeys:
                emission = sum(
                    [
                        n.emission
                        for n in cwtensor.get_all_neurons_for_pubkey(
                            hot.hotkey.address
                        )
                    ]
                )
                hotkey_stake = cwtensor.get_stake_for_coldkey_and_hotkey(
                    hotkey=hot.hotkey.address,
                    coldkey=wallet.coldkeypub.address,
                )
                stakes[hot.hotkey.address] = {
                    "name": hot.hotkey_str,
                    "stake": hotkey_stake,
                    "rate": emission,
                }
            return stakes

        def get_stakes_from_delegates(
                wallet: "cybertensor.Wallet",
                cwtensor: "cybertensor.cwtensor"
        ) -> Dict[str, Dict[str, Union[str, Balance]]]:
            """Fetch stakes from delegates for the provided wallet.

            Args:
                wallet: The wallet object to fetch the stakes for.
                cwtensor: The cwtensor object.

            Returns:
                A dictionary of stakes related to delegates.
            """
            delegates = cwtensor.get_delegated(
                delegatee=wallet.coldkeypub.address
            )
            stakes = {}
            for dele, staked in delegates:
                for nom in dele.nominators:
                    if nom[0] == wallet.coldkeypub.address:
                        delegate_name = (
                            # registered_delegate_info[dele.hotkey].name
                            # if dele.hotkey in registered_delegate_info
                            # else dele.hotkey
                            dele.hotkey
                        )
                        stakes[dele.hotkey] = {
                            "name": delegate_name,
                            "stake": nom[1],
                            "rate": dele.total_daily_return.gboot
                            * (nom[1] / dele.total_stake.gboot),
                        }
            return stakes

        def get_all_wallet_accounts(
                wallets: list["cybertensor.Wallet"],
                cwtensor: "cybertensor.cwtensor"
        ) -> List[Dict[str, Dict[str, Union[str, Balance]]]]:
            """Fetch stake accounts for all provided wallets using a ThreadPool.

            Args:
                wallets: List of wallets to fetch the stake accounts for.
                cwtensor: The cwtensor object.

            Returns:
                A list of dictionaries, each dictionary containing stake account details for each wallet.
            """

            accounts = []
            # Create a progress bar using tqdm
            with tqdm(total=len(wallets), desc="Fetching accounts", ncols=100) as pbar:
                for wallet in wallets:
                    accounts.append(get_stake_accounts(wallet, cwtensor))
                    pbar.update()
            return accounts

        accounts = get_all_wallet_accounts(wallets=wallets, cwtensor=cwtensor)

        total_stake = 0
        total_balance = 0
        total_rate = 0
        for acc in accounts:
            total_balance += acc["balance"].boot
            for key, value in acc["accounts"].items():
                total_stake += value["stake"].boot
                total_rate += float(value["rate"])
        table = Table(show_footer=True, pad_edge=False, box=None, expand=False)
        table.add_column(
            "[overline white]Coldkey", footer_style="overline white", style="bold white"
        )
        table.add_column(
            "[overline white]Balance",
            f"{cwtensor.giga_token_symbol}{total_balance:.5f}",
            footer_style="overline white",
            style="green",
        )
        table.add_column(
            "[overline white]Account", footer_style="overline white", style="blue"
        )
        table.add_column(
            "[overline white]Stake",
            f"{cwtensor.giga_token_symbol}{total_stake:.5f}",
            footer_style="overline white",
            style="green",
        )
        table.add_column(
            "[overline white]Rate",
            f"{cwtensor.giga_token_symbol}{total_rate:.5f}/d",
            footer_style="overline white",
            style="green",
        )
        for acc in accounts:
            table.add_row(acc["name"], acc["balance"], "", "")
            for key, value in acc["accounts"].items():
                table.add_row(
                    "", "", value["name"], value["stake"], str(value["rate"]) + "/d"
                )
        console.print(table)

    @staticmethod
    def check_config(config: "Config"):
        if (
            not config.get("all", d=None)
            and not config.is_set("wallet.name")
            and not config.no_prompt
        ):
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        list_parser = parser.add_parser(
            "show", help="""List all stake accounts for wallet."""
        )
        list_parser.add_argument(
            "--all",
            action="store_true",
            help="""Check all coldkey wallets.""",
            default=False,
        )

        Wallet.add_args(list_parser)
        cybertensor.cwtensor.add_args(list_parser)
