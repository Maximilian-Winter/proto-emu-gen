# GameBoy PPU (Picture Processing Unit) Technical Specifications

## Document Information
- **Target Systems**: Nintendo GameBoy (DMG) / GameBoy Pocket / GameBoy Color (CGB)
- **PPU Type**: Custom 2D tile-based graphics processor
- **Document Version**: 1.0

---

## 1. PPU OVERVIEW

### 1.1 Architecture and Capabilities

The GameBoy PPU is a custom 2D graphics processor integrated into the SM83 CPU die. It operates independently of the CPU, generating video signals while the CPU executes instructions.

| Feature | DMG | CGB |
|---------|-----|-----|
| Display Type | Reflective LCD (no backlight) | Reflective LCD (no backlight) |
| Colors | 4 shades of gray (monochrome) | 32,768 colors (RGB555), 56 on screen |
| Background Layers | 1 (BG) + 1 (Window) | 1 (BG) + 1 (Window) |
| Sprite Layers | 1 | 1 |
| Hardware Priority | BG/Window → Sprites | BG/Window ↔ Sprites (configurable) |
| VRAM Size | 8 KB | 16 KB (2 banks) |
| Palettes | 1 BG, 2 OBJ (4 colors each) | 8 BG, 8 OBJ (4 colors each) |

### 1.2 LCD Specifications

| Specification | Value |
|---------------|-------|
| **Resolution** | 160 × 144 pixels |
| **Aspect Ratio** | 10:9 (square pixels) |
| **Refresh Rate** | ~59.7275 Hz (V-Blank frequency) |
| **Frame Time** | ~16.74 ms |
| **Visible Scanlines** | 144 |
| **Total Scanlines** | 154 (144 visible + 10 V-Blank) |
| **Scanline Time** | 456 T-states (~108.7 µs) |
| **Dot Clock** | 4.194304 MHz (1 T-state = 1 dot) |

### 1.3 Display Modes and State Machine

The PPU operates in 4 distinct modes, cycling continuously:

```
Mode 2 (OAM Search) → Mode 3 (Pixel Transfer) → Mode 0 (H-Blank) → [repeat 144×]
                                                            ↓
                                                    Mode 1 (V-Blank) → [repeat 10×]
                                                            ↓
                                                    [Back to Mode 2]
```

| Mode | Name | Duration | CPU VRAM Access |
|------|------|----------|-----------------|
| 2 | OAM Search | 80 T-states | OAM: **NO**, VRAM: YES |
| 3 | Pixel Transfer | 168-291 T-states | OAM: **NO**, VRAM: **NO** |
| 0 | H-Blank | 85-208 T-states | OAM: YES, VRAM: YES |
| 1 | V-Blank | 4560 T-states (10 lines) | OAM: YES, VRAM: YES |

**LCD Control Register (0xFF40 - LCDC):**

| Bit | Name | Function |
|-----|------|----------|
| 7 | LCD Display Enable | 0=Off, 1=On |
| 6 | Window Tile Map | 0=0x9800-0x9BFF, 1=0x9C00-0x9FFF |
| 5 | Window Display | 0=Off, 1=On |
| 4 | BG/Window Tile Data | 0=0x8800-0x97FF (signed), 1=0x8000-0x8FFF (unsigned) |
| 3 | BG Tile Map | 0=0x9800-0x9BFF, 1=0x9C00-0x9FFF |
| 2 | OBJ Size | 0=8×8, 1=8×16 |
| 1 | OBJ Display | 0=Off, 1=On |
| 0 | BG/Window Priority | 0=Off, 1=On (DMG: always on) |

---

## 2. LCD TIMING

### 2.1 Scanline Timing (456 T-states)

Each scanline consists of exactly 456 T-states (CPU cycles), divided among PPU modes:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SINGLE SCANLINE (456 T-states)                    │
├────────────────┬──────────────────────────────────┬─────────────────────────┤
│  Mode 2 (OAM)  │         Mode 3 (Pixel Transfer)  │      Mode 0 (H-Blank)   │
│   80 T-states  │        168-291 T-states          │      85-208 T-states    │
├────────────────┼──────────────────────────────────┼─────────────────────────┤
│  0    →   80   │  80   →      variable      → 368 │  368  →      →   456    │
│ Search OAM for │   Render pixels to LCD line      │    CPU can access VRAM  │
│  visible OBJs  │  (duration depends on sprites)   │     PPU is idle         │
└────────────────┴──────────────────────────────────┴─────────────────────────┘
```

### 2.2 Frame Timing (154 Scanlines)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COMPLETE FRAME (70224 T-states)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    VISIBLE SCANLINES (Lines 0-143)                  │   │
│  │  ┌─────────┐  ┌─────────────┐  ┌─────────┐                          │   │
│  │  │ Mode 2  │→ │   Mode 3    │→ │ Mode 0  │  × 144 lines = 65664 T   │   │
│  │  │ 80 T    │  │ 168-291 T   │  │ rest    │                          │   │
│  │  └─────────┘  └─────────────┘  └─────────┘                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    V-BLANK PERIOD (Lines 144-153)                   │   │
│  │                    Mode 1: 456 T-states × 10 = 4560 T               │   │
│  │                    (CPU has full VRAM/OAM access)                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                        │
│                            [Loop to Line 0]                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Mode 0-3 Detailed Breakdown

#### Mode 2: OAM Search (80 T-states, fixed)

The PPU searches OAM (Object Attribute Memory) to find sprites that intersect the current scanline.

- **Start**: Beginning of scanline (T-state 0)
- **Duration**: Exactly 80 T-states
- **Process**: PPU reads all 40 sprites, selecting up to 10 for rendering
- **CPU Access**: OAM is **INACCESSIBLE**, VRAM is accessible

**Sprite Selection Criteria:**
```
For 8×8 sprites:  (LY + 16) >= SpriteY AND (LY + 8) < SpriteY
For 8×16 sprites: (LY + 16) >= SpriteY AND (LY + 16) < SpriteY
```

#### Mode 3: Pixel Transfer (168-291 T-states, variable)

The PPU fetches and renders pixels to the LCD.

- **Start**: T-state 80
- **Duration**: Minimum 168 T-states, increases with sprites
- **Process**: 
  - Fetch background/window tiles
  - Fetch sprite tiles (if applicable)
  - Mix pixels according to priority
- **CPU Access**: **OAM and VRAM are INACCESSIBLE**

**Timing Penalty per Sprite:**
| Condition | Additional T-states |
|-----------|---------------------|
| Sprite on current line | +10-11 T-states |
| Sprite X < 8 (left clip) | May reduce penalty |

#### Mode 0: H-Blank (85-208 T-states, variable)

Horizontal blanking period between scanlines.

- **Start**: After Mode 3 completes
- **Duration**: 456 - (80 + Mode3_duration)
- **Process**: PPU idle, LCD driver moves to next line
- **CPU Access**: **Full access to OAM and VRAM**
- **Best time**: VRAM updates, OAM DMA

#### Mode 1: V-Blank (4560 T-states, 10 scanlines)

Vertical blanking period between frames.

- **Start**: After scanline 143 completes
- **Duration**: 10 scanlines × 456 T-states = 4560 T-states
- **Process**: LCD inactive, beam returns to top
- **CPU Access**: **Full access to OAM and VRAM**
- **Interrupt**: V-Blank interrupt (0x0040) fires at start

### 2.4 STAT Register and Interrupts

**STAT Register (0xFF41):**

| Bit | Name | Description |
|-----|------|-------------|
| 6 | LYC=LY Interrupt | Enable interrupt when LYC == LY |
| 5 | Mode 2 OAM Interrupt | Enable interrupt at Mode 2 start |
| 4 | Mode 1 V-Blank Interrupt | Enable interrupt at Mode 1 start |
| 3 | Mode 0 H-Blank Interrupt | Enable interrupt at Mode 0 start |
| 2 | LYC=LY Flag | Set when LYC register equals current LY |
| 1-0 | Mode Flag | Current PPU mode (0-3) |

**Mode Flag Values:**
| Value | Mode | Description |
|-------|------|-------------|
| 0 | H-Blank | Horizontal blanking period |
| 1 | V-Blank | Vertical blanking period |
| 2 | OAM Search | Searching OAM for sprites |
| 3 | Pixel Transfer | Rendering pixels to LCD |

**Interrupt Behavior:**
- STAT interrupts fire when the corresponding bit is set AND the condition becomes true
- Multiple STAT bits can be set simultaneously
- V-Blank interrupt (0x0040) is separate from STAT V-Blank mode interrupt

---

## 3. BACKGROUND LAYER

### 3.1 Tile Data Regions

Tile data is stored in 8×8 pixel tiles, each requiring 16 bytes (2 bits per pixel).

**Two addressing modes controlled by LCDC bit 4:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TILE DATA ADDRESSING MODES                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  UNSIGNED MODE (LCDC.4 = 1)           SIGNED MODE (LCDC.4 = 0)             │
│  Address: 0x8000-0x8FFF               Address: 0x8800-0x97FF               │
│  Range: 0-255 (256 tiles)             Range: -128 to +127 (256 tiles)      │
│                                                                             │
│  ┌─────────────────────────┐          ┌─────────────────────────┐          │
│  │ 0x8000: Tile 0          │          │ 0x8800: Tile 0 (signed  │          │
│  │ 0x8010: Tile 1          │          │        index -128)      │          │
│  │ 0x8020: Tile 2          │          │ 0x8810: Tile 1 (-127)   │          │
│  │   ...                   │          │   ...                   │          │
│  │ 0x8FF0: Tile 255        │          │ 0x8F00: Tile 112 (-16)  │          │
│  └─────────────────────────┘          │ 0x8F10: Tile 113 (-15)  │          │
│                                       │   ...                   │          │
│                                       │ 0x97F0: Tile 255 (+127) │          │
│                                       └─────────────────────────┘          │
│                                                                             │
│  Tile index in map: 0-255             Tile index in map: 0-255             │
│  Direct address = 0x8000 +            If index < 128:                      │
│                   (index × 16)          address = 0x9000 + (index × 16)    │
│                                       If index >= 128:                     │
│                                         address = 0x8800 +                 │
│                                                   ((index-128) × 16)       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Tile Maps

Two tile map regions define the background layout (32×32 tiles = 256×256 pixels):

| Address Range | Size | Controlled By |
|---------------|------|---------------|
| 0x9800-0x9BFF | 1024 bytes | LCDC.3 = 0 (BG), LCDC.6 = 0 (Window) |
| 0x9C00-0x9FFF | 1024 bytes | LCDC.3 = 1 (BG), LCDC.6 = 1 (Window) |

**Tile Map Layout (32×32 grid):**
```
        Column 0    Column 1    ...    Column 31
      ┌──────────┬──────────┬─────┬──────────┐
Row 0 │  0x9800  │  0x9801  │ ... │  0x981F  │ ← Each byte = tile index
      ├──────────┼──────────┼─────┼──────────┤
Row 1 │  0x9820  │  0x9821  │ ... │  0x983F  │
      ├──────────┼──────────┼─────┼──────────┤
      │   ...    │   ...    │ ... │   ...    │
      ├──────────┼──────────┼─────┼──────────┤
Row 31│  0x9FE0  │  0x9FE1  │ ... │  0x9FFF  │
      └──────────┴──────────┴─────┴──────────┘
```

### 3.3 SCX/SCY Scroll Registers

| Register | Address | Function |
|----------|---------|----------|
| SCY | 0xFF42 | Background vertical scroll (0-255) |
| SCX | 0xFF43 | Background horizontal scroll (0-255) |

**Scrolling Behavior:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BACKGROUND SCROLLING VISUALIZATION                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  256×256 pixel background (32×32 tiles)                                 │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│      │
│  └──────────────────────────────────────────────────────────────┘      │
│          ↑                                                              │
│          └── SCY (vertical scroll)                                      │
│               ┌────────────────────────┐                                │
│               │░░░░░░░░░░░░░░░░░░░░░░░░│ ← 160×144 visible area        │
│               │░░░░░░░░░░░░░░░░░░░░░░░░│   (LCD screen)                │
│               │░░░░░░░░░░░░░░░░░░░░░░░░│                                │
│               │░░░░░░░░░░░░░░░░░░░░░░░░│                                │
│               └────────────────────────┘                                │
│               SCX (horizontal scroll) →                                 │
│                                                                         │
│  Note: Background wraps around (256×256 toroidal)                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.4 8×8 Tile Format

Each tile is 8×8 pixels with 2 bits per pixel (4 colors/shades):

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TILE DATA FORMAT (16 bytes)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Tile stored as 8 rows, each row = 2 bytes (bit planes)                    │
│                                                                             │
│  Row 0: Byte 0 (low bit plane), Byte 1 (high bit plane)                    │
│  Row 1: Byte 2 (low bit plane), Byte 3 (high bit plane)                    │
│  ...                                                                        │
│  Row 7: Byte 14 (low bit plane), Byte 15 (high bit plane)                  │
│                                                                             │
│  Pixel value = (HighBit << 1) | LowBit  (0-3)                              │
│                                                                             │
│  Example tile data for a simple pattern:                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Address  │ Data  │ Binary    │ Description                          │   │
│  ├──────────┼───────┼───────────┼──────────────────────────────────────┤   │
│  │ 0x8000   │ 0x7E  │ 01111110  │ Row 0, low bits                      │   │
│  │ 0x8001   │ 0x7E  │ 01111110  │ Row 0, high bits                     │   │
│  │ 0x8002   │ 0x81  │ 10000001  │ Row 1, low bits                      │   │
│  │ 0x8003   │ 0x81  │ 10000001  │ Row 1, high bits                     │   │
│  │ 0x8004   │ 0xA5  │ 10100101  │ Row 2, low bits                      │   │
│  │ 0x8005   │ 0xA5  │ 10100101  │ Row 2, high bits                     │   │
│  │   ...    │  ...  │    ...    │ ...                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Pixel decoding for Row 0, Column 0:                                       │
│    Low bit = bit 7 of 0x7E = 0                                             │
│    High bit = bit 7 of 0x7E = 0                                            │
│    Pixel value = (0 << 1) | 0 = 0 (color 0)                                │
│                                                                             │
│  Pixel decoding for Row 0, Column 1:                                       │
│    Low bit = bit 6 of 0x7E = 1                                             │
│    High bit = bit 6 of 0x7E = 1                                            │
│    Pixel value = (1 << 1) | 1 = 3 (color 3)                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. WINDOW LAYER

### 4.1 WX/WY Position Registers

| Register | Address | Function | Notes |
|----------|---------|----------|-------|
| WY | 0xFF4A | Window Y position | 0-143 (must be >= 0 for visibility) |
| WX | 0xFF4B | Window X position | 0-166 (actual X = WX - 7) |

### 4.2 Window Visibility Conditions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        WINDOW VISIBILITY CONDITIONS                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Window is VISIBLE when ALL conditions are met:                            │
│                                                                             │
│  1. LCDC.5 (Window Display Enable) = 1                                     │
│  2. LCDC.0 (BG/Window Master Enable) = 1                                   │
│  3. WY <= current scanline (LY)                                            │
│  4. WX <= 166 (for any visible portion)                                    │
│                                                                             │
│  Window is INVISIBLE when ANY condition fails:                             │
│                                                                             │
│  - WY > 143: Window never appears                                          │
│  - WX > 166: Window completely off-screen right                            │
│  - WX < 7: Window starts partially off-screen left                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 How Window Overrides Background

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      WINDOW RENDERING BEHAVIOR                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  When window is enabled and visible:                                       │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        LCD SCREEN (160×144)                         │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│   │   │
│  │  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│   │   │
│  │  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│   │   │
│  │  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│   │   │
│  │  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│   │   │
│  │  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│   │   │
│  │  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│   │   │
│  │  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│   │   │
│  │  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│   │   │
│  │  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│   │   │
│  │  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│   │   │
│  │  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│   │   │
│  │  │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│   │   │
│  │  │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│   │   │
│  │  │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│   │   │
│  │  │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  ▓▓▓ = Background (scrolling)    ░░░ = Window (fixed, no scroll)   │   │
│  │                                                                     │   │
│  │  Window uses its own tile map (selected by LCDC.6)                  │   │
│  │  Window uses same tile data as background                           │   │
│  │  Window does NOT wrap - it extends infinitely right/down            │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Key behavior: Once window starts on a scanline, it continues to the edge   │
│  Window has priority over background on pixels where both would render      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.4 WX/WY Quirks

| Quirk | Description |
|-------|-------------|
| WX offset | Actual X position = WX - 7 (so WX=7 places window at left edge) |
| WX=0-6 | Window visible but clipped on left side |
| WX=166+ | Window completely off-screen |
| WY change | Changing WY mid-frame can cause window to appear/disappear |
| WX change | Changing WX mid-frame causes visible "window slide" effect |

---

## 5. SPRITE/OBJ LAYER

### 5.1 OAM (Object Attribute Memory)

| Attribute | Address Range | Size | Description |
|-----------|---------------|------|-------------|
| OAM | 0xFE00-0xFE9F | 160 bytes | 40 sprites × 4 bytes each |

**OAM is inaccessible during Mode 2 (OAM Search) and Mode 3 (Pixel Transfer).**

### 5.2 Sprite Attributes

Each sprite consists of 4 bytes:

| Byte | Name | Description |
|------|------|-------------|
| 0 | Y Position | Vertical position on screen (Y + 16 = screen position) |
| 1 | X Position | Horizontal position on screen (X + 8 = screen position) |
| 2 | Tile Index | Tile number (8×8 mode: 0-255; 8×16 mode: even numbers only) |
| 3 | Attributes | Flags (priority, flip, palette, etc.) |

**Attribute Flags (Byte 3):**

| Bit | Name | DMG | CGB |
|-----|------|-----|-----|
| 7 | Priority | 0=Above BG, 1=Behind BG colors 1-3 | Same |
| 6 | Y Flip | 0=Normal, 1=Flip vertically | Same |
| 5 | X Flip | 0=Normal, 1=Flip horizontally | Same |
| 4 | Palette | 0=OBP0, 1=OBP1 | 0=OBP0, 1=OBP1 (DMG mode) |
| 3 | Tile VRAM Bank | Unused | 0=Bank 0, 1=Bank 1 |
| 2-0 | CGB Palette | Unused | 0-7 (selects OCP palette) |

### 5.3 8×8 and 8×16 Modes

**Controlled by LCDC.2:**

| Mode | Size | Tiles Used | Tile Index |
|------|------|------------|------------|
| 8×8 | 8×8 pixels | 1 tile | Any (0-255) |
| 8×16 | 8×16 pixels | 2 tiles | Even numbers only (0, 2, 4, ...) |

**8×16 Mode Details:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          8×16 SPRITE FORMAT                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Sprite with tile index N (must be even):                                  │
│                                                                             │
│  ┌─────────────────┐                                                       │
│  │                 │  ← Top 8×8 tile = N                                   │
│  │   Tile N        │     (at sprite Y position)                            │
│  │                 │                                                       │
│  ├─────────────────┤                                                       │
│  │                 │  ← Bottom 8×8 tile = N+1                              │
│  │   Tile N+1      │     (at sprite Y+8 position)                          │
│  │                 │                                                       │
│  └─────────────────┘                                                       │
│                                                                             │
│  Note: When Y-flipped, the order of tiles is swapped (N+1 on top)          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.4 Sprite Priority and Limits

**Per-Scanline Limits:**
| Limit | Value | Description |
|-------|-------|-------------|
| Max sprites per line | 10 | Only first 10 sprites drawn |
| Max sprites total | 40 | OAM can hold 40 sprites |

**Sprite Priority Rules:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SPRITE PRIORITY RULES                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. OAM Order Priority (for selection):                                    │
│     - Sprites are checked in OAM order (0-39)                              │
│     - First 10 sprites intersecting current line are selected                │
│     - Lower OAM index = higher priority                                    │
│                                                                             │
│  2. X-Position Priority (for rendering):                                   │
│     - Among selected sprites, smaller X position draws on top              │
│     - If X positions equal, lower OAM index draws on top                   │
│                                                                             │
│  3. Background Priority (pixel mixing):                                    │
│     - Sprite priority bit = 0: Sprite draws over BG (except color 0)       │
│     - Sprite priority bit = 1: Sprite draws behind BG colors 1-3           │
│     - BG color 0 is always transparent                                     │
│                                                                             │
│  4. Final Pixel Priority (DMG):                                            │
│     - Window/BG color 0: Transparent                                       │
│     - Sprite color 0: Transparent                                          │
│     - Priority: Window → BG → Sprites (with priority bit considered)       │
│                                                                             │
│  5. Final Pixel Priority (CGB):                                            │
│     - Priority bit in tile attribute can make BG draw over sprites         │
│     - More complex priority system with master priority bit                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Sprite Position Encoding:**
| Screen Position | Y Value | X Value | Visibility |
|-----------------|---------|---------|------------|
| Top-left (0,0) | 16 | 8 | Visible |
| Off-screen top | 0-15 | any | Hidden |
| Off-screen left | any | 0-7 | Partially visible |
| Off-screen bottom | 160+ | any | Hidden |
| Off-screen right | any | 168+ | Hidden |

---

## 6. PALETTES

### 6.1 DMG Palettes (Monochrome)

**BGP - Background Palette (0xFF47):**

| Bits | Description |
|------|-------------|
| 7-6 | Color for pixel value 3 |
| 5-4 | Color for pixel value 2 |
| 3-2 | Color for pixel value 1 |
| 1-0 | Color for pixel value 0 |

**Color Values:**
| Value | Shade | Typical RGB |
|-------|-------|-------------|
| 0 | White | #FFFFFF |
| 1 | Light Gray | #AAAAAA |
| 2 | Dark Gray | #555555 |
| 3 | Black | #000000 |

**OBP0 - Object Palette 0 (0xFF48):**

| Bits | Description |
|------|-------------|
| 7-6 | Color for pixel value 3 |
| 5-4 | Color for pixel value 2 |
| 3-2 | Color for pixel value 1 |
| 1-0 | Unused (transparent) |

**OBP1 - Object Palette 1 (0xFF49):** Same format as OBP0

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DMG PALETTE REGISTERS                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  BGP (0xFF47) - Background Palette                                          │
│  ┌────┬────┬────┬────┬────┬────┬────┬────┐                                 │
│  │ 7  │ 6  │ 5  │ 4  │ 3  │ 2  │ 1  │ 0  │                                 │
│  ├────┴────┼────┴────┼────┴────┼────┴────┤                                 │
│  │ Color 3 │ Color 2 │ Color 1 │ Color 0 │                                 │
│  └─────────┴─────────┴─────────┴─────────┘                                 │
│                                                                             │
│  OBP0/OBP1 (0xFF48/0xFF49) - Object Palettes                                │
│  ┌────┬────┬────┬────┬────┬────┬────┬────┐                                 │
│  │ 7  │ 6  │ 5  │ 4  │ 3  │ 2  │ 1  │ 0  │                                 │
│  ├────┴────┼────┴────┼────┴────┼─────────┤                                 │
│  │ Color 3 │ Color 2 │ Color 1 │  (tr)   │  ← Color 0 is always transparent│
│  └─────────┴─────────┴─────────┴─────────┘                                 │
│                                                                             │
│  Example: BGP = 0xE4 (binary: 11100100)                                     │
│  ┌─────────┬─────────┬─────────┬─────────┐                                 │
│  │  3 (11) │  0 (00) │  1 (01) │  2 (10) │                                 │
│  │  BLACK  │  WHITE  │ LT GRAY │ DK GRAY │                                 │
│  └─────────┴─────────┴─────────┴─────────┘                                 │
│                                                                             │
│  This creates an inverted palette: pixel 0=white, 1=light, 2=dark, 3=black │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 CGB Palettes (Color)

**Background Palette Registers:**

| Register | Address | Function |
|----------|---------|----------|
| BCPS/BGPI | 0xFF68 | Background Palette Index |
| BCPD/BGPD | 0xFF69 | Background Palette Data |

**Object Palette Registers:**

| Register | Address | Function |
|----------|---------|----------|
| OCPS/OBPI | 0xFF6A | Object Palette Index |
| OCPD/OBPD | 0xFF6B | Object Palette Data |

**Palette Index Register Format (BCPS/OCPS):**

| Bit | Name | Description |
|-----|------|-------------|
| 7 | Auto-Increment | 0=Manual, 1=Auto-increment after write |
| 5-0 | Index | Which color/palette to access |

**Index Encoding:**
```
Index bits: [5:3] = Palette number (0-7)
            [2:1] = Color number within palette (0-3)
            [0]   = Low/High byte of color (0=low, 1=high)

Example indices:
  0x00 = Palette 0, Color 0, Low byte
  0x01 = Palette 0, Color 0, High byte
  0x02 = Palette 0, Color 1, Low byte
  0x08 = Palette 1, Color 0, Low byte
  0x3F = Palette 7, Color 3, High byte
```

**RGB555 Color Format:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CGB RGB555 COLOR FORMAT                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Each color is 15 bits, stored as 2 bytes:                                 │
│                                                                             │
│  Low Byte (first):                                                         │
│  ┌────┬────┬────┬────┬────┬────┬────┬────┐                                 │
│  │ 7  │ 6  │ 5  │ 4  │ 3  │ 2  │ 1  │ 0  │                                 │
│  ├────┴────┴────┴────┴────┼────┴────┴────┤                                 │
│  │      Red (5 bits)       │ Green[2:0]   │                                 │
│  └─────────────────────────┴──────────────┘                                 │
│                                                                             │
│  High Byte (second):                                                       │
│  ┌────┬────┬────┬────┬────┬────┬────┬────┐                                 │
│  │ 7  │ 6  │ 5  │ 4  │ 3  │ 2  │ 1  │ 0  │                                 │
│  ├────┴────┴────┼────┴────┴────┴────┴────┤                                 │
│  │ Green[4:3]   │      Blue (5 bits)      │                                 │
│  └──────────────┴─────────────────────────┘                                 │
│                                                                             │
│  Color = {Red[4:0], Green[4:0], Blue[4:0]}                                  │
│                                                                             │
│  Example: Bright Red                                                       │
│  Red = 31 (0x1F), Green = 0, Blue = 0                                      │
│  Low byte = 0x1F, High byte = 0x00                                         │
│                                                                             │
│  Example: White                                                            │
│  Red = 31, Green = 31, Blue = 31                                           │
│  Low byte = 0xFF, High byte = 0x7F                                         │
│                                                                             │
│  Note: Each palette has 4 colors, so 8 palettes × 4 colors = 32 colors     │
│        for backgrounds, and 32 colors for sprites                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**CGB Palette Summary:**

| Feature | Value |
|---------|-------|
| BG Palettes | 8 |
| OBJ Palettes | 8 |
| Colors per palette | 4 |
| Total BG colors | 32 |
| Total OBJ colors | 32 |
| Colors on screen | Max 56 (32 BG + 32 OBJ - shared transparent) |
| Color depth | 15-bit RGB (32768 possible colors) |

---

## 7. VRAM LAYOUT

### 7.1 Address Ranges

**DMG VRAM Map:**

| Address Range | Size | Content |
|---------------|------|---------|
| 0x8000-0x87FF | 2 KB | Tile Data Block 0 (Tiles 0-127, unsigned) |
| 0x8800-0x8FFF | 2 KB | Tile Data Block 1 (Tiles 128-255, unsigned / -128 to -1, signed) |
| 0x9000-0x97FF | 2 KB | Tile Data Block 2 (Tiles 0-127, signed mode) |
| 0x9800-0x9BFF | 1 KB | Tile Map 0 |
| 0x9C00-0x9FFF | 1 KB | Tile Map 1 |

**Total DMG VRAM: 8 KB (0x8000-0x9FFF)**

### 7.2 VRAM Banking (CGB Only)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CGB VRAM BANKING                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CGB has 16 KB of VRAM, accessed through banking:                          │
│                                                                             │
│  SVBK Register (0xFF70) - WRAM Bank (commonly confused with VRAM)          │
│  VBK Register (0xFF4F) - VRAM Bank                                         │
│                                                                             │
│  VBK Register Format:                                                      │
│  ┌────┬────┬────┬────┬────┬────┬────┬────┐                                 │
│  │ 7  │ 6  │ 5  │ 4  │ 3  │ 2  │ 1  │ 0  │                                 │
│  ├────┴────┴────┴────┴────┴────┴────┴────┤                                 │
│  │           Unused           │  VRAM Bank │                                 │
│  └────────────────────────────┴────────────┘                                 │
│                                                                             │
│  VRAM Bank 0 (VBK = 0):                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 0x8000-0x8FFF │ Tile Data Block 0 (Tiles 0-255, unsigned)           │   │
│  │ 0x9000-0x97FF │ Tile Data Block 1 (Tiles 128-255 signed / 0-127)    │   │
│  │ 0x9800-0x9BFF │ Tile Map 0                                          │   │
│  │ 0x9C00-0x9FFF │ Tile Map 1                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  VRAM Bank 1 (VBK = 1):                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 0x8000-0x8FFF │ Additional Tile Data (Tiles 0-255, bank 1)          │   │
│  │ 0x9000-0x97FF │ Additional Tile Data (Tiles 256-383, bank 1)        │   │
│  │ 0x9800-0x9BFF │ Tile Map 0 Attribute Table                          │   │
│  │ 0x9C00-0x9FFF │ Tile Map 1 Attribute Table                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Tile Map Attribute Table (CGB only, Bank 1):                              │
│  Each byte corresponds to a tile in the tile map on Bank 0                 │
│                                                                             │
│  Attribute Byte Format:                                                    │
│  ┌────┬────┬────┬────┬────┬────┬────┬────┐                                 │
│  │ 7  │ 6  │ 5  │ 4  │ 3  │ 2  │ 1  │ 0  │                                 │
│  ├────┼────┼────┼────┼────┼────┴────┴────┤                                 │
│  │Prty│YFl │XFl │None│Bank│   Palette    │                                 │
│  └────┴────┴────┴────┴────┴──────────────┘                                 │
│                                                                             │
│  Bit 7: Priority (0=Normal, 1=Draw above sprites)                          │
│  Bit 6: Y Flip                                                             │
│  Bit 5: X Flip                                                             │
│  Bit 4: Unused                                                             │
│  Bit 3: VRAM Bank (0=Bank 0, 1=Bank 1)                                     │
│  Bit 2-0: Palette (0-7)                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Access Restrictions During Modes 2-3

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      VRAM/OAM ACCESS RESTRICTIONS                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PPU Mode │ OAM Access │ VRAM Access │ Palette Access │ Behavior on Read   │
│  ─────────┼────────────┼─────────────┼────────────────┼─────────────────── │
│  Mode 0   │    YES     │    YES      │      YES       │ Normal             │
│  Mode 1   │    YES     │    YES      │      YES       │ Normal             │
│  Mode 2   │    NO      │    YES      │      YES       │ OAM: returns 0xFF  │
│  Mode 3   │    NO      │    NO       │      YES       │ OAM: returns 0xFF  │
│           │            │             │                │ VRAM: returns 0xFF │
│  ─────────┴────────────┴─────────────┴────────────────┴─────────────────── │
│                                                                             │
│  Important Notes:                                                          │
│  • Writes to restricted memory are ignored                                 │
│  • Reads return 0xFF during restriction                                    │
│  • OAM DMA can run during Modes 0-1, but NOT during Mode 2                 │
│  • CGB palette registers are always accessible                             │
│  • CGB HDMA can transfer during H-Blank (Mode 0)                           │
│                                                                             │
│  Safe VRAM Update Windows:                                                 │
│  • During V-Blank (Mode 1): 4560 T-states (~1.09 ms)                       │
│  • During H-Blank (Mode 0): 85-208 T-states (~20-50 µs)                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. DMG vs CGB DIFFERENCES

### 8.1 Color Capabilities Comparison

| Feature | DMG | CGB |
|---------|-----|-----|
| Display Colors | 4 shades of gray | 32,768 colors (RGB555) |
| On-screen Colors | 4 | Up to 56 (32 BG + 32 OBJ) |
| BG Palettes | 1 (4 colors) | 8 (4 colors each) |
| OBJ Palettes | 2 (3 colors each) | 8 (4 colors each) |
| Palette Memory | 3 registers | 64 bytes indexed |

### 8.2 VRAM and Banking

| Feature | DMG | CGB |
|---------|-----|-----|
| VRAM Size | 8 KB | 16 KB |
| VRAM Banks | 1 | 2 |
| Bank Select | N/A | VBK register (0xFF4F) |
| Tile Data | 256 tiles (128 in signed mode) | 512 tiles (384 usable) |
| Tile Maps | 2 (with attributes in ROM) | 2 (with attributes in VRAM Bank 1) |

### 8.3 Priority Bit

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PRIORITY BIT DIFFERENCES                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  DMG Priority System:                                                      │
│  ───────────────────                                                       │
│  • Sprite priority bit: 0=Above BG, 1=Behind BG colors 1-3                 │
│  • BG color 0 is always transparent                                        │
│  • Sprite color 0 is always transparent                                    │
│  • Fixed priority: Window → Background → Sprites                           │
│                                                                             │
│  CGB Priority System:                                                      │
│  ───────────────────                                                       │
│  • Sprite priority bit: Same as DMG                                        │
│  • BG Attribute bit 7: 0=Normal, 1=BG draws above all sprites              │
│  • Allows BG tiles to have priority over sprites                           │
│  • More flexible layering control                                          │
│                                                                             │
│  Example Use Case:                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  In a platformer, you might want:                                   │   │
│  │  • Player sprite to appear IN FRONT of foreground tiles             │   │
│  │  • Player sprite to appear BEHIND background pillars                │   │
│  │                                                                     │   │
│  │  CGB Solution: Set BG attribute bit 7 on pillar tiles               │   │
│  │  DMG Limitation: Cannot achieve this effect cleanly                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.4 HDMA (CGB Only)

**HDMA Registers:**

| Register | Address | Function |
|----------|---------|----------|
| HDMA1 | 0xFF51 | Source address high byte |
| HDMA2 | 0xFF52 | Source address low byte (lower 4 bits ignored) |
| HDMA3 | 0xFF53 | Destination address high byte |
| HDMA4 | 0xFF54 | Destination address low byte (lower 4 bits ignored) |
| HDMA5 | 0xFF55 | Length/mode/control |

**HDMA5 Register Format:**

| Bit | Name | Description |
|-----|------|-------------|
| 7 | Mode | 0=General DMA (immediate), 1=H-Blank DMA |
| 6-0 | Length | Transfer length = (Length + 1) × 16 bytes |

**HDMA Modes:**

| Mode | Description | Timing |
|------|-------------|--------|
| General DMA | Immediate transfer | ~8 µs per 16 bytes, CPU halted |
| H-Blank DMA | Transfer during each H-Blank | 16 bytes per scanline, CPU runs |

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CGB HDMA OPERATION                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  H-Blank DMA Mode (Recommended for active display):                        │
│  ───────────────────────────────────────────────────                       │
│                                                                             │
│  1. Set source address (HDMA1-HDMA2)                                       │
│  2. Set destination address (HDMA3-HDMA4) - must be in VRAM (0x8000-0x9FFF)│
│  3. Write to HDMA5 with bit 7 = 1                                          │
│                                                                             │
│  Transfer proceeds automatically:                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  Scanline N: Mode 2 → Mode 3 → Mode 0 [HDMA transfers 16 bytes] →   │   │
│  │  Scanline N+1: Mode 2 → Mode 3 → Mode 0 [HDMA transfers 16 bytes] → │   │
│  │  ...                                                                │   │
│  │  Until all data transferred                                         │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  CPU continues running during H-Blank DMA!                                 │
│  Reading HDMA5 returns remaining blocks (bit 7 = 0 when complete)          │
│  Writing 0x80 to HDMA5 cancels active H-Blank DMA                          │
│                                                                             │
│  General DMA Mode (Use during V-Blank):                                    │
│  ─────────────────────────────────────                                     │
│  • Write to HDMA5 with bit 7 = 0                                           │
│  • CPU halted during transfer                                              │
│  • Transfer completes immediately                                          │
│  • Can transfer up to 2048 bytes (128 × 16)                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.5 Feature Summary Table

| Feature | DMG | CGB | Notes |
|---------|-----|-----|-------|
| Color Output | 4 shades | 32768 colors | CGB compatible mode uses DMG palettes |
| VRAM Size | 8 KB | 16 KB | CGB has 2 banks |
| Tile Count | 256/128 | 512/384 | Depending on addressing mode |
| BG Palettes | 1 | 8 | CGB: BCPS/BCPD registers |
| OBJ Palettes | 2 | 8 | CGB: OCPS/OCPD registers |
| Tile Attributes | None | Yes | Bank 1: priority, flip, palette, bank |
| HDMA | No | Yes | H-Blank and General DMA |
| Infrared Port | No | Yes | For communication |
| Speed Mode | No | Yes | Normal (4MHz) / Double (8MHz) |

---

## Appendix A: PPU Register Reference

| Register | Address | R/W | Description |
|----------|---------|-----|-------------|
| LCDC | 0xFF40 | R/W | LCD Control |
| STAT | 0xFF41 | R/W | LCD Status |
| SCY | 0xFF42 | R/W | Scroll Y |
| SCX | 0xFF43 | R/W | Scroll X |
| LY | 0xFF44 | R | Current scanline (0-153) |
| LYC | 0xFF45 | R/W | LY Compare |
| DMA | 0xFF46 | W | OAM DMA trigger |
| BGP | 0xFF47 | R/W | Background Palette (DMG) |
| OBP0 | 0xFF48 | R/W | Object Palette 0 (DMG) |
| OBP1 | 0xFF49 | R/W | Object Palette 1 (DMG) |
| WY | 0xFF4A | R/W | Window Y Position |
| WX | 0xFF4B | R/W | Window X Position |
| VBK | 0xFF4F | R/W | VRAM Bank (CGB only) |
| HDMA1 | 0xFF51 | R/W | HDMA Source High (CGB) |
| HDMA2 | 0xFF52 | R/W | HDMA Source Low (CGB) |
| HDMA3 | 0xFF53 | R/W | HDMA Dest High (CGB) |
| HDMA4 | 0xFF54 | R/W | HDMA Dest Low (CGB) |
| HDMA5 | 0xFF55 | R/W | HDMA Length/Mode (CGB) |
| BCPS | 0xFF68 | R/W | BG Palette Index (CGB) |
| BCPD | 0xFF69 | R/W | BG Palette Data (CGB) |
| OCPS | 0xFF6A | R/W | OBJ Palette Index (CGB) |
| OCPD | 0xFF6B | R/W | OBJ Palette Data (CGB) |

---

## Appendix B: Timing Reference

| Parameter | Value | Notes |
|-----------|-------|-------|
| CPU Clock | 4.194304 MHz | 1 T-state = 1 cycle |
| Scanline Time | 456 T-states | ~108.7 µs |
| H-Blank Time | 85-208 T-states | Variable |
| OAM Search | 80 T-states | Fixed |
| Pixel Transfer | 168-291 T-states | Depends on sprites |
| V-Blank Time | 4560 T-states | 10 scanlines |
| Frame Time | 70224 T-states | ~16.74 ms |
| Refresh Rate | ~59.7275 Hz | V-Blank frequency |

---

*Document compiled for GameBoy development reference. All addresses in hexadecimal.*
