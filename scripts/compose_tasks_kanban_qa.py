from __future__ import annotations

from pathlib import Path

from PIL import Image


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = REPOSITORY_ROOT / "Ref" / "Deteil" / "Tasks" / "My Tasks" / "Kanban"
OUTPUT_ROOT = REPOSITORY_ROOT / "artifacts" / "tasks-kanban" / "comparisons"


def compose(name: str, reference: Path, implementation: Path, crop: tuple[int, int, int, int] | None = None) -> None:
    with Image.open(reference) as source_image, Image.open(implementation) as implementation_image:
        source = source_image.convert("RGB")
        built = implementation_image.convert("RGB")
        if crop is not None:
            source = source.crop(crop)
            built = built.crop(crop)
        comparison = Image.new("RGB", (source.width + built.width, max(source.height, built.height)), "white")
        comparison.paste(source, (0, 0))
        comparison.paste(built, (source.width, 0))
        OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_ROOT / name
        comparison.save(path)
        print(path)


def main() -> None:
    expanded_reference = REFERENCE_ROOT / "Tasks_Kanban_Expanded.png"
    collapsed_reference = REFERENCE_ROOT / "Tasks_Kanban_Collapsed.png"
    expanded = OUTPUT_ROOT.parent / "01-expanded-sidebar.png"
    collapsed = OUTPUT_ROOT.parent / "02-collapsed-sidebar.png"
    compose("expanded-full.png", expanded_reference, expanded)
    compose("collapsed-full.png", collapsed_reference, collapsed)
    compose("expanded-toolbar.png", expanded_reference, expanded, (0, 0, 1920, 136))
    compose("expanded-columns.png", expanded_reference, expanded, (232, 136, 1920, 1080))


if __name__ == "__main__":
    main()
