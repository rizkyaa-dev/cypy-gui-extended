import os
import re

from PIL import ImageFont

from cypy.core.reporting import ensure_reporter
from cypy.core.settings import ProcessingSettings
from cypy.core.filesystem import atomic_replace

try:
    import requests as _requests
except ImportError:
    _requests = None


_DEFAULT_HTTP_CLIENT = object()
_font_path_cache = {}
_MAX_FONT_BYTES = 64 * 1024 * 1024

_NOTO_SANS_MAP = {
    "korean": "Noto+Sans+KR",
    "chinese": "Noto+Sans+SC",
    "chinese (simplified)": "Noto+Sans+SC",
    "chinese (traditional)": "Noto+Sans+TC",
    "mandarin": "Noto+Sans+SC",
    "thai": "Noto+Sans+Thai",
    "arabic": "Noto+Sans+Arabic",
    "hindi": "Noto+Sans+Devanagari",
    "bengali": "Noto+Sans+Bengali",
    "tamil": "Noto+Sans+Tamil",
    "telugu": "Noto+Sans+Telugu",
    "russian": "Noto+Sans",
    "ukrainian": "Noto+Sans",
    "greek": "Noto+Sans",
    "hebrew": "Noto+Sans+Hebrew",
    "georgian": "Noto+Sans+Georgian",
    "armenian": "Noto+Sans+Armenian",
    "burmese": "Noto+Sans+Myanmar",
    "khmer": "Noto+Sans+Khmer",
    "lao": "Noto+Sans+Lao",
    "tibetan": "Noto+Sans+Tibetan",
    "mongolian": "Noto+Sans+Mongolian",
    "vietnamese": "Noto+Sans",
    "malay": "Noto+Sans",
    "turkish": "Noto+Sans",
    "persian": "Noto+Sans+Arabic",
    "urdu": "Noto+Sans+Arabic",
}

_DIRECT_FONT_MAP = {
    "korean": ("https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/Korean/NotoSansCJKkr-Regular.otf", ".otf"),
    "chinese (simplified)": ("https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf", ".otf"),
    "chinese": ("https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf", ".otf"),
    "china": ("https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf", ".otf"),
    "chinese (traditional)": ("https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf", ".otf"),
    "mandarin": ("https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf", ".otf"),
    "thai": ("https://github.com/google/fonts/raw/main/ofl/notosansthai/NotoSansThai%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "thailand": ("https://github.com/google/fonts/raw/main/ofl/notosansthai/NotoSansThai%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "arabic": ("https://github.com/google/fonts/raw/main/ofl/notosansarabic/NotoSansArabic%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "urdu": ("https://github.com/google/fonts/raw/main/ofl/notosansarabic/NotoSansArabic%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "russian": ("https://github.com/google/fonts/raw/main/ofl/notosans/NotoSans%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "vietnamese": ("https://github.com/google/fonts/raw/main/ofl/notosans/NotoSans%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "bengali": ("https://github.com/google/fonts/raw/main/ofl/notosansbengali/NotoSansBengali%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "hindi": ("https://github.com/google/fonts/raw/main/ofl/notosansdevanagari/NotoSansDevanagari%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "hebrew": ("https://github.com/google/fonts/raw/main/ofl/notosanshebrew/NotoSansHebrew%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "tamil": ("https://github.com/google/fonts/raw/main/ofl/notosanstamil/NotoSansTamil%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "myanmar": ("https://github.com/google/fonts/raw/main/ofl/notosansmyanmar/NotoSansMyanmar%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "burmese": ("https://github.com/google/fonts/raw/main/ofl/notosansmyanmar/NotoSansMyanmar%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "mongolian": ("https://github.com/google/fonts/raw/main/ofl/notosansmongolian/NotoSansMongolian-Regular.ttf", ".ttf"),
    "khmer": ("https://github.com/google/fonts/raw/main/ofl/notosanskhmer/NotoSansKhmer%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "lao": ("https://github.com/google/fonts/raw/main/ofl/notosanslao/NotoSansLao%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "telugu": ("https://github.com/google/fonts/raw/main/ofl/notosanstelugu/NotoSansTelugu%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "kannada": ("https://github.com/google/fonts/raw/main/ofl/notosanskannada/NotoSansKannada%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "malayalam": ("https://github.com/google/fonts/raw/main/ofl/notosansmalayalam/NotoSansMalayalam%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "gujarati": ("https://github.com/google/fonts/raw/main/ofl/notosansgujarati/NotoSansGujarati%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "punjabi": ("https://github.com/google/fonts/raw/main/ofl/notosansgurmukhi/NotoSansGurmukhi%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "georgian": ("https://github.com/google/fonts/raw/main/ofl/notosansgeorgian/NotoSansGeorgian%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "armenian": ("https://github.com/google/fonts/raw/main/ofl/notosansarmenian/NotoSansArmenian%5Bwdth%2Cwght%5D.ttf", ".ttf"),
    "amharic": ("https://github.com/google/fonts/raw/main/ofl/notosansethiopic/NotoSansEthiopic%5Bwdth%2Cwght%5D.ttf", ".ttf"),
}

_DIRECT_FONT_MAP.update({
    "pakistan": _DIRECT_FONT_MAP["urdu"],
    "russia": _DIRECT_FONT_MAP["russian"],
    "vietnam": _DIRECT_FONT_MAP["vietnamese"],
    "bangladesh": _DIRECT_FONT_MAP["bengali"],
    "india": _DIRECT_FONT_MAP["hindi"],
    "mongolia": _DIRECT_FONT_MAP["mongolian"],
    "kamboja": _DIRECT_FONT_MAP["khmer"],
    "laos": _DIRECT_FONT_MAP["lao"],
    "gurmukhi": _DIRECT_FONT_MAP["punjabi"],
    "georgia": _DIRECT_FONT_MAP["georgian"],
    "armenia": _DIRECT_FONT_MAP["armenian"],
    "kazakhstan": _DIRECT_FONT_MAP["russian"],
    "kazakh": _DIRECT_FONT_MAP["russian"],
    "uzbekistan": _DIRECT_FONT_MAP["russian"],
    "uzbek": _DIRECT_FONT_MAP["russian"],
    "kirgizstan": _DIRECT_FONT_MAP["russian"],
    "kyrgyz": _DIRECT_FONT_MAP["russian"],
    "kyrgyzstan": _DIRECT_FONT_MAP["russian"],
    "ethiopia": _DIRECT_FONT_MAP["amharic"],
    "eritrea": _DIRECT_FONT_MAP["amharic"],
    "tigrinya": _DIRECT_FONT_MAP["amharic"],
    "tigre": _DIRECT_FONT_MAP["amharic"],
})

_LATIN_EXCEPTIONS = set(
    " \t\n\r.,!?;:'\"\\-()[]{}"
    "\u2026\u2014\u2013\u00b7\u2022\u00ab\u00bb\u00a1\u00bf\u266a~"
)


class _LazyFontPath:
    def __init__(self, resolver):
        self._resolver = resolver

    def __fspath__(self):
        return str(self)

    def __str__(self):
        return self._resolver()

    def __repr__(self):
        return repr(str(self))

    def __getattr__(self, name):
        return getattr(str(self), name)


def _settings(settings=None):
    return settings or ProcessingSettings.from_config()


def font_cache_dir(settings=None):
    cfg = _settings(settings)
    return os.path.join(cfg.root_dir, "cypy_cache", "fonts")


def _has_non_latin(text):
    for ch in str(text):
        if ord(ch) > 0x024F and ch not in _LATIN_EXCEPTIONS:
            return True
    return False


class FontResolver:
    def __init__(self, settings, reporter=None, http_client=_DEFAULT_HTTP_CLIENT):
        self.settings = settings
        self.reporter = ensure_reporter(reporter)
        self.http_client = _requests if http_client is _DEFAULT_HTTP_CLIENT else http_client

    @property
    def cache_dir(self):
        return font_cache_dir(self.settings)

    def resolve(self, text, size, language=None):
        if _has_non_latin(text):
            font = self._resolve_non_latin(text, size, language)
            if font is not None:
                return font

        try:
            return ImageFont.truetype(self.settings.font_manga, size)
        except Exception:
            return ImageFont.load_default()

    def download_noto_font(self, language):
        if self.http_client is None:
            self.reporter.warning(
                "  [!] 'requests' library is not installed. Custom fonts cannot be downloaded automatically."
            )
            return None

        os.makedirs(self.cache_dir, exist_ok=True)
        lang_key = (language or "").lower()

        if lang_key in _DIRECT_FONT_MAP:
            return self._download_direct_font(lang_key)

        return self._download_css_font(lang_key)

    def _resolve_non_latin(self, text, size, language):
        lang = (language or "").lower()
        if lang == "jepang":
            lang = "japanese"

        if lang == "japanese":
            font = self._try_font_path(self.settings.font_japanese, size)
            if font is not None:
                return font

        cache_key = f"lang_{lang}"
        if cache_key in _font_path_cache:
            font = self._try_font_path(_font_path_cache[cache_key], size)
            if font is not None:
                return font

        if lang:
            noto_path = self.download_noto_font(lang)
            _font_path_cache[cache_key] = noto_path
            font = self._try_font_path(noto_path, size)
            if font is not None:
                return font

        return self._try_font_path(self.settings.font_japanese, size)

    def _download_direct_font(self, lang_key):
        url, ext = _DIRECT_FONT_MAP[lang_key]
        safe_name = f"NotoSans_{lang_key.replace(' ', '')}_v3"
        cached_file = os.path.join(self.cache_dir, f"{safe_name}{ext}")

        if os.path.exists(cached_file):
            return cached_file

        self.reporter.info(f"  [Font] Downloading full font {safe_name}{ext}...")
        try:
            response = self.http_client.get(url, stream=True, timeout=30, allow_redirects=True)
            if response.status_code == 200:
                self._write_stream(cached_file, response)
                return cached_file
            self.reporter.warning(f"  [!] Font download failed with status: {response.status_code}")
        except Exception as exc:
            self.reporter.warning(f"  [!] Font download error: {exc}")
        return None

    def _download_css_font(self, lang_key):
        font_family = self._font_family_for(lang_key)
        cached_ttf = os.path.join(
            self.cache_dir,
            f"{font_family.replace('+', '').replace(' ', '')}.ttf",
        )

        if os.path.exists(cached_ttf):
            return cached_ttf

        self.reporter.info(f"  [Font] Fetching {font_family.replace('+', ' ')} from Google Fonts...")
        css_url = f"https://fonts.googleapis.com/css?family={font_family}"
        headers = {"User-Agent": "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)"}

        try:
            css_resp = self.http_client.get(css_url, headers=headers, timeout=15)
            if css_resp.status_code != 200:
                return None

            match = re.search(r"url\((https://[^)]+)\)", css_resp.text)
            if not match:
                return None

            font_url = match.group(1).strip("'\"")
            font_resp = self.http_client.get(font_url, stream=True, timeout=30)
            if font_resp.status_code != 200:
                return None

            self._write_stream(cached_ttf, font_resp)
            self.reporter.info(f"  [Font] Downloaded successfully: {os.path.basename(cached_ttf)}")
            return cached_ttf
        except Exception as exc:
            self.reporter.warning(f"  [!] Font download error: {exc}")
            return None

    def _font_family_for(self, lang_key):
        font_family = _NOTO_SANS_MAP.get(lang_key)
        if font_family:
            return font_family

        for key, family in _NOTO_SANS_MAP.items():
            if key in lang_key or lang_key in key:
                return family

        return "Noto+Sans"

    def _try_font_path(self, path, size):
        if not path or not os.path.exists(path):
            return None

        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return None

    def _write_stream(self, path, response):
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > _MAX_FONT_BYTES:
            raise ValueError("Font download exceeds the 64 MiB safety limit.")

        def write(temp_path):
            downloaded = 0
            with open(temp_path, "wb") as handle:
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    downloaded += len(chunk)
                    if downloaded > _MAX_FONT_BYTES:
                        raise ValueError("Font download exceeds the 64 MiB safety limit.")
                    handle.write(chunk)

        atomic_replace(path, write)


def _download_noto_font(
    language,
    settings=None,
    reporter=None,
    http_client=_DEFAULT_HTTP_CLIENT,
):
    resolver = FontResolver(_settings(settings), reporter=reporter, http_client=http_client)
    return resolver.download_noto_font(language)


def _get_font_for_text(
    text,
    size,
    language=None,
    settings=None,
    reporter=None,
    font_resolver=None,
    http_client=_DEFAULT_HTTP_CLIENT,
):
    resolver = font_resolver or FontResolver(
        _settings(settings),
        reporter=reporter,
        http_client=http_client,
    )
    return resolver.resolve(text, size, language)


FONT_CACHE_DIR = _LazyFontPath(lambda: font_cache_dir())
FONT_JAPANESE = _LazyFontPath(lambda: ProcessingSettings.from_config().font_japanese)
