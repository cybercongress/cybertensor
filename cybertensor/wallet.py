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
import copy
import os
from typing import Optional, Union, Tuple, Dict, overload

from termcolor import colored

import cybertensor
from cybertensor.config import Config
from cybertensor.keypair import Keypair
from cybertensor.utils import is_valid_cybertensor_address_or_public_key


def display_mnemonic_msg(keypair: Keypair, key_type: str):
    """
    Display the mnemonic and a warning message to keep the mnemonic safe.

    Args:
        keypair (Keypair): Keypair object.
        key_type (str): Type of the key (coldkey or hotkey).
    """
    mnemonic = keypair.mnemonic
    mnemonic_green = colored(mnemonic, "green")
    print(
        colored(
            "\nIMPORTANT: Store this mnemonic in a secure (preferable offline place), as anyone "
            "who has possession of this mnemonic can use it to regenerate the key and access your tokens. \n",
            "red",
        )
    )
    print(
        f"The mnemonic to the new {key_type} is:\n"
        f"\n"
        f"{mnemonic_green}\n"
        f"You can use the mnemonic to recreate the key in case it gets lost. "
        f"The command to use to regenerate the key using this mnemonic is:\n"
        f"ctcli w regen_{key_type} --mnemonic {mnemonic}\n"
    )


class Wallet:
    """
    The wallet class in the cybertensor framework handles wallet functionality, crucial for participating in 
    the cybertensor network.
    It manages two types of keys: coldkey and hotkey, each serving different purposes in network operations. 
    Each wallet contains a coldkey and a hotkey.
    The coldkey is the user's primary key for holding stake in their wallet and is the only way that users
    can access Tao. Coldkeys can hold tokens and should be encrypted on your device.
    The coldkey is the primary key used for securing the wallet's stake in the cybertensor network (Tao) and
    is critical for financial transactions like staking and unstaking tokens. It's recommended to keep the
    coldkey encrypted and secure, as it holds the actual tokens.
    The hotkey, in contrast, is used for operational tasks like subscribing to and setting weights in the
    network. It's linked to the coldkey through the metagraph and does not directly hold tokens, thereby
    offering a safer way to interact with the network during regular operations.
    Args:
        name (str): The name of the wallet, used to identify it among possibly multiple wallets.
        path (str): File system path where wallet keys are stored.
        hotkey (str): String identifier for the hotkey.
        _hotkey, _coldkey, _coldkeypub (cybertensor.Keypair): Internal representations of the hotkey and coldkey.
    Methods:
        create_if_non_existent, create, recreate: Methods to handle the creation of wallet keys.
        get_coldkey, get_hotkey, get_coldkeypub: Methods to retrieve specific keys.
        set_coldkey, set_hotkey, set_coldkeypub: Methods to set or update keys.
        hotkey_file, coldkey_file, coldkeypub_file: Properties that return respective key file objects.
        regenerate_coldkey, regenerate_hotkey, regenerate_coldkeypub: Methods to regenerate keys from different sources.
        config, help, add_args: Utility methods for configuration and assistance.
    The wallet class is a fundamental component for users to interact securely with the cybertensor network,
    facilitating both operational tasks and transactions involving value transfer across the network.

    Example Usage::
        # Create a new wallet with default coldkey and hotkey names
        my_wallet = Wallet()
        # Access hotkey and coldkey
        hotkey = my_wallet.get_hotkey()
        coldkey = my_wallet.get_coldkey()
        # Set a new coldkey
        my_wallet.new_coldkey(n_words=24) # number of seed words to use
        # Update wallet hotkey
        my_wallet.set_hotkey(new_hotkey)
        # Print wallet details
        print(my_wallet)
        # Access coldkey property, must use password to unlock
        my_wallet.coldkey
    """

    @classmethod
    def config(cls) -> "Config":
        """
        Get config from the argument parser.

        Returns:
            Config: Config object.
        """
        parser = argparse.ArgumentParser()
        cls.add_args(parser)
        return Config(parser, args=[])

    @classmethod
    def help(cls):
        """
        Print help to stdout.
        """
        parser = argparse.ArgumentParser()
        cls.add_args(parser)
        print(cls.__new__.__doc__)
        parser.print_help()

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser, prefix: str = None):
        """
        Accept specific arguments from parser.

        Args:
            parser (argparse.ArgumentParser): Argument parser object.
            prefix (str): Argument prefix.
        """
        prefix_str = "" if prefix is None else prefix + "."
        try:
            default_name = os.getenv("CT_WALLET_NAME") or "default"
            default_hotkey = os.getenv("CT_WALLET_NAME") or "default"
            default_path = os.getenv("CT_WALLET_PATH") or "~/.cybertensor/wallets/"
            parser.add_argument(
                "--" + prefix_str + "wallet.name",
                required=False,
                default=default_name,
                help="The name of the wallet to unlock for running cybertensor "
                "(name mock is reserved for mocking this wallet)",
            )
            parser.add_argument(
                "--" + prefix_str + "wallet.hotkey",
                required=False,
                default=default_hotkey,
                help="The name of the wallet's hotkey.",
            )
            parser.add_argument(
                "--" + prefix_str + "wallet.path",
                required=False,
                default=default_path,
                help="The path to your cybertensor wallets",
            )
            parser.add_argument(
                "--no_prompt",
                dest="no_prompt",
                action="store_true",
                help="""Set true to avoid prompting the user.""",
                default=False,
            )
        except argparse.ArgumentError as e:
            print(f'ArgumentError {e}')
            pass

    def __init__(
        self,
        name: str = None,
        hotkey: str = None,
        path: str = None,
        config: "Config" = None,
    ):
        r"""
        Initialize the cybertensor wallet object containing a hot and coldkey.

        Args:
            name (str, optional): The name of the wallet to unlock for running cybertensor. Defaults to ``default``.
            hotkey (str, optional): The name of hotkey used to running the miner. Defaults to ``default``.
            path (str, optional): The path to your cybertensor wallets. Defaults to ``~/.cybertensor/wallets/``.
            config (Config, optional): Wallet.config(). Defaults to ``None``.
        """
        # Fill config from passed args using command line defaults.
        if config is None:
            config = Wallet.config()
        self.config = copy.deepcopy(config)
        self.config.wallet.name = name or self.config.wallet.get(
            "name", cybertensor.defaults.wallet.name
        )
        self.config.wallet.hotkey = hotkey or self.config.wallet.get(
            "hotkey", cybertensor.defaults.wallet.hotkey
        )
        self.config.wallet.path = path or self.config.wallet.get(
            "path", cybertensor.defaults.wallet.path
        )

        self.name = self.config.wallet.name
        self.path = self.config.wallet.path
        self.hotkey_str = self.config.wallet.hotkey

        self._hotkey = None
        self._coldkey = None
        self._coldkeypub = None

    def __str__(self):
        """
        Returns the string representation of the Wallet object.

        Returns:
            str: The string representation.
        """
        return f"wallet({self.name}, {self.hotkey_str}, {self.path})"

    def __repr__(self):
        """
        Returns the string representation of the Wallet object.

        Returns:
            str: The string representation.
        """
        return self.__str__()

    def create_if_non_existent(
        self, coldkey_use_password: bool = True, hotkey_use_password: bool = False
    ) -> "Wallet":
        """
        Checks for existing coldkeypub and hotkeys, and creates them if non-existent.

        Args:
            coldkey_use_password (bool, optional): Whether to use a password for coldkey. Defaults to ``True``.
            hotkey_use_password (bool, optional): Whether to use a password for hotkey. Defaults to ``False``.

        Returns:
            Wallet: The Wallet object.
        """
        return self.create(coldkey_use_password, hotkey_use_password)

    def create(
        self, coldkey_use_password: bool = True, hotkey_use_password: bool = False
    ) -> "Wallet":
        """
        Checks for existing coldkeypub and hotkeys and creates them if non-existent.

        Args:
            coldkey_use_password (bool, optional): Whether to use a password for coldkey. Defaults to ``True``.
            hotkey_use_password (bool, optional): Whether to use a password for hotkey. Defaults to ``False``.

        Returns:
            Wallet: The Wallet object.
        """
        # ---- Setup Wallet. ----
        if (
            not self.coldkey_file.exists_on_device()
            and not self.coldkeypub_file.exists_on_device()
        ):
            self.create_new_coldkey(n_words=12, use_password=coldkey_use_password)
        if not self.hotkey_file.exists_on_device():
            self.create_new_hotkey(n_words=12, use_password=hotkey_use_password)
        return self

    def recreate(
        self, coldkey_use_password: bool = True, hotkey_use_password: bool = False
    ) -> "Wallet":
        """
        Checks for existing coldkeypub and hotkeys and creates them if non-existent.

        Args:
            coldkey_use_password (bool, optional): Whether to use a password for coldkey. Defaults to ``True``.
            hotkey_use_password (bool, optional): Whether to use a password for hotkey. Defaults to ``False``.

        Returns:
            Wallet: The Wallet object.
        """
        # ---- Setup Wallet. ----
        self.create_new_coldkey(n_words=12, use_password=coldkey_use_password)
        self.create_new_hotkey(n_words=12, use_password=hotkey_use_password)
        return self

    @property
    def hotkey_file(self) -> "cybertensor.keyfile":
        """
        Property that returns the hotkey file.

        Returns:
            cybertensor.keyfile: The hotkey file.
        """
        wallet_path = os.path.expanduser(os.path.join(self.path, self.name))
        hotkey_path = os.path.join(wallet_path, "hotkeys", self.hotkey_str)
        return cybertensor.keyfile(path=hotkey_path)

    @property
    def coldkey_file(self) -> "cybertensor.keyfile":
        """
        Property that returns the coldkey file.

        Returns:
            cybertensor.keyfile: The coldkey file.
        """
        wallet_path = os.path.expanduser(os.path.join(self.path, self.name))
        coldkey_path = os.path.join(wallet_path, "coldkey")
        return cybertensor.keyfile(path=coldkey_path)

    @property
    def coldkeypub_file(self) -> "cybertensor.keyfile":
        """
        Property that returns the coldkeypub file.

        Returns:
            cybertensor.keyfile: The coldkeypub file.
        """
        wallet_path = os.path.expanduser(os.path.join(self.path, self.name))
        coldkeypub_path = os.path.join(wallet_path, "coldkeypub.txt")
        return cybertensor.keyfile(path=coldkeypub_path)

    def set_hotkey(
        self,
        keypair: "cybertensor.Keypair",
        encrypt: bool = False,
        overwrite: bool = False,
    ) -> "cybertensor.keyfile":
        """
        Sets the hotkey for the wallet.

        Args:
            keypair (cybertensor.Keypair): The hotkey keypair.
            encrypt (bool, optional): Whether to encrypt the hotkey. Defaults to ``False``.
            overwrite (bool, optional): Whether to overwrite an existing hotkey. Defaults to ``False``.

        Returns:
            cybertensor.keyfile: The hotkey file.
        """
        self._hotkey = keypair
        self.hotkey_file.set_keypair(keypair, encrypt=encrypt, overwrite=overwrite)

    def set_coldkeypub(
        self,
        keypair: "cybertensor.Keypair",
        encrypt: bool = False,
        overwrite: bool = False,
    ) -> "cybertensor.keyfile":
        """
        Sets the coldkeypub for the wallet.

        Args:
            keypair (cybertensor.Keypair): The coldkeypub keypair.
            encrypt (bool, optional): Whether to encrypt the coldkeypub. Defaults to ``False``.
            overwrite (bool, optional): Whether to overwrite an existing coldkeypub. Defaults to ``False``.

        Returns:
            cybertensor.keyfile: The coldkeypub file.
        """
        self._coldkeypub = cybertensor.Keypair(
            address=keypair.address, public_key=keypair.public_key
        )
        self.coldkeypub_file.set_keypair(
            self._coldkeypub, encrypt=encrypt, overwrite=overwrite
        )

    def set_coldkey(
        self,
        keypair: "cybertensor.Keypair",
        encrypt: bool = True,
        overwrite: bool = False,
    ) -> "cybertensor.keyfile":
        """
        Sets the coldkey for the wallet.

        Args:
            keypair (cybertensor.Keypair): The coldkey keypair.
            encrypt (bool, optional): Whether to encrypt the coldkey. Defaults to ``True``.
            overwrite (bool, optional): Whether to overwrite an existing coldkey. Defaults to ``False``.

        Returns:
            cybertensor.keyfile: The coldkey file.
        """
        self._coldkey = keypair
        self.coldkey_file.set_keypair(
            self._coldkey, encrypt=encrypt, overwrite=overwrite
        )

    def get_coldkey(self, password: str = None) -> "cybertensor.Keypair":
        """
        Gets the coldkey from the wallet.

        Args:
            password (str, optional): The password to decrypt the coldkey. Defaults to ``None``.

        Returns:
            cybertensor.Keypair: The coldkey keypair.
        """
        return self.coldkey_file.get_keypair(password=password)

    def get_hotkey(self, password: str = None) -> "cybertensor.Keypair":
        """
        Gets the hotkey from the wallet.

        Args:
            password (str, optional): The password to decrypt the hotkey. Defaults to ``None``.

        Returns:
            cybertensor.Keypair: The hotkey keypair.
        """
        return self.hotkey_file.get_keypair(password=password)

    def get_coldkeypub(self, password: str = None) -> "cybertensor.Keypair":
        """
        Gets the coldkeypub from the wallet.

        Args:
            password (str, optional): The password to decrypt the coldkeypub. Defaults to ``None``.

        Returns:
            cybertensor.Keypair: The coldkeypub keypair.
        """
        return self.coldkeypub_file.get_keypair(password=password)

    @property
    def hotkey(self) -> "cybertensor.Keypair":
        r"""Loads the hotkey from wallet.path/wallet.name/hotkeys/wallet.hotkey or raises an error.
        Returns:
            hotkey (Keypair):
                hotkey loaded from config arguments.
        Raises:
            KeyFileError: Raised if the file is corrupt of non-existent.
            CryptoKeyError: Raised if the user enters an incorrec password for an encrypted keyfile.
        """
        if self._hotkey is None:
            self._hotkey = self.hotkey_file.keypair
        return self._hotkey

    @property
    def coldkey(self) -> "cybertensor.Keypair":
        r"""Loads the hotkey from wallet.path/wallet.name/coldkey or raises an error.
        Returns:
            coldkey (Keypair):
                colkey loaded from config arguments.
        Raises:
            KeyFileError: Raised if the file is corrupt of non-existent.
            CryptoKeyError: Raised if the user enters an incorrec password for an encrypted keyfile.
        """
        if self._coldkey is None:
            self._coldkey = self.coldkey_file.keypair
        return self._coldkey

    @property
    def coldkeypub(self) -> "cybertensor.Keypair":
        r"""Loads the coldkeypub from wallet.path/wallet.name/coldkeypub.txt or raises an error.
        Returns:
            coldkeypub (Keypair):
                colkeypub loaded from config arguments.
        Raises:
            KeyFileError: Raised if the file is corrupt of non-existent.
            CryptoKeyError: Raised if the user enters an incorrect password for an encrypted keyfile.
        """
        if self._coldkeypub is None:
            self._coldkeypub = self.coldkeypub_file.keypair
        return self._coldkeypub

    def new_coldkey(
        self,
        n_words: int = 12,
        use_password: bool = True,
        overwrite: bool = False,
        suppress: bool = False,
    ) -> "Wallet":
        """Creates a new coldkey, optionally encrypts it with the user's inputed password and saves to disk.
        Args:
            n_words: (int, optional):
                Number of mnemonic words to use.
            use_password (bool, optional):
                Is the created key password protected.
            overwrite (bool, optional):
                Determines if this operation overwrites the coldkey under the same path <wallet path>/<wallet name>/coldkey
        Returns:
            wallet (Wallet):
                this object with newly created coldkey.
        """
        self.create_new_coldkey(n_words, use_password, overwrite, suppress)

    def create_new_coldkey(
        self,
        n_words: int = 12,
        use_password: bool = True,
        overwrite: bool = False,
        suppress: bool = False,
    ) -> "Wallet":
        """Creates a new coldkey, optionally encrypts it with the user's inputed password and saves to disk.
        Args:
            n_words: (int, optional):
                Number of mnemonic words to use.
            use_password (bool, optional):
                Is the created key password protected.
            overwrite (bool, optional):
                Determines if this operation overwrites the coldkey under the same path <wallet path>/<wallet name>/coldkey
        Returns:
            wallet (Wallet):
                this object with newly created coldkey.
        """
        mnemonic = Keypair.generate_mnemonic(n_words)
        keypair = Keypair.create_from_mnemonic(mnemonic)
        if not suppress:
            display_mnemonic_msg(keypair, "coldkey")
        self.set_coldkey(keypair, encrypt=use_password, overwrite=overwrite)
        self.set_coldkeypub(keypair, overwrite=overwrite)
        return self

    def new_hotkey(
        self,
        n_words: int = 12,
        use_password: bool = False,
        overwrite: bool = False,
        suppress: bool = False,
    ) -> "Wallet":
        """Creates a new hotkey, optionally encrypts it with the user's inputed password and saves to disk.
        Args:
            n_words: (int, optional):
                Number of mnemonic words to use.
            use_password (bool, optional):
                Is the created key password protected.
            overwrite (bool, optional):
                Determines if this operation overwrites the hotkey under the same path <wallet path>/<wallet name>/hotkeys/<hotkey>
        Returns:
            wallet (Wallet):
                this object with newly created hotkey.
        """
        self.create_new_hotkey(n_words, use_password, overwrite, suppress)

    def create_new_hotkey(
        self,
        n_words: int = 12,
        use_password: bool = False,
        overwrite: bool = False,
        suppress: bool = False,
    ) -> "Wallet":
        """Creates a new hotkey, optionally encrypts it with the user's inputed password and saves to disk.
        Args:
            n_words: (int, optional):
                Number of mnemonic words to use.
            use_password (bool, optional):
                Is the created key password protected.
            overwrite (bool, optional):
                Determines if this operation overwrites the hotkey under the same path <wallet path>/<wallet name>/hotkeys/<hotkey>
        Returns:
            wallet (Wallet):
                this object with newly created hotkey.
        """
        mnemonic = Keypair.generate_mnemonic(n_words)
        keypair = Keypair.create_from_mnemonic(mnemonic)
        if not suppress:
            display_mnemonic_msg(keypair, "hotkey")
        self.set_hotkey(keypair, encrypt=use_password, overwrite=overwrite)
        return self

    def regenerate_coldkeypub(
        self,
        address: Optional[str] = None,
        public_key: Optional[Union[str, bytes]] = None,
        overwrite: bool = False,
        suppress: bool = False,
    ) -> "Wallet":
        """Regenerates the coldkeypub from passed address or public_key and saves the file.
           Requires either address or public_key to be passed.
        Args:
            address: (str, optional):
                Address as string.
            public_key: (str | bytes, optional):
                Public key as hex string or bytes.
            overwrite (bool, optional) (default: False):
                Determines if this operation overwrites the coldkeypub (if exists) under the same path <wallet path>/<wallet name>/coldkeypub
        Returns:
            wallet (Wallet):
                newly re-generated Wallet with coldkeypub.

        """
        if address is None and public_key is None:
            raise ValueError("Either address or public_key must be passed")

        if not is_valid_cybertensor_address_or_public_key(
            address if address is not None else public_key
        ):
            raise ValueError(
                f"Invalid {'address' if address is not None else 'public_key'}"
            )

        if address is not None:
            # TODO decode bech32 prefix and pass prefix extracted from address
            keypair = Keypair(
                address=address,
                public_key=public_key,
                prefix=cybertensor.__chain_address_prefix__,
            )
        else:
            keypair = Keypair(
                address=address,
                public_key=public_key,
                prefix=cybertensor.__chain_address_prefix__,
            )

        # No need to encrypt the public key
        self.set_coldkeypub(keypair, overwrite=overwrite)

        return self

    # Short name for regenerate_coldkeypub
    regen_coldkeypub = regenerate_coldkeypub

    @overload
    def regenerate_coldkey(
        self,
        mnemonic: Optional[Union[list, str]] = None,
        use_password: bool = True,
        overwrite: bool = False,
        suppress: bool = False,
    ) -> "Wallet":
        ...

    @overload
    def regenerate_coldkey(
        self,
        seed: Optional[str] = None,
        use_password: bool = True,
        overwrite: bool = False,
        suppress: bool = False,
    ) -> "Wallet":
        ...

    @overload
    def regenerate_coldkey(
        self,
        json: Optional[Tuple[Union[str, Dict], str]] = None,
        use_password: bool = True,
        overwrite: bool = False,
        suppress: bool = False,
    ) -> "Wallet":
        ...

    def regenerate_coldkey(
        self,
        use_password: bool = True,
        overwrite: bool = False,
        suppress: bool = False,
        **kwargs,
    ) -> "Wallet":
        """Regenerates the coldkey from passed mnemonic, seed, or json encrypts it with the user's password and saves the file
        Args:
            mnemonic: (Union[list, str], optional):
                Key mnemonic as list of words or string space separated words.
            seed: (str, optional):
                Seed as hex string.
            json: (Tuple[Union[str, Dict], str], optional):
                Restore from encrypted JSON backup as (json_data: Union[str, Dict], passphrase: str)
            use_password (bool, optional):
                Is the created key password protected.
            overwrite (bool, optional):
                Determines if this operation overwrites the coldkey under the same path <wallet path>/<wallet name>/coldkey
        Returns:
            wallet (Wallet):
                this object with newly created coldkey.

        Note: uses priority order: mnemonic > seed > json
        """
        if len(kwargs) == 0:
            raise ValueError("Must pass either mnemonic, seed, or json")

        # Get from kwargs
        mnemonic = kwargs.get("mnemonic", None)
        seed = kwargs.get("seed", None)
        json = kwargs.get("json", None)

        if mnemonic is None and seed is None and json is None:
            raise ValueError("Must pass either mnemonic, seed, or json")
        if mnemonic is not None:
            if isinstance(mnemonic, str):
                mnemonic = mnemonic.split()
            if len(mnemonic) not in [12, 15, 18, 21, 24]:
                raise ValueError(
                    "Mnemonic has invalid size. This should be 12,15,18,21 or 24 words"
                )
            keypair = Keypair.create_from_mnemonic(
                mnemonic=" ".join(mnemonic),
                prefix=cybertensor.__chain_address_prefix__,
            )
            if not suppress:
                display_mnemonic_msg(keypair, "coldkey")
        elif seed is not None:
            raise ValueError("Not implemented")
        else:
            # json is not None
            raise ValueError("Not implemented")

        self.set_coldkey(keypair, encrypt=use_password, overwrite=overwrite)
        self.set_coldkeypub(keypair, overwrite=overwrite)
        return self

    # Short name for regenerate_coldkey
    regen_coldkey = regenerate_coldkey

    @overload
    def regenerate_hotkey(
        self,
        mnemonic: Optional[Union[list, str]] = None,
        use_password: bool = True,
        overwrite: bool = False,
        suppress: bool = False,
    ) -> "Wallet":
        ...

    @overload
    def regenerate_hotkey(
        self,
        seed: Optional[str] = None,
        use_password: bool = True,
        overwrite: bool = False,
        suppress: bool = False,
    ) -> "Wallet":
        ...

    @overload
    def regenerate_hotkey(
        self,
        json: Optional[Tuple[Union[str, Dict], str]] = None,
        use_password: bool = True,
        overwrite: bool = False,
        suppress: bool = False,
    ) -> "Wallet":
        ...

    def regenerate_hotkey(
        self,
        use_password: bool = True,
        overwrite: bool = False,
        suppress: bool = False,
        **kwargs,
    ) -> "Wallet":
        """Regenerates the hotkey from passed mnemonic, encrypts it with the user's password and save the file
        Args:
            mnemonic: (Union[list, str], optional):
                Key mnemonic as list of words or string space separated words.
            seed: (str, optional):
                Seed as hex string.
            json: (Tuple[Union[str, Dict], str], optional):
                Restore from encrypted JSON backup as (json_data: Union[str, Dict], passphrase: str)
            use_password (bool, optional):
                Is the created key password protected.
            overwrite (bool, optional):
                Will this operation overwrite the hotkey under the same path <wallet path>/<wallet name>/hotkeys/<hotkey>
        Returns:
            wallet (Wallet):
                this object with newly created hotkey.
        """
        if len(kwargs) == 0:
            raise ValueError("Must pass either mnemonic, seed, or json")

        # Get from kwargs
        mnemonic = kwargs.get("mnemonic", None)
        seed = kwargs.get("seed", None)
        json = kwargs.get("json", None)

        if mnemonic is None and seed is None and json is None:
            raise ValueError("Must pass either mnemonic, seed, or json")
        if mnemonic is not None:
            if isinstance(mnemonic, str):
                mnemonic = mnemonic.split()
            if len(mnemonic) not in [12, 15, 18, 21, 24]:
                raise ValueError(
                    "Mnemonic has invalid size. This should be 12,15,18,21 or 24 words"
                )
            keypair = Keypair.create_from_mnemonic(
                mnemonic=" ".join(mnemonic),
                prefix=cybertensor.__chain_address_prefix__,
            )
            if not suppress:
                display_mnemonic_msg(keypair, "hotkey")
        elif seed is not None:
            raise ValueError("Not implemented")
        else:
            # json is not None
            raise ValueError("Not implemented")

        self.set_hotkey(keypair, encrypt=use_password, overwrite=overwrite)
        return self

    # Short name for regenerate_hotkey
    regen_hotkey = regenerate_hotkey
