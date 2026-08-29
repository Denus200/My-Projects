from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = ROOT / "Ref" / "Deteil" / "Projects"
CAPTURE_ROOT = ROOT / "artifacts" / "projects"
OUTPUT_ROOT = CAPTURE_ROOT / "comparisons"


PAIRS = (
    ("projects-list-expanded", "Projects_Expanded.png", "projects-list-expanded.png", (232, 0, 1920, 941)),
    ("projects-list-collapsed", "Projects_Collapsed.png", "projects-list-collapsed.png", (56, 0, 1920, 941)),
    ("project-overview", "Projects_Expanded_Projects_Overview.png", "project-overview-cycle.png", (232, 0, 1920, 941)),
    ("project-plan", "Projects_Expanded_Projects_Plan.png", "project-plan.png", (232, 0, 1920, 941)),
    ("project-tasks-all", "Projects_Expanded_Projects_Tasks_All Tasks.png", "project-tasks-all.png", (232, 0, 1920, 941)),
    ("project-tasks-by-stage", "Projects_Expanded_Projects_Tasks_By Stage.png", "project-tasks-by-stage.png", (232, 0, 1920, 941)),
    ("project-notes-files", "Projects_Expanded_Projects_Notes&Files.png", "project-notes-files.png", (205, 0, 1672, 941)),
    ("project-archive", "Projects_Expanded_Projects_Archive.png", "project-archive.png", (205, 0, 1672, 941)),
    ("create-project", "Create_Project.png", "create-project.png", None),
)


def _fit(image: Image.Image, width: int, height: int) -> Image.Image:
    copy = image.copy()
    copy.thumbnail((width, height), Image.Resampling.LANCZOS)
    return copy


def compose(name: str, reference_name: str, capture_name: str, crop: tuple[int, int, int, int] | None) -> Path:
    with Image.open(REFERENCE_ROOT / reference_name) as source_image:
        source = source_image.convert("RGB")
        if crop is not None:
            source = source.crop(crop)
    with Image.open(CAPTURE_ROOT / capture_name) as implementation_image:
        implementation = implementation_image.convert("RGB")

    panel_width = 844 if name != "create-project" else 499
    panel_height = 471 if name != "create-project" else 635
    source = _fit(source, panel_width, panel_height)
    implementation = _fit(implementation, panel_width, panel_height)
    label_height = 34
    canvas = Image.new("RGB", (panel_width * 2, max(source.height, implementation.height) + label_height), "#FFFFFF")
    canvas.paste(source, (0, label_height))
    canvas.paste(implementation, (panel_width, label_height))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.text((12, 10), "REFERENCE", fill="#17131A", font=font)
    draw.text((panel_width + 12, 10), "IMPLEMENTATION", fill="#17131A", font=font)
    draw.line((panel_width, 0, panel_width, canvas.height), fill="#E11D48", width=2)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_ROOT / f"{name}-comparison.png"
    canvas.save(output)
    return output


def main() -> None:
    for pair in PAIRS:
        print(compose(*pair))


if __name__ == "__main__":
    main()
