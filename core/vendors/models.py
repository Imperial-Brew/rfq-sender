from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any


@dataclass
class Contact:
    name: str = ""
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    type: str = ""
    state: str = ""
    primary: bool = False
    website: str = ""
    title: str = ""

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Vendor:
    id: str = ""
    name: str = ""
    processes: List[str] = field(default_factory=list)
    contacts: List[Contact] = field(default_factory=list)
    address: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    rating: int = 0
    active: bool = True

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["contacts"] = [c.to_dict() for c in self.contacts]
        return data
