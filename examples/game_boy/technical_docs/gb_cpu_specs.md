# Sharp LR35902 CPU Technical Specifications
## GameBoy (DMG) & GameBoy Color (CGB) Reference

**Document Version:** 1.0  
**Purpose:** Emulator Development Reference  
**Target Systems:** Nintendo GameBoy (DMG-01), GameBoy Pocket (MGB), GameBoy Color (CGB)

---

# 1. CPU OVERVIEW

## 1.1 Architecture

The Sharp LR35902 is a custom 8-bit microprocessor combining features from both the Zilog Z80 and Intel 8080:

| Feature | Z80 | 8080 | LR35902 |
|---------|-----|------|---------|
| Register Set | Extended (IX, IY) | Basic | Basic (no IX/IY) |
| Instruction Set | Extended | Basic | Custom subset |
| I/O Ports | Separate space | Memory-mapped | Memory-mapped |
| Interrupts | Mode 0, 1, 2 | RST only | Custom vectors |
| CB Prefix | Yes | No | Yes (bit ops) |
| DD/FD Prefix | Yes | No | No |
| ED Prefix | Yes | No | No |

## 1.2 Clock Speeds

| Mode | Clock Frequency | T-states/sec | Notes |
|------|-----------------|--------------|-------|
| **DMG Normal** | 4.194304 MHz | 4,194,304 | Standard GameBoy speed |
| **CGB Normal** | 4.194304 MHz | 4,194,304 | Backward compatible mode |
| **CGB Double** | 8.388608 MHz | 8,388,608 | CGB exclusive mode |

- 1 Machine Cycle (M-cycle) = 4 T-states (clock periods)
- DMG: ~1.05 MHz effective instruction rate
- CGB Double: ~2.10 MHz effective instruction rate

## 1.3 Register Set

### 8-bit Registers

| Register | Purpose | Description |
|----------|---------|-------------|
| A | Accumulator | Primary arithmetic register |
| F | Flags | Condition flags (cannot be directly accessed) |
| B | General | Loop counter, parameter passing |
| C | General | Often used with B as BC |
| D | General | Often used with E as DE |
| E | General | Often used with D as DE |
| H | General | High byte of HL, memory addressing |
| L | General | Low byte of HL, memory addressing |

### 16-bit Register Pairs

| Pair | Registers | Primary Use |
|------|-----------|-------------|
| AF | A + F | Accumulator and flags |
| BC | B + C | General purpose, loop counter |
| DE | D + E | General purpose, memory operations |
| HL | H + L | Primary memory pointer, arithmetic |
| SP | - | Stack Pointer |
| PC | - | Program Counter |

### Flag Register (F) Layout

| Bit | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|-----|---|---|---|---|---|---|---|---|
| Flag | Z | N | H | C | 0 | 0 | 0 | 0 |
| Name | Zero | Subtract | Half-Carry | Carry | - | - | - | - |

| Flag | Description |
|------|-------------|
| **Z** | Set if result of operation is zero |
| **N** | Set if last operation was subtraction |
| **H** | Set if carry from bit 3 to bit 4 (BCD) |
| **C** | Set if carry from bit 7 (or bit 15 for 16-bit) |

---

# 2. COMPLETE OPCODE TABLE

## 2.1 Primary Opcodes (0x00 - 0xFF)

### Legend
- **Bytes:** Total instruction length
- **Cycles:** M-cycles (machine cycles, 1 M-cycle = 4 T-states)
- **Flags:** `-` = unaffected, `0` = reset, `1` = set, `Z` = affected per result

### 0x00 - 0x0F

| Hex | Mnemonic | Bytes | Cycles | Flags (ZNHC) | Description |
|-----|----------|-------|--------|--------------|-------------|
| 00 | NOP | 1 | 1 | ---- | No operation |
| 01 | LD BC, d16 | 3 | 3 | ---- | BC = immediate 16-bit |
| 02 | LD (BC), A | 1 | 2 | ---- | Write A to address BC |
| 03 | INC BC | 1 | 2 | ---- | BC = BC + 1 |
| 04 | INC B | 1 | 1 | Z0H- | B = B + 1 |
| 05 | DEC B | 1 | 1 | Z1H- | B = B - 1 |
| 06 | LD B, d8 | 2 | 2 | ---- | B = immediate 8-bit |
| 07 | RLCA | 1 | 1 | 000C | Rotate A left circular |
| 08 | LD (a16), SP | 3 | 5 | ---- | Write SP to immediate address |
| 09 | ADD HL, BC | 1 | 2 | -0HC | HL = HL + BC |
| 0A | LD A, (BC) | 1 | 2 | ---- | A = read from address BC |
| 0B | DEC BC | 1 | 2 | ---- | BC = BC - 1 |
| 0C | INC C | 1 | 1 | Z0H- | C = C + 1 |
| 0D | DEC C | 1 | 1 | Z1H- | C = C - 1 |
| 0E | LD C, d8 | 2 | 2 | ---- | C = immediate 8-bit |
| 0F | RRCA | 1 | 1 | 000C | Rotate A right circular |

### 0x10 - 0x1F

| Hex | Mnemonic | Bytes | Cycles | Flags (ZNHC) | Description |
|-----|----------|-------|--------|--------------|-------------|
| 10 | STOP 0 | 2 | 1 | ---- | Enter low power mode |
| 11 | LD DE, d16 | 3 | 3 | ---- | DE = immediate 16-bit |
| 12 | LD (DE), A | 1 | 2 | ---- | Write A to address DE |
| 13 | INC DE | 1 | 2 | ---- | DE = DE + 1 |
| 14 | INC D | 1 | 1 | Z0H- | D = D + 1 |
| 15 | DEC D | 1 | 1 | Z1H- | D = D - 1 |
| 16 | LD D, d8 | 2 | 2 | ---- | D = immediate 8-bit |
| 17 | RLA | 1 | 1 | 000C | Rotate A left through carry |
| 18 | JR r8 | 2 | 3 | ---- | PC = PC + signed 8-bit |
| 19 | ADD HL, DE | 1 | 2 | -0HC | HL = HL + DE |
| 1A | LD A, (DE) | 1 | 2 | ---- | A = read from address DE |
| 1B | DEC DE | 1 | 2 | ---- | DE = DE - 1 |
| 1C | INC E | 1 | 1 | Z0H- | E = E + 1 |
| 1D | DEC E | 1 | 1 | Z1H- | E = E - 1 |
| 1E | LD E, d8 | 2 | 2 | ---- | E = immediate 8-bit |
| 1F | RRA | 1 | 1 | 000C | Rotate A right through carry |

### 0x20 - 0x2F

| Hex | Mnemonic | Bytes | Cycles | Flags (ZNHC) | Description |
|-----|----------|-------|--------|--------------|-------------|
| 20 | JR NZ, r8 | 2 | 2/3 | ---- | Jump if Z=0 (3 cycles if taken) |
| 21 | LD HL, d16 | 3 | 3 | ---- | HL = immediate 16-bit |
| 22 | LD (HL+), A | 1 | 2 | ---- | Write A to HL, then HL++ |
| 23 | INC HL | 1 | 2 | ---- | HL = HL + 1 |
| 24 | INC H | 1 | 1 | Z0H- | H = H + 1 |
| 25 | DEC H | 1 | 1 | Z1H- | H = H - 1 |
| 26 | LD H, d8 | 2 | 2 | ---- | H = immediate 8-bit |
| 27 | DAA | 1 | 1 | Z-0C | Decimal adjust accumulator |
| 28 | JR Z, r8 | 2 | 2/3 | ---- | Jump if Z=1 (3 cycles if taken) |
| 29 | ADD HL, HL | 1 | 2 | -0HC | HL = HL + HL |
| 2A | LD A, (HL+) | 1 | 2 | ---- | A = read HL, then HL++ |
| 2B | DEC HL | 1 | 2 | ---- | HL = HL - 1 |
| 2C | INC L | 1 | 1 | Z0H- | L = L + 1 |
| 2D | DEC L | 1 | 1 | Z1H- | L = L - 1 |
| 2E | LD L, d8 | 2 | 2 | ---- | L = immediate 8-bit |
| 2F | CPL | 1 | 1 | -11- | A = ~A (complement) |

### 0x30 - 0x3F

| Hex | Mnemonic | Bytes | Cycles | Flags (ZNHC) | Description |
|-----|----------|-------|--------|--------------|-------------|
| 30 | JR NC, r8 | 2 | 2/3 | ---- | Jump if C=0 (3 cycles if taken) |
| 31 | LD SP, d16 | 3 | 3 | ---- | SP = immediate 16-bit |
| 32 | LD (HL-), A | 1 | 2 | ---- | Write A to HL, then HL-- |
| 33 | INC SP | 1 | 2 | ---- | SP = SP + 1 |
| 34 | INC (HL) | 1 | 3 | Z0H- | Increment value at HL |
| 35 | DEC (HL) | 1 | 3 | Z1H- | Decrement value at HL |
| 36 | LD (HL), d8 | 2 | 3 | ---- | Write immediate to HL address |
| 37 | SCF | 1 | 1 | -001 | Set carry flag |
| 38 | JR C, r8 | 2 | 2/3 | ---- | Jump if C=1 (3 cycles if taken) |
| 39 | ADD HL, SP | 1 | 2 | -0HC | HL = HL + SP |
| 3A | LD A, (HL-) | 1 | 2 | ---- | A = read HL, then HL-- |
| 3B | DEC SP | 1 | 2 | ---- | SP = SP - 1 |
| 3C | INC A | 1 | 1 | Z0H- | A = A + 1 |
| 3D | DEC A | 1 | 1 | Z1H- | A = A - 1 |
| 3E | LD A, d8 | 2 | 2 | ---- | A = immediate 8-bit |
| 3F | CCF | 1 | 1 | -00C | Complement carry flag |

### 0x40 - 0x4F (LD B, r)

| Hex | Mnemonic | Bytes | Cycles | Flags | Description |
|-----|----------|-------|--------|-------|-------------|
| 40 | LD B, B | 1 | 1 | ---- | B = B (NOP) |
| 41 | LD B, C | 1 | 1 | ---- | B = C |
| 42 | LD B, D | 1 | 1 | ---- | B = D |
| 43 | LD B, E | 1 | 1 | ---- | B = E |
| 44 | LD B, H | 1 | 1 | ---- | B = H |
| 45 | LD B, L | 1 | 1 | ---- | B = L |
| 46 | LD B, (HL) | 1 | 2 | ---- | B = read from HL |
| 47 | LD B, A | 1 | 1 | ---- | B = A |
| 48 | LD C, B | 1 | 1 | ---- | C = B |
| 49 | LD C, C | 1 | 1 | ---- | C = C (NOP) |
| 4A | LD C, D | 1 | 1 | ---- | C = D |
| 4B | LD C, E | 1 | 1 | ---- | C = E |
| 4C | LD C, H | 1 | 1 | ---- | C = H |
| 4D | LD C, L | 1 | 1 | ---- | C = L |
| 4E | LD C, (HL) | 1 | 2 | ---- | C = read from HL |
| 4F | LD C, A | 1 | 1 | ---- | C = A |

### 0x50 - 0x5F (LD D, r / LD E, r)

| Hex | Mnemonic | Bytes | Cycles | Flags | Description |
|-----|----------|-------|--------|-------|-------------|
| 50 | LD D, B | 1 | 1 | ---- | D = B |
| 51 | LD D, C | 1 | 1 | ---- | D = C |
| 52 | LD D, D | 1 | 1 | ---- | D = D (NOP) |
| 53 | LD D, E | 1 | 1 | ---- | D = E |
| 54 | LD D, H | 1 | 1 | ---- | D = H |
| 55 | LD D, L | 1 | 1 | ---- | D = L |
| 56 | LD D, (HL) | 1 | 2 | ---- | D = read from HL |
| 57 | LD D, A | 1 | 1 | ---- | D = A |
| 58 | LD E, B | 1 | 1 | ---- | E = B |
| 59 | LD E, C | 1 | 1 | ---- | E = C |
| 5A | LD E, D | 1 | 1 | ---- | E = D |
| 5B | LD E, E | 1 | 1 | ---- | E = E (NOP) |
| 5C | LD E, H | 1 | 1 | ---- | E = H |
| 5D | LD E, L | 1 | 1 | ---- | E = L |
| 5E | LD E, (HL) | 1 | 2 | ---- | E = read from HL |
| 5F | LD E, A | 1 | 1 | ---- | E = A |

### 0x60 - 0x6F (LD H, r / LD L, r)

| Hex | Mnemonic | Bytes | Cycles | Flags | Description |
|-----|----------|-------|--------|-------|-------------|
| 60 | LD H, B | 1 | 1 | ---- | H = B |
| 61 | LD H, C | 1 | 1 | ---- | H = C |
| 62 | LD H, D | 1 | 1 | ---- | H = D |
| 63 | LD H, E | 1 | 1 | ---- | H = E |
| 64 | LD H, H | 1 | 1 | ---- | H = H (NOP) |
| 65 | LD H, L | 1 | 1 | ---- | H = L |
| 66 | LD H, (HL) | 1 | 2 | ---- | H = read from HL |
| 67 | LD H, A | 1 | 1 | ---- | H = A |
| 68 | LD L, B | 1 | 1 | ---- | L = B |
| 69 | LD L, C | 1 | 1 | ---- | L = C |
| 6A | LD L, D | 1 | 1 | ---- | L = D |
| 6B | LD L, E | 1 | 1 | ---- | L = E |
| 6C | LD L, H | 1 | 1 | ---- | L = H |
| 6D | LD L, L | 1 | 1 | ---- | L = L (NOP) |
| 6E | LD L, (HL) | 1 | 2 | ---- | L = read from HL |
| 6F | LD L, A | 1 | 1 | ---- | L = A |

### 0x70 - 0x7F (LD (HL), r / LD r, A)

| Hex | Mnemonic | Bytes | Cycles | Flags | Description |
|-----|----------|-------|--------|-------|-------------|
| 70 | LD (HL), B | 1 | 2 | ---- | Write B to HL address |
| 71 | LD (HL), C | 1 | 2 | ---- | Write C to HL address |
| 72 | LD (HL), D | 1 | 2 | ---- | Write D to HL address |
| 73 | LD (HL), E | 1 | 2 | ---- | Write E to HL address |
| 74 | LD (HL), H | 1 | 2 | ---- | Write H to HL address |
| 75 | LD (HL), L | 1 | 2 | ---- | Write L to HL address |
| 76 | HALT | 1 | 1 | ---- | Halt until interrupt |
| 77 | LD (HL), A | 1 | 2 | ---- | Write A to HL address |
| 78 | LD A, B | 1 | 1 | ---- | A = B |
| 79 | LD A, C | 1 | 1 | ---- | A = C |
| 7A | LD A, D | 1 | 1 | ---- | A = D |
| 7B | LD A, E | 1 | 1 | ---- | A = E |
| 7C | LD A, H | 1 | 1 | ---- | A = H |
| 7D | LD A, L | 1 | 1 | ---- | A = L |
| 7E | LD A, (HL) | 1 | 2 | ---- | A = read from HL |
| 7F | LD A, A | 1 | 1 | ---- | A = A (NOP) |

### 0x80 - 0x8F (ADD A, r)

| Hex | Mnemonic | Bytes | Cycles | Flags (ZNHC) | Description |
|-----|----------|-------|--------|--------------|-------------|
| 80 | ADD A, B | 1 | 1 | Z0HC | A = A + B |
| 81 | ADD A, C | 1 | 1 | Z0HC | A = A + C |
| 82 | ADD A, D | 1 | 1 | Z0HC | A = A + D |
| 83 | ADD A, E | 1 | 1 | Z0HC | A = A + E |
| 84 | ADD A, H | 1 | 1 | Z0HC | A = A + H |
| 85 | ADD A, L | 1 | 1 | Z0HC | A = A + L |
| 86 | ADD A, (HL) | 1 | 2 | Z0HC | A = A + value at HL |
| 87 | ADD A, A | 1 | 1 | Z0HC | A = A + A |
| 88 | ADC A, B | 1 | 1 | Z0HC | A = A + B + C |
| 89 | ADC A, C | 1 | 1 | Z0HC | A = A + C + C |
| 8A | ADC A, D | 1 | 1 | Z0HC | A = A + D + C |
| 8B | ADC A, E | 1 | 1 | Z0HC | A = A + E + C |
| 8C | ADC A, H | 1 | 1 | Z0HC | A = A + H + C |
| 8D | ADC A, L | 1 | 1 | Z0HC | A = A + L + C |
| 8E | ADC A, (HL) | 1 | 2 | Z0HC | A = A + (HL) + C |
| 8F | ADC A, A | 1 | 1 | Z0HC | A = A + A + C |

### 0x90 - 0x9F (SUB r / SBC r)

| Hex | Mnemonic | Bytes | Cycles | Flags (ZNHC) | Description |
|-----|----------|-------|--------|--------------|-------------|
| 90 | SUB B | 1 | 1 | Z1HC | A = A - B |
| 91 | SUB C | 1 | 1 | Z1HC | A = A - C |
| 92 | SUB D | 1 | 1 | Z1HC | A = A - D |
| 93 | SUB E | 1 | 1 | Z1HC | A = A - E |
| 94 | SUB H | 1 | 1 | Z1HC | A = A - H |
| 95 | SUB L | 1 | 1 | Z1HC | A = A - L |
| 96 | SUB (HL) | 1 | 2 | Z1HC | A = A - value at HL |
| 97 | SUB A | 1 | 1 | Z1HC | A = A - A (A=0) |
| 98 | SBC A, B | 1 | 1 | Z1HC | A = A - B - C |
| 99 | SBC A, C | 1 | 1 | Z1HC | A = A - C - C |
| 9A | SBC A, D | 1 | 1 | Z1HC | A = A - D - C |
| 9B | SBC A, E | 1 | 1 | Z1HC | A = A - E - C |
| 9C | SBC A, H | 1 | 1 | Z1HC | A = A - H - C |
| 9D | SBC A, L | 1 | 1 | Z1HC | A = A - L - C |
| 9E | SBC A, (HL) | 1 | 2 | Z1HC | A = A - (HL) - C |
| 9F | SBC A, A | 1 | 1 | Z1HC | A = A - A - C |

### 0xA0 - 0xAF (AND r / XOR r)

| Hex | Mnemonic | Bytes | Cycles | Flags (ZNHC) | Description |
|-----|----------|-------|--------|--------------|-------------|
| A0 | AND B | 1 | 1 | Z010 | A = A & B |
| A1 | AND C | 1 | 1 | Z010 | A = A & C |
| A2 | AND D | 1 | 1 | Z010 | A = A & D |
| A3 | AND E | 1 | 1 | Z010 | A = A & E |
| A4 | AND H | 1 | 1 | Z010 | A = A & H |
| A5 | AND L | 1 | 1 | Z010 | A = A & L |
| A6 | AND (HL) | 1 | 2 | Z010 | A = A & value at HL |
| A7 | AND A | 1 | 1 | Z010 | A = A & A |
| A8 | XOR B | 1 | 1 | Z000 | A = A ^ B |
| A9 | XOR C | 1 | 1 | Z000 | A = A ^ C |
| AA | XOR D | 1 | 1 | Z000 | A = A ^ D |
| AB | XOR E | 1 | 1 | Z000 | A = A ^ E |
| AC | XOR H | 1 | 1 | Z000 | A = A ^ H |
| AD | XOR L | 1 | 1 | Z000 | A = A ^ L |
| AE | XOR (HL) | 1 | 2 | Z000 | A = A ^ value at HL |
| AF | XOR A | 1 | 1 | Z000 | A = A ^ A (A=0) |

### 0xB0 - 0xBF (OR r / CP r)

| Hex | Mnemonic | Bytes | Cycles | Flags (ZNHC) | Description |
|-----|----------|-------|--------|--------------|-------------|
| B0 | OR B | 1 | 1 | Z000 | A = A | B |
| B1 | OR C | 1 | 1 | Z000 | A = A | C |
| B2 | OR D | 1 | 1 | Z000 | A = A | D |
| B3 | OR E | 1 | 1 | Z000 | A = A | E |
| B4 | OR H | 1 | 1 | Z000 | A = A | H |
| B5 | OR L | 1 | 1 | Z000 | A = A | L |
| B6 | OR (HL) | 1 | 2 | Z000 | A = A | value at HL |
| B7 | OR A | 1 | 1 | Z000 | A = A | A |
| B8 | CP B | 1 | 1 | Z1HC | Compare A - B |
| B9 | CP C | 1 | 1 | Z1HC | Compare A - C |
| BA | CP D | 1 | 1 | Z1HC | Compare A - D |
| BB | CP E | 1 | 1 | Z1HC | Compare A - E |
| BC | CP H | 1 | 1 | Z1HC | Compare A - H |
| BD | CP L | 1 | 1 | Z1HC | Compare A - L |
| BE | CP (HL) | 1 | 2 | Z1HC | Compare A - value at HL |
| BF | CP A | 1 | 1 | Z1HC | Compare A - A |

### 0xC0 - 0xCF

| Hex | Mnemonic | Bytes | Cycles | Flags | Description |
|-----|----------|-------|--------|-------|-------------|
| C0 | RET NZ | 1 | 2/5 | ---- | Return if Z=0 |
| C1 | POP BC | 1 | 3 | ---- | BC = pop from stack |
| C2 | JP NZ, a16 | 3 | 3/4 | ---- | Jump if Z=0 |
| C3 | JP a16 | 3 | 4 | ---- | Unconditional jump |
| C4 | CALL NZ, a16 | 3 | 3/6 | ---- | Call if Z=0 |
| C5 | PUSH BC | 1 | 4 | ---- | Push BC to stack |
| C6 | ADD A, d8 | 2 | 2 | Z0HC | A = A + immediate |
| C7 | RST 00H | 1 | 4 | ---- | Call $0000 |
| C8 | RET Z | 1 | 2/5 | ---- | Return if Z=1 |
| C9 | RET | 1 | 4 | ---- | Unconditional return |
| CA | JP Z, a16 | 3 | 3/4 | ---- | Jump if Z=1 |
| CB | PREFIX CB | 1 | 1 | ---- | CB prefix (bit operations) |
| CC | CALL Z, a16 | 3 | 3/6 | ---- | Call if Z=1 |
| CD | CALL a16 | 3 | 6 | ---- | Unconditional call |
| CE | ADC A, d8 | 2 | 2 | Z0HC | A = A + imm + C |
| CF | RST 08H | 1 | 4 | ---- | Call $0008 |

### 0xD0 - 0xDF

| Hex | Mnemonic | Bytes | Cycles | Flags | Description |
|-----|----------|-------|--------|-------|-------------|
| D0 | RET NC | 1 | 2/5 | ---- | Return if C=0 |
| D1 | POP DE | 1 | 3 | ---- | DE = pop from stack |
| D2 | JP NC, a16 | 3 | 3/4 | ---- | Jump if C=0 |
| D3 | - | - | - | - | **UNDEFINED** |
| D4 | CALL NC, a16 | 3 | 3/6 | ---- | Call if C=0 |
| D5 | PUSH DE | 1 | 4 | ---- | Push DE to stack |
| D6 | SUB d8 | 2 | 2 | Z1HC | A = A - immediate |
| D7 | RST 10H | 1 | 4 | ---- | Call $0010 |
| D8 | RET C | 1 | 2/5 | ---- | Return if C=1 |
| D9 | RETI | 1 | 4 | ---- | Return and enable interrupts |
| DA | JP C, a16 | 3 | 3/4 | ---- | Jump if C=1 |
| DB | - | - | - | - | **UNDEFINED** |
| DC | CALL C, a16 | 3 | 3/6 | ---- | Call if C=1 |
| DD | - | - | - | - | **UNDEFINED** |
| DE | SBC A, d8 | 2 | 2 | Z1HC | A = A - imm - C |
| DF | RST 18H | 1 | 4 | ---- | Call $0018 |

### 0xE0 - 0xEF

| Hex | Mnemonic | Bytes | Cycles | Flags | Description |
|-----|----------|-------|--------|-------|-------------|
| E0 | LDH (a8), A | 2 | 3 | ---- | Write A to $FF00+a8 |
| E1 | POP HL | 1 | 3 | ---- | HL = pop from stack |
| E2 | LD (C), A | 1 | 2 | ---- | Write A to $FF00+C |
| E3 | - | - | - | - | **UNDEFINED** |
| E4 | - | - | - | - | **UNDEFINED** |
| E5 | PUSH HL | 1 | 4 | ---- | Push HL to stack |
| E6 | AND d8 | 2 | 2 | Z010 | A = A & immediate |
| E7 | RST 20H | 1 | 4 | ---- | Call $0020 |
| E8 | ADD SP, r8 | 2 | 4 | 00HC | SP = SP + signed 8-bit |
| E9 | JP (HL) | 1 | 1 | ---- | PC = HL |
| EA | LD (a16), A | 3 | 4 | ---- | Write A to immediate address |
| EB | - | - | - | - | **UNDEFINED** |
| EC | - | - | - | - | **UNDEFINED** |
| ED | - | - | - | - | **UNDEFINED** |
| EE | XOR d8 | 2 | 2 | Z000 | A = A ^ immediate |
| EF | RST 28H | 1 | 4 | ---- | Call $0028 |

### 0xF0 - 0xFF

| Hex | Mnemonic | Bytes | Cycles | Flags | Description |
|-----|----------|-------|--------|-------|-------------|
| F0 | LDH A, (a8) | 2 | 3 | ---- | A = read from $FF00+a8 |
| F1 | POP AF | 1 | 3 | ZNHC | AF = pop from stack |
| F2 | LD A, (C) | 1 | 2 | ---- | A = read from $FF00+C |
| F3 | DI | 1 | 1 | ---- | Disable interrupts (IME=0) |
| F4 | - | - | - | - | **UNDEFINED** |
| F5 | PUSH AF | 1 | 4 | ---- | Push AF to stack |
| F6 | OR d8 | 2 | 2 | Z000 | A = A | immediate |
| F7 | RST 30H | 1 | 4 | ---- | Call $0030 |
| F8 | LD HL, SP+r8 | 2 | 3 | 00HC | HL = SP + signed 8-bit |
| F9 | LD SP, HL | 1 | 2 | ---- | SP = HL |
| FA | LD A, (a16) | 3 | 4 | ---- | A = read from immediate address |
| FB | EI | 1 | 1 | ---- | Enable interrupts (IME=1 after next instr) |
| FC | - | - | - | - | **UNDEFINED** |
| FD | - | - | - | - | **UNDEFINED** |
| FE | CP d8 | 2 | 2 | Z1HC | Compare A - immediate |
| FF | RST 38H | 1 | 4 | ---- | Call $0038 |

---

## 2.2 CB-Prefixed Opcodes (0xCB00 - 0xCBFF)

The CB prefix enables bit manipulation operations. The second byte determines the operation and target register.

### CB Opcode Structure
```
CB XX: [01/00/11][operation][register]
  Bits 7-6: Operation type (01=BIT, 10=RES, 11=SET, 00=rotate/shift)
  Bits 5-3: Bit number (0-7) or operation subtype
  Bits 2-0: Register (0=B, 1=C, 2=D, 3=E, 4=H, 5=L, 6=(HL), 7=A)
```

### CB 0x00-0x07: RLC (Rotate Left Circular)

| Hex | Mnemonic | Cycles | Flags (ZNHC) | Description |
|-----|----------|--------|--------------|-------------|
| CB 00 | RLC B | 2 | Z00C | B = B rotated left circular |
| CB 01 | RLC C | 2 | Z00C | C = C rotated left circular |
| CB 02 | RLC D | 2 | Z00C | D = D rotated left circular |
| CB 03 | RLC E | 2 | Z00C | E = E rotated left circular |
| CB 04 | RLC H | 2 | Z00C | H = H rotated left circular |
| CB 05 | RLC L | 2 | Z00C | L = L rotated left circular |
| CB 06 | RLC (HL) | 4 | Z00C | Value at HL rotated left circular |
| CB 07 | RLC A | 2 | Z00C | A = A rotated left circular |

### CB 0x08-0x0F: RRC (Rotate Right Circular)

| Hex | Mnemonic | Cycles | Flags (ZNHC) | Description |
|-----|----------|--------|--------------|-------------|
| CB 08 | RRC B | 2 | Z00C | B = B rotated right circular |
| CB 09 | RRC C | 2 | Z00C | C = C rotated right circular |
| CB 0A | RRC D | 2 | Z00C | D = D rotated right circular |
| CB 0B | RRC E | 2 | Z00C | E = E rotated right circular |
| CB 0C | RRC H | 2 | Z00C | H = H rotated right circular |
| CB 0D | RRC L | 2 | Z00C | L = L rotated right circular |
| CB 0E | RRC (HL) | 4 | Z00C | Value at HL rotated right circular |
| CB 0F | RRC A | 2 | Z00C | A = A rotated right circular |

### CB 0x10-0x17: RL (Rotate Left through Carry)

| Hex | Mnemonic | Cycles | Flags (ZNHC) | Description |
|-----|----------|--------|--------------|-------------|
| CB 10 | RL B | 2 | Z00C | B = B rotated left through carry |
| CB 11 | RL C | 2 | Z00C | C = C rotated left through carry |
| CB 12 | RL D | 2 | Z00C | D = D rotated left through carry |
| CB 13 | RL E | 2 | Z00C | E = E rotated left through carry |
| CB 14 | RL H | 2 | Z00C | H = H rotated left through carry |
| CB 15 | RL L | 2 | Z00C | L = L rotated left through carry |
| CB 16 | RL (HL) | 4 | Z00C | Value at HL rotated left through carry |
| CB 17 | RL A | 2 | Z00C | A = A rotated left through carry |

### CB 0x18-0x1F: RR (Rotate Right through Carry)

| Hex | Mnemonic | Cycles | Flags (ZNHC) | Description |
|-----|----------|--------|--------------|-------------|
| CB 18 | RR B | 2 | Z00C | B = B rotated right through carry |
| CB 19 | RR C | 2 | Z00C | C = C rotated right through carry |
| CB 1A | RR D | 2 | Z00C | D = D rotated right through carry |
| CB 1B | RR E | 2 | Z00C | E = E rotated right through carry |
| CB 1C | RR H | 2 | Z00C | H = H rotated right through carry |
| CB 1D | RR L | 2 | Z00C | L = L rotated right through carry |
| CB 1E | RR (HL) | 4 | Z00C | Value at HL rotated right through carry |
| CB 1F | RR A | 2 | Z00C | A = A rotated right through carry |

### CB 0x20-0x27: SLA (Shift Left Arithmetic)

| Hex | Mnemonic | Cycles | Flags (ZNHC) | Description |
|-----|----------|--------|--------------|-------------|
| CB 20 | SLA B | 2 | Z00C | B = B << 1, bit 0 = 0 |
| CB 21 | SLA C | 2 | Z00C | C = C << 1, bit 0 = 0 |
| CB 22 | SLA D | 2 | Z00C | D = D << 1, bit 0 = 0 |
| CB 23 | SLA E | 2 | Z00C | E = E << 1, bit 0 = 0 |
| CB 24 | SLA H | 2 | Z00C | H = H << 1, bit 0 = 0 |
| CB 25 | SLA L | 2 | Z00C | L = L << 1, bit 0 = 0 |
| CB 26 | SLA (HL) | 4 | Z00C | Value at HL << 1 |
| CB 27 | SLA A | 2 | Z00C | A = A << 1, bit 0 = 0 |

### CB 0x28-0x2F: SRA (Shift Right Arithmetic)

| Hex | Mnemonic | Cycles | Flags (ZNHC) | Description |
|-----|----------|--------|--------------|-------------|
| CB 28 | SRA B | 2 | Z00C | B = B >> 1, bit 7 unchanged |
| CB 29 | SRA C | 2 | Z00C | C = C >> 1, bit 7 unchanged |
| CB 2A | SRA D | 2 | Z00C | D = D >> 1, bit 7 unchanged |
| CB 2B | SRA E | 2 | Z00C | E = E >> 1, bit 7 unchanged |
| CB 2C | SRA H | 2 | Z00C | H = H >> 1, bit 7 unchanged |
| CB 2D | SRA L | 2 | Z00C | L = L >> 1, bit 7 unchanged |
| CB 2E | SRA (HL) | 4 | Z00C | Value at HL >> 1, bit 7 unchanged |
| CB 2F | SRA A | 2 | Z00C | A = A >> 1, bit 7 unchanged |

### CB 0x30-0x37: SWAP (Swap Nibbles)

| Hex | Mnemonic | Cycles | Flags (ZNHC) | Description |
|-----|----------|--------|--------------|-------------|
| CB 30 | SWAP B | 2 | Z000 | B = (B << 4) | (B >> 4) |
| CB 31 | SWAP C | 2 | Z000 | C = (C << 4) | (C >> 4) |
| CB 32 | SWAP D | 2 | Z000 | D = (D << 4) | (D >> 4) |
| CB 33 | SWAP E | 2 | Z000 | E = (E << 4) | (E >> 4) |
| CB 34 | SWAP H | 2 | Z000 | H = (H << 4) | (H >> 4) |
| CB 35 | SWAP L | 2 | Z000 | L = (L << 4) | (L >> 4) |
| CB 36 | SWAP (HL) | 4 | Z000 | Swap nibbles at HL |
| CB 37 | SWAP A | 2 | Z000 | A = (A << 4) | (A >> 4) |

### CB 0x38-0x3F: SRL (Shift Right Logical)

| Hex | Mnemonic | Cycles | Flags (ZNHC) | Description |
|-----|----------|--------|--------------|-------------|
| CB 38 | SRL B | 2 | Z00C | B = B >> 1, bit 7 = 0 |
| CB 39 | SRL C | 2 | Z00C | C = C >> 1, bit 7 = 0 |
| CB 3A | SRL D | 2 | Z00C | D = D >> 1, bit 7 = 0 |
| CB 3B | SRL E | 2 | Z00C | E = E >> 1, bit 7 = 0 |
| CB 3C | SRL H | 2 | Z00C | H = H >> 1, bit 7 = 0 |
| CB 3D | SRL L | 2 | Z00C | L = L >> 1, bit 7 = 0 |
| CB 3E | SRL (HL) | 4 | Z00C | Value at HL >> 1, bit 7 = 0 |
| CB 3F | SRL A | 2 | Z00C | A = A >> 1, bit 7 = 0 |

### CB 0x40-0x7F: BIT (Test Bit)

| Hex | Mnemonic | Cycles | Flags (ZNHC) | Description |
|-----|----------|--------|--------------|-------------|
| CB 40-47 | BIT 0, r | 2 | Z01- | Test bit 0 of register |
| CB 48-4F | BIT 1, r | 2 | Z01- | Test bit 1 of register |
| CB 50-57 | BIT 2, r | 2 | Z01- | Test bit 2 of register |
| CB 58-5F | BIT 3, r | 2 | Z01- | Test bit 3 of register |
| CB 60-67 | BIT 4, r | 2 | Z01- | Test bit 4 of register |
| CB 68-6F | BIT 5, r | 2 | Z01- | Test bit 5 of register |
| CB 70-77 | BIT 6, r | 2 | Z01- | Test bit 6 of register |
| CB 78-7F | BIT 7, r | 2 | Z01- | Test bit 7 of register |

**BIT Register Mapping:**
- x0: B, x1: C, x2: D, x3: E, x4: H, x5: L, x6: (HL), x7: A
- BIT (HL) takes 3 cycles

### CB 0x80-0xBF: RES (Reset Bit)

| Hex | Mnemonic | Cycles | Flags | Description |
|-----|----------|--------|-------|-------------|
| CB 80-87 | RES 0, r | 2 | ---- | Clear bit 0 of register |
| CB 88-8F | RES 1, r | 2 | ---- | Clear bit 1 of register |
| CB 90-97 | RES 2, r | 2 | ---- | Clear bit 2 of register |
| CB 98-9F | RES 3, r | 2 | ---- | Clear bit 3 of register |
| CB A0-A7 | RES 4, r | 2 | ---- | Clear bit 4 of register |
| CB A8-AF | RES 5, r | 2 | ---- | Clear bit 5 of register |
| CB B0-B7 | RES 6, r | 2 | ---- | Clear bit 6 of register |
| CB B8-BF | RES 7, r | 2 | ---- | Clear bit 7 of register |

**RES (HL) takes 4 cycles**

### CB 0xC0-0xFF: SET (Set Bit)

| Hex | Mnemonic | Cycles | Flags | Description |
|-----|----------|--------|-------|-------------|
| CB C0-C7 | SET 0, r | 2 | ---- | Set bit 0 of register |
| CB C8-CF | SET 1, r | 2 | ---- | Set bit 1 of register |
| CB D0-D7 | SET 2, r | 2 | ---- | Set bit 2 of register |
| CB D8-DF | SET 3, r | 2 | ---- | Set bit 3 of register |
| CB E0-E7 | SET 4, r | 2 | ---- | Set bit 4 of register |
| CB E8-EF | SET 5, r | 2 | ---- | Set bit 5 of register |
| CB F0-F7 | SET 6, r | 2 | ---- | Set bit 6 of register |
| CB F8-FF | SET 7, r | 2 | ---- | Set bit 7 of register |

**SET (HL) takes 4 cycles**

---

# 3. INTERRUPT SYSTEM

## 3.1 Interrupt Overview

The GameBoy has a vectored interrupt system with 5 interrupt sources.

## 3.2 Interrupt Registers

### IE Register (Interrupt Enable) - $FFFF

| Bit | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|-----|---|---|---|---|---|---|---|---|
| Flag | - | - | - | Joypad | Serial | Timer | LCD | V-Blank |
| Name | - | - | - | IE4 | IE3 | IE2 | IE1 | IE0 |

### IF Register (Interrupt Flag) - $FF0F

| Bit | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|-----|---|---|---|---|---|---|---|---|
| Flag | - | - | - | Joypad | Serial | Timer | LCD | V-Blank |
| Name | - | - | - | IF4 | IF3 | IF2 | IF1 | IF0 |

### IME (Interrupt Master Enable)

- Single bit flag, not memory-mapped
- Cleared automatically when interrupt is serviced
- Set by `EI` instruction (after next instruction)
- Cleared by `DI` instruction or when interrupt occurs

## 3.3 Interrupt Vectors

| Priority | Source | Vector | IE/IF Bit | Description |
|----------|--------|--------|-----------|-------------|
| 1 (Highest) | V-Blank | $0040 | 0 | LCD vertical blanking period |
| 2 | LCD STAT | $0048 | 1 | LCD status triggers |
| 3 | Timer | $0050 | 2 | Timer overflow |
| 4 | Serial | $0058 | 3 | Serial transfer complete |
| 5 (Lowest) | Joypad | $0060 | 4 | Button pressed |

## 3.4 Interrupt Timing

| Phase | Cycles | Description |
|-------|--------|-------------|
| Completion of current instruction | Variable | Finish executing current instruction |
| Interrupt dispatch | 2 M-cycles | Push PC, fetch vector |
| Total overhead | 5 M-cycles | 20 T-states minimum |

## 3.5 Interrupt Behavior

```
When interrupt occurs and IME=1:
  1. IME is cleared (disable further interrupts)
  2. PC is pushed onto stack (2 M-cycles)
  3. PC is loaded with interrupt vector address
  4. Execution continues at vector

HALT behavior:
  - If IME=1: Wake on any enabled interrupt, service it
  - If IME=0: Wake on any enabled interrupt, continue (no service)
  - If no interrupts enabled: HALT permanently (requires reset)

STOP behavior:
  - Enters very low power mode
  - Only wakes from joypad interrupt
  - All oscillators stopped except divider
```

## 3.6 Interrupt Sources Detail

### V-Blank Interrupt
- **Trigger:** LCD enters V-Blank period (line 144-153)
- **Duration:** ~1.1 ms (10 scanlines)
- **Purpose:** Safe time to update VRAM/OAM

### LCD STAT Interrupt
- **Sources:** Multiple LCD status conditions
- **LYC=LY Coincidence** - When LY register matches LYC
- **Mode 0** - H-Blank period (line 0-143, pixel 168-455)
- **Mode 1** - V-Blank period
- **Mode 2** - OAM search period (pixel 0-79)

### Timer Interrupt
- **Trigger:** TIMA register overflow ($FF -> $00)
- **TAC Register ($FF07):**
  - Bit 2: Timer enable
  - Bits 1-0: Clock select (00=4KHz, 01=16KHz, 10=64KHz, 11=256KHz)

### Serial Interrupt
- **Trigger:** Serial transfer complete (8 bits transferred)
- **SC Register ($FF02):** Controls transfer

### Joypad Interrupt
- **Trigger:** Any button transition from not pressed to pressed
- **P1 Register ($FF00):** Joypad input register

---

# 4. INSTRUCTION TIMING

## 4.1 Timing Units

| Unit | Definition | Relationship |
|------|------------|--------------|
| T-state | Single clock period | 1 T = 1 clock cycle |
| M-cycle | Machine cycle | 1 M = 4 T-states |

## 4.2 Memory Access Timing

| Operation | Duration | Notes |
|-----------|----------|-------|
| Internal operation | 1 T-state | Register operations |
| Memory read (ROM/RAM) | 1 M-cycle | 4 T-states |
| Memory write (ROM/RAM) | 1 M-cycle | 4 T-states |
| I/O read/write | 1 M-cycle | HRAM, I/O registers |
| VRAM/OAM access | 1 M-cycle | Restricted during display |

## 4.3 Conditional Instruction Timing

| Instruction | Condition | Cycles (Not Taken) | Cycles (Taken) |
|-------------|-----------|-------------------|----------------|
| JR cc, r8 | cc = false | 2 M-cycles | 3 M-cycles |
| JP cc, a16 | cc = false | 3 M-cycles | 4 M-cycles |
| CALL cc, a16 | cc = false | 3 M-cycles | 6 M-cycles |
| RET cc | cc = false | 2 M-cycles | 5 M-cycles |

## 4.4 Detailed Instruction Timing Reference

### Fastest Instructions (1 M-cycle)

| Instruction | Cycles | Description |
|-------------|--------|-------------|
| NOP | 1 | No operation |
| LD r, r' | 1 | Register to register |
| INC r | 1 | Increment register |
| DEC r | 1 | Decrement register |
| ADD/ADC/SUB/SBC/AND/XOR/OR/CP A, r | 1 | ALU operations |
| RLCA/RLA/RRCA/RRA | 1 | Accumulator rotates |
| DAA/CPL/SCF/CCF | 1 | Flag operations |
| JP (HL) | 1 | Jump to HL |
| DI/EI | 1 | Interrupt control |
| HALT | 1 | Halt CPU |

### Slowest Instructions

| Instruction | Cycles | Description |
|-------------|--------|-------------|
| LD (a16), SP | 5 | Write SP to memory |
| PUSH rr | 4 | Push register pair |
| CALL a16 | 6 | Subroutine call |
| RST n | 4 | Restart to vector |
| CB-prefixed (HL) | 4 | Bit ops on memory |
| ADD SP, r8 | 4 | Add signed to SP |

---

# 5. DMG vs CGB DIFFERENCES

## 5.1 Speed Modes

| Feature | DMG | CGB Normal | CGB Double |
|---------|-----|------------|------------|
| Clock | 4.194304 MHz | 4.194304 MHz | 8.388608 MHz |
| Divider | Normal | Normal | Normal |
| Timer | Normal | Normal | Normal |
| DMA | Normal | Normal | 2x speed |
| HDMA | No | Yes | Yes |

## 5.2 Speed Switching (CGB Only)

### KEY1 Register ($FF4D)

| Bit | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|-----|---|---|---|---|---|---|---|---|
| Name | Current Speed | - | - | - | - | - | - | Prepare Switch |

- **Bit 7 (Read-only):** Current speed (0=Normal, 1=Double)
- **Bit 0 (Read/Write):** Prepare speed switch

### Speed Switch Procedure

```
1. Write $01 to KEY1 ($FF4D) - Prepare switch
2. Execute STOP instruction
3. CPU switches speed
4. Bit 7 toggles, Bit 0 clears
```

### Speed Switch Timing

| Phase | Duration |
|-------|----------|
| STOP execution | 2050 T-states (approx) |
| Speed change | Immediate |
| Resume execution | At new speed |

## 5.3 Instruction Timing Comparison

| Instruction | DMG Cycles | CGB Normal | CGB Double |
|-------------|------------|------------|------------|
| NOP | 1 M (4T) | 1 M (4T) | 1 M (8T) |
| LD A, (HL) | 2 M (8T) | 2 M (8T) | 2 M (16T) |
| CALL a16 | 6 M (24T) | 6 M (24T) | 6 M (48T) |
| CB RLC (HL) | 4 M (16T) | 4 M (16T) | 4 M (32T) |

**Note:** M-cycles remain constant; T-states double in double-speed mode.

## 5.4 CGB Exclusive Features

| Feature | Description |
|---------|-------------|
| HDMA | Horizontal blank DMA transfers |
| VRAM Banks | 2 banks of 8KB VRAM |
| WRAM Banks | 7 banks of 4KB WRAM |
| Palettes | 8 background, 8 sprite palettes |
| Infrared | IR communication port |

## 5.5 Undocumented Opcodes

### Undefined Opcodes (0xD3, 0xDB, 0xDD, 0xE3, 0xE4, 0xEB, 0xEC, 0xED, 0xF4, 0xFC, 0xFD)

| Opcode | Behavior | Notes |
|--------|----------|-------|
| 0xD3 | NOP | Acts as 1-byte NOP |
| 0xDB | NOP | Acts as 1-byte NOP |
| 0xDD | NOP | Acts as 1-byte NOP |
| 0xE3 | NOP | Acts as 1-byte NOP |
| 0xE4 | NOP | Acts as 1-byte NOP |
| 0xEB | NOP | Acts as 1-byte NOP |
| 0xEC | NOP | Acts as 1-byte NOP |
| 0xED | NOP | Acts as 1-byte NOP |
| 0xF4 | NOP | Acts as 1-byte NOP |
| 0xFC | NOP | Acts as 1-byte NOP |
| 0xFD | NOP | Acts as 1-byte NOP |

**Note:** All undefined opcodes consume 1 byte and 1 M-cycle, behaving as NOP.

---

# APPENDIX A: QUICK REFERENCE TABLES

## A.1 Register Codes

| Code | Register |
|------|----------|
| 000 | B |
| 001 | C |
| 010 | D |
| 011 | E |
| 100 | H |
| 101 | L |
| 110 | (HL) |
| 111 | A |

## A.2 RP (Register Pair) Codes

| Code | Pair |
|------|------|
| 00 | BC |
| 01 | DE |
| 10 | HL |
| 11 | SP (or AF for PUSH/POP) |

## A.3 CC (Condition) Codes

| Code | Condition | Flag |
|------|-----------|------|
| 00 | NZ | Z = 0 |
| 01 | Z | Z = 1 |
| 10 | NC | C = 0 |
| 11 | C | C = 1 |

## A.4 ALU Operation Codes

| Code | Operation |
|------|-----------|
| 000 | ADD |
| 001 | ADC |
| 010 | SUB |
| 011 | SBC |
| 100 | AND |
| 101 | XOR |
| 110 | OR |
| 111 | CP |

## A.5 RST Vectors

| Opcode | Vector |
|--------|--------|
| RST 00H | $0000 |
| RST 08H | $0008 |
| RST 10H | $0010 |
| RST 18H | $0018 |
| RST 20H | $0020 |
| RST 28H | $0028 |
| RST 30H | $0030 |
| RST 38H | $0038 |

---

# APPENDIX B: MEMORY MAP

| Address Range | Size | Description |
|---------------|------|-------------|
| $0000-$3FFF | 16KB | ROM Bank 0 (fixed) |
| $4000-$7FFF | 16KB | ROM Bank N (switchable) |
| $8000-$9FFF | 8KB | Video RAM (VRAM) |
| $A000-$BFFF | 8KB | External RAM (cartridge) |
| $C000-$CFFF | 4KB | Work RAM Bank 0 |
| $D000-$DFFF | 4KB | Work RAM Bank 1 (CGB: 1-7) |
| $E000-$FDFF | 7.5KB | Echo RAM (mirror of $C000-$DDFF) |
| $FE00-$FE9F | 160B | OAM (Sprite Attribute Table) |
| $FEA0-$FEFF | 96B | Not Usable |
| $FF00-$FF7F | 128B | I/O Registers |
| $FF80-$FFFE | 127B | High RAM (HRAM) |
| $FFFF | 1B | Interrupt Enable Register (IE) |

---

**Document End - Sharp LR35902 CPU Technical Specifications**

*For emulator development use. Verify against hardware for critical applications.*
