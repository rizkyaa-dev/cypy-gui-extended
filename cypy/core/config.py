import os
import sys
from dotenv import load_dotenv

from cypy.core.filesystem import atomic_write_json, atomic_write_text

# ✦ Path Helper - Let's find where everything is~ ✦
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
# CORE_DIR is where our core essence lies
# ROOT_DIR is our magical home

if getattr(sys, 'frozen', False):
    ROOT_DIR = os.path.dirname(sys.executable)
    ASSETS_DIR = os.path.join(getattr(sys, '_MEIPASS', ROOT_DIR), "assets")
else:
    ROOT_DIR = os.path.abspath(os.path.join(CORE_DIR, "..", ".."))
    ASSETS_DIR = os.path.join(ROOT_DIR, "assets")

load_dotenv(os.path.join(ROOT_DIR, ".env"))


# ==========================================
# ✦ LLM PROVIDER SETTINGS - Choose your translation engine~ ♪ ✦
# ==========================================
# Supported providers: gemini, openai, zen, openrouter, custom
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

# Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_GEMINI = os.getenv("MODEL_GEMINI", "gemini-3.1-flash-lite")

# OpenRouter (https://openrouter.ai)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL_OPENROUTER = os.getenv("MODEL_OPENROUTER", "qwen/qwen2.5-vl-72b-instruct:free")

# OpenAI (https://platform.openai.com)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_OPENAI = os.getenv("MODEL_OPENAI", "gpt-5.4-mini")

# Zen (https://opencode.ai) — no API key required
ZEN_API_KEY = os.getenv("ZEN_API_KEY", "")
MODEL_ZEN = os.getenv("MODEL_ZEN", "minimax-m3-free")

# Custom OpenAI-compatible provider
CUSTOM_API_KEY = os.getenv("CUSTOM_API_KEY", "")
CUSTOM_BASE_URL = os.getenv("CUSTOM_BASE_URL", "")
MODEL_CUSTOM = os.getenv("MODEL_CUSTOM", "gpt-5.4-mini")

# Target language (saved after first run)
TARGET_LANGUAGE = os.getenv("TARGET_LANGUAGE", "")


# ✦ Assets Path - YOLO model and font files go here~ ✦
MODEL_YOLO = os.path.join(ASSETS_DIR, "eyecyre.onnx")
FONT_MANGA = os.path.join(ASSETS_DIR, "Komika Axis.ttf")


# ==========================================
# ✦ LANGUAGE SETTINGS - Supported target languages~ ♪ ✦
# ==========================================
LANG_CODES = {
    "english": "en",
    "indonesian": "id",
    "spanish": "es",
    "portuguese": "pt",
    "javanese": "jv",
    "japanese": "jp",
    "jepang": "jp",
    "korean": "kr",
    "korea": "kr",
    "chinese": "cn",
    "chinese (simplified)": "cn",
    "chinese (traditional)": "tw",
    "mandarin": "cn",
    "thai": "th",
    "vietnamese": "vi",
    "russian": "ru",
    "arabic": "ar",
    "hindi": "hi",
    "malay": "ms",
    "tagalog": "tl"
}

# Supported image file extensions
SUPPORTED_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


# ==========================================
# ✦ MOSAIC & CROP SETTINGS - Arranging page panels beautifully~ ✦
# ==========================================
MAX_TINGGI_MOSAIK = 6000

PAD_X_RATIO = 0.40
PAD_Y_RATIO = 0.25
MIN_PAD = 35

SKALA_POTONGAN_MOSAIK = 2.0

OVERLAP_BATAS_CROP = 0.35

MASK_AREA_LUAR_BOX = True
MASK_MARGIN = 18
MASK_MARGIN_RATIO = 0.12

MARGIN_KIRI_NOMOR = 55
MARGIN_KANAN = 10
JARAK_ANTAR_POTONGAN = 10
LEBAR_MOSAIK_MIN = 360


# ==========================================
# ✦ SFX & IMAGE FILTER - Sweeping away unwanted noises~ ✦
# ==========================================
# If True, boxes resembling SFX/background drawings will be removed~
# Set to False if some speech bubbles get mistakenly filtered out ♪
FILTER_SFX_AKTIF = True

# Modes:
# "longgar"   = safest mode, very low chance of filtering actual bubbles
# "seimbang"  = highly recommended balance ♪
# "ketat"     = aggressive filtering, might remove some actual bubbles too
FILTER_SFX_MODE = "seimbang"

# If True, filtered out SFX boxes will be saved for your manual inspection~
SIMPAN_DEBUG_FILTER_SFX = True


# ==========================================
# ✦ FLAT BOX PATCH SETTINGS - Keeping our beautiful drawings safe from being covered~ ✦
# ==========================================
PAKAI_PATCH_UNTUK_BOX_GEPENG = True

RASIO_BOX_GEPENG = 2.4
LEBAR_BOX_GEPENG_RATIO = 0.45
TINGGI_BOX_GEPENG_RATIO = 0.22


# ==========================================
# ✦ MANUAL TRANSLATION OVERRIDE - For correcting specific bubble IDs manually ♪ ✦
# ==========================================
MANUAL_TRANSLATION_OVERRIDE = {}


# ==========================================
# ✦ PROVIDER HELPERS - Utility functions for provider management~ ♪ ✦
# ==========================================
def get_provider_config(provider_name=None):
    """
    Returns (api_key, model_name) for the given provider.
    Defaults to the currently configured LLM_PROVIDER.
    """
    provider = (provider_name or LLM_PROVIDER).lower()

    if provider == "gemini":
        return GEMINI_API_KEY, MODEL_GEMINI
    elif provider == "openrouter":
        return OPENROUTER_API_KEY, MODEL_OPENROUTER
    elif provider == "openai":
        return OPENAI_API_KEY, MODEL_OPENAI
    elif provider == "zen":
        return ZEN_API_KEY, MODEL_ZEN
    elif provider == "custom":
        return CUSTOM_API_KEY, MODEL_CUSTOM
    else:
        return "", ""


# ==========================================
# ✦ TWEAKABLE PARAMETERS - Interactive adjustments~ ♪ ✦
# ==========================================
import json

TWEAKABLE_PARAMS = {
    "sfx_mode": {
        "var_name": "FILTER_SFX_MODE",
        "type": "str",
        "default": "seimbang",
        "options": ["longgar", "seimbang", "ketat"],
        "desc": "Tingkat agresivitas menghapus teks (SFX) / background.",
        "effect": "'ketat' = banyak balon terhapus (bisa kena balon asli), 'longgar' = aman tapi banyak sampah ikut ke-translate."
    },
    "pad_x": {
        "var_name": "PAD_X_RATIO",
        "type": "float",
        "default": 0.40,
        "min": 0.0,
        "max": 1.5,
        "desc": "Rasio kelonggaran potongan gambar balon teks (kiri-kanan) yang dikirim ke AI (OCR).",
        "effect": "Makin BESAR = mencegah teks kepotong di mata AI, tapi rawan menabrak teks sebelahnya."
    },
    "pad_y": {
        "var_name": "PAD_Y_RATIO",
        "type": "float",
        "default": 0.25,
        "min": 0.0,
        "max": 1.5,
        "desc": "Rasio kelonggaran potongan gambar balon teks (atas-bawah) yang dikirim ke AI (OCR).",
        "effect": "Makin BESAR = mencegah teks kepotong di mata AI, tapi rawan menabrak teks atas/bawahnya."
    },
    "skala_potongan": {
        "var_name": "SKALA_POTONGAN_MOSAIK",
        "type": "float",
        "default": 2.0,
        "min": 1.0,
        "max": 5.0,
        "desc": "Faktor perbesaran gambar sebelum dikirim ke AI.",
        "effect": "Makin BESAR = teks kecil makin terbaca oleh AI, tapi proses loading/upload lebih lambat."
    },
    "patch_gepeng": {
        "var_name": "PAKAI_PATCH_UNTUK_BOX_GEPENG",
        "type": "bool",
        "default": True,
        "desc": "Timpa teks yang bentuknya sangat panjang (gepeng) dengan kotak putih tebal.",
        "effect": "Matikan (False) jika garis border panel komik malah tertimpa kotak putih secara ngawur."
    },
    "min_pad": {
        "var_name": "MIN_PAD",
        "type": "int",
        "default": 35,
        "min": 0,
        "max": 150,
        "desc": "Batas kelonggaran minimum (dalam piksel) untuk potongan gambar yang dikirim ke AI.",
        "effect": "Makin BESAR = mencegah potongan gambar AI terlalu sempit pada teks yang sangat kecil."
    },
    "mask_margin": {
        "var_name": "MASK_MARGIN_RATIO",
        "type": "float",
        "default": 0.12,
        "min": 0.0,
        "max": 0.45,
        "desc": "Rasio penyempitan (inward margin) area kotak putih masking dari tepi asli kotak teks.",
        "effect": "Makin KECIL = kotak putih makin MEMBESAR. Makin BESAR = kotak putih makin MENGECIL."
    }
}

def load_local_profile():
    """Loads tweaks from cypy_profile.json in the current working directory."""
    profile_path = os.path.join(os.getcwd(), "cypy_profile.json")
    if os.path.exists(profile_path):
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            for key, val in data.items():
                if key in TWEAKABLE_PARAMS:
                    meta = TWEAKABLE_PARAMS[key]
                    globals()[meta["var_name"]] = val
            return True
        except Exception as e:
            print(f"[!] Error loading local profile: {e}")
    return False

def save_local_profile():
    """Saves current tweakable values to cypy_profile.json in the current working directory."""
    profile_path = os.path.join(os.getcwd(), "cypy_profile.json")
    data = {}
    for key, meta in TWEAKABLE_PARAMS.items():
        data[key] = globals().get(meta["var_name"], meta["default"])
        
    try:
        atomic_write_json(profile_path, data)
        return True
    except Exception as e:
        print(f"[!] Error saving local profile: {e}")
        return False


# ==========================================
# ✦ PERSISTENT SETTINGS (data/settings.json) ✦
# ==========================================
DATA_DIR = os.path.join(ROOT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

def load_settings():
    """Loads target language, provider, and model configurations from data/settings.json."""
    global LLM_PROVIDER, TARGET_LANGUAGE
    global GEMINI_API_KEY, MODEL_GEMINI
    global OPENAI_API_KEY, MODEL_OPENAI
    global OPENROUTER_API_KEY, MODEL_OPENROUTER
    global ZEN_API_KEY, MODEL_ZEN
    global CUSTOM_API_KEY, CUSTOM_BASE_URL, MODEL_CUSTOM
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            LLM_PROVIDER = data.get("llm_provider", LLM_PROVIDER)
            TARGET_LANGUAGE = data.get("target_language", TARGET_LANGUAGE)
            
            legacy_secrets = {
                "GEMINI_API_KEY": data.get("gemini_api_key", ""),
                "OPENAI_API_KEY": data.get("openai_api_key", ""),
                "OPENROUTER_API_KEY": data.get("openrouter_api_key", ""),
                "ZEN_API_KEY": data.get("zen_api_key", ""),
                "CUSTOM_API_KEY": data.get("custom_api_key", ""),
            }

            # Models and endpoints are preferences; credentials live only in .env.
            MODEL_GEMINI = data.get("model_gemini", MODEL_GEMINI)
            MODEL_OPENAI = data.get("model_openai", MODEL_OPENAI)
            MODEL_OPENROUTER = data.get("model_openrouter", MODEL_OPENROUTER)
            MODEL_ZEN = data.get("model_zen", MODEL_ZEN)
            CUSTOM_BASE_URL = data.get("custom_base_url", CUSTOM_BASE_URL)
            MODEL_CUSTOM = data.get("model_custom", MODEL_CUSTOM)

            if any(legacy_secrets.values()):
                _migrate_legacy_secrets(legacy_secrets)
                save_settings()
            
            # Synchronize environment variables for the session
            if GEMINI_API_KEY: os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
            if OPENAI_API_KEY: os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
            if OPENROUTER_API_KEY: os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY
            if ZEN_API_KEY: os.environ["ZEN_API_KEY"] = ZEN_API_KEY
            if CUSTOM_API_KEY: os.environ["CUSTOM_API_KEY"] = CUSTOM_API_KEY
            if CUSTOM_BASE_URL: os.environ["CUSTOM_BASE_URL"] = CUSTOM_BASE_URL
            
            return True
        except Exception as e:
            print(f"[!] Error loading settings: {e}")
    return False

def save_settings():
    """Saves current provider, language, and model configurations to data/settings.json."""
    data = {
        "llm_provider": LLM_PROVIDER,
        "target_language": TARGET_LANGUAGE,
        "model_gemini": MODEL_GEMINI,
        "model_openai": MODEL_OPENAI,
        "model_openrouter": MODEL_OPENROUTER,
        "model_zen": MODEL_ZEN,
        "custom_base_url": CUSTOM_BASE_URL,
        "model_custom": MODEL_CUSTOM
    }
    try:
        atomic_write_json(SETTINGS_FILE, data)
        return True
    except Exception as e:
        print(f"[!] Error saving settings: {e}")
    return False


def _migrate_legacy_secrets(legacy_secrets):
    """Move credentials from legacy settings.json into the ignored .env store."""
    env_path = os.path.join(ROOT_DIR, ".env")
    existing_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as handle:
            existing_lines = handle.read().splitlines()

    current = {}
    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, value = stripped.split("=", 1)
            current[key.strip()] = value

    changed = False
    for key, value in legacy_secrets.items():
        if value and not os.getenv(key):
            current[key] = json.dumps(str(value), ensure_ascii=False)
            os.environ[key] = str(value)
            globals()[key] = str(value)
            changed = True

    if not changed:
        return

    managed_keys = set(current)
    preserved = [
        line
        for line in existing_lines
        if not (
            line.strip()
            and not line.lstrip().startswith("#")
            and "=" in line
            and line.split("=", 1)[0].strip() in managed_keys
        )
    ]
    preserved.extend(f"{key}={value}" for key, value in current.items())
    atomic_write_text(env_path, "\n".join(preserved).rstrip() + "\n")

# Initialize settings load
load_settings()
