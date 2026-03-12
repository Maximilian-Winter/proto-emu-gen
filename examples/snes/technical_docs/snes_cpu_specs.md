# SNES Ricoh 5A22 CPU Technical Specifications

## Based on WDC 65C816 16-bit Microprocessor

---

# 1. CPU OVERVIEW

## 1.1 Core Architecture

The Ricoh 5A22 is a custom 16-bit microprocessor based on the Western Design Center (WDC) 65C816. It serves as the main CPU for the Super Nintendo Entertainment System (SNES).

| Specification | Details |
|--------------|---------|
| **Base Architecture** | WDC 65C816 (CMOS) |
| **Data Bus** | 8-bit |
| **Address Bus** | 24-bit (16 MB addressable) |
| **Internal Registers** | 16-bit |
| **Instruction Set** | 65C02 superset with 16-bit extensions |
| **Package** | 100-pin QFP |

## 1.2 Clock Speeds and Timing

The 5A22 uses a complex clocking scheme with multiple clock domains:

| Clock Signal | Frequency | Purpose |
|-------------|-----------|---------|
| **Master Clock** | 21.477272 MHz (NTSC) / 21.281370 MHz (PAL) | Input oscillator |
| **CPU Clock** | 2.68 MHz / 3.58 MHz | Internal CPU operations |
| **Bus Clock** | 2.68 MHz / 3.58 MHz | Memory access cycles |
| **Access Speed** | Slow (6 cycles) / Fast (4 cycles) / X-Slow (8 cycles) | Memory region dependent |

### Clock Calculation (NTSC):
- Master Clock: 21.477272 MHz = 6 × NTSC colorburst (3.579545 MHz)
- CPU Clock: Master ÷ 6 = 3.579545 MHz (fast access)
- CPU Clock: Master ÷ 8 = 2.684659 MHz (slow access)

### Memory Access Timing:
| Access Type | Cycles | When Used |
|------------|--------|-----------|
| **Fast** | 4 cycles | Banks $80-$BF:$8000-$FFFF (FastROM) |
| **Slow** | 6 cycles | Banks $00-$3F:$8000-$FFFF, $40-$7F |
| **X-Slow** | 8 cycles | Register accesses, WRAM |

## 1.3 Operating Modes

The 65C816 has two primary operating modes controlled by the **E** (Emulation) flag:

### Emulation Mode (E = 1)
- **Compatibility**: Full backward compatibility with 6502/65C02
- **Register Size**: A, X, Y limited to 8-bit
- **Stack**: Fixed at $0100-$01FF (page 1)
- **Interrupt Vectors**: Located at $FFxx (same as 6502)
- **Reset State**: CPU starts in Emulation mode

### Native Mode (E = 0)
- **Full 16-bit**: All registers can operate in 16-bit mode
- **Variable Stack**: Stack pointer can address any page
- **Extended Vectors**: Native mode vectors at $FExx
- **Bank Addressing**: Full 24-bit address space accessible

### Mode Transition:
```
XCE (eXchange Carry with Emulation) - Only way to toggle E flag
    - If C=0: Enter Native mode (E=0)
    - If C=1: Enter Emulation mode (E=1)
```

---

# 2. REGISTER SET

## 2.1 Primary Registers

### Accumulator (A) - 8/16-bit
| Attribute | Description |
|-----------|-------------|
| **Size** | 8-bit (M=1) or 16-bit (M=0) |
| **Purpose** | Primary arithmetic/logic register |
| **High Byte** | B register (accessible via XBA) |

```
16-bit mode (M=0):  |  B  |  A  |
                    | AH  |  AL |
                    15----8-7----0

8-bit mode (M=1):   |  B  |  A  |
                    |hidden| AL |
                    15----8-7----0
```

### Index Register X - 8/16-bit
| Attribute | Description |
|-----------|-------------|
| **Size** | 8-bit (X=1) or 16-bit (X=0) |
| **Purpose** | Index addressing, counter |

```
16-bit mode (X=0):  |  XH  |  XL  |
                    15-----8-7-----0

8-bit mode (X=1):   |  00  |  XL  |
                    15-----8-7-----0
```

### Index Register Y - 8/16-bit
| Attribute | Description |
|-----------|-------------|
| **Size** | 8-bit (X=1) or 16-bit (X=0) |
| **Purpose** | Index addressing, counter |

```
16-bit mode (X=0):  |  YH  |  YL  |
                    15-----8-7-----0

8-bit mode (X=1):   |  00  |  YL  |
                    15-----8-7-----0
```

### Stack Pointer (S/SP)
| Attribute | Description |
|-----------|-------------|
| **Size** | 16-bit always |
| **Emulation Mode** | High byte forced to $01 |
| **Native Mode** | Full 16-bit addressing |

```
Emulation mode:     |  01  |  S   |
                    15-----8-7-----0

Native mode:        |  SH  |  SL  |
                    15-----8-7-----0
```

### Program Counter (PC)
| Attribute | Description |
|-----------|-------------|
| **Size** | 16-bit (within current bank) |
| **Range** | $0000-$FFFF within bank |

```
Program Counter:    |  PCH |  PCL |
                    15-----8-7-----0
```

## 2.2 Bank Registers

### Program Bank Register (PB/K)
| Attribute | Description |
|-----------|-------------|
| **Size** | 8-bit |
| **Symbol** | K (in documentation), PB (in practice) |
| **Purpose** | Holds bank for instruction fetches |
| **Range** | $00-$FF |

```
Full PC:  |  PB  |  PC  |
          23-----16-15----0
```

### Data Bank Register (DB/B)
| Attribute | Description |
|-----------|-------------|
| **Size** | 8-bit |
| **Symbol** | B (in documentation), DB (in practice) |
| **Purpose** | Default bank for data accesses |
| **Range** | $00-$FF |

## 2.3 Direct Page Register (D)
| Attribute | Description |
|-----------|-------------|
| **Size** | 16-bit |
| **Purpose** | Base address for Direct Page addressing |
| **Default** | $0000 |

Direct Page addressing: Effective Address = D + offset

## 2.4 Processor Status Register (P)

| Bit | Flag | Name | Description |
|-----|------|------|-------------|
| 7 | **N** | Negative | Set if result MSB = 1 |
| 6 | **V** | Overflow | Set if signed overflow occurred |
| 5 | **M** | Memory/Accumulator | 0=16-bit A, 1=8-bit A (Native only) |
| 4 | **X** | Index | 0=16-bit X,Y, 1=8-bit X,Y (Native only) |
| 3 | **D** | Decimal | 0=Binary mode, 1=Decimal mode |
| 2 | **I** | Interrupt Disable | 0=IRQ enabled, 1=IRQ disabled |
| 1 | **Z** | Zero | Set if result = 0 |
| 0 | **C** | Carry | Carry/borrow from arithmetic |

### Status Register Layout:
```
Bit:    7   6   5   4   3   2   1   0
       +---+---+---+---+---+---+---+---+
       | N | V | M | X | D | I | Z | C |
       +---+---+---+---+---+---+---+---+
```

### Special Notes:
- **M and X flags**: Ignored in Emulation mode (treated as set)
- **E flag (Emulation)**: Not directly visible in P register, swapped with C via XCE
- **B flag (Break)**: Only exists in Emulation mode, bit 4 of stack P after BRK

---

# 3. COMPLETE OPCODE TABLE

## Legend:
- **A**: Accumulator
- **X**: X index register
- **Y**: Y index register
- **S**: Stack pointer
- **D**: Direct page register
- **B**: Data bank register
- **K**: Program bank register
- **#**: Immediate value
- **addr**: 16-bit address
- **long**: 24-bit address
- **dp**: 8-bit direct page offset
- **sr**: 8-bit stack relative offset
- **label**: Relative branch target
- **M**: Memory/Accumulator flag
- **X**: Index register flag

## 3.1 LOAD/STORE INSTRUCTIONS

### LDA - Load Accumulator
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| A9 | LDA #const | Immediate | 2* | 2 | N, Z |
| AD | LDA addr | Absolute | 3 | 4 | N, Z |
| AF | LDA long | Absolute Long | 4 | 5 | N, Z |
| A5 | LDA dp | Direct Page | 2 | 3** | N, Z |
| B2 | LDA (dp) | DP Indirect | 2 | 5** | N, Z |
| A7 | LDA [dp] | DP Indirect Long | 2 | 6** | N, Z |
| B5 | LDA dp,X | DP Indexed X | 2 | 4** | N, Z |
| BD | LDA addr,X | Absolute Indexed X | 3 | 4* | N, Z |
| BF | LDA long,X | Abs Long Idx X | 4 | 5* | N, Z |
| B9 | LDA addr,Y | Absolute Indexed Y | 3 | 4* | N, Z |
| A1 | LDA (dp,X) | DP Indexed Indirect | 2 | 6** | N, Z |
| B1 | LDA (dp),Y | DP Indirect Indexed | 2 | 5** | N, Z |
| A3 | LDA sr,S | Stack Relative | 2 | 4 | N, Z |
| B7 | LDA [dp],Y | DP Ind Long Idx Y | 2 | 6** | N, Z |
| B3 | LDA (sr,S),Y | SR Indirect Idx Y | 2 | 7 | N, Z |

*Add 1 cycle if M=0 (16-bit)
**Add 1 cycle if D low byte != 0
*Add 1 cycle if page boundary crossed (X=1, 8-bit index)

### LDX - Load X Register
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| A2 | LDX #const | Immediate | 2* | 2 | N, Z |
| AE | LDX addr | Absolute | 3 | 4 | N, Z |
| A6 | LDX dp | Direct Page | 2 | 3** | N, Z |
| BE | LDX addr,Y | Absolute Indexed Y | 3 | 4* | N, Z |
| B6 | LDX dp,Y | DP Indexed Y | 2 | 4** | N, Z |

*Add 1 cycle if X=0 (16-bit)
**Add 1 cycle if D low byte != 0

### LDY - Load Y Register
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| A0 | LDY #const | Immediate | 2* | 2 | N, Z |
| AC | LDY addr | Absolute | 3 | 4 | N, Z |
| A4 | LDY dp | Direct Page | 2 | 3** | N, Z |
| BC | LDY addr,X | Absolute Indexed X | 3 | 4* | N, Z |
| B4 | LDY dp,X | DP Indexed X | 2 | 4** | N, Z |

*Add 1 cycle if X=0 (16-bit)
**Add 1 cycle if D low byte != 0

### STA - Store Accumulator
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 8D | STA addr | Absolute | 3 | 4 | None |
| 8F | STA long | Absolute Long | 4 | 5 | None |
| 85 | STA dp | Direct Page | 2 | 3** | None |
| 92 | STA (dp) | DP Indirect | 2 | 5** | None |
| 87 | STA [dp] | DP Indirect Long | 2 | 6** | None |
| 95 | STA dp,X | DP Indexed X | 2 | 4** | None |
| 9D | STA addr,X | Absolute Indexed X | 3 | 5 | None |
| 9F | STA long,X | Abs Long Idx X | 4 | 6 | None |
| 99 | STA addr,Y | Absolute Indexed Y | 3 | 5 | None |
| 81 | STA (dp,X) | DP Indexed Indirect | 2 | 6** | None |
| 91 | STA (dp),Y | DP Indirect Indexed | 2 | 6** | None |
| 83 | STA sr,S | Stack Relative | 2 | 4 | None |
| 97 | STA [dp],Y | DP Ind Long Idx Y | 2 | 6** | None |
| 93 | STA (sr,S),Y | SR Indirect Idx Y | 2 | 7 | None |

**Add 1 cycle if D low byte != 0

### STX - Store X Register
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 8E | STX addr | Absolute | 3 | 4 | None |
| 86 | STX dp | Direct Page | 2 | 3** | None |
| 96 | STX dp,Y | DP Indexed Y | 2 | 4** | None |

**Add 1 cycle if D low byte != 0

### STY - Store Y Register
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 8C | STY addr | Absolute | 3 | 4 | None |
| 84 | STY dp | Direct Page | 2 | 3** | None |
| 94 | STY dp,X | DP Indexed X | 2 | 4** | None |

**Add 1 cycle if D low byte != 0

### STZ - Store Zero
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 9C | STZ addr | Absolute | 3 | 4 | None |
| 64 | STZ dp | Direct Page | 2 | 3** | None |
| 74 | STZ dp,X | DP Indexed X | 2 | 4** | None |
| 9E | STZ addr,X | Absolute Indexed X | 3 | 5 | None |

**Add 1 cycle if D low byte != 0

## 3.2 BLOCK MOVE INSTRUCTIONS

### MVN - Block Move Next
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 54 | MVN src,dest | Block Move | 3 | 7* | None |

- Moves bytes from (src,X) to (dest,Y)
- Increments X, Y; decrements A
- Repeats until A = $FFFF
- *Cycles: 7 per byte moved

### MVP - Block Move Previous
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 44 | MVP src,dest | Block Move | 3 | 7* | None |

- Moves bytes from (src,X) to (dest,Y)
- Decrements X, Y, A
- Repeats until A = $FFFF
- *Cycles: 7 per byte moved

## 3.3 ARITHMETIC INSTRUCTIONS

### ADC - Add with Carry
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 69 | ADC #const | Immediate | 2* | 2 | N, V, Z, C |
| 6D | ADC addr | Absolute | 3 | 4 | N, V, Z, C |
| 6F | ADC long | Absolute Long | 4 | 5 | N, V, Z, C |
| 65 | ADC dp | Direct Page | 2 | 3** | N, V, Z, C |
| 72 | ADC (dp) | DP Indirect | 2 | 5** | N, V, Z, C |
| 67 | ADC [dp] | DP Indirect Long | 2 | 6** | N, V, Z, C |
| 75 | ADC dp,X | DP Indexed X | 2 | 4** | N, V, Z, C |
| 7D | ADC addr,X | Absolute Indexed X | 3 | 4* | N, V, Z, C |
| 7F | ADC long,X | Abs Long Idx X | 4 | 5* | N, V, Z, C |
| 79 | ADC addr,Y | Absolute Indexed Y | 3 | 4* | N, V, Z, C |
| 61 | ADC (dp,X) | DP Indexed Indirect | 2 | 6** | N, V, Z, C |
| 71 | ADC (dp),Y | DP Indirect Indexed | 2 | 5** | N, V, Z, C |
| 63 | ADC sr,S | Stack Relative | 2 | 4 | N, V, Z, C |
| 77 | ADC [dp],Y | DP Ind Long Idx Y | 2 | 6** | N, V, Z, C |
| 73 | ADC (sr,S),Y | SR Indirect Idx Y | 2 | 7 | N, V, Z, C |

*Add 1 cycle if M=0 (16-bit)
**Add 1 cycle if D low byte != 0

### SBC - Subtract with Carry
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| E9 | SBC #const | Immediate | 2* | 2 | N, V, Z, C |
| ED | SBC addr | Absolute | 3 | 4 | N, V, Z, C |
| EF | SBC long | Absolute Long | 4 | 5 | N, V, Z, C |
| E5 | SBC dp | Direct Page | 2 | 3** | N, V, Z, C |
| F2 | SBC (dp) | DP Indirect | 2 | 5** | N, V, Z, C |
| E7 | SBC [dp] | DP Indirect Long | 2 | 6** | N, V, Z, C |
| F5 | SBC dp,X | DP Indexed X | 2 | 4** | N, V, Z, C |
| FD | SBC addr,X | Absolute Indexed X | 3 | 4* | N, V, Z, C |
| FF | SBC long,X | Abs Long Idx X | 4 | 5* | N, V, Z, C |
| F9 | SBC addr,Y | Absolute Indexed Y | 3 | 4* | N, V, Z, C |
| E1 | SBC (dp,X) | DP Indexed Indirect | 2 | 6** | N, V, Z, C |
| F1 | SBC (dp),Y | DP Indirect Indexed | 2 | 5** | N, V, Z, C |
| E3 | SBC sr,S | Stack Relative | 2 | 4 | N, V, Z, C |
| F7 | SBC [dp],Y | DP Ind Long Idx Y | 2 | 6** | N, V, Z, C |
| F3 | SBC (sr,S),Y | SR Indirect Idx Y | 2 | 7 | N, V, Z, C |

*Add 1 cycle if M=0 (16-bit)
**Add 1 cycle if D low byte != 0

### CMP - Compare Accumulator
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| C9 | CMP #const | Immediate | 2* | 2 | N, Z, C |
| CD | CMP addr | Absolute | 3 | 4 | N, Z, C |
| CF | CMP long | Absolute Long | 4 | 5 | N, Z, C |
| C5 | CMP dp | Direct Page | 2 | 3** | N, Z, C |
| D2 | CMP (dp) | DP Indirect | 2 | 5** | N, Z, C |
| C7 | CMP [dp] | DP Indirect Long | 2 | 6** | N, Z, C |
| D5 | CMP dp,X | DP Indexed X | 2 | 4** | N, Z, C |
| DD | CMP addr,X | Absolute Indexed X | 3 | 4* | N, Z, C |
| DF | CMP long,X | Abs Long Idx X | 4 | 5* | N, Z, C |
| D9 | CMP addr,Y | Absolute Indexed Y | 3 | 4* | N, Z, C |
| C1 | CMP (dp,X) | DP Indexed Indirect | 2 | 6** | N, Z, C |
| D1 | CMP (dp),Y | DP Indirect Indexed | 2 | 5** | N, Z, C |
| C3 | CMP sr,S | Stack Relative | 2 | 4 | N, Z, C |
| D7 | CMP [dp],Y | DP Ind Long Idx Y | 2 | 6** | N, Z, C |
| D3 | CMP (sr,S),Y | SR Indirect Idx Y | 2 | 7 | N, Z, C |

*Add 1 cycle if M=0 (16-bit)
**Add 1 cycle if D low byte != 0

### CPX - Compare X Register
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| E0 | CPX #const | Immediate | 2* | 2 | N, Z, C |
| EC | CPX addr | Absolute | 3 | 4 | N, Z, C |
| E4 | CPX dp | Direct Page | 2 | 3** | N, Z, C |

*Add 1 cycle if X=0 (16-bit)
**Add 1 cycle if D low byte != 0

### CPY - Compare Y Register
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| C0 | CPY #const | Immediate | 2* | 2 | N, Z, C |
| CC | CPY addr | Absolute | 3 | 4 | N, Z, C |
| C4 | CPY dp | Direct Page | 2 | 3** | N, Z, C |

*Add 1 cycle if X=0 (16-bit)
**Add 1 cycle if D low byte != 0

### DEC - Decrement
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 3A | DEC A | Accumulator | 1 | 2 | N, Z |
| CE | DEC addr | Absolute | 3 | 6** | N, Z |
| C6 | DEC dp | Direct Page | 2 | 5*** | N, Z |
| D6 | DEC dp,X | DP Indexed X | 2 | 6*** | N, Z |
| DE | DEC addr,X | Absolute Indexed X | 3 | 7** | N, Z |

**Add 2 cycles if M=0 (16-bit)
***Add 1 cycle if D low byte != 0, add 2 if M=0

### DEX - Decrement X
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| CA | DEX | Implied | 1 | 2 | N, Z |

### DEY - Decrement Y
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 88 | DEY | Implied | 1 | 2 | N, Z |

### INC - Increment
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 1A | INC A | Accumulator | 1 | 2 | N, Z |
| EE | INC addr | Absolute | 3 | 6** | N, Z |
| E6 | INC dp | Direct Page | 2 | 5*** | N, Z |
| F6 | INC dp,X | DP Indexed X | 2 | 6*** | N, Z |
| FE | INC addr,X | Absolute Indexed X | 3 | 7** | N, Z |

**Add 2 cycles if M=0 (16-bit)
***Add 1 cycle if D low byte != 0, add 2 if M=0

### INX - Increment X
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| E8 | INX | Implied | 1 | 2 | N, Z |

### INY - Increment Y
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| C8 | INY | Implied | 1 | 2 | N, Z |

## 3.4 LOGICAL INSTRUCTIONS

### AND - Logical AND
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 29 | AND #const | Immediate | 2* | 2 | N, Z |
| 2D | AND addr | Absolute | 3 | 4 | N, Z |
| 2F | AND long | Absolute Long | 4 | 5 | N, Z |
| 25 | AND dp | Direct Page | 2 | 3** | N, Z |
| 32 | AND (dp) | DP Indirect | 2 | 5** | N, Z |
| 27 | AND [dp] | DP Indirect Long | 2 | 6** | N, Z |
| 35 | AND dp,X | DP Indexed X | 2 | 4** | N, Z |
| 3D | AND addr,X | Absolute Indexed X | 3 | 4* | N, Z |
| 3F | AND long,X | Abs Long Idx X | 4 | 5* | N, Z |
| 39 | AND addr,Y | Absolute Indexed Y | 3 | 4* | N, Z |
| 21 | AND (dp,X) | DP Indexed Indirect | 2 | 6** | N, Z |
| 31 | AND (dp),Y | DP Indirect Indexed | 2 | 5** | N, Z |
| 23 | AND sr,S | Stack Relative | 2 | 4 | N, Z |
| 37 | AND [dp],Y | DP Ind Long Idx Y | 2 | 6** | N, Z |
| 33 | AND (sr,S),Y | SR Indirect Idx Y | 2 | 7 | N, Z |

*Add 1 cycle if M=0 (16-bit)
**Add 1 cycle if D low byte != 0

### EOR - Exclusive OR
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 49 | EOR #const | Immediate | 2* | 2 | N, Z |
| 4D | EOR addr | Absolute | 3 | 4 | N, Z |
| 4F | EOR long | Absolute Long | 4 | 5 | N, Z |
| 45 | EOR dp | Direct Page | 2 | 3** | N, Z |
| 52 | EOR (dp) | DP Indirect | 2 | 5** | N, Z |
| 47 | EOR [dp] | DP Indirect Long | 2 | 6** | N, Z |
| 55 | EOR dp,X | DP Indexed X | 2 | 4** | N, Z |
| 5D | EOR addr,X | Absolute Indexed X | 3 | 4* | N, Z |
| 5F | EOR long,X | Abs Long Idx X | 4 | 5* | N, Z |
| 59 | EOR addr,Y | Absolute Indexed Y | 3 | 4* | N, Z |
| 41 | EOR (dp,X) | DP Indexed Indirect | 2 | 6** | N, Z |
| 51 | EOR (dp),Y | DP Indirect Indexed | 2 | 5** | N, Z |
| 43 | EOR sr,S | Stack Relative | 2 | 4 | N, Z |
| 57 | EOR [dp],Y | DP Ind Long Idx Y | 2 | 6** | N, Z |
| 53 | EOR (sr,S),Y | SR Indirect Idx Y | 2 | 7 | N, Z |

*Add 1 cycle if M=0 (16-bit)
**Add 1 cycle if D low byte != 0

### ORA - Logical OR
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 09 | ORA #const | Immediate | 2* | 2 | N, Z |
| 0D | ORA addr | Absolute | 3 | 4 | N, Z |
| 0F | ORA long | Absolute Long | 4 | 5 | N, Z |
| 05 | ORA dp | Direct Page | 2 | 3** | N, Z |
| 12 | ORA (dp) | DP Indirect | 2 | 5** | N, Z |
| 07 | ORA [dp] | DP Indirect Long | 2 | 6** | N, Z |
| 15 | ORA dp,X | DP Indexed X | 2 | 4** | N, Z |
| 1D | ORA addr,X | Absolute Indexed X | 3 | 4* | N, Z |
| 1F | ORA long,X | Abs Long Idx X | 4 | 5* | N, Z |
| 19 | ORA addr,Y | Absolute Indexed Y | 3 | 4* | N, Z |
| 01 | ORA (dp,X) | DP Indexed Indirect | 2 | 6** | N, Z |
| 11 | ORA (dp),Y | DP Indirect Indexed | 2 | 5** | N, Z |
| 03 | ORA sr,S | Stack Relative | 2 | 4 | N, Z |
| 17 | ORA [dp],Y | DP Ind Long Idx Y | 2 | 6** | N, Z |
| 13 | ORA (sr,S),Y | SR Indirect Idx Y | 2 | 7 | N, Z |

*Add 1 cycle if M=0 (16-bit)
**Add 1 cycle if D low byte != 0

### BIT - Bit Test
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 89 | BIT #const | Immediate | 2* | 2 | Z (M=1: N,V unchanged) |
| 2C | BIT addr | Absolute | 3 | 4 | N, V, Z |
| 24 | BIT dp | Direct Page | 2 | 3** | N, V, Z |
| 34 | BIT dp,X | DP Indexed X | 2 | 4** | N, V, Z |
| 3C | BIT addr,X | Absolute Indexed X | 3 | 4* | N, V, Z |

*Add 1 cycle if M=0 (16-bit), add 1 if page crossed (X=1)
**Add 1 cycle if D low byte != 0

Note: Immediate BIT only affects Z flag (and N,V if M=0 in 65C816)

## 3.5 SHIFT/ROTATE INSTRUCTIONS

### ASL - Arithmetic Shift Left
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 0A | ASL A | Accumulator | 1 | 2 | N, Z, C |
| 0E | ASL addr | Absolute | 3 | 6** | N, Z, C |
| 06 | ASL dp | Direct Page | 2 | 5*** | N, Z, C |
| 16 | ASL dp,X | DP Indexed X | 2 | 6*** | N, Z, C |
| 1E | ASL addr,X | Absolute Indexed X | 3 | 7** | N, Z, C |

**Add 2 cycles if M=0 (16-bit)
***Add 1 cycle if D low byte != 0, add 2 if M=0

### LSR - Logical Shift Right
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 4A | LSR A | Accumulator | 1 | 2 | N, Z, C |
| 4E | LSR addr | Absolute | 3 | 6** | N, Z, C |
| 46 | LSR dp | Direct Page | 2 | 5*** | N, Z, C |
| 56 | LSR dp,X | DP Indexed X | 2 | 6*** | N, Z, C |
| 5E | LSR addr,X | Absolute Indexed X | 3 | 7** | N, Z, C |

**Add 2 cycles if M=0 (16-bit)
***Add 1 cycle if D low byte != 0, add 2 if M=0

### ROL - Rotate Left
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 2A | ROL A | Accumulator | 1 | 2 | N, Z, C |
| 2E | ROL addr | Absolute | 3 | 6** | N, Z, C |
| 26 | ROL dp | Direct Page | 2 | 5*** | N, Z, C |
| 36 | ROL dp,X | DP Indexed X | 2 | 6*** | N, Z, C |
| 3E | ROL addr,X | Absolute Indexed X | 3 | 7** | N, Z, C |

**Add 2 cycles if M=0 (16-bit)
***Add 1 cycle if D low byte != 0, add 2 if M=0

### ROR - Rotate Right
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 6A | ROR A | Accumulator | 1 | 2 | N, Z, C |
| 6E | ROR addr | Absolute | 3 | 6** | N, Z, C |
| 66 | ROR dp | Direct Page | 2 | 5*** | N, Z, C |
| 76 | ROR dp,X | DP Indexed X | 2 | 6*** | N, Z, C |
| 7E | ROR addr,X | Absolute Indexed X | 3 | 7** | N, Z, C |

**Add 2 cycles if M=0 (16-bit)
***Add 1 cycle if D low byte != 0, add 2 if M=0

### TRB - Test and Reset Bits
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 1C | TRB addr | Absolute | 3 | 6** | Z |
| 14 | TRB dp | Direct Page | 2 | 5*** | Z |

**Add 2 cycles if M=0 (16-bit)
***Add 1 cycle if D low byte != 0, add 2 if M=0

### TSB - Test and Set Bits
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 0C | TSB addr | Absolute | 3 | 6** | Z |
| 04 | TSB dp | Direct Page | 2 | 5*** | Z |

**Add 2 cycles if M=0 (16-bit)
***Add 1 cycle if D low byte != 0, add 2 if M=0

## 3.6 BRANCH INSTRUCTIONS

### BCC - Branch if Carry Clear
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 90 | BCC label | Relative | 2 | 2* | None |

*Add 1 if branch taken, add 1 more if page boundary crossed

### BCS - Branch if Carry Set
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| B0 | BCS label | Relative | 2 | 2* | None |

*Add 1 if branch taken, add 1 more if page boundary crossed

### BEQ - Branch if Equal (Zero Set)
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| F0 | BEQ label | Relative | 2 | 2* | None |

*Add 1 if branch taken, add 1 more if page boundary crossed

### BMI - Branch if Minus (Negative Set)
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 30 | BMI label | Relative | 2 | 2* | None |

*Add 1 if branch taken, add 1 more if page boundary crossed

### BNE - Branch if Not Equal (Zero Clear)
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| D0 | BNE label | Relative | 2 | 2* | None |

*Add 1 if branch taken, add 1 more if page boundary crossed

### BPL - Branch if Plus (Negative Clear)
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 10 | BPL label | Relative | 2 | 2* | None |

*Add 1 if branch taken, add 1 more if page boundary crossed

### BRA - Branch Always
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 80 | BRA label | Relative | 2 | 3* | None |

*Add 1 if page boundary crossed

### BVC - Branch if Overflow Clear
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 50 | BVC label | Relative | 2 | 2* | None |

*Add 1 if branch taken, add 1 more if page boundary crossed

### BVS - Branch if Overflow Set
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 70 | BVS label | Relative | 2 | 2* | None |

*Add 1 if branch taken, add 1 more if page boundary crossed

### BRL - Branch Always Long
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 82 | BRL label | Relative Long | 3 | 4 | None |

- 16-bit signed offset allows branching anywhere in current bank

## 3.7 JUMP/SUBROUTINE INSTRUCTIONS

### JMP - Jump
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 4C | JMP addr | Absolute | 3 | 3 | None |
| 6C | JMP (addr) | Absolute Indirect | 3 | 5 | None |
| 7C | JMP (addr,X) | Abs Indexed Indirect | 3 | 6 | None |
| 5C | JMP long | Absolute Long | 4 | 4 | None |
| DC | JMP [addr] | Absolute Indirect Long | 3 | 6 | None |

### JSR - Jump to Subroutine
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 20 | JSR addr | Absolute | 3 | 6 | None |
| FC | JSR (addr,X) | Abs Indexed Indirect | 3 | 8 | None |
| 22 | JSR long | Absolute Long | 4 | 8 | None |

### RTL - Return from Subroutine Long
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 6B | RTL | Implied | 1 | 6 | None |

- Pulls 3 bytes: PC+3 (24-bit return address)

### RTS - Return from Subroutine
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 60 | RTS | Implied | 1 | 6 | None |

- Pulls 2 bytes: PC+2 (16-bit, same bank)

### RTI - Return from Interrupt
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 40 | RTI | Implied | 1 | 6* | ALL |

*Add 1 cycle in Native mode (pulls PB)
- Pulls P, then PC (and PB in Native mode)
- Restores all flags including M, X

## 3.8 INTERRUPT INSTRUCTIONS

### BRK - Break
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 00 | BRK #const | Stack/Interrupt | 2 | 7* | I=1, D=0 |

*8 cycles in Emulation mode
- Pushes PB (Native only), PC+2, P
- Sets I=1, D=0
- Jumps through vector:
  - Native: $FFE6-$FFE7
  - Emulation: $FFFE-$FFFF

### COP - Coprocessor
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 02 | COP #const | Stack/Interrupt | 2 | 7* | I=1, D=0 |

*8 cycles in Emulation mode
- Same as BRK but uses COP vectors:
  - Native: $FFE4-$FFE5
  - Emulation: $FFF4-$FFF5

## 3.9 FLAG MANIPULATION INSTRUCTIONS

### CLC - Clear Carry
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 18 | CLC | Implied | 1 | 2 | C=0 |

### CLD - Clear Decimal
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| D8 | CLD | Implied | 1 | 2 | D=0 |

### CLI - Clear Interrupt Disable
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 58 | CLI | Implied | 1 | 2 | I=0 |

### CLV - Clear Overflow
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| B8 | CLV | Implied | 1 | 2 | V=0 |

### SEC - Set Carry
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 38 | SEC | Implied | 1 | 2 | C=1 |

### SED - Set Decimal
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| F8 | SED | Implied | 1 | 2 | D=1 |

### SEI - Set Interrupt Disable
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 78 | SEI | Implied | 1 | 2 | I=1 |

### REP - Reset Processor Status Bits
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| C2 | REP #const | Immediate | 2 | 3 | Selected |

- Clears bits in P specified by mask
- Example: REP #$30 clears M and X (sets 16-bit mode)

### SEP - Set Processor Status Bits
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| E2 | SEP #const | Immediate | 2 | 3 | Selected |

- Sets bits in P specified by mask
- Example: SEP #$30 sets M and X (sets 8-bit mode)

## 3.10 TRANSFER INSTRUCTIONS

### TAX - Transfer A to X
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| AA | TAX | Implied | 1 | 2 | N, Z |

### TAY - Transfer A to Y
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| A8 | TAY | Implied | 1 | 2 | N, Z |

### TSX - Transfer S to X
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| BA | TSX | Implied | 1 | 2 | N, Z |

### TXA - Transfer X to A
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 8A | TXA | Implied | 1 | 2 | N, Z |

### TXS - Transfer X to S
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 9A | TXS | Implied | 1 | 2 | None |

### TXY - Transfer X to Y
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 9B | TXY | Implied | 1 | 2 | N, Z |

### TYA - Transfer Y to A
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 98 | TYA | Implied | 1 | 2 | N, Z |

### TYX - Transfer Y to X
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| BB | TYX | Implied | 1 | 2 | N, Z |

### TCD - Transfer A to D (16-bit)
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 5B | TCD | Implied | 1 | 2 | N, Z |

- Also known as TAD

### TCS - Transfer A to S (16-bit)
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 1B | TCS | Implied | 1 | 2 | None |

- Also known as TAS

### TDC - Transfer D to A (16-bit)
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 7B | TDC | Implied | 1 | 2 | N, Z |

- Also known as TDA

### TSC - Transfer S to A (16-bit)
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 3B | TSC | Implied | 1 | 2 | N, Z |

- Also known as TSA

### XBA - Exchange B and A Accumulators
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| EB | XBA | Implied | 1 | 3 | N, Z |

- Swaps high and low bytes of accumulator

### XCE - Exchange Carry with Emulation
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| FB | XCE | Implied | 1 | 2 | C, E, M, X |

- Only way to change E flag
- Exchanges C flag with E flag
- When entering Emulation: M and X forced to 1

## 3.11 STACK INSTRUCTIONS

### PHA - Push Accumulator
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 48 | PHA | Stack | 1 | 3* | None |

*Add 1 cycle if M=0 (16-bit)

### PHB - Push Data Bank Register
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 8B | PHB | Stack | 1 | 3 | None |

### PHD - Push Direct Page Register
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 0B | PHD | Stack | 1 | 4 | None |

### PHK - Push Program Bank Register
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 4B | PHK | Stack | 1 | 3 | None |

### PHP - Push Processor Status
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 08 | PHP | Stack | 1 | 3 | None |

### PHX - Push X Register
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| DA | PHX | Stack | 1 | 3* | None |

*Add 1 cycle if X=0 (16-bit)

### PHY - Push Y Register
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 5A | PHY | Stack | 1 | 3* | None |

*Add 1 cycle if X=0 (16-bit)

### PLA - Pull Accumulator
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 68 | PLA | Stack | 1 | 4* | N, Z |

*Add 1 cycle if M=0 (16-bit)

### PLB - Pull Data Bank Register
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| AB | PLB | Stack | 1 | 4 | N, Z |

### PLD - Pull Direct Page Register
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 2B | PLD | Stack | 1 | 5 | N, Z |

### PLP - Pull Processor Status
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 28 | PLP | Stack | 1 | 4 | ALL |

### PLX - Pull X Register
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| FA | PLX | Stack | 1 | 4* | N, Z |

*Add 1 cycle if X=0 (16-bit)

### PLY - Pull Y Register
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 7A | PLY | Stack | 1 | 4* | N, Z |

*Add 1 cycle if X=0 (16-bit)

### PEI - Push Effective Indirect Address
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| D4 | PEI dp | Direct Page Indirect | 2 | 6* | None |

*Add 1 cycle if D low byte != 0
- Pushes 16-bit address from DP indirect

### PER - Push Effective Relative Address
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 62 | PER label | Stack Relative | 3 | 6 | None |

- Pushes PC + 3 + signed 16-bit offset

## 3.12 CONTROL INSTRUCTIONS

### NOP - No Operation
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| EA | NOP | Implied | 1 | 2 | None |

### WDM - Reserved for Future Expansion
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| 42 | WDM #const | Immediate | 2 | 2* | ? |

*Originally reserved, used for NOP on 65C816

### WAI - Wait for Interrupt
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| CB | WAI | Implied | 1 | 3* | None |

*Halts CPU until interrupt occurs

### STP - Stop the Processor
| Opcode | Mnemonic | Addressing Mode | Bytes | Cycles | Flags |
|--------|----------|-----------------|-------|--------|-------|
| DB | STP | Implied | 1 | 3* | None |

*Halts CPU until RESET

---

# 4. ADDRESSING MODES

## 4.1 Immediate (#)

### 8-bit Immediate (M=1 or X=1)
- Operand is single byte following opcode
- Example: `LDA #$5A` loads $5A into accumulator

### 16-bit Immediate (M=0 or X=0)
- Operand is two bytes (low, high) following opcode
- Example: `LDA #$1234` loads $1234 into accumulator

```
Instruction Format:
  PC     PC+1   PC+2
+------+------+------+
| Op   | Low  | High |
+------+------+------+
```

## 4.2 Absolute (abs)

16-bit address within current data bank.

```
Effective Address = {DB, addr}

Instruction Format:
  PC     PC+1    PC+2
+------+-------+-------+
| Op   | AddrL | AddrH |
+------+-------+-------+
```

## 4.3 Absolute Indexed X (abs,X)

16-bit base address + X register, within current data bank.

```
Effective Address = {DB, addr + X}

Instruction Format:
  PC     PC+1    PC+2
+------+-------+-------+
| Op   | AddrL | AddrH |
+------+-------+-------+
```

## 4.4 Absolute Indexed Y (abs,Y)

16-bit base address + Y register, within current data bank.

```
Effective Address = {DB, addr + Y}
```

## 4.5 Absolute Long (long)

Full 24-bit address specified directly.

```
Effective Address = {Bank, addr}

Instruction Format:
  PC     PC+1    PC+2    PC+3
+------+-------+-------+-------+
| Op   | AddrL | AddrH | Bank  |
+------+-------+-------+-------+
```

## 4.6 Absolute Long Indexed X (long,X)

Full 24-bit base address + X register.

```
Effective Address = {Bank, addr + X}
```

## 4.7 Direct Page (dp)

8-bit offset from Direct Page register.

```
Effective Address = D + dp

Instruction Format:
  PC     PC+1
+------+------+
| Op   | Off  |
+------+------+
```

Note: If D low byte != 0, add 1 cycle for page boundary crossing.

## 4.8 Direct Page Indexed X (dp,X)

8-bit offset + X register, from Direct Page.

```
Effective Address = D + dp + X
```

## 4.9 Direct Page Indexed Y (dp,Y)

8-bit offset + Y register, from Direct Page.

```
Effective Address = D + dp + Y
```

## 4.10 Direct Page Indirect (dp)

Pointer at DP offset points to 16-bit address.

```
Pointer Address = D + dp
Effective Address = {DB, [Pointer Address]}

[Pointer Address] = 16-bit value at D+dp, D+dp+1
```

## 4.11 Direct Page Indirect Long [dp]

Pointer at DP offset points to 24-bit address.

```
Pointer Address = D + dp
Effective Address = [Pointer Address] (24-bit)
```

## 4.12 Direct Page Indexed Indirect (dp,X)

DP offset + X points to 16-bit indirect address.

```
Pointer Address = D + dp + X
Effective Address = {DB, [Pointer Address]}
```

## 4.13 Direct Page Indirect Indexed (dp),Y

Pointer at DP offset points to 16-bit base, then add Y.

```
Pointer Address = D + dp
Base Address = [Pointer Address]
Effective Address = {DB, Base Address + Y}
```

## 4.14 Direct Page Indirect Long Indexed [dp],Y

Pointer at DP offset points to 24-bit base, then add Y.

```
Pointer Address = D + dp
Base Address = [Pointer Address] (24-bit)
Effective Address = Base Address + Y
```

## 4.15 Stack Relative (sr,S)

8-bit offset from stack pointer.

```
Effective Address = S + sr

Instruction Format:
  PC     PC+1
+------+------+
| Op   | Off  |
+------+------+
```

## 4.16 Stack Relative Indirect Indexed (sr,S),Y

Pointer at stack offset points to 16-bit base, then add Y.

```
Pointer Address = S + sr
Base Address = [Pointer Address]
Effective Address = {DB, Base Address + Y}
```

## 4.17 Accumulator (A)

Operation on accumulator contents only.

Example: `ASL A`, `ROL A`, `INC A`

## 4.18 Implied

No operands, operation implicit.

Example: `NOP`, `CLC`, `DEX`, `RTS`

## 4.19 Relative

Signed 8-bit offset from PC+2.

```
Target = PC + 2 + (signed)offset

Instruction Format:
  PC     PC+1
+------+------+
| Op   | Off  |
+------+------+
```

## 4.20 Relative Long

Signed 16-bit offset from PC+3.

```
Target = PC + 3 + (signed)offset

Instruction Format:
  PC     PC+1    PC+2
+------+-------+-------+
| Op   | OffL  | OffH  |
+------+-------+-------+
```

---

# 5. MEMORY MAP

## 5.1 SNES Memory Layout Overview

The SNES uses a 24-bit address bus, allowing access to 16 MB of address space organized into 256 banks of 64 KB each.

```
+--------------------------------------------------+
| Bank | Address Range    | Description            |
+--------------------------------------------------+
| $00-$3F | $0000-$FFFF | System Area (LoROM)    |
| $40-$7F | $0000-$FFFF | System Area Mirror     |
| $80-$BF | $0000-$FFFF | System Area (FastROM)  |
| $C0-$FF | $0000-$FFFF | Cartridge ROM          |
+--------------------------------------------------+
```

## 5.2 System Area ($00-$3F / $80-$BF)

### Low System Area ($00-$3F)

| Bank | Address Range | Description |
|------|---------------|-------------|
| $00-$3F | $0000-$1FFF | Work RAM (WRAM) - 128 KB mirrored |
| $00-$3F | $2000-$20FF | Unused/Open Bus |
| $00-$3F | $2100-$21FF | PPU1 Registers (B-bus) |
| $00-$3F | $2200-$2FFF | Unused/Open Bus |
| $00-$3F | $3000-$3FFF | DSP-1, SA-1, etc. (if present) |
| $00-$3F | $4000-$40FF | Controller Port Registers |
| $00-$3F | $4100-$41FF | Controller Port Registers |
| $00-$3F | $4200-$420F | Internal CPU Registers |
| $00-$3F | $4210-$421F | Internal CPU Registers |
| $00-$3F | $4300-$437F | DMA/HDMA Registers |
| $00-$3F | $4380-$4FFF | Unused |
| $00-$3F | $5000-$7FFF | Reserved for enhancement chips |
| $00-$3F | $8000-$FFFF | Cartridge ROM (LoROM) |

### High System Area ($80-$BF)

Same as $00-$3F but with FastROM access timing (4 cycles vs 6 cycles).

## 5.3 WRAM Organization

```
WRAM (128 KB total):
+----------------------------------------+
| Bank $7E | $0000-$FFFF | First 64 KB   |
| Bank $7F | $0000-$FFFF | Second 64 KB  |
+----------------------------------------+

WRAM Mirrors:
- $00-$3F:$0000-$1FFF → First 8 KB of $7E
- $80-$BF:$0000-$1FFF → First 8 KB of $7E (Fast)
```

## 5.4 Cartridge ROM Areas

### LoROM Mapping

| Bank | Address Range | Content |
|------|---------------|---------|
| $00-$7F | $8000-$FFFF | ROM banks $00-$7F |
| $80-$FF | $8000-$FFFF | ROM banks $80-$FF (Fast) |

### HiROM Mapping

| Bank | Address Range | Content |
|------|---------------|---------|
| $00-$3F | $8000-$FFFF | ROM banks $00-$3F |
| $40-$7D | $0000-$FFFF | ROM banks $40-$7D |
| $80-$BF | $8000-$FFFF | ROM banks $80-$BF (Fast) |
| $C0-$FF | $0000-$FFFF | ROM banks $C0-$FF (Fast) |

## 5.5 Important Memory Regions

### System Vectors

| Address | Vector | Description |
|---------|--------|-------------|
| $FFE4-$FFE5 | COP (Native) | Coprocessor |
| $FFE6-$FFE7 | BRK (Native) | Software Interrupt |
| $FFE8-$FFE9 | ABORT (Native) | Abort (unused) |
| $FFEA-$FFEB | NMI (Native) | Non-Maskable Interrupt |
| $FFEC-$FFED | RESET (Native) | Reset (unused in Native) |
| $FFEE-$FFEF | IRQ (Native) | Interrupt Request |

| Address | Vector | Description |
|---------|--------|-------------|
| $FFF4-$FFF5 | COP (Emu) | Coprocessor |
| $FFF6-$FFF7 | - | Unused |
| $FFF8-$FFF9 | ABORT (Emu) | Abort (unused) |
| $FFFA-$FFFB | NMI (Emu) | Non-Maskable Interrupt |
| $FFFC-$FFFD | RESET (Emu) | Reset Vector |
| $FFFE-$FFFF | IRQ/BRK (Emu) | IRQ/Break |

### CPU Internal Registers

| Address | Register | Description |
|---------|----------|-------------|
| $4200 | NMITIMEN | Interrupt Enable |
| $4201 | WRIO | I/O Port Write |
| $4202 | WRMPYA | Multiplicand A |
| $4203 | WRMPYB | Multiplicand B |
| $4204-$4205 | WRDIVL/H | Dividend |
| $4206 | WRDIVB | Divisor |
| $4207-$4208 | HTIMEL/H | H-Timer |
| $4209-$420A | VTIMEL/H | V-Timer |
| $420B | MDMAEN | DMA Enable |
| $420C | HDMAEN | HDMA Enable |
| $420D | MEMSEL | Memory Select (FastROM) |

| Address | Register | Description |
|---------|----------|-------------|
| $4210 | RDNMI | NMI Flag |
| $4211 | TIMEUP | IRQ Flag |
| $4212 | HVBJOY | PPU Status |
| $4213 | RDIO | I/O Port Read |
| $4214-$4215 | RDDIVL/H | Divide Result |
| $4216-$4217 | RDMPYL/H | Multiply/Divide Remainder |
| $4218-$421F | JOY1-4L/H | Controller Data |

### DMA Registers ($4300-$437F)

Each of 8 DMA channels has 8 registers:

| Offset | Register | Description |
|--------|----------|-------------|
| +$00 | DMAPx | DMA Control |
| +$01 | BBADx | B-Bus Address |
| +$02 | A1TxL | A-Bus Address Low |
| +$03 | A1TxH | A-Bus Address High |
| +$04 | A1Bx | A-Bus Bank |
| +$05 | DASxL | DMA Size Low |
| +$06 | DASxH | DMA Size High |
| +$07 | DASBx | Indirect HDMA Bank |
| +$08 | A2AxL | HDMA Table Address Low |
| +$09 | A2AxH | HDMA Table Address High |
| +$0A | NTRLx | HDMA Line Counter |
| +$0B | UNUSEDx | Unused |
| +$0C | MDMAx | Mirror of DMAPx |
| +$0D | MDMAx | Mirror of BBADx |
| +$0E | MDMAx | Mirror of unused |
| +$0F | MDMAx | Mirror of unused |

---

# 6. INTERRUPT SYSTEM

## 6.1 Interrupt Vectors

| Interrupt | Native Mode | Emulation Mode |
|-----------|-------------|----------------|
| RESET | $FFFC-$FFFD | $FFFC-$FFFD |
| NMI | $FFEA-$FFEB | $FFFA-$FFFB |
| IRQ | $FFEE-$FFEF | $FFFE-$FFFF |
| BRK | $FFE6-$FFE7 | $FFFE-$FFFF |
| COP | $FFE4-$FFE5 | $FFF4-$FFF5 |

## 6.2 Interrupt Behavior

### NMI (Non-Maskable Interrupt)
- Triggered at V-Blank start (configurable)
- Cannot be disabled by I flag
- Pushes PB (Native), PC, P
- Sets I=1, D=0
- Jumps to NMI vector

### IRQ (Interrupt Request)
- Triggered by various sources (timer, controller)
- Disabled when I=1
- Pushes PB (Native), PC, P
- Sets I=1, D=0
- Jumps to IRQ vector

### BRK (Software Break)
- Software-triggered interrupt
- Pushes PB (Native), PC+2, P
- Sets I=1, D=0
- Jumps to BRK vector

---

# 7. CYCLE TIMING NOTES

## 7.1 Cycle Calculation

Base cycles listed in opcode tables assume:
- Fast ROM access ($80-$BF:$8000-$FFFF with MEMSEL=$01)
- Direct Page aligned (D & $FF = 0)
- 8-bit accumulator (M=1)
- 8-bit index registers (X=1)

## 7.2 Cycle Adjustments

| Condition | Adjustment |
|-----------|------------|
| Slow ROM access | +2 cycles |
| X-Slow access (registers) | +4 cycles |
| D low byte != 0 | +1 cycle (DP addressing) |
| M=0 (16-bit accumulator) | +1 cycle (read/write), +2 (R-M-W) |
| X=0 (16-bit index) | +1 cycle (immediate loads), +1 (page cross) |
| Page boundary crossed | +1 cycle (indexed addressing) |
| Branch taken | +1 cycle |
| Branch page cross | +1 additional cycle |

## 7.3 Read-Modify-Write Instructions

Instructions like ASL, ROL, INC, DEC on memory:
- 8-bit: Read (3), Modify (0), Write (3) = 6 cycles base
- 16-bit: ReadL (3), ReadH (3), Modify (0), WriteL (3), WriteH (3) = 8 cycles

---

# 8. QUICK REFERENCE

## 8.1 Flag Effects Summary

| Instruction | N | V | M | X | D | I | Z | C |
|-------------|---|---|---|---|---|---|---|---|
| LDA/LDX/LDY | * | - | - | - | - | - | * | - |
| STA/STX/STY/STZ | - | - | - | - | - | - | - | - |
| ADC | * | * | - | - | - | - | * | * |
| SBC | * | * | - | - | - | - | * | * |
| CMP/CPX/CPY | * | - | - | - | - | - | * | * |
| AND/EOR/ORA | * | - | - | - | - | - | * | - |
| BIT | * | * | - | - | - | - | * | - |
| ASL/LSL/ROL/ROR | * | - | - | - | - | - | * | * |
| INC/INX/INY/DEC/DEX/DEY | * | - | - | - | - | - | * | - |
| SEC/CLC | - | - | - | - | - | - | - | 1/0 |
| SED/CLD | - | - | - | - | 1/0 | - | - | - |
| SEI/CLI | - | - | - | - | - | 1/0 | - | - |
| CLV | - | 0 | - | - | - | - | - | - |
| REP | * | * | * | * | * | * | * | * |
| SEP | * | * | * | * | * | * | * | * |
| TAX/TAY/TXA/TYA/TSX | * | - | - | - | - | - | * | - |
| TXS | - | - | - | - | - | - | - | - |
| XCE | * | - | 1/0 | 1/0 | - | - | - | * |

* = affected, - = not affected, 1/0 = set/clear

## 8.2 Opcode Quick Reference by Hex

```
00 BRK  20 JSR  40 RTI  60 RTS  80 BRA  A0 LDY  C0 CPY  E0 CPX
01 ORA  21 AND  41 EOR  61 ADC  81 STA  A1 LDA  C1 CMP  E1 SBC
02 COP  22 JSR  42 WDM  62 PER  82 BRL  A2 LDX  C2 REP  E2 SEP
03 ORA  23 AND  43 EOR  63 ADC  83 STA  A3 LDA  C3 CMP  E3 SBC
04 TSB  24 BIT  44 MVP  64 STZ  84 STY  A4 LDY  C4 CPY  E4 CPX
05 ORA  25 AND  45 EOR  65 ADC  85 STA  A5 LDA  C5 CMP  E5 SBC
06 ASL  26 ROL  46 LSR  66 ROR  86 STX  A6 LDX  C6 DEC  E6 INC
07 ORA  27 AND  47 EOR  67 ADC  87 STA  A7 LDA  C7 CMP  E7 SBC
08 PHP  28 PLP  48 PHA  68 PLA  88 DEY  A8 TAY  C8 INY  E8 INX
09 ORA  29 AND  49 EOR  69 ADC  89 BIT  A9 LDA  C9 CMP  E9 SBC
0A ASL  2A ROL  4A LSR  6A ROR  8A TXA  AA TAX  CA DEX  EA NOP
0B PHD  2B PLD  4B PHK  6B RTL  8B PHB  AB PLB  CB WAI  EB XBA
0C TSB  2C BIT  4C JMP  6C JMP  8C STY  AC LDY  CC CPY  EC CPX
0D ORA  2D AND  4D EOR  6D ADC  8D STA  AD LDA  CD CMP  ED SBC
0E ASL  2E ROL  4E LSR  6E ROR  8E STX  AE LDX  CE DEC  EE INC
0F ORA  2F AND  4F EOR  6F ADC  8F STA  AF LDA  CF CMP  EF SBC

10 BPL  30 BMI  50 BVC  70 BVS  90 BCC  B0 BCS  D0 BNE  F0 BEQ
11 ORA  31 AND  51 EOR  71 ADC  91 STA  B1 LDA  D1 CMP  F1 SBC
12 ORA  32 AND  52 EOR  72 ADC  92 STA  B2 LDA  D2 CMP  F2 SBC
13 ORA  33 AND  53 EOR  73 ADC  93 STA  B3 LDA  D3 CMP  F3 SBC
14 TRB  34 BIT  54 MVN  74 STZ  94 STY  B4 LDY  D4 PEI  F4 PEA
15 ORA  35 AND  55 EOR  75 ADC  95 STA  B5 LDA  D5 CMP  F5 SBC
16 ASL  36 ROL  56 LSR  76 ROR  96 STX  B6 LDX  D6 DEC  F6 INC
17 ORA  37 AND  57 EOR  77 ADC  97 STA  B7 LDA  D7 CMP  F7 SBC
18 CLC  38 SEC  58 CLI  78 SEI  98 TYA  B8 CLV  D8 CLD  F8 SED
19 ORA  39 AND  59 EOR  79 ADC  99 STA  B9 LDA  D9 CMP  F9 SBC
1A INC  3A DEC  5A PHY  7A PLY  9A TXS  BA TSX  DA PHX  FA PLX
1B TCS  3B TSC  5B TCD  7B TDC  9B TXY  BB TYX  DB STP  FB XCE
1C TRB  3C BIT  5C JMP  7C JMP  9C STZ  BC LDY  DC JMP  FC JSR
1D ORA  3D AND  5D EOR  7D ADC  9D STA  BD LDA  DD CMP  FD SBC
1E ASL  3E ROL  5E LSR  7E ROR  9E STZ  BE LDX  DE DEC  FE INC
1F ORA  3F AND  5F EOR  7F ADC  9F STA  BF LDA  DF CMP  FF SBC
```

---

# Document Information

**CPU**: Ricoh 5A22 (based on WDC 65C816)
**System**: Super Nintendo Entertainment System (SNES)
**Document Version**: 1.0
**Last Updated**: Technical Reference

## References
- WDC 65C816 datasheet
- SNES Development Manual
- Fullsnes - Nocash SNES hardware documentation
- Anomie's SNES documents
