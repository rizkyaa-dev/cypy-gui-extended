# cypy-extended

<p align="center">
  <img src="assets/favicon.png" width="128" alt="cypy Logo" />
</p>

**cypy-extended** is a fork of [`indravoyager/cypy`](https://github.com/indravoyager/cypy) focused on a cleaner modular core, safer batch processing, and broader provider support while keeping the original CLI workflow intact.

The app translates manga pages by detecting speech bubbles with YOLO/ONNX, sending numbered bubble mosaics to an LLM provider, and rendering translated text back into the page.

---

## Preview

| Before (Original Page) | After (Translated Page) |
| :---: | :---: |
| ![Original Manga Page](assets/before.jpg) | ![Translated Indonesian Manga Page](assets/after.png) |

---

## Features

- **Multi-language translation:** English, Indonesian, Japanese with vertical text layout, Mandarin, Spanish, Portuguese, Javanese, and custom languages.
- **Multiple AI providers:** Gemini, OpenAI, Zen, OpenRouter, and custom OpenAI-compatible APIs.
- **Interactive CLI:** Change language, provider, model, and status without restarting.
- **Zero-setup startup:** Prompts for API keys and creates `.env` when needed. Zen can run without an API key.
- **Modular core:** Detection, imaging, translation, document processing, providers, settings, and reporting are split into focused modules.
- **Text-assisted bubble refinement:** Optional PP-OCR ONNX text detection can expand/recover speech-bubble boxes when `assets/ppocrv6_small_det.onnx` is present.
- **Safer batch processing:** Archive extraction rejects unsafe paths, provider calls are guarded in batch workers, and compatibility facades are covered by tests.
- **Persistent settings:** User preferences are saved to `data/settings.json`.
- **Desktop shortcut:** Windows builds can create a desktop shortcut on first run.

---

## Installation

### Standalone Release

Download a package from [Releases](https://github.com/rizkyaa-dev/cypy-extended/releases), extract it, and run the app:

- Windows: double-click `cypy.exe`.
- Linux/macOS: run `./cypy` from the extracted folder.

Windows release packages also include `run-gui.bat` for launching the desktop GUI.

### Run From Source

```bash
git clone https://github.com/rizkyaa-dev/cypy-extended.git
cd cypy-extended
```

On Windows, the simplest path is the launcher script:

```bat
run.bat
```

`run.bat` will:

- find Python through `py -3` or `python`
- reuse `venv`/`.venv` if it exists
- create a virtual environment if needed
- verify `pip` and required dependencies
- install the project with `pip install -e .` when dependencies are missing
- start `cypy` with `python -m cypy`
- keep the terminal open after the app exits

Useful launcher modes:

```bat
run.bat --check
run.bat --reinstall
run.bat --dev
run.bat --reinstall --dev
```

For manual setup on any platform:

```bash
python -m venv venv
```

Activate the environment:

```bash
# Linux/macOS
source venv/bin/activate

# Windows PowerShell
.\venv\Scripts\Activate.ps1
```

Install and run:

```bash
pip install -e .
cypy
```

You can also run from the project root:

```bash
python -m cypy
```

### Development Setup

```bash
pip install -e ".[dev]"
python -m compileall -q cypy tests
python -m pytest
```

### Desktop GUI

The desktop GUI uses Python's built-in Tkinter/ttk toolkit and the same core pipeline as the CLI. No additional GUI package is downloaded.

```bash
pip install -e .
cypy-gui
```

You can also run it directly from the project root:

```bash
python -m cypy.gui.app
```

Current GUI foundation:

- queue model for image jobs
- side-by-side original and translated page workspace
- multi-page navigation with current-page translation
- automatic numbered speech-bubble bounding boxes on the original page
- background processing through `ThreadPoolExecutor`
- thread-safe queue reporter for logs and job events
- target language selector, progress, retry, and page removal
- reusable controller/service layer over `cypy.core`

Tkinter is included in the official Windows Python installer. Some Linux distributions package it separately as `python3-tk`.

Recommended fork workflow:

```bash
git switch -c refactor/modular-core
git push -u origin refactor/modular-core
```

Open a pull request into `main` after tests pass.

### Build Standalone Package

```bash
python build.py
```

The build script uses PyInstaller and writes zip packages to `releases/`.

---

## Configuration

The CLI can create `.env` automatically. You can also configure providers manually:

```env
GEMINI_API_KEY=your_gemini_api_key_here
MODEL_GEMINI=gemini-3.1-flash-lite

OPENAI_API_KEY=your_openai_api_key_here
MODEL_OPENAI=gpt-5.4-mini

ZEN_API_KEY=
MODEL_ZEN=minimax-m3-free

OPENROUTER_API_KEY=your_openrouter_api_key_here
MODEL_OPENROUTER=qwen/qwen2.5-vl-72b-instruct:free

CUSTOM_BASE_URL=https://your-api.example.com/v1
CUSTOM_API_KEY=your_api_key_here
MODEL_CUSTOM=gpt-5.4-mini
```

Advanced layout defaults still live in `cypy/core/config.py`. New processing code accepts `ProcessingSettings` so tests and future integrations can avoid mutating global config.

Text-assisted detection is enabled by default when `assets/ppocrv6_small_det.onnx` exists. Disable it with:

```env
TEXT_ASSIST_ENABLED=0
```

---

## Architecture

```text
cypy/
  app.py                  # CLI orchestration
  gui/                    # Tkinter desktop adapter and background workers
  core/
    settings.py           # typed settings bridge
    errors.py             # domain exceptions
    models.py             # core dataclasses
    detection/            # YOLO adapter, detector interface, box filters
    imaging/              # crop, mosaic, render, fonts, text layout
    translation/          # prompt, JSON parser, retry/guarded service
    documents/            # image, folder, PDF, and archive processors
    providers/            # Gemini, OpenAI, OpenRouter, Zen, custom factory
    reporting.py          # console/null/memory reporters
    translator.py         # legacy compatibility facade
    utils.py              # legacy compatibility facade
tests/                    # deterministic unit and smoke tests
```

Legacy imports remain available during the transition:

```python
from cypy.core.translator import proses_satu_gambar, proses_folder
from cypy.core.utils import bersihkan_json_dari_gemini
from cypy.core.yolo_onnx import YOLOONNX
```

---

## CI

GitHub Actions runs:

```bash
python -m compileall -q cypy tests
python -m pytest
```

Release builds run on version tags (`v*`) or manual workflow dispatch.

---

## License

[MIT](LICENSE)
