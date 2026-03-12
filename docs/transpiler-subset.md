# Transpiler Subset

`proto-gen` does not execute opcode and handler Python at runtime. It transpiles selected Python function bodies into C using AST walking.

This document describes the subset that is clearly supported by the current implementation and tests.

## Design goal

The transpiler is meant to cover the kinds of code emulator authors write constantly:

- register moves,
- flag updates,
- memory reads and writes,
- basic arithmetic and bitwise logic,
- branch logic,
- small loops,
- helper calls,
- simple typed temporaries.

It is not a general Python compiler.

## Where transpilation is used

Python handler bodies are transpiled for:

- CPU opcodes,
- prefix opcodes,
- opcode families,
- register block reads,
- register block writes,
- memory controller write handlers,
- memory controller bank resolvers,
- memory controller access guards,
- signal assert handlers,
- chip helpers,
- DMA transfer handlers,
- chip tick handlers,
- step preambles.

## Supported statements

The following statement forms are directly handled by the current transpiler:

- `pass`
- assignment
- annotated assignment
- augmented assignment such as `x += 1`
- `return`
- bare expression calls such as `mem_write(...)`
- `if` / `elif` / `else`
- `while`
- `for ... in range(...)`
- `break`
- `continue`

Docstrings at the top of a handler body are ignored.

## Supported expressions

The current implementation supports:

- integer, boolean, and string constants
- local names
- attribute access
- subscript access
- binary arithmetic
- unary operators such as `not`, `~`, unary `-`
- boolean `and` / `or`
- comparisons
- function calls
- ternary expressions (`a if cond else b`)

### Binary operators

Supported operators map directly to C:

- `+`
- `-`
- `*`
- `/`
- `%`
- `//`
- `&`
- `|`
- `^`
- `<<`
- `>>`

### Comparisons

Supported comparison operators:

- `==`
- `!=`
- `<`
- `>`
- `<=`
- `>=`

## Special emulator-aware rewrites

The transpiler is aware of several emulator-specific idioms.

### Self parameter mapping

The first argument is usually a chip-like object such as `cpu`, `chip`, or `ctrl`.

Example:

```python
def lda(cpu):
    cpu.A = read_imm8()
```

becomes roughly:

```c
sys->cpu.A = read_imm8(sys);
```

### Cross-component access

Named components on the board can be referenced directly.

Example:

```python
def fn(cpu):
    ppu.scanline = 0
```

becomes:

```c
sys->ppu.scanline = 0;
```

### Flag access

If a CPU defines flags with `set_flags("F", {...})`, then:

- `cpu.F.Z` reads become `cpu_get_Z(sys)`
- `cpu.F.Z = expr` writes become `cpu_set_Z(sys, expr)`

This is used throughout opcode bodies.

### Register pairs

If register pairs are defined, then:

- `cpu.HL` reads become `cpu_get_HL(sys)`
- `cpu.HL = expr` writes become `cpu_set_HL(sys, expr)`

### System helper calls

Common emulator helpers automatically receive `sys`:

- `mem_read`
- `mem_write`
- `mem_read16`
- `read_imm8`
- `read_imm16`
- `push8`
- `push16`
- `pop8`
- `pop16`
- `internal_op`

In multi-CPU systems, these can also be remapped to chip-specific helper names.

### signal_assert

This:

```python
signal_assert("timer_irq")
```

becomes:

```c
signal_assert_timer_irq(sys)
```

### Variant substitution in opcode families

Opcode-family parameters are substituted into generated code.

Example:

```python
@cpu.opcode_family("LD {},{}", [(0x78, "A", "B")], cycles=4)
def ld_r_r(cpu, dst, src):
    cpu.dst = cpu.src
```

produces code equivalent to:

```c
sys->cpu.A = sys->cpu.B;
```

This is one of the most useful features for dense ISAs.

## Typed locals and casts

The transpiler recognizes symbolic type names rather than real Python runtime types.

### Annotations

Supported annotation names currently include:

- `uint8`
- `uint16`
- `uint32`
- `uint64`
- `int8`
- `int16`
- `int32`
- `int64`
- `bool`
- `int`

Example:

```python
x: uint8 = 0
```

becomes:

```c
uint8_t x = 0;
```

### Cast-style helpers

Calls such as:

- `uint8(expr)`
- `uint16(expr)`
- `int8(expr)`

become C casts.

### Array declarations

Array declarations are supported via annotated assignment:

```python
buf: array[uint8, 160] = None
```

becomes:

```c
uint8_t buf[160];
```

## Type inference for local variables

Untyped locals are inferred conservatively from a few common cases:

- `mem_read(...)` -> `uint8_t`
- `read_imm8()` / `pop8()` -> `uint8_t`
- `read_imm16()` / `pop16()` / `mem_read16(...)` -> `uint16_t`
- small integer constants -> `uint8_t`
- medium integer constants -> `uint16_t`
- larger integer constants -> `uint32_t`

If you want precise control, prefer explicit annotations or casts.

## Builtin and extern calls

The transpiler treats a set of standard C functions as extern-safe, including:

- `printf`
- `sprintf`
- `snprintf`
- `fprintf`
- `memcpy`
- `memset`
- `memmove`
- `malloc`
- `calloc`
- `realloc`
- `free`
- `abs`
- `sizeof`

Board-declared externs are also treated as direct calls without prepending `sys`.

Unknown function names are assumed to be generated helpers and receive `sys` automatically.

## Practical authoring guidelines

Handlers work best when they are:

- small,
- straight-line,
- explicit,
- side-effect focused.

Good style:

```python
@cpu.opcode(0x80, "ADD A,B", cycles=4)
def add_a_b(cpu):
    result = cpu.A + cpu.B
    cpu.F.C = 1 if result > 0xFF else 0
    cpu.A = result & 0xFF
    cpu.F.Z = 1 if cpu.A == 0 else 0
```

Less safe style:

- nested abstractions that depend on unsupported Python features,
- dynamic Python objects,
- list comprehensions,
- keyword-argument heavy helper usage,
- exception handling,
- context managers,
- generators,
- class definitions,
- pattern matching.

## Unsupported or best-avoided constructs

The transpiler does not currently implement general support for:

- `try` / `except`
- `with`
- `match`
- list, dict, and set comprehensions
- lambdas
- nested function definitions intended for transpilation
- keyword arguments in calls
- arbitrary Python objects or containers
- imports inside handler bodies
- decorators other than the framework entry points themselves

If you need one of these, use raw C for that handler.

## Testing as the source of truth

The most complete behavior reference for the transpiler today is:

- [`tests/test_transpiler.py`](/H:/Dev42/proto-emu-gen/tests/test_transpiler.py)
- [`tests/test_tier2_cycle_accurate.py`](/H:/Dev42/proto-emu-gen/tests/test_tier2_cycle_accurate.py)
- [`tests/test_tier3.py`](/H:/Dev42/proto-emu-gen/tests/test_tier3.py)

When in doubt, copy a pattern from those tests or from the working examples.
