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

import time

from cosmpy.aerial.wallet import LocalWallet
from cosmpy.crypto.keypairs import PrivateKey
from rich.prompt import Confirm

import cybertensor
from cybertensor import __console__ as console
from cybertensor.utils.balance import Balance
from cybertensor.wallet import Wallet


def register_subnetwork_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "Wallet",
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    """
    Registers a new subnetwork.
    Args:
        cwtensor (cybertensor.cwtensor):
            the CWTensor
        wallet (Wallet):
            cybertensor wallet object.
        wait_for_finalization (bool):
            If set, waits for the transaction to be finalized on the chain before returning ``true``,
            or returns ``false`` if the transaction fails to be finalized within the timeout.
        prompt (bool):
            If ``true``, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            Flag is ``true`` if extrinsic was finalized or included in the block.
            If we did not wait for finalization / inclusion, the response is ``true``.
    """
    your_balance = cwtensor.get_balance(wallet.coldkeypub.address)
    burn_cost = Balance(cwtensor.get_subnet_burn_cost())
    if burn_cost > your_balance:
        console.print(
            f"Your balance of: [green]{your_balance}[/green] is not enough to pay the subnet lock cost of: "
            f"[green]{burn_cost}[/green]"
        )
        return False

    if prompt:
        console.print(f"Your balance is: [green]{your_balance}[/green]")
        if not Confirm.ask(
            f"Do you want to register a subnet for [green]{burn_cost}[/green]?"
        ):
            return False

    wallet.coldkey  # unlock coldkey

    with console.status(":satellite: Registering subnet..."):
        create_register_network_msg = {"register_network": {}}
        signer_wallet = LocalWallet(
            PrivateKey(wallet.coldkey.private_key), cwtensor.address_prefix
        )
        gas = cybertensor.__default_gas__
        funds = burn_cost.__int__().__str__().__add__(cwtensor.token)

        if not wait_for_finalization:
            tx = cwtensor.contract.execute(
                create_register_network_msg, signer_wallet, gas, funds
            )
            console.print(
                f":exclamation_mark: [yellow]Warning[/yellow]: TX {tx.tx_hash} broadcasted without finalization "
                f"confirmation..."
            )
        else:
            tx = cwtensor.contract.execute(
                create_register_network_msg, signer_wallet, gas, funds
            )
            console.print(
                f":satellite: [green]Processing..[/green]: TX {tx.tx_hash} waiting to complete..."
            )
            try:
                tx.wait_to_complete()
                if tx.response.is_successful():
                    console.print(
                        f":white_heavy_check_mark: [green]Registered subnetwork with netuid: "
                        f"{tx.response.events.get('wasm').get('netuid_to_register')}[/green]"
                    )
                    return True
                else:
                    console.print(
                        f":cross_mark: [red]Failed[/red]: error:{tx.response.raw_log}"
                    )
                    time.sleep(0.5)
                    return False
            except Exception as e:
                console.print(f":cross_mark: [red]Failed[/red]: error:{e}")
                return False


def find_event_attributes_in_extrinsic_receipt(response, event_name) -> list:
    for event in response.triggered_events:
        # Access the event details
        event_details = event.value["event"]
        # Check if the event_id is 'NetworkAdded'
        if event_details["event_id"] == event_name:
            # Once found, you can access the attributes of the event_name
            return event_details["attributes"]
    return [-1]


from cybertensor.commands.network import HYPERPARAMS


def set_hyperparameter_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "Wallet",
    netuid: int,
    parameter: str,
    value,
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    """
    Sets a hyperparameter for a specific subnetwork.
    Args:
        cwtensor (cybertensor.cwtensor):
            the CWTensor
        wallet (Wallet):
            cybertensor wallet object.
        netuid (int):
            Subnetwork uid.
        parameter (str):
            Hyperparameter name.
        value (any):
            New hyperparameter value.
        wait_for_finalization (bool):
            If set, waits for the transaction to be finalized on the chain before returning ``true``,
            or returns ``false`` if the transaction fails to be finalized within the timeout.
        prompt (bool):
            If ``true``, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            Flag is ``true`` if extrinsic was finalized or included in the block.
            If we did not wait for finalization / inclusion, the response is ``true``.
    """

    if cwtensor.get_subnet_owner(netuid) != wallet.coldkeypub.address:
        console.print(
            ":cross_mark: [red]This wallet doesn't own the specified subnet.[/red]"
        )
        return False

    wallet.coldkey  # unlock coldkey

    message = HYPERPARAMS.get(parameter)
    if message is None:
        console.print(":cross_mark: [red]Invalid hyperparameter specified.[/red]")
        return False

    with console.status(
        f":satellite: Setting hyperparameter {parameter} to {value} on subnet: {netuid} ..."
    ):
        sudo_msg = {
            str(message): {"netuid": netuid, str(parameter): int(value)},
        }
        signer_wallet = LocalWallet(
            PrivateKey(wallet.coldkey.private_key), cwtensor.address_prefix
        )
        gas = cybertensor.__default_gas__

        if not wait_for_finalization:
            tx = cwtensor.contract.execute(sudo_msg, signer_wallet, gas)
            console.print(
                f":exclamation_mark: [yellow]Warning[/yellow]: TX {tx.tx_hash} broadcasted without confirmation..."
            )
        else:
            tx = cwtensor.contract.execute(sudo_msg, signer_wallet, gas)
            console.print(
                f":satellite: [green]Processing..[/green]: TX {tx.tx_hash} waiting to complete..."
            )
            try:
                tx.wait_to_complete()
                if tx.response.is_successful():
                    console.print(
                        f":white_heavy_check_mark: [green]Hyper parameter {parameter} changed to {value}[/green]"
                    )
                    return True
                else:
                    console.print(
                        f":cross_mark: [red]Failed[/red]: error:{tx.response.raw_log}"
                    )
                    time.sleep(0.5)
                    return False
            except Exception as e:
                console.print(f":cross_mark: [red]Failed[/red]: error:{e}")
                return False
