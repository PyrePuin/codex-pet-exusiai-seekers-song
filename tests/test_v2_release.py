import hashlib
import json
import unittest
from pathlib import Path

from PIL import Image


RELEASE = Path(__file__).resolve().parents[1]
BASELINE = json.loads(
    (RELEASE / "tests/fixtures/v1-standard-rows.json").read_text(encoding="utf-8")
)


class ExusiaiV2ReleaseTests(unittest.TestCase):
    def test_manifest_is_v2_without_renaming_pet(self):
        data = json.loads((RELEASE / "pet.json").read_text(encoding="utf-8"))
        self.assertEqual(data["id"], "exusiai-seekers-song")
        self.assertEqual(data["displayName"], "新约能天使-寻翼之歌")
        self.assertEqual(data["spriteVersionNumber"], 2)

    def test_extended_atlas_geometry(self):
        with Image.open(RELEASE / "spritesheet.webp") as atlas:
            self.assertEqual(atlas.size, (1536, 2288))
            self.assertEqual(atlas.mode, "RGBA")

    def test_first_nine_rows_are_preserved(self):
        with Image.open(RELEASE / "spritesheet.webp") as atlas:
            rgba = atlas.convert("RGBA")
            for row in range(9):
                alpha = rgba.crop(
                    (0, row * 208, 1536, (row + 1) * 208)
                ).getchannel("A")
                actual = hashlib.sha256(alpha.tobytes()).hexdigest()
                self.assertEqual(actual, BASELINE[str(row)], f"row {row}")

    def test_direction_qa_artifacts_exist(self):
        for relative in (
            "preview/contact-sheet-v2.png",
            "preview/look-directions.png",
            "qa/direction-semantics.json",
            "qa/direction-blind-validation.json",
            "qa/look-continuity.json",
            "qa/validation-extended.json",
        ):
            self.assertTrue((RELEASE / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
