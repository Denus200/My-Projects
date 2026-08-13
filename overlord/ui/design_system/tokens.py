from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StateColors:
    main: str
    background: str
    text: str


@dataclass(frozen=True, slots=True)
class ThemeTokens:
    app_background: str
    app_bar: str
    surface_card: str
    surface_inner: str
    surface_elevated: str
    border_default: str
    border_strong: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent_primary: str
    accent_primary_hover: str
    accent_primary_pressed: str
    accent_primary_disabled: str
    accent_bright: str
    on_accent: str
    focus_ring: str
    interactive_hover: str
    interactive_pressed: str
    interactive_selected: str
    control_background: str
    control_background_hover: str
    control_background_disabled: str
    text_disabled: str
    dashboard_add_background: str
    dashboard_add_border: str
    dashboard_add_text: str
    dashboard_add_icon: str
    dashboard_add_disabled_background: str
    dashboard_add_disabled_border: str
    dashboard_add_disabled_text: str
    dashboard_completion_border: str
    dashboard_completion_fill: str
    dashboard_completion_fill_border: str
    dashboard_completion_check: str
    profile_trigger_background: str
    profile_trigger_foreground: str
    sidebar_foreground: str
    sidebar_border: str
    sidebar_active_border: str
    sidebar_hover_border: str
    toggle_track_default: str
    toggle_track_hover: str
    toggle_track_pressed: str
    scrim: str
    soft_red_background: str
    soft_red_border: str
    soft_red_text: str
    # Deprecated compatibility tokens. New secondary emphasis uses the alt family.
    pink_accent: str
    pink_background: str
    pink_text: str
    success: StateColors
    warning: StateColors
    blocker: StateColors
    info: StateColors
    neutral: StateColors
    error: StateColors
    accent_alt: str | None = None
    accent_alt_hover: str | None = None
    accent_alt_pressed: str | None = None
    accent_alt_disabled: str | None = None
    on_accent_alt: str | None = None
    interactive_hover_alt: str | None = None
    interactive_pressed_alt: str | None = None
    interactive_selected_alt: str | None = None
    soft_teal_background: str | None = None
    soft_teal_border: str | None = None
    soft_teal_text: str | None = None
    space_0: int = 0
    space_1: int = 4
    space_2: int = 8
    space_3: int = 12
    space_4: int = 16
    space_5: int = 20
    space_6: int = 24
    space_8: int = 32
    space_10: int = 40
    space_12: int = 48
    text_small: int = 12
    text_body: int = 14
    text_emphasis: int = 16
    text_title: int = 20
    text_display: int = 28
    radius_small: int = 6
    radius_medium: int = 10
    radius_card: int = 14
    radius_large: int = 18
    radius_pill: int = 999
    border_width: int = 1
    focus_width: int = 2
    icon_small: int = 16
    icon_medium: int = 20
    icon_large: int = 24
    icon_display: int = 32
    control_height_compact: int = 36
    control_height: int = 40
    control_height_large: int = 44
    table_heading_height: int = 40
    table_row_height: int = 44
    field_padding_horizontal: int = 12
    field_padding_vertical: int = 10
    button_padding_horizontal: int = 16
    line_height_body: float = 1.4
    motion_none: int = 0
    motion_fast: int = 150
    motion_normal: int = 180
    motion_slow: int = 240


DARK_TOKENS = ThemeTokens(
    app_background="#0E0F13", app_bar="#11131A", surface_card="#151720",
    surface_inner="#1A1D28", surface_elevated="#1C1F2B", border_default="#2A2E3A",
    border_strong="#3A4050", text_primary="#F5F3F7", text_secondary="#A6A3B0",
    text_muted="#75727E", accent_primary="#E11D48", accent_primary_hover="#F43F5E",
    accent_primary_pressed="#BE123C", accent_primary_disabled="#6B2A3A",
    accent_bright="#FF3B5C", on_accent="#FFFFFF", focus_ring="#FB7185",
    interactive_hover="#202430", interactive_pressed="#292E3D", interactive_selected="#3A111C",
    control_background="#151720", control_background_hover="#1A1D28",
    control_background_disabled="#11131A", text_disabled="#66626D",
    dashboard_add_background="#F1F1F1", dashboard_add_border="#E9E9E9",
    dashboard_add_text="#9A9A9A", dashboard_add_icon="#000000",
    dashboard_add_disabled_background="#ECECEC",
    dashboard_add_disabled_border="#E7E7E7", dashboard_add_disabled_text="#DDDDDD",
    dashboard_completion_border="#3A4050", dashboard_completion_fill="#2ED17C",
    dashboard_completion_fill_border="#238A57", dashboard_completion_check="#D9FFE6",
    profile_trigger_background="#FFFFFF", profile_trigger_foreground="#000000",
    sidebar_foreground="#F5F3F7", sidebar_border="#2A2E3A",
    sidebar_active_border="#BE123C", sidebar_hover_border="#7F1D32",
    toggle_track_default="#3A4050", toggle_track_hover="#4A5060",
    toggle_track_pressed="#596071", scrim="#99000000",
    soft_red_background="#3A111C",
    soft_red_border="#7F1D32", soft_red_text="#FFB3C1", pink_accent="#FF7AB6",
    pink_background="#321325", pink_text="#FF9DCD",
    success=StateColors("#2ED17C", "#0B2A1A", "#86EFAC"),
    warning=StateColors("#F4B740", "#30230A", "#FCD34D"),
    blocker=StateColors("#A78BFA", "#24163F", "#C4B5FD"),
    info=StateColors("#5A8DFF", "#10213F", "#93C5FD"),
    neutral=StateColors("#8B95A5", "#1C2430", "#CBD5E1"),
    error=StateColors("#FF4444", "#3B1114", "#FCA5A5"),
)


LIGHT_TOKENS = ThemeTokens(
    app_background="#FAF7F5", app_bar="#FFFFFF", surface_card="#FFFFFF",
    surface_inner="#F7F2F4", surface_elevated="#FFFDFC", border_default="#E5DDE2",
    border_strong="#D4C8D0", text_primary="#17131A", text_secondary="#6F6472",
    text_muted="#918793", accent_primary="#D61F45", accent_primary_hover="#B9143A",
    accent_primary_pressed="#8F1235", accent_primary_disabled="#D8AEB9",
    accent_bright="#FF3B5C", on_accent="#FFFFFF", focus_ring="#7F1D3A",
    accent_alt="#0F766E", accent_alt_hover="#115E56", accent_alt_pressed="#134E4A",
    accent_alt_disabled="#BFDBD8", on_accent_alt="#FFFFFF",
    interactive_hover="#FFF1F4", interactive_pressed="#F9DCE4", interactive_selected="#FFE5EC",
    interactive_hover_alt="#EAF6F4", interactive_pressed_alt="#C7E7E3",
    interactive_selected_alt="#D3EEEA",
    control_background="#FFFFFF", control_background_hover="#FFFAFB",
    control_background_disabled="#F1ECEF", text_disabled="#AAA0A7",
    dashboard_add_background="#F1F1F1", dashboard_add_border="#E9E9E9",
    dashboard_add_text="#9A9A9A", dashboard_add_icon="#000000",
    dashboard_add_disabled_background="#ECECEC",
    dashboard_add_disabled_border="#E7E7E7", dashboard_add_disabled_text="#DDDDDD",
    dashboard_completion_border="#DDDDDD", dashboard_completion_fill="#12C933",
    dashboard_completion_fill_border="#47A958", dashboard_completion_check="#D9FFE6",
    profile_trigger_background="#FFFFFF", profile_trigger_foreground="#000000",
    sidebar_foreground="#37303A", sidebar_border="#ECE8EB",
    sidebar_active_border="#BF0F34", sidebar_hover_border="#FFD8E2",
    toggle_track_default="#D4C8D0", toggle_track_hover="#C1AEBB",
    toggle_track_pressed="#AF98A7", scrim="#99000000",
    soft_red_background="#FFE5EC",
    soft_red_border="#FFC2D0", soft_red_text="#9F1239", pink_accent="#DB2777",
    soft_teal_background="#E1F3F1", soft_teal_border="#B8E0DB", soft_teal_text="#0B5D57",
    pink_background="#FCE7F3", pink_text="#9D174D",
    success=StateColors("#16A34A", "#DCFCE7", "#166534"),
    warning=StateColors("#D97706", "#FEF3C7", "#92400E"),
    blocker=StateColors("#7C3AED", "#EDE9FE", "#5B21B6"),
    info=StateColors("#2563EB", "#DBEAFE", "#1D4ED8"),
    neutral=StateColors("#64748B", "#F1F5F9", "#475569"),
    error=StateColors("#DC2626", "#FEE2E2", "#991B1B"),
)


def resolve_tokens(theme_mode: str, system_is_dark: bool = False) -> ThemeTokens:
    if theme_mode == "dark" or (theme_mode == "system" and system_is_dark):
        return DARK_TOKENS
    return LIGHT_TOKENS
