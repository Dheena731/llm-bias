"""
Experiment 3: AI-Generated UI Detection Study
==============================================
Phase 1: Generate 40 AI UIs from LLMs and render to screenshots.

This script:
  1. Prompts your LLM models to generate React+Tailwind mobile app UIs
  2. Saves each as a standalone HTML file (self-contained, no build needed)
  3. Renders each HTML to a PNG screenshot using a headless browser
  4. Organizes outputs into folders for the survey

Requirements:
    pip install openai anthropic google-generativeai playwright
    playwright install chromium

Usage:
    python generate_uis.py --pilot          # Generate 2 UIs to test
    python generate_uis.py --full           # Generate all 40 UIs
    python generate_uis.py --render-only    # Just render existing HTML files
    python generate_uis.py --survey-prep    # Prepare randomized survey images
"""

import os
import re
import json
import time
import random
import argparse
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────

APP_CATEGORIES = [
    "productivity / task management",
    "social media / messaging",
    "finance / banking",
    "health / fitness tracking",
    "food delivery / restaurant ordering",
    "travel / hotel booking",
    "music / audio streaming",
    "online education / course learning",
]

# 5 UIs per category × 8 categories = 40 total
UIS_PER_CATEGORY = 5

MODELS = [
    {"id": "xiaomi/mimo-v2-flash", "provider": "together", "short": "mimo"},
]

OUTPUT_DIR = "experiment_3_uis"
HTML_DIR = f"{OUTPUT_DIR}/html"
SCREENSHOT_DIR = f"{OUTPUT_DIR}/screenshots_ai"
SURVEY_DIR = f"{OUTPUT_DIR}/survey_images"

GENERATION_PROMPT = """Create a complete, visually polished UI for a {category} mobile app.

Requirements:
- Design the main screen with realistic content (use real-looking text, not lorem ipsum)
- Use a professional color scheme appropriate for this type of app
- Include proper spacing, typography, and visual hierarchy
- Add realistic UI elements: navigation, cards, buttons, icons (use Unicode symbols for icons)
- Make it look like a real production app, not a wireframe

Technical requirements:
- Write a SINGLE self-contained HTML file
- Use inline CSS (no external stylesheets)
- Design for mobile viewport: 375px wide, 812px tall (iPhone size)
- Set the body/html to exactly 375px × 812px with overflow hidden
- Use system fonts: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif
- DO NOT use any external dependencies, CDNs, or imports
- DO NOT use JavaScript — pure HTML and CSS only
- DO NOT include any <script> tags

Output ONLY the HTML code, nothing else. No explanations, no markdown fences.
Start with <!DOCTYPE html> and end with </html>.
"""

# ── Model Calling ────────────────────────────────────────────────────────────

def call_model(model_config: dict, prompt: str) -> str:
    """Call an LLM and return the response text."""
    model_id = model_config["id"]
    provider = model_config["provider"]
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

    if provider == "openai":
        from openai import OpenAI
        client = OpenAI(
            api_key=openrouter_api_key or os.getenv("OPENAI_API_KEY"),
            base_url="https://openrouter.ai/api/v1" if openrouter_api_key else None,
        )
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.8,
        )
        return response.choices[0].message.content

    elif provider == "google":
        if openrouter_api_key:
            from openai import OpenAI
            client = OpenAI(
                api_key=openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
            )
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.8,
            )
            return response.choices[0].message.content

        import google.generativeai as genai
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=4096,
                temperature=0.8,
            ),
        )
        return response.text

    elif provider == "together":
        from openai import OpenAI
        client = OpenAI(
            api_key=openrouter_api_key or os.environ.get("TOGETHER_API_KEY"),
            base_url="https://openrouter.ai/api/v1" if openrouter_api_key else "https://api.together.xyz/v1",
        )
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.8,
        )
        return response.choices[0].message.content

    elif provider == "ollama":
        import subprocess
        result = subprocess.run(
            ["ollama", "run", model_id.replace("ollama:", "")],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.stdout

    else:
        raise ValueError(f"Unknown provider: {provider}")


def extract_html(response: str) -> str:
    """Extract HTML from model response, handling markdown fences."""
    # Remove markdown code fences if present
    response = re.sub(r'^```html?\s*\n?', '', response, flags=re.MULTILINE)
    response = re.sub(r'\n?```\s*$', '', response, flags=re.MULTILINE)
    response = response.strip()

    # Find the HTML document
    match = re.search(r'(<!DOCTYPE html>.*?</html>)', response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1)

    # If no DOCTYPE, try finding <html>
    match = re.search(r'(<html.*?</html>)', response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1)

    # Last resort: if it looks like HTML, wrap it
    if '<div' in response or '<body' in response:
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=375">
<style>* {{margin:0;padding:0;box-sizing:border-box}} body {{width:375px;height:812px;overflow:hidden;font-family:-apple-system,sans-serif}}</style>
</head><body>{response}</body></html>"""

    return ""


# ── Generation ───────────────────────────────────────────────────────────────

def build_generation_jobs(pilot: bool = False) -> list[dict]:
    """Build the list of UI generation jobs in a deterministic order."""
    n_per_category = 1 if pilot else UIS_PER_CATEGORY
    jobs = []
    total = 0

    for category in APP_CATEGORIES:
        for ui_idx in range(n_per_category):
            model_config = MODELS[ui_idx % len(MODELS)]
            total += 1

            cat_slug = category.split("/")[0].strip().replace(" ", "_")
            filename = f"ai_{cat_slug}_{ui_idx+1}_{model_config['short']}"

            jobs.append({
                "job_number": total,
                "category": category,
                "ui_index": ui_idx + 1,
                "model_config": model_config,
                "filename": filename,
                "prompt": GENERATION_PROMPT.replace("{category}", category),
            })

    return jobs


def run_generation_job(job: dict) -> dict:
    """Execute a single UI generation job."""
    response = call_model(job["model_config"], job["prompt"])
    html = extract_html(response)

    if not html:
        raise ValueError("Could not extract HTML from response")

    html_path = f"{HTML_DIR}/{job['filename']}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    return {
        "manifest_entry": {
            "id": job["filename"],
            "category": job["category"],
            "model": job["model_config"]["id"],
            "model_short": job["model_config"]["short"],
            "html_file": html_path,
            "source": "ai",
            "generated_at": datetime.now().isoformat(),
        },
        "html_path": html_path,
        "html_length": len(html),
    }


def generate_uis(pilot: bool = False, workers: int = 1):
    """Generate AI UIs from all models."""
    os.makedirs(HTML_DIR, exist_ok=True)

    jobs = build_generation_jobs(pilot=pilot)
    manifest = []
    errors = 0

    workers = max(1, workers)
    print(f"Generating {len(jobs)} UIs with {workers} worker(s)...")

    for job in jobs:
        print(
            f"[{job['job_number']}] Queued: {job['category']} | "
            f"{job['model_config']['short']} | #{job['ui_index']}"
        )

    if workers == 1:
        for job in jobs:
            print(
                f"[{job['job_number']}] Generating: {job['category']} | "
                f"{job['model_config']['short']} | #{job['ui_index']}"
            )
            try:
                result = run_generation_job(job)
                manifest.append(result["manifest_entry"])
                print(f"  Saved: {result['html_path']} ({result['html_length']} chars)")
            except Exception as e:
                print(f"  ERROR: {e}")
                errors += 1

            time.sleep(1)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_job = {
                executor.submit(run_generation_job, job): job for job in jobs
            }

            for future in as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    result = future.result()
                    manifest.append(result["manifest_entry"])
                    print(
                        f"[{job['job_number']}] Saved: {result['html_path']} "
                        f"({result['html_length']} chars)"
                    )
                except Exception as e:
                    print(
                        f"[{job['job_number']}] ERROR: {job['category']} | "
                        f"{job['model_config']['short']} | #{job['ui_index']} -> {e}"
                    )
                    errors += 1

                time.sleep(0.25)

    manifest.sort(key=lambda item: item["id"])

    # Save manifest
    manifest_path = f"{OUTPUT_DIR}/manifest_ai.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nGeneration complete: {len(manifest)} UIs generated, {errors} errors")
    print(f"Manifest saved to {manifest_path}")
    return manifest


# ── Rendering ────────────────────────────────────────────────────────────────

def render_single_screenshot(html_file: Path):
    """Render one HTML file to a PNG screenshot using Playwright."""
    from playwright.sync_api import sync_playwright

    png_path = f"{SCREENSHOT_DIR}/{html_file.stem}.png"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 375, "height": 812})
        page.goto(f"file://{html_file.resolve()}")
        page.wait_for_timeout(1000)
        page.screenshot(path=png_path, clip={
            "x": 0, "y": 0, "width": 375, "height": 812
        })
        browser.close()

    return png_path


def render_screenshots(workers: int = 1):
    """Render all HTML files to PNG screenshots using Playwright."""
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        print("Install playwright: pip install playwright && playwright install chromium")
        return

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    html_files = sorted(Path(HTML_DIR).glob("*.html"))

    if not html_files:
        print(f"No HTML files found in {HTML_DIR}")
        return

    workers = max(1, workers)
    print(f"Rendering {len(html_files)} HTML files to screenshots with {workers} worker(s)...")

    if workers == 1:
        for html_file in html_files:
            png_path = f"{SCREENSHOT_DIR}/{html_file.stem}.png"
            print(f"  Rendering: {html_file.name} -> {png_path}")

            try:
                render_single_screenshot(html_file)
            except Exception as e:
                print(f"    ERROR: {e}")
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_file = {
                executor.submit(render_single_screenshot, html_file): html_file
                for html_file in html_files
            }

            for future in as_completed(future_to_file):
                html_file = future_to_file[future]
                try:
                    png_path = future.result()
                    print(f"  Rendered: {html_file.name} -> {png_path}")
                except Exception as e:
                    print(f"  ERROR: {html_file.name} -> {e}")

    print(f"Screenshots saved to {SCREENSHOT_DIR}/")


# ── Survey Preparation ───────────────────────────────────────────────────────

def prepare_survey():
    """
    Combine AI and human screenshots into a randomized survey set.

    BEFORE running this:
    1. Collect 40 human-designed UI screenshots from Dribbble/Behance
    2. Crop/resize them to 375×812 px
    3. Save them in: experiment_3_uis/screenshots_human/
       Named: human_productivity_1.png, human_social_media_2.png, etc.
    """
    os.makedirs(SURVEY_DIR, exist_ok=True)

    ai_images = sorted(Path(SCREENSHOT_DIR).glob("ai_*.png"))
    human_dir = f"{OUTPUT_DIR}/screenshots_human"
    human_images = sorted(Path(human_dir).glob("human_*.png")) if os.path.exists(human_dir) else []

    print(f"AI images found: {len(ai_images)}")
    print(f"Human images found: {len(human_images)}")

    if not human_images:
        print(f"\nNo human images found in {human_dir}/")
        print("To collect human-designed UIs:")
        print("  1. Go to dribbble.com and search for each app category + 'mobile app UI'")
        print("  2. Screenshot 5 designs per category (8 categories = 40 total)")
        print("  3. Crop each to 375x812 pixels")
        print(f"  4. Save in {human_dir}/ as human_[category]_[number].png")
        print("  5. Re-run: python generate_uis.py --survey-prep")
        return

    # Build combined list
    all_images = []
    for img in ai_images:
        all_images.append({"path": str(img), "source": "ai", "original_name": img.name})
    for img in human_images:
        all_images.append({"path": str(img), "source": "human", "original_name": img.name})

    # Randomize
    random.seed(42)  # Reproducible randomization
    random.shuffle(all_images)

    # Copy with anonymized names
    answer_key = []
    for idx, img in enumerate(all_images, 1):
        new_name = f"ui_{idx:03d}.png"
        dest = f"{SURVEY_DIR}/{new_name}"

        # Copy file
        import shutil
        shutil.copy2(img["path"], dest)

        answer_key.append({
            "survey_id": new_name,
            "survey_number": idx,
            "true_source": img["source"],
            "original_file": img["original_name"],
        })

    # Save answer key (DO NOT share with participants)
    key_path = f"{OUTPUT_DIR}/answer_key_DO_NOT_SHARE.json"
    with open(key_path, "w") as f:
        json.dump(answer_key, f, indent=2)

    print(f"\nSurvey prepared: {len(all_images)} images in {SURVEY_DIR}/")
    print(f"  AI: {sum(1 for x in answer_key if x['true_source']=='ai')}")
    print(f"  Human: {sum(1 for x in answer_key if x['true_source']=='human')}")
    print(f"Answer key saved to {key_path}")
    print(f"\nNext: Upload images to Google Forms/Typeform and create the survey.")
    print(f"See prompt_library.json → experiment_3_ui_detection → study_design for survey questions.")


# ── Dribbble Collection Guide ────────────────────────────────────────────────

def print_collection_guide():
    """Print step-by-step instructions for collecting human UIs."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║       COLLECTING HUMAN-DESIGNED UIs — STEP BY STEP              ║
╚══════════════════════════════════════════════════════════════════╝

For each of the 8 categories below, collect 5 screenshots from Dribbble:

CATEGORY                          SEARCH QUERY ON DRIBBBLE
─────────────────────────────────────────────────────────────────
1. Productivity                   "task management app mobile UI"
2. Social media                   "social media app mobile UI design"
3. Finance                        "banking app mobile UI"
4. Health / Fitness               "fitness tracker app mobile UI"
5. Food delivery                  "food delivery app mobile UI"
6. Travel                         "travel booking app mobile UI"
7. Music streaming                "music player app mobile UI"
8. Education                      "education app mobile UI design"

RULES FOR SELECTION:
  ✓ Pick designs from DIFFERENT designers (check the author name)
  ✓ Choose completed, polished designs (not wireframes or sketches)
  ✓ Select the main/home screen only
  ✓ Avoid designs that have Dribbble watermarks or text overlays
  ✓ Pick a mix of visual styles (not all minimal, not all colorful)

SCREENSHOT PROCESS:
  1. Open the Dribbble shot in full view
  2. Screenshot just the phone mockup (crop out the background)
  3. Resize to exactly 375 × 812 pixels (use any image editor)
  4. Save as PNG

NAMING CONVENTION:
  human_productivity_1.png
  human_productivity_2.png
  human_social_media_1.png
  human_finance_1.png
  ... etc.

SAVE LOCATION:
  experiment_3_uis/screenshots_human/

TOTAL: 8 categories × 5 screenshots = 40 human-designed UIs
TIME ESTIMATE: ~60-90 minutes

After collecting all 40 human UIs, run:
  python generate_uis.py --survey-prep
""")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Experiment 3: AI UI Generation")
    parser.add_argument("--pilot", action="store_true", help="Generate 1 UI per category (test run)")
    parser.add_argument("--full", action="store_true", help="Generate all 40 UIs")
    parser.add_argument("--render-only", action="store_true", help="Render existing HTML to screenshots")
    parser.add_argument("--survey-prep", action="store_true", help="Prepare randomized survey images")
    parser.add_argument("--collection-guide", action="store_true", help="Show Dribbble collection guide")
    parser.add_argument("--workers", type=int, default=1,
                        help="Parallel workers for HTML generation (default: 1)")
    parser.add_argument("--render-workers", type=int, default=1,
                        help="Parallel workers for screenshot rendering (default: 1)")
    args = parser.parse_args()

    if args.pilot:
        generate_uis(pilot=True, workers=args.workers)
        render_screenshots(workers=args.render_workers)
    elif args.full:
        generate_uis(pilot=False, workers=args.workers)
        render_screenshots(workers=args.render_workers)
    elif args.render_only:
        render_screenshots(workers=args.render_workers)
    elif args.survey_prep:
        prepare_survey()
    elif args.collection_guide:
        print_collection_guide()
    else:
        parser.print_help()
        print("\nTypical workflow:")
        print("  1. python generate_uis.py --pilot          # Test with 8 UIs")
        print("  2. python generate_uis.py --full           # Generate all 40")
        print("  3. python generate_uis.py --collection-guide  # Instructions for human UIs")
        print("  4. [Manually collect 40 human UIs from Dribbble]")
        print("  5. python generate_uis.py --survey-prep    # Randomize for survey")


if __name__ == "__main__":
    main()
