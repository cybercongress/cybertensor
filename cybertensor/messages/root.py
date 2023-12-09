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
from typing import Union, List

import torch
from loguru import logger
from rich.prompt import Confirm

import cybertensor
import cybertensor.utils.weight_utils as weight_utils

logger = logger.opt(colors=True)


def root_register_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "cybertensor.wallet",
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    r"""Registers the wallet to root network.
    Args:
        wallet (cybertensor.wallet):
            cybertensor wallet object.
        wait_for_finalization (bool):
            If set, waits for the extrinsic to be finalized on the chain before returning true,
            or returns false if the extrinsic fails to be finalized within the timeout.
        prompt (bool):
            If true, the call waits for confirmation from the user before proceeding.
    Returns:
        success (bool):
            flag is true if extrinsic was finalized or uncluded in the block.
            If we did not wait for finalization / inclusion, the response is true.
    """

    wallet.coldkey  # unlock coldkey

    is_registered = cwtensor.is_hotkey_registered(
        netuid=0, hotkey=wallet.hotkey.address
    )
    if is_registered:
        cybertensor.__console__.print(
            ":white_heavy_check_mark: [green]Already registered on root network.[/green]"
        )
        return True

    if prompt:
        # Prompt user for confirmation.
        if not Confirm.ask("Register to root network?"):
            return False

    with cybertensor.__console__.status(":satellite: Registering to root network..."):
        success, err_msg = cwtensor._do_root_register(
            wallet=wallet,
            wait_for_finalization=wait_for_finalization,
        )

        if success != True or success is False:
            cybertensor.__console__.print(
                f":cross_mark: [red]Failed[/red]: error:{err_msg}"
            )
            time.sleep(0.5)

        # Successful registration, final check for neuron and pubkey
        else:
            is_registered = cwtensor.is_hotkey_registered(
                netuid=0, hotkey=wallet.hotkey.address
            )
            if is_registered:
                cybertensor.__console__.print(
                    ":white_heavy_check_mark: [green]Registered[/green]"
                )
                return True
            else:
                # neuron not found, try again
                cybertensor.__console__.print(
                    ":cross_mark: [red]Unknown error. Neuron not found.[/red]"
                )


def set_root_weights_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "cybertensor.wallet",
    netuids: Union[torch.LongTensor, list],
    weights: Union[torch.FloatTensor, list],
    version_key: int = 0,
    wait_for_finalization: bool = False,
    prompt: bool = False,
) -> bool:
    r"""Sets the given weights and values on chain for wallet hotkey account.
    Args:
        wallet (cybertensor.wallet):
            cybertensor wallet object.
        netuids (List[int]):
            netuid of the subnet to set weights for.
        weights ( Union[torch.FloatTensor, list]):
            weights to set which must floats and correspond to the passed uids.
        version_key (int):
            version key of the validator.
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
    # First convert types.
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
    formatted_weights = cybertensor.utils.weight_utils.normalize_max_weight(
        x=weights, limit=max_weight_limit
    )
    cybertensor.__console__.print(
        f"\nNormalized weights: \n\t{weights} -> {formatted_weights}\n"
    )

    # Ask before moving on.
    if prompt:
        if not Confirm.ask(
            f"Do you want to set the following root weights?:\n"
            f"[bold white]  weights: {formatted_weights}\n"
            f"  uids: {netuids}[/bold white ]?"
        ):
            return False

    with cybertensor.__console__.status(
        f":satellite: Setting root weights on [white]{cwtensor.network}[/white] ..."
    ):
        try:
            weight_uids, weight_vals = weight_utils.convert_weights_and_uids_for_emit(
                netuids, weights
            )
            success, error_message = cwtensor._do_set_weights(
                wallet=wallet,
                netuid=0,
                uids=weight_uids,
                vals=weight_vals,
                version_key=version_key,
                wait_for_finalization=wait_for_finalization,
            )

            cybertensor.__console__.print(success, error_message)

            if not wait_for_finalization:
                return True

            if success is True:
                cybertensor.__console__.print(
                    ":white_heavy_check_mark: [green]Finalized[/green]"
                )
                cybertensor.logging.success(
                    prefix="Set weights",
                    sufix="<green>Finalized: </green>" + str(success),
                )
                return True
            else:
                cybertensor.__console__.print(
                    f":cross_mark: [red]Failed[/red]: error:{error_message}"
                )
                cybertensor.logging.warning(
                    prefix="Set weights",
                    sufix=f"<red>Failed: </red>{error_message}",
                )
                return False

        except Exception as e:
            # TODO( devs ): lets remove all of the cybertensor.__console__ calls and replace with loguru.
            cybertensor.__console__.print(
                f":cross_mark: [red]Failed[/red]: error:{e}"
            )
            cybertensor.logging.warning(
                prefix="Set weights", sufix=f"<red>Failed: </red>{e}"
            )
            return False
