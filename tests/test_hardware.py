"""
Tier 1D + 1E -- Hardware and CPU definition unit tests.

Tests Clock, SignalLine, Port, RegisterBlock, Chip, Board, DMAChannel,
CPUDefinition, RegisterDef, OpcodeEntry, and opcode decorators.
"""

import pytest
from proto.hardware import (
    Clock, SignalLine, SignalType, SignalEdge,
    Port, PortSide, PortLatching,
    RegisterBlock, RegisterEntry,
    DMAChannel, DMAMode,
    Chip, Board,
)
from proto.memory import (
    MemoryRegion, MemoryBank, MemoryBus, MemoryController,
    MemoryAccessLevel, Handler, HandlerType,
)
from proto.cpu import (
    CPUDefinition, OpcodeEntry, RegisterDef, RegisterPairDef, FlagDef,
)


# ===================================================================
# Clock
# ===================================================================

class TestClock:

    def test_master_clock(self):
        clk = Clock("master", frequency_hz=21_000_000)
        assert clk.name == "master"
        assert clk.frequency_hz == 21_000_000
        assert clk.is_master is True
        assert clk.parent is None
        assert clk.master_divider == 1

    def test_derive_with_divider(self):
        master = Clock("master", frequency_hz=21_000_000)
        cpu_clk = master.derive("cpu", divider=6)
        assert cpu_clk.frequency_hz == 3_500_000
        assert cpu_clk.parent is master
        assert cpu_clk.divider == 6
        assert cpu_clk.is_master is False

    def test_derive_with_multiplier(self):
        master = Clock("master", frequency_hz=10_000_000)
        fast_clk = master.derive("fast", multiplier=2)
        assert fast_clk.frequency_hz == 20_000_000

    def test_derive_with_divider_and_multiplier(self):
        master = Clock("master", frequency_hz=21_000_000)
        clk = master.derive("mixed", divider=3, multiplier=2)
        assert clk.frequency_hz == 14_000_000

    def test_master_divider_chain(self):
        master = Clock("master", frequency_hz=21_000_000)
        cpu = master.derive("cpu", divider=6)
        sub = cpu.derive("sub", divider=2)
        assert master.master_divider == 1
        assert cpu.master_divider == 6
        assert sub.master_divider == 12  # 6 * 2

    def test_children_tracking(self):
        master = Clock("master", frequency_hz=21_000_000)
        c1 = master.derive("c1", divider=6)
        c2 = master.derive("c2", divider=21)
        assert len(master.children) == 2
        assert c1 in master.children
        assert c2 in master.children

    def test_cycles_per(self):
        master = Clock("master", frequency_hz=21_000_000)
        cpu = master.derive("cpu", divider=6)  # 3.5 MHz
        spc = master.derive("spc", divider=21)  # 1.0 MHz
        assert cpu.cycles_per(spc) == pytest.approx(3.5, rel=1e-6)

    def test_cycles_per_zero(self):
        c = Clock("c", frequency_hz=0)
        assert c.cycles_per(c) == 0.0

    def test_repr_master(self):
        clk = Clock("master", frequency_hz=4_000_000)
        assert "master" in repr(clk)

    def test_repr_derived(self):
        master = Clock("master", frequency_hz=21_000_000)
        cpu = master.derive("cpu", divider=6)
        assert "/6" in repr(cpu)


# ===================================================================
# SignalLine
# ===================================================================

class TestSignalLine:

    def test_basic_creation(self):
        chip_a = Chip("cpu")
        chip_b = Chip("tmr")
        sig = SignalLine("irq", SignalType.Interrupt,
                         source=chip_b, sinks=[chip_a])
        assert sig.name == "irq"
        assert sig.signal_type == SignalType.Interrupt
        assert chip_b in sig.sources
        assert chip_a in sig.sinks

    def test_multiple_sources(self):
        cpu = Chip("cpu")
        tmr = Chip("tmr")
        ppu = Chip("ppu")
        sig = SignalLine("irq", SignalType.Interrupt,
                         sources=[tmr, ppu], sinks=[cpu])
        assert len(sig.sources) == 2

    def test_signal_types(self):
        for st in SignalType:
            sig = SignalLine("sig", st)
            assert sig.signal_type == st

    def test_edge_modes(self):
        for edge in SignalEdge:
            sig = SignalLine("sig", SignalType.Interrupt, edge=edge)
            assert sig.edge == edge

    def test_on_assert_decorator(self):
        cpu = Chip("cpu")
        tmr = Chip("tmr")
        sig = SignalLine("irq", SignalType.Interrupt,
                         source=tmr, sinks=[cpu])

        @sig.on_assert(cpu)
        def handler(cpu):
            cpu.halted = 0

        assert "cpu" in sig.on_assert_handlers
        h = sig.on_assert_handlers["cpu"]
        assert h.handler_type == HandlerType.Python
        assert h.func is handler

    def test_set_on_assert_raw(self):
        cpu = Chip("cpu")
        sig = SignalLine("irq", SignalType.Interrupt, sinks=[cpu])
        sig.set_on_assert_raw(cpu, "sys->cpu.halted = false;")
        h = sig.on_assert_handlers["cpu"]
        assert h.handler_type == HandlerType.RawC

    def test_active_low(self):
        sig = SignalLine("reset", SignalType.Reset, active_low=True)
        assert sig.active_low is True


# ===================================================================
# Port
# ===================================================================

class TestPort:

    def test_basic_port(self):
        chip_a = Chip("main")
        chip_b = Chip("snd")
        port = Port("comm",
                     side_a=PortSide(chip=chip_a, addr_start=0x2100, addr_end=0x2103),
                     side_b=PortSide(chip=chip_b, addr_start=0x00F4, addr_end=0x00F7))
        assert port.name == "comm"
        assert port.width == 4

    def test_independent_latching(self):
        port = Port("p", latching=PortLatching.Independent)
        assert port.latching == PortLatching.Independent

    def test_shared_latching(self):
        port = Port("p", latching=PortLatching.Shared)
        assert port.latching == PortLatching.Shared

    def test_port_side_width(self):
        ps = PortSide(addr_start=0x2100, addr_end=0x2103)
        assert ps.width == 4

    def test_port_side_no_addrs(self):
        ps = PortSide()
        assert ps.width == 0

    def test_port_width_from_side_a(self):
        port = Port("p",
                     side_a=PortSide(addr_start=0, addr_end=3),
                     side_b=None)
        assert port.width == 4

    def test_port_width_no_sides(self):
        port = Port("p")
        assert port.width == 0


# ===================================================================
# RegisterBlock
# ===================================================================

class TestRegisterBlock:

    def test_basic_creation(self):
        rb = RegisterBlock("io_regs", base_addr=0xFF00, size=16)
        assert rb.name == "io_regs"
        assert rb.base_addr == 0xFF00
        assert rb.size == 16
        assert rb.addr_end == 0xFF0F

    def test_bind_register(self):
        rb = RegisterBlock("io", base_addr=0xFF00, size=4)
        rb.bind(0, "counter", default="0", comment="Timer counter")
        assert 0 in rb.registers
        assert rb.registers[0].name == "counter"
        assert rb.registers[0].default == "0"

    def test_bind_read_only(self):
        rb = RegisterBlock("io", base_addr=0xFF00, size=4)
        rb.bind(0, "status", read_only=True)
        assert rb.registers[0].read_only is True

    def test_bind_write_only(self):
        rb = RegisterBlock("io", base_addr=0xFF00, size=4)
        rb.bind(0, "data", write_only=True)
        assert rb.registers[0].write_only is True

    def test_bind_write_mask(self):
        rb = RegisterBlock("io", base_addr=0xFF00, size=4)
        rb.bind(0, "ctrl", write_mask=(0xF0, 0x0F))
        assert rb.registers[0].write_mask == (0xF0, 0x0F)

    def test_on_write_decorator(self):
        rb = RegisterBlock("io", base_addr=0xFF00, size=4)

        @rb.on_write(0)
        def handler(chip, val):
            pass

        assert rb.registers[0].write_handler is not None
        assert rb.registers[0].write_handler.func is handler

    def test_on_read_decorator(self):
        rb = RegisterBlock("io", base_addr=0xFF00, size=4)

        @rb.on_read(0)
        def handler(chip):
            pass

        assert rb.registers[0].read_handler is not None

    def test_on_write_creates_entry_if_missing(self):
        rb = RegisterBlock("io", base_addr=0xFF00, size=4)

        @rb.on_write(2)
        def handler(chip, val):
            pass

        assert 2 in rb.registers

    def test_set_write_handler_raw(self):
        rb = RegisterBlock("io", base_addr=0xFF00, size=4)
        rb.set_write_handler_raw(0, "sys->ppu.ctrl = val;")
        assert rb.registers[0].write_handler.handler_type == HandlerType.RawC

    def test_set_read_handler_raw(self):
        rb = RegisterBlock("io", base_addr=0xFF00, size=4)
        rb.set_read_handler_raw(0, "return sys->ppu.status;")
        assert rb.registers[0].read_handler.handler_type == HandlerType.RawC

    def test_repr(self):
        rb = RegisterBlock("io", base_addr=0xFF00, size=16)
        s = repr(rb)
        assert "io" in s
        assert "FF00" in s


# ===================================================================
# DMAChannel
# ===================================================================

class TestDMAChannel:

    def test_basic_creation(self):
        dma = DMAChannel("gpdma", mode=DMAMode.OneShot, channels=8)
        assert dma.name == "gpdma"
        assert dma.mode == DMAMode.OneShot
        assert dma.channels == 8

    def test_modes(self):
        for mode in DMAMode:
            dma = DMAChannel("dma", mode=mode)
            assert dma.mode == mode

    def test_add_state(self):
        dma = DMAChannel("dma")
        dma.add_state("src_addr", "uint32_t", "0", "Source")
        assert len(dma.state_fields) == 1

    def test_transfer_handler_initially_none(self):
        dma = DMAChannel("dma")
        assert dma.transfer_handler is None


# ===================================================================
# Chip
# ===================================================================

class TestChip:

    def test_basic_creation(self):
        clk = Clock("cpu_clk", frequency_hz=4_000_000)
        chip = Chip("cpu", clock=clk, comment="Main CPU")
        assert chip.name == "cpu"
        assert chip.clock is clk
        assert chip.has_cpu is False

    def test_add_state(self):
        chip = Chip("ppu")
        chip.add_state("scanline", "uint16_t", "0", "Current scanline")
        assert len(chip.state_fields) == 1
        name, ctype, default, comment = chip.state_fields[0]
        assert name == "scanline"

    def test_set_cpu_core(self):
        chip = Chip("cpu")
        cpu_def = CPUDefinition("z80")
        chip.set_cpu_core(cpu_def)
        assert chip.has_cpu is True
        assert chip.cpu_core is cpu_def

    def test_no_cpu_core(self):
        chip = Chip("ppu")
        assert chip.has_cpu is False

    def test_set_bus(self):
        chip = Chip("cpu")
        bus = MemoryBus("main", address_bits=16)
        chip.set_bus(bus)
        assert chip.bus is bus

    def test_add_internal_memory(self):
        chip = Chip("cpu")
        r = MemoryRegion("ram", size_in_bytes=256)
        chip.add_internal_memory(r)
        assert len(chip.internal_memory) == 1
        assert chip.internal_memory[0] is r

    def test_add_memory_controller(self):
        chip = Chip("cpu")
        ctrl = MemoryController("mapper")
        chip.add_memory_controller(ctrl)
        assert len(chip.memory_controllers) == 1

    def test_add_register_block(self):
        chip = Chip("ppu")
        rb = RegisterBlock("ppu_io", base_addr=0xFF40, size=16)
        chip.add_register_block(rb)
        assert len(chip.register_blocks) == 1

    def test_add_dma(self):
        chip = Chip("cpu")
        dma = DMAChannel("oam_dma")
        chip.add_dma(dma)
        assert len(chip.dma_channels) == 1

    def test_add_helper_raw(self):
        chip = Chip("cpu")
        chip.add_helper("do_stuff", code="return;", returns="void")
        assert len(chip.helpers) == 1

    def test_helper_decorator(self):
        chip = Chip("cpu")

        @chip.helper("compute", returns="uint8_t",
                      params=[("val", "uint8_t")])
        def compute(cpu, val):
            return val + 1

        assert len(chip.helpers) == 1
        assert chip.helpers[0]["name"] == "compute"
        assert chip.helpers[0]["returns"] == "uint8_t"

    def test_tick_decorator(self):
        chip = Chip("tmr")

        @chip.tick()
        def tick_handler(timer, cycles):
            pass

        assert chip.tick_handler is not None
        assert chip.tick_handler.handler_type == HandlerType.Python

    def test_set_tick_raw(self):
        chip = Chip("tmr")
        chip.set_tick(code="/* tick */")
        assert chip.tick_handler is not None
        assert chip.tick_handler.handler_type == HandlerType.RawC

    def test_set_init(self):
        chip = Chip("cpu")
        chip.set_init(code="sys->cpu.PC = 0x100;")
        assert chip.init_handler is not None

    def test_repr(self):
        chip = Chip("cpu", clock=Clock("clk", 4000000))
        s = repr(chip)
        assert "cpu" in s


# ===================================================================
# Board
# ===================================================================

class TestBoard:

    def _make_minimal_board(self):
        master = Clock("master", frequency_hz=4_000_000)
        bus = MemoryBus("main", address_bits=16)
        chip = Chip("cpu", clock=master)
        cpu_def = CPUDefinition("z80")
        chip.set_cpu_core(cpu_def)
        chip.set_bus(bus)
        board = Board("TestBoard")
        board.set_master_clock(master)
        board.add_chip(chip)
        board.add_bus(bus)
        return board

    def test_basic_creation(self):
        board = Board("GameBoy")
        assert board.name == "GameBoy"
        assert board.chips == []
        assert board.buses == []
        assert board.ports == []
        assert board.signals == []

    def test_set_master_clock(self):
        board = Board("GB")
        clk = Clock("master", 4_000_000)
        board.set_master_clock(clk)
        assert board.master_clock is clk

    def test_add_chip(self):
        board = Board("GB")
        chip = Chip("cpu")
        board.add_chip(chip)
        assert len(board.chips) == 1

    def test_get_chip(self):
        board = Board("GB")
        chip = Chip("cpu")
        board.add_chip(chip)
        assert board.get_chip("cpu") is chip
        assert board.get_chip("ppu") is None

    def test_add_bus(self):
        board = Board("GB")
        bus = MemoryBus("main", address_bits=16)
        board.add_bus(bus)
        assert len(board.buses) == 1

    def test_add_port(self):
        board = Board("SNES")
        port = Port("comm")
        board.add_port(port)
        assert len(board.ports) == 1

    def test_add_signal(self):
        board = Board("GB")
        sig = SignalLine("vblank", SignalType.Interrupt)
        board.add_signal(sig)
        assert len(board.signals) == 1

    def test_add_extern_func(self):
        board = Board("GB")
        board.add_extern_func("printf")
        assert "printf" in board.extern_funcs

    def test_cpu_chips(self):
        board = Board("GB")
        cpu_chip = Chip("cpu")
        cpu_chip.set_cpu_core(CPUDefinition("z80"))
        ppu_chip = Chip("ppu")
        board.add_chip(cpu_chip)
        board.add_chip(ppu_chip)
        assert len(board.cpu_chips) == 1
        assert board.cpu_chips[0] is cpu_chip

    def test_peripheral_chips(self):
        board = Board("GB")
        cpu_chip = Chip("cpu")
        cpu_chip.set_cpu_core(CPUDefinition("z80"))
        ppu_chip = Chip("ppu")
        board.add_chip(cpu_chip)
        board.add_chip(ppu_chip)
        assert len(board.peripheral_chips) == 1
        assert board.peripheral_chips[0] is ppu_chip

    def test_validate_no_clock(self):
        board = Board("bad")
        board.add_chip(Chip("cpu"))
        board.add_bus(MemoryBus("main"))
        errors = board.validate()
        assert any("clock" in e.lower() for e in errors)

    def test_validate_no_chips(self):
        board = Board("bad")
        board.set_master_clock(Clock("m", 1000))
        board.add_bus(MemoryBus("main"))
        errors = board.validate()
        assert any("chip" in e.lower() for e in errors)

    def test_validate_no_buses(self):
        board = Board("bad")
        board.set_master_clock(Clock("m", 1000))
        board.add_chip(Chip("cpu"))
        errors = board.validate()
        assert any("bus" in e.lower() for e in errors)

    def test_validate_no_cpu(self):
        board = Board("bad")
        board.set_master_clock(Clock("m", 1000))
        board.add_chip(Chip("ppu"))
        board.add_bus(MemoryBus("main"))
        errors = board.validate()
        assert any("cpu" in e.lower() for e in errors)

    def test_validate_chip_no_clock(self):
        board = Board("bad")
        board.set_master_clock(Clock("m", 1000))
        chip = Chip("cpu")  # No clock!
        chip.set_cpu_core(CPUDefinition("z80"))
        board.add_chip(chip)
        board.add_bus(MemoryBus("main"))
        errors = board.validate()
        assert any("clock" in e.lower() for e in errors)

    def test_validate_cpu_no_bus(self):
        board = Board("bad")
        master = Clock("m", 1000)
        board.set_master_clock(master)
        chip = Chip("cpu", clock=master)
        chip.set_cpu_core(CPUDefinition("z80"))
        # chip.set_bus() not called!
        board.add_chip(chip)
        board.add_bus(MemoryBus("main"))
        errors = board.validate()
        assert any("bus" in e.lower() for e in errors)

    def test_validate_clean(self):
        board = self._make_minimal_board()
        errors = board.validate()
        assert errors == []

    def test_repr(self):
        board = self._make_minimal_board()
        s = repr(board)
        assert "TestBoard" in s


# ===================================================================
# CPUDefinition
# ===================================================================

class TestCPUDefinition:

    def test_basic_creation(self):
        cpu = CPUDefinition("z80", data_width=8, address_width=16)
        assert cpu.name == "z80"
        assert cpu.data_width == 8
        assert cpu.address_width == 16
        assert len(cpu.registers) == 0
        assert len(cpu.opcodes) == 0

    def test_builtin_state(self):
        cpu = CPUDefinition("z80")
        names = [s[0] for s in cpu.builtin_state]
        assert "PC" in names
        assert "SP" in names
        assert "cycle_count" in names
        assert "halted" in names

    def test_add_register(self):
        cpu = CPUDefinition("z80")
        cpu.add_register("A", 8)
        assert len(cpu.registers) == 1
        assert cpu.registers[0].name == "A"
        assert cpu.registers[0].bits == 8

    def test_register_c_type(self):
        r8 = RegisterDef("A", 8)
        assert r8.c_type == "uint8_t"
        r16 = RegisterDef("HL", 16)
        assert r16.c_type == "uint16_t"
        r32 = RegisterDef("EAX", 32)
        assert r32.c_type == "uint32_t"

    def test_register_default(self):
        cpu = CPUDefinition("z80")
        cpu.add_register("A", 8, default="0xFF")
        assert cpu.registers[0].default == "0xFF"

    def test_add_register_pair(self):
        cpu = CPUDefinition("z80")
        cpu.add_register("H", 8)
        cpu.add_register("L", 8)
        cpu.add_register_pair("HL", "H", "L")
        assert len(cpu.register_pairs) == 1
        rp = cpu.register_pairs[0]
        assert rp.name == "HL"
        assert rp.high == "H"
        assert rp.low == "L"

    def test_set_flags(self):
        cpu = CPUDefinition("z80")
        cpu.set_flags("F", {"Z": 7, "N": 6, "H": 5, "C": 4})
        assert cpu.flag_def is not None
        assert cpu.flag_def.register == "F"
        assert cpu.flag_def.flags["Z"] == 7

    def test_opcode_decorator(self):
        cpu = CPUDefinition("z80")

        @cpu.opcode(0x00, "NOP", cycles=4)
        def nop(cpu):
            pass

        assert 0x00 in cpu.opcodes
        entry = cpu.opcodes[0x00]
        assert entry.code == 0x00
        assert entry.mnemonic == "NOP"
        assert entry.cycles == 4
        assert entry.func is nop
        assert entry.is_transpiled is True

    def test_add_opcode_raw(self):
        cpu = CPUDefinition("z80")
        cpu.add_opcode_raw(0xFF, "RST 38", cycles=16, c_code="push16(sys, sys->cpu.PC);")
        entry = cpu.opcodes[0xFF]
        assert entry.c_code is not None
        assert entry.is_transpiled is False

    def test_opcode_family(self):
        cpu = CPUDefinition("z80")
        cpu.add_register("A", 8)
        cpu.add_register("B", 8)

        @cpu.opcode_family("LD {},{}", variants=[
            (0x78, "A", "B"),
            (0x79, "A", "C"),
        ], cycles=4)
        def ld_r_r(cpu, dst, src):
            pass

        assert 0x78 in cpu.opcodes
        assert 0x79 in cpu.opcodes
        assert cpu.opcodes[0x78].mnemonic == "LD A,B"
        assert cpu.opcodes[0x79].mnemonic == "LD A,C"
        assert cpu.opcodes[0x78].variant_args == ("A", "B")

    def test_prefix_opcode(self):
        cpu = CPUDefinition("z80")

        @cpu.prefix_opcode(0xCB, 0x7F, "BIT 7,A", cycles=8)
        def bit_7_a(cpu):
            pass

        assert 0xCB in cpu.prefix_tables
        assert 0x7F in cpu.prefix_tables[0xCB]
        entry = cpu.prefix_tables[0xCB][0x7F]
        assert entry.mnemonic == "BIT 7,A"

    def test_add_prefix_table(self):
        cpu = CPUDefinition("z80")
        cpu.add_prefix_table(0xCB)
        assert 0xCB in cpu.prefix_tables
        assert cpu.prefix_tables[0xCB] == {}

    def test_all_register_names(self):
        cpu = CPUDefinition("z80")
        cpu.add_register("A", 8)
        cpu.add_register("H", 8)
        cpu.add_register("L", 8)
        cpu.add_register_pair("HL", "H", "L")
        names = cpu.all_register_names
        assert "A" in names
        assert "H" in names
        assert "L" in names
        assert "HL" in names

    def test_address_width_types(self):
        cpu8 = CPUDefinition("tiny", address_width=8)
        cpu16 = CPUDefinition("z80", address_width=16)
        cpu32 = CPUDefinition("arm", address_width=32)
        # Check PC type in builtin state
        pc_types = {}
        for cpu in [cpu8, cpu16, cpu32]:
            for name, ctype, _, _ in cpu.builtin_state:
                if name == "PC":
                    pc_types[cpu.name] = ctype
        assert pc_types["tiny"] == "uint8_t"
        assert pc_types["z80"] == "uint16_t"
        assert pc_types["arm"] == "uint32_t"

    def test_repr(self):
        cpu = CPUDefinition("z80")
        cpu.add_register("A", 8)
        cpu.add_opcode_raw(0x00, "NOP", 4, "")
        s = repr(cpu)
        assert "z80" in s
        assert "1 regs" in s
        assert "1 opcodes" in s


# ===================================================================
# OpcodeEntry
# ===================================================================

class TestOpcodeEntry:

    def test_basic_entry(self):
        entry = OpcodeEntry(code=0x3E, mnemonic="LD A,d8", cycles=8)
        assert entry.code == 0x3E
        assert entry.mnemonic == "LD A,d8"
        assert entry.cycles == 8
        assert entry.is_transpiled is False
        assert entry.func is None
        assert entry.c_code is None

    def test_with_func(self):
        def my_func(cpu):
            pass
        entry = OpcodeEntry(code=0x00, mnemonic="NOP", cycles=4, func=my_func)
        assert entry.is_transpiled is True

    def test_with_c_code(self):
        entry = OpcodeEntry(code=0x00, mnemonic="NOP", cycles=4,
                            c_code="/* nop */")
        assert entry.is_transpiled is False
        assert entry.c_code == "/* nop */"

    def test_repr(self):
        entry = OpcodeEntry(code=0xCB, mnemonic="PREFIX CB", cycles=0)
        s = repr(entry)
        assert "0xCB" in s
        assert "PREFIX CB" in s
