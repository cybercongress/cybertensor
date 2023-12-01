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
import json
import time

from cosmpy.aerial.client import Coin
from cosmpy.aerial.wallet import LocalWallet
from cosmpy.crypto.keypairs import PrivateKey

import cybertensor
# import cybertensor.utils.networking as net
from dataclasses import asdict
from rich.prompt import Confirm


def register_subnetwork_message(
        cwtensor: "cybertensor.cwtensor",
        wallet: "cybertensor.wallet",
        wait_for_inclusion: bool = True,
        wait_for_finalization: bool = False,
        prompt: bool = False,
) -> bool:
    r"""Registers a new subnetwork
    Args:
        wallet (cybertensor.wallet):
            bittensor wallet object.
        wait_for_inclusion (bool):
            If set, waits for the extrinsic to enter a block before returning true,
            or returns false if the extrinsic fails to enter the block within the timeout.
        wait_for_finalization (bool):
            If set, waits for the extrinsic to be finalized on the chain before returning true,
            or returns false if the extrinsic fails to be finalized within the timeout.
        prompt (bool):
            If true, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            flag is true if extrinsic was finalized or included in the block.
            If we did not wait for finalization / inclusion, the response is true.
    """
    your_balance = cwtensor.client.query_bank_balance(wallet.coldkeypub.address, cybertensor.__token__)
    burn_cost = cwtensor.get_subnet_burn_cost()
    if burn_cost > your_balance:
        cybertensor.__console__.print(
            f"Your balance of: [green]{your_balance} {cybertensor.__token__}[/green] is not enough to pay the subnet lock cost of: [green]{burn_cost} {cybertensor.__token__}[/green]"
        )
        return False

    if prompt:
        cybertensor.__console__.print(f"Your balance is: [green]{your_balance} {cybertensor.__token__}[/green]")
        if not Confirm.ask(
                f"Do you want to register a subnet for [green]{burn_cost} {cybertensor.__token__}[/green]?"
        ):
            return False

    wallet.coldkey  # unlock coldkey

    with cybertensor.__console__.status(":satellite: Registering subnet..."):
        create_register_network_msg = {
            "register_network": {}
        }
        wallet = LocalWallet(PrivateKey(wallet.coldkey.private_key), cybertensor.__chain_address_prefix__)
        gas = cybertensor.__default_gas__
        # burn_cost = burn_cost.__str__().__add__(cybertensor.__token__)
        burn_cost = '1boot'

        if not wait_for_inclusion:
            tx = cwtensor.contract.execute(create_register_network_msg, wallet, gas, burn_cost)
            cybertensor.__console__.print(
                f":exclamation_mark: [yellow]Warning[/yellow]: TX {tx.tx_hash} broadcasted without confirmation. Check the TX hash manually."
            )
        else:
            tx = cwtensor.contract.execute(create_register_network_msg, wallet, gas, burn_cost)
            cybertensor.__console__.print(
                f":satellite: [green]Processing..[/green]: TX {tx.tx_hash} waiting to complete..."
            )
            try:
                tx.wait_to_complete()
                if tx.response.is_successful():
                    cybertensor.__console__.print(
                        f":white_heavy_check_mark: [green]Registered subnetwork with netuid: {tx.response.events.get('wasm').get('netuid_to_register')} tx: {tx.tx_hash}[/green]"
                    )
                    return True
                else:
                    cybertensor.__console__.print(
                        f":cross_mark: [red]Failed[/red]: error:{tx.response.raw_log}"
                    )
                    return False
            except Exception as e:
                cybertensor.__console__.print(
                        f":cross_mark: [red]Failed[/red]: error:{e}"
                    )
                return False

        # process if registration successful

        # -- executed in try-except section --

        # if not tx.response.is_successful():
        #     # TODO catch error. RECHECK TODO
        #     cybertensor.__console__.print(
        #         f":cross_mark: [red]Failed[/red]: error:{tx.response.raw_log}"
        #     )
        #     time.sleep(0.5)

        # Successful registration, final check for membership

        # -- executed in try-except section --

        # else:
        #     cybertensor.__console__.print(
        #         f":white_heavy_check_mark: [green]Registered subnetwork with netuid: {tx.response.events.get('wasm').get('netuid_to_register')} tx: {tx.tx_hash}[/green]"
        #     )
        #     return True

from ..commands.network import HYPERPARAMS


def set_hyperparameter_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "cybertensor.wallet",
    netuid: int,
    parameter: str,
    value,
    wait_for_inclusion: bool = True,
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    r"""Sets a hyperparameter for a specific subnetwork.
    Args:
        wallet (cybertensor.wallet):
            bittensor wallet object.
        netuid (int):
            Subnetwork uid.
        parameter (str):
            Hyperparameter name.
        value (any):
            New hyperparameter value.
        wait_for_inclusion (bool):
            If set, waits for the extrinsic to enter a block before returning true,
            or returns false if the extrinsic fails to enter the block within the timeout.
        wait_for_finalization (bool):
            If set, waits for the extrinsic to be finalized on the chain before returning true,
            or returns false if the extrinsic fails to be finalized within the timeout.
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
    if message == None:
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
        wallet = LocalWallet(PrivateKey(wallet.coldkey.private_key), cybertensor.__chain_address_prefix__)
        gas = cybertensor.__default_gas__

        if not wait_for_inclusion:
            tx = cwtensor.contract.execute(sudo_msg, wallet, gas)
            cybertensor.__console__.print(
                f":exclamation_mark: [yellow]Warning[/yellow]: TX {tx.tx_hash} broadcasted without confirmation. Check the TX hash manually."
            )
        else:
            tx = cwtensor.contract.execute(sudo_msg, wallet, gas)
            cybertensor.__console__.print(
                f":satellite: [green]Processing..[/green]: TX {tx.tx_hash} waiting to complete..."
            )
            try:
                tx.wait_to_complete()
                if tx.response.is_successful():
                    cybertensor.__console__.print(
                        f":white_heavy_check_mark: [green]Registered subnetwork with netuid: {tx.response.events.get('wasm').get('netuid_to_register')} tx: {tx.tx_hash}[/green]"
                    )
                    return True
                else:
                    cybertensor.__console__.print(
                        f":cross_mark: [red]Failed[/red]: error:{tx.response.raw_log}"
                    )
                    return False
            except Exception as e:
                cybertensor.__console__.print(
                        f":cross_mark: [red]Failed[/red]: error:{e}"
                    )
                return False


        # try:
        #     response = cwtensor.contract.execute(
        #         sudo_msg,
        #         LocalWallet(PrivateKey(wallet.coldkey.private_key), cybertensor.__chain_address_prefix__),
        #         cybertensor.__default_gas__,
        #     ).wait_to_complete()
        # except Exception as e:
        #     cybertensor.__console__.print(
        #         f":cross_mark: [red]Failed[/red]: error:{e}"
        #     )
        #     response = None

        # We only wait here if we expect finalization.
        # if not wait_for_finalization and not wait_for_inclusion:
        #     return True

        # process if error in the broadcast
        # if not response:
        #     cybertensor.__console__.print(
        #         ":cross_mark: [red]Failed[/red]: error: broadcast is failed"
        #     )

        # process if registration successful
        # elif not response.response.is_successful():
            # TODO catch error
            # cybertensor.__console__.print(
            #     ":cross_mark: [red]Failed[/red]: error:{}".format(
            #         response.response.raw_log
            #     )
            # )
            # time.sleep(0.5)

        # Successful registration, final check for membership
        # else:
        #     cybertensor.__console__.print(
        #         f":white_heavy_check_mark: [green]Hyper parameter {parameter} changed to {value}[/green]"
        #     )
        #     return True
