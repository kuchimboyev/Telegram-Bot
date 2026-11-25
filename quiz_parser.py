# -*- coding: utf-8 -*-
"""
Admin yuborgan matnni savollar ro'yxatiga aylantiradi.

Kutilayotgan format (bitta savol):

    Savol matni?
    A) variant 1
    B) variant 2
    C) variant 3
    D) variant 4
    Javob: B

Bitta xabarda bir nechta savol bo'sh qatordan keyin ketma-ket yozilishi mumkin.
"""
import re

OPTION_RE = re.compile(r"^\s*([A-DА-Г])[\)\.\:\-]\s*(.+)$", re.IGNORECASE | re.UNICODE)
ANSWER_RE = re.compile(
    r"^\s*(javob|to'?g'?ri\s*javob|to‘g‘ri\s*javob)\s*[:\-]?\s*([A-DА-Г])\s*$",
    re.IGNORECASE | re.UNICODE,
)

LETTER_ORDER = "ABCD"


class ParseError(Exception):
    pass


def _normalize_letter(letter):
    mapping = {"А": "A", "Б": "B", "В": "C", "Г": "D"}
    letter = letter.upper()
    return mapping.get(letter, letter)


def parse_questions(raw_text):
    """raw_text -> list of {"text": str, "options": [str,...], "correct": int}
    Xato bo'lsa ParseError(sabab) ko'taradi."""
    blocks = re.split(r"\n\s*\n", raw_text.strip())
    questions = []
    for block_num, block in enumerate(blocks, start=1):
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue

        question_lines = []
        options = []
        answer_letter = None

        for line in lines:
            ans_match = ANSWER_RE.match(line)
            opt_match = OPTION_RE.match(line)
            if ans_match:
                answer_letter = _normalize_letter(ans_match.group(2))
            elif opt_match:
                letter = _normalize_letter(opt_match.group(1))
                options.append((letter, opt_match.group(2).strip()))
            elif not options:
                question_lines.append(line)
            # variantlardan keyin kelgan, javob ham bo'lmagan ortiqcha qatorlar e'tiborsiz qoldiriladi

        if not question_lines:
            raise ParseError(
                f"{block_num}-blokda savol matni topilmadi:\n\n{block}"
            )
        if len(options) < 2:
            raise ParseError(
                f"{block_num}-blokda kamida 2 ta variant bo'lishi kerak (A) B) ... ko'rinishida):\n\n{block}"
            )
        if answer_letter is None:
            raise ParseError(
                f"{block_num}-blokda to'g'ri javob ko'rsatilmagan. Oxiriga \"Javob: B\" kabi qator qo'shing:\n\n{block}"
            )

        letters = [o[0] for o in options]
        if answer_letter not in letters:
            raise ParseError(
                f"{block_num}-blokda \"Javob: {answer_letter}\" ko'rsatilgan, lekin variantlar orasida bunday harf yo'q:\n\n{block}"
            )

        correct_index = letters.index(answer_letter)
        questions.append({
            "text": "\n".join(question_lines),
            "options": [o[1] for o in options],
            "correct": correct_index,
        })

    if not questions:
        raise ParseError("Hech qanday savol topilmadi. Iltimos formatga rioya qiling.")

    return questions
