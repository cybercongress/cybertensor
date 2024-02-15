# The MIT License (MIT)
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

from typing import Optional, Union

from bip39 import bip39_generate, bip39_validate
from cosmpy.crypto.address import Address
from cosmpy.crypto.keypairs import PrivateKey, PublicKey
from cosmpy.mnemonic import (
    derive_child_key_from_mnemonic,
    COSMOS_HD_PATH,
    validate_mnemonic_and_normalise,
)

from cybertensor import __chain_address_prefix__


class Keypair:
    def __init__(
        self,
        address: str = None,
        public_key: Union[bytes, str] = None,
        private_key: Union[bytes, str] = None,
        prefix: Optional[str] = None,
    ):
        """
        Allows generation of Keypairs from a variety of input combination, such as a public/private key combination,
        mnemonic or URI containing soft and hard derivation paths. With these Keypairs data can be signed and verified

        Parameters
        ----------
        public_key: hex string or bytes of public_key key
        private_key: hex string or bytes of private key
        prefix: prefix, defaults to None
        """

        if prefix is None:
            prefix = __chain_address_prefix__

        self.prefix = prefix

        if private_key:
            if type(private_key) is str:
                private_key = bytes.fromhex(private_key.replace("0x", ""))

            private_key_obj = PrivateKey(private_key)
            public_key = private_key_obj.public_key.public_key
            address = Address(PublicKey(private_key_obj.public_key), prefix).__str__()

        if not public_key:
            raise ValueError("No public key provided")

        self.public_key: bytes = public_key

        self.address: str = address

        self.private_key: bytes = private_key

        self.mnemonic = None

    @classmethod
    def generate_mnemonic(cls, words: int = 12) -> str:
        """
        Generates a new seed phrase with given amount of words (default 12)

        Parameters
        ----------
        words: The amount of words to generate, valid values are 12, 15, 18, 21 and 24

        Returns
        -------
        str: Seed phrase
        """
        return bip39_generate(words, "en")

    @classmethod
    def validate_mnemonic(cls, mnemonic: str) -> bool:
        """
        Verify if specified mnemonic is valid

        Parameters
        ----------
        mnemonic: Seed phrase

        Returns
        -------
        bool
        """
        return bip39_validate(mnemonic, "en")

    @classmethod
    def create_from_mnemonic(
        cls, mnemonic: str, prefix: Optional[str] = None
    ) -> "Keypair":
        """
        Create a Keypair for given mnemonic

        Parameters
        ----------
        mnemonic: Seed phrase
        prefix: prefix, defaults to None

        Returns
        -------
        Keypair
        """

        if prefix is None:
            prefix = __chain_address_prefix__

        mnemonic = validate_mnemonic_and_normalise(mnemonic)

        private_key = derive_child_key_from_mnemonic(mnemonic, path=COSMOS_HD_PATH)

        keypair = cls.create_from_private_key(private_key, prefix=prefix)

        keypair.mnemonic = mnemonic

        return keypair

    @classmethod
    def create_from_private_key(
        cls, private_key: Union[bytes, str], prefix: Optional[str] = None
    ) -> "Keypair":
        """
        Creates Keypair for specified public/private keys
        Parameters
        ----------
        private_key: hex string or bytes of private key
        prefix: prefix, defaults to None

        Returns
        -------
        Keypair
        """

        if prefix is None:
            prefix = __chain_address_prefix__

        return cls(
            public_key=PrivateKey(private_key).public_key.public_key,
            private_key=private_key,
            prefix=prefix,
        )

    def verify(self, data: Union[bytes, str], signature: Union[bytes, str]) -> bool:
        """
        Verifies data with specified signature

        Parameters
        ----------
        data: data to be verified in bytes or hex string format
        signature: signature in bytes or hex string format

        Returns
        -------
        True if data is signed with this Keypair, otherwise False
        """

        if data[0:2] == "0x":
            data = bytes.fromhex(data[2:])
        elif type(data) is str:
            data = data.encode()

        if type(signature) is str and signature[0:2] == "0x":
            signature = bytes.fromhex(signature[2:])

        if type(signature) is not bytes:
            raise TypeError("Signature should be of type bytes or a hex-string")

        # TODO replace verify function to correct
        verified = True
        # verified = crypto_verify_fn(signature, data, self.public_key)
        #
        # if not verified:
        #     verified = crypto_verify_fn(signature, b'<Bytes>' + data + b'</Bytes>', self.public_key)
        #
        return verified

    def __repr__(self):
        if self.address:
            return f"<Keypair (address={self.address})>"
        else:
            return f"<Keypair (public_key={self.public_key})>"
