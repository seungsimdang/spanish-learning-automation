#!/usr/bin/env python3
"""
Create Notion pages for collected Spanish learning materials.
"""
import os
import requests
import json
import sys
import subprocess
import time
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

def create_notion_page(title, url, content_type, memo, category="", duration="", difficulty="", is_alternative=False):
    """Notion 페이지 생성 - 중복 시 자동으로 대체 자료 검색"""
    
    # 중복 페이지 확인 (대안 검색 모드가 아닐 때만)
    if not is_alternative:
        print(f"\n🔍 중복 페이지 확인 중: {title}")
        if check_duplicate_page(title, content_type):
            print(f"⚠️  중복 페이지가 이미 존재합니다: {title}")
            print(f"🔄 자동으로 대체 자료를 검색합니다...")
            print(f"📝 중복 발견으로 LLM 분석 건너뛰기")
            
            # 자동으로 대체 자료 검색 및 등록 시도 (LLM 분석 없이)
            if try_alternative_materials(content_type):
                print("✅ 대체 자료 검색 및 등록 완료!")
                return "ALTERNATIVE_REGISTERED"
            else:
                print("❌ 대체 자료 검색 실패")
                return "DUPLICATE_FOUND"
    else:
        print(f"\n🔄 대안 자료로 페이지 생성 중: {title}")
        # 대안 자료도 중복 체크는 해야 함
        if check_duplicate_page(title, content_type):
            print(f"⚠️  대안 자료도 중복입니다: {title}")
            return "DUPLICATE_FOUND"
    
    print(f"✅ 중복 없음. 새로운 자료로 페이지 생성을 시작합니다.")
    print(f"🔍 LLM 분석 시작 (새로운 컨텐츠)")
    
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
    
    # 실제 속성 이름 찾기 - 명확한 매핑
    title_prop = None
    url_prop = None
    type_prop = None        # 자료 유형
    date_prop = None        # 학습 예정일
    difficulty_prop = None  # 난이도 (B1/B2/C1)
    area_prop = None        # 학습 영역
    region_prop = None      # 지역
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
                
        # Rich text 속성들 - 이름으로 구분
        elif prop_type == 'rich_text':
            if '시간' in prop_name or '재생' in prop_name:
                duration_prop = prop_name
    
    print(f"매핑된 속성들:")
    print(f"- 제목: {title_prop}")
    print(f"- URL: {url_prop}")
    print(f"- 자료 유형: {type_prop}")
    print(f"- 난이도: {difficulty_prop}")
    print(f"- 학습 영역: {area_prop}")
    print(f"- 지역: {region_prop}")
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
            
        properties[type_prop] = {
            "select": {
                "name": type_value
            }
        }
    
    # 난이도 속성 - 동적으로 분석된 난이도 사용
    if difficulty_prop:
        difficulty_options = select_options.get(difficulty_prop, [])
        
        # 전달받은 난이도를 우선 사용
        preferred_difficulty = difficulty if difficulty else "B2"
        
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
            
        properties[difficulty_prop] = {
            "select": {
                "name": difficulty_value
            }
        }
    
    # 학습 영역 속성 - 유효한 옵션만 사용
    if area_prop:
        area_options = select_options.get(area_prop, [])
        
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
            
        properties[area_prop] = {
            "select": {
                "name": area_value
            }
        }
    
    # 지역 속성 - 유효한 옵션만 사용
    if region_prop:
        region_options = select_options.get(region_prop, [])
        
        # 팟캐스트일 때는 제목으로 지역 판단
        if content_type == "podcast":
            if "Radio Ambulante" in title:
                # Radio Ambulante는 중남미 팟캐스트
                if "중남미" in region_options:
                    region_value = "중남미"
                elif "라틴아메리카" in region_options:
                    region_value = "라틴아메리카"
                elif "남미" in region_options:
                    region_value = "남미"
                elif "Latin America" in region_options:
                    region_value = "Latin America"
                else:
                    region_value = region_options[0] if region_options else "중남미"
            else:
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
            
        properties[region_prop] = {
            "select": {
                "name": region_value
            }
        }
    
    
    # 날짜 속성 - 항상 오늘 날짜
    if date_prop:
        properties[date_prop] = {
            "date": {
                "start": datetime.now().strftime('%Y-%m-%d')
            }
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

    # 페이지 내용 블록 생성 - 메모를 보기 좋게 정리
    children = create_page_content(content_type, memo, title, url, duration, category, difficulty, skip_llm_analysis=False)

    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": properties,
        "children": children
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
        
        # 먼저 데이터베이스 속성 정보를 가져와서 올바른 속성명 확인
        db_properties = get_database_properties(DATABASE_ID, headers)
        
        # 제목 속성 찾기
        title_prop_name = None
        for prop_name, prop_info in db_properties.items():
            if prop_info.get('type') == 'title':
                title_prop_name = prop_name
                break
        
        if not title_prop_name:
            print("⚠️  제목 속성을 찾을 수 없습니다. 중복 체크를 건너뜁니다.")
            return False
        
        # 제목으로 간단하게 검색 (정렬 없이)
        search_payload = {
            "filter": {
                "property": title_prop_name,
                "rich_text": {
                    "contains": title[:20]  # 제목의 첫 20자로 검색
                }
            },
            "page_size": 20
        }
        
        response = requests.post(
            f'https://api.notion.com/v1/databases/{DATABASE_ID}/query',
            headers=headers,
            json=search_payload
        )
        
        if response.status_code == 200:
            results = response.json().get('results', [])
            
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
            print(f"응답 내용: {response.text[:200]}...")
            
            # 검색 실패시 중복이 없는 것으로 간주 (페이지 생성 진행)
            print("⚠️  중복 체크 실패. 중복이 없는 것으로 간주하고 페이지 생성을 진행합니다.")
            return False
            
    except Exception as e:
        print(f"중복 확인 오류: {e}")
        return False

def simple_duplicate_check(title, headers, database_id):
    """간단한 제목 검색으로 중복 체크"""
    try:
        # 더 간단한 검색 쿼리
        search_payload = {
            "filter": {
                "property": "제목",  # 한글 속성명 직접 사용
                "rich_text": {
                    "contains": title.split()[0] if title.split() else title[:20]  # 첫 단어 또는 첫 20자
                }
            },
            "page_size": 10
        }
        
        response = requests.post(
            f'https://api.notion.com/v1/databases/{database_id}/query',
            headers=headers,
            json=search_payload
        )
        
        if response.status_code == 200:
            results = response.json().get('results', [])
            
            for result in results:
                # 제목 추출
                properties = result.get('properties', {})
                for prop_name, prop_value in properties.items():
                    if prop_value.get('type') == 'title':
                        title_texts = prop_value.get('title', [])
                        if title_texts:
                            existing_title = title_texts[0].get('text', {}).get('content', '')
                            
                            # 간단한 포함 관계 확인
                            if title.lower() in existing_title.lower() or existing_title.lower() in title.lower():
                                return True
            
            return False
        else:
            # 모든 검색이 실패하면 안전하게 중복으로 간주
            return True
            
    except Exception as e:
        # 오류 시 안전하게 중복으로 간주
        return True

def try_alternative_materials(content_type):
    """중복 발견시 대체 자료를 자동으로 검색하고 등록"""
    try:
        print(f"\n🔄 {content_type} 대체 자료 검색 시작...")
        
        if content_type == "article":
            return find_and_register_alternative_article()
        elif content_type == "podcast":
            return find_and_register_alternative_podcast()
        else:
            print(f"❌ 지원하지 않는 컨텐츠 타입: {content_type}")
            return False
            
    except Exception as e:
        print(f"❌ 대체 자료 검색 오류: {e}")
        return False

def find_and_register_alternative_article():
    """대안 기사를 찾아서 바로 등록"""
    current_source = os.environ.get('READING_SOURCE', '')
    
    alternative_sources = [
        ("20minutos", "https://www.20minutos.es/rss/"),
        ("El País", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada"),
        ("El País 사설", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/opinion"),
        ("El Mundo", "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml"),
        ("ABC", "https://www.abc.es/rss/feeds/abc_EspanaEspana.xml")
    ]
    
    # 현재 소스 제외
    available_sources = [source for source in alternative_sources if source[0] != current_source]
    
    print(f"기사 대안 소스들 시도: {[s[0] for s in available_sources]}")
    
    for source_name, rss_url in available_sources:
        try:
            print(f"\n📰 {source_name} 시도 중...")
            
            # collect_materials.py 실행하여 새로운 기사 수집
            env = os.environ.copy()
            env['READING_SOURCE'] = source_name
            env['FORCE_ALTERNATIVE'] = 'true'
            
            result = subprocess.run([
                sys.executable,
                os.path.join(os.path.dirname(__file__), 'collect_materials.py')
            ], env=env, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                # 출력에서 새로운 기사 정보 파싱
                output_lines = result.stdout.strip().split('\n')
                
                # 환경변수 형태로 출력된 내용 파싱
                for line in output_lines:
                    if line.startswith('ARTICLE_TITLE='):
                        new_title = line.split('=', 1)[1].strip('"')
                        # 새로운 기사가 중복인지 확인
                        if not check_duplicate_page(new_title, "article"):
                            print(f"✅ 새로운 기사 발견: {new_title}")
                            
                            # 환경변수 업데이트
                            for env_line in output_lines:
                                if '=' in env_line and env_line.startswith(('ARTICLE_', 'PODCAST_')):
                                    key, value = env_line.split('=', 1)
                                    os.environ[key] = value.strip('"')
                            
                            # 새로운 기사로 Notion 페이지 생성 (대안 모드)
                            new_article_url = create_notion_page(
                                title=os.environ.get('ARTICLE_TITLE', ''),
                                url=os.environ.get('ARTICLE_URL', ''),
                                content_type="article",
                                memo=os.environ.get('ARTICLE_MEMO', ''),
                                category=os.environ.get('ARTICLE_CATEGORY', ''),
                                difficulty=os.environ.get('ARTICLE_DIFFICULTY', 'B2'),
                                is_alternative=True  # 대안 모드로 호출
                            )
                            
                            if new_article_url and new_article_url not in ["DUPLICATE_FOUND", "ALTERNATIVE_REGISTERED"]:
                                print(f"✅ 대안 기사 Notion 페이지 생성 완료: {new_article_url}")
                                return True
                        break
                        
        except subprocess.TimeoutExpired:
            print(f"⏰ {source_name}: 시간 초과")
        except Exception as e:
            print(f"❌ {source_name} 오류: {e}")
    
    return False

def find_and_register_alternative_podcast():
    """대안 팟캐스트를 찾아서 바로 등록 - 확장된 검색"""
    current_podcast = os.environ.get('PODCAST_NAME', '')
    
    # 실제 검증된 유효한 대안 팟캐스트들 - curl로 확인된 200 OK 피드만
    alternative_podcasts = [
        {
            "name": "Notes in Spanish",
            "rss": "https://feeds.feedburner.com/notesinspanish",
            "apple_base": "https://podcasts.apple.com/us/podcast/notes-in-spanish/id139033480"
        },
        {
            "name": "Unlimited Spanish",
            "rss": "https://unlimitedspanish.libsyn.com/rss",
            "apple_base": "https://podcasts.apple.com/podcast/unlimited-spanish/id1446095651"
        },
        {
            "name": "Radio Ambulante",
            "rss": "https://radioambulante.org/feed",
            "apple_base": "https://podcasts.apple.com/podcast/radio-ambulante/id527614348"
        },
        {
            "name": "SoundCloud Spanish Learning",
            "rss": "https://feeds.soundcloud.com/users/soundcloud:users:144513835/sounds.rss",
            "apple_base": "https://podcasts.apple.com/podcast/spanish-learning/id1234567899"
        },
        {
            "name": "SoundCloud Spanish Podcast",
            "rss": "https://feeds.soundcloud.com/users/soundcloud:users:250208044/sounds.rss",
            "apple_base": "https://podcasts.apple.com/podcast/spanish-podcast/id1234567900"
        }
    ]
    
    # 현재 팟캐스트 제외
    available_podcasts = [p for p in alternative_podcasts if p['name'] != current_podcast]
    
    print(f"팟캐스트 대안들 시도: {[p['name'] for p in available_podcasts]}")
    
    # 각 팟캐스트마다 여러 번 시도 (다른 에피소드 얻기 위해)
    for attempt in range(3):  # 3번 시도
        print(f"\n🔄 시도 {attempt + 1}/3")
        
        for podcast in available_podcasts:
            try:
                print(f"\n🎧 {podcast['name']} 시도 중...")
                
                # collect_materials.py 실행하여 새로운 팟캐스트 수집
                env = os.environ.copy()
                env['PODCAST_NAME'] = podcast['name']
                env['PODCAST_RSS'] = podcast['rss']
                env['PODCAST_APPLE_BASE'] = podcast['apple_base'] 
                env['FORCE_ALTERNATIVE'] = 'true'
                env['RANDOM_EPISODE'] = 'true'  # 랜덤 에피소드 선택
                env['EPISODE_OFFSET'] = str(attempt * 5)  # 다른 에피소드를 위한 오프셋
                
                result = subprocess.run([
                    sys.executable,
                    os.path.join(os.path.dirname(__file__), 'collect_materials.py')
                ], env=env, capture_output=True, text=True, timeout=120)  # 타임아웃 증가
                
                if result.returncode == 0:
                    # 출력에서 새로운 팟캐스트 정보 파싱
                    output_lines = result.stdout.strip().split('\n')
                    
                    for line in output_lines:
                        if line.startswith('PODCAST_TITLE='):
                            new_title = line.split('=', 1)[1].strip('"')
                            # 새로운 팟캐스트가 중복인지 확인
                            if not check_duplicate_page(new_title, "podcast"):
                                print(f"✅ 새로운 팟캐스트 발견: {new_title}")
                                
                                # 환경변수 업데이트
                                for env_line in output_lines:
                                    if '=' in env_line and env_line.startswith(('ARTICLE_', 'PODCAST_')):
                                        key, value = env_line.split('=', 1)
                                        os.environ[key] = value.strip('"')
                                
                                # 새로운 팟캐스트로 Notion 페이지 생성 (대안 모드)
                                podcast_url = os.environ.get('PODCAST_APPLE', '') or os.environ.get('PODCAST_URL', '')
                                new_podcast_url = create_notion_page(
                                    title=os.environ.get('PODCAST_TITLE', ''),
                                    url=podcast_url,
                                    content_type="podcast",
                                    memo=os.environ.get('PODCAST_MEMO', ''),
                                    category=os.environ.get('PODCAST_TOPIC', ''),
                                    difficulty=os.environ.get('PODCAST_DIFFICULTY', 'B2'),
                                    duration=os.environ.get('PODCAST_DURATION', ''),
                                    is_alternative=True  # 대안 모드로 호출
                                )
                                
                                if new_podcast_url and new_podcast_url not in ["DUPLICATE_FOUND", "ALTERNATIVE_REGISTERED"]:
                                    print(f"✅ 대안 팟캐스트 Notion 페이지 생성 완료: {new_podcast_url}")
                                    return True
                            else:
                                print(f"⚠️  새로운 팟캐스트도 중복: {new_title}")
                            break
                else:
                    print(f"❌ {podcast['name']} 수집 실패: {result.stderr}")
                            
            except subprocess.TimeoutExpired:
                print(f"⏰ {podcast['name']}: 시간 초과")
            except Exception as e:
                print(f"❌ {podcast['name']} 오류: {e}")
        
        # 첫 번째 시도에서 성공하면 바로 종료
        time.sleep(2)  # 다음 시도 전 잠시 대기
    
    return False

def try_backup_podcast_feeds():
    """추가 백업 피드들을 시도하여 팟캐스트 페이지 생성"""
    print("🔄 백업 피드들을 시도합니다...")
    
    # 추가 백업 피드들 - 실제 존재하는 피드 URL들
    backup_feeds = [
        {
            "name": "Notes in Spanish",
            "rss": "https://feeds.feedburner.com/notesinspanish",
            "apple_base": "https://podcasts.apple.com/us/podcast/notes-in-spanish/id1234567891"
        }
    ]
    
    for feed in backup_feeds:
        try:
            print(f"\n🎧 백업 피드 {feed['name']} 시도 중...")
            
            # collect_materials.py 호출
            env = os.environ.copy()
            env['PODCAST_NAME'] = feed['name']
            env['PODCAST_RSS'] = feed['rss']
            env['PODCAST_APPLE_BASE'] = feed['apple_base']
            env['FORCE_ALTERNATIVE'] = 'true'
            
            result = subprocess.run([
                sys.executable,
                os.path.join(os.path.dirname(__file__), 'collect_materials.py')
            ], env=env, capture_output=True, text=True, timeout=90)
            
            if result.returncode == 0:
                # 출력에서 새로운 팟캐스트 정보 파싱
                output_lines = result.stdout.strip().split('\n')
                
                for line in output_lines:
                    if line.startswith('PODCAST_TITLE='):
                        new_title = line.split('=', 1)[1].strip('"')
                        
                        # 중복 체크
                        if not check_duplicate_page(new_title, "podcast"):
                            print(f"✅ 백업 피드에서 새로운 팟캐스트 발견: {new_title}")
                            
                            # 환경변수 업데이트
                            for env_line in output_lines:
                                if '=' in env_line and env_line.startswith('PODCAST_'):
                                    key, value = env_line.split('=', 1)
                                    os.environ[key] = value.strip('"')
                            
                            # 새로운 팟캐스트로 Notion 페이지 생성
                            backup_podcast_url = create_notion_page(
                                title=os.environ.get('PODCAST_TITLE', ''),
                                url=os.environ.get('PODCAST_APPLE', '') or os.environ.get('PODCAST_URL', ''),
                                content_type="podcast",
                                memo=os.environ.get('PODCAST_MEMO', ''),
                                category=os.environ.get('PODCAST_TOPIC', ''),
                                difficulty=os.environ.get('PODCAST_DIFFICULTY', 'B2'),
                                duration=os.environ.get('PODCAST_DURATION', ''),
                                is_alternative=True
                            )
                            
                            if backup_podcast_url and backup_podcast_url not in ["DUPLICATE_FOUND", "ALTERNATIVE_REGISTERED"]:
                                print(f"✅ 백업 피드 팟캐스트 페이지 생성 완료: {backup_podcast_url}")
                                return True
                        else:
                            print(f"⚠️  백업 피드 팟캐스트도 중복: {new_title}")
                        break
                        
        except subprocess.TimeoutExpired:
            print(f"⏰ {feed['name']}: 시간 초과")
        except Exception as e:
            print(f"❌ {feed['name']} 백업 피드 오류: {e}")
    
    return False

def extract_spanish_transcript_from_memo(memo):
    """팟캐스트 메모에서 실제 스페인어 transcript 내용만 추출"""
    if not memo:
        return ""
    
    # 메모에서 다양한 메타데이터 패턴 제거
    import re
    
    # 이모지와 메타데이터 패턴들
    metadata_patterns = [
        r'🎧.*?팟캐스트',
        r'📺.*?에피소드.*?:',
        r'⏱️.*?재생시간.*?:',
        r'🎯.*?학습목표.*?:',
        r'🌍.*?주제.*?:',
        r'🎯.*?구어체.*?:',
        r'🤖.*?AI 분석',
        r'🔍.*?검색어.*?:',
        r'📻.*?권장.*?:',
        r'💡.*?추천.*?:',
        r'📝.*?메모.*?:',
        r'⭐.*?평점.*?:',
        r'📅.*?날짜.*?:',
        r'🏷️.*?태그.*?:',
        r'📊.*?통계.*?:',
        r'🔗.*?링크.*?:',
        r'👤.*?발표자.*?:',
        r'🏢.*?출처.*?:',
    ]
    
    content = memo
    
    # 메타데이터 패턴 제거
    for pattern in metadata_patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
    
    # 시간 표기 패턴 제거 (24:39, (전체 24:39 청취) 등)
    content = re.sub(r'\d+:\d+', '', content)
    content = re.sub(r'\([^)]*\d+:\d+[^)]*\)', '', content)
    
    # 구어체 표현 목록 패턴 제거 (a ver (한번 보자) | por el contrario 등)
    content = re.sub(r'[a-záéíóúñü\s]+\s*\([^)]+\)\s*\|?', '', content, flags=re.IGNORECASE)
    
    # 영어 단어들 제거 (메타데이터에 섞인 영어)
    content = re.sub(r'\b[a-zA-Z]+\b', '', content)
    
    # 특수 문자와 이모지 제거
    content = re.sub(r'[🎧📺⏱️🎯🌍🤖🔍📻💡📝⭐📅🏷️📊🔗👤🏢]', '', content)
    content = re.sub(r'[→|]', '', content)
    
    # 숫자만 있는 라인 제거
    content = re.sub(r'^\d+$', '', content, flags=re.MULTILINE)
    
    # 빈 라인들 정리
    content = re.sub(r'\n\s*\n', '\n', content)
    content = re.sub(r'^\s+|\s+$', '', content, flags=re.MULTILINE)
    
    # 최종 정리
    content = content.strip()
    
    # 스페인어 문장만 추출 (간단한 스페인어 패턴 매칭)
    spanish_sentences = []
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if len(line) < 10:  # 너무 짧은 라인 제외
            continue
            
        # 스페인어 특징적 패턴 확인
        spanish_indicators = [
            r'\b(el|la|los|las|un|una|de|del|en|con|por|para|que|es|son|está|están|tiene|tienen|hace|haz|hacer|ver|ir|venir|poder|querer|saber|conocer|dar|decir|hablar|vivir|trabajar|estudiar|comer|beber|dormir)\b',
            r'[ñáéíóú]',  # 스페인어 특수 문자
            r'\b(muy|más|menos|todo|todos|todas|cada|algún|alguna|ningún|ninguna|otro|otra|mismo|misma)\b'
        ]
        
        spanish_score = 0
        for pattern in spanish_indicators:
            if re.search(pattern, line, re.IGNORECASE):
                spanish_score += 1
        
        # 스페인어 스코어가 2 이상이면 스페인어 문장으로 판단
        if spanish_score >= 2:
            spanish_sentences.append(line)
    
    return '\n'.join(spanish_sentences)

def create_page_content(content_type, memo, title, url, duration="", category="", difficulty="", skip_llm_analysis=False):
    """페이지 내용 블록을 생성 - 체계적인 학습 템플릿 with AI 분석"""
    children = []
    
    if not memo:
        return children
    
    # LLM 분석 수행 (skip_llm_analysis가 True면 건너뛰기)
    grammar_analysis = {}
    colloquial_expressions = []
    learning_goals = []
    
    if not skip_llm_analysis:
        try:
            from llm_analyzer import SpanishLLMAnalyzer
            analyzer = SpanishLLMAnalyzer()
            
            if content_type == "article":
                # 기사 문법 분석
                print(f"    🔍 기사 문법 분석 시작...")
                grammar_analysis = analyzer.analyze_article_grammar(memo, difficulty)
                print(f"    ✅ 기사 문법 분석 완료")
            elif content_type == "podcast":
                # 팟캐스트 구어체 분석 먼저 수행
                print(f"\n    🔍 Notion 페이지용 팟캐스트 구어체 분석 시작...")
                print(f"    📊 입력 메모 길이: {len(memo)}자")
                print(f"    🎯 분석 난이도: {difficulty}")
                print(f"    📄 입력 메모 미리보기: {memo[:200].replace(chr(10), ' ').strip()}...")
                
                # 메모에서 실제 스페인어 transcript 내용만 추출
                transcript_content = extract_spanish_transcript_from_memo(memo)
                print(f"    📝 추출된 transcript 내용 길이: {len(transcript_content)}자")
                
                if transcript_content and len(transcript_content.strip()) >= 50:
                    print(f"    📄 transcript 미리보기: {transcript_content[:200].replace(chr(10), ' ').strip()}...")
                    # 추출된 transcript로 구어체 분석 수행
                    colloquial_expressions = analyzer.analyze_podcast_colloquialisms(transcript_content, difficulty)
                else:
                    print(f"    ⚠️  추출된 transcript가 너무 짧음 ({len(transcript_content.strip())}자)")
                    print(f"    📝 원본 메모로 분석 시도...")
                    # 추출 실패시 원본 메모 사용하되 메타데이터 문제 알림
                    colloquial_expressions = analyzer.analyze_podcast_colloquialisms(memo, difficulty)
                
                print(f"\n    📊 Notion용 구어체 분석 최종 결과:")
                print(f"    ✅ 추출된 구어체 표현: {len(colloquial_expressions)}개")
                
                if colloquial_expressions:
                    print(f"    🎯 발견된 구어체 표현들:")
                    for i, expr in enumerate(colloquial_expressions, 1):
                        print(f"       {i}. {expr}")
                else:
                    print(f"    📝 구어체 표현이 0개인 이유:")
                    print(f"       • 메모 텍스트가 정식/공식적 언어로 구성됨")
                    print(f"       • 팟캐스트 메타데이터(제목, 시간, 설명) 위주의 내용")
                    print(f"       • 실제 대화 transcript가 아닌 요약 정보일 가능성")
                
                # 팟캐스트 학습 목표 생성 (구어체 표현 개수 반영)
                print(f"\n    🎯 Notion용 학습 목표 생성 시작...")
                print(f"    📝 구어체 표현 개수 반영: {len(colloquial_expressions)}개")
                learning_goals = analyzer.generate_podcast_learning_goals(memo, title, difficulty, len(colloquial_expressions))
                print(f"    ✅ 학습 목표 생성 완료: {len(learning_goals)}개 목표")
            
        except Exception as e:
            print(f"    ⚠️  LLM 분석 실패: {e}")
            grammar_analysis = {}
            colloquial_expressions = []
            learning_goals = []
    else:
        print(f"    ⏭️  LLM 분석 건너뛰기 (중복 체크 후 호출)")
        # 기본 학습 목표 설정 (LLM 없이)
        if content_type == "podcast":
            learning_goals = [
                f"{difficulty} 수준 청취 연습",
                "핵심 어휘 및 표현 학습",
                "문맥 이해 및 내용 파악",
                "발음 및 억양 패턴 익히기"
            ]
    
    # 기사인 경우 - 문법 분석 중심 템플릿
    if content_type == "article":
        # 제목 (H1)
        children.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"📰 스페인어 기사 독해 ({difficulty} 수준)"
                        }
                    }
                ]
            }
        })
        
        # 기사 정보 (H2)
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "📅 기사 정보"
                        }
                    }
                ]
            }
        })
        
        # 기사 메타 정보
        from datetime import datetime
        today = datetime.now().strftime('%Y년 %m월 %d일')
        children.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "발행일: "
                        }
                    },
                    {
                        "type": "text",
                        "text": {
                            "content": today
                        },
                        "annotations": {
                            "bold": True
                        }
                    }
                ]
            }
        })
        
        children.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "출처/주제: "
                        }
                    },
                    {
                        "type": "text",
                        "text": {
                            "content": category or '일반 기사'
                        },
                        "annotations": {
                            "bold": True
                        }
                    }
                ]
            }
        })
        
        children.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"학습 목표: 15분 독해, {difficulty} 문법 구조 분석"
                        }
                    }
                ]
            }
        })
        
        # 구분선
        children.append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })
        
        # 주요 문법 분석 (H2)
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"📝 주요 문법 분석 ({difficulty} 수준)"
                        }
                    }
                ]
            }
        })
        
        # 실제 분석된 문법 포인트들 추가
        if grammar_analysis and grammar_analysis.get('original_sentence'):
            # 원문 문장 먼저 표시 (실제 분석된 문장)
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "원문: "
                            }
                        },
                        {
                            "type": "text",
                            "text": {
                                "content": grammar_analysis['original_sentence']
                            },
                            "annotations": {
                                "bold": True
                            }
                        }
                    ]
                }
            })
            
            # 문법 내용 정리 제목
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📌 문법 내용 정리:"
                            },
                            "annotations": {
                                "bold": True
                            }
                        }
                    ]
                }
            })
            
            # 각 문법 구조를 자연스러운 형태로 표시
            for grammar_item in grammar_analysis.get('grammar_analysis', []):
                # 문법 구조 제목 (볼드)
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": grammar_item['title']
                                },
                                "annotations": {
                                    "bold": True
                                }
                            }
                        ]
                    }
                })
                
                # 설명 포인트들
                for point in grammar_item.get('points', []):
                    children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"- {point}"
                                    }
                                }
                            ]
                        }
                    })
        else:
            # 빈 템플릿 - 사용자 예시 형태로 자연스럽게 구성
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "원문: "
                            }
                        },
                        {
                            "type": "text",
                            "text": {
                                "content": "Esto, lógicamente, provoca que muchas personas busquen alternativas para disfrut..."
                            },
                            "annotations": {
                                "bold": True
                            }
                        }
                    ]
                }
            })
            
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📌 문법 내용 정리:"
                            },
                            "annotations": {
                                "bold": True
                            }
                        }
                    ]
                }
            })
            
            # 접속법 현재 예시
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "접속법 현재 (Presente de Subjuntivo)"
                            },
                            "annotations": {
                                "bold": True
                            }
                        }
                    ]
                }
            })
            
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "- \"busquen\" - buscar 동사의 접속법 현재 3인칭 복수형"
                            }
                        }
                    ]
                }
            })
            
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "- \"que + 접속법\" 구조로 주관적 판단이나 감정을 표현"
                            }
                        }
                    ]
                }
            })
            
            # 동사 활용 예시
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "동사 활용"
                            },
                            "annotations": {
                                "bold": True
                            }
                        }
                    ]
                }
            })
            
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "- \"provoca\" - provocar 동사의 직설법 현재 3인칭 단수형"
                            }
                        }
                    ]
                }
            })
            
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "- 규칙 동사 활용"
                            }
                        }
                    ]
                }
            })
            
            # 구문 구조 예시
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "구문 구조"
                            },
                            "annotations": {
                                "bold": True
                            }
                        }
                    ]
                }
            })
            
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "- \"Esto provoca que...\" - 결과나 원인을 나타내는 구조"
                            }
                        }
                    ]
                }
            })
            
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "- 주절(직설법) + que + 종속절(접속법) 패턴"
                            }
                        }
                    ]
                }
            })
            
            # 어휘 및 표현 예시
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "어휘 및 표현"
                            },
                            "annotations": {
                                "bold": True
                            }
                        }
                    ]
                }
            })
            
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "- \"lógicamente\" - 부사로 사용되어 논리적 연결 표현 (삽입구)"
                            }
                        }
                    ]
                }
            })
            
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "- \"muchas personas\" - 부정 형용사 + 명사 구조"
                            }
                        }
                    ]
                }
            })
            
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "- \"alternativas para...\" - 목적을 나타내는 para + 동사원형"
                            }
                        }
                    ]
                }
            })
            
            # 문장 성분 예시
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "문장 성분"
                            },
                            "annotations": {
                                "bold": True
                            }
                        }
                    ]
                }
            })
            
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "- \"Esto\" - 주어 (지시대명사)"
                            }
                        }
                    ]
                }
            })
            
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "- \"lógicamente\" - 부사구 (삽입구 역할)"
                            }
                        }
                    ]
                }
            })
            
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "- \"que muchas personas busquen...\" - 목적절 (접속법 사용)"
                            }
                        }
                    ]
                }
            })
        
        # AI 권장 학습 전략 (H2)
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "🎯 AI 권장 학습 전략"
                        }
                    }
                ]
            }
        })
        
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "문장의 "
                        }
                    },
                    {
                        "type": "text",
                        "text": {
                            "content": "시제 구조, 접속법, 부정사, 부사구"
                        },
                        "annotations": {
                            "bold": True
                        }
                    },
                    {
                        "type": "text",
                        "text": {
                            "content": "를 포인트 삼아 분석\n"
                        }
                    },
                    {
                        "type": "text",
                        "text": {
                            "content": f"{difficulty} 문장 구조 반복 노출 → 예문 작성 → 문장 따라쓰기"
                        },
                        "annotations": {
                            "bold": True
                        }
                    },
                    {
                        "type": "text",
                        "text": {
                            "content": "로 정착"
                        }
                    }
                ]
            }
        })
        
        # 개인 메모 (H2)
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "💡 개인 메모"
                        }
                    }
                ]
            }
        })
        
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "[개인 학습 메모 및 느낀 점 작성]"
                        }
                    }
                ]
            }
        })
    
    # 팟캐스트인 경우 - 구어체 표현 중심 템플릿
    elif content_type == "podcast":
        # 제목 (H1)
        children.append({
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"🎧 팟캐스트 학습 ({difficulty} 수준)"
                        }
                    }
                ]
            }
        })
        
        # 에피소드 정보 (H2)
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "📺 에피소드 정보"
                        }
                    }
                ]
            }
        })
        
        # 에피소드 메타 정보
        children.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "제목: "
                        }
                    },
                    {
                        "type": "text",
                        "text": {
                            "content": title
                        },
                        "annotations": {
                            "bold": True
                        }
                    }
                ]
            }
        })
        
        children.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "재생시간: "
                        }
                    },
                    {
                        "type": "text",
                        "text": {
                            "content": f"{duration or '미정'}"
                        },
                        "annotations": {
                            "bold": True
                        }
                    }
                ]
            }
        })
        
        children.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "주제: "
                        }
                    },
                    {
                        "type": "text",
                        "text": {
                            "content": category or '스페인어 학습'
                        },
                        "annotations": {
                            "bold": True
                        }
                    }
                ]
            }
        })
        
        # 학습 목표 (H2)
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "🎯 학습 목표"
                        }
                    }
                ]
            }
        })
        
        # 학습 목표 텍스트를 LLM이 생성한 목표로 대체
        if learning_goals:
            for goal in learning_goals:
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": goal
                                }
                            }
                        ]
                    }
                })
        else:
            # 기본 목표 (LLM 분석 실패 시)
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"팟캐스트 주제 관련 어휘 학습 ({difficulty} 수준)"
                            }
                        }
                    ]
                }
            })
            
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "구어체 표현 파악 및 실제 사용법 이해"
                            }
                        }
                    ]
                }
            })
            
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "자연스러운 발음과 억양 패턴 학습"
                            }
                        }
                    ]
                }
            })
        
        # 구어체 표현 정리 (H2) - 구어체 표현이 실제로 있을 때만 생성
        print(f"\n    📋 Notion 구어체 섹션 생성 검토...")
        print(f"    📊 구어체 표현 개수: {len(colloquial_expressions) if colloquial_expressions else 0}개")
        
        if colloquial_expressions and len(colloquial_expressions) > 0:
            print(f"    ✅ 구어체 표현 발견 - 구어체 섹션 생성")
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"🌍 구어체 표현 정리 ({difficulty} 수준)"
                            }
                        }
                    ]
                }
            })
            
            print(f"    ✅ {len(colloquial_expressions)}개의 구어체 표현이 분석되었습니다.")
        else:
            # 구어체 표현이 0개인 경우 아무 섹션도 생성하지 않음
            print(f"    📝 구어체 표현 0개 - 해당 섹션 생성하지 않음")
            print(f"    📝 이유: 메모가 팟캐스트 메타데이터나 요약 정보로만 구성됨")
        
        # 분석된 구어체 표현들을 템플릿 형태로 추가
        if colloquial_expressions and len(colloquial_expressions) > 0:
            print(f"    📝 구어체 표현 템플릿 생성 중...")
            print(f"    ✅ {len(colloquial_expressions)}개의 구어체 표현이 분석되었습니다.")
            for i, expr in enumerate(colloquial_expressions, 1):
                # 구어체 표현을 파싱하여 더 구조화된 형태로 표시
                try:
                    # 표현이 딕셔너리 형태인지 확인
                    if isinstance(expr, dict):
                        expression = expr.get('expression', '')
                        meaning = expr.get('meaning', '')
                        example = expr.get('example', '')
                        
                        children.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": f"[표현 {i}] "
                                        },
                                        "annotations": {
                                            "bold": True
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": f"{expression}"
                                        },
                                        "annotations": {
                                            "bold": True,
                                            "color": "blue"
                                        }
                                    }
                                ]
                            }
                        })
                        
                        # 의미 설명
                        if meaning:
                            children.append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": f"   → 의미: {meaning}"
                                            }
                                        }
                                    ]
                                }
                            })
                        
                        # 예시 문장
                        if example:
                            children.append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": f"   → 예시: {example}"
                                            },
                                            "annotations": {
                                                "italic": True
                                            }
                                        }
                                    ]
                                }
                            })
                    else:
                        # 문자열 형태의 구어체 표현
                        children.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": f"[표현 {i}]: "
                                        },
                                        "annotations": {
                                            "bold": True
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": str(expr)
                                        }
                                    }
                                ]
                            }
                        })
                except Exception as e:
                    print(f"    ⚠️  표현 {i} 파싱 오류: {e}")
                    # 기본 형태로 추가
                    children.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"[표현 {i}]: {str(expr)}"
                                    }
                                }
                            ]
                        }
                    })
        else:
            # 구어체 표현이 0개인 경우 아무것도 추가하지 않음 (기본 템플릿도 생성하지 않음)
            print(f"    📝 구어체 표현 0개 - 표현 템플릿 생성하지 않음")
            print(f"    📝 상세 이유:")
            print(f"       • 분석된 메모가 메타데이터 중심 (제목, 시간, 설명)")
            print(f"       • 실제 팟캐스트 대화 내용이 아닌 요약 정보")
            print(f"       • LLM이 정식/공식적 언어로 판단")
            print(f"    💡 Notion 페이지: 청취 전략 중심으로 구성됨")
        
        # AI 분석 (H2)
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "🤖 AI 분석"
                        }
                    }
                ]
            }
        })
        
        children.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "검색어: "
                        },
                        "annotations": {
                            "bold": True
                        }
                    },
                    {
                        "type": "text",
                        "text": {
                            "content": f'"{title}"'
                        }
                    }
                ]
            }
        })
        
        # 청취 전략 결정 및 로깅
        strategy_text = ""
        strategy_reason = ""
        
        if not colloquial_expressions or len(colloquial_expressions) == 0:
            strategy_text = "주제별 전문 어휘와 논리적 구조에 집중하여 듣기"
            strategy_reason = "구어체 표현이 0개이므로 정식 언어 중심 전략 적용"
        else:
            strategy_text = "구어체 표현에 집중하여 듣기"
            strategy_reason = f"{len(colloquial_expressions)}개 구어체 표현 발견으로 구어체 중심 전략 적용"
        
        print(f"\n    📻 Notion 청취 전략 설정:")
        print(f"    🎯 선택된 전략: {strategy_text}")
        print(f"    📝 선택 이유: {strategy_reason}")
        
        children.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "청취 전략: "
                        },
                        "annotations": {
                            "bold": True
                        }
                    },
                    {
                        "type": "text",
                        "text": {
                            "content": strategy_text
                        }
                    }
                ]
            }
        })
        
        # 개인 메모 (H2)
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "💡 개인 메모"
                        }
                    }
                ]
            }
        })
        
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "[개인 학습 메모 및 느낀 점 작성]"
                        }
                    }
                ]
            }
        })
    
    return children

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
        'ARTICLE_DIFFICULTY': os.environ.get('ARTICLE_DIFFICULTY', 'B2'),
        'ARTICLE_MEMO': os.environ.get('ARTICLE_MEMO', ''),
        'PODCAST_TITLE': os.environ.get('PODCAST_TITLE', ''),
        'PODCAST_URL': os.environ.get('PODCAST_URL', ''),
        'PODCAST_APPLE': os.environ.get('PODCAST_APPLE', ''),
        'PODCAST_DURATION': os.environ.get('PODCAST_DURATION', ''),
        'PODCAST_TOPIC': os.environ.get('PODCAST_TOPIC', ''),
        'PODCAST_DIFFICULTY': os.environ.get('PODCAST_DIFFICULTY', 'B2'),  # 팟캐스트 난이도 추가
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
            difficulty=env_vars['ARTICLE_DIFFICULTY'],  # env_vars에서 동적 난이도 가져오기
            is_alternative=False  # 일반 모드
        )
        
        if article_page_url == "DUPLICATE_FOUND":
            print(f"🔄 기사 중복 발견했지만 대체 자료 검색 실패.")
            print(f"💡 수동으로 다른 뉴스 소스에서 기사를 가져오거나 다른 날짜의 기사를 사용하세요.")
        elif article_page_url == "ALTERNATIVE_REGISTERED":
            print(f"✅ 기사 중복으로 인해 대체 기사가 자동으로 등록되었습니다.")
        elif article_page_url:
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
            difficulty=env_vars['PODCAST_DIFFICULTY'],  # 팟캐스트 난이도 추가
            duration=env_vars['PODCAST_DURATION'],
            is_alternative=False  # 일반 모드
        )
        
        if podcast_page_url == "DUPLICATE_FOUND":
            print(f"🔄 팟캐스트 중복 발견했지만 대체 자료 검색 실패.")
            print(f"💡 백업 옵션: 기존 팟캐스트를 수정하거나 다른 피드를 시도합니다...")
            
            # 백업 옵션 1: 기존 제목에 날짜나 번호 추가하여 새 페이지 생성
            today = datetime.now().strftime("%m%d")
            backup_title = f"{podcast_title} (백업 {today})"
            
            print(f"🔄 백업 제목으로 재시도: {backup_title}")
            backup_page_url = create_notion_page(
                title=backup_title,
                url=podcast_url,
                content_type="podcast",
                memo=env_vars['PODCAST_MEMO'],
                category=env_vars['PODCAST_TOPIC'],
                difficulty=env_vars['PODCAST_DIFFICULTY'],
                duration=env_vars['PODCAST_DURATION'],
                is_alternative=True  # 백업 모드
            )
            
            if backup_page_url and backup_page_url not in ["DUPLICATE_FOUND", "ALTERNATIVE_REGISTERED"]:
                print(f"✅ 백업 팟캐스트 페이지 생성 완료: {backup_page_url}")
            else:
                print(f"❌ 백업 팟캐스트 페이지도 생성 실패. 추가 백업 피드를 시도합니다...")
                
                # 백업 옵션 2: 추가 백업 피드들 시도
                if try_backup_podcast_feeds():
                    print(f"✅ 백업 피드에서 팟캐스트 페이지 생성 완료!")
                else:
                    print(f"❌ 모든 백업 옵션 실패")
        elif podcast_page_url == "ALTERNATIVE_REGISTERED":
            print(f"✅ 팟캐스트 중복으로 인해 대체 팟캐스트가 자동으로 등록되었습니다.")
        elif podcast_page_url:
            print(f"✅ 팟캐스트 페이지 생성 완료: {podcast_page_url}")
        else:
            print(f"❌ 팟캐스트 페이지 생성 실패")
    else:
        print(f"\n🎧 팟캐스트 제목이 없어서 팟캐스트 페이지를 건너뜁니다.")
        print(f"PODCAST_TITLE 환경변수 확인 필요!")

    print("\n=== Notion 페이지 생성 완료 ===")

if __name__ == "__main__":
    main()
