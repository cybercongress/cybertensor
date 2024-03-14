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
from typing import List, Union, Optional, Tuple

import torch
from rich.prompt import Confirm

import cybertensor
from cybertensor import __console__ as console
from cybertensor.utils.registration import POWSolution, create_pow
from cybertensor.wallet import Wallet


def register_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "Wallet",
    netuid: int,
    wait_for_finalization: bool = True,
    prompt: bool = False,
    max_allowed_attempts: int = 3,
    output_in_place: bool = True,
    cuda: bool = False,
    dev_id: Union[List[int], int] = 0,
    tpb: int = 256,
    num_processes: Optional[int] = None,
    update_interval: Optional[int] = None,
    log_verbose: bool = False,
) -> bool:
    r"""Registers the wallet to chain.
    Args:
        wallet (Wallet):
            cybertensor wallet object.
        netuid (int):
            The netuid of the subnet to register on.
        wait_for_finalization (bool):
            If set, waits for the extrinsic to be finalized on the chain before returning ``true``,
            or returns ``false`` if the extrinsic fails to be finalized within the timeout.
        prompt (bool):
            If ``true``, the call waits for confirmation from the user before proceeding.
        max_allowed_attempts (int):
            Maximum number of attempts to register the wallet.
        cuda (bool):
            If true, the wallet should be registered using CUDA device(s).
        dev_id (Union[List[int], int]):
            The CUDA device id to use, or a list of device ids.
        tpb (int):
            The number of threads per block (CUDA).
        num_processes (int):
            The number of processes to use to register.
        update_interval (int):
            The number of nonces to solve between updates.
        log_verbose (bool):
            If true, the registration process will log more information.
    Returns:
        success (bool):
            Flag is ``true`` if extrinsic was finalized or uncluded in the block.
            If we did not wait for finalization / inclusion, the response is ``true``.
    """
    if not cwtensor.subnet_exists(netuid):
        console.print(
            f":cross_mark: [red]Failed[/red]: error: [bold white]subnet:{netuid}[/bold white] does not exist."
        )
        return False

    with console.status(
        f":satellite: Checking Account on [bold]subnet:{netuid}[/bold]..."
    ):
        neuron = cwtensor.get_neuron_for_pubkey_and_subnet(
            wallet.hotkey.address, netuid=netuid
        )
        if not neuron.is_null:
            cybertensor.logging.debug(
                f"Wallet {wallet} is already registered on {neuron.netuid} with {neuron.uid}"
            )
            return True

    if prompt:
        if not Confirm.ask(
            f"Continue Registration?\n"
            f"  hotkey:     [bold white]{wallet.hotkey.address}[/bold white]\n"
            f"  coldkey:    [bold white]{wallet.coldkeypub.address}[/bold white]\n"
            f"  network:    [bold white]{cwtensor.network}[/bold white]"
        ):
            return False

    # Attempt rolling registration.
    attempts = 1
    while True:
        console.print(
            f":satellite: Registering...({attempts}/{max_allowed_attempts})"
        )
        # Solve latest POW.
        if cuda:
            if not torch.cuda.is_available():
                if prompt:
                    console.error("CUDA is not available.")
                return False
            pow_result: Optional[POWSolution] = create_pow(
                cwtensor,
                wallet,
                netuid,
                output_in_place,
                cuda=cuda,
                dev_id=dev_id,
                tpb=tpb,
                num_processes=num_processes,
                update_interval=update_interval,
                log_verbose=log_verbose,
            )
        else:
            pow_result: Optional[POWSolution] = create_pow(
                cwtensor,
                wallet,
                netuid,
                output_in_place,
                cuda=cuda,
                num_processes=num_processes,
                update_interval=update_interval,
                log_verbose=log_verbose,
            )

        # pow failed
        if not pow_result:
            # might be registered already on this subnet
            is_registered = cwtensor.is_hotkey_registered(
                netuid=netuid, hotkey=wallet.hotkey.address
            )
            if is_registered:
                console.print(
                    f":white_heavy_check_mark: [green]Already registered on netuid:{netuid}[/green]"
                )
                return True

        # pow successful, proceed to submit pow to chain for registration
        else:
            with console.status(":satellite: Submitting POW..."):
                # check if pow result is still valid
                while not pow_result.is_stale(cwtensor=cwtensor):
                    result: Tuple[bool, Optional[str]] = cwtensor._do_pow_register(
                        netuid=netuid,
                        wallet=wallet,
                        pow_result=pow_result,
                        wait_for_finalization=wait_for_finalization,
                    )
                    success, err_msg = result

                    if success != True or success is False:
                        if "key is already registered" in err_msg:
                            # Error meant that the key is already registered.
                            console.print(
                                f":white_heavy_check_mark: [green]Already Registered on [bold]subnet:{netuid}[/bold][/green]"
                            )
                            return True

                        console.print(
                            f":cross_mark: [red]Failed[/red]: error:{err_msg}"
                        )
                        time.sleep(0.5)

                    # Successful registration, final check for neuron and pubkey
                    else:
                        console.print(":satellite: Checking Balance...")
                        is_registered = cwtensor.is_hotkey_registered(
                            netuid=netuid, hotkey=wallet.hotkey.address
                        )
                        if is_registered:
                            console.print(
                                ":white_heavy_check_mark: [green]Registered[/green]"
                            )
                            return True
                        else:
                            # neuron not found, try again
                            console.print(
                                ":cross_mark: [red]Unknown error. Neuron not found.[/red]"
                            )
                            continue
                else:
                    # Exited loop because pow is no longer valid.
                    console.print("[red]POW is stale.[/red]")
                    # Try again.
                    continue

        if attempts < max_allowed_attempts:
            # Failed registration, retry pow
            attempts += 1
            console.print(
                f":satellite: Failed registration, retrying pow ...({attempts}/{max_allowed_attempts})"
            )
        else:
            # Failed to register after max attempts.
            console.print("[red]No more attempts.[/red]")
            return False


def burned_register_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "Wallet",
    netuid: int,
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    r"""Registers the wallet to chain by recycling GBOOT.
    Args:
        wallet (Wallet):
            cybertensor wallet object.
        netuid (int):
            The netuid of the subnet to register on.
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
    if not cwtensor.subnet_exists(netuid):
        console.print(
            f":cross_mark: [red]Failed[/red]: error: [bold white]subnet:{netuid}[/bold white] does not exist."
        )
        return False

    wallet.coldkey  # unlock coldkey
    with console.status(
        f":satellite: Checking Account on [bold]subnet:{netuid}[/bold]..."
    ):
        neuron = cwtensor.get_neuron_for_pubkey_and_subnet(
            wallet.hotkey.address, netuid=netuid
        )

        old_balance = cwtensor.get_balance(wallet.coldkeypub.address)

        recycle_amount = cwtensor.recycle(netuid=netuid)

        if not neuron.is_null:
            console.print(
                f":white_heavy_check_mark: [green]Already Registered[/green]:\n"
                f"uid: [bold white]{neuron.uid}[/bold white]\n"
                f"netuid: [bold white]{neuron.netuid}[/bold white]\n"
                f"hotkey: [bold white]{neuron.hotkey}[/bold white]\n"
                f"coldkey: [bold white]{neuron.coldkey}[/bold white]"
            )
            return True

    if prompt:
        # Prompt user for confirmation.
        if not Confirm.ask(f"Recycle {recycle_amount} to register on subnet:{netuid}?"):
            return False

    with console.status(":satellite: Recycling BOOT for Registration..."):
        success, err_msg = cwtensor._do_burned_register(
            netuid=netuid,
            burn=recycle_amount.__int__(),
            wallet=wallet,
            wait_for_finalization=wait_for_finalization,
        )

        if success is not True:
            console.print(
                f":cross_mark: [red]Failed[/red]: error:{err_msg}"
            )
            time.sleep(0.5)

        # Successful registration, final check for neuron and pubkey
        else:
            console.print(":satellite: Checking Balance...")
            new_balance = cwtensor.get_balance(
                wallet.coldkeypub.address
            )

            console.print(
                f"Balance:\n"
                f"  [blue]{old_balance}[/blue] :arrow_right: [green]{new_balance}[/green]"
            )
            is_registered = cwtensor.is_hotkey_registered(
                netuid=netuid, hotkey=wallet.hotkey.address
            )
            if is_registered:
                console.print(
                    ":white_heavy_check_mark: [green]Registered[/green]"
                )
                return True
            else:
                # neuron not found, try again
                console.print(
                    ":cross_mark: [red]Unknown error. Neuron not found.[/red]"
                )


def swap_hotkey_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "cybertensor.Wallet",
    new_wallet: "cybertensor.Wallet",
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    wallet.coldkey  # unlock coldkey
    if prompt:
        # Prompt user for confirmation.
        if not Confirm.ask(
            f"Swap {wallet.hotkey} for new hotkey: {new_wallet.hotkey}?"
        ):
            return False

    with cybertensor.__console__.status(":satellite: Swapping hotkeys..."):
        success, err_msg = cwtensor._do_swap_hotkey(
            wallet=wallet,
            new_wallet=new_wallet,
            wait_for_finalization=wait_for_finalization,
        )

        if success is not True or success is False:
            cybertensor.__console__.print(
                ":cross_mark: [red]Failed[/red]: error:{}".format(err_msg)
            )
            time.sleep(0.5)

        else:
            cybertensor.__console__.print(
                f"Hotkey {wallet.hotkey} swapped for new hotkey: {new_wallet.hotkey}"
            )
