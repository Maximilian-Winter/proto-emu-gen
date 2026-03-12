"""
cycle_accurate.py -- Cycle-accurate timing demonstration.

A minimal system proving cycle-accurate code generation works:
  - access_cycles on bus mappings (each memory access costs cycles)
  - internal_op() in opcodes (non-memory CPU internal cycles)
  - sync function (peripherals ticked on every bus access)
  - No per-opcode cycle_count += N (cycles tracked per-access instead)
  - Bus arbitration (dma_active guard in step)

System: TinyCycleAccurate
  Chips:
    - cpu_chip: 8-bit CPU (A, X, flags Z/C)
    - timer_chip: simple tick counter

  Memory:
    - RAM: 256 bytes at 0x0000-0x00FF (2 cycles per access)
    - ROM: 1KB at 0x8000-0x83FF (3 cycles per access)

  Bus:
    - 16-bit, cpu as master, "dma" as secondary master

Usage:
    python cycle_accurate.py
    gcc -O2 -o cycle_accurate cycle_accurate.c && ./cycle_accurate
"""

from proto.memory import MemoryRegion, MemoryBus, MemoryAccessLevel
from proto.hardware import Clock, Chip, Board, RegisterBlock
from proto.cpu import CPUDefinition
from proto.codegen import BoardCodeGenerator


# ===================================================================
# Clock
# ===================================================================

master = Clock("master", frequency_hz=4_000_000)


# ===================================================================
# Memory regions
# ===================================================================

ram = MemoryRegion("ram", size_in_bytes=256,
    access=MemoryAccessLevel.ReadWrite, comment="RAM")

rom = MemoryRegion("rom", size_in_bytes=1024,
    access=MemoryAccessLevel.ReadOnly, comment="Program ROM")


# ===================================================================
# Timer chip (peripheral with tick handler)
# ===================================================================

timer_chip = Chip("timer", clock=master, comment="Cycle counter")
timer_chip.add_state("ticks", "uint32_t", "0", "Total ticks received")
timer_chip.set_tick(code="""\
    sys->timer.ticks += cycles;
""")


# ===================================================================
# CPU definition
# ===================================================================

cpu_def = CPUDefinition("cycle8", data_width=8, address_width=16)
cpu_def.add_register("A", 8)
cpu_def.add_register("X", 8)
cpu_def.set_flags("F", {"Z": 7, "C": 0})


@cpu_def.opcode(0x00, "NOP", cycles=0)
def nop(cpu):
    internal_op(1)  # 1 internal cycle


@cpu_def.opcode(0x01, "LDA #imm8", cycles=0)
def lda_imm8(cpu):
    cpu.A = read_imm8()  # 1 bus access (costed by access_cycles)


@cpu_def.opcode(0x02, "LDX #imm8", cycles=0)
def ldx_imm8(cpu):
    cpu.X = read_imm8()


@cpu_def.opcode(0x03, "STA abs16", cycles=0)
def sta_abs16(cpu):
    addr = read_imm16()  # 2 bus accesses
    mem_write(addr, cpu.A)  # 1 bus access


@cpu_def.opcode(0x04, "LDA abs16", cycles=0)
def lda_abs16(cpu):
    cpu.A = mem_read(read_imm16())


@cpu_def.opcode(0x07, "TAX", cycles=0)
def tax(cpu):
    internal_op(1)  # pure internal, no bus
    cpu.X = cpu.A


@cpu_def.opcode(0x08, "TXA", cycles=0)
def txa(cpu):
    internal_op(1)
    cpu.A = cpu.X


@cpu_def.opcode(0x09, "ADD abs16", cycles=0)
def add_abs16(cpu):
    addr = read_imm16()
    result = cpu.A + mem_read(addr)
    cpu.F.C = 1 if result > 255 else 0
    cpu.A = result & 255
    cpu.F.Z = 1 if cpu.A == 0 else 0


@cpu_def.opcode(0x0B, "JMP abs16", cycles=0)
def jmp_abs16(cpu):
    cpu.PC = read_imm16()


@cpu_def.opcode(0x0C, "BCC abs16", cycles=0)
def bcc_abs16(cpu):
    target = read_imm16()
    if not cpu.F.C:
        cpu.PC = target


@cpu_def.opcode(0x0F, "HALT", cycles=0)
def halt(cpu):
    internal_op(1)
    cpu.halted = 1


# ===================================================================
# CPU chip
# ===================================================================

cpu_chip = Chip("cpu", clock=master, comment="8-bit CPU")
cpu_chip.set_cpu_core(cpu_def)
cpu_chip.add_internal_memory(ram)
cpu_chip.add_internal_memory(rom)


# ===================================================================
# Memory bus with access timing
# ===================================================================

bus = MemoryBus("main", address_bits=16)
cpu_chip.set_bus(bus)

# RAM: 2 cycles per access
bus.map(0x0000, 0x00FF, region=ram, offset=0,
    access_cycles=2, comment="RAM (2 cycles)")

# ROM: 3 cycles per access (opcode fetch + operand reads)
bus.map(0x8000, 0x83FF, region=rom, offset=0,
    access_cycles=3, comment="ROM (3 cycles)")

bus.set_fallback(read=0xFF)

# Bus masters: CPU is primary, DMA as secondary
bus.add_master("cpu", priority=0, comment="CPU")
bus.add_master("dma", priority=1, comment="DMA controller")


# ===================================================================
# Board (cycle-accurate!)
# ===================================================================

board = Board("CycleTest", comment="Cycle-accurate test system",
              cycle_accurate=True)
board.set_master_clock(master)
board.add_chip(cpu_chip)
board.add_chip(timer_chip)
board.add_bus(bus)
board.add_extern_func("printf")


# ===================================================================
# Test program: A = 3 + 5, store to RAM, halt
#
# Cycle accounting:
#   Each opcode fetch = 3 cycles (ROM access)
#   Each read_imm8 operand = 3 cycles (ROM access)
#   Each read_imm16 = 2 * 3 = 6 cycles (two ROM reads)
#   Each RAM read/write = 2 cycles
#   Each internal_op(1) = 1 cycle
# ===================================================================

PROGRAM_START = 0x8000

# fmt: off
PROGRAM = bytes([
    # LDA #3       => fetch(3) + imm8(3) = 6 cycles
    0x01, 0x03,
    # STA $0000    => fetch(3) + imm16(6) + ram_write(2) = 11 cycles
    0x03, 0x00, 0x00,
    # LDA #5       => fetch(3) + imm8(3) = 6 cycles
    0x01, 0x05,
    # ADD $0000    => fetch(3) + imm16(6) + ram_read(2) = 11 cycles
    0x09, 0x00, 0x00,
    # STA $0001    => fetch(3) + imm16(6) + ram_write(2) = 11 cycles
    0x03, 0x01, 0x00,
    # HALT         => fetch(3) + internal(1) = 4 cycles
    0x0F,
])
# fmt: on

EXPECTED_CYCLES = 6 + 11 + 6 + 11 + 11 + 4  # = 49


# ===================================================================
# Generate main()
# ===================================================================

def generate_main() -> str:
    prog_bytes = ', '.join(f'0x{b:02X}' for b in PROGRAM)
    return f"""
/* ===================== main ===================== */

int main(void) {{
    cycletest_t sys;
    cycletest_init(&sys);

    /* Load program into ROM */
    uint8_t program[] = {{ {prog_bytes} }};
    memcpy(sys.cpu.rom, program, sizeof(program));
    sys.cpu.PC = 0x{PROGRAM_START:04X};

    /* Run until halted */
    while (!sys.cpu.halted) {{
        cycletest_step(&sys);
    }}

    printf("A = %d (expected 8)\\n", sys.cpu.A);
    printf("RAM[0] = %d (expected 3)\\n", sys.cpu.ram[0]);
    printf("RAM[1] = %d (expected 8)\\n", sys.cpu.ram[1]);
    printf("CPU cycles = %llu (expected {EXPECTED_CYCLES})\\n",
           (unsigned long long)sys.cpu.cycle_count);
    printf("Timer ticks = %u\\n", sys.timer.ticks);

    /* Verify */
    int ok = 1;
    if (sys.cpu.A != 8) {{ printf("FAIL: A != 8\\n"); ok = 0; }}
    if (sys.cpu.ram[0] != 3) {{ printf("FAIL: RAM[0] != 3\\n"); ok = 0; }}
    if (sys.cpu.ram[1] != 8) {{ printf("FAIL: RAM[1] != 8\\n"); ok = 0; }}
    if (sys.cpu.cycle_count != {EXPECTED_CYCLES}) {{
        printf("FAIL: cycle_count = %llu, expected {EXPECTED_CYCLES}\\n",
               (unsigned long long)sys.cpu.cycle_count);
        ok = 0;
    }}
    if (sys.timer.ticks == 0) {{ printf("FAIL: timer never ticked\\n"); ok = 0; }}

    if (ok) printf("CYCLE-ACCURATE TEST PASSED\\n");
    else printf("CYCLE-ACCURATE TEST FAILED\\n");

    return ok ? 0 : 1;
}}
"""


# ===================================================================
# Generate and write
# ===================================================================

if __name__ == "__main__":
    gen = BoardCodeGenerator(board)
    c_code = gen.generate() + generate_main()

    out_path = "cycle_accurate.c"
    with open(out_path, "w") as f:
        f.write(c_code)

    print(f"Generated {out_path} ({len(c_code)} bytes)")
    print(f"Compile: gcc -O2 -o cycle_accurate {out_path}")

    # Also print the C code
    print("\n" + "=" * 60)
    print(c_code)
