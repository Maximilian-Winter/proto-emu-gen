# GameBoy Hardware Technical Specifications
## Original GameBoy (DMG) & GameBoy Color (CGB)

---

## 1. PHYSICAL SPECIFICATIONS

### 1.1 Original GameBoy (DMG-01)

| Parameter | Specification |
|-----------|---------------|
| **Model Number** | DMG-01 (Dot Matrix Game) |
| **Width** | 90 mm (3.54 in) |
| **Height** | 148 mm (5.83 in) |
| **Depth** | 32 mm (1.26 in) |
| **Weight** | 220 g (7.76 oz) without batteries |
| **Weight (with batteries)** | ~300 g (4x AA alkaline) |
| **Screen Size** | 66 mm (2.6 in) diagonal |
| **Screen Type** | STN (Super-Twisted Nematic) LCD |
| **Display Area** | 47 x 43 mm |

### 1.2 GameBoy Color (CGB-001)

| Parameter | Specification |
|-----------|---------------|
| **Model Number** | CGB-001 (Color GameBoy) |
| **Width** | 75 mm (2.95 in) |
| **Height** | 133 mm (5.24 in) |
| **Depth** | 27 mm (1.06 in) |
| **Weight** | 138 g (4.87 oz) without batteries |
| **Weight (with batteries)** | ~190 g (2x AA alkaline) |
| **Screen Size** | 59 mm (2.32 in) diagonal |
| **Screen Type** | Color TFT LCD with backlight |
| **Display Area** | 44 x 40 mm |

### 1.3 Button Layout

Both DMG and CGB share the same button configuration:

| Button | Type | Function |
|--------|------|----------|
| **D-Pad** | Rubber conductive, 4-directional | Directional input (Up/Down/Left/Right) |
| **A Button** | Rubber conductive, circular | Primary action |
| **B Button** | Rubber conductive, circular | Secondary action |
| **Start** | Rubber conductive, small circular | Menu/Pause |
| **Select** | Rubber conductive, small circular | Option/Secondary menu |
| **Power Switch** | Slide switch | Power on/off |
| **Volume Wheel** | Rotary potentiometer | Audio level control |
| **Contrast Wheel** | Rotary potentiometer | LCD contrast (DMG only) |

**Button Register (P1/JOYP):** Memory address `0xFF00`

---

## 2. POWER SPECIFICATIONS

### 2.1 Original GameBoy (DMG)

| Parameter | Specification |
|-----------|---------------|
| **Battery Type** | 4x AA (LR6) alkaline or rechargeable |
| **Battery Voltage** | 6.0V nominal (4 x 1.5V) |
| **Operating Voltage Range** | 4.5V - 7.5V |
| **DC Input Jack** | 6V DC, 300mA, center negative |
| **Jack Size** | 3.5mm x 1.35mm |
| **Active Current** | 70-100 mA (varies with cartridge) |
| **Idle Current** | ~50 mA (screen on, no activity) |
| **Battery Life** | 10-35 hours (alkaline AA) |
| **Power LED** | Red LED, no battery indicator |

### 2.2 GameBoy Color (CGB)

| Parameter | Specification |
|-----------|---------------|
| **Battery Type** | 2x AA (LR6) alkaline or rechargeable |
| **Battery Voltage** | 3.0V nominal (2 x 1.5V) |
| **Operating Voltage Range** | 2.2V - 3.8V |
| **DC Input Jack** | 3V DC, 300mA, center negative |
| **Jack Size** | 3.5mm x 1.35mm |
| **Active Current** | 45-70 mA (varies with cartridge) |
| **Idle Current** | ~30 mA (screen on, no activity) |
| **Battery Life** | 10-30 hours (alkaline AA) |
| **Power LED** | Dual-color LED (Green/Red) |

### 2.3 CGB Power LED Behavior

| LED State | Battery Condition |
|-----------|-------------------|
| **Green** | Battery good (>2.5V) |
| **Red** | Battery low (<2.5V) |
| **Off** | Power off or critical battery |

The CGB uses a voltage comparator to switch LED colors at approximately 2.5V threshold.

---

## 3. CLOCK AND TIMING

### 3.1 System Clock Specifications

| Parameter | DMG | CGB |
|-----------|-----|-----|
| **Crystal Frequency** | 4.194304 MHz | 4.194304 MHz / 8.388608 MHz |
| **CPU Clock (Normal Mode)** | 1.048576 MHz | 1.048576 MHz |
| **CPU Clock (Double Speed)** | N/A | 2.097152 MHz |
| **Machine Cycle** | 4 clock cycles | 4 clock cycles |
| **Instruction Cycle** | 4-24 clock cycles | 4-24 clock cycles |

### 3.2 Clock Derivation

```
4.194304 MHz Crystal
        |
        +-- [Divide by 4] --> CPU Clock: 1.048576 MHz (DMG/CGB Normal)
        |
        +-- [Divide by 2] --> CPU Clock: 2.097152 MHz (CGB Double Speed)
```

### 3.3 Timer Divider Details

| Register | Address | Function |
|----------|---------|----------|
| **DIV** | 0xFF04 | Divider Register (16-bit counter upper 8 bits) |
| **TIMA** | 0xFF05 | Timer Counter |
| **TMA** | 0xFF06 | Timer Modulo (reload value) |
| **TAC** | 0xFF07 | Timer Control |

**TAC Register Bits:**
- Bit 2: Timer Enable (1=on, 0=off)
- Bits 1-0: Clock Select
  - 00: CPU Clock / 1024 (4096 Hz)
  - 01: CPU Clock / 16 (262144 Hz)
  - 10: CPU Clock / 64 (65536 Hz)
  - 11: CPU Clock / 256 (16384 Hz)

### 3.4 CGB Double Speed Mode

The CGB supports a double-speed mode activated by writing to KEY1 register (0xFF4D):
- Bit 7: Current Speed (0=Normal, 1=Double)
- Bit 0: Speed Switch Request (1=prepare switch)

Speed change requires STOP instruction execution after setting bit 0.

---

## 4. I/O PORTS

### 4.1 Link Cable Port

Both DMG and CGB use a 6-pin proprietary connector for serial communication.

#### Link Cable Pinout

| Pin | Signal | Description |
|-----|--------|-------------|
| **1** | VCC | +5V (DMG) / +3.3V (CGB) |
| **2** | SO (Serial Out) | Data output from master |
| **3** | SI (Serial In) | Data input to master |
| **4** | SD (Serial Data)** | Bidirectional data (CGB only) |
| **5** | SC (Serial Clock) | Clock signal |
| **6** | GND | Ground |

**Note:** Pin 4 (SD) is only used on CGB for faster transfer modes.

#### Serial Communication Protocol

| Parameter | Specification |
|-----------|---------------|
| **Transfer Rate (Internal Clock)** | 8192 bits/second (DMG) |
| **Transfer Rate (CGB Normal)** | 8192 bits/second |
| **Transfer Rate (CGB Fast)** | 524288 bits/second |
| **Data Format** | 8-bit, LSB first |
| **Master/Slave** | Master provides clock, slave receives |

**Serial Registers:**
- SB (0xFF01): Serial Transfer Data
- SC (0xFF02): Serial Transfer Control
  - Bit 7: Transfer Start Flag
  - Bit 1: Clock Select (0=external, 1=internal)
  - Bit 0: CGB Speed (0=normal, 1=fast)

### 4.2 Cartridge Slot Pinout

The cartridge connector provides 32 pins for ROM/RAM access and expansion.

| Pin | Signal | Type | Description |
|-----|--------|------|-------------|
| **1** | VCC | Power | +5V (DMG) / +3.3V (CGB) |
| **2** | PHI | Output | System clock (1.05/2.10 MHz) |
| **3** | /WR | Output | Write strobe (active low) |
| **4** | /RD | Output | Read strobe (active low) |
| **5** | /CS | Output | Chip select (active low) |
| **6-20** | A0-A14 | Output | Address bus (15 bits, 32KB range) |
| **21-28** | D0-D7 | I/O | Data bus (8-bit) |
| **29** | /RST | Output | Reset signal (active low) |
| **30** | NC | - | No connection |
| **31** | AUDIO IN | Input | External audio input |
| **32** | GND | Power | Ground |

**CGB Additional Signals:**
- Pin 30 (CGB only): /CS2 - RAM chip select for CGB cartridges

### 4.3 Infrared Port (CGB Only)

The CGB includes an infrared transceiver for wireless communication.

| Parameter | Specification |
|-----------|---------------|
| **Type** | Infrared LED + phototransistor |
| **Wavelength** | ~940 nm |
| **Carrier Frequency** | None (baseband) |
| **Data Rate** | Up to 512 bits/second (software controlled) |
| **Range** | ~1-2 meters (line of sight) |
| **Register** | RP (0xFF56) - Infrared Port |

**RP Register Bits:**
- Bit 1: Write Data (1=emit IR, 0=off)
- Bit 0: Read Data (1=IR detected, 0=no IR)

---

## 5. INPUT/CONTROLS

### 5.1 Button Register (P1/JOYP)

**Address:** `0xFF00`

The P1 register uses a matrix scanning method to read button states.

#### P1 Register Bit Layout

| Bit | Function |
|-----|----------|
| **7** | Not used |
| **6** | Not used |
| **5** | P15 Out - Select Action buttons (A, B, Select, Start) |
| **4** | P14 Out - Select Direction buttons (Up, Down, Left, Right) |
| **3** | P13 In - Down or Start (depending on P14/P15) |
| **2** | P12 In - Up or Select (depending on P14/P15) |
| **1** | P11 In - Left or B (depending on P14/P15) |
| **0** | P10 In - Right or A (depending on P14/P15) |

#### Button Matrix

| Input Line | P14=Low (Direction) | P15=Low (Action) |
|------------|---------------------|------------------|
| **P10** | Right | A |
| **P11** | Left | B |
| **P12** | Up | Select |
| **P13** | Down | Start |

### 5.2 Reading Button States

To read all buttons, software must perform two reads:

```
1. Write 0x10 to P1 (P14 low) -> Read direction buttons
2. Write 0x20 to P1 (P15 low) -> Read action buttons
```

**Important:** Bits return 0 when button is pressed, 1 when released (active low).

### 5.3 Button Interrupt

Button presses can generate an interrupt when:
- Any button transitions from not pressed (1) to pressed (0)
- P1 register must have both P14 and P15 high (0x30) to enable detection
- Interrupt vector: 0x0060 ( Joypad interrupt )

---

## 6. LCD SPECIFICATIONS

### 6.1 Display Parameters (Both Models)

| Parameter | Value |
|-----------|-------|
| **Resolution** | 160 x 144 pixels |
| **Aspect Ratio** | 10:9 |
| **Refresh Rate** | 59.73 Hz (V-Sync) |
| **Frame Time** | 16.74 ms |
| **Visible Scanlines** | 144 |
| **Total Scanlines** | 154 (includes V-Blank) |
| **Pixel Clock** | 4.194304 MHz |

### 6.2 DMG LCD Specifications

| Parameter | Specification |
|-----------|---------------|
| **Technology** | STN (Super-Twisted Nematic) LCD |
| **Colors** | 4 shades of gray |
| **Gray Levels** | Black, Dark Gray, Light Gray, White |
| **Pixel Density** | ~86 PPI (pixels per inch) |
| **Viewing Angle** | ~45 degrees optimal |
| **Response Time** | ~150-200 ms |
| **Contrast Control** | External potentiometer (variable resistor) |
| **Backlight** | None (reflective) |

#### DMG Gray Palette

| Value | Shade | Hex (approximate) |
|-------|-------|-------------------|
| 0 | White | #FFFFFF |
| 1 | Light Gray | #AAAAAA |
| 2 | Dark Gray | #555555 |
| 3 | Black | #000000 |

### 6.3 CGB LCD Specifications

| Parameter | Specification |
|-----------|---------------|
| **Technology** | Color TFT (Thin Film Transistor) LCD |
| **Color Depth** | 15-bit RGB (RGB555) |
| **Total Colors** | 32,768 (2^15) |
| **Displayable Colors** | 56 simultaneous (8 palettes x 4 colors x 2 banks) |
| **Pixel Density** | ~97 PPI (pixels per inch) |
| **Viewing Angle** | ~60 degrees optimal |
| **Response Time** | ~50-80 ms |
| **Contrast Control** | Automatic (no external adjustment) |
| **Backlight** | None (reflective with frontlight option) |

#### CGB Color Format

Each color is stored as 15-bit RGB555:
- Bits 0-4: Red (5 bits, 32 levels)
- Bits 5-9: Green (5 bits, 32 levels)
- Bits 10-14: Blue (5 bits, 32 levels)
- Bit 15: Not used

### 6.4 LCD Controller Registers

| Register | Address | Function |
|----------|---------|----------|
| **LCDC** | 0xFF40 | LCD Control |
| **STAT** | 0xFF41 | LCD Status |
| **SCY** | 0xFF42 | Scroll Y |
| **SCX** | 0xFF43 | Scroll X |
| **LY** | 0xFF44 | LCD Y Coordinate (current line) |
| **LYC** | 0xFF45 | LY Compare |
| **DMA** | 0xFF46 | DMA Transfer |
| **BGP** | 0xFF47 | Background Palette (DMG) |
| **OBP0** | 0xFF48 | Object Palette 0 (DMG) |
| **OBP1** | 0xFF49 | Object Palette 1 (DMG) |
| **WY** | 0xFF4A | Window Y Position |
| **WX** | 0xFF4B | Window X Position |
| **VBK** | 0xFF4F | VRAM Bank (CGB only) |
| **HDMA1-5** | 0xFF51-55 | HDMA Transfer (CGB only) |
| **RP** | 0xFF56 | Infrared Port (CGB only) |
| **BCPS** | 0xFF68 | BG Palette Index (CGB only) |
| **BCPD** | 0xFF69 | BG Palette Data (CGB only) |
| **OCPS** | 0xFF6A | OBJ Palette Index (CGB only) |
| **OCPD** | 0xFF6B | OBJ Palette Data (CGB only) |

---

## 7. COMPONENTS

### 7.1 CPU: Sharp LR35902

| Parameter | Specification |
|-----------|---------------|
| **Manufacturer** | Sharp Corporation |
| **Model** | LR35902 (custom Z80 derivative) |
| **Architecture** | 8-bit |
| **Instruction Set** | Z80-like with modifications |
| **Address Bus** | 16-bit (64KB addressable) |
| **Data Bus** | 8-bit |
| **Registers** | A, F, B, C, D, E, H, L, SP, PC |
| **Flags** | Z (Zero), N (Subtract), H (Half-carry), C (Carry) |

**Missing Z80 Features:**
- IX, IY index registers
- Alternate register set (AF', BC', DE', HL')
- 16-bit I/O port addressing

**Added Features:**
- SWAP instruction (nibble swap)
- LD HL,SP+n instruction
- HALT bug (DMG only, fixed in CGB)

### 7.2 Memory Map

| Address Range | Size | Content |
|---------------|------|---------|
| 0x0000-0x3FFF | 16KB | ROM Bank 0 (fixed) |
| 0x4000-0x7FFF | 16KB | ROM Bank N (switchable) |
| 0x8000-0x97FF | 8KB | Video RAM (VRAM) |
| 0x9800-0x9BFF | 1KB | BG Map Data 1 |
| 0x9C00-0x9FFF | 1KB | BG Map Data 2 |
| 0xA000-0xBFFF | 8KB | External RAM (cartridge) |
| 0xC000-0xCFFF | 4KB | Work RAM Bank 0 |
| 0xD000-0xDFFF | 4KB | Work RAM Bank 1 (CGB: switchable 1-7) |
| 0xE000-0xFDFF | 7.68KB | Echo RAM (mirror of C000-DDFF) |
| 0xFE00-0xFE9F | 160B | OAM (Sprite Attribute Table) |
| 0xFEA0-0xFEFF | 96B | Not usable |
| 0xFF00-0xFF7F | 128B | I/O Registers |
| 0xFF80-0xFFFE | 127B | High RAM (HRAM) |
| 0xFFFF | 1B | Interrupt Enable Register |

### 7.3 RAM Specifications

#### DMG RAM

| RAM Type | Size | Location |
|----------|------|----------|
| **Work RAM** | 8KB total | Internal |
| - Bank 0 | 4KB | 0xC000-0xCFFF |
| - Bank 1 | 4KB | 0xD000-0xDFFF |
| **Video RAM** | 8KB | 0x8000-0x9FFF |
| **OAM** | 160 bytes | 0xFE00-0xFE9F |
| **HRAM** | 127 bytes | 0xFF80-0xFFFE |

#### CGB RAM

| RAM Type | Size | Location |
|----------|------|----------|
| **Work RAM** | 32KB total | Internal |
| - Bank 0 | 4KB | 0xC000-0xCFFF (fixed) |
| - Banks 1-7 | 4KB each | 0xD000-0xDFFF (switchable) |
| **Video RAM** | 16KB total | 0x8000-0x9FFF (banked) |
| - Bank 0 | 8KB | Tile data |
| - Bank 1 | 8KB | Tile attributes |
| **OAM** | 160 bytes | 0xFE00-0xFE9F |
| **HRAM** | 127 bytes | 0xFF80-0xFFFE |

### 7.4 Screen Driver ICs

#### DMG LCD Driver

| Parameter | Specification |
|-----------|---------------|
| **Controller** | Custom Sharp LCD controller |
| **Display RAM** | Internal to LCD module |
| **Interface** | Parallel data bus |
| **Control Signals** | HSYNC, VSYNC, CLK, DATA |

#### CGB LCD Driver

| Parameter | Specification |
|-----------|---------------|
| **Controller** | Custom Sharp color LCD controller |
| **Display RAM** | Internal to LCD module |
| **Interface** | Parallel data bus |
| **Additional Features** | Hardware palette, priority bits |

### 7.5 Power Regulation

#### DMG Power Circuit

| Component | Function |
|-----------|----------|
| **DC-DC Converter** | Step-up to 5V and -19V |
| **5V Regulator** | Logic power supply |
| **-19V Generator** | LCD bias voltage |
| **Voltage Reference** | Contrast adjustment |

#### CGB Power Circuit

| Component | Function |
|-----------|----------|
| **DC-DC Converter** | Step-up to 5V |
| **5V Regulator** | Logic power supply |
| **3.3V Regulator** | Cartridge and I/O |
| **Voltage Monitor** | Battery level detection |

---

## 8. DMG vs CGB DIFFERENCES

### 8.1 Physical Comparison

| Parameter | DMG | CGB | Difference |
|-----------|-----|-----|------------|
| **Width** | 90 mm | 75 mm | -15 mm |
| **Height** | 148 mm | 133 mm | -15 mm |
| **Depth** | 32 mm | 27 mm | -5 mm |
| **Weight (no batteries)** | 220 g | 138 g | -82 g |
| **Batteries** | 4x AA | 2x AA | -2 cells |
| **Battery Voltage** | 6.0V | 3.0V | -3.0V |
| **Screen Size** | 66 mm | 59 mm | -7 mm |

### 8.2 Power Consumption Comparison

| Mode | DMG | CGB | Notes |
|------|-----|-----|-------|
| **Active (typical)** | 70-100 mA | 45-70 mA | CGB more efficient |
| **Idle** | ~50 mA | ~30 mA | CGB more efficient |
| **Battery Life** | 10-35 hrs | 10-30 hrs | Similar with fewer cells |
| **Power LED** | Red only | Green/Red | CGB has battery indicator |

### 8.3 Screen Technology Comparison

| Feature | DMG | CGB |
|---------|-----|-----|
| **Technology** | STN LCD | Color TFT LCD |
| **Colors** | 4 gray shades | 32,768 colors (15-bit) |
| **Simultaneous Colors** | 4 | 56 (8 palettes x 7) |
| **Resolution** | 160x144 | 160x144 |
| **Refresh Rate** | 59.73 Hz | 59.73 Hz |
| **Contrast Control** | Manual wheel | Automatic |
| **Pixel Density** | ~86 PPI | ~97 PPI |
| **Response Time** | ~150-200 ms | ~50-80 ms |
| **Backlight** | No | No (frontlight option available) |

### 8.4 Hardware Feature Comparison

| Feature | DMG | CGB | Notes |
|---------|-----|-----|-------|
| **CPU Speed** | 1.05 MHz | 1.05/2.10 MHz | CGB has double speed mode |
| **Work RAM** | 8KB | 32KB | CGB has 4x more RAM |
| **Video RAM** | 8KB | 16KB | CGB banked VRAM |
| **Infrared Port** | No | Yes | CGB wireless communication |
| **HDMA** | No | Yes | CGB hardware DMA transfers |
| **Color Palettes** | No | Yes | CGB 8 BG + 8 OBJ palettes |
| **Link Cable Fast Mode** | No | Yes | CGB 512Kbps mode |

### 8.5 PCB Revisions

#### DMG PCB Revisions

| Revision | Notes |
|----------|-------|
| **DMG-CPU-01** | Original release (1989) |
| **DMG-CPU-02** | Minor component changes |
| **DMG-CPU-03** | Improved power regulation |
| **DMG-CPU-04** | Cost reduction revision |
| **DMG-CPU-05** | Final DMG revision |
| **DMG-CPU-06** | Play It Loud series |

#### CGB PCB Revisions

| Revision | Notes |
|----------|-------|
| **CGB-CPU-01** | Original release (1998) |
| **CGB-CPU-02** | Minor component changes |
| **CGB-CPU-03** | Cost reduction revision |
| **CGB-CPU-04** | Final CGB revision |
| **CGB-CPU-05** | Later production |

### 8.6 Cartridge Compatibility

| Cartridge Type | DMG | CGB | Behavior |
|----------------|-----|-----|----------|
| **DMG Game** | Yes | Yes | CGB in DMG compatibility mode |
| **CGB Game** | No | Yes | DMG shows "This game pak is designed only for use on the Game Boy Color" |
| **Dual Mode** | Yes | Yes | Enhanced colors on CGB |

### 8.7 Audio Differences

| Feature | DMG | CGB |
|---------|-----|-----|
| **Channels** | 4 | 4 |
| **Output** | Mono/Stereo (headphones) | Mono/Stereo (headphones) |
| **Speaker** | Mono only | Mono only |
| **Wave RAM Bug** | Present | Fixed |

The CGB fixes a bug where reading wave RAM while channel 3 is playing returns 0xFF on DMG.

---

## 9. TECHNICAL NOTES

### 9.1 DMG Contrast Circuit

The DMG uses a voltage divider network controlled by a 16k ohm potentiometer to generate the LCD bias voltage (-19V typical). The contrast wheel adjusts the voltage between -10V and -20V, affecting the liquid crystal twist angle and thus the display contrast.

### 9.2 CGB Infrared Implementation

The CGB infrared port uses:
- **Transmitter:** 940nm IR LED with 100 ohm current limiting resistor
- **Receiver:** Phototransistor with pull-up resistor
- **Range:** Limited by LED power and receiver sensitivity to ~1-2 meters
- **Protocol:** Software-defined (no hardware encoding)

### 9.3 Link Cable Timing

Normal mode transfer timing:
- 1 byte = 8 bits
- Each bit = 122 clock cycles (CPU)
- Byte transfer = 976 clock cycles
- Rate = 1.05MHz / 976 = ~1076 bytes/second (theoretical)
- Actual = ~8192 bits/second = 1024 bytes/second

### 9.4 V-Blank Period

The V-Blank interval provides 10 scanlines (154 total - 144 visible):
- Duration: ~1.1 ms
- Available CPU cycles: ~1140
- Used for: OAM DMA, VRAM updates, game logic

---

## 10. REFERENCE INFORMATION

### 10.1 Official Part Numbers

| Component | DMG Part Number | CGB Part Number |
|-----------|-----------------|-----------------|
| **Main Board** | DMG-CPU-0x | CGB-CPU-0x |
| **LCD Module** | DMG-LCD | CGB-LCD |
| **Power Board** | DMG-DC-DC | CGB-DC-DC |
| **Button Board** | DMG-BTN | CGB-BTN |

### 10.2 Manufacturing Information

| Parameter | DMG | CGB |
|-----------|-----|-----|
| **Manufacturer** | Nintendo Co., Ltd. | Nintendo Co., Ltd. |
| **Release Date** | April 21, 1989 (JP) | October 21, 1998 (JP) |
| **Discontinued** | 2003 | 2003 |
| **Units Sold** | ~64 million | ~49 million |

---

*Document Version: 1.0*
*Last Updated: Technical specifications compiled from official Nintendo documentation, reverse engineering analysis, and hardware teardowns.*
