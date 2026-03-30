import re
import fitz
import gc
import torch
import unicodedata
from pathlib import Path

from pythainlp.util import normalize as thai_normalize
from pythainlp.util import num_to_thaiword


class DataPreprocessing:
    def __init__(self, reader=None):
        self.__reader = reader

        self.__chapter_pattern = re.compile(
            r"(ตอน\s*[ทที่]*\s*[0-9๐-๙]+|ep\s*\.?\s*\d+|chapter\s*\d+)", re.IGNORECASE
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
    def _needs_ocr(self, text: str) -> bool:
        if not text or len(text.strip()) < 20:
            return True

        thai_chars = len(re.findall(r"[ก-ฮ]", text))
        return thai_chars < 10

    def _ocr_page(self, page):
        if self.__reader is None:
            raise ValueError("OCR reader not initialized")

        import numpy as np
        import cv2

        mat = fitz.Matrix(200 / 72, 200 / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)

        img = np.frombuffer(pix.samples, dtype=np.uint8)
        img = img.reshape(pix.height, pix.width)

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
    def fix_ocr_noise(self, text: str) -> str:
        if not text:
            return ""

        text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")

        text = re.sub(r"[ฺ์ํ]+", "", text)

        text = re.sub(r"([ก-ฮ])\s+([่้๊๋])", r"\1\2", text)
        text = re.sub(r"([ก-ฮ])\s+([ะาำิีึืุู])", r"\1\2", text)
        text = re.sub(r"([เแโใไ])\s+([ก-ฮ])", r"\1\2", text)

        text = re.sub(r"\s{2,}", " ", text)

        return text.strip()

    def clean(self, text):
        text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")
        text = thai_normalize(text)
        return " ".join(text.split())

    def convert_numbers(self, text):
        def repl(m):
            try:
                return num_to_thaiword(int(m.group()))
            except:
                return m.group()

        return re.sub(r"\d+", repl, text)

    # =========================
    # split
    # =========================
    def split_into_chapters(self, text):
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

            chapters.append({"order": order, "story": text[start:end].strip()})

        return chapters

    # =========================
    # PDF streaming
    # =========================
    def extract_batches(self, pdf_path, batch_size=20):
        with fitz.open(pdf_path) as doc:
            total = len(doc)

            for start in range(0, total, batch_size):
                end = min(start + batch_size, total)
                texts = []

                for i in range(start, end):
                    try:
                        text = doc[i].get_text("text")

                        if self._needs_ocr(text):
                            text = self._ocr_page(doc[i])

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
