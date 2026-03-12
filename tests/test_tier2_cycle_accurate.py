"""
Tier 2 -- Cycle-accurate code generation tests.

Tests for:
  - Access timing in bus read/write
  - Sync function generation
  - internal_op function generation
  - Per-opcode cycle_count suppression in cycle_accurate mode
  - Bus arbitration (DMA guard)
  - BusMaster data model
  - Cycle-accurate example integration
"""

import os
import shutil
import subprocess
import sys
import tempfile
import pytest

# ===================================================================
# Imports for unit tests
# ===================================================================

from proto.memory import (
    MemoryRegion, MemoryBank, MemoryBus, MemoryController,
    MemoryAccessLevel, BusMaster,
)
from proto.hardware import Clock, Chip, Board, RegisterBlock
from proto.cpu import CPUDefinition
from proto.codegen import BoardCodeGenerator


# ===================================================================
# Helpers
# ===================================================================

def _make_minimal_cycle_board(cycle_accurate=True, access_cycles=2,
                              add_masters=False, add_peripheral=False):
    """Create a minimal board for testing cycle-accurate features."""
    clk = Clock("master", 4_000_000)
    ram = MemoryRegion("ram", 256, MemoryAccessLevel.ReadWrite)
    rom = MemoryRegion("rom", 1024, MemoryAccessLevel.ReadOnly)

    cpu_def = CPUDefinition("test8", data_width=8, address_width=16)
    cpu_def.add_register("A", 8)
    cpu_def.set_flags("F", {"Z": 7})

    @cpu_def.opcode(0x00, "NOP", cycles=4)
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

    bus = MemoryBus("main", address_bits=16)
    cpu_chip.set_bus(bus)
    bus.map(0x0000, 0x00FF, region=ram, offset=0,
            access_cycles=access_cycles, comment="RAM")
    bus.map(0x8000, 0x83FF, region=rom, offset=0,
            access_cycles=access_cycles + 1, comment="ROM")
    bus.set_fallback(read=0xFF)

    if add_masters:
        bus.add_master("cpu", priority=0)
        bus.add_master("dma", priority=1)

    board = Board("Test", comment="Test", cycle_accurate=cycle_accurate)
    board.set_master_clock(clk)
    board.add_chip(cpu_chip)
    board.add_bus(bus)

    if add_peripheral:
        pchip = Chip("timer", clock=clk)
        pchip.add_state("ticks", "uint32_t", "0")
        pchip.set_tick(code="sys->timer.ticks += cycles;")
        board.add_chip(pchip)

    board.add_extern_func("printf")
    return board


# ===================================================================
# Data model tests
# ===================================================================

class TestBusMaster:

    def test_bus_master_creation(self):
        bm = BusMaster(chip_name="cpu", priority=0, comment="main CPU")
        assert bm.chip_name == "cpu"
        assert bm.priority == 0
        assert bm.comment == "main CPU"

    def test_bus_add_master(self):
        bus = MemoryBus("main", 16)
        bus.add_master("cpu", priority=0)
        bus.add_master("dma", priority=1, comment="DMA controller")
        assert len(bus.masters) == 2
        assert bus.masters[0].chip_name == "cpu"
        assert bus.masters[1].chip_name == "dma"
        assert bus.masters[1].priority == 1

    def test_bus_no_masters_by_default(self):
        bus = MemoryBus("main", 16)
        assert bus.masters == []


class TestBoardCycleAccurate:

    def test_cycle_accurate_default_false(self):
        board = Board("test")
        assert board.cycle_accurate is False

    def test_cycle_accurate_set_true(self):
        board = Board("test", cycle_accurate=True)
        assert board.cycle_accurate is True


def _find_func_body(code, signature_prefix):
    """Extract a C function body from generated code.

    Searches for a function definition (not forward declaration) matching
    the given signature prefix, then extracts everything until the closing
    brace at column 0.
    """
    # Find function definition (ends with { not ;)
    search_from = 0
    while True:
        idx = code.index(signature_prefix, search_from)
        # Find end of line
        eol = code.index('\n', idx)
        line = code[idx:eol]
        if line.rstrip().endswith('{'):
            break  # Found the definition, not forward decl
        if line.rstrip().endswith(';'):
            search_from = eol + 1
            continue
        # Multi-line definition: check next few chars
        break
    # Now find the matching closing brace (at column 0 or start of line)
    # Simple approach: find "\n}" pattern after idx
    end = code.index("\n}", idx)
    return code[idx:end + 2]


# ===================================================================
# Code generation tests (string-level)
# ===================================================================

class TestAccessTimingCodegen:

    def test_bus_read_includes_timing(self):
        board = _make_minimal_cycle_board(cycle_accurate=False, access_cycles=5)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        # Even without cycle_accurate, access_cycles should add to cycle_count
        assert "sys->cpu.cycle_count += 5;" in code

    def test_bus_write_includes_timing(self):
        board = _make_minimal_cycle_board(cycle_accurate=False, access_cycles=3)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        # The write function should also add access timing
        write_section = code[code.index("main_write"):]
        assert "sys->cpu.cycle_count += 3;" in write_section

    def test_no_timing_when_zero_cycles(self):
        """When all mappings have access_cycles=0, no timing code in bus_read."""
        clk = Clock("master", 4_000_000)
        ram = MemoryRegion("ram", 256, MemoryAccessLevel.ReadWrite)
        cpu_def = CPUDefinition("t", data_width=8, address_width=16)
        cpu_def.add_register("A", 8)

        @cpu_def.opcode(0x0F, "HALT", cycles=1)
        def halt(cpu):
            cpu.halted = 1

        chip = Chip("cpu", clock=clk)
        chip.set_cpu_core(cpu_def)
        chip.add_internal_memory(ram)
        bus = MemoryBus("main", 16)
        chip.set_bus(bus)
        bus.map(0x0000, 0x00FF, region=ram, access_cycles=0)
        bus.set_fallback(read=0xFF)
        board = Board("Test")
        board.set_master_clock(clk)
        board.add_chip(chip)
        board.add_bus(bus)
        board.add_extern_func("printf")

        gen = BoardCodeGenerator(board)
        code = gen.generate()
        read_func = _find_func_body(code, "static uint8_t main_read(")
        assert "cycle_count" not in read_func

    def test_cycle_accurate_read_calls_sync(self):
        board = _make_minimal_cycle_board(cycle_accurate=True, access_cycles=2)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        read_func = _find_func_body(code, "static uint8_t main_read(")
        assert "test_sync(sys," in read_func

    def test_cycle_accurate_write_calls_sync(self):
        board = _make_minimal_cycle_board(cycle_accurate=True, access_cycles=2)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        write_func = _find_func_body(code, "static void main_write(")
        assert "test_sync(sys," in write_func

    def test_non_cycle_accurate_no_sync(self):
        board = _make_minimal_cycle_board(cycle_accurate=False, access_cycles=2)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        assert "test_sync" not in code


class TestSyncFunction:

    def test_sync_generated_when_cycle_accurate(self):
        board = _make_minimal_cycle_board(cycle_accurate=True, add_peripheral=True)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        assert "static void test_sync(test_t* sys, uint32_t master_cycles)" in code

    def test_sync_not_generated_when_not_cycle_accurate(self):
        board = _make_minimal_cycle_board(cycle_accurate=False)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        assert "test_sync" not in code

    def test_sync_ticks_peripherals(self):
        board = _make_minimal_cycle_board(cycle_accurate=True, add_peripheral=True)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        assert "timer_tick(sys," in code

    def test_sync_forward_declared(self):
        board = _make_minimal_cycle_board(cycle_accurate=True)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        assert "static void test_sync(test_t* sys, uint32_t master_cycles);" in code


class TestInternalOp:

    def test_internal_op_generated_when_cycle_accurate(self):
        board = _make_minimal_cycle_board(cycle_accurate=True)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        assert "static void cpu_internal_op(test_t* sys, uint32_t cycles)" in code

    def test_internal_op_increments_cycles(self):
        board = _make_minimal_cycle_board(cycle_accurate=True)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        body = _find_func_body(code, "static void cpu_internal_op(")
        assert "sys->cpu.cycle_count += cycles;" in body

    def test_internal_op_calls_sync(self):
        board = _make_minimal_cycle_board(cycle_accurate=True)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        body = _find_func_body(code, "static void cpu_internal_op(")
        assert "test_sync(sys," in body

    def test_internal_op_alias_single_cpu(self):
        board = _make_minimal_cycle_board(cycle_accurate=True)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        assert "static void internal_op(test_t* sys, uint32_t cycles)" in code

    def test_internal_op_no_sync_when_not_cycle_accurate(self):
        """internal_op exists but doesn't call sync when not cycle-accurate."""
        board = _make_minimal_cycle_board(cycle_accurate=False)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        assert "cpu_internal_op" in code
        assert "cycle_count += cycles" in code

    def test_internal_op_forward_declared(self):
        board = _make_minimal_cycle_board(cycle_accurate=True)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        assert "static void cpu_internal_op(test_t* sys, uint32_t cycles);" in code
        assert "static void internal_op(test_t* sys, uint32_t cycles);" in code


class TestOpcodeNoCycleCount:

    def test_no_cycle_count_in_opcode_when_cycle_accurate(self):
        board = _make_minimal_cycle_board(cycle_accurate=True)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        step_func = _find_func_body(code, "static void cpu_step(")
        # NOP has cycles=4, LDA has cycles=2, HALT has cycles=1
        # None of these should appear as cycle_count += N in cycle_accurate mode
        assert "cycle_count += 4;" not in step_func
        assert "cycle_count += 2;" not in step_func
        assert "cycle_count += 1;" not in step_func

    def test_cycle_count_present_when_not_cycle_accurate(self):
        board = _make_minimal_cycle_board(cycle_accurate=False)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        step_func = _find_func_body(code, "static void cpu_step(")
        assert "cycle_count += 4;" in step_func  # NOP
        assert "cycle_count += 2;" in step_func  # LDA
        assert "cycle_count += 1;" in step_func  # HALT


class TestBusArbitration:

    def test_dma_active_in_board_struct(self):
        board = _make_minimal_cycle_board(add_masters=True)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        assert "bool main_dma_active;" in code

    def test_no_dma_active_without_masters(self):
        board = _make_minimal_cycle_board(add_masters=False)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        assert "dma_active" not in code

    def test_step_guards_dma_active(self):
        board = _make_minimal_cycle_board(cycle_accurate=True, add_masters=True)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        step_func = _find_func_body(code, "static void test_step(")
        assert "main_dma_active" in step_func
        assert "return;" in step_func

    def test_step_no_guard_without_masters(self):
        board = _make_minimal_cycle_board(cycle_accurate=True, add_masters=False)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        step_func = _find_func_body(code, "static void test_step(")
        assert "dma_active" not in step_func


class TestStepCycleAccurate:

    def test_step_no_catchup_when_cycle_accurate(self):
        """In cycle_accurate mode, step() should NOT contain catch-up logic."""
        board = _make_minimal_cycle_board(cycle_accurate=True, add_peripheral=True)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        step_func = _find_func_body(code, "static void test_step(")
        # Should NOT have elapsed calculation
        assert "before" not in step_func
        assert "elapsed" not in step_func
        # Should NOT directly call timer_tick from step
        assert "timer_tick" not in step_func
        # Should just call cpu_step
        assert "cpu_step(sys)" in step_func

    def test_step_has_catchup_when_not_cycle_accurate(self):
        """Normal mode should have catch-up ticking."""
        board = _make_minimal_cycle_board(cycle_accurate=False, add_peripheral=True)
        gen = BoardCodeGenerator(board)
        code = gen.generate()
        step_func = _find_func_body(code, "static void test_step(")
        assert "before" in step_func
        assert "elapsed" in step_func
        assert "timer_tick" in step_func


# ===================================================================
# Transpiler tests for internal_op
# ===================================================================

class TestTranspilerInternalOp:

    def test_internal_op_transpiles_with_sys(self):
        """internal_op() should get sys prepended like other system functions."""
        from proto.transpiler import Transpiler
        t = Transpiler(self_param="cpu", chip_name="cpu",
                       component_names={"cpu"})

        def test_fn(cpu):
            internal_op(2)

        code = t.transpile_function(test_fn)
        assert "internal_op(sys, 2)" in code

    def test_internal_op_remapped_multi_cpu(self):
        """In multi-CPU, internal_op should be remapped to cpu-specific version."""
        from proto.transpiler import Transpiler
        t = Transpiler(
            self_param="cpu", chip_name="spc",
            component_names={"main", "spc"},
            func_remap={"internal_op": "spc_internal_op"},
        )

        def test_fn(cpu):
            internal_op(3)

        code = t.transpile_function(test_fn)
        assert "spc_internal_op(sys, 3)" in code


# ===================================================================
# Integration tests (compile + run)
# ===================================================================

GCC = shutil.which("gcc")
pytestmark_gcc = pytest.mark.skipif(GCC is None, reason="gcc not found in PATH")

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")
SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "src")


def _run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True,
                          timeout=30, **kwargs)


def _generate_and_compile_and_run(example_py, expected_output_substr=None):
    with tempfile.TemporaryDirectory() as tmpdir:
        example_name = os.path.splitext(os.path.basename(example_py))[0]
        c_file = os.path.join(tmpdir, f"{example_name}.c")
        exe_file = os.path.join(tmpdir, f"{example_name}.exe")

        env = os.environ.copy()
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        result = _run([sys.executable, example_py], cwd=tmpdir, env=env)
        assert result.returncode == 0, (
            f"Python generation failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")

        assert os.path.exists(c_file), f"Expected {c_file} to be generated"

        result = _run([GCC, "-O2", "-o", exe_file, c_file])
        assert result.returncode == 0, (
            f"gcc compilation failed:\nstderr: {result.stderr}")

        result = _run([exe_file])
        assert result.returncode == 0, (
            f"Binary exited with code {result.returncode}:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}")

        if expected_output_substr:
            assert expected_output_substr in result.stdout, (
                f"Expected '{expected_output_substr}' in output:\n{result.stdout}")
        return result.stdout


@pytest.mark.skipif(GCC is None, reason="gcc not found in PATH")
class TestCycleAccurateIntegration:

    def test_generates_compiles_and_runs(self):
        example = os.path.join(EXAMPLES_DIR, "cycle_accurate.py")
        output = _generate_and_compile_and_run(
            example, "CYCLE-ACCURATE TEST PASSED")

    def test_correct_cycle_count(self):
        example = os.path.join(EXAMPLES_DIR, "cycle_accurate.py")
        output = _generate_and_compile_and_run(example)
        assert "CPU cycles = 49 (expected 49)" in output

    def test_timer_ticked(self):
        example = os.path.join(EXAMPLES_DIR, "cycle_accurate.py")
        output = _generate_and_compile_and_run(example)
        # Timer should have received ticks (equal to cycle count since same clock)
        assert "Timer ticks = 49" in output

    def test_computation_correct(self):
        example = os.path.join(EXAMPLES_DIR, "cycle_accurate.py")
        output = _generate_and_compile_and_run(example)
        assert "A = 8 (expected 8)" in output
        assert "RAM[1] = 8 (expected 8)" in output


# Also verify existing examples still work in non-cycle-accurate mode
@pytest.mark.skipif(GCC is None, reason="gcc not found in PATH")
class TestExistingExamplesStillWork:

    def test_fibonacci_still_works(self):
        example = os.path.join(EXAMPLES_DIR, "fibonacci.py")
        _generate_and_compile_and_run(example, "Done!")

    def test_tinyboy_still_works(self):
        example = os.path.join(EXAMPLES_DIR, "tinyboy.py")
        _generate_and_compile_and_run(example, "ALL TESTS PASSED")

    def test_tinysuper_still_works(self):
        example = os.path.join(EXAMPLES_DIR, "tinysuper.py")
        _generate_and_compile_and_run(example,
                                      "DUAL-CPU PORT COMMUNICATION TEST PASSED")
