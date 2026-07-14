"""
createHead.py — CPH Behavior/Resource Pack Generator
=====================================================
Reads HeadsToCreate.csv and generates all required pack files for every
head listed. Each row in the CSV fully describes one head:

  name, sound, model, texture, display

Run:
    python createHead.py

Output folders CPH_BP/ and CPH_RP/ are written next to this script, fully
regenerated from templates/ on every run. See HeadsToCreate.csv for full
column documentation.

Two source folders feed the generator:
  templates/    The baked-in baseline — manifests, scripts, the "head"
                model, the shared default sound, and the Player/Herobrine
                heads that ship with the addon. Always copied first.
  user_assets/  Where a user drops files for their OWN heads — textures,
                custom sounds, custom models — mirroring the RP's own
                layout. Copied in per-head, on top of the template
                baseline, only for rows whose asset isn't already baked
                into templates/. See user_assets/ for the exact layout.

Unlike VMH (mob heads), player heads have no loot-table drop mechanic —
they're spawned directly by the scripting API in index.js when a player
dies — so this generator has no loot_tables step. It does have one thing
VMH doesn't need: a sound_definitions.json entry per custom sound, since
each player head can have its own kill sound.
"""

import csv
import json
import os
import re
import shutil
import glob

# ============================================================
# CONFIGURATION
# ============================================================

# Input file — relative to this script
HEADS_CSV = "HeadsToCreate.csv"

# Where users drop their own textures/sounds/models for new heads —
# relative to this script. Mirrors the RP's own folder layout so it's
# obvious where a file goes. See the README inside this folder.
USER_ASSETS_DIR = "user_assets"

# Heads that ship with fully hand-crafted block/attachable files inside
# the templates folder. The generator skips auto-creating those file
# types for these names so the hand-crafted versions stay intact.
# (Empty for now — every current CPH head uses the generic "head" model.
# Add a name here if you ever hand-build a unique block/attachable for it.)
SPECIAL_HEADS = set()

# Default values used when a CSV column is blank
DEFAULTS = {
    "sound":   "default",
    "model":   "head",
    "texture": None,  # None → auto-derived from name
    "display": None,  # None → auto-derived from name
}

# ============================================================
# TEMPLATE REGISTRY
# Maps a logical template type to its source file and output path.
# [lower custom name] is replaced at generation time.
# ============================================================
TEMPLATE_REGISTRY = {
    "items_rp": {
        "template_file": "templates/items_rp.json",
        "file_path":     "CPH_RP/items/[lower custom name]_head.json",
    },
    "items_bp": {
        "template_file": "templates/items_bp.json",
        "file_path":     "CPH_BP/items/[lower custom name]_head.json",
    },
    "block": {
        "template_file": "templates/block.json",
        "file_path":     "CPH_BP/blocks/[lower custom name]_head.json",
    },
    "recipe_toBlock": {
        "template_file": "templates/recipe_toBlock.json",
        "file_path":     "CPH_BP/recipes/[lower custom name]_toBlock.json",
    },
    "recipe_toHead": {
        "template_file": "templates/recipe_toHead.json",
        "file_path":     "CPH_BP/recipes/[lower custom name]_toHead.json",
    },
    "attachable": {
        "template_file": "templates/attachable.json",
        "file_path":     "CPH_RP/attachables/[lower custom name]_head.json",
    },
}


# ============================================================
# CSV PARSING
# ============================================================

def parse_heads_csv(file_path):
    """
    Reads HeadsToCreate.csv and returns a list of head definition dicts.
    Lines starting with # are treated as comments and skipped.
    Missing or blank columns fall back to DEFAULTS.
    """
    heads = []

    with open(file_path, "r", encoding="utf-8") as f:
        cleaned_lines = [line for line in f if not line.lstrip().startswith("#")]

    reader = csv.DictReader(cleaned_lines)

    for row_num, row in enumerate(reader, start=2):
        name = row.get("name", "").strip()
        if not name:
            print(f"  WARNING: row {row_num} has no name — skipping.")
            continue

        sound = row.get("sound", "").strip() or DEFAULTS["sound"]
        model = row.get("model", "").strip() or DEFAULTS["model"]
        texture = row.get("texture", "").strip() or f"textures/blocks/skulls/{name}"
        display = row.get("display", "").strip() or (name.replace("_", " ") + " Head")

        heads.append({
            "name":    name,
            "sound":   sound,
            "model":   model,
            "texture": texture,
            "display": display,
        })

    return heads


# ============================================================
# TEMPLATE-BASED FILE GENERATION
# ============================================================

def create_json_from_template(template_type, head_name,
                               model_name=None, texture_path=None):
    """
    Loads a JSON template, substitutes placeholders, and writes the result
    to the correct output path.

    Placeholders inside templates:
        [custom name]       → head_name (original casing)
        [lower custom name] → head_name.lower()
        [custom model name] → model_name
        [texture path]      → texture_path
    """
    lower_head_name = head_name.lower()

    if template_type not in TEMPLATE_REGISTRY:
        print(f"  ERROR: Unknown template type '{template_type}'.")
        return

    info = TEMPLATE_REGISTRY[template_type]
    template_path = info["template_file"]
    file_path = info["file_path"].replace("[lower custom name]", lower_head_name)

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_str = json.dumps(json.load(f))
    except Exception as e:
        print(f"  ERROR loading template '{template_path}': {e}")
        return

    template_str = template_str.replace("[custom name]",       head_name)
    template_str = template_str.replace("[lower custom name]", lower_head_name)
    template_str = template_str.replace("[custom model name]", model_name or "")
    template_str = template_str.replace("[texture path]",      texture_path or "")

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(json.loads(template_str), f, indent=4)
        print(f"  Created: {file_path}")
    except IOError as e:
        print(f"  ERROR writing '{file_path}': {e}")


# ============================================================
# USER ASSET COPYING (textures / sounds / models)
# ============================================================
#
# templates/CPH_RP/... already ships the assets for the built-in heads
# (Player, Herobrine): the copy_folder() call in main() puts those in
# place before this ever runs. These functions only need to reach into
# user_assets/ for anything a user has added for their OWN heads. If a
# file isn't in user_assets/ AND isn't already sitting in the output
# (i.e. it wasn't baked into templates/ either), we warn instead of
# silently shipping a broken pack.

def copy_user_texture(head_name, texture_path):
    """
    Copies a texture from user_assets/textures/<name>.<ext> to
    CPH_RP/<texture_path>.<ext>. Skipped if the destination already
    exists (built-in heads ship their texture via templates/).
    """
    dst_no_ext = f"CPH_RP/{texture_path}"
    if glob.glob(f"{dst_no_ext}.*"):
        return  # already present via templates/ baseline

    matches = glob.glob(f"{USER_ASSETS_DIR}/textures/{head_name}.*")
    if not matches:
        print(f"  WARNING: no texture found for '{head_name}' "
              f"(expected {USER_ASSETS_DIR}/textures/{head_name}.png).")
        return

    src = matches[0]
    dst = dst_no_ext + os.path.splitext(src)[1]
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  Copied texture: {src}  →  {dst}")


def copy_user_sound(sound):
    """
    Copies a custom sound from user_assets/sounds/<sound>.ogg to
    CPH_RP/sounds/skulls/<sound>.ogg. Skipped entirely for "default"
    (the shared fallback sound already ships via templates/).
    """
    if not sound or sound.lower() == "default":
        return

    dst = f"CPH_RP/sounds/skulls/{sound}.ogg"
    if os.path.exists(dst):
        return  # already present via templates/ baseline

    src = f"{USER_ASSETS_DIR}/sounds/{sound}.ogg"
    if not os.path.exists(src):
        print(f"  WARNING: no sound file found for '{sound}' (expected {src}).")
        return

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  Copied sound: {src}  →  {dst}")


def copy_user_model(model):
    """
    Copies a custom model's block geometry and attachable geometry from
    user_assets/models/... to CPH_RP/models/.... Skipped entirely for
    "head" (the shared default model already ships via templates/).
    """
    if not model or model.lower() == "head":
        return

    pairs = [
        (f"{USER_ASSETS_DIR}/models/blocks/{model}.geo.json",
         f"CPH_RP/models/blocks/{model}.geo.json",
         "block model"),
        (f"{USER_ASSETS_DIR}/models/entity/{model}_attachable.geo.json",
         f"CPH_RP/models/entity/{model}_attachable.geo.json",
         "attachable model"),
    ]

    for src, dst, label in pairs:
        if os.path.exists(dst):
            continue  # already present via templates/ baseline
        if not os.path.exists(src):
            print(f"  WARNING: no {label} found for '{model}' (expected {src}).")
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  Copied {label}: {src}  →  {dst}")


# ============================================================
# index.js UPDATE
# ============================================================

def update_index_js(head_name, sound):
    """
    Appends a [item_id, block_id, key, sound] tuple to the headArray
    inside CPH_BP/scripts/index.js.
    """
    file_name = "CPH_BP/scripts/index.js"
    lower_name = head_name.lower()
    lower_sound = sound.lower() if sound else "default"

    new_element = (
        f'["cph:{lower_name}_head", "cph:{lower_name}_head_block", '
        f'"{lower_name}_head", "head.{lower_sound}"]'
    )

    try:
        with open(file_name, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"  ERROR: {file_name} not found.")
        return

    match = re.search(r"const headArray = \[.*?\];", content, re.DOTALL)
    if not match:
        print(f"  ERROR: {file_name} does not contain the expected headArray definition.")
        return

    existing = match.group(0)[match.group(0).find("[") + 1:
                               match.group(0).rfind("]")].strip()
    if existing:
        updated = f"const headArray = [\n    {existing},\n    {new_element}\n];"
    else:
        updated = f"const headArray = [\n    {new_element}\n];"

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(content[: match.start()] + updated + content[match.end():])

    print(f"  Updated: {file_name}  (+{head_name})")


# ============================================================
# SHARED / AGGREGATE FILE GENERATION
# ============================================================

def create_sound_definitions(heads):
    """
    Writes sound_definitions.json with a "head.<sound>" entry for every
    unique non-default sound used across all heads, on top of the shared
    "head.default" fallback. Expects a matching .ogg to already exist at
    CPH_RP/sounds/skulls/<sound>.ogg (this script does not create audio).
    """
    file_name = "CPH_RP/sounds/sound_definitions.json"

    try:
        with open(file_name, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"format_version": "1.14.0", "sound_definitions": {}}

    for head in heads:
        sound = head["sound"]
        if not sound or sound.lower() == "default":
            continue
        lower_sound = sound.lower()
        data["sound_definitions"][f"head.{lower_sound}"] = {
            "category": "record",
            "max_distance": 48.0,
            "sounds": [f"sounds/skulls/{sound}"],
        }

    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"Created: {file_name}")


def create_place_sounds(head_names):
    """Writes blocks.json, assigning a place-sound to every head block."""
    file_name = "CPH_RP/blocks.json"
    data = {"format_version": "1.21.40"}
    for name in head_names:
        data[f"cph:{name.lower()}_head_block"] = {"sound": "stone"}

    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"Created: {file_name}")


def create_lang_file(heads):
    """Writes en_US.lang with display names for every head."""
    file_name = "CPH_RP/texts/en_US.lang"
    lines = []
    for head in heads:
        lower = head["name"].lower()
        display = head["display"]
        lines.append(f"tile.cph:{lower}_head_block.name={display}")
        lines.append(f"item.cph:{lower}_head={display}")

    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    with open(file_name, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Created: {file_name}")


def create_terrain_texture(head_names, head_textures):
    """Writes the combined terrain texture atlas JSON."""
    if len(head_names) != len(head_textures):
        raise ValueError("head_names and head_textures must be the same length.")

    file_name = "CPH_RP/textures/terrain_texture.json"
    texture_data = {
        f"{name.lower()}_head": {"textures": path}
        for name, path in zip(head_names, head_textures)
    }

    final = {
        "num_mip_levels":     4,
        "padding":            8,
        "resource_pack_name": "cph_head",
        "texture_name":       "atlas.terrain",
        "texture_data":       texture_data,
    }

    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=4)
    print(f"Created: {file_name}")


# ============================================================
# FOLDER COPY HELPER
# ============================================================

def copy_folder(src, dst):
    """Recursively copies src → dst, merging into any existing dst."""
    if not os.path.exists(src):
        print(f"  WARNING: Source folder does not exist: {src}")
        return
    os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)
    print(f"Copied template: {src}  →  {dst}")


# ============================================================
# MAIN
# ============================================================

def main():
    # 1. Seed output folders from templates
    print("=" * 60)
    print("Step 1: Copying template pack folders")
    print("=" * 60)
    copy_folder("templates/CPH_RP", "CPH_RP")
    copy_folder("templates/CPH_BP", "CPH_BP")

    # 2. Parse input CSV
    print("\n" + "=" * 60)
    print(f"Step 2: Reading {HEADS_CSV}")
    print("=" * 60)
    heads = parse_heads_csv(HEADS_CSV)
    print(f"  Loaded {len(heads)} head definitions.\n")

    head_names    = []
    head_textures = []

    # 3. Generate per-head files
    print("=" * 60)
    print("Step 3: Generating per-head files")
    print("=" * 60)

    for head in heads:
        name    = head["name"]
        sound   = head["sound"]
        model   = head["model"]
        texture = head["texture"]

        print(f"\n[{name}]  sound={sound}  model={model}  texture={texture}")

        # index.js entry
        update_index_js(name, sound)

        # Item and recipe files (generated for every head)
        create_json_from_template("items_rp",       name)
        create_json_from_template("items_bp",       name)
        create_json_from_template("recipe_toBlock", name)
        create_json_from_template("recipe_toHead",  name)

        # Block and attachable — skipped for special hand-crafted heads
        if name not in SPECIAL_HEADS:
            create_json_from_template("block",      name, model)
            create_json_from_template("attachable", name, model, texture)

        # Pull in the user's own texture/sound/model files (if this head
        # isn't one of the built-in ones already shipped via templates/)
        copy_user_texture(name, texture)
        copy_user_sound(sound)
        copy_user_model(model)

        head_names.append(name)
        head_textures.append(texture)

    # 4. Aggregate / shared files
    print("\n" + "=" * 60)
    print("Step 4: Writing shared pack files")
    print("=" * 60)
    create_place_sounds(head_names)
    create_lang_file(heads)
    create_terrain_texture(head_names, head_textures)
    create_sound_definitions(heads)

    print("\n" + "=" * 60)
    print(f"Done!  Generated files for {len(head_names)} heads.")
    print("=" * 60)


if __name__ == "__main__":
    main()
