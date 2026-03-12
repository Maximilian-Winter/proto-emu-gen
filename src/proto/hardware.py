"""
hardware.py -- Hardware abstraction layer for declarative emulator framework.

  Clock         -- Timing source with frequency derivation
  SignalLine    -- Wires between chips (interrupts, resets, control)
  Port          -- Latched bidirectional communication channels
  Chip          -- Physical IC package (the universal container)
  Board         -- Complete system (the PCB)
"""

import enum
import dataclasses
from typing import (
    List, Optional, Tuple, Callable, Dict, Any, Union,
)

from .memory import (
    MemoryRegion, MemoryBank, MemoryBus, MemoryController,
    Handler, HandlerType,
)


# ===================================================================
# Clock
# ===================================================================

class Clock:
    def __init__(self, name: str, frequency_hz: int,
                 parent: Optional['Clock'] = None,
                 divider: int = 1, multiplier: int = 1,
                 comment: str = ""):
        self.name = name
        self.frequency_hz = frequency_hz
        self.parent = parent
        self.divider = divider
        self.multiplier = multiplier
        self.comment = comment
        self.children: List['Clock'] = []

    def derive(self, name: str, divider: int = 1,
               multiplier: int = 1, comment: str = "") -> 'Clock':
        freq = (self.frequency_hz * multiplier) // divider
        child = Clock(name=name, frequency_hz=freq, parent=self,
                      divider=divider, multiplier=multiplier, comment=comment)
        self.children.append(child)
        return child

    @property
    def master_divider(self) -> int:
        if self.parent is None:
            return 1
        return self.divider * self.parent.master_divider

    @property
    def is_master(self) -> bool:
        return self.parent is None

    def cycles_per(self, other: 'Clock') -> float:
        if self.frequency_hz == 0 or other.frequency_hz == 0:
            return 0.0
        return self.frequency_hz / other.frequency_hz

    def __repr__(self) -> str:
        if self.parent:
            return (f"Clock({self.name!r}, {self.frequency_hz:,} Hz, "
                    f"/{self.divider})")
        return f"Clock({self.name!r}, {self.frequency_hz:,} Hz, master)"


# ===================================================================
# Signal types and lines
# ===================================================================

class SignalType(enum.Enum):
    Interrupt = "irq"
    NonMaskableInterrupt = "nmi"
    Reset = "reset"
    Custom = "custom"


class SignalEdge(enum.Enum):
    RisingEdge = "rising"
    FallingEdge = "falling"
    Level = "level"


class SignalLine:
    def __init__(self, name: str, signal_type: SignalType,
                 source: Optional['Chip'] = None,
                 sources: Optional[List['Chip']] = None,
                 sinks: Optional[List['Chip']] = None,
                 edge: SignalEdge = SignalEdge.Level,
                 active_low: bool = False, comment: str = ""):
        self.name = name
        self.signal_type = signal_type
        self.edge = edge
        self.active_low = active_low
        self.comment = comment
        if sources:
            self.sources = sources
        elif source:
            self.sources = [source]
        else:
            self.sources = []
        self.sinks = sinks or []
        self.on_assert_handlers: Dict[str, Handler] = {}

    def on_assert(self, sink_chip: 'Chip'):
        def decorator(func):
            handler = Handler(handler_type=HandlerType.Python, func=func)
            self.on_assert_handlers[sink_chip.name] = handler
            return func
        return decorator

    def set_on_assert_raw(self, sink_chip: 'Chip', code: str):
        self.on_assert_handlers[sink_chip.name] = Handler(
            handler_type=HandlerType.RawC, code=code)

    def __repr__(self) -> str:
        src = [s.name for s in self.sources]
        snk = [s.name for s in self.sinks]
        return f"SignalLine({self.name!r}, {src} -> {snk})"


# ===================================================================
# Port -- latched bidirectional communication
# ===================================================================

@dataclasses.dataclass
class PortSide:
    chip: Optional['Chip'] = None
    addr_start: Optional[int] = None
    addr_end: Optional[int] = None

    @property
    def width(self) -> int:
        if self.addr_start is not None and self.addr_end is not None:
            return self.addr_end - self.addr_start + 1
        return 0


class PortLatching(enum.Enum):
    Independent = "independent"
    Shared = "shared"


class Port:
    def __init__(self, name: str,
                 side_a: Optional[PortSide] = None,
                 side_b: Optional[PortSide] = None,
                 latching: PortLatching = PortLatching.Independent,
                 comment: str = ""):
        self.name = name
        self.side_a = side_a
        self.side_b = side_b
        self.latching = latching
        self.comment = comment

    @property
    def width(self) -> int:
        if self.side_a:
            return self.side_a.width
        if self.side_b:
            return self.side_b.width
        return 0

    def __repr__(self) -> str:
        a = self.side_a.chip.name if self.side_a and self.side_a.chip else "?"
        b = self.side_b.chip.name if self.side_b and self.side_b.chip else "?"
        return f"Port({self.name!r}, {a} <-> {b}, width={self.width})"


# ===================================================================
# RegisterBlock -- memory-mapped I/O
# ===================================================================

@dataclasses.dataclass
class RegisterEntry:
    index: int
    name: str = ""
    read_handler: Optional[Handler] = None
    write_handler: Optional[Handler] = None
    read_only: bool = False
    write_only: bool = False
    write_mask: Optional[Tuple[int, int]] = None
    default: str = "0"
    comment: str = ""


class RegisterBlock:
    def __init__(self, name: str, base_addr: int, size: int,
                 comment: str = ""):
        self.name = name
        self.base_addr = base_addr
        self.size = size
        self.comment = comment
        self.registers: Dict[int, RegisterEntry] = {}

    def bind(self, index: int, name: str, default: str = "0",
             read_only: bool = False, write_only: bool = False,
             write_mask: Optional[Tuple[int, int]] = None,
             comment: str = ""):
        self.registers[index] = RegisterEntry(
            index=index, name=name, default=default,
            read_only=read_only, write_only=write_only,
            write_mask=write_mask, comment=comment,
        )

    def on_write(self, index: int):
        def decorator(func):
            if index not in self.registers:
                self.registers[index] = RegisterEntry(index=index)
            self.registers[index].write_handler = Handler(
                handler_type=HandlerType.Python, func=func)
            return func
        return decorator

    def on_read(self, index: int):
        def decorator(func):
            if index not in self.registers:
                self.registers[index] = RegisterEntry(index=index)
            self.registers[index].read_handler = Handler(
                handler_type=HandlerType.Python, func=func)
            return func
        return decorator

    def set_write_handler_raw(self, index: int, code: str):
        if index not in self.registers:
            self.registers[index] = RegisterEntry(index=index)
        self.registers[index].write_handler = Handler(
            handler_type=HandlerType.RawC, code=code)

    def set_read_handler_raw(self, index: int, code: str):
        if index not in self.registers:
            self.registers[index] = RegisterEntry(index=index)
        self.registers[index].read_handler = Handler(
            handler_type=HandlerType.RawC, code=code)

    @property
    def addr_end(self) -> int:
        return self.base_addr + self.size - 1

    def __repr__(self) -> str:
        return (f"RegisterBlock({self.name!r}, "
                f"0x{self.base_addr:04X}-0x{self.addr_end:04X})")


# ===================================================================
# DMAChannel
# ===================================================================

class DMAMode(enum.Enum):
    OneShot = "oneshot"
    HBlank = "hblank"
    Cycle = "cycle"


class DMAChannel:
    def __init__(self, name: str, mode: DMAMode = DMAMode.OneShot,
                 channels: int = 1, comment: str = ""):
        self.name = name
        self.mode = mode
        self.channels = channels
        self.comment = comment
        self.state_fields: List[Tuple[str, str, str, str]] = []
        self.transfer_handler: Optional[Handler] = None

    def add_state(self, name: str, c_type: str = "uint8_t",
                  default: str = "0", comment: str = ""):
        self.state_fields.append((name, c_type, default, comment))

    def transfer(self):
        """Decorator: register per-unit transfer handler."""
        def decorator(func):
            self.transfer_handler = Handler(
                handler_type=HandlerType.Python, func=func)
            return func
        return decorator

    def set_transfer_raw(self, code: str):
        """Register raw C transfer handler."""
        self.transfer_handler = Handler(
            handler_type=HandlerType.RawC, code=code)


# ===================================================================
# Chip -- Physical IC package
# ===================================================================

class Chip:
    def __init__(self, name: str, clock: Optional[Clock] = None,
                 comment: str = ""):
        self.name = name
        self.clock = clock
        self.comment = comment
        self.state_fields: List[Tuple[str, str, str, str]] = []
        self.cpu_core: Optional[Any] = None
        self.internal_memory: List[MemoryRegion] = []
        self.memory_controllers: List[MemoryController] = []
        self.register_blocks: List[RegisterBlock] = []
        self.dma_channels: List[DMAChannel] = []
        self.helpers: List[Dict[str, Any]] = []
        self.tick_handler: Optional[Handler] = None
        self.init_handler: Optional[Handler] = None
        # FIX: chip knows which bus it talks to
        self.bus: Optional[MemoryBus] = None
        self.step_preamble: Optional[str] = None  # raw C before opcode fetch
        self.step_preamble_handler: Optional[Handler] = None  # Python handler alternative

    def add_state(self, name: str, c_type: str = "uint8_t",
                  default: str = "0", comment: str = ""):
        self.state_fields.append((name, c_type, default, comment))

    def set_cpu_core(self, cpu_definition):
        self.cpu_core = cpu_definition

    @property
    def has_cpu(self) -> bool:
        return self.cpu_core is not None

    def set_bus(self, bus: MemoryBus):
        """Associate this chip with a memory bus.
        Each CPU chip needs a bus for mem_read/mem_write generation."""
        self.bus = bus

    def set_step_preamble(self, code: Optional[str] = None,
                          func: Optional[Callable] = None):
        """Code inserted at top of cpu_step(), before opcode fetch.
        Use code= for raw C, or func= for a Python function to transpile."""
        if func:
            self.step_preamble_handler = Handler(
                handler_type=HandlerType.Python, func=func)
            self.step_preamble = None
        elif code:
            self.step_preamble = code
            self.step_preamble_handler = None

    def step_preamble_decorator(self):
        """Decorator: register a transpiled step preamble function."""
        def decorator(func):
            self.set_step_preamble(func=func)
            return func
        return decorator

    def add_internal_memory(self, region: MemoryRegion):
        self.internal_memory.append(region)

    def add_memory_controller(self, controller: MemoryController):
        self.memory_controllers.append(controller)

    def add_register_block(self, block: RegisterBlock):
        self.register_blocks.append(block)

    def add_dma(self, channel: DMAChannel):
        self.dma_channels.append(channel)

    def add_helper(self, name: str, func: Optional[Callable] = None,
                   code: Optional[str] = None, returns: str = "void",
                   params: Optional[List[Tuple[str, str]]] = None,
                   comment: str = ""):
        handler_type = HandlerType.Python if func else HandlerType.RawC
        self.helpers.append({
            'name': name,
            'handler': Handler(handler_type=handler_type, func=func, code=code),
            'returns': returns,
            'params': params or [],
            'comment': comment,
        })

    def helper(self, name: str, returns: str = "void",
               params: Optional[List[Tuple[str, str]]] = None):
        def decorator(func):
            self.add_helper(name, func=func, returns=returns, params=params)
            return func
        return decorator

    def set_tick(self, func: Optional[Callable] = None,
                 code: Optional[str] = None):
        if func:
            self.tick_handler = Handler(handler_type=HandlerType.Python, func=func)
        elif code:
            self.tick_handler = Handler(handler_type=HandlerType.RawC, code=code)

    def tick(self):
        def decorator(func):
            self.set_tick(func=func)
            return func
        return decorator

    def set_init(self, func: Optional[Callable] = None,
                 code: Optional[str] = None):
        if func:
            self.init_handler = Handler(handler_type=HandlerType.Python, func=func)
        elif code:
            self.init_handler = Handler(handler_type=HandlerType.RawC, code=code)

    def __repr__(self) -> str:
        parts = [f"Chip({self.name!r}"]
        if self.clock:
            parts.append(f"clock={self.clock.name}")
        if self.has_cpu:
            parts.append("cpu=True")
        return ', '.join(parts) + ')'


# ===================================================================
# Board -- The complete system (the PCB)
# ===================================================================

class Board:
    def __init__(self, name: str, comment: str = "",
                 cycle_accurate: bool = False):
        self.name = name
        self.comment = comment
        self.cycle_accurate = cycle_accurate
        self.master_clock: Optional[Clock] = None
        self.chips: List[Chip] = []
        self.buses: List[MemoryBus] = []
        self.ports: List[Port] = []
        self.signals: List[SignalLine] = []
        self.extern_funcs: List = []

    def set_master_clock(self, clock: Clock):
        self.master_clock = clock

    def add_chip(self, chip: Chip):
        self.chips.append(chip)

    def get_chip(self, name: str) -> Optional[Chip]:
        for chip in self.chips:
            if chip.name == name:
                return chip
        return None

    def add_bus(self, bus: MemoryBus):
        self.buses.append(bus)

    def add_port(self, port: Port):
        self.ports.append(port)

    def add_signal(self, signal: SignalLine):
        self.signals.append(signal)

    def add_extern_func(self, name: str, returns: str = "void",
                        params: Optional[List[Tuple[str, str]]] = None):
        """Register an external function.
        Can be called as add_extern_func("name") for simple registration,
        or add_extern_func("name", "void", [("buf", "uint8_t*")]) for full signature."""
        if params is not None or returns != "void":
            self.extern_funcs.append({
                'name': name, 'returns': returns,
                'params': params or [],
            })
        else:
            self.extern_funcs.append(name)

    @property
    def cpu_chips(self) -> List[Chip]:
        return [c for c in self.chips if c.has_cpu]

    @property
    def peripheral_chips(self) -> List[Chip]:
        return [c for c in self.chips if not c.has_cpu]

    def validate(self) -> List[str]:
        errors = []
        if not self.master_clock:
            errors.append("No master clock set")
        if not self.chips:
            errors.append("No chips on the board")
        if not self.buses:
            errors.append("No memory buses defined")
        if not any(c.has_cpu for c in self.chips):
            errors.append("No chip has a CPU core")
        for chip in self.chips:
            if not chip.clock:
                errors.append(f"Chip {chip.name!r} has no clock")
            if chip.has_cpu and not chip.bus:
                errors.append(f"CPU chip {chip.name!r} has no bus assigned")
        return errors

    def __repr__(self) -> str:
        return (f"Board({self.name!r}, chips={len(self.chips)}, "
                f"buses={len(self.buses)})")
