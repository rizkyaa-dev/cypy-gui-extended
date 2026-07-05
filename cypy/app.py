import os
import sys
import time

from cypy.core.filesystem import atomic_write_text

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from cypy.core.detection.yolo_onnx import YOLOONNX as YOLO
from cypy.core.config import get_provider_config
import cypy.core.config as config
from cypy.core.documents import (
    mulai_ritual_archive,
    mulai_ritual_pdf,
    proses_folder,
    proses_satu_gambar,
)
from cypy.core.providers import create_provider
from cypy.core.desktop import create_shortcut_if_first_run
from cypy.core import ui
from cypy.core.version import APP_VER


# ==========================================
# ✦ PROVIDER SETUP - Choose your translation engine~ ♪ ✦
# ==========================================
PROVIDER_INFO = {
    "gemini": {
        "name": "Google Gemini",
        "env_key": "GEMINI_API_KEY",
        "url": "https://aistudio.google.com/",
        "desc": "Free tier available",
    },
    "openai": {
        "name": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "url": "https://platform.openai.com/api-keys",
        "desc": "GPT-5.4, GPT-5.4-mini",
    },
    "zen": {
        "name": "Zen (opencode.ai)",
        "env_key": "ZEN_API_KEY",
        "url": "https://opencode.ai/auth",
        "desc": "Free models, optional API key for more quota",
    },
    "openrouter": {
        "name": "OpenRouter",
        "env_key": "OPENROUTER_API_KEY",
        "url": "https://openrouter.ai/keys",
        "desc": "Access 100+ models (Claude, Llama, Mistral, etc.)",
    },
    "custom": {
        "name": "Custom",
        "env_key": "CUSTOM_API_KEY",
        "url": "",
        "desc": "OpenAI-compatible API, custom base URL",
    },
}


def pilih_bahasa():
    options = [
        "[1] English",
        "[2] Indonesian",
        "[3] Japanese (日本語)",
        "[4] Mandarin (简体中文)",
        "[5] Spanish (Español)",
        "[6] Portuguese (Português)",
        "[7] Javanese (Basa Jawa)",
        "[8] Custom (type your own)",
    ]
    ui.print_box("Target Language / Bahasa Target:", options, col_width=28)

    lang_choice = input("Select choice / Pilih (1-8) [Default: 2]: ").strip()
    if lang_choice == "1":
        target_language = "English"
    elif lang_choice == "2":
        target_language = "Indonesian"
    elif lang_choice == "3":
        target_language = "Japanese"
    elif lang_choice == "4":
        target_language = "Mandarin"
    elif lang_choice == "5":
        target_language = "Spanish"
    elif lang_choice == "6":
        target_language = "Portuguese"
    elif lang_choice == "7":
        target_language = "Javanese"
    elif lang_choice == "8":
        custom = input("Type your target language (e.g. Korean, Thai, Arabic): ").strip()
        if custom:
            target_language = custom.title()
        else:
            target_language = "Indonesian"
    else:
        target_language = "Indonesian"

    print(f"\n[+] Target language set to: {target_language}")
    return target_language


def pilih_provider():
    options = [
        "[1] Google Gemini",
        "[2] OpenAI (GPT-5.4)",
        "[3] Zen (opencode.ai)",
        "[4] OpenRouter",
        "[5] Custom (OpenAI-compatible)",
    ]
    ui.print_box("API Provider Selection:", options, col_width=28)

    choice = input("Select provider (1-5) [Default: 1]: ").strip()
    if choice == "2":
        return "openai"
    elif choice == "3":
        return "zen"
    elif choice == "4":
        return "openrouter"
    elif choice == "5":
        return "custom"
    else:
        return "gemini"


def _save_to_env(env_path, env_key, api_key, provider_name):
    """Write/update a key in .env file."""
    existing_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()

    key_found = False
    new_lines = []
    for line in existing_lines:
        if line.strip().startswith(f"{env_key}="):
            new_lines.append(f"{env_key}={api_key}\n")
            key_found = True
        else:
            new_lines.append(line)
    if not key_found:
        new_lines.append(f"{env_key}={api_key}\n")

    provider_found = any(l.strip().startswith("LLM_PROVIDER=") for l in new_lines)
    if not provider_found:
        new_lines.insert(0, f"LLM_PROVIDER={provider_name}\n")

    # Ensure default model written once
    model_defaults = {
        "gemini": "MODEL_GEMINI=gemini-3.1-flash-lite\n",
        "openai": "MODEL_OPENAI=gpt-5.4-mini\n",
        "openrouter": "MODEL_OPENROUTER=qwen/qwen2.5-vl-72b-instruct:free\n",
        "zen": "MODEL_ZEN=minimax-m3-free\n",
        "custom": "MODEL_CUSTOM=gpt-5.4-mini\n",
    }
    if provider_name in model_defaults:
        prefix = model_defaults[provider_name].split("=")[0] + "="
        if not any(l.strip().startswith(prefix) for l in new_lines):
            new_lines.append(model_defaults[provider_name])

    atomic_write_text(env_path, "".join(new_lines))


def _save_to_env_simple(env_path, key, value):
    """Write/update a single key=value line in .env file."""
    existing_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()

    key_found = False
    new_lines = []
    for line in existing_lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            key_found = True
        else:
            new_lines.append(line)
    if not key_found:
        new_lines.append(f"{key}={value}\n")

    atomic_write_text(env_path, "".join(new_lines))


def _env_has_key(env_path, key):
    """Check if a key exists in the .env file."""
    if not os.path.exists(env_path):
        return False
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith(f"{key}="):
                return True
    return False


def setup_provider(provider_name=None):
    """Sets up the LLM provider, requesting API key if missing~ ♪"""
    import cypy.core.config as config

    if provider_name is None:
        provider_name = config.LLM_PROVIDER

    api_key, model_name = get_provider_config(provider_name)
    info = PROVIDER_INFO.get(provider_name, PROVIDER_INFO["gemini"])
    env_path = os.path.join(config.ROOT_DIR, ".env")

    if provider_name == "zen":
        # Key is optional — prompt only if not already set
        if not api_key:
            print(f"\n[i] Zen (opencode.ai) works without an API key~ ♪")
            print(f"    Optional: get a key at {info['url']} for more quota.")
            entered = input("Paste your Zen API Key (or press Enter to skip): ").strip()
            if entered:
                api_key = entered
                try:
                    _save_to_env(env_path, info["env_key"], api_key, provider_name)
                    config.ZEN_API_KEY = api_key
                    os.environ[info["env_key"]] = api_key
                    print(f"[+] Zen API Key saved to: {env_path} (✿◠‿◠)")
                except Exception as e:
                    print(f"[!] Warning: Failed to save API Key to .env: {e}")
            else:
                print("[+] Proceeding without API key~ ♪")

    elif provider_name == "custom":
        # Custom provider: base URL is required, API key is optional
        base_url = config.CUSTOM_BASE_URL
        if not base_url:
            print(f"\n[i] Enter the base URL for your OpenAI-compatible API.")
            print(f"    Example: https://api.example.com/v1")
            entered = input("Base URL: ").strip()
            while not entered:
                entered = input("Base URL cannot be empty: ").strip()
            base_url = entered
            # Save base URL to .env
            try:
                _save_to_env_simple(env_path, "CUSTOM_BASE_URL", base_url)
                config.CUSTOM_BASE_URL = base_url
                os.environ["CUSTOM_BASE_URL"] = base_url
                print(f"[+] Base URL saved to: {env_path}")
            except Exception as e:
                print(f"[!] Warning: Failed to save Base URL: {e}")

        if not api_key:
            print(f"\n[i] API key is optional (some providers don't require one).")
            entered = input("Paste your API Key (or press Enter to skip): ").strip()
            if entered:
                api_key = entered
                try:
                    _save_to_env(env_path, info["env_key"], api_key, provider_name)
                    config.CUSTOM_API_KEY = api_key
                    os.environ[info["env_key"]] = api_key
                    print(f"[+] API Key saved to: {env_path} (✿◠‿◠)")
                except Exception as e:
                    print(f"[!] Warning: Failed to save API Key to .env: {e}")
            else:
                print("[+] Proceeding without API key~ ♪")

    elif not api_key:
        print(f"\n[!] {info['name']} API Key is missing!")
        print(f"Get your API key from: {info['url']}")
        api_key = input(f"Please paste your {info['name']} API Key here: ").strip()

        while not api_key:
            api_key = input("API Key cannot be empty. Please paste your API Key: ").strip()

        try:
            _save_to_env(env_path, info["env_key"], api_key, provider_name)
            print(f"[+] API Key saved to: {env_path} (✿◠‿◠)")

            if provider_name == "gemini":
                config.GEMINI_API_KEY = api_key
            elif provider_name == "openrouter":
                config.OPENROUTER_API_KEY = api_key
            elif provider_name == "openai":
                config.OPENAI_API_KEY = api_key

            os.environ[info["env_key"]] = api_key

        except Exception as e:
            print(f"[!] Warning: Failed to save API Key to .env: {e}")

    extra = {}
    if provider_name == "custom":
        extra["base_url"] = config.CUSTOM_BASE_URL

    # Save updated keys/endpoints to data/settings.json
    config.save_settings()

    provider = create_provider(provider_name, api_key=api_key, model_name=model_name, **extra)
    return provider


def menu_tweak():
    import cypy.core.config as config
    print("\n" + "="*60)
    print("TWEAK MENU - Adjust Settings on the fly~ ♪")
    print("="*60 + "\n")
    
    for key, meta in config.TWEAKABLE_PARAMS.items():
        curr_val = getattr(config, meta["var_name"], meta["default"])
        print(f"  [{key}]")
        print(f"    Current : {curr_val} (Default: {meta['default']})")
        
        if "min" in meta and "max" in meta:
            print(f"    Range   : {meta['min']} - {meta['max']}")
        elif "options" in meta:
            opts = ", ".join(meta['options'])
            print(f"    Options : {opts}")
            
        print(f"    Info    : {meta['desc']}")
        if "effect" in meta:
            print(f"    Efek    : {meta['effect']}")
        print("")  # spacing antar parameter

    print("="*60)
    print("  Type 'set <param> <value>' to change (e.g. set pad_x 0.5)")
    print("  Type 'back' or 'done' to return to main menu.")
    print("="*60)

    while True:
        cmd = input("tweak> ").strip().lower()
        if cmd in ("back", "done", "exit", "stop", "quit"):
            break
            
        if cmd.startswith("set "):
            parts = cmd.split(" ", 2)
            if len(parts) < 3:
                print("  [!] Format salah. Contoh: set pad_x 0.5")
                continue
                
            _, param, val_str = parts
            if param not in config.TWEAKABLE_PARAMS:
                print(f"  [!] Parameter '{param}' tidak ditemukan.")
                continue
                
            meta = config.TWEAKABLE_PARAMS[param]
            val = None
            try:
                if meta["type"] == "int":
                    val = int(val_str)
                elif meta["type"] == "float":
                    val = float(val_str)
                elif meta["type"] == "bool":
                    val = val_str.lower() in ("true", "1", "yes", "y", "on")
                else:
                    val = val_str
                    
                if "options" in meta and val not in meta["options"]:
                    opts = ", ".join(meta['options'])
                    print(f"  [!] Nilai harus salah satu dari: {opts}")
                    continue
                if "min" in meta and val < meta["min"]:
                    print(f"  [!] Nilai minimal adalah {meta['min']}")
                    continue
                if "max" in meta and val > meta["max"]:
                    print(f"  [!] Nilai maksimal adalah {meta['max']}")
                    continue
                    
                setattr(config, meta["var_name"], val)
                print(f"  [+] {param} diubah menjadi {val}")
                
                if config.save_local_profile():
                    print("  [+] Profil tersimpan ke cypy_profile.json")
                    
            except ValueError:
                print(f"  [!] Nilai harus berupa tipe {meta['type']}")

def tampilkan_help():
    ui.tampilkan_help()


def tampilkan_status(provider, target_language):
    ui.tampilkan_status(provider, target_language)


def main():
    if "--gui" in sys.argv[1:]:
        from cypy.gui.app import main as gui_main

        return gui_main()

    # Automatically create desktop shortcut on first run (Windows only)
    create_shortcut_if_first_run()

    import cypy.core.config as config
    if config.load_local_profile():
        print("\n[+] Loaded local profile (cypy_profile.json)")

    ui.print_logo(APP_VER.lstrip('v'))

    # Load LLM provider from settings.json or env
    if config.LLM_PROVIDER:
        provider_name = config.LLM_PROVIDER
    else:
        provider_name = pilih_provider()
        config.LLM_PROVIDER = provider_name
        config.save_settings()

    provider = setup_provider(provider_name)

    if not os.path.exists(config.MODEL_YOLO):
        print("[!] YOLO model file not found.")
        raise SystemExit

    if not os.path.exists(config.FONT_MANGA):
        print("[!] Font file not found (will fallback to default).")

    yolo_model = YOLO(config.MODEL_YOLO)

    # Load Target Language from settings.json or env
    if config.TARGET_LANGUAGE:
        target_language = config.TARGET_LANGUAGE
    else:
        target_language = pilih_bahasa()
        config.TARGET_LANGUAGE = target_language
        config.save_settings()

    # Show current config
    tampilkan_status(provider, target_language)

    while True:
        try:
            raw_input_str = input("\nDrag-and-drop image/PDF/CBZ/folder here (or 'help' 'stop'): ")
            input_file = raw_input_str.strip("\"'& ")

            cmd = input_file.lower()

            if cmd in ("stop", "exit", "quit"):
                print("Goodbye~ ♪")
                break

            if cmd in ("lang", "switch", "change"):
                target_language = pilih_bahasa()
                config.TARGET_LANGUAGE = target_language
                config.save_settings()
                continue

            if cmd in ("provider", "api"):
                provider_name = pilih_provider()
                provider = setup_provider(provider_name)
                config.LLM_PROVIDER = provider_name
                # Save default model name for that provider
                _, default_model = config.get_provider_config(provider_name)
                if provider_name == "gemini": config.MODEL_GEMINI = default_model
                elif provider_name == "openai": config.MODEL_OPENAI = default_model
                elif provider_name == "openrouter": config.MODEL_OPENROUTER = default_model
                elif provider_name == "zen": config.MODEL_ZEN = default_model
                elif provider_name == "custom": config.MODEL_CUSTOM = default_model
                config.save_settings()
                tampilkan_status(provider, target_language)
                continue

            if cmd == "model":
                new_model = input("Enter model name: ").strip()
                if new_model:
                    provider.model_name = new_model
                    p_name = provider.provider_name.lower()
                    if "gemini" in p_name: config.MODEL_GEMINI = new_model
                    elif "openai" in p_name: config.MODEL_OPENAI = new_model
                    elif "openrouter" in p_name: config.MODEL_OPENROUTER = new_model
                    elif "zen" in p_name: config.MODEL_ZEN = new_model
                    elif "custom" in p_name: config.MODEL_CUSTOM = new_model
                    config.save_settings()
                    print(f"[+] Model changed to: {new_model}")
                continue

            if cmd == "status":
                tampilkan_status(provider, target_language)
                continue
                
            if cmd == "tweak":
                menu_tweak()
                continue

            if cmd == "help":
                tampilkan_help()
                continue

            if not input_file:
                continue

            # Folder batch processing
            if os.path.isdir(input_file):
                start_time = time.time()
                proses_folder(input_file, yolo_model, provider=provider, target_language=target_language)
                elapsed = time.time() - start_time
                print(f"\n[Timer] Total time: {elapsed:.1f}s")
                continue

            if os.path.exists(input_file):
                start_time = time.time()

                if input_file.lower().endswith(".pdf"):
                    mulai_ritual_pdf(input_file, yolo_model, provider=provider, target_language=target_language)

                elif input_file.lower().endswith(('.zip', '.cbz', '.rar', '.cbr')):
                    mulai_ritual_archive(input_file, yolo_model, provider=provider, target_language=target_language)

                elif input_file.lower().endswith(config.SUPPORTED_IMAGE_EXTENSIONS):
                    hasil = proses_satu_gambar(input_file, yolo_model, provider=provider, target_language=target_language)

                    if hasil:
                        print(f"Done! Saved at: {hasil}")

                else:
                    print("[!] Unsupported format. Please give me PNG, JPG, JPEG, WEBP, PDF, CBZ, ZIP, CBR, or RAR~ ♪")
                    continue

                elapsed = time.time() - start_time
                print(f"[Timer] Completed in {elapsed:.1f}s")

            else:
                print("[!] File not found.")

        except KeyboardInterrupt:
            print("\n\nGoodbye.")
            break
        except Exception as e:
            print(f"[!] An error occurred: {e}")


if __name__ == "__main__":
    main()
