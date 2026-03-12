"""
Tier 3 -- SNES-specific abstraction tests.

Tests for:
  Phase 0: push8, pop8, mem_read16 convenience functions
  Phase 1: 24-bit address formatting
  Phase 2: DMA code generation (data model + codegen)
  Phase 3: Interrupt vector table (data model + codegen)
  Regression: existing examples still generate valid C
"""

import os
import shutil
import subprocess
import sys
import tempfile
import pytest

from proto.memory import (
    MemoryRegion, MemoryBank, MemoryBus, MemoryController,
    MemoryAccessLevel, BusMaster, Handler, HandlerType,
)
from proto.hardware import (
    Clock, Chip, Board, RegisterBlock, DMAChannel, DMAMode,
    SignalLine, SignalType, SignalEdge,
)
from proto.cpu import CPUDefinition, InterruptVector
from proto.codegen import BoardCodeGenerator
from proto.transpiler import Transpiler


# ===================================================================
# Helpers
# ===================================================================

def _make_minimal_board(cycle_accurate=False, address_bits=16):
    """Create a minimal board for testing."""
    clk = Clock("master", 4_000_000)
    ram = MemoryRegion("ram", 256, MemoryAccessLevel.ReadWrite)
    rom = MemoryRegion("rom", 1024, MemoryAccessLevel.ReadOnly)

    cpu_def = CPUDefinition("test8", data_width=8, address_width=address_bits)
    cpu_def.add_register("A", 8)
    cpu_def.add_register("X", 8)
    cpu_def.set_flags("F", {"Z": 7, "C": 0})

    @cpu_def.opcode(0x00, "NOP", cycles=1)
    def nop(cpu):
        pass

    @cpu_def.opcode(0x01, "LDA #imm8", cycles=2)
    def lda(cpu):
        cpu.A = read_imm8()

    @cpu_def.opcode(0x0F, "HALT", cycles=1)
    def halt(cpu):
        cpu.halted = 1

    cpu_chip = Chip("cpu", clock=clk)
    cpu_chip.set_cpu_core(cpu_def)
    cpu_chip.add_internal_memory(ram)
    cpu_chip.add_internal_memory(rom)

    bus = MemoryBus("main", address_bits=address_bits)
    cpu_chip.set_bus(bus)
    bus.map(0x0000, 0x00FF, region=ram, offset=0, comment="RAM")
    bus.map(0x8000, 0x83FF, region=rom, offset=0, comment="ROM")
    bus.set_fallback(read=0xFF)

    board = Board("Test", comment="Test", cycle_accurate=cycle_accurate)
    board.set_master_clock(clk)
    board.add_chip(cpu_chip)
    board.add_bus(bus)
    board.add_extern_func("printf")
    return board, cpu_def, cpu_chip


def _gen(board):
    """Generate C code from a board."""
    return BoardCodeGenerator(board).generate()


def _find_func_body(code, signature_prefix):
    """Extract a C function body from generated code."""
    search_from = 0
    while True:
        idx = code.index(signature_prefix, search_from)
        eol = code.index('\n', idx)
        line = code[idx:eol]
        if line.rstrip().endswith('{'):
            break
        if line.rstrip().endswith(';'):
            search_from = eol + 1
            continue
        break
    end = code.index("\n}", idx)
    return code[idx:end + 2]


# ===================================================================
# Phase 0: push8, pop8, mem_read16
# ===================================================================

class TestPush8Pop8Codegen:

    def test_push8_forward_decl(self):
        board, _, _ = _make_minimal_board()
        code = _gen(board)
        assert "static void cpu_push8(test_t* sys, uint8_t val);" in code

    def test_pop8_forward_decl(self):
        board, _, _ = _make_minimal_board()
        code = _gen(board)
        assert "static uint8_t cpu_pop8(test_t* sys);" in code

    def test_mem_read16_forward_decl(self):
        board, _, _ = _make_minimal_board()
        code = _gen(board)
        assert "static uint16_t cpu_mem_read16(test_t* sys, uint16_t addr);" in code

    def test_push8_function_body(self):
        board, _, _ = _make_minimal_board()
        code = _gen(board)
        body = _find_func_body(code, "static void cpu_push8(")
        assert "sys->cpu.SP--" in body
        assert "mem_write(sys, sys->cpu.SP, val)" in body

    def test_pop8_function_body(self):
        board, _, _ = _make_minimal_board()
        code = _gen(board)
        body = _find_func_body(code, "static uint8_t cpu_pop8(")
        assert "mem_read(sys, sys->cpu.SP++)" in body

    def test_mem_read16_function_body(self):
        board, _, _ = _make_minimal_board()
        code = _gen(board)
        body = _find_func_body(code, "static uint16_t cpu_mem_read16(")
        assert "mem_read(sys, addr)" in body
        assert "mem_read(sys, addr + 1)" in body
        assert "((uint16_t)hi << 8) | lo" in body

    def test_single_cpu_aliases(self):
        """Single-CPU board gets global push8/pop8/mem_read16 aliases."""
        board, _, _ = _make_minimal_board()
        code = _gen(board)
        assert "static void push8(test_t* sys, uint8_t val)" in code
        assert "static uint8_t pop8(test_t* sys)" in code
        assert "static uint16_t mem_read16(test_t* sys, uint16_t addr)" in code


class TestPush8Pop8Transpiler:

    def test_mem_read16_prepends_sys(self):
        def f(cpu):
            x = mem_read16(0x1234)
        t = Transpiler(self_param="cpu", chip_name="cpu")
        result = t.transpile_function(f)
        assert "mem_read16(sys, 0x1234)" in result

    def test_push8_remapped_multi_cpu(self):
        def f(cpu):
            push8(42)
        t = Transpiler(
            self_param="cpu", chip_name="main",
            func_remap={"push8": "main_push8"},
        )
        result = t.transpile_function(f)
        assert "main_push8(sys, 42)" in result

    def test_pop8_remapped_multi_cpu(self):
        def f(cpu):
            x = pop8()
        t = Transpiler(
            self_param="cpu", chip_name="main",
            func_remap={"pop8": "main_pop8"},
        )
        result = t.transpile_function(f)
        assert "main_pop8(sys)" in result

    def test_mem_read16_inferred_uint16(self):
        def f(cpu):
            x = mem_read16(0x1234)
        t = Transpiler(self_param="cpu", chip_name="cpu")
        result = t.transpile_function(f)
        assert "uint16_t x" in result

    def test_push8_in_remappable_funcs(self):
        """push8/pop8/mem_read16 are in REMAPPABLE_FUNCS."""
        from proto.transpiler import REMAPPABLE_FUNCS
        assert "push8" in REMAPPABLE_FUNCS
        assert "pop8" in REMAPPABLE_FUNCS
        assert "mem_read16" in REMAPPABLE_FUNCS


# ===================================================================
# Phase 1: 24-bit address formatting
# ===================================================================

class Test24BitAddressing:

    def test_16bit_uses_4digit_hex(self):
        board, _, _ = _make_minimal_board(address_bits=16)
        code = _gen(board)
        assert "0x0000" in code
        assert "0x00FF" in code
        assert "0x8000" in code

    def test_24bit_uses_6digit_hex(self):
        """24-bit bus uses 0x000000 format for addresses."""
        clk = Clock("master", 4_000_000)
        ram = MemoryRegion("ram", 256, MemoryAccessLevel.ReadWrite)
        rom = MemoryRegion("rom", 1024, MemoryAccessLevel.ReadOnly)

        cpu_def = CPUDefinition("test24", data_width=8, address_width=24)
        cpu_def.add_register("A", 8)
        cpu_def.set_flags("F", {"Z": 7})

        @cpu_def.opcode(0x00, "NOP", cycles=1)
        def nop(cpu):
            pass

        cpu_chip = Chip("cpu", clock=clk)
        cpu_chip.set_cpu_core(cpu_def)
        cpu_chip.add_internal_memory(ram)
        cpu_chip.add_internal_memory(rom)

        bus = MemoryBus("main", address_bits=24)
        cpu_chip.set_bus(bus)
        bus.map(0x7E0000, 0x7E00FF, region=ram, offset=0)
        bus.map(0x008000, 0x0083FF, region=rom, offset=0)
        bus.set_fallback(read=0xFF)

        board = Board("Test24", comment="24-bit test")
        board.set_master_clock(clk)
        board.add_chip(cpu_chip)
        board.add_bus(bus)
        board.add_extern_func("printf")

        code = _gen(board)
        assert "0x7E0000" in code
        assert "0x7E00FF" in code
        assert "0x008000" in code
        assert "0x0083FF" in code

    def test_24bit_addr_type_uint32(self):
        """24-bit bus uses uint32_t for addresses."""
        bus = MemoryBus("test", address_bits=24)
        assert bus.addr_type == "uint32_t"

    def test_16bit_addr_type_uint16(self):
        bus = MemoryBus("test", address_bits=16)
        assert bus.addr_type == "uint16_t"

    def test_24bit_pc_printf_format(self):
        """24-bit CPU uses %06X for PC in error messages."""
        clk = Clock("master", 4_000_000)
        ram = MemoryRegion("ram", 256, MemoryAccessLevel.ReadWrite)

        cpu_def = CPUDefinition("test24", data_width=8, address_width=24)
        cpu_def.add_register("A", 8)

        @cpu_def.opcode(0x00, "NOP", cycles=1)
        def nop(cpu):
            pass

        cpu_chip = Chip("cpu", clock=clk)
        cpu_chip.set_cpu_core(cpu_def)
        cpu_chip.add_internal_memory(ram)

        bus = MemoryBus("main", address_bits=24)
        cpu_chip.set_bus(bus)
        bus.map(0x000000, 0x0000FF, region=ram, offset=0)
        bus.set_fallback(read=0xFF)

        board = Board("Test24", comment="24-bit test")
        board.set_master_clock(clk)
        board.add_chip(cpu_chip)
        board.add_bus(bus)
        board.add_extern_func("printf")

        code = _gen(board)
        assert "PC=0x%06X" in code


# ===================================================================
# Phase 2: DMA code generation
# ===================================================================

class TestDMADataModel:

    def test_dma_channel_creation(self):
        dma = DMAChannel("gpdma", mode=DMAMode.OneShot, channels=8)
        assert dma.name == "gpdma"
        assert dma.mode == DMAMode.OneShot
        assert dma.channels == 8

    def test_dma_add_state(self):
        dma = DMAChannel("gpdma")
        dma.add_state("src_addr", "uint32_t", "0", "Source address")
        dma.add_state("count", "uint16_t", "0", "Transfer count")
        assert len(dma.state_fields) == 2
        assert dma.state_fields[0] == ("src_addr", "uint32_t", "0", "Source address")

    def test_dma_transfer_decorator(self):
        dma = DMAChannel("gpdma")

        @dma.transfer()
        def do_transfer(chip):
            pass

        assert dma.transfer_handler is not None
        assert dma.transfer_handler.handler_type == HandlerType.Python

    def test_dma_set_transfer_raw(self):
        dma = DMAChannel("gpdma")
        dma.set_transfer_raw("/* raw DMA */")
        assert dma.transfer_handler is not None
        assert dma.transfer_handler.handler_type == HandlerType.RawC
        assert dma.transfer_handler.code == "/* raw DMA */"


class TestDMACodegen:

    def _make_dma_board(self, raw_handler=True, multi_channel=False):
        clk = Clock("master", 4_000_000)
        ram = MemoryRegion("ram", 256, MemoryAccessLevel.ReadWrite)

        cpu_def = CPUDefinition("test8", data_width=8, address_width=16)
        cpu_def.add_register("A", 8)

        @cpu_def.opcode(0x00, "NOP", cycles=1)
        def nop(cpu):
            pass

        cpu_chip = Chip("cpu", clock=clk)
        cpu_chip.set_cpu_core(cpu_def)
        cpu_chip.add_internal_memory(ram)

        channels = 4 if multi_channel else 1
        dma = DMAChannel("gpdma", mode=DMAMode.OneShot, channels=channels)
        dma.add_state("src_addr", "uint32_t", "0", "Source address")
        dma.add_state("count", "uint16_t", "0", "Transfer count")

        if raw_handler:
            dma.set_transfer_raw("/* DMA transfer unit */")
        cpu_chip.add_dma(dma)

        bus = MemoryBus("main", address_bits=16)
        cpu_chip.set_bus(bus)
        bus.map(0x0000, 0x00FF, region=ram, offset=0)
        bus.set_fallback(read=0xFF)
        bus.add_master("cpu", priority=0)
        bus.add_master("dma", priority=1)

        board = Board("DMATest", comment="DMA test",
                      cycle_accurate=True)
        board.set_master_clock(clk)
        board.add_chip(cpu_chip)
        board.add_bus(bus)
        board.add_extern_func("printf")
        return board

    def test_dma_state_fields_in_struct(self):
        board = self._make_dma_board()
        code = _gen(board)
        assert "uint32_t gpdma_src_addr;" in code
        assert "uint16_t gpdma_count;" in code

    def test_dma_multi_channel_arrays(self):
        board = self._make_dma_board(multi_channel=True)
        code = _gen(board)
        assert "uint32_t gpdma_src_addr[4];" in code
        assert "uint16_t gpdma_count[4];" in code

    def test_dma_transfer_forward_decl(self):
        board = self._make_dma_board()
        code = _gen(board)
        assert "static void gpdma_transfer(dmatest_t* sys);" in code

    def test_dma_transfer_function_generated(self):
        board = self._make_dma_board()
        code = _gen(board)
        body = _find_func_body(code, "static void gpdma_transfer(")
        assert "/* DMA transfer unit */" in body

    def test_dma_step_integration(self):
        """DMA transfer called from step when dma_active."""
        board = self._make_dma_board()
        code = _gen(board)
        step_body = _find_func_body(code, "static void dmatest_step(")
        assert "main_dma_active" in step_body
        assert "gpdma_transfer(sys)" in step_body

    def test_dma_no_transfer_without_handler(self):
        """DMA without transfer handler: no transfer function generated."""
        clk = Clock("master", 4_000_000)
        ram = MemoryRegion("ram", 256, MemoryAccessLevel.ReadWrite)
        cpu_def = CPUDefinition("test8", data_width=8, address_width=16)
        cpu_def.add_register("A", 8)

        @cpu_def.opcode(0x00, "NOP", cycles=1)
        def nop(cpu):
            pass

        cpu_chip = Chip("cpu", clock=clk)
        cpu_chip.set_cpu_core(cpu_def)
        cpu_chip.add_internal_memory(ram)

        dma = DMAChannel("gpdma")
        # No transfer handler set
        cpu_chip.add_dma(dma)

        bus = MemoryBus("main", address_bits=16)
        cpu_chip.set_bus(bus)
        bus.map(0x0000, 0x00FF, region=ram, offset=0)
        bus.set_fallback(read=0xFF)

        board = Board("DMATest", comment="test")
        board.set_master_clock(clk)
        board.add_chip(cpu_chip)
        board.add_bus(bus)
        board.add_extern_func("printf")

        code = _gen(board)
        assert "gpdma_transfer" not in code

    def test_dma_init_defaults(self):
        """DMA state fields with non-zero defaults are initialized."""
        clk = Clock("master", 4_000_000)
        ram = MemoryRegion("ram", 256, MemoryAccessLevel.ReadWrite)
        cpu_def = CPUDefinition("test8", data_width=8, address_width=16)
        cpu_def.add_register("A", 8)

        @cpu_def.opcode(0x00, "NOP", cycles=1)
        def nop(cpu):
            pass

        cpu_chip = Chip("cpu", clock=clk)
        cpu_chip.set_cpu_core(cpu_def)
        cpu_chip.add_internal_memory(ram)

        dma = DMAChannel("gpdma")
        dma.add_state("mode", "uint8_t", "3", "DMA mode")
        cpu_chip.add_dma(dma)

        bus = MemoryBus("main", address_bits=16)
        cpu_chip.set_bus(bus)
        bus.map(0x0000, 0x00FF, region=ram, offset=0)
        bus.set_fallback(read=0xFF)

        board = Board("DMATest", comment="test")
        board.set_master_clock(clk)
        board.add_chip(cpu_chip)
        board.add_bus(bus)
        board.add_extern_func("printf")

        code = _gen(board)
        init = _find_func_body(code, "static void dmatest_init(")
        assert "sys->cpu.gpdma_mode = 3" in init

    def test_dma_init_multi_channel_defaults(self):
        """Multi-channel DMA with non-zero defaults inits each channel."""
        clk = Clock("master", 4_000_000)
        ram = MemoryRegion("ram", 256, MemoryAccessLevel.ReadWrite)
        cpu_def = CPUDefinition("test8", data_width=8, address_width=16)
        cpu_def.add_register("A", 8)

        @cpu_def.opcode(0x00, "NOP", cycles=1)
        def nop(cpu):
            pass

        cpu_chip = Chip("cpu", clock=clk)
        cpu_chip.set_cpu_core(cpu_def)
        cpu_chip.add_internal_memory(ram)

        dma = DMAChannel("gpdma", channels=3)
        dma.add_state("mode", "uint8_t", "1", "DMA mode")
        cpu_chip.add_dma(dma)

        bus = MemoryBus("main", address_bits=16)
        cpu_chip.set_bus(bus)
        bus.map(0x0000, 0x00FF, region=ram, offset=0)
        bus.set_fallback(read=0xFF)

        board = Board("DMATest", comment="test")
        board.set_master_clock(clk)
        board.add_chip(cpu_chip)
        board.add_bus(bus)
        board.add_extern_func("printf")

        code = _gen(board)
        init = _find_func_body(code, "static void dmatest_init(")
        assert "sys->cpu.gpdma_mode[0] = 1" in init
        assert "sys->cpu.gpdma_mode[1] = 1" in init
        assert "sys->cpu.gpdma_mode[2] = 1" in init


# ===================================================================
# Phase 3: Interrupt vector table
# ===================================================================

class TestInterruptVectorDataModel:

    def test_interrupt_vector_creation(self):
        iv = InterruptVector(
            name="NMI", address=0xFFEA, priority=1,
            signal_name="nmi", push_sequence=["PC", "F"],
            set_flags_on_entry={"I": 1},
        )
        assert iv.name == "NMI"
        assert iv.address == 0xFFEA
        assert iv.priority == 1
        assert iv.signal_name == "nmi"
        assert iv.push_sequence == ["PC", "F"]
        assert iv.set_flags_on_entry == {"I": 1}
        assert not iv.is_software

    def test_software_interrupt(self):
        iv = InterruptVector(name="BRK", address=0xFFFE, is_software=True)
        assert iv.is_software

    def test_cpu_add_interrupt_vector(self):
        cpu_def = CPUDefinition("test", data_width=8, address_width=16)
        cpu_def.add_interrupt_vector("NMI", 0xFFEA, priority=1)
        cpu_def.add_interrupt_vector("IRQ", 0xFFEE, priority=0)
        assert len(cpu_def.interrupt_vectors) == 2
        assert cpu_def.interrupt_vectors[0].name == "NMI"
        assert cpu_def.interrupt_vectors[1].name == "IRQ"

    def test_cpu_default_no_interrupt_vectors(self):
        cpu_def = CPUDefinition("test", data_width=8, address_width=16)
        assert cpu_def.interrupt_vectors == []


class TestInterruptCodegen:

    def _make_interrupt_board(self, with_flags=True):
        clk = Clock("master", 4_000_000)
        ram = MemoryRegion("ram", 256, MemoryAccessLevel.ReadWrite)
        rom = MemoryRegion("rom", 65536, MemoryAccessLevel.ReadOnly)

        cpu_def = CPUDefinition("test8", data_width=8, address_width=16)
        cpu_def.add_register("A", 8)
        if with_flags:
            cpu_def.set_flags("P", {"Z": 7, "I": 2, "D": 3})

        @cpu_def.opcode(0x00, "NOP", cycles=1)
        def nop(cpu):
            pass

        @cpu_def.opcode(0x0F, "HALT", cycles=1)
        def halt(cpu):
            cpu.halted = 1

        # Add interrupt vectors
        cpu_def.add_interrupt_vector(
            "NMI", address=0xFFEA, priority=1,
            signal_name="nmi",
            push_sequence=["PC", "P"],
            set_flags_on_entry={"I": 1},
        )
        cpu_def.add_interrupt_vector(
            "IRQ", address=0xFFEE, priority=0,
            signal_name="irq",
            push_sequence=["PC", "P"],
            set_flags_on_entry={"I": 1, "D": 0},
        )
        # Software interrupt (should NOT appear in check_interrupts)
        cpu_def.add_interrupt_vector(
            "BRK", address=0xFFFE, is_software=True,
        )

        cpu_chip = Chip("cpu", clock=clk)
        cpu_chip.set_cpu_core(cpu_def)
        cpu_chip.add_internal_memory(ram)
        cpu_chip.add_internal_memory(rom)

        bus = MemoryBus("main", address_bits=16)
        cpu_chip.set_bus(bus)
        bus.map(0x0000, 0x00FF, region=ram, offset=0)
        bus.map(0x0000, 0xFFFF, region=rom, offset=0)
        bus.set_fallback(read=0xFF)

        # Signal lines for NMI and IRQ
        nmi_sig = SignalLine("nmi", SignalType.NonMaskableInterrupt)
        irq_sig = SignalLine("irq", SignalType.Interrupt)

        board = Board("IntTest", comment="Interrupt test")
        board.set_master_clock(clk)
        board.add_chip(cpu_chip)
        board.add_bus(bus)
        board.add_signal(nmi_sig)
        board.add_signal(irq_sig)
        board.add_extern_func("printf")
        return board

    def test_check_interrupts_forward_decl(self):
        board = self._make_interrupt_board()
        code = _gen(board)
        assert "static void cpu_check_interrupts(inttest_t* sys);" in code

    def test_check_interrupts_function_exists(self):
        board = self._make_interrupt_board()
        code = _gen(board)
        body = _find_func_body(code, "static void cpu_check_interrupts(")
        assert "nmi_asserted" in body
        assert "irq_asserted" in body

    def test_nmi_higher_priority_checked_first(self):
        """NMI (priority 1) should appear before IRQ (priority 0)."""
        board = self._make_interrupt_board()
        code = _gen(board)
        body = _find_func_body(code, "static void cpu_check_interrupts(")
        nmi_pos = body.index("nmi_asserted")
        irq_pos = body.index("irq_asserted")
        assert nmi_pos < irq_pos

    def test_push_sequence_generates_push_calls(self):
        board = self._make_interrupt_board()
        code = _gen(board)
        body = _find_func_body(code, "static void cpu_check_interrupts(")
        # PC is 16-bit builtin -> push16
        assert "cpu_push16(sys, sys->cpu.PC)" in body
        # P is 8-bit flag register -> push8
        assert "cpu_push8(sys, sys->cpu.P)" in body

    def test_set_flags_on_entry(self):
        board = self._make_interrupt_board()
        code = _gen(board)
        body = _find_func_body(code, "static void cpu_check_interrupts(")
        assert "cpu_set_I(sys, 1)" in body
        # IRQ also sets D=0
        assert "cpu_set_D(sys, 0)" in body

    def test_vector_address_loaded(self):
        board = self._make_interrupt_board()
        code = _gen(board)
        body = _find_func_body(code, "static void cpu_check_interrupts(")
        assert "cpu_mem_read16(sys, 0xFFEA)" in body  # NMI
        assert "cpu_mem_read16(sys, 0xFFEE)" in body  # IRQ

    def test_software_interrupt_excluded(self):
        """Software interrupts (BRK) should NOT appear in check_interrupts."""
        board = self._make_interrupt_board()
        code = _gen(board)
        body = _find_func_body(code, "static void cpu_check_interrupts(")
        assert "BRK" not in body
        assert "0xFFFE" not in body

    def test_check_interrupts_called_in_step(self):
        """cpu_step should call check_interrupts before opcode fetch."""
        board = self._make_interrupt_board()
        code = _gen(board)
        step_body = _find_func_body(code, "static void cpu_step(")
        # check_interrupts should come before opcode fetch
        check_pos = step_body.index("cpu_check_interrupts(sys)")
        opcode_pos = step_body.index("uint8_t opcode")
        assert check_pos < opcode_pos

    def test_signal_clears_on_service(self):
        """Interrupt signal should be cleared when serviced."""
        board = self._make_interrupt_board()
        code = _gen(board)
        body = _find_func_body(code, "static void cpu_check_interrupts(")
        assert "sys->nmi_asserted = false" in body
        assert "sys->irq_asserted = false" in body

    def test_no_check_interrupts_without_vectors(self):
        """CPU without interrupt vectors should not generate check_interrupts."""
        board, _, _ = _make_minimal_board()
        code = _gen(board)
        assert "check_interrupts" not in code


# ===================================================================
# Regression: existing examples still generate valid C
# ===================================================================

class TestRegressionExistingExamples:

    def test_cycle_accurate_example_generates(self):
        """cycle_accurate.py example still generates valid C."""
        # Import and generate
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "cycle_accurate",
            os.path.join(os.path.dirname(__file__), "..", "examples", "cycle_accurate.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        gen = BoardCodeGenerator(mod.board)
        code = gen.generate() + mod.generate_main()
        # Verify key markers
        assert "cycletest_t" in code
        assert "cpu_step" in code
        assert "cycletest_sync" in code
        assert "internal_op" in code

    def test_cycle_accurate_compiles_and_runs(self):
        """cycle_accurate example compiles with gcc and runs correctly."""
        if not shutil.which("gcc"):
            pytest.skip("gcc not found")

        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "cycle_accurate",
            os.path.join(os.path.dirname(__file__), "..", "examples", "cycle_accurate.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        gen = BoardCodeGenerator(mod.board)
        code = gen.generate() + mod.generate_main()

        with tempfile.TemporaryDirectory() as tmpdir:
            c_path = os.path.join(tmpdir, "cycle_accurate.c")
            exe_path = os.path.join(tmpdir, "cycle_accurate")
            with open(c_path, "w") as f:
                f.write(code)
            result = subprocess.run(
                ["gcc", "-O2", "-o", exe_path, c_path],
                capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, f"Compile failed: {result.stderr}"

            result = subprocess.run(
                [exe_path], capture_output=True, text=True, timeout=10)
            assert result.returncode == 0, f"Run failed: {result.stdout}"
            assert "CYCLE-ACCURATE TEST PASSED" in result.stdout

    def test_fibonacci_example_generates(self):
        """fibonacci.py example still generates valid C (if present)."""
        fib_path = os.path.join(
            os.path.dirname(__file__), "..", "examples", "fibonacci.py")
        if not os.path.exists(fib_path):
            pytest.skip("fibonacci.py example not found")

        import importlib.util
        spec = importlib.util.spec_from_file_location("fibonacci", fib_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        gen = BoardCodeGenerator(mod.board)
        code = gen.generate()
        assert "_t" in code  # board struct type

    def test_tinyboy_example_generates(self):
        """tinyboy.py example still generates valid C (if present)."""
        tb_path = os.path.join(
            os.path.dirname(__file__), "..", "examples", "tinyboy.py")
        if not os.path.exists(tb_path):
            pytest.skip("tinyboy.py example not found")

        import importlib.util
        spec = importlib.util.spec_from_file_location("tinyboy", tb_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        gen = BoardCodeGenerator(mod.board)
        code = gen.generate()
        assert "_t" in code


# ===================================================================
# InterruptVector export
# ===================================================================

class TestExports:

    def test_interrupt_vector_importable(self):
        """InterruptVector is importable from proto package."""
        from proto import InterruptVector as IV
        assert IV is InterruptVector

    def test_dma_mode_importable(self):
        from proto.hardware import DMAMode
        assert DMAMode.OneShot.value == "oneshot"
        assert DMAMode.HBlank.value == "hblank"
        assert DMAMode.Cycle.value == "cycle"
