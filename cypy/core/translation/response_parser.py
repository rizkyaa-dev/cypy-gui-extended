def bersihkan_json_dari_gemini(teks_mentah):
    """Clean provider markdown/noise so json.loads can parse the object payload."""
    teks = str(teks_mentah or "").strip()

    if teks.startswith("```json"):
        teks = teks[7:].strip()

    if teks.startswith("```"):
        teks = teks[3:].strip()

    if teks.endswith("```"):
        teks = teks[:-3].strip()

    awal = teks.find("{")
    akhir = teks.rfind("}")

    if awal != -1 and akhir != -1 and akhir > awal:
        teks = teks[awal:akhir + 1]

    return teks.strip()
