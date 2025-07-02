#!/usr/bin/env python3
"""
Collect Spanish learning materials: articles and podcast episodes with content analysis.
"""
import os
import sys
import requests
import feedparser
from datetime import datetime
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

def get_article_content(url):
    """실제 기사 URL에 접속해서 본문 내용을 가져오는 함수"""
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
    """실제 기사 내용에서 학습자 수준에 맞는 핵심 어휘를 추출"""
    if not content:
        return []
    
    # 수준별 어휘 추출 기준
    if difficulty == "B2":
        # B2 수준: 중급 어휘, 일상적이지 않은 표현들
        target_patterns = [
            # 동사류
            r'\b(desarrollar|establecer|implementar|generar|promover|fortalecer|consolidar|impulsar|fomentar|garantizar)\b',
            # 명사류  
            r'\b(iniciativa|propuesta|medida|estrategia|política|programa|proyecto|inversión|desarrollo|crecimiento)\b',
            # 형용사류
            r'\b(fundamental|esencial|crucial|significativo|relevante|considerable|notable|destacado|principal|prioritario)\b',
            # 연결어
            r'\b(además|asimismo|por tanto|sin embargo|no obstante|en consecuencia|por consiguiente|en definitiva)\b',
            # 기관/조직 관련
            r'\b(entidad|organismo|institución|administración|departamento|ministerio|ayuntamiento|comunidad)\b'
        ]
    elif difficulty == "C1":
        # C1 수준: 고급 어휘, 전문적/학술적 표현들
        target_patterns = [
            # 고급 동사
            r'\b(implementar|consolidar|incrementar|optimizar|diversificar|potenciar|materializar|vehicular|canalizar)\b',
            # 전문 명사
            r'\b(sostenibilidad|competitividad|rentabilidad|eficiencia|transparencia|gobernanza|paradigma|metodología)\b',
            # 고급 형용사
            r'\b(innovador|sostenible|competitivo|eficiente|transparente|inclusivo|participativo|colaborativo)\b',
            # 학술적 연결어
            r'\b(en este sentido|cabe destacar|es preciso|conviene señalar|resulta evidente|se constata)\b',
            # 전문 분야 용어
            r'\b(digitalización|transformación|modernización|reestructuración|reconversión|reorientación)\b'
        ]
    else:
        # 기본 B2 패턴 사용
        target_patterns = [
            r'\b(desarrollar|establecer|implementar|medida|estrategia|fundamental|además|sin embargo)\b'
        ]
    
    found_vocab = []
    content_lower = content.lower()
    
    # 어휘 추출 및 의미 매핑
    vocab_meanings = {
        # B2 수준 어휘
        'desarrollar': '개발하다, 발전시키다',
        'establecer': '설립하다, 확립하다',
        'implementar': '시행하다, 구현하다',
        'generar': '생성하다, 만들어내다',
        'promover': '촉진하다, 장려하다',
        'fortalecer': '강화하다',
        'consolidar': '통합하다, 견고히 하다',
        'impulsar': '추진하다, 촉진하다',
        'fomentar': '장려하다, 촉진하다',
        'garantizar': '보장하다',
        'iniciativa': '계획, 주도권',
        'propuesta': '제안',
        'medida': '조치, 대책',
        'estrategia': '전략',
        'política': '정책',
        'programa': '프로그램',
        'proyecto': '프로젝트',
        'inversión': '투자',
        'desarrollo': '발전, 개발',
        'crecimiento': '성장',
        'fundamental': '기본적인, 근본적인',
        'esencial': '필수적인',
        'crucial': '중요한, 결정적인',
        'significativo': '의미있는, 중요한',
        'relevante': '관련있는, 중요한',
        'considerable': '상당한',
        'notable': '주목할 만한',
        'destacado': '뛰어난, 두드러진',
        'principal': '주요한',
        'prioritario': '우선적인',
        'además': '게다가, 또한',
        'asimismo': '마찬가지로',
        'por tanto': '따라서',
        'sin embargo': '그러나',
        'no obstante': '그럼에도 불구하고',
        'en consecuencia': '결과적으로',
        'por consiguiente': '따라서',
        'en definitiva': '결국',
        'entidad': '기관, 단체',
        'organismo': '기관, 조직',
        'institución': '기관, 제도',
        'administración': '행정부',
        'departamento': '부서',
        'ministerio': '부 (정부기관)',
        'ayuntamiento': '시청',
        'comunidad': '지역사회, 공동체',
        
        # C1 수준 어휘
        'incrementar': '증가시키다',
        'optimizar': '최적화하다',
        'diversificar': '다양화하다',
        'potenciar': '강화하다, 잠재력을 키우다',
        'materializar': '실현하다',
        'vehicular': '전달하다, 수단이 되다',
        'canalizar': '경로를 제공하다',
        'sostenibilidad': '지속가능성',
        'competitividad': '경쟁력',
        'rentabilidad': '수익성',
        'eficiencia': '효율성',
        'transparencia': '투명성',
        'gobernanza': '거버넌스, 통치',
        'paradigma': '패러다임',
        'metodología': '방법론',
        'innovador': '혁신적인',
        'sostenible': '지속가능한',
        'competitivo': '경쟁적인',
        'eficiente': '효율적인',
        'transparente': '투명한',
        'inclusivo': '포용적인',
        'participativo': '참여적인',
        'colaborativo': '협력적인',
        'digitalización': '디지털화',
        'transformación': '변화, 변혁',
        'modernización': '현대화',
        'reestructuración': '구조조정',
        'reconversión': '전환',
        'reorientación': '방향 전환'
    }
    
    # 패턴 매칭으로 어휘 찾기
    for pattern in target_patterns:
        matches = re.findall(pattern, content_lower, re.IGNORECASE)
        for match in matches:
            if match.lower() in vocab_meanings and match.lower() not in [v.split(' (')[0].lower() for v in found_vocab]:
                meaning = vocab_meanings[match.lower()]
                found_vocab.append(f"{match} ({meaning})")
    
    # 중복 제거 및 최대 5개 반환
    unique_vocab = []
    seen = set()
    for vocab in found_vocab:
        word = vocab.split(' (')[0].lower()
        if word not in seen:
            unique_vocab.append(vocab)
            seen.add(word)
            if len(unique_vocab) >= 5:
                break
    
    return unique_vocab

def extract_category_from_content(title, content):
    """제목과 내용을 기반으로 카테고리 분류"""
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
        difficulty = data.get('difficulty', 'B2')
        
        vocab_text = ""
        if vocabulary:
            vocab_list = ", ".join(vocabulary[:3])  # 처음 3개만 표시
            vocab_text = f"📚 핵심 어휘: {vocab_list} "
        
        return (f"📰 {category} 분야 기사 ({difficulty} 수준) "
               f"📅 발행: {data.get('published', '오늘')} "
               f"🎯 학습목표: 15분 독해, {difficulty} 수준 어휘 정리 "
               f"{vocab_text}"
               f"📝 권장: 실제 기사 내용 분석을 통한 맞춤 어휘 학습")

    elif content_type == "podcast":
        podcast_name = data.get('podcast_name', '')
        duration = data.get('duration', '15-25분')
        topic = data.get('topic', '일반 주제')
        episode_num = data.get('episode_number', '')
        
        # 주제에 따른 학습목표 설정
        learning_goals = {
            '경제': '금융 어휘',
            '정치': '정치 용어',
            '문화': '문화 표현',
            '사회': '사회 이슈 어휘',
            '교육': '교육 관련 어휘',
            '건강': '의료 용어',
            '기술': '기술 용어',
            '문법': '문법 구조'
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
        
        return (f"🎧 {podcast_name} Ep.{episode_num} - {weekday_name} 스페인 팟캐스트 "
               f"⏱️ 재생시간: {duration} {listen_plan} "
               f"🎯 학습목표: {goal} 5개 정리 "
               f"🌍 주제: {topic} "
               f"📝 권장: 핵심 어휘에 집중하여 청취")

def main():
    # 환경변수에서 설정값 가져오기
    reading_source = os.environ.get('READING_SOURCE', '')
    reading_difficulty = os.environ.get('READING_DIFFICULTY', 'B2')
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
                # 실제 내용에서 어휘 추출
                vocabulary = extract_vocabulary_from_content(article_content, reading_difficulty)
                category = extract_category_from_content(clean_title, article_content)
                
                print(f"추출된 어휘: {vocabulary}")
                print(f"분류된 카테고리: {category}")
                
                article_data = {
                    'title': clean_title,
                    'url': article_url,
                    'published': latest.get('published', ''),
                    'category': category,
                    'vocabulary': vocabulary,
                    'difficulty': reading_difficulty,
                    'content_preview': article_content[:200] + "..." if len(article_content) > 200 else article_content
                }
            else:
                print("기사 내용을 가져올 수 없어 RSS 요약 사용")
                # 내용을 가져올 수 없으면 RSS 요약 사용
                summary = latest.get('summary', '')
                vocabulary = extract_vocabulary_from_content(summary, reading_difficulty)
                category = extract_category_from_content(clean_title, summary)
                
                article_data = {
                    'title': clean_title,
                    'url': article_url,
                    'published': latest.get('published', ''),
                    'category': category,
                    'vocabulary': vocabulary,
                    'difficulty': reading_difficulty,
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
        
        if feed.entries:
            latest = feed.entries[0]
            print(f"최신 에피소드 정보:")
            print(f"- 제목: {latest.title}")
            print(f"- 링크: {latest.link}")
            print(f"- 발행일: {latest.get('published', 'N/A')}")
            print(f"- 요약 길이: {len(latest.get('summary', ''))}")
            
            episode_number = extract_episode_number(latest.title)
            duration = extract_duration_from_feed(latest)
            topic = extract_topic_keywords(latest.title, latest.get('summary', ''))
            
            episode_link = latest.link
            
            # Apple Podcasts 링크 생성 개선
            if 'npr.org' in episode_link or 'radioambulante' in episode_link:
                apple_link = podcast_apple_base
            else:
                apple_link = f"{podcast_apple_base}?i={episode_number}" if episode_number else podcast_apple_base
            
            podcast_data = {
                'title': latest.title,
                'url': episode_link,
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
            
        else:
            print("팟캐스트 에피소드를 찾을 수 없음")
            print("다른 RSS 피드를 시도합니다...")
            
            # 백업 RSS 피드들 시도
            backup_feeds = [
                "https://feeds.feedburner.com/hoyhablamos",  # Hoy Hablamos
                "https://feeds.npr.org/510311/podcast.xml",   # Radio Ambulante
                "https://anchor.fm/s/f4f4a4f0/podcast/rss"    # DELE Podcast
            ]
            
            for backup_url in backup_feeds:
                try:
                    print(f"백업 피드 시도: {backup_url}")
                    backup_feed = feedparser.parse(backup_url)
                    if backup_feed.entries:
                        latest = backup_feed.entries[0]
                        episode_number = extract_episode_number(latest.title)
                        duration = extract_duration_from_feed(latest)
                        topic = extract_topic_keywords(latest.title, latest.get('summary', ''))
                        
                        podcast_data = {
                            'title': latest.title,
                            'url': latest.link,
                            'apple_link': podcast_apple_base,
                            'published': latest.get('published', ''),
                            'duration': duration,
                            'episode_number': episode_number or 'N/A',
                            'topic': topic,
                            'podcast_name': f"{podcast_name} (백업)",
                            'summary': latest.get('summary', '')[:200]
                        }
                        print(f"백업 피드에서 에피소드 찾음: {latest.title}")
                        break
                except Exception as backup_e:
                    print(f"백업 피드 오류: {backup_e}")
                    continue
            
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
