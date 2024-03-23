# The MIT License (MIT)
# Copyright © 2021-2022 Yuma Rao
# Copyright © 2022 Opentensor Foundation
# Copyright © 2023 Opentensor Technologies Inc
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

from typing import Union

from cosmpy.aerial.client import Coin

from cybertensor import __giga_boot_symbol__, __boot_symbol__


class Balance:
    """
    Represents the cybertensor balance of the wallet, stored as boot (int).
    This class provides a way to interact with balances in two different units: boot and gboot.
    It provides methods to convert between these units, as well as to perform arithmetic and comparison operations.

    Attributes:
        unit: A string representing the symbol for the gboot unit.
        boot_unit: A string representing the symbol for the boot unit.
        boot: An integer that stores the balance in boot units.
        gboot: A float property that gives the balance in gboot units.
    """

    unit: str = __giga_boot_symbol__  # This is the gboot unit
    boot_unit: str = __boot_symbol__  # This is the boot unit
    boot: int
    gboot: float

    def __init__(self, balance: Union[int, float, Coin, list[Coin]]):
        """
        Initialize a Balance object. If balance is an int, it's assumed to be in boot.
        If balance is a float, it's assumed to be in gboot.
        If balance is a cosmpy.aerial.client.Coin, the amount of boot is retrieved.
        If balance is a list of cosmpy.aerial.client.Coin, the amount of boot is retrieved.

        Args:
            balance: The initial balance, in either boot (if an int, cosmpy.aerial.client.Coin, list of Coin),
            or gboot (if a float).
        """
        if isinstance(balance, int):
            self.boot = balance
        elif isinstance(balance, float):
            # Assume gboot value for the float
            self.boot = int(balance * pow(10, 9))
        elif isinstance(balance, Coin):
            self.boot = (
                int(balance.amount) if balance.denom == Balance.boot_unit.lower() else 0
            )
        elif isinstance(balance, list):
            self.boot = 0
            for _coin in balance:
                assert isinstance(_coin, Coin)
                if _coin.denom == Balance.boot_unit.lower():
                    self.boot = int(_coin.amount)
                    break
        else:
            raise TypeError(
                f"balance must be an int ({self.boot_unit}), a float ({self.unit}), "
                f"cosmpy.aerial.client.Coin, or list of cosmpy.aerial.client.Coin"
            )

    @property
    def gboot(self):
        return self.boot / pow(10, 9)

    def __int__(self):
        """
        Convert the Balance object to an int. The resulting value is in boot.
        """
        return self.boot

    def __float__(self):
        """
        Convert the Balance object to a float. The resulting value is in gboot.
        """
        return self.gboot

    def __str__(self):
        """
        Returns the Balance object as a string in the format "symbolvalue", where the value is in gboot.
        """
        return f"{self.unit}{float(self.gboot):,.9f}"

    def __rich__(self):
        return "[green]{}[/green][green]{}[/green][green].[/green][dim green]{}[/dim green]".format(
            self.unit,
            format(float(self.gboot), "f").split(".")[0],
            format(float(self.gboot), "f").split(".")[1],
        )

    def __str_boot__(self):
        return f"{self.boot_unit}{int(self.boot)}"

    def __rich_boot__(self):
        return f"[green]{self.boot_unit}{int(self.boot)}[/green]"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other: Union[int, float, "Balance"]):
        if other is None:
            return False

        if hasattr(other, "boot"):
            return self.boot == other.boot
        else:
            try:
                # Attempt to cast to int from boot
                other_boot = int(other)
                return self.boot == other_boot
            except (TypeError, ValueError):
                raise NotImplementedError("Unsupported type")

    def __ne__(self, other: Union[int, float, "Balance"]):
        return not self == other

    def __gt__(self, other: Union[int, float, "Balance"]):
        if hasattr(other, "boot"):
            return self.boot > other.boot
        else:
            try:
                # Attempt to cast to int from boot
                other_boot = int(other)
                return self.boot > other_boot
            except ValueError:
                raise NotImplementedError("Unsupported type")

    def __lt__(self, other: Union[int, float, "Balance"]):
        if hasattr(other, "boot"):
            return self.boot < other.boot
        else:
            try:
                # Attempt to cast to int from boot
                other_boot = int(other)
                return self.boot < other_boot
            except ValueError:
                raise NotImplementedError("Unsupported type")

    def __le__(self, other: Union[int, float, "Balance"]):
        try:
            return self < other or self == other
        except TypeError:
            raise NotImplementedError("Unsupported type")

    def __ge__(self, other: Union[int, float, "Balance"]):
        try:
            return self > other or self == other
        except TypeError:
            raise NotImplementedError("Unsupported type")

    def __add__(self, other: Union[int, float, "Balance"]):
        if hasattr(other, "boot"):
            return Balance.from_boot(int(self.boot + other.boot))
        else:
            try:
                # Attempt to cast to int from boot
                return Balance.from_boot(int(self.boot + other))
            except (ValueError, TypeError):
                raise NotImplementedError("Unsupported type")

    def __radd__(self, other: Union[int, float, "Balance"]):
        try:
            return self + other
        except TypeError:
            raise NotImplementedError("Unsupported type")

    def __sub__(self, other: Union[int, float, "Balance"]):
        try:
            return self + -other
        except TypeError:
            raise NotImplementedError("Unsupported type")

    def __rsub__(self, other: Union[int, float, "Balance"]):
        try:
            return -self + other
        except TypeError:
            raise NotImplementedError("Unsupported type")

    def __mul__(self, other: Union[int, float, "Balance"]):
        if hasattr(other, "boot"):
            return Balance.from_boot(int(self.boot * other.boot))
        else:
            try:
                # Attempt to cast to int from boot
                return Balance.from_boot(int(self.boot * other))
            except (ValueError, TypeError):
                raise NotImplementedError("Unsupported type")

    def __rmul__(self, other: Union[int, float, "Balance"]):
        return self * other

    def __truediv__(self, other: Union[int, float, "Balance"]):
        if hasattr(other, "boot"):
            return Balance.from_boot(int(self.boot / other.boot))
        else:
            try:
                # Attempt to cast to int from boot
                return Balance.from_boot(int(self.boot / other))
            except (ValueError, TypeError):
                raise NotImplementedError("Unsupported type")

    def __rtruediv__(self, other: Union[int, float, "Balance"]):
        if hasattr(other, "boot"):
            return Balance.from_boot(int(other.boot / self.boot))
        else:
            try:
                # Attempt to cast to int from boot
                return Balance.from_boot(int(other / self.boot))
            except (ValueError, TypeError):
                raise NotImplementedError("Unsupported type")

    def __floordiv__(self, other: Union[int, float, "Balance"]):
        if hasattr(other, "boot"):
            return Balance.from_boot(int(self.gboot // other.gboot))
        else:
            try:
                # Attempt to cast to int from boot
                return Balance.from_boot(int(self.boot // other))
            except (ValueError, TypeError):
                raise NotImplementedError("Unsupported type")

    def __rfloordiv__(self, other: Union[int, float, "Balance"]):
        if hasattr(other, "boot"):
            return Balance.from_boot(int(other.boot // self.boot))
        else:
            try:
                # Attempt to cast to int from boot
                return Balance.from_boot(int(other // self.boot))
            except (ValueError, TypeError):
                raise NotImplementedError("Unsupported type")

    def __int__(self) -> int:
        return self.boot

    def __float__(self) -> float:
        return self.gboot

    def __list__(self) -> list:
        return [Coin(amount=self.boot, denom=Balance.boot_unit.lower())]

    def __nonzero__(self) -> bool:
        return bool(self.boot)

    def __neg__(self):
        return Balance.from_boot(-self.boot)

    def __pos__(self):
        return Balance.from_boot(self.boot)

    def __abs__(self):
        return Balance.from_boot(abs(self.boot))

    @staticmethod
    def from_float(amount: float):
        """
        Given gboot (float), return Balance object with boot(int) and gboot(float), where boot = int(gboot*pow(10,9))
        Args:
            amount: The amount in gboot.

        Returns:
            A Balance object representing the given amount.
        """
        boot = int(amount * pow(10, 9))
        return Balance(boot)

    @staticmethod
    def from_gboot(amount: float):
        """
        Given gboot (float), return Balance object with boot(int) and gboot(float), where boot = int(gboot*pow(10,9))

        Args:
            amount: The amount in gboot.

        Returns:
            A Balance object representing the given amount.
        """
        boot = int(amount * pow(10, 9))
        return Balance(boot)

    @staticmethod
    def from_boot(amount: int):
        """
        Given boot (int), return Balance object with boot(int) and gboot(float), where boot = int(gboot*pow(10,9))

        Args:
            amount: The amount in boot.

        Returns:
            A Balance object representing the given amount.
        """
        return Balance(amount)

    @staticmethod
    def from_coin(coin: Coin):
        """
        Given coin (cosmpy.aerial.client.Coin), return Balance object with boot(int) and gboot(float),
        where boot = int(gboot*pow(10,9))

        Args:
            coin: The Coin item.

        Returns:
            A Balance object representing the given coin item.
        """
        return Balance(coin)
