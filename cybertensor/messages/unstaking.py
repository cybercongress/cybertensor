# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
# Copyright © 2023 Opentensor Foundation
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

from time import sleep
from typing import List, Union, Optional

from rich.prompt import Confirm

import cybertensor
from cybertensor import __console__ as console
from cybertensor.utils.balance import Balance
from cybertensor.wallet import Wallet


def __do_remove_stake_single(
    cwtensor: "cybertensor.cwtensor",
    wallet: "Wallet",
    hotkey: str,
    amount: "Balance",
    wait_for_finalization: bool = True,
) -> bool:
    r"""
    Executes an unstake call to the chain using the wallet and amount specified.
    Args:
        wallet (Wallet):
            Cybertensor wallet object.
        hotkey (str):
            Hotkey address to unstake from.
        amount (Balance):
            Amount to unstake as cybertensor balance object.
        wait_for_finalization (bool):
            If set, waits for the extrinsic to be finalized on the chain before returning ``true``,
            or returns ``false`` if the extrinsic fails to be finalized within the timeout.
        prompt (bool):
            If ``true``, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            Flag is ``true`` if extrinsic was finalized or uncluded in the block.
            If we did not wait for finalization / inclusion, the response is ``true``.
    Raises:
        cybertensor.errors.StakeError:
            If the extrinsic fails to be finalized or included in the block.
        cybertensor.errors.NotRegisteredError:
            If the hotkey is not registered in any subnets.

    """
    # Decrypt keys,
    wallet.coldkey

    success = cwtensor._do_unstake(
        wallet=wallet,
        hotkey=hotkey,
        amount=amount,
        wait_for_finalization=wait_for_finalization,
    )

    return success


def unstake_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "Wallet",
    hotkey: Optional[str] = None,
    amount: Optional[Union[Balance, float]] = None,
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    r"""Removes stake into the wallet coldkey from the specified hotkey uid.
    Args:
        wallet (Wallet):
            cybertensor wallet object.
        hotkey (Optional[str]):
            address of the hotkey to unstake from.
            by default, the wallet hotkey is used.
        amount (Union[Balance, float]):
            Amount to stake as cybertensor balance, or ``float`` interpreted as GBOOT.
        wait_for_finalization (bool):
            If set, waits for the extrinsic to be finalized on the chain before returning ``true``,
            or returns ``false`` if the extrinsic fails to be finalized within the timeout.
        prompt (bool):
            If ``true``, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            Flag is ``true`` if extrinsic was finalized or uncluded in the block.
            If we did not wait for finalization / inclusion, the response is ``true``.
    """
    # Decrypt keys,
    wallet.coldkey

    if hotkey is None:
        hotkey = wallet.hotkey.address  # Default to wallet's own hotkey.

    with console.status(
        f":satellite: Syncing with chain: [white]{cwtensor.network}[/white] ..."
    ):
        old_balance = cwtensor.get_balance(wallet.coldkeypub.address)
        old_stake = cwtensor.get_stake_for_coldkey_and_hotkey(
            coldkey=wallet.coldkeypub.address, hotkey=hotkey
        )

    # Convert to Balance
    if amount is None:
        # Unstake it all.
        unstaking_balance = old_stake
    elif not isinstance(amount, Balance):
        unstaking_balance = Balance.from_gboot(amount)
    else:
        unstaking_balance = amount

    # Check enough to unstake.
    stake_on_uid = old_stake
    if unstaking_balance > stake_on_uid:
        console.print(
            f":cross_mark: [red]Not enough stake[/red]: [green]{stake_on_uid}[/green] "
            f"to unstake: [blue]{unstaking_balance}[/blue] from hotkey: [white]{wallet.hotkey_str}[/white]"
        )
        return False

    # Ask before moving on.
    if prompt:
        if not Confirm.ask(
            f"Do you want to unstake:\n"
            f"[bold white]  amount: {unstaking_balance}\n"
            f"  hotkey: {wallet.hotkey_str}[/bold white ]?"
        ):
            return False

    try:
        with console.status(
            f":satellite: Unstaking from chain: [white]{cwtensor.network}[/white] ..."
        ):
            staking_response: bool = __do_remove_stake_single(
                cwtensor=cwtensor,
                wallet=wallet,
                hotkey=hotkey,
                amount=unstaking_balance,
                wait_for_finalization=wait_for_finalization,
            )

        if staking_response is True:  # If we successfully unstaked.
            # We only wait here if we expect finalization.
            if not wait_for_finalization:
                return True

            console.print(
                ":white_heavy_check_mark: [green]Finalized[/green]"
            )
            with console.status(
                f":satellite: Checking Balance on: [white]{cwtensor.network}[/white] ..."
            ):
                new_balance = cwtensor.get_balance(address=wallet.coldkeypub.address)
                new_stake = cwtensor.get_stake_for_coldkey_and_hotkey(
                    coldkey=wallet.coldkeypub.address, hotkey=hotkey
                )  # Get stake on hotkey.
                console.print(
                    f"Balance:\n"
                    f"  [blue]{old_balance}[/blue] :arrow_right: [green]{new_balance}[/green]"
                )
                console.print(
                    f"Stake:\n"
                    f"  [blue]{old_stake}[/blue] :arrow_right: [green]{new_stake}[/green]"
                )
                return True
        else:
            console.print(
                ":cross_mark: [red]Failed[/red]: Error unknown."
            )
            return False

    except cybertensor.errors.NotRegisteredError as e:
        console.print(
            f":cross_mark: [red]Hotkey: {wallet.hotkey_str} is not registered.[/red]"
        )
        return False
    except cybertensor.errors.StakeError as e:
        console.print(f":cross_mark: [red]Stake Error: {e}[/red]")
        return False


def unstake_multiple_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "Wallet",
    hotkey: List[str],
    amounts: Optional[List[Union[Balance, float]]] = None,
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    r"""Removes stake from each hotkey in the list, using each amount, to a common coldkey.
    Args:
        wallet (Wallet):
            The wallet with the coldkey to unstake to.
        hotkey (List[str]):
            List of hotkeys to unstake from.
        amounts (List[Union[Balance, float]]):
            List of amounts to unstake. If None, unstake all.
        wait_for_finalization (bool):
            If set, waits for the extrinsic to be finalized on the chain before returning ``true``,
            or returns ``false`` if the extrinsic fails to be finalized within the timeout.
        prompt (bool):
            If ``true``, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            flag is true if extrinsic was finalized or included in the block.
            flag is true if any wallet was unstaked.
            If we did not wait for finalization / inclusion, the response is ``true``.
    """
    if not isinstance(hotkey, list) or not all(
        isinstance(hotkey, str) for hotkey in hotkey
    ):
        raise TypeError("hotkey must be a list of str")

    if len(hotkey) == 0:
        return True

    if amounts is not None and len(amounts) != len(hotkey):
        raise ValueError("amounts must be a list of the same length as hotkey")

    if amounts is not None and not all(
        isinstance(amount, (Balance, float)) for amount in amounts
    ):
        raise TypeError(
            "amounts must be a [list of Balance or float] or None"
        )

    if amounts is None:
        amounts = [None] * len(hotkey)
    else:
        # Convert to Balance
        amounts = [
            Balance.from_gboot(amount)
            if isinstance(amount, float)
            else amount
            for amount in amounts
        ]

        if sum(amount.gboot for amount in amounts) == 0:
            # Staking 0 GBOOT
            return True

    # Unlock coldkey.
    wallet.coldkey

    old_stakes = []
    with console.status(
        f":satellite: Syncing with chain: [white]{cwtensor.network}[/white] ..."
    ):
        old_balance = cwtensor.get_balance(wallet.coldkeypub.address)

        for hotkey in hotkey:
            old_stake = cwtensor.get_stake_for_coldkey_and_hotkey(
                coldkey=wallet.coldkeypub.address, hotkey=hotkey
            )  # Get stake on hotkey.
            old_stakes.append(old_stake)  # None if not registered.

    successful_unstakes = 0
    for idx, (hotkey, amount, old_stake) in enumerate(zip(hotkey, amounts, old_stakes)):
        # Covert to Balance
        if amount is None:
            # Unstake it all.
            unstaking_balance = old_stake
        elif not isinstance(amount, Balance):
            unstaking_balance = Balance.from_gboot(amount)
        else:
            unstaking_balance = amount

        # Check enough to unstake.
        stake_on_uid = old_stake
        if unstaking_balance > stake_on_uid:
            console.print(
                f":cross_mark: [red]Not enough stake[/red]: [green]{stake_on_uid}[/green] "
                f"to unstake: [blue]{unstaking_balance}[/blue] from hotkey: [white]{wallet.hotkey_str}[/white]"
            )
            continue

        # Ask before moving on.
        if prompt:
            if not Confirm.ask(
                f"Do you want to unstake:\n"
                f"[bold white]  amount: {unstaking_balance}\n"
                f"  hotkey: {wallet.hotkey_str}[/bold white ]?"
            ):
                continue

        try:
            with console.status(
                f":satellite: Unstaking from chain: [white]{cwtensor.network}[/white] ..."
            ):
                staking_response: bool = __do_remove_stake_single(
                    cwtensor=cwtensor,
                    wallet=wallet,
                    hotkey=hotkey,
                    amount=unstaking_balance,
                    wait_for_finalization=wait_for_finalization,
                )

            if staking_response is True:  # If we successfully unstaked.
                # We only wait here if we expect finalization.

                if idx < len(hotkey) - 1:
                    # Wait for tx rate limit.
                    tx_rate_limit_blocks = cwtensor.tx_rate_limit()
                    if tx_rate_limit_blocks > 0:
                        console.print(
                            f":hourglass: [yellow]Waiting for tx rate limit: "
                            f"[white]{tx_rate_limit_blocks}[/white] blocks[/yellow]"
                        )
                        sleep(tx_rate_limit_blocks * 12)  # 12 seconds per block

                if not wait_for_finalization:
                    successful_unstakes += 1
                    continue

                console.print(
                    ":white_heavy_check_mark: [green]Finalized[/green]"
                )
                with console.status(
                    f":satellite: Checking Balance on: [white]{cwtensor.network}[/white] ..."
                ):
                    block = cwtensor.get_current_block()
                    new_stake = cwtensor.get_stake_for_coldkey_and_hotkey(
                        coldkey=wallet.coldkeypub.address,
                        hotkey=hotkey,
                        block=block,
                    )
                    console.print(
                        f"Stake ({hotkey}): [blue]{stake_on_uid}[/blue] :arrow_right: [green]{new_stake}[/green]"
                    )
                    successful_unstakes += 1
            else:
                console.print(
                    ":cross_mark: [red]Failed[/red]: Error unknown."
                )
                continue

        except cybertensor.errors.NotRegisteredError as e:
            console.print(
                f":cross_mark: [red]{hotkey} is not registered.[/red]"
            )
            continue
        except cybertensor.errors.StakeError as e:
            console.print(f":cross_mark: [red]Stake Error: {e}[/red]")
            continue

    if successful_unstakes != 0:
        with console.status(
            f":satellite: Checking Balance on: ([white]{cwtensor.network}[/white] ..."
        ):
            new_balance = cwtensor.get_balance(wallet.coldkeypub.address)
        console.print(
            f"Balance: [blue]{old_balance}[/blue] :arrow_right: [green]{new_balance}[/green]"
        )
        return True

    return False
