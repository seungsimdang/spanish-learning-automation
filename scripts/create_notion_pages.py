#!/usr/bin/env python3
"""
Create Notion pages for collected Spanish learning materials.
"""
import os
import requests
import json
from datetime import datetime

def get_database_properties(database_id, headers):
    """데이터베이스의 속성 정보를 조회"""
    try:
        response = requests.get(
            f'https://api.notion.com/v1/databases/{database_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            db_data = response.json()
            properties = db_data.get('properties', {})
            print("=== Notion 데이터베이스 속성 정보 ===")
            for prop_name, prop_info in properties.items():
                prop_type = prop_info.get('type', 'unknown')
                print(f"- {prop_name}: {prop_type}")
                
                # Select 타입의 경우 사용 가능한 옵션들도 출력
                if prop_type == 'select':
                    options = prop_info.get('select', {}).get('options', [])
                    if options:
                        option_names = [opt.get('name', '') for opt in options]
                        print(f"  옵션들: {option_names}")
                    
            print("=======================================")
            return properties
        else:
            print(f"데이터베이스 조회 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return {}
    except Exception as e:
        print(f"데이터베이스 조회 오류: {e}")
        return {}

def create_notion_page(title, url, content_type, memo, category="", vocabulary="", duration="", difficulty=""):
    """Notion 페이지 생성"""
    
    # 중복 페이지 확인
    print(f"\n🔍 중복 페이지 확인 중: {title}")
    if check_duplicate_page(title, content_type):
        print(f"⚠️  중복 페이지가 이미 존재합니다. 페이지 생성을 건너뜁니다.")
        return None
    
    print(f"✅ 중복 없음. 페이지 생성을 계속합니다.")
    
    # Notion API 설정
    NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
    DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')

    if not NOTION_TOKEN or not DATABASE_ID:
        print("Notion 토큰 또는 데이터베이스 ID가 설정되지 않았습니다.")
        return None

    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }
    
    # 데이터베이스 속성 정보 조회
    db_properties = get_database_properties(DATABASE_ID, headers)
    
    # 사용 가능한 옵션들 저장
    select_options = {}
    for prop_name, prop_info in db_properties.items():
        if prop_info.get('type') == 'select':
            options = prop_info.get('select', {}).get('options', [])
            select_options[prop_name] = [opt.get('name', '') for opt in options]
    
    print(f"DEBUG: Select 옵션들: {select_options}")
    
    # 실제 속성 이름 찾기 - 명확한 매핑
    title_prop = None
    url_prop = None
    type_prop = None        # 자료 유형
    notes_prop = None       # 메모/학습 내용
    date_prop = None        # 학습 예정일
    difficulty_prop = None  # 난이도 (B1/B2/C1)
    area_prop = None        # 학습 영역
    region_prop = None      # 지역
    vocabulary_prop = None  # 핵심 어휘
    duration_prop = None    # 재생시간
    
    # 속성 이름으로 정확히 매핑
    for prop_name, prop_info in db_properties.items():
        prop_type = prop_info.get('type', '')
        
        # 제목 속성
        if prop_type == 'title':
            title_prop = prop_name
        
        # URL 속성  
        elif prop_type == 'url':
            url_prop = prop_name
            
        # 날짜 속성
        elif prop_type == 'date':
            date_prop = prop_name
            
        # Select 속성들 - 이름으로 구분
        elif prop_type == 'select':
            if '난이도' in prop_name:
                difficulty_prop = prop_name
            elif '자료' in prop_name or '유형' in prop_name:
                type_prop = prop_name
            elif '영역' in prop_name:
                area_prop = prop_name
            elif '지역' in prop_name or 'region' in prop_name.lower():
                region_prop = prop_name
                print(f"DEBUG: 지역 속성 발견: '{prop_name}'")
                
        # Rich text 속성들 - 이름으로 구분
        elif prop_type == 'rich_text':
            if '메모' in prop_name or '학습' in prop_name or '내용' in prop_name:
                notes_prop = prop_name
            elif '어휘' in prop_name:
                vocabulary_prop = prop_name
            elif '시간' in prop_name or '재생' in prop_name:
                duration_prop = prop_name
    
    print(f"매핑된 속성들:")
    print(f"- 제목: {title_prop}")
    print(f"- URL: {url_prop}")
    print(f"- 자료 유형: {type_prop}")
    print(f"- 난이도: {difficulty_prop}")
    print(f"- 학습 영역: {area_prop}")
    print(f"- 지역: {region_prop}")
    print(f"- 메모: {notes_prop}")
    print(f"- 어휘: {vocabulary_prop}")
    print(f"- 재생시간: {duration_prop}")
    print(f"- 날짜: {date_prop}")
    
    # 필수 속성이 없으면 오류
    if not title_prop:
        print("오류: 제목 속성을 찾을 수 없습니다.")
        return None
    
    # 페이지 속성 설정 - 올바른 값들로 설정
    properties = {}
    
    # 제목 속성 (필수)
    if title_prop:
        properties[title_prop] = {
            "title": [
                {
                    "text": {
                        "content": title or "제목 없음"
                    }
                }
            ]
        }
    
    # URL 속성 - 유효한 URL만 추가
    if url_prop and url and (url.startswith('http://') or url.startswith('https://')):
        properties[url_prop] = {
            "url": url
        }
    
    # 자료 유형 속성 - 유효한 옵션만 사용
    if type_prop:
        type_options = select_options.get(type_prop, [])
        print(f"DEBUG: 자료 유형 옵션들: {type_options}")
        
        # content_type에 따라 적절한 값 설정
        if content_type == "podcast":
            # 팟캐스트 관련 옵션 찾기
            if "팟캐스트" in type_options:
                type_value = "팟캐스트"
            elif "Podcast" in type_options:
                type_value = "Podcast"  
            elif "듣기" in type_options:
                type_value = "듣기"
            else:
                type_value = type_options[0] if type_options else "기타"
        elif content_type == "article":
            # 기사 관련 옵션 찾기
            if "기사" in type_options:
                type_value = "기사"
            elif "Article" in type_options:
                type_value = "Article"
            elif "읽기" in type_options:  
                type_value = "읽기"
            else:
                type_value = type_options[0] if type_options else "기타"
        else:
            type_value = type_options[0] if type_options else "기타"
            
        print(f"DEBUG: 선택된 자료 유형: {type_value}")
        properties[type_prop] = {
            "select": {
                "name": type_value
            }
        }
    
    # 난이도 속성 - 동적으로 분석된 난이도 사용
    if difficulty_prop:
        difficulty_options = select_options.get(difficulty_prop, [])
        print(f"DEBUG: 난이도 옵션들: {difficulty_options}")
        
        # 전달받은 난이도를 우선 사용
        preferred_difficulty = difficulty if difficulty else "B2"
        
        print(f"DEBUG: 전달받은 난이도: {preferred_difficulty}")
        
        # 유효한 옵션 중에서 선택
        if preferred_difficulty in difficulty_options:
            difficulty_value = preferred_difficulty
        elif "B2+" in difficulty_options and preferred_difficulty == "B2+":
            difficulty_value = "B2+"
        elif "B1+" in difficulty_options and preferred_difficulty == "B1+":
            difficulty_value = "B1+"
        elif "B2" in difficulty_options:
            difficulty_value = "B2"
        elif "B1" in difficulty_options:
            difficulty_value = "B1"
        elif "C1" in difficulty_options:
            difficulty_value = "C1"
        else:
            difficulty_value = difficulty_options[0] if difficulty_options else "B2"
            
        print(f"DEBUG: 선택된 난이도: {difficulty_value}")
        properties[difficulty_prop] = {
            "select": {
                "name": difficulty_value
            }
        }
    
    # 학습 영역 속성 - 유효한 옵션만 사용
    if area_prop:
        area_options = select_options.get(area_prop, [])
        print(f"DEBUG: 학습 영역 옵션들: {area_options}")
        
        if content_type == "podcast":
            # 듣기 관련 옵션 찾기
            if "청해" in area_options:
                area_value = "청해"
            elif "듣기" in area_options:
                area_value = "듣기"
            elif "Listening" in area_options:
                area_value = "Listening"
            else:
                area_value = area_options[0] if area_options else "청해"
        elif content_type == "article":
            # 읽기 관련 옵션 찾기
            if "읽기" in area_options:
                area_value = "읽기"
            elif "독해" in area_options:
                area_value = "독해"
            elif "Reading" in area_options:
                area_value = "Reading"
            else:
                area_value = area_options[0] if area_options else "읽기"
        else:
            area_value = area_options[0] if area_options else "종합"
            
        print(f"DEBUG: 선택된 학습 영역: {area_value}")
        properties[area_prop] = {
            "select": {
                "name": area_value
            }
        }
    
    # 지역 속성 - 유효한 옵션만 사용
    if region_prop:
        region_options = select_options.get(region_prop, [])
        print(f"DEBUG: 지역 속성명: '{region_prop}'")
        print(f"DEBUG: 지역 옵션들: {region_options}")
        print(f"DEBUG: 제목: '{title}'")
        print(f"DEBUG: 콘텐츠 타입: '{content_type}'")
        
        # 팟캐스트일 때는 제목으로 지역 판단
        if content_type == "podcast":
            if "Radio Ambulante" in title:
                print("DEBUG: Radio Ambulante 팟캐스트 감지됨 - 중남미로 설정")
                # Radio Ambulante는 중남미 팟캐스트
                if "중남미" in region_options:
                    region_value = "중남미"
                    print("DEBUG: '중남미' 옵션 사용")
                elif "라틴아메리카" in region_options:
                    region_value = "라틴아메리카"
                    print("DEBUG: '라틴아메리카' 옵션 사용")
                elif "남미" in region_options:
                    region_value = "남미"
                    print("DEBUG: '남미' 옵션 사용")
                elif "Latin America" in region_options:
                    region_value = "Latin America"
                    print("DEBUG: 'Latin America' 옵션 사용")
                else:
                    region_value = region_options[0] if region_options else "중남미"
                    print(f"DEBUG: 기본값 사용: '{region_value}'")
            else:
                print("DEBUG: 일반 팟캐스트 - 스페인으로 설정")
                # 다른 팟캐스트들은 스페인
                if "스페인" in region_options:
                    region_value = "스페인"
                elif "Spain" in region_options:
                    region_value = "Spain"
                else:
                    region_value = region_options[0] if region_options else "스페인"
        else:
            # 기사는 기본적으로 스페인
            if "스페인" in region_options:
                region_value = "스페인"
            elif "Spain" in region_options:
                region_value = "Spain"
            elif "유럽" in region_options:
                region_value = "유럽"
            else:
                region_value = region_options[0] if region_options else "스페인"
            
        print(f"DEBUG: 선택된 지역: '{region_value}'")
        properties[region_prop] = {
            "select": {
                "name": region_value
            }
        }
        print(f"DEBUG: 지역 속성 '{region_prop}'에 '{region_value}' 설정됨")
    else:
        print("WARNING: 지역 속성을 찾을 수 없습니다!")
    
    # 메모 속성 - 빈 값이라도 추가
    if notes_prop:
        properties[notes_prop] = {
            "rich_text": [
                {
                    "text": {
                        "content": memo or "메모 없음"
                    }
                }
            ]
        }
    
    # 날짜 속성 - 항상 오늘 날짜
    if date_prop:
        properties[date_prop] = {
            "date": {
                "start": datetime.now().strftime('%Y-%m-%d')
            }
        }
    
    # 어휘 속성 - 빈 값이라도 추가
    if vocabulary_prop:
        properties[vocabulary_prop] = {
            "rich_text": [
                {
                    "text": {
                        "content": vocabulary or "어휘 없음"
                    }
                }
            ]
        }
    
    # 재생시간 속성 - 팟캐스트일 때만 추가
    if duration_prop and content_type == "podcast":
        properties[duration_prop] = {
            "rich_text": [
                {
                    "text": {
                        "content": duration or "시간 정보 없음"
                    }
                }
            ]
        }

    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": properties
    }

    try:
        response = requests.post(
            'https://api.notion.com/v1/pages',
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            page_data = response.json()
            return page_data['url']
        else:
            print(f"Notion 페이지 생성 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return None
            
    except Exception as e:
        print(f"Notion API 오류: {e}")
        return None

def check_duplicate_page(title, content_type):
    """Notion에서 중복 페이지가 있는지 확인"""
    try:
        NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
        DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')
        
        if not NOTION_TOKEN or not DATABASE_ID:
            print("중복 확인: Notion 설정이 없습니다.")
            return False
        
        headers = {
            'Authorization': f'Bearer {NOTION_TOKEN}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
        
        # 최근 7일간의 페이지만 검색 (성능 최적화)
        from datetime import datetime, timedelta
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        # 제목으로 검색
        search_payload = {
            "filter": {
                "and": [
                    {
                        "property": "title",
                        "title": {
                            "contains": title[:50]  # 제목의 첫 50자로 검색
                        }
                    },
                    {
                        "property": "created_time",
                        "created_time": {
                            "after": week_ago
                        }
                    }
                ]
            },
            "sorts": [
                {
                    "property": "created_time",
                    "direction": "descending"
                }
            ]
        }
        
        response = requests.post(
            f'https://api.notion.com/v1/databases/{DATABASE_ID}/query',
            headers=headers,
            json=search_payload
        )
        
        if response.status_code == 200:
            results = response.json().get('results', [])
            print(f"DEBUG: 중복 검색 결과 - {len(results)}개 페이지 발견")
            
            for result in results:
                existing_title = ""
                title_prop = result.get('properties', {})
                for prop_name, prop_value in title_prop.items():
                    if prop_value.get('type') == 'title':
                        title_texts = prop_value.get('title', [])
                        if title_texts:
                            existing_title = title_texts[0].get('text', {}).get('content', '')
                        break
                
                if existing_title:
                    # 제목 유사도 확인 (90% 이상 유사하면 중복)
                    title_words = set(title.lower().split())
                    existing_words = set(existing_title.lower().split())
                    
                    if title_words and existing_words:
                        similarity = len(title_words & existing_words) / len(title_words | existing_words)
                        
                        if similarity >= 0.9:
                            print(f"🔍 중복 페이지 발견!")
                            print(f"   새 제목: {title}")
                            print(f"   기존 제목: {existing_title}")
                            print(f"   유사도: {similarity:.2f}")
                            return True
            
            return False
        else:
            print(f"중복 검색 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"중복 확인 오류: {e}")
        return False

def main():
    print("=== Notion 페이지 생성 시작 ===")
    
    # Notion API 설정 확인
    NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
    DATABASE_ID = os.environ.get('NOTION_DATABASE_ID')

    if not NOTION_TOKEN or not DATABASE_ID:
        print("Notion 토큰 또는 데이터베이스 ID가 설정되지 않았습니다.")
        return

    # 모든 환경변수 출력
    print("\n=== 받은 환경변수 확인 ===")
    env_vars = {
        'ARTICLE_TITLE': os.environ.get('ARTICLE_TITLE', ''),
        'ARTICLE_URL': os.environ.get('ARTICLE_URL', ''),
        'ARTICLE_CATEGORY': os.environ.get('ARTICLE_CATEGORY', ''),
        'ARTICLE_VOCABULARY': os.environ.get('ARTICLE_VOCABULARY', ''),
        'ARTICLE_DIFFICULTY': os.environ.get('ARTICLE_DIFFICULTY', 'B2'),  # 추가
        'ARTICLE_MEMO': os.environ.get('ARTICLE_MEMO', ''),
        'PODCAST_TITLE': os.environ.get('PODCAST_TITLE', ''),
        'PODCAST_URL': os.environ.get('PODCAST_URL', ''),
        'PODCAST_APPLE': os.environ.get('PODCAST_APPLE', ''),
        'PODCAST_DURATION': os.environ.get('PODCAST_DURATION', ''),
        'PODCAST_TOPIC': os.environ.get('PODCAST_TOPIC', ''),
        'PODCAST_MEMO': os.environ.get('PODCAST_MEMO', '')
    }
    
    for key, value in env_vars.items():
        print(f"- {key}: {'[있음]' if value else '[없음]'} ({len(value)} chars)")
        if value and len(value) < 100:
            print(f"  값: {value}")

    # 기사 페이지 생성
    article_title = env_vars['ARTICLE_TITLE']
    if article_title:
        print(f"\n📰 기사 페이지 생성 시작...")
        article_page_url = create_notion_page(
            title=article_title,
            url=env_vars['ARTICLE_URL'],
            content_type="article",
            memo=env_vars['ARTICLE_MEMO'],
            category=env_vars['ARTICLE_CATEGORY'],
            vocabulary=env_vars['ARTICLE_VOCABULARY'],
            difficulty=env_vars['ARTICLE_DIFFICULTY']  # env_vars에서 동적 난이도 가져오기
        )
        
        if article_page_url:
            print(f"✅ 기사 페이지 생성 완료: {article_page_url}")
        else:
            print(f"❌ 기사 페이지 생성 실패")
    else:
        print(f"\n📰 기사 제목이 없어서 기사 페이지를 건너뜁니다.")

    # 팟캐스트 페이지 생성  
    podcast_title = env_vars['PODCAST_TITLE']
    if podcast_title:
        print(f"\n🎧 팟캐스트 페이지 생성 시작...")
        podcast_url = env_vars['PODCAST_APPLE'] or env_vars['PODCAST_URL']
        
        print(f"팟캐스트 정보:")
        print(f"  제목: {podcast_title}")
        print(f"  URL: {podcast_url}")
        print(f"  듀레이션: {env_vars['PODCAST_DURATION']}")
        print(f"  토픽: {env_vars['PODCAST_TOPIC']}")
        print(f"  메모: {env_vars['PODCAST_MEMO'][:100]}..." if env_vars['PODCAST_MEMO'] else "  메모: [없음]")
        
        podcast_page_url = create_notion_page(
            title=podcast_title,
            url=podcast_url,
            content_type="podcast",
            memo=env_vars['PODCAST_MEMO'],
            category=env_vars['PODCAST_TOPIC'],
            duration=env_vars['PODCAST_DURATION']
        )
        
        if podcast_page_url:
            print(f"✅ 팟캐스트 페이지 생성 완료: {podcast_page_url}")
        else:
            print(f"❌ 팟캐스트 페이지 생성 실패")
    else:
        print(f"\n🎧 팟캐스트 제목이 없어서 팟캐스트 페이지를 건너뜁니다.")
        print(f"PODCAST_TITLE 환경변수 확인 필요!")

    print("\n=== Notion 페이지 생성 완료 ===")

if __name__ == "__main__":
    main()
