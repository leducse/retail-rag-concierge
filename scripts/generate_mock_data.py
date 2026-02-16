#!/usr/bin/env python3
"""
Magic Apron POC — Step 1: Data Preparation

GCP CONCEPTS (teaching):
------------------------
• Vertex AI Search uses a "Data Store" that is filled by ingestion from a source.
  This script creates the source data (CSV + markdown) that we will upload to
  GCS. The Data Store will later index that GCS content for RAG.

• In production, this data would typically come from BigQuery (catalog) or a CMS
  (DIY guides). BigQuery → scheduled export to GCS → Vertex AI Search ingests
  from GCS. We simulate that with local files first.

• Why CSV + Markdown? Vertex AI Search can index both. CSV gives structured
  product info; markdown gives narrative steps. One data store can hold both.
"""

import csv
import random
from pathlib import Path

# --- Product catalog: home improvement SKUs ---
CATEGORIES = [
    ("Plumbing", "A", "Faucets, pipes, fittings, drain cleaners"),
    ("Electrical", "B", "Wire, outlets, switches, LED bulbs"),
    ("Paint", "C", "Interior/exterior paint, brushes, rollers"),
    ("Hardware", "D", "Screws, nails, tools, fasteners"),
    ("Outdoor", "E", "Grills, garden, patio, lighting"),
]

PRODUCT_TEMPLATES = [
    ("Plumbing", ["Faucet", "Pipe Fitting", "Drain Snake", "Shut-off Valve", "Pipe Tape", "Plunger", "P-Trap", "Supply Line"]),
    ("Electrical", ["LED Bulb", "Outlet", "Switch", "Wire Nut", "Extension Cord", "Circuit Breaker", "Outlet Cover"]),
    ("Paint", ["Interior Paint", "Exterior Paint", "Brush Set", "Roller", "Drop Cloth", "Primer", "Caulk"]),
    ("Hardware", ["Screw Assortment", "Drill Bit Set", "Level", "Tape Measure", "Hammer", "Wrench Set", "Utility Knife"]),
    ("Outdoor", ["Grill Cover", "Garden Hose", "Solar Light", "Planter", "Mulch", "Weed Barrier", "Fence Post"]),
]

def _price(base: float, variance: float = 0.3) -> float:
    return round(base * (1 + random.uniform(-variance, variance)), 2)

def generate_products(n: int = 50) -> list[dict]:
    rows = []
    sku = 10000
    for _ in range(n):
        cat_name, aisle, desc_prefix = random.choice(CATEGORIES)
        templates = next(t[1] for t in PRODUCT_TEMPLATES if t[0] == cat_name)
        name = random.choice(templates)
        if random.random() > 0.5:
            name += f" - {random.choice(['Standard', 'Pro', 'Heavy Duty', 'Economy'])}"
        price = _price(random.choice([4.99, 12.99, 24.99, 49.99, 89.99, 149.99]))
        aisle_loc = f"{aisle}{random.randint(1, 24)}"
        description = f"{desc_prefix}. {name} for home improvement projects."
        rows.append({
            "sku_id": str(sku),
            "product_name": name,
            "category": cat_name,
            "price": f"{price:.2f}",
            "aisle_location": aisle_loc,
            "description": description,
        })
        sku += 1
    return rows

def write_product_catalog(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = generate_products(50)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["sku_id", "product_name", "category", "price", "aisle_location", "description"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out_path}")

DIY_GUIDES = {
    "how-to-fix-faucet.md": """# How to Fix a Leaky Faucet

## Tools You'll Need
- Adjustable wrench
- Phillips and flathead screwdrivers
- Replacement washer or cartridge (match your faucet type)

## Steps
1. **Turn off the water supply** at the shut-off valves under the sink.
2. **Remove the faucet handle** by prying off the cap and loosening the screw.
3. **Inspect the cartridge or stem** for worn washers or O-rings.
4. **Replace the washer or cartridge** with an exact match from the hardware store.
5. **Reassemble** and turn the water back on. Test for leaks.
""",
    "how-to-paint-a-room.md": """# How to Paint a Room

## Materials
- Interior paint (eggshell or satin for most rooms)
- Primer (if walls are stained or dark)
- Roller, tray, and extension pole
- Brush for edges
- Drop cloth and painter's tape

## Steps
1. **Prep**: Move furniture, cover floors, tape trim and ceilings.
2. **Prime** if needed; let dry per can instructions.
3. **Cut in** edges with a brush (ceiling line, corners, trim).
4. **Roll** walls in W or M patterns; maintain a wet edge to avoid lap marks.
5. **Second coat** after first is dry. Remove tape before paint is fully dry.
""",
    "how-to-install-led-bulbs.md": """# How to Install LED Bulbs

## What You Need
- LED bulbs (match base type: A19, BR30, PAR, etc.) and wattage equivalent
- Ladder if needed for ceiling fixtures

## Steps
1. **Turn off the switch** (and circuit breaker for ceiling fixtures if unsure).
2. **Allow old bulbs to cool** before touching.
3. **Remove the old bulb** by turning counterclockwise; support the fixture if heavy.
4. **Insert the LED** by aligning the base and turning clockwise until snug.
5. **Turn power back on** and test. Use dimmer-compatible LEDs if on a dimmer.
""",
    "how-to-hang-shelves.md": """# How to Hang Shelves

## Tools & Materials
- Level, tape measure, pencil
- Stud finder
- Drill and bits, screws (or wall anchors for drywall)
- Shelves and brackets

## Steps
1. **Locate studs** with a stud finder; mark at least two per shelf.
2. **Measure and mark** bracket positions; use a level to keep them even.
3. **Drill pilot holes** at marks (into studs or for anchors).
4. **Install anchors** if not in studs; then drive screws through brackets.
5. **Place the shelf** on the brackets and secure if required.
""",
    "how-to-unclog-a-drain.md": """# How to Unclog a Drain

## Options (easiest first)
- Plunger
- Baking soda + vinegar, then hot water
- Drain snake (hand or mechanical)

## Steps (plunger method)
1. **Remove** the strainer or overflow cover if possible.
2. **Block the overflow** (e.g., wet cloth) on sinks so pressure goes down the drain.
3. **Seal the plunger** over the drain and push firmly 10–15 times.
4. **Run hot water** to clear debris. Repeat if needed.

## If still clogged
Use a drain snake: feed it in until you feel resistance, twist to grab the clog, then pull back. Flush with hot water.
""",
}

def write_diy_guides(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, content in DIY_GUIDES.items():
        path = out_dir / name
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path}")
    print(f"Wrote {len(DIY_GUIDES)} DIY guides to {out_dir}")

def main():
    # Project root = google_cloud/magic_apron (parent of scripts/)
    base = Path(__file__).resolve().parent.parent
    data_dir = base / "data"
    write_product_catalog(data_dir / "product_catalog.csv")
    write_diy_guides(data_dir / "diy_guides")

if __name__ == "__main__":
    main()
