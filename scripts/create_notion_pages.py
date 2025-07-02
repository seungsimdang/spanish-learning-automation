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
            print("=======================================")
            return properties
        else:
            print(f"데이터베이스 조회 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return {}
    except Exception as e:
        print(f"데이터베이스 조회 오류: {e}")
        return {}

def create_notion_page(title, url, content_type, memo, category="", vocabulary="", duration=""):
    """Notion 페이지 생성"""
    
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
    
    # 실제 속성 이름 찾기 - 더 유연한 매핑
    title_prop = None
    url_prop = None
    type_prop = None
    notes_prop = None
    date_prop = None
    category_prop = None
    vocabulary_prop = None
    duration_prop = None
    
    for prop_name, prop_info in db_properties.items():
        prop_type = prop_info.get('type', '')
        prop_name_lower = prop_name.lower()
        
        if prop_type == 'title':
            title_prop = prop_name
        elif prop_type == 'url':
            url_prop = prop_name
        elif prop_type == 'select' and not type_prop:  # 첫 번째 select를 타입으로
            type_prop = prop_name
        elif prop_type == 'rich_text' and not notes_prop:  # 첫 번째 rich_text를 메모로
            notes_prop = prop_name
        elif prop_type == 'date':
            date_prop = prop_name
        elif prop_type == 'select' and type_prop and not category_prop:  # 두 번째 select를 카테고리로
            category_prop = prop_name
    
    # rich_text 속성들을 순서대로 할당
    rich_text_props = [name for name, info in db_properties.items() if info.get('type') == 'rich_text']
    if len(rich_text_props) >= 1:
        notes_prop = rich_text_props[0]
    if len(rich_text_props) >= 2:
        vocabulary_prop = rich_text_props[1]
    if len(rich_text_props) >= 3:
        duration_prop = rich_text_props[2]
    
    print(f"매핑된 속성들:")
    print(f"- 제목: {title_prop}")
    print(f"- URL: {url_prop}")
    print(f"- 타입: {type_prop}")
    print(f"- 메모: {notes_prop}")
    print(f"- 날짜: {date_prop}")
    print(f"- 카테고리: {category_prop}")
    print(f"- 어휘: {vocabulary_prop}")
    print(f"- 재생시간: {duration_prop}")
    
    # 필수 속성이 없으면 기본값 사용
    if not title_prop:
        print("경고: 제목 속성을 찾을 수 없어서 첫 번째 title 속성을 사용합니다.")
        for prop_name, prop_info in db_properties.items():
            if prop_info.get('type') == 'title':
                title_prop = prop_name
                break
    
    if not title_prop:
        print("오류: 제목 속성을 찾을 수 없습니다.")
        return None
    
    # 페이지 속성 설정 - 모든 속성을 기본값으로라도 채우기
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
    
    # URL 속성 - 빈 값이라도 추가하지 않음 (Notion URL 타입은 유효한 URL만 허용)
    if url_prop and url and (url.startswith('http://') or url.startswith('https://')):
        properties[url_prop] = {
            "url": url
        }
    
    # 타입 속성 - 항상 추가
    if type_prop:
        properties[type_prop] = {
            "select": {
                "name": content_type or "일반"
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
    
    # 카테고리 속성 - 기본값 설정
    if category_prop:
        properties[category_prop] = {
            "select": {
                "name": category or "일반"
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
    
    # 재생시간 속성 - 빈 값이라도 추가
    if duration_prop:
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
            content_type="독해",
            memo=env_vars['ARTICLE_MEMO'],
            category=env_vars['ARTICLE_CATEGORY'],
            vocabulary=env_vars['ARTICLE_VOCABULARY']
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
            content_type="청취",
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
