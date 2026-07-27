import streamlit as st
import io
import zipfile
import re
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image

st.set_page_config(page_title="PDF 분리 및 보안 처리", page_icon="📄")
st.title("📄 이수증 PDF 분리 (OCR 및 수정 방지)")

# ==================== 이름/생년월일 추출 ====================
BLACKLIST = {"성명","이름","생년","월일","주소","과정","교육","장소","수료","이수","증명",
             "발급","기관","일자","번호","성별","연락","전화","소속","부서","직급","직위"}

SEP = r"[\s:;>$\|)．·・.,=_~\-]*"                       # 구분기호(오인식 포함) 0회 이상
STOP = (r"(?=생년|생일|생|년|월|일|주소|과정|교육|장소|수료|이수|번호|성별|"
        r"연락|전화|소속|부서|직급|직위|[0-9]|[A-Za-z]|$)")   # 이름 끝 경계

def _clean_name(name):
    name = re.sub(r'[^가-힣A-Za-z]', '', name or "")
    if name.startswith("명") and len(name) >= 3:   # 라벨 '명' 찌꺼기 제거
        name = name[1:]
    return name

def _valid_name(name):
    return bool(name) and 2 <= len(name) <= 4 and name not in BLACKLIST

def extract_name(clean_text):
    cands = []  # (우선순위, 등장위치, 이름)
    # 전략1: 정상 라벨 '성명'(명 중복 허용)/'이름'
    for lab in [r"성\s*명명?", r"이\s*름"]:
        for m in re.finditer(lab + SEP + r"([가-힣]{2,4}?)" + STOP, clean_text):
            cands.append((0, m.start(), m.group(1)))
    # 전략2: 대체 라벨
    alt = r"(?:수료자|대상자|참가자|교육생|응시자|성\s*함|귀하)"
    for m in re.finditer(alt + SEP + r"([가-힣]{2,4}?)" + STOP, clean_text):
        cands.append((1, m.start(), m.group(1)))
    # 전략3: 라벨 첫 글자 오인식([성정생]) + 둘째글자 + 구분기호 필수
    for m in re.finditer(r"[성정생][가-힣][:;>$\|)．·.,=_~\-]+([가-힣]{2,4}?)" + STOP, clean_text):
        cands.append((2, m.start(), m.group(1)))
    # 전략4: 라벨 없이 '생년월일' 바로 앞 (최후 수단)
    for m in re.finditer(r"([가-힣]{2,4}?)(?=생년|생일)", clean_text):
        cands.append((3, m.start(), m.group(1)))

    out = []
    for pr, pos, raw in cands:
        nm = _clean_name(raw)
        if _valid_name(nm):
            out.append((pr, pos, nm))
    if not out:
        return None
    out.sort(key=lambda x: (x[0], x[1]))   # 정식 라벨 우선 → 먼저 등장한 것
    return out[0][2]

def _norm_digits(s):
    table = str.maketrans({'O':'0','o':'0','Q':'0','D':'0','I':'1','l':'1','|':'1',
                           'L':'1','Z':'2','z':'2','S':'5','s':'5','B':'8','g':'9','b':'6'})
    return s.translate(table)

def extract_birth(clean_text):
    m = re.search(r"생\s*년\s*월?\s*일?" + SEP + r"(.{0,15})", clean_text)
    region = _norm_digits(m.group(1)) if m else ""
    d = re.search(r"(\d{4})\D?(\d{1,2})\D?(\d{1,2})", region)
    if not d:
        d = re.search(r"((?:19|20)\d{2})\D{0,2}(\d{1,2})\D{0,2}(\d{1,2})",
                      _norm_digits(clean_text))
    if d:
        return f"{d.group(1)}{d.group(2).zfill(2)}{d.group(3).zfill(2)}"
    return None

# ==================== OCR ====================
def preprocess(img):
    gray = img.convert("L")
    return gray.point(lambda x: 0 if x < 160 else 255, mode="1")

def ocr_best(img):
    """여러 psm 설정으로 OCR을 시도해 '이름이 인식되는' 결과를 우선 채택"""
    variants = [img, preprocess(img)]                 # 원본 + 전처리본
    psms = ["--oem 1 --psm 6", "--oem 1 --psm 4", "--oem 1 --psm 11"]
    best_text, best_score = "", -1
    for im in variants:
        for cfg in psms:
            try:
                t = pytesseract.image_to_string(im, lang="kor+eng", config=cfg)
            except Exception:
                continue
            ct = t.replace("\n", "").replace(" ", "")
            score = (2 if extract_name(ct) else 0) + (1 if extract_birth(ct) else 0)
            if score > best_score:
                best_text, best_score = t, score
            if score == 3:                            # 이름+생년월일 모두 성공 시 조기 종료
                return best_text
    return best_text

# ==================== 메인 ====================
st.write("PDF를 OCR로 인식해 사람별로 분리하며, 결과물은 수정 불가한 '이미지형 PDF'로 제공됩니다.")
uploaded_file = st.file_uploader("PDF 파일을 업로드해주세요", type=["pdf"])
debug = st.checkbox("🔍 디버그 모드 (OCR 원문 보기)", value=False)

if uploaded_file is not None:
    pdf_bytes = uploaded_file.read()
    st.info("PDF를 이미지로 변환하고 텍스트를 분석 중입니다. (시간이 다소 소요될 수 있습니다)")
    try:
        images = convert_from_bytes(pdf_bytes, dpi=300)   # 해상도 상향
        zip_buffer = io.BytesIO()
        results = []
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i, img in enumerate(images):
                text = ocr_best(img)
                clean_text = text.replace("\n", "").replace(" ", "")
                name = extract_name(clean_text) or f"이름인식실패_페이지{i+1}"
                birth = extract_birth(clean_text) or "생년월일인식실패"
                filename = f"{name}_{birth}.pdf"
                results.append((i + 1, name, birth))

                pdf_buf = io.BytesIO()
                img.save(pdf_buf, format="PDF", resolution=200.0)  # 원본 화질로 저장
                zip_file.writestr(filename, pdf_buf.getvalue())

                if debug:
                    with st.expander(f"[페이지 {i+1}] {filename}"):
                        st.text(text[:600])

        fail = sum(1 for _, n, _ in results if n.startswith("이름인식실패"))
        st.success(f"총 {len(results)}개 처리 완료 (이름 인식 실패 {fail}건)")
        st.dataframe(
            {"페이지":[r[0] for r in results],
             "이름":[r[1] for r in results],
             "생년월일":[r[2] for r in results]},
            use_container_width=True)
        st.download_button("📦 보호된 분리 파일 전체 다운로드 (ZIP)",
                           data=zip_buffer.getvalue(),
                           file_name="수정불가_이수증.zip", mime="application/zip")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
        st.write("시스템에 Tesseract와 Poppler가 정상 설치되어 있는지 확인해주세요.")
