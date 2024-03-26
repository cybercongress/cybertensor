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

import sys
from typing import List, Union, Optional, Tuple

from rich.prompt import Confirm, Prompt
from tqdm import tqdm

import cybertensor
from cybertensor import __console__ as console
from cybertensor.commands import defaults
from cybertensor.commands.utils import get_hotkey_wallets_for_wallet
from cybertensor.config import Config
from cybertensor.utils.balance import Balance
from cybertensor.wallet import Wallet


class UnStakeCommand:
    """
    Executes the 'remove' command to unstake GBOOT tokens from one or more hotkeys and transfer them back to the user's coldkey on the Cybertensor network.
    This command is used to withdraw tokens previously staked to different hotkeys.

    Usage:
    Users can specify the amount to unstake, the hotkeys to unstake from (either by name or address),
    and whether to unstake from all hotkeys. The command checks for sufficient stake and prompts for confirmation before proceeding with the unstaking process.

    Optional arguments:
    - --all (bool): When set, unstakes all staked tokens from the specified hotkeys.
    - --amount (float): The amount of GBOOT tokens to unstake.
    - --hotkey_address (str): The address of the hotkey to unstake from.
    - --max_stake (float): Sets the maximum amount of GBOOT to remain staked in each hotkey.
    - --hotkeys (list): Specifies hotkeys by name or address to unstake from.
    - --all_hotkeys (bool): When set, unstakes from all hotkeys associated with the wallet, excluding any specified in --hotkeys.

    The command prompts for confirmation before executing the unstaking operation.

    Example usage:
    >>> ctcli stake remove --amount 100 --hotkeys hk1,hk2

    Note:
    This command is important for users who wish to reallocate their stakes or withdraw them from the network.
    It allows for flexible management of token stakes across different neurons (hotkeys) on the network.
    """

    @classmethod
    def check_config(cls, config: "Config"):
        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

        if (
            not config.get("hotkey_address", d=None)
            and not config.is_set("wallet.hotkey")
            and not config.no_prompt
            and not config.get("all_hotkeys")
            and not config.get("hotkeys")
        ):
            hotkey = Prompt.ask("Enter hotkey name", default=defaults.wallet.hotkey)
            config.wallet.hotkey = str(hotkey)

        # Get amount.
        if (
            not config.get("hotkey_address")
            and not config.get("amount")
            and not config.get("unstake_all")
            and not config.get("max_stake")
        ):
            hotkeys: str = ""
            if config.get("all_hotkeys"):
                hotkeys = "all hotkeys"
            elif config.get("hotkeys"):
                hotkeys = str(config.hotkeys).replace("[", "").replace("]", "")
            else:
                hotkeys = str(config.wallet.hotkey)
            amount = Prompt.ask(
                f"Enter {cybertensor.__giga_boot_symbol__} amount to unstake from [bold]{hotkeys}[/bold]"
            )
            config.unstake_all = False
            try:
                config.amount = float(amount)
            except ValueError:
                console.print(
                    f":cross_mark:[red] Invalid {cybertensor.__giga_boot_symbol__} amount[/red] [bold white]{amount}[/bold white]"
                )
                sys.exit()

    @staticmethod
    def add_args(command_parser):
        unstake_parser = command_parser.add_parser(
            "remove",
            help="""Remove stake from the specified hotkey into the coldkey balance.""",
        )
        unstake_parser.add_argument(
            "--all", dest="unstake_all", action="store_true", default=False
        )
        unstake_parser.add_argument(
            "--amount", dest="amount", type=float, required=False
        )
        unstake_parser.add_argument(
            "--hotkey_address", dest="hotkey_address", type=str, required=False
        )
        unstake_parser.add_argument(
            "--max_stake",
            dest="max_stake",
            type=float,
            required=False,
            action="store",
            default=None,
            help="""Specify the maximum amount of GBOOT to have staked in each hotkey.""",
        )
        unstake_parser.add_argument(
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
        unstake_parser.add_argument(
            "--all_hotkeys",
            "--wallet.all_hotkeys",
            required=False,
            action="store_true",
            default=False,
            help="""To specify all hotkeys. Specifying hotkeys will exclude them from this all.""",
        )
        Wallet.add_args(unstake_parser)
        cybertensor.cwtensor.add_args(unstake_parser)

    @staticmethod
    def run(cli: "cybertensor.cli") -> None:
        r"""Unstake token of amount from hotkey(s)."""
        try:
            cwtensor = cybertensor.cwtensor(config=cli.config, log_verbose=False)
            UnStakeCommand._run(cli, cwtensor)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def _run(cli: "cybertensor.cli", cwtensor: "cybertensor.cwtensor"):
        config = cli.config.copy()
        wallet = Wallet(config=config)

        # Get the hotkey_names (if any) and the hotkeys.
        hotkeys_to_unstake_from: List[Tuple[Optional[str], str]] = []
        if cli.config.get("hotkey_address"):
            # Stake to specific hotkey.
            hotkeys_to_unstake_from = [(None, cli.config.get("hotkey_address"))]
        elif cli.config.get("all_hotkeys"):
            # Stake to all hotkeys.
            all_hotkeys: List[Wallet] = get_hotkey_wallets_for_wallet(
                wallet=wallet
            )
            # Get the hotkeys to exclude. (d)efault to no exclusions.
            hotkeys_to_exclude: List[str] = cli.config.get("hotkeys", d=[])
            # Exclude hotkeys that are specified.
            hotkeys_to_unstake_from = [
                (wallet.hotkey_str, wallet.hotkey.address)
                for wallet in all_hotkeys
                if wallet.hotkey_str not in hotkeys_to_exclude
            ]  # definitely wallets

        elif cli.config.get("hotkeys"):
            # Stake to specific hotkeys.
            for hotkey_or_hotkey_name in cli.config.get("hotkeys"):
                if cybertensor.utils.is_valid_address(hotkey_or_hotkey_name):
                    # If the hotkey is a valid address, we add it to the list.
                    hotkeys_to_unstake_from.append((None, hotkey_or_hotkey_name))
                else:
                    # If the hotkey is not a valid address, we assume it is a hotkey name.
                    #  We then get the hotkey from the wallet and add it to the list.
                    wallet_ = Wallet(
                        config=cli.config, hotkey=hotkey_or_hotkey_name
                    )
                    hotkeys_to_unstake_from.append(
                        (wallet_.hotkey_str, wallet_.hotkey.address)
                    )
        elif cli.config.wallet.get("hotkey"):
            # Only cli.config.wallet.hotkey is specified.
            #  so we stake to that single hotkey.
            hotkey_or_name = cli.config.wallet.get("hotkey")
            if cybertensor.utils.is_valid_address(hotkey_or_name):
                hotkeys_to_unstake_from = [(None, hotkey_or_name)]
            else:
                # Hotkey is not a valid address, so we assume it is a hotkey name.
                wallet_ = Wallet(
                    config=cli.config, hotkey=hotkey_or_name
                )
                hotkeys_to_unstake_from = [
                    (wallet_.hotkey_str, wallet_.hotkey.address)
                ]
        else:
            # Only cli.config.wallet.hotkey is specified.
            #  so we stake to that single hotkey.
            assert cli.config.wallet.hotkey is not None
            hotkeys_to_unstake_from = [
                (None, Wallet(config=cli.config).hotkey.address)
            ]

        final_hotkeys: List[Tuple[str, str]] = []
        final_amounts: List[Union[float, Balance]] = []
        for hotkey in tqdm(hotkeys_to_unstake_from):
            hotkey: Tuple[Optional[str], str]  # (hotkey_name (or None), hotkey)
            unstake_amount_gigaboot: float = cli.config.get(
                "amount"
            )  # The amount specified to unstake.
            hotkey_stake: Balance = cwtensor.get_stake_for_coldkey_and_hotkey(
                hotkey=hotkey[1], coldkey=wallet.coldkeypub.address
            )
            if unstake_amount_gigaboot is None:
                unstake_amount_gigaboot = hotkey_stake.gboot
            if cli.config.get("max_stake"):
                # Get the current stake of the hotkey from this coldkey.
                unstake_amount_gigaboot: float = hotkey_stake.gboot - cli.config.get(
                    "max_stake"
                )
                cli.config.amount = unstake_amount_gigaboot
                if unstake_amount_gigaboot < 0:
                    # Skip if max_stake is greater than current stake.
                    continue
            else:
                if unstake_amount_gigaboot is not None:
                    # There is a specified amount to unstake.
                    if unstake_amount_gigaboot > hotkey_stake.gboot:
                        # Skip if the specified amount is greater than the current stake.
                        continue

            final_amounts.append(unstake_amount_gigaboot)
            final_hotkeys.append(hotkey)  # add both the name and the address.

        if len(final_hotkeys) == 0:
            # No hotkeys to unstake from.
            console.print(
                "Not enough stake to unstake from any hotkeys or max_stake is more than current stake."
            )
            return None

        # Ask to unstake
        if not cli.config.no_prompt:
            if not Confirm.ask(
                f"Do you want to unstake from the following keys to {wallet.name}:\n"
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
            # do regular unstake
            return cwtensor.unstake(
                wallet=wallet,
                hotkey=final_hotkeys[0][1],
                amount=None if cli.config.get("unstake_all") else final_amounts[0],
                wait_for_finalization=True,
                prompt=not cli.config.no_prompt,
            )

        cwtensor.unstake_multiple(
            wallet=wallet,
            hotkeys=[hotkey for _, hotkey in final_hotkeys],
            amounts=None if cli.config.get("unstake_all") else final_amounts,
            wait_for_finalization=True,
            prompt=False,
        )
