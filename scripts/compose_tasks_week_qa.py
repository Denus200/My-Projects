from __future__ import annotations

from pathlib import Path

from PIL import Image


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = REPOSITORY_ROOT / "Ref" / "Deteil" / "Tasks" / "My Tasks" / "Week"
OUTPUT_ROOT = REPOSITORY_ROOT / "artifacts" / "tasks-week" / "comparisons"


def compose(
    name: str,
    reference: Path,
    implementation: Path,
    crop: tuple[int, int, int, int] | None = None,
) -> None:
    with Image.open(reference) as source_image, Image.open(implementation) as implementation_image:
        source = source_image.convert("RGB")
        built = implementation_image.convert("RGB")
        if crop is not None:
            source = source.crop(crop)
            built = built.crop(crop)
        comparison = Image.new(
            "RGB",
            (source.width + built.width, max(source.height, built.height)),
            "white",
        )
        comparison.paste(source, (0, 0))
        comparison.paste(built, (source.width, 0))
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_ROOT / name
        comparison.save(path)
        print(path)


def compose_regions(
    name: str,
    reference: Path,
    implementation: Path,
    reference_crop: tuple[int, int, int, int],
    implementation_crop: tuple[int, int, int, int],
) -> None:
    with Image.open(reference) as source_image, Image.open(implementation) as implementation_image:
        source = source_image.convert("RGB").crop(reference_crop)
        built = implementation_image.convert("RGB").crop(implementation_crop)
        comparison = Image.new(
            "RGB",
            (source.width + built.width, max(source.height, built.height)),
            "white",
        )
        comparison.paste(source, (0, 0))
        comparison.paste(built, (source.width, 0))
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_ROOT / name
        comparison.save(path)
        print(path)


def main() -> None:
    expanded_reference = REFERENCE_ROOT / "Tasks_Week_Expanded.png"
    collapsed_reference = REFERENCE_ROOT / "Tasks_Week_Collapsed.png"
    expanded = OUTPUT_ROOT.parent / "01-expanded-sidebar.png"
    collapsed = OUTPUT_ROOT.parent / "02-collapsed-sidebar.png"
    expanded_navigation = OUTPUT_ROOT.parent / "07-expanded-week-navigation.png"
    tabs_reference = REPOSITORY_ROOT / "Ref" / "Deteil" / "Component" / "Tabs.png"
    compose("expanded-full.png", expanded_reference, expanded)
    compose("collapsed-full.png", collapsed_reference, collapsed)
    compose("expanded-toolbar.png", expanded_reference, expanded, (232, 0, 1920, 136))
    compose("expanded-week-board.png", expanded_reference, expanded, (232, 136, 1920, 1080))
    compose_regions(
        "week-tab-collapsed.png",
        tabs_reference,
        expanded,
        (0, 80, 560, 160),
        (232, 56, 792, 136),
    )
    compose_regions(
        "week-tab-expanded.png",
        tabs_reference,
        expanded_navigation,
        (0, 160, 560, 240),
        (232, 56, 792, 136),
    )


if __name__ == "__main__":
    main()
