# SNES Enhancement Chips and Coprocessors - Technical Specifications

## Comprehensive Technical Documentation for Emulator Development and Hardware Preservation

---

## Table of Contents

1. [SUPER FX (GSU-1/GSU-2)](#1-super-fx-gsu-1gsu-2)
2. [SA-1 (Super Accelerator 1)](#2-sa-1-super-accelerator-1)
3. [DSP Series (DSP-1/DSP-1A/DSP-1B/DSP-2/DSP-3/DSP-4)](#3-dsp-series)
4. [CX4 (Hitachi HG51B169)](#4-cx4-hitachi-hg51b169)
5. [S-DD1 (Data Decompression)](#5-s-dd1-data-decompression)
6. [S-RTC (Real-Time Clock)](#6-s-rtc-real-time-clock)
7. [OBC-1 (Object Attribute Controller)](#7-obc-1-object-attribute-controller)
8. [SPC7110 (Data Decompression + RTC)](#8-spc7110-data-decompression--rtc)
9. [SETA ST010/ST011/ST018](#9-seta-st010st011st018)
10. [Summary Tables](#10-summary-tables)

---

## 1. SUPER FX (GSU-1/GSU-2)

### 1.1 Overview

The Super FX chip (also known as the Graphics Support Unit or GSU) is a 16-bit RISC coprocessor designed by Argonaut Software specifically for the SNES. It enables real-time 3D polygon rendering and advanced 2D graphical effects.

**Part Numbers:**
- MARIO Chip (first revision, used in Star Fox only)
- GSU-1 (standard package, supports up to 8 Mbit/1 MB ROM)
- GSU-2 (supports full 16 Mbit/2 MB ROM)

**Clock Speeds:**
- GSU-1: 10.74 MHz (default) / 21.477 MHz (high speed mode)
- GSU-2: 10.74 MHz (default) / 21.477 MHz (high speed mode)

### 1.2 Architecture

The GSU is a RISC-based processor with:
- 16-bit internal architecture
- 3 independent 8-bit external buses (SNES, ROM, RAM)
- Pipelined instruction execution
- Hardware pixel plotting with automatic bitplane conversion
- 512-byte instruction cache

### 1.3 General-Purpose Registers (R0-R15)

| Register | Address | Description | SNES Access |
|----------|---------|-------------|-------------|
| R0 | $3000 | Default source/destination register | R/W |
| R1 | $3002 | Pixel plot X position register | R/W |
| R2 | $3004 | Pixel plot Y position register | R/W |
| R3 | $3006 | General purpose | R/W |
| R4 | $3008 | Lower 16-bit result of LMULT | R/W |
| R5 | $300A | General purpose | R/W |
| R6 | $300C | Multiplier for FMULT and LMULT | R/W |
| R7 | $300E | Fixed point texel X position for merge | R/W |
| R8 | $3010 | Fixed point texel Y position for merge | R/W |
| R9 | $3012 | General purpose | R/W |
| R10 | $3014 | General purpose | R/W |
| R11 | $3016 | Return address set by LINK | R/W |
| R12 | $3018 | Loop counter | R/W |
| R13 | $301A | Loop point address | R/W |
| R14 | $301C | ROM address for GETB/GETBH/GETBL/GETBS | R/W |
| R15 | $301E | Program counter | R/W |

### 1.4 Control Registers

| Name | Address | Description | Size | Access |
|------|---------|-------------|------|--------|
| SFR | $3030 | Status Flag Register | 16-bit | R/W |
| BRAMR | $3033 | Backup RAM Register | 8-bit | W |
| PBR | $3034 | Program Bank Register | 8-bit | R/W |
| ROMBR | $3036 | ROM Bank Register | 8-bit | R |
| CFGR | $3037 | Control Flags Register | 8-bit | W |
| SCBR | $3038 | Screen Base Register | 8-bit | W |
| CLSR | $3039 | Clock Speed Register | 8-bit | W |
| SCMR | $303A | Screen Mode Register | 8-bit | W |
| VCR | $303B | Version Code Register (read-only) | 8-bit | R |
| RAMBR | $303C | RAM Bank Register | 8-bit | R |
| CBR | $303E | Cache Base Register | 16-bit | R |

### 1.5 Status Flag Register (SFR) Bits

| Bit | Description |
|-----|-------------|
| 0 | Reserved |
| 1 | Z - Zero flag |
| 2 | CY - Carry flag |
| 3 | S - Sign flag |
| 4 | OV - Overflow flag |
| 5 | G - Go flag (1 when GSU is running) |
| 6 | R - Set when reading ROM using R14 |
| 7 | Reserved |
| 8 | ALT1 - Mode setup flag |
| 9 | ALT2 - Mode setup flag |
| 10 | IL - Immediate lower 8-bit flag |
| 11 | IH - Immediate higher 8-bit flag |
| 12 | B - Set when WITH instruction executed |
| 13-14 | Reserved |
| 15 | IRQ - Set when GSU caused interrupt |

### 1.6 Screen Mode Register (SCMR)

| Bits | Description |
|------|-------------|
| 0-1 | Color depth: 00=2bpp, 01=4bpp, 10=8bpp |
| 2-3 | Screen height: 00=128px, 01=160px, 10=192px, 11=OBJ mode |
| 4 | RAN - RAM access by GSU (0=ROM only, 1=RAM access) |
| 5 | MD - Multiply/Divide delay (0=fast, 1=slow) |
| 6 | HT - High speed timer |
| 7 | Reserved |

### 1.7 Complete Instruction Set

#### Control Instructions

| Instruction | Opcode | Description | Cycles |
|-------------|--------|-------------|--------|
| STOP | $00 | Stop GSU execution | 3 |
| NOP | $01 | No operation | 3 |
| CACHE | $02 | Set cache base register | 3-4 |

#### Prefix Instructions

| Instruction | Opcode | Description |
|-------------|--------|-------------|
| ALT1 | $3D | Set ALT1 mode flag |
| ALT2 | $3E | Set ALT2 mode flag |
| ALT3 | $3F | Set ALT1 and ALT2 mode flags |
| TO | $10-1F | Set destination register (Rn) |
| FROM | $B0-BF | Set source register (Rn) |
| WITH | $20-2F | Set source and destination register |

#### Arithmetic Instructions

| Instruction | Opcode | Description | ALT1 | ALT2 |
|-------------|--------|-------------|------|------|
| ADD | $50-5F | Add | ADC (with carry) | ADD #n |
| SUB | $60-6F | Subtract | SBC (with carry) | SUB #n |
| CMP | $60-6F | Compare (sets flags only) | CMPR | CMP #n |
| MULT | $80-8F | Signed multiply (8x8) | UMULT | MULT #n |
| LMULT | $9F (ALT1) | Signed multiply (16x16) | - | - |
| FMULT | $9F | Fractional multiply | LMULT | - |
| DIV2 | $96 (ALT1) | Divide by 2 | - | - |

#### Logical Instructions

| Instruction | Opcode | Description | ALT1 | ALT2 |
|-------------|--------|-------------|------|------|
| AND | $70-7F | Logical AND | BIC (bit clear) | AND #n |
| OR | $C0-CF | Logical OR | XOR | OR #n |
| NOT | $4F | Invert all bits | - | - |

#### Shift Instructions

| Instruction | Opcode | Description |
|-------------|--------|-------------|
| LSR | $03 | Logical shift right |
| ASR | $96 | Arithmetic shift right |
| ROL | $04 | Rotate left through carry |
| ROR | $97 | Rotate right through carry |

#### Branch Instructions

| Instruction | Opcode | Description |
|-------------|--------|-------------|
| BRA | $05 | Branch always |
| BGE | $06 | Branch if greater than or equal |
| BLT | $07 | Branch if less than |
| BNE | $08 | Branch if not equal |
| BEQ | $09 | Branch if equal |
| BPL | $0A | Branch if plus |
| BMI | $0B | Branch if minus |
| BCC | $0C | Branch if carry clear |
| BCS | $0D | Branch if carry set |
| BVC | $0E | Branch if overflow clear |
| BVS | $0F | Branch if overflow set |
| LOOP | $3C | Decrement R12, branch if not zero |

#### Data Transfer Instructions

| Instruction | Opcode | Description |
|-------------|--------|-------------|
| MOVE | $20-2F, $10-1F | Move Rn' to Rn |
| MOVES | $2B-2F, $B0-BF | Move with flag update |
| SWAP | $4D | Swap high and low bytes |
| SEX | $95 | Sign extend |
| LOB | $9E | Load low byte |
| HIB | $9E (ALT1) | Load high byte |
| MERGE | $70 | Merge R7 and R8 high bytes |

#### Memory Access Instructions

| Instruction | Opcode | Description |
|-------------|--------|-------------|
| LDW | $F0-FF | Load word from RAM |
| LMS | $A0-AF (ALT1) | Load word, short address |
| STW | $30-3F | Store word to RAM |
| SBK | $90-9F | Store to last RAM address |
| GETB | $EF | Get byte from ROM buffer |
| GETBH | $EF (ALT1) | Get high byte from ROM |
| GETBL | $EF (ALT2) | Get low byte from ROM |
| GETBS | $EF (ALT3) | Get signed byte from ROM |
| GETC | $DF | Get byte to color register |

#### Graphics Instructions

| Instruction | Opcode | Description |
|-------------|--------|-------------|
| PLOT | $4C | Plot pixel |
| RPIX | $4C (ALT1) | Read pixel color |
| COLOR | $4E | Set plot color from register |
| CMODE | $4E (ALT1) | Set plot mode |

#### Jump Instructions

| Instruction | Opcode | Description |
|-------------|--------|-------------|
| LJMP | $09 (ALT1) | Long jump (sets PBR) |
| LJSR | $09 (ALT2) | Long jump to subroutine |
| LINK | $09 | Link return address |

### 1.8 Graphics Capabilities

**Virtual Screen Modes:**
- 256x128 pixels (2bpp/4bpp/8bpp)
- 256x160 pixels (2bpp/4bpp/8bpp)
- 256x192 pixels (2bpp/4bpp/8bpp)
- OBJ mode: 4x 128x128 pixel screens

**Pixel Buffer System:**
- 8-pixel wide bitmap buffer for efficient rendering
- Automatic bitplane conversion on flush
- Dual buffer system (primary/secondary) for pipelining

**Plotting Features:**
- Hardware dithering support
- Transparent pixel handling
- Color depth switching (2bpp/4bpp/8bpp)
- Framebuffer readback (RPIX)

### 1.9 Games Using Super FX

| Game | Chip | Year | Notes |
|------|------|------|-------|
| Star Fox / Starwing | MARIO/GSU-1 | 1993 | First Super FX game |
| Stunt Race FX | GSU-1 | 1994 | 3D racing |
| Vortex | GSU-1 | 1994 | 3D shooter |
| Dirt Racer | GSU-1 | 1995 | Racing |
| Doom | GSU-2 | 1995 | Port of PC classic |
| Yoshi's Island | GSU-2 | 1995 | Sprite effects |
| Winter Gold | GSU-2 | 1996 | Multi-event sports |

---

## 2. SA-1 (Super Accelerator 1)

### 2.1 Overview

The SA-1 is a coprocessor based on the 65C816 processor (same as the SNES main CPU) but running at 10.74 MHz - four times the base speed of the SNES CPU. It was manufactured by Nintendo as the RF5A123 chip.

**Part Number:** RF5A123
**Clock Speed:** 10.74 MHz base (effective speed varies based on memory access)
**Architecture:** 65C816 (16-bit with 8-bit compatibility mode)

### 2.2 Memory Organization

**I-RAM (Internal RAM):**
- Size: 2 KB ($0000-$07FF on SA-1 side, $3000-$37FF on SNES side)
- Speed: 10.74 MHz (no wait states)
- Purpose: High-speed work RAM

**BW-RAM (Backup RAM):**
- Maximum: 256 KB (2 Mbit)
- Typical: 8-64 KB
- Speed: 5.37 MHz
- Battery-backed for saves

**Memory Map:**

| Region | SNES CPU | SA-1 CPU | Description |
|--------|----------|----------|-------------|
| $0000-$07FF | WRAM | I-RAM | Fast internal RAM |
| $3000-$37FF | I-RAM | I-RAM | Shared I-RAM |
| $6000-$7FFF | BW-RAM Bank | BW-RAM Bank | Mappable 8KB window |
| $40-$4F:0000-FFFF | BW-RAM | BW-RAM | Full BW-RAM access |
| $60-$6F:0000-FFFF | - | Bitmap BW-RAM | Bitmap view |

### 2.3 Register Map ($2200-$23FF)

**Write Registers ($2200-$22FF):**

| Address | Name | Description |
|---------|------|-------------|
| $2200 | CCNT | SA-1 control |
| $2201 | SIE | SNES IRQ enable |
| $2202 | SIC | SNES IRQ clear |
| $2203 | CRV | SA-1 reset vector |
| $2204 | CRV+1 | SA-1 reset vector (high) |
| $2205 | CNV | SA-1 NMI vector |
| $2206 | CNV+1 | SA-1 NMI vector (high) |
| $2207 | CIV | SA-1 IRQ vector |
| $2208 | CIV+1 | SA-1 IRQ vector (high) |
| $2209 | SCNT | SNES control |
| $220A | CIE | SA-1 IRQ enable |
| $220B | CIC | SA-1 IRQ clear |
| $220C | SNV | SNES NMI vector |
| $220D | SNV+1 | SNES NMI vector (high) |
| $220E | SIV | SNES IRQ vector |
| $220F | SIV+1 | SNES IRQ vector (high) |
| $2210 | TMC | Timer control |
| $2211 | CTR | Timer counter (low) |
| $2212 | CTR+1 | Timer counter (high) |
| $2213 | HCNT | H-count |
| $2214 | HCNT+1 | H-count (high) |
| $2215 | VCNT | V-count |
| $2216 | VCNT+1 | V-count (high) |
| $2220 | CXB | ROM bank C mapping |
| $2221 | DXB | ROM bank D mapping |
| $2222 | EXB | ROM bank E mapping |
| $2223 | FXB | ROM bank F mapping |
| $2224 | BMAPS | SNES BW-RAM mapping |
| $2225 | BMAPC | SA-1 BW-RAM mapping |
| $2226 | SBWE | SNES BW-RAM write enable |
| $2227 | CBWE | SA-1 BW-RAM write enable |
| $2228 | BPWA | BW-RAM write-protected area |
| $2229 | SIWP | SNES I-RAM write protection |
| $222A | CIWP | SA-1 I-RAM write protection |
| $2230 | DCNT | DMA control |
| $2231 | CDMA | Character conversion DMA params |
| $2232-$2234 | SDA | DMA source address |
| $2235-$2237 | DDA | DMA destination address |
| $2238-$2239 | DTC | DMA terminal counter |
| $223F | BBF | BW-RAM bitmap format |
| $2240-$224F | BRF | Bitmap register file |
| $2250 | MCNT | Arithmetic control |
| $2251-$2252 | MA | Multiplicand/Dividend |
| $2253-$2254 | MB | Multiplier/Divisor |
| $2258 | VBD | Variable-length bit processing |
| $2259-$225B | VDA | Variable-length bit ROM address |

**Read Registers ($2300-$23FF):**

| Address | Name | Description |
|---------|------|-------------|
| $2300 | SFR | SNES CPU flag read |
| $2301 | CFR | SA-1 CPU flag read |
| $2302-$2303 | HCR | H-count read |
| $2304-$2305 | VCR | V-count read |
| $2306-$230A | MR | Arithmetic result |
| $230B | OF | Arithmetic overflow flag |
| $230C-$230D | VDP | Variable-length data read |
| $230E-$230F | VC | Version code |

### 2.4 Arithmetic Unit

**Multiplication:**
- 16-bit x 16-bit signed multiplication
- 32-bit result
- 5 cycle latency

**Division:**
- 16-bit / 16-bit signed division
- 16-bit quotient, 16-bit remainder
- 5 cycle latency

**Cumulative Sum:**
- 40-bit accumulator
- Multiply-and-accumulate operation
- Useful for matrix calculations

### 2.5 DMA Controller

**DMA Modes:**
- ROM to I-RAM: 1 byte per 10.74 MHz cycle
- ROM to BW-RAM: 1 byte per 5.37 MHz cycle
- I-RAM to BW-RAM: 1 byte per 5.37 MHz cycle
- BW-RAM to I-RAM: 1 byte per 5.37 MHz cycle

**Character Conversion DMA:**
- Converts bitmap graphics to SNES bitplane format
- Automatic (Type 1) and semi-automatic (Type 2) modes
- Supports 2bpp, 4bpp, and 8bpp conversion
- On-the-fly conversion during SNES DMA

### 2.6 Bitmap Mode

Banks $60-$6F provide a bitmap view of BW-RAM:
- 2BPP mode: Each byte split into 4 x 2-bit pixels
- 4BPP mode: Each byte split into 2 x 4-bit pixels
- Configured via BBF register ($223F)

### 2.7 Variable-Length Bit Processing

- Reads fractional bits from ROM
- Useful for decompression algorithms
- Automatic and fixed modes
- Configurable bit count per read

### 2.8 Games Using SA-1

| Game | Year | Notes |
|------|------|-------|
| Super Mario RPG | 1996 | First SA-1 game |
| Kirby Super Star | 1996 | Multiple minigames |
| Kirby's Dream Land 3 | 1997 | |
| Marvelous | 1996 | Japan only |
| J.League '96 | 1996 | Japan only |
| Jumpin' Derby | 1996 | Japan only |
| SD Gundam G NEXT | 1995 | Japan only |
| Pebble Beach no Hatou New | 1996 | Japan only |
| PGA Tour 96 | 1995 | |
| PGA European Tour | 1996 | |
| Super Shooter | 1996 | Japan only |
| Shogi Saikyou 2 | 1996 | Japan only |
| Mini Yonku Shining Scorpion | 1996 | Japan only |
| Derby Stallion '96 | 1996 | Japan only |
| Itoi Shigesato no Bass Tsuri No. 1 | 1997 | Japan only |
| Bassin's Black Bass | 1994 | |
| Kakinoki Shogi | 1995 | Japan only |
| Hayashi Kaihou Kudan Shogi | 1995 | Japan only |
| Saikousoku Shikou Shogi Mahjong | 1995 | Japan only |
| Shogi Sanmai | 1995 | Japan only |
| Asahi Shinbun Rensai | 1995 | Japan only |
| Harukanaru Augusta 3 | 1994 | Japan only |
| Masters New Harukanaru Augusta | 1995 | Japan only |
| Ongaku Tsukuru Kanadeeru | 1996 | Japan only |
| RPG Tsukuru 2 | 1996 | Japan only |
| Sound Novel Tsukuru | 1996 | Japan only |
| Crayon Shin-chan 4 | 1994 | Japan only |
| Crayon Shin-chan 5 | 1995 | Japan only |
| Daisenryaku Expert WWII | 1996 | Japan only |
| Daisenryaku Expert WWII DX | 1996 | Japan only |
| Takemoto Miho | 1996 | Japan only |
| SFZ2 Turbo Cammy | 1994 | Prototype |

---

## 3. DSP Series

### 3.1 Overview

The DSP series are fixed-point math coprocessors manufactured by NEC. Despite the name "Digital Signal Processor," they function as general-purpose math accelerators rather than traditional DSPs.

**Base Architecture:** NEC uPD77C25 (DSP-1) / uPD96050 (ST series)
**Clock Speed:** 8 MHz (DSP-1), 8.192 MHz (DSP-1A), 8 MHz (DSP-1B)

### 3.2 DSP Variants

| Chip | Games | Notes |
|------|-------|-------|
| DSP-1 | 16 games | Original version |
| DSP-1A | 1 game | Pin-compatible revision |
| DSP-1B | 4 games | Bug fixes |
| DSP-2 | 1 game | Different microcode |
| DSP-3 | 1 game | Different microcode |
| DSP-4 | 1 game | Different microcode |

### 3.3 Internal Architecture

**Program ROM:** 6 KB (2048 x 24-bit instructions)
**Data ROM:** 2 KB (1024 x 16-bit words) - lookup tables
**Data RAM:** 512 bytes (256 x 16-bit words)

**ALU Features:**
- Single-cycle 16-bit x 16-bit signed multiplication
- 32-bit accumulator
- Fixed-point arithmetic support
- 15 ALU functions

### 3.4 SNES Interface

**Register Mapping:**
- Mode 20 (LoROM): $30-$3F:$8000-$FFFF / $B0-$BF:$8000-$FFFF
- Mode 21 (HiROM): $00-$0F:$6000-$6FFF / $80-$8F:$6000-$6FFF

**Data Register (DR):**
- 16-bit internal, 8-bit or 16-bit access mode
- Configurable via command

**Status Register (SR):**
| Bit | Description |
|-----|-------------|
| 7 | RQM - Request for Master (ready for data) |
| 6-0 | Reserved/unknown |

### 3.5 DSP-1 Command Set

| Command | Code | Description | Input Words | Output Words |
|---------|------|-------------|-------------|--------------|
| Multiply | $00 | 16-bit multiplication | 2 | 1 |
| Inverse | $10 | Floating-point reciprocal | 2 | 2 |
| Sin/Cos | $1C | Trigonometric calculation | 1 | 2 |
| Vector Size | $22 | Calculate vector magnitude | 2 | 1 |
| Vector Size Compare | $2D | Compare vector sizes | 4 | 1 |
| Vector Absolute | $30 | Vector absolute value | 2 | 2 |
| Coordinate | $3A | 2D coordinate transform | 2 | 2 |
| 3D Rotation | $3D | 3D coordinate rotation | 6 | 3 |
| Projection | $02 | 3D to 2D projection | 7 | 3 |
| Raster | $0A | Mode 7 raster calculation | 6 | 4/scanline |
| Object Projection | $06 | Object projection | 7 | 4 |
| Screen Coordinate | $3E | Screen to world coordinate | 4 | 2 |
| Attitude Control | $0E | Attitude matrix update | 6 | 6 |
| Global to Object | $1E | Coordinate conversion | 6 | 3 |
| Object to Global | $21 | Coordinate conversion | 6 | 3 |
| Inner Product | $23 | Vector inner product | 6 | 1 |
| New Angle | $2B | Angle calculation | 4 | 2 |

### 3.6 Command Details

**Multiply ($00):**
- Input: Multiplicand (K), Multiplier (I)
- Output: Product (M)
- Cycles: ~27

**Inverse ($10):**
- Input: Coefficient (a), Exponent (b)
- Output: Coefficient (A), Exponent (B)
- Calculates: 1/(a * 2^b) = A * 2^B
- Cycles: ~98

**Sin/Cos ($1C):**
- Input: Angle
- Output: Sin, Cos
- Cycles: ~78

**Projection ($02):**
- Input: X, Y, Z, Xc, Yc, Zc, M
- Output: Xs, Ys, Zs
- Cycles: ~187

**Raster ($0A):**
- Input: Various projection parameters
- Output: Mode 7 matrix values (A, B, C, D) per scanline
- Designed for HDMA usage
- Continuous output until terminated

### 3.7 Games Using DSP-1

| Game | Chip |
|------|------|
| Pilotwings | DSP-1/1B |
| Super Mario Kart | DSP-1/1B |
| Ballz 3D | DSP-1B |
| Dungeon Master | DSP-2 |
| SD Gundam GX | DSP-3 |
| Top Gear 3000 | DSP-4 |
| Soukou Kihei Votoms | DSP-1 |
| Bike Daisuki! Hashiriya Kon | DSP-1 |
| Final Stretch | DSP-1 |
| Lock On / Super Air Diver | DSP-1 |
| Michael Andretti's Indy Car Challenge | DSP-1/1A |
| Shutokou Battle '94 | DSP-1B |
| Shutokou Battle 2 | DSP-1B |
| Suzuka 8 Hours | DSP-1 |
| Super Air Diver 2 | DSP-1 |
| Super Bases Loaded 2 | DSP-1 |
| Super F1 Circus Gaiden | DSP-1 |
| Battle Racers | DSP-1 |
| Ace o Nerae! 3D Tennis | DSP-1A |

---

## 4. CX4 (Hitachi HG51B169)

### 4.1 Overview

The CX4 is a DSP chip manufactured by Hitachi (part number HG51B169) used by Capcom for 3D wireframe graphics and sprite rotation effects in Mega Man X2 and X3.

**Part Number:** Hitachi HG51B169
**Clock Speed:** 20 MHz
**Architecture:** 24-bit DSP with 16-bit opcodes

### 4.2 Memory Organization

**Program ROM:** 256 x 16-bit pages (from SNES ROM)
**Program RAM:** 2 x 256 x 16-bit (2 banks)
**Data ROM:** 1024 x 24-bit (internal lookup tables)
**Data RAM:** 4 x 384 x 16-bit
**Call Stack:** 8 levels, 16-bit wide

### 4.3 Data ROM Contents

| Location | Table Data |
|----------|------------|
| $000-$0FF | Inverse (1/x) |
| $100-$1FF | Square Root |
| $200-$27F | First Quadrant Sine |
| $280-$2FF | First Quadrant Arcsine |
| $300-$37F | First Quadrant Tangent |
| $380-$3FF | First Quadrant Cosine |

### 4.4 Register Interface

**SNES Memory Map:**
- Mode: $20 (HiROM)
- Banks: $00-$3F
- RAM: $6000-$6BFF
- Registers: $7F40-$7FAF

**Key Registers:**

| Address | Function |
|---------|----------|
| $7F40-$7F47 | DMA Transfer |
| $7F49-$7F4B | ROM Offset |
| $7F4D-$7F4E | Page Select |
| $7F4F | Instruction Pointer |
| $7F5E | Status Register |

**16 General-Purpose 24-bit Registers:** $7F80-$7FAF

### 4.5 Command Set

| Command | Code | Function |
|---------|------|----------|
| $00 | Sprite Functions |
| $01 | Wireframe |
| $05 | Propulsion |
| $0D | Set Vector Length |
| $10 | Triangle (polar to cartesian) |
| $13 | Triangle (variant) |
| $15 | Pythagorean |
| $1F | Arc-Tan |
| $22 | Trapezoid |
| $25 | Multiply |
| $2D | Transform Coordinates |

### 4.6 Command Details

**Triangle ($10):**
- Input: Angle (R0), Radius (R1)
- Output: X (R2), Y (R3)
- Calculates: X = R1 * cos(R0), Y = R1 * sin(R0)

**Wireframe ($01):**
- 3D wireframe rendering
- Used for boss introductions in Mega Man X2/X3

### 4.7 Games Using CX4

| Game | Year |
|------|------|
| Mega Man X2 / Rockman X2 | 1994 |
| Mega Man X3 / Rockman X3 | 1995 |

---

## 5. S-DD1 (Data Decompression)

### 5.1 Overview

The S-DD1 (S-DD1) is a hardware data decompression chip that allows the SNES CPU to read compressed data from ROM without software decompression.

**Part Number:** S-DD1
**Manufacturer:** Unknown (likely Nintendo)
**Function:** Lossless data decompression

### 5.2 Compression Algorithm

The S-DD1 uses a variant of Golomb-Rice coding with adaptive probability estimation:

**Key Components:**
- 32 contexts with individual state machines
- 8 Golomb decoders (one per codeword size)
- Arithmetic coding with state transitions
- Bitplane-oriented compression

**Codeword Types:**
- 0-codeword: Run of 2^N MPS (Most Probable Symbol)
- 1N-codeword: Run of [0, 2^N-1] MPS followed by LPS

### 5.3 Register Interface

**Register Mapping:** $4800-$4807 in I/O area banks

| Address | Name | Description |
|---------|------|-------------|
| $4800-$4803 | MMC | ROM bank registers |
| $4804 | DMA Source | DMA channel select |
| $4805-$4806 | Unknown | Written by Star Ocean |
| $4807 | Unknown | Written by Star Ocean |

### 5.4 Decompression Process

1. SNES CPU configures S-DD1 with DMA channel
2. SNES initiates DMA from ROM
3. S-DD1 intercepts DMA reads
4. Decompressor outputs bytes on-the-fly
5. Decompressed data fed to DMA controller

### 5.5 Games Using S-DD1

| Game | Year | Compressed Size | Decompressed Size |
|------|------|-----------------|-------------------|
| Star Ocean | 1996 | 6 MB | 12 MB |
| Street Fighter Alpha 2 | 1996 | - | - |

---

## 6. S-RTC (Real-Time Clock)

### 6.1 Overview

The S-RTC is a real-time clock chip used in a single SNES game for timekeeping functionality.

**Part Number:** S-RTC (with external RTC-4513)
**Manufacturer:** Epson (RTC-4513)
**Function:** Real-time clock/calendar

### 6.2 RTC-4513 Specifications

**Features:**
- Built-in crystal oscillator
- Serial interface (3 signal lines)
- Automatic leap year correction
- 30-second adjustment capability
- Operating voltage: 2.7V - 5.5V

**Pinout:**
| Pin | Function |
|-----|----------|
| 2 | DATA |
| 12 | CE (Chip Enable) |
| 13 | CLK (Clock) |
| 6 | VDD |
| 9 | GND |

### 6.3 Register Interface

The S-RTC interfaces with the SNES through serial communication:
- Data: Serial data line
- CLK: Clock signal
- CE: Chip enable

### 6.4 Games Using S-RTC

| Game | Year |
|------|------|
| Daikaijuu Monogatari II | 1996 (Japan only) |

---

## 7. OBC-1 (Object Attribute Controller)

### 7.1 Overview

The OBC-1 is one of the simplest SNES enhancement chips, designed to help build sprite tables in RAM for DMA to OAM (Object Attribute Memory).

**Part Number:** OBC-1
**Function:** Sprite table management

### 7.2 Functionality

The OBC-1 assists with:
- Building sprite attribute tables in cartridge RAM
- Managing OAM data structures
- Preparing sprite data for DMA transfer

### 7.3 Games Using OBC-1

| Game | Year |
|------|------|
| Metal Combat: Falcon's Revenge | 1993 |

---

## 8. SPC7110 (Data Decompression + RTC)

### 8.1 Overview

The SPC7110 is a data decompression chip manufactured by Epson (Seiko Epson Corporation). It includes integrated real-time clock functionality in some configurations.

**Part Number:** SPC7110F0a
**Manufacturer:** Seiko Epson Corporation
**Functions:** Data decompression, RTC interface

### 8.2 Memory Organization

**ROM Layout:**
- Program ROM: 8 Mbit (1 MB) - $C0:0000-$CF:FFFF
- Data ROM: 32 Mbit (4 MB) - banks $D0-$FF
- Decompressed data mapped to: $50:0000-$50:FFFF

### 8.3 Register Map ($4800-$4842)

**Decompression Registers:**

| Address | Name | Description |
|---------|------|-------------|
| $4800 | DECOMP | Decompressed data read port |
| $4801-$4803 | TABLE | Compressed data table pointer |
| $4804 | INDEX | Table index |
| $4805-$4806 | OFFSET | Decompressed data offset |
| $4807 | DMA | DMA channel select |
| $4808 | OPTION | Unknown |
| $4809-$480A | LENGTH | Compression length counter |
| $480B | MODE | Decompression command mode |
| $480C | STATUS | Decompression finished status |

**Data ROM Access:**

| Address | Name | Description |
|---------|------|-------------|
| $4810 | DREAD | Data ROM read port |
| $4811-$4813 | DPTR | Data ROM pointer |
| $4814-$4815 | ADJUST | Pointer adjust |
| $4816-$4817 | INCR | Pointer increment |
| $4818 | CMD | Data ROM command mode |
| $481A | DREADA | Read after adjust |

**Math Unit:**

| Address | Name | Description |
|---------|------|-------------|
| $4820-$4821 | MULTA | 16-bit multiplicand |
| $4822-$4823 | DIVIDEND | 32-bit dividend |
| $4824-$4825 | MULTB | 16-bit multiplier |
| $4826-$4827 | DIVISOR | 16-bit divisor |
| $4828-$482B | RESULT | 32-bit product/quotient |
| $482C-$482D | REMAINDER | 16-bit remainder |
| $482E | RESET | Math reset |
| $482F | STATUS | Math status |

**Bank Mapping:**

| Address | Name | Description |
|---------|------|-------------|
| $4830 | SRAM | SRAM enable |
| $4831-$4833 | BANK | ROM bank mapping |

**RTC Registers:**

| Address | Name | Description |
|---------|------|-------------|
| $4840 | RTCEN | RTC enable/disable |
| $4841 | RTCDAT | RTC index/data port |
| $4842 | RTCSTS | RTC ready status |

### 8.4 RTC Registers (Internal)

| Index | Description |
|-------|-------------|
| $00 | Seconds 1's digit |
| $01 | Seconds 10's digit |
| $02 | Minutes 1's digit |
| $03 | Minutes 10's digit |
| $04 | Hours 1's digit |
| $05 | Hours 10's digit |
| $06 | Day 1's digit |
| $07 | Day 10's digit |
| $08 | Month 1's digit |
| $09 | Month 10's digit |
| $0A | Year 1's digit |
| $0B | Year 10's digit |
| $0C | Day of week |
| $0D-$0F | Control registers |

### 8.5 Decompression Modes

**Mode $00:** Manual decompression
- Direct read from data ROM
- Disable offset modes

**Mode $02:** Hardware decompression
- Decompressed data mapped to bank $50
- Enable offset modes

### 8.6 Games Using SPC7110

| Game | Year | RTC |
|------|------|-----|
| Tengai Makyou Zero (Far East of Eden Zero) | 1995 | Yes |
| Momotaro Dentetsu Happy | 1996 | No |
| Super Power League 4 | 1996 | No |

---

## 9. SETA ST010/ST011/ST018

### 9.1 Overview

The SETA ST series are AI and physics coprocessors based on NEC DSP cores. They were used exclusively by SETA Corporation for enhanced game AI.

### 9.2 ST010

**Part Number:** ST010 (marked ST-010 on PCB)
**Base Chip:** NEC uPD96050
**Clock Speed:** 10 MHz (20 MHz oscillator / 2)

**Architecture:**
- 24-bit ALU
- 16-bit x 16-bit multiplication
- 8-level stack
- 14-bit program counter
- 16 KB program ROM (16384 x 24-bit)
- 4 KB data ROM (2048 x 16-bit)
- 4 KB data RAM (2048 x 16-bit, battery-backed)

**SNES Interface:**
- DR (Data Register): $60:0000
- SR (Status Register): $60:0001
- Data RAM: $68-$6F:$0000-$0FFF / $E8-$EF:$0000-$0FFF

**Game:**
- F1 ROC II: Race of Champions (1993)

### 9.3 ST011

**Part Number:** ST011
**Base Chip:** NEC uPD96050
**Clock Speed:** 15 MHz

**Architecture:** Same as ST010

**Game:**
- Hayazashi Nidan Morita Shogi (1995, Japan only)

### 9.4 ST018

**Part Number:** ST018 (marked ST-018 on PCB)
**Architecture:** ARMv3 32-bit RISC
**Clock Speed:** 21.47 MHz

**Features:**
- 32-bit ARM processor
- Advanced AI capabilities
- More powerful than ST010/ST011

**Game:**
- Hayazashi Nidan Morita Shogi 2 (1995, Japan only)

### 9.5 NEC uPD96050 Architecture

**Comparison with uPD77C25:**

| Feature | uPD77C25 | uPD96050 |
|---------|----------|----------|
| Clock | 8.192 MHz | 20 MHz (10 MIPS) |
| Stack | 4-level | 8-level |
| Program ROM | 2048 x 24-bit | 16384 x 24-bit |
| Data ROM | 1024 x 16-bit | 2048 x 16-bit |
| Data RAM | 256 x 16-bit | 2048 x 16-bit |
| PC | 11-bit | 14-bit |
| RP | 10-bit | 11-bit |
| DP | 8-bit | 11-bit |

---

## 10. Summary Tables

### 10.1 Enhancement Chip Comparison

| Chip | Manufacturer | CPU Type | Clock | Main Function |
|------|--------------|----------|-------|---------------|
| MARIO/GSU-1 | Argonaut/Nintendo | Custom RISC | 10.74/21.48 MHz | 3D graphics |
| GSU-2 | Argonaut/Nintendo | Custom RISC | 10.74/21.48 MHz | 3D graphics |
| SA-1 | Nintendo | 65C816 | 10.74 MHz | General acceleration |
| DSP-1 | NEC | uPD77C25 | 8 MHz | Math coprocessor |
| DSP-1A | NEC | uPD77C25 | 8.192 MHz | Math coprocessor |
| DSP-1B | NEC | uPD77C25 | 8 MHz | Math coprocessor |
| DSP-2 | NEC | uPD77C25 | 8 MHz | Math coprocessor |
| DSP-3 | NEC | uPD77C25 | 8 MHz | Math coprocessor |
| DSP-4 | NEC | uPD77C25 | 8 MHz | Math coprocessor |
| CX4 | Hitachi | HG51B169 | 20 MHz | 3D wireframe |
| S-DD1 | Nintendo | Custom | - | Decompression |
| S-RTC | Epson | RTC-4513 | - | Real-time clock |
| OBC-1 | Nintendo | Custom | - | Sprite management |
| SPC7110 | Epson | Custom | - | Decompression/RTC |
| ST010 | SETA/NEC | uPD96050 | 10 MHz | AI/Physics |
| ST011 | SETA/NEC | uPD96050 | 15 MHz | AI/Physics |
| ST018 | SETA | ARMv3 | 21.47 MHz | AI/Physics |

### 10.2 Games by Enhancement Chip

| Chip | Game Count | Notable Games |
|------|------------|---------------|
| Super FX | 7 | Star Fox, Doom, Yoshi's Island |
| SA-1 | 33 | Super Mario RPG, Kirby Super Star |
| DSP-1 | 19 | Super Mario Kart, Pilotwings |
| DSP-2 | 1 | Dungeon Master |
| DSP-3 | 1 | SD Gundam GX |
| DSP-4 | 1 | Top Gear 3000 |
| CX4 | 2 | Mega Man X2, X3 |
| S-DD1 | 2 | Star Ocean, Street Fighter Alpha 2 |
| S-RTC | 1 | Daikaijuu Monogatari II |
| OBC-1 | 1 | Metal Combat |
| SPC7110 | 3 | Far East of Eden Zero |
| ST010 | 1 | F1 ROC II |
| ST011 | 1 | Hayazashi Nidan Morita Shogi |
| ST018 | 1 | Hayazashi Nidan Morita Shogi 2 |

### 10.3 Memory Map Summary

| Chip | ROM Max | RAM | Special Memory |
|------|---------|-----|----------------|
| GSU-1 | 1 MB | 32-64 KB | 512 B cache |
| GSU-2 | 2 MB | 32-64 KB | 512 B cache |
| SA-1 | 8 MB | 256 KB BW + 2 KB I-RAM | - |
| DSP-1 | N/A | 512 B | 6 KB prog, 2 KB data |
| CX4 | 4 MB | 3 KB | 3 KB data ROM |
| S-DD1 | 6 MB | - | - |
| SPC7110 | 5 MB | 8 KB | - |

### 10.4 Instruction Set Summary

| Chip | Opcode Size | Registers | Multiply |
|------|-------------|-----------|----------|
| GSU | 8-bit | 16 x 16-bit | 8x8, 16x16 |
| SA-1 | 8-bit (65C816) | 6 (A,X,Y,D,S,DB,PB) | Hardware 16x16 |
| DSP-1 | 24-bit | 4 x 16-bit | 16x16 (1 cycle) |
| CX4 | 16-bit | 16 x 24-bit | 24x24 |
| ST010 | 24-bit | 4 x 16-bit | 16x16 |

---

## References

1. Super Nintendo Development Manual (Books I & II)
2. SNESdev Wiki (snes.nesdev.org)
3. Super Famicom Development Wiki (wiki.superfamicom.org)
4. SNESLab (sneslab.net)
5. jsgroth's Blog (jsgroth.dev)
6. bsnes Emulator Source Code
7. Snes9x Emulator Source Code
8. ares Emulator Source Code

---

*Document Version: 1.0*
*Last Updated: 2025*
*For Emulator Development and Hardware Preservation*
