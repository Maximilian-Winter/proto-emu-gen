# Workflow and Examples

This guide shows how to approach a new emulator project with `proto-gen` and where to look in the repository for working patterns.

## The normal workflow

Most projects follow this order:

1. Define clocks.
2. Define memory regions.
3. Define one or more CPU cores.
4. Define peripheral chips and their register blocks.
5. Define buses, controllers, banking, signals, and ports.
6. Assemble the board.
7. Generate C.
8. Add a handwritten `main()` or generate an SDL host.

## Step 1: Start with the CPU core

Begin by modeling the machine's instruction set with `CPUDefinition`.

Typical tasks:

- add general-purpose registers,
- define register pairs if the ISA has them,
- define the flag register layout,
- add a few opcodes first,
- use raw C for unusual instructions if needed.

Good first milestone:

- enough opcodes to load immediates,
- move values between registers,
- read and write memory,
- jump,
- halt.

That is exactly how the smaller examples are structured.

## Step 2: Add memory

Define storage with `MemoryRegion`.

Common patterns:

- static RAM or VRAM with a fixed size,
- dynamic cartridge ROM with `size_in_bytes=0`,
- banked windows using `MemoryBank`,
- mappers using `MemoryController`.

Then route everything through a `MemoryBus`.

Ask yourself:

- which ranges are fixed,
- which are banked,
- which are register-mapped,
- which writes should be intercepted,
- what fallback value should unmapped reads return.

## Step 3: Add peripherals as chips

Peripheral chips usually start with:

- state fields,
- one or more `RegisterBlock` instances,
- an optional tick handler.

Examples:

- timer registers and overflow logic,
- PPU control/status and framebuffer memory,
- joypad state and read multiplexing,
- APU channel registers and sample generation.

## Step 4: Connect chips together

Use:

- `SignalLine` for interrupts and events,
- `Port` for mailbox-style communication,
- shared bus mappings for memory-visible peripherals.

This is where the board becomes a system instead of a CPU core with RAM.

## Step 5: Generate C early and often

Do not wait until the entire system is modeled before generating code.

A productive rhythm is:

1. add a small slice,
2. generate C,
3. inspect the output,
4. compile,
5. run a focused test ROM or micro-program.

That is how the repository examples are structured.

## Example progression in this repository

### 1. Fibonacci

File:

- [`examples/fibonacci.py`](/H:/Dev42/proto-emu-gen/examples/fibonacci.py)

What it teaches:

- minimal CPU definition,
- simple memory map,
- register block used as an output device,
- generated C plus a handwritten `main()`.

Use it when:

- you want the smallest complete end-to-end reference.

### 2. TinyBoy

File:

- [`examples/tinyboy.py`](/H:/Dev42/proto-emu-gen/examples/tinyboy.py)

What it teaches:

- banked ROM,
- memory controller state and write handlers,
- bank resolvers,
- timer peripheral with tick handler,
- interrupt-style signaling,
- a more realistic single-CPU console architecture.

Use it when:

- you are building a cartridge-based 8-bit machine.

### 3. TinySuper

File:

- [`examples/tinysuper.py`](/H:/Dev42/proto-emu-gen/examples/tinysuper.py)

What it teaches:

- multiple CPUs,
- separate buses,
- derived clocks,
- latched ports between chips,
- catch-up scheduling across chips.

Use it when:

- your machine has a main CPU plus co-processor or sound CPU.

### 4. Cycle-accurate example

File:

- [`examples/cycle_accurate.py`](/H:/Dev42/proto-emu-gen/examples/cycle_accurate.py)

What it teaches:

- bus `access_cycles`,
- `internal_op()` timing,
- synchronized peripheral ticking during execution,
- DMA-aware scheduling hooks.

Use it when:

- timing behavior matters more than simple per-opcode cycle totals.

### 5. Game Boy

Files:

- [`examples/game_boy/game_boy.py`](/H:/Dev42/proto-emu-gen/examples/game_boy/game_boy.py)
- [`examples/game_boy/game_boy_host.py`](/H:/Dev42/proto-emu-gen/examples/game_boy/game_boy_host.py)

What they teach:

- large-scale board composition,
- heavy use of transpiled register handlers,
- cartridge mapper logic,
- PPU/APU/timer/joypad chips,
- SDL host generation and ROM loading.

Use them when:

- you want the most complete reference for real project structure.

## Suggested project milestones

If you are starting a new machine, this order usually works well:

1. Bootable CPU plus RAM and ROM.
2. Enough opcodes to run a micro-test program.
3. Memory-mapped I/O skeleton.
4. Interrupt wiring.
5. Banking or DMA if the target machine needs it.
6. Video or audio peripherals.
7. Host integration.

Keep each milestone independently runnable if possible.

## Choosing between transpiled Python and raw C

Prefer transpiled Python when:

- the logic is straight-line and register-centric,
- you want readability at the system-model level,
- you want opcode families or shared helper patterns.

Prefer raw C when:

- the transpiler subset gets in your way,
- you need precise control over emitted code,
- you are copying known-good logic from an existing emulator,
- the handler is awkward to express in the supported subset.

Most successful uses of this framework will likely mix both styles.

## Suggested development loop

For a board-only project:

```bash
python examples/fibonacci.py
gcc -O2 -o fibonacci examples/fibonacci.c
./fibonacci
```

For test-driven development:

```bash
pytest
```

For a host-enabled project:

1. generate the board C or SDL host C,
2. compile with your SDL3 toolchain,
3. run against a test ROM,
4. inspect both generated C and runtime behavior.

## How to read generated C

The generated file is long but regular. A good reading order is:

1. board and chip structs,
2. bus read/write functions,
3. register block dispatchers,
4. controller resolvers,
5. CPU step function,
6. board init and board step.

That mirrors the code generator organization in [`src/proto/codegen.py`](/H:/Dev42/proto-emu-gen/src/proto/codegen.py).

## Common pitfalls

- Forgetting to assign a bus to a CPU chip with `chip.set_bus(...)`.
- Forgetting to add a master clock to the board.
- Using Python features outside the transpiler subset.
- Expecting dynamic Python behavior at runtime instead of generated C behavior.
- Defining handler logic that would be clearer as raw C.
- Assuming all data-model features are already wired into code generation without checking examples or tests.

## Best references in the repo

For modeling patterns:

- [`examples`](/H:/Dev42/proto-emu-gen/examples)

For exact behavior:

- [`tests`](/H:/Dev42/proto-emu-gen/tests)

For generator implementation details:

- [`src/proto/codegen.py`](/H:/Dev42/proto-emu-gen/src/proto/codegen.py)
- [`src/proto/transpiler.py`](/H:/Dev42/proto-emu-gen/src/proto/transpiler.py)
