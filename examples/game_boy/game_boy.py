"""
game_boy.py -- Nintendo Game Boy (DMG) system definition.

Complete Game Boy using the proto framework with ALL code transpiled
from Python. Features:
  - Sharp SM83 CPU with all 500 opcodes transpiled via @cpu.opcode()
  - Full 64KB memory map with MBC1/3/5 banking
  - PPU scanline renderer (BG + window + sprites) -- transpiled
  - APU 4-channel audio (2 square, 1 wave, 1 noise) -- transpiled
  - Timer with DIV/TIMA/TMA/TAC -- transpiled
  - Joypad input -- transpiled
  - External hooks: render_frame(), audio_push(), poll_input()
  - RegisterBlock handlers -- transpiled via @block.on_read/@block.on_write
  - MBC handlers -- transpiled via @mbc.bank_resolver/@mbc.on_write
  - Step preamble (interrupt dispatch) -- transpiled
  - Tick handlers -- transpiled
"""

import os
import sys as _sys

from proto import (
    MemoryRegion, MemoryBank, MemoryBus, MemoryController,
    MemoryAccessLevel, Handler, HandlerType,
    Clock, Chip, Board, RegisterBlock, CPUDefinition,
    BoardCodeGenerator,
)

# ===================================================================
# Clock
# ===================================================================
master_clock = Clock("master", 4_194_304)

# ===================================================================
# PPU Chip
# ===================================================================
ppu_chip = Chip("ppu", clock=master_clock, comment="Pixel Processing Unit")

# PPU state
ppu_chip.add_state("dot_counter", "uint32_t", "0", "Dot counter within line")
ppu_chip.add_state("mode", "uint8_t", "2", "PPU mode (0-3)")
ppu_chip.add_state("frame_ready", "bool", "false", "Frame complete flag")
ppu_chip.add_state("line_dots", "uint32_t", "0", "Accumulated dots this line")
ppu_chip.add_state("show_bg", "bool", "true", "Debug: show background layer")
ppu_chip.add_state("show_sprites", "bool", "true", "Debug: show sprite layer")

# PPU internal memory
ppu_vram = MemoryRegion("vram", 8192, comment="Video RAM")
ppu_oam = MemoryRegion("oam", 160, comment="Object Attribute Memory")
ppu_chip.add_internal_memory(ppu_vram)
ppu_chip.add_internal_memory(ppu_oam)

# Framebuffer: 160x144 pixels, 1 byte per pixel (palette index) = 23040 bytes
ppu_fb = MemoryRegion("framebuffer", 23040, comment="160x144 pixel framebuffer")
ppu_chip.add_internal_memory(ppu_fb)

# PPU I/O registers (FF40-FF4B)
ppu_io = RegisterBlock("ppu_io", base_addr=0xFF40, size=12)
ppu_io.bind(0, "lcdc", default="0x91", comment="LCD Control")
ppu_io.bind(1, "stat", default="0", comment="LCD Status")
ppu_io.bind(2, "scy", comment="Scroll Y")
ppu_io.bind(3, "scx", comment="Scroll X")
ppu_io.bind(4, "ly", comment="LCD Y coordinate", read_only=True)
ppu_io.bind(5, "lyc", comment="LY Compare")
ppu_io.bind(6, "dma", comment="OAM DMA transfer", write_only=True)
ppu_io.bind(7, "bgp", default="0xFC", comment="BG Palette")
ppu_io.bind(8, "obp0", comment="Object Palette 0")
ppu_io.bind(9, "obp1", comment="Object Palette 1")
ppu_io.bind(10, "wy", comment="Window Y")
ppu_io.bind(11, "wx", comment="Window X")

# LY read handler (transpiled)
@ppu_io.on_read(4)
def ppu_ly_read(chip):
    return chip.ly

# DMA write handler (transpiled)
@ppu_io.on_write(6)
def ppu_dma_write(chip, val):
    chip.dma = val
    src: uint16 = uint16(val << 8)
    for i in range(160):
        chip.oam[i] = mem_read(uint16(src + i))

ppu_chip.add_register_block(ppu_io)

# ===================================================================
# APU Chip
# ===================================================================
apu_chip = Chip("apu", clock=master_clock, comment="Audio Processing Unit")

# Channel 1 (square + sweep)
apu_chip.add_state("ch1_enabled", "bool", "false")
apu_chip.add_state("ch1_dac", "bool", "false")
apu_chip.add_state("ch1_length", "uint16_t", "0")
apu_chip.add_state("ch1_volume", "uint8_t", "0")
apu_chip.add_state("ch1_env_timer", "uint8_t", "0")
apu_chip.add_state("ch1_env_dir", "uint8_t", "0")
apu_chip.add_state("ch1_env_pace", "uint8_t", "0")
apu_chip.add_state("ch1_freq", "uint16_t", "0")
apu_chip.add_state("ch1_freq_timer", "int32_t", "0")
apu_chip.add_state("ch1_duty", "uint8_t", "0")
apu_chip.add_state("ch1_duty_pos", "uint8_t", "0")
apu_chip.add_state("ch1_length_en", "bool", "false")
apu_chip.add_state("ch1_sweep_pace", "uint8_t", "0")
apu_chip.add_state("ch1_sweep_dir", "uint8_t", "0")
apu_chip.add_state("ch1_sweep_step", "uint8_t", "0")
apu_chip.add_state("ch1_sweep_timer", "uint8_t", "0")
apu_chip.add_state("ch1_sweep_en", "bool", "false")
apu_chip.add_state("ch1_sweep_freq", "uint16_t", "0")
apu_chip.add_state("ch1_sweep_shadow", "uint16_t", "0")
apu_chip.add_state("ch1_sweep_enabled", "bool", "false")

# Channel 2 (square)
apu_chip.add_state("ch2_enabled", "bool", "false")
apu_chip.add_state("ch2_dac", "bool", "false")
apu_chip.add_state("ch2_length", "uint16_t", "0")
apu_chip.add_state("ch2_volume", "uint8_t", "0")
apu_chip.add_state("ch2_env_timer", "uint8_t", "0")
apu_chip.add_state("ch2_env_dir", "uint8_t", "0")
apu_chip.add_state("ch2_env_pace", "uint8_t", "0")
apu_chip.add_state("ch2_freq", "uint16_t", "0")
apu_chip.add_state("ch2_freq_timer", "int32_t", "0")
apu_chip.add_state("ch2_duty", "uint8_t", "0")
apu_chip.add_state("ch2_duty_pos", "uint8_t", "0")
apu_chip.add_state("ch2_length_en", "bool", "false")

# Channel 3 (wave)
apu_chip.add_state("ch3_enabled", "bool", "false")
apu_chip.add_state("ch3_dac", "bool", "false")
apu_chip.add_state("ch3_length", "uint16_t", "0")
apu_chip.add_state("ch3_volume_code", "uint8_t", "0")
apu_chip.add_state("ch3_freq", "uint16_t", "0")
apu_chip.add_state("ch3_freq_timer", "int32_t", "0")
apu_chip.add_state("ch3_sample_pos", "uint8_t", "0")
apu_chip.add_state("ch3_length_en", "bool", "false")

# Channel 4 (noise)
apu_chip.add_state("ch4_enabled", "bool", "false")
apu_chip.add_state("ch4_dac", "bool", "false")
apu_chip.add_state("ch4_length", "uint16_t", "0")
apu_chip.add_state("ch4_volume", "uint8_t", "0")
apu_chip.add_state("ch4_env_timer", "uint8_t", "0")
apu_chip.add_state("ch4_env_dir", "uint8_t", "0")
apu_chip.add_state("ch4_env_pace", "uint8_t", "0")
apu_chip.add_state("ch4_freq_timer", "int32_t", "0")
apu_chip.add_state("ch4_lfsr", "uint16_t", "0x7FFF")
apu_chip.add_state("ch4_width", "uint8_t", "0")
apu_chip.add_state("ch4_clock_shift", "uint8_t", "0")
apu_chip.add_state("ch4_divisor_code", "uint8_t", "0")
apu_chip.add_state("ch4_length_en", "bool", "false")

# Frame sequencer
apu_chip.add_state("frame_seq_counter", "int32_t", "0")
apu_chip.add_state("frame_seq_step", "uint8_t", "0")
apu_chip.add_state("apu_enabled", "bool", "true")

# Sample buffer and downsampling
apu_chip.add_state("sample_counter", "int32_t", "0")
apu_chip.add_state("sample_count", "uint32_t", "0")
apu_chip.add_state("sample_buffer", "int16_t[4096]", "0", "Stereo sample buffer (2048 pairs)")

# Debug mute flags
apu_chip.add_state("debug_ch1_mute", "bool", "false")
apu_chip.add_state("debug_ch2_mute", "bool", "false")
apu_chip.add_state("debug_ch3_mute", "bool", "false")
apu_chip.add_state("debug_ch4_mute", "bool", "false")

# Wave RAM (internal memory on APU chip)
wave_ram = MemoryRegion("wave_ram", 16, comment="Wave pattern RAM")
apu_chip.add_internal_memory(wave_ram)

# APU I/O registers (FF10-FF3F)
apu_io = RegisterBlock("apu_io", base_addr=0xFF10, size=48)
# NR10-NR14 (Channel 1)
apu_io.bind(0, "nr10", comment="Ch1 Sweep")
apu_io.bind(1, "nr11", comment="Ch1 Length/Duty")
apu_io.bind(2, "nr12", comment="Ch1 Volume/Envelope")
apu_io.bind(3, "nr13", comment="Ch1 Freq Low")
apu_io.bind(4, "nr14", comment="Ch1 Freq Hi/Control")
# NR21-NR24 (Channel 2)
apu_io.bind(6, "nr21", comment="Ch2 Length/Duty")
apu_io.bind(7, "nr22", comment="Ch2 Volume/Envelope")
apu_io.bind(8, "nr23", comment="Ch2 Freq Low")
apu_io.bind(9, "nr24", comment="Ch2 Freq Hi/Control")
# NR30-NR34 (Channel 3)
apu_io.bind(10, "nr30", comment="Ch3 DAC Enable")
apu_io.bind(11, "nr31", comment="Ch3 Length")
apu_io.bind(12, "nr32", comment="Ch3 Volume")
apu_io.bind(13, "nr33", comment="Ch3 Freq Low")
apu_io.bind(14, "nr34", comment="Ch3 Freq Hi/Control")
# NR41-NR44 (Channel 4)
apu_io.bind(16, "nr41", comment="Ch4 Length")
apu_io.bind(17, "nr42", comment="Ch4 Volume/Envelope")
apu_io.bind(18, "nr43", comment="Ch4 Polynomial Counter")
apu_io.bind(19, "nr44", comment="Ch4 Control")
# NR50-NR52
apu_io.bind(20, "nr50", comment="Master Volume")
apu_io.bind(21, "nr51", comment="Sound Panning")
apu_io.bind(22, "nr52", comment="Sound On/Off")

# NR52 read handler (transpiled)
@apu_io.on_read(22)
def apu_nr52_read(chip):
    r: uint8 = chip.nr52 & 128
    if chip.ch1_enabled:
        r = r | 1
    if chip.ch2_enabled:
        r = r | 2
    if chip.ch3_enabled:
        r = r | 4
    if chip.ch4_enabled:
        r = r | 8
    return uint8(r | 112)

# NR10 write (transpiled)
@apu_io.on_write(0)
def apu_nr10_write(chip, val):
    chip.nr10 = val
    chip.ch1_sweep_pace = (val >> 4) & 7
    chip.ch1_sweep_dir = (val >> 3) & 1
    chip.ch1_sweep_step = val & 7

# NR11 write
@apu_io.on_write(1)
def apu_nr11_write(chip, val):
    chip.nr11 = val
    chip.ch1_duty = (val >> 6) & 3
    chip.ch1_length = 64 - (val & 63)

# NR12 write
@apu_io.on_write(2)
def apu_nr12_write(chip, val):
    chip.nr12 = val
    chip.ch1_dac = 1 if (val & 248) else 0
    if not chip.ch1_dac:
        chip.ch1_enabled = 0

# NR13 write
@apu_io.on_write(3)
def apu_nr13_write(chip, val):
    chip.nr13 = val
    chip.ch1_freq = uint16((chip.ch1_freq & 1792) | val)

# NR14 write: trigger channel 1
@apu_io.on_write(4)
def apu_nr14_write(chip, val):
    chip.nr14 = val
    chip.ch1_freq = uint16((chip.ch1_freq & 255) | (uint16(val & 7) << 8))
    chip.ch1_length_en = 1 if (val & 64) else 0
    if val & 128:
        chip.ch1_enabled = chip.ch1_dac
        if chip.ch1_length == 0:
            chip.ch1_length = 64
        chip.ch1_freq_timer = (2048 - chip.ch1_freq) * 4
        chip.ch1_volume = (chip.nr12 >> 4) & 15
        chip.ch1_env_dir = (chip.nr12 >> 3) & 1
        chip.ch1_env_pace = chip.nr12 & 7
        chip.ch1_env_timer = chip.ch1_env_pace
        chip.ch1_sweep_freq = chip.ch1_freq
        chip.ch1_sweep_timer = chip.ch1_sweep_pace if chip.ch1_sweep_pace else 8
        chip.ch1_sweep_en = 1 if (chip.ch1_sweep_pace > 0) or (chip.ch1_sweep_step > 0) else 0

# NR21 write
@apu_io.on_write(6)
def apu_nr21_write(chip, val):
    chip.nr21 = val
    chip.ch2_duty = (val >> 6) & 3
    chip.ch2_length = 64 - (val & 63)

# NR22 write
@apu_io.on_write(7)
def apu_nr22_write(chip, val):
    chip.nr22 = val
    chip.ch2_dac = 1 if (val & 248) else 0
    if not chip.ch2_dac:
        chip.ch2_enabled = 0

# NR23 write
@apu_io.on_write(8)
def apu_nr23_write(chip, val):
    chip.nr23 = val
    chip.ch2_freq = uint16((chip.ch2_freq & 1792) | val)

# NR24 write: trigger channel 2
@apu_io.on_write(9)
def apu_nr24_write(chip, val):
    chip.nr24 = val
    chip.ch2_freq = uint16((chip.ch2_freq & 255) | (uint16(val & 7) << 8))
    chip.ch2_length_en = 1 if (val & 64) else 0
    if val & 128:
        chip.ch2_enabled = chip.ch2_dac
        if chip.ch2_length == 0:
            chip.ch2_length = 64
        chip.ch2_freq_timer = (2048 - chip.ch2_freq) * 4
        chip.ch2_volume = (chip.nr22 >> 4) & 15
        chip.ch2_env_dir = (chip.nr22 >> 3) & 1
        chip.ch2_env_pace = chip.nr22 & 7
        chip.ch2_env_timer = chip.ch2_env_pace

# NR30 write
@apu_io.on_write(10)
def apu_nr30_write(chip, val):
    chip.nr30 = val
    chip.ch3_dac = 1 if (val & 128) else 0
    if not chip.ch3_dac:
        chip.ch3_enabled = 0

# NR31 write
@apu_io.on_write(11)
def apu_nr31_write(chip, val):
    chip.nr31 = val
    chip.ch3_length = 256 - val

# NR32 write
@apu_io.on_write(12)
def apu_nr32_write(chip, val):
    chip.nr32 = val
    chip.ch3_volume_code = (val >> 5) & 3

# NR33 write
@apu_io.on_write(13)
def apu_nr33_write(chip, val):
    chip.nr33 = val
    chip.ch3_freq = uint16((chip.ch3_freq & 1792) | val)

# NR34 write: trigger channel 3
@apu_io.on_write(14)
def apu_nr34_write(chip, val):
    chip.nr34 = val
    chip.ch3_freq = uint16((chip.ch3_freq & 255) | (uint16(val & 7) << 8))
    chip.ch3_length_en = 1 if (val & 64) else 0
    if val & 128:
        chip.ch3_enabled = chip.ch3_dac
        if chip.ch3_length == 0:
            chip.ch3_length = 256
        chip.ch3_freq_timer = (2048 - chip.ch3_freq) * 2
        chip.ch3_sample_pos = 0

# NR41 write
@apu_io.on_write(16)
def apu_nr41_write(chip, val):
    chip.nr41 = val
    chip.ch4_length = 64 - (val & 63)

# NR42 write
@apu_io.on_write(17)
def apu_nr42_write(chip, val):
    chip.nr42 = val
    chip.ch4_dac = 1 if (val & 248) else 0
    if not chip.ch4_dac:
        chip.ch4_enabled = 0

# NR43 write
@apu_io.on_write(18)
def apu_nr43_write(chip, val):
    chip.nr43 = val
    chip.ch4_clock_shift = (val >> 4) & 15
    chip.ch4_width = (val >> 3) & 1
    chip.ch4_divisor_code = val & 7

# NR44 write: trigger channel 4
@apu_io.on_write(19)
def apu_nr44_write(chip, val):
    chip.nr44 = val
    chip.ch4_length_en = 1 if (val & 64) else 0
    if val & 128:
        chip.ch4_enabled = chip.ch4_dac
        if chip.ch4_length == 0:
            chip.ch4_length = 64
        chip.ch4_lfsr = 32767
        chip.ch4_volume = (chip.nr42 >> 4) & 15
        chip.ch4_env_dir = (chip.nr42 >> 3) & 1
        chip.ch4_env_pace = chip.nr42 & 7
        chip.ch4_env_timer = chip.ch4_env_pace
        chip.ch4_clock_shift = (chip.nr43 >> 4) & 15
        chip.ch4_width = (chip.nr43 >> 3) & 1
        chip.ch4_divisor_code = chip.nr43 & 7

apu_chip.add_register_block(apu_io)

# ===================================================================
# Timer Chip
# ===================================================================
timer_chip = Chip("timer", clock=master_clock, comment="Timer")
timer_chip.add_state("div_counter", "uint16_t", "0", "DIV internal counter")
timer_chip.add_state("tima_counter", "int32_t", "0", "TIMA cycle counter")

timer_io = RegisterBlock("timer_io", base_addr=0xFF04, size=4)
timer_io.bind(0, "div", comment="Divider register")
timer_io.bind(1, "tima", comment="Timer counter")
timer_io.bind(2, "tma", comment="Timer modulo")
timer_io.bind(3, "tac", comment="Timer control")

# DIV read returns upper byte of internal counter (transpiled)
@timer_io.on_read(0)
def timer_div_read(chip):
    return uint8(chip.div_counter >> 8)

# DIV write resets counter (transpiled)
@timer_io.on_write(0)
def timer_div_write(chip, val):
    chip.div_counter = 0
    chip.div = 0

timer_chip.add_register_block(timer_io)

# ===================================================================
# Joypad Chip
# ===================================================================
joypad_chip = Chip("joypad", clock=master_clock, comment="Joypad")
joypad_chip.add_state("button_state", "uint8_t", "0xFF", "Button state (active low)")
joypad_chip.add_state("direction_state", "uint8_t", "0xFF", "Direction state (active low)")

joypad_io = RegisterBlock("joypad_io", base_addr=0xFF00, size=1)
joypad_io.bind(0, "p1", comment="Joypad register")

# Joypad read handler (transpiled)
@joypad_io.on_read(0)
def joypad_read(chip):
    sel: uint8 = chip.p1 & 48
    r: uint8 = sel | 192
    if not (sel & 16):
        r = r | (chip.direction_state & 15)
    elif not (sel & 32):
        r = r | (chip.button_state & 15)
    else:
        r = r | 15
    return r

joypad_chip.add_register_block(joypad_io)

# ===================================================================
# CPU Chip
# ===================================================================
cpu_chip = Chip("cpu", clock=master_clock, comment="Sharp SM83 CPU")

# CPU-managed state (interrupt, halt, MBC)
cpu_chip.add_state("ime", "bool", "false", "Interrupt master enable")
cpu_chip.add_state("ime_delay", "uint8_t", "0", "EI delay counter")
cpu_chip.add_state("interrupt_enable", "uint8_t", "0", "IE register")
cpu_chip.add_state("interrupt_flags", "uint8_t", "0", "IF register")
cpu_chip.add_state("mbc_type", "uint8_t", "0", "MBC type (0=ROM, 1=MBC1, 3=MBC3, 5=MBC5)")
cpu_chip.add_state("rom_bank", "uint16_t", "1", "Current ROM bank")
cpu_chip.add_state("ram_bank", "uint8_t", "0", "Current RAM bank")
cpu_chip.add_state("ram_enabled", "bool", "false", "Cart RAM enabled")
cpu_chip.add_state("mbc_mode", "uint8_t", "0", "MBC1 banking mode")

# ===================================================================
# Memory Regions
# ===================================================================
rom_region = MemoryRegion("rom", 0, access=MemoryAccessLevel.ReadOnly,
                          comment="Cartridge ROM (dynamic)")
cart_ram_region = MemoryRegion("cart_ram", 0,
                               comment="Cartridge RAM (dynamic)")
wram = MemoryRegion("wram", 8192, comment="Work RAM")
hram = MemoryRegion("hram", 127, comment="High RAM")

cpu_chip.add_internal_memory(rom_region)
cpu_chip.add_internal_memory(cart_ram_region)
cpu_chip.add_internal_memory(wram)
cpu_chip.add_internal_memory(hram)

# ===================================================================
# ROM Banking (MBC) -- all transpiled
# ===================================================================
rom_fixed_bank = MemoryBank("rom_fixed", region=rom_region,
                            bank_size=16384, max_banks=1, default_bank=0)
rom_banked_bank = MemoryBank("rom_banked", region=rom_region,
                             bank_size=16384, max_banks=512, default_bank=1)
cart_ram_bank = MemoryBank("cart_ram_bank", region=cart_ram_region,
                           bank_size=8192, max_banks=16, default_bank=0)

mbc = MemoryController("mbc", controls=[rom_fixed_bank, rom_banked_bank, cart_ram_bank])

# Bank resolvers (transpiled)
@mbc.bank_resolver(rom_fixed_bank)
def resolve_rom_fixed(ctrl, addr):
    return 0

@mbc.bank_resolver(rom_banked_bank)
def resolve_rom_banked(ctrl, addr):
    return ctrl.rom_bank

@mbc.bank_resolver(cart_ram_bank)
def resolve_cart_ram(ctrl, addr):
    return ctrl.ram_bank

# Access guards for cart RAM (transpiled)
@mbc.read_guard(cart_ram_bank)
def guard_read_cart_ram(ctrl):
    return ctrl.ram_enabled

@mbc.write_guard(cart_ram_bank)
def guard_write_cart_ram(ctrl):
    return ctrl.ram_enabled

# MBC write handlers (transpiled)
@mbc.on_write(0x0000, 0x1FFF)
def mbc_ram_enable(ctrl, val, addr):
    ctrl.ram_enabled = 1 if (val & 15) == 10 else 0

@mbc.on_write(0x2000, 0x3FFF)
def mbc_rom_bank_select(ctrl, val, addr):
    if ctrl.mbc_type == 1:
        b: uint8 = val & 31
        if b == 0:
            b = 1
        ctrl.rom_bank = uint16((ctrl.rom_bank & 96) | b)
    elif ctrl.mbc_type == 3:
        b2: uint8 = val & 127
        if b2 == 0:
            b2 = 1
        ctrl.rom_bank = b2
    elif ctrl.mbc_type == 5:
        ctrl.rom_bank = uint16((ctrl.rom_bank & 256) | val)
        if ctrl.rom_bank == 0:
            ctrl.rom_bank = 1

@mbc.on_write(0x4000, 0x5FFF)
def mbc_ram_bank_select(ctrl, val, addr):
    if ctrl.mbc_type == 1:
        if ctrl.mbc_mode == 0:
            ctrl.rom_bank = uint16((ctrl.rom_bank & 31) | ((val & 3) << 5))
        else:
            ctrl.ram_bank = val & 3
    elif ctrl.mbc_type == 3 or ctrl.mbc_type == 5:
        ctrl.ram_bank = val & 15

@mbc.on_write(0x6000, 0x7FFF)
def mbc_mode_select(ctrl, val, addr):
    if ctrl.mbc_type == 1:
        ctrl.mbc_mode = val & 1

cpu_chip.add_memory_controller(mbc)

# ===================================================================
# Memory Bus (64KB address space)
# ===================================================================
bus = MemoryBus("bus", address_bits=16)

# 0000-3FFF: ROM bank 0 (fixed)
bus.map(0x0000, 0x3FFF, bank=rom_fixed_bank, controller=mbc, comment="ROM bank 0")
# 4000-7FFF: ROM bank N (switchable)
bus.map(0x4000, 0x7FFF, bank=rom_banked_bank, controller=mbc, comment="ROM bank N")
# 8000-9FFF: VRAM
bus.map(0x8000, 0x9FFF, region=ppu_vram, comment="Video RAM")
# A000-BFFF: Cart RAM (banked)
bus.map(0xA000, 0xBFFF, bank=cart_ram_bank, controller=mbc, comment="Cart RAM")
# C000-DFFF: WRAM
bus.map(0xC000, 0xDFFF, region=wram, comment="Work RAM")
# E000-FDFF: Echo RAM (mirrors C000-DDFF)
bus.map(0xE000, 0xFDFF, region=wram, comment="Echo RAM")
# FE00-FE9F: OAM
bus.map(0xFE00, 0xFE9F, region=ppu_oam, comment="OAM")
# FF00: Joypad
bus.map(0xFF00, 0xFF00, handler=joypad_io, comment="Joypad")
# FF04-FF07: Timer
bus.map(0xFF04, 0xFF07, handler=timer_io, comment="Timer")
# FF10-FF3F: APU
bus.map(0xFF10, 0xFF3F, handler=apu_io, comment="APU registers")
# FF40-FF4B: PPU
bus.map(0xFF40, 0xFF4B, handler=ppu_io, comment="PPU registers")
# FF80-FFFE: HRAM
bus.map(0xFF80, 0xFFFE, region=hram, comment="High RAM")

# Write-only MBC intercepts
bus.map_writes(0x0000, 0x7FFF, controller=mbc, comment="MBC writes")

# Wave RAM mapping
bus.map(0xFF30, 0xFF3F, region=wave_ram, comment="Wave RAM")

# Fallback
bus.set_fallback(read=0xFF, write=None)

# Set bus on CPU chip
cpu_chip.set_bus(bus)

# ===================================================================
# CPU Definition
# ===================================================================
cpu = CPUDefinition("sm83", data_width=8, address_width=16)

# Registers
cpu.add_register("A", 8, default="0x01")
cpu.add_register("F", 8, default="0xB0")
cpu.add_register("B", 8)
cpu.add_register("C", 8, default="0x13")
cpu.add_register("D", 8)
cpu.add_register("E", 8, default="0xD8")
cpu.add_register("H", 8)
cpu.add_register("L", 8, default="0x4D")

# Register pairs
cpu.add_register_pair("AF", "A", "F")
cpu.add_register_pair("BC", "B", "C")
cpu.add_register_pair("DE", "D", "E")
cpu.add_register_pair("HL", "H", "L")

# Flags (in F register) -- Z=bit7, N=bit6, H=bit5, C=bit4
cpu.set_flags("F", {"Z": 7, "N": 6, "H": 5, "C": 4})
cpu.registers = [r for r in cpu.registers if r.name != "F"]

cpu.add_prefix_table(0xCB)

# ===================================================================
# IF / IE register blocks (transpiled)
# ===================================================================
if_io = RegisterBlock("if_io", base_addr=0xFF0F, size=1)
if_io.bind(0, "interrupt_flags")

@if_io.on_read(0)
def if_read(chip):
    return uint8(chip.interrupt_flags | 224)

@if_io.on_write(0)
def if_write(chip, val):
    chip.interrupt_flags = val & 31

cpu_chip.add_register_block(if_io)

ie_io = RegisterBlock("ie_io", base_addr=0xFFFF, size=1)
ie_io.bind(0, "interrupt_enable")

@ie_io.on_read(0)
def ie_read(chip):
    return chip.interrupt_enable

@ie_io.on_write(0)
def ie_write(chip, val):
    chip.interrupt_enable = val

cpu_chip.add_register_block(ie_io)

bus.map(0xFF0F, 0xFF0F, handler=if_io, comment="IF register")
bus.map(0xFFFF, 0xFFFF, handler=ie_io, comment="IE register")

# ===================================================================
# Serial stub (FF01-FF02)
# ===================================================================
serial_io = RegisterBlock("serial_io", base_addr=0xFF01, size=2)
serial_io.bind(0, "sb", comment="Serial data")
serial_io.bind(1, "sc", comment="Serial control")
cpu_chip.add_register_block(serial_io)
bus.map(0xFF01, 0xFF02, handler=serial_io, comment="Serial")

# ===================================================================
# Chip helpers -- ALL transpiled from Python
# ===================================================================

# PPU update helper (transpiled)
@ppu_chip.helper("update_ppu", returns="void", params=[("cycles", "uint32_t")])
def update_ppu(ppu, cycles):
    ppu.line_dots = ppu.line_dots + cycles
    while ppu.line_dots >= 456:
        ppu.line_dots = ppu.line_dots - 456
        ppu.ly = uint8(ppu.ly + 1)
        if ppu.ly == 144:
            ppu.mode = 1
            cpu.interrupt_flags = cpu.interrupt_flags | 1
            ppu.frame_ready = 1
            render_frame(ppu.framebuffer, 160, 144)
        elif ppu.ly >= 154:
            ppu.ly = 0
            ppu.mode = 2
        if ppu.ly < 144:
            lcdc: uint8 = ppu.lcdc
            if not (lcdc & 128):
                continue
            ly: uint8 = ppu.ly
            bgp: uint8 = ppu.bgp
            pal0: uint8 = bgp & 3
            pal1: uint8 = (bgp >> 2) & 3
            pal2: uint8 = (bgp >> 4) & 3
            pal3: uint8 = (bgp >> 6) & 3
            fb_off: uint32 = uint32(ly) * 160
            if lcdc & 1:
                tile_map: uint16 = 7168 if (lcdc & 8) else 6144
                tile_data: uint16 = 0 if (lcdc & 16) else 2048
                scrolly: uint8 = uint8(ppu.scy + ly)
                ty: uint8 = scrolly >> 3
                tyl: uint8 = scrolly & 7
                for px in range(160):
                    scrollx: uint8 = uint8(ppu.scx + px)
                    tx: uint8 = scrollx >> 3
                    txl: uint8 = scrollx & 7
                    tile_idx: uint8 = ppu.vram[tile_map + uint16(ty) * 32 + tx]
                    addr: uint16 = 0
                    if lcdc & 16:
                        addr = uint16(tile_idx) * 16 + uint16(tyl) * 2
                    else:
                        addr = uint16(tile_data + uint16(int8(tile_idx) + 128) * 16 + uint16(tyl) * 2)
                    lo: uint8 = ppu.vram[addr]
                    hi: uint8 = ppu.vram[uint16(addr + 1)]
                    bit: uint8 = 7 - txl
                    color: uint8 = ((lo >> bit) & 1) | (((hi >> bit) & 1) << 1)
                    if color == 0:
                        ppu.framebuffer[fb_off + px] = pal0
                    elif color == 1:
                        ppu.framebuffer[fb_off + px] = pal1
                    elif color == 2:
                        ppu.framebuffer[fb_off + px] = pal2
                    else:
                        ppu.framebuffer[fb_off + px] = pal3
            else:
                for px in range(160):
                    ppu.framebuffer[fb_off + px] = 0
            # Window layer
            if (lcdc & 32) and ly >= ppu.wy:
                win_map: uint16 = 7168 if (lcdc & 64) else 6144
                w_tile_data: uint16 = 0 if (lcdc & 16) else 2048
                wx: int32 = int(ppu.wx) - 7
                wly: uint8 = uint8(ly - ppu.wy)
                wty: uint8 = wly >> 3
                wtyl: uint8 = wly & 7
                for wpx in range(160):
                    if wpx < wx:
                        continue
                    wtxl: uint8 = uint8(wpx - wx) & 7
                    wtx: uint8 = uint8(wpx - wx) >> 3
                    w_tile_idx: uint8 = ppu.vram[win_map + uint16(wty) * 32 + wtx]
                    waddr: uint16 = 0
                    if lcdc & 16:
                        waddr = uint16(w_tile_idx) * 16 + uint16(wtyl) * 2
                    else:
                        waddr = uint16(w_tile_data + uint16(int8(w_tile_idx) + 128) * 16 + uint16(wtyl) * 2)
                    wlo: uint8 = ppu.vram[waddr]
                    whi: uint8 = ppu.vram[uint16(waddr + 1)]
                    wbit: uint8 = 7 - wtxl
                    wcolor: uint8 = ((wlo >> wbit) & 1) | (((whi >> wbit) & 1) << 1)
                    if wcolor == 0:
                        ppu.framebuffer[fb_off + wpx] = pal0
                    elif wcolor == 1:
                        ppu.framebuffer[fb_off + wpx] = pal1
                    elif wcolor == 2:
                        ppu.framebuffer[fb_off + wpx] = pal2
                    else:
                        ppu.framebuffer[fb_off + wpx] = pal3
            # Sprites
            if lcdc & 2:
                sprite_h: uint8 = 16 if (lcdc & 4) else 8
                count: int32 = 0
                for i in range(40):
                    if count >= 10:
                        break
                    sy: uint8 = uint8(ppu.oam[i * 4] - 16)
                    sx: uint8 = uint8(ppu.oam[i * 4 + 1] - 8)
                    tile: uint8 = ppu.oam[i * 4 + 2]
                    flags: uint8 = ppu.oam[i * 4 + 3]
                    if ly < sy:
                        continue
                    if ly >= uint8(sy + sprite_h):
                        continue
                    count = count + 1
                    row: uint8 = uint8(ly - sy)
                    if flags & 64:
                        row = uint8(sprite_h - 1 - row)
                    if sprite_h == 16:
                        tile = tile & 254
                    saddr: uint16 = uint16(tile) * 16 + uint16(row) * 2
                    slo: uint8 = ppu.vram[saddr]
                    shi: uint8 = ppu.vram[uint16(saddr + 1)]
                    sp_pal: uint8 = ppu.obp1 if (flags & 16) else ppu.obp0
                    sp0: uint8 = sp_pal & 3
                    sp1: uint8 = (sp_pal >> 2) & 3
                    sp2: uint8 = (sp_pal >> 4) & 3
                    sp3: uint8 = (sp_pal >> 6) & 3
                    for b in range(8):
                        xpos: int32 = int(sx) + (7 - b if (flags & 32) else b)
                        if xpos < 0:
                            continue
                        if xpos >= 160:
                            continue
                        sbit: uint8 = uint8(7 - b)
                        scolor: uint8 = ((slo >> sbit) & 1) | (((shi >> sbit) & 1) << 1)
                        if scolor == 0:
                            continue
                        if (flags & 128) and ppu.framebuffer[fb_off + xpos] != pal0:
                            continue
                        if scolor == 1:
                            ppu.framebuffer[fb_off + xpos] = sp1
                        elif scolor == 2:
                            ppu.framebuffer[fb_off + xpos] = sp2
                        else:
                            ppu.framebuffer[fb_off + xpos] = sp3
        # LYC compare
        if ppu.ly == ppu.lyc:
            ppu.stat = ppu.stat | 4
            if ppu.stat & 64:
                cpu.interrupt_flags = cpu.interrupt_flags | 2
        else:
            ppu.stat = ppu.stat & 251

# Timer update helper (transpiled)
@timer_chip.helper("update_timer", returns="void", params=[("cycles", "uint32_t")])
def update_timer(timer, cycles):
    timer.div_counter = uint16(timer.div_counter + cycles)
    tac: uint8 = timer.tac
    if tac & 4:
        timer.tima_counter = timer.tima_counter + cycles
        # TAC rate selection: 0=1024, 1=16, 2=64, 3=256
        rate: uint16 = 1024
        tac_sel: uint8 = tac & 3
        if tac_sel == 1:
            rate = 16
        elif tac_sel == 2:
            rate = 64
        elif tac_sel == 3:
            rate = 256
        while timer.tima_counter >= rate:
            timer.tima_counter = timer.tima_counter - rate
            timer.tima = uint8(timer.tima + 1)
            if timer.tima == 0:
                timer.tima = timer.tma
                cpu.interrupt_flags = cpu.interrupt_flags | 4

# APU update helper (transpiled from Python -- full synthesis)
@apu_chip.helper("update_apu", returns="void", params=[("dots", "uint32_t")])
def update_apu(apu, dots):
    if not (apu.nr52 & 128):
        return

    # Duty table flattened: 4 patterns x 8 steps = 32 entries
    duty_table: array[uint8, 32]
    # Pattern 0: 12.5%  00000001
    duty_table[0] = 0
    duty_table[1] = 0
    duty_table[2] = 0
    duty_table[3] = 0
    duty_table[4] = 0
    duty_table[5] = 0
    duty_table[6] = 0
    duty_table[7] = 1
    # Pattern 1: 25%  10000001
    duty_table[8] = 1
    duty_table[9] = 0
    duty_table[10] = 0
    duty_table[11] = 0
    duty_table[12] = 0
    duty_table[13] = 0
    duty_table[14] = 0
    duty_table[15] = 1
    # Pattern 2: 50%  10000111
    duty_table[16] = 1
    duty_table[17] = 0
    duty_table[18] = 0
    duty_table[19] = 0
    duty_table[20] = 0
    duty_table[21] = 1
    duty_table[22] = 1
    duty_table[23] = 1
    # Pattern 3: 75%  01111110
    duty_table[24] = 0
    duty_table[25] = 1
    duty_table[26] = 1
    duty_table[27] = 1
    duty_table[28] = 1
    duty_table[29] = 1
    duty_table[30] = 1
    duty_table[31] = 0

    # Channel 1 frequency timer
    if apu.ch1_enabled:
        apu.ch1_freq_timer = apu.ch1_freq_timer - int32(dots)
        while apu.ch1_freq_timer <= 0:
            freq: uint16 = uint16(apu.nr13) | ((uint16(apu.nr14) & 7) << 8)
            apu.ch1_freq_timer = apu.ch1_freq_timer + int32(2048 - freq) * 4
            apu.ch1_duty_pos = (apu.ch1_duty_pos + 1) & 7

    # Channel 2 frequency timer
    if apu.ch2_enabled:
        apu.ch2_freq_timer = apu.ch2_freq_timer - int32(dots)
        while apu.ch2_freq_timer <= 0:
            freq: uint16 = uint16(apu.nr23) | ((uint16(apu.nr24) & 7) << 8)
            apu.ch2_freq_timer = apu.ch2_freq_timer + int32(2048 - freq) * 4
            apu.ch2_duty_pos = (apu.ch2_duty_pos + 1) & 7

    # Channel 3 frequency timer
    if apu.ch3_enabled:
        apu.ch3_freq_timer = apu.ch3_freq_timer - int32(dots)
        while apu.ch3_freq_timer <= 0:
            freq: uint16 = uint16(apu.nr33) | ((uint16(apu.nr34) & 7) << 8)
            apu.ch3_freq_timer = apu.ch3_freq_timer + int32(2048 - freq) * 2
            apu.ch3_sample_pos = (apu.ch3_sample_pos + 1) & 31

    # Channel 4 frequency timer (noise LFSR)
    if apu.ch4_enabled:
        apu.ch4_freq_timer = apu.ch4_freq_timer - int32(dots)
        while apu.ch4_freq_timer <= 0:
            div_code: uint8 = apu.nr43 & 7
            shift: uint8 = (apu.nr43 >> 4) & 15
            divisor: int32 = int32(div_code) * 16 if div_code else 8
            apu.ch4_freq_timer = apu.ch4_freq_timer + (divisor << shift)
            xor_bit: uint16 = (apu.ch4_lfsr & 1) ^ ((apu.ch4_lfsr >> 1) & 1)
            apu.ch4_lfsr = (apu.ch4_lfsr >> 1) | (xor_bit << 14)
            if apu.nr43 & 8:
                apu.ch4_lfsr = apu.ch4_lfsr & ~(1 << 6)
                apu.ch4_lfsr = apu.ch4_lfsr | (xor_bit << 6)

    # Frame sequencer (length, sweep, envelope)
    apu.frame_seq_counter = apu.frame_seq_counter + dots
    while apu.frame_seq_counter >= 8192:
        apu.frame_seq_counter = apu.frame_seq_counter - 8192
        step: uint8 = apu.frame_seq_step

        # Length counter (steps 0, 2, 4, 6)
        if (step & 1) == 0:
            if (apu.nr14 & 64) and apu.ch1_length > 0:
                apu.ch1_length = apu.ch1_length - 1
                if apu.ch1_length == 0:
                    apu.ch1_enabled = 0
            if (apu.nr24 & 64) and apu.ch2_length > 0:
                apu.ch2_length = apu.ch2_length - 1
                if apu.ch2_length == 0:
                    apu.ch2_enabled = 0
            if (apu.nr34 & 64) and apu.ch3_length > 0:
                apu.ch3_length = apu.ch3_length - 1
                if apu.ch3_length == 0:
                    apu.ch3_enabled = 0
            if (apu.nr44 & 64) and apu.ch4_length > 0:
                apu.ch4_length = apu.ch4_length - 1
                if apu.ch4_length == 0:
                    apu.ch4_enabled = 0

        # Sweep (steps 2, 6)
        if step == 2 or step == 6:
            if apu.ch1_sweep_enabled:
                apu.ch1_sweep_timer = apu.ch1_sweep_timer - 1
                if apu.ch1_sweep_timer == 0:
                    period: uint8 = (apu.nr10 >> 4) & 7
                    apu.ch1_sweep_timer = period if period else 8
                    if period:
                        sw_shift: uint8 = apu.nr10 & 7
                        delta: uint16 = apu.ch1_sweep_shadow >> sw_shift
                        new_freq: uint16 = 0
                        if apu.nr10 & 8:
                            new_freq = apu.ch1_sweep_shadow - delta
                        else:
                            new_freq = apu.ch1_sweep_shadow + delta
                        if new_freq > 2047:
                            apu.ch1_enabled = 0
                        elif sw_shift:
                            apu.ch1_sweep_shadow = new_freq
                            apu.nr13 = new_freq & 255
                            apu.nr14 = (apu.nr14 & 248) | ((new_freq >> 8) & 7)
                            delta2: uint16 = new_freq >> sw_shift
                            check2: uint16 = (new_freq - delta2) if (apu.nr10 & 8) else (new_freq + delta2)
                            if check2 > 2047:
                                apu.ch1_enabled = 0

        # Envelope (step 7)
        if step == 7:
            if (apu.nr12 & 7) and apu.ch1_enabled:
                apu.ch1_env_timer = apu.ch1_env_timer - 1
                if apu.ch1_env_timer == 0:
                    apu.ch1_env_timer = apu.nr12 & 7
                    if apu.nr12 & 8:
                        if apu.ch1_volume < 15:
                            apu.ch1_volume = apu.ch1_volume + 1
                    else:
                        if apu.ch1_volume > 0:
                            apu.ch1_volume = apu.ch1_volume - 1
            if (apu.nr22 & 7) and apu.ch2_enabled:
                apu.ch2_env_timer = apu.ch2_env_timer - 1
                if apu.ch2_env_timer == 0:
                    apu.ch2_env_timer = apu.nr22 & 7
                    if apu.nr22 & 8:
                        if apu.ch2_volume < 15:
                            apu.ch2_volume = apu.ch2_volume + 1
                    else:
                        if apu.ch2_volume > 0:
                            apu.ch2_volume = apu.ch2_volume - 1
            if (apu.nr42 & 7) and apu.ch4_enabled:
                apu.ch4_env_timer = apu.ch4_env_timer - 1
                if apu.ch4_env_timer == 0:
                    apu.ch4_env_timer = apu.nr42 & 7
                    if apu.nr42 & 8:
                        if apu.ch4_volume < 15:
                            apu.ch4_volume = apu.ch4_volume + 1
                    else:
                        if apu.ch4_volume > 0:
                            apu.ch4_volume = apu.ch4_volume - 1

        apu.frame_seq_step = (step + 1) & 7

    # Sample generation (downsample from ~4.19MHz to ~48kHz, every ~87 cycles)
    apu.sample_counter = apu.sample_counter + dots
    while apu.sample_counter >= 87:
        apu.sample_counter = apu.sample_counter - 87
        if apu.sample_count >= 1614:
            continue
        left: int16 = 0
        right: int16 = 0

        # Channel 1 (square + sweep)
        if apu.ch1_enabled and not apu.debug_ch1_mute:
            duty: uint8 = (apu.nr11 >> 6) & 3
            sample: int16 = int16(apu.ch1_volume) if duty_table[int(duty) * 8 + int(apu.ch1_duty_pos)] else 0
            if apu.nr51 & 16:
                left = left + sample
            if apu.nr51 & 1:
                right = right + sample

        # Channel 2 (square)
        if apu.ch2_enabled and not apu.debug_ch2_mute:
            duty: uint8 = (apu.nr21 >> 6) & 3
            sample: int16 = int16(apu.ch2_volume) if duty_table[int(duty) * 8 + int(apu.ch2_duty_pos)] else 0
            if apu.nr51 & 32:
                left = left + sample
            if apu.nr51 & 2:
                right = right + sample

        # Channel 3 (wave)
        if apu.ch3_enabled and not apu.debug_ch3_mute:
            pos: uint8 = apu.ch3_sample_pos
            byte: uint8 = apu.wave_ram[pos >> 1]
            nibble: uint8 = (byte & 15) if (pos & 1) else (byte >> 4)
            vol_shift: uint8 = (apu.nr32 >> 5) & 3
            sample: int16 = 0 if vol_shift == 0 else int16(nibble >> (vol_shift - 1))
            if apu.nr51 & 64:
                left = left + sample
            if apu.nr51 & 4:
                right = right + sample

        # Channel 4 (noise)
        if apu.ch4_enabled and not apu.debug_ch4_mute:
            sample: int16 = 0 if (apu.ch4_lfsr & 1) else int16(apu.ch4_volume)
            if apu.nr51 & 128:
                left = left + sample
            if apu.nr51 & 8:
                right = right + sample

        # Master volume and output
        vol_l: int16 = int16(((apu.nr50 >> 4) & 7) + 1)
        vol_r: int16 = int16((apu.nr50 & 7) + 1)
        left = left * vol_l * 32
        right = right * vol_r * 32
        apu.sample_buffer[apu.sample_count] = left
        apu.sample_count = apu.sample_count + 1
        apu.sample_buffer[apu.sample_count] = right
        apu.sample_count = apu.sample_count + 1

# ===================================================================
# Tick handlers (transpiled)
# ===================================================================
@ppu_chip.tick()
def ppu_tick(ppu, cycles):
    update_ppu(cycles)

@timer_chip.tick()
def timer_tick(timer, cycles):
    update_timer(cycles)

@apu_chip.tick()
def apu_tick(apu, cycles):
    update_apu(cycles)
    if apu.sample_count >= 1614:
        audio_push(apu.sample_buffer, apu.sample_count)
        apu.sample_count = 0

# ===================================================================
# Step preamble (EI delay + interrupt dispatch) -- transpiled
# ===================================================================
def step_preamble(cpu):
    if cpu.ime_delay > 0:
        cpu.ime_delay = uint8(cpu.ime_delay - 1)
        if cpu.ime_delay == 0:
            cpu.ime = 1
    if cpu.ime:
        pending: uint8 = cpu.interrupt_enable & cpu.interrupt_flags
        if pending:
            cpu.ime = 0
            cpu.halted = 0
            if pending & 1:
                cpu.interrupt_flags = cpu.interrupt_flags & 254
                push16(cpu.PC)
                cpu.PC = 64
                cpu.cycle_count = cpu.cycle_count + 5
            elif pending & 2:
                cpu.interrupt_flags = cpu.interrupt_flags & 253
                push16(cpu.PC)
                cpu.PC = 72
                cpu.cycle_count = cpu.cycle_count + 5
            elif pending & 4:
                cpu.interrupt_flags = cpu.interrupt_flags & 251
                push16(cpu.PC)
                cpu.PC = 80
                cpu.cycle_count = cpu.cycle_count + 5
            elif pending & 8:
                cpu.interrupt_flags = cpu.interrupt_flags & 247
                push16(cpu.PC)
                cpu.PC = 88
                cpu.cycle_count = cpu.cycle_count + 5
            elif pending & 16:
                cpu.interrupt_flags = cpu.interrupt_flags & 239
                push16(cpu.PC)
                cpu.PC = 96
                cpu.cycle_count = cpu.cycle_count + 5
    elif cpu.halted:
        pending2: uint8 = cpu.interrupt_enable & cpu.interrupt_flags
        if pending2:
            cpu.halted = 0
        else:
            cpu.cycle_count = cpu.cycle_count + 1
            return

cpu_chip.set_step_preamble(func=step_preamble)

# ===================================================================
# SM83 Opcodes -- ALL transpiled from Python
# ===================================================================

# --- 0x00: NOP ---
@cpu.opcode(0x00, "NOP", cycles=1)
def op_nop(cpu):
    pass

# --- 0x01, 0x11, 0x21, 0x31: LD rr, d16 ---
@cpu.opcode(0x01, "LD BC,d16", cycles=3)
def op_ld_bc_d16(cpu):
    cpu.C = read_imm8()
    cpu.B = read_imm8()

@cpu.opcode(0x11, "LD DE,d16", cycles=3)
def op_ld_de_d16(cpu):
    cpu.E = read_imm8()
    cpu.D = read_imm8()

@cpu.opcode(0x21, "LD HL,d16", cycles=3)
def op_ld_hl_d16(cpu):
    cpu.L = read_imm8()
    cpu.H = read_imm8()

@cpu.opcode(0x31, "LD SP,d16", cycles=3)
def op_ld_sp_d16(cpu):
    lo = read_imm8()
    hi = read_imm8()
    cpu.SP = uint16((hi << 8) | lo)

# --- LD (rr), A ---
@cpu.opcode(0x02, "LD (BC),A", cycles=2)
def op_ld_bc_a(cpu):
    mem_write(cpu.BC, cpu.A)

@cpu.opcode(0x12, "LD (DE),A", cycles=2)
def op_ld_de_a(cpu):
    mem_write(cpu.DE, cpu.A)

@cpu.opcode(0x22, "LD (HL+),A", cycles=2)
def op_ldi_hl_a(cpu):
    mem_write(cpu.HL, cpu.A)
    cpu.HL = uint16(cpu.HL + 1)

@cpu.opcode(0x32, "LD (HL-),A", cycles=2)
def op_ldd_hl_a(cpu):
    mem_write(cpu.HL, cpu.A)
    cpu.HL = uint16(cpu.HL - 1)

# --- LD A, (rr) ---
@cpu.opcode(0x0A, "LD A,(BC)", cycles=2)
def op_ld_a_bc(cpu):
    cpu.A = mem_read(cpu.BC)

@cpu.opcode(0x1A, "LD A,(DE)", cycles=2)
def op_ld_a_de(cpu):
    cpu.A = mem_read(cpu.DE)

@cpu.opcode(0x2A, "LD A,(HL+)", cycles=2)
def op_ldi_a_hl(cpu):
    cpu.A = mem_read(cpu.HL)
    cpu.HL = uint16(cpu.HL + 1)

@cpu.opcode(0x3A, "LD A,(HL-)", cycles=2)
def op_ldd_a_hl(cpu):
    cpu.A = mem_read(cpu.HL)
    cpu.HL = uint16(cpu.HL - 1)

# --- INC rr ---
@cpu.opcode(0x03, "INC BC", cycles=2)
def op_inc_bc(cpu):
    cpu.BC = uint16(cpu.BC + 1)

@cpu.opcode(0x13, "INC DE", cycles=2)
def op_inc_de(cpu):
    cpu.DE = uint16(cpu.DE + 1)

@cpu.opcode(0x23, "INC HL", cycles=2)
def op_inc_hl(cpu):
    cpu.HL = uint16(cpu.HL + 1)

@cpu.opcode(0x33, "INC SP", cycles=2)
def op_inc_sp(cpu):
    cpu.SP = uint16(cpu.SP + 1)

# --- DEC rr ---
@cpu.opcode(0x0B, "DEC BC", cycles=2)
def op_dec_bc(cpu):
    cpu.BC = uint16(cpu.BC - 1)

@cpu.opcode(0x1B, "DEC DE", cycles=2)
def op_dec_de(cpu):
    cpu.DE = uint16(cpu.DE - 1)

@cpu.opcode(0x2B, "DEC HL", cycles=2)
def op_dec_hl(cpu):
    cpu.HL = uint16(cpu.HL - 1)

@cpu.opcode(0x3B, "DEC SP", cycles=2)
def op_dec_sp(cpu):
    cpu.SP = uint16(cpu.SP - 1)

# --- INC r (8-bit) ---
@cpu.opcode(0x04, "INC B", cycles=1)
def op_inc_b(cpu):
    cpu.F.H = 1 if (cpu.B & 15) == 15 else 0
    cpu.B = uint8(cpu.B + 1)
    cpu.F.Z = 1 if cpu.B == 0 else 0
    cpu.F.N = 0

@cpu.opcode(0x0C, "INC C", cycles=1)
def op_inc_c(cpu):
    cpu.F.H = 1 if (cpu.C & 15) == 15 else 0
    cpu.C = uint8(cpu.C + 1)
    cpu.F.Z = 1 if cpu.C == 0 else 0
    cpu.F.N = 0

@cpu.opcode(0x14, "INC D", cycles=1)
def op_inc_d(cpu):
    cpu.F.H = 1 if (cpu.D & 15) == 15 else 0
    cpu.D = uint8(cpu.D + 1)
    cpu.F.Z = 1 if cpu.D == 0 else 0
    cpu.F.N = 0

@cpu.opcode(0x1C, "INC E", cycles=1)
def op_inc_e(cpu):
    cpu.F.H = 1 if (cpu.E & 15) == 15 else 0
    cpu.E = uint8(cpu.E + 1)
    cpu.F.Z = 1 if cpu.E == 0 else 0
    cpu.F.N = 0

@cpu.opcode(0x24, "INC H", cycles=1)
def op_inc_h(cpu):
    cpu.F.H = 1 if (cpu.H & 15) == 15 else 0
    cpu.H = uint8(cpu.H + 1)
    cpu.F.Z = 1 if cpu.H == 0 else 0
    cpu.F.N = 0

@cpu.opcode(0x2C, "INC L", cycles=1)
def op_inc_l(cpu):
    cpu.F.H = 1 if (cpu.L & 15) == 15 else 0
    cpu.L = uint8(cpu.L + 1)
    cpu.F.Z = 1 if cpu.L == 0 else 0
    cpu.F.N = 0

@cpu.opcode(0x3C, "INC A", cycles=1)
def op_inc_a(cpu):
    cpu.F.H = 1 if (cpu.A & 15) == 15 else 0
    cpu.A = uint8(cpu.A + 1)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 0

@cpu.opcode(0x34, "INC (HL)", cycles=3)
def op_inc_hl_ind(cpu):
    v = mem_read(cpu.HL)
    cpu.F.H = 1 if (v & 15) == 15 else 0
    v = uint8(v + 1)
    mem_write(cpu.HL, v)
    cpu.F.Z = 1 if v == 0 else 0
    cpu.F.N = 0

# --- DEC r (8-bit) ---
@cpu.opcode(0x05, "DEC B", cycles=1)
def op_dec_b(cpu):
    cpu.F.H = 1 if (cpu.B & 15) == 0 else 0
    cpu.B = uint8(cpu.B - 1)
    cpu.F.Z = 1 if cpu.B == 0 else 0
    cpu.F.N = 1

@cpu.opcode(0x0D, "DEC C", cycles=1)
def op_dec_c(cpu):
    cpu.F.H = 1 if (cpu.C & 15) == 0 else 0
    cpu.C = uint8(cpu.C - 1)
    cpu.F.Z = 1 if cpu.C == 0 else 0
    cpu.F.N = 1

@cpu.opcode(0x15, "DEC D", cycles=1)
def op_dec_d(cpu):
    cpu.F.H = 1 if (cpu.D & 15) == 0 else 0
    cpu.D = uint8(cpu.D - 1)
    cpu.F.Z = 1 if cpu.D == 0 else 0
    cpu.F.N = 1

@cpu.opcode(0x1D, "DEC E", cycles=1)
def op_dec_e(cpu):
    cpu.F.H = 1 if (cpu.E & 15) == 0 else 0
    cpu.E = uint8(cpu.E - 1)
    cpu.F.Z = 1 if cpu.E == 0 else 0
    cpu.F.N = 1

@cpu.opcode(0x25, "DEC H", cycles=1)
def op_dec_h(cpu):
    cpu.F.H = 1 if (cpu.H & 15) == 0 else 0
    cpu.H = uint8(cpu.H - 1)
    cpu.F.Z = 1 if cpu.H == 0 else 0
    cpu.F.N = 1

@cpu.opcode(0x2D, "DEC L", cycles=1)
def op_dec_l(cpu):
    cpu.F.H = 1 if (cpu.L & 15) == 0 else 0
    cpu.L = uint8(cpu.L - 1)
    cpu.F.Z = 1 if cpu.L == 0 else 0
    cpu.F.N = 1

@cpu.opcode(0x3D, "DEC A", cycles=1)
def op_dec_a(cpu):
    cpu.F.H = 1 if (cpu.A & 15) == 0 else 0
    cpu.A = uint8(cpu.A - 1)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 1

@cpu.opcode(0x35, "DEC (HL)", cycles=3)
def op_dec_hl_ind(cpu):
    v = mem_read(cpu.HL)
    cpu.F.H = 1 if (v & 15) == 0 else 0
    v = uint8(v - 1)
    mem_write(cpu.HL, v)
    cpu.F.Z = 1 if v == 0 else 0
    cpu.F.N = 1

# --- LD r, d8 ---
@cpu.opcode(0x06, "LD B,d8", cycles=2)
def op_ld_b_d8(cpu):
    cpu.B = read_imm8()

@cpu.opcode(0x0E, "LD C,d8", cycles=2)
def op_ld_c_d8(cpu):
    cpu.C = read_imm8()

@cpu.opcode(0x16, "LD D,d8", cycles=2)
def op_ld_d_d8(cpu):
    cpu.D = read_imm8()

@cpu.opcode(0x1E, "LD E,d8", cycles=2)
def op_ld_e_d8(cpu):
    cpu.E = read_imm8()

@cpu.opcode(0x26, "LD H,d8", cycles=2)
def op_ld_h_d8(cpu):
    cpu.H = read_imm8()

@cpu.opcode(0x2E, "LD L,d8", cycles=2)
def op_ld_l_d8(cpu):
    cpu.L = read_imm8()

@cpu.opcode(0x36, "LD (HL),d8", cycles=3)
def op_ld_hl_d8(cpu):
    mem_write(cpu.HL, read_imm8())

@cpu.opcode(0x3E, "LD A,d8", cycles=2)
def op_ld_a_d8(cpu):
    cpu.A = read_imm8()

# --- Rotation/shift A ---
@cpu.opcode(0x07, "RLCA", cycles=1)
def op_rlca(cpu):
    c = (cpu.A >> 7) & 1
    cpu.A = uint8((cpu.A << 1) | c)
    cpu.F.Z = 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = c

@cpu.opcode(0x0F, "RRCA", cycles=1)
def op_rrca(cpu):
    c = cpu.A & 1
    cpu.A = uint8((cpu.A >> 1) | (c << 7))
    cpu.F.Z = 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = c

@cpu.opcode(0x17, "RLA", cycles=1)
def op_rla(cpu):
    old_c = cpu.F.C
    cpu.F.C = (cpu.A >> 7) & 1
    cpu.A = uint8((cpu.A << 1) | old_c)
    cpu.F.Z = 0
    cpu.F.N = 0
    cpu.F.H = 0

@cpu.opcode(0x1F, "RRA", cycles=1)
def op_rra(cpu):
    old_c = cpu.F.C
    cpu.F.C = cpu.A & 1
    cpu.A = uint8((cpu.A >> 1) | (old_c << 7))
    cpu.F.Z = 0
    cpu.F.N = 0
    cpu.F.H = 0

# --- DAA ---
@cpu.opcode(0x27, "DAA", cycles=1)
def op_daa(cpu):
    a = int(cpu.A)
    if cpu.F.N:
        if cpu.F.C:
            a = a - 96
        if cpu.F.H:
            a = a - 6
    else:
        if cpu.F.C or a > 153:
            a = a + 96
            cpu.F.C = 1
        if cpu.F.H or (a & 15) > 9:
            a = a + 6
    cpu.A = uint8(a)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.H = 0

# --- CPL ---
@cpu.opcode(0x2F, "CPL", cycles=1)
def op_cpl(cpu):
    cpu.A = uint8(cpu.A ^ 255)
    cpu.F.N = 1
    cpu.F.H = 1

# --- SCF / CCF ---
@cpu.opcode(0x37, "SCF", cycles=1)
def op_scf(cpu):
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = 1

@cpu.opcode(0x3F, "CCF", cycles=1)
def op_ccf(cpu):
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = 1 if cpu.F.C == 0 else 0

# --- ADD HL, rr ---
@cpu.opcode(0x09, "ADD HL,BC", cycles=2)
def op_add_hl_bc(cpu):
    result = int(cpu.HL) + int(cpu.BC)
    cpu.F.N = 0
    cpu.F.H = 1 if ((cpu.HL & 0xFFF) + (cpu.BC & 0xFFF)) > 0xFFF else 0
    cpu.F.C = 1 if result > 0xFFFF else 0
    cpu.HL = uint16(result)

@cpu.opcode(0x19, "ADD HL,DE", cycles=2)
def op_add_hl_de(cpu):
    result = int(cpu.HL) + int(cpu.DE)
    cpu.F.N = 0
    cpu.F.H = 1 if ((cpu.HL & 0xFFF) + (cpu.DE & 0xFFF)) > 0xFFF else 0
    cpu.F.C = 1 if result > 0xFFFF else 0
    cpu.HL = uint16(result)

@cpu.opcode(0x29, "ADD HL,HL", cycles=2)
def op_add_hl_hl(cpu):
    result = int(cpu.HL) + int(cpu.HL)
    cpu.F.N = 0
    cpu.F.H = 1 if ((cpu.HL & 0xFFF) + (cpu.HL & 0xFFF)) > 0xFFF else 0
    cpu.F.C = 1 if result > 0xFFFF else 0
    cpu.HL = uint16(result)

@cpu.opcode(0x39, "ADD HL,SP", cycles=2)
def op_add_hl_sp(cpu):
    result = int(cpu.HL) + int(cpu.SP)
    cpu.F.N = 0
    cpu.F.H = 1 if ((cpu.HL & 0xFFF) + (cpu.SP & 0xFFF)) > 0xFFF else 0
    cpu.F.C = 1 if result > 0xFFFF else 0
    cpu.HL = uint16(result)

# --- JR ---
@cpu.opcode(0x18, "JR r8", cycles=3)
def op_jr(cpu):
    offset = int8(read_imm8())
    cpu.PC = uint16(cpu.PC + offset)

@cpu.opcode(0x20, "JR NZ,r8", cycles=2)
def op_jr_nz(cpu):
    offset = int8(read_imm8())
    if cpu.F.Z == 0:
        cpu.PC = uint16(cpu.PC + offset)
        cpu.cycle_count = cpu.cycle_count + 1

@cpu.opcode(0x28, "JR Z,r8", cycles=2)
def op_jr_z(cpu):
    offset = int8(read_imm8())
    if cpu.F.Z:
        cpu.PC = uint16(cpu.PC + offset)
        cpu.cycle_count = cpu.cycle_count + 1

@cpu.opcode(0x30, "JR NC,r8", cycles=2)
def op_jr_nc(cpu):
    offset = int8(read_imm8())
    if cpu.F.C == 0:
        cpu.PC = uint16(cpu.PC + offset)
        cpu.cycle_count = cpu.cycle_count + 1

@cpu.opcode(0x38, "JR C,r8", cycles=2)
def op_jr_c(cpu):
    offset = int8(read_imm8())
    if cpu.F.C:
        cpu.PC = uint16(cpu.PC + offset)
        cpu.cycle_count = cpu.cycle_count + 1

# --- LD (a16), SP ---
@cpu.opcode(0x08, "LD (a16),SP", cycles=5)
def op_ld_a16_sp(cpu):
    lo = read_imm8()
    hi = read_imm8()
    addr = uint16((hi << 8) | lo)
    mem_write(addr, uint8(cpu.SP & 255))
    mem_write(uint16(addr + 1), uint8((cpu.SP >> 8) & 255))

# --- STOP / HALT ---
@cpu.opcode(0x10, "STOP", cycles=1)
def op_stop(cpu):
    read_imm8()

@cpu.opcode(0x76, "HALT", cycles=1)
def op_halt(cpu):
    cpu.halted = 1

# === LD r,r' block (0x40-0x7F except 0x76=HALT) ===
_r2r = []
for d in ['B','C','D','E','H','L','A']:
    for s in ['B','C','D','E','H','L','A']:
        di = ['B','C','D','E','H','L',None,'A'].index(d)
        si = ['B','C','D','E','H','L',None,'A'].index(s)
        _r2r.append((0x40 + di*8 + si, d, s))

@cpu.opcode_family("LD {},{}", _r2r, cycles=1)
def op_ld_r_r(cpu, dst, src):
    cpu.dst = cpu.src

# LD r, (HL) -- read from memory at HL into register
@cpu.opcode(0x46, "LD B,(HL)", cycles=2)
def op_ld_b_hl(cpu):
    cpu.B = mem_read(cpu.HL)

@cpu.opcode(0x4E, "LD C,(HL)", cycles=2)
def op_ld_c_hl(cpu):
    cpu.C = mem_read(cpu.HL)

@cpu.opcode(0x56, "LD D,(HL)", cycles=2)
def op_ld_d_hl(cpu):
    cpu.D = mem_read(cpu.HL)

@cpu.opcode(0x5E, "LD E,(HL)", cycles=2)
def op_ld_e_hl(cpu):
    cpu.E = mem_read(cpu.HL)

@cpu.opcode(0x66, "LD H,(HL)", cycles=2)
def op_ld_h_hl(cpu):
    cpu.H = mem_read(cpu.HL)

@cpu.opcode(0x6E, "LD L,(HL)", cycles=2)
def op_ld_l_hl(cpu):
    cpu.L = mem_read(cpu.HL)

@cpu.opcode(0x7E, "LD A,(HL)", cycles=2)
def op_ld_a_hl(cpu):
    cpu.A = mem_read(cpu.HL)

# LD (HL), r -- write register to memory at HL
@cpu.opcode(0x70, "LD (HL),B", cycles=2)
def op_ld_hl_b(cpu):
    mem_write(cpu.HL, cpu.B)

@cpu.opcode(0x71, "LD (HL),C", cycles=2)
def op_ld_hl_c(cpu):
    mem_write(cpu.HL, cpu.C)

@cpu.opcode(0x72, "LD (HL),D", cycles=2)
def op_ld_hl_d(cpu):
    mem_write(cpu.HL, cpu.D)

@cpu.opcode(0x73, "LD (HL),E", cycles=2)
def op_ld_hl_e(cpu):
    mem_write(cpu.HL, cpu.E)

@cpu.opcode(0x74, "LD (HL),H", cycles=2)
def op_ld_hl_h(cpu):
    mem_write(cpu.HL, cpu.H)

@cpu.opcode(0x75, "LD (HL),L", cycles=2)
def op_ld_hl_l(cpu):
    mem_write(cpu.HL, cpu.L)

@cpu.opcode(0x77, "LD (HL),A", cycles=2)
def op_ld_hl_a(cpu):
    mem_write(cpu.HL, cpu.A)

# === ALU A,r (0x80-0xBF) ===

# ADD A,r
@cpu.opcode_family("ADD A,{}", [
    (0x80,'B'),(0x81,'C'),(0x82,'D'),(0x83,'E'),
    (0x84,'H'),(0x85,'L'),(0x87,'A'),
], cycles=1)
def op_add_a_r(cpu, src):
    v = cpu.src
    r = uint16(cpu.A) + uint16(v)
    cpu.F.H = 1 if ((cpu.A & 15) + (v & 15)) > 15 else 0
    cpu.F.C = 1 if r > 255 else 0
    cpu.A = uint8(r)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 0

@cpu.opcode(0x86, "ADD A,(HL)", cycles=2)
def op_add_a_hl(cpu):
    v = mem_read(cpu.HL)
    r = uint16(cpu.A) + uint16(v)
    cpu.F.H = 1 if ((cpu.A & 15) + (v & 15)) > 15 else 0
    cpu.F.C = 1 if r > 255 else 0
    cpu.A = uint8(r)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 0

# ADC A,r
@cpu.opcode_family("ADC A,{}", [
    (0x88,'B'),(0x89,'C'),(0x8A,'D'),(0x8B,'E'),
    (0x8C,'H'),(0x8D,'L'),(0x8F,'A'),
], cycles=1)
def op_adc_a_r(cpu, src):
    v = cpu.src
    cy = cpu.F.C
    r = uint16(cpu.A) + uint16(v) + uint16(cy)
    cpu.F.H = 1 if ((cpu.A & 15) + (v & 15) + cy) > 15 else 0
    cpu.F.C = 1 if r > 255 else 0
    cpu.A = uint8(r)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 0

@cpu.opcode(0x8E, "ADC A,(HL)", cycles=2)
def op_adc_a_hl(cpu):
    v = mem_read(cpu.HL)
    cy = cpu.F.C
    r = uint16(cpu.A) + uint16(v) + uint16(cy)
    cpu.F.H = 1 if ((cpu.A & 15) + (v & 15) + cy) > 15 else 0
    cpu.F.C = 1 if r > 255 else 0
    cpu.A = uint8(r)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 0

# SUB A,r
@cpu.opcode_family("SUB A,{}", [
    (0x90,'B'),(0x91,'C'),(0x92,'D'),(0x93,'E'),
    (0x94,'H'),(0x95,'L'),(0x97,'A'),
], cycles=1)
def op_sub_a_r(cpu, src):
    v = cpu.src
    cpu.F.H = 1 if (cpu.A & 15) < (v & 15) else 0
    cpu.F.C = 1 if cpu.A < v else 0
    cpu.A = uint8(cpu.A - v)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 1

@cpu.opcode(0x96, "SUB A,(HL)", cycles=2)
def op_sub_a_hl(cpu):
    v = mem_read(cpu.HL)
    cpu.F.H = 1 if (cpu.A & 15) < (v & 15) else 0
    cpu.F.C = 1 if cpu.A < v else 0
    cpu.A = uint8(cpu.A - v)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 1

# SBC A,r
@cpu.opcode_family("SBC A,{}", [
    (0x98,'B'),(0x99,'C'),(0x9A,'D'),(0x9B,'E'),
    (0x9C,'H'),(0x9D,'L'),(0x9F,'A'),
], cycles=1)
def op_sbc_a_r(cpu, src):
    v = cpu.src
    cy = cpu.F.C
    r = int(cpu.A) - int(v) - int(cy)
    cpu.F.H = 1 if (int(cpu.A & 15) - int(v & 15) - int(cy)) < 0 else 0
    cpu.F.C = 1 if r < 0 else 0
    cpu.A = uint8(r)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 1

@cpu.opcode(0x9E, "SBC A,(HL)", cycles=2)
def op_sbc_a_hl(cpu):
    v = mem_read(cpu.HL)
    cy = cpu.F.C
    r = int(cpu.A) - int(v) - int(cy)
    cpu.F.H = 1 if (int(cpu.A & 15) - int(v & 15) - int(cy)) < 0 else 0
    cpu.F.C = 1 if r < 0 else 0
    cpu.A = uint8(r)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 1

# AND A,r
@cpu.opcode_family("AND {}", [
    (0xA0,'B'),(0xA1,'C'),(0xA2,'D'),(0xA3,'E'),
    (0xA4,'H'),(0xA5,'L'),(0xA7,'A'),
], cycles=1)
def op_and_r(cpu, src):
    cpu.A = cpu.A & cpu.src
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1
    cpu.F.C = 0

@cpu.opcode(0xA6, "AND (HL)", cycles=2)
def op_and_hl(cpu):
    cpu.A = cpu.A & mem_read(cpu.HL)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1
    cpu.F.C = 0

# XOR A,r
@cpu.opcode_family("XOR {}", [
    (0xA8,'B'),(0xA9,'C'),(0xAA,'D'),(0xAB,'E'),
    (0xAC,'H'),(0xAD,'L'),(0xAF,'A'),
], cycles=1)
def op_xor_r(cpu, src):
    cpu.A = cpu.A ^ cpu.src
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = 0

@cpu.opcode(0xAE, "XOR (HL)", cycles=2)
def op_xor_hl(cpu):
    cpu.A = cpu.A ^ mem_read(cpu.HL)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = 0

# OR A,r
@cpu.opcode_family("OR {}", [
    (0xB0,'B'),(0xB1,'C'),(0xB2,'D'),(0xB3,'E'),
    (0xB4,'H'),(0xB5,'L'),(0xB7,'A'),
], cycles=1)
def op_or_r(cpu, src):
    cpu.A = cpu.A | cpu.src
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = 0

@cpu.opcode(0xB6, "OR (HL)", cycles=2)
def op_or_hl(cpu):
    cpu.A = cpu.A | mem_read(cpu.HL)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = 0

# CP A,r
@cpu.opcode_family("CP {}", [
    (0xB8,'B'),(0xB9,'C'),(0xBA,'D'),(0xBB,'E'),
    (0xBC,'H'),(0xBD,'L'),(0xBF,'A'),
], cycles=1)
def op_cp_r(cpu, src):
    v = cpu.src
    cpu.F.Z = 1 if cpu.A == v else 0
    cpu.F.N = 1
    cpu.F.H = 1 if (cpu.A & 15) < (v & 15) else 0
    cpu.F.C = 1 if cpu.A < v else 0

@cpu.opcode(0xBE, "CP (HL)", cycles=2)
def op_cp_hl(cpu):
    v = mem_read(cpu.HL)
    cpu.F.Z = 1 if cpu.A == v else 0
    cpu.F.N = 1
    cpu.F.H = 1 if (cpu.A & 15) < (v & 15) else 0
    cpu.F.C = 1 if cpu.A < v else 0

# === ALU A,d8 ===

@cpu.opcode(0xC6, "ADD A,d8", cycles=2)
def op_add_a_d8(cpu):
    v = read_imm8()
    r = uint16(cpu.A) + uint16(v)
    cpu.F.H = 1 if ((cpu.A & 15) + (v & 15)) > 15 else 0
    cpu.F.C = 1 if r > 255 else 0
    cpu.A = uint8(r)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 0

@cpu.opcode(0xCE, "ADC A,d8", cycles=2)
def op_adc_a_d8(cpu):
    v = read_imm8()
    cy = cpu.F.C
    r = uint16(cpu.A) + uint16(v) + uint16(cy)
    cpu.F.H = 1 if ((cpu.A & 15) + (v & 15) + cy) > 15 else 0
    cpu.F.C = 1 if r > 255 else 0
    cpu.A = uint8(r)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 0

@cpu.opcode(0xD6, "SUB d8", cycles=2)
def op_sub_d8(cpu):
    v = read_imm8()
    cpu.F.H = 1 if (cpu.A & 15) < (v & 15) else 0
    cpu.F.C = 1 if cpu.A < v else 0
    cpu.A = uint8(cpu.A - v)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 1

@cpu.opcode(0xDE, "SBC A,d8", cycles=2)
def op_sbc_a_d8(cpu):
    v = read_imm8()
    cy = cpu.F.C
    r = int(cpu.A) - int(v) - int(cy)
    cpu.F.H = 1 if (int(cpu.A & 15) - int(v & 15) - int(cy)) < 0 else 0
    cpu.F.C = 1 if r < 0 else 0
    cpu.A = uint8(r)
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 1

@cpu.opcode(0xE6, "AND d8", cycles=2)
def op_and_d8(cpu):
    cpu.A = cpu.A & read_imm8()
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1
    cpu.F.C = 0

@cpu.opcode(0xEE, "XOR d8", cycles=2)
def op_xor_d8(cpu):
    cpu.A = cpu.A ^ read_imm8()
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = 0

@cpu.opcode(0xF6, "OR d8", cycles=2)
def op_or_d8(cpu):
    cpu.A = cpu.A | read_imm8()
    cpu.F.Z = 1 if cpu.A == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = 0

@cpu.opcode(0xFE, "CP d8", cycles=2)
def op_cp_d8(cpu):
    v = read_imm8()
    cpu.F.Z = 1 if cpu.A == v else 0
    cpu.F.N = 1
    cpu.F.H = 1 if (cpu.A & 15) < (v & 15) else 0
    cpu.F.C = 1 if cpu.A < v else 0

# === RET / CALL / JP / RST / PUSH / POP / misc ===

@cpu.opcode(0xC0, "RET NZ", cycles=2)
def op_ret_nz(cpu):
    if cpu.F.Z == 0:
        lo = mem_read(cpu.SP)
        cpu.SP = uint16(cpu.SP + 1)
        hi = mem_read(cpu.SP)
        cpu.SP = uint16(cpu.SP + 1)
        cpu.PC = uint16((hi << 8) | lo)
        cpu.cycle_count = cpu.cycle_count + 3

@cpu.opcode(0xC8, "RET Z", cycles=2)
def op_ret_z(cpu):
    if cpu.F.Z:
        lo = mem_read(cpu.SP)
        cpu.SP = uint16(cpu.SP + 1)
        hi = mem_read(cpu.SP)
        cpu.SP = uint16(cpu.SP + 1)
        cpu.PC = uint16((hi << 8) | lo)
        cpu.cycle_count = cpu.cycle_count + 3

@cpu.opcode(0xD0, "RET NC", cycles=2)
def op_ret_nc(cpu):
    if cpu.F.C == 0:
        lo = mem_read(cpu.SP)
        cpu.SP = uint16(cpu.SP + 1)
        hi = mem_read(cpu.SP)
        cpu.SP = uint16(cpu.SP + 1)
        cpu.PC = uint16((hi << 8) | lo)
        cpu.cycle_count = cpu.cycle_count + 3

@cpu.opcode(0xD8, "RET C", cycles=2)
def op_ret_c(cpu):
    if cpu.F.C:
        lo = mem_read(cpu.SP)
        cpu.SP = uint16(cpu.SP + 1)
        hi = mem_read(cpu.SP)
        cpu.SP = uint16(cpu.SP + 1)
        cpu.PC = uint16((hi << 8) | lo)
        cpu.cycle_count = cpu.cycle_count + 3

@cpu.opcode(0xC9, "RET", cycles=4)
def op_ret(cpu):
    lo = mem_read(cpu.SP)
    cpu.SP = uint16(cpu.SP + 1)
    hi = mem_read(cpu.SP)
    cpu.SP = uint16(cpu.SP + 1)
    cpu.PC = uint16((hi << 8) | lo)

@cpu.opcode(0xD9, "RETI", cycles=4)
def op_reti(cpu):
    lo = mem_read(cpu.SP)
    cpu.SP = uint16(cpu.SP + 1)
    hi = mem_read(cpu.SP)
    cpu.SP = uint16(cpu.SP + 1)
    cpu.PC = uint16((hi << 8) | lo)
    cpu.ime = 1

# --- JP ---
@cpu.opcode(0xC3, "JP a16", cycles=4)
def op_jp(cpu):
    lo = read_imm8()
    hi = read_imm8()
    cpu.PC = uint16((hi << 8) | lo)

@cpu.opcode(0xC2, "JP NZ,a16", cycles=3)
def op_jp_nz(cpu):
    lo = read_imm8()
    hi = read_imm8()
    if cpu.F.Z == 0:
        cpu.PC = uint16((hi << 8) | lo)
        cpu.cycle_count = cpu.cycle_count + 1

@cpu.opcode(0xCA, "JP Z,a16", cycles=3)
def op_jp_z(cpu):
    lo = read_imm8()
    hi = read_imm8()
    if cpu.F.Z:
        cpu.PC = uint16((hi << 8) | lo)
        cpu.cycle_count = cpu.cycle_count + 1

@cpu.opcode(0xD2, "JP NC,a16", cycles=3)
def op_jp_nc(cpu):
    lo = read_imm8()
    hi = read_imm8()
    if cpu.F.C == 0:
        cpu.PC = uint16((hi << 8) | lo)
        cpu.cycle_count = cpu.cycle_count + 1

@cpu.opcode(0xDA, "JP C,a16", cycles=3)
def op_jp_c(cpu):
    lo = read_imm8()
    hi = read_imm8()
    if cpu.F.C:
        cpu.PC = uint16((hi << 8) | lo)
        cpu.cycle_count = cpu.cycle_count + 1

@cpu.opcode(0xE9, "JP HL", cycles=1)
def op_jp_hl(cpu):
    cpu.PC = cpu.HL

# --- CALL ---
@cpu.opcode(0xCD, "CALL a16", cycles=6)
def op_call(cpu):
    lo = read_imm8()
    hi = read_imm8()
    push16(cpu.PC)
    cpu.PC = uint16((hi << 8) | lo)

@cpu.opcode(0xC4, "CALL NZ,a16", cycles=3)
def op_call_nz(cpu):
    lo = read_imm8()
    hi = read_imm8()
    if cpu.F.Z == 0:
        push16(cpu.PC)
        cpu.PC = uint16((hi << 8) | lo)
        cpu.cycle_count = cpu.cycle_count + 3

@cpu.opcode(0xCC, "CALL Z,a16", cycles=3)
def op_call_z(cpu):
    lo = read_imm8()
    hi = read_imm8()
    if cpu.F.Z:
        push16(cpu.PC)
        cpu.PC = uint16((hi << 8) | lo)
        cpu.cycle_count = cpu.cycle_count + 3

@cpu.opcode(0xD4, "CALL NC,a16", cycles=3)
def op_call_nc(cpu):
    lo = read_imm8()
    hi = read_imm8()
    if cpu.F.C == 0:
        push16(cpu.PC)
        cpu.PC = uint16((hi << 8) | lo)
        cpu.cycle_count = cpu.cycle_count + 3

@cpu.opcode(0xDC, "CALL C,a16", cycles=3)
def op_call_c(cpu):
    lo = read_imm8()
    hi = read_imm8()
    if cpu.F.C:
        push16(cpu.PC)
        cpu.PC = uint16((hi << 8) | lo)
        cpu.cycle_count = cpu.cycle_count + 3

# --- RST (transpiled) ---
@cpu.opcode(0xC7, "RST 00H", cycles=4)
def op_rst_00(cpu):
    push16(cpu.PC)
    cpu.PC = 0

@cpu.opcode(0xCF, "RST 08H", cycles=4)
def op_rst_08(cpu):
    push16(cpu.PC)
    cpu.PC = 8

@cpu.opcode(0xD7, "RST 10H", cycles=4)
def op_rst_10(cpu):
    push16(cpu.PC)
    cpu.PC = 16

@cpu.opcode(0xDF, "RST 18H", cycles=4)
def op_rst_18(cpu):
    push16(cpu.PC)
    cpu.PC = 24

@cpu.opcode(0xE7, "RST 20H", cycles=4)
def op_rst_20(cpu):
    push16(cpu.PC)
    cpu.PC = 32

@cpu.opcode(0xEF, "RST 28H", cycles=4)
def op_rst_28(cpu):
    push16(cpu.PC)
    cpu.PC = 40

@cpu.opcode(0xF7, "RST 30H", cycles=4)
def op_rst_30(cpu):
    push16(cpu.PC)
    cpu.PC = 48

@cpu.opcode(0xFF, "RST 38H", cycles=4)
def op_rst_38(cpu):
    push16(cpu.PC)
    cpu.PC = 56

# --- PUSH / POP ---
@cpu.opcode(0xC5, "PUSH BC", cycles=4)
def op_push_bc(cpu):
    push16(cpu.BC)

@cpu.opcode(0xD5, "PUSH DE", cycles=4)
def op_push_de(cpu):
    push16(cpu.DE)

@cpu.opcode(0xE5, "PUSH HL", cycles=4)
def op_push_hl(cpu):
    push16(cpu.HL)

@cpu.opcode(0xF5, "PUSH AF", cycles=4)
def op_push_af(cpu):
    push16(cpu.AF)

@cpu.opcode(0xC1, "POP BC", cycles=3)
def op_pop_bc(cpu):
    lo = mem_read(cpu.SP)
    cpu.SP = uint16(cpu.SP + 1)
    hi = mem_read(cpu.SP)
    cpu.SP = uint16(cpu.SP + 1)
    cpu.B = hi
    cpu.C = lo

@cpu.opcode(0xD1, "POP DE", cycles=3)
def op_pop_de(cpu):
    lo = mem_read(cpu.SP)
    cpu.SP = uint16(cpu.SP + 1)
    hi = mem_read(cpu.SP)
    cpu.SP = uint16(cpu.SP + 1)
    cpu.D = hi
    cpu.E = lo

@cpu.opcode(0xE1, "POP HL", cycles=3)
def op_pop_hl(cpu):
    lo = mem_read(cpu.SP)
    cpu.SP = uint16(cpu.SP + 1)
    hi = mem_read(cpu.SP)
    cpu.SP = uint16(cpu.SP + 1)
    cpu.H = hi
    cpu.L = lo

@cpu.opcode(0xF1, "POP AF", cycles=3)
def op_pop_af(cpu):
    lo = mem_read(cpu.SP)
    cpu.SP = uint16(cpu.SP + 1)
    hi = mem_read(cpu.SP)
    cpu.SP = uint16(cpu.SP + 1)
    cpu.A = hi
    cpu.F = uint8(lo & 240)

# --- Misc ---
@cpu.opcode(0xE0, "LDH (a8),A", cycles=3)
def op_ldh_a8_a(cpu):
    addr = uint16(0xFF00 + read_imm8())
    mem_write(addr, cpu.A)

@cpu.opcode(0xF0, "LDH A,(a8)", cycles=3)
def op_ldh_a_a8(cpu):
    addr = uint16(0xFF00 + read_imm8())
    cpu.A = mem_read(addr)

@cpu.opcode(0xE2, "LD (C),A", cycles=2)
def op_ld_c_ind_a(cpu):
    mem_write(uint16(0xFF00 + cpu.C), cpu.A)

@cpu.opcode(0xF2, "LD A,(C)", cycles=2)
def op_ld_a_c_ind(cpu):
    cpu.A = mem_read(uint16(0xFF00 + cpu.C))

@cpu.opcode(0xEA, "LD (a16),A", cycles=4)
def op_ld_a16_a(cpu):
    lo = read_imm8()
    hi = read_imm8()
    mem_write(uint16((hi << 8) | lo), cpu.A)

@cpu.opcode(0xFA, "LD A,(a16)", cycles=4)
def op_ld_a_a16(cpu):
    lo = read_imm8()
    hi = read_imm8()
    cpu.A = mem_read(uint16((hi << 8) | lo))

@cpu.opcode(0xE8, "ADD SP,r8", cycles=4)
def op_add_sp_r8(cpu):
    offset = int8(read_imm8())
    result = int(cpu.SP) + offset
    cpu.F.Z = 0
    cpu.F.N = 0
    cpu.F.H = 1 if ((cpu.SP ^ offset ^ result) & 16) else 0
    cpu.F.C = 1 if ((cpu.SP ^ offset ^ result) & 256) else 0
    cpu.SP = uint16(result)

@cpu.opcode(0xF8, "LD HL,SP+r8", cycles=3)
def op_ld_hl_sp_r8(cpu):
    offset = int8(read_imm8())
    result = int(cpu.SP) + offset
    cpu.F.Z = 0
    cpu.F.N = 0
    cpu.F.H = 1 if ((cpu.SP ^ offset ^ result) & 16) else 0
    cpu.F.C = 1 if ((cpu.SP ^ offset ^ result) & 256) else 0
    cpu.HL = uint16(result)

@cpu.opcode(0xF9, "LD SP,HL", cycles=2)
def op_ld_sp_hl(cpu):
    cpu.SP = cpu.HL

# --- DI / EI ---
@cpu.opcode(0xF3, "DI", cycles=1)
def op_di(cpu):
    cpu.ime = 0
    cpu.ime_delay = 0

@cpu.opcode(0xFB, "EI", cycles=1)
def op_ei(cpu):
    cpu.ime_delay = 2

# ===================================================================
# CB-prefix opcodes (256 opcodes) -- ALL transpiled from Python
# ===================================================================

# --- RLC r (0x00-0x07) ---
@cpu.prefix_opcode_family(0xCB, "RLC {}", [
    (0x00,'B'),(0x01,'C'),(0x02,'D'),(0x03,'E'),
    (0x04,'H'),(0x05,'L'),(0x07,'A'),
], cycles=2)
def cb_rlc_r(cpu, reg):
    val = cpu.reg
    c = (val >> 7) & 1
    cpu.reg = uint8((val << 1) | c)
    cpu.F.Z = 1 if cpu.reg == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = c

@cpu.prefix_opcode(0xCB, 0x06, "RLC (HL)", cycles=4)
def cb_rlc_hl(cpu):
    val = mem_read(cpu.HL)
    c = (val >> 7) & 1
    r = uint8((val << 1) | c)
    mem_write(cpu.HL, r)
    cpu.F.Z = 1 if r == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = c

# --- RRC r (0x08-0x0F) ---
@cpu.prefix_opcode_family(0xCB, "RRC {}", [
    (0x08,'B'),(0x09,'C'),(0x0A,'D'),(0x0B,'E'),
    (0x0C,'H'),(0x0D,'L'),(0x0F,'A'),
], cycles=2)
def cb_rrc_r(cpu, reg):
    val = cpu.reg
    c = val & 1
    cpu.reg = uint8((val >> 1) | (c << 7))
    cpu.F.Z = 1 if cpu.reg == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = c

@cpu.prefix_opcode(0xCB, 0x0E, "RRC (HL)", cycles=4)
def cb_rrc_hl(cpu):
    val = mem_read(cpu.HL)
    c = val & 1
    r = uint8((val >> 1) | (c << 7))
    mem_write(cpu.HL, r)
    cpu.F.Z = 1 if r == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = c

# --- RL r (0x10-0x17) ---
@cpu.prefix_opcode_family(0xCB, "RL {}", [
    (0x10,'B'),(0x11,'C'),(0x12,'D'),(0x13,'E'),
    (0x14,'H'),(0x15,'L'),(0x17,'A'),
], cycles=2)
def cb_rl_r(cpu, reg):
    val = cpu.reg
    old_c = cpu.F.C
    c = (val >> 7) & 1
    cpu.reg = uint8((val << 1) | old_c)
    cpu.F.Z = 1 if cpu.reg == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = c

@cpu.prefix_opcode(0xCB, 0x16, "RL (HL)", cycles=4)
def cb_rl_hl(cpu):
    val = mem_read(cpu.HL)
    old_c = cpu.F.C
    c = (val >> 7) & 1
    r = uint8((val << 1) | old_c)
    mem_write(cpu.HL, r)
    cpu.F.Z = 1 if r == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = c

# --- RR r (0x18-0x1F) ---
@cpu.prefix_opcode_family(0xCB, "RR {}", [
    (0x18,'B'),(0x19,'C'),(0x1A,'D'),(0x1B,'E'),
    (0x1C,'H'),(0x1D,'L'),(0x1F,'A'),
], cycles=2)
def cb_rr_r(cpu, reg):
    val = cpu.reg
    old_c = cpu.F.C
    c = val & 1
    cpu.reg = uint8((val >> 1) | (old_c << 7))
    cpu.F.Z = 1 if cpu.reg == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = c

@cpu.prefix_opcode(0xCB, 0x1E, "RR (HL)", cycles=4)
def cb_rr_hl(cpu):
    val = mem_read(cpu.HL)
    old_c = cpu.F.C
    c = val & 1
    r = uint8((val >> 1) | (old_c << 7))
    mem_write(cpu.HL, r)
    cpu.F.Z = 1 if r == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = c

# --- SLA r (0x20-0x27) ---
@cpu.prefix_opcode_family(0xCB, "SLA {}", [
    (0x20,'B'),(0x21,'C'),(0x22,'D'),(0x23,'E'),
    (0x24,'H'),(0x25,'L'),(0x27,'A'),
], cycles=2)
def cb_sla_r(cpu, reg):
    val = cpu.reg
    c = (val >> 7) & 1
    cpu.reg = uint8(val << 1)
    cpu.F.Z = 1 if cpu.reg == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = c

@cpu.prefix_opcode(0xCB, 0x26, "SLA (HL)", cycles=4)
def cb_sla_hl(cpu):
    val = mem_read(cpu.HL)
    c = (val >> 7) & 1
    r = uint8(val << 1)
    mem_write(cpu.HL, r)
    cpu.F.Z = 1 if r == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = c

# --- SRA r (0x28-0x2F) ---
@cpu.prefix_opcode_family(0xCB, "SRA {}", [
    (0x28,'B'),(0x29,'C'),(0x2A,'D'),(0x2B,'E'),
    (0x2C,'H'),(0x2D,'L'),(0x2F,'A'),
], cycles=2)
def cb_sra_r(cpu, reg):
    val = cpu.reg
    c = val & 1
    cpu.reg = uint8((val >> 1) | (val & 128))
    cpu.F.Z = 1 if cpu.reg == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = c

@cpu.prefix_opcode(0xCB, 0x2E, "SRA (HL)", cycles=4)
def cb_sra_hl(cpu):
    val = mem_read(cpu.HL)
    c = val & 1
    r = uint8((val >> 1) | (val & 128))
    mem_write(cpu.HL, r)
    cpu.F.Z = 1 if r == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = c

# --- SWAP r (0x30-0x37) ---
@cpu.prefix_opcode_family(0xCB, "SWAP {}", [
    (0x30,'B'),(0x31,'C'),(0x32,'D'),(0x33,'E'),
    (0x34,'H'),(0x35,'L'),(0x37,'A'),
], cycles=2)
def cb_swap_r(cpu, reg):
    val = cpu.reg
    cpu.reg = uint8((val >> 4) | (val << 4))
    cpu.F.Z = 1 if cpu.reg == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = 0

@cpu.prefix_opcode(0xCB, 0x36, "SWAP (HL)", cycles=4)
def cb_swap_hl(cpu):
    val = mem_read(cpu.HL)
    r = uint8((val >> 4) | (val << 4))
    mem_write(cpu.HL, r)
    cpu.F.Z = 1 if r == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = 0

# --- SRL r (0x38-0x3F) ---
@cpu.prefix_opcode_family(0xCB, "SRL {}", [
    (0x38,'B'),(0x39,'C'),(0x3A,'D'),(0x3B,'E'),
    (0x3C,'H'),(0x3D,'L'),(0x3F,'A'),
], cycles=2)
def cb_srl_r(cpu, reg):
    val = cpu.reg
    c = val & 1
    cpu.reg = uint8(val >> 1)
    cpu.F.Z = 1 if cpu.reg == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = c

@cpu.prefix_opcode(0xCB, 0x3E, "SRL (HL)", cycles=4)
def cb_srl_hl(cpu):
    val = mem_read(cpu.HL)
    c = val & 1
    r = uint8(val >> 1)
    mem_write(cpu.HL, r)
    cpu.F.Z = 1 if r == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 0
    cpu.F.C = c

# --- BIT b,r (0x40-0x7F) ---
@cpu.prefix_opcode_family(0xCB, "BIT 0,{}", [
    (0x40,'B'),(0x41,'C'),(0x42,'D'),(0x43,'E'),
    (0x44,'H'),(0x45,'L'),(0x47,'A'),
], cycles=2)
def cb_bit0_r(cpu, reg):
    cpu.F.Z = 1 if (cpu.reg & 1) == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1

@cpu.prefix_opcode_family(0xCB, "BIT 1,{}", [
    (0x48,'B'),(0x49,'C'),(0x4A,'D'),(0x4B,'E'),
    (0x4C,'H'),(0x4D,'L'),(0x4F,'A'),
], cycles=2)
def cb_bit1_r(cpu, reg):
    cpu.F.Z = 1 if (cpu.reg & 2) == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1

@cpu.prefix_opcode_family(0xCB, "BIT 2,{}", [
    (0x50,'B'),(0x51,'C'),(0x52,'D'),(0x53,'E'),
    (0x54,'H'),(0x55,'L'),(0x57,'A'),
], cycles=2)
def cb_bit2_r(cpu, reg):
    cpu.F.Z = 1 if (cpu.reg & 4) == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1

@cpu.prefix_opcode_family(0xCB, "BIT 3,{}", [
    (0x58,'B'),(0x59,'C'),(0x5A,'D'),(0x5B,'E'),
    (0x5C,'H'),(0x5D,'L'),(0x5F,'A'),
], cycles=2)
def cb_bit3_r(cpu, reg):
    cpu.F.Z = 1 if (cpu.reg & 8) == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1

@cpu.prefix_opcode_family(0xCB, "BIT 4,{}", [
    (0x60,'B'),(0x61,'C'),(0x62,'D'),(0x63,'E'),
    (0x64,'H'),(0x65,'L'),(0x67,'A'),
], cycles=2)
def cb_bit4_r(cpu, reg):
    cpu.F.Z = 1 if (cpu.reg & 16) == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1

@cpu.prefix_opcode_family(0xCB, "BIT 5,{}", [
    (0x68,'B'),(0x69,'C'),(0x6A,'D'),(0x6B,'E'),
    (0x6C,'H'),(0x6D,'L'),(0x6F,'A'),
], cycles=2)
def cb_bit5_r(cpu, reg):
    cpu.F.Z = 1 if (cpu.reg & 32) == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1

@cpu.prefix_opcode_family(0xCB, "BIT 6,{}", [
    (0x70,'B'),(0x71,'C'),(0x72,'D'),(0x73,'E'),
    (0x74,'H'),(0x75,'L'),(0x77,'A'),
], cycles=2)
def cb_bit6_r(cpu, reg):
    cpu.F.Z = 1 if (cpu.reg & 64) == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1

@cpu.prefix_opcode_family(0xCB, "BIT 7,{}", [
    (0x78,'B'),(0x79,'C'),(0x7A,'D'),(0x7B,'E'),
    (0x7C,'H'),(0x7D,'L'),(0x7F,'A'),
], cycles=2)
def cb_bit7_r(cpu, reg):
    cpu.F.Z = 1 if (cpu.reg & 128) == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1

# BIT b,(HL)
@cpu.prefix_opcode(0xCB, 0x46, "BIT 0,(HL)", cycles=3)
def cb_bit0_hl(cpu):
    cpu.F.Z = 1 if (mem_read(cpu.HL) & 1) == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1

@cpu.prefix_opcode(0xCB, 0x4E, "BIT 1,(HL)", cycles=3)
def cb_bit1_hl(cpu):
    cpu.F.Z = 1 if (mem_read(cpu.HL) & 2) == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1

@cpu.prefix_opcode(0xCB, 0x56, "BIT 2,(HL)", cycles=3)
def cb_bit2_hl(cpu):
    cpu.F.Z = 1 if (mem_read(cpu.HL) & 4) == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1

@cpu.prefix_opcode(0xCB, 0x5E, "BIT 3,(HL)", cycles=3)
def cb_bit3_hl(cpu):
    cpu.F.Z = 1 if (mem_read(cpu.HL) & 8) == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1

@cpu.prefix_opcode(0xCB, 0x66, "BIT 4,(HL)", cycles=3)
def cb_bit4_hl(cpu):
    cpu.F.Z = 1 if (mem_read(cpu.HL) & 16) == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1

@cpu.prefix_opcode(0xCB, 0x6E, "BIT 5,(HL)", cycles=3)
def cb_bit5_hl(cpu):
    cpu.F.Z = 1 if (mem_read(cpu.HL) & 32) == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1

@cpu.prefix_opcode(0xCB, 0x76, "BIT 6,(HL)", cycles=3)
def cb_bit6_hl(cpu):
    cpu.F.Z = 1 if (mem_read(cpu.HL) & 64) == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1

@cpu.prefix_opcode(0xCB, 0x7E, "BIT 7,(HL)", cycles=3)
def cb_bit7_hl(cpu):
    cpu.F.Z = 1 if (mem_read(cpu.HL) & 128) == 0 else 0
    cpu.F.N = 0
    cpu.F.H = 1

# --- RES b,r (0x80-0xBF) ---
@cpu.prefix_opcode_family(0xCB, "RES 0,{}", [(0x80,'B'),(0x81,'C'),(0x82,'D'),(0x83,'E'),(0x84,'H'),(0x85,'L'),(0x87,'A')], cycles=2)
def cb_res0_r(cpu, reg):
    cpu.reg = cpu.reg & 254

@cpu.prefix_opcode_family(0xCB, "RES 1,{}", [(0x88,'B'),(0x89,'C'),(0x8A,'D'),(0x8B,'E'),(0x8C,'H'),(0x8D,'L'),(0x8F,'A')], cycles=2)
def cb_res1_r(cpu, reg):
    cpu.reg = cpu.reg & 253

@cpu.prefix_opcode_family(0xCB, "RES 2,{}", [(0x90,'B'),(0x91,'C'),(0x92,'D'),(0x93,'E'),(0x94,'H'),(0x95,'L'),(0x97,'A')], cycles=2)
def cb_res2_r(cpu, reg):
    cpu.reg = cpu.reg & 251

@cpu.prefix_opcode_family(0xCB, "RES 3,{}", [(0x98,'B'),(0x99,'C'),(0x9A,'D'),(0x9B,'E'),(0x9C,'H'),(0x9D,'L'),(0x9F,'A')], cycles=2)
def cb_res3_r(cpu, reg):
    cpu.reg = cpu.reg & 247

@cpu.prefix_opcode_family(0xCB, "RES 4,{}", [(0xA0,'B'),(0xA1,'C'),(0xA2,'D'),(0xA3,'E'),(0xA4,'H'),(0xA5,'L'),(0xA7,'A')], cycles=2)
def cb_res4_r(cpu, reg):
    cpu.reg = cpu.reg & 239

@cpu.prefix_opcode_family(0xCB, "RES 5,{}", [(0xA8,'B'),(0xA9,'C'),(0xAA,'D'),(0xAB,'E'),(0xAC,'H'),(0xAD,'L'),(0xAF,'A')], cycles=2)
def cb_res5_r(cpu, reg):
    cpu.reg = cpu.reg & 223

@cpu.prefix_opcode_family(0xCB, "RES 6,{}", [(0xB0,'B'),(0xB1,'C'),(0xB2,'D'),(0xB3,'E'),(0xB4,'H'),(0xB5,'L'),(0xB7,'A')], cycles=2)
def cb_res6_r(cpu, reg):
    cpu.reg = cpu.reg & 191

@cpu.prefix_opcode_family(0xCB, "RES 7,{}", [(0xB8,'B'),(0xB9,'C'),(0xBA,'D'),(0xBB,'E'),(0xBC,'H'),(0xBD,'L'),(0xBF,'A')], cycles=2)
def cb_res7_r(cpu, reg):
    cpu.reg = cpu.reg & 127

# RES b,(HL)
@cpu.prefix_opcode(0xCB, 0x86, "RES 0,(HL)", cycles=4)
def cb_res0_hl(cpu):
    mem_write(cpu.HL, mem_read(cpu.HL) & 254)

@cpu.prefix_opcode(0xCB, 0x8E, "RES 1,(HL)", cycles=4)
def cb_res1_hl(cpu):
    mem_write(cpu.HL, mem_read(cpu.HL) & 253)

@cpu.prefix_opcode(0xCB, 0x96, "RES 2,(HL)", cycles=4)
def cb_res2_hl(cpu):
    mem_write(cpu.HL, mem_read(cpu.HL) & 251)

@cpu.prefix_opcode(0xCB, 0x9E, "RES 3,(HL)", cycles=4)
def cb_res3_hl(cpu):
    mem_write(cpu.HL, mem_read(cpu.HL) & 247)

@cpu.prefix_opcode(0xCB, 0xA6, "RES 4,(HL)", cycles=4)
def cb_res4_hl(cpu):
    mem_write(cpu.HL, mem_read(cpu.HL) & 239)

@cpu.prefix_opcode(0xCB, 0xAE, "RES 5,(HL)", cycles=4)
def cb_res5_hl(cpu):
    mem_write(cpu.HL, mem_read(cpu.HL) & 223)

@cpu.prefix_opcode(0xCB, 0xB6, "RES 6,(HL)", cycles=4)
def cb_res6_hl(cpu):
    mem_write(cpu.HL, mem_read(cpu.HL) & 191)

@cpu.prefix_opcode(0xCB, 0xBE, "RES 7,(HL)", cycles=4)
def cb_res7_hl(cpu):
    mem_write(cpu.HL, mem_read(cpu.HL) & 127)

# --- SET b,r (0xC0-0xFF) ---
@cpu.prefix_opcode_family(0xCB, "SET 0,{}", [(0xC0,'B'),(0xC1,'C'),(0xC2,'D'),(0xC3,'E'),(0xC4,'H'),(0xC5,'L'),(0xC7,'A')], cycles=2)
def cb_set0_r(cpu, reg):
    cpu.reg = cpu.reg | 1

@cpu.prefix_opcode_family(0xCB, "SET 1,{}", [(0xC8,'B'),(0xC9,'C'),(0xCA,'D'),(0xCB,'E'),(0xCC,'H'),(0xCD,'L'),(0xCF,'A')], cycles=2)
def cb_set1_r(cpu, reg):
    cpu.reg = cpu.reg | 2

@cpu.prefix_opcode_family(0xCB, "SET 2,{}", [(0xD0,'B'),(0xD1,'C'),(0xD2,'D'),(0xD3,'E'),(0xD4,'H'),(0xD5,'L'),(0xD7,'A')], cycles=2)
def cb_set2_r(cpu, reg):
    cpu.reg = cpu.reg | 4

@cpu.prefix_opcode_family(0xCB, "SET 3,{}", [(0xD8,'B'),(0xD9,'C'),(0xDA,'D'),(0xDB,'E'),(0xDC,'H'),(0xDD,'L'),(0xDF,'A')], cycles=2)
def cb_set3_r(cpu, reg):
    cpu.reg = cpu.reg | 8

@cpu.prefix_opcode_family(0xCB, "SET 4,{}", [(0xE0,'B'),(0xE1,'C'),(0xE2,'D'),(0xE3,'E'),(0xE4,'H'),(0xE5,'L'),(0xE7,'A')], cycles=2)
def cb_set4_r(cpu, reg):
    cpu.reg = cpu.reg | 16

@cpu.prefix_opcode_family(0xCB, "SET 5,{}", [(0xE8,'B'),(0xE9,'C'),(0xEA,'D'),(0xEB,'E'),(0xEC,'H'),(0xED,'L'),(0xEF,'A')], cycles=2)
def cb_set5_r(cpu, reg):
    cpu.reg = cpu.reg | 32

@cpu.prefix_opcode_family(0xCB, "SET 6,{}", [(0xF0,'B'),(0xF1,'C'),(0xF2,'D'),(0xF3,'E'),(0xF4,'H'),(0xF5,'L'),(0xF7,'A')], cycles=2)
def cb_set6_r(cpu, reg):
    cpu.reg = cpu.reg | 64

@cpu.prefix_opcode_family(0xCB, "SET 7,{}", [(0xF8,'B'),(0xF9,'C'),(0xFA,'D'),(0xFB,'E'),(0xFC,'H'),(0xFD,'L'),(0xFF,'A')], cycles=2)
def cb_set7_r(cpu, reg):
    cpu.reg = cpu.reg | 128

# SET b,(HL)
@cpu.prefix_opcode(0xCB, 0xC6, "SET 0,(HL)", cycles=4)
def cb_set0_hl(cpu):
    mem_write(cpu.HL, mem_read(cpu.HL) | 1)

@cpu.prefix_opcode(0xCB, 0xCE, "SET 1,(HL)", cycles=4)
def cb_set1_hl(cpu):
    mem_write(cpu.HL, mem_read(cpu.HL) | 2)

@cpu.prefix_opcode(0xCB, 0xD6, "SET 2,(HL)", cycles=4)
def cb_set2_hl(cpu):
    mem_write(cpu.HL, mem_read(cpu.HL) | 4)

@cpu.prefix_opcode(0xCB, 0xDE, "SET 3,(HL)", cycles=4)
def cb_set3_hl(cpu):
    mem_write(cpu.HL, mem_read(cpu.HL) | 8)

@cpu.prefix_opcode(0xCB, 0xE6, "SET 4,(HL)", cycles=4)
def cb_set4_hl(cpu):
    mem_write(cpu.HL, mem_read(cpu.HL) | 16)

@cpu.prefix_opcode(0xCB, 0xEE, "SET 5,(HL)", cycles=4)
def cb_set5_hl(cpu):
    mem_write(cpu.HL, mem_read(cpu.HL) | 32)

@cpu.prefix_opcode(0xCB, 0xF6, "SET 6,(HL)", cycles=4)
def cb_set6_hl(cpu):
    mem_write(cpu.HL, mem_read(cpu.HL) | 64)

@cpu.prefix_opcode(0xCB, 0xFE, "SET 7,(HL)", cycles=4)
def cb_set7_hl(cpu):
    mem_write(cpu.HL, mem_read(cpu.HL) | 128)

# ===================================================================
# Finalize CPU and Board
# ===================================================================
cpu_chip.set_cpu_core(cpu)

board = Board("GameBoy", comment="Nintendo Game Boy DMG")
board.set_master_clock(master_clock)
board.add_chip(cpu_chip)
board.add_chip(ppu_chip)
board.add_chip(apu_chip)
board.add_chip(timer_chip)
board.add_chip(joypad_chip)
board.add_bus(bus)

# External function hooks
board.add_extern_func("render_frame", "void",
                      [("framebuffer", "uint8_t*"), ("width", "int"), ("height", "int")])
board.add_extern_func("audio_push", "void",
                      [("samples", "int16_t*"), ("count", "int")])
board.add_extern_func("poll_input", "void",
                      [("sys", "void*")])

# ===================================================================
# Code Generation
# ===================================================================
if __name__ == "__main__":
    errors = board.validate()
    if errors:
        print("Validation errors:")
        for e in errors:
            print(f"  - {e}")
        _sys.exit(1)

    gen = BoardCodeGenerator(board)
    code = gen.generate()

    # Append a test main
    code += """

/* === Stub implementations for standalone testing === */
void render_frame(uint8_t* fb, int w, int h) {
    (void)fb; (void)w; (void)h;
}
void audio_push(int16_t* samples, int count) {
    (void)samples; (void)count;
}
void poll_input(void* sys) {
    (void)sys;
}

int main(int argc, char** argv) {
    gameboy_t sys;
    gameboy_init(&sys);

    /* Set SP, PC, F to typical post-boot values */
    sys.cpu.SP = 0xFFFE;
    sys.cpu.PC = 0x0100;
    sys.cpu.F = 0xB0;

    if (argc > 1) {
        FILE* f = fopen(argv[1], "rb");
        if (f) {
            fseek(f, 0, SEEK_END);
            long size = ftell(f);
            fseek(f, 0, SEEK_SET);
            sys.cpu.rom = (uint8_t*)malloc(size);
            sys.cpu.rom_size = (uint32_t)size;
            fread(sys.cpu.rom, 1, size, f);
            fclose(f);

            /* Detect MBC type from cartridge header */
            if (size > 0x0149) {
                uint8_t cart_type = sys.cpu.rom[0x0147];
                if (cart_type >= 0x01 && cart_type <= 0x03) sys.cpu.mbc_type = 1;
                else if (cart_type >= 0x0F && cart_type <= 0x13) sys.cpu.mbc_type = 3;
                else if (cart_type >= 0x19 && cart_type <= 0x1E) sys.cpu.mbc_type = 5;

                /* Allocate cart RAM based on header byte 0x0149 */
                uint8_t ram_code = sys.cpu.rom[0x0149];
                uint32_t ram_sizes[] = {0, 0, 8192, 32768, 131072, 65536};
                if (ram_code > 0 && ram_code <= 5) {
                    sys.cpu.cart_ram_size = ram_sizes[ram_code];
                    sys.cpu.cart_ram = (uint8_t*)calloc(sys.cpu.cart_ram_size, 1);
                }
            }
            printf("Loaded ROM: %ld bytes, MBC type: %d, RAM: %u bytes\\n", size, sys.cpu.mbc_type, sys.cpu.cart_ram_size);
        } else {
            printf("Failed to open ROM: %s\\n", argv[1]);
            return 1;
        }
    } else {
        /* No ROM: load a small test program */
        static uint8_t test_rom[32768];
        memset(test_rom, 0, sizeof(test_rom));
        /* LD SP, 0xFFFE */
        test_rom[0x100] = 0x31;
        test_rom[0x101] = 0xFE;
        test_rom[0x102] = 0xFF;
        /* LD A, 42 */
        test_rom[0x103] = 0x3E;
        test_rom[0x104] = 42;
        /* LD B, A */
        test_rom[0x105] = 0x47;
        /* ADD A, B */
        test_rom[0x106] = 0x80;
        /* HALT */
        test_rom[0x107] = 0x76;
        sys.cpu.rom = test_rom;
        sys.cpu.rom_size = sizeof(test_rom);
        printf("No ROM specified, running test program...\\n");
    }

    /* Run */
    for (int i = 0; i < 1000000 && !sys.cpu.halted; i++) {
        gameboy_step(&sys);
    }
    printf("A=%d B=%d halted=%d cycles=%llu\\n",
           sys.cpu.A, sys.cpu.B, sys.cpu.halted,
           (unsigned long long)sys.cpu.cycle_count);

    if (sys.cpu.rom && argc > 1) free(sys.cpu.rom);
    return 0;
}
"""

    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "game_boy.c")
    with open(out_path, "w") as f:
        f.write(code)
    print(f"Generated: {out_path}")
    print(f"  Opcodes: {len(cpu.opcodes)} main + {len(cpu.prefix_tables.get(0xCB, {}))} CB-prefix")
    print(f"  Size: {len(code)} bytes")
