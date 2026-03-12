"""
host_codegen.py -- SDL3 host C code generator for proto-gen boards.

Takes an SDLHost definition and generates a complete, compilable C file
containing both the board emulation code and the SDL3 host layer.
"""

from .host import SDLHost, MenuItemType
from .codegen import BoardCodeGenerator


# ===================================================================
# 8x8 Bitmap Font Data (ASCII 32-126, IBM VGA style)
# Each character is 8 bytes, each byte is one row (MSB = leftmost pixel)
# ===================================================================

FONT_8X8 = [
    [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],  # 32 (space)
    [0x18,0x3C,0x3C,0x18,0x18,0x00,0x18,0x00],  # 33 !
    [0x36,0x36,0x14,0x00,0x00,0x00,0x00,0x00],  # 34 "
    [0x36,0x36,0x7F,0x36,0x7F,0x36,0x36,0x00],  # 35 #
    [0x0C,0x3E,0x03,0x1E,0x30,0x1F,0x0C,0x00],  # 36 $
    [0x00,0x63,0x33,0x18,0x0C,0x66,0x63,0x00],  # 37 %
    [0x1C,0x36,0x1C,0x6E,0x3B,0x33,0x6E,0x00],  # 38 &
    [0x06,0x06,0x03,0x00,0x00,0x00,0x00,0x00],  # 39 '
    [0x18,0x0C,0x06,0x06,0x06,0x0C,0x18,0x00],  # 40 (
    [0x06,0x0C,0x18,0x18,0x18,0x0C,0x06,0x00],  # 41 )
    [0x00,0x66,0x3C,0xFF,0x3C,0x66,0x00,0x00],  # 42 *
    [0x00,0x0C,0x0C,0x3F,0x0C,0x0C,0x00,0x00],  # 43 +
    [0x00,0x00,0x00,0x00,0x00,0x0C,0x0C,0x06],  # 44 ,
    [0x00,0x00,0x00,0x3F,0x00,0x00,0x00,0x00],  # 45 -
    [0x00,0x00,0x00,0x00,0x00,0x0C,0x0C,0x00],  # 46 .
    [0x60,0x30,0x18,0x0C,0x06,0x03,0x01,0x00],  # 47 /
    [0x3E,0x63,0x73,0x7B,0x6F,0x67,0x3E,0x00],  # 48 0
    [0x0C,0x0E,0x0C,0x0C,0x0C,0x0C,0x3F,0x00],  # 49 1
    [0x1E,0x33,0x30,0x1C,0x06,0x33,0x3F,0x00],  # 50 2
    [0x1E,0x33,0x30,0x1C,0x30,0x33,0x1E,0x00],  # 51 3
    [0x38,0x3C,0x36,0x33,0x7F,0x30,0x78,0x00],  # 52 4
    [0x3F,0x03,0x1F,0x30,0x30,0x33,0x1E,0x00],  # 53 5
    [0x1C,0x06,0x03,0x1F,0x33,0x33,0x1E,0x00],  # 54 6
    [0x3F,0x33,0x30,0x18,0x0C,0x0C,0x0C,0x00],  # 55 7
    [0x1E,0x33,0x33,0x1E,0x33,0x33,0x1E,0x00],  # 56 8
    [0x1E,0x33,0x33,0x3E,0x30,0x18,0x0E,0x00],  # 57 9
    [0x00,0x0C,0x0C,0x00,0x00,0x0C,0x0C,0x00],  # 58 :
    [0x00,0x0C,0x0C,0x00,0x00,0x0C,0x0C,0x06],  # 59 ;
    [0x18,0x0C,0x06,0x03,0x06,0x0C,0x18,0x00],  # 60 <
    [0x00,0x00,0x3F,0x00,0x00,0x3F,0x00,0x00],  # 61 =
    [0x06,0x0C,0x18,0x30,0x18,0x0C,0x06,0x00],  # 62 >
    [0x1E,0x33,0x30,0x18,0x0C,0x00,0x0C,0x00],  # 63 ?
    [0x3E,0x63,0x7B,0x7B,0x7B,0x03,0x1E,0x00],  # 64 @
    [0x0C,0x1E,0x33,0x33,0x3F,0x33,0x33,0x00],  # 65 A
    [0x3F,0x66,0x66,0x3E,0x66,0x66,0x3F,0x00],  # 66 B
    [0x3C,0x66,0x03,0x03,0x03,0x66,0x3C,0x00],  # 67 C
    [0x1F,0x36,0x66,0x66,0x66,0x36,0x1F,0x00],  # 68 D
    [0x7F,0x46,0x16,0x1E,0x16,0x46,0x7F,0x00],  # 69 E
    [0x7F,0x46,0x16,0x1E,0x16,0x06,0x0F,0x00],  # 70 F
    [0x3C,0x66,0x03,0x03,0x73,0x66,0x7C,0x00],  # 71 G
    [0x33,0x33,0x33,0x3F,0x33,0x33,0x33,0x00],  # 72 H
    [0x1E,0x0C,0x0C,0x0C,0x0C,0x0C,0x1E,0x00],  # 73 I
    [0x78,0x30,0x30,0x30,0x33,0x33,0x1E,0x00],  # 74 J
    [0x67,0x66,0x36,0x1E,0x36,0x66,0x67,0x00],  # 75 K
    [0x0F,0x06,0x06,0x06,0x46,0x66,0x7F,0x00],  # 76 L
    [0x63,0x77,0x7F,0x7F,0x6B,0x63,0x63,0x00],  # 77 M
    [0x63,0x67,0x6F,0x7B,0x73,0x63,0x63,0x00],  # 78 N
    [0x1C,0x36,0x63,0x63,0x63,0x36,0x1C,0x00],  # 79 O
    [0x3F,0x66,0x66,0x3E,0x06,0x06,0x0F,0x00],  # 80 P
    [0x1E,0x33,0x33,0x33,0x3B,0x1E,0x38,0x00],  # 81 Q
    [0x3F,0x66,0x66,0x3E,0x36,0x66,0x67,0x00],  # 82 R
    [0x1E,0x33,0x07,0x0E,0x38,0x33,0x1E,0x00],  # 83 S
    [0x3F,0x2D,0x0C,0x0C,0x0C,0x0C,0x1E,0x00],  # 84 T
    [0x33,0x33,0x33,0x33,0x33,0x33,0x3F,0x00],  # 85 U
    [0x33,0x33,0x33,0x33,0x33,0x1E,0x0C,0x00],  # 86 V
    [0x63,0x63,0x63,0x6B,0x7F,0x77,0x63,0x00],  # 87 W
    [0x63,0x63,0x36,0x1C,0x1C,0x36,0x63,0x00],  # 88 X
    [0x33,0x33,0x33,0x1E,0x0C,0x0C,0x1E,0x00],  # 89 Y
    [0x7F,0x63,0x31,0x18,0x4C,0x66,0x7F,0x00],  # 90 Z
    [0x1E,0x06,0x06,0x06,0x06,0x06,0x1E,0x00],  # 91 [
    [0x03,0x06,0x0C,0x18,0x30,0x60,0x40,0x00],  # 92 backslash
    [0x1E,0x18,0x18,0x18,0x18,0x18,0x1E,0x00],  # 93 ]
    [0x08,0x1C,0x36,0x63,0x00,0x00,0x00,0x00],  # 94 ^
    [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0xFF],  # 95 _
    [0x0C,0x0C,0x18,0x00,0x00,0x00,0x00,0x00],  # 96 `
    [0x00,0x00,0x1E,0x30,0x3E,0x33,0x6E,0x00],  # 97 a
    [0x07,0x06,0x06,0x3E,0x66,0x66,0x3B,0x00],  # 98 b
    [0x00,0x00,0x1E,0x33,0x03,0x33,0x1E,0x00],  # 99 c
    [0x38,0x30,0x30,0x3E,0x33,0x33,0x6E,0x00],  # 100 d
    [0x00,0x00,0x1E,0x33,0x3F,0x03,0x1E,0x00],  # 101 e
    [0x1C,0x36,0x06,0x0F,0x06,0x06,0x0F,0x00],  # 102 f
    [0x00,0x00,0x6E,0x33,0x33,0x3E,0x30,0x1F],  # 103 g
    [0x07,0x06,0x36,0x6E,0x66,0x66,0x67,0x00],  # 104 h
    [0x0C,0x00,0x0E,0x0C,0x0C,0x0C,0x1E,0x00],  # 105 i
    [0x30,0x00,0x30,0x30,0x30,0x33,0x33,0x1E],  # 106 j
    [0x07,0x06,0x66,0x36,0x1E,0x36,0x67,0x00],  # 107 k
    [0x0E,0x0C,0x0C,0x0C,0x0C,0x0C,0x1E,0x00],  # 108 l
    [0x00,0x00,0x33,0x7F,0x7F,0x6B,0x63,0x00],  # 109 m
    [0x00,0x00,0x1F,0x33,0x33,0x33,0x33,0x00],  # 110 n
    [0x00,0x00,0x1E,0x33,0x33,0x33,0x1E,0x00],  # 111 o
    [0x00,0x00,0x3B,0x66,0x66,0x3E,0x06,0x0F],  # 112 p
    [0x00,0x00,0x6E,0x33,0x33,0x3E,0x30,0x78],  # 113 q
    [0x00,0x00,0x3B,0x6E,0x66,0x06,0x0F,0x00],  # 114 r
    [0x00,0x00,0x3E,0x03,0x1E,0x30,0x1F,0x00],  # 115 s
    [0x08,0x0C,0x3E,0x0C,0x0C,0x2C,0x18,0x00],  # 116 t
    [0x00,0x00,0x33,0x33,0x33,0x33,0x6E,0x00],  # 117 u
    [0x00,0x00,0x33,0x33,0x33,0x1E,0x0C,0x00],  # 118 v
    [0x00,0x00,0x63,0x6B,0x7F,0x7F,0x36,0x00],  # 119 w
    [0x00,0x00,0x63,0x36,0x1C,0x36,0x63,0x00],  # 120 x
    [0x00,0x00,0x33,0x33,0x33,0x3E,0x30,0x1F],  # 121 y
    [0x00,0x00,0x3F,0x19,0x0C,0x26,0x3F,0x00],  # 122 z
    [0x38,0x0C,0x0C,0x07,0x0C,0x0C,0x38,0x00],  # 123 {
    [0x18,0x18,0x18,0x00,0x18,0x18,0x18,0x00],  # 124 |
    [0x07,0x0C,0x0C,0x38,0x0C,0x0C,0x07,0x00],  # 125 }
    [0x6E,0x3B,0x00,0x00,0x00,0x00,0x00,0x00],  # 126 ~
]


class HostCodeGenerator:
    """Generates SDL3 host C code wrapping a proto-gen board.

    Output is a single monolithic .c file:
      1. Board code (from BoardCodeGenerator)
      2. SDL3 includes
      3. Bitmap font data (if menu enabled)
      4. Config struct and defaults (if menu enabled)
      5. SDL global variables
      6. Palette lookup table
      7. Mini-JSON config load/save (if menu enabled)
      8. File dialog (if menu enabled)
      9. Menu bar data (if menu enabled)
     10. Menu bar logic (if menu enabled)
     11. Menu apply config (if menu enabled)
     12. render_frame() implementation
     13. audio_push() implementation
     14. poll_input() implementation
     15. main() with SDL3 init, event loop, cleanup
    """

    def __init__(self, host: SDLHost):
        self.host = host
        self.board = host.board
        self.board_gen = BoardCodeGenerator(host.board)

    # --- naming helpers (mirror codegen.py) ---

    @property
    def sn(self):
        """Board name lowercased."""
        return self.board.name.lower()

    @property
    def st(self):
        """Board struct type name."""
        return f"{self.sn}_t"

    @property
    def cpu_chip_name(self):
        """Name of the primary CPU chip."""
        cpus = self.board.cpu_chips
        return cpus[0].name if cpus else "cpu"

    def _has_menu_bar(self):
        """Whether the menu bar system is enabled."""
        return self.host._menu_bar is not None

    # --- Collect config vars from menu tree ---

    def _collect_config_vars(self):
        """Walk menu tree and collect all config-backed variables.

        Returns list of dicts: {key, c_type, default_expr, c_accessor}
        Also adds key_bindings entries.
        """
        vars_list = []
        seen_keys = set()
        d = self.host.display

        for menu in self.host._menus:
            for item in menu.items:
                if item.item_type == MenuItemType.Toggle and item.toggle_config_key:
                    key = item.toggle_config_key
                    if key not in seen_keys:
                        seen_keys.add(key)
                        default = "true"
                        if key == "vsync":
                            default = "true" if (d and d.vsync) else "false"
                        vars_list.append({
                            'key': key, 'c_type': 'bool',
                            'default_expr': default,
                            'c_accessor': f'config.{key}',
                        })
                elif item.item_type == MenuItemType.Slider and item.slider_config_key:
                    key = item.slider_config_key
                    if key not in seen_keys:
                        seen_keys.add(key)
                        default = "100"
                        if key == "display_scale":
                            default = str(d.scale if d else 4)
                        elif key == "volume":
                            default = "100"
                        vars_list.append({
                            'key': key, 'c_type': 'int',
                            'default_expr': default,
                            'c_accessor': f'config.{key}',
                            'min': item.slider_min,
                            'max': item.slider_max,
                            'step': item.slider_step,
                        })
        return vars_list

    # --- Flatten menu tree into item arrays ---

    def _flatten_menus(self):
        """Flatten the menu tree into parallel arrays for codegen.

        Returns:
            menus: list of {label, item_start, item_count}
            items: list of {label, type_str, data_index}
            actions: list of {code}
            toggles: list of {config_key, chip, field}
            sliders: list of {config_key, min, max, step}
            keybinds: list of {binding_index}
        """
        menus = []
        items = []
        actions = []
        toggles = []
        sliders = []
        keybinds = []

        for menu in self.host._menus:
            item_start = len(items)
            for mi in menu.items:
                if mi.item_type == MenuItemType.Action:
                    items.append({'label': mi.label, 'type': 'MTYPE_ACTION', 'data_index': len(actions)})
                    actions.append({'code': mi.action_code or ''})
                elif mi.item_type == MenuItemType.Toggle:
                    items.append({'label': mi.label, 'type': 'MTYPE_TOGGLE', 'data_index': len(toggles)})
                    toggles.append({
                        'config_key': mi.toggle_config_key,
                        'chip': mi.toggle_chip,
                        'field': mi.toggle_field,
                    })
                elif mi.item_type == MenuItemType.Slider:
                    items.append({'label': mi.label, 'type': 'MTYPE_SLIDER', 'data_index': len(sliders)})
                    sliders.append({
                        'config_key': mi.slider_config_key,
                        'min': mi.slider_min,
                        'max': mi.slider_max,
                        'step': mi.slider_step,
                    })
                elif mi.item_type == MenuItemType.Separator:
                    items.append({'label': '', 'type': 'MTYPE_SEPARATOR', 'data_index': 0})
                elif mi.item_type == MenuItemType.KeyBind:
                    items.append({'label': mi.label, 'type': 'MTYPE_KEYBIND', 'data_index': len(keybinds)})
                    keybinds.append({'binding_index': mi.keybind_index})
            menus.append({
                'label': menu.label,
                'item_start': item_start,
                'item_count': len(menu.items),
            })

        return menus, items, actions, toggles, sliders, keybinds

    # --- generation pipeline ---

    def generate(self) -> str:
        """Generate complete C file: board + SDL3 host."""
        parts = [
            self._gen_board_code(),
            self._gen_sdl_includes(),
        ]
        if self._has_menu_bar():
            parts.append(self._gen_font_data())
            parts.append(self._gen_config_struct())
        parts += [
            self._gen_sdl_globals(),
            self._gen_palette_table(),
        ]
        if self._has_menu_bar():
            parts.append(self._gen_mini_json())
            parts.append(self._gen_file_dialog())
            parts.append(self._gen_menu_bar_data())
            parts.append(self._gen_menu_bar_logic())
            parts.append(self._gen_menu_apply())
        parts += [
            self._gen_render_impl(),
            self._gen_audio_impl(),
            self._gen_input_impl(),
            self._gen_main(),
        ]
        return '\n\n'.join(p for p in parts if p)

    # --- 1. Board code ---

    def _gen_board_code(self) -> str:
        """Full board C code from BoardCodeGenerator."""
        return self.board_gen.generate()

    # --- 2. SDL3 includes ---

    def _gen_sdl_includes(self) -> str:
        lines = [
            "/* ================================================================= */",
            "/* SDL3 Host Layer                                                    */",
            "/* ================================================================= */",
            "",
            "#include <SDL3/SDL.h>",
            "#include <SDL3/SDL_main.h>",
        ]
        if self._has_menu_bar():
            lines.append("#include <SDL3/SDL_dialog.h>")
            lines.append("#include <string.h>")
        return '\n'.join(lines)

    # --- 3. Bitmap font data (menu only) ---

    def _gen_font_data(self) -> str:
        """Generate 8x8 bitmap font and text drawing helpers (1x and scaled)."""
        lines = [
            "/* ================================================================= */",
            "/* Bitmap Font (8x8, ASCII 32-126)                                   */",
            "/* ================================================================= */",
            "",
            "static const uint8_t font_8x8[95][8] = {",
        ]
        for i, glyph in enumerate(FONT_8X8):
            ch = chr(i + 32)
            safe_ch = ch if ch not in ('\\', "'") else f'\\{ch}'
            row_str = ",".join(f"0x{b:02X}" for b in glyph)
            lines.append(f"    {{{row_str}}},  /* {i+32} '{safe_ch}' */")
        lines.append("};")
        lines.append("")

        # draw_char (1x, for game-res overlay if needed)
        lines += [
            "static void draw_char(SDL_Renderer* r, int x, int y, char ch,",
            "                      uint8_t cr, uint8_t cg, uint8_t cb, uint8_t ca) {",
            "    if (ch < 32 || ch > 126) return;",
            "    const uint8_t* glyph = font_8x8[ch - 32];",
            "    SDL_SetRenderDrawColor(r, cr, cg, cb, ca);",
            "    for (int row = 0; row < 8; row++) {",
            "        uint8_t bits = glyph[row];",
            "        for (int col = 0; col < 8; col++) {",
            "            if (bits & (1 << col)) {",
            "                SDL_FRect rc = {(float)(x+col), (float)(y+row), 1.0f, 1.0f};",
            "                SDL_RenderFillRect(r, &rc);",
            "            }",
            "        }",
            "    }",
            "}",
            "",
            "static void draw_text(SDL_Renderer* r, int x, int y, const char* text,",
            "                      uint8_t cr, uint8_t cg, uint8_t cb, uint8_t ca) {",
            "    while (*text) {",
            "        draw_char(r, x, y, *text, cr, cg, cb, ca);",
            "        x += 8;",
            "        text++;",
            "    }",
            "}",
            "",
        ]

        # draw_char_scaled and draw_text_scaled (for menu bar at window res)
        lines += [
            "static void draw_char_scaled(SDL_Renderer* r, int x, int y, char ch,",
            "                             int scale,",
            "                             uint8_t cr, uint8_t cg, uint8_t cb, uint8_t ca) {",
            "    if (ch < 32 || ch > 126) return;",
            "    const uint8_t* glyph = font_8x8[ch - 32];",
            "    SDL_SetRenderDrawColor(r, cr, cg, cb, ca);",
            "    for (int row = 0; row < 8; row++) {",
            "        uint8_t bits = glyph[row];",
            "        for (int col = 0; col < 8; col++) {",
            "            if (bits & (1 << col)) {",
            "                SDL_FRect rc = {(float)(x + col*scale),",
            "                                (float)(y + row*scale),",
            "                                (float)scale, (float)scale};",
            "                SDL_RenderFillRect(r, &rc);",
            "            }",
            "        }",
            "    }",
            "}",
            "",
            "static void draw_text_scaled(SDL_Renderer* r, int x, int y,",
            "                             const char* text, int scale,",
            "                             uint8_t cr, uint8_t cg, uint8_t cb, uint8_t ca) {",
            "    while (*text) {",
            "        draw_char_scaled(r, x, y, *text, scale, cr, cg, cb, ca);",
            "        x += 8 * scale;",
            "        text++;",
            "    }",
            "}",
            "",
            "static int text_width_scaled(const char* text, int scale) {",
            "    int len = 0;",
            "    while (*text) { len++; text++; }",
            "    return len * 8 * scale;",
            "}",
        ]
        return '\n'.join(lines)

    # --- 4. Config struct and defaults (menu only) ---

    def _gen_config_struct(self) -> str:
        """Generate config struct auto-built from menu tree."""
        config_vars = self._collect_config_vars()
        bindings = self.host.input.bindings
        n = len(bindings)

        lines = [
            "/* ================================================================= */",
            "/* Configuration                                                      */",
            "/* ================================================================= */",
            "",
            f"#define NUM_KEY_BINDINGS {n}",
            "",
            "typedef struct {",
        ]

        # Config fields from menu tree
        for cv in config_vars:
            lines.append(f"    {cv['c_type']} {cv['key']};")
        # Key bindings array
        lines.append(f"    SDL_Scancode key_bindings[{max(n,1)}];")
        lines.append("} emu_config_t;")
        lines.append("")
        lines.append("static emu_config_t config;")
        lines.append("")

        # Key labels and defaults
        if n > 0:
            lines.append(f"static const char* key_labels[{n}] = {{")
            for i, kb in enumerate(bindings):
                label = kb.label or f"Key {i}"
                lines.append(f'    "{label}",')
            lines.append("};")
            lines.append("")

            lines.append(f"static const SDL_Scancode key_defaults[{n}] = {{")
            for kb in bindings:
                lines.append(f"    {kb.scancode},")
            lines.append("};")
            lines.append("")

        # config_set_defaults
        lines.append("static void config_set_defaults(void) {")
        for cv in config_vars:
            lines.append(f"    config.{cv['key']} = {cv['default_expr']};")
        if n > 0:
            lines.append(f"    for (int i = 0; i < {n}; i++)")
            lines.append("        config.key_bindings[i] = key_defaults[i];")
        lines.append("}")
        return '\n'.join(lines)

    # --- 5. SDL globals ---

    def _gen_sdl_globals(self) -> str:
        lines = []

        if self.host.display:
            d = self.host.display
            lines.append(f"#define NATIVE_W {d.width}")
            lines.append(f"#define NATIVE_H {d.height}")
            lines.append("")

        if self._has_menu_bar():
            bar = self.host._menu_bar
            lines.append(f"#define MENU_BAR_HEIGHT {bar.bar_height}")
            lines.append(f"#define MENU_FONT_SCALE {bar.font_scale}")
            lines.append(f"#define MENU_CHAR_W (8 * MENU_FONT_SCALE)")
            lines.append(f"#define MENU_CHAR_H (8 * MENU_FONT_SCALE)")
            lines.append("")

        lines += [
            "static SDL_Window* sdl_window = NULL;",
            "static SDL_Renderer* sdl_renderer = NULL;",
            "static SDL_Texture* sdl_texture = NULL;",
            "static bool sdl_running = true;",
        ]

        if self._has_menu_bar():
            lines.append("static int win_w = 0, win_h = 0;")
            lines.append(f"static {self.st}* menu_sys = NULL;")

        # RGBA conversion buffer (if display configured)
        if self.host.display:
            d = self.host.display
            buf_size = d.width * d.height
            lines.append(f"static uint32_t sdl_rgba_buffer[{buf_size}];")

        # Audio stream (if audio configured)
        if self.host.audio:
            lines.append("static SDL_AudioStream* sdl_audio_stream = NULL;")

        return '\n'.join(lines)

    # --- 6. Palette lookup table ---

    def _gen_palette_table(self) -> str:
        if not self.host.palette:
            return ""

        pal = self.host.palette
        entries = sorted(pal.entries, key=lambda e: e.index)
        count = max(e.index for e in entries) + 1 if entries else 0

        lines = [f"static const uint32_t {pal.name}_lut[{count}] = {{"]
        table = [0x000000FF] * count
        for e in entries:
            rgba = (e.r << 24) | (e.g << 16) | (e.b << 8) | e.a
            table[e.index] = rgba

        for i, rgba in enumerate(table):
            lines.append(f"    0x{rgba:08X},  /* index {i} */")

        lines.append("};")
        return '\n'.join(lines)

    # --- 7. Mini-JSON config load/save (menu only) ---

    def _gen_mini_json(self) -> str:
        """Generate config_save and config_load for registered config vars."""
        config_vars = self._collect_config_vars()
        n = len(self.host.input.bindings)

        lines = [
            "/* ================================================================= */",
            "/* Config Save/Load (minimal JSON)                                   */",
            "/* ================================================================= */",
            "",
        ]

        # config_save
        lines += [
            'static bool config_save(const char* path) {',
            '    FILE* f = fopen(path, "w");',
            '    if (!f) return false;',
            '    fprintf(f, "{\\n");',
        ]
        for i, cv in enumerate(config_vars):
            comma = "," if (i < len(config_vars) - 1 or n > 0) else ""
            if cv['c_type'] == 'bool':
                lines.append(f'    fprintf(f, "  \\"{cv["key"]}\\": %s{comma}\\n", config.{cv["key"]} ? "true" : "false");')
            else:
                lines.append(f'    fprintf(f, "  \\"{cv["key"]}\\": %d{comma}\\n", config.{cv["key"]});')
        if n > 0:
            lines += [
                '    fprintf(f, "  \\"key_bindings\\": {\\n");',
                f'    for (int i = 0; i < {n}; i++) {{',
                f'        fprintf(f, "    \\"%s\\": %d%s\\n", key_labels[i],',
                f'                (int)config.key_bindings[i], i < {n}-1 ? "," : "");',
                '    }',
                '    fprintf(f, "  }\\n");',
            ]
        lines += [
            '    fprintf(f, "}\\n");',
            '    fclose(f);',
            '    return true;',
            '}',
            '',
        ]

        # config_load
        lines += [
            'static bool config_load(const char* path) {',
            '    FILE* f = fopen(path, "rb");',
            '    if (!f) return false;',
            '    fseek(f, 0, SEEK_END);',
            '    long size = ftell(f);',
            '    fseek(f, 0, SEEK_SET);',
            '    char* buf = (char*)malloc(size + 1);',
            '    fread(buf, 1, size, f);',
            '    buf[size] = \'\\0\';',
            '    fclose(f);',
            '',
            '    const char* p = buf;',
            '    while (*p) {',
            '        while (*p && *p != \'"\') p++;',
            '        if (!*p) break;',
            '        p++;',
            '        const char* key_start = p;',
            '        while (*p && *p != \'"\') p++;',
            '        if (!*p) break;',
            '        int key_len = (int)(p - key_start);',
            '        p++;',
            '        while (*p && *p != \':\') p++;',
            '        if (!*p) break;',
            '        p++;',
            '        while (*p == \' \' || *p == \'\\t\' || *p == \'\\n\' || *p == \'\\r\') p++;',
            '',
        ]
        # Match known keys
        first = True
        for cv in config_vars:
            kl = len(cv['key'])
            prefix = "        if" if first else "        } else if"
            first = False
            lines.append(f'{prefix} (key_len == {kl} && memcmp(key_start, "{cv["key"]}", {kl}) == 0) {{')
            if cv['c_type'] == 'bool':
                lines.append(f"            config.{cv['key']} = (*p == 't');")
            else:
                lines.append(f"            config.{cv['key']} = atoi(p);")

        if n > 0:
            prefix = "        } else if" if not first else "        if"
            lines += [
                f'{prefix} (key_len == 12 && memcmp(key_start, "key_bindings", 12) == 0) {{',
                '            while (*p && *p != \'}\') {',
                '                while (*p && *p != \'"\') p++;',
                '                if (!*p || *p == \'}\') break;',
                '                p++;',
                '                const char* lbl_start = p;',
                '                while (*p && *p != \'"\') p++;',
                '                if (!*p) break;',
                '                int lbl_len = (int)(p - lbl_start);',
                '                p++;',
                '                while (*p && *p != \':\') p++;',
                '                if (!*p) break;',
                '                p++;',
                '                while (*p == \' \' || *p == \'\\t\') p++;',
                '                int sc = atoi(p);',
                f'                for (int i = 0; i < {n}; i++) {{',
                '                    if ((int)strlen(key_labels[i]) == lbl_len &&',
                '                        memcmp(key_labels[i], lbl_start, lbl_len) == 0) {',
                '                        config.key_bindings[i] = (SDL_Scancode)sc;',
                '                        break;',
                '                    }',
                '                }',
                '            }',
            ]

        if not first:
            lines.append('        }')
        lines += [
            '    }',
            '    free(buf);',
            '    return true;',
            '}',
        ]
        return '\n'.join(lines)

    # --- 8. File dialog (menu only) ---

    def _gen_file_dialog(self) -> str:
        """Generate SDL3 file dialog callback and opener."""
        # Check if any action references menu_open_file_dialog
        has_file_dialog = False
        for menu in self.host._menus:
            for item in menu.items:
                if item.item_type == MenuItemType.Action and item.action_code:
                    if 'menu_open_file_dialog' in item.action_code:
                        has_file_dialog = True
                        break
        if not has_file_dialog:
            return ""

        filters = self.host._file_filters or [("All Files", "*")]

        lines = [
            "/* ================================================================= */",
            "/* File Dialog                                                        */",
            "/* ================================================================= */",
            "",
            "static char pending_rom_path[4096] = {0};",
            "static bool pending_rom_load = false;",
            "",
            "static void SDLCALL file_dialog_callback(void* userdata,",
            "    const char* const* filelist, int filter) {",
            "    (void)userdata; (void)filter;",
            "    if (!filelist || !*filelist) return;",
            "    strncpy(pending_rom_path, filelist[0], sizeof(pending_rom_path) - 1);",
            "    pending_rom_load = true;",
            "}",
            "",
            "static void menu_open_file_dialog(void) {",
            f"    static SDL_DialogFileFilter filters[] = {{",
        ]
        for name, pattern in filters:
            lines.append(f'        {{"{name}", "{pattern}"}},')
        lines += [
            "    };",
            f"    SDL_ShowOpenFileDialog(file_dialog_callback, NULL, sdl_window,",
            f"        filters, {len(filters)}, NULL, false);",
            "}",
        ]
        return '\n'.join(lines)

    # --- 9. Menu bar data (menu only) ---

    def _gen_menu_bar_data(self) -> str:
        """Generate static menu arrays from flattened menu tree."""
        menus, items, actions, toggles, sliders, keybinds = self._flatten_menus()

        n_menus = len(menus)
        n_items = len(items)
        n_actions = len(actions)
        n_toggles = len(toggles)
        n_sliders = len(sliders)
        n_keybinds = len(keybinds)

        lines = [
            "/* ================================================================= */",
            "/* Menu Bar Data                                                      */",
            "/* ================================================================= */",
            "",
            "#define MTYPE_ACTION    0",
            "#define MTYPE_TOGGLE    1",
            "#define MTYPE_SLIDER    2",
            "#define MTYPE_SEPARATOR 3",
            "#define MTYPE_KEYBIND   4",
            "",
            f"#define N_MENUS    {n_menus}",
            f"#define N_ITEMS    {max(n_items, 1)}",
            f"#define N_ACTIONS  {max(n_actions, 1)}",
            f"#define N_TOGGLES  {max(n_toggles, 1)}",
            f"#define N_SLIDERS  {max(n_sliders, 1)}",
            f"#define N_KEYBINDS {max(n_keybinds, 1)}",
            "",
            "typedef struct { const char* label; int type; int data_index; } menu_item_t;",
            "typedef struct { const char* label; int item_start; int item_count; int bar_x; int bar_w; } menu_def_t;",
            "",
        ]

        # Menu definitions
        lines.append(f"static menu_def_t menus[N_MENUS] = {{")
        for m in menus:
            lines.append(f'    {{"{m["label"]}", {m["item_start"]}, {m["item_count"]}, 0, 0}},')
        lines.append("};")
        lines.append("")

        # Item definitions
        lines.append(f"static menu_item_t items[N_ITEMS] = {{")
        for it in items:
            lbl = it['label'].replace('"', '\\"')
            lines.append(f'    {{"{lbl}", {it["type"]}, {it["data_index"]}}},')
        if not items:
            lines.append('    {"", 0, 0},')
        lines.append("};")
        lines.append("")

        # Menu state
        lines += [
            "static int menu_open = -1;",
            "static int menu_hover_item = -1;",
            "static int menu_hover_bar = -1;",
            "static bool menu_rebinding = false;",
            "static int menu_rebind_idx = -1;",
            "",
            "/* Forward declarations */",
            "static void menu_apply_config(void);",
            "",
        ]

        return '\n'.join(lines)

    # --- 10. Menu bar logic (menu only) ---

    def _gen_menu_bar_logic(self) -> str:
        """Generate menu bar init, render, hit-test, and event handling."""
        menus, items, actions, toggles, sliders, keybinds = self._flatten_menus()
        bar = self.host._menu_bar
        bg = bar.bg_color
        tc = bar.text_color
        hl = bar.highlight_color
        ac = bar.active_color
        sc = bar.separator_color
        dd_bg = bar.dropdown_bg

        lines = [
            "/* ================================================================= */",
            "/* Menu Bar Logic                                                     */",
            "/* ================================================================= */",
            "",
        ]

        # menu_bar_init: compute bar_x/bar_w for each menu
        lines += [
            "static void menu_bar_init(void) {",
            "    int x = 8;",
            "    for (int i = 0; i < N_MENUS; i++) {",
            "        menus[i].bar_x = x;",
            "        menus[i].bar_w = text_width_scaled(menus[i].label, MENU_FONT_SCALE) + 16;",
            "        x += menus[i].bar_w;",
            "    }",
            "}",
            "",
        ]

        # menu_bar_render
        lines += [
            "static void menu_bar_render(SDL_Renderer* r, int ww) {",
            "    SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_BLEND);",
            "",
            "    /* Bar background */",
            f"    SDL_SetRenderDrawColor(r, {bg[0]}, {bg[1]}, {bg[2]}, {bg[3]});",
            "    SDL_FRect bar_bg = {0, 0, (float)ww, (float)MENU_BAR_HEIGHT};",
            "    SDL_RenderFillRect(r, &bar_bg);",
            "",
            "    /* Bottom border */",
            f"    SDL_SetRenderDrawColor(r, {sc[0]}, {sc[1]}, {sc[2]}, {sc[3]});",
            "    SDL_FRect border = {0, (float)(MENU_BAR_HEIGHT-1), (float)ww, 1.0f};",
            "    SDL_RenderFillRect(r, &border);",
            "",
            "    /* Category labels */",
            "    int text_y = (MENU_BAR_HEIGHT - MENU_CHAR_H) / 2;",
            "    for (int i = 0; i < N_MENUS; i++) {",
            "        bool is_open = (menu_open == i);",
            "        bool is_hover = (menu_hover_bar == i && menu_open < 0);",
            "        if (is_open) {",
            f"            SDL_SetRenderDrawColor(r, {ac[0]}, {ac[1]}, {ac[2]}, {ac[3]});",
            "            SDL_FRect cat_bg = {(float)menus[i].bar_x, 0, (float)menus[i].bar_w, (float)MENU_BAR_HEIGHT};",
            "            SDL_RenderFillRect(r, &cat_bg);",
            "        } else if (is_hover) {",
            f"            SDL_SetRenderDrawColor(r, {hl[0]}, {hl[1]}, {hl[2]}, {hl[3]});",
            "            SDL_FRect cat_bg = {(float)menus[i].bar_x, 0, (float)menus[i].bar_w, (float)MENU_BAR_HEIGHT};",
            "            SDL_RenderFillRect(r, &cat_bg);",
            "        }",
            f"        draw_text_scaled(r, menus[i].bar_x + 8, text_y,",
            f"            menus[i].label, MENU_FONT_SCALE,",
            f"            {tc[0]}, {tc[1]}, {tc[2]}, {tc[3]});",
            "    }",
            "",
        ]

        # Dropdown rendering
        lines += [
            "    /* Dropdown */",
            "    if (menu_open >= 0 && menu_open < N_MENUS) {",
            "        menu_def_t* md = &menus[menu_open];",
            "        int item_h = MENU_CHAR_H + 4;",
            "        int sep_h = 6;",
            "",
            "        /* Calculate dropdown dimensions */",
            "        int dd_w = 0;",
            "        int dd_h = 4;  /* top padding */",
            "        for (int i = 0; i < md->item_count; i++) {",
            "            menu_item_t* mi = &items[md->item_start + i];",
            "            if (mi->type == MTYPE_SEPARATOR) { dd_h += sep_h; continue; }",
            "            int lw = text_width_scaled(mi->label, MENU_FONT_SCALE) + 32;",
            "            /* Extra space for toggle/slider/keybind values */",
            "            if (mi->type == MTYPE_TOGGLE) lw += 60;",
            "            if (mi->type == MTYPE_SLIDER) lw += 100;",
            "            if (mi->type == MTYPE_KEYBIND) lw += 120;",
            "            if (lw > dd_w) dd_w = lw;",
            "            dd_h += item_h;",
            "        }",
            "        dd_h += 4;  /* bottom padding */",
            "        if (dd_w < 120) dd_w = 120;",
            "",
            "        /* Dropdown background */",
            f"        SDL_SetRenderDrawColor(r, {dd_bg[0]}, {dd_bg[1]}, {dd_bg[2]}, {dd_bg[3]});",
            "        SDL_FRect dd_rect = {(float)md->bar_x, (float)MENU_BAR_HEIGHT, (float)dd_w, (float)dd_h};",
            "        SDL_RenderFillRect(r, &dd_rect);",
            "",
            "        /* Dropdown border */",
            f"        SDL_SetRenderDrawColor(r, {sc[0]}, {sc[1]}, {sc[2]}, {sc[3]});",
            "        SDL_RenderRect(r, &dd_rect);",
            "",
            "        /* Items */",
            "        int iy = MENU_BAR_HEIGHT + 4;",
            "        int selectable_idx = 0;",
            "        for (int i = 0; i < md->item_count; i++) {",
            "            menu_item_t* mi = &items[md->item_start + i];",
            "            if (mi->type == MTYPE_SEPARATOR) {",
            f"                SDL_SetRenderDrawColor(r, {sc[0]}, {sc[1]}, {sc[2]}, {sc[3]});",
            "                SDL_FRect sep = {(float)(md->bar_x + 4), (float)(iy + 2), (float)(dd_w - 8), 1.0f};",
            "                SDL_RenderFillRect(r, &sep);",
            "                iy += sep_h;",
            "                continue;",
            "            }",
            "",
            "            /* Highlight hovered item */",
            "            if (selectable_idx == menu_hover_item) {",
            f"                SDL_SetRenderDrawColor(r, {hl[0]}, {hl[1]}, {hl[2]}, 200);",
            "                SDL_FRect item_bg = {(float)(md->bar_x + 1), (float)iy, (float)(dd_w - 2), (float)item_h};",
            "                SDL_RenderFillRect(r, &item_bg);",
            "            }",
            "",
            "            /* Item label */",
            "            int ix = md->bar_x + 8;",
            f"            draw_text_scaled(r, ix, iy + 2, mi->label, MENU_FONT_SCALE,",
            f"                {tc[0]}, {tc[1]}, {tc[2]}, {tc[3]});",
            "",
            "            /* Type-specific value display */",
            "            char vbuf[64];",
            "            if (mi->type == MTYPE_TOGGLE) {",
        ]

        # Render toggle values
        lines += [
            "                bool val = false;",
        ]
        # Generate toggle value lookup
        for ti, tg in enumerate(toggles):
            prefix = "if" if ti == 0 else "else if"
            if tg['config_key']:
                lines.append(f"                {prefix} (mi->data_index == {ti}) {{ val = config.{tg['config_key']}; }}")
            elif tg['chip'] and tg['field']:
                lines.append(f"                {prefix} (mi->data_index == {ti}) {{ val = menu_sys->{tg['chip']}.{tg['field']}; }}")
        lines += [
            '                snprintf(vbuf, sizeof(vbuf), "%s", val ? "[ON]" : "[OFF]");',
            f"                draw_text_scaled(r, md->bar_x + dd_w - text_width_scaled(vbuf, MENU_FONT_SCALE) - 8,",
            f"                    iy + 2, vbuf, MENU_FONT_SCALE, {tc[0]}, {tc[1]}, {tc[2]}, {tc[3]});",
            "            } else if (mi->type == MTYPE_SLIDER) {",
        ]

        # Render slider values
        lines += [
            "                int val = 0;",
        ]
        for si, sl in enumerate(sliders):
            prefix = "if" if si == 0 else "else if"
            lines.append(f"                {prefix} (mi->data_index == {si}) {{ val = config.{sl['config_key']}; }}")
        lines += [
            '                snprintf(vbuf, sizeof(vbuf), "< %d >", val);',
            f"                draw_text_scaled(r, md->bar_x + dd_w - text_width_scaled(vbuf, MENU_FONT_SCALE) - 8,",
            f"                    iy + 2, vbuf, MENU_FONT_SCALE, {tc[0]}, {tc[1]}, {tc[2]}, {tc[3]});",
            "            } else if (mi->type == MTYPE_KEYBIND) {",
        ]

        # Render keybind values
        lines += [
            "                int bidx = -1;",
        ]
        for ki, kb in enumerate(keybinds):
            prefix = "if" if ki == 0 else "else if"
            lines.append(f"                {prefix} (mi->data_index == {ki}) {{ bidx = {kb['binding_index']}; }}")
        lines += [
            "                if (menu_rebinding && selectable_idx == menu_hover_item) {",
            '                    snprintf(vbuf, sizeof(vbuf), "[...]");',
            "                } else if (bidx >= 0) {",
            "                    const char* kn = SDL_GetScancodeName(config.key_bindings[bidx]);",
            '                    snprintf(vbuf, sizeof(vbuf), "[%s]", kn ? kn : "?");',
            "                } else {",
            '                    snprintf(vbuf, sizeof(vbuf), "[?]");',
            "                }",
            f"                draw_text_scaled(r, md->bar_x + dd_w - text_width_scaled(vbuf, MENU_FONT_SCALE) - 8,",
            f"                    iy + 2, vbuf, MENU_FONT_SCALE, {tc[0]}, {tc[1]}, {tc[2]}, {tc[3]});",
            "            }",
            "",
            "            selectable_idx++;",
            "            iy += item_h;",
            "        }",
            "    }",
            "",
            "    SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_NONE);",
            "}",
            "",
        ]

        # --- menu_bar_handle_event ---
        lines += [
            "static bool menu_bar_handle_event(SDL_Event* event) {",
            "",
            "    /* Key rebind mode: capture next keypress */",
            "    if (menu_rebinding) {",
            "        if (event->type == SDL_EVENT_KEY_DOWN) {",
            "            if (event->key.scancode == SDL_SCANCODE_ESCAPE) {",
            "                menu_rebinding = false;",
            "            } else {",
            "                config.key_bindings[menu_rebind_idx] = event->key.scancode;",
            "                menu_rebinding = false;",
            "            }",
            "            return true;",
            "        }",
            "        return (event->type == SDL_EVENT_MOUSE_MOTION ||",
            "                event->type == SDL_EVENT_MOUSE_BUTTON_DOWN);",
            "    }",
            "",
            "    /* Mouse motion: update hover states */",
            "    if (event->type == SDL_EVENT_MOUSE_MOTION) {",
            "        float mx = event->motion.x;",
            "        float my = event->motion.y;",
            "",
            "        /* Check bar hover */",
            "        int old_hover_bar = menu_hover_bar;",
            "        menu_hover_bar = -1;",
            "        if (my >= 0 && my < MENU_BAR_HEIGHT) {",
            "            for (int i = 0; i < N_MENUS; i++) {",
            "                if (mx >= menus[i].bar_x && mx < menus[i].bar_x + menus[i].bar_w) {",
            "                    menu_hover_bar = i;",
            "                    break;",
            "                }",
            "            }",
            "        }",
            "",
            "        /* If a dropdown is open and we hover a different bar item, switch */",
            "        if (menu_open >= 0 && menu_hover_bar >= 0 && menu_hover_bar != menu_open) {",
            "            menu_open = menu_hover_bar;",
            "            menu_hover_item = -1;",
            "        }",
            "",
            "        /* Check dropdown item hover */",
            "        if (menu_open >= 0 && menu_open < N_MENUS) {",
            "            menu_def_t* md = &menus[menu_open];",
            "            int item_h = MENU_CHAR_H + 4;",
            "            int sep_h = 6;",
            "            /* Calculate dropdown width (must match render) */",
            "            int dd_w = 0;",
            "            for (int j = 0; j < md->item_count; j++) {",
            "                menu_item_t* mj = &items[md->item_start + j];",
            "                if (mj->type == MTYPE_SEPARATOR) continue;",
            "                int lw = text_width_scaled(mj->label, MENU_FONT_SCALE) + 32;",
            "                if (mj->type == MTYPE_TOGGLE) lw += 60;",
            "                if (mj->type == MTYPE_SLIDER) lw += 100;",
            "                if (mj->type == MTYPE_KEYBIND) lw += 120;",
            "                if (lw > dd_w) dd_w = lw;",
            "            }",
            "            if (dd_w < 120) dd_w = 120;",
            "            int iy = MENU_BAR_HEIGHT + 4;",
            "            menu_hover_item = -1;",
            "            int sel_idx = 0;",
            "            for (int i = 0; i < md->item_count; i++) {",
            "                menu_item_t* mi = &items[md->item_start + i];",
            "                if (mi->type == MTYPE_SEPARATOR) { iy += sep_h; continue; }",
            "                if (mx >= md->bar_x && mx < md->bar_x + dd_w &&",
            "                    my >= iy && my < iy + item_h) {",
            "                    menu_hover_item = sel_idx;",
            "                }",
            "                sel_idx++;",
            "                iy += item_h;",
            "            }",
            "        }",
            "",
            "        return (menu_open >= 0);  /* consume motion if dropdown open */",
            "    }",
            "",
            "    /* Mouse click */",
            "    if (event->type == SDL_EVENT_MOUSE_BUTTON_DOWN &&",
            "        event->button.button == SDL_BUTTON_LEFT) {",
            "        float mx = event->button.x;",
            "        float my = event->button.y;",
            "",
            "        /* Click on menu bar */",
            "        if (my >= 0 && my < MENU_BAR_HEIGHT) {",
            "            for (int i = 0; i < N_MENUS; i++) {",
            "                if (mx >= menus[i].bar_x && mx < menus[i].bar_x + menus[i].bar_w) {",
            "                    if (menu_open == i) {",
            "                        menu_open = -1;  /* toggle off */",
            "                    } else {",
            "                        menu_open = i;",
            "                        menu_hover_item = -1;",
            "                    }",
            "                    return true;",
            "                }",
            "            }",
            "            return true;  /* clicked on bar but not on a menu */",
            "        }",
            "",
            "        /* Click in dropdown area */",
            "        if (menu_open >= 0 && menu_hover_item >= 0) {",
            "            menu_def_t* md = &menus[menu_open];",
            "            /* Find the actual item at this selectable index */",
            "            int sel_idx = 0;",
            "            for (int i = 0; i < md->item_count; i++) {",
            "                menu_item_t* mi = &items[md->item_start + i];",
            "                if (mi->type == MTYPE_SEPARATOR) continue;",
            "                if (sel_idx == menu_hover_item) {",
            "                    /* Execute item */",
        ]

        # Generate action dispatch
        lines += [
            "                    if (mi->type == MTYPE_ACTION) {",
            "                        switch (mi->data_index) {",
        ]
        for ai, act in enumerate(actions):
            code = act['code'].strip().rstrip(';')
            lines.append(f"                        case {ai}: {{ {code}; }} break;")
        lines += [
            "                        }",
            "                        menu_open = -1;",
            "                    } else if (mi->type == MTYPE_TOGGLE) {",
            "                        switch (mi->data_index) {",
        ]
        for ti, tg in enumerate(toggles):
            if tg['config_key']:
                lines.append(f"                        case {ti}: config.{tg['config_key']} = !config.{tg['config_key']}; break;")
            elif tg['chip'] and tg['field']:
                lines.append(f"                        case {ti}: menu_sys->{tg['chip']}.{tg['field']} = !menu_sys->{tg['chip']}.{tg['field']}; break;")
        lines += [
            "                        }",
            "                        menu_apply_config();",
            "                    } else if (mi->type == MTYPE_SLIDER) {",
            "                        /* Click on \"<\" side decreases, \">\" side increases */",
            "                        menu_def_t* smd = &menus[menu_open];",
            "                        /* Compute dropdown width to find midpoint */",
            "                        int sl_dd_w = 0;",
            "                        for (int k = 0; k < smd->item_count; k++) {",
            "                            menu_item_t* mk = &items[smd->item_start + k];",
            "                            if (mk->type == MTYPE_SEPARATOR) continue;",
            "                            int lw = text_width_scaled(mk->label, MENU_FONT_SCALE) + 32;",
            "                            if (mk->type == MTYPE_TOGGLE) lw += 60;",
            "                            if (mk->type == MTYPE_SLIDER) lw += 100;",
            "                            if (mk->type == MTYPE_KEYBIND) lw += 120;",
            "                            if (lw > sl_dd_w) sl_dd_w = lw;",
            "                        }",
            "                        if (sl_dd_w < 120) sl_dd_w = 120;",
            "                        float mid_x = smd->bar_x + sl_dd_w / 2.0f;",
            "                        int delta = (mx < mid_x) ? -1 : 1;",
            "                        switch (mi->data_index) {",
        ]
        for si, sl in enumerate(sliders):
            lines.append(f"                        case {si}: "
                         f"config.{sl['config_key']} += delta * {sl['step']}; "
                         f"if (config.{sl['config_key']} < {sl['min']}) config.{sl['config_key']} = {sl['min']}; "
                         f"if (config.{sl['config_key']} > {sl['max']}) config.{sl['config_key']} = {sl['max']}; break;")
        lines += [
            "                        }",
            "                        menu_apply_config();",
            "                    } else if (mi->type == MTYPE_KEYBIND) {",
            "                        switch (mi->data_index) {",
        ]
        for ki, kb in enumerate(keybinds):
            lines.append(f"                        case {ki}: menu_rebind_idx = {kb['binding_index']}; menu_rebinding = true; break;")
        lines += [
            "                        }",
            "                    }",
            "                    break;",
            "                }",
            "                sel_idx++;",
            "            }",
            "            return true;",
            "        }",
            "",
            "        /* Click outside dropdown: close it */",
            "        if (menu_open >= 0) {",
            "            menu_open = -1;",
            "            return true;",
            "        }",
            "    }",
            "",
            "    return false;",
            "}",
        ]
        return '\n'.join(lines)

    # --- 11. Menu apply config (menu only) ---

    def _gen_menu_apply(self) -> str:
        """Generate menu_apply_config() for applying runtime config changes."""
        config_vars = self._collect_config_vars()
        config_keys = {cv['key'] for cv in config_vars}

        lines = [
            "/* ================================================================= */",
            "/* Apply Config Changes                                               */",
            "/* ================================================================= */",
            "",
            "static void menu_apply_config(void) {",
        ]
        # Apply display_scale if it exists as a config var
        if 'display_scale' in config_keys:
            lines += [
                "    int new_w = NATIVE_W * config.display_scale;",
                "    int new_h = NATIVE_H * config.display_scale + MENU_BAR_HEIGHT;",
                "    SDL_SetWindowSize(sdl_window, new_w, new_h);",
                "    win_w = new_w;",
                "    win_h = new_h;",
            ]
        # Apply vsync if it exists as a config var
        if 'vsync' in config_keys:
            lines.append("    SDL_SetRenderVSync(sdl_renderer, config.vsync ? 1 : 0);")
        lines.append("}")
        return '\n'.join(lines)

    # --- 12. render_frame() implementation ---

    def _gen_render_impl(self) -> str:
        if not self.host._render_extern:
            return ""

        extern_name = self.host._render_extern
        sig = self._find_extern_sig(extern_name)
        if not sig:
            sig = f"void {extern_name}(uint8_t* framebuffer, int width, int height)"

        lines = [f"{sig} {{"]

        if self.host.palette:
            pal = self.host.palette
            mask = len(pal) - 1
            if (len(pal) & (len(pal) - 1)) == 0 and len(pal) > 0:
                idx_expr = f"framebuffer[i] & 0x{mask:02X}"
            else:
                idx_expr = f"framebuffer[i] % {len(pal)}"
            lines.append(f"    for (int i = 0; i < width * height; i++) {{")
            lines.append(f"        sdl_rgba_buffer[i] = {pal.name}_lut[{idx_expr}];")
            lines.append(f"    }}")
        else:
            lines.append(f"    for (int i = 0; i < width * height; i++) {{")
            lines.append(f"        uint8_t v = framebuffer[i];")
            lines.append(f"        sdl_rgba_buffer[i] = (v << 24) | (v << 16) | (v << 8) | 0xFF;")
            lines.append(f"    }}")

        lines.append(f"    SDL_UpdateTexture(sdl_texture, NULL, sdl_rgba_buffer, width * sizeof(uint32_t));")

        if self._has_menu_bar():
            # Compositing pipeline: clear, game texture, then menu bar ON TOP
            lines.append(f"    SDL_SetRenderDrawColor(sdl_renderer, 30, 30, 30, 255);")
            lines.append(f"    SDL_RenderClear(sdl_renderer);")
            lines.append(f"    /* Scale game to fill window below menu bar, preserving aspect ratio */")
            lines.append(f"    int game_area_w = win_w;")
            lines.append(f"    int game_area_h = win_h - MENU_BAR_HEIGHT;")
            lines.append(f"    float scale_x = (float)game_area_w / (float)NATIVE_W;")
            lines.append(f"    float scale_y = (float)game_area_h / (float)NATIVE_H;")
            lines.append(f"    float scale = scale_x < scale_y ? scale_x : scale_y;")
            lines.append(f"    float gw = NATIVE_W * scale;")
            lines.append(f"    float gh = NATIVE_H * scale;")
            lines.append(f"    float gx = (game_area_w - gw) / 2.0f;")
            lines.append(f"    float gy = MENU_BAR_HEIGHT + (game_area_h - gh) / 2.0f;")
            lines.append(f"    SDL_FRect dst = {{gx, gy, gw, gh}};")
            lines.append(f"    SDL_RenderTexture(sdl_renderer, sdl_texture, NULL, &dst);")
            lines.append(f"    /* Menu bar + dropdown rendered LAST so dropdowns appear on top */")
            lines.append(f"    menu_bar_render(sdl_renderer, win_w);")
        else:
            lines.append(f"    SDL_RenderClear(sdl_renderer);")
            lines.append(f"    SDL_RenderTexture(sdl_renderer, sdl_texture, NULL, NULL);")

        lines.append(f"    SDL_RenderPresent(sdl_renderer);")
        lines.append(f"}}")
        return '\n'.join(lines)

    # --- 13. audio_push() implementation ---

    def _gen_audio_impl(self) -> str:
        if not self.host._audio_extern:
            return ""

        extern_name = self.host._audio_extern
        sig = self._find_extern_sig(extern_name)
        if not sig:
            sig = f"void {extern_name}(int16_t* samples, int count)"

        lines = [f"{sig} {{"]
        lines.append(f"    if (sdl_audio_stream) {{")

        # Volume scaling (menu only)
        if self._has_menu_bar():
            lines.append(f"        if (config.volume < 100) {{")
            lines.append(f"            for (int i = 0; i < count; i++)")
            lines.append(f"                samples[i] = (int16_t)((int32_t)samples[i] * config.volume / 100);")
            lines.append(f"        }}")

        lines.append(f"        SDL_PutAudioStreamData(sdl_audio_stream, samples,")
        lines.append(f"            count * sizeof(int16_t));")
        lines.append(f"    }}")
        lines.append(f"}}")
        return '\n'.join(lines)

    # --- 14. poll_input() implementation ---

    def _gen_input_impl(self) -> str:
        if not self.host._input_extern:
            return ""

        extern_name = self.host._input_extern
        sig = self._find_extern_sig(extern_name)
        if not sig:
            sig = f"void {extern_name}(void* opaque_sys)"

        param_name = "sys"
        if "void*" in sig:
            import re
            m = re.search(r'void\*\s+(\w+)', sig)
            if m:
                param_name = m.group(1)
            cast_sig = sig.replace(f"void* {param_name}", f"void* _opaque")
            lines = [f"{cast_sig} {{"]
            lines.append(f"    {self.st}* {param_name} = ({self.st}*)_opaque;")
        else:
            lines = [f"{sig} {{"]

        lines.append(f"    const bool* keys = SDL_GetKeyboardState(NULL);")

        # Group bindings by (chip_name, field_name)
        field_groups = {}
        for i, kb in enumerate(self.host.input.bindings):
            key = (kb.chip_name, kb.field_name)
            if key not in field_groups:
                field_groups[key] = []
            field_groups[key].append((i, kb))

        # Reset all bound fields
        for (chip, field), bindings in field_groups.items():
            if bindings[0][1].active_low:
                lines.append(f"    sys->{chip}.{field} = 0xFF;")
            else:
                lines.append(f"    sys->{chip}.{field} = 0x00;")

        # Key checks
        for (chip, field), bindings in field_groups.items():
            for idx, kb in bindings:
                if self._has_menu_bar():
                    key_expr = f"config.key_bindings[{idx}]"
                else:
                    key_expr = kb.scancode
                if kb.active_low:
                    lines.append(
                        f"    if (keys[{key_expr}]) "
                        f"sys->{chip}.{field} &= ~(1 << {kb.bit_index});"
                    )
                else:
                    lines.append(
                        f"    if (keys[{key_expr}]) "
                        f"sys->{chip}.{field} |= (1 << {kb.bit_index});"
                    )

        lines.append(f"}}")
        return '\n'.join(lines)

    # --- 15. main() ---

    def _gen_main(self) -> str:
        d = self.host.display
        a = self.host.audio
        t = self.host.timing
        has_menu = self._has_menu_bar()

        lines = ["int main(int argc, char** argv) {"]

        # Config initialization (menu only)
        if has_menu:
            lines.append(f"    config_set_defaults();")
            lines.append(f"")

        # SDL initialization
        init_flags = []
        if d:
            init_flags.append("SDL_INIT_VIDEO")
        if a:
            init_flags.append("SDL_INIT_AUDIO")
        flags_str = " | ".join(init_flags) if init_flags else "0"

        lines.append(f"    if (!SDL_Init({flags_str})) {{")
        lines.append(f'        fprintf(stderr, "SDL_Init failed: %s\\n", SDL_GetError());')
        lines.append(f"        return 1;")
        lines.append(f"    }}")

        # Window and renderer
        if d:
            init_win_w = d.width * d.scale
            init_win_h = d.height * d.scale
            if has_menu:
                init_win_h += self.host._menu_bar.bar_height
                lines.append(f"")
                lines.append(f"    win_w = {init_win_w};")
                lines.append(f"    win_h = {init_win_h};")
                lines.append(f'    sdl_window = SDL_CreateWindow("{d.title}", win_w, win_h, SDL_WINDOW_RESIZABLE);')
            else:
                lines.append(f"")
                lines.append(f'    sdl_window = SDL_CreateWindow("{d.title}", {init_win_w}, {init_win_h}, SDL_WINDOW_RESIZABLE);')
            lines.append(f"    if (!sdl_window) {{")
            lines.append(f'        fprintf(stderr, "SDL_CreateWindow failed: %s\\n", SDL_GetError());')
            lines.append(f"        SDL_Quit();")
            lines.append(f"        return 1;")
            lines.append(f"    }}")
            lines.append(f"")
            lines.append(f"    sdl_renderer = SDL_CreateRenderer(sdl_window, NULL);")
            config_keys = {cv['key'] for cv in self._collect_config_vars()} if has_menu else set()
            if has_menu and 'vsync' in config_keys:
                lines.append(f"    SDL_SetRenderVSync(sdl_renderer, config.vsync ? 1 : 0);")
            elif has_menu:
                vsync_val = 1 if d.vsync else 0
                lines.append(f"    SDL_SetRenderVSync(sdl_renderer, {vsync_val});")
            else:
                if d.vsync:
                    lines.append(f"    SDL_SetRenderVSync(sdl_renderer, 1);")
                lines.append(f"    SDL_SetRenderLogicalPresentation(sdl_renderer, {d.width}, {d.height},")
                lines.append(f"        SDL_LOGICAL_PRESENTATION_LETTERBOX);")
            lines.append(f"")
            lines.append(f"    sdl_texture = SDL_CreateTexture(sdl_renderer,")
            lines.append(f"        SDL_PIXELFORMAT_RGBA8888, SDL_TEXTUREACCESS_STREAMING,")
            lines.append(f"        {d.width}, {d.height});")
            lines.append(f"    SDL_SetTextureScaleMode(sdl_texture, SDL_SCALEMODE_NEAREST);")

        # Audio device
        if a:
            lines.append(f"")
            lines.append(f"    {{")
            lines.append(f"        SDL_AudioSpec audio_spec;")
            lines.append(f"        audio_spec.freq = {a.sample_rate};")
            lines.append(f"        audio_spec.format = SDL_AUDIO_S16;")
            lines.append(f"        audio_spec.channels = {a.channels};")
            lines.append(f"        sdl_audio_stream = SDL_OpenAudioDeviceStream(")
            lines.append(f"            SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK, &audio_spec, NULL, NULL);")
            lines.append(f"        if (sdl_audio_stream) {{")
            lines.append(f"            SDL_ResumeAudioStreamDevice(sdl_audio_stream);")
            lines.append(f"        }}")
            lines.append(f"    }}")

        # Menu bar init
        if has_menu:
            lines.append(f"")
            lines.append(f"    menu_bar_init();")

        # Config load from file
        if has_menu:
            config_path = self.host._config_path
            lines.append(f"")
            lines.append(f'    if (config_load("{config_path}")) {{')
            lines.append(f'        printf("Loaded config: {config_path}\\n");')
            lines.append(f"        menu_apply_config();")
            lines.append(f"    }}")

        # Board initialization
        lines.append(f"")
        lines.append(f"    {self.st} sys;")
        lines.append(f"    {self.sn}_init(&sys);")

        # Set global menu_sys pointer (for chip field toggles)
        if has_menu:
            lines.append(f"    menu_sys = &sys;")

        # Post-init code
        if self.host._post_init_code:
            for line in self._indent_raw_c(self.host._post_init_code, "    "):
                lines.append(line)

        # ROM loading
        if self.host._rom_loader_code:
            lines.append(f"")
            for line in self._indent_raw_c(self.host._rom_loader_code, "    "):
                lines.append(line)
        elif self.host._rom_chip:
            chip = self.host._rom_chip
            field = self.host._rom_field
            size_field = self.host._rom_size_field
            lines.append(f"")
            lines.append(f"    if (argc > 1) {{")
            lines.append(f'        FILE* f = fopen(argv[1], "rb");')
            lines.append(f"        if (f) {{")
            lines.append(f"            fseek(f, 0, SEEK_END);")
            lines.append(f"            long size = ftell(f);")
            lines.append(f"            fseek(f, 0, SEEK_SET);")
            lines.append(f"            sys.{chip}.{field} = (uint8_t*)malloc(size);")
            lines.append(f"            sys.{chip}.{size_field} = (uint32_t)size;")
            lines.append(f"            fread(sys.{chip}.{field}, 1, size, f);")
            lines.append(f"            fclose(f);")
            lines.append(f"        }} else {{")
            lines.append(f'            fprintf(stderr, "Failed to open ROM: %s\\n", argv[1]);')
            lines.append(f"            return 1;")
            lines.append(f"        }}")
            lines.append(f"    }}")

        # Main loop
        cpu_name = self.cpu_chip_name
        cpf = t.cycles_per_frame if t else 70224
        fb_chip = self.host._render_fb_chip or "ppu"
        fb_field = self.host._render_fb_field or "framebuffer"
        render_fn = self.host._render_extern or "render_frame"

        lines.append(f"")
        lines.append(f"    while (sdl_running) {{")

        # Event polling
        lines.append(f"        SDL_Event event;")
        lines.append(f"        while (SDL_PollEvent(&event)) {{")
        lines.append(f"            if (event.type == SDL_EVENT_QUIT) sdl_running = false;")

        if has_menu:
            # Track window resize
            lines.append(f"            if (event.type == SDL_EVENT_WINDOW_RESIZED) {{")
            lines.append(f"                win_w = event.window.data1;")
            lines.append(f"                win_h = event.window.data2;")
            lines.append(f"            }}")
            # Menu bar gets first crack at events
            lines.append(f"            if (menu_bar_handle_event(&event)) continue;")
        # Escape to quit
        lines.append(f"            if (event.type == SDL_EVENT_KEY_DOWN &&")
        lines.append(f"                event.key.scancode == SDL_SCANCODE_ESCAPE) sdl_running = false;")
        lines.append(f"        }}")

        if has_menu:
            # Check for pending file dialog ROM load
            has_file_dialog = any(
                item.action_code and 'menu_open_file_dialog' in item.action_code
                for menu in self.host._menus for item in menu.items
            )
            if has_file_dialog:
                lines.append(f"")
                lines.append(f"        if (pending_rom_load) {{")
                lines.append(f"            pending_rom_load = false;")
                lines.append(f"            /* TODO: Implement ROM reload from pending_rom_path */")
                lines.append(f"        }}")

        # Input and frame stepping
        lines.append(f"")
        if has_menu:
            # Input only when not rebinding
            if self.host._input_extern:
                lines.append(f"        if (!menu_rebinding) {self.host._input_extern}(&sys);")
        else:
            if self.host._input_extern:
                lines.append(f"        {self.host._input_extern}(&sys);")

        lines.append(f"")
        lines.append(f"        uint64_t frame_start = sys.{cpu_name}.cycle_count;")
        lines.append(f"        while (sys.{cpu_name}.cycle_count - frame_start < {cpf}) {{")
        lines.append(f"            {self.sn}_step(&sys);")
        lines.append(f"        }}")

        lines.append(f"    }}")

        # Cleanup
        lines.append(f"")
        if a:
            lines.append(f"    if (sdl_audio_stream) SDL_DestroyAudioStream(sdl_audio_stream);")
        if d:
            lines.append(f"    SDL_DestroyTexture(sdl_texture);")
            lines.append(f"    SDL_DestroyRenderer(sdl_renderer);")
            lines.append(f"    SDL_DestroyWindow(sdl_window);")
        lines.append(f"    SDL_Quit();")

        if self.host._rom_chip and self.host._rom_field:
            chip = self.host._rom_chip
            field = self.host._rom_field
            lines.append(f"    if (sys.{chip}.{field}) free(sys.{chip}.{field});")

        lines.append(f"    return 0;")
        lines.append(f"}}")
        return '\n'.join(lines)

    # --- utility ---

    def _find_extern_sig(self, name: str) -> str:
        """Find the extern function signature string from the board."""
        for ef in self.board.extern_funcs:
            if isinstance(ef, dict) and ef['name'] == name:
                params_str = ", ".join(
                    f"{pt} {pn}" for pn, pt in ef['params']
                ) if ef['params'] else "void"
                return f"{ef['returns']} {name}({params_str})"
            elif isinstance(ef, str) and ef == name:
                return f"void {name}(void)"
        return ""

    @staticmethod
    def _indent_raw_c(code: str, base_indent: str = "    ") -> list:
        """Dedent raw C code and re-indent with base_indent."""
        import textwrap
        dedented = textwrap.dedent(code).strip()
        result = []
        for line in dedented.splitlines():
            if line.strip():
                result.append(f"{base_indent}{line}")
            else:
                result.append("")
        return result
