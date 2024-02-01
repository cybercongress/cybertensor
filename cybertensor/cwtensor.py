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

import argparse
import copy
import os
from typing import List, Dict, Union, Optional, Tuple, TypedDict

import torch
from cosmpy.aerial.client import LedgerClient
from cosmpy.aerial.contract import LedgerContract
from cosmpy.aerial.wallet import LocalWallet
from cosmpy.crypto.address import Address
from cosmpy.crypto.keypairs import PrivateKey
from loguru import logger
from retry import retry

import cybertensor
from .chain_data import (
    NeuronInfo,
    DelegateInfo,
    PrometheusInfo,
    SubnetInfo,
    SubnetHyperparameters,
    StakeInfo,
    NeuronInfoLite,
    AxonInfo,
)
from .commands.utils import DelegatesDetails
from .errors import *
from .messages.delegation import (
    delegate_message,
    nominate_message,
    undelegate_message,
)
from .messages.network import (
    register_subnetwork_message,
    set_hyperparameter_message,
)
from .messages.prometheus import prometheus_message
from .messages.registration import (
    register_message,
    burned_register_message,
)
from .messages.root import root_register_message, set_root_weights_message
from .messages.serving import serve_message, serve_axon_message
from .messages.set_weights import set_weights_message
from .messages.staking import add_stake_message, add_stake_multiple_message
from .messages.transfer import transfer_message
from .messages.unstaking import unstake_message, unstake_multiple_message
from .types import AxonServeCallParams, PrometheusServeCallParams
from .utils import U16_NORMALIZED_FLOAT, coin_from_str
from .utils.balance import Balance
from .utils.registration import POWSolution

logger = logger.opt(colors=True)


class cwtensor:
    """Factory Class for cybertensor.cwtensor

    The cwtensor class handles interactions with the substrate cwtensor chain.
    By default, the cwtensor class connects to the Finney which serves as the main cybertensor network.
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
        prefix_str = "" if prefix is None else prefix + "."
        try:
            default_network = os.getenv("CT_CYBER_NETWORK") or "space-pussy"
            # default_contract_address = os.getenv("CT_CONTRACT_ADDRESS") or "bostrom1"

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
    def setup_config(network: str, config: "cybertensor.config"):
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
                        -- bostrom (main network)
                        -- local (local running network)
                        -- space-pussy (space-pussy network)
                or cwtensor endpoint flag. If set, overrides the network argument.
        """

        # Determine config.cwtensor.chain_endpoint and config.cwtensor.network config.
        # If chain_endpoint is set, we override the network flag, otherwise, the chain_endpoint is assigned by the network.
        # Argument importance: network > config.cwtensor.network
        if config is None:
            config = cwtensor.config()
        self.config = copy.deepcopy(config)

        # Setup config.cwtensor.network and config.cwtensor.chain_endpoint
        (
            self.network,
            self.network_config,
        ) = cwtensor.setup_config(network, config)
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

    def __str__(self) -> str:
        # Connecting to network with endpoint known.
        return (
            f"cwtensor({self.network}, {self.network_config}, {self.contract_address})"
        )

    def __repr__(self) -> str:
        return self.__str__()

    #####################
    #### Delegation #####
    #####################
    def nominate(
        self,
        wallet: "cybertensor.wallet",
        wait_for_finalization: bool = True,
    ) -> bool:
        """Becomes a delegate for the hotkey."""
        return nominate_message(
            cwtensor=self,
            wallet=wallet,
            wait_for_finalization=wait_for_finalization,
        )

    def _do_nominate(
        self,
        wallet: "cybertensor.wallet",
        wait_for_finalization: bool = True,
    ) -> bool:
        nominate_msg = {"become_delegate": {"hotkey": wallet.hotkey.address}}
        signer_wallet = LocalWallet(
            PrivateKey(wallet.coldkey.private_key), self.address_prefix
        )
        gas = cybertensor.__default_gas__

        @retry(delay=2, tries=3, backoff=2, max_delay=4)
        def make_call_with_retry():
            if not wait_for_finalization:
                self.contract.execute(nominate_msg, signer_wallet, gas)
                return True
            else:
                tx = self.contract.execute(nominate_msg, signer_wallet, gas)
                try:
                    tx.wait_to_complete()
                    if tx.response.is_successful():
                        return True
                    else:
                        raise NominationError(tx.response.logs)
                except Exception as e:
                    raise NominationError(e.__str__())

        return make_call_with_retry()

    def delegate(
        self,
        wallet: "cybertensor.wallet",
        delegate: Optional[str] = None,
        amount: Union[Balance, float] = None,
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """Adds the specified amount of stake to the passed delegate using the passed wallet."""
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
        wallet: "cybertensor.wallet",
        delegate: str,
        amount: "Balance",
        wait_for_finalization: bool = True,
    ) -> bool:
        delegation_msg = {"add_stake": {"hotkey": delegate}}
        signer_wallet = LocalWallet(
            PrivateKey(wallet.coldkey.private_key), self.address_prefix
        )
        gas = cybertensor.__default_gas__
        funds = amount.boot.__str__().__add__(self.token)

        @retry(delay=2, tries=3, backoff=2, max_delay=4)
        def make_call_with_retry():
            if not wait_for_finalization:
                self.contract.execute(delegation_msg, signer_wallet, gas, funds)
                return True
            else:
                tx = self.contract.execute(delegation_msg, signer_wallet, gas, funds)
                try:
                    tx.wait_to_complete()
                    if tx.response.is_successful():
                        return True
                    else:
                        raise StakeError(tx.response.code)
                except Exception as e:
                    raise StakeError(e.__str__())

        return make_call_with_retry()

    def undelegate(
        self,
        wallet: "cybertensor.wallet",
        delegate: Optional[str] = None,
        amount: Union[Balance, float] = None,
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """Removes the specified amount of stake from the passed delegate using the passed wallet."""
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
        wallet: "cybertensor.wallet",
        delegate: str,
        amount: "Balance",
        wait_for_finalization: bool = True,
    ) -> bool:
        undelegation_msg = {"remove_stake": {"hotkey": delegate, "amount": amount.boot}}
        signer_wallet = LocalWallet(
            PrivateKey(wallet.coldkey.private_key), self.address_prefix
        )
        gas = cybertensor.__default_gas__

        @retry(delay=2, tries=3, backoff=2, max_delay=4)
        def make_call_with_retry():
            if not wait_for_finalization:
                self.contract.execute(undelegation_msg, signer_wallet, gas)
                return True
            else:
                tx = self.contract.execute(undelegation_msg, signer_wallet, gas)
                try:
                    tx.wait_to_complete()
                    if tx.response.is_successful():
                        return True
                    else:
                        raise StakeError(tx.response.code)
                except Exception as e:
                    raise StakeError(e.__str__())

        return make_call_with_retry()

    #####################
    #### Set Weights ####
    #####################

    def set_weights(
        self,
        wallet: "cybertensor.wallet",
        netuid: int,
        uids: Union[torch.LongTensor, torch.Tensor, list],
        weights: Union[torch.FloatTensor, torch.Tensor, list],
        version_key: int = cybertensor.__version_as_int__,
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        return set_weights_message(
            cwtensor=self,
            wallet=wallet,
            netuid=netuid,
            uids=uids,
            weights=weights,
            version_key=version_key,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    def _do_set_weights(
        self,
        wallet: "cybertensor.wallet",
        uids: List[int],
        vals: List[int],
        netuid: int,
        version_key: int = cybertensor.__version_as_int__,
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:  # (success, error_message)
        set_weights_msg = {
            "set_weights": {
                "netuid": netuid,
                "dests": uids,
                "weights": vals,
                "version_key": version_key,
            }
        }
        signer_wallet = LocalWallet(
            PrivateKey(wallet.hotkey.private_key), self.address_prefix
        )
        gas = cybertensor.__default_gas__

        @retry(delay=2, tries=3, backoff=2, max_delay=4)
        def make_call_with_retry():
            if not wait_for_finalization:
                self.contract.execute(set_weights_msg, signer_wallet, gas)
                return True, None
            else:
                tx = self.contract.execute(set_weights_msg, signer_wallet, gas)
                try:
                    tx.wait_to_complete()
                    if tx.response.is_successful():
                        return True, None
                    else:
                        return False, tx.response.code
                except Exception as e:
                    return False, e.__str__()

        return make_call_with_retry()

    ######################
    #### Registration ####
    ######################
    def register(
        self,
        wallet: "cybertensor.wallet",
        netuid: int,
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
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """Sends a (POW) register extrinsic to the chain.
        Args:
            netuid (int): the subnet to register on.
            wallet (cybertensor.wallet): the wallet to register.
            pow_result (POWSolution): the pow result to register.
            wait_for_finalization (bool): if true, waits for the extrinsic to be finalized.
        Returns:
            success (bool): True if the extrinsic was included in a block.
            error (Optional[str]): None on success or not waiting for inclusion/finalization, otherwise the error message.
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
        gas = cybertensor.__default_gas__

        # TODO check decorator and improve error handling
        @retry(delay=2, tries=3, backoff=2, max_delay=4)
        def make_call_with_retry():
            if not wait_for_finalization:
                self.contract.execute(register_msg, signer_wallet, gas)
                return True, None
            else:
                tx = self.contract.execute(register_msg, signer_wallet, gas)
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
        wallet: "cybertensor.wallet",
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        burned_register_msg = {
            "burned_register": {"netuid": netuid, "hotkey": wallet.hotkey.address}
        }
        signer_wallet = LocalWallet(
            PrivateKey(wallet.coldkey.private_key), self.address_prefix
        )
        gas = cybertensor.__default_gas__
        funds = burn.__str__().__add__(self.token)

        @retry(delay=2, tries=3, backoff=2, max_delay=4)
        def make_call_with_retry():
            if not wait_for_finalization:
                self.contract.execute(burned_register_msg, signer_wallet, gas, funds)
                return True, None
            else:
                tx = self.contract.execute(
                    burned_register_msg, signer_wallet, gas, funds
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
    def transfer(
        self,
        wallet: "cybertensor.wallet",
        dest: str,
        amount: Union[Balance, float],
        wait_for_inclusion: bool = True,
        wait_for_finalization: bool = False,
        prompt: bool = False,
    ) -> bool:
        """Transfers funds from this wallet to the destination public key address"""
        return transfer_message(
            cwtensor=self,
            wallet=wallet,
            dest=dest,
            amount=amount,
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    def get_transfer_fee(
        self, gas_limit: int = cybertensor.__default_transfer_gas__
    ) -> Balance:
        return Balance.from_coin(
            coin_from_str(self.client.estimate_fee_from_gas(gas_limit=gas_limit))
        )

    def _do_transfer(
        self,
        wallet: "cybertensor.wallet",
        dest: Address,
        transfer_balance: Balance,
        wait_for_inclusion: bool = True,
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Sends a transfer extrinsic to the chain.
        Args:
            wallet (:obj:`cybertensor.wallet`): Wallet object.
            dest (:obj:`str`): Destination public key address.
            transfer_balance (:obj:`Balance`): Amount to transfer.
            wait_for_inclusion (:obj:`bool`): If true, waits for inclusion.
            wait_for_finalization (:obj:`bool`): If true, waits for finalization.
        Returns:
            success (:obj:`bool`): True if transfer was successful.
            tx_hash (:obj:`str`): Tx hash of the transfer.
                (On success and if wait_for_ finalization/inclusion is True)
            error (:obj:`str`): Error message if transfer failed.
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

        if not wait_for_finalization and not wait_for_inclusion:
            return True, None, None

        tx.wait_to_complete()

        if tx.response.height:
            tx_hash = tx.response.hash
            return True, tx_hash, None
        else:
            return False, None, tx.response.raw_log

    def get_existential_deposit(self, block: Optional[int] = None) -> Optional[Balance]:
        """Returns the existential deposit for the chain."""
        # TODO Is it needed?
        return Balance.from_boot(0)

    #################
    #### Network ####
    #################
    def register_subnetwork(
        self,
        wallet: "cybertensor.wallet",
        wait_for_finalization=True,
        prompt: bool = False,
    ) -> bool:
        return register_subnetwork_message(
            self,
            wallet=wallet,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    def set_hyperparameter(
        self,
        wallet: "cybertensor.wallet",
        netuid: int,
        parameter: str,
        value,
        wait_for_finalization=True,
        prompt: bool = False,
    ) -> bool:
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
        return serve_axon_message(self, netuid, axon, wait_for_finalization)

    def _do_serve_axon(
        self,
        wallet: "cybertensor.wallet",
        call_params: AxonServeCallParams,
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        signer_wallet = LocalWallet(
            PrivateKey(wallet.hotkey.private_key), self.address_prefix
        )
        gas = cybertensor.__default_gas__

        @retry(delay=2, tries=3, backoff=2, max_delay=4)
        def make_call_with_retry():
            if not wait_for_finalization:
                self.contract.execute(call_params, signer_wallet, gas)
                return True, None
            else:
                tx = self.contract.execute(call_params, signer_wallet, gas)
                try:
                    tx.wait_to_complete()
                    if tx.response.is_successful():
                        return True, None
                    else:
                        return False, tx.response.code
                except Exception as e:
                    return False, e.__str__()

        return make_call_with_retry()

    def serve_prometheus(
        self,
        wallet: "cybertensor.wallet",
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
        wallet: "cybertensor.wallet",
        call_params: PrometheusServeCallParams,
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Sends a serve prometheus extrinsic to the chain.
        Args:
            wallet (:obj:`cybertensor.wallet`): Wallet object.
            call_params (:obj:`PrometheusServeCallParams`): Prometheus serve call parameters.
            wait_for_finalization (:obj:`bool`): If true, waits for finalization.
        Returns:
            success (:obj:`bool`): True if serve prometheus was successful.
            error (:obj:`Optional[str]`): Error message if serve prometheus failed, None otherwise.
        """

        signer_wallet = LocalWallet(
            PrivateKey(wallet.hotkey.private_key), self.address_prefix
        )
        gas = cybertensor.__default_gas__

        @retry(delay=2, tries=3, backoff=2, max_delay=4)
        def make_call_with_retry():
            if not wait_for_finalization:
                self.contract.execute(call_params, signer_wallet, gas)
                return True, None
            else:
                tx = self.contract.execute(call_params, signer_wallet, gas)
                try:
                    tx.wait_to_complete()
                    if tx.response.is_successful():
                        return True, None
                    else:
                        return False, tx.response.code
                except Exception as e:
                    return False, e.__str__()

        return make_call_with_retry()

    #################
    #### Staking ####
    #################
    def add_stake(
        self,
        wallet: "cybertensor.wallet",
        hotkey: Optional[str] = None,
        amount: Union[Balance, float] = None,
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """Adds the specified amount of stake to passed hotkey uid."""
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
        wallet: "cybertensor.wallet",
        hotkeys: List[str],
        amounts: List[Union[Balance, float]] = None,
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """Adds stake to each hotkey in the list, using each amount, from a common coldkey."""
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
        wallet: "cybertensor.wallet",
        hotkey: str,
        amount: Balance,
        wait_for_finalization: bool = True,
    ) -> bool:
        """Sends a stake extrinsic to the chain.
        Args:
            wallet (:obj:`cybertensor.wallet`): Wallet object that can sign the extrinsic.
            hotkey (:obj:`str`): Hotkey address to stake to.
            amount (:obj:`Balance`): Amount to stake.
            wait_for_finalization (:obj:`bool`): If true, waits for finalization before returning.
        Returns:
            success (:obj:`bool`): True if the extrinsic was successful.
        Raises:
            StakeError: If the extrinsic failed.
        """

        add_stake_msg = {"add_stake": {"hotkey": hotkey}}
        signer_wallet = LocalWallet(
            PrivateKey(wallet.coldkey.private_key), self.address_prefix
        )
        gas = cybertensor.__default_gas__
        funds = amount.boot.__str__().__add__(self.token)

        @retry(delay=2, tries=3, backoff=2, max_delay=4)
        def make_call_with_retry():
            if not wait_for_finalization:
                self.contract.execute(add_stake_msg, signer_wallet, gas, funds)
                return True
            else:
                tx = self.contract.execute(add_stake_msg, signer_wallet, gas, funds)
                try:
                    tx.wait_to_complete()
                    if tx.response.is_successful():
                        return True
                    else:
                        raise StakeError(tx.response.code)
                except Exception as e:
                    raise StakeError(e.__str__())

        return make_call_with_retry()

    ###################
    #### Unstaking ####
    ###################
    def unstake_multiple(
        self,
        wallet: "cybertensor.wallet",
        hotkeys: List[str],
        amounts: List[Union[Balance, float]] = None,
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """Removes stake from each hotkey in the list, using each amount, to a common coldkey."""
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
        wallet: "cybertensor.wallet",
        hotkey: Optional[str] = None,
        amount: Union[Balance, float] = None,
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """Removes stake into the wallet coldkey from the specified hotkey uid."""
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
        wallet: "cybertensor.wallet",
        hotkey: str,
        amount: Balance,
        wait_for_finalization: bool = False,
    ) -> bool:
        """Sends an unstake extrinsic to the chain.
        Args:
            wallet (:obj:`cybertensor.wallet`): Wallet object that can sign the extrinsic.
            hotkey (:obj:`str`): Hotkey address to unstake from.
            amount (:obj:`Balance`): Amount to unstake.
            wait_for_finalization (:obj:`bool`): If true, waits for finalization before returning.
        Returns:
            success (:obj:`bool`): True if the extrinsic was successful.
        Raises:
            StakeError: If the extrinsic failed.
        """

        remove_stake_msg = {"remove_stake": {"hotkey": hotkey, "amount": amount.boot}}
        signer_wallet = LocalWallet(
            PrivateKey(wallet.coldkey.private_key), self.address_prefix
        )
        gas = cybertensor.__default_gas__

        @retry(delay=2, tries=3, backoff=2, max_delay=4)
        def make_call_with_retry():
            if not wait_for_finalization:
                self.contract.execute(remove_stake_msg, signer_wallet, gas)
                return True
            else:
                tx = self.contract.execute(remove_stake_msg, signer_wallet, gas)
                try:
                    tx.wait_to_complete()
                    if tx.response.is_successful():
                        return True
                    else:
                        raise StakeError(tx.response.code)
                except Exception as e:
                    raise StakeError(e.__str__())

        return make_call_with_retry()

    ##############
    #### Root ####
    ##############

    def root_register(
        self,
        wallet: "cybertensor.wallet",
        wait_for_finalization: bool = True,
        prompt: bool = False,
    ) -> bool:
        """Registers the wallet to root network."""
        return root_register_message(
            cwtensor=self,
            wallet=wallet,
            wait_for_finalization=wait_for_finalization,
            prompt=prompt,
        )

    def _do_root_register(
        self,
        wallet: "cybertensor.wallet",
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        root_register_msg = {"root_register": {"hotkey": wallet.hotkey.address}}
        signer_wallet = LocalWallet(
            PrivateKey(wallet.coldkey.private_key), self.address_prefix
        )
        gas = cybertensor.__default_gas__

        @retry(delay=2, tries=3, backoff=2, max_delay=4)
        def make_call_with_retry():
            if not wait_for_finalization:
                self.contract.execute(root_register_msg, signer_wallet, gas)
                return True, None
            else:
                tx = self.contract.execute(root_register_msg, signer_wallet, gas)
                try:
                    tx.wait_to_complete()
                    if tx.response.is_successful():
                        return True, None
                    else:
                        return False, tx.response.code
                except Exception as e:
                    return False, e.__str__()

        return make_call_with_retry()

    def root_set_weights(
        self,
        wallet: "cybertensor.wallet",
        netuids: Union[torch.LongTensor, torch.Tensor, list],
        weights: Union[torch.FloatTensor, torch.Tensor, list],
        version_key: int = 0,
        wait_for_finalization: bool = False,
        prompt: bool = False,
    ) -> bool:
        """Sets weights for the root network."""
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

    """ Returns network Burn hyper parameter """

    def burn(self, netuid: int, block: Optional[int] = None) -> Optional[int]:
        burn = self.contract.query({"get_burn": {"netuid": netuid}})

        if burn is None:
            return None

        return burn

    """ Returns network Difficulty hyper parameter """

    def difficulty(self, netuid: int, block: Optional[int] = None) -> Optional[int]:
        difficulty = self.contract.query({"get_difficulty": {"netuid": netuid}})

        if difficulty is None:
            return None

        return difficulty

    """ Returns network MinAllowedWeights hyper parameter """

    def min_allowed_weights(
        self, netuid: int, block: Optional[int] = None
    ) -> Optional[int]:
        min_allowed_weights = self.contract.query(
            {"get_min_allowed_weights": {"netuid": netuid}}
        )

        if min_allowed_weights is None:
            return None

        return min_allowed_weights

    """ Returns network MaxWeightsLimit hyper parameter """

    def max_weight_limit(
        self, netuid: int, block: Optional[int] = None
    ) -> Optional[float]:
        max_weight_limit = self.contract.query(
            {"get_max_weight_limit": {"netuid": netuid}}
        )

        if max_weight_limit is None:
            return None

        return U16_NORMALIZED_FLOAT(max_weight_limit)

    """ Returns network Tempo hyper parameter """

    def tempo(self, netuid: int, block: Optional[int] = None) -> Optional[int]:
        tempo = self.contract.query({"get_tempo": {"netuid": netuid}})

        if tempo is None:
            return None

        return tempo

    ##########################
    #### Account functions ###
    ##########################

    """ Returns the total stake held on a hotkey including delegative """

    def get_total_stake_for_hotkey(
        self, address: str, block: Optional[int] = None
    ) -> Optional["Balance"]:
        return Balance.from_boot(
            self.contract.query({"get_total_stake_for_hotkey": {"address": address}})
        )

    """ Returns the total stake held on a coldkey across all hotkeys including delegates"""

    def get_total_stake_for_coldkey(
        self, address: str, block: Optional[int] = None
    ) -> Optional["Balance"]:
        resp = self.contract.query(
            {"get_total_stake_for_coldkey": {"address": address}}
        )
        return Balance.from_boot(resp) if resp is not None else Balance(0)

    """ Returns the stake under a coldkey - hotkey pairing """

    def get_stake_for_coldkey_and_hotkey(
        self, hotkey: str, coldkey: str, block: Optional[int] = None
    ) -> Optional["Balance"]:
        resp = self.contract.query(
            {"get_stake_for_coldkey_and_hotkey": {"coldkey": coldkey, "hotkey": hotkey}}
        )
        return Balance.from_boot(resp) if resp is not None else Balance(0)

    """ Returns a list of stake tuples (coldkey, balance) for each delegating coldkey including the owner"""

    def get_stake(
        self, hotkey: str, block: Optional[int] = None
    ) -> List[Tuple[str, "Balance"]]:
        return [
            (r[0].value, Balance.from_boot(r[1].value))
            for r in self.contract.query({"get_stake": {"hotkey": hotkey}})
        ]

    """ Returns true if the hotkey is known by the chain and there are accounts. """

    def does_hotkey_exist(self, hotkey: str, block: Optional[int] = None) -> bool:
        return self.contract.query({"get_hotkey_exist": {"hotkey": hotkey}})

    """ Returns the coldkey owner of the passed hotkey """

    def get_hotkey_owner(
        self, hotkey: str, block: Optional[int] = None
    ) -> Optional[str]:
        # TODO remove one call
        if self.does_hotkey_exist(hotkey, block):
            return self.contract.query({"get_hotkey_owner": {"hotkey": hotkey}})
        else:
            return None

    """ Returns the axon information for this hotkey account """

    def get_axon_info(
        self, netuid: int, hotkey: str, block: Optional[int] = None
    ) -> Optional[AxonInfo]:
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

    """ Returns the prometheus information for this hotkey account """

    def get_prometheus_info(
        self, netuid: int, hotkey: str, block: Optional[int] = None
    ) -> Optional[PrometheusInfo]:
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
        return Balance.from_boot(self.contract.query({"get_total_issuance": {}}))

    def total_stake(self, block: Optional[int] = None) -> "Balance":
        return Balance.from_boot(self.contract.query({"get_total_stake": {}}))

    def tx_rate_limit(self, block: Optional[int] = None) -> Optional[int]:
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
        assert isinstance(netuid, int)
        return self.contract.query({"get_subnet_exist": {"netuid": netuid}})

    def get_all_subnet_netuids(self, block: Optional[int] = None) -> List[int]:
        subnet_netuids = []
        return self.contract.query({"get_all_subnet_netuids": {}})

    def get_total_subnets(self, block: Optional[int] = None) -> int:
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

    def is_hotkey_delegate(self, hotkey: str, block: Optional[int] = None) -> bool:
        return hotkey in [info.hotkey for info in self.get_delegates(block=block)]

    def get_delegate_take(
        self, hotkey: str, block: Optional[int] = None
    ) -> Optional[float]:
        return U16_NORMALIZED_FLOAT(
            self.contract.query({"get_delegate_take": {"hotkey": hotkey}})
        )

    def get_nominators_for_hotkey(
        self, hotkey: str, block: Optional[int] = None
    ) -> List[Tuple[str, Balance]]:
        result = self.contract.query({"get_stake": {"hotkey": hotkey}})
        if result is not None:
            return [(record[0].value, record[1].value) for record in result]
        else:
            return 0

    def get_delegate_by_hotkey(
        self, hotkey: str, block: Optional[int] = None
    ) -> Optional[DelegateInfo]:
        result = self.contract.query({"get_delegate": {"delegate": hotkey}})

        if result in (None, []):
            return None

        return DelegateInfo.from_list_any(result)

    def get_delegates(self, block: Optional[int] = None) -> List[DelegateInfo]:
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
        """Returns the list of delegates that a given delegatee is staked to."""

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
        """Returns the list of StakeInfo objects for this coldkey"""

        result = self.contract.query(
            {"get_stake_info_for_coldkey": {"coldkey": coldkey}}
        )

        return StakeInfo.list_from_list_any(result)

    def get_stake_info_for_coldkeys(
        self, coldkey_list: List[str], block: Optional[int] = None
    ) -> Dict[str, List[StakeInfo]]:
        """Returns the list of StakeInfo objects for all coldkeys in the list."""
        result = self.contract.query(
            {"get_stake_info_for_coldkeys": {"coldkeys": coldkey_list}}
        )

        return StakeInfo.list_of_tuple_from_vec_u8(result)

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
        return self.get_uid_for_hotkey_on_subnet(hotkey, netuid, block) is not None

    def is_hotkey_registered(
        self,
        hotkey: str,
        netuid: Optional[int] = None,
        block: Optional[int] = None,
    ) -> bool:
        if netuid is None:
            return self.is_hotkey_registered_any(hotkey, block)
        else:
            return self.is_hotkey_registered_on_subnet(hotkey, netuid, block)

    def get_uid_for_hotkey_on_subnet(
        self, hotkey: str, netuid: int, block: Optional[int] = None
    ) -> Optional[int]:
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
        if uid is None:
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
            metagraph ( `cybertensor.Metagraph` ):
                The metagraph for the subnet at the block.
        """
        metagraph_ = cybertensor.metagraph(
            network=self.network, netuid=netuid, lite=lite, sync=False
        )
        metagraph_.sync(block=block, lite=lite, cwtensor=self)

        return metagraph_

    def weights(
        self, netuid: int, block: Optional[int] = None
    ) -> List[Tuple[int, List[Tuple[int, int]]]]:
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

    #################
    #### General ####
    #################

    def get_balance(self, address: str, block: Optional[int] = None) -> Balance:
        r"""Returns the token balance for the passed address
        Args:
            address (cyber address):
                chain address.
            block (int):
                Not used now! block number for getting balance.
        Return:
            balance (cybertensor.utils.balance.Balance):
                account balance
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
        return self.client.query_latest_block().height

    # TODO rewrite logic
    def get_block_hash(self, block_id: int) -> str:
        return "0x0000000000000000000000000000000000000000000000000000000000000000"
