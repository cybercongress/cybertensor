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

from typing import Union, Tuple

import torch
from loguru import logger
from rich.prompt import Confirm

import cybertensor
from cybertensor import __console__ as console
from cybertensor.utils import weight_utils
from cybertensor.wallet import Wallet

logger = logger.opt(colors=True)


def set_weights_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "Wallet",
    netuid: int,
    uids: Union[torch.LongTensor, list],
    weights: Union[torch.FloatTensor, list],
    version_key: int = 0,
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> Tuple[bool, str]:
    r"""Sets the given weights and values on chain for wallet hotkey account.
    Args:
        cwtensor (cybertensor.cwtensor):
            CWTensor object
        wallet (Wallet):
            cybertensor wallet object.
        netuid (int):
            netuid of the subnet to set weights for.
        uids (Union[torch.LongTensor, list]):
            uint64 uids of destination neurons.
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
    if isinstance(uids, list):
        uids = torch.tensor(uids, dtype=torch.int64)
    if isinstance(weights, list):
        weights = torch.tensor(weights, dtype=torch.float32)

    # Reformat and normalize.
    weight_uids, weight_vals = weight_utils.convert_weights_and_uids_for_emit(
        uids, weights
    )

    # Ask before moving on.
    if prompt:
        if not Confirm.ask(
            f"Do you want to set weights:\n"
            f"[bold white]  weights: {[float(v / 65535) for v in weight_vals]}\n"
            f"  uids: {weight_uids}[/bold white ]?"
        ):
            return False, "Prompt refused."

    with console.status(
        f":satellite: Setting weights on [white]{cwtensor.network}[/white] ..."
    ):
        try:
            success, error_message = cwtensor._do_set_weights(
                wallet=wallet,
                netuid=netuid,
                uids=weight_uids,
                vals=weight_vals,
                version_key=version_key,
                wait_for_finalization=wait_for_finalization,
            )

            if not wait_for_finalization:
                return True, "Not waiting for finalization."

            if success is True:
                cybertensor.__console__.print(
                    prefix="Set weights",
                    sufix="<green>Finalized: </green>" + str(success),
                )
                return True, "Successfully set weights and Finalized."
            else:
                cybertensor.__console__.print(
                    ":cross_mark: [red]Failed[/red]: error:{}".format(error_message)
                )

                cybertensor.logging.warning(
                    prefix="Set weights",
                    sufix="<red>Failed: </red>" + str(error_message),
                )
                return False, error_message

        except Exception as e:
            # TODO( devs ): lets remove all of the cybertensor.__console__ calls and replace with loguru.
            cybertensor.logging.warning(
                prefix="Set weights", sufix="<red>Failed: </red>" + str(e)
            )
            return False, str(e)
