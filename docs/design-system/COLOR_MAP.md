# Overlord Color Map

Status: current implementation reference. The source of truth remains
[`overlord/ui/design_system/tokens.py`](../../overlord/ui/design_system/tokens.py).

The product uses the **Crimson Focus** palette: a warm neutral foundation with
crimson as the primary interactive colour. The light palette is the approved
design baseline. Dark values provide behavioural parity and are not yet a final
visual redesign.

## Core surfaces and borders

| Token | Light | Dark | Intended use |
| --- | --- | --- | --- |
| `app_background` | `#FAF7F5` | `#0E0F13` | Application canvas |
| `app_bar` | `#FFFFFF` | `#11131A` | Sidebar / app bar |
| `surface_card` | `#FFFFFF` | `#151720` | Cards and standard surfaces |
| `surface_inner` | `#F7F2F4` | `#1A1D28` | Nested surfaces |
| `surface_elevated` | `#FFFDFC` | `#1C1F2B` | Dialogs and elevated areas |
| `border_default` | `#E5DDE2` | `#2A2E3A` | Default boundaries |
| `border_strong` | `#D4C8D0` | `#3A4050` | Stronger control boundaries |
| `scrim` | `#99000000` | `#99000000` | Modal overlay |

## Text and primary accent

| Token | Light | Dark | Intended use |
| --- | --- | --- | --- |
| `text_primary` | `#17131A` | `#F5F3F7` | Headings and normal text |
| `text_secondary` | `#6F6472` | `#A6A3B0` | Supporting text and inactive icons |
| `text_muted` | `#918793` | `#75727E` | Metadata only |
| `text_disabled` | `#AAA0A7` | `#66626D` | Disabled content |
| `sidebar_foreground` | `#37303A` | `#F5F3F7` | Default Sidebar labels and icons |
| `sidebar_border` | `#ECE8EB` | `#2A2E3A` | Sidebar divider |
| `sidebar_active_border` | `#BF0F34` | `#BE123C` | Compact active-item boundary |
| `sidebar_hover_border` | `#FFD8E2` | `#7F1D32` | Compact hover boundary |
| `accent_primary` | `#D61F45` | `#E11D48` | Primary action and selected state |
| `accent_primary_hover` | `#B9143A` | `#F43F5E` | Primary-action hover |
| `accent_primary_pressed` | `#8F1235` | `#BE123C` | Primary-action pressed |
| `accent_primary_disabled` | `#D8AEB9` | `#6B2A3A` | Disabled primary action |
| `accent_bright` | `#FF3B5C` | `#FF3B5C` | High-attention accent |
| `on_accent` | `#FFFFFF` | `#FFFFFF` | Content placed on an accent |
| `focus_ring` | `#7F1D3A` | `#FB7185` | Keyboard focus |

## Interaction and control states

| Token | Light | Dark | Intended use |
| --- | --- | --- | --- |
| `interactive_hover` | `#FFF1F4` | `#202430` | Hovered selectable area |
| `interactive_pressed` | `#F9DCE4` | `#292E3D` | Pressed selectable area |
| `interactive_selected` | `#FFE5EC` | `#3A111C` | Selected selectable area |
| `control_background` | `#FFFFFF` | `#151720` | Input / unselected control |
| `control_background_hover` | `#FFFAFB` | `#1A1D28` | Hovered input / control |
| `control_background_disabled` | `#F1ECEF` | `#11131A` | Disabled input / control |
| `toggle_track_default` | `#D4C8D0` | `#3A4050` | Inactive toggle track |
| `toggle_track_hover` | `#C1AEBB` | `#4A5060` | Inactive toggle hover |
| `toggle_track_pressed` | `#AF98A7` | `#596071` | Inactive toggle pressed |

## Supporting crimson and pink roles

| Token | Light | Dark | Intended use |
| --- | --- | --- | --- |
| `soft_red_background` | `#FFE5EC` | `#3A111C` | Soft crimson emphasis |
| `soft_red_border` | `#FFC2D0` | `#7F1D32` | Soft crimson boundary |
| `soft_red_text` | `#9F1239` | `#FFB3C1` | Text on soft crimson |
| `pink_accent` | `#DB2777` | `#FF7AB6` | Secondary pink accent |
| `pink_background` | `#FCE7F3` | `#321325` | Soft pink background |
| `pink_text` | `#9D174D` | `#FF9DCD` | Text on soft pink |

## Semantic feedback colours

| Meaning | Main (light / dark) | Background (light / dark) | Text (light / dark) |
| --- | --- | --- | --- |
| Success | `#16A34A` / `#2ED17C` | `#DCFCE7` / `#0B2A1A` | `#166534` / `#86EFAC` |
| Warning | `#D97706` / `#F4B740` | `#FEF3C7` / `#30230A` | `#92400E` / `#FCD34D` |
| Blocker | `#7C3AED` / `#A78BFA` | `#EDE9FE` / `#24163F` | `#5B21B6` / `#C4B5FD` |
| Info | `#2563EB` / `#5A8DFF` | `#DBEAFE` / `#10213F` | `#1D4ED8` / `#93C5FD` |
| Neutral | `#64748B` / `#8B95A5` | `#F1F5F9` / `#1C2430` | `#475569` / `#CBD5E1` |
| Error | `#DC2626` / `#FF4444` | `#FEE2E2` / `#3B1114` | `#991B1B` / `#FCA5A5` |

## Sidebar quick reference

| State | Light | Dark |
| --- | --- | --- |
| Sidebar background | `#FFFFFF` | `#11131A` |
| Default label and icon | `#37303A` | `#F5F3F7` |
| Active surface | `#D61F45` | `#E11D48` |
| Active label and icon | `#FFFFFF` | `#FFFFFF` |
| Active background | `#D61F45` | `#E11D48` |
| Hover background | `#FFE5EC` | `#3A111C` |
| Pressed background | `#F9DCE4` | `#292E3D` |
| Panel divider | `#ECE8EB` | `#2A2E3A` |
