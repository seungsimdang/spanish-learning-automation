# 스페인어 학습 자동화 시스템

## 개요

ChatGPT API를 사용하여 스페인어 학습 자료를 자동으로 수집하고 분석하는 시스템입니다.
매일 자동으로 스페인어 기사와 팟캐스트를 수집하여 Notion에 정리합니다.

## 🚀 빠른 시작

### 1. Repository Secrets 설정

GitHub Repository → Settings → Secrets and variables → Actions → Repository secrets에서 다음을 추가:

#### 필수 Secrets:

- `OPENAI_API_KEY`: OpenAI API 키
- `NOTION_TOKEN`: Notion API 키
- `NOTION_DATABASE_ID`: Notion 데이터베이스 ID

### 2. 자동 실행

- **자동**: 매일 평일 오전 8시 (한국시간)에 자동 실행
- **수동**: Actions 탭 → "스페인어 학습 자료 자동 수집" → "Run workflow"

### 3. 결과 확인

Notion 데이터베이스에서 자동으로 생성된 학습 자료 확인

## 📋 API 키 발급 방법

### OpenAI API 키

1. [OpenAI Platform](https://platform.openai.com/api-keys)에서 로그인
2. "Create new secret key" 클릭
3. 키 복사 후 Repository Secret에 `OPENAI_API_KEY`로 저장

### Notion API 키

1. [Notion Integrations](https://www.notion.so/my-integrations)에서 로그인
2. "New integration" 클릭
3. 이름 설정 후 "Submit"
4. "Internal Integration Token" 복사 후 Repository Secret에 `NOTION_TOKEN`으로 저장
5. 학습 자료 데이터베이스에 integration 권한 부여
6. 데이터베이스 ID를 Repository Secret에 `NOTION_DATABASE_ID`로 저장

## 🏗️ 프로젝트 구조

```
spanish-learning-automation/
├── .github/workflows/
│   └── spanish-learning-automation.yml  # GitHub Actions 워크플로우
└── scripts/
    ├── calculate_schedule.py           # 학습 일정 계산
    ├── collect_materials.py            # 학습 자료 수집 및 분석
    ├── create_notion_pages.py          # Notion 페이지 생성
    ├── llm_analyzer.py                 # LLM 기반 분석기
    └── alternative_finder.py           # 대체 표현 찾기
```

## 📊 분석 결과 형식

### 기사 분석

```
📝 B2 문법: 이 문장에는 접속법 현재가 쓰이고 있다 (B2): 'Es importante que sepamos la verdad' - 중요성이나 필요성을 표현할 때 사용
```

### 팟캐스트 분석

```
🎯 B2 구어체: o sea (즉, 그러니까) | ¿no te parece? (그렇게 생각하지 않아?) | la cosa es que (문제는)
```

## 🐛 문제 해결

### Actions 실행 실패

**해결**: Repository Secrets에 필요한 키들이 모두 올바르게 설정되어 있는지 확인

### API 키 오류

**해결**: OpenAI API 키가 유효하고 크레딧이 있는지 확인

### Notion 연동 오류

**해결**:

- Notion API 키가 유효한지 확인
- 데이터베이스 ID가 올바른지 확인
- Integration에 데이터베이스 권한이 있는지 확인
