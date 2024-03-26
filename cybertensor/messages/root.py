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
from typing import Union, List

import torch
from loguru import logger
from rich.prompt import Confirm

import cybertensor
from cybertensor import __console__ as console
from cybertensor.utils.weight_utils import normalize_max_weight, convert_weights_and_uids_for_emit
from cybertensor.wallet import Wallet

logger = logger.opt(colors=True)


def root_register_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "Wallet",
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    r"""Registers the wallet to root network.
    Args:
        wallet (Wallet):
            cybertensor wallet object.
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

    wallet.coldkey  # unlock coldkey

    is_registered = cwtensor.is_hotkey_registered(
        netuid=0, hotkey=wallet.hotkey.address
    )
    if is_registered:
        console.print(
            f":white_heavy_check_mark: [green] {wallet.name} {wallet.coldkey.address} "
            f"Already registered on root network.[/green]"
        )
        return True

    if prompt:
        # Prompt user for confirmation.
        if not Confirm.ask("Register to root network?"):
            return False

    with console.status(":satellite: Registering to root network..."):
        success = cwtensor._do_root_register(
            wallet=wallet,
            wait_for_finalization=wait_for_finalization,
        )
        time.sleep(0.5)

        # Successful registration, final check for neuron and pubkey
        if success is True:
            is_registered = cwtensor.is_hotkey_registered(
                netuid=0, hotkey=wallet.hotkey.address
            )
            if is_registered:
                console.print(
                    ":white_heavy_check_mark: [green]Registered in root[/green]"
                )
                return True
            else:
                # neuron not found, try again
                console.print(
                    ":cross_mark: [red]Unknown error. Neuron was not registered.[/red]"
                )

        return False


def set_root_weights_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "Wallet",
    netuids: Union[torch.LongTensor, list],
    weights: Union[torch.FloatTensor, list],
    version_key: int = 0,
    wait_for_finalization: bool = False,
    prompt: bool = False,
) -> bool:
    r"""Sets the given weights and values on chain for wallet hotkey account.
    Args:
        wallet (Wallet):
            cybertensor wallet object.
        netuids (List[int]):
            netuid of the subnet to set weights for.
        weights ( Union[torch.FloatTensor, list]):
            weights to set which must floats and correspond to the passed uids.
        version_key (int):
            version key of the validator.
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
    # First convert types.
    print(f"netuids {netuids}  weights {weights}")
    if isinstance(netuids, list):
        netuids = torch.tensor(netuids, dtype=torch.int64)
    if isinstance(weights, list):
        weights = torch.tensor(weights, dtype=torch.float32)

    # Get weight restrictions.
    min_allowed_weights = cwtensor.min_allowed_weights(netuid=0)
    max_weight_limit = cwtensor.max_weight_limit(netuid=0)

    # Get non zero values.
    non_zero_weight_idx = torch.argwhere(weights > 0).squeeze(dim=1)
    non_zero_weight_uids = netuids[non_zero_weight_idx]
    non_zero_weights = weights[non_zero_weight_idx]
    if non_zero_weights.numel() < min_allowed_weights:
        raise ValueError(
            f"The minimum number of weights required to set weights is {min_allowed_weights}, "
            f"got {non_zero_weights.numel()}"
        )

    # Normalize the weights to max value.
    formatted_weights = normalize_max_weight(x=weights, limit=max_weight_limit)
    console.print(f"\nRaw Weights -> Normalized weights: \n\t{weights} -> \n\t{formatted_weights}\n")

    # Ask before moving on.
    if prompt:
        if not Confirm.ask(
            f"Do you want to set the following root weights?:\n"
            f"[bold white]  weights: {formatted_weights}\n"
            f"  uids: {netuids}[/bold white ]?"
        ):
            return False

    with console.status(
        f":satellite: Setting root weights on [white]{cwtensor.network}[/white] ..."
    ):
        weight_uids, weight_vals = convert_weights_and_uids_for_emit(
            netuids, weights
        )
        return cwtensor._do_set_weights(
            wallet=wallet,
            netuid=0,
            uids=weight_uids,
            vals=weight_vals,
            version_key=version_key,
            wait_for_finalization=wait_for_finalization,
        )
