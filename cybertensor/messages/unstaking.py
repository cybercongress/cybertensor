# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
# Copyright © 2023 Opentensor Foundation
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

import cybertensor
from rich.prompt import Confirm
from time import sleep
from typing import List, Dict, Union, Optional
from cybertensor.utils.balance import Balance


def __do_remove_stake_single(
    cwtensor: "cybertensor.cwtensor",
    wallet: "cybertensor.wallet",
    hotkey: str,
    amount: "cybertensor.Balance",
    wait_for_finalization: bool = True,
) -> bool:
    r"""
    Executes an unstake call to the chain using the wallet and amount specified.
    Args:
        wallet (cybertensor.wallet):
            Bittensor wallet object.
        hotkey (str):
            Hotkey address to unstake from.
        amount (cybertensor.Balance):
            Amount to unstake as cybertensor balance object.
        wait_for_finalization (bool):
            If set, waits for the extrinsic to be finalized on the chain before returning true,
            or returns false if the extrinsic fails to be finalized within the timeout.
        prompt (bool):
            If true, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            flag is true if extrinsic was finalized or uncluded in the block.
            If we did not wait for finalization / inclusion, the response is true.
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
    wallet: "cybertensor.wallet",
    hotkey: Optional[str] = None,
    amount: Union[Balance, float] = None,
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    r"""Removes stake into the wallet coldkey from the specified hotkey uid.
    Args:
        wallet (cybertensor.wallet):
            cybertensor wallet object.
        hotkey (Optional[str]):
            address of the hotkey to unstake from.
            by default, the wallet hotkey is used.
        amount (Union[Balance, float]):
            Amount to stake as cybertensor balance, or float interpreted as tao.
        wait_for_finalization (bool):
            if set, waits for the extrinsic to be finalized on the chain before returning true,
            or returns false if the extrinsic fails to be finalized within the timeout.
        prompt (bool):
            If true, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            flag is true if extrinsic was finalized or uncluded in the block.
            If we did not wait for finalization / inclusion, the response is true.
    """
    # Decrypt keys,
    wallet.coldkey

    if hotkey is None:
        hotkey = wallet.hotkey.address  # Default to wallet's own hotkey.

    with cybertensor.__console__.status(
        ":satellite: Syncing with chain: [white]{}[/white] ...".format(
            cwtensor.network
        )
    ):
        old_balance = cwtensor.get_balance(wallet.coldkeypub.address)
        old_stake = cwtensor.get_stake_for_coldkey_and_hotkey(
            coldkey=wallet.coldkeypub.address, hotkey=hotkey
        )

    # Convert to cybertensor.Balance
    if amount == None:
        # Unstake it all.
        unstaking_balance = old_stake
    elif not isinstance(amount, cybertensor.Balance):
        unstaking_balance = cybertensor.Balance.from_gboot(amount)
    else:
        unstaking_balance = amount

    # Check enough to unstake.
    stake_on_uid = old_stake
    if unstaking_balance > stake_on_uid:
        cybertensor.__console__.print(
            ":cross_mark: [red]Not enough stake[/red]: [green]{}[/green] to unstake: [blue]{}[/blue] from hotkey: [white]{}[/white]".format(
                stake_on_uid, unstaking_balance, wallet.hotkey_str
            )
        )
        return False

    # Ask before moving on.
    if prompt:
        if not Confirm.ask(
            "Do you want to unstake:\n[bold white]  amount: {}\n  hotkey: {}[/bold white ]?".format(
                unstaking_balance, wallet.hotkey_str
            )
        ):
            return False

    try:
        with cybertensor.__console__.status(
            ":satellite: Unstaking from chain: [white]{}[/white] ...".format(
                cwtensor.network
            )
        ):
            staking_response: bool = __do_remove_stake_single(
                cwtensor=cwtensor,
                wallet=wallet,
                hotkey=hotkey,
                amount=unstaking_balance,
                wait_for_finalization=wait_for_finalization,
            )

        if staking_response == True:  # If we successfully unstaked.
            # We only wait here if we expect finalization.
            if not wait_for_finalization:
                return True

            cybertensor.__console__.print(
                ":white_heavy_check_mark: [green]Finalized[/green]"
            )
            with cybertensor.__console__.status(
                ":satellite: Checking Balance on: [white]{}[/white] ...".format(
                    cwtensor.network
                )
            ):
                new_balance = cwtensor.get_balance(
                    address=wallet.coldkeypub.address
                )
                new_stake = cwtensor.get_stake_for_coldkey_and_hotkey(
                    coldkey=wallet.coldkeypub.address, hotkey=hotkey
                )  # Get stake on hotkey.
                cybertensor.__console__.print(
                    "Balance:\n  [blue]{}[/blue] :arrow_right: [green]{}[/green]".format(
                        old_balance, new_balance
                    )
                )
                cybertensor.__console__.print(
                    "Stake:\n  [blue]{}[/blue] :arrow_right: [green]{}[/green]".format(
                        old_stake, new_stake
                    )
                )
                return True
        else:
            cybertensor.__console__.print(
                ":cross_mark: [red]Failed[/red]: Error unknown."
            )
            return False

    except cybertensor.errors.NotRegisteredError as e:
        cybertensor.__console__.print(
            ":cross_mark: [red]Hotkey: {} is not registered.[/red]".format(
                wallet.hotkey_str
            )
        )
        return False
    except cybertensor.errors.StakeError as e:
        cybertensor.__console__.print(":cross_mark: [red]Stake Error: {}[/red]".format(e))
        return False


def unstake_multiple_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "cybertensor.wallet",
    hotkey: List[str],
    amounts: List[Union[Balance, float]] = None,
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    r"""Removes stake from each hotkey in the list, using each amount, to a common coldkey.
    Args:
        wallet (cybertensor.wallet):
            The wallet with the coldkey to unstake to.
        hotkey (List[str]):
            List of hotkeys to unstake from.
        amounts (List[Union[Balance, float]]):
            List of amounts to unstake. If None, unstake all.
        wait_for_finalization (bool):
            if set, waits for the extrinsic to be finalized on the chain before returning true,
            or returns false if the extrinsic fails to be finalized within the timeout.
        prompt (bool):
            If true, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            flag is true if extrinsic was finalized or included in the block.
            flag is true if any wallet was unstaked.
            If we did not wait for finalization / inclusion, the response is true.
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
            "amounts must be a [list of cybertensor.Balance or float] or None"
        )

    if amounts is None:
        amounts = [None] * len(hotkey)
    else:
        # Convert to Balance
        amounts = [
            cybertensor.Balance.from_gboot(amount) if isinstance(amount, float) else amount
            for amount in amounts
        ]

        if sum(amount.gboot for amount in amounts) == 0:
            # Staking 0 tao
            return True

    # Unlock coldkey.
    wallet.coldkey

    old_stakes = []
    with cybertensor.__console__.status(
        ":satellite: Syncing with chain: [white]{}[/white] ...".format(
            cwtensor.network
        )
    ):
        old_balance = cwtensor.get_balance(wallet.coldkeypub.address)

        for hotkey in hotkey:
            old_stake = cwtensor.get_stake_for_coldkey_and_hotkey(
                coldkey=wallet.coldkeypub.address, hotkey=hotkey
            )  # Get stake on hotkey.
            old_stakes.append(old_stake)  # None if not registered.

    successful_unstakes = 0
    for idx, (hotkey, amount, old_stake) in enumerate(
        zip(hotkey, amounts, old_stakes)
    ):
        # Covert to cybertensor.Balance
        if amount == None:
            # Unstake it all.
            unstaking_balance = old_stake
        elif not isinstance(amount, cybertensor.Balance):
            unstaking_balance = cybertensor.Balance.from_gboot(amount)
        else:
            unstaking_balance = amount

        # Check enough to unstake.
        stake_on_uid = old_stake
        if unstaking_balance > stake_on_uid:
            cybertensor.__console__.print(
                ":cross_mark: [red]Not enough stake[/red]: [green]{}[/green] to unstake: [blue]{}[/blue] from hotkey: [white]{}[/white]".format(
                    stake_on_uid, unstaking_balance, wallet.hotkey_str
                )
            )
            continue

        # Ask before moving on.
        if prompt:
            if not Confirm.ask(
                "Do you want to unstake:\n[bold white]  amount: {}\n  hotkey: {}[/bold white ]?".format(
                    unstaking_balance, wallet.hotkey_str
                )
            ):
                continue

        try:
            with cybertensor.__console__.status(
                ":satellite: Unstaking from chain: [white]{}[/white] ...".format(
                    cwtensor.network
                )
            ):
                staking_response: bool = __do_remove_stake_single(
                    cwtensor=cwtensor,
                    wallet=wallet,
                    hotkey=hotkey,
                    amount=unstaking_balance,
                    wait_for_finalization=wait_for_finalization,
                )

            if staking_response == True:  # If we successfully unstaked.
                # We only wait here if we expect finalization.

                if idx < len(hotkey) - 1:
                    # Wait for tx rate limit.
                    tx_rate_limit_blocks = cwtensor.tx_rate_limit()
                    if tx_rate_limit_blocks > 0:
                        cybertensor.__console__.print(
                            ":hourglass: [yellow]Waiting for tx rate limit: [white]{}[/white] blocks[/yellow]".format(
                                tx_rate_limit_blocks
                            )
                        )
                        sleep(tx_rate_limit_blocks * 12)  # 12 seconds per block

                if not wait_for_finalization:
                    successful_unstakes += 1
                    continue

                cybertensor.__console__.print(
                    ":white_heavy_check_mark: [green]Finalized[/green]"
                )
                with cybertensor.__console__.status(
                    ":satellite: Checking Balance on: [white]{}[/white] ...".format(
                        cwtensor.network
                    )
                ):
                    block = cwtensor.get_current_block()
                    new_stake = cwtensor.get_stake_for_coldkey_and_hotkey(
                        coldkey=wallet.coldkeypub.address,
                        hotkey=hotkey,
                        block=block,
                    )
                    cybertensor.__console__.print(
                        "Stake ({}): [blue]{}[/blue] :arrow_right: [green]{}[/green]".format(
                            hotkey, stake_on_uid, new_stake
                        )
                    )
                    successful_unstakes += 1
            else:
                cybertensor.__console__.print(
                    ":cross_mark: [red]Failed[/red]: Error unknown."
                )
                continue

        except cybertensor.errors.NotRegisteredError as e:
            cybertensor.__console__.print(
                ":cross_mark: [red]{} is not registered.[/red]".format(hotkey)
            )
            continue
        except cybertensor.errors.StakeError as e:
            cybertensor.__console__.print(
                ":cross_mark: [red]Stake Error: {}[/red]".format(e)
            )
            continue

    if successful_unstakes != 0:
        with cybertensor.__console__.status(
            ":satellite: Checking Balance on: ([white]{}[/white] ...".format(
                cwtensor.network
            )
        ):
            new_balance = cwtensor.get_balance(wallet.coldkeypub.address)
        cybertensor.__console__.print(
            "Balance: [blue]{}[/blue] :arrow_right: [green]{}[/green]".format(
                old_balance, new_balance
            )
        )
        return True

    return False
