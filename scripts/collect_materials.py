#!/usr/bin/env python3
"""
Collect Spanish learning materials: articles and podcast episodes with content analysis.
"""
import os
import sys
import requests
import feedparser
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from spanish_vocabulary import search_vocabulary

def is_episode_recent(published_date, max_days_old=2):
    """에피소드가 최근 며칠 이내에 발행되었는지 확인"""
    try:
        if not published_date:
            return True  # 날짜 정보가 없으면 허용
        
        # feedparser가 파싱한 날짜를 datetime으로 변환
        if hasattr(published_date, 'tm_year'):  # struct_time 객체인 경우
            episode_date = datetime(*published_date[:6])
        elif isinstance(published_date, str):
            # 문자열인 경우 파싱 시도
            from email.utils import parsedate_tz
            import calendar
            parsed = parsedate_tz(published_date)
            if parsed:
                episode_date = datetime(*parsed[:6])
            else:
                return True  # 파싱 실패시 허용
        else:
            return True
        
        current_date = datetime.now()
        days_diff = (current_date - episode_date).days
        
        print(f"DEBUG: 에피소드 날짜 확인 - 발행일: {episode_date.strftime('%Y-%m-%d')}, 현재: {current_date.strftime('%Y-%m-%d')}, 차이: {days_diff}일")
        
        return days_diff <= max_days_old
        
    except Exception as e:
        print(f"날짜 확인 오류: {e}")
        return True  # 오류 시 허용

def is_duplicate_content(title, existing_titles=[]):
    """제목 중복 확인"""
    if not existing_titles:
        return False
    
    # 제목 정규화 (특수문자, 공백 제거)
    normalized_title = re.sub(r'[^\w\s]', '', title.lower()).strip()
    
    for existing_title in existing_titles:
        normalized_existing = re.sub(r'[^\w\s]', '', existing_title.lower()).strip()
        
        # 80% 이상 유사하면 중복으로 판단
        similarity = len(set(normalized_title.split()) & set(normalized_existing.split())) / max(len(normalized_title.split()), len(normalized_existing.split()))
        
        if similarity >= 0.8:
            print(f"DEBUG: 중복 콘텐츠 감지 - 기존: {existing_title}, 새로운: {title} (유사도: {similarity:.2f})")
            return True
    
    return False

def analyze_text_difficulty(content):
    """Analyze text difficulty and return appropriate CEFR level"""
    if not content:
        return "B2"  # 기본값
    
    # 텍스트 길이로 기본 판단
    word_count = len(content.split())
    sentence_count = len([s for s in content.split('.') if s.strip()])
    avg_sentence_length = word_count / max(sentence_count, 1)
    
    # 복잡한 문법 구조 확인 (가중치)
    complexity_score = 0
    
    # 접속법 (subjunctive) 패턴들
    subjunctive_patterns = [
        r'\b(sea|seas|seamos|sean)\b',  # ser 접속법
        r'\b(tenga|tengas|tengamos|tengan)\b',  # tener 접속법  
        r'\b(haga|hagas|hagamos|hagan)\b',  # hacer 접속법
        r'\b(vaya|vayas|vayamos|vayan)\b',  # ir 접속법
        r'\bque\s+\w+[ae]s?\b',  # que + 접속법 패턴
        r'\bsi\s+\w+[ai]era\b',  # si + 접속법 과거
        r'\bojalá\b',  # ojalá (접속법 신호)
        r'\bes\s+importante\s+que\b',  # 감정/의견 표현 + que
        r'\bespero\s+que\b',
        r'\bdudo\s+que\b'
    ]
    
    for pattern in subjunctive_patterns:
        complexity_score += len(re.findall(pattern, content, re.IGNORECASE))
    
    # 복잡한 시제들
    complex_tenses = [
        r'\b\w+ado\s+sido\b',  # 완료형
        r'\b\w+ido\s+sido\b',
        r'\bhabía\s+\w+[adi]o\b',  # 과거완료
        r'\bhabrá\s+\w+[adi]o\b',  # 미래완료
        r'\bestaba\s+\w+ndo\b',  # 과거진행
        r'\bestaría\s+\w+ndo\b'  # 조건법 진행
    ]
    
    for pattern in complex_tenses:
        complexity_score += len(re.findall(pattern, content, re.IGNORECASE))
    
    # 고급 어휘 (추상적, 학술적 어휘)
    advanced_vocab = [
        r'\b(perspectiva|análisis|consecuencia|implicación|estrategia)\b',
        r'\b(implementar|consolidar|optimizar|contextualizar)\b',
        r'\b(paradigma|metodología|epistemología|ontología)\b',
        r'\b(inherente|intrínseco|subyacente|tangible|intangible)\b',
        r'\b(heterogéneo|homogéneo|multifacético|polifacético)\b'
    ]
    
    for pattern in advanced_vocab:
        complexity_score += len(re.findall(pattern, content, re.IGNORECASE)) * 2  # 고급어휘는 가중치 2배
    
    # 복잡한 연결사들
    complex_connectors = [
        r'\bsin\s+embargo\b', r'\bno\s+obstante\b', r'\ba\s+pesar\s+de\b',
        r'\ben\s+cuanto\s+a\b', r'\brespecto\s+a\b', r'\bcon\s+respecto\s+a\b',
        r'\bpor\s+consiguiente\b', r'\bpor\s+ende\b', r'\basimismo\b',
        r'\bademás\s+de\b', r'\baparte\s+de\b', r'\bexcepto\b', r'\bsalvo\b'
    ]
    
    for pattern in complex_connectors:
        complexity_score += len(re.findall(pattern, content, re.IGNORECASE))
    
    # 수동형
    passive_patterns = [
        r'\bfue\s+\w+[adi]o\b', r'\bfueron\s+\w+[adi]os\b',
        r'\bes\s+\w+[adi]o\b', r'\bson\s+\w+[adi]os\b',
        r'\bserá\s+\w+[adi]o\b', r'\bserían\s+\w+[adi]os\b'
    ]
    
    for pattern in passive_patterns:
        complexity_score += len(re.findall(pattern, content, re.IGNORECASE))
    
    # 정규화된 복잡도 점수 계산
    normalized_score = complexity_score / max(word_count / 100, 1)  # 100단어당 복잡도
    
    print(f"DEBUG: 난이도 분석 - 단어수: {word_count}, 복잡도 점수: {complexity_score}, 정규화 점수: {normalized_score:.2f}")
    
    # 난이도 판정
    if normalized_score >= 3.0 or avg_sentence_length > 25:
        return "C1"
    elif normalized_score >= 1.5 or avg_sentence_length > 20:
        return "B2+"
    elif normalized_score >= 0.8:
        return "B2"
    else:
        return "B1+"

def search_apple_podcasts_episode(podcast_name, episode_title, apple_base):
    """Search for exact episode URL using Apple iTunes Search API"""
    try:
        import urllib.parse
        
        # Radio Ambulante의 정확한 iTunes ID
        if 'Radio Ambulante' in podcast_name:
            podcast_id = "527614348"
        else:
            # 다른 팟캐스트의 경우 기본값 반환
            return apple_base
        
        # 검색어를 여러 방식으로 시도
        search_terms = []
        
        # 1. 전체 제목으로 검색
        search_terms.append(episode_title)
        
        # 2. "The Network:" 부분만으로 검색 (Radio Ambulante 시리즈)
        if ':' in episode_title:
            main_part = episode_title.split(':')[0].strip()
            search_terms.append(main_part)
            
            # 부제목 부분도 추가
            subtitle = episode_title.split(':', 1)[1].strip()
            search_terms.append(subtitle)
        
        # 3. Radio Ambulante + 키워드 조합
        keywords = episode_title.lower().split()
        important_words = [w for w in keywords if len(w) > 3 and w not in ['the', 'and', 'of', 'in', 'to', 'for']]
        if important_words:
            search_terms.append(f"Radio Ambulante {' '.join(important_words[:2])}")
        
        print(f"Apple 검색어들: {search_terms}")
        
        for search_term in search_terms:
            encoded_term = urllib.parse.quote(search_term)
            search_url = f"https://itunes.apple.com/search?term={encoded_term}&media=podcast&entity=podcastEpisode&limit=50"
            
            print(f"Apple iTunes Search API 호출: {search_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                print(f"iTunes 검색 결과 ({search_term}): {len(results)}개 에피소드 발견")
                
                # 검색 결과에서 Radio Ambulante 에피소드 찾기
                for result in results:
                    collection_name = result.get('collectionName', '').lower()
                    track_name = result.get('trackName', '')
                    
                    print(f"  검토 중: {track_name} (컬렉션: {collection_name})")
                    
                    # Radio Ambulante 팟캐스트인지 확인
                    if 'radio ambulante' in collection_name:
                        # 제목 유사도 확인 - 더 관대한 매칭
                        title_words = episode_title.lower().split()
                        track_words = track_name.lower().split()
                        
                        # 주요 단어가 포함되어 있는지 확인
                        common_words = set(title_words) & set(track_words)
                        if len(common_words) >= 2 or any(word in track_name.lower() for word in title_words if len(word) > 4):
                            episode_url = result.get('episodeUrl')
                            track_id = result.get('trackId')
                            
                            if episode_url:
                                print(f"✅ Apple Podcasts에서 에피소드 발견: {track_name}")
                                print(f"   Direct URL: {episode_url}")
                                return episode_url
                            elif track_id:
                                apple_url = f"https://podcasts.apple.com/kr/podcast/radio-ambulante/id{podcast_id}?i={track_id}"
                                print(f"✅ Apple Podcasts에서 에피소드 발견: {track_name}")
                                print(f"   Track URL: {apple_url}")
                                return apple_url
                
            else:
                print(f"iTunes Search API 호출 실패: {response.status_code}")
                
        print(f"❌ Apple Podcasts에서 정확한 에피소드를 찾지 못함")
        # 정확한 에피소드를 찾지 못했으면 메인 팟캐스트 페이지 반환
        return apple_base
        
    except Exception as e:
        print(f"Apple Podcasts 검색 오류: {e}")
        return apple_base

def generate_apple_podcast_link(podcast_name, apple_base, episode_link, episode_number, episode_title=""):
    """Generate optimized Apple Podcasts link by podcast type"""
    
    # 팟캐스트별 링크 생성 전략
    if 'Radio Ambulante' in podcast_name or 'npr.org' in episode_link:
        # Radio Ambulante는 에피소드별 직접 링크 생성 시도
        if episode_link and 'radioambulante.org' in episode_link:
            # 원본 에피소드 링크가 있으면 그것을 우선 사용
            return episode_link
        else:
            # Apple iTunes Search API를 사용해서 정확한 에피소드 찾기
            if episode_title:
                apple_url = search_apple_podcasts_episode(podcast_name, episode_title, apple_base)
                # 정확한 에피소드를 찾았을 때만 Apple URL 사용 (apple_base와 다른 경우)
                if apple_url != apple_base and validate_url(apple_url):
                    print(f"✅ Apple Podcasts에서 정확한 에피소드 링크 찾음: {apple_url}")
                    return apple_url
                else:
                    print(f"❌ Apple Podcasts에서 정확한 에피소드를 찾지 못함, 에피소드 URL 사용")
                    # Apple에서 찾지 못했으면 원본 에피소드 URL 사용
                    return episode_link
            
            # 에피소드 제목이 없으면 원본 링크 사용
            print(f"❌ 에피소드 제목이 없어 Apple 검색 불가, 에피소드 URL 사용")
            return episode_link

    elif 'Hoy Hablamos' in podcast_name:
        # Hoy Hablamos는 에피소드 번호 기반으로 링크 생성
        if episode_number and episode_number != 'N/A':
            try:
                # 에피소드 번호를 숫자로 변환
                ep_num = int(episode_number)
                return f"{apple_base}?i=1000{ep_num:06d}"  # Apple의 에피소드 ID 패턴
            except:
                pass
        return apple_base
    elif 'SpanishWithVicente' in podcast_name:
        # SpanishWithVicente는 에피소드 번호가 있으면 추가
        if episode_number and episode_number != 'N/A':
            return f"{apple_base}?i={episode_number}"
        else:
            return apple_base
    elif 'DELE' in podcast_name:
        # DELE Podcast는 메인 링크 사용
        return apple_base
    else:
        # 기본 전략: 에피소드 번호가 있으면 추가
        if episode_number and episode_number != 'N/A':
            return f"{apple_base}?i={episode_number}"
        else:
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

def extract_vocabulary_from_content(content, difficulty="B2"):
    """Extract vocabulary from article content based on difficulty level"""
    if not content:
        print("DEBUG: 내용이 없어서 어휘 추출 불가")
        return []
    
    print(f"DEBUG: 어휘 추출 중... 내용 길이: {len(content)}, 난이도: {difficulty}")
    print(f"DEBUG: 내용 미리보기: {content[:200]}...")
    
    # 새로운 어휘 모듈 사용
    found_vocabulary = search_vocabulary(content, difficulty, max_results=8)
    
    print(f"DEBUG: 총 추출된 어휘 개수: {len(found_vocabulary)}")
    for vocab in found_vocabulary:
        print(f"DEBUG: 찾은 어휘 - {vocab}")
    
    return found_vocabulary

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
        vocabulary = data.get('vocabulary', [])
        difficulty = data.get('difficulty', 'B2')  # 동적으로 분석된 난이도 사용
        
        print(f"DEBUG: 메모 생성 - 카테고리: {category}, 난이도: {difficulty}")
        
        vocab_text = ""
        if vocabulary:
            # 어휘 리스트를 개선된 형태로 표시
            vocab_list = []
            for vocab in vocabulary[:4]:  # 처음 4개만 표시
                if '(' in vocab:
                    word = vocab.split('(')[0].strip()
                    meaning = vocab.split('(')[1].replace(')', '').strip()
                    vocab_list.append(f"{word}({meaning})")
                else:
                    vocab_list.append(vocab)
            vocab_text = f"📚 핵심 어휘: {', '.join(vocab_list)} "
        
        return (f"📰 {category} 분야 기사 ({difficulty} 수준) "
               f"📅 발행: {data.get('published', '오늘')} "
               f"🎯 학습목표: 15분 독해, {difficulty} 수준 어휘 정리 "
               f"{vocab_text}"
               f"📝 권장: 실제 기사 내용 분석을 통한 맞춤 어휘 학습")

    elif content_type == "podcast":
        podcast_name = data.get('podcast_name', '').replace(' (백업)', '')  # 백업 텍스트 제거
        duration = data.get('duration', '15-25분')
        topic = data.get('topic', '일반 주제')
        episode_num = data.get('episode_number', '')
        episode_title = data.get('title', '')  # 정확한 에피소드 제목 추가
        
        # 'N/A'나 빈 값 처리
        if episode_num == 'N/A' or not episode_num:
            episode_num = ''
        
        # 주제 정리 (원하지 않는 값들 제거)
        if topic in ['일반 주제', 'N/A', '']:
            topic = '스페인어 학습'
        
        # 팟캐스트 이름 정리 (백업 표시나 불필요한 텍스트 제거)
        clean_podcast_name = podcast_name.replace(" (백업)", "").strip()
        
        # 주제에 따른 학습목표 설정
        learning_goals = {
            '경제': '금융 어휘',
            '정치': '정치 용어',
            '문화': '문화 표현',
            '사회': '사회 이슈 어휘',
            '교육': '교육 관련 어휘',
            '건강': '의료 용어',
            '기술': '기술 용어',
            '문법': '문법 구조',
            '스페인어 학습': '일상 어휘'
        }
        goal = learning_goals.get(topic, '핵심 어휘')
        
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
        
        # 정확한 에피소드 제목 추가 (Apple Podcasts에서 검색할 수 있도록)
        search_info = ""
        if episode_title:
            # 제목이 너무 길면 축약
            short_title = episode_title[:50] + "..." if len(episode_title) > 50 else episode_title
            search_info = f"🔍 검색어: \"{short_title}\" "
        
        # Radio Ambulante인 경우 웹사이트 URL 정보 추가
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
        
        return (f"🎧 {clean_podcast_name} {episode_text}{weekday_name} 스페인 팟캐스트 "
               f"📺 에피소드: \"{episode_title}\" "
               f"⏱️ 재생시간: {duration} {listen_plan} "
               f"🎯 학습목표: {goal} 5개 정리 "
               f"🌍 주제: {topic} "
               f"{search_info}"
               f"{url_info}"
               f"📝 권장: 핵심 어휘에 집중하여 청취")

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

def main():
    # 환경변수에서 설정값 가져오기
    reading_source = os.environ.get('READING_SOURCE', '')
    preset_difficulty = os.environ.get('READING_DIFFICULTY', 'B2')  # 기본값으로만 사용
    podcast_rss = os.environ.get('PODCAST_RSS', '')
    podcast_name = os.environ.get('PODCAST_NAME', '')
    weekday_name = os.environ.get('WEEKDAY_NAME', '')
    podcast_apple_base = os.environ.get('PODCAST_APPLE_BASE', '')
    
    article_data = None
    podcast_data = None  # 명시적으로 None으로 초기화

    print(f"=== 학습 자료 수집 시작 ===")
    print(f"독해 소스: {reading_source}")
    print(f"팟캐스트: {podcast_name}")
    print(f"팟캐스트 RSS: {podcast_rss}")
    print(f"요일: {weekday_name}")
    print(f"====================")

    # 기사 수집 및 실제 내용 분석
    try:
        if reading_source == "20minutos":
            feed_url = "https://www.20minutos.es/rss/"
        elif "El País" in reading_source:
            if "사설" in reading_source:
                feed_url = "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/opinion"
            else:
                feed_url = "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada"
        
        print(f"RSS 피드에서 기사 정보 수집 중: {feed_url}")
        feed = feedparser.parse(feed_url)
        
        if feed.entries:
            latest = feed.entries[0]
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
                
                # 분석된 난이도로 어휘 추출
                vocabulary = extract_vocabulary_from_content(article_content, analyzed_difficulty)
                category = extract_category_from_content(clean_title, article_content)
                
                print(f"추출된 어휘: {vocabulary}")
                print(f"분류된 카테고리: {category}")
                
                article_data = {
                    'title': clean_title,
                    'url': article_url,
                    'published': latest.get('published', ''),
                    'category': category,
                    'vocabulary': vocabulary,
                    'difficulty': analyzed_difficulty,  # 동적으로 분석된 난이도 사용
                    'content_preview': article_content[:200] + "..." if len(article_content) > 200 else article_content
                }
            else:
                print("기사 내용을 가져올 수 없어 RSS 요약 사용")
                # 내용을 가져올 수 없으면 RSS 요약 사용
                summary = latest.get('summary', '')
                analyzed_difficulty = analyze_text_difficulty(summary) if summary else preset_difficulty
                vocabulary = extract_vocabulary_from_content(summary, analyzed_difficulty)
                category = extract_category_from_content(clean_title, summary)
                
                article_data = {
                    'title': clean_title,
                    'url': article_url,
                    'published': latest.get('published', ''),
                    'category': category,
                    'vocabulary': vocabulary,
                    'difficulty': analyzed_difficulty,
                    'content_preview': summary
                }
                
        else:
            print("RSS 피드에서 기사를 찾을 수 없음")
            
    except Exception as e:
        print(f"기사 수집 오류: {e}")

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
            print("백업 RSS 피드들을 시도합니다...")
            
            # 백업 RSS 피드들 시도 - 더 정확한 피드 URL들 사용
            backup_feeds = []
            
            # 요일에 따라 적절한 백업 피드들 설정
            if weekday_name == "수요일":
                # 수요일은 SpanishWithVicente이지만 피드가 작동하지 않으므로 다른 옵션들 시도
                backup_feeds = [
                    ("https://www.hoyhablamos.com/podcast.rss", "Hoy Hablamos", "https://podcasts.apple.com/kr/podcast/hoy-hablamos-podcast-diario-para-aprender-español-learn/id1201483158"),
                    ("https://feeds.npr.org/510311/podcast.xml", "Radio Ambulante", "https://podcasts.apple.com/kr/podcast/radio-ambulante/id527614348"),
                    ("https://anchor.fm/s/f4f4a4f0/podcast/rss", "DELE Podcast", "https://podcasts.apple.com/us/podcast/examen-dele/id1705001626")
                ]
            else:
                # 다른 요일들의 일반적인 백업 피드들
                backup_feeds = [
                    ("https://www.hoyhablamos.com/podcast.rss", "Hoy Hablamos", "https://podcasts.apple.com/kr/podcast/hoy-hablamos-podcast-diario-para-aprender-español-learn/id1201483158"),
                    ("https://feeds.npr.org/510311/podcast.xml", "Radio Ambulante", "https://podcasts.apple.com/kr/podcast/radio-ambulante/id527614348"),
                    ("https://anchor.fm/s/f4f4a4f0/podcast/rss", "DELE Podcast", "https://podcasts.apple.com/us/podcast/examen-dele/id1705001626"),
                    ("https://feeds.feedburner.com/SpanishWithVicente", "SpanishWithVicente (대체 피드)", "https://podcasts.apple.com/kr/podcast/spanish-with-vicente/id1493547273")
                ]
            
            for backup_url, backup_podcast_name, backup_apple_base in backup_feeds:
                try:
                    print(f"백업 피드 시도: {backup_url} ({backup_podcast_name})")
                    backup_feed = feedparser.parse(backup_url)
                    
                    # 백업 피드 상태 확인
                    backup_status = getattr(backup_feed, 'status', 'N/A')
                    print(f"백업 피드 상태: {backup_status}, 에피소드 개수: {len(backup_feed.entries)}")
                    
                    if backup_feed.entries:
                        # 백업 피드에서도 최근 에피소드 확인
                        recent_episodes = []
                        for entry in backup_feed.entries[:3]:  # 백업에서는 3개만 확인
                            if is_episode_recent(entry.get('published_parsed')):
                                recent_episodes.append(entry)
                        
                        if not recent_episodes:
                            recent_episodes = [backup_feed.entries[0]]  # 최신 에피소드라도 사용
                        
                        latest = recent_episodes[0]
                        print(f"백업 피드에서 선택된 에피소드:")
                        print(f"  제목: {latest.title}")
                        print(f"  발행일: {latest.get('published', 'N/A')}")
                        print(f"  RSS 에피소드 URL: {latest.link}")
                        
                        episode_number = extract_episode_number(latest.title)
                        duration = extract_duration_from_feed(latest)
                        topic = extract_topic_keywords(latest.title, latest.get('summary', ''))
                        
                        # Radio Ambulante인 경우 실제 웹사이트 URL 시도
                        if 'Radio Ambulante' in backup_podcast_name:
                            radio_ambulante_url = extract_radio_ambulante_url(latest)
                            if radio_ambulante_url:
                                print(f"  Radio Ambulante 웹사이트 URL: {radio_ambulante_url}")
                                episode_link = radio_ambulante_url
                            else:
                                print(f"  Radio Ambulante 웹사이트 URL 추출 실패, RSS URL 사용")
                                episode_link = latest.link
                        else:
                            episode_link = latest.link
                        
                        # Apple Podcasts 링크 생성 - 에피소드 제목 포함
                        apple_link = generate_apple_podcast_link(backup_podcast_name, backup_apple_base, episode_link, episode_number, latest.title)
                        
                        # Radio Ambulante의 경우 Apple에서 찾지 못하면 에피소드 URL을 메인 URL로 사용
                        final_episode_url = episode_link
                        if 'Radio Ambulante' in backup_podcast_name:
                            # Apple에서 정확한 에피소드를 찾았는지 확인
                            if apple_link != backup_apple_base and validate_url(apple_link):
                                # Apple에서 정확한 에피소드를 찾았으면 Apple URL을 사용
                                print(f"  ✅ Apple Podcasts에서 정확한 에피소드 찾음, Apple URL 사용")
                                final_episode_url = apple_link
                            else:
                                # Apple에서 찾지 못했으면 원본 에피소드 URL 사용
                                print(f"  ❌ Apple Podcasts에서 정확한 에피소드를 찾지 못함, NPR URL 사용")
                                final_episode_url = episode_link
                                apple_link = backup_apple_base  # Apple 링크는 메인 페이지로 설정
                        else:
                            # 다른 팟캐스트는 기존 로직 유지
                            if not validate_url(episode_link):
                                print(f"  ⚠️  에피소드 링크가 유효하지 않음: {episode_link}")
                                final_episode_url = apple_link if validate_url(apple_link) else backup_apple_base
                                
                            if not validate_url(apple_link):
                                print(f"  ⚠️  Apple 링크가 유효하지 않음: {apple_link}")
                                apple_link = backup_apple_base
                        
                        podcast_data = {
                            'title': latest.title,
                            'url': final_episode_url,  # Apple에서 찾지 못하면 에피소드 URL 사용
                            'apple_link': apple_link,
                            'published': latest.get('published', ''),
                            'duration': duration,
                            'episode_number': episode_number or 'N/A',
                            'topic': topic,
                            'podcast_name': backup_podcast_name,
                            'summary': latest.get('summary', '')[:200]
                        }
                        
                        print(f"✅ 백업 피드 성공! 사용된 피드: {backup_podcast_name}")
                        print(f"   에피소드: {latest.title}")
                        print(f"   최종 에피소드 URL: {final_episode_url}")
                        print(f"   Apple URL: {apple_link}")
                        print(f"   URL 검증 결과 - 에피소드: {'✅' if validate_url(final_episode_url) else '❌'}, Apple: {'✅' if validate_url(apple_link) else '❌'}")
                        break
                except Exception as backup_e:
                    print(f"백업 피드 오류 ({backup_podcast_name}): {backup_e}")
                    continue
        
        elif feed.entries:
            print(f"피드에서 최신 에피소드 확인 중...")
            
            # 최근 며칠 이내의 에피소드만 필터링
            recent_episodes = []
            for entry in feed.entries[:5]:  # 최근 5개 에피소드만 확인
                print(f"  에피소드 확인: {entry.title}")
                print(f"    발행일: {entry.get('published', 'N/A')}")
                
                if is_episode_recent(entry.get('published_parsed')):
                    recent_episodes.append(entry)
                    print(f"    ✅ 최근 에피소드로 확인됨")
                else:
                    print(f"    ❌ 오래된 에피소드")
            
            if not recent_episodes:
                print("⚠️  최근 에피소드가 없습니다. 가장 최신 에피소드를 사용합니다.")
                recent_episodes = [feed.entries[0]]
            
            latest = recent_episodes[0]
            print(f"선택된 에피소드: {latest.title}")
            print(f"- 링크: {latest.link}")
            print(f"- 발행일: {latest.get('published', 'N/A')}")
            print(f"- 요약 길이: {len(latest.get('summary', ''))}")
            
            episode_number = extract_episode_number(latest.title)
            duration = extract_duration_from_feed(latest)
            topic = extract_topic_keywords(latest.title, latest.get('summary', ''))
            
            episode_link = latest.link
            
            # 에피소드 링크 유효성 검증
            if not validate_url(episode_link):
                print(f"⚠️  에피소드 링크가 유효하지 않음: {episode_link}")
                episode_link = podcast_apple_base  # 기본값으로 Apple Podcasts 사용
            
            # Apple Podcasts 링크 생성 - 에피소드 제목 포함
            apple_link = generate_apple_podcast_link(podcast_name, podcast_apple_base, episode_link, episode_number, latest.title)
            
            # Radio Ambulante의 경우 Apple에서 찾지 못하면 에피소드 URL을 메인 URL로 사용
            final_episode_url = episode_link
            if 'Radio Ambulante' in podcast_name:
                # Apple에서 정확한 에피소드를 찾았는지 확인
                if apple_link != podcast_apple_base and validate_url(apple_link):
                    # Apple에서 정확한 에피소드를 찾았으면 Apple URL을 사용
                    print(f"✅ Apple Podcasts에서 정확한 에피소드 찾음, Apple URL 사용")
                    final_episode_url = apple_link
                else:
                    # Apple에서 찾지 못했으면 원본 에피소드 URL 사용
                    print(f"❌ Apple Podcasts에서 정확한 에피소드를 찾지 못함, NPR URL 사용")
                    final_episode_url = episode_link
                    apple_link = podcast_apple_base  # Apple 링크는 메인 페이지로 설정
            else:
                # 다른 팟캐스트는 기존 로직 유지
                if not validate_url(apple_link):
                    print(f"⚠️  Apple Podcasts 링크가 유효하지 않음, 기본 링크 사용")
                    apple_link = podcast_apple_base
            
            podcast_data = {
                'title': latest.title,
                'url': final_episode_url,  # Apple에서 찾지 못하면 에피소드 URL 사용
                'apple_link': apple_link,
                'published': latest.get('published', ''),
                'duration': duration,
                'episode_number': episode_number or 'N/A',
                'topic': topic,
                'podcast_name': podcast_name,
                'summary': latest.get('summary', '')[:200]
            }
            
            print(f"팟캐스트 데이터 생성 완료:")
            print(f"- 에피소드 번호: {episode_number}")
            print(f"- 재생시간: {duration}")
            print(f"- 주제: {topic}")
            print(f"- 최종 에피소드 URL: {final_episode_url}")
            print(f"- Apple Podcasts URL: {apple_link}")
            print(f"- URL 유효성 - 에피소드: {'✅' if validate_url(final_episode_url) else '❌'}, Apple: {'✅' if validate_url(apple_link) else '❌'}")
            
        else:
            print("메인 피드에 에피소드가 없음 - 이 경우는 위에서 처리됨")
            
    except Exception as e:
        print(f"팟캐스트 수집 오류: {e}")
        import traceback
        print(f"상세 오류: {traceback.format_exc()}")

    # 학습 자료 정보를 환경변수로 출력
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        if article_data:
            f.write(f"article_title={article_data['title']}\n")
            f.write(f"article_url={article_data['url']}\n")
            f.write(f"article_category={article_data['category']}\n")
            f.write(f"article_vocabulary={', '.join(article_data['vocabulary'])}\n")
            f.write(f"article_difficulty={article_data['difficulty']}\n")  # 동적 난이도 출력
            f.write(f"article_memo={create_detailed_memo('article', article_data, weekday_name)}\n")
        
        if podcast_data:
            f.write(f"podcast_title={podcast_data['title']}\n")
            f.write(f"podcast_url={podcast_data['url']}\n")
            f.write(f"podcast_apple={podcast_data['apple_link']}\n")
            f.write(f"podcast_duration={podcast_data['duration']}\n")
            f.write(f"podcast_topic={podcast_data['topic']}\n")
            f.write(f"podcast_memo={create_detailed_memo('podcast', podcast_data, weekday_name)}\n")

    print("학습 자료 수집 완료!")
    if article_data:
        print(f"✅ 기사: {article_data['title']}")
        print(f"   카테고리: {article_data['category']}")
        print(f"   난이도: {article_data['difficulty']}")  # 동적 난이도 출력
        print(f"   어휘: {article_data['vocabulary']}")
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
