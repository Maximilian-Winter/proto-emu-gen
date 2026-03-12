"""
codegen.py -- Board-level C code generator.
Takes a Board and emits a complete, compilable C file.
"""

import inspect
from typing import Optional, Set
from .memory import (
    MemoryRegion, MemoryBank, MemoryBus, MemoryController,
    MemoryAccessLevel, BusMapping, BusOverlay, Handler, HandlerType,
)
from .hardware import (
    Clock, Port, PortLatching, Chip, Board, RegisterBlock,
)
from .cpu import CPUDefinition, OpcodeEntry
from .transpiler import Transpiler


class BoardCodeGenerator:
    def __init__(self, board: Board):
        self.board = board
        for e in board.validate():
            print(f"[WARNING] {e}")

    def generate(self) -> str:
        parts = [
            self._gen_header(),
            self._gen_chip_structs(),
            self._gen_board_struct(),
            self._gen_forward_decls(),
            self._gen_flag_helpers(),
            self._gen_pair_helpers(),
            self._gen_sync_function(),
            self._gen_bus_dispatch(),
            self._gen_mem_convenience(),
            self._gen_signal_functions(),
            self._gen_register_dispatchers(),
            self._gen_controller_resolvers(),
            self._gen_chip_helpers(),
            self._gen_dma_functions(),
            self._gen_interrupt_check(),
            self._gen_cpu_steps(),
            self._gen_chip_ticks(),
            self._gen_init(),
            self._gen_step(),
        ]
        return '\n\n'.join(p for p in parts if p)

    # --- naming helpers ---

    @property
    def st(self):
        return f"{self.board.name.lower()}_t"

    @property
    def sn(self):
        return self.board.name.lower()

    def _chip_names(self) -> Set[str]:
        return {c.name for c in self.board.chips}

    def _find_region_owner(self, region: MemoryRegion) -> Optional[str]:
        for chip in self.board.chips:
            for mem in chip.internal_memory:
                if mem.name == region.name:
                    return chip.name
        return None

    def _find_ctrl_owner(self, ctrl: MemoryController) -> Optional[str]:
        for chip in self.board.chips:
            for c in chip.memory_controllers:
                if c.name == ctrl.name:
                    return chip.name
        return None

    def _find_chip(self, name: str) -> Optional[Chip]:
        for c in self.board.chips:
            if c.name == name:
                return c
        return None

    def _find_bus_cpu(self, bus: MemoryBus) -> Optional[Chip]:
        """Find the CPU chip that owns a given bus."""
        for chip in self.board.chips:
            if chip.has_cpu and chip.bus == bus:
                return chip
        return None

    def _hex(self, val: int, bus: MemoryBus = None) -> str:
        """Format an address as hex literal, width-aware for 24-bit+ buses."""
        if bus and bus.address_bits > 16:
            return f"0x{val:06X}"
        return f"0x{val:04X}"

    def _pc_fmt(self, bus: MemoryBus = None) -> str:
        """Printf format for PC addresses (e.g. %04X or %06X)."""
        if bus and bus.address_bits > 16:
            return "%06X"
        return "%04X"

    def _mr(self, chip: Chip) -> str:
        """Per-chip mem_read name."""
        return f"{chip.name}_mem_read" if len(self.board.cpu_chips) > 1 else "mem_read"

    def _mw(self, chip: Chip) -> str:
        return f"{chip.name}_mem_write" if len(self.board.cpu_chips) > 1 else "mem_write"

    def _make_transpiler(self, chip: Chip, self_param: str = "cpu",
                         variant_args=None, variant_param_names=None) -> Transpiler:
        flag_register = None
        flag_bits = {}
        cpu_name = chip.name
        pairs = set()

        def _extract(c):
            nonlocal flag_register, flag_bits, cpu_name, pairs
            if c.has_cpu and c.cpu_core.flag_def:
                flag_register = c.cpu_core.flag_def.register
                flag_bits = c.cpu_core.flag_def.flags
                cpu_name = c.name
                pairs = {rp.name for rp in c.cpu_core.register_pairs}

        if chip.has_cpu:
            _extract(chip)
        else:
            for c in self.board.chips:
                if c.has_cpu:
                    _extract(c)
                    break

        # Build function remap for per-chip functions
        func_remap = {}
        if chip.has_cpu and len(self.board.cpu_chips) > 1:
            cn = chip.name
            func_remap = {
                "mem_read": self._mr(chip),
                "mem_write": self._mw(chip),
                "mem_read16": f"{cn}_mem_read16",
                "read_imm8": f"{cn}_read_imm8",
                "read_imm16": f"{cn}_read_imm16",
                "push8": f"{cn}_push8",
                "push16": f"{cn}_push16",
                "pop8": f"{cn}_pop8",
                "pop16": f"{cn}_pop16",
                "internal_op": f"{cn}_internal_op",
            }

        # Extract extern func names (support both string and dict entries)
        ef_names = set()
        for ef in self.board.extern_funcs:
            if isinstance(ef, dict):
                ef_names.add(ef['name'])
            else:
                ef_names.add(ef)

        return Transpiler(
            self_param=self_param,
            chip_name=chip.name,
            component_names=self._chip_names(),
            extern_funcs=ef_names,
            flag_register=flag_register,
            flag_bits=flag_bits,
            cpu_name=cpu_name,
            register_pairs=pairs,
            variant_args=variant_args,
            variant_param_names=variant_param_names,
            mem_read_func=self._mr(chip) if chip.has_cpu else "mem_read",
            mem_write_func=self._mw(chip) if chip.has_cpu else "mem_write",
            func_remap=func_remap,
        )

    def _transpile_handler(self, handler: Handler, chip: Chip,
                           self_param: str = "cpu", indent: int = 3) -> str:
        """Transpile a Python handler and return indented C lines."""
        t = self._make_transpiler(chip, self_param=self_param)
        code = t.transpile_function(handler.func)
        prefix = "    " * indent
        result = []
        for line in code.split('\n'):
            stripped = line.strip()
            if stripped:
                result.append(f"{prefix}{stripped}")
        return '\n'.join(result)

    # =================================================================
    # 1. Header
    # =================================================================

    def _gen_header(self) -> str:
        lines = [
            f"/* Generated by proto framework -- Board: {self.board.name} */",
            "#include <stdio.h>",
            "#include <stdlib.h>",
            "#include <stdint.h>",
            "#include <stdbool.h>",
            "#include <string.h>",
        ]
        # Emit extern function declarations
        for ef in self.board.extern_funcs:
            if isinstance(ef, dict):
                params_str = ", ".join(
                    f"{pt} {pn}" for pn, pt in ef['params']
                ) if ef['params'] else "void"
                lines.append(
                    f"extern {ef['returns']} {ef['name']}({params_str});")
        return '\n'.join(lines)

    # =================================================================
    # 2. Chip structs
    # =================================================================

    def _gen_chip_structs(self) -> str:
        parts = []
        for chip in self.board.chips:
            lines = [f"typedef struct {{"]

            if chip.has_cpu:
                cpu = chip.cpu_core
                for name, c_type, default, comment in cpu.builtin_state:
                    cmt = f"  /* {comment} */" if comment else ""
                    lines.append(f"    {c_type} {name};{cmt}")
                for reg in cpu.registers:
                    lines.append(f"    {reg.c_type} {reg.name};")
                if cpu.flag_def:
                    lines.append(f"    uint8_t {cpu.flag_def.register};")

            for name, c_type, default, comment in chip.state_fields:
                cmt = f"  /* {comment} */" if comment else ""
                # Handle array types: "int16_t[4096]" -> "int16_t name[4096];"
                if '[' in c_type:
                    base, arr = c_type.split('[', 1)
                    lines.append(f"    {base} {name}[{arr};{cmt}")
                else:
                    lines.append(f"    {c_type} {name};{cmt}")

            for ctrl in chip.memory_controllers:
                for name, c_type, default, comment in ctrl.state_fields:
                    lines.append(f"    {c_type} {name};")

            existing = set()
            for name, _, _, _ in chip.state_fields:
                existing.add(name)
            for block in chip.register_blocks:
                for idx, entry in sorted(block.registers.items()):
                    if entry.name and entry.name not in existing:
                        lines.append(f"    uint8_t {entry.name};")
                        existing.add(entry.name)

            # DMA channel state fields
            for dma in chip.dma_channels:
                for fname, ftype, fdefault, fcomment in dma.state_fields:
                    cmt = f"  /* {fcomment} */" if fcomment else ""
                    if dma.channels > 1:
                        lines.append(f"    {ftype} {dma.name}_{fname}[{dma.channels}];{cmt}")
                    else:
                        lines.append(f"    {ftype} {dma.name}_{fname};{cmt}")

            for region in chip.internal_memory:
                if region.is_dynamic:
                    lines.append(f"    {region.c_data_type}* {region.name};")
                    lines.append(f"    uint32_t {region.name}_size;")
                else:
                    lines.append(f"    {region.c_data_type} {region.name}[{region.size_in_bytes}];")

            lines.append(f"}} {chip.name}_t;")
            parts.append('\n'.join(lines))
        return '\n\n'.join(parts)

    # =================================================================
    # 3. Board struct
    # =================================================================

    def _gen_board_struct(self) -> str:
        lines = [f"typedef struct {{"]
        for chip in self.board.chips:
            lines.append(f"    {chip.name}_t {chip.name};")
        for port in self.board.ports:
            w = port.width
            if port.latching == PortLatching.Independent:
                lines.append(f"    uint8_t {port.name}_a_out[{w}];")
                lines.append(f"    uint8_t {port.name}_b_out[{w}];")
            else:
                lines.append(f"    uint8_t {port.name}_shared[{w}];")
        for sig in self.board.signals:
            lines.append(f"    bool {sig.name}_asserted;")
        for bus in self.board.buses:
            for ov in bus.overlays:
                lines.append(f"    bool {ov.state_field};")
        # Bus arbitration state
        for bus in self.board.buses:
            if bus.masters:
                lines.append(f"    bool {bus.name}_dma_active;  /* bus arbitration */")
        lines.append(f"}} {self.st};")
        return '\n'.join(lines)

    # =================================================================
    # 4. Forward declarations
    # =================================================================

    def _gen_forward_decls(self) -> str:
        L = [f"/* Forward declarations */"]
        L.append(f"static void {self.sn}_init({self.st}* sys);")
        L.append(f"static void {self.sn}_step({self.st}* sys);")

        # Sync function (cycle-accurate boards)
        if self.board.cycle_accurate:
            L.append(f"static void {self.sn}_sync({self.st}* sys, uint32_t master_cycles);")

        for bus in self.board.buses:
            at = bus.addr_type
            L.append(f"static uint8_t {bus.name}_read({self.st}* sys, {at} addr);")
            L.append(f"static void {bus.name}_write({self.st}* sys, {at} addr, uint8_t val);")

        for chip in self.board.chips:
            if chip.has_cpu:
                bus = chip.bus
                at = bus.addr_type if bus else "uint16_t"
                mr, mw = self._mr(chip), self._mw(chip)
                cn = chip.name
                L.append(f"static void {cn}_step({self.st}* sys);")
                L.append(f"static uint8_t {mr}({self.st}* sys, {at} addr);")
                L.append(f"static void {mw}({self.st}* sys, {at} addr, uint8_t val);")
                L.append(f"static uint8_t {cn}_read_imm8({self.st}* sys);")
                L.append(f"static uint16_t {cn}_read_imm16({self.st}* sys);")
                L.append(f"static void {cn}_push8({self.st}* sys, uint8_t val);")
                L.append(f"static uint8_t {cn}_pop8({self.st}* sys);")
                L.append(f"static void {cn}_push16({self.st}* sys, uint16_t val);")
                L.append(f"static uint16_t {cn}_pop16({self.st}* sys);")
                L.append(f"static uint16_t {cn}_mem_read16({self.st}* sys, {at} addr);")
                L.append(f"static void {cn}_internal_op({self.st}* sys, uint32_t cycles);")

        # Single-CPU global aliases
        if len(self.board.cpu_chips) == 1:
            chip = self.board.cpu_chips[0]
            bus = chip.bus
            at = bus.addr_type if bus else "uint16_t"
            L.append(f"static uint8_t read_imm8({self.st}* sys);")
            L.append(f"static uint16_t read_imm16({self.st}* sys);")
            L.append(f"static void push8({self.st}* sys, uint8_t val);")
            L.append(f"static uint8_t pop8({self.st}* sys);")
            L.append(f"static void push16({self.st}* sys, uint16_t val);")
            L.append(f"static uint16_t pop16({self.st}* sys);")
            L.append(f"static uint16_t mem_read16({self.st}* sys, {at} addr);")
            L.append(f"static void internal_op({self.st}* sys, uint32_t cycles);")

        for chip in self.board.chips:
            for block in chip.register_blocks:
                L.append(f"static uint8_t {block.name}_read({self.st}* sys, uint8_t idx);")
                L.append(f"static void {block.name}_write({self.st}* sys, uint8_t idx, uint8_t val);")

        for chip in self.board.chips:
            for ctrl in chip.memory_controllers:
                for bank_name in ctrl.bank_resolvers:
                    bus = chip.bus or (self.board.buses[0] if self.board.buses else None)
                    at = bus.addr_type if bus else "uint16_t"
                    L.append(f"static uint32_t {ctrl.name}_resolve_{bank_name}({self.st}* sys, {at} addr);")
                for (bname, direction), _ in ctrl.access_guards.items():
                    L.append(f"static bool {ctrl.name}_guard_{direction}_{bname}({self.st}* sys);")

        for chip in self.board.chips:
            for h in chip.helpers:
                params = f"{self.st}* sys"
                for pn, pt in h['params']:
                    params += f", {pt} {pn}"
                L.append(f"static {h['returns']} {h['name']}({params});")

        for sig in self.board.signals:
            L.append(f"static void signal_assert_{sig.name}({self.st}* sys);")

        for chip in self.board.chips:
            if chip.tick_handler:
                L.append(f"static void {chip.name}_tick({self.st}* sys, uint32_t cycles);")

        # DMA transfer functions
        for chip in self.board.chips:
            for dma in chip.dma_channels:
                if dma.transfer_handler:
                    L.append(f"static void {dma.name}_transfer({self.st}* sys);")

        # Interrupt check functions
        for chip in self.board.chips:
            if chip.has_cpu and chip.cpu_core.interrupt_vectors:
                L.append(f"static void {chip.name}_check_interrupts({self.st}* sys);")

        return '\n'.join(L)

    # =================================================================
    # 5-6. Flag and pair helpers
    # =================================================================

    def _gen_flag_helpers(self) -> str:
        parts = []
        for chip in self.board.chips:
            if chip.has_cpu and chip.cpu_core.flag_def:
                fd = chip.cpu_core.flag_def
                cn = chip.name
                for flag, bit in fd.flags.items():
                    mask = 1 << bit
                    parts.append(
                        f"static inline bool {cn}_get_{flag}({self.st}* sys) "
                        f"{{ return (sys->{cn}.{fd.register} >> {bit}) & 1; }}")
                    parts.append(
                        f"static inline void {cn}_set_{flag}({self.st}* sys, bool val) "
                        f"{{ if (val) sys->{cn}.{fd.register} |= 0x{mask:02X}; "
                        f"else sys->{cn}.{fd.register} &= ~0x{mask:02X}; }}")
        return '\n'.join(parts)

    def _gen_pair_helpers(self) -> str:
        parts = []
        for chip in self.board.chips:
            if chip.has_cpu:
                cn = chip.name
                for rp in chip.cpu_core.register_pairs:
                    parts.append(
                        f"static inline uint16_t {cn}_get_{rp.name}({self.st}* sys) "
                        f"{{ return ((uint16_t)sys->{cn}.{rp.high} << 8) | sys->{cn}.{rp.low}; }}")
                    parts.append(
                        f"static inline void {cn}_set_{rp.name}({self.st}* sys, uint16_t val) "
                        f"{{ sys->{cn}.{rp.high} = val >> 8; sys->{cn}.{rp.low} = val & 0xFF; }}")
        return '\n'.join(parts)

    # =================================================================
    # Sync function (cycle-accurate mode)
    # =================================================================

    def _gen_sync_function(self) -> str:
        if not self.board.cycle_accurate:
            return ""

        cpu_chips = self.board.cpu_chips
        if not cpu_chips:
            return ""

        primary = cpu_chips[0]
        L = [f"/* Sync: tick all peripherals and secondary CPUs for the given master cycles */"]
        L.append(f"static void {self.sn}_sync({self.st}* sys, uint32_t master_cycles) {{")

        # Tick peripherals
        for pchip in self.board.chips:
            if pchip == primary:
                continue
            if pchip.has_cpu:
                div = pchip.clock.master_divider if pchip.clock else 1
                L.append(f"    {{ uint32_t cyc = master_cycles / {div};")
                L.append(f"      for (uint32_t i = 0; i < cyc; i++) {pchip.name}_step(sys);")
                L.append(f"    }}")
            elif pchip.tick_handler:
                div = pchip.clock.master_divider if pchip.clock else 1
                L.append(f"    {pchip.name}_tick(sys, master_cycles / {div});")

        L.append(f"}}")
        return '\n'.join(L)

    # =================================================================
    # 7. Bus dispatch (read + write for each bus)
    # =================================================================

    def _gen_bus_dispatch(self) -> str:
        parts = []
        for bus in self.board.buses:
            parts.append(self._bus_read(bus))
            parts.append(self._bus_write(bus))
        return '\n\n'.join(parts)

    def _access_timing(self, m: BusMapping, bus: MemoryBus, indent: int = 2) -> str:
        """Generate access timing code for a bus mapping."""
        if m.access_cycles <= 0:
            return ""
        cpu_chip = self._find_bus_cpu(bus)
        if not cpu_chip:
            return ""
        ind = "    " * indent
        cn = cpu_chip.name
        lines = [f"{ind}sys->{cn}.cycle_count += {m.access_cycles};"]
        if self.board.cycle_accurate:
            div = cpu_chip.clock.master_divider if cpu_chip.clock else 1
            lines.append(
                f"{ind}{self.sn}_sync(sys, {m.access_cycles} * {div});")
        return '\n'.join(lines)

    @staticmethod
    def _sort_mappings(mappings):
        """Sort bus mappings so narrower ranges come before wider overlapping ones.

        This ensures that when a specific sub-range (e.g. FF30-FF3F wave RAM)
        overlaps with a broader range (e.g. FF10-FF3F APU registers), the
        narrower mapping is checked first in the generated if-chain.

        Sort key: span ascending (narrower first), then start address ascending.
        """
        return sorted(mappings,
                      key=lambda m: (m.addr_end - m.addr_start, m.addr_start))

    def _bus_read(self, bus: MemoryBus) -> str:
        at = bus.addr_type
        hx = lambda v: self._hex(v, bus)
        L = [f"static uint8_t {bus.name}_read({self.st}* sys, {at} addr) {{"]

        for ov in bus.overlays:
            L.append(f"    if (sys->{ov.state_field} && "
                     f"addr >= {hx(ov.addr_start)} && addr <= {hx(ov.addr_end)}) {{")
            owner = self._find_region_owner(ov.region)
            p = f"sys->{owner}." if owner else ""
            L.append(f"        return {p}{ov.region.name}[addr - {hx(ov.addr_start)}];")
            L.append(f"    }}")

        # Port reads (before regular mappings to handle address overlap)
        for port in self.board.ports:
            for side_label, side in [("a", port.side_a), ("b", port.side_b)]:
                if side and side.chip and side.chip.bus == bus:
                    L.append(f"    if (addr >= {hx(side.addr_start)} && addr <= {hx(side.addr_end)}) {{")
                    other = "b" if side_label == "a" else "a"
                    if port.latching == PortLatching.Independent:
                        L.append(f"        return sys->{port.name}_{other}_out[addr - {hx(side.addr_start)}];")
                    else:
                        L.append(f"        return sys->{port.name}_shared[addr - {hx(side.addr_start)}];")
                    L.append(f"    }}")

        for m in self._sort_mappings(bus.mappings):
            if m.write_only:
                continue
            L.append(f"    if (addr >= {hx(m.addr_start)} && addr <= {hx(m.addr_end)}) {{")
            # Access timing
            timing = self._access_timing(m, bus)
            if timing:
                L.append(timing)
            if m.bank and m.controller:
                L.append(self._banked_read(m, bus))
            elif m.handler:
                b = m.handler
                L.append(f"        return {b.name}_read(sys, addr - {hx(b.base_addr)});")
            elif m.region:
                owner = self._find_region_owner(m.region)
                p = f"sys->{owner}." if owner else ""
                L.append(f"        return {p}{m.region.name}[addr - {hx(m.addr_start)} + {m.offset}];")
            L.append(f"    }}")

        if isinstance(bus.fallback_read, int):
            L.append(f"    return 0x{bus.fallback_read:02X};")
        else:
            L.append(f"    {bus.fallback_read}")
        L.append(f"}}")
        return '\n'.join(L)

    def _bus_write(self, bus: MemoryBus) -> str:
        at = bus.addr_type
        hx = lambda v: self._hex(v, bus)
        L = [f"static void {bus.name}_write({self.st}* sys, {at} addr, uint8_t val) {{"]

        for ov in bus.overlays:
            if ov.disable_on_write:
                da, _ = ov.disable_on_write
                L.append(f"    if (addr == {hx(da)}) sys->{ov.state_field} = false;")

        # Write-only mappings (controller intercepts) -- checked first
        for m in bus.write_mappings:
            L.append(f"    if (addr >= {hx(m.addr_start)} && addr <= {hx(m.addr_end)}) {{")
            if m.controller:
                L.append(self._ctrl_write_dispatch(m, bus))
            L.append(f"        return;")
            L.append(f"    }}")

        # Port writes (checked before regular mappings to handle address overlap)
        for port in self.board.ports:
            for side_label, side in [("a", port.side_a), ("b", port.side_b)]:
                if side and side.chip and side.chip.bus == bus:
                    L.append(f"    if (addr >= {hx(side.addr_start)} && addr <= {hx(side.addr_end)}) {{")
                    if port.latching == PortLatching.Independent:
                        L.append(f"        sys->{port.name}_{side_label}_out[addr - {hx(side.addr_start)}] = val;")
                    else:
                        L.append(f"        sys->{port.name}_shared[addr - {hx(side.addr_start)}] = val;")
                    L.append(f"        return;")
                    L.append(f"    }}")

        for m in self._sort_mappings(bus.mappings):
            if m.write_only:
                continue
            L.append(f"    if (addr >= {hx(m.addr_start)} && addr <= {hx(m.addr_end)}) {{")
            # Access timing
            timing = self._access_timing(m, bus)
            if timing:
                L.append(timing)
            if m.bank and m.controller:
                L.append(self._banked_write(m, bus))
            elif m.handler:
                b = m.handler
                L.append(f"        {b.name}_write(sys, addr - {hx(b.base_addr)}, val);")
            elif m.region:
                if m.region.access == MemoryAccessLevel.ReadOnly:
                    L.append(f"        /* read-only */")
                else:
                    owner = self._find_region_owner(m.region)
                    p = f"sys->{owner}." if owner else ""
                    L.append(f"        {p}{m.region.name}[addr - {hx(m.addr_start)} + {m.offset}] = val;")
                    if m.on_write_side_effect:
                        L.append(f"        {m.on_write_side_effect}")
            L.append(f"        return;")
            L.append(f"    }}")

        L.append(f"}}")
        return '\n'.join(L)

    def _banked_read(self, m: BusMapping, bus: MemoryBus = None) -> str:
        ctrl = m.controller
        bank = m.bank
        region = bank.region
        owner = self._find_ctrl_owner(ctrl) or self._find_region_owner(region)
        p = f"sys->{owner}." if owner else ""
        hx = lambda v: self._hex(v, bus)
        L = []

        guard = ctrl.access_guards.get((bank.name, "read"))
        if guard:
            L.append(f"        if (!{ctrl.name}_guard_read_{bank.name}(sys)) return 0xFF;")

        if m.fixed:
            L.append(f"        return {p}{region.name}[addr - {hx(m.addr_start)} + {m.offset}];")
        else:
            L.append(f"        uint32_t bk = {ctrl.name}_resolve_{bank.name}(sys, addr);")
            L.append(f"        uint32_t off = bk * 0x{bank.bank_size:X}u + (addr - {hx(m.addr_start)});")
            if region.is_dynamic:
                L.append(f"        if ({p}{region.name}_size) off %= {p}{region.name}_size;")
                L.append(f"        return {p}{region.name} ? {p}{region.name}[off] : 0xFF;")
            else:
                L.append(f"        return {p}{region.name}[off % {region.size_in_bytes}u];")
        return '\n'.join(L)

    def _banked_write(self, m: BusMapping, bus: MemoryBus = None) -> str:
        ctrl = m.controller
        bank = m.bank
        region = bank.region
        owner = self._find_ctrl_owner(ctrl) or self._find_region_owner(region)
        p = f"sys->{owner}." if owner else ""
        hx = lambda v: self._hex(v, bus)
        L = []

        if region.access == MemoryAccessLevel.ReadOnly:
            L.append(f"        /* read-only bank */")
            return '\n'.join(L)

        guard = ctrl.access_guards.get((bank.name, "write"))
        if guard:
            L.append(f"        if (!{ctrl.name}_guard_write_{bank.name}(sys)) return;")

        if m.fixed:
            L.append(f"        {p}{region.name}[addr - {hx(m.addr_start)} + {m.offset}] = val;")
        else:
            L.append(f"        uint32_t bk = {ctrl.name}_resolve_{bank.name}(sys, addr);")
            L.append(f"        uint32_t off = bk * 0x{bank.bank_size:X}u + (addr - {hx(m.addr_start)});")
            if region.is_dynamic:
                L.append(f"        if ({p}{region.name}_size) off %= {p}{region.name}_size;")
                L.append(f"        if ({p}{region.name}) {p}{region.name}[off] = val;")
            else:
                L.append(f"        off %= {region.size_in_bytes}u;")
                L.append(f"        {p}{region.name}[off] = val;")
        return '\n'.join(L)

    def _ctrl_write_dispatch(self, m: BusMapping, bus: MemoryBus = None) -> str:
        ctrl = m.controller
        chip_name = self._find_ctrl_owner(ctrl)
        chip = self._find_chip(chip_name) if chip_name else None
        hx = lambda v: self._hex(v, bus)
        L = []
        for handler in ctrl.write_handlers:
            if handler.addr_start is None:
                continue
            L.append(f"        if (addr >= {hx(handler.addr_start)} && addr <= {hx(handler.addr_end)}) {{")
            if handler.handler_type == HandlerType.RawC:
                L.append(f"            {handler.code}")
            elif handler.func and chip:
                L.append(self._transpile_handler(handler, chip, self_param="ctrl", indent=3))
            L.append(f"            return;")
            L.append(f"        }}")
        return '\n'.join(L)

    # =================================================================
    # 8. Per-chip memory convenience
    # =================================================================

    def _gen_mem_convenience(self) -> str:
        parts = []
        for chip in self.board.chips:
            if not chip.has_cpu or not chip.bus:
                continue
            bus = chip.bus
            at = bus.addr_type
            cn = chip.name
            mr, mw = self._mr(chip), self._mw(chip)

            parts.append(f"""\
static uint8_t {mr}({self.st}* sys, {at} addr) {{ return {bus.name}_read(sys, addr); }}
static void {mw}({self.st}* sys, {at} addr, uint8_t val) {{ {bus.name}_write(sys, addr, val); }}
static uint8_t {cn}_read_imm8({self.st}* sys) {{ return {mr}(sys, sys->{cn}.PC++); }}
static uint16_t {cn}_read_imm16({self.st}* sys) {{
    uint8_t lo = {cn}_read_imm8(sys);
    uint8_t hi = {cn}_read_imm8(sys);
    return ((uint16_t)hi << 8) | lo;
}}
static void {cn}_push8({self.st}* sys, uint8_t val) {{
    sys->{cn}.SP--; {mw}(sys, sys->{cn}.SP, val);
}}
static uint8_t {cn}_pop8({self.st}* sys) {{
    return {mr}(sys, sys->{cn}.SP++);
}}
static void {cn}_push16({self.st}* sys, uint16_t val) {{
    sys->{cn}.SP--; {mw}(sys, sys->{cn}.SP, (val >> 8) & 0xFF);
    sys->{cn}.SP--; {mw}(sys, sys->{cn}.SP, val & 0xFF);
}}
static uint16_t {cn}_pop16({self.st}* sys) {{
    uint8_t lo = {mr}(sys, sys->{cn}.SP++);
    uint8_t hi = {mr}(sys, sys->{cn}.SP++);
    return ((uint16_t)hi << 8) | lo;
}}
static uint16_t {cn}_mem_read16({self.st}* sys, {at} addr) {{
    uint8_t lo = {mr}(sys, addr);
    uint8_t hi = {mr}(sys, addr + 1);
    return ((uint16_t)hi << 8) | lo;
}}""")

            # internal_op: cycle-accurate syncs peripherals, otherwise just counts
            if self.board.cycle_accurate:
                div = chip.clock.master_divider if chip.clock else 1
                parts.append(f"""\
static void {cn}_internal_op({self.st}* sys, uint32_t cycles) {{
    sys->{cn}.cycle_count += cycles;
    {self.sn}_sync(sys, cycles * {div});
}}""")
            else:
                parts.append(f"""\
static void {cn}_internal_op({self.st}* sys, uint32_t cycles) {{
    sys->{cn}.cycle_count += cycles;
}}""")

        if len(self.board.cpu_chips) == 1:
            chip = self.board.cpu_chips[0]
            cn = chip.name
            bus = chip.bus
            at = bus.addr_type if bus else "uint16_t"
            alias_lines = f"""\
static uint8_t read_imm8({self.st}* sys) {{ return {cn}_read_imm8(sys); }}
static uint16_t read_imm16({self.st}* sys) {{ return {cn}_read_imm16(sys); }}
static void push8({self.st}* sys, uint8_t val) {{ {cn}_push8(sys, val); }}
static uint8_t pop8({self.st}* sys) {{ return {cn}_pop8(sys); }}
static void push16({self.st}* sys, uint16_t val) {{ {cn}_push16(sys, val); }}
static uint16_t pop16({self.st}* sys) {{ return {cn}_pop16(sys); }}
static uint16_t mem_read16({self.st}* sys, {at} addr) {{ return {cn}_mem_read16(sys, addr); }}
static void internal_op({self.st}* sys, uint32_t cycles) {{ {cn}_internal_op(sys, cycles); }}"""
            parts.append(alias_lines)

        return '\n\n'.join(parts)

    # =================================================================
    # 9. Signal functions
    # =================================================================

    def _gen_signal_functions(self) -> str:
        parts = []
        for sig in self.board.signals:
            L = [f"static void signal_assert_{sig.name}({self.st}* sys) {{"]
            L.append(f"    sys->{sig.name}_asserted = true;")
            for sink in sig.sinks:
                handler = sig.on_assert_handlers.get(sink.name)
                if handler:
                    if handler.handler_type == HandlerType.RawC:
                        L.append(f"    {handler.code}")
                    elif handler.func:
                        L.append(self._transpile_handler(handler, sink, indent=1))
            L.append(f"}}")
            parts.append('\n'.join(L))
        return '\n\n'.join(parts)

    # =================================================================
    # 10. Register block dispatchers
    # =================================================================

    def _gen_register_dispatchers(self) -> str:
        parts = []
        for chip in self.board.chips:
            for block in chip.register_blocks:
                parts.append(self._reg_read(chip, block))
                parts.append(self._reg_write(chip, block))
        return '\n\n'.join(parts)

    def _reg_read(self, chip: Chip, block: RegisterBlock) -> str:
        L = [f"static uint8_t {block.name}_read({self.st}* sys, uint8_t idx) {{"]
        L.append(f"    switch (idx) {{")
        for idx, entry in sorted(block.registers.items()):
            L.append(f"        case {idx}:")
            if entry.read_handler:
                if entry.read_handler.handler_type == HandlerType.RawC:
                    L.append(f"            {entry.read_handler.code}")
                elif entry.read_handler.func:
                    L.append(f"        {{")
                    L.append(self._transpile_handler(entry.read_handler, chip,
                                                     self_param="chip", indent=3))
                    L.append(f"        }}")
            elif entry.name:
                L.append(f"            return sys->{chip.name}.{entry.name};")
            else:
                L.append(f"            return 0xFF;")
        L.append(f"        default: return 0xFF;")
        L.append(f"    }}")
        L.append(f"}}")
        return '\n'.join(L)

    def _reg_write(self, chip: Chip, block: RegisterBlock) -> str:
        L = [f"static void {block.name}_write({self.st}* sys, uint8_t idx, uint8_t val) {{"]
        L.append(f"    switch (idx) {{")
        for idx, entry in sorted(block.registers.items()):
            if entry.read_only:
                continue
            L.append(f"        case {idx}:")
            if entry.write_handler:
                if entry.write_handler.handler_type == HandlerType.RawC:
                    L.append(f"            {entry.write_handler.code}")
                elif entry.write_handler.func:
                    L.append(f"        {{")
                    L.append(self._transpile_handler(entry.write_handler, chip,
                                                     self_param="chip", indent=3))
                    L.append(f"        }}")
            elif entry.write_mask:
                pres, writ = entry.write_mask
                L.append(f"            sys->{chip.name}.{entry.name} = "
                         f"(sys->{chip.name}.{entry.name} & 0x{pres:02X}) | (val & 0x{writ:02X});")
            elif entry.name:
                L.append(f"            sys->{chip.name}.{entry.name} = val;")
            L.append(f"            break;")
        L.append(f"    }}")
        L.append(f"}}")
        return '\n'.join(L)

    # =================================================================
    # 11. Controller resolvers and guards
    # =================================================================

    def _gen_controller_resolvers(self) -> str:
        parts = []
        for chip in self.board.chips:
            for ctrl in chip.memory_controllers:
                bus = chip.bus or (self.board.buses[0] if self.board.buses else None)
                at = bus.addr_type if bus else "uint16_t"

                for bank_name, handler in ctrl.bank_resolvers.items():
                    if handler.handler_type == HandlerType.Python and handler.func:
                        code = self._transpile_handler(handler, chip, self_param="ctrl", indent=1)
                        parts.append(
                            f"static uint32_t {ctrl.name}_resolve_{bank_name}({self.st}* sys, {at} addr) {{\n"
                            f"{code}\n}}")
                    elif handler.handler_type == HandlerType.RawC:
                        parts.append(
                            f"static uint32_t {ctrl.name}_resolve_{bank_name}({self.st}* sys, {at} addr) {{\n"
                            f"    {handler.code}\n}}")

                for (bname, direction), handler in ctrl.access_guards.items():
                    if handler.handler_type == HandlerType.Python and handler.func:
                        code = self._transpile_handler(handler, chip, self_param="ctrl", indent=1)
                        parts.append(
                            f"static bool {ctrl.name}_guard_{direction}_{bname}({self.st}* sys) {{\n"
                            f"{code}\n}}")
                    elif handler.handler_type == HandlerType.RawC:
                        parts.append(
                            f"static bool {ctrl.name}_guard_{direction}_{bname}({self.st}* sys) {{\n"
                            f"    {handler.code}\n}}")

        return '\n\n'.join(parts)

    # =================================================================
    # 12. Chip helpers
    # =================================================================

    def _gen_chip_helpers(self) -> str:
        parts = []
        for chip in self.board.chips:
            for h in chip.helpers:
                params = f"{self.st}* sys"
                for pn, pt in h['params']:
                    params += f", {pt} {pn}"
                handler = h['handler']
                if handler.handler_type == HandlerType.RawC:
                    parts.append(
                        f"static {h['returns']} {h['name']}({params}) {{\n"
                        f"    {handler.code}\n}}")
                elif handler.func:
                    sp = self._guess_self_param(handler.func)
                    code = self._transpile_handler(handler, chip, self_param=sp, indent=1)
                    parts.append(
                        f"static {h['returns']} {h['name']}({params}) {{\n"
                        f"{code}\n}}")
        return '\n\n'.join(parts)

    # =================================================================
    # 12b. DMA transfer functions
    # =================================================================

    def _gen_dma_functions(self) -> str:
        parts = []
        for chip in self.board.chips:
            for dma in chip.dma_channels:
                if not dma.transfer_handler:
                    continue
                handler = dma.transfer_handler
                if handler.handler_type == HandlerType.RawC:
                    parts.append(
                        f"static void {dma.name}_transfer({self.st}* sys) {{\n"
                        f"    {handler.code}\n}}")
                elif handler.func:
                    sp = self._guess_self_param(handler.func)
                    code = self._transpile_handler(handler, chip, self_param=sp, indent=1)
                    parts.append(
                        f"static void {dma.name}_transfer({self.st}* sys) {{\n"
                        f"{code}\n}}")
        return '\n\n'.join(parts)

    # =================================================================
    # 12c. Interrupt check functions
    # =================================================================

    def _gen_interrupt_check(self) -> str:
        parts = []
        for chip in self.board.chips:
            if not chip.has_cpu:
                continue
            cpu = chip.cpu_core
            if not cpu.interrupt_vectors:
                continue
            cn = chip.name
            # Sort by priority descending (highest checked first)
            vectors = sorted(
                [v for v in cpu.interrupt_vectors if not v.is_software],
                key=lambda v: v.priority, reverse=True)
            if not vectors:
                continue

            L = [f"static void {cn}_check_interrupts({self.st}* sys) {{"]
            for vec in vectors:
                signal = vec.signal_name or vec.name.lower()
                L.append(f"    /* {vec.name} (priority {vec.priority}) */")
                L.append(f"    if (sys->{signal}_asserted) {{")
                L.append(f"        sys->{signal}_asserted = false;")

                # Push sequence
                if vec.push_sequence:
                    for reg_name in vec.push_sequence:
                        # Determine push width from register
                        reg_def = next(
                            (r for r in cpu.registers if r.name == reg_name),
                            None)
                        # Check builtin state (PC, SP)
                        builtin = next(
                            (b for b in cpu.builtin_state if b[0] == reg_name),
                            None)
                        if builtin:
                            # PC and SP are typically 16-bit
                            btype = builtin[1]
                            if "16" in btype or "32" in btype:
                                L.append(f"        {cn}_push16(sys, sys->{cn}.{reg_name});")
                            else:
                                L.append(f"        {cn}_push8(sys, sys->{cn}.{reg_name});")
                        elif reg_def and reg_def.bits > 8:
                            L.append(f"        {cn}_push16(sys, sys->{cn}.{reg_name});")
                        elif cpu.flag_def and reg_name == cpu.flag_def.register:
                            L.append(f"        {cn}_push8(sys, sys->{cn}.{reg_name});")
                        else:
                            L.append(f"        {cn}_push8(sys, sys->{cn}.{reg_name});")

                # Set flags on entry
                if vec.set_flags_on_entry and cpu.flag_def:
                    for flag_name, flag_val in vec.set_flags_on_entry.items():
                        L.append(f"        {cn}_set_{flag_name}(sys, {flag_val});")

                # Load vector address
                L.append(f"        sys->{cn}.PC = {cn}_mem_read16(sys, {self._hex(vec.address)});")
                L.append(f"        return;")
                L.append(f"    }}")

            L.append(f"}}")
            parts.append('\n'.join(L))
        return '\n\n'.join(parts)

    # =================================================================
    # 13. CPU step (opcode dispatch)
    # =================================================================

    def _gen_cpu_steps(self) -> str:
        parts = []
        for chip in self.board.chips:
            if chip.has_cpu:
                parts.append(self._cpu_step(chip))
        return '\n\n'.join(parts)

    def _cpu_step(self, chip: Chip) -> str:
        cpu = chip.cpu_core
        cn = chip.name
        mr = self._mr(chip)
        L = [f"static void {cn}_step({self.st}* sys) {{"]
        has_preamble = ((chip.step_preamble_handler and chip.step_preamble_handler.func)
                        or chip.step_preamble)
        if not has_preamble:
            # Default HALT: just return (no custom wake-up logic provided)
            L.append(f"    if (sys->{cn}.halted) return;")
        if chip.step_preamble_handler and chip.step_preamble_handler.func:
            L.append(self._transpile_handler(
                chip.step_preamble_handler, chip, self_param="cpu", indent=1))
        elif chip.step_preamble:
            for line in chip.step_preamble.strip().split('\n'):
                s = line.strip()
                if s:
                    L.append(f"    {s}")
        if cpu.interrupt_vectors:
            L.append(f"    {cn}_check_interrupts(sys);")
        L.append(f"    uint8_t opcode = {mr}(sys, sys->{cn}.PC++);")
        L.append(f"    switch (opcode) {{")

        for code in sorted(cpu.opcodes.keys()):
            entry = cpu.opcodes[code]
            L.append(f"        case 0x{code:02X}: {{ /* {entry.mnemonic} */")

            if entry.c_code:
                L.append(f"            {entry.c_code}")
            elif entry.func:
                # Get variant parameter names from function signature
                vpnames = None
                if entry.variant_args:
                    sig = inspect.signature(entry.func)
                    plist = list(sig.parameters.keys())
                    # First param is self (cpu), rest are variant params
                    vpnames = plist[1:]

                t = self._make_transpiler(
                    chip, self_param="cpu",
                    variant_args=entry.variant_args,
                    variant_param_names=vpnames,
                )
                c = t.transpile_function(entry.func)
                for line in c.split('\n'):
                    s = line.strip()
                    if s:
                        L.append(f"            {s}")

            if not self.board.cycle_accurate:
                L.append(f"            sys->{cn}.cycle_count += {entry.cycles};")
            L.append(f"            break; }}")

        # Prefix tables
        for prefix_op, table in cpu.prefix_tables.items():
            L.append(f"        case 0x{prefix_op:02X}: {{")
            L.append(f"            uint8_t cb = {mr}(sys, sys->{cn}.PC++);")
            L.append(f"            switch (cb) {{")
            for code in sorted(table.keys()):
                entry = table[code]
                L.append(f"                case 0x{code:02X}: {{ /* {entry.mnemonic} */")
                if entry.c_code:
                    L.append(f"                    {entry.c_code}")
                elif entry.func:
                    vpnames = None
                    if entry.variant_args:
                        sig = inspect.signature(entry.func)
                        plist = list(sig.parameters.keys())
                        vpnames = plist[1:]
                    t = self._make_transpiler(
                        chip, self_param="cpu",
                        variant_args=entry.variant_args,
                        variant_param_names=vpnames,
                    )
                    c = t.transpile_function(entry.func)
                    for line in c.split('\n'):
                        s = line.strip()
                        if s:
                            L.append(f"                    {s}")
                if not self.board.cycle_accurate:
                    L.append(f"                    sys->{cn}.cycle_count += {entry.cycles};")
                L.append(f"                    break; }}")
            L.append(f'                default: printf("Unknown CB opcode: 0x%02X\\n", cb); break;')
            L.append(f"            }}")
            L.append(f"            break; }}")

        L.append(f'        default:')
        pc_fmt = self._pc_fmt(chip.bus)
        L.append(f'            printf("Unknown opcode: 0x%02X at PC=0x{pc_fmt}\\n", opcode, sys->{cn}.PC - 1);')
        L.append(f'            sys->{cn}.halted = true; break;')
        L.append(f"    }}")
        L.append(f"}}")
        return '\n'.join(L)

    # =================================================================
    # 14. Chip tick functions
    # =================================================================

    def _gen_chip_ticks(self) -> str:
        parts = []
        for chip in self.board.chips:
            if chip.tick_handler:
                handler = chip.tick_handler
                if handler.handler_type == HandlerType.RawC:
                    parts.append(
                        f"static void {chip.name}_tick({self.st}* sys, uint32_t cycles) {{\n"
                        f"    {handler.code}\n}}")
                elif handler.func:
                    sp = self._guess_self_param(handler.func)
                    code = self._transpile_handler(handler, chip, self_param=sp, indent=1)
                    parts.append(
                        f"static void {chip.name}_tick({self.st}* sys, uint32_t cycles) {{\n"
                        f"{code}\n}}")
        return '\n\n'.join(parts)

    # =================================================================
    # 15. Board init
    # =================================================================

    def _gen_init(self) -> str:
        L = [f"static void {self.sn}_init({self.st}* sys) {{"]
        L.append(f"    memset(sys, 0, sizeof({self.st}));")

        for chip in self.board.chips:
            cn = chip.name
            if chip.has_cpu:
                for reg in chip.cpu_core.registers:
                    if reg.default != "0":
                        L.append(f"    sys->{cn}.{reg.name} = {reg.default};")

            for name, c_type, default, comment in chip.state_fields:
                if default and default != "0" and default != "false":
                    if '[' not in c_type:  # skip array types
                        L.append(f"    sys->{cn}.{name} = {default};")

            for ctrl in chip.memory_controllers:
                for name, c_type, default, comment in ctrl.state_fields:
                    if default and default != "0" and default != "false":
                        L.append(f"    sys->{cn}.{name} = {default};")

            for block in chip.register_blocks:
                for idx, entry in sorted(block.registers.items()):
                    if entry.default and entry.default != "0" and entry.name:
                        L.append(f"    sys->{cn}.{entry.name} = {entry.default};")

            # DMA state defaults
            for dma in chip.dma_channels:
                for fname, ftype, fdefault, fcomment in dma.state_fields:
                    if fdefault and fdefault != "0" and fdefault != "false":
                        if dma.channels > 1:
                            for i in range(dma.channels):
                                L.append(f"    sys->{cn}.{dma.name}_{fname}[{i}] = {fdefault};")
                        else:
                            L.append(f"    sys->{cn}.{dma.name}_{fname} = {fdefault};")

        for bus in self.board.buses:
            for ov in bus.overlays:
                L.append(f"    sys->{ov.state_field} = true;")

        L.append(f"}}")
        return '\n'.join(L)

    # =================================================================
    # 16. Board step (catch-up scheduler)
    # =================================================================

    def _gen_step(self) -> str:
        cpu_chips = self.board.cpu_chips
        if not cpu_chips:
            return ""

        L = [f"static void {self.sn}_step({self.st}* sys) {{"]

        if self.board.cycle_accurate:
            # Cycle-accurate mode: sync happens inline via bus access + internal_op.
            # step() just drives the primary CPU; peripherals/secondaries are
            # ticked by _sync() which fires on every memory access.
            primary = cpu_chips[0]
            cn = primary.name
            # Bus arbitration: DMA transfer when active, else CPU step
            if primary.bus and primary.bus.masters:
                dma_transfers = []
                for chip in self.board.chips:
                    for dma in chip.dma_channels:
                        if dma.transfer_handler:
                            dma_transfers.append(dma.name)
                if dma_transfers:
                    L.append(f"    if (sys->{primary.bus.name}_dma_active) {{")
                    for dn in dma_transfers:
                        L.append(f"        {dn}_transfer(sys);")
                    L.append(f"        return;")
                    L.append(f"    }}")
                else:
                    L.append(f"    if (sys->{primary.bus.name}_dma_active) return;")
            L.append(f"    {cn}_step(sys);")
        elif len(cpu_chips) == 1:
            # Single CPU: step, compute elapsed, tick peripherals
            chip = cpu_chips[0]
            cn = chip.name
            L.append(f"    uint64_t before = sys->{cn}.cycle_count;")
            L.append(f"    {cn}_step(sys);")
            L.append(f"    uint32_t elapsed = (uint32_t)(sys->{cn}.cycle_count - before);")

            for pchip in self.board.chips:
                if pchip.tick_handler and not pchip.has_cpu:
                    # Same clock: pass elapsed directly
                    # Different clock: scale by ratio
                    if pchip.clock and chip.clock and pchip.clock != chip.clock:
                        # Use master divider ratio
                        cpu_div = chip.clock.master_divider
                        pchip_div = pchip.clock.master_divider
                        if cpu_div != pchip_div:
                            L.append(f"    /* clock scaling: CPU div={cpu_div}, {pchip.name} div={pchip_div} */")
                            L.append(f"    {pchip.name}_tick(sys, elapsed * {pchip_div} / {cpu_div});")
                            continue
                    L.append(f"    {pchip.name}_tick(sys, elapsed);")
        else:
            # Multi-CPU: catch-up scheduling
            # Step the primary CPU, compute master cycles, step others proportionally
            primary = cpu_chips[0]
            pn = primary.name
            L.append(f"    uint64_t before = sys->{pn}.cycle_count;")
            L.append(f"    {pn}_step(sys);")
            L.append(f"    uint32_t elapsed = (uint32_t)(sys->{pn}.cycle_count - before);")
            L.append(f"    uint32_t master_elapsed = elapsed * {primary.clock.master_divider if primary.clock else 1};")

            for chip in self.board.chips:
                if chip == primary:
                    continue
                div = chip.clock.master_divider if chip.clock else 1
                if chip.has_cpu:
                    L.append(f"    {{ uint32_t cyc = master_elapsed / {div};")
                    L.append(f"      for (uint32_t i = 0; i < cyc; i++) {chip.name}_step(sys);")
                    L.append(f"    }}")
                elif chip.tick_handler:
                    L.append(f"    {chip.name}_tick(sys, master_elapsed / {div});")

        L.append(f"}}")
        return '\n'.join(L)

    # =================================================================
    # Utility
    # =================================================================

    def _guess_self_param(self, func) -> str:
        try:
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            if params:
                return params[0]
        except (ValueError, TypeError):
            pass
        return "cpu"
