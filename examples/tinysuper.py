"""
tinysuper.py -- Minimal SNES-like system to validate multi-bus architecture.

Architecture:
  - Two CPUs on SEPARATE buses (like SNES main CPU + SPC700)
  - Master clock 21 MHz, CPU1 divides by 6, CPU2 divides by 21
  - Port with independent latching connects them (4 bytes)
  - CPU1 has ROM + RAM on its bus
  - CPU2 has its own internal RAM (like ARAM)
  - CPU1 writes data to port, CPU2 reads it and computes, writes result back

Memory map (CPU1 bus - 16 bit):
  0x0000-0x3FFF  ROM (fixed, no banking)
  0x8000-0x80FF  RAM (256 bytes)
  0x2100-0x2103  Port side A (write to CPU2)

Memory map (CPU2 bus - 16 bit):
  0x0000-0x00FF  Internal RAM (256 bytes)
  0x00F4-0x00F7  Port side B (read from CPU1)

Test scenario:
  CPU1 writes 0x07 to port[0], 0x03 to port[1]
  CPU2 reads port[0] and port[1], multiplies them, writes result to port[0]
  CPU1 reads port[0] and stores to RAM
  Expected: RAM[0] = 21 (0x15)
"""

import sys as _sys
import os

from proto import (
    MemoryRegion, MemoryBank, MemoryBus, MemoryController,
    MemoryAccessLevel,
    Clock, Chip, Board, Port, PortSide, PortLatching,
    CPUDefinition, BoardCodeGenerator,
)


# ===================================================================
# Clocks: master 21MHz, CPU1 /6, CPU2 /21
# ===================================================================

master = Clock("master", frequency_hz=21_000_000)
cpu1_clock = master.derive("cpu1_clk", divider=6)    # 3.5 MHz
cpu2_clock = master.derive("cpu2_clk", divider=21)    # 1.0 MHz


# ===================================================================
# Memory regions
# ===================================================================

rom = MemoryRegion("rom", size_in_bytes=0, access=MemoryAccessLevel.ReadOnly)
ram1 = MemoryRegion("ram1", size_in_bytes=256, comment="CPU1 work RAM")
aram = MemoryRegion("aram", size_in_bytes=256, comment="CPU2 audio RAM")


# ===================================================================
# CPU1: main processor (simple 8-bit)
# ===================================================================

cpu1_def = CPUDefinition("main_cpu", data_width=8, address_width=16)
cpu1_def.add_register("A", 8)
cpu1_def.add_register("B", 8)
cpu1_def.set_flags("F", {"Z": 7, "C": 4})

@cpu1_def.opcode(0x00, "NOP", cycles=4)
def nop1(cpu): pass

@cpu1_def.opcode(0x76, "HALT", cycles=4)
def halt1(cpu): cpu.halted = 1

@cpu1_def.opcode(0x3E, "LD A,d8", cycles=8)
def ld_a_d8_1(cpu): cpu.A = read_imm8()

@cpu1_def.opcode(0x06, "LD B,d8", cycles=8)
def ld_b_d8_1(cpu): cpu.B = read_imm8()

@cpu1_def.opcode(0x78, "LD A,B", cycles=4)
def ld_a_b_1(cpu): cpu.A = cpu.B

@cpu1_def.opcode(0xEA, "LD (a16),A", cycles=16)
def ld_a16_a_1(cpu):
    addr = read_imm16()
    mem_write(addr, cpu.A)

@cpu1_def.opcode(0xFA, "LD A,(a16)", cycles=16)
def ld_a_a16_1(cpu):
    addr = read_imm16()
    cpu.A = mem_read(addr)

@cpu1_def.opcode(0xFE, "CP d8", cycles=8)
def cp_d8_1(cpu):
    val = read_imm8()
    result = (cpu.A - val) & 0xFF
    cpu.F.Z = 1 if result == 0 else 0

@cpu1_def.opcode(0xCA, "JP Z,d16", cycles=12)
def jp_z_1(cpu):
    addr = read_imm16()
    if cpu.F.Z:
        cpu.PC = addr

@cpu1_def.opcode(0xC2, "JP NZ,d16", cycles=12)
def jp_nz_1(cpu):
    addr = read_imm16()
    if not cpu.F.Z:
        cpu.PC = addr

@cpu1_def.opcode(0xC3, "JP d16", cycles=16)
def jp_d16_1(cpu):
    cpu.PC = read_imm16()


# ===================================================================
# CPU2: sound processor (simple 8-bit, separate bus)
# ===================================================================

cpu2_def = CPUDefinition("sound_cpu", data_width=8, address_width=16)
cpu2_def.add_register("A", 8)
cpu2_def.add_register("B", 8)
cpu2_def.set_flags("F", {"Z": 7, "C": 4})

@cpu2_def.opcode(0x00, "NOP", cycles=4)
def nop2(cpu): pass

@cpu2_def.opcode(0x76, "HALT", cycles=4)
def halt2(cpu): cpu.halted = 1

@cpu2_def.opcode(0x3E, "LD A,d8", cycles=8)
def ld_a_d8_2(cpu): cpu.A = read_imm8()

@cpu2_def.opcode(0x06, "LD B,d8", cycles=8)
def ld_b_d8_2(cpu): cpu.B = read_imm8()

@cpu2_def.opcode(0x78, "LD A,B", cycles=4)
def ld_a_b_2(cpu): cpu.A = cpu.B

@cpu2_def.opcode(0xFA, "LD A,(a16)", cycles=16)
def ld_a_a16_2(cpu):
    addr = read_imm16()
    cpu.A = mem_read(addr)

@cpu2_def.opcode(0xEA, "LD (a16),A", cycles=16)
def ld_a16_a_2(cpu):
    addr = read_imm16()
    mem_write(addr, cpu.A)

# MUL A,B: A = A * B (custom opcode, not real -- proves extensibility)
@cpu2_def.opcode(0xD0, "MUL A,B", cycles=8)
def mul_a_b(cpu):
    cpu.A = (cpu.A * cpu.B) & 0xFF

@cpu2_def.opcode(0xC3, "JP d16", cycles=16)
def jp_d16_2(cpu):
    cpu.PC = read_imm16()

@cpu2_def.opcode(0xFE, "CP d8", cycles=8)
def cp_d8_2(cpu):
    val = read_imm8()
    result = (cpu.A - val) & 0xFF
    cpu.F.Z = 1 if result == 0 else 0
    cpu.F.C = 1 if cpu.A < val else 0

@cpu2_def.opcode(0xC2, "JP NZ,d16", cycles=12)
def jp_nz_2(cpu):
    addr = read_imm16()
    if not cpu.F.Z:
        cpu.PC = addr

@cpu2_def.opcode(0xCA, "JP Z,d16", cycles=12)
def jp_z_2(cpu):
    addr = read_imm16()
    if cpu.F.Z:
        cpu.PC = addr


# ===================================================================
# Chips
# ===================================================================

chip1 = Chip("main", clock=cpu1_clock, comment="Main processor")
chip1.set_cpu_core(cpu1_def)
chip1.add_internal_memory(rom)
chip1.add_internal_memory(ram1)

chip2 = Chip("snd", clock=cpu2_clock, comment="Sound processor")
chip2.set_cpu_core(cpu2_def)
chip2.add_internal_memory(aram)


# ===================================================================
# Port: 4 bytes, independently latched
# ===================================================================

comm_port = Port("comm",
    side_a=PortSide(chip=chip1, addr_start=0x2100, addr_end=0x2103),
    side_b=PortSide(chip=chip2, addr_start=0x00F4, addr_end=0x00F7),
    latching=PortLatching.Independent,
    comment="Main CPU <-> Sound CPU communication")


# ===================================================================
# Buses
# ===================================================================

bus1 = MemoryBus("bus_a", address_bits=16)
bus1.map(0x0000, 0x3FFF, region=rom, fixed=True)
bus1.map(0x8000, 0x80FF, region=ram1)
bus1.set_fallback(read=0xFF)

bus2 = MemoryBus("bus_b", address_bits=16)
bus2.map(0x0000, 0x00FF, region=aram)
bus2.set_fallback(read=0xFF)

chip1.set_bus(bus1)
chip2.set_bus(bus2)


# ===================================================================
# Board
# ===================================================================

board = Board("TinySuper", comment="Dual-CPU system with port communication")
board.set_master_clock(master)
board.add_chip(chip1)
board.add_chip(chip2)
board.add_bus(bus1)
board.add_bus(bus2)
board.add_port(comm_port)
board.add_extern_func("printf")


# ===================================================================
# Generate
# ===================================================================

if __name__ == "__main__":
    gen = BoardCodeGenerator(board)
    c_code = gen.generate()


    c_code += r"""

/* ===== Test: CPU1 sends data through port, CPU2 computes, sends back ===== */
/*
 * PROTOCOL:
 *   1. CPU1 writes 0x15 to port[0], then 0xAA (sync) to port[2]
 *   2. CPU2 polls port[2] until it sees 0xAA
 *   3. CPU2 reads port[0], doubles it (MUL A,B where B=2), writes to port[0]
 *   4. CPU2 writes 0xBB to port[2] as "done" signal
 *   5. CPU1 polls port[2] until it sees 0xBB
 *   6. CPU1 reads port[0] -> should be 0x2A (42)
 */
int main(void) {
    tinysuper_t sys;
    tinysuper_init(&sys);

    static uint8_t rom1[0x4000] = {0};

    /* CPU1 program:
       0x0000: LD A, 0x15       (3E 15)
       0x0002: LD (0x2100), A   (EA 00 21)  -- port[0] = 0x15
       0x0005: LD A, 0xAA       (3E AA)
       0x0007: LD (0x2102), A   (EA 02 21)  -- port[2] = 0xAA (sync)
       -- poll: wait for CPU2 to signal 0xBB on port[2]
       0x000A: LD A, (0x2102)   (FA 02 21)  -- read port[2] (b_out)
       0x000D: CP 0xBB          (FE BB)
       0x000F: JP NZ, 0x000A    (C2 0A 00)  -- keep polling
       -- read result
       0x0012: LD A, (0x2100)   (FA 00 21)  -- read port[0] (b_out)
       0x0015: LD (0x8000), A   (EA 00 80)  -- store to RAM
       0x0018: HALT             (76)
    */
    rom1[0x0000] = 0x3E; rom1[0x0001] = 0x15;
    rom1[0x0002] = 0xEA; rom1[0x0003] = 0x00; rom1[0x0004] = 0x21;
    rom1[0x0005] = 0x3E; rom1[0x0006] = 0xAA;
    rom1[0x0007] = 0xEA; rom1[0x0008] = 0x02; rom1[0x0009] = 0x21;
    rom1[0x000A] = 0xFA; rom1[0x000B] = 0x02; rom1[0x000C] = 0x21;
    rom1[0x000D] = 0xFE; rom1[0x000E] = 0xBB;
    rom1[0x000F] = 0xC2; rom1[0x0010] = 0x0A; rom1[0x0011] = 0x00;
    rom1[0x0012] = 0xFA; rom1[0x0013] = 0x00; rom1[0x0014] = 0x21;
    rom1[0x0015] = 0xEA; rom1[0x0016] = 0x00; rom1[0x0017] = 0x80;
    rom1[0x0018] = 0x76;

    /* CPU2 program (in ARAM):
       -- poll: wait for CPU1 to write 0xAA on port[2]
       0x0000: LD A, (0x00F6)   (FA F6 00)  -- read port[2] (a_out)
       0x0003: CP 0xAA          (FE AA)
       0x0005: JP NZ, 0x0000    (C2 00 00)  -- keep polling
       -- read, compute, write
       0x0008: LD A, (0x00F4)   (FA F4 00)  -- read port[0] = 0x15
       0x000B: LD B, 0x02       (06 02)     -- B = 2
       0x000D: MUL A,B          (D0)        -- A = 0x15 * 2 = 0x2A
       0x000E: LD (0x00F4), A   (EA F4 00)  -- write result to port[0]
       0x0011: LD A, 0xBB       (3E BB)     -- done marker
       0x0013: LD (0x00F6), A   (EA F6 00)  -- port[2] = 0xBB
       0x0016: HALT             (76)
    */
    sys.snd.aram[0x00] = 0xFA; sys.snd.aram[0x01] = 0xF6; sys.snd.aram[0x02] = 0x00;
    sys.snd.aram[0x03] = 0xFE; sys.snd.aram[0x04] = 0xAA;
    sys.snd.aram[0x05] = 0xC2; sys.snd.aram[0x06] = 0x00; sys.snd.aram[0x07] = 0x00;
    sys.snd.aram[0x08] = 0xFA; sys.snd.aram[0x09] = 0xF4; sys.snd.aram[0x0A] = 0x00;
    sys.snd.aram[0x0B] = 0x06; sys.snd.aram[0x0C] = 0x02;
    sys.snd.aram[0x0D] = 0xD0;
    sys.snd.aram[0x0E] = 0xEA; sys.snd.aram[0x0F] = 0xF4; sys.snd.aram[0x10] = 0x00;
    sys.snd.aram[0x11] = 0x3E; sys.snd.aram[0x12] = 0xBB;
    sys.snd.aram[0x13] = 0xEA; sys.snd.aram[0x14] = 0xF6; sys.snd.aram[0x15] = 0x00;
    sys.snd.aram[0x16] = 0x76;

    /* Load ROM */
    sys.main.rom = rom1;
    sys.main.rom_size = sizeof(rom1);

    printf("=== TinySuper Test ===\n");
    printf("CPU1: 3.5 MHz (master/6), CPU2: 1.0 MHz (master/21)\n");
    printf("Protocol: CPU1 writes 0x15, CPU2 doubles to 0x2A, sends back\n\n");

    int steps = 0;
    while (!sys.main.halted && steps < 100000) {
        tinysuper_step(&sys);
        steps++;
    }

    printf("Halted after %d steps\n", steps);
    printf("CPU1 A    = 0x%02X (expected 0x2A)\n", sys.main.A);
    printf("RAM[0]    = 0x%02X (expected 0x2A)\n", sys.main.ram1[0]);
    printf("CPU2 A    = 0x%02X\n", sys.snd.A);
    printf("CPU2 halt = %d, PC = 0x%04X\n", sys.snd.halted, sys.snd.PC);
    printf("Port A->B = [%02X %02X %02X %02X]\n",
        sys.comm_a_out[0], sys.comm_a_out[1], sys.comm_a_out[2], sys.comm_a_out[3]);
    printf("Port B->A = [%02X %02X %02X %02X]\n",
        sys.comm_b_out[0], sys.comm_b_out[1], sys.comm_b_out[2], sys.comm_b_out[3]);

    if (sys.main.ram1[0] == 0x2A) {
        printf("\n*** DUAL-CPU PORT COMMUNICATION TEST PASSED ***\n");
        printf("Two CPUs on separate buses, different clocks, synced via port!\n");
        return 0;
    } else {
        printf("\n*** TEST FAILED ***\n");
        return 1;
    }
}
"""

    out_path = "tinysuper.c"
    with open(out_path, "w") as f:
        f.write(c_code)

    print(f"Generated {out_path} ({os.path.getsize(out_path)} bytes)")
