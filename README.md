# Aesthetic Anchoring in Large Language Models
## Research on Bias and Aesthetic Influence in AI Responses

A comprehensive research project investigating how aesthetic elements, visual anchors, and color palettes influence the outputs of large language models (LLMs) across different domains.

---

## 📋 Project Overview

This project runs a series of controlled experiments to measure and quantify aesthetic bias in LLM responses. We test models from OpenAI, Google, Anthropic, and Together AI across multiple conditions to identify patterns in how aesthetic choices influence model behavior.

**Key Research Questions:**
- How persistent are emoji choices across different models?
- Do color/gradient suggestions exhibit bias toward certain aesthetic preferences?
- Can humans distinguish between human-designed and AI-generated UIs?
- How do multiple simultaneous aesthetic constraints affect model outputs?

---

## 🏗️ Project Structure

```
├── experiment_runner.py          # Runs API-based experiments (1, 2, 4)
├── generate_uis.py              # Generates UI screenshots (Experiment 3)
├── analyze_results.py           # Analyzes results from all experiments
├── main.py                      # Entry point
├── prompt_library.json          # Master prompt/condition definitions
├── pyproject.toml               # Project dependencies & metadata
├── experiment_data/             # CSV results from each experiment
├── experiment_3_uis/            # Generated UIs and screenshots
│   ├── html/                    # HTML files for generated UIs
│   ├── screenshots_ai/          # PNG screenshots of UIs
│   └── manifest_ai.json         # Metadata for generated UIs
└── README_MASTER_GUIDE.md       # Detailed execution guide
```

---

## 🔬 Experiments

### Experiment 1: Emoji Persistence ✅
**Status:** Complete (9,898 responses)

Tests whether models consistently use emojis across different contexts and prompts.

**Results Location:** `experiment_data/exp1_emoji_persistence_*.csv`

```bash
# Re-analyze results
python analyze_results.py --experiment 1 --input exp1_emoji_persistence_20260227_111102.csv
```

**Key Findings:**
- Social media contexts show 96% emoji adoption
- Formality exhibits strong correlation (r=0.83, p=0.041)
- GLM shows highest non-compliance at 10.7%

---

### Experiment 2: Color/Gradient Bias ⚙️
**Status:** Pilot phase (Qwen only); pending full run

Tests whether models prefer specific color schemes and hues when suggesting color palettes for different company types.

**Setup:**
1. Export API keys:
```bash
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."
export ANTHROPIC_API_KEY="sk-ant-..."
export TOGETHER_API_KEY="..."
```

2. Run pilot (2 runs per condition, ~120 API calls):
```bash
python experiment_runner.py --experiment 2 --pilot
```

3. Run full experiment (10 runs per condition, ~600 API calls):
```bash
python experiment_runner.py --experiment 2 --full
```

4. Analyze results:
```bash
python analyze_results.py --experiment 2 --input exp2_color_bias_TIMESTAMP.csv
```

**Expected Output:** `experiment_data/exp2_color_bias_YYYYMMDD_HHMMSS.csv`

---

### Experiment 3: Human UI Detection 📱
**Status:** Ready to run; awaiting human study phase

Generates AI-created UIs and tests whether humans can distinguish them from human-designed interfaces.

**Phase A — Generate UIs:**

1. Install Playwright:
```bash
pip install playwright
playwright install chromium
```

2. Pilot run (8 UIs, 1 per category):
```bash
python generate_uis.py --pilot
```
Outputs: `experiment_3_uis/screenshots_ai/`

3. Generate full set (40 UIs):
```bash
python generate_uis.py --full
```

**Phase B — Human Study:**
Deploy via Prolific or UserTesting (manual setup required)

---

### Experiment 4: Multi-Constraint Bias 🎯
**Status:** Pilot phase; pending full analysis

Tests how models handle multiple simultaneous aesthetic constraints (e.g., "modern + colorful + minimalist").

**Run pilot:**
```bash
python experiment_runner.py --experiment 4 --pilot
```

**Run full:**
```bash
python experiment_runner.py --experiment 4 --full
```

**Analyze:**
```bash
python analyze_results.py --experiment 4 --input exp4_multi_constraint_TIMESTAMP.csv
```

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.12+
- pip or uv package manager
- API keys for: OpenAI, Google, Anthropic, Together AI

### Install Dependencies

```bash
# Using pip
pip install -r requirements.txt

# Or using uv (faster)
uv pip install -r requirements.txt

# Or using pyproject.toml
pip install -e .
```

**Required Packages:**
- `openai` — GPT models via OpenAI API
- `google-generativeai` — Gemini models
- `anthropic` — Claude models
- `langchain-openai`, `langchain-ollama` — Model abstraction
- `pandas` — Data analysis & CSV handling
- `matplotlib`, `seaborn` — Result visualization
- `scipy` — Statistical analysis
- `playwright` — Browser automation (Experiment 3)
- `python-dotenv` — Environment variable management

### Environment Setup

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...
TOGETHER_API_KEY=...
```

Or export as environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."
export ANTHROPIC_API_KEY="sk-ant-..."
export TOGETHER_API_KEY="..."
```

---

## 🚀 Quick Start

### Run a Quick Test
```bash
# Pilot Experiment 1 with 2 runs per condition
python experiment_runner.py --experiment 1 --pilot
```

### View Results
```bash
# Analyze Experiment 1 results
python analyze_results.py --experiment 1 --input experiment_data/exp1_emoji_persistence_20260227_111102.csv
```

### Generate UIs
```bash
# Generate 8 sample UIs for testing
python generate_uis.py --pilot
```

---

## 📊 Data & Results

### Output Formats

**Experiment Results CSV Columns:**
- `prompt_id` — Unique identifier for the prompt
- `model` — Model name (gpt-3.5, gpt-4, gemini-pro, etc.)
- `response_text` — Full model response
- `extracted_metric` — Parsed/extracted metric (emoji count, hex colors, etc.)
- `timestamp` — When response was generated

### Result Files
- `experiment_data/exp1_emoji_persistence_*.csv` — Experiment 1 results
- `experiment_data/exp2_color_bias_*.csv` — Experiment 2 results
- `experiment_data/exp4_multi_constraint_*.csv` — Experiment 4 results
- `experiment_3_uis/manifest_ai.json` — Experiment 3 UI metadata

### Analysis Output
All analysis generates:
- Summary statistics
- Visualizations (PNG plots)
- P-values and effect sizes
- Comparison tables across models

---

## 🔌 API Usage & Costs

| Model | Provider | Cost (per 1K tokens) | Status |
|-------|----------|---------------------|--------|
| GPT-3.5 Turbo | OpenAI | $0.0005 | ✅ Active |
| GPT-4 | OpenAI | $0.03 / $0.06 | ✅ Active |
| Gemini Pro | Google | Free (with limits) | ✅ Active |
| Claude 3 | Anthropic | $0.003 / $0.015 | ✅ Active |
| Llama 2 | Together AI | $0.0002 | ✅ Active |

**Cost Estimation:**
- Pilot run (~300 API calls): ~$2-5
- Full run (~1,500 API calls): ~$10-25
- Estimate before running: Review API costs in provider dashboards

---

## 📈 Analysis & Visualization

The `analyze_results.py` script generates:

1. **Summary Statistics**
   - Mean, std, median metrics per model
   - Effect sizes and confidence intervals

2. **Visualizations**
   - Box plots (model comparison)
   - Heatmaps (cross-condition effects)
   - Distribution plots

3. **Statistical Tests**
   - ANOVA (across models)
   - T-tests (pairwise comparisons)
   - Chi-square (categorical outcomes)

```bash
# Generate comprehensive analysis
python analyze_results.py --experiment 1 --input data.csv --visualize
```

---

## 🛠️ Development & Troubleshooting

### Common Issues

**"API Key not found"**
```bash
# Ensure keys are exported
echo $OPENAI_API_KEY  # Should print your key
# If empty, set it in .env or terminal
```

**"Module not found" errors**
```bash
# Reinstall dependencies
pip install --upgrade -e .
```

**Playwright installation issues**
```bash
pip install playwright
playwright install chromium
```

### Debug Mode

Run with verbose output:
```bash
python experiment_runner.py --experiment 1 --pilot --verbose
```

---

## 📝 Prompt Library

All prompts and experimental conditions are defined in `prompt_library.json`:

```json
{
  "experiment_1": {
    "category_1": [
      {
        "id": "emoji_social",
        "prompt": "...",
        "condition": "social_media"
      }
    ]
  }
}
```

Edit this file to modify prompts, add new conditions, or change model parameters.

---

## 📚 Documentation

- **Detailed Guide:** See [README_MASTER_GUIDE.md](README_MASTER_GUIDE.md) for comprehensive experiment walkthrough
- **Experiment 1:** Emoji persistence across domains
- **Experiment 2:** Color/gradient preference bias
- **Experiment 3:** Human UI vs AI UI detection
- **Experiment 4:** Multi-constraint aesthetic effects

---

## 👨‍💻 Contributing

To add new experiments:

1. Define prompts in `prompt_library.json`
2. Add experiment logic to `experiment_runner.py`
3. Add analysis logic to `analyze_results.py`
4. Document in this README

---

## 📄 License

Specify your project license here (MIT, Apache 2.0, etc.)

---

## 📧 Contact

For questions, contact: Dhinakaran Thangaraj

---

## Version History

- **v0.1.0** (Apr 2026) — Initial release
  - Experiments 1–4 implemented
  - Core analysis pipeline
  - UI generation framework
