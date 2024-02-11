from argparse import ArgumentParser
from random import sample
from time import sleep
from typing import Union, TypedDict, Optional
from torch.multiprocessing import Pool

from cyber_sdk.client.lcd import LCDClient
from cyber_sdk.client.lcd.api.tx import CreateTxOptions, BlockTxBroadcastResult
from cyber_sdk.core import Coin, Coins, AccAddress
from cyber_sdk.core.bank import MsgSend
from cyber_sdk.core.fee import Fee
from cyber_sdk.exceptions import LCDResponseError
from cyber_sdk.key.mnemonic import MnemonicKey
from cyberutils.bash import execute_bash
from cyberutils.contract import execute_contract
from tqdm import tqdm

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
parser.add_argument("--lcd", default="http://localhost:1317")
args = parser.parse_args()

ADDRESSES_NUMBER = int(args.addresses)
SEND_TOKEN_TO_CONTRACT = args.send_to_contract.lower() in ["true", "1", "t", "y", "yes"]
ACTIVATE_CONTRACT = args.activate_contract.lower() in ["true", "1", "t", "y", "yes"]
SEND_TOKEN_TO_WALLETS = args.send_to_wallets.lower() in ["true", "1", "t", "y", "yes"]
NUMBER_OF_THREADS = int(args.threads)
LCD_URL = args.lcd


def send_coins(
    to_address: Union[str, AccAddress], amount: int, denom: str = "boot"
) -> Optional[BlockTxBroadcastResult]:
    _msgs = [
        MsgSend(
            from_address=base_wallet_address,
            to_address=AccAddress(to_address),
            amount=Coins([Coin(amount=amount, denom=denom)]),
        )
    ]
    _tx_signed = base_wallet.create_and_sign_tx(
        CreateTxOptions(
            msgs=_msgs,
            memo="cybertensor test",
            fee=Fee(1000000, Coins([Coin(amount=0, denom=tensor.token)])),
            gas_adjustment=1.6,
        )
    )

    try:
        _tx_broadcasted = lcd_client.tx.broadcast(_tx_signed)
        return _tx_broadcasted
    except LCDResponseError as _e:
        print(f"LCDResponseError: {_e}")
        return None


def send_token_to_contract() -> None:
    if SEND_TOKEN_TO_CONTRACT:
        send_coins(to_address=tensor.contract_address, amount=10_000_000_000)
        sleep(5)


def activate_contract() -> None:
    if ACTIVATE_CONTRACT:
        tx = execute_contract(
            execute_msgs=[{"activate": {}}],
            wallet=base_wallet,
            contract_address=tensor.contract_address,
            lcd_client=lcd_client,
            fee_denom=tensor.token,
        )
        print(tx)
    print(f"contract balance: {tensor.get_balance(tensor.contract_address)}")


def get_accounts(addresses_number: int = ADDRESSES_NUMBER) -> list[Account]:
    accounts: list[Account] = []
    for i in range(1, addresses_number + 1):
        wallet_name = f"wallet{i}"
        wallet = Wallet(name=wallet_name, hotkey=wallet_name, path="temp")
        wallet.create_if_non_existent(
            coldkey_use_password=False, hotkey_use_password=False
        )
        wallet_address = wallet.get_coldkey().address
        wallet_hotkey_address = wallet.get_hotkey().address
        print(f"address: {wallet_address}")
        amount = 20_000_000_000
        if SEND_TOKEN_TO_WALLETS:
            send_coins(to_address=wallet_address, amount=amount)
            send_coins(to_address=wallet_hotkey_address, amount=1_000_000)
        accounts.append(
            Account(
                wallet=wallet,
                wallet_address=wallet_address,
                wallet_hotkey_address=wallet_hotkey_address,
                start_amount=amount,
            )
        )
    return accounts


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
    try:
        tensor = cwtensor(network="local")
        if register_subnetwork:
            tensor.register_subnetwork(wallet=account["wallet"])
        if root_register:
            tensor.root_register(wallet=account["wallet"])
        if netuids is None:
            netuids = tensor.get_all_subnet_netuids()
        if subnet_register:
            for _netuid in netuids:
                tensor.burned_register(wallet=account["wallet"], netuid=_netuid)
        if subnet_nominate:
            tensor.nominate(wallet=account["wallet"])
        # you can stake only to root validators
        if self_stake:
            tensor.add_stake(
                wallet=account["wallet"],
                hotkey=account["wallet_hotkey_address"],
                amount=self_stake_amount,
            )
        if self_unstake:
            tensor.unstake(
                wallet=account["wallet"],
                hotkey=account["wallet_hotkey_address"],
                amount=self_unstake_amount,
            )
        if root_set_weight:
            if root_weights is None:
                root_weights = sample(range(1, 1 + len(netuids)), len(netuids))
                print(f'netuids: {netuids}'
                      f'len(netuids): {len(netuids)}'
                      f'root_weights: {root_weights}')
            tensor.root_set_weights(
                wallet=account["wallet"], netuids=netuids, weights=root_weights
            )
        if subnets_set_weight:
            sleep(10)
            if subnets_weights is None:
                subnets_weights = {
                    netuid: [
                        [
                            neuron.uid
                            for neuron in tensor.metagraph(netuid=netuid).neurons
                        ],
                        sample(
                            range(1, 1 + len(tensor.metagraph(netuid=netuid).neurons)),
                            len(tensor.metagraph(netuid=netuid).neurons),
                        ),
                    ]
                    for netuid in netuids
                }
            for _netuid in subnets_weights.keys():
                tensor.set_weights(
                    wallet=account["wallet"],
                    netuid=_netuid,
                    uids=subnets_weights[_netuid][0],
                    weights=subnets_weights[_netuid][1],
                )
    except Exception as _e:
        print(f"ERROR {_e}")


def display_state() -> None:
    tensor = cwtensor(network="local")
    netuids = tensor.get_all_subnet_netuids()
    print(f"contract balance: {tensor.get_balance(tensor.contract_address)}")
    print(f"existing subnets: {netuids}\n")
    print(f"delegates: {tensor.get_delegates()}\n")
    print(f"root weights {tensor.weights(netuid=0)}\n")
    for netuid in netuids[1:]:
        print(f"subnet {netuid} weights {tensor.weights(netuid=netuid)}")

    for netuid in netuids:
        print(f'{"subnet" + str(netuid) if netuid != 0 else "root"}:')
        for i, _account in enumerate(accounts):
            print(
                f"\twallet {i + 1} registration: "
                f'{tensor.is_hotkey_registered_on_subnet(hotkey=_account["wallet_hotkey_address"], netuid=netuid)}'
            )


def run_workflow(account_name: str) -> bool:
    print(f"account name: {account_name}")
    _output, _error = execute_bash(
        f"source ./venv/bin/activate && python load_test_job.py --wallet-name={account_name}",
        timeout=400,
        shell=True,
    )

    if _output:
        print(_output)
        print(f"{account_name} done")
        return True
    else:
        # print(f"{account_name} error: {_error}")
        return False


if __name__ == "__main__":
    tensor = cwtensor(network="local")
    mk = MnemonicKey(mnemonic=BASE_WALLET_SEED)
    lcd_client = LCDClient(url=LCD_URL, chain_id=tensor.client.network_config.chain_id)
    base_wallet = lcd_client.wallet(mk)
    base_wallet_address = base_wallet.key.acc_address
    print(
        f"base address: {base_wallet_address}\n"
        f"base address balance: {lcd_client.bank.balance(address=base_wallet_address)[0]}\n"
        f"number of wallets: {ADDRESSES_NUMBER}\n"
        f"send token to the contract: {SEND_TOKEN_TO_CONTRACT}\n"
        f"activate contract: {ACTIVATE_CONTRACT}\n"
        f"send token to wallets: {SEND_TOKEN_TO_WALLETS}\n"
    )

    send_token_to_contract()
    activate_contract()
    accounts = get_accounts()

    tasks = accounts
    print(f"Number of tasks: {len(tasks):>,}")
    print(f"Number of threads: {NUMBER_OF_THREADS:>,}")

    with Pool(processes=NUMBER_OF_THREADS) as pool:
        res_participation = list(tqdm(pool.imap(workflow, tasks), total=len(tasks)))

    display_state()
