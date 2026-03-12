# Super Nintendo Entertainment System (SNES) Technical Specifications

## Comprehensive System-Level Documentation

---

## 1. SYSTEM OVERVIEW

### 1.1 Release Information

| Region | Release Date | Official Name | Model Number |
|--------|--------------|---------------|--------------|
| Japan | November 21, 1990 | Super Famicom (SFC) | SHVC-001 |
| North America | August 23, 1991 | Super Nintendo Entertainment System | SNS-001 |
| Europe | April 11, 1992 | Super Nintendo Entertainment System | SNSP-001A |
| Australia | July 3, 1992 | Super Nintendo Entertainment System | SNSP-001A |
| South Korea | 1992 | Super Comboy | - |

### 1.2 Regional Variants

**Super Famicom (Japan)**
- Purple and gray color scheme
- Different cartridge shape (physical region lock)
- Eject button on top
- RF output standard
- Expansion port on bottom

**SNES (North America)**
- Purple and gray color scheme
- Boxier design with sliding power switch
- Different cartridge shape
- No expansion port on retail units

**SNES (PAL Regions)**
- Similar to North American design
- Different internal oscillator for 50Hz video
- Slower CPU clock speed

### 1.3 Master Clock Frequencies

| Region | Master Clock | CPU Clock | Dot Clock | Notes |
|--------|--------------|-----------|-----------|-------|
| NTSC (JPN/USA) | 21.477272 MHz | 3.579545 MHz | 5.369318 MHz | Derived from color subcarrier × 6 |
| PAL (EUR/AUS) | 21.281370 MHz | 3.546895 MHz | 5.320342 MHz | Derived from PAL color subcarrier |

### 1.4 Clock Derivation

```
NTSC Master Clock: 21.477272 MHz
├── ÷ 6 = 3.579545 MHz (CPU Clock)
├── ÷ 4 = 5.369318 MHz (Dot Clock)
└── ÷ 11.25 = 1.789772 MHz (Audio Clock base)

PAL Master Clock: 21.281370 MHz
├── ÷ 6 = 3.546895 MHz (CPU Clock)
├── ÷ 4 = 5.320342 MHz (Dot Clock)
└── ÷ 11.25 = 1.892834 MHz (Audio Clock base)
```

### 1.5 System Components

| Component | Manufacturer | Model | Function |
|-----------|--------------|-------|----------|
| CPU | Ricoh | 5A22 | Custom 65C816-based processor |
| PPU1 | Ricoh | 5C77 | Picture Processing Unit 1 |
| PPU2 | Ricoh | 5C78 | Picture Processing Unit 2 |
| SPU | Sony | S-DSP + SPC700 | Sound Processing Unit |
| CIC | Sharp | Various | Lockout/region protection |

---

## 2. MEMORY MAP

### 2.1 Address Space Architecture

The SNES uses a 24-bit address bus (16MB addressable space) organized into 256 banks ($00-$FF). Each bank contains 64KB ($0000-$FFFF).

### 2.2 Bank Organization Overview

```
Banks $00-$3F: System Area + ROM (LoROM/HiROM)
Banks $40-$6F: ROM continuation
Banks $70-$77: SRAM (typically)
Banks $80-$BF: Mirror of $00-$3F (with FastROM)
Banks $C0-$FF: ROM (HiROM) or continuation (LoROM)
```

### 2.3 Low Bank ($00-$3F) Memory Map

| Address Range | Size | Description | Access |
|---------------|------|-------------|--------|
| $0000-$1FFF | 8KB | Work RAM (WRAM) - Low | R/W |
| $2000-$20FF | 256B | PPU1 Registers | Write mostly |
| $2100-$21FF | 256B | PPU2 Registers | Write mostly |
| $2200-$2FFF | 3.75KB | Unused/Expansion | - |
| $3000-$3FFF | 4KB | Unused/Expansion | - |
| $4000-$40FF | 256B | Controller Port 1/2 Registers | R/W |
| $4100-$41FF | 256B | Controller Port 3/4 / Unused | R/W |
| $4200-$42FF | 256B | Internal CPU Registers | R/W |
| $4300-$437F | 128B | DMA/HDMA Channel Registers | R/W |
| $4380-$5FFF | ~8KB | Unused | - |
| $6000-$7FFF | 8KB | SRAM (if present) | R/W |
| $8000-$FFFF | 32KB | Cartridge ROM | Read |

### 2.4 WRAM (Work RAM) Details

```
WRAM: 128KB total (SRAM chips: 2 × 64KB or 1 × 128KB)

Bank $00: $0000-$1FFF → WRAM $0000-$1FFF
Bank $00: $2000-$FFFF → WRAM $0000-$DFFF (mirror of $0000-$DFFF)

Bank $01-$3F: $6000-$7FFF → WRAM $0000-$FFFF (full 64KB accessible)
Bank $01-$3F: $0000-$1FFF → WRAM $0000-$1FFF (mirror)

Bank $7E: $0000-$FFFF → WRAM $0000-$FFFF (full 64KB)
Bank $7F: $0000-$FFFF → WRAM $10000-$1FFFF (second 64KB)
```

### 2.5 PPU1 Registers ($2000-$20FF)

| Address | Register | Description |
|---------|----------|-------------|
| $2100 | INIDISP | Display Control 1 |
| $2101 | OBSEL | Object Size and Character Base |
| $2102 | OAMADDL | OAM Address Low |
| $2103 | OAMADDH | OAM Address High & Priority Rotation |
| $2104 | OAMDATA | OAM Data Write |
| $2105 | BGMODE | BG Mode and Character Size |
| $2106 | MOSAIC | Mosaic Size and Enable |
| $2107 | BG1SC | BG1 Tilemap Address and Size |
| $2108 | BG2SC | BG2 Tilemap Address and Size |
| $2109 | BG3SC | BG3 Tilemap Address and Size |
| $210A | BG4SC | BG4 Tilemap Address and Size |
| $210B | BG12NBA | BG1/2 Character Data Address |
| $210C | BG34NBA | BG3/4 Character Data Address |
| $210D | BG1HOFS | BG1 Horizontal Scroll |
| $210E | BG1VOFS | BG1 Vertical Scroll |
| $210F | BG2HOFS | BG2 Horizontal Scroll |
| $2110 | BG2VOFS | BG2 Vertical Scroll |
| $2111 | BG3HOFS | BG3 Horizontal Scroll |
| $2112 | BG3VOFS | BG3 Vertical Scroll |
| $2113 | BG4HOFS | BG4 Horizontal Scroll |
| $2114 | BG4VOFS | BG4 Vertical Scroll |
| $2115 | VMAIN | Video Port Control |
| $2116 | VMADDL | Video Port Address Low |
| $2117 | VMADDH | Video Port Address High |
| $2118 | VMDATAL | Video Port Data Low |
| $2119 | VMDATAH | Video Port Data High |
| $211A | M7SEL | Mode 7 Settings |
| $211B | M7A | Mode 7 Matrix A |
| $211C | M7B | Mode 7 Matrix B |
| $211D | M7C | Mode 7 Matrix C |
| $211E | M7D | Mode 7 Matrix D |
| $211F | M7X | Mode 7 Center X |
| $2120 | M7Y | Mode 7 Center Y |

### 2.6 PPU2 Registers ($2100-$213F)

| Address | Register | Description |
|---------|----------|-------------|
| $2121 | CGADD | CGRAM Address |
| $2122 | CGDATA | CGRAM Data Write |
| $2123 | W12SEL | Window Mask Settings for BG1/2 |
| $2124 | W34SEL | Window Mask Settings for BG3/4 |
| $2125 | WOBJSEL | Window Mask Settings for OBJ/Color |
| $2126 | WH0 | Window 1 Left Position |
| $2127 | WH1 | Window 1 Right Position |
| $2128 | WH2 | Window 2 Left Position |
| $2129 | WH3 | Window 2 Right Position |
| $212A | WBGLOG | Window Logic for BGs |
| $212B | WOBJLOG | Window Logic for OBJ/Color |
| $212C | TM | Main Screen Designation |
| $212D | TS | Sub Screen Designation |
| $212E | TMW | Window Mask Designation for Main Screen |
| $212F | TSW | Window Mask Designation for Sub Screen |
| $2130 | CGWSEL | Color Math Selection |
| $2131 | CGADSUB | Color Math Enable |
| $2132 | COLDATA | Fixed Color Data |
| $2133 | SETINI | Display Control 2 |
| $2134 | MPYL | PPU1 Signed Multiply Result Low |
| $2135 | MPYM | PPU1 Signed Multiply Result Middle |
| $2136 | MPYH | PPU1 Signed Multiply Result High |
| $2137 | SLHV | PPU1 Latch H/V Counter |
| $2138 | RDOAM | PPU1 OAM Data Read |
| $2139 | RDVRAML | PPU1 VRAM Data Read Low |
| $213A | RDVRAMH | PPU1 VRAM Data Read High |
| $213B | RDCGRAM | PPU2 CGRAM Data Read |
| $213C | OPHCT | PPU2 Horizontal Counter Latch |
| $213D | OPVCT | PPU2 Vertical Counter Latch |
| $213E | STAT77 | PPU1 Status |
| $213F | STAT78 | PPU2 Status |

### 2.7 CPU Internal Registers ($4200-$42FF)

| Address | Register | Description |
|---------|----------|-------------|
| $4200 | NMITIMEN | Interrupt Enable |
| $4201 | WRIO | I/O Port Write |
| $4202 | WRMPYA | Multiplicand A |
| $4203 | WRMPYB | Multiplier B |
| $4204 | WRDIVL | Dividend Low |
| $4205 | WRDIVH | Dividend High |
| $4206 | WRDIVB | Divisor |
| $4207 | HTIMEL | H-Count Timer Low |
| $4208 | HTIMEH | H-Count Timer High |
| $4209 | VTIMEL | V-Count Timer Low |
| $420A | VTIMEH | V-Count Timer High |
| $420B | MDMAEN | DMA Enable |
| $420C | HDMAEN | HDMA Enable |
| $420D | MEMSEL | Memory-2 Wait State Control |
| $4210 | RDNMI | NMI Flag |
| $4211 | TIMEUP | IRQ Flag |
| $4212 | HVBJOY | H/V Blank and Joypad Status |
| $4213 | RDIO | I/O Port Read |
| $4214 | RDDIVL | Quotient of Divide Result Low |
| $4215 | RDDIVH | Quotient of Divide Result High |
| $4216 | RDMPYL | Product/Remainder Low |
| $4217 | RDMPYH | Product/Remainder High |
| $4218-$421F | JOY1-JOY4 | Joypad Registers |

### 2.8 DMA/HDMA Registers ($4300-$437F)

Each of the 8 DMA channels has 16 bytes of registers:

| Offset | Register | Description |
|--------|----------|-------------|
| +$00 | DMAPx | DMA/HDMA Parameters |
| +$01 | BBADx | DMA/HDMA I/O-Bus Address (PPU register) |
| +$02 | A1TxL | HDMA Table Start Address / DMA Current Address Low |
| +$03 | A1TxH | HDMA Table Start Address / DMA Current Address High |
| +$04 | A1Bx | HDMA Table Start Address / DMA Current Address Bank |
| +$05 | DASxL | Indirect HDMA Address / DMA Byte Counter Low |
| +$06 | DASxH | Indirect HDMA Address / DMA Byte Counter High |
| +$07 | DASBx | Indirect HDMA Address Bank |
| +$08 | A2AxL | HDMA Table Current Address Low |
| +$09 | A2AxH | HDMA Table Current Address High |
| +$0A | NLTRx | HDMA Line Counter and Repeat |
| +$0B | UNUSEDx | Unused |
| +$0C | UNUSEDx | Unused |
| +$0D | UNUSEDx | Unused |
| +$0E | UNUSEDx | Unused |
| +$0F | UNUSEDx | Unused |

**Channel Base Addresses:**
- Channel 0: $4300-$430F
- Channel 1: $4310-$431F
- Channel 2: $4320-$432F
- Channel 3: $4330-$433F
- Channel 4: $4340-$434F
- Channel 5: $4350-$435F
- Channel 6: $4360-$436F
- Channel 7: $4370-$437F

### 2.9 Cartridge Memory Mapping Modes

#### LoROM (Mode 20/21)
```
Banks $00-$7D: $8000-$FFFF = ROM (32KB per bank)
Banks $80-$FF: $8000-$FFFF = ROM (mirror with FastROM)
SRAM typically at $70-$7D: $0000-$7FFF
Total ROM: Up to 32MB (4MB typical)
```

#### HiROM (Mode 25)
```
Banks $00-$3F: $8000-$FFFF = ROM (32KB per bank)
Banks $40-$6F: $0000-$FFFF = ROM (64KB per bank)
Banks $C0-$FF: $0000-$FFFF = ROM (mirror with FastROM)
SRAM typically at $20-$3F: $6000-$7FFF
Total ROM: Up to 64MB (4MB typical)
```

#### ExLoROM (Mode 22/32)
```
Extended LoROM with additional banks
Supports up to 64MB ROM
```

#### ExHiROM (Mode 25)
```
Extended HiROM with additional banks
Supports up to 128MB ROM
```

### 2.10 Complete Bank Reference

| Bank Range | Purpose |
|------------|---------|
| $00-$3F | System registers, WRAM, ROM (LoROM/HiROM) |
| $40-$6F | ROM continuation (HiROM) |
| $70-$77 | SRAM (typical location) |
| $78-$7D | SRAM expansion |
| $7E-$7F | Full WRAM access (128KB) |
| $80-$BF | Mirror of $00-$3F with FastROM |
| $C0-$FF | ROM (HiROM) or continuation (LoROM) |

---

## 3. PPU (PICTURE PROCESSING UNIT)

### 3.1 PPU Architecture Overview

The SNES PPU is split into two custom chips:

**PPU1 (5C77):**
- Background rendering engine
- Mode 7 transformation unit
- OAM (sprite) processing
- VRAM interface
- Multiply unit

**PPU2 (5C78):**
- Color math/compositing
- Windowing logic
- Screen output generation
- CGRAM (palette) management
- H/V counter

### 3.2 VRAM Organization

```
VRAM: 64KB (32K × 16-bit words)

Addressing: $0000-$7FFF (word addresses)

Tile Data:
- 2bpp tiles: 32 bytes per tile
- 4bpp tiles: 32 bytes per tile
- 8bpp tiles: 64 bytes per tile
- Mode 7 tiles: 8 bytes per tile

Tilemap Data:
- 2 bytes per tilemap entry
```

### 3.3 CGRAM (Color Generator RAM)

```
CGRAM: 512 bytes (256 × 15-bit colors)

Format: 0bbbbbgggggrrrrr (BGR555)
- 5 bits per color component
- 32,768 possible colors
- Color 0 is transparent for each palette

Organization:
- Colors $00-$7F: Background palettes
- Colors $80-$FF: Sprite palettes
```

### 3.4 OAM (Object Attribute Memory)

```
OAM: 544 bytes total

Primary OAM: 512 bytes (128 sprites × 4 bytes)
- X coordinate (9 bits)
- Y coordinate (8 bits)
- Tile number (9 bits)
- Attributes: palette, priority, flip

Secondary OAM: 32 bytes (32 entries × 1 byte)
- Sprite index for active sprites per scanline
```

### 3.5 Video Modes

#### Mode 0 (4 backgrounds, 2bpp each)
```
BG1: 2bpp (4 colors)
BG2: 2bpp (4 colors)
BG3: 2bpp (4 colors)
BG4: 2bpp (4 colors)
Max colors on screen: 32 (4 palettes × 4 colors × 2)
Priority: BG1/2 > Sprites > BG3/4
```

#### Mode 1 (3 backgrounds, mixed depth)
```
BG1: 4bpp (16 colors)
BG2: 4bpp (16 colors)
BG3: 2bpp (4 colors) or 4bpp with OPT
Max colors on screen: 128
Most common game mode
```

#### Mode 2 (2 backgrounds, 4bpp + offset change)
```
BG1: 4bpp with horizontal offset-per-tile
BG2: 4bpp with vertical offset-per-tile
Used for parallax effects
```

#### Mode 3 (2 backgrounds, 8bpp + 4bpp)
```
BG1: 8bpp (256 colors) - direct color mode available
BG2: 4bpp (16 colors)
Max colors: 256 + 16 = 272
Used for high-color backgrounds
```

#### Mode 4 (2 backgrounds, 8bpp + 2bpp + offset)
```
BG1: 8bpp with horizontal offset-per-tile
BG2: 2bpp with vertical offset-per-tile
```

#### Mode 5 (2 backgrounds, 16×8 tiles)
```
BG1: 4bpp, 16×8 tiles (interlace mode)
BG2: 2bpp, 16×8 tiles
Horizontal resolution: 512 pixels
```

#### Mode 6 (1 background, 16×8 + offset)
```
BG1: 4bpp, 16×8 tiles with offset-per-tile
Horizontal resolution: 512 pixels
```

#### Mode 7 (1 background, rotation/scaling)
```
BG1: 8bpp, 1024×1024 pixel background
Matrix transformation: rotate, scale, perspective
Direct color available
```

### 3.6 Mode 7 Matrix Mathematics

```
X' = ((A × (X - CX)) + (B × (Y - CY))) / 256 + CX
Y' = ((C × (X - CX)) + (D × (Y - CY))) / 256 + CY

Where:
- A, B, C, D are 8.8 fixed-point matrix values
- CX, CY are center coordinates
- X, Y are screen coordinates
- X', Y' are background fetch coordinates
```

### 3.7 Background Layer Specifications

| Attribute | Specification |
|-----------|---------------|
| Tile sizes | 8×8 or 16×16 pixels |
| Tilemap sizes | 32×32, 64×32, 32×64, 64×64 tiles |
| Max tilemaps | 4 (BG1-BG4) |
| Priority levels | 0-3 per background |
| Scroll resolution | 1 pixel (Mode 7: 1/256 pixel) |

### 3.8 Sprite System

| Attribute | Specification |
|-----------|---------------|
| Max sprites | 128 |
| Max sprites/scanline | 32 |
| Sprite sizes | 8×8, 16×16, 32×32, 64×64 (various combinations) |
| Sprite sizes (small/large) | Configurable per game |
| Colors per sprite | 16 (4bpp) or 256 (8bpp in Modes 3,4,7) |
| Priority levels | 0-3 |

**Sprite Size Combinations (OBSEL register):**
```
Value | Small | Large
------|-------|------
  0   |  8×8  | 16×16
  1   |  8×8  | 32×32
  2   |  8×8  | 64×64
  3   | 16×16 | 32×32
  4   | 16×16 | 64×64
  5   | 32×32 | 64×64
  6   | 16×32 | 32×64
  7   | 16×32 | 32×32
```

### 3.9 Color Math

**Operations:**
- Add (clamped or unclamped)
- Subtract (clamped or unclamped)
- Average (halve result)

**Sources:**
- Main screen (any BGs/sprites)
- Sub screen (any BGs/sprites)
- Fixed color (register $2132)

**Application:**
- Entire screen
- Inside windows only
- Outside windows only

### 3.10 Windowing System

**Window Registers:**
- Window 1: WH0, WH1 (horizontal bounds)
- Window 2: WH2, WH3 (horizontal bounds)

**Window Logic:**
- OR (union)
- AND (intersection)
- XOR (exclusive)
- XNOR (inverse XOR)

**Applications:**
- Per-layer masking
- Color math regions
- Screen fade effects

### 3.11 HDMA Effects

HDMA can modify per-scanline:
- Background scroll registers
- Color math settings
- Window positions
- Mode 7 matrix
- Palette entries

---

## 4. DMA AND HDMA

### 4.1 DMA Overview

The SNES has 8 independent DMA channels for high-speed data transfer between memory and I/O registers.

### 4.2 DMA Transfer Modes

| Mode | Transfer Pattern | Description |
|------|------------------|-------------|
| 0 | A → B | Single byte/word |
| 1 | A → B, A+1 → B | Two registers |
| 2 | A → B, A → B+1 | Single to two registers |
| 3 | A → B, A+1 → B, A+2 → B, A+3 → B | Four sequential |
| 4 | A → B, A+1 → B, A → B+1, A+1 → B+1 | Two pairs |
| 5 | A → B, A+1 → B, A+2 → B, A+3 → B, A+4 → B, A+5 → B | Six sequential |
| 6 | A → B, A → B+1, A+1 → B, A+1 → B+1 | Two to two registers |
| 7 | A → B, A+1 → B, A+2 → B, A+3 → B, A → B+1, A+1 → B+1, A+2 → B+1, A+3 → B+1 | Four to two registers |

### 4.3 DMAPx Register Format

```
Bit 7: Transfer Direction
  0 = CPU → I/O (write to PPU)
  1 = I/O → CPU (read from PPU)

Bit 6: Addressing Mode
  0 = Increment A bus address
  1 = Fixed A bus address (HDMA only)
  1 = Decrement A bus address (DMA only)

Bit 5: Unused

Bits 4-3: A Bus Address Step
  00 = Increment/decrement by 1
  01 = Increment/decrement by 2
  10 = Increment/decrement by 4
  11 = Reserved

Bits 2-0: Transfer Mode (0-7)
```

### 4.4 HDMA Operation

HDMA transfers data during H-Blank, allowing per-scanline effects.

**HDMA Table Format:**
```
Byte 0: Line count and repeat flag
  Bit 7: Repeat flag (1 = repeat this entry)
  Bits 6-0: Number of scanlines - 1

Byte 1+: Data bytes (1-4 depending on mode)

$00: End of table
```

**Indirect HDMA:**
- Table contains pointers to data
- Allows longer data sequences
- Uses DASxL/H/B for indirect address

### 4.5 DMA Timing

```
DMA Transfer Cycle:
- 8 master clocks setup per channel
- 8 master clocks per byte transferred

HDMA Transfer Cycle:
- 18 master clocks setup per active channel
- 8 master clocks per byte transferred
- Occurs during H-Blank
```

### 4.6 DMA Register Programming

**Standard DMA:**
```
1. Set DMAPx (transfer mode and direction)
2. Set BBADx (destination PPU register)
3. Set A1TxL/H/B (source address)
4. Set DASxL/H (byte count)
5. Write to MDMAEN ($420B) to start
```

**HDMA:**
```
1. Set DMAPx (transfer mode)
2. Set BBADx (destination PPU register)
3. Set A1TxL/H/B (table start address)
4. Set A2AxL/H (optional: current table address)
5. Write to HDMAEN ($420C) to enable
```

---

## 5. INTERRUPT SYSTEM

### 5.1 Interrupt Types

| Interrupt | Source | Vector | Priority |
|-----------|--------|--------|----------|
| RESET | Hardware | $FFFC-$FFFD | Highest |
| NMI | V-Blank | $FFEA-$FFEB | High |
| IRQ | H-Blank/Timer | $FFEE-$FFEF | Medium |
| ABORT | Cartridge | $FFF8-$FFF9 | Low |
| BRK | Software | $FFE6-$FFE7 | Lowest |
| COP | Software | $FFE4-$FFE5 | Lowest |

### 5.2 NMI (Non-Maskable Interrupt)

**Trigger:** V-Blank start (scanline 224/240 NTSC, 240/288 PAL)

**NMITIMEN Register ($4200):**
```
Bit 7: NMI Enable (1 = enable)
Bit 6: Unused
Bit 5: Auto-Joypad Read Enable
Bit 4: IRQ Enable (H-Blank)
Bit 3: IRQ Enable (V-Blank)
Bit 2-0: Unused
```

**RDNMI Register ($4210):**
```
Bit 7: NMI Flag (1 = NMI occurred)
Bit 6-4: CPU Version
Bit 3-0: Unused

Reading clears bit 7
```

### 5.3 IRQ (Interrupt Request)

**Sources:**
- H-Blank counter match
- V-Blank counter match
- Combined H/V counter match

**HTIME/VTIME Registers:**
```
HTIMEL ($4207): H-count low byte
HTIMEH ($4208): H-count high bit (bit 0)
VTIMEL ($4209): V-count low byte
VTIMEH ($420A): V-count high bit (bit 0)
```

**TIMEUP Register ($4211):**
```
Bit 7: IRQ Flag (1 = IRQ occurred)
Reading clears bit 7
```

### 5.4 Interrupt Timing

**V-Blank Period (NTSC):**
```
Scanlines 224-261 (262 total)
V-Blank duration: 38 scanlines
NMI triggers at start of scanline 224
```

**H-Blank Period:**
```
Cycles 1096-1359 per scanline (NTSC)
H-Blank duration: ~264 cycles
```

### 5.5 Interrupt Vectors

| Vector | Native Mode | Emulation Mode |
|--------|-------------|----------------|
| COP | $FFE4-$FFE5 | $FFF4-$FFF5 |
| BRK | $FFE6-$FFE7 | $FFFE-$FFFF |
| ABORT | $FFE8-$FFE9 | $FFF8-$FFF9 |
| NMI | $FFEA-$FFEB | $FFFA-$FFFB |
| RESET | - | $FFFC-$FFFD |
| IRQ | $FFEE-$FFEF | $FFFE-$FFFF |

---

## 6. CARTRIDGE INTERFACE

### 6.1 Cartridge Connector Pinout (62 pins)

| Pin | Name | Direction | Description |
|-----|------|-----------|-------------|
| 1-24 | A0-A23 | Out | Address bus |
| 25-40 | D0-D7 | Bidir | Data bus |
| 41 | /CART | In | Cartridge select |
| 42 | /RD | Out | Read strobe |
| 43 | /WR | Out | Write strobe |
| 44 | /ROMSEL | Out | ROM select |
| 45 | /RST | Out | System reset |
| 46 | /IRQ | In | Interrupt request |
| 47 | /NMI | In | Non-maskable interrupt |
| 48 | /REFRESH | Out | DRAM refresh |
| 49 | CLK | Out | System clock |
| 50 | /INTRO | In | CIC lockout |
| 51 | /INTCLK | Bidir | CIC clock |
| 52 | /EXPAND | Out | Expansion port enable |
| 53-62 | Various | Mixed | Power, ground, audio |

### 6.2 Memory Mapping Modes

#### Mode 20 - LoROM (SlowROM)
```
ROM Speed: 200ns (3.58MHz access)
Banks: $00-$7D, $80-$FF (upper 32KB)
SRAM: $70-$7D: $0000-$7FFF
Header: $7FB0-$7FFF
```

#### Mode 21 - LoROM (FastROM)
```
ROM Speed: 120ns (3.58MHz access, 0 wait states)
Same layout as Mode 20
Access at $80-$FF banks for fast access
```

#### Mode 25 - HiROM (FastROM)
```
ROM Speed: 120ns
Banks $00-$3F: $8000-$FFFF
Banks $40-$6F: $0000-$FFFF (full 64KB)
Banks $C0-$FF: Mirror with fast access
SRAM: $20-$3F: $6000-$7FFF
Header: $FFB0-$FFFF
```

#### Mode 22 - ExLoROM
```
Extended LoROM
Up to 64MB ROM
Additional banks in $40-$6F
```

#### Mode 23 - ExLoROM (SA-1)
```
Super Accelerator 1 mapper
Enhanced processing capabilities
```

### 6.3 Speed Selection

**MEMSEL Register ($420D):**
```
Bit 0: Memory-2 Wait State Control
  0 = 2.68MHz access (slow, default)
  1 = 3.58MHz access (fast)

Affects banks $80-$BF and $C0-$FF
```

### 6.4 Expansion Pins

| Pin | Function |
|-----|----------|
| /EXPAND | Expansion port chip select |
| /CART | Cartridge presence detect |
| Audio In/Out | Mixed audio from cartridge |

### 6.5 Cartridge Header

**LoROM Header ($7FB0-$7FFF):**
```
$7FB0-$7FB1: Maker code
$7FB2-$7FB3: Game code
$7FB4: Expansion RAM size
$7FB5: Special version
$7FB6: Cartridge type
$7FB7: ROM size
$7FB8: RAM size
$7FB9: Destination code
$7FBA: Version
$7FBB: Complement check
$7FBC: Checksum
$7FBD-$7FBF: Unknown
$7FC0-$7FD4: Game title (21 bytes)
$7FD5: Map mode
$7FD6: Cartridge type
$7FD7: ROM size
$7FD8: RAM size
$7FD9: Destination code
$7FDA: Version
$7FDB: Complement check
$7FDC-$7FDD: Checksum
$7FDE-$7FFF: Reset vector
```

---

## 7. CONTROLLER PORTS

### 7.1 Serial Protocol

The SNES uses a serial communication protocol for controllers.

**Controller Port Registers:**
```
$4016: JOYSER0 - Port 1 data latch
$4017: JOYSER1 - Port 2 data latch

$4201: WRIO - I/O Port Write
  Bit 7: Port 2 /JOY2 output
  Bit 6: Port 1 /JOY1 output

$4213: RDIO - I/O Port Read
  Bit 7: Port 2 data
  Bit 6: Port 1 data
```

### 7.2 Standard Controller Mapping

**Button Order (16-bit serial):**
```
Bit 15: B
Bit 14: Y
Bit 13: Select
Bit 12: Start
Bit 11: Up
Bit 10: Down
Bit 9: Left
Bit 8: Right
Bit 7: A
Bit 6: X
Bit 5: L
Bit 4: R
Bit 3-0: Unused (0)
```

### 7.3 Controller Reading Sequence

```
1. Write $01 to $4016 (latch high)
2. Write $00 to $4016 (latch low)
3. Read $4016/$4017 16 times
   - Each read returns one button state
   - Bit 0 contains button data
```

### 7.4 Auto-Joypad Read

**NMITIMEN Bit 5:**
```
1 = Enable automatic joypad reading during V-Blank

Results stored in:
$4218-$421F: JOY1-JOY4 registers
```

### 7.5 Multitap Support

**Super Multitap (Hudson Soft):**
- Connects to Port 2
- Supports up to 4 additional controllers
- Total: 5 players

**Reading Multitap:**
```
First 16 reads: Controller 1 (Port 1)
Next 16 reads: Controller 2A (Multitap)
Next 16 reads: Controller 2B (Multitap)
Next 16 reads: Controller 2C (Multitap)
Next 16 reads: Controller 2D (Multitap)
```

### 7.6 Other Peripherals

| Device | Port | Protocol |
|--------|------|----------|
| Mouse | 1 or 2 | Serial, 32-bit |
| Super Scope | 2 | Serial, 8-bit |
| Justifier | 2 | Serial, special |
| ASCII Pad | 1 or 2 | Serial, turbo |

---

## 8. TIMING SPECIFICATIONS

### 8.1 NTSC Timing (262 scanlines)

| Parameter | Value |
|-----------|-------|
| Master Clock | 21.477272 MHz |
| CPU Clock | 3.579545 MHz |
| Dot Clock | 5.369318 MHz |
| Horizontal Resolution | 256 or 512 pixels |
| Vertical Resolution | 224 or 239 lines (progressive) |
| Refresh Rate | 60.0988 Hz |

### 8.2 PAL Timing (312 scanlines)

| Parameter | Value |
|-----------|-------|
| Master Clock | 21.281370 MHz |
| CPU Clock | 3.546895 MHz |
| Dot Clock | 5.320342 MHz |
| Horizontal Resolution | 256 or 512 pixels |
| Vertical Resolution | 239 or 287 lines (progressive) |
| Refresh Rate | 50.0070 Hz |

### 8.3 Horizontal Timing (NTSC)

| Period | Dot Cycles | Description |
|--------|------------|-------------|
| H-Blank | 274 cycles | Retrace period |
| Active Display | 1364 cycles | Visible pixels |
| Total | 1364 cycles | One scanline |

**Horizontal Details:**
```
Dots 0-255: BG/sprite fetch
Dots 256-339: H-Blank
Dots 322-337: Sprite fetch for next line
Dots 338-1363: BG fetch for next line
```

### 8.4 Vertical Timing (NTSC)

| Period | Scanlines | Description |
|--------|-----------|-------------|
| Active Display | 224 lines | Visible area |
| V-Blank | 38 lines | Retrace period |
| Total | 262 lines | One frame |

**Vertical Details:**
```
Lines 0-223: Active display
Line 224: NMI triggers (if enabled)
Lines 224-261: V-Blank
Line 262: Pre-render line
```

### 8.5 V-Blank/H-Blank Periods

**V-Blank Duration:**
```
NTSC: 38 scanlines × 1364 dots × 4 master clocks = 207,328 master clocks
      ≈ 9.66ms

PAL: 73 scanlines × 1364 dots × 4 master clocks = 398,288 master clocks
     ≈ 18.71ms
```

**H-Blank Duration:**
```
NTSC: 274 dots × 4 master clocks = 1,096 master clocks
      ≈ 51.1μs
```

### 8.6 DMA Timing

**DMA Transfer Rate:**
```
Setup: 8 master clocks per channel
Transfer: 8 master clocks per byte

Maximum DMA per frame:
NTSC V-Blank: ~25,000 bytes
PAL V-Blank: ~49,000 bytes
```

**HDMA Overhead:**
```
Per active channel: 18 master clocks setup
Per byte: 8 master clocks
Per scanline: ~18-36 master clocks (depending on channels)
```

### 8.7 CPU Cycle Timing

| Operation | Cycles |
|-----------|--------|
| Internal operation | 6-8 master clocks |
| Memory read (slow) | 8 master clocks |
| Memory read (fast) | 6 master clocks |
| Memory write | 8 master clocks |
| DMA transfer | 8 master clocks/byte |
| HDMA transfer | 8 master clocks/byte + 18 setup |

### 8.8 PPU Rendering Pipeline

| Stage | Timing |
|-------|--------|
| BG tile fetch | 4 dots per tile |
| Sprite evaluation | Lines 0-223 |
| Sprite fetch | Dots 322-337 |
| Pixel output | 1 dot per pixel |
| CGRAM access | 1 dot per pixel |

---

## 9. APPENDIX

### 9.1 Register Quick Reference

**PPU1 Registers ($2100-$213F):**
```
$2100: INIDISP  - Display control
$2101: OBSEL    - Object settings
$2102: OAMADDL  - OAM address low
$2103: OAMADDH  - OAM address high
$2104: OAMDATA  - OAM data write
$2105: BGMODE   - BG mode
$2106: MOSAIC   - Mosaic effect
$2107-$210A: BGxSC - BG tilemap address
$210B-$210C: BGxxNBA - BG character address
$210D-$2114: BGxHOFS/BGxVOFS - BG scroll
$2115: VMAIN    - VRAM port control
$2116-$2117: VMADD - VRAM address
$2118-$2119: VMDATA - VRAM data
$211A-$2120: M7x - Mode 7 registers
```

**PPU2 Registers ($2121-$213F):**
```
$2121: CGADD    - CGRAM address
$2122: CGDATA   - CGRAM data
$2123-$2129: WxSEL/WHx - Window registers
$212A-$212B: WxLOG - Window logic
$212C-$212D: TM/TS - Screen designation
$212E-$212F: TMxW - Window mask
$2130-$2132: CGWxSEL/CGxADSUB/COLDATA - Color math
$2133: SETINI   - Display control 2
$2134-$2136: MPYx - Multiply result
$2137: SLHV     - Latch H/V counter
$2138: RDOAM    - OAM read
$2139-$213A: RDVRAMx - VRAM read
$213B: RDCGRAM  - CGRAM read
$213C-$213D: OPxCT - Counter read
$213E-$213F: STATxx - Status registers
```

### 9.2 Common Memory Locations

```
$7E0000-$7E1FFF: WRAM Low (mirror of $0000-$1FFF)
$7E2000-$7EFFFF: WRAM continuation
$7F0000-$7FFFFF: WRAM High

$8000-$FFFF in banks $00-$7D: LoROM
$0000-$FFFF in banks $40-$6F: HiROM
```

### 9.3 Interrupt Summary

| Interrupt | Enable | Flag | Vector |
|-----------|--------|------|--------|
| NMI | $4200.7 | $4210.7 | $FFEA |
| H-IRQ | $4200.4 | $4211.7 | $FFEE |
| V-IRQ | $4200.5 | $4211.7 | $FFEE |
| HV-IRQ | $4200.4+5 | $4211.7 | $FFEE |

---

## Document Information

**Version:** 1.0  
**Last Updated:** 2024  
**Purpose:** Technical reference for SNES emulator development and hardware analysis  
**Target Audience:** Emulator developers, hardware hackers, retro gaming enthusiasts

---

*This document provides comprehensive technical specifications for the Super Nintendo Entertainment System. All information is compiled from publicly available technical documentation and reverse engineering efforts for educational and development purposes.*
