from __future__ import annotations

from dataclasses import dataclass


PROJECT_COLOR_PALETTE = (
    "#F1ECEF",
    "#FFC7D2",
    "#D6F2E7",
    "#E1D6F7",
    "#FAE9BD",
    "#CCEFF3",
    "#F8DDCB",
)

# Canonical supplied UI-kit colors that are shared by Projects controls.
UI_KIT_BLACK = "#000000"
UI_KIT_SHADOW = "#1A000000"
UI_KIT_CONTROL_MUTED = "#999999"
UI_KIT_MENU_ITEM_HOVER = "#F2F2F2"
UI_KIT_DISABLED_BORDER = "#80000000"
PROJECT_METRIC_BACKGROUND = "#0A000000"
PROJECT_METRIC_BORDER = "#29000000"
PROJECT_CARD_ACTION_BACKGROUND = "#F2F2F2"
PROJECT_CARD_EMPTY_BACKGROUND = "#F7F7F7"
PROJECT_CARD_EMPTY_ICON = "#A0A0A0"
PROJECT_CARD_EMPTY_DASH = "#40000000"
STATUS_BADGE_COLORS: dict[str, tuple[str, str, str]] = {
    "active": ("#40BF40", "#E0F5E0", "#39AC39"),
    "completed": ("#40BF40", "#E0F5E0", "#39AC39"),
    "inactive": ("#808080", "#EBEBEB", "#808080"),
    "archived": ("#808080", "#EBEBEB", "#808080"),
    "planned": ("#808080", "#EBEBEB", "#808080"),
    "upcoming": ("#808080", "#EBEBEB", "#808080"),
    "not_completed": ("#BF40AA", "#F5E0F1", "#BF40AA"),
    "next_checkpoint": ("#7657D6", "#E4DEF7", "#7657D6"),
    "in_progress": ("#40BFBF", "#E0F5F5", "#40BFBF"),
    "blocked": ("#BF4040", "#F5E0E0", "#BF4040"),
    "paused": ("#BF8040", "#F5EBE0", "#BF8040"),
}


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
    tertiary_foreground: str
    tertiary_foreground_hover: str
    tertiary_foreground_pressed: str
    selection_foreground: str
    selection_foreground_hover: str
    selection_foreground_pressed: str
    selection_surface_hover: str
    selection_surface_pressed: str
    selection_surface_selected: str
    theme_secondary: str
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
    dashboard_board_background: str
    dashboard_board_border: str
    dashboard_board_divider: str
    dashboard_weekly_bar_track: str
    dashboard_weekly_bar_fill: str
    dashboard_weekly_today: str
    dashboard_date_chip_background: str
    dashboard_date_chip_border: str
    weather_card_background: str
    weather_card_border: str
    weather_glass_fill: str
    weather_glass_border: str
    weather_tab_active_background: str
    weather_tab_shadow: str
    weather_sunny_shadow: str
    weather_sunny_icon: str
    weather_sunny_icon_background: str
    weather_rainy_shadow: str
    weather_rainy_icon: str
    weather_rainy_icon_background: str
    weather_cloudy_shadow: str
    weather_cloudy_icon: str
    weather_cloudy_icon_background: str
    weather_snowy_shadow: str
    weather_snowy_icon: str
    weather_snowy_icon_background: str
    task_card_background: str
    task_card_border: str
    task_card_hover_border: str
    task_card_completed_text: str
    task_meta_date_background: str
    task_meta_date_text: str
    task_meta_deadline_background: str
    task_meta_deadline_text: str
    task_meta_cycle_background: str
    task_meta_cycle_text: str
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
    success: StateColors
    warning: StateColors
    blocker: StateColors
    info: StateColors
    neutral: StateColors
    error: StateColors
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
    task_card_radius: int = 13
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
    tertiary_foreground="#E11D48", tertiary_foreground_hover="#E11D48",
    tertiary_foreground_pressed="#E11D48", selection_foreground="#E11D48",
    selection_foreground_hover="#F43F5E", selection_foreground_pressed="#BE123C",
    selection_surface_hover="#202430", selection_surface_pressed="#292E3D",
    selection_surface_selected="#3A111C", theme_secondary="#FF7AB6",
    control_background="#151720", control_background_hover="#1A1D28",
    control_background_disabled="#11131A", text_disabled="#66626D",
    dashboard_add_background="#F1F1F1", dashboard_add_border="#E9E9E9",
    dashboard_add_text="#9A9A9A", dashboard_add_icon="#000000",
    dashboard_add_disabled_background="#ECECEC",
    dashboard_add_disabled_border="#E7E7E7", dashboard_add_disabled_text="#DDDDDD",
    dashboard_completion_border="#3A4050", dashboard_completion_fill="#2ED17C",
    dashboard_completion_fill_border="#238A57", dashboard_completion_check="#D9FFE6",
    dashboard_board_background="#1A1D28", dashboard_board_border="#3A4050",
    dashboard_board_divider="#2A2E3A", dashboard_weekly_bar_track="#3A4050",
    dashboard_weekly_bar_fill="#E11D48", dashboard_weekly_today="#F4B740",
    dashboard_date_chip_background="#151720",
    dashboard_date_chip_border="#3A4050",
    weather_card_background="#1A1D28", weather_card_border="#3A4050",
    weather_glass_fill="#1AFFFFFF", weather_glass_border="#3DFFFFFF",
    weather_tab_active_background="#FFFFFF", weather_tab_shadow="#40000000",
    weather_sunny_shadow="#8D3C07", weather_sunny_icon="#F0A061",
    weather_sunny_icon_background="#24F0A061",
    weather_rainy_shadow="#192776", weather_rainy_icon="#8795CA",
    weather_rainy_icon_background="#248795CA",
    weather_cloudy_shadow="#415D7C", weather_cloudy_icon="#8297AC",
    weather_cloudy_icon_background="#248297AC",
    weather_snowy_shadow="#526A82", weather_snowy_icon="#9BB4C9",
    weather_snowy_icon_background="#249BB4C9",
    task_card_background="#151720",
    task_card_border="#2A2E3A", task_card_hover_border="#E11D48",
    task_card_completed_text="#66626D", task_meta_date_background="#5B7F24",
    task_meta_date_text="#FFFFFF", task_meta_deadline_background="#4A1D20",
    task_meta_deadline_text="#FF9B91", task_meta_cycle_background="#252553",
    task_meta_cycle_text="#A9A9FF",
    profile_trigger_background="#FFFFFF", profile_trigger_foreground="#000000",
    sidebar_foreground="#F5F3F7", sidebar_border="#2A2E3A",
    sidebar_active_border="#BE123C", sidebar_hover_border="#7F1D32",
    toggle_track_default="#3A4050", toggle_track_hover="#4A5060",
    toggle_track_pressed="#596071", scrim="#99000000",
    soft_red_background="#3A111C",
    soft_red_border="#7F1D32", soft_red_text="#FFB3C1",
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
    interactive_hover="#FFF1F4", interactive_pressed="#F9DCE4", interactive_selected="#FFE5EC",
    tertiary_foreground="#0F766E", tertiary_foreground_hover="#115E56",
    tertiary_foreground_pressed="#134E4A", selection_foreground="#0F766E",
    selection_foreground_hover="#115E56", selection_foreground_pressed="#134E4A",
    selection_surface_hover="#EAF6F4", selection_surface_pressed="#C7E7E3",
    selection_surface_selected="#D3EEEA", theme_secondary="#0F766E",
    control_background="#FFFFFF", control_background_hover="#FFFAFB",
    control_background_disabled="#F1ECEF", text_disabled="#AAA0A7",
    dashboard_add_background="#F1F1F1", dashboard_add_border="#E9E9E9",
    dashboard_add_text="#9A9A9A", dashboard_add_icon="#000000",
    dashboard_add_disabled_background="#ECECEC",
    dashboard_add_disabled_border="#E7E7E7", dashboard_add_disabled_text="#DDDDDD",
    dashboard_completion_border="#DDDDDD", dashboard_completion_fill="#12C933",
    dashboard_completion_fill_border="#47A958", dashboard_completion_check="#D9FFE6",
    dashboard_board_background="#F7F7F7", dashboard_board_border="#E5DDE2",
    dashboard_board_divider="#EBEBEB", dashboard_weekly_bar_track="#E7E5E5",
    dashboard_weekly_bar_fill="#E53A3A", dashboard_weekly_today="#FE4806",
    dashboard_date_chip_background="#FFFFFF",
    dashboard_date_chip_border="#EEEEEE",
    weather_card_background="#F7F7F7", weather_card_border="#E5DDE2",
    weather_glass_fill="#1AFFFFFF", weather_glass_border="#3DFFFFFF",
    weather_tab_active_background="#FFFFFF", weather_tab_shadow="#40000000",
    weather_sunny_shadow="#8D3C07", weather_sunny_icon="#F0A061",
    weather_sunny_icon_background="#24F0A061",
    weather_rainy_shadow="#192776", weather_rainy_icon="#8795CA",
    weather_rainy_icon_background="#248795CA",
    weather_cloudy_shadow="#415D7C", weather_cloudy_icon="#8297AC",
    weather_cloudy_icon_background="#248297AC",
    weather_snowy_shadow="#526A82", weather_snowy_icon="#9BB4C9",
    weather_snowy_icon_background="#249BB4C9",
    task_card_background="#FFFFFF",
    task_card_border="#E9E9E9", task_card_hover_border="#D61F45",
    task_card_completed_text="#E1E1E1", task_meta_date_background="#5B7F24",
    task_meta_date_text="#FFFFFF", task_meta_deadline_background="#FFD5D2",
    task_meta_deadline_text="#C9372C", task_meta_cycle_background="#D2D2FF",
    task_meta_cycle_text="#2C2CC9",
    profile_trigger_background="#FFFFFF", profile_trigger_foreground="#000000",
    sidebar_foreground="#37303A", sidebar_border="#ECE8EB",
    sidebar_active_border="#BF0F34", sidebar_hover_border="#FFD8E2",
    toggle_track_default="#D4C8D0", toggle_track_hover="#C1AEBB",
    toggle_track_pressed="#AF98A7", scrim="#99000000",
    soft_red_background="#FFE5EC",
    soft_red_border="#FFC2D0", soft_red_text="#9F1239",
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
