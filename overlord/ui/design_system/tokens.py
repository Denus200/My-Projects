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
    accent_bright: str
    on_accent: str
    soft_red_background: str
    soft_red_border: str
    soft_red_text: str
    pink_accent: str
    pink_background: str
    pink_text: str
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
    border_width: int = 1
    focus_width: int = 2
    icon_small: int = 16
    icon_medium: int = 20
    icon_large: int = 24
    icon_display: int = 32
    motion_none: int = 0
    motion_fast: int = 100
    motion_normal: int = 180
    motion_slow: int = 240


DARK_TOKENS = ThemeTokens(
    app_background="#0E0F13", app_bar="#11131A", surface_card="#151720",
    surface_inner="#1A1D28", surface_elevated="#1C1F2B", border_default="#2A2E3A",
    border_strong="#3A4050", text_primary="#F5F3F7", text_secondary="#A6A3B0",
    text_muted="#75727E", accent_primary="#E11D48", accent_primary_hover="#F43F5E",
    accent_bright="#FF3B5C", on_accent="#FFFFFF", soft_red_background="#3A111C",
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
    accent_bright="#FF3B5C", on_accent="#FFFFFF", soft_red_background="#FFE5EC",
    soft_red_border="#FFC2D0", soft_red_text="#9F1239", pink_accent="#DB2777",
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
