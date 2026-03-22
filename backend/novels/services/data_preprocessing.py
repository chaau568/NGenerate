# root@bbac6ab6e08f:/workspace/ngenerate/api/services# cat data_preprocessing.py
import os
import re
import fitz
import numpy as np
import unicodedata
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from pythainlp.util import normalize as thai_normalize
from pythainlp.corpus.common import thai_words
from pythainlp.tokenize import word_tokenize
from pythainlp.util import num_to_thaiword


class DataPreprocessing:

    def __init__(self, poppler_path: str | None = None, reader=None):
        self.__poppler_path = Path(poppler_path) if poppler_path else None
        self.__reader = reader

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
        self.__tone_lookup = self._build_tone_lookup()

    # --------------------------------------------------
    # EasyOCR reader
    # --------------------------------------------------

    def _get_reader(self):
        if self.__reader is None:
            raise RuntimeError(
                "EasyOCR reader not initialized. Pass reader= when creating DataPreprocessing."
            )
        return self.__reader

    # --------------------------------------------------
    # Thai text cleaning
    # --------------------------------------------------

    def fix_thai_spacing_and_tones(self, text: str) -> str:
        if not text:
            return ""

        text = re.sub(r"([ก-ฮ])\s+([่้๊๋])", r"\1\2", text)

        text = re.sub(r"([ก-ฮ][่้๊๋]?)\s+([ะาำิีึืุู])", r"\1\2", text)

        text = re.sub(r"([เแโใไ])\s+([ก-ฮ])", r"\1\2", text)
        text = re.sub(r"([ไใเแโ])\s+([มกข])", r"\1\2", text)

        text = re.sub(r"(?<!\S)([ก-ฮ])\s+([ก-ฮ]{1,2})(?!\S)", r"\1\2", text)

        text = re.sub(r"น\s*้\s*ำ", "น้ำ", text)
        text = re.sub(r"น้\s*ำ", "น้ำ", text)

        text = unicodedata.normalize("NFC", text)

        def reorder(match):
            base = match.group(1)
            tone = match.group(2)
            vowel = match.group(3)
            return base + vowel + tone

        text = re.sub(r"([ก-ฮ])([่้๊๋])([ัิีึืุู])", reorder, text)

        text = re.sub(r"\s{2,}", " ", text)

        return text

    def fix_common_thai_errors(self, text: str) -> str:
        COMMON_FIX = {
            "ไม": "ไม่",
            "ได": "ได้",
            "เปน": "เป็น",
            "แลว": "แล้ว",
            "นํา": "นำ",
            "น้ํา": "น้ำ",
        }

        for wrong, right in COMMON_FIX.items():
            text = re.sub(rf"\b{wrong}\b", right, text)

        return text

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

    def expand_mai_yamok(self, text: str) -> str:
        words = word_tokenize(text, engine="newmm")
        result = []
        i = 0
        while i < len(words):
            if words[i] == "ๆ" and result:
                prev = result[-1]
                result.append(prev)
            else:
                result.append(words[i])
            i += 1
        return "".join(result)

    def convert_numbers_to_words(self, text: str) -> str:
        text = self.thai_to_arabic(text)

        def replace_num(match):
            try:
                return num_to_thaiword(int(match.group()))
            except Exception:
                return match.group()

        return re.sub(r"\d+", replace_num, text)

    def _build_tone_lookup(self):
        from collections import defaultdict
        from pythainlp.corpus.common import thai_words as _tw

        tones = ["่", "้", "๊", "๋"]
        _dict = set(_tw())
        tone_lookup = defaultdict(list)
        for word in _dict:
            stripped = "".join(c for c in word if c not in tones)
            if stripped != word:
                tone_lookup[stripped].append(word)
        return tone_lookup

    def fix_missing_tones(self, text: str) -> str:
        tones = ["่", "้", "๊", "๋"]
        TONE_PRIORITY = {"่": 0, "้": 1, "๊": 2, "๋": 3}
        _dict = self.__thai_dict
        tone_lookup = self.__tone_lookup

        FORCE_MAP = {
            "ที": "ที่",
            "ไม": "ไม่",
            "แต": "แต่",
            "ใกล": "ใกล้",
            "แลว": "แล้ว",
            "ดาน": "ด้าน",
            "นา": "น่า",
            "หนา": "หน้า",
            "ขาง": "ข้าง",
            "ฝาย": "ฝ่าย",
            "ถา": "ถ้า",
            "หม": "ห่ม",
            "ตอนที": "ตอนที่",
            "เมือ": "เมื่อ",
            "เรือง": "เรื่อง",
            "เชือ": "เชื่อ",
            "เพือ": "เพื่อ",
            "รู": "รู้",
            "อยู": "อยู่",
            "แม": "แม้",
            "ได": "ได้",
            "วา": "ว่า",
            "ดวย": "ด้วย",
            "ตอง": "ต้อง",
            "ครัง": "ครั้ง",
            "ครง": "ครั้ง",
            "ใหญ": "ใหญ่",
            "นอย": "น้อย",
            "ใหม": "ใหม่",
            "เกา": "เก่า",
            "เปน": "เป็น",
        }

        NO_FIX = {
            "เมือง",
            "ตอน",
            "ใน",
            "เขา",
            "ทาง",
            "นาง",
            "วาง",
            "ราง",
            "กาง",
            "วาน",
        }

        def get_tones_in_word(word):
            return [c for c in word if c in tones]

        def best_candidate(word):
            if word in NO_FIX:
                return word
            if word in FORCE_MAP:
                return FORCE_MAP[word]
            if word in _dict:
                return word
            candidates = tone_lookup.get(word, [])
            if not candidates:
                return word
            if len(candidates) == 1:
                return candidates[0]

            def score(w):
                ts = get_tones_in_word(w)
                return min((TONE_PRIORITY.get(t, 99) for t in ts), default=99)

            return min(candidates, key=score)

        words = text.split(" ")
        corrected = []
        for w in words:
            if not w:
                corrected.append(w)
            elif not any(
                c in "กขคงจฉชซญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮเแโใไ" for c in w
            ):
                corrected.append(w)
            else:
                corrected.append(best_candidate(w))
        return " ".join(corrected)

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

        text = self.fix_thai_spacing_and_tones(text)

        text = thai_normalize(text)
        text = unicodedata.normalize("NFKC", text)

        text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")

        text = re.sub(r"ๆ+", "ๆ", text)
        text = re.sub(r"([่้๊๋]){2,}", r"\1", text)
        text = re.sub(r"([ิีึืุู]){2,}", r"\1", text)
        text = " ".join(text.split())

        text = self.fix_common_thai_errors(text)

        text = self.fix_short_u_guarded(text)

        text = self.fix_missing_tones(text)

        text = self.expand_mai_yamok(text)

        return text

    def is_text_readable(self, text: str) -> bool:
        if not text.strip():
            return False
        thai_chars = re.findall(r"[ก-๙]", text)
        if len(thai_chars) > 10 or len(text.strip()) > 50:
            return True
        return False

    # --------------------------------------------------
    # Sample page selection
    # --------------------------------------------------

    def _get_sample_indices(self, total_pages: int, n: int = 10) -> list:
        if total_pages <= n:
            return list(range(total_pages))

        skip = min(5, total_pages // 10)
        usable = total_pages - skip

        step = max(1, usable // n)
        return [skip + i * step for i in range(n) if skip + i * step < total_pages]

    # --------------------------------------------------
    # Tone quality check
    # --------------------------------------------------

    def _check_tone_quality(self, sample: str) -> bool:
        MUST_HAVE_TONE = [
            "ได้",
            "ไม่",
            "ที่",
            "ว่า",
            "ต้อง",
            "แล้ว",
            "ให้",
            "ด้วย",
            "นั้น",
            "นี้",
            "อยู่",
            "รู้",
            "แต่",
            "เมื่อ",
            "เพื่อ",
        ]
        WITHOUT_TONE = [
            "ได",
            "ไม",
            "ที",
            "วา",
            "ตอง",
            "แลว",
            "ให",
            "ดวย",
            "นน",
            "อยู",
            "รู",
            "แต",
            "เมือ",
            "เพือ",
        ]

        found_with = sum(1 for w in MUST_HAVE_TONE if w in sample)
        found_without = sum(1 for w in WITHOUT_TONE if w in sample)

        print(f"   tone check: with={found_with}, without={found_without}")

        if found_with >= 2:
            return True

        if found_with == 0 and found_without == 0:
            return True

        return False

    # --------------------------------------------------
    # PyMuPDF extraction — parallel pages
    # --------------------------------------------------

    def _extract_page_text(self, page) -> str:
        raw = page.get_text()
        raw = self.fix_thai_spacing_and_tones(raw)

        return self.advanced_thai_cleaner(raw)

    def pymupdf_extraction(self, pdf_path: Path, max_workers: int = 8) -> str:
        with fitz.open(pdf_path) as doc:
            pages = list(doc)
            results = [None] * len(pages)

            def process(args):
                i, page = args
                return i, self._extract_page_text(page)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(process, (i, p)): i for i, p in enumerate(pages)
                }
                for future in as_completed(futures):
                    i, text = future.result()
                    results[i] = text

        return "\n\n".join(r for r in results if r)

    # --------------------------------------------------
    # EasyOCR extraction — batch (ใช้เฉพาะ PDF สแกนจริงๆ)
    # --------------------------------------------------

    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        import cv2

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        gray = cv2.filter2D(gray, -1, kernel)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    def _page_to_image_bytes(self, page, dpi: int = 150) -> np.ndarray:
        import cv2

        pix = page.get_pixmap(dpi=dpi)
        if pix.width > 2000:
            pix = page.get_pixmap(dpi=110)
        img_bytes = np.frombuffer(pix.tobytes("png"), dtype=np.uint8)
        return cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)

    def _ocr_page(self, page_img: np.ndarray) -> str:
        ocr_reader = self._get_reader()
        page_img = self._preprocess_image(page_img)
        result = ocr_reader.readtext(page_img, detail=1)

        if not result:
            return ""

        lines = [
            text
            for (_, text, conf) in result
            if isinstance(text, str) and text.strip() and conf > 0.3
        ]

        return self.advanced_thai_cleaner("\n".join(lines))

    def ocr_extraction(
        self,
        pdf_path: Path,
        max_workers: int = 4,
        batch_size: int = 8,
    ) -> str:
        print(f"EasyOCR: opening {pdf_path}")

        with fitz.open(pdf_path) as doc:
            pages = list(doc)
            total = len(pages)
            print(f"EasyOCR: {total} pages")

            page_images = [None] * total

            def render(args):
                i, page = args
                return i, self._page_to_image_bytes(page)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(render, (i, p)): i for i, p in enumerate(pages)
                }
                for future in as_completed(futures):
                    page_idx, page_img = future.result()
                    page_images[page_idx] = page_img

        results = [None] * total
        for batch_start in range(0, total, batch_size):
            batch = page_images[batch_start : batch_start + batch_size]
            for j, page_img in enumerate(batch):
                idx = batch_start + j
                try:
                    results[idx] = self._ocr_page(page_img)
                    if idx % 50 == 0:
                        print(f"EasyOCR: page {idx+1}/{total}")
                except Exception as e:
                    print(f"EasyOCR error page {idx+1}: {e}")
                    results[idx] = ""

        print("EasyOCR: done")
        return "\n\n".join(r for r in results if r)

    # --------------------------------------------------
    # Main extract — auto-detect embedded vs scan
    # --------------------------------------------------

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        print(f"Opening PDF: {pdf_path}")

        with fitz.open(pdf_path) as doc:
            if len(doc) == 0:
                raise ValueError("PDF has no pages")

            total_pages = len(doc)

            sample_indices = self._get_sample_indices(total_pages, n=10)
            sample_texts = [doc[i].get_text() for i in sample_indices]
            sample = "\n".join(sample_texts)

        has_text = len(sample.strip()) > 100 and self.is_text_readable(sample)

        if not has_text:
            print(f"Strategy: EasyOCR (scanned, no embedded text)")
            return self.ocr_extraction(pdf_path)

        tone_ok = self._check_tone_quality(sample)

        if tone_ok:
            print(f"Strategy: PyMuPDF (embedded text, tone_ok=True)")
        else:
            print(f"Strategy: PyMuPDF + aggressive cleaning (tone_ok=False)")

        return self.pymupdf_extraction(pdf_path)

    # --------------------------------------------------
    # Thai number conversion
    # --------------------------------------------------

    def thai_to_arabic(self, text: str) -> str:
        thai_digits = "๐๑๒๓๔๕๖๗๘๙"
        arabic_digits = "0123456789"
        return text.translate(str.maketrans(thai_digits, arabic_digits))

    # --------------------------------------------------
    # Chapter splitting
    # --------------------------------------------------

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

    # --------------------------------------------------
    # Run
    # --------------------------------------------------

    def run(self, input_file: str):
        path = Path(input_file)

        if path.suffix == ".txt":
            content = path.read_text(encoding="utf-8")
        elif path.suffix == ".pdf":
            content = self.extract_text_from_pdf(path)
        else:
            raise ValueError("Unsupported file type")

        chapters = self.split_into_chapters(content)

        for chapter in chapters:
            chapter["story"] = self.convert_numbers_to_words(chapter["story"])

        return chapters
