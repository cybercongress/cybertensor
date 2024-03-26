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


from typing import Union

from cosmpy.crypto.address import Address
from rich.prompt import Confirm

import cybertensor
from cybertensor.utils import is_valid_address
from cybertensor.utils.balance import Balance
from cybertensor.wallet import Wallet
from cybertensor import __console__ as console


def transfer_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "Wallet",
    dest: Union[Address, str],
    amount: Union[Balance, float],
    wait_for_finalization: bool = False,
    keep_alive: bool = True,
    prompt: bool = False,
) -> bool:
    r"""Transfers funds from this wallet to the destination public key address
    Args:
        wallet (Wallet):
            cybertensor wallet object to make transfer from.
        dest (Union[cosmpy.crypto.address.Address, str]):
            Destination public key address of a receiver.
        amount (Union[Balance, int]):
            Amount to stake as cybertensor balance, or ``float`` interpreted as GBOOT.
        wait_for_finalization (bool):
            If set, waits for the extrinsic to be finalized on the chain before returning ``true``,
            or returns ``false`` if the extrinsic fails to be finalized within the timeout.
        keep_alive (bool):
            If set, keeps the account alive by keeping the balance above the existential deposit.
        prompt (bool):
            If ``true``, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            Flag is ``true`` if extrinsic was finalized or uncluded in the block.
            If we did not wait for finalization / inclusion, the response is ``true``.
    """
    # Validate destination address.
    if not is_valid_address(dest):
        console.print(
            f":cross_mark: [red]Invalid destination address[/red]:[bold white]\n  {dest}[/bold white]"
        )
        return False

    # Unlock wallet coldkey.
    wallet.coldkey

    # Convert to Balance
    if not isinstance(amount, Balance):
        transfer_balance = Balance.from_gboot(amount)
    else:
        transfer_balance = amount

    # Check balance.
    with console.status(":satellite: Checking Balance..."):
        account_balance = cwtensor.get_balance(wallet.coldkey.address)
        # check existential deposit.
        existential_deposit = cwtensor.get_existential_deposit()

    with console.status(":satellite: Transferring..."):
        fee = cwtensor.get_transfer_fee()

    if not keep_alive:
        # Check if the transfer should keep_alive the account
        existential_deposit = Balance(0)

    # Check if we have enough balance.
    if account_balance < (transfer_balance + fee + existential_deposit):
        console.print(
            f":cross_mark: [red]Not enough balance[/red]:[bold white]\n"
            f"  balance: {account_balance}\n"
            f"  amount: {transfer_balance}\n"
            f"  for fee: {fee}[/bold white]"
        )
        return False

    # Ask before moving on.
    if prompt:
        if not Confirm.ask(
            f"Do you want to transfer:[bold white]\n"
            f"  amount: {transfer_balance}\n"
            f"  from: {wallet.name}:{wallet.coldkey.address}\n"
            f"  to: {dest}\n"
            f"  for fee: {fee}[/bold white]"
        ):
            return False

    with console.status(":satellite: Transferring..."):
        success, tx_hash, err_msg = cwtensor._do_transfer(
            wallet,
            Address(dest),
            transfer_balance,
            wait_for_finalization=wait_for_finalization,
        )

        if success:
            console.print(
                ":white_heavy_check_mark: [green]Finalized[/green]"
            )
            console.print(f"[green]Tx Hash: {tx_hash}[/green]")

            explorer_url = cybertensor.utils.get_explorer_url_for_network(
                network_config=cwtensor.network_config, tx_hash=tx_hash
            )
            if explorer_url is not None:
                console.print(
                    f"[green]Explorer Link: {explorer_url}[/green]"
                )
        else:
            console.print(
                f":cross_mark: [red]Failed[/red]: error:{err_msg}"
            )

    if success:
        with console.status(":satellite: Checking Balance..."):
            new_balance = cwtensor.get_balance(wallet.coldkey.address)
            console.print(
                f"Balance:\n"
                f"  [blue]{account_balance}[/blue] :arrow_right: [green]{new_balance}[/green]"
            )
            return True

    return False
