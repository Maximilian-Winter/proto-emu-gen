# GameBoy APU (Audio Processing Unit) Technical Specifications

## DMG (Original GameBoy) & CGB (GameBoy Color) Sound Hardware Reference

---

# 1. APU OVERVIEW

## Architecture and Capabilities

The GameBoy APU is a 4-channel programmable sound generator integrated into the SM83 CPU die. It produces all audio entirely through digital synthesis - no sample-based PCM playback (except Channel 3's limited wavetable).

| Feature | Specification |
|---------|---------------|
| **Channels** | 4 independent channels |
| **Channel Types** | 2× Square Wave, 1× Waveform, 1× Noise |
| **Output** | 4-bit digital per channel, mixed to analog |
| **Sample Rate** | ~2.1 MHz internal clock (CPU clock / 4) |
| **Output Pins** | SO1 (left), SO2 (right), Vin (external input) |
| **Volume Steps** | 16 levels per channel (4-bit) |

## Channel Summary

| Channel | Type | Features | Registers |
|---------|------|----------|-----------|
| CH1 | Square Wave | Sweep, Duty, Envelope, Length | NR10-NR14 |
| CH2 | Square Wave | Duty, Envelope, Length | NR20-NR24 |
| CH3 | Waveform | 32× 4-bit samples, Volume | NR30-NR34 |
| CH4 | Noise | LFSR, Envelope, Length | NR41-NR44 |

## Output Format (Digital to Analog)

The APU performs digital mixing before D/A conversion:

1. **Individual Channel Output**: Each channel produces 4-bit values (0-15)
2. **Digital Mixing**: Channels are summed digitally
3. **Master Volume**: NR50 applies left/right master volume (0-7)
4. **D/A Conversion**: Final mixed value converted to analog voltage

### Output Voltage Formula

```
Vout = (Digital_Sum / 60) × Vmax × (Master_Volume / 7)
```

Where Digital_Sum is the sum of all enabled channel outputs (max 60 = 4 channels × 15).

## Master Control Registers

### NR50 - Channel Control / ON-OFF / Volume (FF24)

| Bit | Name | Description |
|-----|------|-------------|
| 7 | Vin→SO2 | Vin to SO2 (right speaker) |
| 6-4 | SO2 Volume | Right channel master volume (0-7) |
| 3 | Vin→SO1 | Vin to SO1 (left speaker) |
| 2-0 | SO1 Volume | Left channel master volume (0-7) |

**Reset Value**: $77

### NR51 - Selection of Sound Output Terminal (FF25)

| Bit | Name | Description |
|-----|------|-------------|
| 7 | CH4→SO2 | Output sound 4 to SO2 (right) |
| 6 | CH3→SO2 | Output sound 3 to SO2 (right) |
| 5 | CH2→SO2 | Output sound 2 to SO2 (right) |
| 4 | CH1→SO2 | Output sound 1 to SO2 (right) |
| 3 | CH4→SO1 | Output sound 4 to SO1 (left) |
| 2 | CH3→SO1 | Output sound 3 to SO1 (left) |
| 1 | CH2→SO1 | Output sound 2 to SO1 (left) |
| 0 | CH1→SO1 | Output sound 1 to SO1 (left) |

**Reset Value**: $F3

### NR52 - Sound On/Off (FF26)

| Bit | Name | Description |
|-----|------|-------------|
| 7 | All Sound On | Master APU enable (0=off, 1=on) |
| 6-4 | - | Unused (read as 1 on DMG, 0 on CGB) |
| 3 | CH4 On | Channel 4 active status (read-only) |
| 2 | CH3 On | Channel 3 active status (read-only) |
| 1 | CH2 On | Channel 2 active status (read-only) |
| 0 | CH1 On | Channel 1 active status (read-only) |

**Reset Value**: $F1 (DMG), $F0 (CGB)

**Note**: Writing 0 to bit 7 clears all registers and stops the APU. Writing 1 re-enables it.

---

# 2. CHANNEL 1 - SQUARE WAVE WITH SWEEP

Channel 1 is a square wave generator with frequency sweep capability, making it ideal for bass slides and sound effects.

## NR10 - Sweep Register (FF10)

| Bit | Name | Description |
|-----|------|-------------|
| 7 | - | Unused |
| 6-4 | Sweep Time | Sweep period = n × (1/128) seconds (0=disabled) |
| 3 | Sweep Direction | 0=Add (frequency increase), 1=Subtract (frequency decrease) |
| 2-0 | Sweep Shift | Number of shift iterations (0-7) |

**Reset Value**: $80

### Sweep Operation Formula

```
frequency = frequency ± (frequency >> sweep_shift)
```

The sweep unit updates at intervals of `sweep_time × (1/128)` seconds.

**Sweep Disable**: Set sweep_time = 0 OR sweep_shift = 0

## NR11 - Sound Length/Wave Pattern Duty (FF11)

| Bit | Name | Description |
|-----|------|-------------|
| 7-6 | Wave Duty | Duty cycle selection (see table below) |
| 5-0 | Sound Length | Length = (64 - n) × (1/256) seconds |

**Reset Value**: $BF

### Duty Cycle Options

| Duty Value | Pattern | Description |
|------------|---------|-------------|
| 0 | 00000001 | 12.5% duty cycle |
| 1 | 10000001 | 25% duty cycle |
| 2 | 10000111 | 50% duty cycle |
| 3 | 01111110 | 75% duty cycle |

The duty pattern represents one period of the square wave (8 steps), where 1 = high, 0 = low.

## NR12 - Volume Envelope (FF12)

| Bit | Name | Description |
|-----|------|-------------|
| 7-4 | Initial Volume | Starting volume (0-15, 0=silent) |
| 3 | Envelope Direction | 0=Decrease, 1=Increase |
| 2-0 | Envelope Period | Step period = n × (1/64) seconds (0=disabled) |

**Reset Value**: $F3

### Envelope Operation

```
Every envelope_period × (1/64) seconds:
    If direction = 0 (decrease) AND volume > 0: volume--
    If direction = 1 (increase) AND volume < 15: volume++
```

## NR13 - Frequency Low (FF13)

| Bit | Name | Description |
|-----|------|-------------|
| 7-0 | Frequency Low | Lower 8 bits of 11-bit frequency value |

**Reset Value**: $C1

## NR14 - Frequency High / Control (FF14)

| Bit | Name | Description |
|-----|------|-------------|
| 7 | Initial | Trigger channel restart (1=trigger, auto-clears) |
| 6 | Counter/Consecutive | 1=Stop when length expires, 0=Ignore length |
| 5-3 | - | Unused |
| 2-0 | Frequency High | Upper 3 bits of 11-bit frequency value |

**Reset Value**: $87

## Frequency Calculation Formula

```
frequency_value = ((NR14 & 0x07) << 8) | NR13
output_frequency = 131072 / (2048 - frequency_value) Hz
```

### Frequency Range

| Frequency Value | Output Frequency |
|-----------------|------------------|
| 0 | 64 Hz |
| 2047 | 131072 Hz |

### Practical Frequency Examples

| Note | Frequency | Frequency Value (hex) |
|------|-----------|----------------------|
| C3 | 130.81 Hz | $16C |
| C4 | 261.63 Hz | $2D6 |
| A4 | 440.00 Hz | $440 |
| C5 | 523.25 Hz | $5AC |
| C6 | 1046.50 Hz | $B58 |

---

# 3. CHANNEL 2 - SQUARE WAVE

Channel 2 is identical to Channel 1 but without the frequency sweep unit. It provides a second independent square wave for harmonies and additional voices.

## NR20 - Not Used (FF15)

This register address is unused. Writing has no effect, reads return $FF.

## NR21 - Sound Length/Wave Pattern Duty (FF16)

| Bit | Name | Description |
|-----|------|-------------|
| 7-6 | Wave Duty | Duty cycle selection (same as CH1) |
| 5-0 | Sound Length | Length = (64 - n) × (1/256) seconds |

**Reset Value**: $3F

## NR22 - Volume Envelope (FF17)

| Bit | Name | Description |
|-----|------|-------------|
| 7-4 | Initial Volume | Starting volume (0-15) |
| 3 | Envelope Direction | 0=Decrease, 1=Increase |
| 2-0 | Envelope Period | Step period = n × (1/64) seconds |

**Reset Value**: $00

## NR23 - Frequency Low (FF18)

| Bit | Name | Description |
|-----|------|-------------|
| 7-0 | Frequency Low | Lower 8 bits of 11-bit frequency |

**Reset Value**: $00

## NR24 - Frequency High / Control (FF19)

| Bit | Name | Description |
|-----|------|-------------|
| 7 | Initial | Trigger channel restart |
| 6 | Counter/Consecutive | 1=Stop when length expires |
| 5-3 | - | Unused |
| 2-0 | Frequency High | Upper 3 bits of 11-bit frequency |

**Reset Value**: $BF

## Differences from Channel 1

| Feature | Channel 1 | Channel 2 |
|---------|-----------|-----------|
| Sweep Unit | Yes | No |
| NR10 Register | Sweep control | Unused |
| Use Case | Bass slides, effects | Melody, harmony |
| Frequency Range | Same | Same |

---

# 4. CHANNEL 3 - WAVEFORM

Channel 3 is a wavetable synthesizer that plays back user-defined 4-bit samples from Wave RAM. It can produce complex tones beyond simple square waves.

## NR30 - Sound On/Off (FF1A)

| Bit | Name | Description |
|-----|------|-------------|
| 7 | Sound Channel 3 Off | 0=Stop channel, 1=Enable channel |
| 6-0 | - | Unused |

**Reset Value**: $7F

**Important**: Channel 3 must be enabled (bit 7 = 1) before triggering. Wave RAM should be initialized before enabling.

## NR31 - Sound Length (FF1B)

| Bit | Name | Description |
|-----|------|-------------|
| 7-0 | Sound Length | Length = (256 - n) × (1/256) seconds |

**Reset Value**: $FF

Channel 3 has longer maximum length (1 second) compared to square channels (0.25 seconds).

## NR32 - Select Output Level (FF1C)

| Bit | Name | Description |
|-----|------|-------------|
| 7-6 | Select Output Level | Volume shift (see table below) |
| 5-0 | - | Unused |

**Reset Value**: $9F

### Volume Settings

| Value | Shift | Effective Volume |
|-------|-------|------------------|
| 0 | Mute | 0% (silent) |
| 1 | 0 | 100% (no shift) |
| 2 | 1 | 50% (shift right 1) |
| 3 | 2 | 25% (shift right 2) |

Note: Unlike channels 1, 2, and 4, Channel 3 does not have an envelope generator.

## NR33 - Frequency Low (FF1D)

| Bit | Name | Description |
|-----|------|-------------|
| 7-0 | Frequency Low | Lower 8 bits of 11-bit frequency |

**Reset Value**: $BF

## NR34 - Frequency High / Control (FF1E)

| Bit | Name | Description |
|-----|------|-------------|
| 7 | Initial | Trigger channel restart |
| 6 | Counter/Consecutive | 1=Stop when length expires |
| 5-3 | - | Unused |
| 2-0 | Frequency High | Upper 3 bits of 11-bit frequency |

**Reset Value**: $BB

## Wave RAM (FF30-FF3F)

Wave RAM contains 16 bytes storing 32 4-bit samples:

| Address | Samples |
|---------|---------|
| FF30 | Sample 0 (high nibble), Sample 1 (low nibble) |
| FF31 | Sample 2 (high nibble), Sample 3 (low nibble) |
| FF32 | Sample 4 (high nibble), Sample 5 (low nibble) |
| ... | ... |
| FF3F | Sample 30 (high nibble), Sample 31 (low nibble) |

### Wave RAM Format

```
Byte at FF30: [Sample 0 (4 bits)][Sample 1 (4 bits)]
Byte at FF31: [Sample 2 (4 bits)][Sample 3 (4 bits)]
...
```

### Sample Playback Mechanism

```
frequency_value = ((NR34 & 0x07) << 8) | NR33
output_frequency = 65536 / (2048 - frequency_value) Hz

Sample playback rate = output_frequency × 32 samples
```

The wave channel plays through all 32 samples at the specified frequency. When it reaches the end, it loops back to the beginning.

### Common Waveform Patterns

| Waveform | Description | Sample Values (hex) |
|----------|-------------|---------------------|
| Sine | Approximate sine wave | $01,$23,$45,$67,$89,$AB,$CD,$EF,$FE,$DC,$BA,$98,$76,$54,$32,$10 |
| Sawtooth | Ramp up | $01,$12,$23,$34,$45,$56,$67,$78,$89,$9A,$AB,$BC,$CD,$DE,$EF,$FF |
| Square | 50% duty | $FF,$FF,$FF,$FF,$00,$00,$00,$00,$FF,$FF,$FF,$FF,$00,$00,$00,$00 |
| Triangle | Linear ramp | $01,$23,$45,$67,$89,$AB,$CD,$EF,$FF,$ED,$CB,$A9,$87,$65,$43,$21 |

---

# 5. CHANNEL 4 - NOISE

Channel 4 generates pseudo-random noise using a Linear Feedback Shift Register (LFSR). Ideal for percussion, explosions, and sound effects.

## NR41 - Sound Length (FF20)

| Bit | Name | Description |
|-----|------|-------------|
| 7-6 | - | Unused |
| 5-0 | Sound Length | Length = (64 - n) × (1/256) seconds |

**Reset Value**: $FF

## NR42 - Volume Envelope (FF21)

| Bit | Name | Description |
|-----|------|-------------|
| 7-4 | Initial Volume | Starting volume (0-15) |
| 3 | Envelope Direction | 0=Decrease, 1=Increase |
| 2-0 | Envelope Period | Step period = n × (1/64) seconds |

**Reset Value**: $00

## NR43 - Polynomial Counter (FF22)

| Bit | Name | Description |
|-----|------|-------------|
| 7-4 | Shift Clock Frequency | Determines LFSR update rate |
| 3 | Counter Step/Width | 0=15-bit LFSR, 1=7-bit LFSR |
| 2-0 | Dividing Ratio | Base frequency divider |

**Reset Value**: $00

### LFSR Frequency Formula

```
If dividing_ratio = 0:
    base_frequency = 524288 Hz
Else:
    base_frequency = 524288 / dividing_ratio Hz

lfsr_frequency = base_frequency >> (shift_clock_frequency + 1)
```

### Dividing Ratio and Frequency Table

| Ratio | Base Frequency |
|-------|----------------|
| 0 | 524288 Hz |
| 1 | 524288 Hz |
| 2 | 262144 Hz |
| 3 | 174762.67 Hz |
| 4 | 131072 Hz |
| 5 | 104857.6 Hz |
| 6 | 87381.33 Hz |
| 7 | 74898.29 Hz |

### LFSR Modes

| Bit 3 | Mode | Period | Character |
|-------|------|--------|-----------|
| 0 | 15-bit | 32767 cycles | "Metallic" noise |
| 1 | 7-bit | 127 cycles | "Regular" noise |

## NR44 - Counter/Consecutive / Initial (FF23)

| Bit | Name | Description |
|-----|------|-------------|
| 7 | Initial | Trigger channel restart |
| 6 | Counter/Consecutive | 1=Stop when length expires |
| 5-0 | - | Unused |

**Reset Value**: $BF

## LFSR (Linear Feedback Shift Register) Operation

The LFSR generates pseudo-random sequences:

### 15-Bit LFSR
```
[14][13][12][11][10][9][8][7][6][5][4][3][2][1][0]
                                  |___________|
                                         XOR
                                          |
New bit = bit1 XOR bit0
Shift right, insert new bit at bit14
Output = bit0 (inverted)
```

### 7-Bit LFSR
```
[6][5][4][3][2][1][0]
          |________|
                 XOR
                  |
New bit = bit1 XOR bit0
Shift right, insert new bit at bit6
Output = bit0 (inverted)
```

### LFSR Implementation Notes

1. The LFSR updates at `lfsr_frequency` rate
2. Output is bit 0, inverted (0 = output high, 1 = output low)
3. When triggered, LFSR is reset to all 1s ($7FFF for 15-bit, $7F for 7-bit)
4. The 7-bit mode produces more tonal noise suitable for percussion

---

# 6. REGISTER MAP

## Complete APU Register Address Table

| Address | Register | Name | Reset Value |
|---------|----------|------|-------------|
| **Channel 1** ||||
| FF10 | NR10 | Sweep | $80 |
| FF11 | NR11 | Length/Duty | $BF |
| FF12 | NR12 | Volume Envelope | $F3 |
| FF13 | NR13 | Frequency Low | $C1 |
| FF14 | NR14 | Frequency High/Control | $87 |
| **Channel 2** ||||
| FF15 | NR20 | Not Used | $FF |
| FF16 | NR21 | Length/Duty | $3F |
| FF17 | NR22 | Volume Envelope | $00 |
| FF18 | NR23 | Frequency Low | $00 |
| FF19 | NR24 | Frequency High/Control | $BF |
| **Channel 3** ||||
| FF1A | NR30 | Sound On/Off | $7F |
| FF1B | NR31 | Sound Length | $FF |
| FF1C | NR32 | Output Level | $9F |
| FF1D | NR33 | Frequency Low | $BF |
| FF1E | NR34 | Frequency High/Control | $BB |
| **Channel 4** ||||
| FF1F | NR40 | Not Used | $FF |
| FF20 | NR41 | Sound Length | $FF |
| FF21 | NR42 | Volume Envelope | $00 |
| FF22 | NR43 | Polynomial Counter | $00 |
| FF23 | NR44 | Control | $BF |
| **Master Control** ||||
| FF24 | NR50 | Master Volume/Vin | $77 |
| FF25 | NR51 | Output Terminal Select | $F3 |
| FF26 | NR52 | Sound On/Off | $F1 (DMG), $F0 (CGB) |
| **Wave RAM** ||||
| FF30 | - | Wave Pattern RAM | Sample 0-1 |
| FF31 | - | Wave Pattern RAM | Sample 2-3 |
| FF32 | - | Wave Pattern RAM | Sample 4-5 |
| FF33 | - | Wave Pattern RAM | Sample 6-7 |
| FF34 | - | Wave Pattern RAM | Sample 8-9 |
| FF35 | - | Wave Pattern RAM | Sample 10-11 |
| FF36 | - | Wave Pattern RAM | Sample 12-13 |
| FF37 | - | Wave Pattern RAM | Sample 14-15 |
| FF38 | - | Wave Pattern RAM | Sample 16-17 |
| FF39 | - | Wave Pattern RAM | Sample 18-19 |
| FF3A | - | Wave Pattern RAM | Sample 20-21 |
| FF3B | - | Wave Pattern RAM | Sample 22-23 |
| FF3C | - | Wave Pattern RAM | Sample 24-25 |
| FF3D | - | Wave Pattern RAM | Sample 26-27 |
| FF3E | - | Wave Pattern RAM | Sample 28-29 |
| FF3F | - | Wave Pattern RAM | Sample 30-31 |

## Bit Definitions Summary

### NR10 (FF10) - Sweep
```
Bit 7: Unused
Bit 6-4: Sweep Time (0-7)
Bit 3: Sweep Direction (0=Add, 1=Sub)
Bit 2-0: Sweep Shift (0-7)
```

### NR11/NR21 (FF11/FF16) - Length/Duty
```
Bit 7-6: Duty (0=12.5%, 1=25%, 2=50%, 3=75%)
Bit 5-0: Length (0-63)
```

### NR12/NR17/NR22/NR42 (FF12/FF17/FF22/FF21) - Volume Envelope
```
Bit 7-4: Initial Volume (0-15)
Bit 3: Direction (0=Dec, 1=Inc)
Bit 2-0: Period (0-7)
```

### NR13/NR18/NR23/NR33 (FF13/FF18/FF1D) - Frequency Low
```
Bit 7-0: Frequency bits 7-0
```

### NR14/NR19/NR24/NR34 (FF14/FF19/FF1E) - Frequency High/Control
```
Bit 7: Trigger (1=Restart)
Bit 6: Counter/Consecutive (1=Use length)
Bit 5-3: Unused
Bit 2-0: Frequency bits 10-8
```

### NR30 (FF1A) - Channel 3 On/Off
```
Bit 7: Channel 3 Enable (1=On)
Bit 6-0: Unused
```

### NR32 (FF1C) - Channel 3 Volume
```
Bit 7-6: Volume (0=Mute, 1=100%, 2=50%, 3=25%)
Bit 5-0: Unused
```

### NR43 (FF22) - Polynomial Counter
```
Bit 7-4: Shift Clock Frequency (0-15)
Bit 3: Counter Step (0=15-bit, 1=7-bit)
Bit 2-0: Dividing Ratio (0-7)
```

### NR50 (FF24) - Master Volume
```
Bit 7: Vin→SO2
Bit 6-4: SO2 Volume (0-7)
Bit 3: Vin→SO1
Bit 2-0: SO1 Volume (0-7)
```

### NR51 (FF25) - Output Select
```
Bit 7: CH4→SO2
Bit 6: CH3→SO2
Bit 5: CH2→SO2
Bit 4: CH1→SO2
Bit 3: CH4→SO1
Bit 2: CH3→SO1
Bit 1: CH2→SO1
Bit 0: CH1→SO1
```

### NR52 (FF26) - Sound On/Off
```
Bit 7: All Sound On (1=Enable APU)
Bit 6-4: Unused (read 1 on DMG, 0 on CGB)
Bit 3: CH4 Active (read-only)
Bit 2: CH3 Active (read-only)
Bit 1: CH2 Active (read-only)
Bit 0: CH1 Active (read-only)
```

---

# 7. DMG vs CGB DIFFERENCES

## Hardware Differences Summary

| Feature | DMG | CGB | Notes |
|---------|-----|-----|-------|
| **CPU Clock** | 4.194304 MHz | 4.194304/8.388608 MHz | CGB has double-speed mode |
| **APU Clock** | 1.048576 MHz | 1.048576 MHz | Same base rate |
| **Wave RAM Access** | Restricted while playing | Always accessible | Major difference |
| **Wave RAM on Read** | Returns $FF while playing | Returns actual value | CGB more flexible |
| **NR52 Unused Bits** | Read as 1 | Read as 0 | Minor difference |
| **Reset Value** | $F1 | $F0 | Bit 4 difference |

## Detailed Differences

### Wave RAM Access (Critical Difference)

**DMG Behavior:**
- Wave RAM cannot be read while Channel 3 is playing
- Reads return $FF when CH3 is active
- Writes may be ignored or corrupted when CH3 is active
- Recommended: Only access Wave RAM when CH3 is disabled (NR30 bit 7 = 0)

**CGB Behavior:**
- Wave RAM is always accessible
- Reads return actual values regardless of CH3 state
- Writes work correctly even while CH3 is playing
- Channel 3 uses an internal buffer for playback

### Channel 3 Buffer Behavior

**DMG:**
- Channel 3 reads directly from Wave RAM during playback
- Each sample byte is read once per 32-sample cycle
- CPU access conflicts with channel playback

**CGB:**
- Channel 3 copies Wave RAM to internal buffer on trigger
- Buffer is used for playback, freeing Wave RAM for CPU access
- Allows dynamic waveform updates during playback

### Power-On/Reset Behavior

| Register | DMG Reset | CGB Reset |
|----------|-----------|-----------|
| NR10 | $80 | $80 |
| NR11 | $BF | $BF |
| NR12 | $F3 | $F3 |
| NR13 | $C1 | $C1 |
| NR14 | $87 | $87 |
| NR21 | $3F | $3F |
| NR22 | $00 | $00 |
| NR23 | $00 | $00 |
| NR24 | $BF | $BF |
| NR30 | $7F | $7F |
| NR31 | $FF | $FF |
| NR32 | $9F | $9F |
| NR33 | $BF | $BF |
| NR34 | $BB | $BB |
| NR41 | $FF | $FF |
| NR42 | $00 | $00 |
| NR43 | $00 | $00 |
| NR44 | $BF | $BF |
| NR50 | $77 | $77 |
| NR51 | $F3 | $F3 |
| NR52 | $F1 | $F0 |

### Compatibility Notes

1. **For DMG Compatibility**: Always disable Channel 3 before writing Wave RAM
2. **For CGB Features**: Can update Wave RAM during playback for dynamic sounds
3. **Audio Emulation**: Must implement both behaviors for accurate emulation

---

# APPENDIX A: FREQUENCY CALCULATION REFERENCE

## Square Channels (1 & 2) Frequency Table

```
f = 131072 / (2048 - x) Hz
```

| Note | Octave | Frequency (Hz) | x (dec) | x (hex) |
|------|--------|----------------|---------|---------|
| C | 2 | 65.41 | 44 | $002C |
| C# | 2 | 69.30 | 155 | $009B |
| D | 2 | 73.42 | 263 | $0107 |
| D# | 2 | 77.78 | 368 | $0170 |
| E | 2 | 82.41 | 470 | $01D6 |
| F | 2 | 87.31 | 569 | $0239 |
| F# | 2 | 92.50 | 665 | $0299 |
| G | 2 | 98.00 | 758 | $02F6 |
| G# | 2 | 103.83 | 848 | $0350 |
| A | 2 | 110.00 | 936 | $03A8 |
| A# | 2 | 116.54 | 1021 | $03FD |
| B | 2 | 123.47 | 1104 | $0450 |
| C | 3 | 130.81 | 1185 | $04A1 |
| C# | 3 | 138.59 | 1263 | $04EF |
| D | 3 | 146.83 | 1339 | $053B |
| D# | 3 | 155.56 | 1413 | $0585 |
| E | 3 | 164.81 | 1485 | $05CD |
| F | 3 | 174.61 | 1555 | $0613 |
| F# | 3 | 185.00 | 1623 | $0657 |
| G | 3 | 196.00 | 1689 | $0699 |
| G# | 3 | 207.65 | 1753 | $06D9 |
| A | 3 | 220.00 | 1816 | $0718 |
| A# | 3 | 233.08 | 1877 | $0755 |
| B | 3 | 246.94 | 1936 | $0790 |
| C | 4 | 261.63 | 1994 | $07CA |
| C# | 4 | 277.18 | 2050 | $0802 |
| D | 4 | 293.66 | 1102 | $044E |
| D# | 4 | 311.13 | 1165 | $048D |
| E | 4 | 329.63 | 1227 | $04CB |
| F | 4 | 349.23 | 1287 | $0507 |
| F# | 4 | 369.99 | 1346 | $0542 |
| G | 4 | 392.00 | 1403 | $057B |
| G# | 4 | 415.30 | 1459 | $05B3 |
| A | 4 | 440.00 | 1514 | $05EA |
| A# | 4 | 466.16 | 1567 | $061F |
| B | 4 | 493.88 | 1619 | $0653 |
| C | 5 | 523.25 | 1670 | $0686 |
| C# | 5 | 554.37 | 1719 | $06B7 |
| D | 5 | 587.33 | 1767 | $06E7 |
| D# | 5 | 622.25 | 1814 | $0716 |
| E | 5 | 659.25 | 1860 | $0744 |
| F | 5 | 698.46 | 1905 | $0771 |
| F# | 5 | 739.99 | 1949 | $079D |
| G | 5 | 783.99 | 1992 | $07C8 |
| G# | 5 | 830.61 | 2034 | $07F2 |
| A | 5 | 880.00 | 2075 | $081B |
| A# | 5 | 932.33 | 2115 | $0843 |
| B | 5 | 987.77 | 2155 | $086B |
| C | 6 | 1046.50 | 2193 | $0891 |

## Wave Channel Frequency Table

```
f = 65536 / (2048 - x) Hz
```

The wave channel has half the frequency range of square channels.

---

# APPENDIX B: TIMING REFERENCE

## Frame Sequencer

The APU contains a frame sequencer that clocks length counters, sweep unit, and envelope at specific intervals:

| Step | Length | Sweep | Envelope |
|------|--------|-------|----------|
| 0 | Clock | - | - |
| 1 | - | - | - |
| 2 | Clock | Clock | - |
| 3 | - | - | - |
| 4 | Clock | - | - |
| 5 | - | - | - |
| 6 | Clock | Clock | - |
| 7 | - | - | Clock |

- Frame sequencer runs at 512 Hz (8192 CPU cycles)
- One complete cycle = 8 steps = 4096 CPU cycles
- Length counter clocks every 2 steps (256 Hz)
- Sweep unit clocks every 4 steps (128 Hz)
- Envelope clocks every 8 steps (64 Hz)

## Length Counter Timing

| Channel | Length Range | Time Resolution | Max Length |
|---------|--------------|-----------------|------------|
| CH1, CH2, CH4 | 0-63 | 1/256 sec | 0.25 sec |
| CH3 | 0-255 | 1/256 sec | 1.0 sec |

## Envelope Timing

```
Envelope period = n × (1/64) seconds
n = 0: Envelope disabled
n = 1-7: Step every n/64 seconds
```

## Sweep Timing

```
Sweep period = n × (1/128) seconds
n = 0: Sweep disabled
n = 1-7: Update every n/128 seconds
```

---

# APPENDIX C: PROGRAMMING EXAMPLES

## Initialize APU

```asm
; Enable APU
ld a, $80
ld [$FF26], a

; Set master volume (max both channels)
ld a, $77
ld [$FF24], a

; Enable all channels to both outputs
ld a, $F3
ld [$FF25], a
```

## Play Note on Channel 1

```asm
; Set sweep (no sweep)
ld a, $00
ld [$FF10], a

; Set duty (50%) and length
ld a, $80
ld [$FF11], a

; Set envelope (max volume, no sweep)
ld a, $F0
ld [$FF12], a

; Set frequency (C4 = $2D6)
ld a, $D6
ld [$FF13], a

; Trigger with frequency high
ld a, $87
ld [$FF14], a
```

## Initialize Wave RAM with Sine Approximation

```asm
; Disable channel 3
ld a, $00
ld [$FF1A], a

; Write sine-like wave pattern
ld hl, $FF30
ld a, $01
ld [hl+], a
ld a, $23
ld [hl+], a
ld a, $45
ld [hl+], a
ld a, $67
ld [hl+], a
ld a, $89
ld [hl+], a
ld a, $AB
ld [hl+], a
ld a, $CD
ld [hl+], a
ld a, $EF
ld [hl+], a
ld a, $FE
ld [hl+], a
ld a, $DC
ld [hl+], a
ld a, $BA
ld [hl+], a
ld a, $98
ld [hl+], a
ld a, $76
ld [hl+], a
ld a, $54
ld [hl+], a
ld a, $32
ld [hl+], a
ld a, $10
ld [hl+], a

; Enable channel 3
ld a, $80
ld [$FF1A], a
```

---

*Document Version: 1.0*
*Last Updated: Technical reference for GameBoy APU development*
*Sources: Nintendo GameBoy Programming Manual, Pan Docs, GB Dev Wiki*
