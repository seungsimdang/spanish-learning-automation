#!/usr/bin/env python3
"""
Create Notion pages for collected Spanish learning materials.
"""
import os
import requests
import json
import sys
import subprocess
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
            
            # 자동으로 대체 자료 검색 및 등록 시도
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
    
    # 실제 속성 이름 찾기 - 명확한 매핑
    title_prop = None
    url_prop = None
    type_prop = None        # 자료 유형
    notes_prop = None       # 메모/학습 내용
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
            if '메모' in prop_name or '학습' in prop_name or '내용' in prop_name:
                notes_prop = prop_name
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
    """대안 팟캐스트를 찾아서 바로 등록"""
    current_podcast = os.environ.get('PODCAST_NAME', '')
    
    alternative_podcasts = [
        {
            "name": "Hoy Hablamos",
            "rss": "https://www.hoyhablamos.com/podcast.rss", 
            "apple_base": "https://podcasts.apple.com/kr/podcast/hoy-hablamos-podcast-diario-para-aprender-español-learn/id1201483158"
        },
        {
            "name": "Radio Ambulante",
            "rss": "https://feeds.npr.org/510311/podcast.xml",
            "apple_base": "https://podcasts.apple.com/kr/podcast/radio-ambulante/id527614348"
        },
        {
            "name": "SpanishWithVicente", 
            "rss": "https://feeds.feedburner.com/SpanishWithVicente",
            "apple_base": "https://podcasts.apple.com/kr/podcast/spanish-with-vicente/id1493547273"
        },
        {
            "name": "DELE Podcast",
            "rss": "https://anchor.fm/s/f4f4a4f0/podcast/rss",
            "apple_base": "https://podcasts.apple.com/us/podcast/examen-dele/id1705001626"
        }
    ]
    
    # 현재 팟캐스트 제외
    available_podcasts = [p for p in alternative_podcasts if p['name'] != current_podcast]
    
    print(f"팟캐스트 대안들 시도: {[p['name'] for p in available_podcasts]}")
    
    for podcast in available_podcasts:
        try:
            print(f"\n🎧 {podcast['name']} 시도 중...")
            
            # collect_materials.py 실행하여 새로운 팟캐스트 수집
            env = os.environ.copy()
            env['PODCAST_NAME'] = podcast['name']
            env['PODCAST_RSS'] = podcast['rss']
            env['PODCAST_APPLE_BASE'] = podcast['apple_base'] 
            env['FORCE_ALTERNATIVE'] = 'true'
            
            result = subprocess.run([
                sys.executable,
                os.path.join(os.path.dirname(__file__), 'collect_materials.py')
            ], env=env, capture_output=True, text=True, timeout=60)
            
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
                                duration=os.environ.get('PODCAST_DURATION', ''),
                                is_alternative=True  # 대안 모드로 호출
                            )
                            
                            if new_podcast_url and new_podcast_url not in ["DUPLICATE_FOUND", "ALTERNATIVE_REGISTERED"]:
                                print(f"✅ 대안 팟캐스트 Notion 페이지 생성 완료: {new_podcast_url}")
                                return True
                        break
                        
        except subprocess.TimeoutExpired:
            print(f"⏰ {podcast['name']}: 시간 초과")
        except Exception as e:
            print(f"❌ {podcast['name']} 오류: {e}")
    
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
            duration=env_vars['PODCAST_DURATION'],
            is_alternative=False  # 일반 모드
        )
        
        if podcast_page_url == "DUPLICATE_FOUND":
            print(f"🔄 팟캐스트 중복 발견했지만 대체 자료 검색 실패.")
            print(f"💡 수동으로 다른 팟캐스트 피드에서 에피소드를 가져오거나 백업 피드를 사용하세요.")
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
