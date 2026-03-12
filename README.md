# proto-gen

`proto-gen` is a declarative Python framework for describing computer systems and generating emulator cores in C.

The core idea is:

1. Model a machine in Python with clocks, chips, buses, memory maps, I/O registers, signals, DMA, and CPUs.
2. Describe CPU instructions and device behavior as small Python functions.
3. Walk those Python functions as ASTs and transpile them into C.
4. Emit a single C program that can be compiled as a fast AST-walking interpreter and, optionally, wrapped in an SDL3 host.

This repository already includes examples ranging from a tiny educational CPU to a Game Boy-scale system definition.

## What this project is for

This framework sits between handwritten emulators and hardware DSLs:

- Higher level than writing a full emulator directly in C.
- More concrete and software-oriented than HDL.
- Focused on emulator generation, not hardware synthesis.

It is a good fit when you want to:

- prototype a new emulator architecture quickly,
- keep system structure declarative and inspectable,
- define opcodes in Python instead of manually duplicating C switch cases,
- generate portable C that can be compiled with `gcc` or similar toolchains,
- experiment with single-CPU, multi-CPU, banked-memory, or cycle-aware systems.

## Current capabilities

Based on the code and tests in this repository, the framework currently supports:

- declarative system modeling with `Board`, `Chip`, `Clock`, `MemoryBus`, `MemoryRegion`, `MemoryBank`, `MemoryController`, `RegisterBlock`, `SignalLine`, `Port`, and `DMAChannel`,
- CPU definitions with registers, register pairs, flags, opcode tables, opcode families, prefix tables, and interrupt vectors,
- Python-to-C transpilation for a focused subset of Python expressions and statements,
- raw C escape hatches anywhere the Python subset is too restrictive,
- generated C interpreters with per-opcode dispatch,
- single-CPU and multi-CPU boards,
- memory banking, guarded access, write intercepts, and overlays,
- cycle-counted and cycle-accurate generation modes,
- DMA hooks and interrupt dispatch generation,
- an SDL3 host generator for windowing, rendering, audio, input, menus, and config handling.

## Repository tour

- [`src/proto`](/H:/Dev42/proto-emu-gen/src/proto) - framework runtime and code generators
- [`examples/fibonacci.py`](/H:/Dev42/proto-emu-gen/examples/fibonacci.py) - smallest end-to-end example
- [`examples/tinyboy.py`](/H:/Dev42/proto-emu-gen/examples/tinyboy.py) - single CPU, banked ROM, timer, signals
- [`examples/tinysuper.py`](/H:/Dev42/proto-emu-gen/examples/tinysuper.py) - dual CPU, separate buses, ports
- [`examples/cycle_accurate.py`](/H:/Dev42/proto-emu-gen/examples/cycle_accurate.py) - access-timed generation
- [`examples/game_boy/game_boy.py`](/H:/Dev42/proto-emu-gen/examples/game_boy/game_boy.py) - large real-world system definition
- [`examples/game_boy/game_boy_host.py`](/H:/Dev42/proto-emu-gen/examples/game_boy/game_boy_host.py) - SDL3 host generation
- [`tests`](/H:/Dev42/proto-emu-gen/tests) - feature coverage and behavior reference

## Installation

The package metadata names the project `proto-gen`, while the import package is `proto`.

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e .[dev]
```

To run tests:

```bash
pytest
```

Some integration tests require `gcc` in `PATH`.

## Mental model

Think in layers:

- `CPUDefinition` describes the ISA and instruction bodies.
- `Chip` packages a CPU core or peripheral state and behavior.
- `MemoryBus` and related memory classes describe the address space.
- `Board` assembles chips, buses, clocks, signals, and ports into a whole machine.
- `BoardCodeGenerator` emits a complete C implementation.
- `SDLHost` and `HostCodeGenerator` optionally wrap the generated board with an SDL frontend.

## Quickstart

The smallest useful flow is:

```python
from proto import (
    Clock, Chip, Board, CPUDefinition,
    MemoryRegion, MemoryBus, MemoryAccessLevel,
    BoardCodeGenerator,
)

master = Clock("master", 1_000_000)

ram = MemoryRegion("ram", 256, MemoryAccessLevel.ReadWrite)
rom = MemoryRegion("rom", 32768, MemoryAccessLevel.ReadOnly)

cpu = CPUDefinition("tiny8", data_width=8, address_width=16)
cpu.add_register("A", 8)

@cpu.opcode(0x00, "NOP", cycles=1)
def nop(cpu):
    pass

@cpu.opcode(0x01, "LDA #imm8", cycles=2)
def lda_imm8(cpu):
    cpu.A = read_imm8()

@cpu.opcode(0x0F, "HALT", cycles=1)
def halt(cpu):
    cpu.halted = 1

cpu_chip = Chip("cpu", clock=master)
cpu_chip.set_cpu_core(cpu)
cpu_chip.add_internal_memory(ram)
cpu_chip.add_internal_memory(rom)

bus = MemoryBus("main", address_bits=16)
bus.map(0x0000, 0x00FF, region=ram)
bus.map(0x8000, 0xFFFF, region=rom)
bus.set_fallback(read=0xFF)
cpu_chip.set_bus(bus)

board = Board("TinyDemo", comment="Minimal generated emulator")
board.set_master_clock(master)
board.add_chip(cpu_chip)
board.add_bus(bus)

c_code = BoardCodeGenerator(board).generate()
with open("tinydemo.c", "w", encoding="utf-8") as f:
    f.write(c_code)
```

Then compile the generated C:

```bash
gcc -O2 -o tinydemo tinydemo.c
```

For a full runnable example with a generated `main()`, start with [`examples/fibonacci.py`](/H:/Dev42/proto-emu-gen/examples/fibonacci.py).

## How Python becomes C

Instruction and device handlers are not executed by the emulator at runtime. Instead, the framework:

1. reads the Python function source with `inspect`,
2. parses it into an AST,
3. rewrites known constructs into C expressions/statements,
4. injects the resulting code into generated helper functions, opcode cases, register handlers, tick handlers, and so on.

That means your Python handler bodies act like a small DSL.

Examples of supported conveniences:

- `cpu.A = read_imm8()`
- `cpu.F.Z = cpu.A == 0`
- `cpu.HL = read_imm16()`
- `mem_write(cpu.HL, cpu.A)`
- `signal_assert("timer_irq")`
- typed locals such as `x: uint8 = 0`
- array declarations such as `buf: array[uint8, 160] = None`
- opcode families with variant substitution such as `cpu.reg = cpu.reg | 1`

More detail is in [`docs/transpiler-subset.md`](/H:/Dev42/proto-emu-gen/docs/transpiler-subset.md).

## Recommended learning path

Read the examples in this order:

1. [`examples/fibonacci.py`](/H:/Dev42/proto-emu-gen/examples/fibonacci.py)
2. [`examples/tinyboy.py`](/H:/Dev42/proto-emu-gen/examples/tinyboy.py)
3. [`examples/tinysuper.py`](/H:/Dev42/proto-emu-gen/examples/tinysuper.py)
4. [`examples/cycle_accurate.py`](/H:/Dev42/proto-emu-gen/examples/cycle_accurate.py)
5. [`examples/game_boy/game_boy.py`](/H:/Dev42/proto-emu-gen/examples/game_boy/game_boy.py)
6. [`examples/game_boy/game_boy_host.py`](/H:/Dev42/proto-emu-gen/examples/game_boy/game_boy_host.py)

That progression mirrors the framework itself:

- tiny single-core board,
- memory controllers and signals,
- multi-CPU scheduling and ports,
- timed bus accesses and synchronization,
- full-system modeling,
- generated desktop host.

## Generation workflow

Typical project flow:

1. Define clocks and memory regions.
2. Define one or more CPU cores with `CPUDefinition`.
3. Attach CPU cores and peripherals to `Chip` objects.
4. Describe the bus topology and register maps.
5. Build a `Board`.
6. Generate C with `BoardCodeGenerator`.
7. Optionally wrap it with `SDLHost` and `HostCodeGenerator`.
8. Compile the emitted C with your platform toolchain.

See [`docs/workflow-and-examples.md`](/H:/Dev42/proto-emu-gen/docs/workflow-and-examples.md) for a more detailed walk-through.

## Raw C escape hatches

You do not need to force everything through the transpiler. The framework also supports raw C injection for:

- opcodes via `add_opcode_raw`,
- register block read/write handlers,
- memory controller write handlers and bank resolvers,
- chip helpers,
- DMA transfers,
- tick handlers,
- step preambles,
- SDL host post-init and ROM loading code.

This is useful when:

- a construct is not supported by the AST transpiler,
- you want exact control over emitted C,
- you are incrementally porting an existing emulator into the declarative model.

## Cycle counting vs cycle-accurate mode

There are two timing styles:

- Normal mode: opcode entries contribute `cycles` directly to `cycle_count`, and board step logic catches peripherals up afterward.
- Cycle-accurate mode: bus accesses and `internal_op()` calls account for timing, and synchronization happens during execution rather than after the opcode finishes.

If you care about memory wait states, peripheral synchronization on every access, or DMA arbitration, read [`examples/cycle_accurate.py`](/H:/Dev42/proto-emu-gen/examples/cycle_accurate.py) alongside [`docs/model-and-architecture.md`](/H:/Dev42/proto-emu-gen/docs/model-and-architecture.md).

## SDL host generation

The host layer lets you keep emulator logic in the generated board while declaring desktop concerns separately:

- window size and title,
- palette conversion,
- audio stream setup,
- input mapping,
- ROM loading,
- menu bar and config,
- render/audio/input hook binding.

See [`docs/host-layer.md`](/H:/Dev42/proto-emu-gen/docs/host-layer.md).

## Limitations and caveats

This project is already useful, but it is still early-stage and opinionated.

- The transpiler intentionally supports only a subset of Python.
- Handler functions should stay simple and side-effect oriented.
- When you need something outside the subset, use raw C hooks.
- Generated output is monolithic C rather than a multi-file project structure.
- The best source of truth for supported patterns today is the combination of [`tests/test_transpiler.py`](/H:/Dev42/proto-emu-gen/tests/test_transpiler.py) and the example systems.
- The data model exposes `Chip.set_init()`, but board initialization is currently driven by field defaults plus generated `main()` or host setup code; chip init handlers are not presently wired into emitted board init code.

## Documentation

- [`docs/model-and-architecture.md`](/H:/Dev42/proto-emu-gen/docs/model-and-architecture.md)
- [`docs/transpiler-subset.md`](/H:/Dev42/proto-emu-gen/docs/transpiler-subset.md)
- [`docs/workflow-and-examples.md`](/H:/Dev42/proto-emu-gen/docs/workflow-and-examples.md)
- [`docs/host-layer.md`](/H:/Dev42/proto-emu-gen/docs/host-layer.md)

## Status

The package metadata marks the project as alpha, which matches the repository well: the foundation is already broad, the examples are ambitious, and the tests cover a lot of behavior, but the API and supported subset are still evolving.
