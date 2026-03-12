# SNES Audio Subsystem Technical Specifications
## SPC700 Sound Processor + S-DSP Digital Signal Processor

---

# Table of Contents

1. [SPC700 Sound Processor Architecture](#1-spc700-sound-processor-architecture)
2. [SPC700 Instruction Set](#2-spc700-instruction-set)
3. [SPC700 Registers](#3-spc700-registers)
4. [S-DSP Architecture](#4-s-dsp-architecture)
5. [DSP Register Map](#5-dsp-register-map)
6. [Audio RAM (ARAM)](#6-audio-ram-aram)
7. [BRR Sample Format](#7-brr-sample-format)
8. [Communication Protocol](#8-communication-protocol)

---

# 1. SPC700 Sound Processor Architecture

## 1.1 Overview

The SPC700 is a custom 8-bit microprocessor designed by Sony for the SNES audio subsystem. It is based on the MOS Technology 6502 architecture but with significant modifications for audio processing tasks.

## 1.2 Core Specifications

| Parameter | Specification |
|-----------|---------------|
| **Architecture** | Modified 6502-based 8-bit processor |
| **Clock Speed** | 1.024 MHz |
| **Memory Space** | 64KB (16-bit addressing) |
| **Data Bus** | 8-bit |
| **Address Bus** | 16-bit |
| **Instruction Set** | 256 opcodes, custom instruction set |
| **Stack** | 256 bytes (Page $01xx) |
| **Reset Vector** | $FFFE-$FFFF |
| **IRQ Vector** | $FFFE-$FFFF |
| **BRK Vector** | $FFDE-$FFDF |

## 1.3 Memory Map

```
$0000-$00EF  : Zero Page RAM (240 bytes)
$00F0-$00FF  : I/O Ports and Control Registers
$0100-$01FF  : Stack Page
$0200-$0FFF  : RAM
$1000-$FFBF  : RAM (if mapped)
$FFC0-$FFCF  : IPL ROM (64 bytes, boot code)
$FFD0-$FFFF  : RAM or IPL ROM (mirror)
```

## 1.4 I/O Port Registers ($00F0-$00FF)

| Address | Register | Description |
|---------|----------|-------------|
| $00F0 | TEST | Testing functions |
| $00F1 | CONTROL | Timer control, reset, IPL ROM enable |
| $00F2 | DSPADDR | DSP register address |
| $00F3 | DSPDATA | DSP register data read/write |
| $00F4 | CPUIO0 | Communication port 0 (from 5A22) |
| $00F5 | CPUIO1 | Communication port 1 (from 5A22) |
| $00F6 | CPUIO2 | Communication port 2 (from 5A22) |
| $00F7 | CPUIO3 | Communication port 3 (from 5A22) |
| $00F8 | AUXIO4 | Auxiliary port 4 |
| $00F9 | AUXIO5 | Auxiliary port 5 |
| $00FA | T0DIV | Timer 0 divider |
| $00FB | T1DIV | Timer 1 divider |
| $00FC | T2DIV | Timer 2 divider |
| $00FD | T0OUT | Timer 0 output/counter |
| $00FE | T1OUT | Timer 1 output/counter |
| $00FF | T2OUT | Timer 2 output/counter |

## 1.5 CONTROL Register ($F1) Bit Map

```
Bit 7: Timer 2 enable
Bit 6: Timer 1 enable
Bit 5: Timer 0 enable
Bit 4: Clear ports 0-1 (write 1 to clear)
Bit 3: Clear ports 2-3 (write 1 to clear)
Bit 2: Reset (write 0 to reset SPC700)
Bit 1: IPL ROM enable (1 = enabled at $FFC0-$FFFF)
Bit 0: IPL ROM enable (same as bit 1)
```

---

# 2. SPC700 Instruction Set

## 2.1 Addressing Modes

| Mode | Syntax | Description |
|------|--------|-------------|
| IMP | - | Implied (no operand) |
| IMM | #nn | Immediate (8-bit value) |
| DP | nn | Direct Page ($00nn) |
| DP+X | nn,X | Direct Page indexed by X |
| DP+Y | nn,Y | Direct Page indexed by Y |
| ABS | nnnn | Absolute (16-bit address) |
| ABS+X | nnnn,X | Absolute indexed by X |
| ABS+Y | nnnn,Y | Absolute indexed by Y |
| (X) | (X) | Indirect via X |
| [DP+X] | [nn+X] | Indirect indexed DP+X |
| [DP]+Y | [nn]+Y | Indirect DP indexed by Y |
| REL | nn | Relative (signed 8-bit offset) |
| ABS_BIT | nnnn.n | Absolute bit addressing |
| DP_BIT | nn.n | Direct Page bit addressing |

## 2.2 Flag Definitions

| Flag | Bit | Name | Description |
|------|-----|------|-------------|
| N | 7 | Negative | Set if result bit 7 = 1 |
| V | 6 | Overflow | Set on signed overflow |
| P | 5 | Direct Page | Direct page select (0=$0000, 1=$0100) |
| B | 4 | Break | Set if interrupt from BRK |
| H | 3 | Half-carry | Carry from bit 3 to 4 |
| I | 2 | Interrupt | Interrupt disable flag |
| Z | 1 | Zero | Set if result = 0 |
| C | 0 | Carry | Carry/borrow flag |

## 2.3 Complete Opcode Table (256 Opcodes)

### 2.3.1 Data Transfer Instructions

#### MOV - Move Data

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $E8 | MOV A,#nn | IMM | 2 | NZ | A = immediate |
| $E6 | MOV A,(X) | (X) | 3 | NZ | A = [$00+X] |
| $BF | MOV A,(X)+ | (X)+ | 4 | NZ | A = [$00+X], X++ |
| $E4 | MOV A,nn | DP | 3 | NZ | A = [DP+nn] |
| $F4 | MOV A,nn+X | DP+X | 4 | NZ | A = [DP+nn+X] |
| $E5 | MOV A,nnnn | ABS | 4 | NZ | A = [nnnn] |
| $F5 | MOV A,nnnn+X | ABS+X | 5 | NZ | A = [nnnn+X] |
| $F6 | MOV A,nnnn+Y | ABS+Y | 5 | NZ | A = [nnnn+Y] |
| $E7 | MOV A,[nn+X] | [DP+X] | 6 | NZ | A = [[nn+X]] |
| $F7 | MOV A,[nn]+Y | [DP]+Y | 6 | NZ | A = [[nn]+Y] |
| $7D | MOV A,X | IMP | 2 | NZ | A = X |
| $DD | MOV A,Y | IMP | 2 | NZ | A = Y |
| $CD | MOV X,#nn | IMM | 2 | NZ | X = immediate |
| $5D | MOV X,A | IMP | 2 | NZ | X = A |
| $F8 | MOV X,nn | DP | 3 | NZ | X = [DP+nn] |
| $F9 | MOV X,nn+Y | DP+Y | 4 | NZ | X = [DP+nn+Y] |
| $E9 | MOV X,nnnn | ABS | 4 | NZ | X = [nnnn] |
| $8D | MOV Y,#nn | IMM | 2 | NZ | Y = immediate |
| $6D | MOV Y,A | IMP | 2 | NZ | Y = A |
| $EB | MOV Y,nn | DP | 3 | NZ | Y = [DP+nn] |
| $FB | MOV Y,nn+X | DP+X | 4 | NZ | Y = [DP+nn+X] |
| $EC | MOV Y,nnnn | ABS | 4 | NZ | Y = [nnnn] |
| $C4 | MOV nn,A | DP | 4 | - | [DP+nn] = A |
| $D4 | MOV nn+X,A | DP+X | 5 | - | [DP+nn+X] = A |
| $C5 | MOV nnnn,A | ABS | 5 | - | [nnnn] = A |
| $D5 | MOV nnnn+X,A | ABS+X | 6 | - | [nnnn+X] = A |
| $D6 | MOV nnnn+Y,A | ABS+Y | 6 | - | [nnnn+Y] = A |
| $C7 | MOV [nn+X],A | [DP+X] | 7 | - | [[nn+X]] = A |
| $D7 | MOV [nn]+Y,A | [DP]+Y | 7 | - | [[nn]+Y] = A |
| $C6 | MOV (X),A | (X) | 4 | - | [$00+X] = A |
| $AF | MOV (X)+,A | (X)+ | 4 | - | [$00+X] = A, X++ |
| $D8 | MOV nn,X | DP | 4 | - | [DP+nn] = X |
| $D9 | MOV nn+Y,X | DP+Y | 5 | - | [DP+nn+Y] = X |
| $C9 | MOV nnnn,X | ABS | 5 | - | [nnnn] = X |
| $CB | MOV nn,Y | DP | 4 | - | [DP+nn] = Y |
| $DB | MOV nn+X,Y | DP+X | 5 | - | [DP+nn+X] = Y |
| $CC | MOV nnnn,Y | ABS | 5 | - | [nnnn] = Y |
| $BA | MOVW YA,nn | DP | 5 | NZ | YA = [DP+nn] (16-bit) |
| $DA | MOVW nn,YA | DP | 5 | - | [DP+nn] = YA (16-bit) |

### 2.3.2 Arithmetic Instructions

#### ADC - Add with Carry

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $88 | ADC A,#nn | IMM | 2 | NVHZC | A = A + nn + C |
| $86 | ADC A,(X) | (X) | 3 | NVHZC | A = A + [X] + C |
| $84 | ADC A,nn | DP | 3 | NVHZC | A = A + [DP+nn] + C |
| $94 | ADC A,nn+X | DP+X | 4 | NVHZC | A = A + [DP+nn+X] + C |
| $85 | ADC A,nnnn | ABS | 4 | NVHZC | A = A + [nnnn] + C |
| $95 | ADC A,nnnn+X | ABS+X | 5 | NVHZC | A = A + [nnnn+X] + C |
| $96 | ADC A,nnnn+Y | ABS+Y | 5 | NVHZC | A = A + [nnnn+Y] + C |
| $87 | ADC A,[nn+X] | [DP+X] | 6 | NVHZC | A = A + [[nn+X]] + C |
| $97 | ADC A,[nn]+Y | [DP]+Y | 6 | NVHZC | A = A + [[nn]+Y] + C |
| $99 | ADC (X),(Y) | (X),(Y) | 5 | NVHZC | [X] = [X] + [Y] + C |
| $89 | ADC nn,nn | DP,DP | 6 | NVHZC | [DP+nn] = [DP+nn] + [DP+nn] + C |

#### SBC - Subtract with Carry

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $A8 | SBC A,#nn | IMM | 2 | NVHZC | A = A - nn - ~C |
| $A6 | SBC A,(X) | (X) | 3 | NVHZC | A = A - [X] - ~C |
| $A4 | SBC A,nn | DP | 3 | NVHZC | A = A - [DP+nn] - ~C |
| $B4 | SBC A,nn+X | DP+X | 4 | NVHZC | A = A - [DP+nn+X] - ~C |
| $A5 | SBC A,nnnn | ABS | 4 | NVHZC | A = A - [nnnn] - ~C |
| $B5 | SBC A,nnnn+X | ABS+X | 5 | NVHZC | A = A - [nnnn+X] - ~C |
| $B6 | SBC A,nnnn+Y | ABS+Y | 5 | NVHZC | A = A - [nnnn+Y] - ~C |
| $A7 | SBC A,[nn+X] | [DP+X] | 6 | NVHZC | A = A - [[nn+X]] - ~C |
| $B7 | SBC A,[nn]+Y | [DP]+Y | 6 | NVHZC | A = A - [[nn]+Y] - ~C |
| $B9 | SBC (X),(Y) | (X),(Y) | 5 | NVHZC | [X] = [X] - [Y] - ~C |

#### CMP - Compare

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $68 | CMP A,#nn | IMM | 2 | NZC | A - nn |
| $66 | CMP A,(X) | (X) | 3 | NZC | A - [X] |
| $64 | CMP A,nn | DP | 3 | NZC | A - [DP+nn] |
| $74 | CMP A,nn+X | DP+X | 4 | NZC | A - [DP+nn+X] |
| $65 | CMP A,nnnn | ABS | 4 | NZC | A - [nnnn] |
| $75 | CMP A,nnnn+X | ABS+X | 5 | NZC | A - [nnnn+X] |
| $76 | CMP A,nnnn+Y | ABS+Y | 5 | NZC | A - [nnnn+Y] |
| $67 | CMP A,[nn+X] | [DP+X] | 6 | NZC | A - [[nn+X]] |
| $77 | CMP A,[nn]+Y | [DP]+Y | 6 | NZC | A - [[nn]+Y] |
| $79 | CMP (X),(Y) | (X),(Y) | 5 | NZC | [X] - [Y] |
| $C8 | CMP X,#nn | IMM | 2 | NZC | X - nn |
| $3E | CMP X,nn | DP | 3 | NZC | X - [DP+nn] |
| $1E | CMP X,nnnn | ABS | 4 | NZC | X - [nnnn] |
| $AD | CMP Y,#nn | IMM | 2 | NZC | Y - nn |
| $7E | CMP Y,nn | DP | 3 | NZC | Y - [DP+nn] |
| $5E | CMP Y,nnnn | ABS | 4 | NZC | Y - [nnnn] |

### 2.3.3 Logical Instructions

#### AND - Logical AND

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $28 | AND A,#nn | IMM | 2 | NZ | A = A & nn |
| $26 | AND A,(X) | (X) | 3 | NZ | A = A & [X] |
| $24 | AND A,nn | DP | 3 | NZ | A = A & [DP+nn] |
| $34 | AND A,nn+X | DP+X | 4 | NZ | A = A & [DP+nn+X] |
| $25 | AND A,nnnn | ABS | 4 | NZ | A = A & [nnnn] |
| $35 | AND A,nnnn+X | ABS+X | 5 | NZ | A = A & [nnnn+X] |
| $36 | AND A,nnnn+Y | ABS+Y | 5 | NZ | A = A & [nnnn+Y] |
| $27 | AND A,[nn+X] | [DP+X] | 6 | NZ | A = A & [[nn+X]] |
| $37 | AND A,[nn]+Y | [DP]+Y | 6 | NZ | A = A & [[nn]+Y] |
| $39 | AND (X),(Y) | (X),(Y) | 5 | NZ | [X] = [X] & [Y] |

#### OR - Logical OR

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $08 | OR A,#nn | IMM | 2 | NZ | A = A \| nn |
| $06 | OR A,(X) | (X) | 3 | NZ | A = A \| [X] |
| $04 | OR A,nn | DP | 3 | NZ | A = A \| [DP+nn] |
| $14 | OR A,nn+X | DP+X | 4 | NZ | A = A \| [DP+nn+X] |
| $05 | OR A,nnnn | ABS | 4 | NZ | A = A \| [nnnn] |
| $15 | OR A,nnnn+X | ABS+X | 5 | NZ | A = A \| [nnnn+X] |
| $16 | OR A,nnnn+Y | ABS+Y | 5 | NZ | A = A \| [nnnn+Y] |
| $07 | OR A,[nn+X] | [DP+X] | 6 | NZ | A = A \| [[nn+X]] |
| $17 | OR A,[nn]+Y | [DP]+Y | 6 | NZ | A = A \| [[nn]+Y] |
| $19 | OR (X),(Y) | (X),(Y) | 5 | NZ | [X] = [X] \| [Y] |

#### EOR - Exclusive OR

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $48 | EOR A,#nn | IMM | 2 | NZ | A = A ^ nn |
| $46 | EOR A,(X) | (X) | 3 | NZ | A = A ^ [X] |
| $44 | EOR A,nn | DP | 3 | NZ | A = A ^ [DP+nn] |
| $54 | EOR A,nn+X | DP+X | 4 | NZ | A = A ^ [DP+nn+X] |
| $45 | EOR A,nnnn | ABS | 4 | NZ | A = A ^ [nnnn] |
| $55 | EOR A,nnnn+X | ABS+X | 5 | NZ | A = A ^ [nnnn+X] |
| $56 | EOR A,nnnn+Y | ABS+Y | 5 | NZ | A = A ^ [nnnn+Y] |
| $47 | EOR A,[nn+X] | [DP+X] | 6 | NZ | A = A ^ [[nn+X]] |
| $57 | EOR A,[nn]+Y | [DP]+Y | 6 | NZ | A = A ^ [[nn]+Y] |
| $59 | EOR (X),(Y) | (X),(Y) | 5 | NZ | [X] = [X] ^ [Y] |

### 2.3.4 Increment/Decrement Instructions

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $BC | INC A | IMP | 2 | NZ | A++ |
| $AB | INC nn | DP | 4 | NZ | [DP+nn]++ |
| $BB | INC nn+X | DP+X | 5 | NZ | [DP+nn+X]++ |
| $AC | INC nnnn | ABS | 5 | NZ | [nnnn]++ |
| $3D | INC X | IMP | 2 | NZ | X++ |
| $FC | INC Y | IMP | 2 | NZ | Y++ |
| $9C | DEC A | IMP | 2 | NZ | A-- |
| $8B | DEC nn | DP | 4 | NZ | [DP+nn]-- |
| $9B | DEC nn+X | DP+X | 5 | NZ | [DP+nn+X]-- |
| $8C | DEC nnnn | ABS | 5 | NZ | [nnnn]-- |
| $1D | DEC X | IMP | 2 | NZ | X-- |
| $DC | DEC Y | IMP | 2 | NZ | Y-- |

### 2.3.5 Shift and Rotate Instructions

#### ASL - Arithmetic Shift Left

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $1C | ASL A | IMP | 2 | NZC | A <<= 1 |
| $0B | ASL nn | DP | 4 | NZC | [DP+nn] <<= 1 |
| $1B | ASL nn+X | DP+X | 5 | NZC | [DP+nn+X] <<= 1 |
| $0C | ASL nnnn | ABS | 5 | NZC | [nnnn] <<= 1 |

#### LSR - Logical Shift Right

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $5C | LSR A | IMP | 2 | NZC | A >>= 1 |
| $4B | LSR nn | DP | 4 | NZC | [DP+nn] >>= 1 |
| $5B | LSR nn+X | DP+X | 5 | NZC | [DP+nn+X] >>= 1 |
| $4C | LSR nnnn | ABS | 5 | NZC | [nnnn] >>= 1 |

#### ROL - Rotate Left

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $3C | ROL A | IMP | 2 | NZC | A = (A << 1) \| C |
| $2B | ROL nn | DP | 4 | NZC | [DP+nn] = ([DP+nn] << 1) \| C |
| $3B | ROL nn+X | DP+X | 5 | NZC | [DP+nn+X] = ([DP+nn+X] << 1) \| C |
| $2C | ROL nnnn | ABS | 5 | NZC | [nnnn] = ([nnnn] << 1) \| C |

#### ROR - Rotate Right

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $7C | ROR A | IMP | 2 | NZC | A = (A >> 1) \| (C << 7) |
| $6B | ROR nn | DP | 4 | NZC | [DP+nn] = ([DP+nn] >> 1) \| (C << 7) |
| $7B | ROR nn+X | DP+X | 5 | NZC | [DP+nn+X] = ([DP+nn+X] >> 1) \| (C << 7) |
| $6C | ROR nnnn | ABS | 5 | NZC | [nnnn] = ([nnnn] >> 1) \| (C << 7) |

#### XCN - Exchange Nibbles

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $9F | XCN A | IMP | 5 | NZ | A = (A << 4) \| (A >> 4) |

### 2.3.6 Bit Manipulation Instructions

#### SET1/CLR1 - Set/Clear Bit

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $02 | SET1 nn.0 | DP_BIT | 4 | - | Set bit 0 of [DP+nn] |
| $22 | SET1 nn.1 | DP_BIT | 4 | - | Set bit 1 of [DP+nn] |
| $42 | SET1 nn.2 | DP_BIT | 4 | - | Set bit 2 of [DP+nn] |
| $62 | SET1 nn.3 | DP_BIT | 4 | - | Set bit 3 of [DP+nn] |
| $82 | SET1 nn.4 | DP_BIT | 4 | - | Set bit 4 of [DP+nn] |
| $A2 | SET1 nn.5 | DP_BIT | 4 | - | Set bit 5 of [DP+nn] |
| $C2 | SET1 nn.6 | DP_BIT | 4 | - | Set bit 6 of [DP+nn] |
| $E2 | SET1 nn.7 | DP_BIT | 4 | - | Set bit 7 of [DP+nn] |
| $12 | CLR1 nn.0 | DP_BIT | 4 | - | Clear bit 0 of [DP+nn] |
| $32 | CLR1 nn.1 | DP_BIT | 4 | - | Clear bit 1 of [DP+nn] |
| $52 | CLR1 nn.2 | DP_BIT | 4 | - | Clear bit 2 of [DP+nn] |
| $72 | CLR1 nn.3 | DP_BIT | 4 | - | Clear bit 3 of [DP+nn] |
| $92 | CLR1 nn.4 | DP_BIT | 4 | - | Clear bit 4 of [DP+nn] |
| $B2 | CLR1 nn.5 | DP_BIT | 4 | - | Clear bit 5 of [DP+nn] |
| $D2 | CLR1 nn.6 | DP_BIT | 4 | - | Clear bit 6 of [DP+nn] |
| $F2 | CLR1 nn.7 | DP_BIT | 4 | - | Clear bit 7 of [DP+nn] |

#### NOT1 - Complement Bit

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $EA | NOT1 nn.nn | ABS_BIT | 5 | C | C = ~C, complement bit |

#### MOV1 - Move Bit

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $AA | MOV1 C,nn.nn | ABS_BIT | 4 | C | C = bit |
| $CA | MOV1 nn.nn,C | ABS_BIT | 6 | - | bit = C |

#### AND1 - AND with Carry

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $4A | AND1 C,nn.nn | ABS_BIT | 4 | C | C = C & bit |
| $6A | AND1 C,/nn.nn | ABS_BIT | 4 | C | C = C & ~bit |

#### OR1 - OR with Carry

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $0A | OR1 C,nn.nn | ABS_BIT | 5 | C | C = C \| bit |
| $2A | OR1 C,/nn.nn | ABS_BIT | 5 | C | C = C \| ~bit |

#### EOR1 - XOR with Carry

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $8A | EOR1 C,nn.nn | ABS_BIT | 5 | C | C = C ^ bit |

#### TSET1/TCLR1 - Test and Set/Clear Bit

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $0E | TSET1 nnnn | ABS | 6 | NZ | A & [nnnn], then [nnnn] \|= A |
| $4E | TCLR1 nnnn | ABS | 6 | NZ | A & [nnnn], then [nnnn] &= ~A |

### 2.3.7 Branch Instructions

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $2F | BRA nn | REL | 4 | - | Branch always |
| $F0 | BEQ nn | REL | 2/4 | - | Branch if Z=1 |
| $D0 | BNE nn | REL | 2/4 | - | Branch if Z=0 |
| $B0 | BCS nn | REL | 2/4 | - | Branch if C=1 |
| $90 | BCC nn | REL | 2/4 | - | Branch if C=0 |
| $30 | BMI nn | REL | 2/4 | - | Branch if N=1 |
| $10 | BPL nn | REL | 2/4 | - | Branch if N=0 |
| $70 | BVS nn | REL | 2/4 | - | Branch if V=1 |
| $50 | BVC nn | REL | 2/4 | - | Branch if V=0 |

#### BBS - Branch if Bit Set

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $03 | BBS0 nn,nn | DP_BIT,REL | 5/7 | - | Branch if bit 0 set |
| $23 | BBS1 nn,nn | DP_BIT,REL | 5/7 | - | Branch if bit 1 set |
| $43 | BBS2 nn,nn | DP_BIT,REL | 5/7 | - | Branch if bit 2 set |
| $63 | BBS3 nn,nn | DP_BIT,REL | 5/7 | - | Branch if bit 3 set |
| $83 | BBS4 nn,nn | DP_BIT,REL | 5/7 | - | Branch if bit 4 set |
| $A3 | BBS5 nn,nn | DP_BIT,REL | 5/7 | - | Branch if bit 5 set |
| $C3 | BBS6 nn,nn | DP_BIT,REL | 5/7 | - | Branch if bit 6 set |
| $E3 | BBS7 nn,nn | DP_BIT,REL | 5/7 | - | Branch if bit 7 set |

#### BBC - Branch if Bit Clear

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $13 | BBC0 nn,nn | DP_BIT,REL | 5/7 | - | Branch if bit 0 clear |
| $33 | BBC1 nn,nn | DP_BIT,REL | 5/7 | - | Branch if bit 1 clear |
| $53 | BBC2 nn,nn | DP_BIT,REL | 5/7 | - | Branch if bit 2 clear |
| $73 | BBC3 nn,nn | DP_BIT,REL | 5/7 | - | Branch if bit 3 clear |
| $93 | BBC4 nn,nn | DP_BIT,REL | 5/7 | - | Branch if bit 4 clear |
| $B3 | BBC5 nn,nn | DP_BIT,REL | 5/7 | - | Branch if bit 5 clear |
| $D3 | BBC6 nn,nn | DP_BIT,REL | 5/7 | - | Branch if bit 6 clear |
| $F3 | BBC7 nn,nn | DP_BIT,REL | 5/7 | - | Branch if bit 7 clear |

#### CBNE/DBNZ - Compare and Branch

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $2E | CBNE nn,nn | DP,REL | 5/7 | - | Branch if A != [DP+nn] |
| $DE | CBNE nn+X,nn | DP+X,REL | 6/8 | - | Branch if A != [DP+nn+X] |
| $6E | DBNZ nn,nn | DP,REL | 5/7 | - | [DP+nn]--, branch if != 0 |
| $FE | DBNZ Y,nn | REL | 4/6 | - | Y--, branch if != 0 |

### 2.3.8 Jump and Call Instructions

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $5F | JMP nnnn | ABS | 3 | - | PC = nnnn |
| $1F | JMP [nnnn+X] | ABS+X | 6 | - | PC = [[nnnn+X]] |
| $3F | CALL nnnn | ABS | 8 | - | Push PC, PC = nnnn |
| $4F | PCALL nn | DP | 6 | - | Push PC, PC = $FF00+nn |
| $01-$0F | TCALL n | IMP | 8 | - | Table call (n=0-15) |
| $6F | RET | IMP | 5 | - | Pop PC |
| $7F | RETI | IMP | 6 | - | Pop PC and PSW |
| $0F | BRK | IMP | 8 | - | Software interrupt |

### 2.3.9 Stack Instructions

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $2D | PUSH A | IMP | 4 | - | Push A to stack |
| $4D | PUSH X | IMP | 4 | - | Push X to stack |
| $6D | PUSH Y | IMP | 4 | - | Push Y to stack |
| $0D | PUSH PSW | IMP | 4 | - | Push PSW to stack |
| $AE | POP A | IMP | 4 | - | Pop A from stack |
| $CE | POP X | IMP | 4 | - | Pop X from stack |
| $EE | POP Y | IMP | 4 | - | Pop Y from stack |
| $8E | POP PSW | IMP | 4 | NZ | Pop PSW from stack |

### 2.3.10 Multiply and Divide

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $CF | MUL YA | IMP | 9 | NZ | YA = Y * A (unsigned) |
| $9E | DIV YA,X | IMP | 12 | NZVH | YA/X, A=quotient, Y=remainder |

### 2.3.11 Decimal Adjust

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $DF | DAA | IMP | 3 | NZC | Decimal adjust A (addition) |
| $BE | DAS | IMP | 3 | NZC | Decimal adjust A (subtraction) |

### 2.3.12 Control Instructions

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $EF | SLEEP | IMP | 3 | - | Enter sleep mode |
| $FF | STOP | IMP | 3 | - | Enter stop mode |
| $00 | NOP | IMP | 2 | - | No operation |

### 2.3.13 Flag Instructions

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $60 | CLRC | IMP | 2 | C=0 | Clear carry |
| $80 | SETC | IMP | 2 | C=1 | Set carry |
| $ED | NOTC | IMP | 3 | C=~C | Complement carry |
| $20 | CLRP | IMP | 2 | P=0 | Clear direct page |
| $40 | SETP | IMP | 2 | P=1 | Set direct page |
| $C0 | DI | IMP | 3 | I=0 | Disable interrupts |
| $A0 | EI | IMP | 3 | I=1 | Enable interrupts |
| $02-$0F | SET1 nn.n | DP_BIT | 4 | - | Set bit |
| $12-$1F | CLR1 nn.n | DP_BIT | 4 | - | Clear bit |

### 2.3.14 Transfer Instructions

| Opcode | Mnemonic | Mode | Cycles | Flags | Description |
|--------|----------|------|--------|-------|-------------|
| $9F | XCN A | IMP | 5 | NZ | Exchange nibbles of A |
| $BA | MOVW YA,nn | DP | 5 | NZ | YA = [nn] (16-bit) |
| $DA | MOVW nn,YA | DP | 5 | - | [nn] = YA (16-bit) |

### 2.3.15 TCALL Vector Table

| Opcode | Vector Address | Description |
|--------|----------------|-------------|
| $01 | $FFDE | TCALL 0 |
| $11 | $FFDC | TCALL 1 |
| $21 | $FFDA | TCALL 2 |
| $31 | $FFD8 | TCALL 3 |
| $41 | $FFD6 | TCALL 4 |
| $51 | $FFD4 | TCALL 5 |
| $61 | $FFD2 | TCALL 6 |
| $71 | $FFD0 | TCALL 7 |
| $81 | $FFCE | TCALL 8 |
| $91 | $FFCC | TCALL 9 |
| $A1 | $FFCA | TCALL 10 |
| $B1 | $FFC8 | TCALL 11 |
| $C1 | $FFC6 | TCALL 12 |
| $D1 | $FFC4 | TCALL 13 |
| $E1 | $FFC2 | TCALL 14 |
| $F1 | $FFC0 | TCALL 15 |



---

# 3. SPC700 Registers

## 3.1 Register Overview

The SPC700 contains six primary registers for program execution:

| Register | Size | Description |
|----------|------|-------------|
| **A** | 8-bit | Accumulator |
| **X** | 8-bit | Index Register X |
| **Y** | 8-bit | Index Register Y |
| **SP** | 8-bit | Stack Pointer |
| **PSW** | 8-bit | Program Status Word (flags) |
| **PC** | 16-bit | Program Counter |
| **YA** | 16-bit | Combined A (low) and Y (high) |

## 3.2 Accumulator (A)

- **Size:** 8 bits
- **Purpose:** Primary arithmetic and logic register
- **Usage:** Most arithmetic, logical, and data transfer operations use A
- **Special Functions:**
  - Combined with Y to form 16-bit YA register
  - Used in MUL/DIV operations
  - Default destination for most operations

## 3.3 Index Register X

- **Size:** 8 bits
- **Purpose:** Index register for memory addressing
- **Usage:** 
  - Indexed addressing modes (nn+X, nnnn+X)
  - Indirect addressing via (X)
  - Counter for loops
- **Special Functions:**
  - Used as divisor in DIV instruction
  - Auto-increment in (X)+ addressing mode

## 3.4 Index Register Y

- **Size:** 8 bits
- **Purpose:** Index register for memory addressing
- **Usage:**
  - Indexed addressing modes (nn+Y, nnnn+Y)
  - Combined with A to form 16-bit YA register
- **Special Functions:**
  - Used as multiplier in MUL instruction
  - High byte of YA register

## 3.5 Stack Pointer (SP)

- **Size:** 8 bits
- **Range:** $00-$FF (points to $0100-$01FF)
- **Purpose:** Points to next free stack location
- **Stack Location:** Page $01 ($0100-$01FF)
- **Operations:**
  - PUSH: [SP] = data, SP--
  - POP: SP++, data = [SP]
- **Reset Value:** $FF

**Stack Operations:**
```
PUSH A:  [SP] = A, SP = SP - 1
POP A:   SP = SP + 1, A = [SP]
```

## 3.6 Program Counter (PC)

- **Size:** 16 bits
- **Range:** $0000-$FFFF
- **Purpose:** Points to next instruction to execute
- **Reset Value:** Fetched from $FFFE-$FFFF (vector)

## 3.7 Program Status Word (PSW)

The PSW contains all processor status flags:

```
Bit 7: N (Negative)      - Set if result bit 7 = 1
Bit 6: V (Overflow)      - Set on signed overflow
Bit 5: P (Direct Page)   - Direct page select (0=$0000, 1=$0100)
Bit 4: B (Break)         - Set if interrupt from BRK
Bit 3: H (Half-carry)    - Carry from bit 3 to 4 (BCD)
Bit 2: I (Interrupt)     - Interrupt disable flag
Bit 1: Z (Zero)          - Set if result = 0
Bit 0: C (Carry)         - Carry/borrow flag
```

### PSW Bit Descriptions

| Bit | Flag | Name | Set When | Clear When |
|-----|------|------|----------|------------|
| 7 | N | Negative | Result bit 7 = 1 | Result bit 7 = 0 |
| 6 | V | Overflow | Signed overflow | No overflow |
| 5 | P | Direct Page | DP = $0100 | DP = $0000 |
| 4 | B | Break | BRK instruction | Other interrupts |
| 3 | H | Half-carry | Carry from bit 3 | No carry from bit 3 |
| 2 | I | Interrupt | Interrupts disabled | Interrupts enabled |
| 1 | Z | Zero | Result = 0 | Result != 0 |
| 0 | C | Carry | Carry occurred | No carry |

### PSW Flag Operations

| Instruction | Effect |
|-------------|--------|
| CLRC | C = 0 |
| SETC | C = 1 |
| NOTC | C = ~C |
| CLRP | P = 0 |
| SETP | P = 1 |
| EI | I = 1 |
| DI | I = 0 |

## 3.8 Combined YA Register

- **Size:** 16 bits
- **Composition:** Y (high byte) + A (low byte)
- **Purpose:** 16-bit operations
- **Instructions:**
  - MUL: YA = Y * A (unsigned multiply)
  - DIV: YA / X, A = quotient, Y = remainder
  - MOVW YA,nn: Load 16-bit value
  - MOVW nn,YA: Store 16-bit value

**YA Register Layout:**
```
  15      8 7       0
  +--------+--------+
  |   Y    |   A    |
  +--------+--------+
```

## 3.9 Register Summary Table

| Register | Reset Value | Description |
|----------|-------------|-------------|
| A | Undefined | Accumulator |
| X | Undefined | Index X |
| Y | Undefined | Index Y |
| SP | $FF | Stack pointer |
| PSW | $00 | Flags (I=0, others=0) |
| PC | [$FFFE] | Program counter |

---

# 4. S-DSP Architecture

## 4.1 Overview

The S-DSP (Sony Digital Signal Processor) is the sound generation chip in the SNES audio subsystem. It works in conjunction with the SPC700 to generate high-quality audio output.

## 4.2 Core Specifications

| Parameter | Specification |
|-----------|---------------|
| **Clock Speed** | 1.024 MHz (same as SPC700) |
| **Voice Channels** | 8 independent voices |
| **Sample Rate** | 32 kHz output |
| **Bit Depth** | 16-bit internal, 16-bit output |
| **Sample Format** | BRR (Bit Rate Reduction) compressed |
| **Interpolation** | 4-point Gaussian |
| **Echo Buffer** | Up to 240ms delay |
| **FIR Filter** | 8-tap for echo processing |

## 4.3 Voice Channel Architecture

Each of the 8 voices contains:

```
+--------------------------------------------------+
|                  VOICE CHANNEL N                 |
+--------------------------------------------------+
|  +------------+    +---------------------------+ |
|  | Volume L   |--->|                           | |
|  | Volume R   |--->|                           | |
|  | Pitch      |--->|   Gaussian Interpolator   | |
|  | Source     |--->|         + BRR Decoder     | |
|  | ADSR/GAIN  |--->|                           | |
|  +------------+    +---------------------------+ |
|                             |                    |
|                             v                    |
|                    +------------------+          |
|                    |   Envelope Gen   |          |
|                    +------------------+          |
|                             |                    |
|                             v                    |
|                    +------------------+          |
|                    |   Output Mixer     |        |
|                    +------------------+          |
+--------------------------------------------------+
```

## 4.4 BRR (Bit Rate Reduction) Format

The S-DSP uses a proprietary compressed sample format called BRR.

### BRR Block Structure

Each BRR block is 9 bytes:

```
Byte 0: Header byte
Bytes 1-8: 16 4-bit samples (compressed)
```

### BRR Header Byte

```
Bit 7: Loop end flag (1 = last block in loop)
Bit 6: Loop flag (1 = sample loops)
Bits 5-4: Filter mode (0-3)
Bits 3-0: Shift value (0-12, 13-15 invalid)
```

### BRR Filter Modes

| Filter | Description | Formula |
|--------|-------------|---------|
| 0 | No filter | Sample = nibble << shift |
| 1 | Light filter | Sample = (nibble << shift) + (old * 1) |
| 2 | Medium filter | Sample = (nibble << shift) + (old * 2) - (older * 1) |
| 3 | Heavy filter | Sample = (nibble << shift) + (old * 2) - (older * 2) |

## 4.5 Gaussian Interpolation

The S-DSP uses a 4-point Gaussian interpolation for smooth sample playback:

```
Output = Sample[-1] * G3 + Sample[0] * G2 + Sample[1] * G1 + Sample[2] * G0
```

Where G0-G3 are Gaussian coefficients based on the fractional part of the sample position.

## 4.6 ADSR Envelope Generator

Each voice has an ADSR (Attack, Decay, Sustain, Release) envelope generator:

```
Level
  |
  |     Attack        Decay         Sustain
  |    /--------\    /      \________________
  |   /          \  /
  |  /            \/
  | /
  +-------------------------------------------> Time
                        |         |
                        |<-Sustain|->
                        |  Level  |
```

### ADSR Parameters

| Stage | Rate | Description |
|-------|------|-------------|
| Attack | 0-15 | How fast level rises from 0 |
| Decay | 0-7 | How fast level falls to sustain |
| Sustain | 0-7 | Sustain level (0-7, scaled to 0-100%) |
| Sustain Rate | 0-31 | How level changes during sustain |

## 4.7 GAIN Mode

Alternative to ADSR, GAIN provides direct envelope control:

| Mode | Description |
|------|-------------|
| Linear Decrease | Decrease at fixed rate |
| Linear Increase | Increase at fixed rate |
| Bent Increase | Slow increase then fast |
| Bent Decrease | Fast decrease then slow |
| Direct | Set envelope directly |

## 4.8 Echo Processing

The S-DSP includes a configurable echo effect:

```
+-------------+     +-------------+     +-------------+
|   Input     |---->|   Delay     |---->|    FIR      |
|   Mix       |     |   Buffer    |     |   Filter    |
+-------------+     +-------------+     +-------------+
                                               |
+-------------+     +-------------+            |
|   Output    |<----|   Echo      |<-----------+
|   Mix       |     |   Volume    |
+-------------+     +-------------+
```

### Echo Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| EDL (Echo Delay) | 0-15 | Echo buffer size (in 16ms steps) |
| EFB (Echo Feedback) | 0-127 | Feedback amount |
| EVOL (Echo Volume) | 0-127 | Left/Right echo volume |
| FIR Coefficients | 8 values | Filter coefficients |

## 4.9 Noise Generator

The S-DSP includes a pseudo-random noise generator:

- **Type:** Linear Feedback Shift Register (LFSR)
- **Period:** 32767 samples
- **Clock:** Programmable (frequency divider)
- **Usage:** Can replace sample data on any voice

## 4.10 Pitch Modulation

The S-DSP supports pitch modulation where one voice can modulate another:

```
Voice N Output -----> Voice N+1 Pitch Input
```

This allows for effects like vibrato and FM synthesis.

## 4.11 Global Sound Processing Flow

```
+----------------------------------------------------------+
|                    S-DSP AUDIO PATH                      |
+----------------------------------------------------------+
|                                                          |
|  +--------+  +--------+  +--------+  +--------+         |
|  | Voice 0|  | Voice 1|  | Voice 2|  | Voice 3|         |
|  +---+----+  +---+----+  +---+----+  +---+----+         |
|      |          |          |          |                 |
|  +---+----+  +---+----+  +---+----+  +---+----+         |
|  | Voice 4|  | Voice 5|  | Voice 6|  | Voice 7|         |
|  +---+----+  +---+----+  +---+----+  +---+----+         |
|      |          |          |          |                 |
|      +----------+----------+----------+                 |
|                    |                                     |
|            +-------v--------+                          |
|            |  Main Mixer    |                          |
|            +-------+--------+                          |
|                    |                                     |
|            +-------v--------+    +-------------+       |
|            |  Echo Buffer   |--->|  FIR Filter |       |
|            +-------+--------+    +------+------+       |
|                    |                    |               |
|            +-------v--------+    +------v------+       |
|            |  Echo Mixer    |<---| Echo Volume |       |
|            +-------+--------+    +-------------+       |
|                    |                                     |
|            +-------v--------+                          |
|            |  Final Output  |                          |
|            |  (16-bit L/R)  |                          |
|            +----------------+                          |
|                                                          |
+----------------------------------------------------------+
```



---

# 5. DSP Register Map

## 5.1 Register Access

DSP registers are accessed through SPC700 I/O ports:
- **$F2 (DSPADDR):** Select DSP register address (0-127)
- **$F3 (DSPDATA):** Read/write DSP register data

## 5.2 Voice Register Layout

Each voice has 10 registers at addresses $x0-$x9, where x = voice number (0-7):

| Address | Register | Description |
|---------|----------|-------------|
| $x0 | VOL(R) | Volume Right |
| $x1 | VOL(L) | Volume Left |
| $x2 | PITCH(L) | Pitch (lower 8 bits) |
| $x3 | PITCH(H) | Pitch (upper 4 bits) |
| $x4 | SRCN | Source Number (sample index) |
| $x5 | ADSR(1) | ADSR configuration 1 |
| $x6 | ADSR(2) | ADSR configuration 2 |
| $x7 | GAIN | GAIN envelope control |
| $x8 | ENVX | Current envelope value (read-only) |
| $x9 | OUTX | Current output value (read-only) |

## 5.3 Voice 0 Registers ($00-$09)

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $00 | V0VOLL | R/W | Voice 0 Volume Left |
| $01 | V0VOLR | R/W | Voice 0 Volume Right |
| $02 | V0PITCHL | R/W | Voice 0 Pitch (low) |
| $03 | V0PITCHH | R/W | Voice 0 Pitch (high) |
| $04 | V0SRCN | R/W | Voice 0 Source Number |
| $05 | V0ADSR1 | R/W | Voice 0 ADSR 1 |
| $06 | V0ADSR2 | R/W | Voice 0 ADSR 2 |
| $07 | V0GAIN | R/W | Voice 0 GAIN |
| $08 | V0ENVX | R | Voice 0 Envelope |
| $09 | V0OUTX | R | Voice 0 Output |

## 5.4 Voice 1 Registers ($10-$19)

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $10 | V1VOLL | R/W | Voice 1 Volume Left |
| $11 | V1VOLR | R/W | Voice 1 Volume Right |
| $12 | V1PITCHL | R/W | Voice 1 Pitch (low) |
| $13 | V1PITCHH | R/W | Voice 1 Pitch (high) |
| $14 | V1SRCN | R/W | Voice 1 Source Number |
| $15 | V1ADSR1 | R/W | Voice 1 ADSR 1 |
| $16 | V1ADSR2 | R/W | Voice 1 ADSR 2 |
| $17 | V1GAIN | R/W | Voice 1 GAIN |
| $18 | V1ENVX | R | Voice 1 Envelope |
| $19 | V1OUTX | R | Voice 1 Output |

## 5.5 Voice 2 Registers ($20-$29)

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $20 | V2VOLL | R/W | Voice 2 Volume Left |
| $21 | V2VOLR | R/W | Voice 2 Volume Right |
| $22 | V2PITCHL | R/W | Voice 2 Pitch (low) |
| $23 | V2PITCHH | R/W | Voice 2 Pitch (high) |
| $24 | V2SRCN | R/W | Voice 2 Source Number |
| $25 | V2ADSR1 | R/W | Voice 2 ADSR 1 |
| $26 | V2ADSR2 | R/W | Voice 2 ADSR 2 |
| $27 | V2GAIN | R/W | Voice 2 GAIN |
| $28 | V2ENVX | R | Voice 2 Envelope |
| $29 | V2OUTX | R | Voice 2 Output |

## 5.6 Voice 3 Registers ($30-$39)

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $30 | V3VOLL | R/W | Voice 3 Volume Left |
| $31 | V3VOLR | R/W | Voice 3 Volume Right |
| $32 | V3PITCHL | R/W | Voice 3 Pitch (low) |
| $33 | V3PITCHH | R/W | Voice 3 Pitch (high) |
| $34 | V3SRCN | R/W | Voice 3 Source Number |
| $35 | V3ADSR1 | R/W | Voice 3 ADSR 1 |
| $36 | V3ADSR2 | R/W | Voice 3 ADSR 2 |
| $37 | V3GAIN | R/W | Voice 3 GAIN |
| $38 | V3ENVX | R | Voice 3 Envelope |
| $39 | V3OUTX | R | Voice 3 Output |

## 5.7 Voice 4 Registers ($40-$49)

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $40 | V4VOLL | R/W | Voice 4 Volume Left |
| $41 | V4VOLR | R/W | Voice 4 Volume Right |
| $42 | V4PITCHL | R/W | Voice 4 Pitch (low) |
| $43 | V4PITCHH | R/W | Voice 4 Pitch (high) |
| $44 | V4SRCN | R/W | Voice 4 Source Number |
| $45 | V4ADSR1 | R/W | Voice 4 ADSR 1 |
| $46 | V4ADSR2 | R/W | Voice 4 ADSR 2 |
| $47 | V4GAIN | R/W | Voice 4 GAIN |
| $48 | V4ENVX | R | Voice 4 Envelope |
| $49 | V4OUTX | R | Voice 4 Output |

## 5.8 Voice 5 Registers ($50-$59)

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $50 | V5VOLL | R/W | Voice 5 Volume Left |
| $51 | V5VOLR | R/W | Voice 5 Volume Right |
| $52 | V5PITCHL | R/W | Voice 5 Pitch (low) |
| $53 | V5PITCHH | R/W | Voice 5 Pitch (high) |
| $54 | V5SRCN | R/W | Voice 5 Source Number |
| $55 | V5ADSR1 | R/W | Voice 5 ADSR 1 |
| $56 | V5ADSR2 | R/W | Voice 5 ADSR 2 |
| $57 | V5GAIN | R/W | Voice 5 GAIN |
| $58 | V5ENVX | R | Voice 5 Envelope |
| $59 | V5OUTX | R | Voice 5 Output |

## 5.9 Voice 6 Registers ($60-$69)

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $60 | V6VOLL | R/W | Voice 6 Volume Left |
| $61 | V6VOLR | R/W | Voice 6 Volume Right |
| $62 | V6PITCHL | R/W | Voice 6 Pitch (low) |
| $63 | V6PITCHH | R/W | Voice 6 Pitch (high) |
| $64 | V6SRCN | R/W | Voice 6 Source Number |
| $65 | V6ADSR1 | R/W | Voice 6 ADSR 1 |
| $66 | V6ADSR2 | R/W | Voice 6 ADSR 2 |
| $67 | V6GAIN | R/W | Voice 6 GAIN |
| $68 | V6ENVX | R | Voice 6 Envelope |
| $69 | V6OUTX | R | Voice 6 Output |

## 5.10 Voice 7 Registers ($70-$79)

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $70 | V7VOLL | R/W | Voice 7 Volume Left |
| $71 | V7VOLR | R/W | Voice 7 Volume Right |
| $72 | V7PITCHL | R/W | Voice 7 Pitch (low) |
| $73 | V7PITCHH | R/W | Voice 7 Pitch (high) |
| $74 | V7SRCN | R/W | Voice 7 Source Number |
| $75 | V7ADSR1 | R/W | Voice 7 ADSR 1 |
| $76 | V7ADSR2 | R/W | Voice 7 ADSR 2 |
| $77 | V7GAIN | R/W | Voice 7 GAIN |
| $78 | V7ENVX | R | Voice 7 Envelope |
| $79 | V7OUTX | R | Voice 7 Output |

## 5.11 Global Registers ($0C-$FF)

### Main Volume Registers

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $0C | MVOLL | R/W | Main Volume Left |
| $1C | MVOLR | R/W | Main Volume Right |

### Echo Volume Registers

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $2C | EVOLL | R/W | Echo Volume Left |
| $3C | EVOLR | R/W | Echo Volume Right |

### Key On/Off Registers

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $4C | KON | W | Key On (start voices) |
| $5C | KOF | W | Key Off (release voices) |

### Flag Register

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $6C | FLG | R/W | DSP Flags |

### End Block Register

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $7C | ENDX | R | End Block (loop status) |

### Echo Feedback and Pitch Modulation

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $0D | EFB | R/W | Echo Feedback |
| $2D | PMON | R/W | Pitch Modulation Enable |

### Noise and Echo Control

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $3D | NON | R/W | Noise Enable |
| $4D | EON | R/W | Echo Enable |
| $5D | DIR | R/W | Sample Directory Address |
| $6D | ESA | R/W | Echo Start Address |

### Echo Delay

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $7D | EDL | R/W | Echo Delay |

### FIR Filter Coefficients

| Address | Register | R/W | Description |
|---------|----------|-----|-------------|
| $0F | COEF0 | R/W | FIR Coefficient 0 |
| $1F | COEF1 | R/W | FIR Coefficient 1 |
| $2F | COEF2 | R/W | FIR Coefficient 2 |
| $3F | COEF3 | R/W | FIR Coefficient 3 |
| $4F | COEF4 | R/W | FIR Coefficient 4 |
| $5F | COEF5 | R/W | FIR Coefficient 5 |
| $6F | COEF6 | R/W | FIR Coefficient 6 |
| $7F | COEF7 | R/W | FIR Coefficient 7 |

## 5.12 Register Bit Definitions

### Volume Registers (VOLL, VOLR, MVOLL, MVOLR, EVOLL, EVOLR)

```
Bits 7-0: Volume level (0-127, signed, 2's complement)
          Range: -128 to +127
          Negative values invert phase
```

### Pitch Registers (PITCHL, PITCHH)

```
Combined 14-bit pitch value:
  PITCH = {PITCHH[5:0], PITCHL[7:0]}
  
Sample rate = (PITCH * 32000) / 4096 Hz
Range: 0 to 16383 (0 to ~128 kHz)
```

### Source Number (SRCN)

```
Bits 7-0: Sample index (0-255)
          Points to sample directory entry
```

### ADSR1 Register

```
Bit 7: ADSR enable (1 = use ADSR, 0 = use GAIN)
Bits 6-4: Decay rate (0-7)
Bits 3-0: Attack rate (0-15)
```

### ADSR2 Register

```
Bit 7: Sustain rate exponential (1 = exponential)
Bits 6-5: Sustain direction (00=none, 01=increase, 10=decrease, 11=decrease exp)
Bits 4-0: Sustain rate (0-31)
```

### GAIN Register

```
When ADSR1 bit 7 = 0:
  Bits 7-5: Mode (0-4)
    000: Direct (set envelope directly)
    101: Linear decrease
    110: Linear increase
    111: Bent increase
  Bits 4-0: Rate/Level
```

### ENVX (Read-Only)

```
Bits 7-0: Current envelope value (0-127)
```

### OUTX (Read-Only)

```
Bits 7-0: Current output value (signed, before volume)
```

### KON (Key On)

```
Bits 7-0: Voice key on (1 = start voice)
Bit n: Start voice n
Writing 1 to a bit starts the corresponding voice
```

### KOF (Key Off)

```
Bits 7-0: Voice key off (1 = release voice)
Bit n: Release voice n
Writing 1 initiates release phase
```

### FLG (Flags)

```
Bit 7: RESET (1 = reset DSP, clear all registers)
Bit 6: MUTE (1 = mute all voices)
Bit 5: ECHO DISABLE (1 = disable echo)
Bits 4-0: Noise clock rate (0-31)
  0 = disable noise
  1-31 = noise frequency divider
```

### ENDX (End Block Status)

```
Bits 7-0: Voice loop status (read-only)
Bit n: Voice n reached loop end
Reading clears all bits
```

### PMON (Pitch Modulation Enable)

```
Bits 7-1: Voice pitch modulation
Bit n: Voice (n+1) uses voice n as modulation source
Bit 0: Unused (voice 0 cannot be modulated)
```

### NON (Noise Enable)

```
Bits 7-0: Voice noise enable
Bit n: Voice n uses noise instead of sample
```

### EON (Echo Enable)

```
Bits 7-0: Voice echo enable
Bit n: Voice n output goes to echo buffer
```

### DIR (Sample Directory)

```
Bits 7-0: Sample directory page address
Address = DIR * $100
```

### ESA (Echo Start Address)

```
Bits 7-0: Echo buffer start page
Address = ESA * $100
```

### EDL (Echo Delay)

```
Bits 3-0: Echo delay
Delay = (EDL * 16ms) + 16ms
Range: 16ms to 256ms
EDL = 0 disables echo
```

### EFB (Echo Feedback)

```
Bits 6-0: Echo feedback level (signed)
Range: -128 to +127
```

### COEFn (FIR Coefficients)

```
Bits 7-0: FIR filter coefficient (signed)
Range: -128 to +127
```

## 5.13 Complete DSP Register Summary

```
Address  Register    Description
-------  --------    -----------
$00-$09  Voice 0     Voice 0 registers
$10-$19  Voice 1     Voice 1 registers
$20-$29  Voice 2     Voice 2 registers
$30-$39  Voice 3     Voice 3 registers
$40-$49  Voice 4     Voice 4 registers
$50-$59  Voice 5     Voice 5 registers
$60-$69  Voice 6     Voice 6 registers
$70-$79  Voice 7     Voice 7 registers

$0C      MVOLL       Main Volume Left
$1C      MVOLR       Main Volume Right
$2C      EVOLL       Echo Volume Left
$3C      EVOLR       Echo Volume Right
$4C      KON         Key On
$5C      KOF         Key Off
$6C      FLG         Flags
$7C      ENDX        End Block Status

$0D      EFB         Echo Feedback
$2D      PMON        Pitch Modulation
$3D      NON         Noise Enable
$4D      EON         Echo Enable
$5D      DIR         Sample Directory
$6D      ESA         Echo Start Address
$7D      EDL         Echo Delay

$0F      COEF0       FIR Coefficient 0
$1F      COEF1       FIR Coefficient 1
$2F      COEF2       FIR Coefficient 2
$3F      COEF3       FIR Coefficient 3
$4F      COEF4       FIR Coefficient 4
$5F      COEF5       FIR Coefficient 5
$6F      COEF6       FIR Coefficient 6
$7F      COEF7       FIR Coefficient 7
```



---

# 6. Audio RAM (ARAM)

## 6.1 Overview

Audio RAM (ARAM) is a 64KB memory space shared between the SPC700 and S-DSP. It stores:
- SPC700 program code
- Sample data (BRR format)
- Sample directory
- Echo buffer
- Variables and working data

## 6.2 Memory Map

```
$0000-$00EF  : Zero Page RAM (SPC700)
$00F0-$00FF  : I/O Registers (SPC700)
$0100-$01FF  : Stack (SPC700)
$0200-$FFC0  : General RAM (code, data, samples)
$FFC0-$FFFF  : IPL ROM (boot code, can be disabled)
```

## 6.3 Typical ARAM Layout

```
+----------------------------------------+ $FFFF
|           IPL ROM (64 bytes)           |
|        (or RAM if IPL disabled)        |
+----------------------------------------+ $FFC0
|                                        |
|         Echo Buffer (variable)         |
|                                        |
+----------------------------------------+ $F000 (example)
|                                        |
|         Sample Data (BRR)              |
|                                        |
+----------------------------------------+ $4000 (example)
|                                        |
|         Sample Directory               |
|                                        |
+----------------------------------------+ $0200 (example)
|         SPC700 Program Code            |
+----------------------------------------+ $0100
|              Stack                     |
+----------------------------------------+ $0000
|           Zero Page / I/O              |
+----------------------------------------+
```

## 6.4 Sample Directory Structure

The sample directory is a table of 4-byte entries, one per sample (up to 256 samples):

```
Entry Format (4 bytes):
  Byte 0-1: Sample start address (16-bit, little-endian)
  Byte 2-3: Loop start address (16-bit, little-endian)
```

### Sample Directory Layout

```
Directory Base Address = DIR * $100

Sample 0: DIR*100 + $00-$03
Sample 1: DIR*100 + $04-$07
Sample 2: DIR*100 + $08-$0B
...
Sample N: DIR*100 + (N * 4) to (N * 4 + 3)
```

### Sample Directory Entry Example

```
Address $2000: Sample Directory (DIR = $20)

$2000-$2001: Sample 0 start address
$2002-$2003: Sample 0 loop address
$2004-$2005: Sample 1 start address
$2006-$2007: Sample 1 loop address
...
```

## 6.5 ARAM Access

### SPC700 Access

The SPC700 can access all 64KB of ARAM directly via its 16-bit address bus.

### Main CPU Access

The main SNES CPU (5A22) accesses ARAM through:
- Communication ports ($2140-$2143)
- Boot ROM transfer protocol
- Direct memory access during IPL boot

---

# 7. BRR Sample Format

## 7.1 Overview

BRR (Bit Rate Reduction) is Sony's proprietary audio compression format used by the S-DSP. It provides approximately 2:1 compression with acceptable quality.

## 7.2 BRR Block Structure

Each BRR block is exactly 9 bytes:

```
Byte 0:    Header byte
Bytes 1-8: 16 compressed samples (4 bits each)
```

### BRR Block Layout

```
+--------+--------+--------+--------+--------+--------+--------+--------+--------+
| Header | Sample | Sample | Sample | Sample | Sample | Sample | Sample | Sample |
| Byte   | 0-1    | 2-3    | 4-5    | 6-7    | 8-9    | 10-11  | 12-13  | 14-15  |
+--------+--------+--------+--------+--------+--------+--------+--------+--------+
   0        1        2        3        4        5        6        7        8
```

## 7.3 BRR Header Byte

```
Bit 7: Loop End Flag (END)
       0 = Not end of loop
       1 = Last block in loop

Bit 6: Loop Flag (LOOP)
       0 = Sample does not loop
       1 = Sample loops to loop address

Bits 5-4: Filter Mode (FILTER)
       00 = No filter
       01 = Light filter
       10 = Medium filter
       11 = Heavy filter

Bits 3-0: Shift Value (SHIFT)
       0-12 = Valid shift values
       13-15 = Invalid (should not be used)
```

### Header Byte Format

```
  7   6   5   4   3   2   1   0
+---+---+---+---+---+---+---+---+
|END|LOOP|  FILTER  |   SHIFT   |
+---+---+---+---+---+---+---+---+
```

## 7.4 BRR Filter Modes

The filter applies prediction to improve compression quality:

### Filter 0: No Filter
```
decoded = (nibble << shift)
```

### Filter 1: Light Filter
```
decoded = (nibble << shift) + (old * 1)
```

### Filter 2: Medium Filter
```
decoded = (nibble << shift) + (old * 2) - (older * 1)
```

### Filter 3: Heavy Filter
```
decoded = (nibble << shift) + (old * 2) - (older * 2)
```

Where:
- `nibble` = 4-bit signed sample (-8 to +7)
- `shift` = shift value from header (0-12)
- `old` = previous decoded sample
- `older` = sample before previous

## 7.5 Sample Nibble Format

Each nibble is a 4-bit signed value:

```
Value Range: -8 to +7
Encoding:
  0 = 0
  1-7 = +1 to +7
  8-F = -8 to -1
```

### Nibble Encoding Table

| Binary | Decimal | Signed Value |
|--------|---------|--------------|
| 0000 | 0 | 0 |
| 0001 | 1 | +1 |
| 0010 | 2 | +2 |
| 0011 | 3 | +3 |
| 0100 | 4 | +4 |
| 0101 | 5 | +5 |
| 0110 | 6 | +6 |
| 0111 | 7 | +7 |
| 1000 | 8 | -8 |
| 1001 | 9 | -7 |
| 1010 | 10 | -6 |
| 1011 | 11 | -5 |
| 1100 | 12 | -4 |
| 1101 | 13 | -3 |
| 1110 | 14 | -2 |
| 1111 | 15 | -1 |

## 7.6 BRR Block Examples

### Example 1: Simple Block (No Filter, Shift 12)

```
Header: $FC (11111100)
  END=1, LOOP=1, FILTER=3, SHIFT=12

Data: 16 nibbles with shift 12 and heavy filter
```

### Example 2: Standard Block (No Filter, Shift 8)

```
Header: $08 (00001000)
  END=0, LOOP=0, FILTER=0, SHIFT=8

Data: 16 nibbles, each shifted left by 8
```

## 7.7 Loop Handling

### Non-Looping Sample

```
Block 0: END=0, LOOP=0
Block 1: END=0, LOOP=0
...
Block N: END=1, LOOP=0  (terminates)
```

### Looping Sample

```
Block 0: END=0, LOOP=1
Block 1: END=0, LOOP=1
...
Block N: END=1, LOOP=1  (jumps to loop address)
```

## 7.8 BRR Decoding Algorithm

```
function decode_brr_block(header, data[8], old, older):
    shift = header & 0x0F
    filter = (header >> 4) & 0x03
    
    for i = 0 to 15:
        // Extract nibble
        if i is even:
            nibble = (data[i/2] >> 4) & 0x0F
        else:
            nibble = data[i/2] & 0x0F
        
        // Sign extend nibble
        if nibble & 0x08:
            nibble = nibble - 16
        
        // Apply shift
        sample = nibble << shift
        
        // Apply filter
        if filter == 1:
            sample = sample + old
        else if filter == 2:
            sample = sample + (old * 2) - older
        else if filter == 3:
            sample = sample + (old * 2) - (older * 2)
        
        // Clamp to 16-bit
        sample = clamp(sample, -32768, 32767)
        
        // Update history
        older = old
        old = sample
        
        output[i] = sample
    
    return output, old, older
```

## 7.9 BRR Compression Ratio

| Format | Bytes per Sample | Ratio |
|--------|------------------|-------|
| Raw 16-bit | 2.0 | 1:1 |
| Raw 8-bit | 1.0 | 2:1 |
| BRR | 0.5625 | ~3.5:1 |

BRR stores 16 samples in 9 bytes = 0.5625 bytes/sample

---

# 8. Communication Protocol

## 8.1 Overview

The SPC700 communicates with the main SNES CPU (5A22) through:
- Four 8-bit communication ports ($2140-$2143 on SNES side)
- Boot ROM transfer protocol
- Interrupts (optional)

## 8.2 Communication Ports

### SNES Side (CPU)

| Address | Register | Description |
|---------|----------|-------------|
| $2140 | APUIO0 | Communication port 0 |
| $2141 | APUIO1 | Communication port 1 |
| $2142 | APUIO2 | Communication port 2 |
| $2143 | APUIO3 | Communication port 3 |

### SPC700 Side

| Address | Register | Description |
|---------|----------|-------------|
| $F4 | CPUIO0 | Communication port 0 |
| $F5 | CPUIO1 | Communication port 1 |
| $F6 | CPUIO2 | Communication port 2 |
| $F7 | CPUIO3 | Communication port 3 |

## 8.3 Port Mapping

```
SNES $2140 <-> SPC700 $F4 (CPUIO0)
SNES $2141 <-> SPC700 $F5 (CPUIO1)
SNES $2142 <-> SPC700 $F6 (CPUIO2)
SNES $2143 <-> SPC700 $F7 (CPUIO3)
```

## 8.4 Basic Transfer Protocol

### Handshake Transfer

```
; SNES sends data to SPC700

; 1. SNES writes data
  LDA #$XX
  STA $2140

; 2. SNES waits for acknowledgment
wait:
  LDA $2140
  CMP #$XX
  BNE wait

; 3. SPC700 reads and acknowledges
  MOV A,$F4    ; Read data
  MOV $F4,A    ; Echo back as ACK
```

## 8.5 Boot ROM Transfer Protocol

During reset, the SPC700 executes the IPL ROM which implements a data transfer protocol:

### Transfer Sequence

```
1. SNES writes $AA to $2141 (start transfer)
2. SNES writes $BB to $2142 (confirm)
3. SPC700 acknowledges
4. SNES sends: Destination address (2 bytes)
5. SNES sends: Data length (2 bytes)
6. SNES sends: Data bytes
7. SPC700 writes to ARAM
8. Repeat until complete
```

### Boot ROM Entry Points

| Address | Function |
|---------|----------|
| $FFC0 | IPL ROM start |
| $FFC9 | Transfer data to ARAM |

## 8.6 Typical Initialization Sequence

```
; 1. Reset SPC700
  LDA #$80
  STA $2140    ; Reset

; 2. Wait for SPC700 ready
  LDA #$AA
wait1:
  CMP $2140
  BNE wait1

; 3. Transfer program
  ; ... transfer code ...

; 4. Start SPC700 program
  LDA #$00
  STA $2140    ; Release reset
```

---

# 9. Timing and Performance

## 9.1 Clock Timing

| Component | Clock Speed |
|-----------|-------------|
| SPC700 | 1.024 MHz |
| S-DSP | 1.024 MHz |
| Sample Rate | 32 kHz |
| CPU Cycles per Sample | 32 |

## 9.2 Instruction Timing

| Category | Cycles |
|----------|--------|
| Fastest instructions | 2 cycles |
| Average instruction | 3-4 cycles |
| Slowest instructions | 12 cycles (DIV) |

## 9.3 Voice Processing Budget

With 32 cycles per sample at 32 kHz:
- 8 voices must be processed in 32 cycles
- Approximately 4 cycles per voice
- Heavy processing requires careful optimization

---

# 10. Reference Tables

## 10.1 SPC700 Opcode Quick Reference

### By Category

| Category | Opcodes |
|----------|---------|
| Data Transfer | MOV, MOVW, PUSH, POP |
| Arithmetic | ADC, SBC, CMP, INC, DEC |
| Logical | AND, OR, EOR |
| Shift/Rotate | ASL, LSR, ROL, ROR, XCN |
| Bit Manipulation | SET1, CLR1, NOT1, MOV1, AND1, OR1, EOR1, TSET1, TCLR1 |
| Branch | BRA, BEQ, BNE, BCS, BCC, BMI, BPL, BVS, BVC, BBS, BBC |
| Jump/Call | JMP, CALL, PCALL, TCALL, RET, RETI, BRK |
| Multiply/Divide | MUL, DIV |
| Decimal | DAA, DAS |
| Control | SLEEP, STOP, NOP |

## 10.2 DSP Register Quick Reference

| Address | Name | Function |
|---------|------|----------|
| $x0 | VOL(R) | Voice volume right |
| $x1 | VOL(L) | Voice volume left |
| $x2 | PITCH(L) | Pitch low byte |
| $x3 | PITCH(H) | Pitch high byte |
| $x4 | SRCN | Sample number |
| $x5 | ADSR1 | ADSR configuration |
| $x6 | ADSR2 | ADSR configuration |
| $x7 | GAIN | GAIN envelope |
| $x8 | ENVX | Envelope value (read) |
| $x9 | OUTX | Output value (read) |
| $4C | KON | Key on |
| $5C | KOF | Key off |
| $6C | FLG | Flags |
| $7C | ENDX | End block status |
| $5D | DIR | Sample directory |
| $6D | ESA | Echo start |
| $7D | EDL | Echo delay |
| $0D | EFB | Echo feedback |
| $2D | PMON | Pitch modulation |
| $3D | NON | Noise enable |
| $4D | EON | Echo enable |
| $0F-$7F | COEF0-7 | FIR coefficients |

---

# Appendix A: SPC700 Instruction Set Summary

## Complete Opcode Map (Hexadecimal Order)

```
$00: NOP          $40: SETP         $80: SETC         $C0: DI
$01: TCALL 0      $41: TCALL 4      $81: TCALL 8      $C1: TCALL 12
$02: SET1 nn.0    $42: SET1 nn.2    $82: SET1 nn.4    $C2: SET1 nn.6
$03: BBS0 nn,nn   $43: BBS2 nn,nn   $83: BBS4 nn,nn   $C3: BBS6 nn,nn
$04: OR A,nn      $44: EOR A,nn     $84: ADC A,nn     $C4: MOV nn,A
$05: OR A,nnnn    $45: EOR A,nnnn   $85: ADC A,nnnn   $C5: MOV nnnn,A
$06: OR A,(X)     $46: EOR A,(X)    $86: ADC A,(X)    $C6: MOV (X),A
$07: OR A,[nn+X]  $47: EOR A,[nn+X] $87: ADC A,[nn+X] $C7: MOV [nn+X],A
$08: OR A,#nn     $48: EOR A,#nn    $88: ADC A,#nn    $C8: CMP X,#nn
$09: OR nn,nn     $49: EOR nn,nn    $89: ADC nn,nn    $C9: MOV nnnn,X
$0A: OR1 C,nn.nn  $4A: AND1 C,nn.nn $8A: EOR1 C,nn.nn $CA: MOV1 nn.nn,C
$0B: ASL nn       $4B: LSR nn       $8B: DEC nn       $CB: MOV nn,Y
$0C: ASL nnnn     $4C: LSR nnnn     $8C: DEC nnnn     $CC: MOV nnnn,Y
$0D: PUSH PSW     $4D: PUSH X       $8D: MOV Y,#nn    $CD: MOV X,#nn
$0E: TSET1 nnnn   $4E: TCLR1 nnnn   $8E: POP PSW      $CE: POP X
$0F: BRK          $4F: PCALL nn     $8F: MOV nn,#nn   $CF: MUL YA

$10: BPL nn       $50: BVC nn       $90: BCC nn       $D0: BNE nn
$11: TCALL 1      $51: TCALL 5      $91: TCALL 9      $D1: TCALL 13
$12: CLR1 nn.0    $52: CLR1 nn.2    $92: CLR1 nn.4    $D2: CLR1 nn.6
$13: BBC0 nn,nn   $53: BBC2 nn,nn   $93: BBC4 nn,nn   $D3: BBC6 nn,nn
$14: OR A,nn+X    $54: EOR A,nn+X   $94: ADC A,nn+X   $D4: MOV nn+X,A
$15: OR A,nnnn+X  $55: EOR A,nnnn+X $95: ADC A,nnnn+X $D5: MOV nnnn+X,A
$16: OR A,nnnn+Y  $56: EOR A,nnnn+Y $96: ADC A,nnnn+Y $D6: MOV nnnn+Y,A
$17: OR A,[nn]+Y  $57: EOR A,[nn]+Y $97: ADC A,[nn]+Y $D7: MOV [nn]+Y,A
$18: OR nn,#nn    $58: EOR nn,#nn   $98: ADC nn,#nn   $D8: MOV nn,X
$19: OR (X),(Y)   $59: EOR (X),(Y)  $99: ADC (X),(Y)  $D9: MOV nn+Y,X
$1A: DECW nn      $5A: CMPW YA,nn   $9A: SUBW YA,nn   $DA: MOVW nn,YA
$1B: ASL nn+X     $5B: LSR nn+X     $9B: DEC nn+X     $DB: MOV nn+X,Y
$1C: ASL A        $5C: LSR A        $9C: DEC A        $DC: DEC Y
$1D: DEC X        $5D: MOV X,A      $9D: MOV X,SP     $DD: MOV A,Y
$1E: CMP X,nnnn   $5E: CMP Y,nnnn   $9E: DIV YA,X     $DE: CBNE nn+X,nn
$1F: JMP [nnnn+X] $5F: JMP nnnn     $9F: XCN A        $DF: DAA

$20: CLRP         $60: CLRC         $A0: EI           $E0: CLRV
$21: TCALL 2      $61: TCALL 6      $A1: TCALL 10     $E1: TCALL 14
$22: SET1 nn.1    $62: SET1 nn.3    $A2: SET1 nn.5    $E2: SET1 nn.7
$23: BBS1 nn,nn   $63: BBS3 nn,nn   $A3: BBS5 nn,nn   $E3: BBS7 nn,nn
$24: AND A,nn     $64: CMP A,nn     $A4: SBC A,nn     $E4: MOV A,nn
$25: AND A,nnnn   $65: CMP A,nnnn   $A5: SBC A,nnnn   $E5: MOV A,nnnn
$26: AND A,(X)    $66: CMP A,(X)    $A6: SBC A,(X)    $E6: MOV A,(X)
$27: AND A,[nn+X] $67: CMP A,[nn+X] $A7: SBC A,[nn+X] $E7: MOV A,[nn+X]
$28: AND A,#nn    $68: CMP A,#nn    $A8: SBC A,#nn    $E8: MOV A,#nn
$29: AND nn,nn    $69: CMP nn,nn    $A9: SBC nn,nn    $E9: MOV X,nnnn
$2A: OR1 C,/nn.nn $6A: AND1 C,/nn.nn $AA: MOV1 C,nn.nn $EA: NOT1 nn.nn
$2B: ROL nn       $6B: ROR nn       $AB: INC nn       $EB: MOV Y,nn
$2C: ROL nnnn     $6C: ROR nnnn     $AC: INC nnnn     $EC: MOV Y,nnnn
$2D: PUSH A       $6D: PUSH Y       $AD: CMP Y,#nn    $ED: NOTC
$2E: CBNE nn,nn   $6E: DBNZ nn,nn   $AE: POP A        $EE: POP Y
$2F: BRA nn       $6F: RET          $AF: MOV (X)+,A   $EF: SLEEP

$30: BMI nn       $70: BVS nn       $B0: BCS nn       $F0: BEQ nn
$31: TCALL 3      $71: TCALL 7      $B1: TCALL 11     $F1: TCALL 15
$32: CLR1 nn.1    $72: CLR1 nn.3    $B2: CLR1 nn.5    $F2: CLR1 nn.7
$33: BBC1 nn,nn   $73: BBC3 nn,nn   $B3: BBC5 nn,nn   $F3: BBC7 nn,nn
$34: AND A,nn+X   $74: CMP A,nn+X   $B4: SBC A,nn+X   $F4: MOV A,nn+X
$35: AND A,nnnn+X $75: CMP A,nnnn+X $B5: SBC A,nnnn+X $F5: MOV A,nnnn+X
$36: AND A,nnnn+Y $76: CMP A,nnnn+Y $B6: SBC A,nnnn+Y $F6: MOV A,nnnn+Y
$37: AND A,[nn]+Y $77: CMP A,[nn]+Y $B7: SBC A,[nn]+Y $F7: MOV A,[nn]+Y
$38: AND nn,#nn   $78: CMP nn,#nn   $B8: SBC nn,#nn   $F8: MOV X,nn
$39: AND (X),(Y)  $79: CMP (X),(Y)  $B9: SBC (X),(Y)  $F9: MOV X,nn+Y
$3A: INCW nn      $7A: ADDW YA,nn   $BA: MOVW YA,nn   $FA: MOV nn,#nn
$3B: ROL nn+X     $7B: ROR nn+X     $BB: INC nn+X     $FB: MOV Y,nn+X
$3C: ROL A        $7C: ROR A        $BC: INC A        $FC: INC Y
$3D: INC X        $7D: MOV A,X      $BD: MOV SP,X     $FD: MOV Y,A
$3E: CMP X,nn     $7E: CMP Y,nn     $BE: DAS          $FE: DBNZ Y,nn
$3F: CALL nnnn    $7F: RETI         $BF: MOV A,(X)+   $FF: STOP
```

---

*Document Version: 1.0*
*Last Updated: SNES Audio Subsystem Technical Reference*
