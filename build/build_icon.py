"""Build the Windows application icon from the supplied portrait image."""

from pathlib import Path

from PIL import Image


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    source_path = project_root / "assets" / "images" / "icon_portrait.png"
    with Image.open(source_path) as source_file:
        source = source_file.convert("RGBA")

    side = min(source.size)
    left = (source.width - side) // 2
    top = (source.height - side) // 2
    source = source.crop((left, top, left + side, top + side))

    sizes = (256, 128, 64, 48, 32, 16)
    images = [source.resize((size, size), Image.Resampling.LANCZOS) for size in sizes]
    output = project_root / "assets" / "icons" / "muramasa.ico"
    output.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(output, format="ICO", sizes=[(size, size) for size in sizes],
                   append_images=images[1:])
    print(f"Generated {output}")


if __name__ == "__main__":
    main()
