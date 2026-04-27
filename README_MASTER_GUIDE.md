# Aesthetic Anchoring — Master File Guide
## Every file, every experiment, every command

---

## YOUR FILES

```
├── experiment_runner.py      ← Runs Experiments 1, 2, and 4 (API calls)
├── generate_uis.py           ← Runs Experiment 3 (UI generation + screenshots)
├── analyze_results.py        ← Analyzes results from ALL experiments
├── prompt_library.json       ← Single source of truth for all prompts/conditions
└── [your CSV results]        ← Output from each experiment run
```

---

## EXPERIMENT 1: EMOJI PERSISTENCE ✅ DONE

**Status:** Complete. 9,898 responses across 4 models.

**No action needed.** Results already analyzed. Key findings:
- Social media → 96% emoji rate at baseline
- Formality correlation r=0.83, p=0.041
- GLM stickiest model at 10.7% non-compliance

**To re-analyze if needed:**
```bash
python analyze_results.py --experiment 1 --input exp1_emoji_persistence_20260227_111102.csv
```

---

## EXPERIMENT 2: COLOR/GRADIENT BIAS ⬜ RUN THIS WEEK

**Status:** Pilot done (Qwen only, null result). Needs to run on all 4 models.

**What the script does:** Asks models to suggest color schemes for different
company types. Extracts hex colors from responses, converts to HSL, checks
if colors fall in the purple/pink hue range (270°–330°).

**Step 1 — Set your API keys:**
```bash
export OPENAI_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"
export TOGETHER_API_KEY="your-key"
```

**Step 2 — Run pilot (test with 2 runs per condition):**
```bash
python experiment_runner.py --experiment 2 --pilot
```
This produces ~120 API calls. Check the output CSV to make sure:
- `response_text` column is populated (not empty)
- `all_colors` column has hex codes (if empty, models may be using color
  names instead of hex — you'll need to fix the extraction)

**Step 3 — Run full (10 runs per condition):**
```bash
python experiment_runner.py --experiment 2 --full
```
Produces ~600 API calls total.

**Step 4 — Analyze:**
```bash
python analyze_results.py --experiment 2 --input exp2_color_bias_TIMESTAMP.csv
```

**Expected output file:** `exp2_color_bias_YYYYMMDD_HHMMSS.csv`

**What to look for:**
- Does any model suggest purple/pink more than chance (~16% of the hue wheel)?
- Do "tech startup" prompts get more purple than "healthcare"?
- If all models show 0% purple: that's a publishable null result

---

## EXPERIMENT 3: HUMAN UI DETECTION ⬜ START NEXT WEEK

**Status:** Script built. Needs to be run.

**This experiment has 3 phases:**

### Phase A — Generate 40 AI UIs (~2-3 hours)

**Step 1 — Install dependencies:**
```bash
pip install playwright
playwright install chromium
```

**Step 2 — Test with 8 UIs (1 per category):**
```bash
python generate_uis.py --pilot
```
Check `experiment_3_uis/screenshots_ai/` — open a few PNGs to make sure
they look like actual app screens, not broken HTML.

**Step 3 — Generate all 40:**
```bash
python generate_uis.py --full
```
This calls your 3 models (Gemini, GPT-3.5, GLM) to generate HTML for
8 app categories × 5 each = 40 UIs, then screenshots them automatically.

**Output:** `experiment_3_uis/screenshots_ai/` with 40 PNG files.

### Phase B — Collect 40 Human UIs (~60-90 min, manual)

**Step 1 — Print the collection guide:**
```bash
python generate_uis.py --collection-guide
```

**Step 2 — Go to Dribbble.com and for each of these 8 categories,
screenshot 5 different mobile app designs:**

| Category        | Search on Dribbble                         |
|-----------------|-------------------------------------------|
| Productivity    | "task management app mobile UI"            |
| Social media    | "social media app mobile UI design"        |
| Finance         | "banking app mobile UI"                    |
| Health/Fitness  | "fitness tracker app mobile UI"            |
| Food delivery   | "food delivery app mobile UI"              |
| Travel          | "travel booking app mobile UI"             |
| Music           | "music player app mobile UI"               |
| Education       | "education app mobile UI design"           |

**Rules:**
- Pick designs from DIFFERENT designers
- Choose polished, finished designs (not wireframes)
- Select main/home screen only
- Crop to 375 × 812 pixels
- Save as: `human_productivity_1.png`, `human_finance_2.png`, etc.

**Step 3 — Save all 40 images to:**
```
experiment_3_uis/screenshots_human/
```

### Phase C — Prepare Survey (~30 min)

**Step 1 — Randomize and anonymize:**
```bash
python generate_uis.py --survey-prep
```
This creates `experiment_3_uis/survey_images/` with 80 files named
`ui_001.png` through `ui_080.png` (randomized, no AI/human labels).
Also creates `answer_key_DO_NOT_SHARE.json`.

**Step 2 — Build the survey on Google Forms or Typeform:**

For each of the 80 images, create a page with:
1. The image displayed
2. "Is this human-designed or AI-generated?" (multiple choice: Human / AI)
3. "How confident are you?" (1-5 scale)
4. "What visual signals influenced your decision?" (checkboxes:
   color scheme, typography, spacing, layout, icon style,
   content realism, overall polish, other)
5. "Briefly describe the strongest signal" (short text, optional)

Add a demographics page at the start:
- Design experience level (none / some / professional)
- How often do you use mobile apps? (daily / weekly / rarely)

**Step 3 — Launch on Prolific (~$50-80):**
- Create Prolific study pointing to your survey
- Screen for: "Uses mobile apps regularly"
- Target: 30 participants
- Estimated time: 15-20 minutes
- Pay: ~$2.50-3.00 per participant

**Step 4 — Export results and analyze:**
```bash
# Export survey responses as CSV (e.g., from Google Forms)
python analyze_results.py --experiment 3 \
    --input exp3_survey_responses.csv \
    --answer-key experiment_3_uis/answer_key_DO_NOT_SHARE.json
```

---

## EXPERIMENT 4: MULTI-CONSTRAINT STRESS TEST ⬜ RUN THIS WEEK

**Status:** Script ready in experiment_runner.py. Not yet run.

**What the script does:** Gives models a writing task with progressively
more constraints stacked on top of each other:
1. No emojis
2. No emojis + no bullet points
3. No emojis + no bullets + no headers
4. ... up to 7 simultaneous constraints

Then measures which constraint breaks first as the load increases.

**Step 1 — Set API keys (same as Exp 2)**

**Step 2 — Run pilot:**
```bash
python experiment_runner.py --experiment 4 --pilot
```
~320 API calls. Check output CSV for populated columns.

**Step 3 — Run full:**
```bash
python experiment_runner.py --experiment 4 --full
```
~3,200 API calls across all models.

**Step 4 — Analyze:**
```bash
python analyze_results.py --experiment 4 --input exp4_multi_constraint_TIMESTAMP.csv
```

**Expected output file:** `exp4_multi_constraint_YYYYMMDD_HHMMSS.csv`

**What to look for:**
- The "compliance decay curve" — overall compliance drops as you stack constraints
- Which constraint breaks first (hypothesis: word count limit, then bullets)
- Which constraint is most robust (hypothesis: emoji suppression)
- Model differences in constraint prioritization

---

## ANALYZE EVERYTHING AT ONCE

Once you have all experiment CSVs in the same directory:
```bash
python analyze_results.py --all
```
This auto-detects files by name and runs the appropriate analysis for each.

---

## RECOMMENDED ORDER OF OPERATIONS

```
TODAY:
  1. python experiment_runner.py --experiment 4 --pilot
  2. python experiment_runner.py --experiment 4 --full
  3. python experiment_runner.py --experiment 2 --full

NEXT WEEK:
  4. pip install playwright && playwright install chromium
  5. python generate_uis.py --pilot
  6. python generate_uis.py --full
  7. Collect 40 human UIs from Dribbble (manual, ~90 min)
  8. python generate_uis.py --survey-prep

WEEK AFTER:
  9. Build survey on Google Forms
  10. Launch Prolific study (~$60)
  11. Wait 3-5 days for responses
  12. python analyze_results.py --all

THEN:
  13. Write the paper
```
