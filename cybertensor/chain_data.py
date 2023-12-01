# The MIT License (MIT)
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
import torch
# from cybertensor import SubnetHyperparameters

import cybertensor

import json
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Tuple, Dict, Optional, Any, TypedDict, Union

from .utils import networking as net, U16_MAX, U16_NORMALIZED_FLOAT
from .utils.balance import Balance

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
    scaling_law_power: float
    subnetwork_n: int
    max_n: int
    blocks_since_epoch: int
    tempo: int
    modality: int
    # netuid -> topk percentile prunning score requirement (u16:MAX normalized.)
    connection_requirements: Dict[str, float]
    emission_value: float
    burn: Balance
    owner: str

    @classmethod
    def from_list_any(cls, list_any: List[Any]) -> Optional["SubnetInfo"]:
        if len(list_any) == 0:
            return None

        return SubnetInfo.fix_decoded_values(list_any)

    @classmethod
    def list_from_list_any(cls, vec_any: List[Any]) -> List["SubnetInfo"]:
        # TODO check if this is correct if empty
        decoded = [SubnetInfo.fix_decoded_values(d) for d in vec_any]

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
            scaling_law_power=decoded["scaling_law_power"],
            subnetwork_n=decoded["subnetwork_n"],
            max_n=decoded["max_allowed_uids"],
            blocks_since_epoch=decoded["blocks_since_last_step"],
            tempo=decoded["tempo"],
            modality=decoded["network_modality"],
            connection_requirements={
                str(int(netuid)): U16_NORMALIZED_FLOAT(int(req))
                for netuid, req in decoded["network_connect"]
            },
            emission_value=decoded["emission_values"],
            burn=Balance.from_boot(decoded["burn"]),
            owner=decoded["owner"],
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

