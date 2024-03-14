# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
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

import argparse

from rich.table import Table

import cybertensor
from cybertensor import __console__ as console
from cybertensor.commands.utils import check_netuid_set
from cybertensor.config import Config
from cybertensor.utils.balance import Balance


# TODO change tokens in table to boot and gigaboot
class MetagraphCommand:
    """
    Executes the 'metagraph' command to retrieve and display the entire metagraph
    for a specified network. This metagraph contains detailed information about
    all the neurons (nodes) participating in the network, including their stakes,
    trust scores, and more.

    Optional arguments:
    --netuid: The netuid of the network to query. Defaults to the default network UID.
    --cwtensor.network: The name of the network to query. Defaults to the default network name.

    The table displayed includes the following columns for each neuron:
    - UID: Unique identifier of the neuron.
    - STAKE(τ): Total stake of the neuron in Tau (τ).
    - RANK: Rank score of the neuron.
    - TRUST: Trust score assigned to the neuron by other neurons.
    - CONSENSUS: Consensus score of the neuron.
    - INCENTIVE: Incentive score representing the neuron's incentive alignment.
    - DIVIDENDS: Dividends earned by the neuron.
    - EMISSION(p): Emission in Rho (p) received by the neuron.
    - VTRUST: Validator trust score indicating the network's trust in the neuron as a validator.
    - VAL: Validator status of the neuron.
    - UPDATED: Number of blocks since the neuron's last update.
    - ACTIVE: Activity status of the neuron.
    - AXON: Network endpoint information of the neuron.
    - HOTKEY: Partial hotkey (public key) of the neuron.
    - COLDKEY: Partial coldkey (public key) of the neuron.

    The command also prints network-wide statistics such as total stake, issuance,
    and difficulty.

    Usage:
    The user must specify the network UID to query the metagraph. If not specified,
    the default network UID is used.

    Example usage:
    >>> ctcli metagraph --netuid 0 # Root network
    >>> ctcli metagraph --netuid 1 --cwtensor.network test

    Note:
    This command provides a snapshot of the network's state at the time of calling.
    It is useful for network analysis and diagnostics. It is intended to be used as
    part of the Cybertensor CLI and not as a standalone function within user code.
    """

    @staticmethod
    def run(cli: "cybertensor.cli") -> None:
        r"""Prints an entire metagraph."""
        try:
            cwtensor = cybertensor.cwtensor(config=cli.config, log_verbose=False)
            MetagraphCommand._run(cli, cwtensor)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def _run(cli: "cybertensor.cli", cwtensor: "cybertensor.cwtensor"):
        console.print(
            ":satellite: Syncing with chain: [white]{}[/white] ...".format(
                cli.config.cwtensor.network
            )
        )
        metagraph: cybertensor.metagraph = cwtensor.metagraph(netuid=cli.config.netuid)
        metagraph.save()
        difficulty = cwtensor.difficulty(cli.config.netuid)
        # subnet_emission = Balance.from_gboot(
        #     cwtensor.get_emission_value_by_subnet(cli.config.netuid)
        # )
        total_issuance = Balance.from_boot(cwtensor.total_issuance().boot)

        TABLE_DATA = []
        total_stake = 0.0
        total_rank = 0.0
        total_validator_trust = 0.0
        total_trust = 0.0
        total_consensus = 0.0
        total_incentive = 0.0
        total_dividends = 0.0
        total_emission = 0
        for uid in metagraph.uids:
            neuron = metagraph.neurons[uid]
            ep = metagraph.axons[uid]
            row = [
                str(neuron.uid),
                "{:.5f}".format(metagraph.total_stake[uid]),
                "{:.5f}".format(metagraph.ranks[uid]),
                "{:.5f}".format(metagraph.trust[uid]),
                "{:.5f}".format(metagraph.consensus[uid]),
                "{:.5f}".format(metagraph.incentive[uid]),
                "{:.5f}".format(metagraph.dividends[uid]),
                "{}".format(int(metagraph.emission[uid] * 1000000000)),
                "{:.5f}".format(metagraph.validator_trust[uid]),
                "*" if metagraph.validator_permit[uid] else "",
                str((metagraph.block.item() - metagraph.last_update[uid].item())),
                str(metagraph.active[uid].item()),
                (
                    ep.ip + ":" + str(ep.port)
                    if ep.is_serving
                    else "[yellow]none[/yellow]"
                ),
                f"{ep.hotkey[:14]}...{ep.hotkey[-6:]}",
                f"{ep.coldkey[:14]}...{ep.coldkey[-6:]}"
            ]
            total_stake += metagraph.total_stake[uid]
            total_rank += metagraph.ranks[uid]
            total_validator_trust += metagraph.validator_trust[uid]
            total_trust += metagraph.trust[uid]
            total_consensus += metagraph.consensus[uid]
            total_incentive += metagraph.incentive[uid]
            total_dividends += metagraph.dividends[uid]
            total_emission += int(metagraph.emission[uid] * 1000000000)
            TABLE_DATA.append(row)
        total_neurons = len(metagraph.uids)
        table = Table(show_footer=False)
        table.title = "[white]Metagraph: net: {}:{}, block: {}, N: {}/{}, stake: {}, issuance: {}, difficulty: {}".format(
            cwtensor.network,
            metagraph.netuid,
            metagraph.block.item(),
            sum(metagraph.active.tolist()),
            metagraph.n.item(),
            Balance.from_gboot(total_stake),
            total_issuance,
            difficulty,
        )
        table.add_column(
            "[overline white]UID",
            str(total_neurons),
            footer_style="overline white",
            style="yellow",
        )
        table.add_column(
            f"[overline white]STAKE({cwtensor.giga_token_symbol})",
            f"{cwtensor.giga_token_symbol}{total_stake:.5f}",
            footer_style="overline white",
            justify="right",
            style="green",
            no_wrap=True,
        )
        table.add_column(
            "[overline white]RANK",
            f"{total_rank:.5f}",
            footer_style="overline white",
            justify="right",
            style="green",
            no_wrap=True,
        )
        table.add_column(
            "[overline white]TRUST",
            f"{total_trust:.5f}",
            footer_style="overline white",
            justify="right",
            style="green",
            no_wrap=True,
        )
        table.add_column(
            "[overline white]CONSENSUS",
            f"{total_consensus:.5f}",
            footer_style="overline white",
            justify="right",
            style="green",
            no_wrap=True,
        )
        table.add_column(
            "[overline white]INCENTIVE",
            f"{total_incentive:.5f}",
            footer_style="overline white",
            justify="right",
            style="green",
            no_wrap=True,
        )
        table.add_column(
            "[overline white]DIVIDENDS",
            f"{total_dividends:.5f}",
            footer_style="overline white",
            justify="right",
            style="green",
            no_wrap=True,
        )
        table.add_column(
            "[overline white]EMISSION(\u03C1)",
            f"\u03C1{int(total_emission)}",
            footer_style="overline white",
            justify="right",
            style="green",
            no_wrap=True,
        )
        table.add_column(
            "[overline white]VTRUST",
            f"{total_validator_trust:.5f}",
            footer_style="overline white",
            justify="right",
            style="green",
            no_wrap=True,
        )
        table.add_column(
            "[overline white]VAL", justify="right", style="green", no_wrap=True
        )
        table.add_column("[overline white]UPDATED", justify="right", no_wrap=True)
        table.add_column(
            "[overline white]ACTIVE", justify="right", style="green", no_wrap=True
        )
        table.add_column(
            "[overline white]AXON", justify="left", style="dim blue", no_wrap=True
        )
        table.add_column("[overline white]HOTKEY", style="dim blue", no_wrap=False)
        table.add_column("[overline white]COLDKEY", style="dim purple", no_wrap=False)
        table.show_footer = True

        for row in TABLE_DATA:
            table.add_row(*row)
        table.box = None
        table.pad_edge = False
        table.width = None
        console.print(table)

    @staticmethod
    def check_config(config: "Config"):
        check_netuid_set(config, cwtensor=cybertensor.cwtensor(config=config, log_verbose=False))

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        metagraph_parser = parser.add_parser(
            "metagraph", help="""View a subnet metagraph information."""
        )
        metagraph_parser.add_argument(
            "--netuid",
            dest="netuid",
            type=int,
            help="""Set the netuid to get the metagraph of""",
            default=False,
        )
        metagraph_parser.add_argument(
            "--no_prompt",
            dest="no_prompt",
            action="store_true",
            help="""Set true to avoid prompting the user.""",
            default=False,
        )

        cybertensor.cwtensor.add_args(metagraph_parser)
