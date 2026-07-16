# 新约能天使-寻翼之歌 v2 十六向扩展 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变现有九个动作的前提下，把发布包升级为包含十六向视线的 Codex v2 桌宠。

**Architecture:** 当前 1536×1872 图集作为不可变的标准动作底座；仅通过 imagegen 生成四向锚点和两条各八帧的连续方向条。hatch-pet 脚本负责注册、组装、去色、方向 QA 和 1536×2288 v2 验证，最后原位更新同一桌宠 ID、安装目录和 GitHub 仓库。

**Tech Stack:** hatch-pet Python/Pillow 脚本、imagegen、JSON/jq、Python unittest、Git/GitHub CLI。

## Global Constraints

- ID 固定为 `exusiai-seekers-song`，显示名固定为 `新约能天使-寻翼之歌`。
- 前九行保留当前角色、美术和动作；只新增图集第 9、10 行。
- 最终图集必须为 `1536x2288`、8×11、RGBA WebP。
- `pet.json` 必须包含 `spriteVersionNumber: 2`。
- 四个基准方向必须明确：000 向上、090 屏幕右、180 向下、270 屏幕左。
- 两条方向行必须分别一次性生成完整八帧，不得拼接单个修补帧。
- 最终必须通过三个隔离盲测、逐方向语义检查、连续性检查和 `validate_atlas.py --require-v2`。

---

### Task 1: 建立 v2 验收测试和 v1 基线

**Files:**
- Create: `release/codex-pet-exusiai-seekers-song/tests/test_v2_release.py`
- Create: `release/codex-pet-exusiai-seekers-song/tests/fixtures/v1-standard-rows.json`
- Test: `release/codex-pet-exusiai-seekers-song/tests/test_v2_release.py`

**Interfaces:**
- Consumes: 当前 `release/codex-pet-exusiai-seekers-song/spritesheet.webp` 与 `pet.json`。
- Produces: 可重复验证尺寸、清单、前九行保真和 QA 产物的测试。

- [ ] **Step 1: 保存 v1 图集基线**

Run:

```bash
$PYTHON -c 'import hashlib,json; from pathlib import Path; from PIL import Image; p=Path("release/codex-pet-exusiai-seekers-song/spritesheet.webp"); im=Image.open(p).convert("RGBA"); rows={str(i):hashlib.sha256(im.crop((0,i*208,1536,(i+1)*208)).getchannel("A").tobytes()).hexdigest() for i in range(9)}; out=Path("release/codex-pet-exusiai-seekers-song/tests/fixtures/v1-standard-rows.json"); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(rows,indent=2)+"\n",encoding="utf-8")'
```

- [ ] **Step 2: 写入失败测试**

```python
import json
import hashlib
import unittest
from pathlib import Path

from PIL import Image


RELEASE = Path(__file__).resolve().parents[1]
BASELINE = json.loads((RELEASE / "tests/fixtures/v1-standard-rows.json").read_text(encoding="utf-8"))


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
                alpha = rgba.crop((0, row * 208, 1536, (row + 1) * 208)).getchannel("A")
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
```

- [ ] **Step 3: 运行测试确认红灯**

Run:

```bash
cd release/codex-pet-exusiai-seekers-song
$PYTHON -m unittest tests/test_v2_release.py
```

Expected: `spriteVersionNumber` 缺失或图集尺寸仍为 1536×1872，测试失败。

- [ ] **Step 4: 提交测试**

```bash
git add tests/test_v2_release.py tests/fixtures/v1-standard-rows.json
git commit -m "test: define v2 pet release contract"
```

### Task 2: 准备升级运行目录与视线机制

**Files:**
- Create: `work/hatch-pet/exusiai-seekers-song-v2/pet_request.json`
- Create: `work/hatch-pet/exusiai-seekers-song-v2/imagegen-jobs.json`
- Create: `work/hatch-pet/exusiai-seekers-song-v2/qa/look-mechanics.md`
- Copy: `work/hatch-pet/exusiai-seekers-song-v2/decoded/*.png`
- Copy: `work/hatch-pet/exusiai-seekers-song-v2/frames/`
- Copy: `work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet.webp`

**Interfaces:**
- Consumes: 已通过验收的当前运行目录和 v1 发布图集。
- Produces: 九个标准任务已完成、三个视线任务待执行的 v2 job graph。

- [ ] **Step 1: 复制已批准的标准动作运行素材到 v2 目录**

Run:

```bash
$PYTHON /Users/mr.puin/.codex/skills/hatch-pet/scripts/prepare_pet_run.py --pet-name '新约能天使-寻翼之歌' --pet-id exusiai-seekers-song --display-name '新约能天使-寻翼之歌' --description '《明日方舟》新约能天使·寻翼之歌同人 Codex 桌宠，包含九个状态动画与十六向视线。' --reference release/codex-pet-exusiai-seekers-song/preview/contact-sheet.png --reference assets/exusiai-seekers-song/full-character-reference.png --output-dir work/hatch-pet/exusiai-seekers-song-v2 --pet-notes '保持当前三头半精致Q版形象、红发黑帽光环白色光翼、红黑服装与鲁特琴；只新增十六向视线。' --style-preset auto --style-notes '精致日系手游Q版赛璐璐风格，角色灵巧自信，身份、比例、光翼与琴严格一致。' --chroma-key '#00FF00' --force
mkdir -p work/hatch-pet/exusiai-seekers-song-v2/final work/hatch-pet/exusiai-seekers-song-v2/qa work/hatch-pet/exusiai-seekers-song-v2/frames/idle work/hatch-pet/exusiai-seekers-song-v2/decoded
cp release/codex-pet-exusiai-seekers-song/spritesheet.webp work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet.webp
cp release/codex-pet-exusiai-seekers-song/preview/contact-sheet.png work/hatch-pet/exusiai-seekers-song-v2/qa/contact-sheet.png
$PYTHON -c 'from pathlib import Path; from PIL import Image; root=Path("work/hatch-pet/exusiai-seekers-song-v2"); cell=Image.open(root/"final/spritesheet.webp").convert("RGBA").crop((0,0,192,208)); cell.save(root/"frames/idle/00.png"); cell.save(root/"decoded/base.png"); cell.save(root/"references/canonical-base.png")'
```

- [ ] **Step 2: 把内部清单统一为正式名称**

Run:

```bash
tmp=$(mktemp)
jq '(.jobs[] | select(.id == "base" or .id == "idle" or .id == "running-right" or .id == "running-left" or .id == "waving" or .id == "jumping" or .id == "failed" or .id == "waiting" or .id == "running" or .id == "review")) += {status:"complete", source_path:"release/codex-pet-exusiai-seekers-song/spritesheet.webp", completed_at:"2026-07-16T00:00:00Z"}' work/hatch-pet/exusiai-seekers-song-v2/imagegen-jobs.json > "$tmp"
mv "$tmp" work/hatch-pet/exusiai-seekers-song-v2/imagegen-jobs.json
perl -pi -e 's/flat pure blue #0000FF/flat pure green #00FF00/g' work/hatch-pet/exusiai-seekers-song-v2/prompts/look-cardinals.md work/hatch-pet/exusiai-seekers-song-v2/prompts/rows/look-row-9.md work/hatch-pet/exusiai-seekers-song-v2/prompts/rows/look-row-10.md
```

- [ ] **Step 3: 写入视线机制**

`qa/look-mechanics.md` must state that eyes and eyelids lead, head/neck and upper torso follow subtly, feet and lower torso stay anchored, hat/halo/hair follow the head, light wings stay attached, and the lute remains held with continuous occlusion and perspective.

- [ ] **Step 4: 验证九个标准动作底座**

Run:

```bash
$PYTHON /Users/mr.puin/.codex/skills/hatch-pet/scripts/validate_atlas.py work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet.webp --json-out work/hatch-pet/exusiai-seekers-song-v2/final/validation-standard.json
```

Expected: `ok: true`, `columns: 8`, `rows: 9`, no errors or warnings.

### Task 3: 生成并批准四向锚点

**Files:**
- Create: `work/hatch-pet/exusiai-seekers-song-v2/decoded/look-cardinals.png`
- Create: `work/hatch-pet/exusiai-seekers-song-v2/decoded/look-anchors/*.png`
- Create: `work/hatch-pet/exusiai-seekers-song-v2/decoded/look-anchors-approved.png`
- Create: `work/hatch-pet/exusiai-seekers-song-v2/qa/cardinal-anchors.json`

**Interfaces:**
- Consumes: canonical base、标准动作 contact sheet、layout guide 和 `qa/look-mechanics.md`。
- Produces: 顺序固定为 000/090/180/270 的已批准锚点条。

- [ ] **Step 1: 用 imagegen 生成一个四姿势横条**

Attach every image listed for `look-cardinals` in `imagegen-jobs.json`; output exactly four full-body poses on `#00FF00`, with unmistakable up/right/down/left gaze.

- [ ] **Step 2: 提取并检查四个锚点**

```bash
$PYTHON /Users/mr.puin/.codex/skills/hatch-pet/scripts/extract_cardinal_anchors.py --strip work/hatch-pet/exusiai-seekers-song-v2/decoded/look-cardinals.png --output-dir work/hatch-pet/exusiai-seekers-song-v2/decoded/look-anchors --chroma-key '#00FF00' --json-out work/hatch-pet/exusiai-seekers-song-v2/qa/cardinal-anchors.json
$PYTHON /Users/mr.puin/.codex/skills/hatch-pet/scripts/compose_cardinal_anchor_strip.py --anchors-dir work/hatch-pet/exusiai-seekers-song-v2/decoded/look-anchors --output work/hatch-pet/exusiai-seekers-song-v2/decoded/look-anchors-approved.png
```

Expected: four non-clipped, full-body anchors; 090 and 270 visibly相反，000/180 的眼睑和头部俯仰明确。

- [ ] **Step 3: 将 `look-cardinals` 标记完成**

Update only that job with `status: "complete"`, selected `source_path`, and UTC `completed_at`.

### Task 4: 生成、注册并检查方向第 9 行

**Files:**
- Create: `work/hatch-pet/exusiai-seekers-song-v2/decoded/look-row-9.png`
- Create: `work/hatch-pet/exusiai-seekers-song-v2/qa/look-row-9-registered.png`
- Create: `work/hatch-pet/exusiai-seekers-song-v2/qa/look-row-9-registration.json`

**Interfaces:**
- Consumes: 已批准四向锚点。
- Produces: 000→157.5 的八个连续方向与固定注册参数。

- [ ] **Step 1: 用 imagegen 一次性生成八个连续方向**

Generate exactly `000, 022.5, 045, 067.5, 090, 112.5, 135, 157.5` as one coherent strip. Do not repair or compose individual cells.

- [ ] **Step 2: 注册并执行边缘检查**

```bash
$PYTHON /Users/mr.puin/.codex/skills/hatch-pet/scripts/assemble_extended_atlas.py --base-atlas work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet.webp --look-row-9 work/hatch-pet/exusiai-seekers-song-v2/decoded/look-row-9.png --neutral-cell work/hatch-pet/exusiai-seekers-song-v2/frames/idle/00.png --chroma-key '#00FF00' --chroma-threshold 96 --registered-row-output work/hatch-pet/exusiai-seekers-song-v2/qa/look-row-9-registered.png --registration-manifest-output work/hatch-pet/exusiai-seekers-song-v2/qa/look-row-9-registration.json
```

Expected: eight ordered groups, no clipping, stable scale and baseline.

- [ ] **Step 3: 检查方向语义和 157.5→180 连续性后标记完成**

Cardinal 000/090 and all right-half quadrants must be correct. Any hard failure regenerates the whole row.

### Task 5: 生成并组装方向第 10 行

**Files:**
- Create: `work/hatch-pet/exusiai-seekers-song-v2/decoded/look-row-10.png`
- Create: `work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet-extended.webp`
- Create: `work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet-extended.json`

**Interfaces:**
- Consumes: 四向锚点、第 9 行和其固定注册参数。
- Produces: 完整 8×11 图集。

- [ ] **Step 1: 用 imagegen 一次性生成第二组八方向**

Generate exactly `180, 202.5, 225, 247.5, 270, 292.5, 315, 337.5` using row 9 for identity and boundary continuity.

- [ ] **Step 2: 使用第 9 行固定注册参数组装扩展图集**

```bash
$PYTHON /Users/mr.puin/.codex/skills/hatch-pet/scripts/assemble_extended_atlas.py --base-atlas work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet.webp --registered-row-9 work/hatch-pet/exusiai-seekers-song-v2/qa/look-row-9-registered.png --row-9-registration work/hatch-pet/exusiai-seekers-song-v2/qa/look-row-9-registration.json --look-row-10 work/hatch-pet/exusiai-seekers-song-v2/decoded/look-row-10.png --neutral-cell work/hatch-pet/exusiai-seekers-song-v2/frames/idle/00.png --chroma-key '#00FF00' --chroma-threshold 96 --output work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet-extended.png --webp-output work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet-extended.webp --manifest-output work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet-extended.json
```

- [ ] **Step 3: 执行唯一一次最终边缘去色并验证 v2**

```bash
$PYTHON /Users/mr.puin/.codex/skills/hatch-pet/scripts/despill_chroma_edges.py work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet-extended.png --output work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet-extended.png --webp-output work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet-extended.webp --chroma-key '#00FF00' --json-out work/hatch-pet/exusiai-seekers-song-v2/qa/chroma-despill-extended.json
$PYTHON /Users/mr.puin/.codex/skills/hatch-pet/scripts/validate_atlas.py work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet-extended.webp --json-out work/hatch-pet/exusiai-seekers-song-v2/final/validation-extended.json --chroma-key '#00FF00' --require-v2
```

Expected: `ok: true`, 1536×2288, 8×11, no chroma or transparency errors.

### Task 6: 完成方向专项 QA 与三个隔离盲测

**Files:**
- Create: `work/hatch-pet/exusiai-seekers-song-v2/qa/contact-sheet-extended.png`
- Create: `work/hatch-pet/exusiai-seekers-song-v2/qa/look-directions.png`
- Create: `work/hatch-pet/exusiai-seekers-song-v2/qa/direction-semantics.json`
- Create: `work/hatch-pet/exusiai-seekers-song-v2/qa/direction-blind-verdicts-{1,2,3}.json`
- Create: `work/hatch-pet/exusiai-seekers-song-v2/qa/direction-blind-validation.json`
- Create: `work/hatch-pet/exusiai-seekers-song-v2/qa/look-continuity.json`

**Interfaces:**
- Consumes: 完整 v2 图集。
- Produces: 可审计的逐方向语义、盲测多数结论和连续性报告。

- [ ] **Step 1: 生成 QA 图和连续性报告**

Run:

```bash
$PYTHON /Users/mr.puin/.codex/skills/hatch-pet/scripts/make_contact_sheet.py work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet-extended.webp --output work/hatch-pet/exusiai-seekers-song-v2/qa/contact-sheet-extended.png
$PYTHON /Users/mr.puin/.codex/skills/hatch-pet/scripts/make_direction_qa_sheet.py work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet-extended.webp --output work/hatch-pet/exusiai-seekers-song-v2/qa/look-directions.png
$PYTHON /Users/mr.puin/.codex/skills/hatch-pet/scripts/make_direction_blind_qa_sheet.py work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet-extended.webp --output work/hatch-pet/exusiai-seekers-song-v2/qa/direction-blind-pairs.png --answer-key work/hatch-pet/exusiai-seekers-song-v2/qa/direction-blind-answer-key.json
$PYTHON /Users/mr.puin/.codex/skills/hatch-pet/scripts/measure_direction_continuity.py work/hatch-pet/exusiai-seekers-song-v2/final/spritesheet-extended.webp --json-out work/hatch-pet/exusiai-seekers-song-v2/qa/look-continuity.json
```

- [ ] **Step 2: 三个隔离视觉 reviewer 仅查看盲测 A/B 图**

Each reviewer must classify all shown pairs without seeing labels, atlas, answer key, prompts, or another verdict. Save each exact JSON result separately.

- [ ] **Step 3: 合并多数结论并应用隐藏答案**

Run:

```bash
$PYTHON /Users/mr.puin/.codex/skills/hatch-pet/scripts/combine_direction_blind_verdicts.py --verdicts work/hatch-pet/exusiai-seekers-song-v2/qa/direction-blind-verdicts-1.json --verdicts work/hatch-pet/exusiai-seekers-song-v2/qa/direction-blind-verdicts-2.json --verdicts work/hatch-pet/exusiai-seekers-song-v2/qa/direction-blind-verdicts-3.json --json-out work/hatch-pet/exusiai-seekers-song-v2/qa/direction-blind-verdicts.json
$PYTHON /Users/mr.puin/.codex/skills/hatch-pet/scripts/validate_direction_blind_verdicts.py --answer-key work/hatch-pet/exusiai-seekers-song-v2/qa/direction-blind-answer-key.json --verdicts work/hatch-pet/exusiai-seekers-song-v2/qa/direction-blind-verdicts.json --json-out work/hatch-pet/exusiai-seekers-song-v2/qa/direction-blind-validation.json
```

Expected: `direction-blind-validation.json` has `ok: true`; cardinal pairs contain no mismatch or ambiguity.

- [ ] **Step 4: 独立最终视觉 QA**

Inspect standard and extended contact sheets, all previews, labeled directions, semantics, blind validation, continuity and atlas validation. Record all 16 directions in `direction-semantics.json`; no `fail` may remain.

### Task 7: 发布、安装、测试与推送

**Files:**
- Modify: `release/codex-pet-exusiai-seekers-song/pet.json`
- Modify: `release/codex-pet-exusiai-seekers-song/spritesheet.webp`
- Modify: `release/codex-pet-exusiai-seekers-song/README.md`
- Create: `release/codex-pet-exusiai-seekers-song/preview/contact-sheet-v2.png`
- Create: `release/codex-pet-exusiai-seekers-song/preview/look-directions.png`
- Create: `release/codex-pet-exusiai-seekers-song/qa/*.json`
- Modify: `/Users/mr.puin/Documents/Codex/2026-07-14/an-zhu/tests/test_exusiai_release.py`
- Modify: `/Users/mr.puin/.codex/pets/exusiai-seekers-song/pet.json`
- Modify: `/Users/mr.puin/.codex/pets/exusiai-seekers-song/spritesheet.webp`

**Interfaces:**
- Consumes: 已通过全部 QA 的 v2 图集和报告。
- Produces: 同一 ID 的已安装、已发布、可复现 v2 桌宠。

- [ ] **Step 1: 更新发布包和中文 README**

Copy the validated extended atlas and selected QA files; add `spriteVersionNumber: 2`; document that 16-direction gaze follows pointer direction while keeping the README Chinese-first and without Petdex submission steps.

- [ ] **Step 2: 安装到同一桌宠目录**

Copy `pet.json` and `spritesheet.webp` together into `/Users/mr.puin/.codex/pets/exusiai-seekers-song/`.

- [ ] **Step 3: 重跑全部测试和验证**

Update `test_exusiai_release.py` so the manifest assertion requires `spriteVersionNumber == 2` and the geometry assertion requires `(1536, 2288)` while retaining the Chinese-first, no-Petdex, final-name, state-preview, and RGBA checks.

```bash
$PYTHON -m unittest /Users/mr.puin/Documents/Codex/2026-07-14/an-zhu/tests/test_exusiai_release.py
cd /Users/mr.puin/Documents/Codex/2026-07-14/an-zhu/release/codex-pet-exusiai-seekers-song
$PYTHON -m unittest tests/test_v2_release.py
$PYTHON /Users/mr.puin/.codex/skills/hatch-pet/scripts/validate_atlas.py spritesheet.webp --json-out /private/tmp/exusiai-v2-final-validation.json --chroma-key '#00FF00' --require-v2
```

Expected: all tests pass and validator returns `ok: true` with no errors or warnings.

- [ ] **Step 4: 提交并推送 GitHub**

```bash
git add README.md pet.json spritesheet.webp preview qa docs tests
git commit -m "feat: add 16-direction v2 pet support"
git push origin main
```

- [ ] **Step 5: 远端逐文件核对**

Compare the GitHub `main` tree blob SHAs with local `git ls-files -s`; report the remote commit SHA and restart requirement.
