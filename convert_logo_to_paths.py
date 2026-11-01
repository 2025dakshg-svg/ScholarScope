"""Converts ScholarScope wordmark text into pure SVG path outlines.

Ensures that static/logo.svg and static/favicon.svg are 100% self-contained:
- Works inside <img> tags without requiring external font loading
- Supports dark mode via prefers-color-scheme with explicit fallbacks
- Retains crispness down to 16px and 32px
"""

from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties


def path_to_svg_d(text_path, offset_x=0, offset_y=0):
    svg_commands = []
    codes = text_path.codes
    vertices = text_path.vertices

    i = 0
    while i < len(codes):
        code = codes[i]
        v = vertices[i]
        x = round(v[0] + offset_x, 2)
        y = round(-v[1] + offset_y, 2)

        if code == 1:
            svg_commands.append(f"M {x} {y}")
            i += 1
        elif code == 2:
            svg_commands.append(f"L {x} {y}")
            i += 1
        elif code == 3:
            v1 = vertices[i]
            v2 = vertices[i+1]
            x1, y1 = round(v1[0] + offset_x, 2), round(-v1[1] + offset_y, 2)
            x2, y2 = round(v2[0] + offset_x, 2), round(-v2[1] + offset_y, 2)
            svg_commands.append(f"Q {x1} {y1} {x2} {y2}")
            i += 2
        elif code == 4:
            v1 = vertices[i]
            v2 = vertices[i+1]
            v3 = vertices[i+2]
            x1, y1 = round(v1[0] + offset_x, 2), round(-v1[1] + offset_y, 2)
            x2, y2 = round(v2[0] + offset_x, 2), round(-v2[1] + offset_y, 2)
            x3, y3 = round(v3[0] + offset_x, 2), round(-v3[1] + offset_y, 2)
            svg_commands.append(f"C {x1} {y1} {x2} {y2} {x3} {y3}")
            i += 3
        elif code == 79:
            svg_commands.append("Z")
            i += 1
        else:
            i += 1

    return " ".join(svg_commands)


def build_svgs():
    fp_bold = FontProperties(family="serif", weight="bold")
    fp_italic = FontProperties(family="serif", style="italic", weight="normal")

    tp_scholar = TextPath((0, 0), "Scholar", size=21, prop=fp_bold)
    tp_scope = TextPath((0, 0), "Scope", size=21, prop=fp_italic)

    scholar_width = tp_scholar.get_extents().width
    d_scholar = path_to_svg_d(tp_scholar, offset_x=44, offset_y=24.5)
    d_scope = path_to_svg_d(tp_scope, offset_x=44 + scholar_width + 1.5, offset_y=24.5)

    # 1. Full Header Logo SVG
    svg_logo = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 215 36" width="215" height="36" role="img" aria-label="ScholarScope Logo">
  <defs>
    <style>
      :root {{
        --logo-accent: #1F4D3F;
        --logo-ink: #1B1B1A;
      }}
      .mark-primary {{ fill: var(--logo-accent, #1F4D3F); }}
      .wordmark-ink {{ fill: var(--logo-ink, #1B1B1A); }}
      .wordmark-accent {{ fill: var(--logo-accent, #1F4D3F); }}

      @media (prefers-color-scheme: dark) {{
        :root {{
          --logo-accent: #4FA888;
          --logo-ink: #EAE8E3;
        }}
        .mark-primary {{ fill: var(--logo-accent, #4FA888); }}
        .wordmark-ink {{ fill: var(--logo-ink, #EAE8E3); }}
        .wordmark-accent {{ fill: var(--logo-accent, #4FA888); }}
      }}
    </style>
  </defs>

  <!-- Geometric 4-Pillar Mark (Scope, Resources, Sources, Outcomes) -->
  <g transform="translate(2, 2)">
    <path class="mark-primary" d="M 5 14.5 L 14.5 14.5 L 14.5 5 C 9.25 5 5 9.25 5 14.5 Z" opacity="0.9" />
    <path class="mark-primary" d="M 17.5 14.5 L 27 14.5 C 27 9.25 22.75 5 17.5 5 L 17.5 14.5 Z" />
    <path class="mark-primary" d="M 5 17.5 C 5 22.75 9.25 27 14.5 27 L 14.5 17.5 L 5 17.5 Z" opacity="0.75" />
    <path class="mark-primary" d="M 17.5 17.5 L 17.5 27 C 22.75 27 27 22.75 27 17.5 L 17.5 17.5 Z" opacity="0.95" />
    <rect class="mark-primary" x="15" y="15" width="2" height="2" transform="rotate(45 16 16)" />
  </g>

  <!-- Wordmark Vector Outlines (Font-Independent Path Vectors) -->
  <path class="wordmark-ink" d="{d_scholar}" />
  <path class="wordmark-accent" d="{d_scope}" />
</svg>
'''

    # 2. Standalone Favicon SVG
    svg_favicon = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32" role="img" aria-label="ScholarScope Favicon">
  <defs>
    <style>
      :root {
        --logo-accent: #1F4D3F;
      }
      .mark-primary { fill: var(--logo-accent, #1F4D3F); }
      @media (prefers-color-scheme: dark) {
        :root {
          --logo-accent: #4FA888;
        }
        .mark-primary { fill: var(--logo-accent, #4FA888); }
      }
    </style>
  </defs>
  <path class="mark-primary" d="M 5 14.5 L 14.5 14.5 L 14.5 5 C 9.25 5 5 9.25 5 14.5 Z" opacity="0.9" />
  <path class="mark-primary" d="M 17.5 14.5 L 27 14.5 C 27 9.25 22.75 5 17.5 5 L 17.5 14.5 Z" />
  <path class="mark-primary" d="M 5 17.5 C 5 22.75 9.25 27 14.5 27 L 14.5 17.5 L 5 17.5 Z" opacity="0.75" />
  <path class="mark-primary" d="M 17.5 17.5 L 17.5 27 C 22.75 27 27 22.75 27 17.5 L 17.5 17.5 Z" opacity="0.95" />
  <rect class="mark-primary" x="15" y="15" width="2" height="2" transform="rotate(45 16 16)" />
</svg>
'''

    with open("static/logo.svg", "w", encoding="utf-8") as f:
        f.write(svg_logo)

    with open("static/favicon.svg", "w", encoding="utf-8") as f:
        f.write(svg_favicon)

    print("✓ Successfully built static/logo.svg and static/favicon.svg with explicit fallbacks and dark mode media queries.")


if __name__ == "__main__":
    build_svgs()
