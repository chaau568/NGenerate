import os
import re
import fitz
import requests
import numpy as np
import unicodedata
import base64
from pathlib import Path

from pythainlp.util import normalize as thai_normalize
from pythainlp.corpus.common import thai_words
from pythainlp.tokenize import word_tokenize


class DataPreprocessing:

    def __init__(self, poppler_path: str | None = None, reader=None):

        self.__poppler_path = Path(poppler_path) if poppler_path else None
        self.__ocr_reader = reader

        self.__session = requests.Session()

        self.__ollama_url = "http://127.0.0.1:11434/api/generate"
        self.__typhoon_model = "scb10x/typhoon-ocr-3b"

        self.__chapter_regex = r"""
        (
        ตอน\s*[ททีี่่]*\s*[0-9๐-๙]+
        |
        ตอน\s*[0-9๐-๙]+
        |
        ต\s*อ\s*น\s*[0-9๐-๙]+
        |
        ep\s*\.?\s*\d+
        |
        episode\s*\d+
        |
        chapter\s*\d+
        )
        """

        self.__chapter_pattern = re.compile(
            self.__chapter_regex, re.VERBOSE | re.IGNORECASE
        )

        self.__thai_dict = set(thai_words())

    # -------------------------------
    # Typhoon OCR
    # -------------------------------

    def typhoon_ocr_page(self, image_bytes):

        img_base64 = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "model": self.__typhoon_model,
            "prompt": "อ่านข้อความภาษาไทยทั้งหมดจากภาพนี้ ให้คงรูปแบบบรรทัดเดิม",
            "images": [img_base64],
            "stream": False,
        }

        for _ in range(3):

            try:

                r = self.__session.post(self.__ollama_url, json=payload, timeout=600)

                r.raise_for_status()

                return r.json()["response"]

            except Exception as e:

                print("OCR RETRY:", e)

        return ""

    # -------------------------------
    # Fix Thai short vowel
    # -------------------------------

    def fix_short_u_guarded(self, text: str) -> str:

        words = word_tokenize(text, engine="newmm")

        fixed_words = []

        for w in words:

            if w in self.__thai_dict:
                fixed_words.append(w)
                continue

            w = re.sub(r"([ก-ฮ])ุ([นงมกบ])", r"\1ั\2", w)

            fixed_words.append(w)

        return "".join(fixed_words)

    # -------------------------------
    # Thai cleaning
    # -------------------------------

    def advanced_thai_cleaner(self, text: str) -> str:

        if not text:
            return ""

        chars_to_fix = {
            "\uf700": "ั",
            "\uf701": "ิ",
            "\uf702": "ี",
            "\uf703": "ึ",
            "\uf704": "ื",
            "\uf705": "่",
            "\uf706": "้",
            "\uf707": "๊",
            "\uf708": "๋",
            "\uf709": "์",
        }

        for wrong, right in chars_to_fix.items():
            text = text.replace(wrong, right)

        text = self.fix_short_u_guarded(text)

        text = thai_normalize(text)
        text = unicodedata.normalize("NFKC", text)

        text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")

        text = re.sub(r"ๆ+", "ๆ", text)
        text = re.sub(r"([่้๊๋]){2,}", r"\1", text)
        text = re.sub(r"([ิีึืุู]){2,}", r"\1", text)

        return " ".join(text.split())

    # -------------------------------
    # Text quality check
    # -------------------------------

    def is_text_readable(self, text: str) -> bool:

        if not text.strip():
            return False

        thai_standard_chars = re.findall(r"[ก-๙]", text)

        if len(thai_standard_chars) > 10 or len(text.strip()) > 50:
            return True

        return False

    # -------------------------------
    # OCR extraction using Typhoon
    # -------------------------------

    def typhoon_ocr_extraction(self, pdf_path: Path) -> str:

        texts = []

        with fitz.open(pdf_path) as doc:

            pages = list(enumerate(doc))

            def process_page(i_page):

                i, page = i_page

                print(f"OCR page {i+1}")

                pix = page.get_pixmap(dpi=140)

                if pix.width > 2000:
                    pix = page.get_pixmap(dpi=110)

                img_bytes = pix.tobytes("png")

                try:

                    text = self.typhoon_ocr_page(img_bytes)

                    text = self.advanced_thai_cleaner(text)

                    return text

                except Exception as e:

                    print("OCR ERROR:", e)

                    return ""

            for page in pages:
                text = process_page(page)
                texts.append(text)

        print("OCR DONE")

        return "\n\n".join(texts)

    # -------------------------------
    # Extract text
    # -------------------------------

    def extract_text_from_pdf(self, pdf_path: Path) -> str:

        print("OPEN PDF:", pdf_path)

        with fitz.open(pdf_path) as doc:

            if len(doc) == 0:
                raise ValueError("PDF has no pages")

            first_page_sample = doc[0].get_text()

            text_len = len(first_page_sample.strip())

            is_readable = self.is_text_readable(first_page_sample)

            print("Sample length:", text_len)

            if text_len > 20 and is_readable:

                print("Using PyMuPDF")

                full_text_parts = []

                for page in doc:

                    raw_text = page.get_text()

                    cleaned = self.advanced_thai_cleaner(raw_text)

                    full_text_parts.append(cleaned)

                return "\n\n".join(full_text_parts)

            else:

                print("Switching to Typhoon OCR")

                return self.typhoon_ocr_extraction(pdf_path)

    # -------------------------------
    # Convert Thai numbers
    # -------------------------------

    def thai_to_arabic(self, text: str) -> str:

        thai_digits = "๐๑๒๓๔๕๖๗๘๙"
        arabic_digits = "0123456789"

        return text.translate(str.maketrans(thai_digits, arabic_digits))

    # -------------------------------
    # Split chapters
    # -------------------------------

    def split_into_chapters(self, text: str):

        matches = list(self.__chapter_pattern.finditer(text))

        chapters = []

        if not matches:
            return [{"order": 1, "story": text.strip()}]

        for i, match in enumerate(matches):

            raw_header = match.group().strip()

            found_nums = re.findall(r"[0-9๐-๙]+", raw_header)

            raw_num = found_nums[0] if found_nums else str(i + 1)

            clean_num = int(self.thai_to_arabic(raw_num))

            start = match.start()

            end = matches[i + 1].start() if i < len(matches) - 1 else len(text)

            chapter_content = text[start:end].strip()

            chapters.append(
                {
                    "order": clean_num,
                    "story": chapter_content,
                }
            )

        return chapters

    # -------------------------------
    # Run
    # -------------------------------

    def run(self, input_file: str):

        path = Path(input_file)

        if path.suffix == ".txt":

            content = self.advanced_thai_cleaner(path.read_text(encoding="utf-8"))

        elif path.suffix == ".pdf":

            content = self.extract_text_from_pdf(path)

        else:

            raise ValueError("Unsupported file type")

        chapters = self.split_into_chapters(content)

        return chapters
