import streamlit as st
import io
import zipfile
import re
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image

st.set_page_config(page_title="PDF 분리 및 보안 처리", page_icon="📄")
st.title("📄 이수증 PDF 분리 (OCR 및 수정 방지)")
st.write("PDF를 이미지로 인식(OCR)하여 사람별로 분리하며, 결과물은 수정 불가한 '이미지형 PDF'로 제공됩니다.")

# ---------- 유틸 함수 ----------
def normalize_digits(s):
    """OCR이 숫자를 알파벳/기호로 오인식하는 대표 케이스 교정"""
    table = str.maketrans({
        'O': '0', 'o': '0', 'Q': '0', 'D': '0',
        'I': '1', 'l': '1', '|': '1', 'L': '1',
        'Z': '2', 'z': '2', 'S': '5', 's': '5',
        'B': '8', 'g': '9', 'b': '6',
    })
    return s.translate(table)

def extract_name(clean_text):
    # 1순위: '성명' 두 글자에 앵커 → '성남시' 등 오매칭 방지, 이름 뒤 경계 지정
    stop = r"(?=생|년|월|일|주|과|[0-9]|[A-Za-z]|$)"   # 수/교는 이름 글자와 충돌하므로 제외
    m = re.search(r"성\s*명\s*[:;>$\|)]*\s*([가-힣]{2,4}?)" + stop, clean_text)
    if m:
        return m.group(1)
    # 2순위: '명'이 깨진 경우 대비 (구분기호는 필수)
    m = re.search(r"성[가-힣]?[:;>$\|)]+([가-힣]{2,4}?)" + stop, clean_text)
    if m:
        return m.group(1)
    return None

def extract_birth(clean_text):
    # '생년월일' 라벨 이후 15자 구간을 잘라 숫자 정규화 후 파싱
    m = re.search(r"생\s*년\s*월?\s*일?\s*[:;>$\|)]*(.{0,15})", clean_text)
    region = normalize_digits(m.group(1)) if m else ""
    d = re.search(r"(\d{4})\D?(\d{1,2})\D?(\d{1,2})", region)
    if d:
        return f"{d.group(1)}{d.group(2).zfill(2)}{d.group(3).zfill(2)}"
    # fallback: 라벨 없이 전체에서 19xx/20xx 날짜 탐색
    d = re.search(r"((?:19|20)\d{2})\D{0,2}(\d{1,2})\D{0,2}(\d{1,2})",
                  normalize_digits(clean_text))
    if d:
        return f"{d.group(1)}{d.group(2).zfill(2)}{d.group(3).zfill(2)}"
    return None

def preprocess(img):
    """OCR 정확도 향상을 위한 그레이스케일 + 대비/이진화"""
    gray = img.convert("L")
    # 임계값 이진화 (스캔 품질에 따라 150~180 조정 가능)
    bw = gray.point(lambda x: 0 if x < 160 else 255, mode="1")
    return bw

# ---------- 메인 로직 ----------
uploaded_file = st.file_uploader("PDF 파일을 업로드해주세요", type=["pdf"])
debug = st.checkbox("🔍 디버그 모드 (OCR 원문 보기)", value=False)

if uploaded_file is not None:
    pdf_bytes = uploaded_file.read()
    st.info("PDF를 이미지로 변환하고 텍스트를 분석 중입니다. (시간이 다소 소요될 수 있습니다)")

    try:
        # 핵심 1) 해상도 300dpi로 상향 → OCR 정확도 대폭 향상
        images = convert_from_bytes(pdf_bytes, dpi=300)
        total_pages = len(images)
        zip_buffer = io.BytesIO()
        success_count = 0
        results = []

        # 핵심 2) Tesseract 설정 최적화 (LSTM 엔진 + 균일 블록 가정 + 한/영 병행)
        ocr_config = r"--oem 1 --psm 6"

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i, img in enumerate(images):
                proc = preprocess(img)
                text = pytesseract.image_to_string(proc, lang="kor+eng", config=ocr_config)
                clean_text = text.replace("\n", "").replace(" ", "")

                name = extract_name(clean_text) or f"이름인
