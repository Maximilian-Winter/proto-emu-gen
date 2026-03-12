# Host Layer

`proto-gen` can generate just the emulator core, or it can generate a desktop wrapper around that core using SDL3.

The host layer is modeled with `SDLHost` and emitted with `HostCodeGenerator`.

## Purpose

The host layer keeps platform concerns separate from the board model.

Use it to declare:

- display size and scaling,
- palette conversion,
- audio output,
- keyboard input,
- frame timing,
- menu bars and config,
- ROM loading,
- post-init boot code,
- bindings between generated board externs and SDL-side implementations.

## Basic flow

```python
from proto import SDLHost, PaletteMap, HostCodeGenerator
from my_board import board

host = SDLHost(board)
host.set_display(160, 144, scale=4, title="My Emulator", vsync=True)
host.set_audio(sample_rate=48000, channels=2, buffer_size=2048)
host.set_timing(cycles_per_frame=70224)

palette = PaletteMap("my_palette")
palette.add(0, 255, 255, 255)
palette.add(1, 170, 170, 170)
palette.add(2, 85, 85, 85)
palette.add(3, 0, 0, 0)
host.set_palette(palette)

host.bind_render("render_frame", "ppu", "framebuffer", "ppu", "frame_ready")
host.bind_audio("audio_push")
host.bind_input("poll_input")

code = HostCodeGenerator(host).generate()
```

The canonical repository example is [`examples/game_boy/game_boy_host.py`](../examples/game_boy/game_boy_host.py).

## What HostCodeGenerator emits

The host generator wraps the board C and appends SDL3-specific code.

Based on the implementation, the output may include:

- the generated board code,
- SDL3 includes,
- palette lookup tables,
- SDL globals for window/renderer/texture/audio,
- optional bitmap font data,
- optional config save/load helpers,
- optional file dialog support,
- optional menu bar data and logic,
- render/audio/input hook implementations,
- a `main()` function with SDL startup and the emulator loop.

## Display

Use `set_display(...)` to configure:

- native framebuffer width,
- native framebuffer height,
- integer scale factor,
- window title,
- vsync preference.

The generated renderer uploads a texture and presents it with nearest-neighbor scaling.

If a menu bar is enabled, the host composes the game view and menu area separately.

## Palette conversion

If your framebuffer stores palette indices rather than RGBA pixels, use `PaletteMap`.

Example:

```python
palette = PaletteMap("gb")
palette.add(0, 0x9B, 0xBC, 0x0F)
palette.add(1, 0x8B, 0xAC, 0x0F)
palette.add(2, 0x30, 0x62, 0x30)
palette.add(3, 0x0F, 0x38, 0x0F)
host.set_palette(palette)
```

Without a palette, the host falls back to grayscale expansion from the framebuffer byte values.

## Audio

Use `set_audio(...)` to declare:

- sample rate,
- channel count,
- buffer size.

Then bind an extern with `bind_audio(...)`.

The board model should declare the corresponding extern function signature via `Board.add_extern_func(...)`.

## Input mapping

Use `map_key(...)` to map SDL scancodes into chip state bits.

A binding includes:

- SDL scancode constant name,
- chip name,
- field name,
- bit index,
- active-low or active-high semantics,
- optional UI label.

This is a declarative way to keep host input wiring out of your core logic.

## Frame timing

Use `set_timing(cycles_per_frame=...)` so the generated `main()` knows how long to run the core before presenting each frame.

The host loop typically does:

1. poll SDL events,
2. update input state,
3. record CPU cycle count,
4. step the board until a frame budget has elapsed,
5. present graphics,
6. continue until quit.

## Render, audio, and input hook binding

These methods connect host-side generated helpers to board-declared externs:

- `bind_render(...)`
- `bind_audio(...)`
- `bind_input(...)`

For rendering you also specify where the framebuffer lives:

- framebuffer chip name,
- framebuffer field name,
- optional frame-ready flag chip and field.

## ROM loading

There are two host-side ROM loading modes.

### Simple field binding

Use:

```python
host.set_rom_loading("cpu", "rom", "rom_size")
```

This tells the generator which fields hold ROM data and size.

### Custom loader

Use:

```python
host.set_rom_loader("...")
```

when you need custom behavior such as:

- cartridge header parsing,
- mapper detection,
- cartridge RAM allocation,
- custom file validation.

The Game Boy host example uses this path.

## Post-init code

Use `set_post_init(...)` to inject host-side boot setup after generated board initialization.

Typical uses:

- setting `PC`, `SP`, or flags to post-BIOS values,
- initializing host-visible runtime flags,
- applying machine-specific startup state.

## Menu bar and config

The host layer can generate a menu bar and lightweight configuration system.

Enable it with:

```python
host.enable_menu()
host.add_default_menus()
```

Then add custom menus:

```python
debug = host.add_menu("Debug")
debug.add_toggle("Show BG", chip="ppu", field="show_bg")
debug.add_action("Reset", code="gameboy_init(menu_sys);")
```

Supported menu item styles include:

- action,
- toggle,
- slider,
- separator,
- keybind.

The host generator can also build config variables from those menu items and persist them through a simple generated config layer.

## File dialogs and filters

Use `set_file_filters(...)` to constrain the file dialog when your menu includes an "Open ROM" action.

This is especially useful for emulator frontends that load cartridge images directly from the host UI.

## Practical guidance

The host layer works best when:

- your board model already exposes clean extern hooks,
- your framebuffer and audio outputs have a stable shape,
- input is modeled as chip state, not ad hoc host callbacks,
- ROM loading and boot configuration are explicit.

If you are just validating the board generator, start without the host layer and use a small handwritten `main()`.

If you are building an interactive emulator application, move to `SDLHost` once the core is stable enough to run frames.

