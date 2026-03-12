"""
host.py -- Declarative SDL3 host definitions for proto-gen boards.

Define display, audio, input, and frame timing for generated emulators.
Pairs with host_codegen.py to generate C host code using SDL3.
"""

import dataclasses
import enum
from typing import Dict, List, Optional, Tuple

from .hardware import Board


# ===================================================================
# Display
# ===================================================================

@dataclasses.dataclass
class DisplayConfig:
    """Window and rendering configuration."""
    width: int                    # Native framebuffer width (e.g., 160 for GB)
    height: int                   # Native framebuffer height (e.g., 144 for GB)
    scale: int = 4                # Window = width*scale x height*scale
    title: str = "proto-gen"      # Window title
    vsync: bool = True            # VSync via SDL_SetRenderVSync


# ===================================================================
# Palette
# ===================================================================

@dataclasses.dataclass
class PaletteEntry:
    """A single palette index mapped to an RGBA color."""
    index: int
    r: int
    g: int
    b: int
    a: int = 255


class PaletteMap:
    """Palette lookup table for converting indexed framebuffers to RGBA."""

    def __init__(self, name: str = "palette"):
        self.name = name
        self.entries: List[PaletteEntry] = []

    def add(self, index: int, r: int, g: int, b: int, a: int = 255):
        """Add a palette entry mapping index -> RGBA."""
        self.entries.append(PaletteEntry(index, r, g, b, a))
        return self

    def add_grayscale(self, count: int):
        """Add evenly-spaced grayscale entries (0=white, count-1=black)."""
        for i in range(count):
            v = 255 - (i * 255 // (count - 1)) if count > 1 else 255
            self.entries.append(PaletteEntry(i, v, v, v))
        return self

    def __len__(self):
        return len(self.entries)


# ===================================================================
# Audio
# ===================================================================

@dataclasses.dataclass
class AudioConfig:
    """Audio output configuration."""
    sample_rate: int = 48000      # SDL audio device sample rate
    channels: int = 2             # 1=mono, 2=stereo
    buffer_size: int = 2048       # Buffer size in samples


# ===================================================================
# Input
# ===================================================================

@dataclasses.dataclass
class KeyBinding:
    """Maps an SDL scancode to a chip state field bit."""
    scancode: str           # SDL scancode (e.g., "SDL_SCANCODE_Z")
    chip_name: str          # Target chip (e.g., "joypad")
    field_name: str         # State field (e.g., "button_state")
    bit_index: int          # Bit position to clear/set
    active_low: bool = True # True = pressed clears the bit
    label: str = ""         # Human-readable label for menu (e.g., "A Button")


class InputMapping:
    """Collection of keyboard-to-emulator input bindings."""

    def __init__(self):
        self.bindings: List[KeyBinding] = []

    def bind(self, scancode: str, chip_name: str, field_name: str,
             bit_index: int, active_low: bool = True, label: str = ""):
        """Add a key binding."""
        self.bindings.append(KeyBinding(
            scancode=scancode, chip_name=chip_name,
            field_name=field_name, bit_index=bit_index,
            active_low=active_low, label=label,
        ))
        return self


# ===================================================================
# Frame Timing
# ===================================================================

@dataclasses.dataclass
class FrameTiming:
    """Frame timing configuration."""
    cycles_per_frame: int         # CPU cycles per frame (e.g., 70224 for GB)
    cpu_clock_hz: int = 0         # Optional: CPU clock (can be derived from board)

    @property
    def target_fps(self) -> float:
        if self.cpu_clock_hz > 0:
            return self.cpu_clock_hz / self.cycles_per_frame
        return 0.0


# ===================================================================
# Menu Bar System -- Declarative menu tree
# ===================================================================

class MenuItemType(enum.Enum):
    """Types of menu items in a dropdown."""
    Action = "action"         # Click to execute C code
    Toggle = "toggle"         # Bool on/off (config var or chip.field)
    Slider = "slider"         # Int range with min/max/step
    Separator = "separator"   # Visual divider line
    KeyBind = "keybind"       # Key rebinding entry


@dataclasses.dataclass
class MenuItem:
    """A single item in a menu dropdown."""
    label: str
    item_type: MenuItemType
    # Action: raw C code to execute on click
    action_code: Optional[str] = None
    # Toggle: references
    toggle_config_key: Optional[str] = None   # Config var (e.g., "vsync")
    toggle_chip: Optional[str] = None         # Chip.field for runtime toggle
    toggle_field: Optional[str] = None
    # Slider: int range with config var
    slider_config_key: Optional[str] = None   # Config var (e.g., "volume")
    slider_min: int = 0
    slider_max: int = 100
    slider_step: int = 1
    # KeyBind: index into key_bindings array
    keybind_index: Optional[int] = None


class Menu:
    """A top-level menu category (e.g., 'File', 'Display').

    Usage:
        menu = Menu("Debug")
        menu.add_toggle("Show BG", chip="ppu", field="show_bg")
        menu.add_action("Reset", code="board_init(menu_sys);")
    """

    def __init__(self, label: str):
        self.label = label
        self.items: List[MenuItem] = []

    def add_action(self, label: str, code: str) -> 'Menu':
        """Add a clickable action item with raw C code."""
        self.items.append(MenuItem(
            label=label,
            item_type=MenuItemType.Action,
            action_code=code,
        ))
        return self

    def add_toggle(self, label: str,
                   config_key: Optional[str] = None,
                   chip: Optional[str] = None,
                   field: Optional[str] = None) -> 'Menu':
        """Add a toggle (bool on/off) item.

        Either config_key (for host config like 'vsync')
        or chip+field (for runtime state like ppu.show_bg).
        """
        self.items.append(MenuItem(
            label=label,
            item_type=MenuItemType.Toggle,
            toggle_config_key=config_key,
            toggle_chip=chip,
            toggle_field=field,
        ))
        return self

    def add_slider(self, label: str, config_key: str,
                   min_val: int = 0, max_val: int = 100,
                   step: int = 1) -> 'Menu':
        """Add a slider (int range) item."""
        self.items.append(MenuItem(
            label=label,
            item_type=MenuItemType.Slider,
            slider_config_key=config_key,
            slider_min=min_val,
            slider_max=max_val,
            slider_step=step,
        ))
        return self

    def add_separator(self) -> 'Menu':
        """Add a visual separator line."""
        self.items.append(MenuItem(
            label="",
            item_type=MenuItemType.Separator,
        ))
        return self

    def add_keybind(self, label: str, binding_index: int) -> 'Menu':
        """Add a key rebinding item (shows current key, click to rebind)."""
        self.items.append(MenuItem(
            label=label,
            item_type=MenuItemType.KeyBind,
            keybind_index=binding_index,
        ))
        return self


@dataclasses.dataclass
class MenuBarConfig:
    """Menu bar appearance and layout configuration."""
    bar_height: int = 24          # Menu bar height in window pixels
    font_scale: int = 2           # Bitmap font scale (2 = 16px chars)
    bg_color: Tuple[int, ...] = (40, 40, 40, 255)
    text_color: Tuple[int, ...] = (220, 220, 220, 255)
    highlight_color: Tuple[int, ...] = (60, 60, 120, 255)
    active_color: Tuple[int, ...] = (80, 80, 160, 255)
    separator_color: Tuple[int, ...] = (80, 80, 80, 255)
    dropdown_bg: Tuple[int, ...] = (50, 50, 50, 240)


# ===================================================================
# SDLHost -- main entry point
# ===================================================================

class SDLHost:
    """Declarative SDL3 host definition for a proto-gen board.

    Usage:
        host = SDLHost(board)
        host.set_display(160, 144, scale=4, title="Game Boy")
        host.set_audio(sample_rate=48000)
        host.set_timing(cycles_per_frame=70224)
        host.set_palette(palette)
        host.map_key("SDL_SCANCODE_Z", "joypad", "button_state", 0, label="A")
        host.bind_render("render_frame", "ppu", "framebuffer")
        host.enable_menu()
        host.add_default_menus()
    """

    def __init__(self, board: Board, name: str = ""):
        self.board = board
        self.name = name or board.name

        # Configuration
        self.display: Optional[DisplayConfig] = None
        self.audio: Optional[AudioConfig] = None
        self.palette: Optional[PaletteMap] = None
        self.input: InputMapping = InputMapping()
        self.timing: Optional[FrameTiming] = None

        # Render hook binding
        self._render_extern: Optional[str] = None
        self._render_fb_chip: Optional[str] = None
        self._render_fb_field: Optional[str] = None
        self._frame_flag_chip: Optional[str] = None
        self._frame_flag_field: Optional[str] = None

        # Audio hook binding
        self._audio_extern: Optional[str] = None

        # Input hook binding
        self._input_extern: Optional[str] = None

        # ROM loading
        self._rom_chip: Optional[str] = None
        self._rom_field: Optional[str] = None
        self._rom_size_field: Optional[str] = None
        self._rom_loader_code: Optional[str] = None

        # Raw C injection points
        self._post_init_code: Optional[str] = None

        # Menu bar system
        self._menu_bar: Optional[MenuBarConfig] = None
        self._menus: List[Menu] = []
        self._file_filters: List[Tuple[str, str]] = []
        self._config_path: str = "config.json"

    # --- Display ---

    def set_display(self, width: int, height: int, scale: int = 4,
                    title: str = "proto-gen",
                    vsync: bool = True) -> 'SDLHost':
        """Configure window and rendering."""
        self.display = DisplayConfig(
            width=width, height=height, scale=scale,
            title=title, vsync=vsync,
        )
        return self

    # --- Audio ---

    def set_audio(self, sample_rate: int = 48000, channels: int = 2,
                  buffer_size: int = 2048) -> 'SDLHost':
        """Configure audio output."""
        self.audio = AudioConfig(
            sample_rate=sample_rate, channels=channels,
            buffer_size=buffer_size,
        )
        return self

    # --- Palette ---

    def set_palette(self, palette: PaletteMap) -> 'SDLHost':
        """Set the palette for framebuffer-to-RGBA conversion."""
        self.palette = palette
        return self

    # --- Timing ---

    def set_timing(self, cycles_per_frame: int) -> 'SDLHost':
        """Set frame timing in CPU cycles per frame."""
        cpu_hz = 0
        if self.board.master_clock:
            cpu_hz = self.board.master_clock.frequency_hz
        self.timing = FrameTiming(
            cycles_per_frame=cycles_per_frame,
            cpu_clock_hz=cpu_hz,
        )
        return self

    # --- Input ---

    def map_key(self, scancode: str, chip_name: str, field_name: str,
                bit_index: int, active_low: bool = True,
                label: str = "") -> 'SDLHost':
        """Map an SDL scancode to a chip state field bit."""
        self.input.bind(scancode, chip_name, field_name,
                        bit_index, active_low, label=label)
        return self

    # --- Hook bindings ---

    def bind_render(self, extern_name: str, framebuffer_chip: str,
                    framebuffer_field: str,
                    frame_flag_chip: Optional[str] = None,
                    frame_flag_field: Optional[str] = None) -> 'SDLHost':
        """Bind the render extern to a chip's framebuffer."""
        self._render_extern = extern_name
        self._render_fb_chip = framebuffer_chip
        self._render_fb_field = framebuffer_field
        self._frame_flag_chip = frame_flag_chip or framebuffer_chip
        self._frame_flag_field = frame_flag_field or "frame_ready"
        return self

    def bind_audio(self, extern_name: str) -> 'SDLHost':
        """Bind the audio extern to SDL3 audio stream."""
        self._audio_extern = extern_name
        return self

    def bind_input(self, extern_name: str) -> 'SDLHost':
        """Bind the input extern to SDL3 keyboard polling."""
        self._input_extern = extern_name
        return self

    # --- ROM loading ---

    def set_rom_loading(self, chip_name: str, rom_field: str,
                        rom_size_field: str) -> 'SDLHost':
        """Configure which chip/fields hold the ROM data."""
        self._rom_chip = chip_name
        self._rom_field = rom_field
        self._rom_size_field = rom_size_field
        return self

    def set_rom_loader(self, code: str) -> 'SDLHost':
        """Provide raw C code for ROM loading and cart header parsing."""
        self._rom_loader_code = code
        return self

    # --- Raw C injection ---

    def set_post_init(self, code: str) -> 'SDLHost':
        """Raw C code injected after board_init() in main()."""
        self._post_init_code = code
        return self

    # --- Menu bar system ---

    def enable_menu(self, bar_height: int = 24,
                    font_scale: int = 2) -> 'SDLHost':
        """Enable the menu bar system.

        Does NOT add any menus by default. Call add_default_menus()
        for standard File/Display/Audio/Input menus, or build your
        own with add_menu().
        """
        self._menu_bar = MenuBarConfig(
            bar_height=bar_height,
            font_scale=font_scale,
        )
        return self

    def add_menu(self, label: str) -> Menu:
        """Add a top-level menu category and return it for chaining.

        Example:
            debug = host.add_menu("Debug")
            debug.add_toggle("Show BG", chip="ppu", field="show_bg")
        """
        menu = Menu(label)
        self._menus.append(menu)
        return menu

    def add_default_menus(self) -> 'SDLHost':
        """Add standard File, Display, Audio, Input menus.

        Built from current display/audio/input configuration.
        Call enable_menu() first.
        """
        # File menu
        file_menu = self.add_menu("File")
        file_menu.add_action("Open ROM...",
                             code="menu_open_file_dialog();")
        file_menu.add_separator()
        file_menu.add_action("Save Config",
                             code=f'config_save("{self._config_path}");')
        file_menu.add_action("Load Config",
                             code=f'config_load("{self._config_path}"); menu_apply_config();')
        file_menu.add_separator()
        file_menu.add_action("Quit", code="sdl_running = false;")

        # Display menu
        if self.display:
            disp_menu = self.add_menu("Display")
            disp_menu.add_toggle("VSync", config_key="vsync")

        # Audio menu
        if self.audio:
            audio_menu = self.add_menu("Audio")
            audio_menu.add_slider("Volume", config_key="volume",
                                  min_val=0, max_val=100, step=5)

        # Input menu
        if self.input.bindings:
            input_menu = self.add_menu("Input")
            for i, kb in enumerate(self.input.bindings):
                lbl = kb.label or f"Key {i}"
                input_menu.add_keybind(lbl, binding_index=i)

        return self

    def set_file_filters(self, filters: List[Tuple[str, str]]) -> 'SDLHost':
        """Set file filters for the Open ROM dialog.

        Args:
            filters: List of (name, pattern) tuples.
                     e.g. [("Game Boy ROMs", "gb;gbc"), ("All Files", "*")]
        """
        self._file_filters = filters
        return self

    def set_config_path(self, path: str = "config.json") -> 'SDLHost':
        """Set the config file path (relative to executable)."""
        self._config_path = path
        return self
