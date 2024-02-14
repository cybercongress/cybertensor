import warnings
from argparse import ArgumentParser
from random import sample, randint
from time import sleep
from typing import Union, TypedDict, Optional

warnings.filterwarnings("ignore", category=DeprecationWarning)

import pandas as pd
from cosmpy.aerial.tx_helpers import SubmittedTx
from cosmpy.aerial.wallet import LocalWallet
from cosmpy.crypto.address import Address
from torch.multiprocessing import Pool
from tqdm import tqdm

from cybertensor import __local_network__ as network
from cybertensor import cwtensor, Wallet


class Account(TypedDict):
    wallet: Wallet
    wallet_address: str
    wallet_hotkey_address: str
    start_amount: int


BASE_WALLET_SEED = "notice oak worry limit wrap speak medal online prefer cluster roof addict wrist behave treat actual wasp year salad speed social layer crew genius"

parser = ArgumentParser()
parser.add_argument("--addresses", default=10)
parser.add_argument("--send-to-contract", default="false")
parser.add_argument("--activate-contract", default="false")
parser.add_argument("--send-to-wallets", default="true")
parser.add_argument("--threads", default=5)
args = parser.parse_args()

ADDRESSES_NUMBER = int(args.addresses)
SEND_TOKEN_TO_CONTRACT = args.send_to_contract.lower() in ["true", "1", "t", "y", "yes"]
ACTIVATE_CONTRACT = args.activate_contract.lower() in ["true", "1", "t", "y", "yes"]
SEND_TOKEN_TO_WALLETS = args.send_to_wallets.lower() in ["true", "1", "t", "y", "yes"]
NUMBER_OF_THREADS = int(args.threads)


def send_coins(
    to_address: Union[str, Address], amount: int, denom: str = "boot"
) -> Optional[SubmittedTx]:
    try:
        _tx_broadcasted = tensor.client.send_tokens(
            destination=Address(to_address),
            amount=amount,
            denom=denom,
            sender=base_wallet,
        ).wait_to_complete()
        return _tx_broadcasted
    except Exception as _e:
        print(f"Exception: {_e}")
        return None


def send_token_to_contract() -> None:
    if SEND_TOKEN_TO_CONTRACT:
        send_coins(to_address=tensor.contract_address, amount=10_000_000_000)
        sleep(5)


def activate_contract() -> None:
    if ACTIVATE_CONTRACT:
        _tx = tensor.contract.execute(
            args={"activate": {}}, sender=base_wallet
        ).wait_to_complete()
        print(_tx)


def get_accounts(addresses_number: int = ADDRESSES_NUMBER) -> list[Account]:
    _accounts: list[Account] = []
    for _i in range(1, addresses_number + 1):
        _wallet_name = f"wallet{_i}"
        _wallet = Wallet(name=_wallet_name, hotkey=_wallet_name, path="temp")
        _wallet.create_if_non_existent(
            coldkey_use_password=False, hotkey_use_password=False
        )
        _wallet_address = _wallet.get_coldkey().address
        _wallet_hotkey_address = _wallet.get_hotkey().address
        print(f"{_wallet_name} address uploaded: {_wallet_address}")
        _amount = 20_000_000_000
        if SEND_TOKEN_TO_WALLETS:
            send_coins(to_address=_wallet_address, amount=_amount)
            send_coins(to_address=_wallet_hotkey_address, amount=1_000_000)
        _accounts.append(
            Account(
                wallet=_wallet,
                wallet_address=_wallet_address,
                wallet_hotkey_address=_wallet_hotkey_address,
                start_amount=_amount,
            )
        )
    return _accounts


def workflow(
    account: Account,
    netuids: Optional[list[int]] = None,
    register_subnetwork: bool = True,
    root_register: bool = True,
    subnet_register: bool = True,
    subnet_nominate: bool = True,
    self_stake: bool = True,
    self_stake_amount: float = 1,
    self_unstake: bool = True,
    self_unstake_amount: float = 0.1,
    root_set_weight: bool = True,
    root_weights: Optional[list[float]] = None,
    subnets_set_weight: bool = True,
    subnets_weights: Optional[dict[int, list[list[int], list[float]]]] = None,
) -> None:
    sleep(randint(0, 40))
    try:
        _tensor = cwtensor(network="local")
        if register_subnetwork:
            _tensor.register_subnetwork(wallet=account["wallet"])
        if root_register:
            _tensor.root_register(wallet=account["wallet"])
        if netuids is None:
            netuids = _tensor.get_all_subnet_netuids()
        _subnetuids = [_netuid for _netuid in netuids if _netuid != 0]
        if subnet_register:
            for _netuid in netuids:
                _tensor.burned_register(wallet=account["wallet"], netuid=_netuid)
        if subnet_nominate:
            _tensor.nominate(wallet=account["wallet"])
        # you can stake only to root validators
        if self_stake:
            _tensor.add_stake(
                wallet=account["wallet"],
                hotkey=account["wallet_hotkey_address"],
                amount=self_stake_amount,
            )
        if self_unstake:
            _tensor.unstake(
                wallet=account["wallet"],
                hotkey=account["wallet_hotkey_address"],
                amount=self_unstake_amount,
            )
        if root_set_weight:
            if root_weights is None:
                root_weights = sample(range(1, 1 + len(_subnetuids)), len(_subnetuids))
                print(
                    f"netuids: {_subnetuids}\t"
                    f"root_weights: {root_weights}"
                )
            _tensor.root_set_weights(
                wallet=account["wallet"],
                netuids=_subnetuids,
                weights=root_weights,
                wait_for_finalization=True,
            )
        if subnets_set_weight:
            if subnets_weights is None:
                subnets_weights = {
                    _netuid: [
                        [
                            _neuron.uid
                            for _neuron in _tensor.metagraph(netuid=_netuid).neurons
                        ],
                        sample(
                            range(
                                1, 1 + len(_tensor.metagraph(netuid=_netuid).neurons)
                            ),
                            len(_tensor.metagraph(netuid=_netuid).neurons),
                        ),
                    ]
                    for _netuid in _subnetuids
                }
            for _netuid in subnets_weights.keys():
                sleep(10)
                _tensor.set_weights(
                    wallet=account["wallet"],
                    netuid=_netuid,
                    uids=subnets_weights[_netuid][0],
                    weights=subnets_weights[_netuid][1],
                )
    except Exception as _e:
        print(f"ERROR {_e}")


def display_state() -> None:
    _tensor = cwtensor(network="local")
    _netuids = _tensor.get_all_subnet_netuids()
    print(f"\ncontract address: {_tensor.contract_address}")
    print(f"contract balance: {_tensor.get_balance(_tensor.contract_address)}")
    print(f"existing subnets: {_netuids}\n")
    print(f"delegates: {_tensor.get_delegates()}\n")
    print(f"root weights {_tensor.weights(netuid=0)}\n")
    for _netuid in _netuids[1:]:
        print(f"subnet {_netuid} weights {_tensor.weights(netuid=_netuid)}")

    _registration_data = [
        [f'{"subnet" + str(_netuid) if _netuid != 0 else "root"}']
        + [
            tensor.is_hotkey_registered_on_subnet(
                hotkey=_account["wallet_hotkey_address"], netuid=_netuid
            )
            for _account in accounts
        ]
        for _netuid in _netuids
    ]
    _registration_columns = ["Subnet"] + [
        _account["wallet"].name for _account in accounts
    ]
    print("\nwallet registration:")
    print(pd.DataFrame(data=_registration_data, columns=_registration_columns))


if __name__ == "__main__":
    tensor = cwtensor(network="local")
    base_wallet = LocalWallet.from_mnemonic(
        mnemonic=BASE_WALLET_SEED, prefix=network.address_prefix
    )
    base_wallet_address = str(base_wallet)
    print(
        f"base address: {base_wallet_address}\n"
        f"base address balance: {tensor.get_balance(address=base_wallet_address)}\n"
        f"number of wallets: {ADDRESSES_NUMBER}\n"
        f"send token to the contract: {SEND_TOKEN_TO_CONTRACT}\n"
        f"activate contract: {ACTIVATE_CONTRACT}\n"
        f"send token to wallets: {SEND_TOKEN_TO_WALLETS}\n"
    )

    send_token_to_contract()
    activate_contract()
    accounts = get_accounts()
    display_state()

    tasks = accounts
    print(f"\nnumber of tasks: {len(tasks):>,}")
    print(f"number of threads: {NUMBER_OF_THREADS:>,}")

    with Pool(processes=NUMBER_OF_THREADS) as pool:
        res_participation = list(tqdm(pool.imap(workflow, tasks), total=len(tasks)))

    display_state()
