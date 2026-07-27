import streamlit as st
import io
import zipfile
import re
from pdf2image import convert_from_bytes
import pytesseract

st.set_page_config(page_title="PDF 분리 및 보안 처리", page_icon="📄")

st.title("📄 이수증 PDF 분리 (OCR 및 수정 방지)")
st.write("PDF의 내용을 이미지로 인식(OCR)하여 파일을 분리하며, 결과물은 텍스트 수정이 불가능한 '이미지형 PDF'로 제공됩니다.")

# 파일 업로더
uploaded_file = st.file_uploader("PDF 파일을 업로드해주세요", type=["pdf"])

if uploaded_file is not None:
    pdf_bytes = uploaded_file.read()
    
    st.info("PDF를 이미지로 변환하고 텍스트를 분석 중입니다. (시간이 다소 소요될 수 있습니다)")
    
    try:
        # PDF의 모든 페이지를 이미지 리스트로 변환
        images = convert_from_bytes(pdf_bytes)
        total_pages = len(images)
        
        # 메모리 상에 ZIP 파일을 만들기 위한 버퍼
        zip_buffer = io.BytesIO()
        success_count = 0
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for i, img in enumerate(images):
                # 이미지에서 한국어 텍스트 추출 (OCR)
                text = pytesseract.image_to_string(img, lang='kor')
                
                # 공백 및 줄바꿈 제거
                clean_text = text.replace('\n', '').replace(' ', '')
                
                # 이름 추출 (성명: ~ 생년월일 앞까지)
                name_match = re.search(r"(성명:|성:)(.+?)생년월일", clean_text)
                if name_match:
                    name = name_match.group(2).replace("명", "")
                else:
                    name = f"이름인식실패_페이지{i+1}"
                
                # 생년월일 추출 (OCR 특성상 온점이 빠지거나 잘못 인식될 수 있으므로 유연하게 대처)
                birth_match = re.search(r"생년월일:(\d{4})[.,]?(\d{2})[.,]?(\d{2})", clean_text)
                if birth_match:
                    birth = f"{birth_match.group(1)}{birth_match.group(2)}{birth_match.group(3)}"
                else:
                    birth = "생년월일인식실패"
                
                # 최종 파일명
                filename = f"{name}_{birth}.pdf"
                
                # 이미지를 PDF로 변환하여 메모리에 저장 (수정 방지 효과)
                pdf_buffer = io.BytesIO()
                img.save(pdf_buffer, format='PDF', resolution=100.0)
                
                # ZIP 파일에 추가
                zip_file.writestr(filename, pdf_buffer.getvalue())
                success_count += 1
                
        st.success(f"성공적으로 {success_count}개의 파일을 분리 및 보안 처리했습니다!")
        
        # 다운로드 버튼
        st.download_button(
            label="📦 보호된 분리 파일 전체 다운로드 (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="수정불가_이수증.zip",
            mime="application/zip"
        )
        
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
        st.write("로컬 환경에서 실행 중이라면 Tesseract와 Poppler가 시스템에 설치되어 있는지 확인해주세요.")
