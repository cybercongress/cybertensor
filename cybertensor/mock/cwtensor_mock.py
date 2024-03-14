# The MIT License (MIT)
# Copyright © 2022-2023 Opentensor Foundation
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

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from random import randint
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union
from unittest.mock import MagicMock

from cybertensor import __version_as_int__, Wallet, Balance, cwtensor, GIGA, U16_NORMALIZED_FLOAT
from cybertensor.chain_data import (
    NeuronInfo,
    NeuronInfoLite,
    PrometheusInfo,
    DelegateInfo,
    SubnetInfo,
    AxonInfo,
)
from cybertensor.errors import *
from cybertensor.utils.registration import POWSolution

# Mock Testing Constant
__GLOBAL_MOCK_STATE__ = {}


class AxonServeCallParams(TypedDict):
    """
    Axon serve chain call parameters.
    """

    version: int
    ip: int
    port: int
    ip_type: int
    netuid: int


class PrometheusServeCallParams(TypedDict):
    """
    Prometheus serve chain call parameters.
    """

    version: int
    ip: int
    port: int
    ip_type: int
    netuid: int


BlockNumber = int


class InfoDict(Mapping):
    @classmethod
    def default(cls):
        raise NotImplementedError

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)


@dataclass
class AxonInfoDict(InfoDict):
    block: int
    version: int
    ip: int  # integer representation of ip address
    port: int
    ip_type: int
    protocol: int
    placeholder1: int  # placeholder for future use
    placeholder2: int

    @classmethod
    def default(cls):
        return cls(
            block=0,
            version=0,
            ip=0,
            port=0,
            ip_type=0,
            protocol=0,
            placeholder1=0,
            placeholder2=0,
        )


@dataclass
class PrometheusInfoDict(InfoDict):
    block: int
    version: int
    ip: int  # integer representation of ip address
    port: int
    ip_type: int

    @classmethod
    def default(cls):
        return cls(block=0, version=0, ip=0, port=0, ip_type=0)


@dataclass
class MockCwtensorValue:
    value: Optional[Any]


class MockMapResult:
    records: Optional[List[Tuple[MockCwtensorValue, MockCwtensorValue]]]

    def __init__(
        self,
        records: Optional[
            List[Tuple[Union[Any, MockCwtensorValue], Union[Any, MockCwtensorValue]]]
        ] = None,
    ):
        _records = [
            (
                (
                    MockCwtensorValue(value=record[0]),
                    MockCwtensorValue(value=record[1]),
                )
                # Make sure record is a tuple of MockCwtensorValue (dict with value attr)
                if not (
                    isinstance(record, tuple)
                    and all(
                        isinstance(item, dict) and hasattr(item, "value")
                        for item in record
                    )
                )
                else record
            )
            for record in records
        ]

        self.records = _records

    def __iter__(self):
        return iter(self.records)


class MockSystemState(TypedDict):
    Account: Dict[str, Dict[int, int]]  # address -> block -> balance


class MockCwtensorState(TypedDict):
    Rho: Dict[int, Dict[BlockNumber, int]]  # netuid -> block -> rho
    Kappa: Dict[int, Dict[BlockNumber, int]]  # netuid -> block -> kappa
    Difficulty: Dict[int, Dict[BlockNumber, int]]  # netuid -> block -> difficulty
    ImmunityPeriod: Dict[
        int, Dict[BlockNumber, int]
    ]  # netuid -> block -> immunity_period
    ValidatorBatchSize: Dict[
        int, Dict[BlockNumber, int]
    ]  # netuid -> block -> validator_batch_size
    Active: Dict[int, Dict[BlockNumber, bool]]  # (netuid, uid), block -> active
    Stake: Dict[str, Dict[str, Dict[int, int]]]  # (hotkey, coldkey) -> block -> stake

    Delegates: Dict[str, Dict[int, float]]  # address -> block -> delegate_take

    NetworksAdded: Dict[int, Dict[BlockNumber, bool]]  # netuid -> block -> added


class MockChainState(TypedDict):
    System: MockSystemState
    CwtensorModule: MockCwtensorState


class MockCwtensor(cwtensor):
    """
    A Mock Cwtensor class for running tests.
    This should mock only methods that make queries to the chain.
    e.g. We mock `Cwtensor.query_cwtensor` instead of all query methods.

    This class will also store a local (mock) state of the chain.
    """

    chain_state: MockChainState
    block_number: int

    @classmethod
    def reset(cls) -> None:
        __GLOBAL_MOCK_STATE__.clear()

        _ = cls()

    def setup(self) -> None:
        if not hasattr(self, "chain_state") or getattr(self, "chain_state") is None:
            self.chain_state = {
                "System": {"Account": {}},
                "Balances": {"ExistentialDeposit": {0: 500}},
                "CwtensorModule": {
                    "NetworksAdded": {},
                    "Rho": {},
                    "Kappa": {},
                    "Difficulty": {},
                    "ImmunityPeriod": {},
                    "ValidatorBatchSize": {},
                    "ValidatorSequenceLength": {},
                    "ValidatorEpochsPerReset": {},
                    "ValidatorEpochLength": {},
                    "MaxAllowedValidators": {},
                    "MinAllowedWeights": {},
                    "MaxWeightLimit": {},
                    "SynergyScalingLawPower": {},
                    "ScalingLawPower": {},
                    "SubnetworkN": {},
                    "MaxAllowedUids": {},
                    "NetworkModality": {},
                    "BlocksSinceLastStep": {},
                    "Tempo": {},
                    "NetworkConnect": {},
                    "EmissionValues": {},
                    "Burn": {},
                    "Active": {},
                    "Uids": {},
                    "Keys": {},
                    "Owner": {},
                    "IsNetworkMember": {},
                    "LastUpdate": {},
                    "Rank": {},
                    "Emission": {},
                    "Incentive": {},
                    "Consensus": {},
                    "Trust": {},
                    "ValidatorTrust": {},
                    "Dividends": {},
                    "PruningScores": {},
                    "ValidatorPermit": {},
                    "Weights": {},
                    "Bonds": {},
                    "Stake": {},
                    "TotalStake": {0: 0},
                    "TotalIssuance": {0: 0},
                    "TotalHotkeyStake": {},
                    "TotalColdkeyStake": {},
                    "TxRateLimit": {0: 0},  # No limit
                    "Delegates": {},
                    "Axons": {},
                    "Prometheus": {},
                    "SubnetOwner": {},
                    "Commits": {},
                },
            }

            self.block_number = 0

            self.network = "mock"
            self.chain_endpoint = "mock_endpoint"
            self.substrate = MagicMock()

    def __init__(self, *args, **kwargs) -> None:
        self.__dict__ = __GLOBAL_MOCK_STATE__

        if not hasattr(self, "chain_state") or getattr(self, "chain_state") is None:
            self.setup()

    def get_block_hash(self, block_id: int) -> str:
        return "0x" + sha256(str(block_id).encode()).hexdigest()[:64]

    def create_subnet(self, netuid: int) -> None:
        cwtensor_state = self.chain_state["CwtensorModule"]
        if netuid not in cwtensor_state["NetworksAdded"]:
            # Per Subnet
            cwtensor_state["Rho"][netuid] = {}
            cwtensor_state["Rho"][netuid][0] = 10
            cwtensor_state["Kappa"][netuid] = {}
            cwtensor_state["Kappa"][netuid][0] = 32_767
            cwtensor_state["Difficulty"][netuid] = {}
            cwtensor_state["Difficulty"][netuid][0] = 10_000_000
            cwtensor_state["ImmunityPeriod"][netuid] = {}
            cwtensor_state["ImmunityPeriod"][netuid][0] = 4096
            cwtensor_state["ValidatorBatchSize"][netuid] = {}
            cwtensor_state["ValidatorBatchSize"][netuid][0] = 32
            cwtensor_state["ValidatorSequenceLength"][netuid] = {}
            cwtensor_state["ValidatorSequenceLength"][netuid][0] = 256
            cwtensor_state["ValidatorEpochsPerReset"][netuid] = {}
            cwtensor_state["ValidatorEpochsPerReset"][netuid][0] = 60
            cwtensor_state["ValidatorEpochLength"][netuid] = {}
            cwtensor_state["ValidatorEpochLength"][netuid][0] = 100
            cwtensor_state["MaxAllowedValidators"][netuid] = {}
            cwtensor_state["MaxAllowedValidators"][netuid][0] = 128
            cwtensor_state["MinAllowedWeights"][netuid] = {}
            cwtensor_state["MinAllowedWeights"][netuid][0] = 1024
            cwtensor_state["MaxWeightLimit"][netuid] = {}
            cwtensor_state["MaxWeightLimit"][netuid][0] = 1_000
            cwtensor_state["SynergyScalingLawPower"][netuid] = {}
            cwtensor_state["SynergyScalingLawPower"][netuid][0] = 50
            cwtensor_state["ScalingLawPower"][netuid] = {}
            cwtensor_state["ScalingLawPower"][netuid][0] = 50
            cwtensor_state["SubnetworkN"][netuid] = {}
            cwtensor_state["SubnetworkN"][netuid][0] = 0
            cwtensor_state["MaxAllowedUids"][netuid] = {}
            cwtensor_state["MaxAllowedUids"][netuid][0] = 4096
            cwtensor_state["NetworkModality"][netuid] = {}
            cwtensor_state["NetworkModality"][netuid][0] = 0
            cwtensor_state["BlocksSinceLastStep"][netuid] = {}
            cwtensor_state["BlocksSinceLastStep"][netuid][0] = 0
            cwtensor_state["Tempo"][netuid] = {}
            cwtensor_state["Tempo"][netuid][0] = 99
            # cwtensor_state['NetworkConnect'][netuid] = {}
            # cwtensor_state['NetworkConnect'][netuid][0] = {}
            cwtensor_state["EmissionValues"][netuid] = {}
            cwtensor_state["EmissionValues"][netuid][0] = 0
            cwtensor_state["Burn"][netuid] = {}
            cwtensor_state["Burn"][netuid][0] = 0
            cwtensor_state["Commits"][netuid] = {}

            # Per-UID/Hotkey

            cwtensor_state["Uids"][netuid] = {}
            cwtensor_state["Keys"][netuid] = {}
            cwtensor_state["Owner"][netuid] = {}

            cwtensor_state["LastUpdate"][netuid] = {}
            cwtensor_state["Active"][netuid] = {}
            cwtensor_state["Rank"][netuid] = {}
            cwtensor_state["Emission"][netuid] = {}
            cwtensor_state["Incentive"][netuid] = {}
            cwtensor_state["Consensus"][netuid] = {}
            cwtensor_state["Trust"][netuid] = {}
            cwtensor_state["ValidatorTrust"][netuid] = {}
            cwtensor_state["Dividends"][netuid] = {}
            cwtensor_state["PruningScores"][netuid] = {}
            cwtensor_state["PruningScores"][netuid][0] = {}
            cwtensor_state["ValidatorPermit"][netuid] = {}

            cwtensor_state["Weights"][netuid] = {}
            cwtensor_state["Bonds"][netuid] = {}

            cwtensor_state["Axons"][netuid] = {}
            cwtensor_state["Prometheus"][netuid] = {}

            cwtensor_state["NetworksAdded"][netuid] = {}
            cwtensor_state["NetworksAdded"][netuid][0] = True

        else:
            raise Exception("Subnet already exists")

    def set_difficulty(self, netuid: int, difficulty: int) -> None:
        cwtensor_state = self.chain_state["CwtensorModule"]
        if netuid not in cwtensor_state["NetworksAdded"]:
            raise Exception("Subnet does not exist")

        cwtensor_state["Difficulty"][netuid][self.block_number] = difficulty

    def _register_neuron(self, netuid: int, hotkey: str, coldkey: str) -> int:
        cwtensor_state = self.chain_state["CwtensorModule"]
        if netuid not in cwtensor_state["NetworksAdded"]:
            raise Exception("Subnet does not exist")

        subnetwork_n = self._get_most_recent_storage(
            cwtensor_state["SubnetworkN"][netuid]
        )

        if subnetwork_n > 0 and any(
            self._get_most_recent_storage(cwtensor_state["Keys"][netuid][uid]) == hotkey
            for uid in range(subnetwork_n)
        ):
            # already_registered
            raise Exception("Hotkey already registered")
        else:
            # Not found
            if subnetwork_n >= self._get_most_recent_storage(
                cwtensor_state["MaxAllowedUids"][netuid]
            ):
                # Subnet full, replace neuron randomly
                uid = randint(0, subnetwork_n - 1)
            else:
                # Subnet not full, add new neuron
                # Append as next uid and increment subnetwork_n
                uid = subnetwork_n
                cwtensor_state["SubnetworkN"][netuid][self.block_number] = (
                    subnetwork_n + 1
                )

            cwtensor_state["Stake"][hotkey] = {}
            cwtensor_state["Stake"][hotkey][coldkey] = {}
            cwtensor_state["Stake"][hotkey][coldkey][self.block_number] = 0

            cwtensor_state["Uids"][netuid][hotkey] = {}
            cwtensor_state["Uids"][netuid][hotkey][self.block_number] = uid

            cwtensor_state["Keys"][netuid][uid] = {}
            cwtensor_state["Keys"][netuid][uid][self.block_number] = hotkey

            cwtensor_state["Owner"][hotkey] = {}
            cwtensor_state["Owner"][hotkey][self.block_number] = coldkey

            cwtensor_state["Active"][netuid][uid] = {}
            cwtensor_state["Active"][netuid][uid][self.block_number] = True

            cwtensor_state["LastUpdate"][netuid][uid] = {}
            cwtensor_state["LastUpdate"][netuid][uid][
                self.block_number
            ] = self.block_number

            cwtensor_state["Rank"][netuid][uid] = {}
            cwtensor_state["Rank"][netuid][uid][self.block_number] = 0.0

            cwtensor_state["Emission"][netuid][uid] = {}
            cwtensor_state["Emission"][netuid][uid][self.block_number] = 0.0

            cwtensor_state["Incentive"][netuid][uid] = {}
            cwtensor_state["Incentive"][netuid][uid][self.block_number] = 0.0

            cwtensor_state["Consensus"][netuid][uid] = {}
            cwtensor_state["Consensus"][netuid][uid][self.block_number] = 0.0

            cwtensor_state["Trust"][netuid][uid] = {}
            cwtensor_state["Trust"][netuid][uid][self.block_number] = 0.0

            cwtensor_state["ValidatorTrust"][netuid][uid] = {}
            cwtensor_state["ValidatorTrust"][netuid][uid][self.block_number] = 0.0

            cwtensor_state["Dividends"][netuid][uid] = {}
            cwtensor_state["Dividends"][netuid][uid][self.block_number] = 0.0

            cwtensor_state["PruningScores"][netuid][uid] = {}
            cwtensor_state["PruningScores"][netuid][uid][self.block_number] = 0.0

            cwtensor_state["ValidatorPermit"][netuid][uid] = {}
            cwtensor_state["ValidatorPermit"][netuid][uid][self.block_number] = False

            cwtensor_state["Weights"][netuid][uid] = {}
            cwtensor_state["Weights"][netuid][uid][self.block_number] = []

            cwtensor_state["Bonds"][netuid][uid] = {}
            cwtensor_state["Bonds"][netuid][uid][self.block_number] = []

            cwtensor_state["Axons"][netuid][hotkey] = {}
            cwtensor_state["Axons"][netuid][hotkey][self.block_number] = {}

            cwtensor_state["Prometheus"][netuid][hotkey] = {}
            cwtensor_state["Prometheus"][netuid][hotkey][self.block_number] = {}

            if hotkey not in cwtensor_state["IsNetworkMember"]:
                cwtensor_state["IsNetworkMember"][hotkey] = {}
            cwtensor_state["IsNetworkMember"][hotkey][netuid] = {}
            cwtensor_state["IsNetworkMember"][hotkey][netuid][self.block_number] = True

            return uid

    @staticmethod
    def _convert_to_balance(balance: Union["Balance", float, int]) -> "Balance":
        if isinstance(balance, float):
            balance = Balance.from_gboot(balance)

        if isinstance(balance, int):
            balance = Balance.from_boot(balance)

        return balance

    def force_register_neuron(
        self,
        netuid: int,
        hotkey: str,
        coldkey: str,
        stake: Union["Balance", float, int] = Balance(0),
        balance: Union["Balance", float, int] = Balance(0),
    ) -> int:
        """
        Force register a neuron on the mock chain, returning the UID.
        """
        stake = self._convert_to_balance(stake)
        balance = self._convert_to_balance(balance)

        cwtensor_state = self.chain_state["CwtensorModule"]
        if netuid not in cwtensor_state["NetworksAdded"]:
            raise Exception("Subnet does not exist")

        uid = self._register_neuron(netuid=netuid, hotkey=hotkey, coldkey=coldkey)

        cwtensor_state["TotalStake"][self.block_number] = (
            self._get_most_recent_storage(cwtensor_state["TotalStake"]) + stake.boot
        )
        cwtensor_state["Stake"][hotkey][coldkey][self.block_number] = stake.boot

        if balance.boot > 0:
            self.force_set_balance(coldkey, balance)
        self.force_set_balance(coldkey, balance)

        return uid

    def force_set_balance(
        self, address: str, balance: Union["Balance", float, int] = Balance(0)
    ) -> Tuple[bool, Optional[str]]:
        """
        Returns:
            Tuple[bool, Optional[str]]: (success, err_msg)
        """
        balance = self._convert_to_balance(balance)

        if address not in self.chain_state["System"]["Account"]:
            self.chain_state["System"]["Account"][address] = {
                "data": {"free": {0: 0}}
            }

        old_balance = self.get_balance(address, self.block_number)
        diff = balance.boot - old_balance.boot

        # Update total issuance
        self.chain_state["CwtensorModule"]["TotalIssuance"][self.block_number] = (
            self._get_most_recent_storage(
                self.chain_state["CwtensorModule"]["TotalIssuance"]
            )
            + diff
        )

        self.chain_state["System"]["Account"][address] = {
            "data": {"free": {self.block_number: balance.boot}}
        }

        return True, None

    # Alias for force_set_balance
    sudo_force_set_balance = force_set_balance

    def do_block_step(self) -> None:
        self.block_number += 1

        # Doesn't do epoch
        cwtensor_state = self.chain_state["CwtensorModule"]
        for subnet in cwtensor_state["NetworksAdded"]:
            cwtensor_state["BlocksSinceLastStep"][subnet][self.block_number] = (
                self._get_most_recent_storage(
                    cwtensor_state["BlocksSinceLastStep"][subnet]
                )
                + 1
            )

    def _handle_type_default(self, name: str, params: List[object]) -> object:
        defaults_mapping = {
            "TotalStake": 0,
            "TotalHotkeyStake": 0,
            "TotalColdkeyStake": 0,
            "Stake": 0,
        }

        return defaults_mapping.get(name, None)

    def commit(self, wallet: "Wallet", netuid: int, data: str) -> None:
        uid = self.get_uid_for_hotkey_on_subnet(
            hotkey=wallet.hotkey.address,
            netuid=netuid,
        )
        if uid is None:
            raise Exception("Neuron not found")
        cwtensor_state = self.chain_state["CwtensorModule"]
        cwtensor_state["Commits"][netuid].setdefault(self.block_number, {})[uid] = data

    def get_commitment(self, netuid: int, uid: int, block: Optional[int] = None) -> str:
        if block and self.block_number < block:
            raise Exception("Cannot query block in the future")
        block = block or self.block_number

        cwtensor_state = self.chain_state["CwtensorModule"]
        return cwtensor_state["Commits"][netuid][block][uid]

    def query_cwtensor(
        self,
        name: str,
        block: Optional[int] = None,
        params: Optional[List[object]] = [],
    ) -> MockCwtensorValue:
        if block:
            if self.block_number < block:
                raise Exception("Cannot query block in the future")

        else:
            block = self.block_number

        state = self.chain_state["CwtensorModule"][name]
        if state is not None:
            # Use prefix
            if len(params) > 0:
                while state is not None and len(params) > 0:
                    state = state.get(params.pop(0), None)
                    if state is None:
                        return SimpleNamespace(
                            value=self._handle_type_default(name, params)
                        )

            # Use block
            state_at_block = state.get(block, None)
            while state_at_block is None and block > 0:
                block -= 1
                state_at_block = self.state.get(block, None)
            if state_at_block is not None:
                return SimpleNamespace(value=state_at_block)

            return SimpleNamespace(value=self._handle_type_default(name, params))
        else:
            return SimpleNamespace(value=self._handle_type_default(name, params))

    def query_map_cwtensor(
        self,
        name: str,
        block: Optional[int] = None,
        params: Optional[List[object]] = [],
    ) -> Optional[MockMapResult]:
        """
        Note: Double map requires one param
        """
        if block:
            if self.block_number < block:
                raise Exception("Cannot query block in the future")

        else:
            block = self.block_number

        state = self.chain_state["CwtensorModule"][name]
        if state is not None:
            # Use prefix
            if len(params) > 0:
                while state is not None and len(params) > 0:
                    state = state.get(params.pop(0), None)
                    if state is None:
                        return MockMapResult([])

            # Check if single map or double map
            if len(state.keys()) == 0:
                return MockMapResult([])

            inner = list(state.values())[0]
            # Should have at least one key
            if len(inner.keys()) == 0:
                raise Exception("Invalid state")

            # Check if double map
            if isinstance(list(inner.values())[0], dict):
                # is double map
                raise ChainQueryError("Double map requires one param")

            # Iterate over each key and add value to list, max at block
            records = []
            for key in state:
                result = self._get_most_recent_storage(state[key], block)
                if result is None:
                    continue  # Skip if no result for this key at `block` or earlier

                records.append((key, result))

            return MockMapResult(records)
        else:
            return MockMapResult([])

    def query_constant(
        self, module_name: str, constant_name: str, block: Optional[int] = None
    ) -> Optional[object]:
        if block:
            if self.block_number < block:
                raise Exception("Cannot query block in the future")

        else:
            block = self.block_number

        state = self.chain_state.get(module_name, None)
        if state is not None:
            if constant_name in state:
                state = state[constant_name]
            else:
                return None

            # Use block
            state_at_block = self._get_most_recent_storage(state, block)
            if state_at_block is not None:
                return SimpleNamespace(value=state_at_block)

            return state_at_block["data"]["free"]  # Can be None
        else:
            return None

    def get_current_block(self) -> int:
        return self.block_number

    # ==== Balance RPC methods ====

    def get_balance(self, address: str, block: int = None) -> "Balance":
        if block:
            if self.block_number < block:
                raise Exception("Cannot query block in the future")

        else:
            block = self.block_number

        state = self.chain_state["System"]["Account"]
        if state is not None:
            if address in state:
                state = state[address]
            else:
                return Balance(0)

            # Use block
            balance_state = state["data"]["free"]
            state_at_block = self._get_most_recent_storage(
                balance_state, block
            )  # Can be None
            if state_at_block is not None:
                bal_as_int = state_at_block
                return Balance.from_boot(bal_as_int)
            else:
                return Balance(0)
        else:
            return Balance(0)

    def get_balances(self, block: int = None) -> Dict[str, "Balance"]:
        balances = {}
        for address in self.chain_state["System"]["Account"]:
            balances[address] = self.get_balance(address, block)

        return balances

    # ==== Neuron RPC methods ====

    def neuron_for_uid(
        self, uid: int, netuid: int, block: Optional[int] = None
    ) -> Optional[NeuronInfo]:
        if uid is None:
            return NeuronInfo._null_neuron()

        if block:
            if self.block_number < block:
                raise Exception("Cannot query block in the future")

        else:
            block = self.block_number

        if netuid not in self.chain_state["CwtensorModule"]["NetworksAdded"]:
            return None

        neuron_info = self._neuron_subnet_exists(uid, netuid, block)
        if neuron_info is None:
            return None

        else:
            return neuron_info

    def neurons(self, netuid: int, block: Optional[int] = None) -> List[NeuronInfo]:
        if netuid not in self.chain_state["CwtensorModule"]["NetworksAdded"]:
            raise Exception("Subnet does not exist")

        neurons = []
        subnet_n = self._get_most_recent_storage(
            self.chain_state["CwtensorModule"]["SubnetworkN"][netuid], block
        )
        for uid in range(subnet_n):
            neuron_info = self.neuron_for_uid(uid, netuid, block)
            if neuron_info is not None:
                neurons.append(neuron_info)

        return neurons

    @staticmethod
    def _get_most_recent_storage(
        storage: Dict[BlockNumber, Any], block_number: Optional[int] = None
    ) -> Any:
        if block_number is None:
            items = list(storage.items())
            items.sort(key=lambda x: x[0], reverse=True)
            if len(items) == 0:
                return None

            return items[0][1]

        else:
            while block_number >= 0:
                if block_number in storage:
                    return storage[block_number]

                block_number -= 1

            return None

    def _get_axon_info(
        self, netuid: int, hotkey: str, block: Optional[int] = None
    ) -> AxonInfoDict:
        # Axons [netuid][hotkey][block_number]
        cwtensor_state = self.chain_state["CwtensorModule"]
        if netuid not in cwtensor_state["Axons"]:
            return AxonInfoDict.default()

        if hotkey not in cwtensor_state["Axons"][netuid]:
            return AxonInfoDict.default()

        result = self._get_most_recent_storage(
            cwtensor_state["Axons"][netuid][hotkey], block
        )
        if not result:
            return AxonInfoDict.default()

        return result

    def _get_prometheus_info(
        self, netuid: int, hotkey: str, block: Optional[int] = None
    ) -> PrometheusInfoDict:
        cwtensor_state = self.chain_state["CwtensorModule"]
        if netuid not in cwtensor_state["Prometheus"]:
            return PrometheusInfoDict.default()

        if hotkey not in cwtensor_state["Prometheus"][netuid]:
            return PrometheusInfoDict.default()

        result = self._get_most_recent_storage(
            cwtensor_state["Prometheus"][netuid][hotkey], block
        )
        if not result:
            return PrometheusInfoDict.default()

        return result

    def _neuron_subnet_exists(
        self, uid: int, netuid: int, block: Optional[int] = None
    ) -> Optional[NeuronInfo]:
        cwtensor_state = self.chain_state["CwtensorModule"]
        if netuid not in cwtensor_state["NetworksAdded"]:
            return None

        if self._get_most_recent_storage(cwtensor_state["SubnetworkN"][netuid]) <= uid:
            return None

        hotkey = self._get_most_recent_storage(cwtensor_state["Keys"][netuid][uid])
        if hotkey is None:
            return None

        axon_info_ = self._get_axon_info(netuid, hotkey, block)

        prometheus_info = self._get_prometheus_info(netuid, hotkey, block)

        coldkey = self._get_most_recent_storage(cwtensor_state["Owner"][hotkey], block)
        active = self._get_most_recent_storage(
            cwtensor_state["Active"][netuid][uid], block
        )
        rank = self._get_most_recent_storage(cwtensor_state["Rank"][netuid][uid], block)
        emission = self._get_most_recent_storage(
            cwtensor_state["Emission"][netuid][uid], block
        )
        incentive = self._get_most_recent_storage(
            cwtensor_state["Incentive"][netuid][uid], block
        )
        consensus = self._get_most_recent_storage(
            cwtensor_state["Consensus"][netuid][uid], block
        )
        trust = self._get_most_recent_storage(
            cwtensor_state["Trust"][netuid][uid], block
        )
        validator_trust = self._get_most_recent_storage(
            cwtensor_state["ValidatorTrust"][netuid][uid], block
        )
        dividends = self._get_most_recent_storage(
            cwtensor_state["Dividends"][netuid][uid], block
        )
        pruning_score = self._get_most_recent_storage(
            cwtensor_state["PruningScores"][netuid][uid], block
        )
        last_update = self._get_most_recent_storage(
            cwtensor_state["LastUpdate"][netuid][uid], block
        )
        validator_permit = self._get_most_recent_storage(
            cwtensor_state["ValidatorPermit"][netuid][uid], block
        )

        weights = self._get_most_recent_storage(
            cwtensor_state["Weights"][netuid][uid], block
        )
        bonds = self._get_most_recent_storage(
            cwtensor_state["Bonds"][netuid][uid], block
        )

        stake_dict = {
            coldkey: Balance.from_boot(
                self._get_most_recent_storage(
                    cwtensor_state["Stake"][hotkey][coldkey], block
                )
            )
            for coldkey in cwtensor_state["Stake"][hotkey]
        }

        stake = sum(stake_dict.values())

        weights = [[int(weight[0]), int(weight[1])] for weight in weights]
        bonds = [[int(bond[0]), int(bond[1])] for bond in bonds]
        rank = U16_NORMALIZED_FLOAT(rank)
        emission = emission / GIGA
        incentive = U16_NORMALIZED_FLOAT(incentive)
        consensus = U16_NORMALIZED_FLOAT(consensus)
        trust = U16_NORMALIZED_FLOAT(trust)
        validator_trust = U16_NORMALIZED_FLOAT(validator_trust)
        dividends = U16_NORMALIZED_FLOAT(dividends)
        prometheus_info = PrometheusInfo.fix_decoded_values(prometheus_info)
        axon_info_ = AxonInfo.from_neuron_info(
            {"hotkey": hotkey, "coldkey": coldkey, "axon_info": axon_info_}
        )

        neuron_info = NeuronInfo(
            hotkey=hotkey,
            coldkey=coldkey,
            uid=uid,
            netuid=netuid,
            active=active,
            rank=rank,
            emission=emission,
            incentive=incentive,
            consensus=consensus,
            trust=trust,
            validator_trust=validator_trust,
            dividends=dividends,
            pruning_score=pruning_score,
            last_update=last_update,
            validator_permit=validator_permit,
            stake=stake,
            stake_dict=stake_dict,
            total_stake=stake,
            prometheus_info=prometheus_info,
            axon_info=axon_info_,
            weights=weights,
            bonds=bonds,
            is_null=False,
        )

        return neuron_info

    def neuron_for_uid_lite(
        self, uid: int, netuid: int, block: Optional[int] = None
    ) -> Optional[NeuronInfoLite]:
        if block:
            if self.block_number < block:
                raise Exception("Cannot query block in the future")

        else:
            block = self.block_number

        if netuid not in self.chain_state["CwtensorModule"]["NetworksAdded"]:
            raise Exception("Subnet does not exist")

        neuron_info = self._neuron_subnet_exists(uid, netuid, block)
        if neuron_info is None:
            return None

        else:
            neuron_info_dict = neuron_info.__dict__
            del neuron_info
            del neuron_info_dict["weights"]
            del neuron_info_dict["bonds"]

            neuron_info_lite = NeuronInfoLite(**neuron_info_dict)
            return neuron_info_lite

    def neurons_lite(
        self, netuid: int, block: Optional[int] = None
    ) -> List[NeuronInfoLite]:
        if netuid not in self.chain_state["CwtensorModule"]["NetworksAdded"]:
            raise Exception("Subnet does not exist")

        neurons = []
        subnet_n = self._get_most_recent_storage(
            self.chain_state["CwtensorModule"]["SubnetworkN"][netuid]
        )
        for uid in range(subnet_n):
            neuron_info = self.neuron_for_uid_lite(uid, netuid, block)
            if neuron_info is not None:
                neurons.append(neuron_info)

        return neurons

    # Extrinsics
    def _do_delegation(
        self,
        wallet: "Wallet",
        delegate: str,
        amount: "Balance",
        wait_for_finalization: bool = False,
    ) -> bool:
        # Check if delegate
        if not self.is_hotkey_delegate(hotkey=delegate):
            raise Exception("Not a delegate")

        # do stake
        success = self._do_stake(
            wallet=wallet,
            hotkey=delegate,
            amount=amount,
            wait_for_finalization=wait_for_finalization,
        )

        return success

    def _do_undelegation(
        self,
        wallet: "Wallet",
        delegate: str,
        amount: "Balance",
        wait_for_finalization: bool = False,
    ) -> bool:
        # Check if delegate
        if not self.is_hotkey_delegate(hotkey=delegate):
            raise Exception("Not a delegate")

        # do unstake
        self._do_unstake(
            wallet=wallet,
            hotkey=delegate,
            amount=amount,
            wait_for_finalization=wait_for_finalization,
        )

    def _do_nominate(
        self,
        wallet: "Wallet",
        wait_for_finalization: bool = False,
    ) -> bool:
        hotkey = wallet.hotkey.address
        coldkey = wallet.coldkeypub.address

        cwtensor_state = self.chain_state["CwtensorModule"]
        if self.is_hotkey_delegate(hotkey=hotkey):
            return True

        else:
            cwtensor_state["Delegates"][hotkey] = {}
            cwtensor_state["Delegates"][hotkey][
                self.block_number
            ] = 0.18  # Constant for now

            return True

    def get_transfer_fee(
        self, wallet: "Wallet", dest: str, value: Union["Balance", float, int]
    ) -> "Balance":
        return Balance(700)

    def _do_transfer(
        self,
        wallet: "Wallet",
        dest: str,
        transfer_balance: "Balance",
        wait_for_finalization: bool = False,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        bal = self.get_balance(wallet.coldkeypub.address)
        dest_bal = self.get_balance(dest)
        transfer_fee = self.get_transfer_fee(wallet, dest, transfer_balance)

        existential_deposit = self.get_existential_deposit()

        if bal < transfer_balance + existential_deposit + transfer_fee:
            raise Exception("Insufficient balance")

        # Remove from the free balance
        self.chain_state["System"]["Account"][wallet.coldkeypub.address]["data"][
            "free"
        ][self.block_number] = (bal - transfer_balance - transfer_fee).boot

        # Add to the free balance
        if dest not in self.chain_state["System"]["Account"]:
            self.chain_state["System"]["Account"][dest] = {"data": {"free": {}}}

        self.chain_state["System"]["Account"][dest]["data"]["free"][
            self.block_number
        ] = (dest_bal + transfer_balance).boot

        return True, None, None

    def _do_pow_register(
        self,
        netuid: int,
        wallet: "Wallet",
        pow_result: "POWSolution",
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        # Assume pow result is valid

        cwtensor_state = self.chain_state["CwtensorModule"]
        if netuid not in cwtensor_state["NetworksAdded"]:
            raise Exception("Subnet does not exist")

        self._register_neuron(
            netuid=netuid,
            hotkey=wallet.hotkey.address,
            coldkey=wallet.coldkeypub.address,
        )

        return True, None

    def _do_burned_register(
        self,
        netuid: int,
        wallet: "Wallet",
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        cwtensor_state = self.chain_state["CwtensorModule"]
        if netuid not in cwtensor_state["NetworksAdded"]:
            raise Exception("Subnet does not exist")

        bal = self.get_balance(wallet.coldkeypub.address)
        burn = self.recycle(netuid=netuid)
        existential_deposit = self.get_existential_deposit()

        if bal < burn + existential_deposit:
            raise Exception("Insufficient funds")

        self._register_neuron(
            netuid=netuid,
            hotkey=wallet.hotkey.address,
            coldkey=wallet.coldkeypub.address,
        )

        # Burn the funds
        self.chain_state["System"]["Account"][wallet.coldkeypub.address]["data"][
            "free"
        ][self.block_number] = (bal - burn).boot

        return True, None

    def _do_stake(
        self,
        wallet: "Wallet",
        hotkey: str,
        amount: "Balance",
        wait_for_finalization: bool = False,
    ) -> bool:
        cwtensor_state = self.chain_state["CwtensorModule"]

        bal = self.get_balance(wallet.coldkeypub.address)
        curr_stake = self.get_stake_for_coldkey_and_hotkey(
            hotkey=hotkey, coldkey=wallet.coldkeypub.address
        )
        if curr_stake is None:
            curr_stake = Balance(0)
        existential_deposit = self.get_existential_deposit()

        if bal < amount + existential_deposit:
            raise Exception("Insufficient funds")

        stake_state = cwtensor_state["Stake"]

        # Stake the funds
        if not hotkey in stake_state:
            stake_state[hotkey] = {}
        if not wallet.coldkeypub.address in stake_state[hotkey]:
            stake_state[hotkey][wallet.coldkeypub.address] = {}

        stake_state[hotkey][wallet.coldkeypub.address][
            self.block_number
        ] = amount.boot

        # Add to total_stake storage
        cwtensor_state["TotalStake"][self.block_number] = (
            self._get_most_recent_storage(cwtensor_state["TotalStake"]) + amount.boot
        )

        total_hotkey_stake_state = cwtensor_state["TotalHotkeyStake"]
        if not hotkey in total_hotkey_stake_state:
            total_hotkey_stake_state[hotkey] = {}

        total_coldkey_stake_state = cwtensor_state["TotalColdkeyStake"]
        if not wallet.coldkeypub.address in total_coldkey_stake_state:
            total_coldkey_stake_state[wallet.coldkeypub.address] = {}

        curr_total_hotkey_stake = self.query_cwtensor(
            name="TotalHotkeyStake",
            params=[hotkey],
            block=min(self.block_number - 1, 0),
        )
        curr_total_coldkey_stake = self.query_cwtensor(
            name="TotalColdkeyStake",
            params=[wallet.coldkeypub.address],
            block=min(self.block_number - 1, 0),
        )

        total_hotkey_stake_state[hotkey][self.block_number] = (
            curr_total_hotkey_stake.value + amount.boot
        )
        total_coldkey_stake_state[wallet.coldkeypub.address][self.block_number] = (
            curr_total_coldkey_stake.value + amount.boot
        )

        # Remove from free balance
        self.chain_state["System"]["Account"][wallet.coldkeypub.address]["data"][
            "free"
        ][self.block_number] = (bal - amount).boot

        return True

    def _do_unstake(
        self,
        wallet: "Wallet",
        hotkey: str,
        amount: "Balance",
        wait_for_finalization: bool = False,
    ) -> bool:
        cwtensor_state = self.chain_state["CwtensorModule"]

        bal = self.get_balance(wallet.coldkeypub.address)
        curr_stake = self.get_stake_for_coldkey_and_hotkey(
            hotkey=hotkey, coldkey=wallet.coldkeypub.address
        )
        if curr_stake is None:
            curr_stake = Balance(0)

        if curr_stake < amount:
            raise Exception("Insufficient funds")

        stake_state = cwtensor_state["Stake"]

        if curr_stake.boot == 0:
            return True

        # Unstake the funds
        # We know that the hotkey has stake, so we can just remove it
        stake_state[hotkey][wallet.coldkeypub.address][self.block_number] = (
            curr_stake - amount
        ).boot
        # Add to the free balance
        if wallet.coldkeypub.address not in self.chain_state["System"]["Account"]:
            self.chain_state["System"]["Account"][wallet.coldkeypub.address] = {
                "data": {"free": {}}
            }

        # Remove from total stake storage
        cwtensor_state["TotalStake"][self.block_number] = (
            self._get_most_recent_storage(cwtensor_state["TotalStake"]) - amount.boot
        )

        total_hotkey_stake_state = cwtensor_state["TotalHotkeyStake"]
        if not hotkey in total_hotkey_stake_state:
            total_hotkey_stake_state[hotkey] = {}
            total_hotkey_stake_state[hotkey][
                self.block_number
            ] = 0  # Shouldn't happen

        total_coldkey_stake_state = cwtensor_state["TotalColdkeyStake"]
        if not wallet.coldkeypub.address in total_coldkey_stake_state:
            total_coldkey_stake_state[wallet.coldkeypub.address] = {}
            total_coldkey_stake_state[wallet.coldkeypub.address][
                self.block_number
            ] = amount.boot  # Shouldn't happen

        total_hotkey_stake_state[hotkey][self.block_number] = (
            self._get_most_recent_storage(
                cwtensor_state["TotalHotkeyStake"][hotkey]
            )
            - amount.boot
        )
        total_coldkey_stake_state[wallet.coldkeypub.address][self.block_number] = (
            self._get_most_recent_storage(
                cwtensor_state["TotalColdkeyStake"][wallet.coldkeypub.address]
            )
            - amount.boot
        )

        self.chain_state["System"]["Account"][wallet.coldkeypub.address]["data"][
            "free"
        ][self.block_number] = (bal + amount).boot

        return True

    def get_delegate_by_hotkey(
        self, hotkey: str, block: Optional[int] = None
    ) -> Optional["DelegateInfo"]:
        cwtensor_state = self.chain_state["CwtensorModule"]

        if hotkey not in cwtensor_state["Delegates"]:
            return None

        newest_state = self._get_most_recent_storage(
            cwtensor_state["Delegates"][hotkey], block
        )
        if newest_state is None:
            return None

        nom_result = []
        nominators = cwtensor_state["Stake"][hotkey]
        for nominator in nominators:
            nom_amount = self.get_stake_for_coldkey_and_hotkey(
                hotkey=hotkey, coldkey=nominator, block=block
            )
            if nom_amount is not None and nom_amount.boot > 0:
                nom_result.append((nominator, nom_amount))

        registered_subnets = []
        for subnet in self.get_all_subnet_netuids(block=block):
            uid = self.get_uid_for_hotkey_on_subnet(
                hotkey=hotkey, netuid=subnet, block=block
            )

            if uid is not None:
                registered_subnets.append((subnet, uid))

        info = DelegateInfo(
            hotkey=hotkey,
            total_stake=self.get_total_stake_for_hotkey(address=hotkey)
            or Balance(0),
            nominators=nom_result,
            owner=self.get_hotkey_owner(hotkey=hotkey, block=block),
            take=0.18,
            validator_permits=[
                subnet
                for subnet, uid in registered_subnets
                if self.neuron_has_validator_permit(uid=uid, netuid=subnet, block=block)
            ],
            registrations=[subnet for subnet, _ in registered_subnets],
            return_per_1000=Balance.from_gboot(1234567),  # Doesn't matter for mock?
            total_daily_return=Balance.from_gboot(1234567),  # Doesn't matter for mock?
        )

        return info

    def get_delegates(self, block: Optional[int] = None) -> List["DelegateInfo"]:
        cwtensor_state = self.chain_state["CwtensorModule"]
        delegates_info = []
        for hotkey in cwtensor_state["Delegates"]:
            info = self.get_delegate_by_hotkey(hotkey=hotkey, block=block)
            if info is not None:
                delegates_info.append(info)

        return delegates_info

    def get_delegated(
        self, coldkey: str, block: Optional[int] = None
    ) -> List[Tuple["DelegateInfo", "Balance"]]:
        """Returns the list of delegates that a given coldkey is staked to."""
        delegates = self.get_delegates(block=block)

        result = []
        for delegate in delegates:
            if coldkey in delegate.nominators:
                result.append((delegate, delegate.nominators[coldkey]))

        return result

    def get_all_subnets_info(self, block: Optional[int] = None) -> List[SubnetInfo]:
        cwtensor_state = self.chain_state["CwtensorModule"]
        result = []
        for subnet in cwtensor_state["NetworksAdded"]:
            info = self.get_subnet_info(netuid=subnet, block=block)
            if info is not None:
                result.append(info)

        return result

    def get_subnet_info(
        self, netuid: int, block: Optional[int] = None
    ) -> Optional[SubnetInfo]:
        if not self.subnet_exists(netuid=netuid, block=block):
            return None

        def query_subnet_info(name: str) -> Optional[object]:
            return self.query_cwtensor(name=name, block=block, params=[netuid]).value

        info = SubnetInfo(
            netuid=netuid,
            rho=query_subnet_info(name="Rho"),
            kappa=query_subnet_info(name="Kappa"),
            difficulty=query_subnet_info(name="Difficulty"),
            immunity_period=query_subnet_info(name="ImmunityPeriod"),
            max_allowed_validators=query_subnet_info(name="MaxAllowedValidators"),
            min_allowed_weights=query_subnet_info(name="MinAllowedWeights"),
            max_weight_limit=query_subnet_info(name="MaxWeightLimit"),
            subnetwork_n=query_subnet_info(name="SubnetworkN"),
            max_n=query_subnet_info(name="MaxAllowedUids"),
            blocks_since_epoch=query_subnet_info(name="BlocksSinceLastStep"),
            tempo=query_subnet_info(name="Tempo"),
            modality=query_subnet_info(name="NetworkModality"),
            emission_value=query_subnet_info(name="EmissionValues"),
            burn=query_subnet_info(name="Burn"),
            owner=query_subnet_info(name="SubnetOwner"),
        )

        return info

    def _do_serve_prometheus(
        self,
        wallet: "Wallet",
        call_params: "PrometheusServeCallParams",
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        return True, None

    def _do_set_weights(
        self,
        wallet: "Wallet",
        uids: List[int],
        vals: List[int],
        netuid: int,
        version_key: int = __version_as_int__,
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        return True, None

    def _do_serve_axon(
        self,
        wallet: "Wallet",
        call_params: "AxonServeCallParams",
        wait_for_finalization: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        return True, None
