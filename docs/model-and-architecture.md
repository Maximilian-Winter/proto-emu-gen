# Model and Architecture

This document explains how the framework is structured and how the main objects fit together.

## Core idea

You describe a machine in Python as a graph of objects. The generator walks that model and emits one C program containing:

- chip state structs,
- a board struct,
- memory dispatch code,
- register and controller helpers,
- opcode dispatch loops,
- optional synchronization, DMA, and interrupt helpers,
- optional SDL host code.

The runtime model is declarative. The emitted C is imperative.

## Object graph

At a high level:

- `Clock` describes timing sources and derived clocks.
- `CPUDefinition` describes an ISA.
- `Chip` packages CPU or peripheral state and behavior.
- `MemoryRegion` describes storage.
- `MemoryBank` describes a switchable window into storage.
- `MemoryController` describes mapper logic and access policies.
- `MemoryBus` describes an address space and dispatch rules.
- `RegisterBlock` describes memory-mapped device registers.
- `SignalLine` describes interrupt/reset/custom signaling between chips.
- `Port` describes latched communication channels between chips.
- `DMAChannel` describes bus-master style transfers.
- `Board` assembles all of the above into one system.

## Clocks

`Clock` is the root of timing relationships.

Use it when:

- the whole board shares one master clock,
- CPUs run at different divisors,
- peripherals need catch-up or synchronized ticking,
- cycle-accurate mode needs master-relative scheduling.

Key behaviors:

- `derive()` creates child clocks,
- `master_divider` lets the generator scale between derived clocks,
- `cycles_per()` is useful at modeling time for reasoning about ratios.

The multi-CPU example in [`examples/tinysuper.py`](../examples/tinysuper.py) is a good reference.

## CPUDefinition

`CPUDefinition` is the instruction-set model. It is not tied to any particular board until attached to a `Chip`.

It holds:

- named registers,
- optional register pairs,
- optional flag register layout,
- builtin CPU state such as `PC`, `SP`, `cycle_count`, and `halted`,
- opcode table entries,
- optional prefix opcode tables,
- optional interrupt vectors.

Instruction bodies can be authored in two ways:

- Python handlers via decorators like `@cpu.opcode(...)`
- raw C snippets via `add_opcode_raw(...)`

Opcode families let you define many opcodes from one Python template, which is especially useful for bit-manipulation families and register-to-register moves.

## Chips

`Chip` is the universal building block for active components.

A chip can represent:

- a CPU package,
- a timer,
- a PPU or APU,
- a mapper or controller-backed component,
- a DMA engine,
- any other stateful device that should become a C struct in the generated output.

Chips may contain:

- CPU cores,
- extra state fields,
- internal memory regions,
- memory controllers,
- register blocks,
- DMA channels,
- helper functions,
- tick handlers,
- step preambles.

A CPU chip should also be connected to its owning bus through `chip.set_bus(bus)`.

## Memory model

The memory API splits concerns intentionally.

### MemoryRegion

`MemoryRegion` represents actual storage:

- static arrays such as RAM, VRAM, HRAM, OAM,
- dynamic allocations such as cartridge ROM or cartridge RAM,
- alternate element types when you need something other than `uint8_t`.

If `size_in_bytes == 0`, the region is treated as dynamic and generated as a pointer plus size field.

### MemoryBank

`MemoryBank` represents a banked window onto a region.

Use it when:

- one address range selects different pages of a larger ROM or RAM,
- part of the address map is fixed while another part is switchable,
- bank numbers come from mapper state.

### MemoryController

`MemoryController` contains the logic behind banking and guarded access.

It supports:

- controller state fields,
- write handlers over address ranges,
- bank resolvers for `MemoryBank` objects,
- read/write guards.

This is the main place to model cartridge mappers and similar memory-management devices.

### MemoryBus

`MemoryBus` is the address decoder and dispatcher.

It stores:

- normal mappings,
- write-only mappings,
- overlays,
- fallback read/write behavior,
- optional bus masters for arbitration.

Mappings can target:

- `MemoryRegion`,
- `MemoryBank` plus `MemoryController`,
- `RegisterBlock`,
- other handler-backed entities.

Important mapping features already present in the codebase:

- address widths above 16 bits,
- per-mapping `access_cycles`,
- write-side effects,
- overlays that can be disabled by writes,
- bus-master metadata for DMA-aware scheduling.

## Register blocks

`RegisterBlock` models memory-mapped I/O.

Each register entry can define:

- a symbolic name,
- default value,
- read-only or write-only behavior,
- a write mask,
- a Python or raw C read handler,
- a Python or raw C write handler.

Use register blocks for:

- timer control registers,
- PPU status registers,
- APU register files,
- joypad inputs,
- simple output devices.

The generated bus code calls into block-specific read/write helpers.

## Signals

`SignalLine` models point-to-point or multi-source signaling between chips.

Typical uses:

- IRQ or NMI lines,
- reset lines,
- custom event signaling between peripherals and CPUs.

Each signal can have:

- a type,
- an edge mode,
- active-low semantics,
- sources and sinks,
- optional assert handlers per sink chip.

This is the cleanest way to keep interrupt source logic outside the CPU core itself.

## Ports

`Port` models a latched communication channel between two chips.

This is useful for console-style chip-to-chip mailboxes, command ports, or shared I/O windows.

Supported latching modes:

- `Independent`
- `Shared`

The dual-CPU example uses this to model a simple SNES-like communication path.

## DMA

`DMAChannel` models generated transfer helpers and per-channel state.

It can express:

- one-shot transfers,
- HBlank-style transfers,
- cycle-oriented transfers,
- multi-channel state arrays,
- Python or raw C transfer bodies.

In cycle-accurate boards with bus masters, DMA can be integrated into board step scheduling.

## Board

`Board` is the full machine.

It owns:

- a master clock,
- chips,
- buses,
- ports,
- signals,
- external function declarations,
- the `cycle_accurate` mode flag.

`Board.validate()` already checks several structural errors:

- missing master clock,
- no chips,
- no buses,
- no CPU chip,
- chips without clocks,
- CPU chips without buses.

## Generation pipeline

`BoardCodeGenerator(board).generate()` emits:

1. C headers and extern declarations
2. per-chip structs
3. the board struct
4. forward declarations
5. flag and register-pair helpers
6. sync helpers for cycle-accurate boards
7. bus read/write dispatch
8. convenience memory helpers
9. signal functions
10. register block dispatchers
11. controller resolvers and guards
12. chip helper functions
13. DMA helpers
14. interrupt checking helpers
15. CPU step functions
16. peripheral tick functions
17. board initialization
18. board stepping logic

The output is intentionally monolithic so it is easy to inspect and compile.

## Normal mode vs cycle-accurate mode

`Board(cycle_accurate=False)`:

- each opcode contributes a fixed `cycles` count,
- peripherals are ticked after the CPU step using catch-up logic.

`Board(cycle_accurate=True)`:

- timing comes from bus accesses and `internal_op()` calls,
- synchronization happens during execution,
- board step drives the primary CPU while sync hooks tick the rest,
- DMA arbitration can short-circuit CPU stepping.

## External functions

`Board.add_extern_func(...)` declares external C hooks that generated code can call.

This is how large systems connect generated cores to host functionality such as:

- framebuffer presentation,
- audio streaming,
- input polling,
- logging or debugging hooks.

## Raw C escape hatches

A practical pattern in this framework is:

- use transpiled Python for most logic,
- drop to raw C only for edge cases or performance-sensitive special handling.

That hybrid approach is visible throughout the examples and is part of the design, not a workaround.

