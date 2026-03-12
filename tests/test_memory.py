"""
Tier 1C -- Memory model unit tests.

Tests MemoryRegion, MemoryBank, MemoryController, MemoryBus at the Python level.
"""

import pytest
from proto.memory import (
    MemoryRegion, MemoryBank, MemoryBus, MemoryController,
    MemoryAccessLevel, Handler, HandlerType, BusMapping, BusOverlay,
)


# ===================================================================
# MemoryRegion
# ===================================================================

class TestMemoryRegion:

    def test_basic_creation(self):
        r = MemoryRegion("ram", size_in_bytes=1024)
        assert r.name == "ram"
        assert r.size_in_bytes == 1024
        assert r.access == MemoryAccessLevel.ReadWrite  # default
        assert r.c_data_type == "uint8_t"  # default

    def test_read_only(self):
        r = MemoryRegion("rom", size_in_bytes=32768,
                         access=MemoryAccessLevel.ReadOnly)
        assert r.access == MemoryAccessLevel.ReadOnly

    def test_write_only(self):
        r = MemoryRegion("fifo", size_in_bytes=16,
                         access=MemoryAccessLevel.WriteOnly)
        assert r.access == MemoryAccessLevel.WriteOnly

    def test_dynamic_region(self):
        r = MemoryRegion("cart_rom", size_in_bytes=0)
        assert r.is_dynamic is True

    def test_static_region(self):
        r = MemoryRegion("ram", size_in_bytes=256)
        assert r.is_dynamic is False

    def test_custom_data_type(self):
        r = MemoryRegion("vram", size_in_bytes=8192, c_data_type="uint16_t")
        assert r.c_data_type == "uint16_t"

    def test_comment_auto_generated(self):
        r = MemoryRegion("ram", size_in_bytes=256)
        assert "ram" in r.comment
        assert "256" in r.comment

    def test_comment_custom(self):
        r = MemoryRegion("ram", size_in_bytes=256, comment="Work RAM")
        assert r.comment == "Work RAM"

    def test_repr(self):
        r = MemoryRegion("ram", size_in_bytes=256)
        s = repr(r)
        assert "ram" in s
        assert "256" in s


# ===================================================================
# MemoryBank
# ===================================================================

class TestMemoryBank:

    def test_basic_creation(self):
        r = MemoryRegion("rom", size_in_bytes=0)
        b = MemoryBank("rom_bank1", region=r, bank_size=0x4000,
                        max_banks=256, default_bank=1)
        assert b.name == "rom_bank1"
        assert b.region is r
        assert b.bank_size == 0x4000
        assert b.max_banks == 256
        assert b.default_bank == 1

    def test_defaults(self):
        r = MemoryRegion("rom", size_in_bytes=0)
        b = MemoryBank("bank", region=r, bank_size=0x2000)
        assert b.max_banks == 256
        assert b.default_bank == 0

    def test_repr(self):
        r = MemoryRegion("rom", size_in_bytes=0)
        b = MemoryBank("rom_b", region=r, bank_size=0x4000)
        s = repr(b)
        assert "rom_b" in s
        assert "rom" in s


# ===================================================================
# Handler
# ===================================================================

class TestHandler:

    def test_python_handler(self):
        def my_func():
            pass
        h = Handler(handler_type=HandlerType.Python, func=my_func)
        assert h.handler_type == HandlerType.Python
        assert h.func is my_func
        assert h.code is None

    def test_raw_c_handler(self):
        h = Handler(handler_type=HandlerType.RawC, code="return 0xFF;")
        assert h.handler_type == HandlerType.RawC
        assert h.code == "return 0xFF;"
        assert h.func is None

    def test_address_range(self):
        h = Handler(handler_type=HandlerType.RawC, code="return;",
                     addr_start=0x2000, addr_end=0x3FFF)
        assert h.addr_start == 0x2000
        assert h.addr_end == 0x3FFF


# ===================================================================
# MemoryController
# ===================================================================

class TestMemoryController:

    def test_basic_creation(self):
        ctrl = MemoryController("mapper")
        assert ctrl.name == "mapper"
        assert ctrl.controls == []
        assert ctrl.state_fields == []
        assert ctrl.write_handlers == []
        assert ctrl.bank_resolvers == {}
        assert ctrl.access_guards == {}

    def test_add_state(self):
        ctrl = MemoryController("mapper")
        ctrl.add_state("rom_bank", "uint8_t", "1", "Current ROM bank")
        assert len(ctrl.state_fields) == 1
        name, ctype, default, comment = ctrl.state_fields[0]
        assert name == "rom_bank"
        assert ctype == "uint8_t"
        assert default == "1"

    def test_on_write_decorator(self):
        ctrl = MemoryController("mapper")

        @ctrl.on_write(0x2000, 0x3FFF)
        def handler(ctrl, val, addr):
            pass

        assert len(ctrl.write_handlers) == 1
        h = ctrl.write_handlers[0]
        assert h.handler_type == HandlerType.Python
        assert h.addr_start == 0x2000
        assert h.addr_end == 0x3FFF
        assert h.func is handler

    def test_add_write_handler_raw(self):
        ctrl = MemoryController("mapper")
        ctrl.add_write_handler_raw(0x2000, 0x3FFF, "sys->cpu.bank = val;")
        assert len(ctrl.write_handlers) == 1
        h = ctrl.write_handlers[0]
        assert h.handler_type == HandlerType.RawC

    def test_bank_resolver_decorator(self):
        r = MemoryRegion("rom", size_in_bytes=0)
        bank = MemoryBank("rom_b", region=r, bank_size=0x4000)
        ctrl = MemoryController("mapper", controls=[bank])

        @ctrl.bank_resolver(bank)
        def resolve(ctrl, addr):
            return ctrl.rom_bank

        assert "rom_b" in ctrl.bank_resolvers
        h = ctrl.bank_resolvers["rom_b"]
        assert h.func is resolve

    def test_set_bank_resolver_raw(self):
        r = MemoryRegion("rom", size_in_bytes=0)
        bank = MemoryBank("rom_b", region=r, bank_size=0x4000)
        ctrl = MemoryController("mapper", controls=[bank])
        ctrl.set_bank_resolver_raw(bank, "return sys->cpu.rom_bank;")
        assert ctrl.bank_resolvers["rom_b"].handler_type == HandlerType.RawC

    def test_read_guard_decorator(self):
        r = MemoryRegion("sram", size_in_bytes=8192)
        bank = MemoryBank("sram_b", region=r, bank_size=8192)
        ctrl = MemoryController("mapper", controls=[bank])

        @ctrl.read_guard(bank)
        def guard(ctrl):
            return ctrl.sram_enabled

        assert ("sram_b", "read") in ctrl.access_guards

    def test_write_guard_decorator(self):
        r = MemoryRegion("sram", size_in_bytes=8192)
        bank = MemoryBank("sram_b", region=r, bank_size=8192)
        ctrl = MemoryController("mapper", controls=[bank])

        @ctrl.write_guard(bank)
        def guard(ctrl):
            return ctrl.sram_enabled

        assert ("sram_b", "write") in ctrl.access_guards

    def test_controls_list(self):
        r = MemoryRegion("rom", size_in_bytes=0)
        b1 = MemoryBank("b1", region=r, bank_size=0x4000)
        b2 = MemoryBank("b2", region=r, bank_size=0x4000)
        ctrl = MemoryController("mapper", controls=[b1, b2])
        assert len(ctrl.controls) == 2


# ===================================================================
# BusMapping
# ===================================================================

class TestBusMapping:

    def test_basic_mapping(self):
        r = MemoryRegion("ram", size_in_bytes=256)
        m = BusMapping(addr_start=0x0000, addr_end=0x00FF, region=r)
        assert m.addr_start == 0x0000
        assert m.addr_end == 0x00FF
        assert m.region is r
        assert m.offset == 0
        assert m.fixed is False
        assert m.write_only is False

    def test_fixed_mapping(self):
        r = MemoryRegion("rom", size_in_bytes=0)
        m = BusMapping(addr_start=0x0000, addr_end=0x3FFF,
                       region=r, fixed=True)
        assert m.fixed is True

    def test_access_cycles(self):
        r = MemoryRegion("rom", size_in_bytes=0)
        m = BusMapping(addr_start=0x0000, addr_end=0x3FFF,
                       region=r, access_cycles=8)
        assert m.access_cycles == 8

    def test_write_side_effect(self):
        r = MemoryRegion("vram", size_in_bytes=8192)
        m = BusMapping(addr_start=0x8000, addr_end=0x9FFF,
                       region=r,
                       on_write_side_effect="sys->ppu.vram_dirty = true;")
        assert m.on_write_side_effect == "sys->ppu.vram_dirty = true;"


# ===================================================================
# BusOverlay
# ===================================================================

class TestBusOverlay:

    def test_basic_overlay(self):
        r = MemoryRegion("bios", size_in_bytes=256)
        ov = BusOverlay(addr_start=0x0000, addr_end=0x00FF, region=r)
        assert ov.addr_start == 0x0000
        assert ov.addr_end == 0x00FF
        assert ov.region is r

    def test_auto_state_field(self):
        r = MemoryRegion("bios", size_in_bytes=256)
        ov = BusOverlay(addr_start=0x0000, addr_end=0x00FF, region=r)
        assert ov.state_field == "bios_overlay_enabled"

    def test_custom_state_field(self):
        r = MemoryRegion("bios", size_in_bytes=256)
        ov = BusOverlay(addr_start=0x0000, addr_end=0x00FF, region=r,
                        state_field="boot_rom_active")
        assert ov.state_field == "boot_rom_active"

    def test_disable_on_write(self):
        r = MemoryRegion("bios", size_in_bytes=256)
        ov = BusOverlay(addr_start=0x0000, addr_end=0x00FF, region=r,
                        disable_on_write=(0xFF50, ""))
        assert ov.disable_on_write == (0xFF50, "")


# ===================================================================
# MemoryBus
# ===================================================================

class TestMemoryBus:

    def test_basic_creation(self):
        bus = MemoryBus("main", address_bits=16)
        assert bus.name == "main"
        assert bus.address_bits == 16
        assert bus.address_space == 0x10000
        assert bus.mappings == []
        assert bus.write_mappings == []
        assert bus.overlays == []

    def test_addr_type_16bit(self):
        bus = MemoryBus("main", address_bits=16)
        assert bus.addr_type == "uint16_t"

    def test_addr_type_24bit(self):
        bus = MemoryBus("main", address_bits=24)
        assert bus.addr_type == "uint32_t"

    def test_addr_type_8bit(self):
        bus = MemoryBus("zp", address_bits=8)
        assert bus.addr_type == "uint16_t"

    def test_map_region(self):
        bus = MemoryBus("main", address_bits=16)
        r = MemoryRegion("ram", size_in_bytes=256)
        bus.map(0x0000, 0x00FF, region=r)
        assert len(bus.mappings) == 1
        m = bus.mappings[0]
        assert m.addr_start == 0x0000
        assert m.addr_end == 0x00FF
        assert m.region is r

    def test_map_with_bank(self):
        bus = MemoryBus("main", address_bits=16)
        r = MemoryRegion("rom", size_in_bytes=0)
        b = MemoryBank("rom_b", region=r, bank_size=0x4000)
        c = MemoryController("mapper", controls=[b])
        bus.map(0x4000, 0x7FFF, bank=b, controller=c)
        assert len(bus.mappings) == 1
        m = bus.mappings[0]
        assert m.bank is b
        assert m.controller is c

    def test_map_writes(self):
        bus = MemoryBus("main", address_bits=16)
        c = MemoryController("mapper")
        bus.map_writes(0x0000, 0x7FFF, controller=c)
        assert len(bus.write_mappings) == 1
        assert bus.write_mappings[0].write_only is True

    def test_overlay(self):
        bus = MemoryBus("main", address_bits=16)
        r = MemoryRegion("bios", size_in_bytes=256)
        bus.overlay(0x0000, 0x00FF, r, disable_on_write=(0xFF50, ""))
        assert len(bus.overlays) == 1
        ov = bus.overlays[0]
        assert ov.region is r
        assert ov.disable_on_write == (0xFF50, "")

    def test_set_fallback(self):
        bus = MemoryBus("main", address_bits=16)
        bus.set_fallback(read=0xFF, write="/* ignored */")
        assert bus.fallback_read == 0xFF
        assert bus.fallback_write == "/* ignored */"

    def test_default_fallback(self):
        bus = MemoryBus("main", address_bits=16)
        assert bus.fallback_read == 0xFF
        assert bus.fallback_write is None

    def test_multiple_mappings(self):
        bus = MemoryBus("main", address_bits=16)
        r1 = MemoryRegion("ram", size_in_bytes=256)
        r2 = MemoryRegion("rom", size_in_bytes=32768)
        bus.map(0x0000, 0x00FF, region=r1)
        bus.map(0x8000, 0xFFFF, region=r2)
        assert len(bus.mappings) == 2

    def test_repr(self):
        bus = MemoryBus("main", address_bits=16)
        s = repr(bus)
        assert "main" in s
        assert "16" in s
