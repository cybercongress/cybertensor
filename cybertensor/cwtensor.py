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

import os
import copy
import torch
import argparse
import cybertensor

from retry import retry
from loguru import logger
from typing import List, Dict, Union, Optional, Tuple, TypedDict, Any

# Local imports.
# from .chain_data import (
#     NeuronInfo,
#     DelegateInfo,
#     PrometheusInfo,
#     SubnetInfo,
#     SubnetHyperparameters,
#     StakeInfo,
#     NeuronInfoLite,
#     AxonInfo,
#     ProposalVoteData,
#     ProposalCallData,
#     IPInfo,
#     custom_rpc_type_registry,
# )
from .errors import *
# from .messages.network import (
#     register_subnetwork_message,
#     set_hyperparameter_message,
# )
# from .messages.staking import add_stake_message, add_stake_multiple_message
# from .messages.unstaking import unstake_message, unstake_multiple_message
# from .messages.serving import serve_message, serve_axon_message
# from .messages.registration import (
#     register_message,
#     burned_register_message,
#     run_faucet_message,
# )
# from .messages.transfer import transfer_message
# from .messages.set_weights import set_weights_message
# from .messages.prometheus import prometheus_message
# from .messages.delegation import (
#     delegate_message,
#     nominate_message,
#     undelegate_message,
# )
# from .messages.root import root_register_message, set_root_weights_message
# from .types import AxonServeCallParams, PrometheusServeCallParams
# from .utils import U16_NORMALIZED_FLOAT, ss58_to_vec_u8
# from .utils.balance import Balance
# from .utils.registration import POWSolution

logger = logger.opt(colors=True)


class ParamWithTypes(TypedDict):
    name: str  # Name of the parameter.
    type: str  # ScaleType string of the parameter.


class cwtensor:
    """Factory Class for cybertensor.cwtensor

    The Subtensor class handles interactions with the substrate cwtensor chain.
    By default, the Subtensor class connects to the Finney which serves as the main bittensor network.
    """

    @staticmethod
    def config() -> "cybertensor.config":
        parser = argparse.ArgumentParser()
        cwtensor.add_args(parser)
        return cybertensor.config(parser, args=[])

    @classmethod
    def help(cls):
        """Print help to stdout"""
        parser = argparse.ArgumentParser()
        cls.add_args(parser)
        print(cls.__new__.__doc__)
        parser.print_help()

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser, prefix: str = None):
        prefix_str = "" if prefix == None else prefix + "."
        try:
            default_network = os.getenv("BT_SUBTENSOR_NETWORK") or "bostrom"
            default_chain_endpoint = (
                os.getenv("BT_SUBTENSOR_CHAIN_ENDPOINT")
                or cybertensor.__finney_entrypoint__
            )
            parser.add_argument(
                "--" + prefix_str + "cwtensor.network",
                default=default_network,
                type=str,
                help="""The cwtensor network flag. The likely choices are:
                                        -- finney (main network)
                                        -- local (local running network)
                                    If this option is set it overloads cwtensor.chain_endpoint with
                                    an entry point node from that network.
                                    """,
            )
            parser.add_argument(
                "--" + prefix_str + "cwtensor.chain_endpoint",
                default=default_chain_endpoint,
                type=str,
                help="""The cwtensor endpoint flag. If set, overrides the --network flag.
                                    """,
            )
            parser.add_argument(
                "--" + prefix_str + "cwtensor._mock",
                default=False,
                type=bool,
                help="""If true, uses a mocked connection to the chain.
                                    """,
            )

        except argparse.ArgumentError:
            # re-parsing arguments.
            pass

    @staticmethod
    def determine_chain_endpoint_and_network(network: str):
        """Determines the chain endpoint and network from the passed network or chain_endpoint.
        Args:
            network (str): The network flag. The likely choices are:
                    -- finney (main network)
                    -- local (local running network)
                    -- test (test network)
            chain_endpoint (str): The chain endpoint flag. If set, overrides the network argument.
        Returns:
            network (str): The network flag. The likely choices are:
            chain_endpoint (str): The chain endpoint flag. If set, overrides the network argument.
        """
        if network == None:
            return None, None
        if network in ["finney", "local", "test", "archive"]:
            if network == "finney":
                # Kiru Finney stagin network.
                return network, cybertensor.__finney_entrypoint__
            elif network == "local":
                return network, cybertensor.__local_entrypoint__
            elif network == "test":
                return network, cybertensor.__finney_test_entrypoint__
            elif network == "archive":
                return network, cybertensor.__archive_entrypoint__
        else:
            if (
                network == cybertensor.__finney_entrypoint__
                or "entrypoint-finney.opentensor.ai" in network
            ):
                return "finney", cybertensor.__finney_entrypoint__
            elif (
                network == cybertensor.__finney_test_entrypoint__
                or "test.finney.opentensor.ai" in network
            ):
                return "test", cybertensor.__finney_test_entrypoint__
            elif (
                network == cybertensor.__archive_entrypoint__
                or "archive.chain.opentensor.ai" in network
            ):
                return "archive", cybertensor.__archive_entrypoint__
            elif "127.0.0.1" in network or "localhost" in network:
                return "local", network
            else:
                return "unknown", network

    @staticmethod
    def setup_config(network: str, config: cybertensor.config):
        if network != None:
            (
                evaluated_network,
                evaluated_endpoint,
            ) = cwtensor.determine_chain_endpoint_and_network(network)
        else:
            if config.get("__is_set", {}).get("cwtensor.chain_endpoint"):
                (
                    evaluated_network,
                    evaluated_endpoint,
                ) = cwtensor.determine_chain_endpoint_and_network(
                    config.cwtensor.chain_endpoint
                )

            elif config.get("__is_set", {}).get("cwtensor.network"):
                (
                    evaluated_network,
                    evaluated_endpoint,
                ) = cwtensor.determine_chain_endpoint_and_network(
                    config.cwtensor.network
                )

            elif config.cwtensor.get("chain_endpoint"):
                (
                    evaluated_network,
                    evaluated_endpoint,
                ) = cwtensor.determine_chain_endpoint_and_network(
                    config.cwtensor.chain_endpoint
                )

            elif config.cwtensor.get("network"):
                (
                    evaluated_network,
                    evaluated_endpoint,
                ) = cwtensor.determine_chain_endpoint_and_network(
                    config.cwtensor.network
                )

            else:
                (
                    evaluated_network,
                    evaluated_endpoint,
                ) = cwtensor.determine_chain_endpoint_and_network(
                    cybertensor.defaults.cwtensor.network
                )

        return (
            cybertensor.utils.networking.get_formatted_ws_endpoint_url(
                evaluated_endpoint
            ),
            evaluated_network,
        )

    def __init__(
        self,
        network: str = None,
        config: "cybertensor.config" = None,
        _mock: bool = False,
    ) -> None:
        r"""Initializes a cwtensor chain interface.
        Args:
            config (:obj:`cybertensor.config`, `optional`):
                cybertensor.cwtensor.config()
            network (default='local or ws://127.0.0.1:9946', type=str)
                The cwtensor network flag. The likely choices are:
                        -- local (local running network)
                        -- finney (main network)
                or cwtensor endpoint flag. If set, overrides the network argument.
        """

        # Determine config.cwtensor.chain_endpoint and config.cwtensor.network config.
        # If chain_endpoint is set, we override the network flag, otherwise, the chain_endpoint is assigned by the network.
        # Argument importance: network > chain_endpoint > config.cwtensor.chain_endpoint > config.cwtensor.network
        if config == None:
            config = cwtensor.config()
        self.config = copy.deepcopy(config)

        # Setup config.cwtensor.network and config.cwtensor.chain_endpoint
        self.chain_endpoint, self.network = cwtensor.setup_config(network, config)

        # Returns a mocked connection with a background chain connection.
        self.config.cwtensor._mock = (
            _mock
            if _mock != None
            else self.config.cwtensor.get("_mock", cybertensor.defaults.cwtensor._mock)
        )
        if self.config.cwtensor._mock:
            config.cwtensor._mock = True
            return cybertensor.cwtensor_mock.MockSubtensor()

        # Set up params.
        # self.substrate = SubstrateInterface(
        #     ss58_format=cybertensor.__ss58_format__,
        #     use_remote_preset=True,
        #     url=self.chain_endpoint,
        #     type_registry=cybertensor.__type_registry__,
        # )

    def __str__(self) -> str:
        if self.network == self.chain_endpoint:
            # Connecting to chain endpoint without network known.
            return "cwtensor({})".format(self.chain_endpoint)
        else:
            # Connecting to network with endpoint known.
            return "cwtensor({}, {})".format(self.network, self.chain_endpoint)

    def __repr__(self) -> str:
        return self.__str__()