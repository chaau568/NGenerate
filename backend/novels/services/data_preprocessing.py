import re
import fitz
import easyocr
import numpy as np
import unicodedata
from pdf2image import convert_from_path
from pathlib import Path
from pythainlp.util import normalize as thai_normalize

from pythainlp.corpus.common import thai_words
from pythainlp.tokenize import word_tokenize


class DataPreprocessing:
    def __init__(self, poppler_path: str):
        self.__poppler_path = Path(poppler_path)
        self.__ocr_reader = easyocr.Reader(["th", "en"], gpu=False)
        self.__chapter_regex = r"""
        (
        ตอน\s*ที\s*[่้]?\s*[0-9๐-๙]+
        |ตอน\s*[0-9๐-๙]+
        |Episode\s*\d+
        )
        """
        self.__chapter_pattern = re.compile(
            self.__chapter_regex, re.VERBOSE | re.IGNORECASE
        )
        self.__thai_dict = set(thai_words())

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
            "\uf70a": "่",
            "\uf70b": "้",
            "\uf70c": "๊",
            "\uf70d": "๋",
            "\uf70e": "์",
            "\uf710": "ั",
            "\uf711": "ู",
            "\uf712": "ุ",
            "\uf713": "ู",
            "\uf714": "ู",
        }
        for wrong, right in chars_to_fix.items():
            text = text.replace(wrong, right)

        # text = re.sub(r"([ก-ฮ])ุ([นงมกบ])", r"\1ั\2", text)
        text = self.fix_short_u_guarded(text)

        text = re.sub(r"เ([ก-ฮ])ั([นงมกบ])", r"เ\1็\2", text)
        text = re.sub(r"เ([ก-ฮ])ุ([นงมกบ])", r"เ\1็\2", text)

        text = thai_normalize(text)
        text = unicodedata.normalize("NFKC", text)

        text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")

        return " ".join(text.split())

    def is_text_readable(self, text: str) -> bool:
        if not text.strip():
            return False

        thai_standard_chars = re.findall(r"[ก-๙]", text)

        if len(thai_standard_chars) > 10 or len(text.strip()) > 50:
            return True
        return False

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        with fitz.open(pdf_path) as doc:
            first_page_sample = doc[0].get_text()
            text_len = len(first_page_sample.strip())
            is_readable = self.is_text_readable(first_page_sample)

            print(f"DEBUG: Length={text_len}, Readable={is_readable}")

            if text_len > 20 and is_readable:
                print("✅ Quality Check Passed: Using PyMuPDF (Cleaned)")
                full_text = ""
                for page in doc:
                    raw_text = page.get_text()
                    full_text += self.advanced_thai_cleaner(raw_text) + "\n\n"
                return full_text
            else:
                print("⚠️ Quality Check Failed or Scanned PDF: Switching to EasyOCR")
                return self.ocr_extraction(pdf_path)

    def ocr_extraction(self, pdf_path: Path) -> str:
        images = convert_from_path(pdf_path, dpi=300, poppler_path=self.__poppler_path)
        full_text = ""
        for i, img in enumerate(images):
            print(f"🔍 OCR Processing Page {i+1}/{len(images)}")
            results = self.__ocr_reader.readtext(np.array(img))
            page_text = "\n".join([r[1] for r in results])
            full_text += self.advanced_thai_cleaner(page_text) + "\n\n"
        return full_text

    def thai_to_arabic(self, text: str) -> str:
        thai_digits = "๐๑๒๓๔๕๖๗๘๙"
        arabic_digits = "0123456789"
        translation_table = str.maketrans(thai_digits, arabic_digits)
        return text.translate(translation_table)

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

            chapters.append({"order": clean_num, "story": chapter_content})

        return chapters

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
