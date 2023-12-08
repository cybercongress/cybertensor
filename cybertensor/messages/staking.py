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


def add_stake_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "cybertensor.wallet",
    hotkey: Optional[str] = None,
    amount: Union[Balance, float] = None,
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    r"""Adds the specified amount of stake to passed hotkey uid.
    Args:
        wallet (cybertensor.wallet):
            cybertensor wallet object.
        hotkey (Optional[str]):
            address of the hotkey account to stake to
            defaults to the wallet's hotkey.
        amount (Union[Balance, float]):
            Amount to stake as cybertensor balance, or float interpreted as GBOOT.
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
        cybertensor.errors.NotRegisteredError:
            If the wallet is not registered on the chain.
        cybertensor.errors.NotDelegateError:
            If the hotkey is not a delegate on the chain.
    """
    # Decrypt keys,
    wallet.coldkey

    # Default to wallet's own hotkey if the value is not passed.
    if hotkey is None:
        hotkey = wallet.hotkey.address

    # Flag to indicate if we are using the wallet's own hotkey.
    own_hotkey: bool

    with cybertensor.__console__.status(
        ":satellite: Syncing with chain: [white]{}[/white] ...".format(
            cwtensor.network
        )
    ):
        old_balance = cwtensor.get_balance(wallet.coldkeypub.address)
        # Get hotkey owner
        hotkey_owner = cwtensor.get_hotkey_owner(hotkey)
        own_hotkey = wallet.coldkeypub.address == hotkey_owner
        if not own_hotkey:
            # This is not the wallet's own hotkey so we are delegating.
            if not cwtensor.is_hotkey_delegate(hotkey):
                raise cybertensor.errors.NotDelegateError(
                    "Hotkey: {} is not a delegate.".format(hotkey)
                )

            # Get hotkey take
            hotkey_take = cwtensor.get_delegate_take(hotkey)

        # Get current stake
        old_stake = cwtensor.get_stake_for_coldkey_and_hotkey(
            coldkey=wallet.coldkeypub.address, hotkey=hotkey
        )

    # Convert to cybertensor.Balance
    if amount == None:
        # Stake it all.
        staking_balance = cybertensor.Balance.from_gboot(old_balance.gboot)
    elif not isinstance(amount, cybertensor.Balance):
        staking_balance = cybertensor.Balance.from_gboot(amount)
    else:
        staking_balance = amount

    # Remove existential balance to keep key alive.
    if staking_balance > cybertensor.Balance.from_boot(1000000):
        staking_balance = staking_balance - cybertensor.Balance.from_boot(1000000)
    else:
        staking_balance = staking_balance

    # Check enough to stake.
    if staking_balance > old_balance:
        cybertensor.__console__.print(
            ":cross_mark: [red]Not enough stake[/red]:[bold white]\n  balance:{}\n  amount: {}\n  coldkey: {}[/bold white]".format(
                old_balance, staking_balance, wallet.name
            )
        )
        return False

    # Ask before moving on.
    if prompt:
        if not own_hotkey:
            # We are delegating.
            if not Confirm.ask(
                "Do you want to delegate:[bold white]\n  amount: {}\n  to: {}\n  take: {}\n  owner: {}[/bold white]".format(
                    staking_balance, wallet.hotkey_str, hotkey_take, hotkey_owner
                )
            ):
                return False
        else:
            if not Confirm.ask(
                "Do you want to stake:[bold white]\n  amount: {}\n  to: {}[/bold white]".format(
                    staking_balance, wallet.hotkey_str
                )
            ):
                return False

    try:
        with cybertensor.__console__.status(
            ":satellite: Staking to: [bold white]{}[/bold white] ...".format(
                cwtensor.network
            )
        ):
            staking_response: bool = __do_add_stake_single(
                cwtensor=cwtensor,
                wallet=wallet,
                hotkey=hotkey,
                amount=staking_balance,
                wait_for_finalization=wait_for_finalization,
            )

        if staking_response == True:  # If we successfully staked.
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
                block = cwtensor.get_current_block()
                new_stake = cwtensor.get_stake_for_coldkey_and_hotkey(
                    coldkey=wallet.coldkeypub.address,
                    hotkey=wallet.hotkey.address,
                    block=block,
                )  # Get current stake

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


def add_stake_multiple_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "cybertensor.wallet",
    hotkeys: List[str],
    amounts: List[Union[Balance, float]] = None,
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    r"""Adds stake to each hotkey in the list, using each amount, from a common coldkey.
    Args:
        wallet (cybertensor.wallet):
            cybertensor wallet object for the coldkey.
        hotkeys (List[str]):
            List of hotkeys to stake to.
        amounts (List[Union[Balance, float]]):
            List of amounts to stake. If None, stake all to the first hotkey.
        wait_for_finalization (bool):
            if set, waits for the extrinsic to be finalized on the chain before returning true,
            or returns false if the extrinsic fails to be finalized within the timeout.
        prompt (bool):
            If true, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            flag is true if extrinsic was finalized or included in the block.
            flag is true if any wallet was staked.
            If we did not wait for finalization / inclusion, the response is true.
    """
    if not isinstance(hotkeys, list) or not all(
        isinstance(hotkey, str) for hotkey in hotkeys
    ):
        raise TypeError("hotkeys must be a list of str")

    if len(hotkeys) == 0:
        return True

    if amounts is not None and len(amounts) != len(hotkeys):
        raise ValueError("amounts must be a list of the same length as hotkeys")

    if amounts is not None and not all(
        isinstance(amount, (Balance, float)) for amount in amounts
    ):
        raise TypeError(
            "amounts must be a [list of cybertensor.Balance or float] or None"
        )

    if amounts is None:
        amounts = [None] * len(hotkeys)
    else:
        # Convert to Balance
        amounts = [
            cybertensor.Balance.from_gboot(amount) if isinstance(amount, float) else amount
            for amount in amounts
        ]

        if sum(amount.gboot for amount in amounts) == 0:
            # Staking 0.gboot
            return True

    # Decrypt coldkey.
    wallet.coldkey

    old_stakes = []
    with cybertensor.__console__.status(
        ":satellite: Syncing with chain: [white]{}[/white] ...".format(
            cwtensor.network
        )
    ):
        old_balance = cwtensor.get_balance(wallet.coldkeypub.address)

        # Get the old stakes.
        for hotkey in hotkeys:
            old_stakes.append(
                cwtensor.get_stake_for_coldkey_and_hotkey(
                    coldkey=wallet.coldkeypub.address, hotkey=hotkey
                )
            )

    # Remove existential balance to keep key alive.
    ## Keys must maintain a balance of at least 1000 boot to stay alive.
    total_staking_boot = sum(
        [amount.boot if amount is not None else 0 for amount in amounts]
    )
    if total_staking_boot == 0:
        # Staking all to the first wallet.
        if old_balance.boot > 1000000:
            old_balance -= cybertensor.Balance.from_boot(1000000)

    elif total_staking_boot < 1000000:
        # Staking less than 1000 boot to the wallets.
        pass
    else:
        # Staking more than 1000 boot to the wallets.
        ## Reduce the amount to stake to each wallet to keep the balance above 1000000 boot.
        percent_reduction = 1 - (1000000 / total_staking_boot)
        amounts = [
            Balance.from_gboot(amount.gboot * percent_reduction) for amount in amounts
        ]

    successful_stakes = 0
    for idx, (hotkey, amount, old_stake) in enumerate(
        zip(hotkeys, amounts, old_stakes)
    ):
        staking_all = False
        # Convert to cybertensor.Balance
        if amount == None:
            # Stake it all.
            staking_balance = cybertensor.Balance.from_gboot(old_balance.gboot)
            staking_all = True
        else:
            # Amounts are cast to balance earlier in the function
            assert isinstance(amount, cybertensor.Balance)
            staking_balance = amount

        # Check enough to stake
        if staking_balance > old_balance:
            cybertensor.__console__.print(
                ":cross_mark: [red]Not enough balance[/red]: [green]{}[/green] to stake: [blue]{}[/blue] from coldkey: [white]{}[/white]".format(
                    old_balance, staking_balance, wallet.name
                )
            )
            continue

        # Ask before moving on.
        if prompt:
            if not Confirm.ask(
                "Do you want to stake:\n[bold white]  amount: {}\n  hotkey: {}[/bold white ]?".format(
                    staking_balance, wallet.hotkey_str
                )
            ):
                continue

        try:
            staking_response: bool = __do_add_stake_single(
                cwtensor=cwtensor,
                wallet=wallet,
                hotkey=hotkey,
                amount=staking_balance,
                wait_for_finalization=wait_for_finalization,
            )

            if staking_response == True:  # If we successfully staked.
                # We only wait here if we expect finalization.

                if idx < len(hotkeys) - 1:
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
                    old_balance -= staking_balance
                    successful_stakes += 1
                    if staking_all:
                        # If staked all, no need to continue
                        break

                    continue

                cybertensor.__console__.print(
                    ":white_heavy_check_mark: [green]Finalized[/green]"
                )

                block = cwtensor.get_current_block()
                new_stake = cwtensor.get_stake_for_coldkey_and_hotkey(
                    coldkey=wallet.coldkeypub.address,
                    hotkey=hotkey,
                    block=block,
                )
                new_balance = cwtensor.get_balance(
                    wallet.coldkeypub.address, block=block
                )
                cybertensor.__console__.print(
                    "Stake ({}): [blue]{}[/blue] :arrow_right: [green]{}[/green]".format(
                        hotkey, old_stake, new_stake
                    )
                )
                old_balance = new_balance
                successful_stakes += 1
                if staking_all:
                    # If staked all, no need to continue
                    break

            else:
                cybertensor.__console__.print(
                    ":cross_mark: [red]Failed[/red]: Error unknown."
                )
                continue

        except cybertensor.errors.NotRegisteredError as e:
            cybertensor.__console__.print(
                ":cross_mark: [red]Hotkey: {} is not registered.[/red]".format(
                    hotkey
                )
            )
            continue
        except cybertensor.errors.StakeError as e:
            cybertensor.__console__.print(
                ":cross_mark: [red]Stake Error: {}[/red]".format(e)
            )
            continue

    if successful_stakes != 0:
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


def __do_add_stake_single(
    cwtensor: "cybertensor.cwtensor",
    wallet: "cybertensor.wallet",
    hotkey: str,
    amount: "cybertensor.Balance",
    wait_for_finalization: bool = True,
) -> bool:
    r"""
    Executes a stake call to the chain using the wallet and amount specified.
    Args:
        wallet (cybertensor.wallet):
            cybertensor wallet object.
        hotkey (str):
            Hotkey to stake to.
        amount (cybertensor.Balance):
            Amount to stake as cybertensor balance object.
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
        cybertensor.errors.NotDelegateError:
            If the hotkey is not a delegate.
        cybertensor.errors.NotRegisteredError:
            If the hotkey is not registered in any subnets.

    """
    # Decrypt keys,
    wallet.coldkey

    hotkey_owner = cwtensor.get_hotkey_owner(hotkey)
    own_hotkey = wallet.coldkeypub.address == hotkey_owner
    if not own_hotkey:
        # We are delegating.
        # Verify that the hotkey is a delegate.
        if not cwtensor.is_hotkey_delegate(hotkey=hotkey):
            raise cybertensor.errors.NotDelegateError(
                "Hotkey: {} is not a delegate.".format(hotkey)
            )

    success = cwtensor._do_stake(
        wallet=wallet,
        hotkey=hotkey,
        amount=amount,
        wait_for_finalization=wait_for_finalization,
    )

    return success
