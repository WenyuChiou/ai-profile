"""Original orthographic voxel characters, shared by the two renderers.

Closed, local SVG geometry only. These shapes are decoration, not data marks.
No downloaded game assets, runtime 3D engine, or raster animation frames.
"""


def _block(x: int, y: int, w: int, h: int, front: str, side: str, top: str) -> str:
    """A small cuboid with a fixed 4 by 3 orthographic depth vector."""
    return (
        f'<path d="M {x + w} {y} l 4 -3 v {h} l -4 3 Z" fill="{side}"/>'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{front}"/>'
        f'<path d="M {x} {y} l 4 -3 h {w} l -4 3 Z" fill="{top}"/>'
    )


def actor_body(kind: str) -> str:
    """Return an original miner or mossy explorer, with feet at y=42.

    Placement belongs to a static outer group; animation belongs to its child.
    The closed vocabulary prevents arbitrary data from entering SVG markup.
    """
    if kind not in {"miner", "zombie"}:
        raise ValueError("Unknown voxel actor")
    miner = kind == "miner"
    skin = ("#eac194", "#b98157", "#ffe1b9") if miner else (
        "#7ba55a", "#496b3a", "#a0c278"
    )
    coat = ("#297b96", "#1d5265", "#62a7b3") if miner else (
        "#627c65", "#3d5244", "#8ba183"
    )
    parts = [
        # The backpack is behind the torso, not associated with any data category.
        _block(1, 19, 6, 15, "#8b693e", "#59452f", "#baa06a"),
        f'<g class="{kind}-leg-l">'
        + _block(7, 33, 6, 9, "#384b62", "#233143", "#5a6a7d") + "</g>",
        _block(16, 33, 6, 9, "#384b62", "#233143", "#5a6a7d"),
        _block(7, 18, 15, 15, *coat),
        _block(7, 30, 15, 3, "#785439", "#4d382a", "#ae8751"),
        _block(6, 5, 16, 13, *skin),
        '<rect x="10" y="10" width="3" height="3" fill="#24352f"/>',
        '<rect x="18" y="10" width="2" height="3" fill="#24352f"/>',
        '<rect x="14" y="15" width="5" height="1" fill="#6f6147"/>',
    ]
    if miner:
        parts.extend([
            _block(5, 4, 18, 4, "#d4972d", "#9c691f", "#f1ca68"),
            _block(4, 7, 20, 2, "#b88024", "#795017", "#e9b647"),
            _block(18, 4, 5, 5, "#ffe5a0", "#c89639", "#fff0c7"),
            '<g class="pickaxe-arm">',
            _block(20, 19, 5, 8, *coat),
            '<path d="M 23 23 L 34 12" stroke="#8e683e" stroke-width="3"/>',
            '<path d="M 29 11 L 35 9 L 40 14 L 39 18 L 34 13 L 28 14 Z" '
            'fill="#9facb5"/>',
            '<path d="M 29 11 L 35 9 L 39 12 L 35 11 Z" fill="#d7e1e3"/>',
            '</g>',
        ])
    else:
        parts.extend([
            _block(21, 20, 5, 10, *skin),
            '<path d="M 7 5 h 5 v 3 H 9 v 2 H 6 V 5 Z" fill="#3d653c"/>',
            '<rect x="16" y="4" width="5" height="3" fill="#4d733e"/>',
            '<rect x="2" y="24" width="5" height="2" fill="#c7b06d"/>',
        ])
    return "\n".join(parts)
