"""
proto -- Declarative emulator framework.

Define hardware systems in Python, generate C emulators.
"""

from .memory import (
    MemoryRegion, MemoryBank, MemoryBus, MemoryController,
    MemoryAccessLevel, Handler, HandlerType, BusMaster,
)
from .hardware import (
    Clock, SignalLine, SignalType, SignalEdge,
    Port, PortSide, PortLatching,
    Chip, Board, RegisterBlock, DMAChannel,
)
from .cpu import CPUDefinition, InterruptVector
from .codegen import BoardCodeGenerator
from .transpiler import Transpiler
from .host import (
    SDLHost, DisplayConfig, AudioConfig,
    PaletteMap, PaletteEntry,
    InputMapping, KeyBinding,
    FrameTiming,
    Menu, MenuItem, MenuItemType, MenuBarConfig,
)
from .host_codegen import HostCodeGenerator
