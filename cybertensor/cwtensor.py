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

import argparse
import copy
import os
from typing import List, Dict, Union, Optional, Tuple, TypeVar

import torch
from cosmpy.aerial.client import LedgerClient
from cosmpy.aerial.contract import LedgerContract
from cosmpy.aerial.wallet import LocalWallet
from cosmpy.crypto.address import Address
from cosmpy.crypto.keypairs import PrivateKey
from loguru import logger
from retry import retry

import cybertensor
from cybertensor import __console__ as console
from cybertensor.chain_data import (
    NeuronInfo,
    DelegateInfo,
    PrometheusInfo,
    SubnetInfo,
    SubnetHyperparameters,
    StakeInfo,
    NeuronInfoLite,
    AxonInfo,
)
from cybertensor.commands.utils import DelegatesDetails
from cybertensor.config import Config
from cybertensor.errors import *
from cybertensor.messages.delegation import (
    delegate_message,
    nominate_message,
    undelegate_message,
)
from cybertensor.messages.network import (
    register_subnetwork_message,
    set_hyperparameter_message,
)
from cybertensor.messages.prometheus import prometheus_message
from cybertensor.messages.registration import (
    register_message,
    burned_register_message,
    swap_hotkey_message
)
from cybertensor.messages.root import root_register_message, set_root_weights_message
from cybertensor.messages.serving import serve_message, serve_axon_message, publish_metadata, get_metadata
from cybertensor.messages.set_weights import set_weights_message
from cybertensor.messages.staking import add_stake_message, add_stake_multiple_message
from cybertensor.messages.transfer import transfer_message
from cybertensor.messages.unstaking import unstake_message, unstake_multiple_message
from cybertensor.types import AxonServeCallParams, PrometheusServeCallParams
from cybertensor.utils import U16_NORMALIZED_FLOAT, coin_from_str
from cybertensor.utils.balance import Balance
from cybertensor.utils.registration import POWSolution
from cybertensor.wallet import Wallet

logger = logger.opt(colors=True)

T = TypeVar("T")


class cwtensor:
    """Factory Class for cybertensor.cwtensor

    The cwtensor class handles interactions with the substrate cwtensor chain.
    By default, the cwtensor class connects to the Finney which serves as the main cybertensor network.
    
    The cwtensor class in cybertensor serves as a crucial interface for interacting with the cybertensor blockchain, 
    facilitating a range of operations essential for the decentralized machine learning network.

    This class enables neurons (network participants) to engage in activities such as registering on the network, managing
    staked weights, setting inter-neuronal weights, and participating in consensus mechanisms.

    The cybertensor network operates on a digital ledger where each neuron holds stakes (S) and learns a set
    of inter-peer weights (W). These weights, set by the neurons themselves, play a critical role in determining
    the ranking and incentive mechanisms within the network. Higher-ranked neurons, as determined by their
    contributions and trust within the network, receive more incentives.

    The cwtensor class connects to various cybertensor networks like the main ``finney`` network or local test
    networks, providing a gateway to the blockchain layer of cybertensor. It leverages a staked weighted trust
    system and consensus to ensure fair and distributed incentive mechanisms, where incentives (I) are
    primarily allocated to neurons that are trusted by the majority of the network.

    Additionally, cybertensor introduces a speculation-based reward mechanism in the form of bonds (B), allowing
    neurons to accumulate bonds in other neurons, speculating on their future value. This mechanism aligns
    with market-based speculation, incentivizing neurons to make judicious decisions in their inter-neuronal
    investments.

    Args:
        network (str): The name of the cybertensor network (e.g., 'bostrom', 'space-pussy', 'local') the instance is
            connected to, determining the blockchain interaction context.
        chain_endpoint (str): The blockchain node endpoint URL, enabling direct communication with the cybertensor
            blockchain for transaction processing and data retrieval.

    Example Usage::

        # Connect to the main cybertensor network (bostrom).
        main_cwtensor = cwtensor(network='bostrom')

        # Register a new neuron on the network.
        wallet = cybertensor.Wallet(...)  # Assuming a wallet instance is created.
        success = main_cwtensor.register(wallet=wallet, netuid=netuid)

        # Set inter-neuronal weights for collaborative learning.
        success = main_cwtensor.set_weights(wallet=wallet, netuid=netuid, uids=[...], weights=[...])

        # Speculate by accumulating bonds in other promising neurons.
        success = main_cwtensor.delegate(wallet=wallet, delegate=other_neuron, amount=bond_amount)

        # Get the metagraph for a specific subnet using given cwtensor connection
        metagraph = cwtensor.metagraph(netuid=netuid)

    By facilitating these operations, the cwtensor class is instrumental in maintaining the decentralized
    intelligence and dynamic learning environment of the cybertensor network.
    """

    @staticmethod
    def config() -> "Config":
        parser = argparse.ArgumentParser()
        cwtensor.add_args(parser)
        return Config(parser, args=[])

    @classmethod
    def help(cls):
        """Print help to stdout"""
        parser = argparse.ArgumentParser()
        cls.add_args(parser)
        print(cls.__new__.__doc__)
        parser.print_help()

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser, prefix: Optional[str] = None):
        prefix_str = "" if prefix is None else f"{prefix}."
        try:
            default_network = os.getenv("CT_CYBER_NETWORK") or cybertensor.__default_network__

            parser.add_argument(
                "--" + prefix_str + "cwtensor.network",
                default=default_network,
                type=str,
                help="""The cwtensor network flag. The likely choices are:
                                        -- bostrom (main network)
                                        -- local (local running network)
                                        -- space-pussy (space-pussy network)
                                    """,
            )

        except argparse.ArgumentError:
            # re-parsing arguments.
            pass

    @staticmethod
    def determine_chain_endpoint_and_network(
        network: str,
    ) -> [Optional[str], Optional["cybertensor.NetworkConfigCwTensor"]]:
        """Determines the chain endpoint and network from the passed network or chain_endpoint.
        Args:
            network (str): The network flag. The likely choices are:
                    -- bostrom (main network)
                    -- local (local running network)
                    -- space-pussy (space-pussy network)
        Returns:
            network (str): The network flag.
            network_config (cybertensor.NetworkConfigCwTensor): The chain network config.
        """
        if network is None:
            return None, None
        if network in ["local", "bostrom", "space-pussy"]:
            if network == "bostrom":
                return (
                    network,
                    cybertensor.__bostrom_network__,
                )
            elif network == "space-pussy":
                return (
                    network,
                    cybertensor.__space_pussy_network__,
                )
            elif network == "local":
                return (
                    network,
                    cybertensor.__local_network__,
                )
        else:
            return "unknown", {}

    @staticmethod
    def setup_config(network: str, config: "Config"):
        if network is not None:
            (
                evaluated_network,
                evaluated_network_config,
            ) = cwtensor.determine_chain_endpoint_and_network(network)
        else:
            if config.get("__is_set", {}).get("cwtensor.network"):
                (
                    evaluated_network,
                    evaluated_network_config,
                ) = cwtensor.determine_chain_endpoint_and_network(
                    config.cwtensor.network
                )
            elif config.cwtensor.get("network"):
                (
                    evaluated_network,
                    evaluated_network_config,
                ) = cwtensor.determine_chain_endpoint_and_network(
                    config.cwtensor.network
                )
            else:
                (
                    evaluated_network,
                    evaluated_network_config,
                ) = cwtensor.determine_chain_endpoint_and_network(
                    # TODO set default
                    "space-pussy"
                )

        return (
            evaluated_network,
            evaluated_network_config,
        )

    def __init__(
        self,
        network: Optional[str] = None,
        config: Optional["Config"] = None,
        _mock: bool = False,
        log_verbose: bool = True,
    ) -> None:
        r"""Initializes a cwtensor chain interface.

        NOTE:
            Currently cwtensor defaults to the ``space-pussy`` network. This will change in a future release.

        We strongly encourage users to run their own local node whenever possible. This increases
        decentralization and resilience of the network. In a future release, bostrom will become the
        default and the fallback to ``space-pussy`` removed. Please plan ahead for this change. We will provide detailed
        instructions on how to run a local node in the documentation in a subsequent release.

        Args:
            config (:obj:`Config`, `optional`):
                Configuration object for the cwtensor. If not provided, a default configuration is used.
            network (default='space-pussy', type=str, optional)
                The cwtensor network flag. The likely choices are:
                        -- bostrom (main network)
                        -- local (local running network)
                        -- space-pussy (space-pussy network)
            _mock (bool, optional): If set to ``True``, uses a mocked connection for testing purposes.

        This initialization sets up the connection to the specified network, allowing for various
        blockchain operations such as neuron registration, stake management, and setting weights.
        """

        # Determine config.cwtensor.chain_endpoint and config.cwtensor.network config.
        # If chain_endpoint is set, we override the network flag, otherwise, the chain_endpoint is assigned by the network.
        # Argument importance: network > config.cwtensor.network

        # Check if network is a config object. (Single argument passed as first positional)
        if isinstance(network, cybertensor.Config):
            if network.cwtensor is None:
                cybertensor.logging.warning(
                    "If passing a cybertensor config object, it must not be empty. Using default cwtensor config."
                )
                config = None
            else:
                config = network
            network = None

        if config is None:
            config = cwtensor.config()
        self.config = copy.deepcopy(config)  # type: ignore

        # Setup config.cwtensor.network and config.cwtensor.chain_endpoint
        (
            self.network,
            self.network_config,
        ) = cwtensor.setup_config(network, config)  # type: ignore

        self.token = self.network_config.token
        self.network_explorer = self.network_config.network_explorer
        self.address_prefix = self.network_config.address_prefix
        self.contract_address = self.network_config.contract_address
        self.token_symbol = self.network_config.token_symbol
        self.giga_token_symbol = self.network_config.giga_token_symbol

        # Set up params.
        self.client = LedgerClient(cfg=self.network_config)
        self.contract = LedgerContract(
            path=cybertensor.__contract_path__,
            client=self.client,
            address=self.contract_address,
            digest=None,
            schema_path=cybertensor.__contract_schema_path__,
        )

        # Returns a mocked connection with a background chain connection.
        self.config.cwtensor._mock = (
            _mock
            if _mock is not None
            else self.config.cwtensor.get("_mock", cybertensor.defaults.cwtensor._mock)
        )
        if (
            self.config.cwtensor._mock
        ):  # TODO: review this doesn't appear to be used anywhere.
            config.cwtensor._mock = True
            return cybertensor.MockCwtensor()  # type: ignore

    def __str__(self) -> str:
        # Connecting to network with endpoint known.
        return (
            f"cwtensor({self.network}, {self.network_config}, {self.contract_address})"
        )

    def __repr__(self) -> str:
        return self.__str__()

    # TODO check decorator and improve error handling
    @retry(delay=3, tries=3, backoff=2, max_delay=8)
    def make_call_with_retry(self, wait_for_finalization: bool,
                             msg: dict,
                             signer_wallet: LocalWallet,
                             error,
                             gas: Optional[int] = cybertensor.__default_gas__,
                             funds: Optional[str] = None) -> Optional[bool]:
        if not wait_for_finalization:
            self.contract.execute(msg, signer_wallet, gas, funds=funds)
            return True
        else:
            tx = self.contract.execute(msg, signer_wallet, gas, funds=funds)
            try:
                tx.wait_to_complete()
                if tx.response.is_successful():
                    print(f'Gas used: {tx.response.gas_used}')
                    return True
                else:
                    raise error(tx.response.logs)
            except Exception as e:
                raise error(e.__str__())

    def _execute_contract(self, wait_for_finalization: bool,
                          msg: dict,
                          wallet: Wallet,
                          error,
                          logging_prefix: str,
                          use_hotkey: bool = True,
                          success_text: str = 'Finalized',
                          exception_text: str = 'Failed',
                          gas: Optional[int] = cybertensor.__default_gas__,
                          funds: Optional[str] = None) -> [bool, Optional[str]]:
        try:
            _private_key = wallet.hotkey.private_key if use_hotkey else wallet.coldkey.private_key
            signer_wallet = LocalWallet(
                PrivateKey(_private_key), self.address_prefix
            )
            res = self.make_call_with_retry(
                wait_for_finalization=wait_for_finalization,
                msg=msg,
                signer_wallet=signer_wallet,
                error=error,
                gas=gas,
                funds=funds)
            if res is True:
                console.print(
                    f":white_heavy_check_mark: [green]{success_text}[/green]"
                )
                cybertensor.logging.success(
                        prefix=logging_prefix,
                        sufix=f"<green>{success_text}</green>",
                    )
                return True, None
        except Exception as e:
            console.print(
                f":cross_mark: [red]{exception_text}[/red]: error:{e}"
            )
            cybertensor.logging.warning(
                prefix=logging_prefix,
                sufix=f"[red]{exception_text}[/red]: error:{e}",
            )
            return False, f"[red]{exception_text}[/red]: error:{e}"
        return False, None

    @retry(delay=3, tries=3, backoff=2, max_delay=8)
    def make_call_with_retry_2(self, wait_for_finalization: bool,
                               msg: dict, signer_wallet: LocalWallet, gas: Optional[int] = cybertensor.__default_gas__,
                               funds: Optional[str] = None) -> [bool, Optional[str]]:
        if not wait_for_finalization:
            self.contract.execute(msg, signer_wallet, gas, funds=funds)
            return True, None
        else:
            tx = self.contract.execute(msg, signer_wallet, gas, funds=funds)
            try:
                tx.wait_to_complete()
                if tx.response.is_successful():
                    print(f'Gas used: {tx.response.gas_used}')
                    return True, None
                else:
                    return False, tx.response.code
            except Exception as e:
                return False, e.__str__()

    ####################
    #### Websocket Interface related
    ####################
    def connect_websocket(self):
        """
        (Re)creates the websocket connection, if the URL contains a 'ws' or 'wss' scheme
        """
        pass

    def close(self):
        """
        Cleans up resources for this cwtensor instance like active websocket connection and active extensions
        """
        pass

    #####################
    #### Delegation #####
    #####################
    def nominate(
        self,
        wallet: "Wallet",
        wait_for_finalization: bool = True,
    ) -> bool:
        """
        Becomes a delegate for the hotkey associated with the given wallet. This method is used to nominate
        a neuron (identified by the hotkey in the wallet) as a delegate on the cybertensor network, allowing it
        to participate in consensus and validation processes.

        Args:
            wallet (cybertensor.Wallet): The wallet containing the hotkey to be nominated.
            wait_for_finalization (bool, optional): If ``True``, waits until the transaction is finalized on the blockchain.

        Returns:
            bool: ``True`` if the nomination process is successful, ``False`` otherwise.

        This function is a key part of the decentralized governance mechanism of cybertensor, allowing for the
        dynamic selection and participation of validators in the network's consensus process.

        """
        return nominate_message(
            cwtensor=self,
            wallet=wallet,
            wait_for_finalization=wait_for_finalization,
        )

    def _do_nominate(
        self,
        wallet: "Wallet",
        wait_for_finalization: bool = True,
    ) -> bool:
        nominate_msg = {"become_delegate": {"hotkey": wallet.hotkey.address}}
        signer_wallet = LocalWallet(
            PrivateKey(wallet.coldkey.private_key), self.address_prefix
        )

        return self.make_call_with_retry(
            wait_for_finalization=wait_for_finalization,
            msg=nominate_msg,
            signer_wallet=signer_wallet,
            error=NominationError)

    def delegate(
        self,
        wallet: "Wallet",
        delegate: Optional[str] = None,
        amount: Optional[Union[Balance, float]] = None,
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """
        Becomes a delegate for the hotkey associated with the given wallet. This method is used to nominate
        a neuron (identified by the hotkey in the wallet) as a delegate on the cybertensor network, allowing it
        to participate in consensus and validation processes.

        Args:
            wallet (cybertensor.Wallet): The wallet containing the hotkey to be nominated.
            delegate (str, optional): The address of the delegate neuron.
            amount (Union[cybertensor.Balance, float], optional): The amount of stake to delegate.
            wait_for_finalization (bool, optional): If ``True``, waits until the transaction is finalized on the blockchain.
            prompt (bool, optional): If ``True``, prompts for user confirmation before proceeding.

        Returns:
            bool: ``True`` if the nomination process is successful, False otherwise.

        This function is a key part of the decentralized governance mechanism of cybertensor, allowing for the
        dynamic selection and participation of validators in the network's consensus process.
        """
        return delegate_message(
            cwtensor=self,
            wallet=wallet,
            delegate=delegate,
            amount=amount,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    def _do_delegation(
        self,
        wallet: "Wallet",
        delegate: str,
        amount: "Balance",
        wait_for_finalization: bool = True,
    ) -> bool:
        delegation_msg = {"add_stake": {"hotkey": delegate}}
        signer_wallet = LocalWallet(
            PrivateKey(wallet.coldkey.private_key), self.address_prefix
        )
        funds = amount.boot.__str__().__add__(self.token)

        return self.make_call_with_retry(
            wait_for_finalization=wait_for_finalization,
            msg=delegation_msg,
            funds=funds,
            signer_wallet=signer_wallet,
            error=StakeError)

    def undelegate(
        self,
        wallet: "Wallet",
        delegate: Optional[str] = None,
        amount: Union[Balance, float] = None,
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """
        Removes a specified amount of stake from a delegate neuron using the provided wallet. This action
        reduces the staked amount on another neuron, effectively withdrawing support or speculation.
        Args:
            wallet (cybertensor.Wallet): The wallet used for the undelegation process.
            delegate (Optional[str]): The address of the delegate neuron.
            amount (Union[cybertensor.Balance, float]): The amount of GBOOT to undelegate.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
            prompt (bool, optional): If ``True``, prompts for user confirmation before proceeding.
        Returns:
            bool: ``True`` if the undelegation is successful, False otherwise.
        This function reflects the dynamic and speculative nature of the cybertensor network, allowing neurons
        to adjust their stakes and investments based on changing perceptions and performances within the network.


        """
        return undelegate_message(
            cwtensor=self,
            wallet=wallet,
            delegate=delegate,
            amount=amount,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    def _do_undelegation(
        self,
        wallet: "Wallet",
        delegate: str,
        amount: "Balance",
        wait_for_finalization: bool = True,
    ) -> bool:
        undelegation_msg = {"remove_stake": {"hotkey": delegate, "amount": amount.boot}}
        signer_wallet = LocalWallet(
            PrivateKey(wallet.coldkey.private_key), self.address_prefix
        )

        return self.make_call_with_retry(
            wait_for_finalization=wait_for_finalization,
            msg=undelegation_msg,
            signer_wallet=signer_wallet,
            error=StakeError)

    #####################
    #### Set Weights ####
    #####################

    def set_weights(
        self,
        wallet: "Wallet",
        netuid: int,
        uids: Union[torch.LongTensor, torch.Tensor, list],
        weights: Union[torch.FloatTensor, torch.Tensor, list],
        version_key: int = cybertensor.__version_as_int__,
        uid: Optional[int] = None,
        wait_for_finalization: bool = True,
        prompt: bool = False,
        max_retries: int = 5,
    ) -> Tuple[bool, str]:
        """
        Sets the inter-neuronal weights for the specified neuron. This process involves specifying the
        influence or trust a neuron places on other neurons in the network, which is a fundamental aspect
        of cybertensor's decentralized learning architecture.

        Args:
            wallet (cybertensor.Wallet): The wallet associated with the neuron setting the weights.
            netuid (int): The unique identifier of the subnet.
            uid (int): Unique identifier for the caller on the subnet specified by `netuid`.
            uids (Union[torch.LongTensor, list]): The list of neuron UIDs that the weights are being set for.
            weights (Union[torch.FloatTensor, list]): The corresponding weights to be set for each UID.
            version_key (int, optional): Version key for compatibility with the network.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
            prompt (bool, optional): If ``True``, prompts for user confirmation before proceeding.
            max_retries (int, optional): The number of maximum attempts to set weights. (Default: 5)

        Returns:
            Tuple[bool, str]: ``True`` if the setting of weights is successful, False otherwise. And `msg`, a string
            value describing the success or potential error.

        This function is crucial in shaping the network's collective intelligence, where each neuron's
        learning and contribution are influenced by the weights it sets towards others【81†source】.
        """
        # uid = self.get_uid_for_hotkey_on_subnet(wallet.hotkey.address, netuid)
        # retries = 0
        success = False
        message = "No attempt made. Perhaps it is too soon to set weights!"
        # while (
        #     self.blocks_since_last_update(netuid, uid) > self.weights_rate_limit(netuid)  # type: ignore
        #     and retries < max_retries
        # ):
        try:
            success, message = set_weights_message(
                cwtensor=self,
                wallet=wallet,
                netuid=netuid,
                uids=uids,
                weights=weights,
                version_key=version_key,
                wait_for_finalization=wait_for_finalization,
                prompt=prompt,
            )
        except Exception as e:
            cybertensor.logging.error(f"Error setting weights: {e}")
            # finally:
            #     retries += 1

        return success, message

    def _do_set_weights(
        self,
        wallet: "Wallet",
        uids: List[int],
        vals: List[int],
        netuid: int,
        version_key: int = cybertensor.__version_as_int__,
        wait_for_finalization: bool = True,
    ) -> [bool, Optional[str]]:
        """
        Internal method to send a transaction to the cybertensor blockchain, setting weights
        for specified neurons. This method constructs and submits the transaction, handling
        retries and blockchain communication.
        Args:
            wallet (cybertensor.Wallet): The wallet associated with the neuron setting the weights.
            uids (List[int]): List of neuron UIDs for which weights are being set.
            vals (List[int]): List of weight values corresponding to each UID.
            netuid (int): Unique identifier for the network.
            version_key (int, optional): Version key for compatibility with the network.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
        Returns:
            Tuple[bool, Optional[str]]: A tuple containing a success flag and an optional error message.
        This method is vital for the dynamic weighting mechanism in cybertensor, where neurons adjust their
        trust in other neurons based on observed performance and contributions.
        """

        set_weights_msg = {
            "set_weights": {
                "netuid": netuid,
                "dests": uids,
                "weights": vals,
                "version_key": version_key,
            }
        }

        return self._execute_contract(
            wait_for_finalization=wait_for_finalization,
            msg=set_weights_msg,
            wallet=wallet,
            error=NotSetWeightError,
            logging_prefix='Set weights'
        )

    ######################
    #### Registration ####
    ######################
    def register(
        self,
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
        """
        Registers a neuron on the cybertensor network using the provided wallet. Registration
        is a critical step for a neuron to become an active participant in the network, enabling
        it to stake, set weights, and receive incentives.
        Args:
            wallet (cybertensor.Wallet): The wallet associated with the neuron to be registered.
            netuid (int): The unique identifier of the subnet.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
            Other arguments: Various optional parameters to customize the registration process.
        Returns:
            bool: ``True`` if the registration is successful, False otherwise.
        This function facilitates the entry of new neurons into the network, supporting the decentralized
        growth and scalability of the cybertensor ecosystem.
        """
        return register_message(
            cwtensor=self,
            wallet=wallet,
            netuid=netuid,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
            max_allowed_attempts=max_allowed_attempts,
            output_in_place=output_in_place,
            cuda=cuda,
            dev_id=dev_id,
            tpb=tpb,
            num_processes=num_processes,
            update_interval=update_interval,
            log_verbose=log_verbose,
        )

    def swap_hotkey(
        self,
        wallet: "Wallet",
        new_wallet: "Wallet",
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """Swaps an old hotkey to a new hotkey."""
        return swap_hotkey_message(
            cwtensor=self,
            wallet=wallet,
            new_wallet=new_wallet,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    def _do_pow_register(
        self,
        netuid: int,
        wallet: "Wallet",
        pow_result: POWSolution,
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Sends a (POW) register extrinsic to the chain.
        Args:
            netuid (int): The subnet to register on.
            wallet (cybertensor.Wallet): The wallet to register.
            pow_result (POWSolution): The pow result to register.
            wait_for_finalization (bool): If ``true``, waits for the extrinsic to be finalized.
        Returns:
            success (bool): ``True`` if the extrinsic was included in a block.
            error (Optional[str]): ``None`` on success or not waiting for inclusion/finalization, otherwise the error message.
        """

        register_msg = {
            "register": {
                "netuid": netuid,
                "block_number": pow_result.block_number,
                "nonce": pow_result.nonce,
                "work": [int(byte_) for byte_ in pow_result.seal],
                "hotkey": wallet.hotkey.address,
                "coldkey": wallet.coldkeypub.address,
            }
        }
        signer_wallet = LocalWallet(
            PrivateKey(wallet.hotkey.private_key), self.address_prefix
        )

        return self.make_call_with_retry_2(
            wait_for_finalization=wait_for_finalization,
            msg=register_msg,
            signer_wallet=signer_wallet)

    def _do_swap_hotkey(
        self,
        wallet: "Wallet",
        new_wallet: "Wallet",
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        # TODO implement it
        pass
        return False, 'Not implemented'

    def burned_register(
        self,
        wallet: "Wallet",
        netuid: int,
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """Registers the wallet to chain by recycling GBOOT."""
        return burned_register_message(
            cwtensor=self,
            wallet=wallet,
            netuid=netuid,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    def _do_burned_register(
        self,
        netuid: int,
        burn: int,
        wallet: "Wallet",
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        burned_register_msg = {
            "burned_register": {"netuid": netuid, "hotkey": wallet.hotkey.address}
        }
        signer_wallet = LocalWallet(
            PrivateKey(wallet.coldkey.private_key), self.address_prefix
        )
        funds = burn.__str__().__add__(self.token)

        return self.make_call_with_retry_2(
            wait_for_finalization=wait_for_finalization,
            msg=burned_register_msg,
            funds=funds,
            signer_wallet=signer_wallet)

    ##################
    #### Transfer ####
    ##################
    def transfer(
        self,
        wallet: "Wallet",
        dest: str,
        amount: Union[Balance, float],
        wait_for_finalization: bool = False,
        prompt: bool = False,
    ) -> bool:
        """
        Executes a transfer of funds from the provided wallet to the specified destination address.
        This function is used to move TAO tokens within the cybertensor network, facilitating transactions
        between neurons.
        Args:
            wallet (cybertensor.Wallet): The wallet from which funds are being transferred.
            dest (str): The destination public key address.
            amount (Union[cybertensor.Balance, float]): The amount of TAO to be transferred.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
            prompt (bool, optional): If ``True``, prompts for user confirmation before proceeding.
        Returns:
            bool: ``True`` if the transfer is successful, False otherwise.
        This function is essential for the fluid movement of tokens in the network, supporting
        various economic activities such as staking, delegation, and reward distribution.
        """
        return transfer_message(
            cwtensor=self,
            wallet=wallet,
            dest=dest,
            amount=amount,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    def get_transfer_fee(
        self, gas_limit: int = cybertensor.__default_transfer_gas__
    ) -> Balance:
        """
        Calculates the transaction fee for transferring tokens from a wallet to a specified destination address.
        This function simulates the transfer to estimate the associated cost, taking into account the current
        network conditions and transaction complexity.
        Args:
            gas_limit (int): The limit of gas
        Returns:
            Balance: The estimated transaction fee for the transfer, represented as a Balance object.
        Estimating the transfer fee is essential for planning and executing token transactions, ensuring that the
        wallet has sufficient funds to cover both the transfer amount and the associated costs. This function
        provides a crucial tool for managing financial operations within the cybertensor network.
        """
        return Balance.from_coin(
            coin_from_str(self.client.estimate_fee_from_gas(gas_limit=gas_limit))
        )

    def _do_transfer(
        self,
        wallet: "Wallet",
        dest: Address,
        transfer_balance: Balance,
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Sends a transfer message to the chain.
        Args:
            wallet (cybertensor.Wallet): Wallet object.
            dest (str): Destination public key address.
            transfer_balance (cybertensor.Balance): Amount to transfer.
            wait_for_finalization (bool): If true, waits for finalization.
        Returns:
            success (bool): True if transfer was successful.
            tx_hash (str): Tx hash of the transfer.
                (On success and if wait_for_ finalization/inclusion is True)
            error (str): Error message if transfer failed.
        """
        signer_wallet = LocalWallet(
            PrivateKey(wallet.coldkey.private_key), self.address_prefix
        )
        tx = self.client.send_tokens(
            destination=dest,
            amount=transfer_balance.boot,
            denom=self.token,
            sender=signer_wallet,
            gas_limit=cybertensor.__default_transfer_gas__,
        )

        if not wait_for_finalization:
            return True, None, None

        tx.wait_to_complete()

        if tx.response.height:
            tx_hash = tx.response.hash
            return True, tx_hash, None
        else:
            return False, None, tx.response.raw_log

    def get_existential_deposit(self, block: Optional[int] = None) -> Optional[Balance]:
        """
        Retrieves the existential deposit amount for the cybertensor network. The existential deposit
        is the minimum amount of GBOOT required for an account to exist on the blockchain. Accounts with
        balances below this threshold can be reaped to conserve network resources.
        Args:
            block (int, optional): Block number at which to query the deposit amount. If ``None``,
                the current block is used.
        Returns:
            Optional[cybertensor.Balance]: The existential deposit amount, or ``None`` if the query fails.

        The existential deposit is a fundamental economic parameter in the cybertensor network, ensuring
        efficient use of storage and preventing the proliferation of dust accounts.
        """
        # TODO Is it needed?
        return Balance.from_boot(0)

    #################
    #### Network ####
    #################
    def register_subnetwork(
        self,
        wallet: "Wallet",
        wait_for_finalization=True,
        prompt: bool = False,
    ) -> bool:
        """
        Registers a new subnetwork on the cybertensor network using the provided wallet. This function
        is used for the creation and registration of subnetworks, which are specialized segments of the
        overall cybertensor network.
        Args:
            wallet (cybertensor.Wallet): The wallet to be used for registration.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
            prompt (bool, optional): If ``True``, prompts for user confirmation before proceeding.
        Returns:
            bool: ``True`` if the subnetwork registration is successful, False otherwise.
        This function allows for the expansion and diversification of the cybertensor network, supporting
        its decentralized and adaptable architecture.
        """
        return register_subnetwork_message(
            self,
            wallet=wallet,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    def set_hyperparameter(
        self,
        wallet: "Wallet",
        netuid: int,
        parameter: str,
        value,
        wait_for_finalization=True,
        prompt: bool = False,
    ) -> bool:
        """
        Sets a specific hyperparameter for a given subnetwork on the cybertensor blockchain. This action
        involves adjusting network-level parameters, influencing the behavior and characteristics of the
        subnetwork.
        Args:
            wallet (cybertensor.Wallet): The wallet used for setting the hyperparameter.
            netuid (int): The unique identifier of the subnetwork.
            parameter (str): The name of the hyperparameter to be set.
            value: The new value for the hyperparameter.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
            prompt (bool, optional): If ``True``, prompts for user confirmation before proceeding.
        Returns:
            bool: ``True`` if the hyperparameter setting is successful, False otherwise.
        This function plays a critical role in the dynamic governance and adaptability of the cybertensor
        network, allowing for fine-tuning of network operations and characteristics.
        """
        return set_hyperparameter_message(
            self,
            wallet=wallet,
            netuid=netuid,
            parameter=parameter,
            value=value,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    #################
    #### Serving ####
    #################

    def serve(
        self,
        wallet: "Wallet",
        ip: str,
        port: int,
        protocol: int,
        netuid: int,
        placeholder1: int = 0,
        placeholder2: int = 0,
        wait_for_finalization=True,
        prompt: bool = False,
    ) -> bool:
        """
        Registers a neuron's serving endpoint on the cybertensor network. This function announces the
        IP address and port where the neuron is available to serve requests, facilitating peer-to-peer
        communication within the network.
        Args:
            wallet (cybertensor.Wallet): The wallet associated with the neuron being served.
            ip (str): The IP address of the serving neuron.
            port (int): The port number on which the neuron is serving.
            protocol (int): The protocol type used by the neuron (e.g., GRPC, HTTP).
            netuid (int): The unique identifier of the subnetwork.
            Other arguments: Placeholder parameters for future extensions.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
            prompt (bool, optional): If ``True``, prompts for user confirmation before proceeding.
        Returns:
            bool: ``True`` if the serve registration is successful, False otherwise.

        This function is essential for establishing the neuron's presence in the network, enabling
        it to participate in the decentralized machine learning processes of cybertensor.
        """
        return serve_message(
            self,
            wallet,
            ip,
            port,
            protocol,
            netuid,
            placeholder1,
            placeholder2,
            wait_for_finalization,
        )

    def serve_axon(
        self,
        netuid: int,
        axon: "cybertensor.axon",
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """
        Registers an Axon serving endpoint on the cybertensor network for a specific neuron. This function
        is used to set up the Axon, a key component of a neuron that handles incoming queries and data
        processing tasks.
        Args:
            netuid (int): The unique identifier of the subnetwork.
            axon (cybertensor.axon): The Axon instance to be registered for serving.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
            prompt (bool, optional): If ``True``, prompts for user confirmation before proceeding.
        Returns:
            bool: ``True`` if the Axon serve registration is successful, False otherwise.
        
        By registering an Axon, the neuron becomes an active part of the network's distributed
        computing infrastructure, contributing to the collective intelligence of cybertensor.
        """

        return serve_axon_message(self, netuid, axon, wait_for_finalization)

    def _do_serve_axon(
        self,
        wallet: "Wallet",
        call_params: AxonServeCallParams,
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Internal method to submit a serve axon transaction to the cybertensor blockchain. This method
        creates and submits a transaction, enabling a neuron's Axon to serve requests on the network.
        Args:
            wallet (cybertensor.wallet): The wallet associated with the neuron.
            call_params (AxonServeCallParams): Parameters required for the serve axon call.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
        Returns:
            Tuple[bool, Optional[str]]: A tuple containing a success flag and an optional error message.
        This function is crucial for initializing and announcing a neuron's Axon service on the network,
        enhancing the decentralized computation capabilities of cybertensor.
        """
        signer_wallet = LocalWallet(
            PrivateKey(wallet.hotkey.private_key), self.address_prefix
        )

        msg = {"serve_axon": {
            "netuid": call_params['netuid'],
            "version": call_params['version'],
            "ip": str(call_params['ip']),
            "port": call_params['port'],
            "ip_type": call_params['ip_type'],
            "protocol": call_params['protocol'],
            "placeholder1": call_params['placeholder1'],
            "placeholder2": call_params['placeholder2'],
        }}

        return self.make_call_with_retry_2(
            wait_for_finalization=wait_for_finalization,
            msg=msg,
            signer_wallet=signer_wallet)

    def serve_prometheus(
        self,
        wallet: "Wallet",
        port: int,
        netuid: int,
        wait_for_finalization: bool = True,
    ) -> bool:
        return prometheus_message(
            self,
            wallet=wallet,
            port=port,
            netuid=netuid,
            wait_for_finalization=wait_for_finalization,
        )

    def _do_serve_prometheus(
        self,
        wallet: "Wallet",
        call_params: PrometheusServeCallParams,
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Sends a serve prometheus extrinsic to the chain.
        Args:
            wallet (cybertensor.Wallet): Wallet object.
            call_params (PrometheusServeCallParams): Prometheus serve call parameters.
            wait_for_finalization (bool): If true, waits for finalization.
        Returns:
            success (bool): True if serve prometheus was successful.
            error (str, optional): Error message if serve prometheus failed, None otherwise.
        """

        signer_wallet = LocalWallet(
            PrivateKey(wallet.hotkey.private_key), self.address_prefix
        )

        msg = {"serve_prometheus": {
            "netuid": call_params['netuid'],
            "version": call_params['version'],
            "ip": str(call_params['ip']),
            "port": call_params['port'],
            "ip_type": call_params['ip_type'],
        }}

        return self.make_call_with_retry_2(
            wait_for_finalization=wait_for_finalization,
            msg=msg,
            signer_wallet=signer_wallet)

    #################
    #### Staking ####
    #################
    def add_stake(
        self,
        wallet: "Wallet",
        hotkey: Optional[str] = None,
        amount: Optional[Union[Balance, float]] = None,
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """
        Adds the specified amount of stake to a neuron identified by the hotkey address. Staking
        is a fundamental process in the cybertensor network that enables neurons to participate actively
        and earn incentives.
        Args:
            wallet (cybertensor.Wallet): The wallet to be used for staking.
            hotkey (str, optional): The address of the hotkey associated with the neuron.
            amount (Union[cybertensor.Balance, float]): The amount of GBOOT to stake.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
            prompt (bool, optional): If ``True``, prompts for user confirmation before proceeding.
        Returns:
            bool: ``True`` if the staking is successful, False otherwise.
        This function enables neurons to increase their stake in the network, enhancing their influence
        and potential rewards in line with cybertensor's consensus and reward mechanisms.

        """
        return add_stake_message(
            cwtensor=self,
            wallet=wallet,
            hotkey=hotkey,
            amount=amount,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    def add_stake_multiple(
        self,
        wallet: "Wallet",
        hotkeys: List[str],
        amounts: Optional[List[Union[Balance, float]]] = None,
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """
        Adds stakes to multiple neurons identified by their hotkey addresses. This bulk operation
        allows for efficient staking across different neurons from a single wallet.
        Args:
            wallet (cybertensor.Wallet): The wallet used for staking.
            hotkey (List[str]): List of addresses of hotkeys to stake to.
            amounts (List[Union[cybertensor.Balance, float]], optional): Corresponding amounts of GBOOT to stake for each hotkey.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
            prompt (bool, optional): If ``True``, prompts for user confirmation before proceeding.
        Returns:
            bool: ``True`` if the staking is successful for all specified neurons, False otherwise.
        This function is essential for managing stakes across multiple neurons, reflecting the dynamic
        and collaborative nature of the cybertensor network.
        """
        return add_stake_multiple_message(
            self,
            wallet,
            hotkeys,
            amounts,
            wait_for_finalization,
            prompt,
        )

    def _do_stake(
        self,
        wallet: "Wallet",
        hotkey: str,
        amount: Balance,
        wait_for_finalization: bool = True,
    ) -> bool:
        """
        Sends a stake message to the chain.
        Args:
            wallet (cybertensor.Wallet): Wallet object that can sign the extrinsic.
            hotkey (str): Hotkey address to stake to.
            amount (cybertensor.Balance): Amount to stake.
            wait_for_finalization (bool): If ``true``, waits for finalization before returning.
        Returns:
            success (bool): ``True`` if the extrinsic was successful.
        Raises:
            StakeError: If the extrinsic failed.
        """

        add_stake_msg = {"add_stake": {"hotkey": hotkey}}
        signer_wallet = LocalWallet(
            PrivateKey(wallet.coldkey.private_key), self.address_prefix
        )
        funds = amount.boot.__str__().__add__(self.token)

        return self.make_call_with_retry(
            wait_for_finalization=wait_for_finalization,
            msg=add_stake_msg,
            signer_wallet=signer_wallet,
            funds=funds,
            error=StakeError)

    ###################
    #### Unstaking ####
    ###################
    def unstake_multiple(
        self,
        wallet: "Wallet",
        hotkeys: List[str],
        amounts: Optional[List[Union[Balance, float]]] = None,
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """
        Performs batch unstaking from multiple hotkey accounts, allowing a neuron to reduce its staked amounts
        efficiently. This function is useful for managing the distribution of stakes across multiple neurons.
        Args:
            wallet (cybertensor.wallet): The wallet linked to the coldkey from which the stakes are being withdrawn.
            hotkey (List[str]): A list of hotkey addresses to unstake from.
            amounts (List[Union[cybertensor.Balance, float]], optional): The amounts of GBOOT to unstake from each hotkey.
                If not provided, unstakes all available stakes.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
            prompt (bool, optional): If ``True``, prompts for user confirmation before proceeding.
        Returns:
            bool: ``True`` if the batch unstaking is successful, False otherwise.

        This function allows for strategic reallocation or withdrawal of stakes, aligning with the dynamic
        stake management aspect of the cybertensor network.
        """
        return unstake_multiple_message(
            self,
            wallet,
            hotkeys,
            amounts,
            wait_for_finalization,
            prompt,
        )

    def unstake(
        self,
        wallet: "Wallet",
        hotkey: Optional[str] = None,
        amount: Optional[Union[Balance, float]] = None,
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """
        Removes a specified amount of stake from a single hotkey account. This function is critical for adjusting
        individual neuron stakes within the cybertensor network.
        Args:
            wallet (cybertensor.Wallet): The wallet associated with the neuron from which the stake is being removed.
            hotkey (Optional[str]): The address of the hotkey account to unstake from.
            amount (Union[cybertensor.Balance, float], optional): The amount of GBOOT to unstake. If not specified, unstakes all.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
            prompt (bool, optional): If ``True``, prompts for user confirmation before proceeding.
        Returns:
            bool: ``True`` if the unstaking process is successful, False otherwise.
        This function supports flexible stake management, allowing neurons to adjust their network participation
        and potential reward accruals.
        """
        return unstake_message(
            self,
            wallet,
            hotkey,
            amount,
            wait_for_finalization,
            prompt,
        )

    def _do_unstake(
        self,
        wallet: "Wallet",
        hotkey: str,
        amount: Balance,
        wait_for_finalization: bool = False,
    ) -> bool:
        """
        Sends an unstake extrinsic to the chain.
        Args:
            wallet (cybertensor.Wallet): Wallet object that can sign the extrinsic.
            hotkey (str): Hotkey address to unstake from.
            amount (cybertensor.Balance): Amount to unstake.
            wait_for_finalization (bool): If ``true``, waits for finalization before returning.
        Returns:
            success (bool): ``True`` if the extrinsic was successful.
        Raises:
            StakeError: If the extrinsic failed.
        """

        remove_stake_msg = {"remove_stake": {"hotkey": hotkey, "amount": amount.boot}}
        signer_wallet = LocalWallet(
            PrivateKey(wallet.coldkey.private_key), self.address_prefix
        )

        return self.make_call_with_retry(
            wait_for_finalization=wait_for_finalization,
            msg=remove_stake_msg,
            signer_wallet=signer_wallet,
            error=StakeError)

    ##############
    #### Root ####
    ##############

    def root_register(
        self,
        wallet: "Wallet",
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """
        Registers the neuron associated with the wallet on the root network. This process is integral for
        participating in the highest layer of decision-making and governance within the cybertensor network.
        Args:
            wallet (cybertensor.Wallet): The wallet associated with the neuron to be registered on the root network.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
            prompt (bool, optional): If ``True``, prompts for user confirmation before proceeding.
        Returns:
            bool: ``True`` if the registration on the root network is successful, False otherwise.

        This function enables neurons to engage in the most critical and influential aspects of the network's
        governance, signifying a high level of commitment and responsibility in the cybertensor ecosystem.
        """
        return root_register_message(
            cwtensor=self,
            wallet=wallet,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    def _do_root_register(
        self,
        wallet: "Wallet",
        wait_for_finalization: bool = True,
    ) -> bool:

        root_register_msg = {"root_register": {"hotkey": wallet.hotkey.address}}

        return self._execute_contract(
            wait_for_finalization=wait_for_finalization,
            msg=root_register_msg,
            wallet=wallet,
            error=RegistrationError,
            use_hotkey=False,
            logging_prefix='root register',
            exception_text='Neuron was not registered in root')

    def root_set_weights(
        self,
        wallet: "Wallet",
        netuids: Union[torch.LongTensor, list],
        weights: Union[torch.FloatTensor, list],
        version_key: int = 0,
        wait_for_finalization: bool = False,
        prompt: bool = False,
    ) -> bool:
        """
        Sets the weights for neurons on the root network. This action is crucial for defining the influence
        and interactions of neurons at the root level of the cybertensor network.
        Args:
            wallet (cybertensor.wallet): The wallet associated with the neuron setting the weights.
            netuids (Union[torch.LongTensor, list]): The list of neuron UIDs for which weights are being set.
            weights (Union[torch.FloatTensor, list]): The corresponding weights to be set for each UID.
            version_key (int, optional): Version key for compatibility with the network.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
            prompt (bool, optional): If ``True``, prompts for user confirmation before proceeding.
        Returns:
            bool: ``True`` if the setting of root-level weights is successful, False otherwise.

        This function plays a pivotal role in shaping the root network's collective intelligence and decision-making
        processes, reflecting the principles of decentralized governance and collaborative learning in cybertensor.
        """

        return set_root_weights_message(
            cwtensor=self,
            wallet=wallet,
            netuids=netuids,
            weights=weights,
            version_key=version_key,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    #####################################
    #### Hyper parameter calls. ####
    #####################################

    def difficulty(self, netuid: int, block: Optional[int] = None) -> Optional[int]:
        """
        Retrieves the 'Difficulty' hyperparameter for a specified subnet in the cybertensor network.
        This parameter is instrumental in determining the computational challenge required for neurons
        to participate in consensus and validation processes.
        Args:
            netuid (int): The unique identifier of the subnet.
            block (int, optional): The blockchain block number for the query.
        Returns:
            Optional[int]: The value of the 'Difficulty' hyperparameter if the subnet exists, ``None`` otherwise.
        The 'Difficulty' parameter directly impacts the network's security and integrity by setting the computational
        effort required for validating transactions and participating in the network's consensus mechanism.
        """
        difficulty = self.contract.query(
            {"get_difficulty": {"netuid": netuid}}
        )

        if difficulty is None:
            return None

        return difficulty

    def recycle(self, netuid: int, block: Optional[int] = None) -> Optional[Balance]:
        """
        Retrieves the 'Burn' hyperparameter for a specified subnet. The 'Burn' parameter represents the
        amount of GBOOT that is effectively recycled within the cybertensor network.

        Args:
            netuid (int): The unique identifier of the subnet.
            block (Optional[int], optional): The blockchain block number for the query.

        Returns:
            Optional[cybertensor.Balance]: The value of the 'Burn' hyperparameter if the subnet exists, None otherwise.

        Understanding the 'Burn' rate is essential for analyzing the network registration usage, particularly
        how it is correlated with user activity and the overall cost of participation in a given subnet.
        """
        if not self.subnet_exists(netuid, block):
            return None
        _result = self.contract.query(
            {"get_burn": {"netuid": netuid}}
        )
        if _result is None:
            return None
        return Balance.from_boot(_result)

    def min_allowed_weights(
        self, netuid: int, block: Optional[int] = None
    ) -> Optional[int]:
        """Returns network MinAllowedWeights hyperparameter"""
        min_allowed_weights = self.contract.query(
            {"get_min_allowed_weights": {"netuid": netuid}}
        )

        if min_allowed_weights is None:
            return None

        return min_allowed_weights

    def max_weight_limit(
        self, netuid: int, block: Optional[int] = None
    ) -> Optional[float]:
        """Returns network MaxWeightsLimit hyperparameter"""
        max_weight_limit = self.contract.query(
            {"get_max_weight_limit": {"netuid": netuid}}
        )

        if max_weight_limit is None:
            return None

        return U16_NORMALIZED_FLOAT(max_weight_limit)

    def subnetwork_n(self, netuid: int, block: Optional[int] = None) -> Optional[int]:
        """Returns network SubnetworkN hyperparameter"""
        # TODO replace with direct query
        # subnetwork_n = self.contract.query({"get_subnetwork_n": {"netuid": netuid}})
        # if subnetwork_n is None:
        #     return None
        #
        # return subnetwork_n

        subnet_info = self.get_subnet_info(netuid)
        if subnet_info is None:
            return None

        return subnet_info.subnetwork_n

    # def max_n(self, netuid: int, block: Optional[int] = None) -> Optional[int]:
    #     """Returns network MaxAllowedUids hyper parameter"""
    #     if not self.subnet_exists(netuid, block):
    #         return None
    #     _res = self.contract.query(
    #         {"max_allowed_uids": {"netuid": netuid}}
    #     )
    #     if _res is None:
    #         return None
    #     return _res
    #
    # def blocks_since_epoch(
    #     self, netuid: int, block: Optional[int] = None
    # ) -> Optional[int]:
    #     """Returns network BlocksSinceLastStep hyper parameter"""
    #     if not self.subnet_exists(netuid, block):
    #         return None
    #     _res = self.contract.query(
    #         {"block_since_last_step": {"netuid": netuid}}
    #     )
    #     if _res is None:
    #         return None
    #     return _res

    # def blocks_since_last_update(self, netuid: int, uid: int) -> Optional[int]:
        # if not self.subnet_exists(netuid):
        #     return None
        # _res = self.contract.query(
        #     {"block_since_last_update": {"netuid": netuid, "uid": uid}}
        # )
        # if _res is None:
        #     return None
        # return _res

    # def weights_rate_limit(self, netuid: int) -> Optional[int]:
        # if not self.subnet_exists(netuid):
        #     return None
        # _res = self.contract.query(
        #     {"weights_set_rate_limit": {"netuid": netuid}}
        # )
        # if _res is None:
        #     return None
        # return _res

    def tempo(self, netuid: int, block: Optional[int] = None) -> Optional[int]:
        """Returns network Tempo hyperparameter"""
        tempo = self.contract.query({"get_tempo": {"netuid": netuid}})

        if tempo is None:
            return None

        return tempo

    ##########################
    #### Account functions ###
    ##########################

    def get_total_stake_for_hotkey(
        self, address: str, block: Optional[int] = None
    ) -> Optional["Balance"]:
        """Returns the total stake held on a hotkey including delegative"""
        return Balance.from_boot(
            self.contract.query({"get_total_stake_for_hotkey": {"address": address}})
        )

    def get_total_stake_for_coldkey(
        self, address: str, block: Optional[int] = None
    ) -> Optional["Balance"]:
        """Returns the total stake held on a coldkey across all hotkeys including delegates"""
        resp = self.contract.query(
            {"get_total_stake_for_coldkey": {"address": address}}
        )
        return Balance.from_boot(resp) if resp is not None else Balance(0)

    def get_stake_for_coldkey_and_hotkey(
        self, hotkey: str, coldkey: str, block: Optional[int] = None
    ) -> Optional["Balance"]:
        """Returns the stake under a coldkey - hotkey pairing"""
        resp = self.contract.query(
            {"get_stake_for_coldkey_and_hotkey": {"coldkey": coldkey, "hotkey": hotkey}}
        )
        return Balance.from_boot(resp) if resp is not None else Balance(0)

    def get_stake(
        self, hotkey: str, block: Optional[int] = None
    ) -> List[Tuple[str, "Balance"]]:
        """Returns a list of stake tuples (coldkey, balance) for each delegating coldkey including the owner"""
        return [
            (r[0].value, Balance.from_boot(r[1].value))
            for r in self.contract.query({"get_stake": {"hotkey": hotkey}})
        ]

    def does_hotkey_exist(self, hotkey: str, block: Optional[int] = None) -> bool:
        """Returns true if the hotkey is known by the chain and there are accounts."""
        return self.contract.query({"get_hotkey_exist": {"hotkey": hotkey}})

    def get_hotkey_owner(
        self, hotkey: str, block: Optional[int] = None
    ) -> Optional[str]:
        """Returns the coldkey owner of the passed hotkey"""
        # TODO remove one call
        if self.does_hotkey_exist(hotkey, block):
            return self.contract.query({"get_hotkey_owner": {"hotkey": hotkey}})
        else:
            return None

    def get_axon_info(
        self, netuid: int, hotkey: str, block: Optional[int] = None
    ) -> Optional[AxonInfo]:
        """Returns the axon information for this hotkey account"""
        result = self.contract.query(
            {"get_axon_info": {"netuid": netuid, "hotkey": hotkey}}
        )

        if result is not None:
            return AxonInfo(
                ip=cybertensor.utils.networking.int_to_ip(result.value["ip"]),
                ip_type=result.value["ip_type"],
                port=result.value["port"],
                protocol=result.value["protocol"],
                version=result.value["version"],
                placeholder1=result.value["placeholder1"],
                placeholder2=result.value["placeholder2"],
            )
        else:
            return None

    def get_prometheus_info(
        self, netuid: int, hotkey: str, block: Optional[int] = None
    ) -> Optional[PrometheusInfo]:
        """Returns the prometheus information for this hotkey account"""
        result = self.contract.query(
            {"get_prometheus_info": {"netuid": netuid, "hotkey": hotkey}}
        )
        if result is not None:
            return PrometheusInfo(
                ip=cybertensor.utils.networking.int_to_ip(result.value["ip"]),
                ip_type=result.value["ip_type"],
                port=result.value["port"],
                version=result.value["version"],
                block=result.value["block"],
            )
        else:
            return None

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
        """
        Retrieves the total issuance of the cybertensor network's native token (Tao) as of a specific
        blockchain block. This represents the total amount of currency that has been issued or mined on the network.
        Args:
            block (int, optional): The blockchain block number at which to perform the query.
        Returns:
            Balance: The total issuance of TAO, represented as a Balance object.
        The total issuance is a key economic indicator in the cybertensor network, reflecting the overall supply
        of the currency and providing insights into the network's economic health and inflationary trends.
        """
        return Balance.from_boot(self.contract.query({"get_total_issuance": {}}))

    def total_stake(self, block: Optional[int] = None) -> "Balance":
        """
        Retrieves the total amount of TAO staked on the cybertensor network as of a specific blockchain block.
        This represents the cumulative stake across all neurons in the network, indicating the overall level
        of participation and investment by the network's participants.
        Args:
            block (int, optional): The blockchain block number at which to perform the query.
        Returns:
            Balance: The total amount of TAO staked on the network, represented as a Balance object.
        The total stake is an important metric for understanding the network's security, governance dynamics,
        and the level of commitment by its participants. It is also a critical factor in the network's
        consensus and incentive mechanisms.
        """
        return Balance.from_boot(self.contract.query({"get_total_stake": {}}))

    def tx_rate_limit(self, block: Optional[int] = None) -> Optional[int]:
        """
        Retrieves the transaction rate limit for the cybertensor network as of a specific blockchain block.
        This rate limit sets the maximum number of transactions that can be processed within a given time frame.
        Args:
            block (int, optional): The blockchain block number at which to perform the query.
        Returns:
            Optional[int]: The transaction rate limit of the network, None if not available.
        
        The transaction rate limit is an essential parameter for ensuring the stability and scalability
        of the cybertensor network. It helps in managing network load and preventing congestion, thereby
        maintaining efficient and timely transaction processing.
        """
        return self.contract.query({"get_tx_rate_limit": {}})

    #####################################
    #### Network Parameters ####
    #####################################

    def get_subnet_burn_cost(self, block: Optional[int] = None) -> Optional[int]:
        lock_cost = self.contract.query({"get_network_registration_cost": {}})

        if lock_cost is None:
            return None

        return lock_cost

    def subnet_exists(self, netuid: int, block: Optional[int] = None) -> bool:
        """
        Checks if a subnet with the specified unique identifier (netuid) exists within the cybertensor network.
        Args:
            netuid (int): The unique identifier of the subnet.
            block (int, optional): The blockchain block number at which to check the subnet's existence.
        Returns:
            bool: ``True`` if the subnet exists, False otherwise.
        This function is critical for verifying the presence of specific subnets in the network,
        enabling a deeper understanding of the network's structure and composition.
        """
        assert isinstance(netuid, int)
        return self.contract.query({"get_subnet_exist": {"netuid": netuid}})

    def get_all_subnet_netuids(self, block: Optional[int] = None) -> List[int]:
        """
        Retrieves the list of all subnet unique identifiers (netuids) currently present in the cybertensor network.
        Args:
            block (int, optional): The blockchain block number at which to retrieve the subnet netuids.
        Returns:
            List[int]: A list of subnet netuids.
        This function provides a comprehensive view of the subnets within the cybertensor network,
        offering insights into its diversity and scale.
        """
        return self.contract.query({"get_all_subnet_netuids": {}})

    def get_total_subnets(self, block: Optional[int] = None) -> int:
        """
        Retrieves the total number of subnets within the cybertensor network as of a specific blockchain block.
        Args:
            block (int, optional): The blockchain block number for the query.
        Returns:
            int: The total number of subnets in the network.
        Understanding the total number of subnets is essential for assessing the network's growth and
        the extent of its decentralized infrastructure.
        """
        return self.contract.query({"get_total_networks": {}})

    def get_emission_value_by_subnet(
        self, netuid: int, block: Optional[int] = None
    ) -> Optional[float]:
        """
        Retrieves the emission value of a specific subnet within the cybertensor network. The emission value
        represents the rate at which the subnet emits or distributes the network's native token (Tao).
        Args:
            netuid (int): The unique identifier of the subnet.
            block (int, optional): The blockchain block number for the query.
        Returns:
            Optional[float]: The emission value of the subnet, None if not available.
        The emission value is a critical economic parameter, influencing the incentive distribution and
        reward mechanisms within the subnet.
        """
        return Balance.from_boot(
            # TODO what if zero
            self.contract.query({"get_emission_value_by_subnet": {"netuid": netuid}})
        )

    def get_subnets(self, block: Optional[int] = None) -> List[int]:
        """
        Retrieves a list of all subnets currently active within the cybertensor network. This function
        provides an overview of the various subnets and their identifiers.
        Args:
            block (int, optional): The blockchain block number for the query.
        Returns:
            List[int]: A list of network UIDs representing each active subnet.
        This function is valuable for understanding the network's structure and the diversity of subnets
        available for neuron participation and collaboration.
        """
        return self.contract.query({"get_networks_added": {}})

    def get_all_subnets_info(self, block: Optional[int] = None) -> List[SubnetInfo]:
        """
        Retrieves detailed information about all subnets within the cybertensor network. This function
        provides comprehensive data on each subnet, including its characteristics and operational parameters.
        Args:
            block (int, optional): The blockchain block number for the query.
        Returns:
            List[SubnetInfo]: A list of SubnetInfo objects, each containing detailed information about a subnet.
        Gaining insights into the subnets' details assists in understanding the network's composition,
        the roles of different subnets, and their unique features.
        """
        result = self.contract.query({"get_subnets_info": {}})

        if result in (None, []):
            return []

        return SubnetInfo.list_from_list_any(result)

    def get_subnet_info(self, netuid: int, block: Optional[int] = None) -> Optional[SubnetInfo]:
        """
        Retrieves detailed information about a specific subnet within the cybertensor network. This function
        provides key data on the subnet, including its operational parameters and network status.
        Args:
            netuid (int): The network UID of the subnet to query.
            block (int, optional): The blockchain block number for the query.
        Returns:
            Optional[SubnetInfo]: Detailed information about the subnet, or ``None`` if not found.
        This function is essential for neurons and stakeholders interested in the specifics of a particular
        subnet, including its governance, performance, and role within the broader network.
        """
        result = self.contract.query({"get_subnet_info": {"netuid": netuid}})

        if result is None:
            return None

        return SubnetInfo.fix_decoded_values(result)

    def get_subnet_hyperparameters(
        self, netuid: int, block: Optional[int] = None
    ) -> Optional[Union[List, SubnetHyperparameters]]:
        """
        Retrieves the hyperparameters for a specific subnet within the cybertensor network. These hyperparameters
        define the operational settings and rules governing the subnet's behavior.
        Args:
            netuid (int): The network UID of the subnet to query.
            block (int, optional): The blockchain block number for the query.
        Returns:
            Optional[SubnetHyperparameters]: The subnet's hyperparameters, or ``None`` if not available.
        Understanding the hyperparameters is crucial for comprehending how subnets are configured and
        managed, and how they interact with the network's consensus and incentive mechanisms.
        """
        result = self.contract.query({"get_subnet_hyperparams": {"netuid": netuid}})

        if result in (None, []):
            return []

        return SubnetHyperparameters.from_list_any(result)  # type: ignore

    def get_subnet_owner(
        self, netuid: int, block: Optional[int] = None
    ) -> Optional[str]:
        """
        Retrieves the owner's address of a specific subnet within the cybertensor network. The owner is
        typically the entity responsible for the creation and maintenance of the subnet.
        Args:
            netuid (int): The network UID of the subnet to query.
            block (int, optional): The blockchain block number for the query.
        Returns:
            Optional[str]: The address of the subnet's owner, or ``None`` if not available.
        Knowing the subnet owner provides insights into the governance and operational control of the subnet,
        which can be important for decision-making and collaboration within the network.
        """
        resp = self.contract.query({"get_subnet_owner": {"netuid": netuid}})
        if resp is None:
            return None
        else:
            return resp

    ####################
    #### Nomination ####
    ####################

    def is_hotkey_delegate(self, hotkey: str, block: Optional[int] = None) -> bool:
        """
        Determines whether a given hotkey (public key) is a delegate on the cybertensor network. This function
        checks if the neuron associated with the hotkey is part of the network's delegation system.
        Args:
            hotkey (str): The address of the neuron's hotkey.
            block (int, optional): The blockchain block number for the query.
        Returns:
            bool: ``True`` if the hotkey is a delegate, ``False`` otherwise.
        Being a delegate is a significant status within the cybertensor network, indicating a neuron's
        involvement in consensus and governance processes.
        """
        return hotkey in [info.hotkey for info in self.get_delegates(block=block)]

    def get_delegate_take(
        self, hotkey: str, block: Optional[int] = None
    ) -> Optional[float]:
        """
        Retrieves the delegate 'take' percentage for a neuron identified by its hotkey. The 'take'
        represents the percentage of rewards that the delegate claims from its nominators' stakes.
        Args:
            hotkey (str): The address of the neuron's hotkey.
            block (int, optional): The blockchain block number for the query.
        Returns:
            Optional[float]: The delegate take percentage, None if not available.
        The delegate take is a critical parameter in the network's incentive structure, influencing
        the distribution of rewards among neurons and their nominators.
        """
        return U16_NORMALIZED_FLOAT(
            self.contract.query({"get_delegate_take": {"hotkey": hotkey}})
        )

    def get_nominators_for_hotkey(
        self, hotkey: str, block: Optional[int] = None
    ) -> Union[List[Tuple[str, Balance]], int]:
        """
        Retrieves a list of nominators and their stakes for a neuron identified by its hotkey.
        Nominators are neurons that stake their tokens on a delegate to support its operations.
        Args:
            hotkey (str): The address of the neuron's hotkey.
            block (int, optional): The blockchain block number for the query.
        Returns:
           Union[List[Tuple[str, Balance]], int]: A list of tuples containing each nominator's address and staked amount or 0.
        This function provides insights into the neuron's support network within the cybertensor ecosystem,
        indicating its trust and collaboration relationships.
        """
        result = self.contract.query({"get_stake": {"hotkey": hotkey}})
        if result is not None:
            return [(record[0].value, record[1].value) for record in result]
        else:
            return 0

    def get_delegate_by_hotkey(
        self, hotkey: str, block: Optional[int] = None
    ) -> Optional[DelegateInfo]:
        """
        Retrieves detailed information about a delegate neuron based on its hotkey. This function provides
        a comprehensive view of the delegate's status, including its stakes, nominators, and reward distribution.
        Args:
            hotkey (str): The address of the delegate's hotkey.
            block (int, optional): The blockchain block number for the query.
        Returns:
            Optional[DelegateInfo]: Detailed information about the delegate neuron, ``None`` if not found.
        This function is essential for understanding the roles and influence of delegate neurons within
        the cybertensor network's consensus and governance structures.
        """
        result = self.contract.query({"get_delegate": {"delegate": hotkey}})

        if result in (None, []):
            return None

        return DelegateInfo.from_list_any(result)

    def get_delegates(self, block: Optional[int] = None) -> List[DelegateInfo]:
        """
        Retrieves a list of all delegate neurons within the cybertensor network. This function provides an
        overview of the neurons that are actively involved in the network's delegation system.
        Args:
            block (int, optional): The blockchain block number for the query.
        Returns:
            List[DelegateInfo]: A list of DelegateInfo objects detailing each delegate's characteristics.
        Analyzing the delegate population offers insights into the network's governance dynamics and the
        distribution of trust and responsibility among participating neurons.
        """
        result = self.contract.query({"get_delegates": {}})

        if result in (None, []):
            return []

        return DelegateInfo.list_from_list_any(result)

    # TODO revisit
    def get_delegates_details_from_chain(
        self, block: Optional[int] = None
    ) -> Dict[str, DelegatesDetails]:
        result = self.contract.query({"get_delegates": {}})

        # if result in (None, []):
        #     return []

        all_delegates_details = {}
        for i in result:
            all_delegates_details[i["delegate"]] = DelegatesDetails.from_json(
                {
                    "name": "mock",
                    "url": "mock",
                    "description": "mock",
                    "signature": "mock",
                }
            )
        return all_delegates_details

    def get_delegated(
        self, delegatee: str, block: Optional[int] = None
    ) -> List[Tuple[DelegateInfo, Balance]]:
        """
        Retrieves a list of delegates and their associated stakes for a given coldkey. This function
        identifies the delegates that a specific account has staked tokens on.
        Args:
            delegatee (str): The address of the account's coldkey.
            block (int, optional): The blockchain block number for the query.
        Returns:
            List[Tuple[DelegateInfo, Balance]]: A list of tuples, each containing a delegate's information and staked amount.
        This function is important for account holders to understand their stake allocations and their
        involvement in the network's delegation and consensus mechanisms.
        """

        result = self.contract.query({"get_delegated": {"delegatee": delegatee}})

        if result in (None, []):
            return []

        return DelegateInfo.delegated_list_from_list_any(result)

    ###########################
    #### Stake Information ####
    ###########################

    def get_stake_info_for_coldkey(
        self, coldkey: str, block: Optional[int] = None
    ) -> List[StakeInfo]:
        """
        Retrieves stake information associated with a specific coldkey. This function provides details
        about the stakes held by an account, including the staked amounts and associated delegates.
        Args:
            coldkey (str): The address of the account's coldkey.
            block (int, optional): The blockchain block number for the query.
        Returns:
            List[StakeInfo]: A list of StakeInfo objects detailing the stake allocations for the account.
        Stake information is vital for account holders to assess their investment and participation
        in the network's delegation and consensus processes.
        """

        result = self.contract.query(
            {"get_stake_info_for_coldkey": {"coldkey": coldkey}}
        )

        return StakeInfo.list_from_list_any(result)  # type: ignore

    def get_stake_info_for_coldkeys(
        self, coldkey_list: List[str], block: Optional[int] = None
    ) -> Dict[str, List[StakeInfo]]:
        """
        Retrieves stake information for a list of coldkeys. This function aggregates stake data for multiple
        accounts, providing a collective view of their stakes and delegations.
        Args:
            coldkey_list (List[str]): A list of addresses of the accounts' coldkeys.
            block (int, optional): The blockchain block number for the query.
        Returns:
            Dict[str, List[StakeInfo]]: A dictionary mapping each coldkey to a list of its StakeInfo objects.
        This function is useful for analyzing the stake distribution and delegation patterns of multiple
        accounts simultaneously, offering a broader perspective on network participation and investment strategies.
        """
        result = self.contract.query(
            {"get_stake_info_for_coldkeys": {"coldkeys": coldkey_list}}
        )

        return StakeInfo.list_of_tuple_from_list_any(result)

    ########################################
    #### Neuron information per subnet ####
    ########################################

    def is_hotkey_registered_any(
        self, hotkey: str, block: Optional[int] = None
    ) -> bool:
        """
        Checks if a neuron's hotkey is registered on any subnet within the cybertensor network.
        Args:
            hotkey (str): The address of the neuron's hotkey.
            block (int, optional): The blockchain block number at which to perform the check.
        Returns:
            bool: ``True`` if the hotkey is registered on any subnet, False otherwise.
        This function is essential for determining the network-wide presence and participation of a neuron.
        """
        return len(self.get_netuids_for_hotkey(hotkey, block)) > 0

    def is_hotkey_registered_on_subnet(
        self, hotkey: str, netuid: int, block: Optional[int] = None
    ) -> bool:
        """
        Checks if a neuron's hotkey is registered on a specific subnet within the cybertensor network.
        Args:
            hotkey (str): The address of the neuron's hotkey.
            netuid (int): The unique identifier of the subnet.
            block (int, optional): The blockchain block number at which to perform the check.
        Returns:
            bool: ``True`` if the hotkey is registered on the specified subnet, False otherwise.
        This function helps in assessing the participation of a neuron in a particular subnet,
        indicating its specific area of operation or influence within the network.
        """
        return self.get_uid_for_hotkey_on_subnet(hotkey, netuid, block) is not None

    def is_hotkey_registered(
        self,
        hotkey: str,
        netuid: Optional[int] = None,
        block: Optional[int] = None,
    ) -> bool:
        """
        Determines whether a given hotkey (public key) is registered in the cybertensor network, either
        globally across any subnet or specifically on a specified subnet. This function checks the registration
        status of a neuron identified by its hotkey, which is crucial for validating its participation and
        activities within the network.
        Args:
            hotkey (str): The address of the neuron's hotkey.
            netuid (int, optional): The unique identifier of the subnet to check the registration.
                If ``None``, the registration is checked across all subnets.
            block (int, optional): The blockchain block number at which to perform the query.
        Returns:
            bool: ``True`` if the hotkey is registered in the specified context (either any subnet or a specific
                subnet), ``False`` otherwise.
        This function is important for verifying the active status of neurons in the cybertensor network. It aids
        in understanding whether a neuron is eligible to participate in network processes such as consensus,
        validation, and incentive distribution based on its registration status.
        """
        if netuid is None:
            return self.is_hotkey_registered_any(hotkey, block)
        else:
            return self.is_hotkey_registered_on_subnet(hotkey, netuid, block)

    def get_uid_for_hotkey_on_subnet(
        self, hotkey: str, netuid: int, block: Optional[int] = None
    ) -> Optional[int]:
        """
        Retrieves the unique identifier (UID) for a neuron's hotkey on a specific subnet.
        Args:
            hotkey (str): The address of the neuron's hotkey.
            netuid (int): The unique identifier of the subnet.
            block (int, optional): The blockchain block number for the query.
        Returns:
            Optional[int]: The UID of the neuron if it is registered on the subnet, ``None`` otherwise.
        The UID is a critical identifier within the network, linking the neuron's hotkey to its
        operational and governance activities on a particular subnet.
        """
        resp = self.contract.query(
            {"get_uid_for_hotkey_on_subnet": {"netuid": netuid, "hotkey": hotkey}}
        )
        if resp is None:
            return None
        else:
            return resp

    def get_all_uids_for_hotkey(
        self, hotkey: str, block: Optional[int] = None
    ) -> List[int]:
        """
        Retrieves all unique identifiers (UIDs) associated with a given hotkey across different subnets
        within the cybertensor network. This function helps in identifying all the neuron instances that are
        linked to a specific hotkey.
        Args:
            hotkey (str): The address of the neuron's hotkey.
            block (int, optional): The blockchain block number at which to perform the query.
        Returns:
            List[int]: A list of UIDs associated with the given hotkey across various subnets.
        This function is important for tracking a neuron's presence and activities across different
        subnets within the cybertensor ecosystem.
        """
        return [
            self.get_uid_for_hotkey_on_subnet(hotkey, netuid, block)
            for netuid in self.get_netuids_for_hotkey(hotkey, block)
        ]

    def get_netuids_for_hotkey(
        self, hotkey: str, block: Optional[int] = None
    ) -> List[int]:
        """
        Retrieves a list of subnet UIDs (netuids) for which a given hotkey is a member. This function
        identifies the specific subnets within the cybertensor network where the neuron associated with
        the hotkey is active.
        Args:
            hotkey (str): The address of the neuron's hotkey.
            block (int, optional): The blockchain block number at which to perform the query.
        Returns:
            List[int]: A list of netuids where the neuron is a member.
        """
        resp = self.contract.query({"get_netuids_for_hotkey": {"hotkey": hotkey}})
        if resp in (None, []):
            return []
        else:
            return resp

    def get_neuron_for_pubkey_and_subnet(
        self, hotkey: str, netuid: int, block: Optional[int] = None
    ) -> Optional[NeuronInfo]:
        """
        Retrieves information about a neuron based on its hotkey address and the specific subnet UID (netuid).
        This function provides detailed neuron information for a particular subnet within the cybertensor network.
        Args:
            hotkey (str): The address of the neuron's hotkey.
            netuid (int): The unique identifier of the subnet.
            block (int, optional): The blockchain block number at which to perform the query.
        Returns:
            Optional[NeuronInfo]: Detailed information about the neuron if found, ``None`` otherwise.
        This function is crucial for accessing specific neuron data and understanding its status, stake,
        and other attributes within a particular subnet of the cybertensor ecosystem.
        """
        return self.neuron_for_uid(
            self.get_uid_for_hotkey_on_subnet(hotkey, netuid, block=block),
            netuid,
            block=block,
        )

    def get_all_neurons_for_pubkey(
        self, hotkey: str, block: Optional[int] = None
    ) -> Optional[List[NeuronInfo]]:
        """
        Retrieves information about all neuron instances associated with a given public key (hotkey address) across
        different subnets of the cybertensor network. This function aggregates neuron data from various subnets
        to provide a comprehensive view of a neuron's presence and status within the network.
        Args:
            hotkey (str): The address of the neuron's hotkey.
            block (int, optional): The blockchain block number for the query.
        Returns:
            Optional[List[NeuronInfo]]: A list of NeuronInfo objects detailing the neuron's presence across various subnets.
        This function is valuable for analyzing a neuron's overall participation, influence, and
        contributions across the cybertensor network.
        """
        netuids = self.get_netuids_for_hotkey(hotkey, block)
        uids = [self.get_uid_for_hotkey_on_subnet(hotkey, net) for net in netuids]
        return [self.neuron_for_uid(uid, net) for uid, net in list(zip(uids, netuids))]  # type: ignore

    def neuron_for_uid(
        self, uid: int, netuid: int, block: Optional[int] = None
    ) -> Optional[NeuronInfo]:
        """
        Retrieves detailed information about a specific neuron identified by its unique identifier (UID)
        within a specified subnet (netuid) of the cybertensor network. This function provides a comprehensive
        view of a neuron's attributes, including its stake, rank, and operational status.
        Args:
            uid (int): The unique identifier of the neuron.
            netuid (int): The unique identifier of the subnet.
            block (int, optional): The blockchain block number for the query.
        Returns:
            Optional[NeuronInfo]: Detailed information about the neuron if found, ``None`` otherwise.
        This function is crucial for analyzing individual neurons' contributions and status within a specific
        subnet, offering insights into their roles in the network's consensus and validation mechanisms.
        """
        if uid is None:
            return NeuronInfo._null_neuron()

        resp = self.contract.query({"get_neuron": {"netuid": netuid, "uid": uid}})
        if resp in (None, []):
            return NeuronInfo._null_neuron()

        return NeuronInfo.from_list_any(resp)

    def neurons(self, netuid: int, block: Optional[int] = None) -> List[NeuronInfo]:
        """
        Retrieves a list of all neurons within a specified subnet of the cybertensor network. This function
        provides a snapshot of the subnet's neuron population, including each neuron's attributes and network
        interactions.
        Args:
            netuid (int): The unique identifier of the subnet.
            block (int, optional): The blockchain block number for the query.
        Returns:
            List[NeuronInfo]: A list of NeuronInfo objects detailing each neuron's characteristics in the subnet.
        Understanding the distribution and status of neurons within a subnet is key to comprehending the
        network's decentralized structure and the dynamics of its consensus and governance processes.
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
        """
        Retrieves a list of neurons in a 'lite' format from a specific subnet of the cybertensor network.
        This function provides a streamlined view of the neurons, focusing on key attributes such as stake
        and network participation.
        Args:
            netuid (int): The unique identifier of the subnet.
            block (int, optional): The blockchain block number for the query.
        Returns:
            List[NeuronInfoLite]: A list of simplified neuron information for the subnet.
        This function offers a quick overview of the neuron population within a subnet, facilitating
        efficient analysis of the network's decentralized structure and neuron dynamics.
        """

        resp = self.contract.query({"get_neurons_lite": {"netuid": netuid}})
        if resp in (None, []):
            return []

        return NeuronInfoLite.list_from_list_any(resp)  # type: ignore

    def metagraph(
        self,
        netuid: int,
        lite: bool = True,
        block: Optional[int] = None,
    ) -> "cybertensor.Metagraph":
        """
        Returns a synced metagraph for a specified subnet within the cybertensor network. The metagraph
        represents the network's structure, including neuron connections and interactions.
        Args:
            netuid (int): The network UID of the subnet to query.
            lite (bool, default=True): If true, returns a metagraph using a lightweight sync (no weights, no bonds).
            block (Optional[int]): Block number for synchronization, or ``None`` for the latest block.
        Returns:
            cybertensor.Metagraph: The metagraph representing the subnet's structure and neuron relationships.
        The metagraph is an essential tool for understanding the topology and dynamics of the cybertensor
        network's decentralized architecture, particularly in relation to neuron interconnectivity and consensus processes.
        """
        metagraph_ = cybertensor.metagraph(
            network=self.network, netuid=netuid, lite=lite, sync=False
        )
        metagraph_.sync(block=block, lite=lite, cwtensor=self)

        return metagraph_

    def weights(
        self, netuid: int, block: Optional[int] = None
    ) -> List[Tuple[int, List[Tuple[int, int]]]]:
        """
        Retrieves the weight distribution set by neurons within a specific subnet of the cybertensor network.
        This function maps each neuron's UID to the weights it assigns to other neurons, reflecting the
        network's trust and value assignment mechanisms.
        Args:
            netuid (int): The network UID of the subnet to query.
            block (Optional[int]): The blockchain block number for the query.
        Returns:
            List[Tuple[int, List[Tuple[int, int]]]]: A list of tuples mapping each neuron's UID to its assigned weights.
        The weight distribution is a key factor in the network's consensus algorithm and the ranking of neurons,
        influencing their influence and reward allocation within the subnet.
        """
        w_map = []

        # TODO test and debug this later
        # weights = self.contract.query({"get_weights": {"netuid": netuid}})
        weights_sparse = self.contract.query({"get_weights_sparse": {"netuid": netuid}})
        # print(f"weights: {weights}")
        # print(f"weights: {weights_sparse}")
        if weights_sparse is not None:
            for uid, w in enumerate(weights_sparse):
                w_map.append((uid, w))

        return w_map

    def bonds(
        self, netuid: int, block: Optional[int] = None
    ) -> List[Tuple[int, List[Tuple[int, int]]]]:
        """
        Retrieves the bond distribution set by neurons within a specific subnet of the cybertensor network.
        Bonds represent the investments or commitments made by neurons in one another, indicating a level
        of trust and perceived value. This bonding mechanism is integral to the network's market-based approach
        to measuring and rewarding machine intelligence.

        Args:
            netuid (int): The network UID of the subnet to query.
            block (int, optional): The blockchain block number for the query.

        Returns:
            List[Tuple[int, List[Tuple[int, int]]]]: A list of tuples mapping each neuron's UID to its bonds with other neurons.

        Understanding bond distributions is crucial for analyzing the trust dynamics and market behavior
        within the subnet. It reflects how neurons recognize and invest in each other's intelligence and
        contributions, supporting diverse and niche systems within the cybertensor ecosystem.
        """
        # TODO implement it
        return []

    #################
    #### General ####
    #################

    def get_balance(self, address: str, block: Optional[int] = None) -> Balance:
        """
        Retrieves the token balance of a specific address within the cybertensor network.
        This function queries the blockchain to determine the amount of GBOOT held by a given account.
        Args:
            address (str): The address.
            block (int, optional): The blockchain block number at which to perform the query.
        Returns:
            Balance: The account balance at the specified block, represented as a Balance object.
        This function is important for monitoring account holdings and managing financial transactions
        within the cybertensor ecosystem. It helps in assessing the economic status and capacity of network participants.
        """

        @retry(delay=2, tries=3, backoff=2, max_delay=4)
        def make_call_with_retry() -> Balance:
            return Balance.from_boot(
                self.client.query_bank_balance(Address(address), self.token)
            )

        balance = make_call_with_retry()

        return balance

    # TODO rewrite logic
    def get_current_block(self) -> int:
        """
        Returns the current block number on the cybertensor blockchain. This function provides the latest block
        number, indicating the most recent state of the blockchain.
        Returns:
            int: The current chain block number.
        Knowing the current block number is essential for querying real-time data and performing time-sensitive
        operations on the blockchain. It serves as a reference point for network activities and data synchronization.
        """
        return self.client.query_latest_block().height

    # TODO rewrite logic
    def get_block_hash(self, block_id: int) -> str:
        """
        # It is not possible to obtain a block hash from a blockchain node.

        Retrieves the hash of a specific block on the cybertensor blockchain. The block hash is a unique
        identifier representing the cryptographic hash of the block's content, ensuring its integrity and
        immutability.
        Args:
            block_id (int): The block number for which the hash is to be retrieved.
        Returns:
            str: The cryptographic hash of the specified block.
        The block hash is a fundamental aspect of blockchain technology, providing a secure reference to
        each block's data. It is crucial for verifying transactions, ensuring data consistency, and
        maintaining the trustworthiness of the blockchain.
        """
        return "0x0000000000000000000000000000000000000000000000000000000000000000"
