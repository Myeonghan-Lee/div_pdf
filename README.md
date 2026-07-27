# 📄 이수증 PDF 분리 및 보안 처리 (OCR 지원)

여러 명의 이수증이 병합된 PDF 파일을 업로드하면, OCR(광학 문자 인식)을 통해 텍스트를 추출하여 사람별로 페이지를 분리하는 Streamlit 기반 웹 애플리케이션입니다. 

특히 분리된 파일은 **텍스트 수정 및 드래그가 불가능한 '이미지형 PDF'**로 자동 변환되어 제공되므로 원본의 위변조를 방지할 수 있습니다.

---

## 🌟 주요 기능

* **OCR 텍스트 추출**: 스캔본이나 이미지 형태의 PDF에서도 Tesseract OCR을 활용하여 '성명' 및 '생년월일' 정보를 자동으로 인식합니다.
* **수정 방지(Flattening)**: 분리된 PDF 페이지를 이미지로 변환한 뒤 다시 PDF로 저장하여, 텍스트 복사나 내용 수정을 원천적으로 차단합니다.
* **스마트 네이밍**: 추출된 데이터를 바탕으로 개별 파일의 이름을 `이름_YYYYMMDD.pdf` 형식으로 자동 변경합니다. (예: `홍길동_19900101.pdf`)
* **일괄 다운로드**: 변환 처리된 전체 파일을 하나의 `.zip` 파일로 압축하여 손쉽게 다운로드할 수 있습니다.

---

## 🛠️ 기술 스택

* **Language**: Python
* **Web Framework**: Streamlit
* **PDF / Image Processing**: pdf2image, Pillow
* **OCR (광학 문자 인식)**: pytesseract (Tesseract OCR)

---

## ☁️ Streamlit Cloud 배포 안내

Streamlit Community Cloud에 배포할 때는 파이썬 라이브러리 외에 리눅스 시스템 패키지 설치가 필요합니다. 
반드시 깃허브 저장소 최상단에 아래 내용이 포함된 `packages.txt` 파일을 생성해 주세요.

**📄 `packages.txt`**
```txt
tesseract-ocr
tesseract-ocr-kor
poppler-utils
