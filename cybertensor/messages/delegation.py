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


from typing import Union, Optional

from loguru import logger
from rich.prompt import Confirm

import cybertensor
from cybertensor import __console__ as console
from cybertensor.errors import *
from cybertensor.utils.balance import Balance
from cybertensor.wallet import Wallet

logger = logger.opt(colors=True)


def nominate_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "Wallet",
    wait_for_finalization: bool = True,
) -> bool:
    r"""Becomes a delegate for the hotkey.
    Args:
        wallet ( Wallet ):
            The wallet to become a delegate for.
    Returns:
        success (bool):
            ``True`` if the transaction was successful.
    """
    # Unlock the coldkey.
    wallet.coldkey
    wallet.hotkey

    # Check if the hotkey is already a delegate.
    if cwtensor.is_hotkey_delegate(wallet.hotkey.address):
        logger.error(
            f"Hotkey {wallet.hotkey.address} is already a delegate."
        )
        return False

    with console.status(
        f":satellite: Sending nominate call on [white]{cwtensor.network}[/white] ..."
    ):
        try:
            success = cwtensor._do_nominate(
                wallet=wallet,
                wait_for_finalization=wait_for_finalization,
            )

            if success is True:
                console.print(
                    ":white_heavy_check_mark: [green]Finalized[/green]"
                )
                cybertensor.logging.success(
                    prefix="Become Delegate",
                    sufix="<green>Finalized: </green>" + str(success),
                )

            # Raises NominationError if False
            return success

        except Exception as e:
            console.print(
                f":cross_mark: [red]Failed[/red]: error:{e}"
            )
            # cybertensor.logging.warning(
            #     prefix="Set weights", sufix=f"<red>Failed: </red>{e}"
            # )
        except NominationError as e:
            console.print(
                f":cross_mark: [red]Failed[/red]: error:{e}"
            )
            # cybertensor.logging.warning(
            #     prefix="Set weights", sufix=f"<red>Failed: </red>{e}"
            # )

    return False


def delegate_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "Wallet",
    delegate: Optional[str] = None,
    amount: Optional[Union[Balance, float]] = None,
    wait_for_finalization: bool = False,
    prompt: bool = False,
) -> bool:
    r"""Delegates the specified amount of stake to the passed delegate.
    Args:
        wallet (Wallet):
            cybertensor wallet object.
        delegate (Optional[str]):
            address of the delegate.
        amount (Union[Balance, float]):
            Amount to stake as cybertensor balance, or ``float`` interpreted as GBOOT.
        wait_for_finalization (bool):
            If set, waits for the extrinsic to be finalized on the chain before returning ``true``,
            or returns ``false`` if the extrinsic fails to be finalized within the timeout.
        prompt (bool):
            If ``true``, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            flag is ``true`` if extrinsic was finalized or uncluded in the block.
            If we did not wait for finalization / inclusion, the response is ``true``.

    Raises:
        NotRegisteredError:
            If the wallet is not registered on the chain.
        NotDelegateError:
            If the hotkey is not a delegate on the chain.
    """
    # Decrypt keys,
    wallet.coldkey
    if not cwtensor.is_hotkey_delegate(delegate):
        raise NotDelegateError(f"Hotkey: {delegate} is not a delegate.")

    # Get state.
    my_prev_coldkey_balance = cwtensor.get_balance(wallet.coldkey.address)
    delegate_take = cwtensor.get_delegate_take(delegate)
    delegate_owner = cwtensor.get_hotkey_owner(delegate)
    my_prev_delegated_stake = cwtensor.get_stake_for_coldkey_and_hotkey(
        coldkey=wallet.coldkeypub.address, hotkey=delegate
    )

    # Convert to Balance
    if amount is None:
        # Stake it all.
        staking_balance = Balance.from_gboot(my_prev_coldkey_balance.gboot)
    elif not isinstance(amount, Balance):
        staking_balance = Balance.from_gboot(amount)
    else:
        staking_balance = amount

    # Remove existential balance to keep key alive.
    if staking_balance > Balance.from_boot(1000000):
        staking_balance = staking_balance - Balance.from_boot(1000000)
    else:
        staking_balance = staking_balance

    # Check enough balance to stake.
    if staking_balance > my_prev_coldkey_balance:
        console.print(
            f":cross_mark: [red]Not enough balance[/red]:[bold white]\n"
            f"  balance:{my_prev_coldkey_balance}\n"
            f"  amount: {staking_balance}\n"
            f"  coldkey: {wallet.name}[/bold white]"
        )
        return False

    # Ask before moving on.
    if prompt:
        if not Confirm.ask(
            f"Do you want to delegate:[bold white]\n"
            f"  amount: {staking_balance}\n"
            f"  to: {delegate}\n"
            f" owner: {delegate_owner}[/bold white]"
        ):
            return False

    try:
        with console.status(
            f":satellite: Staking to: [bold white]{cwtensor.network}[/bold white] ..."
        ):
            staking_response: bool = cwtensor._do_delegation(
                wallet=wallet,
                delegate=delegate,
                amount=staking_balance,
                wait_for_finalization=wait_for_finalization,
            )

        if staking_response is True:  # If we successfully staked.
            # We only wait here if we expect finalization.
            if not wait_for_finalization:
                return True

            console.print(
                ":white_heavy_check_mark: [green]Finalized[/green]"
            )
            with console.status(
                f":satellite: Checking Balance on: [white]{cwtensor.network}[/white] ..."
            ):
                new_balance = cwtensor.get_balance(address=wallet.coldkey.address)
                block = cwtensor.get_current_block()
                new_delegate_stake = cwtensor.get_stake_for_coldkey_and_hotkey(
                    coldkey=wallet.coldkeypub.address,
                    hotkey=delegate,
                    block=block,
                )  # Get current stake

                console.print(
                    f"Balance:\n"
                    f"  [blue]{my_prev_coldkey_balance}[/blue] :arrow_right: [green]{new_balance}[/green]"
                )
                console.print(
                    f"Stake:\n  [blue]{my_prev_delegated_stake}[/blue] :arrow_right: [green]{new_delegate_stake}[/green]"
                )
                return True
        else:
            console.print(
                ":cross_mark: [red]Failed[/red]: Error unknown."
            )
            return False

    except NotRegisteredError as e:
        console.print(
            f":cross_mark: [red]Hotkey: {wallet.hotkey_str} is not registered.[/red]"
        )
        return False
    except StakeError as e:
        console.print(f":cross_mark: [red]Stake Error: {e}[/red]")
        return False


def undelegate_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "Wallet",
    delegate: Optional[str] = None,
    amount: Optional[Union[Balance, float]] = None,
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    r"""Un-delegates stake from the passed delegate.
    Args:
        wallet (Wallet):
            cybertensor wallet object.
        delegate (Optional[str]):
            address of the delegate.
        amount (Union[Balance, float]):
            Amount to unstake as cybertensor balance, or ``float`` interpreted as GBOOT.
        wait_for_finalization (bool):
            If set, waits for the extrinsic to be finalized on the chain before returning ``true``,
            or returns ``false`` if the extrinsic fails to be finalized within the timeout.
        prompt (bool):
            If ``true``, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            flag is ``true`` if extrinsic was finalized or uncluded in the block.
            If we did not wait for finalization / inclusion, the response is ``true``.

    Raises:
        NotRegisteredError:
            If the wallet is not registered on the chain.
        NotDelegateError:
            If the hotkey is not a delegate on the chain.
    """
    # Decrypt keys,
    wallet.coldkey
    if not cwtensor.is_hotkey_delegate(delegate):
        raise NotDelegateError(f"Hotkey: {delegate} is not a delegate.")

    # Get state.
    my_prev_coldkey_balance = cwtensor.get_balance(wallet.coldkey.address)
    delegate_take = cwtensor.get_delegate_take(delegate)
    delegate_owner = cwtensor.get_hotkey_owner(delegate)
    my_prev_delegated_stake = cwtensor.get_stake_for_coldkey_and_hotkey(
        coldkey=wallet.coldkeypub.address, hotkey=delegate
    )

    # Convert to Balance
    if amount is None:
        # Stake it all.
        unstaking_balance = Balance.from_gboot(my_prev_delegated_stake.gboot)

    elif not isinstance(amount, Balance):
        unstaking_balance = Balance.from_gboot(amount)

    else:
        unstaking_balance = amount

    # Check enough stake to unstake.
    if unstaking_balance > my_prev_delegated_stake:
        console.print(
            f":cross_mark: [red]Not enough delegated stake[/red]:[bold white]\n"
            f"  stake:{my_prev_delegated_stake}\n"
            f"  amount: {unstaking_balance}\n"
            f" coldkey: {wallet.name}[/bold white]"
        )
        return False

    # Ask before moving on.
    if prompt:
        if not Confirm.ask(
            f"Do you want to un-delegate:[bold white]\n"
            f"  amount: {unstaking_balance}\n"
            f"  from: {delegate}\n"
            f"  owner: {delegate}[/bold white]"
        ):
            return False

    try:
        with console.status(
            f":satellite: Unstaking from: [bold white]{cwtensor.network}[/bold white] ..."
        ):
            staking_response: bool = cwtensor._do_undelegation(
                wallet=wallet,
                delegate=delegate,
                amount=unstaking_balance,
                wait_for_finalization=wait_for_finalization,
            )

        if staking_response is True:  # If we successfully staked.
            # We only wait here if we expect finalization.
            if not wait_for_finalization:
                return True

            console.print(
                ":white_heavy_check_mark: [green]Finalized[/green]"
            )
            with console.status(
                f":satellite: Checking Balance on: [white]{cwtensor.network}[/white] ..."
            ):
                new_balance = cwtensor.get_balance(address=wallet.coldkey.address)
                block = cwtensor.get_current_block()
                new_delegate_stake = cwtensor.get_stake_for_coldkey_and_hotkey(
                    coldkey=wallet.coldkeypub.address,
                    hotkey=delegate,
                    block=block,
                )  # Get current stake

                console.print(
                    f"Balance:\n"
                    f"  [blue]{my_prev_coldkey_balance}[/blue] :arrow_right: [green]{new_balance}[/green]"
                )
                console.print(
                    f"Stake:\n"
                    f"  [blue]{my_prev_delegated_stake}[/blue] :arrow_right: [green]{new_delegate_stake}[/green]"
                )
                return True
        else:
            console.print(
                ":cross_mark: [red]Failed[/red]: Error unknown."
            )
            return False

    except NotRegisteredError as e:
        console.print(
            f":cross_mark: [red]Hotkey: {wallet.hotkey_str} is not registered.[/red]"
        )
        return False
    except StakeError as e:
        console.print(f":cross_mark: [red]Stake Error: {e}[/red]")
        return False
