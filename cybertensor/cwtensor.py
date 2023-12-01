# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
# Copyright © 2023 Opentensor Foundation
# Copyright © 2023 cyber~Congress
import json
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

from cosmpy.aerial.client import LedgerClient
from cosmpy.aerial.config import NetworkConfig
from cosmpy.aerial.contract import LedgerContract

import cybertensor

from retry import retry
from loguru import logger
from typing import List, Dict, Union, Optional, Tuple, TypedDict, Any

from .chain_data import SubnetInfo, SubnetHyperparameters
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
from .messages.network import register_subnetwork_message, set_hyperparameter_message

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
            default_network = os.getenv("CT_CYBER_NETWORK") or "local"
            # default_contract_address = os.getenv("CT_CONTRACT_ADDRESS") or "bostrom1"

            parser.add_argument(
                "--" + prefix_str + "cwtensor.network",
                default=default_network,
                type=str,
                help="""The cwtensor network flag. The likely choices are:
                                        -- bostrom (main network)
                                        -- local (local running network)
                                    """,
            )

            # parser.add_argument(
            #     "--" + prefix_str + "cwtensor.address",
            #     default=default_contract_address,
            #     type=str,
            #     help="""The cwtensor contract flag.
            #                         """,
            # )

        except argparse.ArgumentError:
            # re-parsing arguments.
            pass

    @staticmethod
    def determine_chain_endpoint_and_network(network: str):
        """Determines the chain endpoint and network from the passed network or chain_endpoint.
        Args:
            network (str): The network flag. The likely choices are:
                    -- bostrom (main network)
                    -- local (local running network)
            chain_endpoint (str): The chain endpoint flag. If set, overrides the network argument.
        Returns:
            network (str): The network flag. The likely choices are:
            chain_endpoint (str): The chain endpoint flag. If set, overrides the network argument.
        """
        if network == None:
            return None, None
        if network in ["local", "bostrom"]:
            if network == "bostrom":
                return network, cybertensor.__bostrom_network__, cybertensor.__contracts__[1]
            elif network == "local":
                return network, cybertensor.__local_network__, cybertensor.__contracts__[0]
        else:
            return "unknown", {}, "unknown"

    @staticmethod
    def setup_config(network: str, config: cybertensor.config):
        if network != None:
            (
                evaluated_network,
                evaluated_network_config,
                evaluated_contract_address
            ) = cwtensor.determine_chain_endpoint_and_network(network)
        else:
            if config.get("__is_set", {}).get("cwtensor.network"):
                (
                    evaluated_network,
                    evaluated_network_config,
                    evaluated_contract_address
                ) = cwtensor.determine_chain_endpoint_and_network(
                    config.cwtensor.network
                )
            elif config.cwtensor.get("network"):
                (
                    evaluated_network,
                    evaluated_network_config,
                    evaluated_contract_address
                ) = cwtensor.determine_chain_endpoint_and_network(
                    config.cwtensor.network
                )
            else:
                (
                    evaluated_network,
                    evaluated_network_config,
                    evaluated_contract_address
                ) = cwtensor.determine_chain_endpoint_and_network(
                    # TODO set default
                    "local"
                )

        return (
            evaluated_network,
            evaluated_network_config,
            evaluated_contract_address,
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
        # Argument importance: network > config.cwtensor.network
        if config == None:
            config = cwtensor.config()
        self.config = copy.deepcopy(config)

        # Setup config.cwtensor.network and config.cwtensor.chain_endpoint
        self.network, self.network_config, self.contract_address = cwtensor.setup_config(network, config)

        # Set up params.
        self.client = LedgerClient(self.network_config)
        self.contract = LedgerContract(cybertensor.__contract_path__, self.client,
                                       self.contract_address, None, cybertensor.__contract_schema_path__)

    def __str__(self) -> str:
        # Connecting to network with endpoint known.
        return "cwtensor({}, {}, {)".format(self.network, self.network_config, self.contract_address)

    def __repr__(self) -> str:
        return self.__str__()

    #################
    #### Network ####
    #################
    def register_subnetwork(
            self,
            wallet: "cybertensor.wallet",
            wait_for_inclusion: bool = True,
            wait_for_finalization=True,
            prompt: bool = False,
    ) -> bool:
        return register_subnetwork_message(
            self,
            wallet=wallet,
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    def set_hyperparameter(
        self,
        wallet: "cybertensor.wallet",
        netuid: int,
        parameter: str,
        value,
        wait_for_inclusion: bool = False,
        wait_for_finalization=True,
        prompt: bool = False,
    ) -> bool:
        return set_hyperparameter_message(
            self,
            wallet=wallet,
            netuid=netuid,
            parameter=parameter,
            value=value,
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    #####################################
    #### Network Parameters ####
    #####################################

    def get_subnet_burn_cost(self, block: Optional[int] = None) -> int:
        lock_cost = self.contract.query({"get_network_registration_cost": {}})

        if lock_cost == None:
            return None

        return lock_cost

    # def subnet_exists(self, netuid: int, block: Optional[int] = None) -> bool:
    #     return self.query_subtensor("NetworksAdded", block, [netuid]).value
    #
    # def get_all_subnet_netuids(self, block: Optional[int] = None) -> List[int]:
    #     subnet_netuids = []
    #     result = self.query_map_subtensor("NetworksAdded", block)
    #     if result.records:
    #         for netuid, exists in result:
    #             if exists:
    #                 subnet_netuids.append(netuid.value)
    #
    #     return subnet_netuids

    def get_total_subnets(self, block: Optional[int] = None) -> int:
        return self.query_subtensor("TotalNetworks", block).value

    # def get_emission_value_by_subnet(
    #     self, netuid: int, block: Optional[int] = None
    # ) -> Optional[float]:
    #     return Balance.from_rao(
    #         self.query_subtensor("EmissionValues", block, [netuid]).value
    #     )

    # def get_subnets(self, block: Optional[int] = None) -> List[int]:
    #     subnets = []
    #     result = self.query_map_subtensor("NetworksAdded", block)
    #     if result.records:
    #         for network in result.records:
    #             subnets.append(network[0].value)
    #         return subnets
    #     else:
    #         return []
    def get_all_subnets_info(self, block: Optional[int] = None) -> List[SubnetInfo]:
        result = self.contract.query({"get_subnets_info": {}})

        if result in (None, []):
            return []

        return SubnetInfo.list_from_list_any(result)

    # def get_subnet_info(
    #     self, netuid: int, block: Optional[int] = None
    # ) -> Optional[SubnetInfo]:
    #     @retry(delay=2, tries=3, backoff=2, max_delay=4)
    #     def make_substrate_call_with_retry():
    #         with self.substrate as substrate:
    #             block_hash = None if block == None else substrate.get_block_hash(block)
    #             params = [netuid]
    #             if block_hash:
    #                 params = params + [block_hash]
    #             return substrate.rpc_request(
    #                 method="subnetInfo_getSubnetInfo",  # custom rpc method
    #                 params=params,
    #             )
    #
    #     json_body = make_substrate_call_with_retry()
    #     result = json_body["result"]
    #
    #     if result in (None, []):
    #         return None
    #
    #     return SubnetInfo.from_vec_u8(result)

    def get_subnet_hyperparameters(
        self, netuid: int, block: Optional[int] = None
    ) -> Optional[SubnetHyperparameters]:
        result = self.contract.query({"get_subnet_hyperparams": {"netuid": netuid}})

        if result in (None, []):
            return []

        return SubnetHyperparameters.from_list_any(result)

    def get_subnet_owner(
        self, netuid: int, block: Optional[int] = None
    ) -> Optional[str]:
        resp = self.contract.query({"get_subnet_owner": {"netuid": netuid}})
        # return self.contract.query({"get_subnet_owner": {"netuid": netuid}})
        # resp
        if resp is None:
            return None
        else:
            return resp
