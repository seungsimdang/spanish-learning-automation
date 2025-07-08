#!/usr/bin/env python3
"""
Collect Spanish learning materials: articles and podcast episodes with LLM-powered content analysis.
"""
import os
import sys
import requests
import feedparser
import re
import time
import random
import traceback
import urllib.parse
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# LLM 분석기 임포트
try:
    from llm_analyzer import SpanishLLMAnalyzer
    LLM_AVAILABLE = True
except ImportError:
    print("⚠️ LLM 분석기를 사용할 수 없습니다. LLM이 필수입니다.")
    LLM_AVAILABLE = False

def is_episode_recent(published_date, max_days_old=30, allow_old=True):
    """
    에피소드가 최근 며칠 이내에 발행되었는지 확인
    모든 에피소드 허용 (학습 목적)
    """
    return True  # 모든 에피소드 허용



def analyze_text_difficulty(content):
    """Analyze text difficulty using LLM"""
    if not content:
        return "B2"  # 기본값
    
    if not LLM_AVAILABLE or not os.environ.get('OPENAI_API_KEY'):
        print("⚠️ LLM 분석기가 필요합니다. 기본 난이도 B2를 사용합니다.")
        return "B2"
    
    try:
        analyzer = SpanishLLMAnalyzer()
        return analyzer.analyze_text_difficulty(content)
    except Exception as e:
        print(f"LLM 난이도 분석 오류: {e}")
        return "B2"  # 기본값

def search_apple_podcasts_episode(podcast_name, episode_title, apple_base):
    """Search for exact episode URL using Apple iTunes Search API"""
    try:
        import urllib.parse
        
        print(f"    🔍 iTunes Search API로 {podcast_name} 에피소드 검색 중...")
        
        # 다양한 검색어로 시도
        search_terms = []
        
        # 1. 팟캐스트 이름 + 에피소드 제목
        search_terms.append(f"{podcast_name} {episode_title}")
        
        # 2. 에피소드 제목만으로도 검색
        search_terms.append(episode_title)
        
        # 3. 팟캐스트 이름만으로 검색 (에피소드가 너무 구체적일 때)
        search_terms.append(podcast_name)
        
        # 특별한 검색어 패턴 추가 (모든 팟캐스트에 적용)
        if ':' in episode_title:
            # 콜론으로 구분된 제목의 경우 (예: "The Network: Episode Title")
            main_part = episode_title.split(':')[0].strip()
            search_terms.append(main_part)
            subtitle = episode_title.split(':', 1)[1].strip()
            search_terms.append(subtitle)
            search_terms.append(f"{podcast_name} {main_part}")
            search_terms.append(f"{podcast_name} {subtitle}")
        
        # 중요한 키워드만 추출하여 검색 (모든 팟캐스트에 적용)
        keywords = episode_title.lower().split()
        important_words = [w for w in keywords if len(w) > 3 and w not in ['the', 'and', 'of', 'in', 'to', 'for', 'with', 'episode', 'ep']]
        if important_words and len(important_words) >= 2:
            search_terms.append(f"{podcast_name} {' '.join(important_words[:2])}")
        
        print(f"    🔍 검색어들: {search_terms[:5]}...")  # 처음 5개만 표시
        
        for search_term in search_terms:
            encoded_term = urllib.parse.quote(search_term)
            search_url = f"https://itunes.apple.com/search?term={encoded_term}&media=podcast&entity=podcastEpisode&limit=50"
            
            print(f"    📡 iTunes Search API 호출: {search_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                print(f"    📊 iTunes 검색 결과 ({search_term}): {len(results)}개 에피소드 발견")
                
                # 검색 결과에서 해당 팟캐스트 에피소드 찾기
                for result in results:
                    collection_name = result.get('collectionName', '').lower()
                    track_name = result.get('trackName', '')
                    track_view_url = result.get('trackViewUrl', '')
                    
                    print(f"    📺 검토 중: {track_name} (컬렉션: {collection_name})")
                    
                    # 팟캐스트 이름 매칭 확인 (통합된 로직)
                    podcast_match = False
                    
                    # 정확한 이름 매칭 우선
                    if podcast_name.lower().replace(' ', '') in collection_name.replace(' ', ''):
                        podcast_match = True
                    # 키워드 기반 매칭
                    elif any(name.lower() in collection_name for name in podcast_name.split() if len(name) > 3):
                        podcast_match = True
                    
                    if podcast_match:
                        # 통합된 에피소드 제목 매칭 로직
                        title_match = False
                        
                        title_words = episode_title.lower().split()
                        track_words = track_name.lower().split()
                        
                        # 1. 공통 단어 매칭 (모든 팟캐스트에 적용)
                        common_words = set(title_words) & set(track_words)
                        if len(common_words) >= 2:
                            title_match = True
                        
                        # 2. 중요한 단어 매칭 (모든 팟캐스트에 적용)
                        elif any(word in track_name.lower() for word in title_words if len(word) > 4):
                            title_match = True
                        
                        # 3. 키워드 기반 매칭 (모든 팟캐스트에 적용)
                        else:
                            important_words = [word for word in title_words if len(word) > 3 and word not in ['the', 'and', 'of', 'in', 'to', 'for', 'with', 'episode', 'ep']]
                            if important_words:
                                matches = sum(1 for word in important_words if word in track_name.lower())
                                if matches >= min(2, len(important_words)):
                                    title_match = True
                        
                        if title_match and track_view_url:
                            print(f"    ✅ Apple Podcast 정확한 에피소드 URL 발견: {track_view_url}")
                            return track_view_url
                
            else:
                print(f"    ❌ iTunes Search API 호출 실패: {response.status_code}")
        
        print(f"    ⚠️ 모든 검색어로 시도했지만 정확한 에피소드를 찾지 못함")
        return apple_base
                
    except Exception as e:
        print(f"    ❌ iTunes Search 오류: {e}")
        return apple_base

def generate_apple_podcast_link(podcast_name, apple_base, episode_link, episode_number, episode_title=""):
    """Generate optimized Apple Podcasts link by podcast type"""
    
    # 모든 팟캐스트에 대한 통합된 링크 생성 전략
    if 'Radio Ambulante' in podcast_name or 'npr.org' in episode_link:
        # Radio Ambulante는 원본 웹사이트 링크를 우선 사용
        if episode_link and 'radioambulante.org' in episode_link and validate_url(episode_link):
            print(f"    ✅ Radio Ambulante 원본 웹사이트 링크 사용: {episode_link}")
            return episode_link
        else:
            # iTunes Search API 시도
            if episode_title:
                apple_url = search_apple_podcasts_episode(podcast_name, episode_title, apple_base)
                if apple_url != apple_base and validate_url(apple_url):
                    print(f"    ✅ iTunes Search API에서 Radio Ambulante 에피소드 발견: {apple_url}")
                    return apple_url
            
            # 모든 시도가 실패하면 원본 링크 또는 기본 Apple 링크 반환
            if episode_link and validate_url(episode_link):
                return episode_link
            else:
                return apple_base
    
    elif 'SpanishPodcast' in podcast_name:
        # SpanishPodcast는 원본 웹사이트 링크를 우선 사용
        if episode_link and validate_url(episode_link):
            print(f"    ✅ SpanishPodcast 원본 웹사이트 링크 사용: {episode_link}")
            return episode_link
        else:
            print(f"    ⚠️ SpanishPodcast 원본 링크 유효하지 않음, iTunes Search API 시도")
            # 원본 링크가 유효하지 않으면 iTunes Search API 시도
            if episode_title:
                apple_url = search_apple_podcasts_episode(podcast_name, episode_title, apple_base)
                if apple_url != apple_base and validate_url(apple_url):
                    print(f"    ✅ iTunes Search API에서 SpanishPodcast 에피소드 발견: {apple_url}")
                    return apple_url
            
            # iTunes Search도 실패하면 기본 Apple Podcasts 링크 반환
            print(f"    🔄 iTunes Search API도 실패, 기본 Apple Podcasts 링크 사용: {apple_base}")
            return apple_base

    elif 'Hoy Hablamos' in podcast_name:
        # iTunes Search API 우선 시도
        if episode_title:
            apple_url = search_apple_podcasts_episode(podcast_name, episode_title, apple_base)
            if apple_url != apple_base and validate_url(apple_url):
                print(f"    ✅ iTunes Search API에서 Hoy Hablamos 에피소드 발견: {apple_url}")
                return apple_url
        
        # iTunes Search가 실패하면 에피소드 번호 기반으로 링크 생성 시도
        if episode_number and episode_number != 'N/A':
            try:
                ep_num = int(episode_number)
                generated_url = f"{apple_base}?i=1000{ep_num:06d}"
                print(f"    🔄 에피소드 번호 기반 URL 생성: {generated_url}")
                if validate_url(generated_url):
                    return generated_url
            except:
                pass
        
        print(f"    🔄 모든 시도 실패, 기본 Apple Podcasts 링크 사용: {apple_base}")
        return apple_base
        
    elif 'SpanishWithVicente' in podcast_name:
        # iTunes Search API 우선 시도
        if episode_title:
            apple_url = search_apple_podcasts_episode(podcast_name, episode_title, apple_base)
            if apple_url != apple_base and validate_url(apple_url):
                print(f"    ✅ iTunes Search API에서 SpanishWithVicente 에피소드 발견: {apple_url}")
                return apple_url
        
        # iTunes Search가 실패하면 에피소드 번호 추가 시도
        if episode_number and episode_number != 'N/A':
            generated_url = f"{apple_base}?i={episode_number}"
            print(f"    🔄 에피소드 번호 추가 URL: {generated_url}")
            if validate_url(generated_url):
                return generated_url
        
        print(f"    🔄 모든 시도 실패, 기본 Apple Podcasts 링크 사용: {apple_base}")
        return apple_base
        
    elif 'DELE' in podcast_name:
        # iTunes Search API 우선 시도
        if episode_title:
            apple_url = search_apple_podcasts_episode(podcast_name, episode_title, apple_base)
            if apple_url != apple_base and validate_url(apple_url):
                print(f"    ✅ iTunes Search API에서 DELE 에피소드 발견: {apple_url}")
                return apple_url
        
        # iTunes Search가 실패하면 메인 링크 사용
        print(f"    🔄 iTunes Search 실패, 기본 Apple Podcasts 링크 사용: {apple_base}")
        return apple_base
    else:
        # 기본 전략: iTunes Search API로 정확한 에피소드 찾기
        if episode_title:
            print(f"    🔍 iTunes Search API로 {podcast_name} 에피소드 검색 중...")
            
            # 다양한 검색어로 시도
            search_terms = []
            
            # 1. 팟캐스트 이름 + 에피소드 제목
            search_terms.append(f"{podcast_name} {episode_title}")
            
            # 2. 에피소드 번호가 있으면 번호로도 검색
            if episode_number and episode_number != 'N/A':
                search_terms.append(f"{podcast_name} {episode_number}")
                search_terms.append(f"{podcast_name} Episode {episode_number}")
                search_terms.append(f"{podcast_name} Ep {episode_number}")
            
            # 3. 에피소드 제목만으로도 검색
            search_terms.append(episode_title)
            
            for search_term in search_terms:
                try:
                    encoded_term = urllib.parse.quote(search_term)
                    search_url = f"https://itunes.apple.com/search?term={encoded_term}&media=podcast&entity=podcastEpisode&limit=20"
                    
                    print(f"    🔍 검색어: {search_term}")
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    response = requests.get(search_url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        results = data.get('results', [])
                        
                        print(f"    📊 iTunes 검색 결과: {len(results)}개 에피소드 발견")
                        
                        for result in results:
                            result_title = result.get('trackName', '').lower()
                            collection_name = result.get('collectionName', '').lower()
                            track_view_url = result.get('trackViewUrl', '')
                            
                            print(f"    📺 검토 중: {result.get('trackName', '')} (컬렉션: {collection_name})")
                            
                            # 팟캐스트 이름 매칭 확인
                            podcast_match = False
                            if 'spanishpodcast' in podcast_name.lower() and 'spanishpodcast' in collection_name:
                                podcast_match = True
                            elif any(name.lower() in collection_name for name in podcast_name.split() if len(name) > 3):
                                podcast_match = True
                            
                            if podcast_match:
                                # 에피소드 제목 매칭 확인
                                title_match = False
                                
                                # 에피소드 번호 매칭
                                if episode_number and episode_number != 'N/A':
                                    if episode_number in result_title or f"episode {episode_number}" in result_title or f"ep {episode_number}" in result_title:
                                        title_match = True
                                
                                # 제목 키워드 매칭
                                if not title_match:
                                    title_words = episode_title.lower().split()
                                    important_words = [word for word in title_words if len(word) > 3 and word not in ['the', 'and', 'of', 'in', 'to', 'for', 'with', 'episode', 'ep']]
                                    if important_words:
                                        matches = sum(1 for word in important_words if word in result_title)
                                        if matches >= min(2, len(important_words)):
                                            title_match = True
                                
                                if title_match and track_view_url:
                                    print(f"    ✅ Apple Podcast 정확한 에피소드 URL 발견: {track_view_url}")
                                    return track_view_url
                        
                        # 이 검색어로 찾았으면 더 이상 시도하지 않음
                        if results:
                            print(f"    ⚠️ iTunes에서 정확한 매칭을 찾지 못함 (검색어: {search_term})")
                            break
                            
                    else:
                        print(f"    ❌ iTunes Search API 오류: {response.status_code}")
                        
                except Exception as e:
                    print(f"    ❌ iTunes Search 오류 (검색어: {search_term}): {e}")
                    continue
            
            print(f"    ⚠️ 모든 검색어로 시도했지만 정확한 에피소드를 찾지 못함")
        
        # 모든 시도가 실패하면 기본 Apple Podcasts 링크 반환
        print(f"    🔄 기본 Apple Podcasts 링크 사용: {apple_base}")
        
        # Apple Podcasts 링크 유효성 검증
        if validate_url(apple_base):
            return apple_base
        else:
            print(f"    ❌ 기본 Apple Podcasts 링크도 유효하지 않음: {apple_base}")
            
            # 지역 코드 변경 시도 (us -> kr, kr -> us)
            if '/us/' in apple_base:
                alternative_url = apple_base.replace('/us/', '/kr/')
                print(f"    🔄 지역 코드 변경 시도 (us -> kr): {alternative_url}")
                if validate_url(alternative_url):
                    return alternative_url
            elif '/kr/' in apple_base:
                alternative_url = apple_base.replace('/kr/', '/us/')
                print(f"    🔄 지역 코드 변경 시도 (kr -> us): {alternative_url}")
                if validate_url(alternative_url):
                    return alternative_url
            
            # 최종적으로 원본 링크 반환
            print(f"    ⚠️ 모든 Apple Podcasts 링크 시도 실패, 원본 링크 반환")
            return apple_base

def get_article_content(url):
    """Get actual article content from URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 사이트별 본문 추출 로직
        content = ""
        
        if '20minutos.es' in url:
            # 20minutos 본문 추출
            article_body = soup.find('div', class_='article-text') or soup.find('div', class_='content')
            if article_body:
                paragraphs = article_body.find_all(['p', 'div'])
                content = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
        
        elif 'elpais.com' in url:
            # El País 본문 추출
            article_body = soup.find('div', {'data-dtm-region': 'articulo_cuerpo'}) or \
                         soup.find('div', class_='a_c clearfix') or \
                         soup.find('div', class_='articulo-cuerpo')
            if article_body:
                paragraphs = article_body.find_all('p')
                content = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
        
        # 일반적인 기사 본문 추출 (fallback)
        if not content:
            # 일반적인 article 태그나 main 태그에서 추출
            article = soup.find('article') or soup.find('main')
            if article:
                paragraphs = article.find_all('p')
                content = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()][:10])  # 처음 10개 문단만
        
        # 내용이 너무 짧으면 다른 방법 시도
        if len(content) < 200:
            all_paragraphs = soup.find_all('p')
            content = ' '.join([p.get_text().strip() for p in all_paragraphs if len(p.get_text().strip()) > 50][:8])
        
        return content[:2000]  # 처음 2000자만 반환
        
    except Exception as e:
        print(f"기사 내용 추출 오류: {e}")
        return ""

def extract_category_from_content(title, content):
    """Extract category from title and content"""
    full_text = (title + " " + content).lower()
    
    keywords = {
        '정치': ['gobierno', 'política', 'elecciones', 'parlamento', 'ministro', 'rey', 'presidente', 'votación', 'congreso'],
        '경제': ['economía', 'banco', 'euro', 'empleo', 'crisis', 'mercado', 'dinero', 'trabajo', 'empresa', 'inversión'],
        '사회': ['sociedad', 'educación', 'sanidad', 'vivienda', 'familia', 'salud', 'población', 'ciudadanos'],
        '스포츠': ['fútbol', 'real madrid', 'barcelona', 'liga', 'deporte', 'partido', 'atletico', 'champions'],
        '기술': ['tecnología', 'internet', 'móvil', 'digital', 'app', 'inteligencia', 'innovación'],
        '문화': ['cultura', 'arte', 'música', 'teatro', 'festival', 'libro', 'cine', 'exposición'],
        '국제': ['internacional', 'mundial', 'europa', 'américa', 'china', 'estados unidos', 'unión europea']
    }
    
    category_scores = {}
    for category, words in keywords.items():
        score = sum(1 for word in words if word in full_text)
        if score > 0:
            category_scores[category] = score
    
    if category_scores:
        return max(category_scores, key=category_scores.get)
    return '일반'

def extract_episode_number(title):
    patterns = [
        r'Ep\.?\s*(\d+)',
        r'Episode\s*(\d+)',
        r'#(\d+)',
        r'(\d{3,4})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def extract_duration_from_feed(entry):
    # iTunes 듀레이션 먼저 확인
    if hasattr(entry, 'itunes_duration'):
        duration = entry.itunes_duration
        # 초 단위인 경우 분:초로 변환
        if duration.isdigit():
            total_seconds = int(duration)
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}:{seconds:02d}"
        return duration
    
    # 요약에서 재생시간 추출 시도
    summary = entry.get('summary', '') + entry.get('description', '')
    duration_patterns = [
        r'(\d+)\s*min',
        r'(\d+)\s*분',
        r'(\d+):(\d+)',
        r'Duration:\s*(\d+)'
    ]
    
    for pattern in duration_patterns:
        match = re.search(pattern, summary)
        if match:
            if ':' in pattern:
                return f"{match.group(1)}:{match.group(2)}"
            else:
                return f"{match.group(1)}분"
    
    return "15-25분"

def extract_topic_keywords(title, summary=""):
    content = (title + " " + summary).lower()
    
    topic_keywords = {
        '문법': ['gramática', 'verbos', 'subjuntivo', 'pretérito', 'sintaxis'],
        '문화': ['cultura', 'tradición', 'costumbres', 'historia', 'arte'],
        '요리': ['cocina', 'comida', 'receta', 'gastronomía', 'plato'],
        '여행': ['viajes', 'turismo', 'ciudades', 'lugares', 'destinos'],
        '직업': ['trabajo', 'empleo', 'profesión', 'carrera', 'oficina'],
        '가족': ['familia', 'padres', 'hijos', 'matrimonio', 'casa'],
        '기술': ['tecnología', 'internet', 'móviles', 'digital', 'aplicaciones'],
        '정치': ['política', 'gobierno', 'elecciones', 'democracia'],
        '경제': ['economía', 'dinero', 'banco', 'trabajo', 'crisis', 'preferentes', 'ahorros'],
        '사회': ['sociedad', 'gente', 'problemas', 'cambios', 'vida'],
        '건강': ['salud', 'medicina', 'hospital', 'enfermedad', 'médico'],
        '교육': ['educación', 'estudiantes', 'universidad', 'aprender']
    }
    
    for topic, keywords in topic_keywords.items():
        if any(keyword in content for keyword in keywords):
            return topic
    return '일반 주제'

def create_detailed_memo(content_type, data, weekday_name):
    if content_type == "article":
        category = data.get('category', '일반')
        difficulty = data.get('difficulty', 'B2')
        content = data.get('content_preview', '')
        
        # 레벨별 문법 포인트 추출
        grammar_points = extract_grammar_points_from_content(content, difficulty)
        
        # 문법 포인트 텍스트 생성
        grammar_text = ""
        if grammar_points:
            grammar_text = f"📝 {difficulty} 문법: {' | '.join(grammar_points)} "
        
        return (f"📰 {category} 분야 기사 ({difficulty} 수준) "
               f"📅 발행: {data.get('published', '오늘')} "
               f"🎯 학습목표: 15분 독해, {difficulty} 수준 문법 분석 "
               f"{grammar_text}"
               f"🤖 AI 분석 "
               f"📖 권장: 문법 구조 분석을 통한 독해 실력 향상")

    elif content_type == "podcast":
        podcast_name = data.get('podcast_name', '')
        duration = data.get('duration', '15-25분')
        topic = data.get('topic', '일반 주제')
        episode_num = data.get('episode_number', '')
        episode_title = data.get('title', '')
        summary = data.get('summary', '')
        difficulty = data.get('difficulty', 'B2')
        
        # 팟캐스트 이름에서 특수 표시 제거하여 정확한 이름 얻기
        clean_podcast_name = podcast_name.replace(" (백업)", "").replace(" (대안)", "").replace(" (중복 가능)", "").strip()
        
        # 'N/A'나 빈 값 처리
        if episode_num == 'N/A' or not episode_num:
            episode_num = ''
        
        # 주제 정리 (원하지 않는 값들 제거)
        if topic in ['일반 주제', 'N/A', '']:
            topic = '스페인어 학습'
        
        # 특별 상태 표시
        status_info = ""
        if "(대안)" in podcast_name:
            status_info = "🔄 대안 팟캐스트로 선택됨 "
        elif "(중복 가능)" in podcast_name:
            status_info = "⚠️ 중복 가능성 있음 "
        
        # 팟캐스트 transcript에서 구어체 표현 분석
        expressions = []
        episode_url = data.get('url', '')
        
        # 실제 transcript나 상세 내용 가져오기
        print(f"\n  🔍 팟캐스트 콘텐츠 수집 시작")
        print(f"  📺 에피소드: {episode_title}")
        print(f"  🔗 원본 URL: {episode_url}")
        
        transcript_content = get_podcast_transcript_or_content(episode_url, episode_title)
        
        print(f"\n  📊 콘텐츠 수집 결과:")
        print(f"  📏 수집된 콘텐츠 길이: {len(transcript_content) if transcript_content else 0}자")
        
        if transcript_content:
            print(f"  ✅ 콘텐츠 수집 성공")
            content_preview = transcript_content[:200].replace('\n', ' ').strip()
            print(f"  � 콘텐츠 미리보기: {content_preview}...")
            print(f"  🤖 구어체 표현 분석 시작...")
            expressions = extract_vocabulary_expressions_from_transcript(transcript_content, difficulty)
        else:
            print(f"  ❌ 콘텐츠 수집 실패 - 모든 소스에서 콘텐츠를 찾지 못함")
            print(f"  📝 구어체 분석 건너뛰기 (콘텐츠 없음)")
            expressions = []
        
        # Apple Podcast에서 정확한 URL을 찾았는지 확인
        found_apple_url = get_found_apple_url()
        if found_apple_url:
            print(f"    🍎 Apple Podcast 정확한 URL 발견: {found_apple_url}")
            # 데이터에 정확한 Apple URL 업데이트
            data['apple_link'] = found_apple_url
        
        # 주제에 따른 학습목표 설정
        learning_goals = {
            '경제': '금융 표현',
            '정치': '정치 표현',
            '문화': '문화 표현',
            '사회': '사회 이슈 표현',
            '교육': '교육 관련 표현',
            '건강': '의료 표현',
            '기술': '기술 표현',
            '문법': '문법 구조',
            '스페인어 학습': '일상 표현'
        }
        goal = learning_goals.get(topic, '핵심 표현')
        
        # 재생시간에 따른 청취 계획 설정
        if ':' in duration:
            try:
                minutes, seconds = duration.split(':')
                total_minutes = int(minutes)
                if total_minutes > 30:
                    listen_plan = f"(30분 청취 목표)"
                elif total_minutes > 20:
                    listen_plan = f"(전체 {duration} 청취)"
                else:
                    listen_plan = f"(전체 {duration} 청취)"
            except:
                listen_plan = "(25분 청취 목표)"
        else:
            listen_plan = "(25분 청취 목표)"
        
        # 에피소드 번호가 있으면 표시, 없으면 생략
        episode_text = f"Ep.{episode_num} - " if episode_num else ""
        
        # 구어체 표현 텍스트 및 청취 전략 생성
        print(f"\n  📊 팟캐스트 메모 생성 중...")
        print(f"  🎯 발견된 구어체 표현 개수: {len(expressions)}개")
        
        expression_text = ""
        listening_strategy = ""
        if expressions:
            print(f"  ✅ 구어체 표현 발견 - 구어체 중심 학습 전략 적용")
            expression_text = f"🎯 {difficulty} 구어체: {' | '.join(expressions)} "
            listening_strategy = "📻 권장: 구어체 표현에 집중하여 청취"
        else:
            print(f"  📝 구어체 표현 없음 - 정식 언어 중심 학습 전략 적용")
            print(f"     • 이유: 팟캐스트가 정식/공식적 언어로 구성됨")
            print(f"     • 대안: 주제별 전문 어휘와 논리적 구조에 집중")
            expression_text = f"🎯 {difficulty} 구어체: 분석 결과 0개 발견 "
            listening_strategy = "📻 권장: 주제별 전문 어휘와 논리적 구조에 집중하여 청취"
        
        # 정확한 에피소드 제목 추가 (Apple Podcasts에서 검색할 수 있도록)
        search_info = ""
        if episode_title:
            # 제목이 너무 길면 축약
            short_title = episode_title[:50] + "..." if len(episode_title) > 50 else episode_title
            search_info = f"🔍 검색어: \"{short_title}\" "
        
        # Radio Ambulante인 경우에만 웹사이트 URL 정보 추가
        url_info = ""
        if 'Radio Ambulante' in clean_podcast_name:
            episode_url = data.get('url', '')
            if 'radioambulante.org' in episode_url:
                url_info = f"🌐 웹사이트에서 직접 청취 가능 "
            elif 'npr.org' in episode_url:
                url_info = f"📻 NPR에서 청취 가능 "
            
            # Apple Podcasts에서 수동 검색을 위한 정보 추가
            if episode_title:
                # 제목에서 부제목 추출 (콜론 이후 부분)
                if ':' in episode_title:
                    main_title = episode_title.split(':')[0].strip()
                    subtitle = episode_title.split(':', 1)[1].strip()
                    url_info += f"🍎 Apple Podcasts 검색: \"{main_title}\" 또는 \"{subtitle}\" "
                else:
                    url_info += f"🍎 Apple Podcasts 검색: \"{episode_title}\" "
        
        return (f"🎧 {clean_podcast_name} {episode_text}{weekday_name} 스페인어 팟캐스트 "
               f"{status_info}"
               f"📺 에피소드: \"{episode_title}\" "
               f"⏱️ 재생시간: {duration} {listen_plan} "
               f"🎯 학습목표: {goal} 5개 정리 "
               f"🌍 주제: {topic} "
               f"{expression_text}"
               f"🤖 AI 분석 "
               f"{search_info}"
               f"{url_info}"
               f"{listening_strategy}")

def extract_radio_ambulante_url(entry):
    """Extract actual Radio Ambulante website URL"""
    try:
        # 에피소드 제목에서 슬러그 생성 시도
        title = entry.title.lower()
        # 특수 문자 제거 및 공백을 하이픈으로 변환
        import re
        slug = re.sub(r'[^\w\s-]', '', title)
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')
        
        # Radio Ambulante 웹사이트 URL 생성
        radio_ambulante_url = f"https://radioambulante.org/audio/{slug}"
        
        # URL 유효성 확인
        if validate_url(radio_ambulante_url):
            return radio_ambulante_url
        
        # 슬러그 생성 실패 시 요약에서 링크 찾기
        summary = entry.get('summary', '') + entry.get('description', '')
        url_match = re.search(r'https://radioambulante\.org/audio/[^\s<>"]+', summary)
        if url_match:
            found_url = url_match.group(0)
            if validate_url(found_url):
                return found_url
                
        # 모든 시도 실패시 None 반환
        return None
        
    except Exception as e:
        print(f"Radio Ambulante URL 추출 오류: {e}")
        return None

def validate_url(url, timeout=5):
    """Validate URL quickly"""
    try:
        if not url or not (url.startswith('http://') or url.startswith('https://')):
            return False
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        return response.status_code < 400
    except:
        return False

def get_alternative_podcasts(current_weekday, current_podcast_name):
    """현재 요일과 팟캐스트를 제외한 대안 팟캐스트 목록 반환 (실제 작동하는 피드들만)"""
    # 실제 작동하는 스페인어 팟캐스트들만
    working_podcasts = {
        "SpanishPodcast": {
            "name": "SpanishPodcast",
            "rss": "https://feeds.feedburner.com/SpanishPodcast",
            "apple_base": "https://podcasts.apple.com/us/podcast/spanishpodcast/id70077665",
            "region": "스페인"
        },
        "Hoy Hablamos": {
            "name": "Hoy Hablamos",
            "rss": "https://www.hoyhablamos.com/feed/podcast/",
            "apple_base": "https://podcasts.apple.com/es/podcast/hoy-hablamos/id1455031513",
            "region": "스페인"
        }
    }
    
    # 현재 팟캐스트를 제외한 대안들 반환
    alternatives = []
    for name, info in working_podcasts.items():
        if name != current_podcast_name:
            alternatives.append((name, info))
    
    return alternatives



def try_alternative_podcast(alternatives, weekday_name):
    """대안 팟캐스트들을 시도해서 중복되지 않은 에피소드 찾기"""
    for alt_name, alt_info in alternatives:
        try:
            print(f"\n🔄 대안 팟캐스트 시도: {alt_name}")
            print(f"   RSS: {alt_info['rss']}")
            
            feed = feedparser.parse(alt_info['rss'])
            
            if not feed.entries:
                print(f"   ❌ {alt_name}: 에피소드가 없음")
                continue
                
            # 최근 에피소드들 확인
            for entry in feed.entries[:3]:  # 최근 3개만 확인
                episode_title = entry.title
                print(f"   📝 에피소드 확인: {episode_title}")
                
                # 날짜 체크
                if not is_episode_recent(entry.get('published_parsed')):
                    print(f"      ❌ 오래된 에피소드")
                    continue
                
                print(f"   ✅ {alt_name}에서 새로운 에피소드 발견!")
                
                # 에피소드 데이터 생성
                episode_number = extract_episode_number(episode_title)
                duration = extract_duration_from_feed(entry)
                topic = extract_topic_keywords(episode_title, entry.get('summary', ''))
                
                episode_link = entry.link
                
                # Radio Ambulante인 경우 실제 웹사이트 URL 시도
                if 'Radio Ambulante' in alt_name:
                    radio_ambulante_url = extract_radio_ambulante_url(entry)
                    if radio_ambulante_url:
                        episode_link = radio_ambulante_url
                
                # Apple Podcasts 링크 생성
                apple_link = generate_apple_podcast_link(alt_name, alt_info['apple_base'], episode_link, episode_number, episode_title)
                
                # Radio Ambulante의 경우 Apple에서 찾지 못하면 에피소드 URL을 메인 URL로 사용
                final_episode_url = episode_link
                if 'Radio Ambulante' in alt_name:
                    if apple_link != alt_info['apple_base'] and validate_url(apple_link):
                        final_episode_url = apple_link
                    else:
                        final_episode_url = episode_link
                        apple_link = alt_info['apple_base']
                else:
                    if not validate_url(episode_link):
                        final_episode_url = apple_link if validate_url(apple_link) else alt_info['apple_base']
                    if not validate_url(apple_link):
                        apple_link = alt_info['apple_base']
                
                # 대안 팟캐스트 난이도 분석
                alt_summary = entry.get('summary', '')
                alt_difficulty = analyze_text_difficulty(alt_summary) if alt_summary else "B2"
                
                podcast_data = {
                    'title': episode_title,
                    'url': final_episode_url,
                    'apple_link': apple_link,
                    'published': entry.get('published', ''),
                    'duration': duration,
                    'episode_number': episode_number or 'N/A',
                    'topic': topic,
                    'podcast_name': f"{alt_name} (대안)",  # 대안임을 표시
                    'summary': entry.get('summary', '')[:200],
                    'difficulty': alt_difficulty  # 난이도 정보 추가
                }
                
                print(f"   📊 대안 팟캐스트 데이터:")
                print(f"      에피소드: {episode_title}")
                print(f"      URL: {final_episode_url}")
                print(f"      Apple: {apple_link}")
                
                return podcast_data
                
        except Exception as e:
            print(f"   ❌ {alt_name} 시도 중 오류: {e}")
            continue
    
    print("\n❌ 모든 대안 팟캐스트에서도 새로운 에피소드를 찾지 못했습니다.")
    return None

# ==========================================
# 스페인어 콘텐츠 검증 함수들 (선택적 사용)
# ==========================================

def verify_spanish_content_with_llm(content, title="", use_llm=False):
    """
    선택적으로 LLM을 사용하여 콘텐츠가 스페인어인지 검증
    use_llm=False인 경우 기본 패턴만 체크 (빠른 검증)
    """
    if not content:
        return False
    
    # LLM 사용하지 않는 경우 (기본값) - 빠른 기본 검증만
    if not use_llm:
        spanish_patterns = ['el ', 'la ', 'es ', 'que ', 'con ', 'de ', 'en ', 'por ', 'para ', 'ñ']
        english_patterns = ['the ', 'and ', 'is ', 'are ', 'was ', 'were ', 'this ', 'that ']
        
        content_lower = content.lower()
        spanish_count = sum(1 for pattern in spanish_patterns if pattern in content_lower)
        english_count = sum(1 for pattern in english_patterns if pattern in content_lower)
        
        return spanish_count > english_count
    
    # LLM 사용하는 경우 (선택적 더블체크)
    if not LLM_AVAILABLE or not os.environ.get('OPENAI_API_KEY'):
        print("⚠️ LLM 분석기가 필요하지만 사용할 수 없음. 기본 검증 방법을 사용합니다.")
        return verify_spanish_content_with_llm(content, title, use_llm=False)
    
    try:
        analyzer = SpanishLLMAnalyzer()
        
        # LLM에게 언어 검증 요청
        verification_prompt = f"""
콘텐츠의 언어를 분석해주세요.

제목: {title}
내용: {content[:500]}...

이 콘텐츠가 스페인어인지 영어인지 판단하고, "SPANISH" 또는 "ENGLISH"로만 답변해주세요.
"""
        
        # LLM API 호출 (간단한 검증용)
        result = analyzer.simple_language_detection(verification_prompt)
        
        if "SPANISH" in result.upper():
            print(f"✅ LLM 검증: 스페인어 콘텐츠로 확인됨")
            return True
        else:
            print(f"❌ LLM 검증: 영어 콘텐츠로 확인됨")
            return False
            
    except Exception as e:
        print(f"LLM 언어 검증 오류: {e}")
        # 오류 시 기본 검증 방법 사용
        return verify_spanish_content_with_llm(content, title, use_llm=False)

def is_spanish_content_by_title(title, summary="", use_llm_verification=False):
    """
    제목과 요약으로 스페인어 콘텐츠인지 판단
    검증된 스페인어 피드를 사용하므로 기본적으로 빠른 검증만 실행
    """
    content = title + " " + summary
    
    # 선택적으로 LLM 더블체크 (use_llm_verification=True인 경우만)
    if use_llm_verification:
        if verify_spanish_content_with_llm(content, title, use_llm=True):
            return True
    
    # 기본 빠른 검증 (검증된 피드이므로 대부분 통과)
    content_lower = content.lower()
    
    # 명확한 스페인어 지표들
    spanish_indicators = [
        'radio ambulante', 'español', 'española', 'spanishpodcast', 
        'hoy hablamos', 'dele', 'notes in spanish', 'ñ', 'españolistos'
    ]
    
    # 명확한 영어 지표들 (혹시 모를 경우를 위해)
    english_indicators = [
        'the daily', 'journalism', 'nytimes', 'npr', 'america', 
        'president', 'congress', 'election', 'english'
    ]
    
    # 명확한 경우 판단
    if any(indicator in content_lower for indicator in spanish_indicators):
        print(f"✅ 스페인어 지표 발견")
        return True
    
    if any(indicator in content_lower for indicator in english_indicators):
        print(f"❌ 영어 지표 발견 (검증된 피드에서 예상치 못한 상황)")
        return False
    
    # 검증된 스페인어 피드이므로 기본적으로 True 반환
    print(f"✅ 검증된 스페인어 피드에서 온 콘텐츠로 간주")
    return True

def extract_grammar_points_from_content(content, difficulty="B2"):
    """
    기사 내용에서 레벨별 문법 포인트 추출 (LLM 전용)
    """
    if not content:
        return []
    
    if not LLM_AVAILABLE or not os.environ.get('OPENAI_API_KEY'):
        print("⚠️ LLM 분석기가 필요합니다. OPENAI_API_KEY를 설정해주세요.")
        return []
    
    try:
        analyzer = SpanishLLMAnalyzer()
        return analyzer.analyze_article_grammar(content, difficulty)
    except Exception as e:
        print(f"LLM 문법 분석 오류: {e}")
        return []

def extract_vocabulary_expressions_from_transcript(transcript, difficulty="B2"):
    """
    팟캐스트 transcript에서 레벨별 구어체 표현 추출 (LLM 전용)
    """
    if not transcript:
        print("⚠️ transcript 내용이 비어있습니다.")
        return []
    
    if not LLM_AVAILABLE or not os.environ.get('OPENAI_API_KEY'):
        print("⚠️ LLM 분석기가 필요합니다. OPENAI_API_KEY를 설정해주세요.")
        return []
    
    try:
        print(f"\n  🔍 구어체 표현 분석 시작")
        print(f"  📊 입력 콘텐츠 길이: {len(transcript)}자")
        print(f"  🎯 분석 난이도: {difficulty}")
        print(f"  📄 입력 콘텐츠 미리보기: {transcript[:200].replace(chr(10), ' ').strip()}...")
        
        analyzer = SpanishLLMAnalyzer()
        result = analyzer.analyze_podcast_colloquialisms(transcript, difficulty)
        
        print(f"\n  📊 구어체 분석 최종 결과:")
        print(f"  ✅ 추출된 구어체 표현: {len(result)}개")
        
        if result:
            print(f"  🎯 발견된 구어체 표현들:")
            for i, expr in enumerate(result, 1):
                print(f"     {i}. {expr}")
            return result
        else:
            print(f"  📝 구어체 표현이 0개인 최종 판정:")
            print(f"     • 텍스트가 정식/공식적 언어로 구성됨")
            print(f"     • 대화체나 비공식적 표현이 실제로 없음")
            print(f"     • 메타데이터 위주의 내용일 가능성")
            return []
    except Exception as e:
        print(f"    ❌ LLM 구어체 표현 분석 오류: {e}")
        print(f"    📝 오류 상세: {traceback.format_exc()}")
        return []

def get_podcast_transcript_or_content(episode_url, episode_title):
    """
    팟캐스트 에피소드 URL에서 transcript나 상세 내용을 가져오기
    원본 URL을 우선적으로 확인 후 다른 소스 검색
    """
    print(f"    🔍 콘텐츠 검색 시작 - 원본 URL 우선 확인...")
    
    # 전역 변수 초기화
    globals()['found_apple_url'] = None
    
    # 1. 먼저 원본 URL에서 transcript 시도 (가장 우선순위)
    print(f"    📄 원본 URL에서 transcript 추출 시도: {episode_url}")
    content = try_extract_from_url(episode_url, episode_title)
    if content:
        print(f"    ✅ 원본 URL에서 콘텐츠 발견! (길이: {len(content)}자)")
        return content
    
    print(f"    ⚠️ 원본 URL에서 콘텐츠를 찾지 못함 - 다른 소스 검색 시작...")
    
    # 2. Radio Ambulante 공식 웹사이트에서 검색
    if 'Radio Ambulante' in episode_title or 'radioambulante.org' in episode_url:
        print(f"    🌐 Radio Ambulante 공식 웹사이트에서 검색...")
        content = search_radio_ambulante_website(episode_title)
        if content:
            return content
    
    # 3. YouTube에서 같은 에피소드 검색
    print(f"    📺 YouTube에서 자막 검색...")
    content = search_youtube_transcript(episode_title)
    if content:
        return content
    
    # 4. 팟캐스트 공식 웹사이트에서 쇼노트 검색
    print(f"    📝 팟캐스트 공식 웹사이트에서 쇼노트 검색...")
    content = search_podcast_website(episode_title, episode_url)
    if content:
        return content
    
    # 5. Apple Podcasts에서 에피소드 설명 검색
    print(f"    🍎 Apple Podcasts에서 에피소드 설명 검색...")
    content = search_apple_podcast_description(episode_title)
    if content:
        return content
    
    print(f"    ❌ 모든 소스에서 콘텐츠를 찾지 못함")
    return ""

def get_found_apple_url():
    """Apple Podcast 검색에서 발견된 URL 반환"""
    return globals().get('found_apple_url', None)

def try_extract_from_url(episode_url, episode_title):
    """원본 URL에서 transcript 추출 시도"""
    try:
        print(f"    📄 {episode_url} 접속 중...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(episode_url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"    ❌ HTTP 오류: {response.status_code}")
            return ""
        
        print(f"    📋 페이지 파싱 중...")
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 범용 transcript 추출 로직
        print(f"    🔍 페이지에서 transcript/콘텐츠 추출 중...")
        
        # 1. transcript 관련 버튼이나 링크에서 실제 transcript URL 찾기
        print(f"    🔍 transcript 버튼/링크에서 URL 추출 시도...")
        transcript_buttons = soup.find_all(['a', 'button'], string=re.compile(r'(transcript|transcripción|ver transcripción)', re.IGNORECASE))
        for button in transcript_buttons:
            href = button.get('href')
            onclick = button.get('onclick', '')
            data_url = button.get('data-url', '')
            
            # 가능한 transcript URL들
            possible_urls = []
            if href and not href.startswith('#'):
                from urllib.parse import urljoin
                # 상대 URL을 절대 URL로 변환
                absolute_url = urljoin(episode_url, href)
                possible_urls.append(absolute_url)
                print(f"    🔗 transcript 링크 발견: {href} → {absolute_url}")
            
            if data_url:
                from urllib.parse import urljoin
                absolute_data_url = urljoin(episode_url, data_url)
                possible_urls.append(absolute_data_url)
                print(f"    🔗 data-url 발견: {data_url} → {absolute_data_url}")
            
            # onclick에서 URL 추출
            if onclick:
                url_match = re.search(r'["\']([^"\']*transcript[^"\']*)["\']', onclick)
                if url_match:
                    onclick_url = url_match.group(1)
                    from urllib.parse import urljoin
                    absolute_onclick_url = urljoin(episode_url, onclick_url)
                    possible_urls.append(absolute_onclick_url)
                    print(f"    🔗 onclick URL 발견: {onclick_url} → {absolute_onclick_url}")
            
            # 추출된 URL들 시도
            for transcript_url in possible_urls:
                try:
                    print(f"    🔍 transcript URL 시도: {transcript_url}")
                    transcript_response = requests.get(transcript_url, headers=headers, timeout=10)
                    if transcript_response.status_code == 200:
                        transcript_content = transcript_response.text.strip()
                        # HTML인 경우 텍스트만 추출
                        if transcript_content.startswith('<'):
                            transcript_soup = BeautifulSoup(transcript_content, 'html.parser')
                            transcript_content = transcript_soup.get_text().strip()
                        
                        if len(transcript_content) > 100:
                            print(f"    ✅ transcript URL에서 콘텐츠 발견! (길이: {len(transcript_content)}자)")
                            return transcript_content[:3000]
                        else:
                            print(f"    ⚠️ transcript 내용이 너무 짧음 (길이: {len(transcript_content)}자)")
                    else:
                        print(f"    ❌ HTTP 오류: {transcript_response.status_code}")
                except Exception as e:
                    print(f"    ❌ transcript URL 접근 실패: {e}")
                    continue
        
        # 2. 페이지 소스에서 JavaScript 변수나 JSON 데이터로 embedded된 transcript 찾기
        print(f"    🔍 JavaScript/JSON 데이터에서 transcript 검색...")
        page_content = response.text
        
        # JavaScript 변수에서 transcript 추출 패턴들
        js_patterns = [
            r'transcript["\']?\s*:\s*["\']([^"\']{200,})["\']',
            r'transcription["\']?\s*:\s*["\']([^"\']{200,})["\']',
            r'content["\']?\s*:\s*["\']([^"\']{200,})["\']',
            r'text["\']?\s*:\s*["\']([^"\']{200,})["\']'
        ]
        
        for pattern in js_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # HTML 엔티티 디코딩 및 정리
                clean_text = match.replace('\\n', '\n').replace('\\t', ' ').replace('\\"', '"')
                if len(clean_text) > 200 and any(word in clean_text.lower() for word in ['el ', 'la ', 'es ', 'que ', 'con ']):
                    print(f"    ✅ JavaScript 데이터에서 스페인어 콘텐츠 발견! (길이: {len(clean_text)}자)")
                    return clean_text[:3000]
        
        # 3. 포괄적인 CSS 셀렉터로 콘텐츠 추출
        print(f"    🔍 CSS 셀렉터로 콘텐츠 추출...")
        
        # transcript 관련 셀렉터들 (우선순위 높음)
        priority_selectors = [
            '.transcript', '.transcription', '.episode-transcript', '.transcript-content',
            '#transcript', '#transcription', '[data-transcript]', '[class*="transcript"]'
        ]
        
        # 일반적인 콘텐츠 셀렉터들
        content_selectors = [
            '.episode-content', '.episode-description', '.show-notes', '.episode-notes',
            '.post-content', '.entry-content', '.content', '.description', '.summary',
            'article', 'main', '.story-content', '.episode-body'
        ]
        
        # 우선순위 셀렉터들 먼저 시도
        for selector in priority_selectors:
            elements = soup.select(selector)
            if elements:
                content = ' '.join([elem.get_text().strip() for elem in elements])
                if len(content) > 100:
                    print(f"    ✅ 우선순위 셀렉터에서 콘텐츠 발견! (셀렉터: {selector}, 길이: {len(content)}자)")
                    return content[:3000]
        
        # 일반 콘텐츠 셀렉터들 시도
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                content = ' '.join([elem.get_text().strip() for elem in elements])
                if len(content) > 200:  # 일반 콘텐츠는 더 긴 텍스트만 허용
                    print(f"    ✅ 일반 셀렉터에서 콘텐츠 발견! (셀렉터: {selector}, 길이: {len(content)}자)")
                    return content[:3000]
        
        # 4. 페이지의 모든 문단에서 스페인어 콘텐츠 필터링
        print(f"    🔍 페이지 전체에서 스페인어 콘텐츠 검색...")
        all_paragraphs = soup.find_all('p')
        spanish_content = []
        
        for p in all_paragraphs:
            text = p.get_text().strip()
            if len(text) > 30:  # 너무 짧은 텍스트 제외
                # 스페인어 패턴 확인 (더 포괄적)
                spanish_patterns = ['el ', 'la ', 'es ', 'que ', 'con ', 'por ', 'para ', 'de ', 'en ', 'un ', 'una ']
                if any(pattern in text.lower() for pattern in spanish_patterns):
                    # 네비게이션이나 메뉴 텍스트 제외
                    if not any(nav_word in text.lower() for nav_word in ['inicio', 'contacto', 'sobre', 'menu', 'copyright', '©']):
                        spanish_content.append(text)
        
        if spanish_content:
            content = ' '.join(spanish_content)
            if len(content) > 200:
                print(f"    ✅ 페이지에서 스페인어 콘텐츠 발견! (길이: {len(content)}자)")
                return content[:3000]
        
        print(f"    ❌ 원본 URL에서 충분한 콘텐츠를 찾지 못함")
        return ""
        
    except Exception as e:
        print(f"    ❌ 원본 URL transcript 추출 오류: {e}")
        return ""

def search_radio_ambulante_website(episode_title):
    """Radio Ambulante 공식 웹사이트에서 에피소드 검색"""
    try:
        # 에피소드 제목에서 슬러그 생성
        import re
        title_clean = re.sub(r'[^\w\s-]', '', episode_title.lower())
        slug = re.sub(r'[-\s]+', '-', title_clean).strip('-')
        
        # 여러 가능한 URL 패턴 시도
        possible_urls = [
            f"https://radioambulante.org/audio/{slug}",
            f"https://radioambulante.org/episodes/{slug}",
            f"https://radioambulante.org/podcast/{slug}"
        ]
        
        for url in possible_urls:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Radio Ambulante 특화 셀렉터들
                    selectors = [
                        '.episode-transcript',
                        '.transcript-content',
                        '.episode-content p',
                        '.story-content p',
                        '.post-content p',
                        '.entry-content p'
                    ]
                    
                    for selector in selectors:
                        elements = soup.select(selector)
                        if elements:
                            content = ' '.join([elem.get_text().strip() for elem in elements])
                            if len(content) > 200:
                                print(f"    ✅ Radio Ambulante 웹사이트에서 콘텐츠 발견 (길이: {len(content)}자)")
                                return content[:3000]
                            
            except Exception as e:
                continue
        
        return ""
        
    except Exception as e:
        print(f"    ❌ Radio Ambulante 웹사이트 검색 오류: {e}")
        return ""

def search_youtube_transcript(episode_title):
    """YouTube에서 같은 에피소드의 자막 검색"""
    try:
        # YouTube 검색 URL 생성
        search_query = f"{episode_title} transcript"
        search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(search_query)}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code == 200:
            # YouTube 검색 결과에서 비디오 ID 추출
            video_id_pattern = r'"videoId":"([^"]+)"'
            video_ids = re.findall(video_id_pattern, response.text)
            
            if video_ids:
                # 첫 번째 비디오의 설명 가져오기 시도
                video_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
                video_response = requests.get(video_url, headers=headers, timeout=10)
                
                if video_response.status_code == 200:
                    soup = BeautifulSoup(video_response.content, 'html.parser')
                    
                    # 비디오 설명 추출
                    description_selectors = [
                        '[data-content]',
                        '.description',
                        '#description'
                    ]
                    
                    for selector in description_selectors:
                        elements = soup.select(selector)
                        if elements:
                            content = ' '.join([elem.get_text().strip() for elem in elements])
                            if len(content) > 200:
                                print(f"    ✅ YouTube 에피소드 설명 발견 (길이: {len(content)}자)")
                                return content[:3000]
        
        return ""
        
    except Exception as e:
        print(f"    ❌ YouTube 검색 오류: {e}")
        return ""

def search_podcast_website(episode_title, episode_url):
    """팟캐스트 공식 웹사이트에서 쇼노트 검색"""
    try:
        # URL에서 도메인 추출
        from urllib.parse import urlparse
        parsed_url = urlparse(episode_url)
        domain = parsed_url.netloc
        
        # 도메인별 특화 검색
        if 'spanishpodcast.org' in domain:
            return search_spanishpodcast_website(episode_title)
        elif 'espanolistos.com' in domain:
            return search_espanolistos_website(episode_title)
        else:
            # 일반적인 팟캐스트 웹사이트 검색
            return search_general_podcast_website(episode_url)
        
    except Exception as e:
        print(f"    ❌ 팟캐스트 웹사이트 검색 오류: {e}")
        return ""

def search_spanishpodcast_website(episode_title):
    """SpanishPodcast 웹사이트에서 쇼노트 검색"""
    try:
        # SpanishPodcast 웹사이트 검색 로직
        base_url = "https://www.spanishpodcast.org"
        
        # 에피소드 번호 추출
        episode_num = extract_episode_number(episode_title)
        if episode_num:
            episode_url = f"{base_url}/podcasts/{episode_num}.html"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(episode_url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # SpanishPodcast 특화 셀렉터들
                selectors = [
                    '.episode-content',
                    '.show-notes',
                    '.description',
                    'article p',
                    '.content p'
                ]
                
                for selector in selectors:
                    elements = soup.select(selector)
                    if elements:
                        content = ' '.join([elem.get_text().strip() for elem in elements])
                        if len(content) > 200:
                            print(f"    ✅ SpanishPodcast 웹사이트에서 쇼노트 발견 (길이: {len(content)}자)")
                            return content[:3000]
        
        return ""
        
    except Exception as e:
        print(f"    ❌ SpanishPodcast 웹사이트 검색 오류: {e}")
        return ""

def search_espanolistos_website(episode_title):
    """Españolistos 웹사이트에서 쇼노트 검색"""
    try:
        # Españolistos 웹사이트는 Spotify 기반이므로 다른 접근 필요
        # 일반적인 검색 시도
        search_query = f"site:espanolistos.com {episode_title}"
        
        # 구글 검색 시뮬레이션은 복잡하므로 일단 패스
        return ""
        
    except Exception as e:
        print(f"    ❌ Españolistos 웹사이트 검색 오류: {e}")
        return ""

def search_general_podcast_website(episode_url):
    """일반적인 팟캐스트 웹사이트에서 쇼노트 검색"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(episode_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 일반적인 쇼노트 셀렉터들
            selectors = [
                '.show-notes',
                '.episode-notes',
                '.description',
                '.summary',
                '.content',
                'article',
                '.post-content'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    content = ' '.join([elem.get_text().strip() for elem in elements])
                    if len(content) > 200:
                        print(f"    ✅ 일반 팟캐스트 웹사이트에서 쇼노트 발견 (길이: {len(content)}자)")
                        return content[:3000]
        
        return ""
        
    except Exception as e:
        print(f"    ❌ 일반 팟캐스트 웹사이트 검색 오류: {e}")
        return ""

def search_apple_podcast_description(episode_title):
    """Apple Podcasts에서 에피소드 설명 검색하고 URL도 반환"""
    try:
        # iTunes Search API를 사용하여 에피소드 설명 가져오기
        search_term = episode_title
        encoded_term = urllib.parse.quote(search_term)
        search_url = f"https://itunes.apple.com/search?term={encoded_term}&media=podcast&entity=podcastEpisode&limit=5"
        
        print(f"    🔍 iTunes Search API 호출: {search_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            print(f"    📊 iTunes Search 결과: {len(results)}개 에피소드 발견")
            
            for i, result in enumerate(results, 1):
                result_title = result.get('trackName', '').lower()
                track_view_url = result.get('trackViewUrl', '')
                print(f"    📺 결과 {i}: {result.get('trackName', 'N/A')}")
                
                if any(word in result_title for word in episode_title.lower().split() if len(word) > 3):
                    description = result.get('description', '') or result.get('longDescription', '')
                    if description and len(description) > 200:
                        print(f"    ✅ Apple Podcasts에서 에피소드 설명 발견 (길이: {len(description)}자)")
                        print(f"    📄 설명 미리보기: {description[:150]}...")
                        
                        # URL도 함께 저장 (전역 변수나 다른 방법으로)
                        if track_view_url:
                            print(f"    🔗 해당 에피소드 URL: {track_view_url}")
                            # 전역 변수에 저장하여 나중에 사용
                            globals()['found_apple_url'] = track_view_url
                        
                        return description[:3000]
                    else:
                        print(f"    ⚠️ 설명이 너무 짧음 (길이: {len(description) if description else 0}자)")
        else:
            print(f"    ❌ iTunes Search API 호출 실패: {response.status_code}")
        
        return ""
        
    except Exception as e:
        print(f"    ❌ Apple Podcasts 검색 오류: {e}")
        return ""

def main():
    # 환경변수에서 설정값 가져오기
    reading_source = os.environ.get('READING_SOURCE', '')
    preset_difficulty = os.environ.get('READING_DIFFICULTY', 'B2')  # 기본값으로만 사용
    podcast_rss = os.environ.get('PODCAST_RSS', '')
    podcast_name = os.environ.get('PODCAST_NAME', '')
    weekday_name = os.environ.get('WEEKDAY_NAME', '')
    podcast_apple_base = os.environ.get('PODCAST_APPLE_BASE', '')
    force_alternative = os.environ.get('FORCE_ALTERNATIVE', 'false').lower() == 'true'
    
    article_data = None
    podcast_data = None  # 명시적으로 None으로 초기화

    print(f"=== 학습 자료 수집 시작 ===")
    print(f"독해 소스: {reading_source}")
    print(f"팟캐스트: {podcast_name}")
    print(f"팟캐스트 RSS: {podcast_rss}")
    print(f"요일: {weekday_name}")
    print(f"대안 모드: {force_alternative}")
    print(f"====================")
    
    # 🎯 검증된 스페인어 팟캐스트 피드 목록 (실제 테스트 완료)
    verified_spanish_feeds = {
        "SpanishPodcast": {
            "rss": "https://feeds.feedburner.com/SpanishPodcast",
            "apple": "https://podcasts.apple.com/us/podcast/spanishpodcast/id70077665",
            "region": "스페인",
            "status": "✅ 작동 확인됨"
        },
        "Hoy Hablamos": {
            "rss": "https://www.hoyhablamos.com/feed/podcast/",
            "apple": "https://podcasts.apple.com/es/podcast/hoy-hablamos/id1455031513",
            "region": "스페인",
            "status": "✅ 작동 확인됨"
        }
        # 참고: 다음 피드들은 현재 문제가 있어서 제외됨
        # - Radio Ambulante (https://feeds.simplecast.com/54nAGcIl): 영어 "The Daily" 반환
        # - Españolistos (https://creators.spotify.com/pod/show/espanolistos/rss): HTML 페이지 반환
    }
    
    # 요일별 검증된 스페인어 피드 할당 (작동하는 피드들만)
    weekday_spanish_feeds = {
        "월요일": "SpanishPodcast",
        "화요일": "Hoy Hablamos", 
        "수요일": "SpanishPodcast",  # 원래 Españolistos였으나 작동하지 않아서 SpanishPodcast로 변경
        "목요일": "Hoy Hablamos",    # 원래 Radio Ambulante였으나 작동하지 않아서 Hoy Hablamos로 변경
        "금요일": "SpanishPodcast"
    }
    
    # 🔒 무조건 검증된 스페인어 피드만 사용 (환경변수 무시)
    selected_podcast = weekday_spanish_feeds.get(weekday_name, "SpanishPodcast")
    podcast_info = verified_spanish_feeds[selected_podcast]
    
    podcast_rss = podcast_info["rss"]
    podcast_name = selected_podcast
    podcast_apple_base = podcast_info["apple"]
    
    print(f"🎯 검증된 스페인어 팟캐스트 강제 선택:")
    print(f"   요일: {weekday_name}")
    print(f"   팟캐스트: {podcast_name} ({podcast_info['region']})")
    print(f"   RSS: {podcast_rss}")
    print(f"   Apple: {podcast_apple_base}")
    print(f"   ✅ 100% 스페인어 콘텐츠 보장됨")

    # 기사 수집 및 실제 내용 분석
    try:
        if reading_source == "20minutos":
            feed_url = "https://www.20minutos.es/rss/"
        elif "El País" in reading_source:
            if "사설" in reading_source:
                feed_url = "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/opinion"
            else:
                feed_url = "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada"
        elif reading_source == "El Mundo":
            feed_url = "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml"
        elif reading_source == "ABC":
            feed_url = "https://www.abc.es/rss/feeds/abc_EspanaEspana.xml"
        else:
            # 기본값
            feed_url = "https://www.20minutos.es/rss/"
        
        print(f"RSS 피드에서 기사 정보 수집 중: {feed_url}")
        feed = feedparser.parse(feed_url)
        
        if feed.entries:
            # 대안 모드에서는 여러 기사 중에서 선택
            entry_index = 0
            if force_alternative:
                # 대안 모드에서는 두 번째 또는 세 번째 기사 시도
                import random
                entry_index = min(random.randint(1, 3), len(feed.entries) - 1)
                print(f"대안 모드: {entry_index + 1}번째 기사 선택")
            
            latest = feed.entries[entry_index]
            article_url = latest.link
            clean_title = latest.title.replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            
            print(f"기사 URL 접속 중: {article_url}")
            # 실제 기사 내용 가져오기
            article_content = get_article_content(article_url)
            
            if article_content:
                print(f"기사 내용 분석 중... (내용 길이: {len(article_content)}자)")
                
                # 동적 난이도 분석
                analyzed_difficulty = analyze_text_difficulty(article_content)
                print(f"분석된 난이도: {analyzed_difficulty}")
                
                # 카테고리 분류
                category = extract_category_from_content(clean_title, article_content)
                
                print(f"분류된 카테고리: {category}")
                
                article_data = {
                    'title': clean_title,
                    'url': article_url,
                    'published': latest.get('published', ''),
                    'category': category,
                    'difficulty': analyzed_difficulty,  # 동적으로 분석된 난이도 사용
                    'content_preview': article_content[:200] + "..." if len(article_content) > 200 else article_content
                }
            else:
                print("기사 내용을 가져올 수 없어 RSS 요약 사용")
                # 내용을 가져올 수 없으면 RSS 요약 사용
                summary = latest.get('summary', '')
                analyzed_difficulty = analyze_text_difficulty(summary) if summary else preset_difficulty
                category = extract_category_from_content(clean_title, summary)
                
                article_data = {
                    'title': clean_title,
                    'url': article_url,
                    'published': latest.get('published', ''),
                    'category': category,
                    'difficulty': analyzed_difficulty,
                    'content_preview': summary
                }
                
        else:
            print("RSS 피드에서 기사를 찾을 수 없음")
            
    except Exception as e:
        print(f"기사 수집 오류: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")

    # 팟캐스트 에피소드 수집
    try:
        print(f"팟캐스트 RSS 피드 수집 중: {podcast_rss}")
        feed = feedparser.parse(podcast_rss)
        
        print(f"피드 파싱 결과:")
        print(f"- 피드 제목: {feed.feed.get('title', '제목 없음')}")
        print(f"- 에피소드 개수: {len(feed.entries)}")
        print(f"- 피드 상태: {getattr(feed, 'status', 'N/A')}")
        
        if hasattr(feed, 'bozo') and feed.bozo:
            print(f"- RSS 피드 파싱 경고: {getattr(feed, 'bozo_exception', 'Unknown')}")
            
        # 피드 상태가 404이거나 에피소드가 없으면 즉시 백업 피드 시도
        if (hasattr(feed, 'status') and feed.status == 404) or len(feed.entries) == 0:
            print(f"⚠️  메인 RSS 피드 사용 불가 (상태: {getattr(feed, 'status', 'N/A')}, 에피소드: {len(feed.entries)})")
            print("🔄 다른 검증된 스페인어 피드들을 시도합니다...")
            
            # 현재 선택된 피드를 제외한 다른 검증된 스페인어 피드들
            alternative_feeds = []
            for name, info in verified_spanish_feeds.items():
                if name != selected_podcast:  # 현재 피드 제외
                    alternative_feeds.append((info["rss"], name, info["apple"]))
            
            # 백업 피드들 시도
            for backup_url, backup_podcast_name, backup_apple_base in alternative_feeds:
                try:
                    print(f"🔄 백업 피드 시도: {backup_podcast_name}")
                    backup_feed = feedparser.parse(backup_url)
                    
                    if backup_feed.entries:
                        print(f"✅ {backup_podcast_name}에서 에피소드 발견! (개수: {len(backup_feed.entries)})")
                        
                        # 백업 피드에서 최근 에피소드 선택 (검증된 스페인어 피드이므로 언어 확인 불필요)
                        latest = backup_feed.entries[0]
                        
                        print(f"백업 피드에서 선택된 에피소드:")
                        print(f"  제목: {latest.title}")
                        print(f"  RSS URL: {latest.link}")
                        
                        episode_number = extract_episode_number(latest.title)
                        duration = extract_duration_from_feed(latest)
                        topic = extract_topic_keywords(latest.title, latest.get('summary', ''))
                        
                        episode_link = latest.link
                        
                        # Radio Ambulante인 경우 실제 웹사이트 URL 시도
                        if 'Radio Ambulante' in backup_podcast_name:
                            radio_ambulante_url = extract_radio_ambulante_url(latest)
                            if radio_ambulante_url:
                                print(f"  Radio Ambulante 웹사이트 URL: {radio_ambulante_url}")
                                episode_link = radio_ambulante_url
                            else:
                                print(f"  Radio Ambulante 웹사이트 URL 추출 실패, RSS URL 사용")
                        
                        # Apple Podcasts 링크 생성
                        apple_link = generate_apple_podcast_link(backup_podcast_name, backup_apple_base, episode_link, episode_number, latest.title)
                        
                        # 최종 URL 결정
                        final_episode_url = episode_link
                        if 'Radio Ambulante' in backup_podcast_name:
                            if apple_link != backup_apple_base and validate_url(apple_link):
                                final_episode_url = apple_link
                            else:
                                final_episode_url = episode_link
                                apple_link = backup_apple_base
                        else:
                            if not validate_url(episode_link):
                                final_episode_url = apple_link if validate_url(apple_link) else backup_apple_base
                            if not validate_url(apple_link):
                                apple_link = backup_apple_base
                        
                        # 백업 피드 난이도 분석
                        backup_summary = latest.get('summary', '')
                        backup_difficulty = analyze_text_difficulty(backup_summary) if backup_summary else "B2"
                        
                        podcast_data = {
                            'title': latest.title,
                            'url': final_episode_url,
                            'apple_link': apple_link,
                            'published': latest.get('published', ''),
                            'duration': duration,
                            'episode_number': episode_number or 'N/A',
                            'topic': topic,
                            'podcast_name': f"{backup_podcast_name} (백업)",
                            'summary': latest.get('summary', '')[:200],
                            'difficulty': backup_difficulty
                        }
                        
                        print(f"✅ 백업 피드 성공! 사용된 피드: {backup_podcast_name}")
                        print(f"   에피소드: {latest.title}")
                        break
                    else:
                        print(f"🚫 {backup_podcast_name} 피드에서 에피소드를 찾을 수 없음")
                        continue
                except Exception as backup_e:
                    print(f"백업 피드 오류 ({backup_podcast_name}): {backup_e}")
                    continue
            
            # 모든 백업 피드에서도 중복이거나 실패한 경우 대안 팟캐스트 시도
            if not podcast_data:
                print(f"\n🔄 모든 백업 피드 실패. 대안 팟캐스트를 찾는 중...")
                current_weekday = datetime.now().weekday()
                alternatives = get_alternative_podcasts(current_weekday, podcast_name)
                alternative_podcast = try_alternative_podcast(alternatives, weekday_name)
                
                if alternative_podcast:
                    print(f"✅ 대안 팟캐스트에서 새로운 에피소드 발견!")
                    podcast_data = alternative_podcast
                else:
                    print(f"❌ 모든 대안에서도 새로운 에피소드를 찾지 못했습니다.")
        
        elif feed.entries:
            print(f"✅ 검증된 스페인어 피드에서 에피소드 선택 중...")
            
            # 대안 모드에서는 다른 에피소드 선택
            episode_index = 0
            if force_alternative and len(feed.entries) > 1:
                import random
                episode_index = min(random.randint(1, 3), len(feed.entries) - 1)
                print(f"🔄 대안 모드: {episode_index + 1}번째 에피소드 선택")
            
            latest = feed.entries[episode_index]
            print(f"선택된 에피소드: {latest.title}")
            print(f"- 링크: {latest.link}")
            print(f"- 발행일: {latest.get('published', 'N/A')}")
            
            episode_number = extract_episode_number(latest.title)
            duration = extract_duration_from_feed(latest)
            topic = extract_topic_keywords(latest.title, latest.get('summary', ''))
            
            episode_link = latest.link
            
            # Radio Ambulante인 경우 실제 웹사이트 URL 시도
            if 'Radio Ambulante' in podcast_name:
                radio_ambulante_url = extract_radio_ambulante_url(latest)
                if radio_ambulante_url:
                    print(f"  Radio Ambulante 웹사이트 URL: {radio_ambulante_url}")
                    episode_link = radio_ambulante_url
                else:
                    print(f"  Radio Ambulante 웹사이트 URL 추출 실패, RSS URL 사용")
            
            # Apple Podcasts 링크 생성
            apple_link = generate_apple_podcast_link(podcast_name, podcast_apple_base, episode_link, episode_number, latest.title)
            
            # 최종 URL 결정
            final_episode_url = episode_link
            if 'Radio Ambulante' in podcast_name:
                if apple_link != podcast_apple_base and validate_url(apple_link):
                    final_episode_url = apple_link
                else:
                    final_episode_url = episode_link
                    apple_link = podcast_apple_base
            else:
                if not validate_url(episode_link):
                    final_episode_url = apple_link if validate_url(apple_link) else podcast_apple_base
                if not validate_url(apple_link):
                    apple_link = podcast_apple_base
            
            # 팟캐스트 난이도 분석
            episode_summary = latest.get('summary', '')
            podcast_difficulty = analyze_text_difficulty(episode_summary) if episode_summary else "B2"
            
            podcast_data = {
                'title': latest.title,
                'url': final_episode_url,
                'apple_link': apple_link,
                'published': latest.get('published', ''),
                'duration': duration,
                'episode_number': episode_number or 'N/A',
                'topic': topic,
                'podcast_name': podcast_name,
                'summary': latest.get('summary', '')[:200],
                'difficulty': podcast_difficulty
            }
            
            print(f"✅ 메인 피드에서 에피소드 선택 완료!")
            
            # 대안 모드에서는 중복 체크를 건너뛰고 바로 진행
            if not force_alternative:
                print(f"✅ 일반 모드: 중복 체크는 create_notion_pages.py에서 수행됩니다.")
            else:
                print(f"🔄 대안 모드: 중복 체크를 건너뛰고 진행합니다.")
            
        else:
            print("메인 피드에 에피소드가 없음 - 이 경우는 위에서 처리됨")
            
    except Exception as e:
        print(f"팟캐스트 수집 오류: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")

    # 학습 자료 정보를 환경변수로 출력
    # 대안 모드에서는 GITHUB_OUTPUT이 없을 수 있으므로 조건부 처리
    if 'GITHUB_OUTPUT' in os.environ:
        try:
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                if article_data:
                    f.write(f"article_title={article_data['title']}\n")
                    f.write(f"article_url={article_data['url']}\n")
                    f.write(f"article_category={article_data['category']}\n")
                    f.write(f"article_difficulty={article_data['difficulty']}\n")  # 동적 난이도 출력
                    f.write(f"article_memo={create_detailed_memo('article', article_data, weekday_name)}\n")
                
                if podcast_data:
                    f.write(f"podcast_title={podcast_data['title']}\n")
                    f.write(f"podcast_url={podcast_data['url']}\n")
                    f.write(f"podcast_apple={podcast_data['apple_link']}\n")
                    f.write(f"podcast_duration={podcast_data['duration']}\n")
                    f.write(f"podcast_topic={podcast_data['topic']}\n")
                    f.write(f"podcast_memo={create_detailed_memo('podcast', podcast_data, weekday_name)}\n")
        except Exception as e:
            print(f"GitHub Output 파일 쓰기 오류: {e}")
    
    # 대안 모드에서는 표준 출력으로 환경변수 형태로 결과 출력
    if force_alternative or 'GITHUB_OUTPUT' not in os.environ:
        print("\n=== 수집된 자료 정보 (환경변수 형태) ===")
        if article_data:
            print(f'ARTICLE_TITLE="{article_data["title"]}"')
            print(f'ARTICLE_URL="{article_data["url"]}"')
            print(f'ARTICLE_CATEGORY="{article_data["category"]}"')
            print(f'ARTICLE_DIFFICULTY="{article_data["difficulty"]}"')
            print(f'ARTICLE_MEMO="{create_detailed_memo("article", article_data, weekday_name)}"')
        
        if podcast_data:
            print(f'PODCAST_TITLE="{podcast_data["title"]}"')
            print(f'PODCAST_URL="{podcast_data["url"]}"')
            print(f'PODCAST_APPLE="{podcast_data["apple_link"]}"')
            print(f'PODCAST_DURATION="{podcast_data["duration"]}"')
            print(f'PODCAST_TOPIC="{podcast_data["topic"]}"')
            print(f'PODCAST_MEMO="{create_detailed_memo("podcast", podcast_data, weekday_name)}"')
        print("=========================================")

    print("학습 자료 수집 완료!")
    if article_data:
        print(f"✅ 기사: {article_data['title']}")
        print(f"   카테고리: {article_data['category']}")
        print(f"   난이도: {article_data['difficulty']}")  # 동적 난이도 출력
    else:
        print(f"❌ 기사 수집 실패")
        
    if podcast_data:
        print(f"✅ 팟캐스트: {podcast_data['title']}")
        print(f"   주제: {podcast_data['topic']}")
        print(f"   재생시간: {podcast_data['duration']}")
    else:
        print(f"❌ 팟캐스트 수집 실패")
        print(f"   RSS URL: {podcast_rss}")
        print(f"   팟캐스트명: {podcast_name}")

if __name__ == "__main__":
    main()
