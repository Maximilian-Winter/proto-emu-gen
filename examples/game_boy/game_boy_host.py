"""
game_boy_host.py -- SDL3 host definition for Game Boy emulator.

Imports the board from game_boy.py and wraps it with SDL3 display,
audio, and input. Generates a self-contained C file.

Usage:
    python game_boy_host.py

Output:
    game_boy_sdl.c

Compile:
    cc -o gameboy_sdl game_boy_sdl.c -lSDL3
"""

import os
import sys as _sys

# Add project root to path for proto imports
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _project_root not in _sys.path:
    _sys.path.insert(0, os.path.join(_project_root, 'src'))

from game_boy import board
from proto import SDLHost, PaletteMap, HostCodeGenerator

# ===================================================================
# Host Definition
# ===================================================================

host = SDLHost(board)

# ===================================================================
# Display: 160x144 native, 4x scale = 640x576 window
# ===================================================================

host.set_display(
    width=160,
    height=144,
    scale=4,
    title="Game Boy - proto-gen",
    vsync=True,
)

# ===================================================================
# Palette: Classic Game Boy green-ish 4-shade palette
# ===================================================================

palette = PaletteMap("gb")
palette.add(0, 0x9B, 0xBC, 0x0F)   # Lightest (yellow-green)
palette.add(1, 0x8B, 0xAC, 0x0F)   # Light green
palette.add(2, 0x30, 0x62, 0x30)   # Dark green
palette.add(3, 0x0F, 0x38, 0x0F)   # Darkest (deep olive)

host.set_palette(palette)

# ===================================================================
# Audio: 48kHz stereo
# ===================================================================

host.set_audio(
    sample_rate=48000,
    channels=2,
    buffer_size=2048,
)

# ===================================================================
# Frame Timing: 4.194304 MHz / 70224 cycles per frame = ~59.7 FPS
# ===================================================================

host.set_timing(cycles_per_frame=70224)

# ===================================================================
# Input Mapping: Keyboard -> Game Boy joypad
#
# Game Boy joypad uses active-low logic:
#   direction_state bits: 0=Right, 1=Left, 2=Up, 3=Down
#   button_state bits:    0=A, 1=B, 2=Select, 3=Start
# ===================================================================

# Direction pad
host.map_key("SDL_SCANCODE_RIGHT", "joypad", "direction_state", 0, label="D-Pad Right")
host.map_key("SDL_SCANCODE_LEFT",  "joypad", "direction_state", 1, label="D-Pad Left")
host.map_key("SDL_SCANCODE_UP",    "joypad", "direction_state", 2, label="D-Pad Up")
host.map_key("SDL_SCANCODE_DOWN",  "joypad", "direction_state", 3, label="D-Pad Down")

# Buttons
host.map_key("SDL_SCANCODE_Z",         "joypad", "button_state", 0, label="A Button")
host.map_key("SDL_SCANCODE_X",         "joypad", "button_state", 1, label="B Button")
host.map_key("SDL_SCANCODE_BACKSPACE", "joypad", "button_state", 2, label="Select")
host.map_key("SDL_SCANCODE_RETURN",    "joypad", "button_state", 3, label="Start")

# ===================================================================
# Menu System: Declarative mouse-driven menu bar
# ===================================================================

host.enable_menu()
host.add_default_menus()    # File, Display, Audio, Input menus

# Custom debug menu for Game Boy
debug = host.add_menu("Debug")
debug.add_toggle("Show BG", chip="ppu", field="show_bg")
debug.add_toggle("Show Sprites", chip="ppu", field="show_sprites")
debug.add_separator()
debug.add_action("Reset", code="gameboy_init(menu_sys);")

host.set_file_filters([("Game Boy ROMs", "gb;gbc"), ("All Files", "*")])

# ===================================================================
# Hook Bindings: Connect board extern stubs to SDL implementations
# ===================================================================

host.bind_render(
    extern_name="render_frame",
    framebuffer_chip="ppu",
    framebuffer_field="framebuffer",
    frame_flag_chip="ppu",
    frame_flag_field="frame_ready",
)

host.bind_audio(extern_name="audio_push")
host.bind_input(extern_name="poll_input")

# ===================================================================
# ROM Loading: Load from argv[1] with MBC auto-detection
# ===================================================================

host.set_rom_loading("cpu", "rom", "rom_size")

host.set_post_init("""
    sys.cpu.SP = 0xFFFE;
    sys.cpu.PC = 0x0100;
    sys.cpu.F = 0xB0;
""")

host.set_rom_loader("""
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
            /* Auto-detect MBC type from cartridge header */
            if (size > 0x0149) {
                uint8_t ct = sys.cpu.rom[0x0147];
                if (ct >= 0x01 && ct <= 0x03) sys.cpu.mbc_type = 1;
                else if (ct >= 0x0F && ct <= 0x13) sys.cpu.mbc_type = 3;
                else if (ct >= 0x19 && ct <= 0x1E) sys.cpu.mbc_type = 5;

                /* Allocate cart RAM based on header byte 0x0149 */
                uint8_t ram_code = sys.cpu.rom[0x0149];
                uint32_t ram_sizes[] = {0, 0, 8192, 32768, 131072, 65536};
                if (ram_code > 0 && ram_code <= 5) {
                    sys.cpu.cart_ram_size = ram_sizes[ram_code];
                    sys.cpu.cart_ram = (uint8_t*)calloc(sys.cpu.cart_ram_size, 1);
                }
            }
            printf("Loaded ROM: %ld bytes, MBC type: %d, RAM: %u bytes\\n",
                   size, sys.cpu.mbc_type, sys.cpu.cart_ram_size);
        } else {
            fprintf(stderr, "Failed to open ROM: %s\\n", argv[1]);
            SDL_Quit();
            return 1;
        }
    } else {
        fprintf(stderr, "Usage: %s <rom_file>\\n", argv[0]);
        SDL_Quit();
        return 1;
    }
""")

# ===================================================================
# Code Generation
# ===================================================================

if __name__ == "__main__":
    gen = HostCodeGenerator(host)
    code = gen.generate()

    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "game_boy_sdl.c")
    with open(out_path, "w") as f:
        f.write(code)

    print(f"Generated: {out_path}")
    print(f"Compile:   gcc -O2 -o gameboy_sdl.exe game_boy_sdl.c -I../extern/SDL3-3.4.0/include -L../extern/SDL3-3.4.0-win32-x64 -lSDL3")
    print(f"Run:       copy ..\\extern\\SDL3-3.4.0-win32-x64\\SDL3.dll . && gameboy_sdl.exe <rom.gb>")
