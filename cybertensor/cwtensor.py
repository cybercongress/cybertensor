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
import json
import argparse

from cosmpy.aerial.client import LedgerClient
from cosmpy.aerial.config import NetworkConfig
from cosmpy.aerial.contract import LedgerContract
from cosmpy.aerial.wallet import LocalWallet
from cosmpy.crypto.keypairs import PrivateKey

from cybertensor import Balance

import cybertensor

from retry import retry
from loguru import logger
from typing import List, Dict, Union, Optional, Tuple, TypedDict, Any

# Local imports.
from .chain_data import (
    NeuronInfo,
    # DelegateInfo,
    # PrometheusInfo,
    SubnetInfo,
    SubnetHyperparameters,
    # StakeInfo,
    NeuronInfoLite,
    # AxonInfo,
    # ProposalVoteData,
    # ProposalCallData,
    # IPInfo,
    # custom_rpc_type_registry,
)
from .errors import *

from .messages.network import (
    register_subnetwork_message,
    set_hyperparameter_message,
)
# from .messages.staking import add_stake_message, add_stake_multiple_message
# from .messages.unstaking import unstake_message, unstake_multiple_message
# from .messages.serving import serve_message, serve_axon_message
from .messages.registration import (
    register_message,
    burned_register_message,
    # run_faucet_message,
)
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
from .utils import U16_NORMALIZED_FLOAT
from .utils.balance import Balance
from .utils.registration import POWSolution

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

    #####################
    #### Delegation #####
    #####################

    #####################
    #### Set Weights ####
    #####################

    ######################
    #### Registration ####
    ######################
    def register(
            self,
            wallet: "cybertensor.wallet",
            netuid: int,
            wait_for_inclusion: bool = False,
            wait_for_finalization: bool = True,
            prompt: bool = False,
            max_allowed_attempts: int = 3,
            output_in_place: bool = True,
            cuda: bool = False,
            dev_id: Union[List[int], int] = 0,
            TPB: int = 256,
            num_processes: Optional[int] = None,
            update_interval: Optional[int] = None,
            log_verbose: bool = False,
    ) -> bool:
        """Registers the wallet to chain."""
        return register_message(
            cwtensor=self,
            wallet=wallet,
            netuid=netuid,
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
            max_allowed_attempts=max_allowed_attempts,
            output_in_place=output_in_place,
            cuda=cuda,
            dev_id=dev_id,
            TPB=TPB,
            num_processes=num_processes,
            update_interval=update_interval,
            log_verbose=log_verbose,
        )

    def _do_pow_register(
            self,
            netuid: int,
            wallet: "cybertensor.wallet",
            pow_result: POWSolution,
            wait_for_inclusion: bool = False,
            wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """Sends a (POW) register extrinsic to the chain.
        Args:
            netuid (int): the subnet to register on.
            wallet (cybertensor.wallet): the wallet to register.
            pow_result (POWSolution): the pow result to register.
            wait_for_inclusion (bool): if true, waits for the extrinsic to be included in a block.
            wait_for_finalization (bool): if true, waits for the extrinsic to be finalized.
        Returns:
            success (bool): True if the extrinsic was included in a block.
            error (Optional[str]): None on success or not waiting for inclusion/finalization, otherwise the error message.
        """

        register_msg = {"register": {
            "netuid": netuid,
            "block_number": pow_result.block_number,
            "nonce": pow_result.nonce,
            "work": [int(byte_) for byte_ in pow_result.seal],
            "hotkey": wallet.hotkey.address,
            "coldkey": wallet.coldkeypub.address,
        }}

        # TODO check decorator and improve error handling
        @retry(delay=2, tries=3, backoff=2, max_delay=4)
        def make_call_with_retry():
            if not wait_for_finalization:
                tx = self.contract.execute(
                    register_msg,
                    LocalWallet(PrivateKey(wallet.hotkey.private_key), cybertensor.__chain_address_prefix__),
                    cybertensor.__default_gas__,
                )
                return True, None
            else:
                tx = self.contract.execute(
                    register_msg,
                    LocalWallet(PrivateKey(wallet.hotkey.private_key), cybertensor.__chain_address_prefix__),
                    cybertensor.__default_gas__,
                )
                try:
                    tx.wait_to_complete()
                    if tx.response.is_successful():
                        return True, None
                    else:
                        return False, tx.response.code
                except Exception as e:
                    return False, e.__str__()

        return make_call_with_retry()

    def burned_register(
            self,
            wallet: "cybertensor.wallet",
            netuid: int,
            wait_for_inclusion: bool = False,
            wait_for_finalization: bool = True,
            prompt: bool = False,
    ) -> bool:
        """Registers the wallet to chain by recycling TAO."""
        return burned_register_message(
            cwtensor=self,
            wallet=wallet,
            netuid=netuid,
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    def _do_burned_register(
            self,
            netuid: int,
            burn: int,
            wallet: "cybertensor.wallet",
            wait_for_inclusion: bool = False,
            wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        burned_register_msg = {"burned_register": {"netuid": netuid, "hotkey": wallet.hotkey.address}}

        @retry(delay=2, tries=3, backoff=2, max_delay=4)
        def make_call_with_retry():
            if not wait_for_finalization:
                tx = self.contract.execute(
                    burned_register_msg,
                    LocalWallet(PrivateKey(wallet.coldkey.private_key), cybertensor.__chain_address_prefix__),
                    cybertensor.__default_gas__,
                    burn.__str__().__add__(cybertensor.__token__)
                )
                return True
            else:
                tx = self.contract.execute(
                    burned_register_msg,
                    LocalWallet(PrivateKey(wallet.coldkey.private_key), cybertensor.__chain_address_prefix__),
                    cybertensor.__default_gas__,
                    burn.__str__().__add__(cybertensor.__token__)
                )
                try:
                    tx.wait_to_complete()
                    if tx.response.is_successful():
                        return True, None
                    else:
                        return False, tx.response.code
                except Exception as e:
                    return False, e.__str__()

        return make_call_with_retry()

    ##################
    #### Transfer ####
    ##################

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

    #################
    #### Serving ####
    #################

    #################
    #### Staking ####
    #################

    ###################
    #### Unstaking ####
    ###################

    ##############
    #### Root ####
    ##############

    #####################################
    #### Hyper parameter calls. ####
    #####################################

    """ Returns network Burn hyper parameter """

    def burn(self, netuid: int, block: Optional[int] = None) -> Optional[int]:
        burn = self.contract.query({"get_burn": {"netuid": netuid}})

        if burn == None:
            return None

        return burn

    """ Returns network Difficulty hyper parameter """

    def difficulty(self, netuid: int, block: Optional[int] = None) -> Optional[int]:
        difficulty = self.contract.query({"get_difficulty": {"netuid": netuid}})

        if difficulty == None:
            return None

        return difficulty

    """ Returns network MinAllowedWeights hyper parameter """

    def min_allowed_weights(
            self, netuid: int, block: Optional[int] = None
    ) -> Optional[int]:
        min_allowed_weights = self.contract.query({"get_min_allowed_weights": {"netuid": netuid}})

        if min_allowed_weights == None:
            return None

        return min_allowed_weights

    """ Returns network MaxWeightsLimit hyper parameter """

    def max_weight_limit(
            self, netuid: int, block: Optional[int] = None
    ) -> Optional[float]:
        max_weight_limit = self.contract.query({"get_max_weight_limit": {"netuid": netuid}})

        if max_weight_limit == None:
            return None

        return U16_NORMALIZED_FLOAT(max_weight_limit)

    """ Returns network Tempo hyper parameter """

    def tempo(self, netuid: int, block: Optional[int] = None) -> int:
        tempo = self.contract.query({"get_tempo": {"netuid": netuid}})

        if tempo == None:
            return None

        return tempo

    ##########################
    #### Account functions ###
    ##########################

    ###########################
    #### Global Parameters ####
    ###########################

    @property
    def block(self) -> int:
        r"""Returns current chain block.
        Returns:
            block (int):
                Current chain block.
        """
        return self.get_current_block()

    def total_issuance(self, block: Optional[int] = None) -> "Balance":
        return Balance.from_boot(self.contract.query({"get_total_issuance": {}}))

    def total_stake(self, block: Optional[int] = None) -> "Balance":
        return Balance.from_boot(self.contract.query({"get_total_stake": {}}))

    def tx_rate_limit(self, block: Optional[int] = None) -> Optional[int]:
        return self.contract.query({"get_tx_rate_limit": {}})

    #####################################
    #### Network Parameters ####
    #####################################

    def get_subnet_burn_cost(self, block: Optional[int] = None) -> int:
        lock_cost = self.contract.query({"get_network_registration_cost": {}})

        if lock_cost == None:
            return None

        return lock_cost

    def subnet_exists(self, netuid: int, block: Optional[int] = None) -> bool:
        return self.contract.query({"get_subnet_exist": {"netuid": netuid}})

    def     get_total_subnets(self, block: Optional[int] = None) -> int:

        return self.contract.query({"get_total_networks": {}})

    def get_emission_value_by_subnet(
            self, netuid: int, block: Optional[int] = None
    ) -> Optional[float]:
        return Balance.from_boot(
            # TODO what if zero
            self.contract.query({"get_emission_value_by_subnet": {"netuid": netuid}})
        )

    def get_subnets(self, block: Optional[int] = None) -> List[int]:
        return self.contract.query({"get_networks_added": {}})

    def get_all_subnets_info(self, block: Optional[int] = None) -> List[SubnetInfo]:
        result = self.contract.query({"get_subnets_info": {}})

        if result in (None, []):
            return []

        return SubnetInfo.list_from_list_any(result)

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
        if resp is None:
            return None
        else:
            return resp

    ####################
    #### Nomination ####
    ####################

    ###########################
    #### Stake Information ####
    ###########################

    ########################################
    #### Neuron information per subnet ####
    ########################################

    def is_hotkey_registered_any(
            self, hotkey: str, block: Optional[int] = None
    ) -> bool:
        return len(self.get_netuids_for_hotkey(hotkey, block)) > 0

    def is_hotkey_registered_on_subnet(
            self, hotkey: str, netuid: int, block: Optional[int] = None
    ) -> bool:
        return self.get_uid_for_hotkey_on_subnet(hotkey, netuid, block) != None

    def is_hotkey_registered(
            self,
            hotkey: str,
            netuid: Optional[int] = None,
            block: Optional[int] = None,
    ) -> bool:
        if netuid == None:
            return self.is_hotkey_registered_any(hotkey, block)
        else:
            return self.is_hotkey_registered_on_subnet(hotkey, netuid, block)

    def get_uid_for_hotkey_on_subnet(
            self, hotkey: str, netuid: int, block: Optional[int] = None
    ) -> Optional[int]:
        resp = self.contract.query({"get_uid_for_hotkey_on_subnet": {"netuid": netuid, "hotkey": hotkey}})
        if resp is None:
            return None
        else:
            return resp

    def get_all_uids_for_hotkey(
            self, hotkey: str, block: Optional[int] = None
    ) -> List[int]:
        return [
            self.get_uid_for_hotkey_on_subnet(hotkey, netuid, block)
            for netuid in self.get_netuids_for_hotkey(hotkey, block)
        ]

    def get_netuids_for_hotkey(
            self, hotkey: str, block: Optional[int] = None
    ) -> List[int]:
        resp = self.contract.query({"get_netuids_for_hotkey": {"hotkey": hotkey}})
        if resp in (None, []):
            return []
        else:
            return resp

    def get_neuron_for_pubkey_and_subnet(
            self, hotkey: str, netuid: int, block: Optional[int] = None
    ) -> Optional[NeuronInfo]:
        return self.neuron_for_uid(
            self.get_uid_for_hotkey_on_subnet(hotkey, netuid, block=block),
            netuid,
            block=block,
        )

    def get_all_neurons_for_pubkey(
            self, hotkey: str, block: Optional[int] = None
    ) -> List[NeuronInfo]:
        netuids = self.get_netuids_for_hotkey(hotkey, block)
        uids = [self.get_uid_for_hotkey_on_subnet(hotkey, net) for net in netuids]
        return [self.neuron_for_uid(uid, net) for uid, net in list(zip(uids, netuids))]

    def neuron_for_uid(
            self, uid: int, netuid: int, block: Optional[int] = None
    ) -> Optional[NeuronInfo]:
        r"""Returns a list of neuron from the chain.
        Args:
            uid ( int ):
                The uid of the neuron to query for.
            netuid ( int ):
                The uid of the network to query for.
            block ( int ):
                The neuron at a particular block
        Returns:
            neuron (Optional[NeuronInfo]):
                neuron metadata associated with uid or None if it does not exist.
        """
        if uid == None:
            return NeuronInfo._null_neuron()

        resp = self.contract.query({"get_neuron": {"netuid": netuid, "uid": uid}})
        if resp in (None, []):
            return NeuronInfo._null_neuron()

        return NeuronInfo.from_list_any(resp)

    def neurons(self, netuid: int, block: Optional[int] = None) -> List[NeuronInfo]:
        r"""Returns a list of neuron from the chain.
        Args:
            netuid ( int ):
                The netuid of the subnet to pull neurons from.
            block ( Optional[int] ):
                block to sync from.
        Returns:
            neuron (List[NeuronInfo]):
                List of neuron metadata objects.
        """
        neurons_lite = self.neurons_lite(netuid=netuid, block=block)
        weights = self.weights(block=block, netuid=netuid)
        bonds = self.bonds(block=block, netuid=netuid)

        weights_as_dict = {uid: w for uid, w in weights}
        bonds_as_dict = {uid: b for uid, b in bonds}

        neurons = [
            NeuronInfo.from_weights_bonds_and_neuron_lite(
                neuron_lite, weights_as_dict, bonds_as_dict
            )
            for neuron_lite in neurons_lite
        ]

        return neurons

    def neurons_lite(
            self, netuid: int, block: Optional[int] = None
    ) -> List[NeuronInfoLite]:
        r"""Returns a list of neuron lite from the chain.
        Args:
            netuid ( int ):
                The netuid of the subnet to pull neurons from.
            block ( Optional[int] ):
                block to sync from.
        Returns:
            neuron (List[NeuronInfoLite]):
                List of neuron lite metadata objects.
        """

        resp = self.contract.query({"get_neurons_lite": {"netuid": netuid}})
        if resp in (None, []):
            return []

        return NeuronInfoLite.list_from_list_any(resp)

    def metagraph(
            self,
            netuid: int,
            lite: bool = True,
            block: Optional[int] = None,
    ) -> "cybertensor.Metagraph":
        r"""Returns a synced metagraph for the subnet.
        Args:
            netuid ( int ):
                The network uid of the subnet to query.
            lite (bool, default=True):
                If true, returns a metagraph using the lite sync (no weights, no bonds)
            block ( Optional[int] ):
                block to sync from, or None for latest block.
        Returns:
            metagraph ( `bittensor.Metagraph` ):
                The metagraph for the subnet at the block.
        """
        metagraph_ = cybertensor.metagraph(
            network=self.network, netuid=netuid, lite=lite, sync=False
        )
        metagraph_.sync(block=block, lite=lite, cwtensor=self)

        return metagraph_

    ################
    #### Legacy ####
    ################

    def get_balance(self, address: str, block: int = None) -> Balance:
        r"""Returns the balance of an address.
        Args:
            address ( str ):
                The address to query for.
            block ( int ):
                The block to query at.
        Returns:
            balance ( Balance ):
                The balance of the address.
        """
        return Balance.from_boot(self.client.query_bank_balance(address, cybertensor.__token__))

    # TODO rewrite logic
    def get_current_block(self) -> int:
        return self.client.query_latest_block().height

    # TODO rewrite logic
    def get_block_hash(self, block_id: int) -> str:
        return "0x0000000000000000000000000000000000000000000000000000000000000000"
