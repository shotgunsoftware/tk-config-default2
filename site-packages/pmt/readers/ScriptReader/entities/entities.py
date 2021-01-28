# ScriptReader. Copyright 2020 Imaginary Spaces. All Rights Reserved.

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections import Counter
from typing import Iterator, Optional, Set


class PMTEntity(ABC):
    """Base class to represent PMT entities.
    Implements methods to convert a project structure to a PMT-json representation
    """

    __slots__ = ("name", "children", "parent")

    def __init__(self, name: str):
        self.name = name
        self.parent: Optional[PMTEntity] = None
        self.children: Set[PMTEntity] = set()

    @abstractmethod
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    @abstractmethod
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PMTEntity):
            # https://docs.python.org/3/library/constants.html#NotImplemented
            return NotImplemented
        # Easily check that two lists of hashable, but not sortable,
        # elements contain the same elements with collections.Counter
        return self.name == other.name and Counter(self.children) == Counter(
            other.children
        )

    @abstractmethod
    def __hash__(self) -> int:
        return hash(self.__repr__())

    @abstractmethod
    def add_child(self, child: PMTEntity) -> None:
        self.children.add(child)
        child.parent = self

    def add_children(self, children: Iterator[PMTEntity]) -> None:
        [self.add_child(child) for child in children]

    @abstractmethod
    def to_pmt_dict(self) -> dict:
        return {
            "type": self.__class__.__name__,
            "name": self.name,
            "children": [child.to_pmt_dict() for child in self.children],
        }

    def to_pmt_json(self) -> str:
        return json.dumps(self.to_pmt_dict())


class Project(PMTEntity):
    def __repr__(self) -> str:
        return super().__repr__()

    def __hash__(self) -> int:
        return super().__hash__()

    def __eq__(self, other: object) -> bool:
        if super().__eq__(other):
            if not isinstance(other, self.__class__):
                raise TypeError(
                    f"Cannot compare a {self.__class__.__name__} and a {other.__class__.__name__}"
                )
            return True
        return False

    def add_child(self, child: PMTEntity) -> None:
        super().add_child(child)

    def to_pmt_dict(self) -> dict:
        project_dict = super().to_pmt_dict()
        return project_dict


class Sequence(PMTEntity):

    __slots__ = "assets"

    def __init__(self, name: str):
        super().__init__(name)
        self.assets: Set[Asset] = set()

    def __repr__(self) -> str:
        return super().__repr__()

    def __eq__(self, other: object) -> bool:
        if super().__eq__(other):
            if not isinstance(other, self.__class__):
                raise TypeError(
                    f"Cannot compare a {self.__class__.__name__} and a {other.__class__.__name__}"
                )
            return Counter(self.assets) == Counter(other.assets)
        return False

    def __hash__(self) -> int:
        return super().__hash__() + hash(frozenset(self.assets))

    def add_child(self, child: PMTEntity) -> None:
        if isinstance(child, Asset):
            # Assets are always parented to the Project, ie the Sequence's parent.
            # Therefore, always add Sequences to the Project before adding Assets to the Sequence
            if self.parent is None:
                raise RuntimeError(
                    "Trying to add an Asset to a Sequence before the Sequence is parented to a Project"
                )
            self.parent.add_child(child)
            # Assets are also added to the Sequence.assets attribute to keep track of the casting
            self._add_asset(child)
        else:
            super().add_child(child)

    def _add_asset(self, asset: Asset) -> None:
        if not isinstance(asset, Asset):
            raise TypeError(f"Only `Asset` instances can be added as assets")
        self.assets.add(asset)

    def to_pmt_dict(self) -> dict:
        seq_dict = super().to_pmt_dict()
        seq_dict.update({"assets": [asset.name for asset in self.assets]})
        return seq_dict


class Asset(PMTEntity):

    __slots__ = "asset_type"

    def __init__(self, name: str, asset_type: str):
        super().__init__(name)
        self.asset_type = asset_type

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name} -- {self.asset_type})"

    def __eq__(self, other: object) -> bool:
        if super().__eq__(other):
            if not isinstance(other, self.__class__):
                raise TypeError(
                    f"Cannot compare a {self.__class__.__name__} and a {other.__class__.__name__}"
                )
            return self.asset_type == other.asset_type
        return False

    def __hash__(self) -> int:
        return super().__hash__() + hash(self.asset_type)

    def add_child(self, child: PMTEntity) -> None:
        raise NotImplementedError("Asset cannot have children PMTEntities")

    def to_pmt_dict(self) -> dict:
        asset_dict = super().to_pmt_dict()
        asset_dict.update(
            {
                "asset_type": self.asset_type,
            }
        )
        return asset_dict
