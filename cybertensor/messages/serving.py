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

from rich.prompt import Confirm

import cybertensor
import cybertensor.utils.networking as net
from cybertensor.types import AxonServeCallParams


def serve_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "cybertensor.wallet",
    ip: str,
    port: int,
    protocol: int,
    netuid: int,
    placeholder1: int = 0,
    placeholder2: int = 0,
    wait_for_finalization=True,
    prompt: bool = False,
) -> bool:
    r"""Subscribes an cybertensor endpoint to the substensor chain.
    Args:
        wallet (cybertensor.wallet):
            cybertensor wallet object.
        ip (str):
            endpoint host port i.e. 192.122.31.4
        port (int):
            endpoint port number i.e. 9221
        protocol (int):
            int representation of the protocol
        netuid (int):
            network uid to serve on.
        placeholder1 (int):
            placeholder for future use.
        placeholder2 (int):
            placeholder for future use.
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
    # Decrypt hotkey
    wallet.hotkey
    params: "AxonServeCallParams" = {
        "netuid": netuid,
        "version": cybertensor.__version_as_int__,
        "ip": net.ip_to_int(ip),
        "port": port,
        "ip_type": net.ip_version(ip),
        # "hotkey": wallet.hotkey.address,
        # "coldkey": wallet.coldkeypub.address,
        "protocol": protocol,
        "placeholder1": placeholder1,
        "placeholder2": placeholder2,
    }
    cybertensor.logging.debug("Checking axon ...")
    neuron = cwtensor.get_neuron_for_pubkey_and_subnet(
        wallet.hotkey.address, netuid=netuid
    )
    neuron_up_to_date = not neuron.is_null and params == {
        "version": neuron.axon_info.version,
        "ip": net.ip_to_int(neuron.axon_info.ip),
        "port": neuron.axon_info.port,
        "ip_type": neuron.axon_info.ip_type,
        "netuid": neuron.netuid,
        "hotkey": neuron.hotkey,
        "coldkey": neuron.coldkey,
        "protocol": neuron.axon_info.protocol,
        "placeholder1": neuron.axon_info.placeholder1,
        "placeholder2": neuron.axon_info.placeholder2,
    }
    output = params.copy()
    output["coldkey"] = wallet.coldkeypub.address
    output["hotkey"] = wallet.hotkey.address
    if neuron_up_to_date:
        cybertensor.logging.debug(
            f"Axon already served on: AxonInfo({wallet.hotkey.address},{ip}:{port}) "
        )
        return True

    if prompt:
        output = params.copy()
        output["coldkey"] = wallet.coldkeypub.address
        output["hotkey"] = wallet.hotkey.address
        if not Confirm.ask(
            f"Do you want to serve axon:\n"
            f"  [bold white]{json.dumps(output, indent=4, sort_keys=True)}[/bold white]"
        ):
            return False

    cybertensor.logging.debug(
        f"Serving axon with: AxonInfo({wallet.hotkey.address},{ip}:{port}) -> {cwtensor.network}:{netuid}"
    )
    success, error_message = cwtensor._do_serve_axon(
        wallet=wallet,
        call_params=params,
        wait_for_finalization=wait_for_finalization,
    )

    if wait_for_finalization:
        if success is True:
            cybertensor.logging.debug(
                f"Axon served with: AxonInfo({wallet.hotkey.address},{ip}:{port}) on {cwtensor.network}:{netuid} "
            )
            return True
        else:
            cybertensor.logging.debug(
                f"Axon failed to served with error: {error_message} "
            )
            return False
    else:
        return True


def serve_axon_message(
    cwtensor: "cybertensor.cwtensor",
    netuid: int,
    axon: "cybertensor.axon",
    wait_for_finalization: bool = True,
    prompt: bool = False,
) -> bool:
    r"""Serves the axon to the network.
    Args:
        netuid ( int ):
            The netuid being served on.
        axon (cybertensor.Axon):
            Axon to serve.
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
    axon.wallet.hotkey
    axon.wallet.coldkeypub
    external_port = axon.external_port

    # ---- Get external ip ----
    if axon.external_ip is None:
        try:
            external_ip = net.get_external_ip()
            cybertensor.__console__.print(
                f":white_heavy_check_mark: [green]Found external ip: {external_ip}[/green]"
            )
            cybertensor.logging.success(
                prefix="External IP", sufix=f"<blue>{external_ip}</blue>"
            )
        except Exception as e:
            raise RuntimeError(
                f"Unable to attain your external ip. Check your internet connection. error: {e}"
            ) from e
    else:
        external_ip = axon.external_ip

    # ---- Subscribe to chain ----
    serve_success = cwtensor.serve(
        wallet=axon.wallet,
        ip=external_ip,
        port=external_port,
        netuid=netuid,
        protocol=4,
        wait_for_finalization=wait_for_finalization,
        prompt=prompt,
    )
    return serve_success
