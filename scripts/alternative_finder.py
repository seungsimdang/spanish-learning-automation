#!/usr/bin/env python3
"""
Alternative material finder for Spanish learning automation.
Finds alternative articles and podcast episodes when duplicates are detected.
"""
import os
import sys
import subprocess
import json
from datetime import datetime, timedelta

def find_alternative_article():
    """기사 중복시 대안 기사를 찾아서 환경변수에 설정"""
    print("🔄 대안 기사 검색 중...")
    
    # 현재 사용된 소스와 다른 소스들 시도
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
    
    print(f"현재 소스: {current_source}")
    print(f"시도할 대안 소스들: {[s[0] for s in available_sources]}")
    
    for source_name, rss_url in available_sources:
        try:
            print(f"\n📰 {source_name} 소스 시도 중...")
            
            # collect_materials.py를 호출하여 대안 기사 수집
            env = os.environ.copy()
            env['READING_SOURCE'] = source_name
            env['FORCE_ALTERNATIVE'] = 'true'  # 대안 검색 모드임을 표시
            
            # collect_materials.py 실행
            result = subprocess.run([
                sys.executable, 
                os.path.join(os.path.dirname(__file__), 'collect_materials.py')
            ], env=env, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ {source_name}에서 새로운 기사 발견!")
                return True
            else:
                print(f"❌ {source_name}: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {source_name}: 시간 초과")
        except Exception as e:
            print(f"❌ {source_name} 오류: {e}")
    
    print("❌ 모든 대안 기사 소스 시도 실패")
    return False

def find_alternative_podcast():
    """팟캐스트 중복시 대안 팟캐스트를 찾아서 환경변수에 설정"""
    print("🔄 대안 팟캐스트 검색 중...")
    
    # 현재 팟캐스트와 다른 팟캐스트들 시도
    current_podcast = os.environ.get('PODCAST_NAME', '')
    current_weekday = os.environ.get('WEEKDAY_NAME', '')
    
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
    
    print(f"현재 팟캐스트: {current_podcast}")
    print(f"시도할 대안 팟캐스트들: {[p['name'] for p in available_podcasts]}")
    
    for podcast in available_podcasts:
        try:
            print(f"\n🎧 {podcast['name']} 팟캐스트 시도 중...")
            
            # collect_materials.py를 호출하여 대안 팟캐스트 수집
            env = os.environ.copy()
            env['PODCAST_NAME'] = podcast['name']
            env['PODCAST_RSS'] = podcast['rss']
            env['PODCAST_APPLE_BASE'] = podcast['apple_base']
            env['FORCE_ALTERNATIVE'] = 'true'  # 대안 검색 모드임을 표시
            
            # collect_materials.py 실행
            result = subprocess.run([
                sys.executable,
                os.path.join(os.path.dirname(__file__), 'collect_materials.py')
            ], env=env, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ {podcast['name']}에서 새로운 에피소드 발견!")
                return True
            else:
                print(f"❌ {podcast['name']}: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {podcast['name']}: 시간 초과")
        except Exception as e:
            print(f"❌ {podcast['name']} 오류: {e}")
    
    print("❌ 모든 대안 팟캐스트 소스 시도 실패")
    return False

def run_create_notion_pages():
    """create_notion_pages.py를 실행하여 새로운 페이지 생성 시도"""
    try:
        print("\n📝 Notion 페이지 생성 재시도...")
        
        result = subprocess.run([
            sys.executable,
            os.path.join(os.path.dirname(__file__), 'create_notion_pages.py')
        ], capture_output=True, text=True, timeout=60)
        
        print("=== create_notion_pages.py 출력 ===")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print("=================================")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ Notion 페이지 생성 시간 초과")
        return False
    except Exception as e:
        print(f"❌ Notion 페이지 생성 오류: {e}")
        return False

def main():
    """대안 자료 검색 및 Notion 페이지 생성을 최대 3회 시도"""
    print("=== 대안 자료 검색기 시작 ===")
    
    max_attempts = 3
    success = False
    
    for attempt in range(1, max_attempts + 1):
        print(f"\n🔄 시도 #{attempt}/{max_attempts}")
        
        # 먼저 현재 환경변수로 Notion 페이지 생성 시도
        if run_create_notion_pages():
            print("✅ 페이지 생성 성공!")
            success = True
            break
        
        print("❌ 페이지 생성 실패 - 대안 자료 검색 시작")
        
        # 기사 대안 검색
        article_title = os.environ.get('ARTICLE_TITLE', '')
        if article_title and not find_alternative_article():
            print("⚠️  기사 대안 검색 실패")
        
        # 팟캐스트 대안 검색
        podcast_title = os.environ.get('PODCAST_TITLE', '')  
        if podcast_title and not find_alternative_podcast():
            print("⚠️  팟캐스트 대안 검색 실패")
        
        # 마지막 시도가 아니면 잠시 대기
        if attempt < max_attempts:
            print("⏳ 3초 대기 후 재시도...")
            import time
            time.sleep(3)
    
    if not success:
        print(f"\n❌ {max_attempts}회 시도했지만 새로운 자료를 찾지 못했습니다.")
        print("💡 다음을 확인해보세요:")
        print("   1. RSS 피드들이 정상적으로 작동하는지")
        print("   2. Notion 데이터베이스 연결 상태")
        print("   3. 환경변수 설정 상태")
        return False
    
    print("\n✅ 대안 자료 검색 완료!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
