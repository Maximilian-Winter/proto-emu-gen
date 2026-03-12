"""
cpu.py -- CPU core definition for the declarative hardware framework.

A CPUDefinition describes the instruction set architecture:
  - Registers, register pairs, flags
  - Opcodes (Python functions transpiled to C)
  - Prefix tables (e.g. CB-prefix on Game Boy)

Attached to a Chip via chip.set_cpu_core(cpu_def).
"""

import dataclasses
from typing import List, Optional, Dict, Tuple, Callable, Any


@dataclasses.dataclass
class OpcodeEntry:
    code: int
    mnemonic: str
    cycles: int
    func: Optional[Callable] = None
    c_code: Optional[str] = None
    variant_args: Optional[Tuple] = None  # for opcode families

    @property
    def is_transpiled(self) -> bool:
        return self.func is not None

    def __repr__(self) -> str:
        return f"Opcode(0x{self.code:02X}, {self.mnemonic!r}, {self.cycles}cyc)"


@dataclasses.dataclass
class RegisterDef:
    name: str
    bits: int
    default: str = "0"

    @property
    def c_type(self) -> str:
        if self.bits <= 8:
            return "uint8_t"
        elif self.bits <= 16:
            return "uint16_t"
        return "uint32_t"


@dataclasses.dataclass
class RegisterPairDef:
    name: str
    high: str
    low: str


@dataclasses.dataclass
class FlagDef:
    register: str
    flags: Dict[str, int]


@dataclasses.dataclass
class InterruptVector:
    """Defines an interrupt vector entry for a CPU."""
    name: str                                      # "NMI", "IRQ", "BRK"
    address: int                                   # Vector table address (e.g. 0xFFEA)
    priority: int = 0                              # Higher = checked first
    is_software: bool = False                      # BRK, COP (handled by opcode)
    signal_name: Optional[str] = None              # Links to SignalLine
    push_sequence: Optional[List[str]] = None      # ["PC", "P"] — what to push
    set_flags_on_entry: Optional[Dict[str, int]] = None  # {"I": 1, "D": 0}
    comment: str = ""


class CPUDefinition:
    def __init__(self, name: str, data_width: int = 8,
                 address_width: int = 16):
        self.name = name
        self.data_width = data_width
        self.address_width = address_width
        self.registers: List[RegisterDef] = []
        self.register_pairs: List[RegisterPairDef] = []
        self.flag_def: Optional[FlagDef] = None

        addr_type = f"uint{address_width}_t" if address_width in (8,16,32) else "uint32_t"
        self.builtin_state = [
            ("PC", addr_type, "0", "Program counter"),
            ("SP", addr_type, "0", "Stack pointer"),
            ("cycle_count", "uint64_t", "0", "Total cycles executed"),
            ("halted", "bool", "false", "CPU halted flag"),
        ]

        self.opcodes: Dict[int, OpcodeEntry] = {}
        self.prefix_tables: Dict[int, Dict[int, OpcodeEntry]] = {}
        self.interrupt_vectors: List[InterruptVector] = []

    def add_register(self, name: str, bits: int = 8, default: str = "0"):
        self.registers.append(RegisterDef(name, bits, default))

    def add_register_pair(self, name: str, high: str, low: str):
        self.register_pairs.append(RegisterPairDef(name, high, low))

    def set_flags(self, register: str, flags: Dict[str, int]):
        self.flag_def = FlagDef(register, flags)

    def opcode(self, code: int, mnemonic: str, cycles: int = 1):
        def decorator(func):
            entry = OpcodeEntry(code=code, mnemonic=mnemonic,
                                cycles=cycles, func=func)
            self.opcodes[code] = entry
            return func
        return decorator

    def add_opcode_raw(self, code: int, mnemonic: str, cycles: int,
                       c_code: str):
        entry = OpcodeEntry(code=code, mnemonic=mnemonic,
                            cycles=cycles, c_code=c_code)
        self.opcodes[code] = entry

    def opcode_family(self, pattern: str, variants: list, cycles: int = 1):
        """Define multiple opcodes from one template.
        variants: list of tuples (opcode, arg1, arg2, ...)
        The function receives (cpu, *args) where args are the variant values."""
        def decorator(func):
            for variant in variants:
                code = variant[0]
                args = variant[1:]
                entry = OpcodeEntry(
                    code=code,
                    mnemonic=pattern.format(*args),
                    cycles=cycles,
                    func=func,
                    variant_args=args,
                )
                self.opcodes[code] = entry
            return func
        return decorator

    def add_interrupt_vector(self, name: str, address: int, priority: int = 0,
                             is_software: bool = False,
                             signal_name: Optional[str] = None,
                             push_sequence: Optional[List[str]] = None,
                             set_flags_on_entry: Optional[Dict[str, int]] = None,
                             comment: str = ""):
        self.interrupt_vectors.append(InterruptVector(
            name=name, address=address, priority=priority,
            is_software=is_software, signal_name=signal_name,
            push_sequence=push_sequence,
            set_flags_on_entry=set_flags_on_entry,
            comment=comment,
        ))

    def add_prefix_table(self, prefix_opcode: int):
        self.prefix_tables[prefix_opcode] = {}

    def prefix_opcode(self, prefix: int, code: int, mnemonic: str,
                      cycles: int = 1):
        if prefix not in self.prefix_tables:
            self.add_prefix_table(prefix)
        def decorator(func):
            entry = OpcodeEntry(code=code, mnemonic=mnemonic,
                                cycles=cycles, func=func)
            self.prefix_tables[prefix][code] = entry
            return func
        return decorator

    def prefix_opcode_family(self, prefix: int, pattern: str,
                             variants: list, cycles: int = 1):
        """Define multiple prefix opcodes from one template.
        variants: list of tuples (opcode, arg1, arg2, ...)
        The function receives (cpu, *args) where args are the variant values."""
        if prefix not in self.prefix_tables:
            self.add_prefix_table(prefix)
        def decorator(func):
            for variant in variants:
                code = variant[0]
                args = variant[1:]
                entry = OpcodeEntry(
                    code=code,
                    mnemonic=pattern.format(*args),
                    cycles=cycles,
                    func=func,
                    variant_args=args,
                )
                self.prefix_tables[prefix][code] = entry
            return func
        return decorator

    @property
    def all_register_names(self) -> List[str]:
        names = [r.name for r in self.registers]
        names.extend(rp.name for rp in self.register_pairs)
        return names

    def __repr__(self) -> str:
        return (f"CPUDefinition({self.name!r}, "
                f"{len(self.registers)} regs, "
                f"{len(self.opcodes)} opcodes)")
