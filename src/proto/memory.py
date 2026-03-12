"""
memory.py -- Memory abstraction layer for declarative emulator framework.

First-class building blocks for modeling memory systems:

  MemoryRegion     -- Physical storage (the silicon)
  MemoryBank       -- Switchable window into a region (banking)
  MemoryController -- Logic governing access and bank selection
  MemoryBus        -- Address space routing (the wires)
"""

import enum
import dataclasses
from typing import (
    List, Optional, Tuple, Callable, Dict, Any, Union,
)


# ===================================================================
# Enums
# ===================================================================

class MemoryAccessLevel(enum.Enum):
    ReadOnly = "ro"
    WriteOnly = "wo"
    ReadWrite = "rw"


class HandlerType(enum.Enum):
    Python = "python"
    RawC = "raw_c"


# ===================================================================
# MemoryRegion -- Physical storage
# ===================================================================

class MemoryRegion:
    def __init__(
        self,
        name: str,
        size_in_bytes: int,
        access: MemoryAccessLevel = MemoryAccessLevel.ReadWrite,
        c_data_type: str = "uint8_t",
        comment: str = "",
    ):
        self.name = name
        self.size_in_bytes = size_in_bytes
        self.access = access
        self.c_data_type = c_data_type
        self.comment = comment or f"{name}: {size_in_bytes} bytes"

    @property
    def is_dynamic(self) -> bool:
        return self.size_in_bytes == 0

    def __repr__(self) -> str:
        return (f"MemoryRegion({self.name!r}, {self.size_in_bytes} bytes, "
                f"access={self.access.value})")


# ===================================================================
# MemoryBank -- Switchable window into a region
# ===================================================================

class MemoryBank:
    def __init__(
        self,
        name: str,
        region: MemoryRegion,
        bank_size: int,
        max_banks: int = 256,
        default_bank: int = 0,
        comment: str = "",
    ):
        self.name = name
        self.region = region
        self.bank_size = bank_size
        self.max_banks = max_banks
        self.default_bank = default_bank
        self.comment = comment or f"{name}: {bank_size} bytes x {max_banks} banks"

    def __repr__(self) -> str:
        return (f"MemoryBank({self.name!r}, region={self.region.name!r}, "
                f"bank_size=0x{self.bank_size:X}, max_banks={self.max_banks})")


# ===================================================================
# Handler -- A piece of logic (Python or raw C)
# ===================================================================

@dataclasses.dataclass
class Handler:
    handler_type: HandlerType
    func: Optional[Callable] = None
    code: Optional[str] = None
    addr_start: Optional[int] = None
    addr_end: Optional[int] = None

    def __repr__(self) -> str:
        if self.handler_type == HandlerType.Python:
            name = self.func.__name__ if self.func else "?"
            return f"Handler(Python, {name})"
        else:
            preview = (self.code or "")[:40]
            return f"Handler(RawC, {preview!r}...)"


# ===================================================================
# MemoryController -- Banking and access logic
# ===================================================================

class MemoryController:
    def __init__(
        self,
        name: str,
        controls: Optional[List[MemoryBank]] = None,
    ):
        self.name = name
        self.controls = controls or []
        self.state_fields: List[Tuple[str, str, str, str]] = []
        self.write_handlers: List[Handler] = []
        # FIX: bank resolvers now receive (ctrl, addr)
        self.bank_resolvers: Dict[str, Handler] = {}
        self.access_guards: Dict[Tuple[str, str], Handler] = {}

    def add_state(self, name: str, c_type: str = "uint8_t",
                  default: str = "0", comment: str = ""):
        self.state_fields.append((name, c_type, default, comment))

    def on_write(self, addr_start: int, addr_end: int):
        """Decorator: register a write handler for an address range.
        Handler signature: (ctrl, val, addr)"""
        def decorator(func):
            handler = Handler(
                handler_type=HandlerType.Python,
                func=func,
                addr_start=addr_start,
                addr_end=addr_end,
            )
            self.write_handlers.append(handler)
            return func
        return decorator

    def add_write_handler_raw(self, addr_start: int, addr_end: int, code: str):
        handler = Handler(
            handler_type=HandlerType.RawC, code=code,
            addr_start=addr_start, addr_end=addr_end,
        )
        self.write_handlers.append(handler)

    def bank_resolver(self, bank: MemoryBank):
        """Decorator: register a bank resolver.
        FIX: signature is now (ctrl, addr) -- addr is the full bus address.
        For 16-bit systems, addr is uint16_t. For 24-bit, uint32_t.
        The resolver returns the bank index."""
        def decorator(func):
            handler = Handler(handler_type=HandlerType.Python, func=func)
            self.bank_resolvers[bank.name] = handler
            return func
        return decorator

    def set_bank_resolver_raw(self, bank: MemoryBank, code: str):
        self.bank_resolvers[bank.name] = Handler(
            handler_type=HandlerType.RawC, code=code)

    def read_guard(self, bank: MemoryBank):
        """Decorator: returns whether reads to this bank are allowed."""
        def decorator(func):
            handler = Handler(handler_type=HandlerType.Python, func=func)
            self.access_guards[(bank.name, "read")] = handler
            return func
        return decorator

    def write_guard(self, bank: MemoryBank):
        """Decorator: returns whether writes to this bank are allowed."""
        def decorator(func):
            handler = Handler(handler_type=HandlerType.Python, func=func)
            self.access_guards[(bank.name, "write")] = handler
            return func
        return decorator

    def add_read_guard_raw(self, bank: MemoryBank, code: str):
        self.access_guards[(bank.name, "read")] = Handler(
            handler_type=HandlerType.RawC, code=code)

    def add_write_guard_raw(self, bank: MemoryBank, code: str):
        self.access_guards[(bank.name, "write")] = Handler(
            handler_type=HandlerType.RawC, code=code)

    def __repr__(self) -> str:
        bank_names = [b.name for b in self.controls]
        return (f"MemoryController({self.name!r}, controls={bank_names})")


# ===================================================================
# Bus mapping entries
# ===================================================================

@dataclasses.dataclass
class BusMapping:
    addr_start: int
    addr_end: int
    comment: str = ""
    region: Optional[MemoryRegion] = None
    offset: int = 0
    fixed: bool = False
    bank: Optional[MemoryBank] = None
    controller: Optional[MemoryController] = None
    handler: Optional[Any] = None
    access_cycles: int = 0
    write_only: bool = False

    # For write-side side effects on region writes (e.g. vram_dirty flag)
    on_write_side_effect: Optional[str] = None

    def __repr__(self) -> str:
        target = "?"
        if self.region:
            target = f"region={self.region.name}"
        elif self.bank:
            target = f"bank={self.bank.name}"
        elif self.handler:
            target = f"handler={self.handler}"
        return (f"BusMapping(0x{self.addr_start:04X}-0x{self.addr_end:04X}, "
                f"{target})")


@dataclasses.dataclass
class BusOverlay:
    addr_start: int
    addr_end: int
    region: MemoryRegion
    comment: str = ""
    disable_on_write: Optional[Tuple[int, str]] = None
    state_field: str = ""

    def __post_init__(self):
        if not self.state_field:
            self.state_field = f"{self.region.name}_overlay_enabled"


# ===================================================================
# MemoryBus -- Address space routing
# ===================================================================

@dataclasses.dataclass
class BusMaster:
    """A device that can drive the bus (CPU, DMA controller, etc.)."""
    chip_name: str
    priority: int = 0
    comment: str = ""


class MemoryBus:
    def __init__(self, name: str, address_bits: int = 16):
        self.name = name
        self.address_bits = address_bits
        self.address_space = 1 << address_bits
        self.mappings: List[BusMapping] = []
        self.write_mappings: List[BusMapping] = []
        self.overlays: List[BusOverlay] = []
        self.fallback_read: Union[int, str] = 0xFF
        self.fallback_write: Optional[str] = None
        self.masters: List[BusMaster] = []

    @property
    def addr_type(self) -> str:
        """C type for addresses on this bus."""
        if self.address_bits <= 16:
            return "uint16_t"
        return "uint32_t"

    def map(
        self,
        addr_start: int,
        addr_end: int,
        region: Optional[MemoryRegion] = None,
        bank: Optional[MemoryBank] = None,
        controller: Optional[MemoryController] = None,
        handler: Optional[Any] = None,
        offset: int = 0,
        fixed: bool = False,
        access_cycles: int = 0,
        on_write_side_effect: Optional[str] = None,
        comment: str = "",
    ):
        mapping = BusMapping(
            addr_start=addr_start, addr_end=addr_end,
            region=region, bank=bank, controller=controller,
            handler=handler, offset=offset, fixed=fixed,
            access_cycles=access_cycles,
            on_write_side_effect=on_write_side_effect,
            comment=comment,
        )
        self.mappings.append(mapping)

    def map_writes(
        self,
        addr_start: int,
        addr_end: int,
        controller: Optional[MemoryController] = None,
        handler: Optional[Any] = None,
        comment: str = "",
    ):
        mapping = BusMapping(
            addr_start=addr_start, addr_end=addr_end,
            controller=controller, handler=handler,
            write_only=True, comment=comment,
        )
        self.write_mappings.append(mapping)

    def overlay(
        self,
        addr_start: int,
        addr_end: int,
        region: MemoryRegion,
        disable_on_write: Optional[Tuple[int, str]] = None,
        comment: str = "",
    ):
        ov = BusOverlay(
            addr_start=addr_start, addr_end=addr_end,
            region=region, disable_on_write=disable_on_write,
            comment=comment,
        )
        self.overlays.append(ov)

    def set_fallback(self, read: Union[int, str] = 0xFF,
                     write: Optional[str] = None):
        self.fallback_read = read
        self.fallback_write = write

    def add_master(self, chip_name: str, priority: int = 0,
                   comment: str = ""):
        """Register a bus master. Higher priority wins arbitration."""
        self.masters.append(BusMaster(
            chip_name=chip_name, priority=priority, comment=comment))

    def __repr__(self) -> str:
        return (f"MemoryBus({self.name!r}, {self.address_bits}-bit, "
                f"{len(self.mappings)} mappings)")
