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

import base64
import hashlib
from typing import Optional, Union

from bech32 import (  # pylint: disable=wrong-import-order
    bech32_encode,
    convertbits,
)
from bip39 import bip39_generate, bip39_validate
from ecdsa import (  # type: ignore # pylint: disable=wrong-import-order
    SECP256k1,
    SigningKey,
    VerifyingKey,
)
from cosmpy.crypto.address import Address
from cosmpy.crypto.hashfuncs import ripemd160
from cosmpy.crypto.keypairs import PrivateKey, PublicKey
from cosmpy.mnemonic import (
    derive_child_key_from_mnemonic,
    COSMOS_HD_PATH,
    validate_mnemonic_and_normalise,
)

import cybertensor as ct
from cybertensor import __chain_address_prefix__
from cybertensor.errors import ConfigurationError


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

        if isinstance(public_key, str):
            self.public_key = public_key
        else:
            self.public_key: str = public_key.decode("utf-8")

        if not self.public_key:
            raise ValueError("No public key provided")

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

    def get_address_from_public_key(self, public_key: str) -> str:
        """
        Get the address from the public key.

        :param public_key: the public key
        :return: str
        """
        public_key_bytes = bytes.fromhex(public_key)
        s = hashlib.new("sha256", public_key_bytes).digest()
        r = ripemd160(s)
        five_bit_r = convertbits(r, 8, 5)
        if five_bit_r is None:  # pragma: nocover
            raise TypeError("Unsuccessful bech32.convertbits call")

        ## TODO add configuration for chain prefix
        address = bech32_encode(__chain_address_prefix__, five_bit_r)
        return address

    def recover_message(self, message: bytes, signature: str) -> tuple[Address, ...]:
        public_keys = self.recover_public_keys_from_message(message, signature)
        addresses = [
            self.get_address_from_public_key(public_key) for public_key in public_keys
        ]
        return tuple(addresses)

    def recover_public_keys_from_message(self, message: bytes, signature: str) -> tuple[str, ...]:
        signature_b64 = base64.b64decode(signature)
        verifying_keys = VerifyingKey.from_public_key_recovery(
            signature_b64,
            message,
            SECP256k1,
            hashfunc=hashlib.sha256,
        )
        public_keys = [
            verifying_key.to_string("compressed").hex()
            for verifying_key in verifying_keys
        ]
        return tuple(public_keys)

    def sign(self, data: Union[bytes, str]) -> bytes:
        """
        Creates a signature for given data

        Parameters
        ----------
        data: data to sign in bytes or hex string format

        Returns
        -------
        signature in bytes

        """
        if data[0:2] == '0x':
            data = bytes.fromhex(data[2:])
        elif type(data) is str:
            data = data.encode()
        elif type(data) is not bytes:
            raise TypeError(f"Signed data should be of type bytes or hex-string, given data type is {type(data)}")

        if not self.private_key:
            raise ConfigurationError("No private key set to create signatures")

        signature_compact = PrivateKey(self.private_key).sign(message=data, deterministic=True)
        signature_base64_str = base64.b64encode(signature_compact).decode("utf-8").encode()

        return signature_base64_str

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
        elif type(data) is not bytes:
            raise TypeError(f"Signed data should be of type bytes or hex-string, given data type is {type(data)}")

        if type(signature) is str and signature[0:2] == "0x":
            signature = bytes.fromhex(signature[2:])

        for address in self.recover_message(message=data, signature=signature):
            if self.address == address:
                return True
        return False

    def __repr__(self):
        if self.address:
            return f"<Keypair (address={self.address})>"
        else:
            return f"<Keypair (public_key={self.public_key})>"
