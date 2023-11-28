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
        wait_for_inclusion: bool = False,
        wait_for_finalization: bool = True,
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
    # burn_cost = 0
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

        response = cwtensor.contract.execute(
            create_register_network_msg,
             LocalWallet(PrivateKey(wallet.coldkey.private_key), cybertensor.__chain_address_prefix__),
             1000000,
             "1000000000boot"
         ).wait_to_complete()

        # We only wait here if we expect finalization.
        # if not wait_for_finalization and not wait_for_inclusion:
        #     return True

        # process if registration successful
        if not response.response.is_successful():
            cybertensor.__console__.print(
                ":cross_mark: [red]Failed[/red]: error:{}".format(
                    response.response.raw_log
                )
            )
            time.sleep(0.5)

        # Successful registration, final check for membership
        else:
            cybertensor.__console__.print(
                # f":white_heavy_check_mark: [green]Registered subnetwork with netuid: {response.triggered_events[1].value['event']['attributes'][0]}[/green]"
                f":white_heavy_check_mark: [green]Registered subnetwork with netuid: {response.response.events.get('wasm').get('netuid_to_register')}[/green]"
            )
            return True
