import streamlit as st
from pypdf import PdfReader, PdfWriter
import io
import zipfile
import re

st.set_page_config(page_title="PDF 자동 분리 및 이름 변경기", page_icon="📄")

st.title("📄 이수증 PDF 자동 분리 및 이름 변경")
st.write("여러 명의 이수증이 합쳐진 PDF 파일을 올리면, 사람별로 분리하고 '이름_생년월일'로 파일명을 자동 생성해 줍니다.")

# 파일 업로더
uploaded_file = st.file_uploader("PDF 파일을 업로드해주세요", type=["pdf"])

if uploaded_file is not None:
    # PDF 읽기
    reader = PdfReader(uploaded_file)
    total_pages = len(reader.pages)
    
    st.info(f"총 {total_pages}페이지의 PDF가 업로드되었습니다. 분리 작업을 시작합니다.")
    
    # 메모리 상에 ZIP 파일을 만들기 위한 버퍼
    zip_buffer = io.BytesIO()
    
    # 처리된 파일 개수를 세기 위한 변수
    success_count = 0
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for i in range(total_pages):
            page = reader.pages[i]
            text = page.extract_text()
            
            # 텍스트 추출 시 줄바꿈이나 공백으로 인한 오류를 줄이기 위해 공백 제거
            clean_text = text.replace('\n', '').replace(' ', '')
            
            # [수정된 부분] 이름 추출 로직: '생년월일' 글자 앞까지만 추출하도록 변경
            name_match = re.search(r"(성명:|성:)(.+?)생년월일", clean_text)
            if name_match:
                # 추출된 그룹에서 이름만 가져오고, 간혹 섞이는 '명' 글자 제거
                name = name_match.group(2).replace("명", "")
            else:
                name = f"이름알수없음_페이지{i+1}"
            
            # 생년월일 추출 로직 (생년월일:1981.01.09 패턴 대비)
            birth_match = re.search(r"생년월일:(\d{4})\.(\d{2})\.(\d{2})", clean_text)
            if birth_match:
                birth = f"{birth_match.group(1)}{birth_match.group(2)}{birth_match.group(3)}"
            else:
                birth = "생년월일알수없음"
            
            # 최종 파일명 생성 (예: 이용민_19810109.pdf)
            filename = f"{name}_{birth}.pdf"
            
            # 개별 페이지를 새로운 PDF로 만들기
            writer = PdfWriter()
            writer.add_page(page)
            
            # 메모리에 개별 PDF 저장 후 ZIP 파일에 추가
            pdf_buffer = io.BytesIO()
            writer.write(pdf_buffer)
            zip_file.writestr(filename, pdf_buffer.getvalue())
            success_count += 1
            
    st.success(f"성공적으로 {success_count}개의 파일을 분리했습니다! 아래 버튼을 눌러 압축 파일을 다운로드하세요.")
    
    # 다운로드 버튼 생성
    st.download_button(
        label="📦 분리된 파일 전체 다운로드 (ZIP)",
        data=zip_buffer.getvalue(),
        file_name="분리된_이수증.zip",
        mime="application/zip"
    )
