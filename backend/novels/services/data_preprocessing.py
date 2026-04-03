import re
import gc
import torch
import unicodedata
from pathlib import Path

from pdf2image import convert_from_path

from pythainlp.util import normalize as thai_normalize
from pythainlp.util import num_to_thaiword

_THAI_RANGE = re.compile(r"[\u0E00-\u0E7F]")
_OCR_NOISE_CHARS = re.compile(r"[\u0E3A\u0E4E]+")
_KEEP_CATEGORIES = frozenset(
    [
        "Lu",
        "Ll",
        "Lt",
        "Lm",
        "Lo",
        "Mn",
        "Mc",
        "Me",
        "Nd",
        "Nl",
        "No",
        "Pc",
        "Pd",
        "Ps",
        "Pe",
        "Pi",
        "Pf",
        "Po",
        "Sm",
        "Sc",
        "Sk",
        "So",
        "Zs",
    ]
)


class DataPreprocessing:
    def __init__(self, reader=None):
        self.__reader = reader

        self.__chapter_pattern = re.compile(
            r"(ตอน\s*[ทที่]*\s*[0-9๐-๙]+|ep\s*\.?\s*\d+|chapter\s*\d+)",
            re.IGNORECASE,
        )

    # =========================
    # utils
    # =========================
    def thai_to_arabic(self, text: str) -> str:
        thai_digits = "๐๑๒๓๔๕๖๗๘๙"
        arabic_digits = "0123456789"
        return text.translate(str.maketrans(thai_digits, arabic_digits))

    def _clear_vram(self):
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()

    # =========================
    # OCR
    # =========================
    def _ocr_image(self, image):
        if self.__reader is None:
            raise ValueError("OCR reader not initialized")

        import numpy as np
        import cv2

        img = np.array(image)

        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        clahe = cv2.createCLAHE(2.0, (8, 8))
        img = clahe.apply(img)

        results = self.__reader.readtext(
            img,
            detail=0,
            paragraph=True,
            contrast_ths=0.1,
            adjust_contrast=0.5,
        )

        return " ".join(results)

    # =========================
    # CLEAN (safe TTS)
    # =========================
    def _strip_control_chars(self, text: str) -> str:
        text = unicodedata.normalize("NFC", text)
        return "".join(
            ch for ch in text if unicodedata.category(ch) in _KEEP_CATEGORIES
        )

    def fix_ocr_noise(self, text: str) -> str:
        if not text:
            return ""

        text = self._strip_control_chars(text)
        text = _OCR_NOISE_CHARS.sub("", text)

        text = re.sub(r"([เแโใไ])\s+([ก-ฮ])", r"\1\2", text)
        text = re.sub(r"([ก-ฮ])\s+([\u0E31-\u0E3A\u0E47-\u0E4E])", r"\1\2", text)
        text = re.sub(r"([ก-ฮ])\s+([ะาำ])", r"\1\2", text)
        text = re.sub(r"\s{2,}", " ", text)

        return text.strip()

    def clean(self, text: str) -> str:
        if not text:
            return ""

        text = unicodedata.normalize("NFC", text)
        text = self._strip_control_chars(text)
        text = thai_normalize(text)

        return " ".join(text.split())
    
    def fix_tts_issues(self, text: str) -> str:
        if not text:
            return ""

        text = text.replace("\n", " ")
        text = re.sub(r"[()\"'`]", "", text)

        def replace_repeat(match):
            before = match.group(1)

            context = before[-30:]

            tokens = word_tokenize(context, keep_whitespace=False)

            if not tokens:
                return before

            last_word = tokens[-1]

            return before + " " + last_word

        text = re.sub(r"(.{0,50})ๆ", replace_repeat, text)
        text = re.sub(r"(.{0,50})ต(?=\s|$)", replace_repeat, text)
        text = re.sub(r"[^\u0E00-\u0E7Fa-zA-Z0-9\s.,!?]", "", text)
        text = re.sub(r"\s{2,}", " ", text)

        return text.strip()

    # =========================
    # split
    # =========================
    def split_into_chapters(self, text: str) -> list:
        matches = list(self.__chapter_pattern.finditer(text))
        if not matches:
            return []

        chapters = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i < len(matches) - 1 else len(text)

            raw = m.group()
            nums = re.findall(r"[0-9๐-๙]+", raw)

            order = None
            if nums:
                order = int(self.thai_to_arabic(nums[0]))

            chapters.append(
                {
                    "order": order,
                    "story": text[start:end].strip(),
                }
            )

        return chapters

    # =========================
    # PDF → OCR → batches
    # =========================
    def extract_batches(self, pdf_path, batch_size=10):
        pages = convert_from_path(pdf_path, dpi=200)

        total = len(pages)

        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            texts = []

            for i in range(start, end):
                try:
                    text = self._ocr_image(pages[i])
                    texts.append(text)

                except Exception as e:
                    print(f"[Page Error] {i}: {e}")
                    texts.append("")

            self._clear_vram()
            yield "\n".join(texts)

    # =========================
    # MAIN
    # =========================
    def run(self, input_file, on_chapter_processed=None):
        path = Path(input_file)

        buffer = []
        carry_text = ""
        BATCH_SIZE = 10

        for text_batch in self.extract_batches(path):
            full_text = carry_text + text_batch
            chapters = self.split_into_chapters(full_text)

            if len(chapters) > 1:
                complete = chapters[:-1]
                carry_text = chapters[-1]["story"]
            else:
                carry_text = full_text
                continue

            for c in complete:
                c["story"] = self.clean(c["story"])
                c["story"] = self.fix_ocr_noise(c["story"])
                c["story"] = self.convert_numbers(c["story"])
                c["story"] = self.fix_tts_issues(c["story"])

                buffer.append(c)

                if len(buffer) >= BATCH_SIZE:
                    if on_chapter_processed:
                        on_chapter_processed(buffer)
                    buffer = []

        if carry_text:
            last = self.split_into_chapters(carry_text)
            for c in last:
                c["story"] = self.clean(c["story"])
                c["story"] = self.fix_ocr_noise(c["story"])
                c["story"] = self.convert_numbers(c["story"])
                buffer.append(c)

        if buffer and on_chapter_processed:
            on_chapter_processed(buffer)

        print("[Done]")
