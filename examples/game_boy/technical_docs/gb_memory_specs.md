# GameBoy Memory System Technical Specifications
## DMG (Original GameBoy) & CGB (GameBoy Color)

---

## 1. MEMORY MAP OVERVIEW

### 1.1 Complete 64KB Address Space

The GameBoy CPU (Sharp LR35902, a Z80 derivative) has a 16-bit address bus, providing a 64KB address space (0x0000-0xFFFF).

```
┌─────────────────────────────────────────────────────────────────┐
│                    GAMEBOY MEMORY MAP                           │
├─────────────────────────────────────────────────────────────────┤
│  0xFFFF  │  Interrupt Enable Register (IE)                     │
│  0xFF80  │  High RAM (HRAM) - 127 bytes                        │
│  0xFF00  │  I/O Registers - 128 bytes                          │
│  0xFEA0  │  Not Usable (read returns $FF)                      │
│  0xFE00  │  OAM (Object Attribute Memory) - 160 bytes          │
│  0xE000  │  Echo RAM (mirror of 0xC000-0xDDFF)                 │
│  0xD000  │  WRAM Bank 1 (CGB) / WRAM continuation (DMG)        │
│  0xC000  │  WRAM Bank 0 - 4KB fixed                            │
│  0xA000  │  Cartridge RAM (if present) - 8KB or banked         │
│  0x9FFF  │  VRAM (Video RAM) - 8KB                             │
│  0x8000  │  VRAM Start                                         │
│  0x7FFF  │  Cartridge ROM - Switchable Bank                    │
│  0x4000  │  Cartridge ROM - Bank 0 (fixed 16KB)                │
│  0x0000  │  Cartridge ROM / Boot ROM (first 256 bytes at boot) │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Detailed Address Space Table

| Address Range | Size | Description | Access |
|--------------|------|-------------|--------|
| 0x0000-0x3FFF | 16KB | ROM Bank 0 (fixed) | Read Only |
| 0x4000-0x7FFF | 16KB | ROM Bank N (switchable) | Read Only |
| 0x8000-0x9FFF | 8KB | Video RAM (VRAM) | Read/Write |
| 0xA000-0xBFFF | 8KB | External RAM (Cartridge) | Read/Write |
| 0xC000-0xCFFF | 4KB | Work RAM Bank 0 (fixed) | Read/Write |
| 0xD000-0xDFFF | 4KB | Work RAM Bank 1 (DMG) / Bank N (CGB) | Read/Write |
| 0xE000-0xFDFF | 7.68KB | Echo RAM (mirror of 0xC000-0xDDFF) | Read/Write |
| 0xFE00-0xFE9F | 160B | OAM (Sprite Attribute Table) | Read/Write |
| 0xFEA0-0xFEFF | 96B | Not Usable | - |
| 0xFF00-0xFF7F | 128B | I/O Registers | Read/Write |
| 0xFF80-0xFFFE | 127B | High RAM (HRAM/Stack) | Read/Write |
| 0xFFFF | 1B | Interrupt Enable Register | Read/Write |

---

## 2. CARTRIDGE MEMORY

### 2.1 ROM Sizes and Banking

| ROM Size Code | Size | Number of Banks | Notes |
|--------------|------|-----------------|-------|
| 0x00 | 32KB | 2 (0-1) | No banking needed |
| 0x01 | 64KB | 4 (0-3) | MBC required |
| 0x02 | 128KB | 8 (0-7) | MBC required |
| 0x03 | 256KB | 16 (0-15) | MBC required |
| 0x04 | 512KB | 32 (0-31) | MBC required |
| 0x05 | 1MB | 64 (0-63) | MBC1/MBC3/MBC5 |
| 0x06 | 2MB | 128 (0-127) | MBC1/MBC3/MBC5 |
| 0x07 | 4MB | 256 (0-255) | MBC5 only |
| 0x08 | 8MB | 512 (0-511) | MBC5 only |

### 2.2 MBC (Memory Bank Controller) Types

#### MBC1 (Max 2MB ROM, 32KB RAM)
```
┌─────────────────────────────────────────────────────────────┐
│ MBC1 REGISTER MAP                                           │
├─────────────────────────────────────────────────────────────┤
│ 0x0000-0x1FFF │ RAM Enable (write 0x0A to enable)           │
│ 0x2000-0x3FFF │ ROM Bank Number (lower 5 bits, 0→1)         │
│ 0x4000-0x5FFF │ RAM Bank Number OR Upper ROM Bank bits      │
│ 0x6000-0x7FFF │ Banking Mode Select (0=ROM16M/RAM8K, 1=ROM4M/RAM32K) │
└─────────────────────────────────────────────────────────────┘
```
- **ROM Banking**: Supports up to 125 banks (banks 0x00, 0x20, 0x40, 0x60 are inaccessible)
- **RAM Banking**: Up to 4 banks (32KB total) in mode 1
- **Mode 0**: 16MBit ROM / 8KB RAM (default)
- **Mode 1**: 4MBit ROM / 32KB RAM

#### MBC2 (Max 256KB ROM, 512x4bits RAM)
```
┌─────────────────────────────────────────────────────────────┐
│ MBC2 REGISTER MAP                                           │
├─────────────────────────────────────────────────────────────┤
│ 0x0000-0x3FFF │ ROM Bank Number (bit 8 selects function)    │
│               │ bit 8 = 0: RAM Enable / ROM Bank (lower 4)  │
│               │ bit 8 = 1: ROM Bank (lower 4) only          │
└─────────────────────────────────────────────────────────────┘
```
- Built-in 512x4bit RAM (only lower 4 bits of each byte used)
- Maximum 16 ROM banks (256KB)

#### MBC3 (Max 2MB ROM, 32KB RAM + RTC)
```
┌─────────────────────────────────────────────────────────────┐
│ MBC3 REGISTER MAP                                           │
├─────────────────────────────────────────────────────────────┤
│ 0x0000-0x1FFF │ RAM Enable / RTC Register Select            │
│ 0x2000-0x3FFF │ ROM Bank Number (0→1, 7 bits = 0-127)       │
│ 0x4000-0x5FFF │ RAM Bank Number (0-3) OR RTC Register Select│
│ 0x6000-0x7FFF │ RTC Latch (write 0 then 1 to latch)         │
└─────────────────────────────────────────────────────────────┘
```
- **RTC Registers** (when RAM bank = 0x08-0x0C):
  - 0x08: Seconds (0-59)
  - 0x09: Minutes (0-59)
  - 0x0A: Hours (0-23)
  - 0x0B: Day Counter Lower 8 bits
  - 0x0C: Day Counter Upper 1 bit + Carry + Halt flag

#### MBC5 (Max 8MB ROM, 128KB RAM + Rumble)
```
┌─────────────────────────────────────────────────────────────┐
│ MBC5 REGISTER MAP                                           │
├─────────────────────────────────────────────────────────────┤
│ 0x0000-0x1FFF │ RAM Enable (write 0x0A to enable)           │
│ 0x2000-0x2FFF │ ROM Bank Number Lower 8 bits (0-255)        │
│ 0x3000-0x3FFF │ ROM Bank Number bit 8 (0-1, total 0-511)    │
│ 0x4000-0x5FFF │ RAM Bank Number (0-15) + Rumble (bit 3)     │
└─────────────────────────────────────────────────────────────┘
```
- **Rumble**: Bit 3 of RAM bank register controls motor (0=off, 1=on)
- Full 9-bit ROM bank selection (512 banks = 8MB)
- 4-bit RAM bank selection (16 banks = 128KB)

#### MBC6 (Max 8MB ROM, 32KB RAM)
- Features FLASH memory for ROM
- Split ROM into two 1MB regions with independent banking
- Rarely used (only "Net de Get: Minigame @ 100" known)

#### MBC7 (Max 8MB ROM, 256KB RAM + Accelerometer)
- Includes accelerometer for tilt controls
- 256 bytes of EEPROM
- Used in "Kirby Tilt 'n' Tumble"

#### MMM01 (Multi Memory Menu)
- Used for multi-game cartridges
- Complex banking for menu selection

### 2.3 RAM Sizes and Banking

| RAM Size Code | Size | Banks | MBC Support |
|--------------|------|-------|-------------|
| 0x00 | None | 0 | All |
| 0x01 | 2KB | Partial | MBC2 only |
| 0x02 | 8KB | 1 | All |
| 0x03 | 32KB | 4 | MBC1, MBC3, MBC5 |
| 0x04 | 128KB | 16 | MBC5 only |
| 0x05 | 64KB | 8 | MBC5 only |

### 2.4 Cartridge Header (0x0100-0x014F)

| Address | Size | Description |
|---------|------|-------------|
| 0x0100-0x0103 | 4B | Entry Point (NOP; JP 0x0150) |
| 0x0104-0x0133 | 48B | Nintendo Logo |
| 0x0134-0x0143 | 16B | Game Title |
| 0x013F-0x0142 | 4B | Manufacturer Code (CGB) |
| 0x0143 | 1B | CGB Flag (0x80=CGB+DMG, 0xC0=CGB only) |
| 0x0144-0x0145 | 2B | New Licensee Code |
| 0x0146 | 1B | SGB Flag (0x03=SGB support) |
| 0x0147 | 1B | Cartridge Type (MBC type) |
| 0x0148 | 1B | ROM Size |
| 0x0149 | 1B | RAM Size |
| 0x014A | 1B | Destination Code |
| 0x014B | 1B | Old Licensee Code |
| 0x014C | 1B | Mask ROM Version |
| 0x014D | 1B | Header Checksum |
| 0x014E-0x014F | 2B | Global Checksum |

### 2.5 Cartridge Type Values (0x0147)

| Value | Type | Description |
|-------|------|-------------|
| 0x00 | ROM ONLY | No MBC |
| 0x01 | MBC1 | MBC1 only |
| 0x02 | MBC1+RAM | MBC1 + RAM |
| 0x03 | MBC1+RAM+BATT | MBC1 + RAM + Battery |
| 0x05 | MBC2 | MBC2 |
| 0x06 | MBC2+BATTERY | MBC2 + Battery |
| 0x08 | ROM+RAM | No MBC + RAM |
| 0x09 | ROM+RAM+BATTERY | No MBC + RAM + Battery |
| 0x0B | MMM01 | MMM01 |
| 0x0C | MMM01+RAM | MMM01 + RAM |
| 0x0D | MMM01+RAM+BATT | MMM01 + RAM + Battery |
| 0x0F | MBC3+TIMER+BATT | MBC3 + RTC + Battery |
| 0x10 | MBC3+TIMER+RAM+BATT | MBC3 + RTC + RAM + Battery |
| 0x11 | MBC3 | MBC3 only |
| 0x12 | MBC3+RAM | MBC3 + RAM |
| 0x13 | MBC3+RAM+BATTERY | MBC3 + RAM + Battery |
| 0x19 | MBC5 | MBC5 only |
| 0x1A | MBC5+RAM | MBC5 + RAM |
| 0x1B | MBC5+RAM+BATTERY | MBC5 + RAM + Battery |
| 0x1C | MBC5+RUMBLE | MBC5 + Rumble |
| 0x1D | MBC5+RUMBLE+RAM | MBC5 + Rumble + RAM |
| 0x1E | MBC5+RUMBLE+RAM+BATT | MBC5 + Rumble + RAM + Battery |
| 0x20 | MBC6 | MBC6 |
| 0x22 | MBC7+SENSOR+RUMBLE+RAM+BATT | MBC7 + Accelerometer |

---

## 3. VRAM (VIDEO RAM)

### 3.1 VRAM Organization (0x8000-0x9FFF)

```
┌─────────────────────────────────────────────────────────────────┐
│                     VRAM LAYOUT                                 │
├─────────────────────────────────────────────────────────────────┤
│  0x9FFF                                                         │
│  0x9C00  │  BG Map 2 (32x32 tiles)                              │
│  0x9800  │  BG Map 1 (32x32 tiles)                              │
│  0x9000  │  Tile Data Block 2 (128 tiles, signed index -128..127)│
│  0x8800  │  Tile Data Block 1 (256 tiles)                       │
│  0x8000  │  Tile Data Block 0 (128 tiles) + OBJ tiles           │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 VRAM Bank Switching (CGB Only)

```
┌─────────────────────────────────────────────────────────────────┐
│ VBK - VRAM Bank Register (0xFF4F)                               │
├─────────────────────────────────────────────────────────────────┤
│  Bit 0: VRAM Bank Select (0=Bank 0, 1=Bank 1)                   │
│  Bits 1-7: Unused (read as 1s on CGB)                           │
└─────────────────────────────────────────────────────────────────┘
```

**CGB VRAM Bank Usage:**
- **Bank 0**: Standard tile data, tile maps, OAM data
- **Bank 1**: Additional tile data (0x8000-0x97FF), BG Attribute Map (0x9800-0x9FFF)

### 3.3 BG Attribute Map (CGB Bank 1, 0x9800-0x9FFF)

| Bit | Function |
|-----|----------|
| 0-2 | Background Palette Number (0-7) |
| 3 | Tile VRAM Bank (0=Bank 0, 1=Bank 1) |
| 4 | Not used |
| 5 | Horizontal Flip |
| 6 | Vertical Flip |
| 7 | BG-to-OAM Priority |

### 3.4 Tile Data Format

Each 8x8 tile = 16 bytes (2 bytes per row)
```
Byte 0: Low bits of pixel row 0
Byte 1: High bits of pixel row 0
Byte 2: Low bits of pixel row 1
Byte 3: High bits of pixel row 1
...
Byte 14: Low bits of pixel row 7
Byte 15: High bits of pixel row 7
```

Pixel color = (high_bit << 1) | low_bit (0-3, index into palette)

---

## 4. WRAM (WORK RAM)

### 4.1 DMG WRAM (8KB)

```
┌─────────────────────────────────────────────────────────────────┐
│ DMG WRAM LAYOUT                                                 │
├─────────────────────────────────────────────────────────────────┤
│  0xDFFF                                                         │
│  0xD000  │  WRAM Bank 1 (4KB) - Fixed                           │
│  0xCFFF                                                         │
│  0xC000  │  WRAM Bank 0 (4KB) - Fixed                           │
└─────────────────────────────────────────────────────────────────┘
Total: 8KB (0xC000-0xDFFF)
```

### 4.2 CGB WRAM (32KB with Banking)

```
┌─────────────────────────────────────────────────────────────────┐
│ CGB WRAM LAYOUT                                                 │
├─────────────────────────────────────────────────────────────────┤
│  0xDFFF                                                         │
│  0xD000  │  WRAM Bank 1-7 (4KB each, switchable)                │
│  0xCFFF                                                         │
│  0xC000  │  WRAM Bank 0 (4KB) - Fixed                           │
└─────────────────────────────────────────────────────────────────┘
Total: 32KB (8 banks x 4KB)
```

### 4.3 SVBK - WRAM Bank Register (CGB Only, 0xFF70)

```
┌─────────────────────────────────────────────────────────────────┐
│ SVBK - WRAM Bank Register (0xFF70)                              │
├─────────────────────────────────────────────────────────────────┤
│  Bits 0-2: WRAM Bank Select                                     │
│            0 → Bank 1 (for compatibility)                       │
│            1-7 → Select banks 1-7                               │
│  Bits 3-7: Unused (read as 1s)                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Note**: Writing 0 to SVBK selects bank 1 (not bank 0), ensuring compatibility with DMG code.

### 4.4 Echo RAM Behavior

```
┌─────────────────────────────────────────────────────────────────┐
│ ECHO RAM (0xE000-0xFDFF)                                        │
├─────────────────────────────────────────────────────────────────┤
│  0xFDFF                                                         │
│  0xE000  │  Echo of 0xC000-0xDDFF                               │
└─────────────────────────────────────────────────────────────────┘
```

- **Address Range**: 0xE000-0xFDFF mirrors 0xC000-0xDDFF
- **Size**: 7.68KB (0xE000-0xFDFF = 0x1E00 bytes)
- **Behavior**: Writing to Echo RAM also writes to corresponding WRAM location
- **CGB Note**: Echo RAM only echoes Bank 0 of WRAM, regardless of SVBK setting
- **Usage**: Often used for stack or temporary storage

---

## 5. OAM (OBJECT ATTRIBUTE MEMORY)

### 5.1 OAM Structure (0xFE00-0xFE9F)

```
┌─────────────────────────────────────────────────────────────────┐
│ OAM LAYOUT (160 bytes = 40 sprites x 4 bytes)                   │
├─────────────────────────────────────────────────────────────────┤
│  0xFE9F                                                         │
│  0xFE00  │  Sprite 0: Y, X, Tile, Flags                         │
│          │  Sprite 1: Y, X, Tile, Flags                         │
│          │  ...                                                 │
│          │  Sprite 39: Y, X, Tile, Flags                        │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Sprite Attribute Format (4 bytes each)

| Byte | Name | Description |
|------|------|-------------|
| 0 | Y Position | Screen Y + 16 (so Y=0 is off-screen top) |
| 1 | X Position | Screen X + 8 (so X=0 is off-screen left) |
| 2 | Tile Number | Tile index in VRAM (0-255) |
| 3 | Flags | Priority, flip, palette |

### 5.3 Sprite Flags (Byte 3)

| Bit | Name | Description |
|-----|------|-------------|
| 7 | Priority | 0=OBJ above BG, 1=OBJ behind BG color 1-3 |
| 6 | Y Flip | 1=Flip vertically |
| 5 | X Flip | 1=Flip horizontally |
| 4 | DMG Palette | 0=OBP0, 1=OBP1 (DMG only) |
| 3 | VRAM Bank | 0=Bank 0, 1=Bank 1 (CGB only) |
| 2-0 | CGB Palette | Palette number 0-7 (CGB only) |

### 5.4 DMA Transfer (0xFF46)

```
┌─────────────────────────────────────────────────────────────────┐
│ DMA - OAM DMA Transfer Register (0xFF46)                        │
├─────────────────────────────────────────────────────────────────┤
│  Write: Source address high byte (transfers from XX00-XX9F)      │
│  Transfer: 160 bytes from XX00-XX9F to FE00-FE9F                │
│  Duration: 160 M-cycles (approximately 640 T-cycles)            │
│  CPU: Only HRAM accessible during transfer                      │
└─────────────────────────────────────────────────────────────────┘
```

**DMA Transfer Procedure:**
```asm
; Typical DMA routine placed in HRAM
DMA_ROUTINE:
    ld a, $C0       ; Source: $C000
    ldh [$FF46], a  ; Start DMA
    ld a, $28       ; Wait 160 cycles (40 iterations)
.wait:
    dec a
    jr nz, .wait
    ret
```

### 5.5 HDMA (CGB Only, 0xFF51-0xFF55)

```
┌─────────────────────────────────────────────────────────────────┐
│ HDMA REGISTERS (CGB Only)                                       │
├─────────────────────────────────────────────────────────────────┤
│  0xFF51  │ HDMA1 - Source High (bits 8-15)                      │
│  0xFF52  │ HDMA2 - Source Low (bits 0-7, lower 4 bits ignored)  │
│  0xFF53  │ HDMA3 - Destination High (bits 8-15, in VRAM)        │
│  0xFF54  │ HDMA4 - Destination Low (bits 0-7, lower 4 ignored)  │
│  0xFF55  │ HDMA5 - Length/Mode/Start                            │
└─────────────────────────────────────────────────────────────────┘
```

**HDMA5 Register Format:**
| Bit | Function |
|-----|----------|
| 7 | Mode (0=General DMA, 1=H-Blank DMA) |
| 6-0 | Length / Remaining blocks |

**General DMA (Mode 0):**
- Transfer completes immediately
- CPU halted during transfer
- Length = ((value & 0x7F) + 1) * 16 bytes
- HDMA5 reads as 0xFF during transfer

**H-Blank DMA (Mode 1):**
- Transfer occurs during H-Blank periods
- 16 bytes transferred per H-Blank
- Length = ((value & 0x7F) + 1) * 16 bytes initially
- HDMA5 decrements after each block, bit 7 stays 1
- Write bit 7 = 0 to cancel

---

## 6. I/O REGISTERS

### 6.1 I/O Register Map (0xFF00-0xFF7F)

```
┌─────────────────────────────────────────────────────────────────┐
│ I/O REGISTER MAP                                                │
├─────────────────────────────────────────────────────────────────┤
│ 0xFF00 │ P1/JOYP   │ Joypad Input                               │
│ 0xFF01 │ SB        │ Serial Transfer Data                       │
│ 0xFF02 │ SC        │ Serial Transfer Control                    │
│ 0xFF04 │ DIV       │ Divider Register                           │
│ 0xFF05 │ TIMA      │ Timer Counter                              │
│ 0xFF06 │ TMA       │ Timer Modulo                               │
│ 0xFF07 │ TAC       │ Timer Control                              │
│ 0xFF0F │ IF        │ Interrupt Flag                             │
│ 0xFF10 │ NR10      │ Sound Channel 1 Sweep                      │
│ 0xFF11 │ NR11      │ Sound Channel 1 Length/Wave                │
│ 0xFF12 │ NR12      │ Sound Channel 1 Envelope                   │
│ 0xFF13 │ NR13      │ Sound Channel 1 Frequency Low              │
│ 0xFF14 │ NR14      │ Sound Channel 1 Frequency High             │
│ 0xFF16 │ NR21      │ Sound Channel 2 Length/Wave                │
│ 0xFF17 │ NR22      │ Sound Channel 2 Envelope                   │
│ 0xFF18 │ NR23      │ Sound Channel 2 Frequency Low              │
│ 0xFF19 │ NR24      │ Sound Channel 2 Frequency High             │
│ 0xFF1A │ NR30      │ Sound Channel 3 Enable                     │
│ 0xFF1B │ NR31      │ Sound Channel 3 Length                     │
│ 0xFF1C │ NR32      │ Sound Channel 3 Output Level               │
│ 0xFF1D │ NR33      │ Sound Channel 3 Frequency Low              │
│ 0xFF1E │ NR34      │ Sound Channel 3 Frequency High             │
│ 0xFF20 │ NR41      │ Sound Channel 4 Length                     │
│ 0xFF21 │ NR42      │ Sound Channel 4 Envelope                   │
│ 0xFF22 │ NR43      │ Sound Channel 4 Polynomial                 │
│ 0xFF23 │ NR44      │ Sound Channel 4 Counter                    │
│ 0xFF24 │ NR50      │ Master Volume/VIN                          │
│ 0xFF25 │ NR51      │ Sound Panning                              │
│ 0xFF26 │ NR52      │ Sound Enable                               │
│ 0xFF30-│ Wave RAM  │ Channel 3 Wave Pattern RAM                 │
│ 0xFF3F │           │                                            │
│ 0xFF40 │ LCDC      │ LCD Control                                │
│ 0xFF41 │ STAT      │ LCD Status                                 │
│ 0xFF42 │ SCY       │ Scroll Y                                   │
│ 0xFF43 │ SCX       │ Scroll X                                   │
│ 0xFF44 │ LY        │ LCD Y-Coordinate                           │
│ 0xFF45 │ LYC       │ LY Compare                                 │
│ 0xFF46 │ DMA       │ OAM DMA Transfer                           │
│ 0xFF47 │ BGP       │ BG Palette Data (DMG)                      │
│ 0xFF48 │ OBP0      │ OBJ Palette 0 Data (DMG)                   │
│ 0xFF49 │ OBP1      │ OBJ Palette 1 Data (DMG)                   │
│ 0xFF4A │ WY        │ Window Y Position                          │
│ 0xFF4B │ WX        │ Window X Position                          │
│ 0xFF4D │ KEY1      │ CPU Speed Switch (CGB)                     │
│ 0xFF4F │ VBK       │ VRAM Bank (CGB)                            │
│ 0xFF51 │ HDMA1     │ HDMA Source High (CGB)                     │
│ 0xFF52 │ HDMA2     │ HDMA Source Low (CGB)                      │
│ 0xFF53 │ HDMA3     │ HDMA Dest High (CGB)                       │
│ 0xFF54 │ HDMA4     │ HDMA Dest Low (CGB)                        │
│ 0xFF55 │ HDMA5     │ HDMA Length/Mode (CGB)                     │
│ 0xFF56 │ RP        │ Infrared Port (CGB)                        │
│ 0xFF68 │ BCPS/BGPI │ BG Palette Index (CGB)                     │
│ 0xFF69 │ BCPD/BGPD │ BG Palette Data (CGB)                      │
│ 0xFF6A │ OCPS/OBPI │ OBJ Palette Index (CGB)                    │
│ 0xFF6B │ OCPD/OBPD │ OBJ Palette Data (CGB)                     │
│ 0xFF6C │ OPRI      │ Object Priority Mode (CGB)                 │
│ 0xFF70 │ SVBK      │ WRAM Bank (CGB)                            │
│ 0xFF76 │ PCM12     │ PCM Amplitude 1&2 (CGB, read-only)         │
│ 0xFF77 │ PCM34     │ PCM Amplitude 3&4 (CGB, read-only)         │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Key Registers Detail

#### P1/JOYP - Joypad (0xFF00)
| Bit | Function |
|-----|----------|
| 7-6 | Not used |
| 5 | Select Action buttons (0=select) |
| 4 | Select Direction buttons (0=select) |
| 3 | Down / Start (0=pressed) |
| 2 | Up / Select (0=pressed) |
| 1 | Left / B (0=pressed) |
| 0 | Right / A (0=pressed) |

#### LCDC - LCD Control (0xFF40)
| Bit | Name | Function |
|-----|------|----------|
| 7 | LCD Enable | 1=Display on |
| 6 | Window Tile Map | 0=0x9800-0x9BFF, 1=0x9C00-0x9FFF |
| 5 | Window Enable | 1=Window on |
| 4 | BG/Window Tile Data | 0=0x8800-0x97FF, 1=0x8000-0x8FFF |
| 3 | BG Tile Map | 0=0x9800-0x9BFF, 1=0x9C00-0x9FFF |
| 2 | OBJ Size | 0=8x8, 1=8x16 |
| 1 | OBJ Enable | 1=Sprites on |
| 0 | BG/Window Enable | 1=BG and Window on (DMG), priority (CGB) |

#### STAT - LCD Status (0xFF41)
| Bit | Name | Function |
|-----|------|----------|
| 7 | Unused | Read as 1 |
| 6 | LYC=LY Interrupt | Enable LYC=LY interrupt |
| 5 | Mode 2 Interrupt | Enable OAM interrupt |
| 4 | Mode 1 Interrupt | Enable V-Blank interrupt |
| 3 | Mode 0 Interrupt | Enable H-Blank interrupt |
| 2 | LYC=LY Flag | 1=LYC equals LY |
| 1-0 | Mode Flag | 0=H-Blank, 1=V-Blank, 2=OAM, 3=Transfer |

#### Timer Registers
| Register | Address | Function |
|----------|---------|----------|
| DIV | 0xFF04 | Divider - increments at 16384Hz, any write resets to 0 |
| TIMA | 0xFF05 | Timer counter - increments at selected rate |
| TMA | 0xFF06 | Timer modulo - loaded into TIMA on overflow |
| TAC | 0xFF07 | Timer control |

**TAC Register:**
| Bit | Function |
|-----|----------|
| 2 | Timer Enable (1=on) |
| 1-0 | Clock Select: 00=4096Hz, 01=262144Hz, 10=65536Hz, 11=16384Hz |

#### Interrupt Registers
| Register | Address | Function |
|----------|---------|----------|
| IF | 0xFF0F | Interrupt Flag (bits 0-4) |
| IE | 0xFFFF | Interrupt Enable (bits 0-4) |

**Interrupt Bits:**
| Bit | Source |
|-----|--------|
| 0 | V-Blank |
| 1 | LCD STAT |
| 2 | Timer |
| 3 | Serial |
| 4 | Joypad |

---

## 7. BOOT ROM

### 7.1 DMG Boot ROM (256 bytes)

```
┌─────────────────────────────────────────────────────────────────┐
│ DMG BOOT ROM (256 bytes at 0x0000-0x00FF at boot)               │
├─────────────────────────────────────────────────────────────────┤
│  Size: 256 bytes (0x100)                                        │
│  Location: Mapped to 0x0000-0x00FF at power-on                  │
│  Unmapped: After execution, or by writing to any address        │
└─────────────────────────────────────────────────────────────────┘
```

**DMG Boot ROM Functions:**
1. Initialize stack pointer to 0xFFFE
2. Initialize audio registers
3. Load and scroll Nintendo logo
4. Compare cartridge logo with internal logo
5. Calculate header checksum (0x0134-0x014D)
6. If valid, unmap boot ROM and jump to 0x0100
7. If invalid, lock up (infinite loop)

### 7.2 CGB Boot ROM (2048 bytes)

```
┌─────────────────────────────────────────────────────────────────┐
│ CGB BOOT ROM (2048 bytes, banked)                               │
├─────────────────────────────────────────────────────────────────┤
│  Size: 2048 bytes total                                         │
│  Bank 0: 256 bytes (0x0000-0x00FF) - Logo & initial setup       │
│  Bank 1: 1792 bytes (0x0200-0x08FF) - Color palettes, checks    │
│                                                                   │
│  Banking: Controlled by writing to 0xFF50                       │
│  0xFF50 = 0x00: Boot ROM mapped                                 │
│  0xFF50 = 0x01: Boot ROM unmapped, cartridge ROM visible        │
└─────────────────────────────────────────────────────────────────┘
```

**CGB Boot ROM Functions:**
1. Initialize hardware (stack, audio, video)
2. Load and display color Nintendo logo
3. Verify cartridge logo
4. Determine palette based on game title
5. Check CGB compatibility byte (0x0143)
6. Initialize CGB-specific registers
7. Unmap boot ROM and jump to 0x0100

### 7.3 Nintendo Logo Check

```
┌─────────────────────────────────────────────────────────────────┐
│ NINTENDO LOGO DATA                                              │
├─────────────────────────────────────────────────────────────────┤
│  Location: 0x0104-0x0133 in cartridge header (48 bytes)         │
│  Stored: Compressed bitmap data                                   │
│                                                                   │
│  DMG Logo: Black and white, scrolled down                       │
│  CGB Logo: Color, with registered trademark symbol              │
│                                                                   │
│  Checksum: The logo data is included in header checksum         │
│  Anti-piracy: Boot ROM compares logo against internal copy      │
└─────────────────────────────────────────────────────────────────┘
```

**Logo Data (Hex):**
```
CE ED 66 66 CC 0D 00 0B 03 73 00 83 00 0C 00 0D
00 08 11 1F 88 89 00 0E DC CC 6E E6 DD DD D9 99
BB BB 67 63 6E 0E EC CC DD DC 99 9F BB B9 33 3E
```

---

## 8. DMG vs CGB DIFFERENCES

### 8.1 Memory Comparison Summary

| Feature | DMG | CGB |
|---------|-----|-----|
| **ROM Space** | 32KB-2MB | 32KB-8MB |
| **WRAM** | 8KB (2 banks) | 32KB (8 banks) |
| **VRAM** | 8KB (1 bank) | 16KB (2 banks) |
| **Cartridge RAM** | Up to 32KB | Up to 128KB |
| **DMA** | OAM DMA only | OAM DMA + HDMA |
| **Boot ROM** | 256 bytes | 256 + 1792 bytes |
| **Palettes** | 4 shades gray | 32768 colors |

### 8.2 WRAM Banking Differences

```
┌─────────────────────────────────────────────────────────────────┐
│ WRAM COMPARISON                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  DMG:                          CGB:                             │
│  ┌──────────────┐              ┌──────────────┐                 │
│  │ 0xDFFF       │              │ 0xDFFF       │                 │
│  │ 0xD000 Bank1 │              │ 0xD000 Bank1 │ ← SVBK=1        │
│  │ 0xCFFF       │              │ 0xD000 Bank2 │ ← SVBK=2        │
│  │ 0xC000 Bank0 │              │ 0xD000 Bank3 │ ← SVBK=3        │
│  └──────────────┘              │ 0xD000 Bank4 │ ← SVBK=4        │
│                                │ 0xD000 Bank5 │ ← SVBK=5        │
│  Total: 8KB                    │ 0xD000 Bank6 │ ← SVBK=6        │
│                                │ 0xD000 Bank7 │ ← SVBK=7        │
│                                │ 0xCFFF       │                 │
│                                │ 0xC000 Bank0 │ ← Fixed         │
│                                └──────────────┘                 │
│                                                                   │
│                                Total: 32KB                      │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 VRAM Banking Differences

```
┌─────────────────────────────────────────────────────────────────┐
│ VRAM COMPARISON                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  DMG (8KB):                    CGB (16KB):                      │
│  ┌──────────────┐              ┌──────────────┐                 │
│  │ 0x9FFF       │              │ 0x9FFF       │                 │
│  │ 0x9C00 BGMap2│              │ 0x9C00 BGMap2│                 │
│  │ 0x9800 BGMap1│              │ 0x9800 BGMap1│                 │
│  │ 0x9000 Tiles │              │ 0x9000 Tiles │                 │
│  │ 0x8000 Tiles │              │ 0x8000 Tiles │                 │
│  └──────────────┘              └──────────────┘                 │
│                                                                   │
│                                Bank 1 (VBK=1):                  │
│                                ┌──────────────┐                 │
│                                │ 0x9FFF       │                 │
│                                │ 0x9800 Attr  │ BG Attributes   │
│                                │ 0x8000 Tiles │ Extra tiles     │
│                                └──────────────┘                 │
│                                                                   │
│  Register: None                Register: 0xFF4F (VBK)           │
└─────────────────────────────────────────────────────────────────┘
```

### 8.4 HDMA (CGB Only)

```
┌─────────────────────────────────────────────────────────────────┐
│ HDMA TRANSFER MODES                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  GENERAL DMA (Mode 0):           H-BLANK DMA (Mode 1):          │
│  ┌─────────────────────┐         ┌─────────────────────┐        │
│  │ Immediate transfer  │         │ Transfer during     │        │
│  │ CPU halted          │         │ H-Blank periods     │        │
│  │ 16-2048 bytes       │         │ 16 bytes per line   │        │
│  │ ~8 cycles/byte      │         │ CPU continues       │        │
│  │                     │         │ Up to 2048 bytes    │        │
│  │ ████████████████    │         │ ██  ██  ██  ██      │        │
│  │ (single block)      │         │ (spread across      │        │
│  └─────────────────────┘         │  multiple frames)   │        │
│                                  └─────────────────────┘        │
│                                                                   │
│  Registers: 0xFF51-0xFF55                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 8.5 CGB-Only Registers Summary

| Register | Address | Function |
|----------|---------|----------|
| KEY1 | 0xFF4D | CPU Speed Switch (single/double speed) |
| VBK | 0xFF4F | VRAM Bank Select |
| HDMA1-5 | 0xFF51-0xFF55 | Horizontal DMA |
| RP | 0xFF56 | Infrared Communication Port |
| BCPS/BGPI | 0xFF68 | Background Palette Index |
| BCPD/BGPD | 0xFF69 | Background Palette Data |
| OCPS/OBPI | 0xFF6A | Object Palette Index |
| OCPD/OBPD | 0xFF6B | Object Palette Data |
| OPRI | 0xFF6C | Object Priority Mode |
| SVBK | 0xFF70 | WRAM Bank Select |
| PCM12 | 0xFF76 | PCM Amplitude Channels 1&2 (read-only) |
| PCM34 | 0xFF77 | PCM Amplitude Channels 3&4 (read-only) |

### 8.6 Palette Differences

```
┌─────────────────────────────────────────────────────────────────┐
│ PALETTE COMPARISON                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  DMG (Monochrome):               CGB (Color):                   │
│  ┌─────────────────────┐         ┌─────────────────────┐        │
│  │ BGP (0xFF47)        │         │ BG Palettes (8)     │        │
│  │ ┌───┬───┬───┬───┐   │         │ ┌───┬───┬───┬───┐   │        │
│  │ │ 3 │ 2 │ 1 │ 0 │   │         │ │ 3 │ 2 │ 1 │ 0 │ x8 │        │
│  │ └───┴───┴───┴───┘   │         │ └───┴───┴───┴───┘   │        │
│  │ 2 bits per color    │         │ 5 bits per RGB      │        │
│  │ 4 shades of gray    │         │ 32768 colors        │        │
│  │                     │         │                     │        │
│  │ OBP0 (0xFF48)       │         │ OBJ Palettes (8)    │        │
│  │ OBP1 (0xFF49)       │         │ Same format as BG   │        │
│  └─────────────────────┘         └─────────────────────┘        │
│                                                                   │
│  CGB Color Format: 15-bit RGB (5 bits per channel)              │
│  ┌────────┬────────┬────────┐                                   │
│  │ Red 5b │ Green 5b │ Blue 5b │                                │
│  └────────┴────────┴────────┘                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. MEMORY ACCESS TIMING

### 9.1 Access Timing Summary

| Memory Region | DMG Cycles | CGB Cycles | Notes |
|--------------|------------|------------|-------|
| ROM (0x0000-0x7FFF) | 4 T-states | 4 T-states | Single speed |
| WRAM (0xC000-0xDFFF) | 4 T-states | 4 T-states | Fast RAM |
| VRAM (0x8000-0x9FFF) | 4 T-states | 4 T-states | Inaccessible during mode 3 |
| Cartridge RAM | 4 T-states | 4 T-states | May have wait states |
| I/O Registers | 4 T-states | 4 T-states | Some have side effects |
| OAM (0xFE00-0xFE9F) | 4 T-states | 4 T-states | Inaccessible during mode 2 |

### 9.2 VRAM Access Restrictions

```
┌─────────────────────────────────────────────────────────────────┐
│ LCD MODE ACCESS RESTRICTIONS                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Mode 0: H-Blank    │ VRAM: OK    │ OAM: OK    │ Normal access │
│  Mode 1: V-Blank    │ VRAM: OK    │ OAM: OK    │ Normal access │
│  Mode 2: OAM Search │ VRAM: OK    │ OAM: NO    │ OAM locked    │
│  Mode 3: Transfer   │ VRAM: NO    │ OAM: NO    │ Both locked   │
│                                                                   │
│  Reading during mode 3 returns $FF                               │
│  Writing during mode 3 is ignored                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## APPENDIX: QUICK REFERENCE TABLES

### A.1 Complete Memory Map (Hex)

```
0000-3FFF  Cartridge ROM - Bank 0 (16KB)
4000-7FFF  Cartridge ROM - Bank N (16KB)
8000-97FF  VRAM - Tile Data Block 0/1 (DMG)
8800-9FFF  VRAM - Tile Data Block 2, BG Maps (DMG)
8000-9FFF  VRAM Bank 0 (CGB, 8KB)
A000-BFFF  Cartridge RAM (8KB or banked)
C000-CFFF  WRAM Bank 0 (4KB)
D000-DFFF  WRAM Bank 1 (DMG) / Bank N (CGB)
E000-FDFF  Echo RAM (mirror of C000-DDFF)
FE00-FE9F  OAM - Sprite Attributes (160 bytes)
FEA0-FEFF  Not Usable
FF00-FF7F  I/O Registers
FF80-FFFE  HRAM (127 bytes)
FFFF       Interrupt Enable Register
```

### A.2 MBC Comparison Table

| Feature | MBC1 | MBC2 | MBC3 | MBC5 | MBC6 | MBC7 |
|---------|------|------|------|------|------|------|
| Max ROM | 2MB | 256KB | 2MB | 8MB | 8MB | 8MB |
| Max RAM | 32KB | 512x4b | 32KB | 128KB | 32KB | 256B |
| RAM Banks | 4 | - | 4 | 16 | 4 | - |
| ROM Banks | 125 | 16 | 128 | 512 | 256+ | 512 |
| RTC | No | No | Yes | No | No | No |
| Rumble | No | No | No | Yes | No | Yes |
| Battery | Opt | Opt | Opt | Opt | Opt | Yes |
| Other | - | - | - | - | FLASH | Accel |

---

*Document Version: 1.0*
*Last Updated: Technical Reference for DMG/CGB Memory Systems*
