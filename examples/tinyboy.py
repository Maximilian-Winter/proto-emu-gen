"""
tinyboy.py -- Minimal GameBoy-like system to validate single-bus architecture.

Architecture:
  - One CPU (8-bit, 16-bit address space)
  - One bus (16-bit)
  - ROM with banking (via simple MBC: bank 0 fixed, bank 1+ switchable)
  - 256 bytes of RAM
  - A timer peripheral with register block
  - ~20 opcodes: enough to load, store, add, jump, call, halt
  - A signal line (timer -> CPU interrupt)

Memory map:
  0x0000-0x3FFF  ROM bank 0 (fixed)
  0x4000-0x7FFF  ROM bank 1+ (switchable)
  0x8000-0x80FF  RAM (256 bytes)
  0xFF00-0xFF01  Timer registers (counter, control)
  0xFFFF         Interrupt enable register
"""

import sys as _sys
import os

from proto import (
    MemoryRegion, MemoryBank, MemoryBus, MemoryController,
    MemoryAccessLevel,
    Clock, Chip, Board, RegisterBlock, SignalLine, SignalType,
    CPUDefinition, BoardCodeGenerator,
)


# ===================================================================
# Clock: single 4MHz master, everything runs off it
# ===================================================================

master = Clock("master", frequency_hz=4_000_000)


# ===================================================================
# Memory regions (the silicon)
# ===================================================================

cart_rom = MemoryRegion("rom", size_in_bytes=0, access=MemoryAccessLevel.ReadOnly,
                        comment="Cartridge ROM (dynamic size)")
ram = MemoryRegion("ram", size_in_bytes=256, comment="Work RAM")


# ===================================================================
# Banking: ROM has bank 0 (fixed) + switchable banks
# ===================================================================

rom_fixed = MemoryBank("rom_fixed", region=cart_rom, bank_size=0x4000,
                        max_banks=1, default_bank=0)
rom_banked = MemoryBank("rom_banked", region=cart_rom, bank_size=0x4000,
                         max_banks=256, default_bank=1)


# ===================================================================
# Memory controller (simple mapper)
# ===================================================================

mapper = MemoryController("mapper", controls=[rom_banked])
mapper.add_state("rom_bank", "uint8_t", "1", "Current ROM bank")

@mapper.on_write(0x2000, 0x3FFF)
def bank_select(ctrl, val, addr):
    bank: uint8 = val & 0x0F
    if bank == 0:
        bank = 1
    ctrl.rom_bank = bank

@mapper.bank_resolver(rom_banked)
def resolve_rom(ctrl, addr):
    return ctrl.rom_bank


# ===================================================================
# CPU definition: minimal 8-bit CPU
# ===================================================================

cpu = CPUDefinition("tiny8", data_width=8, address_width=16)
cpu.add_register("A", 8)
cpu.add_register("B", 8)
cpu.add_register("H", 8)
cpu.add_register("L", 8)
cpu.set_flags("F", {"Z": 7, "C": 4})
cpu.add_register_pair("HL", "H", "L")

# -- System opcodes --

@cpu.opcode(0x00, "NOP", cycles=4)
def nop(cpu):
    pass

@cpu.opcode(0x76, "HALT", cycles=4)
def halt(cpu):
    cpu.halted = 1

# -- 8-bit loads --

@cpu.opcode(0x3E, "LD A,d8", cycles=8)
def ld_a_d8(cpu):
    cpu.A = read_imm8()

@cpu.opcode(0x06, "LD B,d8", cycles=8)
def ld_b_d8(cpu):
    cpu.B = read_imm8()

@cpu.opcode(0x78, "LD A,B", cycles=4)
def ld_a_b(cpu):
    cpu.A = cpu.B

@cpu.opcode(0x47, "LD B,A", cycles=4)
def ld_b_a(cpu):
    cpu.B = cpu.A

# -- 16-bit load --

@cpu.opcode(0x21, "LD HL,d16", cycles=12)
def ld_hl_d16(cpu):
    cpu.HL = read_imm16()

@cpu.opcode(0x31, "LD SP,d16", cycles=12)
def ld_sp_d16(cpu):
    cpu.SP = read_imm16()

# -- Memory access --

@cpu.opcode(0x7E, "LD A,(HL)", cycles=8)
def ld_a_hl(cpu):
    cpu.A = mem_read(cpu.HL)

@cpu.opcode(0x77, "LD (HL),A", cycles=8)
def ld_hl_a(cpu):
    mem_write(cpu.HL, cpu.A)

@cpu.opcode(0xEA, "LD (a16),A", cycles=16)
def ld_a16_a(cpu):
    addr = read_imm16()
    mem_write(addr, cpu.A)

@cpu.opcode(0xFA, "LD A,(a16)", cycles=16)
def ld_a_a16(cpu):
    addr = read_imm16()
    cpu.A = mem_read(addr)

# -- ALU --

@cpu.opcode(0x80, "ADD A,B", cycles=4)
def add_a_b(cpu):
    result = cpu.A + cpu.B
    cpu.F.C = 1 if result > 0xFF else 0
    cpu.A = result & 0xFF
    cpu.F.Z = 1 if cpu.A == 0 else 0

@cpu.opcode(0xC6, "ADD A,d8", cycles=8)
def add_a_d8(cpu):
    val = read_imm8()
    result = cpu.A + val
    cpu.F.C = 1 if result > 0xFF else 0
    cpu.A = result & 0xFF
    cpu.F.Z = 1 if cpu.A == 0 else 0

@cpu.opcode(0x3C, "INC A", cycles=4)
def inc_a(cpu):
    cpu.A = (cpu.A + 1) & 0xFF
    cpu.F.Z = 1 if cpu.A == 0 else 0

@cpu.opcode(0xFE, "CP d8", cycles=8)
def cp_d8(cpu):
    val = read_imm8()
    result = (cpu.A - val) & 0xFF
    cpu.F.Z = 1 if result == 0 else 0
    cpu.F.C = 1 if cpu.A < val else 0

# -- Jumps --

@cpu.opcode(0xC3, "JP d16", cycles=16)
def jp_d16(cpu):
    cpu.PC = read_imm16()

@cpu.opcode(0xCA, "JP Z,d16", cycles=12)
def jp_z(cpu):
    addr = read_imm16()
    if cpu.F.Z:
        cpu.PC = addr

@cpu.opcode(0xC2, "JP NZ,d16", cycles=12)
def jp_nz(cpu):
    addr = read_imm16()
    if not cpu.F.Z:
        cpu.PC = addr

# -- Call / Ret --

@cpu.opcode(0xCD, "CALL d16", cycles=24)
def call_d16(cpu):
    addr = read_imm16()
    push16(cpu.PC)
    cpu.PC = addr

@cpu.opcode(0xC9, "RET", cycles=16)
def ret_(cpu):
    cpu.PC = pop16()


# ===================================================================
# Timer chip: counts up, fires interrupt on overflow
# ===================================================================

timer_chip = Chip("tmr", clock=master, comment="Simple timer")
timer_chip.add_state("counter", "uint8_t", "0", "Tmr counter")
timer_chip.add_state("enabled", "uint8_t", "0", "Timer enabled")

timer_regs = RegisterBlock("timer_io", base_addr=0xFF00, size=2,
                           comment="Timer I/O registers")
timer_regs.bind(0, "counter", comment="Tmr counter (R/W)")
timer_regs.bind(1, "enabled", comment="Timer enable (bit 0)")
timer_chip.add_register_block(timer_regs)

@timer_chip.tick()
def timer_tick(timer, cycles):
    if timer.enabled:
        old: uint8 = timer.counter
        timer.counter = (timer.counter + uint8(cycles)) & 0xFF
        if timer.counter < old:
            signal_assert("timer_irq")


# ===================================================================
# CPU chip: contains the CPU core and interrupt state
# ===================================================================

cpu_chip = Chip("cpu", clock=master, comment="Main processor")
cpu_chip.set_cpu_core(cpu)
cpu_chip.add_internal_memory(cart_rom)
cpu_chip.add_internal_memory(ram)
cpu_chip.add_memory_controller(mapper)


# ===================================================================
# Signal: timer overflow -> CPU interrupt flag
# ===================================================================

timer_irq = SignalLine("timer_irq", SignalType.Interrupt,
                       source=timer_chip, sinks=[cpu_chip],
                       comment="Timer overflow interrupt")

@timer_irq.on_assert(cpu_chip)
def on_timer_irq(cpu):
    # Just set a flag; real system would vector to interrupt handler
    cpu.halted = 0


# ===================================================================
# Memory bus
# ===================================================================

bus = MemoryBus("main", address_bits=16)

# ROM bank 0: fixed
bus.map(0x0000, 0x3FFF, bank=rom_fixed, controller=mapper, fixed=True)

# ROM bank 1+: switchable
bus.map(0x4000, 0x7FFF, bank=rom_banked, controller=mapper)

# Write intercepts for mapper
bus.map_writes(0x0000, 0x7FFF, controller=mapper)

# RAM
bus.map(0x8000, 0x80FF, region=ram)

# Timer registers
bus.map(0xFF00, 0xFF01, handler=timer_regs)

bus.set_fallback(read=0xFF)

# Wire bus to CPU chip
cpu_chip.set_bus(bus)


# ===================================================================
# Board assembly
# ===================================================================

board = Board("TinyBoy", comment="Minimal GameBoy-like system")
board.set_master_clock(master)
board.add_chip(cpu_chip)
board.add_chip(timer_chip)
board.add_bus(bus)
board.add_signal(timer_irq)
board.add_extern_func("printf")


# ===================================================================
# Generate and write
# ===================================================================

if __name__ == "__main__":
    gen = BoardCodeGenerator(board)
    c_code = gen.generate()

    # Add a test main() that loads a tiny ROM and runs it
    c_code += """

/* ===== Test program ===== */
int main(void) {
    tinyboy_t sys;
    tinyboy_init(&sys);

    /* Hand-assemble a tiny ROM:
       0x0000: LD SP, 0x80FF    (31 FF 80)
       0x0003: LD A, 0x05       (3E 05)
       0x0005: LD B, 0x03       (06 03)
       0x0007: ADD A, B         (80)
       0x0008: LD (0x8000), A   (EA 00 80)  -- store result in RAM
       0x000B: LD A, 0x02       (3E 02)
       0x000D: LD (0xFF01), A   (EA 01 FF)  -- enable timer
       0x0010: CALL 0x0020      (CD 20 00)  -- call subroutine
       0x0013: LD A, (0x8000)   (FA 00 80)  -- read result back
       0x0016: CP 0x08          (FE 08)     -- compare with 8
       0x0018: JP Z, 0x001C     (CA 1C 00)  -- jump if equal
       0x001B: HALT             (76)
       0x001C: LD A, 0x42       (3E 42)     -- success marker
       0x001E: HALT             (76)
       (gap)
       0x0020: INC A            (3C)        -- subroutine: A++
       0x0021: RET              (C9)

       Bank switch test:
       0x0022: LD A, 0x02       (3E 02)
       0x0024: LD (0x2000), A   (EA 00 20)  -- switch to bank 2
       0x0027: HALT             (76)
    */
    static uint8_t rom[0x8000] = {0};

    /* Main code at bank 0 */
    rom[0x0000] = 0x31; rom[0x0001] = 0xFF; rom[0x0002] = 0x80;  /* LD SP, 0x80FF */
    rom[0x0003] = 0x3E; rom[0x0004] = 0x05;                      /* LD A, 5 */
    rom[0x0005] = 0x06; rom[0x0006] = 0x03;                      /* LD B, 3 */
    rom[0x0007] = 0x80;                                           /* ADD A, B -> A=8 */
    rom[0x0008] = 0xEA; rom[0x0009] = 0x00; rom[0x000A] = 0x80;  /* LD (0x8000), A */
    rom[0x000B] = 0x3E; rom[0x000C] = 0x02;                      /* LD A, 2 */
    rom[0x000D] = 0xEA; rom[0x000E] = 0x01; rom[0x000F] = 0xFF;  /* LD (0xFF01), A -> enable timer */
    rom[0x0010] = 0xCD; rom[0x0011] = 0x20; rom[0x0012] = 0x00;  /* CALL 0x0020 */
    rom[0x0013] = 0xFA; rom[0x0014] = 0x00; rom[0x0015] = 0x80;  /* LD A, (0x8000) -> A=8 */
    rom[0x0016] = 0xFE; rom[0x0017] = 0x08;                      /* CP 8 */
    rom[0x0018] = 0xCA; rom[0x0019] = 0x1C; rom[0x001A] = 0x00;  /* JP Z, 0x001C */
    rom[0x001B] = 0x76;                                           /* HALT (fail) */
    rom[0x001C] = 0x3E; rom[0x001D] = 0x42;                      /* LD A, 0x42 (success!) */
    rom[0x001E] = 0x76;                                           /* HALT */

    /* Subroutine at 0x0020 */
    rom[0x0020] = 0x3C;                                           /* INC A */
    rom[0x0021] = 0xC9;                                           /* RET */

    /* Load ROM into system */
    sys.cpu.rom = rom;
    sys.cpu.rom_size = sizeof(rom);

    printf("=== TinyBoy Test ===\\n");

    /* Run until halted */
    int steps = 0;
    while (!sys.cpu.halted && steps < 1000) {
        tinyboy_step(&sys);
        steps++;
    }

    printf("Halted after %d steps\\n", steps);
    printf("A = 0x%02X (expected 0x42)\\n", sys.cpu.A);
    printf("RAM[0] = 0x%02X (expected 0x08)\\n", sys.cpu.ram[0]);
    printf("Tmr counter = %d\\n", sys.tmr.counter);
    printf("ROM bank = %d\\n", sys.cpu.rom_bank);

    if (sys.cpu.A == 0x42 && sys.cpu.ram[0] == 0x08) {
        printf("\\n*** ALL TESTS PASSED ***\\n");
        return 0;
    } else {
        printf("\\n*** TEST FAILED ***\\n");
        return 1;
    }
}
"""

    out_path = "tinyboy.c"
    with open(out_path, "w") as f:
        f.write(c_code)

    print(f"Generated {out_path} ({os.path.getsize(out_path)} bytes)")
