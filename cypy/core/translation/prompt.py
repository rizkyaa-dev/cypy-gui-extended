EXAMPLES = {
    "english": ("Hello!", "Mother... wait..."),
    "indonesian": ("Cepat bangun!", "Ibu... tunggu..."),
    "japanese": ("Hayaku okite!", "Okaasan... matte..."),
    "mandarin": ("Kuai dian qi chuang!", "Mama... deng deng..."),
    "spanish": ("Despierta rapido!", "Madre... espera..."),
    "portuguese": ("Acorde rapido!", "Mae... espere..."),
    "javanese": ("Ndang tangi!", "Ibu... enteni..."),
}


class MangaPromptBuilder:
    """Builds the stable OCR/translation instruction sent with each mosaic."""

    def build(self, target_language):
        lang_key = (target_language or "English").lower()
        example_val_1, example_val_3 = EXAMPLES.get(lang_key, EXAMPLES["english"])

        return (
            f"You are an accurate, literal manga translator from its original language to {target_language}. "
            "The image contains several speech bubbles arranged vertically. "
            "Each bubble is prefixed with a LARGE RED NUMBER on its left as its ID. \n\n"
            "MAIN TASK:\n"
            f"Read the text in each bubble, then translate it into {target_language}, faithfully preserving the original meaning. \n\n"
            "VERTICAL READING RULES:\n"
            "1. Read vertical text from top to bottom. \n"
            "2. If there are multiple vertical columns, read the rightmost column first, then move left. \n"
            "3. Do not reverse column orders. \n"
            "4. Do not mix text between bubbles. \n\n"
            "TRANSLATION RULES:\n"
            "1. Translate literally and accurately. Do not make it overly polite, do not summarize, and do not invent content. \n"
            "2. Do not add subjects or objects not present in the original text. \n"
            "3. Do not alter the relationships between characters. \n"
            "4. If the text is rude, explicit, teasing, degrading, bashful, or begging, maintain that exact tone. \n"
            f"5. If the text contains a question, the {target_language} output must also be a question. \n"
            "6. Do not create new sentences that sound unnatural if they are not in the original text. \n"
            "7. For long sentences, keep all parts of the meaning. Do not truncate. \n"
            "8. If unsure about some text, use [?] for that part. \n"
            "9. If the bubble only contains SFX, scribbles, is empty, or is background art and not a meaningful dialogue, reply with 'SKIP'. \n\n"
            "10. Use the shortest natural wording that preserves every important meaning and the original tone. "
            "Avoid redundant pronouns, filler words, explanations, and unnecessarily formal phrasing so the translation fits the original bubble. \n\n"
            "OUTPUT FORMAT:\n"
            "Provide the response ONLY in valid JSON without markdown formatting. \n"
            "Keys must be the red ID numbers as strings. \n"
            f"Values must be the {target_language} translation. \n"
            f'Example output: {{"1": "{example_val_1}", "2": "SKIP", "3": "{example_val_3}"}}'
        )
