# The MIT License (MIT)
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
import torch
import json
from dataclasses import dataclass, asdict
from typing import List, Tuple, Dict, Optional, Any

import cybertensor
# from cybertensor import SubnetHyperparameters
from cybertensor.utils import networking as net, U16_MAX, U16_NORMALIZED_FLOAT, GIGA
from cybertensor.utils.balance import Balance


# Dataclasses for chain data.
@dataclass
class NeuronInfo:
    r"""
    Dataclass for neuron metadata.
    """
    hotkey: str
    coldkey: str
    uid: int
    netuid: int
    active: int
    stake: Balance
    # mapping of coldkey to amount staked to this Neuron
    stake_dict: Dict[str, Balance]
    total_stake: Balance
    rank: float
    emission: float
    incentive: float
    consensus: float
    trust: float
    validator_trust: float
    dividends: float
    last_update: int
    validator_permit: bool
    weights: List[List[int]]
    bonds: List[List[int]]
    prometheus_info: "PrometheusInfo"
    axon_info: "AxonInfo"
    pruning_score: int
    is_null: bool = False

    @classmethod
    def fix_decoded_values(cls, neuron_info_decoded: Any) -> "NeuronInfo":
        r"""Fixes the values of the NeuronInfo object."""
        neuron_info_decoded["hotkey"] = neuron_info_decoded["hotkey"]
        neuron_info_decoded["coldkey"] = neuron_info_decoded["coldkey"]
        stake_dict = {
            coldkey: Balance.from_boot(int(stake))
            for coldkey, stake in neuron_info_decoded["stake"]
        }
        neuron_info_decoded["stake_dict"] = stake_dict
        neuron_info_decoded["stake"] = sum(stake_dict.values())
        neuron_info_decoded["total_stake"] = neuron_info_decoded["stake"]
        neuron_info_decoded["weights"] = [
            [int(weight[0]), int(weight[1])]
            for weight in neuron_info_decoded["weights"]
        ]
        neuron_info_decoded["bonds"] = [
            [int(bond[0]), int(bond[1])] for bond in neuron_info_decoded["bonds"]
        ]
        neuron_info_decoded["rank"] = U16_NORMALIZED_FLOAT(neuron_info_decoded["rank"])
        neuron_info_decoded["emission"] = neuron_info_decoded["emission"] / GIGA
        neuron_info_decoded["incentive"] = U16_NORMALIZED_FLOAT(
            neuron_info_decoded["incentive"]
        )
        neuron_info_decoded["consensus"] = U16_NORMALIZED_FLOAT(
            neuron_info_decoded["consensus"]
        )
        neuron_info_decoded["trust"] = U16_NORMALIZED_FLOAT(
            neuron_info_decoded["trust"]
        )
        neuron_info_decoded["validator_trust"] = U16_NORMALIZED_FLOAT(
            neuron_info_decoded["validator_trust"]
        )
        neuron_info_decoded["dividends"] = U16_NORMALIZED_FLOAT(
            neuron_info_decoded["dividends"]
        )
        neuron_info_decoded["prometheus_info"] = PrometheusInfo.fix_decoded_values(
            neuron_info_decoded["prometheus_info"]
        )
        neuron_info_decoded["axon_info"] = AxonInfo.from_neuron_info(
            neuron_info_decoded
        )

        return cls(**neuron_info_decoded)

    @classmethod
    def from_list_any(cls, list_any: List[Any]) -> "NeuronInfo":
        r"""Returns a NeuronInfo object from a ``vec_u8``."""
        if len(list_any) == 0:
            return NeuronInfo._null_neuron()

        decoded = NeuronInfo.fix_decoded_values(list_any)

        return decoded

    @classmethod
    def list_from_list_any(cls, vec_any: List[Any]) -> List["NeuronInfo"]:
        r"""Returns a list of NeuronInfo objects from a ``vec_u8``."""

        decoded_list = [
            NeuronInfo.fix_decoded_values(decoded) for decoded in vec_any
        ]
        return decoded_list

    @staticmethod
    def _null_neuron() -> "NeuronInfo":
        neuron = NeuronInfo(
            uid=0,
            netuid=0,
            active=0,
            stake=Balance.from_boot(0),
            stake_dict={},
            total_stake=Balance.from_boot(0),
            rank=0,
            emission=0,
            incentive=0,
            consensus=0,
            trust=0,
            validator_trust=0,
            dividends=0,
            last_update=0,
            validator_permit=False,
            weights=[],
            bonds=[],
            prometheus_info=None,
            axon_info=None,
            is_null=True,
            coldkey="000000000000000000000000000000000000000000000000",
            hotkey="000000000000000000000000000000000000000000000000",
            pruning_score=0,
        )
        return neuron

    @classmethod
    def from_weights_bonds_and_neuron_lite(
        cls,
        neuron_lite: "NeuronInfoLite",
        weights_as_dict: Dict[int, List[Tuple[int, int]]],
        bonds_as_dict: Dict[int, List[Tuple[int, int]]],
    ) -> "NeuronInfo":
        n_dict = neuron_lite.__dict__
        n_dict["weights"] = weights_as_dict.get(neuron_lite.uid, [])
        n_dict["bonds"] = bonds_as_dict.get(neuron_lite.uid, [])

        return cls(**n_dict)

    @staticmethod
    def _neuron_dict_to_namespace(neuron_dict) -> "NeuronInfo":
        neuron = NeuronInfo(**neuron_dict)
        neuron.stake_dict = {
            hk: Balance.from_boot(stake) for hk, stake in neuron.stake.items()
        }
        neuron.stake = Balance.from_boot(neuron.total_stake)
        neuron.total_stake = neuron.stake
        neuron.rank = neuron.rank / U16_MAX
        neuron.trust = neuron.trust / U16_MAX
        neuron.consensus = neuron.consensus / U16_MAX
        neuron.validator_trust = neuron.validator_trust / U16_MAX
        neuron.incentive = neuron.incentive / U16_MAX
        neuron.dividends = neuron.dividends / U16_MAX
        neuron.emission = neuron.emission / GIGA

        return neuron


@dataclass
class NeuronInfoLite:
    r"""
    Dataclass for neuron metadata, but without the weights and bonds.
    """
    hotkey: str
    coldkey: str
    uid: int
    netuid: int
    active: int
    stake: Balance
    # mapping of coldkey to amount staked to this Neuron
    stake_dict: Dict[str, Balance]
    total_stake: Balance
    rank: float
    emission: float
    incentive: float
    consensus: float
    trust: float
    validator_trust: float
    dividends: float
    last_update: int
    validator_permit: bool
    # weights: List[List[int]]
    # bonds: List[List[int]] No weights or bonds in lite version
    pruning_score: int
    prometheus_info: Optional["PrometheusInfo"] = None
    axon_info: Optional["AxonInfo"] = None
    is_null: bool = False

    @classmethod
    def fix_decoded_values(cls, neuron_info_decoded: Any) -> "NeuronInfoLite":
        r"""Fixes the values of the NeuronInfoLite object."""
        neuron_info_decoded["hotkey"] = neuron_info_decoded["hotkey"]
        neuron_info_decoded["coldkey"] = neuron_info_decoded["coldkey"]
        stake_dict = {
            coldkey: Balance.from_boot(int(stake))
            for coldkey, stake in neuron_info_decoded["stake"]
        }
        neuron_info_decoded["stake_dict"] = stake_dict
        neuron_info_decoded["stake"] = sum(stake_dict.values())
        neuron_info_decoded["total_stake"] = neuron_info_decoded["stake"]
        # Don't need weights and bonds in lite version
        # neuron_info_decoded['weights'] = [[int(weight[0]), int(weight[1])] for weight in neuron_info_decoded['weights']]
        # neuron_info_decoded['bonds'] = [[int(bond[0]), int(bond[1])] for bond in neuron_info_decoded['bonds']]
        neuron_info_decoded["rank"] = U16_NORMALIZED_FLOAT(neuron_info_decoded["rank"])
        neuron_info_decoded["emission"] = neuron_info_decoded["emission"] / GIGA
        neuron_info_decoded["incentive"] = U16_NORMALIZED_FLOAT(
            neuron_info_decoded["incentive"]
        )
        neuron_info_decoded["consensus"] = U16_NORMALIZED_FLOAT(
            neuron_info_decoded["consensus"]
        )
        neuron_info_decoded["trust"] = U16_NORMALIZED_FLOAT(
            neuron_info_decoded["trust"]
        )
        neuron_info_decoded["validator_trust"] = U16_NORMALIZED_FLOAT(
            neuron_info_decoded["validator_trust"]
        )
        neuron_info_decoded["dividends"] = U16_NORMALIZED_FLOAT(
            neuron_info_decoded["dividends"]
        )
        neuron_info_decoded["prometheus_info"] = PrometheusInfo.fix_decoded_values(
            neuron_info_decoded["prometheus_info"]
        )
        neuron_info_decoded["axon_info"] = AxonInfo.from_neuron_info(
            neuron_info_decoded
        )
        return cls(**neuron_info_decoded)

    @classmethod
    def from_list_any(cls, list_any: List[Any]) -> "NeuronInfoLite":
        r"""Returns a NeuronInfoLite object from a ``vec_u8``."""
        if len(list_any) == 0:
            return NeuronInfoLite._null_neuron()

        decoded = NeuronInfoLite.fix_decoded_values(list_any)

        return decoded

    @classmethod
    def list_from_list_any(cls, vec_any: List[Any]) -> List["NeuronInfoLite"]:
        r"""Returns a list of NeuronInfoLite objects from a ``vec_u8``."""

        decoded_list = [
            NeuronInfoLite.fix_decoded_values(decoded) for decoded in vec_any
        ]
        return decoded_list

    @staticmethod
    def _null_neuron() -> "NeuronInfoLite":
        neuron = NeuronInfoLite(
            uid=0,
            netuid=0,
            active=0,
            stake=Balance.from_boot(0),
            stake_dict={},
            total_stake=Balance.from_boot(0),
            rank=0,
            emission=0,
            incentive=0,
            consensus=0,
            trust=0,
            validator_trust=0,
            dividends=0,
            last_update=0,
            validator_permit=False,
            # weights = [], // No weights or bonds in lite version
            # bonds = [],
            prometheus_info=None,
            axon_info=None,
            is_null=True,
            coldkey="000000000000000000000000000000000000000000000000",
            hotkey="000000000000000000000000000000000000000000000000",
            pruning_score=0,
        )
        return neuron

    @staticmethod
    def _neuron_dict_to_namespace(neuron_dict) -> "NeuronInfoLite":
        neuron = NeuronInfoLite(**neuron_dict)
        neuron.stake = Balance.from_boot(neuron.total_stake)
        neuron.stake_dict = {
            hk: Balance.from_boot(stake) for hk, stake in neuron.stake.items()
        }
        neuron.total_stake = neuron.stake
        neuron.rank = neuron.rank / U16_MAX
        neuron.trust = neuron.trust / U16_MAX
        neuron.consensus = neuron.consensus / U16_MAX
        neuron.validator_trust = neuron.validator_trust / U16_MAX
        neuron.incentive = neuron.incentive / U16_MAX
        neuron.dividends = neuron.dividends / U16_MAX
        neuron.emission = neuron.emission / GIGA

        return neuron

@dataclass
class PrometheusInfo:
    r"""
    Dataclass for prometheus info.
    """
    block: int
    version: int
    ip: str
    port: int
    ip_type: int

    @classmethod
    def fix_decoded_values(cls, prometheus_info_decoded: Dict) -> "PrometheusInfo":
        r"""Returns a PrometheusInfo object from a prometheus_info_decoded dictionary."""
        prometheus_info_decoded["ip"] = net.int_to_ip(
            int(prometheus_info_decoded["ip"])
        )

        return cls(**prometheus_info_decoded)

@dataclass
class AxonInfo:
    version: int
    ip: str
    port: int
    ip_type: int
    hotkey: str
    coldkey: str
    protocol: int = 4
    placeholder1: int = 0
    placeholder2: int = 0

    @property
    def is_serving(self) -> bool:
        """True if the endpoint is serving."""
        if self.ip == "0.0.0.0":
            return False
        else:
            return True

    def ip_str(self) -> str:
        """Return the whole IP as string"""
        return net.ip__str__(self.ip_type, self.ip, self.port)

    def __eq__(self, other: "AxonInfo"):
        if other is None:
            return False
        if (
            self.version == other.version
            and self.ip == other.ip
            and self.port == other.port
            and self.ip_type == other.ip_type
            and self.coldkey == other.coldkey
            and self.hotkey == other.hotkey
        ):
            return True
        else:
            return False

    def __str__(self):
        return "AxonInfo( {}, {}, {}, {} )".format(
            str(self.ip_str()), str(self.hotkey), str(self.coldkey), self.version
        )

    def __repr__(self):
        return self.__str__()

    def to_string(self) -> str:
        """Converts the AxonInfo object to a string representation using JSON."""
        try:
            return json.dumps(asdict(self))
        except (TypeError, ValueError) as e:
            cybertensor.logging.error(f"Error converting AxonInfo to string: {e}")
            return AxonInfo(0, "", 0, 0, "", "").to_string()

    @classmethod
    def from_string(cls, s: str) -> "AxonInfo":
        """Creates an AxonInfo object from its string representation using JSON."""
        try:
            data = json.loads(s)
            return cls(**data)
        except json.JSONDecodeError as e:
            cybertensor.logging.error(f"Error decoding JSON: {e}")
        except TypeError as e:
            cybertensor.logging.error(f"Type error: {e}")
        except ValueError as e:
            cybertensor.logging.error(f"Value error: {e}")
        return AxonInfo(0, "", 0, 0, "", "")

    @classmethod
    def from_neuron_info(cls, neuron_info: dict) -> "AxonInfo":
        """Converts a dictionary to an axon_info object."""
        return cls(
            version=neuron_info["axon_info"]["version"],
            ip=net.int_to_ip(int(neuron_info["axon_info"]["ip"])),
            port=neuron_info["axon_info"]["port"],
            ip_type=neuron_info["axon_info"]["ip_type"],
            hotkey=neuron_info["hotkey"],
            coldkey=neuron_info["coldkey"],
        )

    def to_parameter_dict(self) -> "torch.nn.ParameterDict":
        r"""Returns a torch tensor of the subnet info."""
        return torch.nn.ParameterDict(self.__dict__)

    @classmethod
    def from_parameter_dict(
        cls, parameter_dict: "torch.nn.ParameterDict"
    ) -> "AxonInfo":
        r"""Returns an axon_info object from a torch parameter_dict."""
        return cls(**dict(parameter_dict))

@dataclass
class DelegateInfo:
    r"""
    Dataclass for delegate info.
    """
    hotkey: str  # Hotkey of delegate
    total_stake: Balance  # Total stake of the delegate
    nominators: List[
        Tuple[str, Balance]
    ]  # List of nominators of the delegate and their stake
    owner: str  # Coldkey of owner
    take: float  # Take of the delegate as a percentage
    validator_permits: List[
        int
    ]  # List of subnets that the delegate is allowed to validate on
    registrations: List[int]  # List of subnets that the delegate is registered on
    return_per_1000: Balance  # Return per 1000 gboot of the delegate over a day
    total_daily_return: Balance  # Total daily return of the delegate

    @classmethod
    def fix_decoded_values(cls, decoded: Any) -> "DelegateInfo":
        r"""Fixes the decoded values."""

        return cls(
            hotkey=decoded["delegate"],
            owner=decoded["owner"],
            take=U16_NORMALIZED_FLOAT(decoded["take"]),
            nominators=[
                (
                    nom[0],
                    Balance.from_boot(nom[1]),
                )
                for nom in decoded["nominators"]
            ],
            total_stake=Balance.from_boot(
                sum([nom[1] for nom in decoded["nominators"]])
            ),
            validator_permits=decoded["validator_permits"],
            registrations=decoded["registrations"],
            return_per_1000=Balance.from_boot(decoded["return_per_1000"]),
            total_daily_return=Balance.from_boot(decoded["total_daily_return"]),
        )

    @classmethod
    def from_list_any(cls, list_any: List[Any]) -> Optional["DelegateInfo"]:
        r"""Returns a DelegateInfo object from a ``vec_u8``."""

        decoded = DelegateInfo.fix_decoded_values(list_any)

        return decoded

    @classmethod
    def list_from_list_any(cls, vec_any: List[Any]) -> List["DelegateInfo"]:
        r"""Returns a list of DelegateInfo objects from a ``vec_u8``."""

        decoded = [DelegateInfo.fix_decoded_values(d) for d in vec_any]

        return decoded

    @classmethod
    def delegated_list_from_list_any(
        cls, vec_any: List[Any]
    ) -> List[Tuple["DelegateInfo", Balance]]:
        r"""Returns a list of Tuples of DelegateInfo objects, and Balance, from a ``vec_u8``.
        This is the list of delegates that the user has delegated to, and the amount of stake delegated.
        """

        decoded = [
            (DelegateInfo.fix_decoded_values(d), Balance.from_boot(s))
            for d, s in vec_any
        ]

        return decoded


@dataclass
class StakeInfo:
    r"""
    Dataclass for stake info.
    """
    hotkey: str  # Hotkey address
    coldkey: str  # Coldkey address
    stake: Balance  # Stake for the hotkey-coldkey pair

    @classmethod
    def fix_decoded_values(cls, decoded: Any) -> "StakeInfo":
        r"""Fixes the decoded values."""

        return cls(
            hotkey=decoded["hotkey"],
            coldkey=decoded["coldkey"],
            stake=Balance.from_boot(decoded["stake"]),
        )

    @classmethod
    def from_list_any(cls, list_any: List[Any]) -> Optional["StakeInfo"]:
        r"""Returns a StakeInfo object from a ``vec_u8``."""
        if len(list_any) == 0:
            return None

        decoded = StakeInfo.fix_decoded_values(list_any)

        return decoded

    @classmethod
    def list_of_tuple_from_list_any(
        cls, vec_any: List[Any]
    ) -> Dict[str, List["StakeInfo"]]:
        r"""Returns a list of StakeInfo objects from a vec_any."""

        stake_map = {
            account_id: [
                StakeInfo.fix_decoded_values(d) for d in stake_info
            ]
            for account_id, stake_info in vec_any
        }

        return stake_map

    @classmethod
    def list_from_list_any(cls, vec_any: List[Any]) -> List["StakeInfo"]:
        r"""Returns a list of StakeInfo objects from a ``vec_u8``."""

        decoded = [StakeInfo.fix_decoded_values(d) for d in vec_any]

        return decoded


@dataclass
class SubnetInfo:
    r"""
    Dataclass for subnet info.
    """

    netuid: int
    rho: int
    kappa: int
    difficulty: int
    immunity_period: int
    max_allowed_validators: int
    min_allowed_weights: int
    max_weight_limit: float
    subnetwork_n: int
    max_n: int
    blocks_since_epoch: int
    tempo: int
    modality: int
    emission_value: float
    burn: Balance
    owner: str
    metadata: str

    @classmethod
    def from_list_any(cls, list_any: List[Any]) -> Optional["SubnetInfo"]:
        if len(list_any) == 0:
            return None

        return SubnetInfo.fix_decoded_values(list_any)

    @classmethod
    def list_from_list_any(cls, vec_any: List[Any]) -> List["SubnetInfo"]:
        # TODO check if this is correct if empty
        decoded = [SubnetInfo.fix_decoded_values(d) for d in vec_any if d is not None]

        return decoded

    @classmethod
    def fix_decoded_values(cls, decoded: Dict) -> "SubnetInfo":
        r"""Returns a SubnetInfo object from a decoded SubnetInfo dictionary."""
        return SubnetInfo(
            netuid=decoded["netuid"],
            rho=decoded["rho"],
            kappa=decoded["kappa"],
            difficulty=decoded["difficulty"],
            immunity_period=decoded["immunity_period"],
            max_allowed_validators=decoded["max_allowed_validators"],
            min_allowed_weights=decoded["min_allowed_weights"],
            max_weight_limit=decoded["max_weights_limit"],
            subnetwork_n=decoded["subnetwork_n"],
            max_n=decoded["max_allowed_uids"],
            blocks_since_epoch=decoded["blocks_since_last_step"],
            tempo=decoded["tempo"],
            modality=decoded["network_modality"],
            emission_value=decoded["emission_values"],
            burn=Balance.from_boot(decoded["burn"]),
            owner=decoded["owner"],
            metadata=decoded["metadata"],
        )

    def to_parameter_dict(self) -> "torch.nn.ParameterDict":
        r"""Returns a torch tensor of the subnet info."""
        return torch.nn.ParameterDict(self.__dict__)

    @classmethod
    def from_parameter_dict(
        cls, parameter_dict: "torch.nn.ParameterDict"
    ) -> "SubnetInfo":
        r"""Returns a SubnetInfo object from a torch parameter_dict."""
        return cls(**dict(parameter_dict))


@dataclass
class SubnetHyperparameters:
    r"""
    Dataclass for subnet hyperparameters.
    """

    rho: int
    kappa: int
    immunity_period: int
    min_allowed_weights: int
    max_weight_limit: float
    tempo: int
    min_difficulty: int
    max_difficulty: int
    weights_version: int
    weights_rate_limit: int
    adjustment_interval: int
    activity_cutoff: int
    registration_allowed: bool
    target_regs_per_interval: int
    min_burn: int
    max_burn: int
    bonds_moving_avg: int
    max_regs_per_block: int
    # serving_rate_limit: int
    # max_validators: int

    @classmethod
    def from_list_any(cls, list_any: List[Any]) -> Optional["SubnetHyperparameters"]:
        if len(list_any) == 0:
            return None

        return SubnetHyperparameters.fix_decoded_values(list_any)

    @classmethod
    def list_from_list_any(cls, vec_any: List[Any]) -> List["SubnetHyperparameters"]:
        # TODO check if this is correct if empty
        decoded = [SubnetHyperparameters.fix_decoded_values(d) for d in vec_any]

        return decoded

    @classmethod
    def fix_decoded_values(cls, decoded: Dict) -> "SubnetHyperparameters":
        r"""Returns a SubnetInfo object from a decoded SubnetInfo dictionary."""
        return SubnetHyperparameters(
            rho=decoded["rho"],
            kappa=decoded["kappa"],
            immunity_period=decoded["immunity_period"],
            min_allowed_weights=decoded["min_allowed_weights"],
            max_weight_limit=decoded["max_weights_limit"],
            tempo=decoded["tempo"],
            min_difficulty=decoded["min_difficulty"],
            max_difficulty=decoded["max_difficulty"],
            weights_version=decoded["weights_version"],
            weights_rate_limit=decoded["weights_rate_limit"],
            adjustment_interval=decoded["adjustment_interval"],
            activity_cutoff=decoded["activity_cutoff"],
            registration_allowed=decoded["registration_allowed"],
            target_regs_per_interval=decoded["target_regs_per_interval"],
            min_burn=decoded["min_burn"],
            max_burn=decoded["max_burn"],
            bonds_moving_avg=decoded["bonds_moving_avg"],
            max_regs_per_block=decoded["max_regs_per_block"],
            # max_validators=decoded["max_validators"],
            # serving_rate_limit=decoded["serving_rate_limit"],
        )

    def to_parameter_dict(self) -> "torch.nn.ParameterDict":
        r"""Returns a torch tensor of the subnet hyperparameters."""
        return torch.nn.ParameterDict(self.__dict__)

    @classmethod
    def from_parameter_dict(
        cls, parameter_dict: "torch.nn.ParameterDict"
    ) -> "SubnetInfo":
        r"""Returns a SubnetHyperparameters object from a torch parameter_dict."""
        return cls(**dict(parameter_dict))


@dataclass
class IPInfo:
    r"""
    Dataclass for associated IP Info.
    """

    ip: str
    ip_type: int
    protocol: int

    def encode(self) -> Dict[str, Any]:
        r"""Returns a dictionary of the IPInfo object that can be encoded."""
        return {
            "ip": net.ip_to_int(
                self.ip
            ),  # IP type and protocol are encoded together as a u8
            "ip_type_and_protocol": ((self.ip_type << 4) + self.protocol) & 0xFF,
        }

    @classmethod
    def from_list_any(cls, list_any: List[Any]) -> Optional["IPInfo"]:
        r"""Returns a IPInfo object from a ``vec_u8``."""
        if len(list_any) == 0:
            return None

        return IPInfo.fix_decoded_values(list_any)

    @classmethod
    def list_from_list_any(cls, vec_any: List[Any]) -> List["IPInfo"]:
        r"""Returns a list of IPInfo objects from a ``vec_u8``."""

        decoded = [IPInfo.fix_decoded_values(d) for d in vec_any]

        return decoded

    @classmethod
    def fix_decoded_values(cls, decoded: Dict) -> "IPInfo":
        r"""Returns a SubnetInfo object from a decoded IPInfo dictionary."""
        return IPInfo(
            ip=cybertensor.utils.networking.int_to_ip(decoded["ip"]),
            ip_type=decoded["ip_type_and_protocol"] >> 4,
            protocol=decoded["ip_type_and_protocol"] & 0xF,
        )

    def to_parameter_dict(self) -> "torch.nn.ParameterDict":
        r"""Returns a torch tensor of the subnet info."""
        return torch.nn.ParameterDict(self.__dict__)

    @classmethod
    def from_parameter_dict(cls, parameter_dict: "torch.nn.ParameterDict") -> "IPInfo":
        r"""Returns a IPInfo object from a torch parameter_dict."""
        return cls(**dict(parameter_dict))