"""
Tier 1A -- Transpiler unit tests.

Tests Python-to-C conversion in isolation via the Transpiler class.
"""

import pytest
from proto.transpiler import Transpiler


# ===================================================================
# Helpers
# ===================================================================

def make_transpiler(**kwargs):
    """Create a transpiler with sensible defaults."""
    defaults = dict(
        self_param="cpu",
        chip_name="cpu",
        component_names={"cpu", "ppu"},
        flag_register="F",
        flag_bits={"Z": 7, "N": 6, "H": 5, "C": 4},
        cpu_name="cpu",
        register_pairs={"HL", "BC"},
    )
    defaults.update(kwargs)
    return Transpiler(**defaults)


def transpile(func, **kwargs):
    """Transpile a function and return the C code string."""
    t = make_transpiler(**kwargs)
    return t.transpile_function(func)


def transpile_stripped(func, **kwargs):
    """Transpile and strip all whitespace for easy assertion."""
    code = transpile(func, **kwargs)
    return " ".join(code.split())


# ===================================================================
# Basic assignments
# ===================================================================

class TestAssignments:

    def test_simple_local_variable(self):
        def func(cpu):
            x = 42
        code = transpile(func)
        assert "uint8_t x = 42;" in code

    def test_local_variable_large_constant(self):
        def func(cpu):
            x = 0x1234
        code = transpile(func)
        assert "uint16_t x = 0x1234;" in code or "uint16_t x = 0x1234;" in code.replace(" ", "")

    def test_local_variable_very_large_constant(self):
        def func(cpu):
            x = 0x12345
        code = transpile(func)
        assert "uint32_t" in code

    def test_register_write(self):
        def func(cpu):
            cpu.A = 10
        code = transpile(func)
        assert "sys->cpu.A = 10;" in code

    def test_register_read_and_write(self):
        def func(cpu):
            cpu.A = cpu.B
        code = transpile(func)
        assert "sys->cpu.A = sys->cpu.B;" in code

    def test_annotated_type_uint8(self):
        def func(cpu):
            x: uint8 = 0
        code = transpile(func)
        assert "uint8_t x = 0;" in code

    def test_annotated_type_uint16(self):
        def func(cpu):
            x: uint16 = 0
        code = transpile(func)
        assert "uint16_t x = 0;" in code

    def test_annotated_type_bool(self):
        def func(cpu):
            x: bool = True
        code = transpile(func)
        assert "bool" in code
        assert "true" in code

    def test_augmented_assign(self):
        def func(cpu):
            cpu.A += 1
        code = transpile(func)
        assert "sys->cpu.A += 1;" in code

    def test_reassignment_no_redeclaration(self):
        def func(cpu):
            x = 10
            x = 20
        code = transpile(func)
        # First should declare, second should not
        lines = [l.strip() for l in code.strip().split('\n') if l.strip()]
        assert "uint8_t x = 10;" in lines[0]
        assert lines[1] == "x = 20;"

    def test_array_declaration(self):
        def func(cpu):
            buf: array[uint8, 160] = None
        code = transpile(func)
        assert "uint8_t buf[160];" in code


# ===================================================================
# Flag operations
# ===================================================================

class TestFlags:

    def test_flag_read(self):
        def func(cpu):
            x = cpu.F.Z
        code = transpile(func)
        assert "cpu_get_Z(sys)" in code

    def test_flag_write_constant(self):
        def func(cpu):
            cpu.F.Z = 1
        code = transpile(func)
        assert "cpu_set_Z(sys, 1);" in code

    def test_flag_write_expression(self):
        def func(cpu):
            cpu.F.Z = cpu.A == 0
        code = transpile(func)
        assert "cpu_set_Z(sys," in code
        assert "sys->cpu.A == 0" in code

    def test_flag_write_ternary_optimization(self):
        """cpu.F.Z = 1 if cond else 0 should optimize to just cond."""
        def func(cpu):
            cpu.F.Z = 1 if cpu.A == 0 else 0
        code = transpile(func)
        assert "cpu_set_Z(sys, (sys->cpu.A == 0));" in code

    def test_flag_write_inverted_ternary_optimization(self):
        """cpu.F.Z = 0 if cond else 1 should optimize to !cond."""
        def func(cpu):
            cpu.F.Z = 0 if cpu.A == 0 else 1
        code = transpile(func)
        assert "!" in code

    def test_flag_read_in_condition(self):
        def func(cpu):
            if cpu.F.C:
                cpu.A = 1
        code = transpile(func)
        assert "cpu_get_C(sys)" in code

    def test_multiple_flags(self):
        def func(cpu):
            cpu.F.Z = 1
            cpu.F.N = 0
            cpu.F.H = 1
            cpu.F.C = 0
        code = transpile(func)
        assert "cpu_set_Z" in code
        assert "cpu_set_N" in code
        assert "cpu_set_H" in code
        assert "cpu_set_C" in code


# ===================================================================
# Register pairs
# ===================================================================

class TestRegisterPairs:

    def test_pair_read(self):
        def func(cpu):
            x = cpu.HL
        code = transpile(func)
        assert "cpu_get_HL(sys)" in code

    def test_pair_write(self):
        def func(cpu):
            cpu.HL = 0x1234
        code = transpile(func)
        assert "cpu_set_HL(sys, 0x1234);" in code

    def test_pair_read_in_expression(self):
        def func(cpu):
            cpu.A = mem_read(cpu.HL)
        code = transpile(func)
        assert "cpu_get_HL(sys)" in code

    def test_pair_bc(self):
        def func(cpu):
            x = cpu.BC
        code = transpile(func)
        assert "cpu_get_BC(sys)" in code


# ===================================================================
# Control flow
# ===================================================================

class TestControlFlow:

    def test_if_statement(self):
        def func(cpu):
            if cpu.A == 0:
                cpu.B = 1
        code = transpile(func)
        assert "if ((sys->cpu.A == 0))" in code
        assert "sys->cpu.B = 1;" in code

    def test_if_else(self):
        def func(cpu):
            if cpu.A > 10:
                cpu.B = 1
            else:
                cpu.B = 0
        code = transpile(func)
        assert "if" in code
        assert "else" in code

    def test_while_loop(self):
        def func(cpu):
            while cpu.A > 0:
                cpu.A -= 1
        code = transpile(func)
        assert "while ((sys->cpu.A > 0))" in code

    def test_for_range_simple(self):
        def func(cpu):
            for i in range(8):
                cpu.A += 1
        code = transpile(func)
        assert "for (int i = 0; i < 8; i++)" in code

    def test_for_range_start_end(self):
        def func(cpu):
            for i in range(2, 10):
                cpu.A += 1
        code = transpile(func)
        assert "for (int i = 2; i < 10; i++)" in code

    def test_break_and_continue(self):
        def func(cpu):
            while True:
                if cpu.A == 0:
                    break
                cpu.A -= 1
                continue
        code = transpile(func)
        assert "break;" in code
        assert "continue;" in code

    def test_nested_if(self):
        def func(cpu):
            if cpu.A > 0:
                if cpu.B > 0:
                    cpu.A = 0
        code = transpile(func)
        # Should have two if blocks
        assert code.count("if") == 2

    def test_pass_generates_nothing(self):
        def func(cpu):
            pass
        code = transpile(func)
        assert code.strip() == ""

    def test_return_value(self):
        def func(cpu):
            return cpu.A
        code = transpile(func)
        assert "return sys->cpu.A;" in code

    def test_return_void(self):
        def func(cpu):
            return
        code = transpile(func)
        assert "return;" in code


# ===================================================================
# Expressions
# ===================================================================

class TestExpressions:

    def test_binary_ops(self):
        def func(cpu):
            x = cpu.A + cpu.B
        code = transpile(func)
        assert "sys->cpu.A" in code
        assert "+" in code
        assert "sys->cpu.B" in code

    def test_bitwise_and(self):
        def func(cpu):
            cpu.A = cpu.A & 0xFF
        code = transpile(func)
        assert "&" in code
        # Transpiler formats constants <= 255 as decimal
        assert "255" in code or "0xFF" in code

    def test_bitwise_or(self):
        def func(cpu):
            cpu.A = cpu.A | 0x80
        code = transpile(func)
        assert "|" in code

    def test_bitwise_xor(self):
        def func(cpu):
            cpu.A = cpu.A ^ 0xFF
        code = transpile(func)
        assert "^" in code

    def test_left_shift(self):
        def func(cpu):
            cpu.A = cpu.A << 1
        code = transpile(func)
        assert "<<" in code

    def test_right_shift(self):
        def func(cpu):
            cpu.A = cpu.A >> 1
        code = transpile(func)
        assert ">>" in code

    def test_unary_not(self):
        def func(cpu):
            if not cpu.F.Z:
                cpu.A = 1
        code = transpile(func)
        assert "!" in code

    def test_unary_invert(self):
        def func(cpu):
            cpu.A = ~cpu.A
        code = transpile(func)
        assert "~" in code

    def test_unary_negate(self):
        def func(cpu):
            x = -cpu.A
        code = transpile(func)
        assert "(-" in code

    def test_boolean_and(self):
        def func(cpu):
            if cpu.A > 0 and cpu.B > 0:
                cpu.A = 0
        code = transpile(func)
        assert "&&" in code

    def test_boolean_or(self):
        def func(cpu):
            if cpu.A > 0 or cpu.B > 0:
                cpu.A = 0
        code = transpile(func)
        assert "||" in code

    def test_comparison_eq(self):
        def func(cpu):
            if cpu.A == 0:
                pass
        code = transpile(func)
        assert "==" in code

    def test_comparison_neq(self):
        def func(cpu):
            if cpu.A != 0:
                pass
        code = transpile(func)
        assert "!=" in code

    def test_comparison_lt_gt_le_ge(self):
        def func(cpu):
            if cpu.A < 10:
                pass
            if cpu.A > 10:
                pass
            if cpu.A <= 10:
                pass
            if cpu.A >= 10:
                pass
        code = transpile(func)
        assert "<" in code
        assert ">" in code
        assert "<=" in code
        assert ">=" in code

    def test_ternary(self):
        def func(cpu):
            cpu.A = 1 if cpu.B > 0 else 0
        code = transpile(func)
        assert "?" in code
        assert ":" in code

    def test_subscript(self):
        def func(cpu):
            cpu.A = cpu.ram[0]
        code = transpile(func)
        assert "sys->cpu.ram[0]" in code

    def test_constant_bool_true(self):
        def func(cpu):
            cpu.halted = True
        code = transpile(func)
        assert "true" in code

    def test_constant_bool_false(self):
        def func(cpu):
            cpu.halted = False
        code = transpile(func)
        assert "false" in code

    def test_constant_large_hex(self):
        def func(cpu):
            x = 0x4000
        code = transpile(func)
        assert "0x4000" in code


# ===================================================================
# Function calls
# ===================================================================

class TestFunctionCalls:

    def test_mem_read_prepends_sys(self):
        def func(cpu):
            x = mem_read(0x1000)
        code = transpile(func)
        assert "mem_read(sys, 0x1000)" in code or "mem_read(sys, 0x1000)" in code

    def test_mem_write_prepends_sys(self):
        def func(cpu):
            mem_write(0x1000, cpu.A)
        code = transpile(func)
        assert "mem_write(sys," in code

    def test_read_imm8_prepends_sys(self):
        def func(cpu):
            cpu.A = read_imm8()
        code = transpile(func)
        assert "read_imm8(sys)" in code

    def test_read_imm16_prepends_sys(self):
        def func(cpu):
            addr = read_imm16()
        code = transpile(func)
        assert "read_imm16(sys)" in code

    def test_push16_prepends_sys(self):
        def func(cpu):
            push16(cpu.PC)
        code = transpile(func)
        assert "push16(sys," in code

    def test_pop16_prepends_sys(self):
        def func(cpu):
            cpu.PC = pop16()
        code = transpile(func)
        assert "pop16(sys)" in code

    def test_signal_assert_string_to_ident(self):
        def func(cpu):
            signal_assert("timer_irq")
        code = transpile(func)
        assert "signal_assert_timer_irq(sys)" in code

    def test_type_cast_uint8(self):
        def func(cpu):
            x = uint8(cpu.A + cpu.B)
        code = transpile(func)
        assert "(uint8_t)" in code

    def test_type_cast_uint16(self):
        def func(cpu):
            x = uint16(cpu.A)
        code = transpile(func)
        assert "(uint16_t)" in code

    def test_extern_func_no_sys(self):
        def func(cpu):
            printf("hello")
        code = transpile(func, extern_funcs={"printf"})
        # printf should NOT get sys prepended
        assert 'printf("hello")' in code

    def test_unknown_func_prepends_sys(self):
        """Non-extern, non-builtin functions get sys prepended."""
        def func(cpu):
            my_helper(42)
        code = transpile(func)
        assert "my_helper(sys, 42)" in code


# ===================================================================
# Cross-component access
# ===================================================================

class TestCrossComponent:

    def test_ppu_access(self):
        def func(cpu):
            x = ppu.scanline
        code = transpile(func)
        assert "sys->ppu.scanline" in code

    def test_ppu_write(self):
        def func(cpu):
            ppu.scanline = 0
        code = transpile(func)
        assert "sys->ppu.scanline = 0;" in code


# ===================================================================
# Opcode families (variant substitution)
# ===================================================================

class TestOpcodeFamily:

    def test_variant_register_substitution(self):
        """Variant args like dst='A', src='B' should substitute in register access."""
        def func(cpu, dst, src):
            cpu.dst = cpu.src

        t = make_transpiler(
            variant_args=("A", "B"),
            variant_param_names=["dst", "src"],
        )
        code = t.transpile_function(func)
        assert "sys->cpu.A = sys->cpu.B;" in code

    def test_variant_integer_substitution(self):
        """Variant args that are integers should substitute directly."""
        def func(cpu, bit):
            cpu.A = cpu.A & bit

        t = make_transpiler(
            variant_args=(0x80,),
            variant_param_names=["bit"],
        )
        code = t.transpile_function(func)
        # Transpiler formats constants <= 255 as decimal
        assert "128" in code or "0x80" in code

    def test_variant_pair_substitution(self):
        """If variant value is a register pair name, use getter."""
        def func(cpu, pair):
            x = cpu.pair

        t = make_transpiler(
            variant_args=("HL",),
            variant_param_names=["pair"],
        )
        code = t.transpile_function(func)
        assert "cpu_get_HL(sys)" in code


# ===================================================================
# Multi-CPU function remapping
# ===================================================================

class TestMultiCPURemap:

    def test_mem_read_remapped(self):
        def func(cpu):
            x = mem_read(0x100)

        t = make_transpiler(
            mem_read_func="z80_mem_read",
            mem_write_func="z80_mem_write",
            func_remap={
                "mem_read": "z80_mem_read",
                "mem_write": "z80_mem_write",
                "read_imm8": "z80_read_imm8",
                "read_imm16": "z80_read_imm16",
                "push16": "z80_push16",
                "pop16": "z80_pop16",
            },
        )
        code = t.transpile_function(func)
        assert "z80_mem_read(sys," in code

    def test_read_imm8_remapped(self):
        def func(cpu):
            cpu.A = read_imm8()

        t = make_transpiler(
            func_remap={"read_imm8": "spc_read_imm8"},
        )
        code = t.transpile_function(func)
        assert "spc_read_imm8(sys)" in code


# ===================================================================
# Type inference
# ===================================================================

class TestTypeInference:

    def test_infer_uint8_from_mem_read(self):
        def func(cpu):
            x = mem_read(0x100)
        code = transpile(func)
        assert "uint8_t x" in code

    def test_infer_uint16_from_read_imm16(self):
        def func(cpu):
            x = read_imm16()
        code = transpile(func)
        assert "uint16_t x" in code

    def test_infer_uint8_from_small_constant(self):
        def func(cpu):
            x = 42
        code = transpile(func)
        assert "uint8_t x" in code

    def test_infer_uint16_from_medium_constant(self):
        def func(cpu):
            x = 0x1000
        code = transpile(func)
        assert "uint16_t x" in code

    def test_infer_uint32_from_large_constant(self):
        def func(cpu):
            x = 0x10000
        code = transpile(func)
        assert "uint32_t x" in code


# ===================================================================
# Edge cases
# ===================================================================

class TestEdgeCases:

    def test_empty_function(self):
        def func(cpu):
            pass
        code = transpile(func)
        assert code.strip() == ""

    def test_docstring_ignored(self):
        def func(cpu):
            """This is a docstring."""
            cpu.A = 1
        code = transpile(func)
        assert "docstring" not in code
        assert "sys->cpu.A = 1;" in code

    def test_string_constant_escaped(self):
        def func(cpu):
            printf("value: %d\n")
        code = transpile(func, extern_funcs={"printf"})
        assert '"value: %d\\n"' in code

    def test_chained_operations(self):
        def func(cpu):
            cpu.A = (cpu.A + cpu.B) & 0xFF
        code = transpile(func)
        assert "sys->cpu.A" in code
        assert "& 0xFF" in code or "& 255" in code

    def test_self_param_substitution(self):
        """The self parameter maps to sys->chip_name."""
        def func(chip):
            chip.scanline = 0
        code = transpile(func, self_param="chip", chip_name="ppu")
        assert "sys->ppu.scanline = 0;" in code

    def test_no_flag_register(self):
        """Transpiler should work without flag definitions."""
        def func(cpu):
            cpu.A = 42
        t = Transpiler(
            self_param="cpu",
            chip_name="cpu",
            flag_register=None,
            flag_bits={},
        )
        code = t.transpile_function(func)
        assert "sys->cpu.A = 42;" in code
