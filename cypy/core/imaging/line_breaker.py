from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class WrapCandidate:
    lines: Tuple[str, ...]
    penalty: float
    hyphenated: bool = False

    @property
    def text(self):
        return "\n".join(self.lines)


@dataclass(frozen=True)
class _Token:
    text: str
    break_before: bool = False


def balanced_wrap_candidates(
    draw,
    text,
    font,
    max_width,
    stroke_width=0,
    allow_hyphenation=False,
):
    """Return the best balanced wrapping candidate for every line count."""
    tokens, was_hyphenated = _tokenize(
        draw,
        text,
        font,
        max_width,
        stroke_width,
        allow_hyphenation,
    )
    if not tokens:
        return ()

    count = len(tokens)
    states = {(0, 0): (0.0, ())}

    for start in range(count):
        previous_states = [
            (line_count, value)
            for (position, line_count), value in states.items()
            if position == start
        ]
        if not previous_states:
            continue

        for end in range(start + 1, count + 1):
            if end > start + 1 and tokens[end - 1].break_before:
                break

            line = " ".join(token.text for token in tokens[start:end])
            line_width = _text_width(
                draw,
                line,
                font,
                stroke_width=stroke_width,
            )
            if line_width > max_width:
                break

            unused_ratio = max(0.0, (max_width - line_width) / max(1, max_width))
            line_penalty = unused_ratio * unused_ratio
            if end == count:
                line_penalty *= 0.30
            if end - start == 1 and len(tokens[start].text) <= 3:
                line_penalty += 0.20

            for line_count, (penalty, lines) in previous_states:
                key = (end, line_count + 1)
                candidate = (penalty + line_penalty, lines + (line,))
                current = states.get(key)
                if current is None or candidate[0] < current[0]:
                    states[key] = candidate

    candidates = []
    for (position, _), (penalty, lines) in states.items():
        if position == count:
            candidates.append(
                WrapCandidate(
                    lines=lines,
                    penalty=penalty,
                    hyphenated=was_hyphenated,
                )
            )
    return tuple(sorted(candidates, key=lambda item: (len(item.lines), item.penalty)))


def _tokenize(
    draw,
    text,
    font,
    max_width,
    stroke_width,
    allow_hyphenation,
):
    tokens = []
    was_hyphenated = False
    paragraphs = str(text).splitlines() or [str(text)]

    for paragraph_index, paragraph in enumerate(paragraphs):
        words = paragraph.split()
        for word_index, word in enumerate(words):
            break_before = paragraph_index > 0 and word_index == 0
            pieces = None
            if allow_hyphenation:
                pieces = _split_oversized_word(
                    draw,
                    word,
                    font,
                    max_width,
                    stroke_width,
                )

            if pieces is None:
                tokens.append(_Token(word, break_before=break_before))
                continue

            first, second = pieces
            tokens.append(_Token(first, break_before=break_before))
            tokens.append(_Token(second, break_before=True))
            was_hyphenated = True

    return tuple(tokens), was_hyphenated


def _split_oversized_word(draw, word, font, max_width, stroke_width):
    clean_word = str(word)
    if len(clean_word) < 10:
        return None
    if _text_width(draw, clean_word, font, stroke_width) <= max_width:
        return None

    preferred_boundaries = _syllable_boundaries(clean_word)
    if not preferred_boundaries:
        return None
    best = None

    for index in preferred_boundaries:
        if index < 3 or index > len(clean_word) - 3:
            continue
        first = clean_word[:index] + "-"
        second = clean_word[index:]
        first_width = _text_width(draw, first, font, stroke_width)
        second_width = _text_width(draw, second, font, stroke_width)
        if first_width > max_width or second_width > max_width:
            continue

        score = abs(first_width - second_width) / max(1, max_width)
        if best is None or score < best[0]:
            best = (score, first, second)

    if best is None:
        return None
    return best[1], best[2]


def _syllable_boundaries(word):
    """Return conservative Indonesian-style syllable boundaries."""
    vowels = set("aeiouAEIOU")
    vowel_positions = [
        index for index, char in enumerate(str(word)) if char in vowels
    ]
    boundaries = set()

    for left_vowel, right_vowel in zip(vowel_positions, vowel_positions[1:]):
        cluster_start = left_vowel + 1
        cluster_end = right_vowel
        cluster = str(word)[cluster_start:cluster_end].lower()
        if not cluster:
            boundaries.add(right_vowel)
        elif len(cluster) == 1 or cluster in ("ng", "ny"):
            boundaries.add(cluster_start)
        else:
            boundaries.add(cluster_end - 1)

    return tuple(sorted(boundaries))


def _text_width(draw, text, font, stroke_width=0):
    bbox = draw.textbbox(
        (0, 0),
        text,
        font=font,
        stroke_width=stroke_width,
    )
    return bbox[2] - bbox[0]
