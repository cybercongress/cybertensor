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

import json

import cybertensor
from cybertensor import __console__ as console
from cybertensor.types import PrometheusServeCallParams
from cybertensor.utils import networking as net
from cybertensor.wallet import Wallet


def prometheus_message(
    cwtensor: "cybertensor.cwtensor",
    wallet: "Wallet",
    port: int,
    netuid: int,
    ip: int = None,
    wait_for_finalization=True,
) -> bool:
    r"""Subscribes a cybertensor endpoint to the chain.
    Args:
        cwtensor (cybertensor.cwtensor):
            cybertensor cwtensor object.
        wallet (Wallet):
            cybertensor wallet object.
        ip (str):
            endpoint host port i.e. ``192.122.31.4``
        port (int):
            endpoint port number i.e. ``9221``
        netuid (int):
            network uid to serve on.
        wait_for_finalization (bool):
            If set, waits for the extrinsic to be finalized on the chain before returning ``true``,
            or returns ``false`` if the extrinsic fails to be finalized within the timeout.
    Returns:
        success (bool):
            Flag is ``true`` if extrinsic was finalized or uncluded in the block.
            If we did not wait for finalization / inclusion, the response is ``true``.
    """

    # ---- Get external ip ----
    if ip is None:
        try:
            external_ip = net.get_external_ip()
            console.print(
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
        external_ip = ip

    call_params: "PrometheusServeCallParams" = {
        "version": cybertensor.__version_as_int__,
        "ip": net.ip_to_int(external_ip),
        "port": port,
        "ip_type": net.ip_version(external_ip),
    }

    with console.status(":satellite: Checking Prometheus..."):
        neuron = cwtensor.get_neuron_for_pubkey_and_subnet(
            wallet.hotkey.address, netuid=netuid
        )
        neuron_up_to_date = not neuron.is_null and call_params == {
            "version": neuron.prometheus_info.version,
            "ip": net.ip_to_int(neuron.prometheus_info.ip),
            "port": neuron.prometheus_info.port,
            "ip_type": neuron.prometheus_info.ip_type,
        }

    if neuron_up_to_date:
        console.print(
            f":white_heavy_check_mark: [green]Prometheus already Served[/green]\n"
            f"[green not bold]- Status: [/green not bold] |"
            f"[green not bold] ip: [/green not bold][white not bold]{net.int_to_ip(neuron.prometheus_info.ip)}[/white not bold] |"
            f"[green not bold] ip_type: [/green not bold][white not bold]{neuron.prometheus_info.ip_type}[/white not bold] |"
            f"[green not bold] port: [/green not bold][white not bold]{neuron.prometheus_info.port}[/white not bold] | "
            f"[green not bold] version: [/green not bold][white not bold]{neuron.prometheus_info.version}[/white not bold] |"
        )

        console.print(
            f":white_heavy_check_mark: [white]Prometheus already served.[/white] {external_ip}"
        )
        return True

    # Add netuid, not in prometheus_info
    call_params["netuid"] = netuid

    with console.status(
        f":satellite: Serving prometheus on: [white]{cwtensor.network}:{netuid}[/white] ..."
    ):
        success, err = cwtensor._do_serve_prometheus(
            wallet=wallet,
            call_params=call_params,
            wait_for_finalization=wait_for_finalization,
        )

        if wait_for_finalization:
            if success is True:
                console.print(
                    f":white_heavy_check_mark: [green]Served prometheus[/green]\n"
                    f"  [bold white]{json.dumps(call_params, indent=4, sort_keys=True)}[/bold white]"
                )
                return True
            else:
                console.print(
                    f":cross_mark: [green]Failed to serve prometheus[/green] error: {err}"
                )
                return False
        else:
            return True
