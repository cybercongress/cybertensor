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

import time

from cosmpy.aerial.wallet import LocalWallet
from cosmpy.crypto.keypairs import PrivateKey
from rich.prompt import Confirm

import cybertensor
from cybertensor import Balance


def register_subnetwork_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "cybertensor.wallet",
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    r"""Registers a new subnetwork
    Args:
        cwtensor (cybertensor.cwtensor):
            the CWTensor
        wallet (cybertensor.wallet):
            cybertensor wallet object.
        wait_for_finalization (bool):
            If set, waits for the transaction to be finalized on the chain before returning true,
            or returns false if the transaction fails to be finalized within the timeout.
        prompt (bool):
            If true, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            flag is true if extrinsic was finalized or included in the block.
            If we did not wait for finalization / inclusion, the response is true.
    """
    your_balance = cwtensor.get_balance(wallet.coldkeypub.address)
    burn_cost = Balance(cwtensor.get_subnet_burn_cost())
    if burn_cost > your_balance:
        cybertensor.__console__.print(
            f"Your balance of: [green]{your_balance}[/green] is not enough to pay the subnet lock cost of: "
            f"[green]{burn_cost}[/green]"
        )
        return False

    if prompt:
        cybertensor.__console__.print(f"Your balance is: [green]{your_balance}[/green]")
        if not Confirm.ask(
            f"Do you want to register a subnet for [green]{burn_cost}[/green]?"
        ):
            return False

    wallet.coldkey  # unlock coldkey

    with cybertensor.__console__.status(":satellite: Registering subnet..."):
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
            cybertensor.__console__.print(
                f":exclamation_mark: [yellow]Warning[/yellow]: TX {tx.tx_hash} broadcasted without finalization "
                f"confirmation..."
            )
        else:
            tx = cwtensor.contract.execute(
                create_register_network_msg, signer_wallet, gas, funds
            )
            cybertensor.__console__.print(
                f":satellite: [green]Processing..[/green]: TX {tx.tx_hash} waiting to complete..."
            )
            try:
                tx.wait_to_complete()
                if tx.response.is_successful():
                    cybertensor.__console__.print(
                        f":white_heavy_check_mark: [green]Registered subnetwork with netuid: "
                        f"{tx.response.events.get('wasm').get('netuid_to_register')}[/green]"
                    )
                    return True
                else:
                    cybertensor.__console__.print(
                        f":cross_mark: [red]Failed[/red]: error:{tx.response.raw_log}"
                    )
                    time.sleep(0.5)
                    return False
            except Exception as e:
                cybertensor.__console__.print(
                    f":cross_mark: [red]Failed[/red]: error:{e}"
                )
                return False


from ..commands.network import HYPERPARAMS


def set_hyperparameter_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "cybertensor.wallet",
    netuid: int,
    parameter: str,
    value,
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    r"""Sets a hyperparameter for a specific subnetwork.
    Args:
        cwtensor (cybertensor.cwtensor):
            the CWTensor
        wallet (cybertensor.wallet):
            cybertensor wallet object.
        netuid (int):
            Subnetwork uid.
        parameter (str):
            Hyperparameter name.
        value (any):
            New hyperparameter value.
        wait_for_finalization (bool):
            If set, waits for the transaction to be finalized on the chain before returning true,
            or returns false if the transaction fails to be finalized within the timeout.
        prompt (bool):
            If true, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            flag is true if extrinsic was finalized or included in the block.
            If we did not wait for finalization / inclusion, the response is true.
    """

    if cwtensor.get_subnet_owner(netuid) != wallet.coldkeypub.address:
        cybertensor.__console__.print(
            ":cross_mark: [red]This wallet doesn't own the specified subnet.[/red]"
        )
        return False

    wallet.coldkey  # unlock coldkey

    message = HYPERPARAMS.get(parameter)
    if message is None:
        cybertensor.__console__.print(
            ":cross_mark: [red]Invalid hyperparameter specified.[/red]"
        )
        return False

    with cybertensor.__console__.status(
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
            cybertensor.__console__.print(
                f":exclamation_mark: [yellow]Warning[/yellow]: TX {tx.tx_hash} broadcasted without confirmation..."
            )
        else:
            tx = cwtensor.contract.execute(sudo_msg, signer_wallet, gas)
            cybertensor.__console__.print(
                f":satellite: [green]Processing..[/green]: TX {tx.tx_hash} waiting to complete..."
            )
            try:
                tx.wait_to_complete()
                if tx.response.is_successful():
                    cybertensor.__console__.print(
                        f":white_heavy_check_mark: [green]Hyper parameter {parameter} changed to {value}[/green]"
                    )
                    return True
                else:
                    cybertensor.__console__.print(
                        f":cross_mark: [red]Failed[/red]: error:{tx.response.raw_log}"
                    )
                    time.sleep(0.5)
                    return False
            except Exception as e:
                cybertensor.__console__.print(
                    f":cross_mark: [red]Failed[/red]: error:{e}"
                )
                return False
