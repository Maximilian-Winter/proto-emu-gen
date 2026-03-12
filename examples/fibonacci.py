"""
fibonacci.py -- Fibonacci calculator on the Board architecture.

A complete test proving the framework works end-to-end:
  Board -> BoardCodeGenerator -> compilable C -> prints Fibonacci numbers

System: TinyFib
  Chips:
    - cpu_chip: 8-bit CPU with registers A, X, flags Z/N/C
    - output_chip: serial output port at address 0x2000

  Memory:
    - RAM: 256 bytes at 0x0000-0x00FF
    - ROM: 32KB at 0x8000-0xFFFF (program loaded here)

  Bus:
    - 16-bit address bus routing RAM, output port, and ROM

  Clock:
    - 1 MHz master, everything runs at master speed

Usage:
    python fibonacci.py
    gcc -O2 -o fibonacci fibonacci.c && ./fibonacci

Expected output:
    Fibonacci sequence (8-bit):
      0
      1
      1
      2
      3
      5
      8
      13
      21
      34
      55
      89
      144
      233
    Done! (xxx cycles)
"""

from proto.memory import MemoryRegion, MemoryBus, MemoryAccessLevel
from proto.hardware import (
    Clock, Chip, Board, RegisterBlock,
)
from proto.cpu import CPUDefinition
from proto.codegen import BoardCodeGenerator


# ===================================================================
# Clock
# ===================================================================

master = Clock("master", frequency_hz=1_000_000)


# ===================================================================
# Memory regions
# ===================================================================

ram = MemoryRegion("ram", size_in_bytes=256,
    access=MemoryAccessLevel.ReadWrite,
    comment="Zero-page RAM")

rom = MemoryRegion("rom", size_in_bytes=32768,
    access=MemoryAccessLevel.ReadOnly,
    comment="Program ROM")


# ===================================================================
# Output chip -- serial port
# ===================================================================

output_chip = Chip("output", clock=master, comment="Serial output port")
output_chip.add_state("last_value", "uint8_t", "0", "Last value written")

output_io = RegisterBlock("output_io", base_addr=0x2000, size=1,
    comment="Output port register")
output_io.bind(0, "last_value", comment="Write prints value")
output_io.set_write_handler_raw(0,
    'sys->output.last_value = val; printf("  %d\\n", val); return;')
output_chip.add_register_block(output_io)


# ===================================================================
# CPU definition
# ===================================================================

cpu_def = CPUDefinition("tiny8", data_width=8, address_width=16)
cpu_def.add_register("A", 8)
cpu_def.add_register("X", 8)
cpu_def.set_flags("F", {"Z": 7, "N": 6, "C": 0})


@cpu_def.opcode(0x00, "NOP", cycles=1)
def nop(cpu):
    pass


@cpu_def.opcode(0x01, "LDA #imm8", cycles=2)
def lda_imm8(cpu):
    cpu.A = read_imm8()


@cpu_def.opcode(0x02, "LDX #imm8", cycles=2)
def ldx_imm8(cpu):
    cpu.X = read_imm8()


@cpu_def.opcode(0x03, "STA abs16", cycles=4)
def sta_abs16(cpu):
    addr = read_imm16()
    mem_write(addr, cpu.A)


@cpu_def.opcode(0x04, "LDA abs16", cycles=4)
def lda_abs16(cpu):
    cpu.A = mem_read(read_imm16())


@cpu_def.opcode(0x05, "STX abs16", cycles=4)
def stx_abs16(cpu):
    addr = read_imm16()
    mem_write(addr, cpu.X)


@cpu_def.opcode(0x06, "LDX abs16", cycles=4)
def ldx_abs16(cpu):
    cpu.X = mem_read(read_imm16())


@cpu_def.opcode(0x07, "TAX", cycles=1)
def tax(cpu):
    cpu.X = cpu.A


@cpu_def.opcode(0x08, "TXA", cycles=1)
def txa(cpu):
    cpu.A = cpu.X


@cpu_def.opcode(0x09, "ADD abs16", cycles=4)
def add_abs16(cpu):
    addr = read_imm16()
    result = cpu.A + mem_read(addr)
    cpu.F.C = 1 if result > 255 else 0
    cpu.A = result & 255
    cpu.F.Z = 1 if cpu.A == 0 else 0


@cpu_def.opcode(0x0B, "JMP abs16", cycles=3)
def jmp_abs16(cpu):
    cpu.PC = read_imm16()


@cpu_def.opcode(0x0C, "BCC abs16", cycles=3)
def bcc_abs16(cpu):
    target = read_imm16()
    if not cpu.F.C:
        cpu.PC = target


@cpu_def.opcode(0x0D, "BCS abs16", cycles=3)
def bcs_abs16(cpu):
    target = read_imm16()
    if cpu.F.C:
        cpu.PC = target


@cpu_def.opcode(0x0F, "HALT", cycles=1)
def halt(cpu):
    cpu.halted = 1


# ===================================================================
# CPU chip
# ===================================================================

cpu_chip = Chip("cpu", clock=master, comment="8-bit CPU")
cpu_chip.set_cpu_core(cpu_def)
cpu_chip.add_internal_memory(ram)
cpu_chip.add_internal_memory(rom)


# ===================================================================
# Memory bus
# ===================================================================

bus = MemoryBus("main", address_bits=16)
cpu_chip.set_bus(bus)

# RAM: 0x0000-0x00FF -> cpu_chip.ram
bus.map(0x0000, 0x00FF,
    region=ram, offset=0,
    comment="Zero-page RAM")

# Output port: 0x2000 -> register dispatch
bus.map(0x2000, 0x2000,
    handler=output_io,
    comment="Serial output port")

# ROM: 0x8000-0xFFFF -> cpu_chip.rom (read-only)
bus.map(0x8000, 0xFFFF,
    region=rom, offset=0,
    comment="Program ROM")

bus.set_fallback(read=0xFF)


# ===================================================================
# Board
# ===================================================================

board = Board("TinyFib", comment="Fibonacci calculator")
board.set_master_clock(master)
board.add_chip(cpu_chip)
board.add_chip(output_chip)
board.add_bus(bus)
board.add_extern_func("printf")


# ===================================================================
# Fibonacci program (hand-assembled machine code)
#
# Algorithm:
#   prev = 0, curr = 1
#   output prev, output curr
#   loop:
#     next = prev + curr
#     if overflow (carry set): halt
#     output next
#     prev = curr, curr = next
#     goto loop
#
# Expected output: 0 1 1 2 3 5 8 13 21 34 55 89 144 233
# ===================================================================

PROGRAM_START = 0x8000

# fmt: off
FIBONACCI_PROGRAM = bytes([
    # -- Initialize variables --
    0x01, 0x00,              # 0x8000: LDA #0
    0x03, 0x00, 0x00,        # 0x8002: STA $0000      ; prev = 0
    0x01, 0x01,              # 0x8005: LDA #1
    0x03, 0x01, 0x00,        # 0x8007: STA $0001      ; curr = 1

    # -- Print initial values --
    0x04, 0x00, 0x00,        # 0x800A: LDA $0000      ; A = 0
    0x03, 0x00, 0x20,        # 0x800D: STA $2000      ; output 0
    0x04, 0x01, 0x00,        # 0x8010: LDA $0001      ; A = 1
    0x03, 0x00, 0x20,        # 0x8013: STA $2000      ; output 1

    # -- Loop: compute next Fibonacci number --
    0x04, 0x00, 0x00,        # 0x8016: LDA $0000      ; A = prev
    0x09, 0x01, 0x00,        # 0x8019: ADD $0001      ; A = prev + curr
    0x0D, 0x2F, 0x80,        # 0x801C: BCS $802F      ; overflow -> done
    0x03, 0x00, 0x20,        # 0x801F: STA $2000      ; output next
    0x07,                    # 0x8022: TAX             ; X = next
    0x04, 0x01, 0x00,        # 0x8023: LDA $0001      ; A = curr
    0x03, 0x00, 0x00,        # 0x8026: STA $0000      ; prev = curr
    0x05, 0x01, 0x00,        # 0x8029: STX $0001      ; curr = next
    0x0B, 0x16, 0x80,        # 0x802C: JMP $8016      ; loop

    # -- Done --
    0x0F,                    # 0x802F: HALT
])
# fmt: on


# ===================================================================
# Generate main()
# ===================================================================

def generate_main() -> str:
    prog_bytes = ', '.join(f'0x{b:02X}' for b in FIBONACCI_PROGRAM)
    return f"""
/* ===================== main ===================== */

int main(void) {{
    tinyfib_t sys;
    tinyfib_init(&sys);

    /* Load program into ROM */
    uint8_t program[] = {{ {prog_bytes} }};
    memcpy(sys.cpu.rom, program, sizeof(program));
    sys.cpu.PC = 0x{PROGRAM_START:04X};

    /* Run until halted */
    printf("Fibonacci sequence (8-bit):\\n");
    while (!sys.cpu.halted) {{
        tinyfib_step(&sys);
    }}
    printf("Done! (%llu cycles)\\n", (unsigned long long)sys.cpu.cycle_count);

    return 0;
}}
"""


# ===================================================================
# Generate and write
# ===================================================================

if __name__ == "__main__":
    gen = BoardCodeGenerator(board)
    c_code = gen.generate() + generate_main()

    out_path = "fibonacci.c"
    with open(out_path, "w") as f:
        f.write(c_code)

    print(f"Generated {out_path} ({len(c_code)} bytes)")
    print(f"Compile: gcc -O2 -o fibonacci {out_path}")

    # Also print the C code
    print("\n" + "=" * 60)
    print(c_code)
