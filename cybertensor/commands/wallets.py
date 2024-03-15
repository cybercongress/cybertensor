# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
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
import os
import sys
from typing import Optional, List

import requests
from rich.prompt import Prompt, Confirm
from rich.table import Table

import cybertensor
from cybertensor import __console__ as console
from cybertensor.commands import defaults
from cybertensor.config import Config
from cybertensor.wallet import Wallet


# TODO rewrite to use raw pubkey against hex or rewrite keypair/keyfile to use hex

class RegenColdkeyCommand:
    """
    Executes the 'regen_coldkey' command to regenerate a coldkey for a wallet on the Cybertensor network.
    This command is used to create a new coldkey from an existing mnemonic, seed, or JSON file.

    Usage:
    Users can specify a mnemonic, a seed string, or a JSON file path to regenerate a coldkey.
    The command supports optional password protection for the generated key and can overwrite an existing coldkey.

    Optional arguments:
    - --mnemonic (str): A mnemonic phrase used to regenerate the key.
    - --seed (str): A seed hex string used for key regeneration.
    - --json (str): Path to a JSON file containing an encrypted key backup.
    - --json_password (str): Password to decrypt the JSON file.
    - --use_password (bool): Enables password protection for the generated key.
    - --overwrite_coldkey (bool): Overwrites the existing coldkey with the new one.

    Example usage:
    >>> ctcli wallet regen_coldkey --mnemonic "word1 word2 ... word12"

    Note:
    This command is critical for users who need to regenerate their coldkey, possibly for recovery or security reasons.
    It should be used with caution to avoid overwriting existing keys unintentionally.
    """

    def run(cli: "cybertensor.cli") -> None:
        r"""Creates a new coldkey under this wallet."""
        try:
            cwtensor = cybertensor.cwtensor(config=cli.config, log_verbose=False)
            RegenColdkeyCommand._run(cli, cwtensor)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def _run(cli: "cybertensor.cli", cwtensor: "cybertensor.cwtensor"):
        wallet = Wallet(config=cli.config)

        json_str: Optional[str] = None
        json_password: Optional[str] = None
        if cli.config.get("json"):
            file_name: str = cli.config.get("json")
            if not os.path.exists(file_name) or not os.path.isfile(file_name):
                raise ValueError(f"File {file_name} does not exist")
            with open(cli.config.get("json"), "r") as f:
                json_str = f.read()

            # Password can be "", assume if None
            json_password = cli.config.get("json_password", "")

        wallet.regenerate_coldkey(
            mnemonic=cli.config.mnemonic,
            seed=cli.config.seed,
            json=(json_str, json_password),
            use_password=cli.config.use_password,
            overwrite=cli.config.overwrite_coldkey,
        )

    @staticmethod
    def check_config(config: "Config"):
        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)
        if (
            config.mnemonic is None
            and config.get("seed", d=None) is None
            and config.get("json", d=None) is None
        ):
            prompt_answer = Prompt.ask("Enter mnemonic, seed, or json file location")
            if prompt_answer.startswith("0x"):
                config.seed = prompt_answer
            elif len(prompt_answer.split(" ")) > 1:
                config.mnemonic = prompt_answer
            else:
                config.json = prompt_answer

        if config.get("json", d=None) and config.get("json_password", d=None) is None:
            config.json_password = Prompt.ask(
                "Enter json backup password", password=True
            )

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        regen_coldkey_parser = parser.add_parser(
            "regen_coldkey", help="""Regenerates a coldkey from a passed value"""
        )
        regen_coldkey_parser.add_argument(
            "--mnemonic",
            required=False,
            nargs="+",
            help="Mnemonic used to regen your key i.e. horse cart dog ...",
        )
        regen_coldkey_parser.add_argument(
            "--seed",
            required=False,
            default=None,
            help="Seed hex string used to regen your key i.e. 0x1234...",
        )
        regen_coldkey_parser.add_argument(
            "--json",
            required=False,
            default=None,
            help="""Path to a json file containing the encrypted key backup. (e.g. from PolkadotJS)""",
        )
        regen_coldkey_parser.add_argument(
            "--json_password",
            required=False,
            default=None,
            help="""Password to decrypt the json file.""",
        )
        regen_coldkey_parser.add_argument(
            "--use_password",
            dest="use_password",
            action="store_true",
            help="""Set true to protect the generated cybertensor key with a password.""",
            default=True,
        )
        regen_coldkey_parser.add_argument(
            "--no_password",
            dest="use_password",
            action="store_false",
            help="""Set off protects the generated cybertensor key with a password.""",
        )
        regen_coldkey_parser.add_argument(
            "--overwrite_coldkey",
            default=False,
            action="store_false",
            help="""Overwrite the old coldkey with the newly generated coldkey""",
        )
        Wallet.add_args(regen_coldkey_parser)
        cybertensor.cwtensor.add_args(regen_coldkey_parser)


class RegenColdkeypubCommand:
    """
    Executes the 'regen_coldkeypub' command to regenerate the public part of a coldkey (coldkeypub) for a wallet on the Cybertensor network.
    This command is used when a user needs to recreate their coldkeypub from an existing public key or address.

    Usage:
    The command requires either a public key in hexadecimal format or an address to regenerate the coldkeypub.
    It optionally allows overwriting an existing coldkeypub file.

    Optional arguments:
    - --public_key_hex (str): The public key in hex format.
    - --address (str): The address of the coldkey.
    - --overwrite_coldkeypub (bool): Overwrites the existing coldkeypub file with the new one.

    Example usage:
    >>> ctcli wallet regen_coldkeypub --address bostrom142x...

    Note:
    This command is particularly useful for users who need to regenerate their coldkeypub, perhaps due to file corruption or loss.
    It is a recovery-focused utility that ensures continued access to wallet functionalities.
    """

    def run(cli: "cybertensor.cli") -> None:
        r"""Creates a new coldkeypub under this wallet."""
        try:
            cwtensor = cybertensor.cwtensor(config=cli.config, log_verbose=False)
            RegenColdkeypubCommand._run(cli, cwtensor)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def _run(cli: "cybertensor.cli", cwtensor: "cybertensor.cwtensor"):
        wallet = Wallet(config=cli.config)
        wallet.regenerate_coldkeypub(
            address=cli.config.get("address"),
            public_key=cli.config.get("public_key_hex"),
            overwrite=cli.config.overwrite_coldkeypub,
        )

    @staticmethod
    def check_config(config: "Config"):
        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)
        if config.address is None and config.public_key_hex is None:
            prompt_answer = Prompt.ask(
                "Enter the address or the public key in hex"
            )
            if prompt_answer.startswith("0x"):
                config.public_key_hex = prompt_answer
            else:
                config.address = prompt_answer
        if not cybertensor.utils.is_valid_cybertensor_address_or_public_key(
                address=(
                        config.address if config.address else config.public_key_hex
                )
        ):
            sys.exit(1)

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        regen_coldkeypub_parser = parser.add_parser(
            "regen_coldkeypub",
            help="""Regenerates a coldkeypub from the public part of the coldkey.""",
        )
        regen_coldkeypub_parser.add_argument(
            "--public_key",
            "--pubkey",
            dest="public_key_hex",
            required=False,
            default=None,
            type=str,
            help="The public key (in hex) of the coldkey to regen e.g. 0x1234 ...",
        )
        regen_coldkeypub_parser.add_argument(
            "--address",
            "--addr",
            dest="address",
            required=False,
            default=None,
            type=str,
            help="The address of the coldkey to regen e.g. bostrom142x...",
        )
        regen_coldkeypub_parser.add_argument(
            "--overwrite_coldkeypub",
            default=False,
            action="store_true",
            help="""Overwrite the old coldkeypub file with the newly generated coldkeypub""",
        )
        Wallet.add_args(regen_coldkeypub_parser)
        cybertensor.cwtensor.add_args(regen_coldkeypub_parser)


class RegenHotkeyCommand:
    """
    Executes the 'regen_hotkey' command to regenerate a hotkey for a wallet on the Cybertensor network.
    Similar to regenerating a coldkey, this command creates a new hotkey from a mnemonic, seed, or JSON file.

    Usage:
    Users can provide a mnemonic, seed string, or a JSON file to regenerate the hotkey.
    The command supports optional password protection and can overwrite an existing hotkey.

    Optional arguments:
    - --mnemonic (str): A mnemonic phrase used to regenerate the key.
    - --seed (str): A seed hex string used for key regeneration.
    - --json (str): Path to a JSON file containing an encrypted key backup.
    - --json_password (str): Password to decrypt the JSON file.
    - --use_password (bool): Enables password protection for the generated key.
    - --overwrite_hotkey (bool): Overwrites the existing hotkey with the new one.

    Example usage:
    >>> ctcli wallet regen_hotkey
    >>> ctcli wallet regen_hotkey --seed 0x1234...

    Note:
    This command is essential for users who need to regenerate their hotkey, possibly for security upgrades or key recovery.
    It should be used cautiously to avoid accidental overwrites of existing keys.
    """

    def run(cli: "cybertensor.cli") -> None:
        r"""Creates a new coldkey under this wallet."""
        wallet = Wallet(config=cli.config)

        json_str: Optional[str] = None
        json_password: Optional[str] = None
        if cli.config.get("json"):
            file_name: str = cli.config.get("json")
            if not os.path.exists(file_name) or not os.path.isfile(file_name):
                raise ValueError(f"File {file_name} does not exist")
            with open(cli.config.get("json"), "r") as f:
                json_str = f.read()

            # Password can be "", assume if None
            json_password = cli.config.get("json_password", "")

        wallet.regenerate_hotkey(
            mnemonic=cli.config.mnemonic,
            seed=cli.config.seed,
            json=(json_str, json_password),
            use_password=cli.config.use_password,
            overwrite=cli.config.overwrite_hotkey,
        )

    @staticmethod
    def check_config(config: "Config"):
        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

        if not config.is_set("wallet.hotkey") and not config.no_prompt:
            hotkey = Prompt.ask("Enter hotkey name", default=defaults.wallet.hotkey)
            config.wallet.hotkey = str(hotkey)
        if (
            config.mnemonic is None
            and config.get("seed", d=None) is None
            and config.get("json", d=None) is None
        ):
            prompt_answer = Prompt.ask("Enter mnemonic, seed, or json file location")
            if prompt_answer.startswith("0x"):
                config.seed = prompt_answer
            elif len(prompt_answer.split(" ")) > 1:
                config.mnemonic = prompt_answer
            else:
                config.json = prompt_answer

        if config.get("json", d=None) and config.get("json_password", d=None) is None:
            config.json_password = Prompt.ask(
                "Enter json backup password", password=True
            )

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        regen_hotkey_parser = parser.add_parser(
            "regen_hotkey", help="""Regenerates a hotkey from a passed mnemonic"""
        )
        regen_hotkey_parser.add_argument(
            "--mnemonic",
            required=False,
            nargs="+",
            help="Mnemonic used to regen your key i.e. horse cart dog ...",
        )
        regen_hotkey_parser.add_argument(
            "--seed",
            required=False,
            default=None,
            help="Seed hex string used to regen your key i.e. 0x1234...",
        )
        regen_hotkey_parser.add_argument(
            "--json",
            required=False,
            default=None,
            help="""Path to a json file containing the encrypted key backup. (e.g. from PolkadotJS)""",
        )
        regen_hotkey_parser.add_argument(
            "--json_password",
            required=False,
            default=None,
            help="""Password to decrypt the json file.""",
        )
        regen_hotkey_parser.add_argument(
            "--use_password",
            dest="use_password",
            action="store_true",
            help="""Set true to protect the generated cybertensor key with a password.""",
            default=False,
        )
        regen_hotkey_parser.add_argument(
            "--no_password",
            dest="use_password",
            action="store_false",
            help="""Set off protects the generated cybertensor key with a password.""",
        )
        regen_hotkey_parser.add_argument(
            "--overwrite_hotkey",
            dest="overwrite_hotkey",
            action="store_true",
            default=False,
            help="""Overwrite the old hotkey with the newly generated hotkey""",
        )
        Wallet.add_args(regen_hotkey_parser)
        cybertensor.cwtensor.add_args(regen_hotkey_parser)


class NewHotkeyCommand:
    """
    Executes the 'new_hotkey' command to create a new hotkey under a wallet on the Cybertensor network.
    This command is used to generate a new hotkey for managing a neuron or participating in the network.

    Usage:
    The command creates a new hotkey with an optional word count for the mnemonic and supports password protection.
    It also allows overwriting an existing hotkey.

    Optional arguments:
    - --n_words (int): The number of words in the mnemonic phrase.
    - --use_password (bool): Enables password protection for the generated key.
    - --overwrite_hotkey (bool): Overwrites the existing hotkey with the new one.

    Example usage:
    >>> ctcli wallet new_hotkey --n_words 24

    Note:
    This command is useful for users who wish to create additional hotkeys for different purposes,
    such as running multiple miners or separating operational roles within the network.
    """

    def run(cli: "cybertensor.cli") -> None:
        """Creates a new hotke under this wallet."""
        try:
            cwtensor = cybertensor.cwtensor(config=cli.config, log_verbose=False)
            NewHotkeyCommand._run(cli, cwtensor)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def _run(cli: "cybertensor.cli", cwtensor: "cybertensor.cwtensor"):
        wallet = Wallet(config=cli.config)
        wallet.create_new_hotkey(
            n_words=cli.config.n_words,
            use_password=cli.config.use_password,
            overwrite=cli.config.overwrite_hotkey,
        )

    @staticmethod
    def check_config(config: "Config"):
        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

        if not config.is_set("wallet.hotkey") and not config.no_prompt:
            hotkey = Prompt.ask("Enter hotkey name", default=defaults.wallet.hotkey)
            config.wallet.hotkey = str(hotkey)

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        new_hotkey_parser = parser.add_parser(
            "new_hotkey",
            help="""Creates a new hotkey (for running a miner) under the specified path.""",
        )
        new_hotkey_parser.add_argument(
            "--n_words",
            type=int,
            choices=[12, 15, 18, 21, 24],
            default=12,
            help="""The number of words representing the mnemonic. i.e. horse cart dog ... x 24""",
        )
        new_hotkey_parser.add_argument(
            "--use_password",
            dest="use_password",
            action="store_true",
            help="""Set true to protect the generated cybertensor key with a password.""",
            default=False,
        )
        new_hotkey_parser.add_argument(
            "--no_password",
            dest="use_password",
            action="store_false",
            help="""Set off protects the generated cybertensor key with a password.""",
        )
        new_hotkey_parser.add_argument(
            "--overwrite_hotkey",
            action="store_false",
            default=False,
            help="""Overwrite the old hotkey with the newly generated hotkey""",
        )
        Wallet.add_args(new_hotkey_parser)
        cybertensor.cwtensor.add_args(new_hotkey_parser)


class NewColdkeyCommand:
    """
    Executes the 'new_coldkey' command to create a new coldkey under a wallet on the Cybertensor network.
    This command generates a coldkey, which is essential for holding balances and performing high-value transactions.

    Usage:
    The command creates a new coldkey with an optional word count for the mnemonic and supports password protection.
    It also allows overwriting an existing coldkey.

    Optional arguments:
    - --n_words (int): The number of words in the mnemonic phrase.
    - --use_password (bool): Enables password protection for the generated key.
    - --overwrite_coldkey (bool): Overwrites the existing coldkey with the new one.

    Example usage:
    >>> ctcli wallet new_coldkey --n_words 15

    Note:
    This command is crucial for users who need to create a new coldkey for enhanced security or as part of setting up a new wallet.
    It's a foundational step in establishing a secure presence on the Cybertensor network.
    """

    def run(cli: "cybertensor.cli") -> None:
        r"""Creates a new coldkey under this wallet."""
        try:
            cwtensor = cybertensor.cwtensor(config=cli.config, log_verbose=False)
            NewColdkeyCommand._run(cli, cwtensor)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def _run(cli: "cybertensor.cli", cwtensor: "cybertensor.cwtensor"):
        wallet = Wallet(config=cli.config)
        wallet.create_new_coldkey(
            n_words=cli.config.n_words,
            use_password=cli.config.use_password,
            overwrite=cli.config.overwrite_coldkey,
        )

    @staticmethod
    def check_config(config: "Config"):
        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        new_coldkey_parser = parser.add_parser(
            "new_coldkey",
            help="""Creates a new coldkey (for containing balance) under the specified path. """,
        )
        new_coldkey_parser.add_argument(
            "--n_words",
            type=int,
            choices=[12, 15, 18, 21, 24],
            default=12,
            help="""The number of words representing the mnemonic. i.e. horse cart dog ... x 24""",
        )
        new_coldkey_parser.add_argument(
            "--use_password",
            dest="use_password",
            action="store_true",
            help="""Set true to protect the generated cybertensor key with a password.""",
            default=True,
        )
        new_coldkey_parser.add_argument(
            "--no_password",
            dest="use_password",
            action="store_false",
            help="""Set off protects the generated cybertensor key with a password.""",
        )
        new_coldkey_parser.add_argument(
            "--overwrite_coldkey",
            action="store_false",
            default=False,
            help="""Overwrite the old coldkey with the newly generated coldkey""",
        )
        Wallet.add_args(new_coldkey_parser)
        cybertensor.cwtensor.add_args(new_coldkey_parser)


class WalletCreateCommand:
    """
    Executes the 'create' command to generate both a new coldkey and hotkey under a specified wallet on the Cybertensor network.
    This command is a comprehensive utility for creating a complete wallet setup with both cold and hotkeys.

    Usage:
    The command facilitates the creation of a new coldkey and hotkey with an optional word count for the mnemonics.
    It supports password protection for the coldkey and allows overwriting of existing keys.

    Optional arguments:
    - --n_words (int): The number of words in the mnemonic phrase for both keys.
    - --use_password (bool): Enables password protection for the coldkey.
    - --overwrite_coldkey (bool): Overwrites the existing coldkey with the new one.
    - --overwrite_hotkey (bool): Overwrites the existing hotkey with the new one.

    Example usage:
    >>> ctcli wallet create --n_words 21

    Note:
    This command is ideal for new users setting up their wallet for the first time or for those who wish to completely renew their wallet keys.
    It ensures a fresh start with new keys for secure and effective participation in the network.
    """

    def run(cli: "cybertensor.cli") -> None:
        r"""Creates a new coldkey and hotkey under this wallet."""
        try:
            cwtensor = cybertensor.cwtensor(config=cli.config, log_verbose=False)
            WalletCreateCommand._run(cli, cwtensor)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def _run(cli: "cybertensor.cli", cwtensor: "cybertensor.cwtensor"):
        wallet = Wallet(config=cli.config)
        wallet.create_new_coldkey(
            n_words=cli.config.n_words,
            use_password=cli.config.use_password,
            overwrite=cli.config.overwrite_coldkey,
        )
        wallet.create_new_hotkey(
            n_words=cli.config.n_words,
            use_password=False,
            overwrite=cli.config.overwrite_hotkey,
        )

    @staticmethod
    def check_config(config: "Config"):
        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)
        if not config.is_set("wallet.hotkey") and not config.no_prompt:
            hotkey = Prompt.ask("Enter hotkey name", default=defaults.wallet.hotkey)
            config.wallet.hotkey = str(hotkey)

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        new_coldkey_parser = parser.add_parser(
            "create",
            help="""Creates a new coldkey (for containing balance) under the specified path. """,
        )
        new_coldkey_parser.add_argument(
            "--n_words",
            type=int,
            choices=[12, 15, 18, 21, 24],
            default=12,
            help="""The number of words representing the mnemonic. i.e. horse cart dog ... x 24""",
        )
        new_coldkey_parser.add_argument(
            "--use_password",
            dest="use_password",
            action="store_true",
            help="""Set true to protect the generated cybertensor key with a password.""",
            default=True,
        )
        new_coldkey_parser.add_argument(
            "--no_password",
            dest="use_password",
            action="store_false",
            help="""Set off protects the generated cybertensor key with a password.""",
        )
        new_coldkey_parser.add_argument(
            "--overwrite_coldkey",
            action="store_false",
            default=False,
            help="""Overwrite the old coldkey with the newly generated coldkey""",
        )
        new_coldkey_parser.add_argument(
            "--overwrite_hotkey",
            action="store_false",
            default=False,
            help="""Overwrite the old hotkey with the newly generated hotkey""",
        )
        Wallet.add_args(new_coldkey_parser)
        cybertensor.cwtensor.add_args(new_coldkey_parser)


def _get_coldkey_wallets_for_path(path: str) -> List["Wallet"]:
    """Get all coldkey wallet names from path."""
    try:
        wallet_names = next(os.walk(os.path.expanduser(path)))[1]
        return [Wallet(path=path, name=name) for name in wallet_names]
    except StopIteration:
        # No wallet files found.
        wallets = []
    return wallets


class UpdateWalletCommand:
    """
    Executes the 'update' command to check and potentially update the security of the wallets in the Cybertensor network.
    This command is used to enhance wallet security using modern encryption standards.

    Usage:
    The command checks if any of the wallets need an update in their security protocols.
    It supports updating all legacy wallets or a specific one based on the user's choice.

    Optional arguments:
    - --all (bool): When set, updates all legacy wallets.
    - --no_prompt (bool): Disables user prompting during the update process.

    Example usage:
    >>> ctcli wallet update --all

    Note:
    This command is important for maintaining the highest security standards for users' wallets.
    It is recommended to run this command periodically to ensure wallets are up-to-date with the latest security practices.
    """

    @staticmethod
    def run(cli: "cybertensor.cli") -> None:
        """Check if any of the wallets needs an update."""
        try:
            cwtensor = cybertensor.cwtensor(config=cli.config, log_verbose=False)
            UpdateWalletCommand._run(cli, cwtensor)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def _run(cli: "cybertensor.cli", cwtensor: "cybertensor.cwtensor"):
        config = cli.config.copy()
        if config.get("all", d=False) is True:
            wallets = _get_coldkey_wallets_for_path(config.wallet.path)
        else:
            wallets = [Wallet(config=config)]

        for wallet in wallets:
            print("\n===== ", wallet, " =====")
            wallet.coldkey_file.check_and_update_encryption()

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        update_wallet_parser = parser.add_parser(
            "update",
            help="""Updates the wallet security using NaCL instead of anvisible vault.""",
        )
        update_wallet_parser.add_argument("--all", action="store_true")
        Wallet.add_args(update_wallet_parser)
        cybertensor.cwtensor.add_args(update_wallet_parser)

    @staticmethod
    def check_config(config: "Config"):
        if config.get("all", d=False) is False:
            if not config.no_prompt:
                if Confirm.ask("Do you want to update all legacy wallets?"):
                    config["all"] = True

        # Ask the user to specify the wallet if the wallet name is not clear.
        if (
            config.get("all", d=False) is False
            and config.wallet.get("name") == cybertensor.defaults.wallet.name
            and not config.no_prompt
        ):
            wallet_name = Prompt.ask(
                "Enter wallet name", default=cybertensor.defaults.wallet.name
            )
            config.wallet.name = str(wallet_name)


def _get_coldkey_addresses_for_path(path: str) -> tuple[list[str], list[str]]:
    """Get all coldkey addresses from path."""

    def list_coldkeypub_files(dir_path):
        abspath = os.path.abspath(os.path.expanduser(dir_path))
        coldkey_files = []
        wallet_names = []

        for potential_wallet_name in os.listdir(abspath):
            coldkey_path = os.path.join(
                abspath, potential_wallet_name, "coldkeypub.txt"
            )
            if os.path.isdir(
                    os.path.join(abspath, potential_wallet_name)
            ) and os.path.exists(coldkey_path):
                coldkey_files.append(coldkey_path)
                wallet_names.append(potential_wallet_name)
            else:
                cybertensor.logging.warning(
                    f"{coldkey_path} does not exist. Excluding..."
                )
        return coldkey_files, wallet_names

    coldkey_files, wallet_names = list_coldkeypub_files(path)
    addresses = [
        cybertensor.keyfile(coldkey_path).keypair.address
        for coldkey_path in coldkey_files
    ]
    return addresses, wallet_names


class WalletBalanceCommand:
    """
    Executes the 'balance' command to check the balance of the wallet on the Cybertensor network.
    This command provides a detailed view of the wallet's coldkey balances, including free and staked balances.

    Usage:
    The command lists the balances of all wallets in the user's configuration directory, showing the wallet name,
    coldkey address, and the respective free and staked balances.

    Optional arguments:
    None. The command uses the wallet and cwtensor configurations to fetch balance data.

    Example usage:
    >>> ctcli wallet balance

    Note:
    This command is essential for users to monitor their financial status on the Cybertensor network.
    It helps in keeping track of assets and ensuring the wallet's financial health.
    """

    @staticmethod
    def run(cli: "cybertensor.cli") -> None:
        """Check the balance of the wallet."""
        try:
            cwtensor = cybertensor.cwtensor(config=cli.config, log_verbose=False)
            WalletBalanceCommand._run(cli, cwtensor)
        finally:
            if "cwtensor" in locals():
                cwtensor.close()
                cybertensor.logging.debug("closing cwtensor connection")

    @staticmethod
    def _run(cli: "cybertensor.cli", cwtensor: "cybertensor.cwtensor"):
        wallet = cybertensor.Wallet(config=cli.config)

        wallet_names = []
        coldkeys = []
        free_balances = []
        staked_balances = []
        total_free_balance = 0
        total_staked_balance = 0
        balances = {}

        if cli.config.get("all", d=None):
            coldkeys, wallet_names = _get_coldkey_addresses_for_path(
                cli.config.wallet.path
            )

            free_balances = [
                cwtensor.get_balance(coldkeys[i]) for i in range(len(coldkeys))
            ]

            staked_balances = [
                cwtensor.get_total_stake_for_coldkey(coldkeys[i])
                for i in range(len(coldkeys))
            ]

            total_free_balance = sum(free_balances)
            total_staked_balance = sum(staked_balances)

            balances = {
                name: (coldkey, free, staked)
                for name, coldkey, free, staked in sorted(
                    zip(wallet_names, coldkeys, free_balances, staked_balances)
                )
            }
        else:
            coldkey_wallet = cybertensor.Wallet(config=cli.config)
            if (
                    coldkey_wallet.coldkeypub_file.exists_on_device()
                    and not coldkey_wallet.coldkeypub_file.is_encrypted()
            ):
                coldkeys = [coldkey_wallet.coldkeypub.address]
                wallet_names = [coldkey_wallet.name]

                free_balances = [
                    cwtensor.get_balance(coldkeys[i]) for i in range(len(coldkeys))
                ]

                staked_balances = [
                    cwtensor.get_total_stake_for_coldkey(coldkeys[i])
                    for i in range(len(coldkeys))
                ]

                total_free_balance = sum(free_balances)
                total_staked_balance = sum(staked_balances)

                balances = {
                    name: (coldkey, free, staked)
                    for name, coldkey, free, staked in sorted(
                        zip(wallet_names, coldkeys, free_balances, staked_balances)
                    )
                }

            if not coldkey_wallet.coldkeypub_file.exists_on_device():
                cybertensor.__console__.print("[bold red]No wallets found.")
                return

        table = Table(show_footer=False)
        table.title = "[white]Wallet Coldkey Balances"
        table.add_column(
            "[white]Wallet Name",
            header_style="overline white",
            footer_style="overline white",
            style="rgb(50,163,219)",
            no_wrap=True,
        )

        table.add_column(
            "[white]Coldkey Address",
            header_style="overline white",
            footer_style="overline white",
            style="rgb(50,163,219)",
            no_wrap=True,
        )

        for typestr in ["Free", "Staked", "Total"]:
            table.add_column(
                f"[white]{typestr} Balance",
                header_style="overline white",
                footer_style="overline white",
                justify="right",
                style="green",
                no_wrap=True,
            )

        for name, (coldkey, free, staked) in balances.items():
            table.add_row(
                name,
                coldkey,
                str(free),
                str(staked),
                str(free + staked),
            )
        table.add_row()
        table.add_row(
            "Total Balance Across All Coldkeys",
            "",
            str(total_free_balance),
            str(total_staked_balance),
            str(total_free_balance + total_staked_balance),
        )
        table.show_footer = True

        table.box = None
        table.pad_edge = False
        table.width = None
        console.print(table)

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        balance_parser = parser.add_parser(
            "balance", help="""Checks balances of wallets in the wallet path."""
        )
        balance_parser.add_argument(
            "--all",
            dest="all",
            action="store_true",
            help="""View balance for all wallets.""",
            default=False,
        )
        Wallet.add_args(balance_parser)
        cybertensor.cwtensor.add_args(balance_parser)

    @staticmethod
    def check_config(config: "Config"):
        if (
            not config.is_set("wallet.path")
            and not config.no_prompt
            and not config.get("all", d=None)
        ):
            path = Prompt.ask("Enter wallets path", default=defaults.wallet.path)
            config.wallet.path = str(path)

        if (
                not config.is_set("wallet.name")
                and not config.no_prompt
                and not config.get("all", d=None)
        ):
            wallet_name = Prompt.ask(
                "Enter wallet name", default=defaults.wallet.name
            )
            config.wallet.name = str(wallet_name)

        if not config.is_set("cwtensor.network") and not config.no_prompt:
            network = Prompt.ask(
                "Enter network",
                default=defaults.cwtensor.network,
                choices=cybertensor.__networks__,
            )
            config.cwtensor.network = str(network)



API_URL = ""
MAX_TXN = 1000
GRAPHQL_QUERY = """
query ($first: Int!, $after: Cursor, $filter: TransferFilter, $order: [TransfersOrderBy!]!) {
    transfers(first: $first, after: $after, filter: $filter, orderBy: $order) {
        nodes {
            id
            from
            to
            amount
            extrinsicId
            blockNumber
        }
        pageInfo {
            endCursor
            hasNextPage
            hasPreviousPage
        }
        totalCount
    }
}
"""


class GetWalletHistoryCommand:
    """
    DISABLED COMMAND

    Executes the ``history`` command to fetch the latest transfers of the provided wallet on the cybertensor network.

    This command provides a detailed view of the transfers carried out on the wallet.

    Usage:
        The command lists the latest transfers of the provided wallet, showing the From, To, Amount, Extrinsic Id and Block Number.

    Optional arguments:
        None. The command uses the wallet and cwtensor configurations to fetch latest transfer data associated with a wallet.

    Example usage::

        ctcli wallet history

    Note:
        This command is essential for users to monitor their financial status on the cybertensor network.
        It helps in fetching info on all the transfers so that user can easily tally and cross-check the transactions.
    """

    @staticmethod
    def run(cli):
        r"""Check the transfer history of the provided wallet."""
        wallet = cybertensor.Wallet(config=cli.config)
        wallet_address = wallet.get_coldkeypub().address
        # Fetch all transfers
        transfers = get_wallet_transfers(wallet_address)

        # Create output table
        table = create_transfer_history_table(transfers)

        cybertensor.__console__.print(table)

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        history_parser = parser.add_parser(
            "history",
            help="""Fetch transfer history associated with the provided wallet""",
        )
        cybertensor.Wallet.add_args(history_parser)
        cybertensor.cwtensor.add_args(history_parser)

    @staticmethod
    def check_config(config: "cybertensor.Config"):
        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)


def get_wallet_transfers(wallet_address) -> List[dict]:
    """Get all transfers associated with the provided wallet address."""

    variables = {
        "first": MAX_TXN,
        "filter": {
            "or": [
                {"from": {"equalTo": wallet_address}},
                {"to": {"equalTo": wallet_address}},
            ]
        },
        "order": "BLOCK_NUMBER_DESC",
    }

    response = requests.post(
        API_URL, json={"query": GRAPHQL_QUERY, "variables": variables}
    )
    data = response.json()

    # Extract nodes and pageInfo from the response
    transfer_data = data.get("data", {}).get("transfers", {})
    transfers = transfer_data.get("nodes", [])

    return transfers


def create_transfer_history_table(transfers):
    """Get output transfer table"""

    table = Table(show_footer=False)
    # Define the column names
    column_names = [
        "Id",
        "From",
        "To",
        f"Amount ({cybertensor.__giga_boot_symbol__})",
        "Extrinsic Id",
        "Block Number",
        "URL (stats)",
    ]
    stats_url_base = ""

    # Create a table
    table = Table(show_footer=False)
    table.title = "[white]Wallet Transfers"

    # Define the column styles
    header_style = "overline white"
    footer_style = "overline white"
    column_style = "rgb(50,163,219)"
    no_wrap = True

    # Add columns to the table
    for column_name in column_names:
        table.add_column(
            f"[white]{column_name}",
            header_style=header_style,
            footer_style=footer_style,
            style=column_style,
            no_wrap=no_wrap,
            justify="left" if column_name == "Id" else "right",
        )

    # Add rows to the table
    for item in transfers:
        try:
            gboot_amount = int(item["amount"]) / cybertensor.GIGA
        except:
            gboot_amount = item["amount"]
        table.add_row(
            item["id"],
            item["from"],
            item["to"],
            f"{gboot_amount:.3f}",
            str(item["extrinsicId"]),
            item["blockNumber"],
            f"{stats_url_base}/{item['blockNumber']}-{item['extrinsicId']}",
        )
    table.add_row()
    table.show_footer = True
    table.box = None
    table.pad_edge = False
    table.width = None
    return table
