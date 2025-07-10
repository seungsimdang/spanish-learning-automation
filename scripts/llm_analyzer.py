#!/usr/bin/env python3
"""
LLM-based Spanish content analyzer using ChatGPT API.
ChatGPT API를 사용한 스페인어 콘텐츠 분석기
"""

import os
import json
import requests
import time
import unicodedata
import html
from typing import List, Dict, Optional

class SpanishLLMAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the LLM analyzer with ChatGPT API
        """
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _make_api_call(self, prompt: str, max_tokens: int = 800) -> str:
        """
        Make API call to ChatGPT
        """
        try:
            payload = {
                "model": "gpt-4o-mini",  # 비용 효율적인 모델 사용
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert Spanish language teacher and linguist specializing in analyzing Spanish content for language learners."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,  # 일관성 있는 분석을 위해 낮은 temperature
                "top_p": 0.9
            }
            
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
            
        except requests.exceptions.RequestException as e:
            print(f"API 호출 오류: {e}")
            return ""
        except Exception as e:
            print(f"분석 오류: {e}")
            return ""
    
    def analyze_podcast_colloquialisms(self, transcript: str, difficulty: str = "B2") -> List[str]:
        """
        Extract colloquial expressions from podcast transcript using LLM
        팟캐스트 transcript에서 구어체 표현 추출
        """
        print(f"\n    🔍 구어체 분석 시작")
        print(f"    📊 원본 텍스트 길이: {len(transcript) if transcript else 0}자")
        
        if not transcript:
            print(f"    ❌ 분석 실패: transcript가 비어있음")
            return []
        
        # 원본 텍스트 내용 분석
        original_preview = transcript[:200].replace('\n', ' ').strip()
        print(f"    📄 원본 텍스트 미리보기: {original_preview}...")
        
        # 메타데이터만 있는지 확인
        if self.is_metadata_only(transcript):
            print(f"    ⚠️  메타데이터만 포함된 콘텐츠로 판단됨 - 구어체 분석 건너뛰기")
            print(f"    📝 메타데이터 유형: 제목, 설명, 기술적 정보만 포함")
            return []
        
        # 텍스트 정리 및 인코딩 문제 해결
        cleaned_transcript = self.clean_text(transcript)
        print(f"    🧹 텍스트 정리 후 길이: {len(cleaned_transcript)}자")
        
        # 이중 언어 콘텐츠에서 스페인어 부분만 추출
        spanish_transcript = self.extract_spanish_content(cleaned_transcript)
        print(f"    🇪🇸 스페인어 추출 후 길이: {len(spanish_transcript)}자")
        
        # 정리된 텍스트가 비어있거나 너무 짧으면 건너뛰기
        if len(spanish_transcript.strip()) < 50:
            print(f"    ❌ 분석 실패: 정리된 텍스트가 너무 짧음 ({len(spanish_transcript.strip())}자)")
            print(f"    📝 실패 원인: 스페인어 콘텐츠 추출 후 의미있는 내용이 부족")
            return []
        
        # 텍스트가 너무 길면 처음 2000자만 사용
        if len(spanish_transcript) > 2000:
            spanish_transcript = spanish_transcript[:2000] + "..."
            print(f"    ✂️  텍스트 길이 조정: 2000자로 제한")
        
        # LLM 분석에 사용될 실제 텍스트 상세 로깅
        final_preview = spanish_transcript[:300].replace('\n', ' ').strip()
        print(f"    🤖 LLM 분석 대상 텍스트 미리보기: {final_preview}...")
        print(f"    📏 LLM 분석 대상 텍스트 길이: {len(spanish_transcript)}자")
        
        # 텍스트 유형 분석
        text_type = self.analyze_text_type(spanish_transcript)
        print(f"    📋 텍스트 유형 분석: {text_type}")
        
        # 구어체 표현 가능성 예측
        colloquial_likelihood = self.predict_colloquial_likelihood(spanish_transcript)
        print(f"    🎯 구어체 표현 발견 가능성: {colloquial_likelihood}")
        
        prompt = f"""
You are analyzing Spanish text to find ACTUAL colloquial expressions that appear in the text.

CRITICAL RULE: Only extract expressions that are ACTUALLY PRESENT in the provided text. Do not suggest or create expressions that are not in the text.

Text to analyze:
{spanish_transcript}

Instructions:
1. Read the text carefully and identify any words, phrases, or expressions that show informal/conversational Spanish
2. Look for language that is characteristic of spoken Spanish rather than formal written Spanish
3. Find expressions that native speakers would use in casual conversation, everyday situations, or informal contexts
4. Include informal vocabulary, conversational connectors, colloquial phrases, everyday expressions, and any language that shows a relaxed, natural speaking style
5. If the text is formal and contains no colloquial expressions, return "NO_COLLOQUIAL_EXPRESSIONS_FOUND"

What makes an expression colloquial:
- Words or phrases commonly used in everyday conversation
- Informal alternatives to more formal expressions
- Conversational fillers, connectors, or transitions
- Casual ways of expressing opinions, emotions, or reactions
- Language that sounds natural and spontaneous rather than scripted or formal

Response format (only if expressions are found):
- "expression" → Korean meaning

If no colloquial expressions are found in this formal text, respond with: NO_COLLOQUIAL_EXPRESSIONS_FOUND
"""
        
        response = self._make_api_call(prompt, max_tokens=400)
        
        print(f"    🤖 LLM 응답 받음: {len(response) if response else 0}자")
        
        if not response:
            print(f"    ❌ LLM 응답 실패 - API 호출 오류")
            return []
        
        # LLM 응답 내용 로깅
        response_preview = response[:200].replace('\n', ' ').strip()
        print(f"    📄 LLM 응답 미리보기: {response_preview}...")
        
        # "NO_COLLOQUIAL_EXPRESSIONS_FOUND" 응답 처리
        if "NO_COLLOQUIAL_EXPRESSIONS_FOUND" in response:
            print(f"    ✅ LLM 분석 완료: 텍스트에 구어체 표현이 없음을 확인")
            print(f"    📝 분석 결과: 제공된 텍스트가 정식/공식적 언어로 구성됨")
            return []
        
        # 응답에서 표현들 추출
        expressions = []
        lines = response.split('\n')
        
        print(f"    🔍 구어체 표현 파싱 시작: {len(lines)}개 라인 분석")
        
        for i, line in enumerate(lines):
            line = line.strip()
            print(f"    📝 라인 {i+1} 분석: {line}")
            
            # 다양한 형식 지원: 
            # 1. "expression" → meaning (context)
            # 2. - "expression" → meaning (context)  
            # 3. expression → meaning
            if '"' in line and '→' in line:
                try:
                    # 따옴표로 묶인 표현 추출
                    start_quote = line.find('"')
                    end_quote = line.find('"', start_quote + 1)
                    if start_quote != -1 and end_quote != -1:
                        expression = line[start_quote+1:end_quote]
                        remaining = line[end_quote+1:]
                        if '→' in remaining:
                            meaning_part = remaining.split('→')[1].strip()
                            # (usage context) 부분 제거
                            if '(' in meaning_part:
                                meaning = meaning_part.split('(')[0].strip()
                            else:
                                meaning = meaning_part.strip()
                            
                            full_expression = f"{expression} ({meaning})"
                            expressions.append(full_expression)
                            print(f"    ✅ 구어체 표현 발견: {full_expression}")
                        else:
                            print(f"    ⚠️  → 기호 없음")
                    else:
                        print(f"    ⚠️  따옴표 쌍이 맞지 않음")
                except Exception as e:
                    print(f"    ⚠️  구어체 표현 파싱 오류 (라인 {i+1}): {e}")
                    print(f"    📝 문제 라인: {line}")
                    continue
            elif '→' in line and not line.startswith('#') and line.strip():
                # 따옴표 없이 → 만 있는 경우도 처리
                try:
                    parts = line.split('→')
                    if len(parts) >= 2:
                        expression_part = parts[0].strip()
                        meaning_part = parts[1].strip()
                        
                        # 앞의 불필요한 기호 제거 (-, *, 등)
                        expression_part = expression_part.lstrip('- *•').strip()
                        
                        # (usage context) 부분 제거
                        if '(' in meaning_part:
                            meaning = meaning_part.split('(')[0].strip()
                        else:
                            meaning = meaning_part.strip()
                        
                        if expression_part and meaning:
                            full_expression = f"{expression_part} ({meaning})"
                            expressions.append(full_expression)
                            print(f"    ✅ 구어체 표현 발견: {full_expression}")
                except Exception as e:
                    print(f"    ⚠️  대안 파싱 오류 (라인 {i+1}): {e}")
                    continue
            else:
                print(f"    ⚠️  구어체 표현 형식이 아님")
                continue
        
        print(f"    📊 최종 구어체 표현 개수: {len(expressions)}개")
        
        if len(expressions) == 0:
            print(f"    🤔 구어체 표현이 0개인 이유 분석:")
            print(f"       • LLM이 텍스트를 정식/공식적 언어로 판단")
            print(f"       • 텍스트에 대화체/비공식적 표현이 실제로 없음")
            print(f"       • 메타데이터나 설명문 위주의 내용일 가능성")
            
        return expressions[:5]  # 최대 5개 반환
    
    def analyze_article_grammar(self, article_content: str, difficulty: str = "B2") -> Dict[str, any]:
        """
        Analyze grammar structures in article content using LLM
        기사 내용의 문법 구조 분석
        """
        if not article_content:
            return {"original_sentence": "", "grammar_analysis": []}
        
        # 텍스트가 너무 길면 처음 1500자만 사용
        if len(article_content) > 1500:
            article_content = article_content[:1500] + "..."
        
        prompt = f"""
Analyze this Spanish article and identify 1 representative sentence for grammar analysis at {difficulty} level.

Select the most complex and educational sentence from the text that contains multiple grammar structures suitable for {difficulty} level learners.

Article content:
{article_content}

Please provide the analysis in this exact format:

ORIGINAL_SENTENCE: [exact sentence from text]

GRAMMAR_ANALYSIS:
**문법 구조 1 (수준)**
- 설명 1
- 설명 2

**문법 구조 2 (수준)**  
- 설명 1
- 설명 2

**문법 구조 3 (수준)**
- 설명 1
- 설명 2

**문법 구조 4 (수준)**
- 설명 1 
- 설명 2

**문법 구조 5 (수준)**
- 설명 1
- 설명 2

Focus on grammar structures appropriate for {difficulty} level such as:
- B1: 현재/과거 시제, ser vs estar, 재귀동사
- B2: 접속법 현재/과거, 조건법, 완료 시제  
- C1: 접속법 완료, 복합 조건문, 수동태

Provide detailed explanations for each grammar point including specific words from the sentence.
"""
        
        response = self._make_api_call(prompt, max_tokens=800)
        
        if not response:
            return {"original_sentence": "", "grammar_analysis": []}
        
        # 응답에서 원문 문장과 문법 분석 추출
        original_sentence = ""
        grammar_analysis = []
        
        lines = response.split('\n')
        current_section = ""
        current_grammar = ""
        current_points = []
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('ORIGINAL_SENTENCE:'):
                original_sentence = line.replace('ORIGINAL_SENTENCE:', '').strip()
            elif line.startswith('GRAMMAR_ANALYSIS:'):
                current_section = "grammar"
            elif line.startswith('**') and line.endswith('**'):
                # 이전 문법 구조 저장
                if current_grammar and current_points:
                    grammar_analysis.append({
                        "title": current_grammar,
                        "points": current_points
                    })
                # 새로운 문법 구조 시작
                current_grammar = line.replace('**', '').strip()
                current_points = []
            elif line.startswith('- ') and current_section == "grammar":
                current_points.append(line[2:].strip())
        
        # 마지막 문법 구조 저장
        if current_grammar and current_points:
            grammar_analysis.append({
                "title": current_grammar,
                "points": current_points
            })
        
        return {
            "original_sentence": original_sentence,
            "grammar_analysis": grammar_analysis
        }
        
        return {
            "original_sentence": original_sentence,
            "grammar_analysis": grammar_analysis
        }
    
    def analyze_text_difficulty(self, content: str) -> str:
        """
        Analyze text difficulty using LLM
        LLM을 사용한 텍스트 난이도 분석
        """
        if not content:
            return "B2"
        
        # 텍스트가 너무 길면 처음 1000자만 사용
        if len(content) > 1000:
            content = content[:1000] + "..."
        
        prompt = f"""
Analyze this Spanish text and determine its CEFR difficulty level (A1, A2, B1, B1+, B2, B2+, C1, C2).

Consider:
- Vocabulary complexity
- Grammar structures used
- Sentence length and complexity
- Abstract vs concrete concepts
- Technical vs everyday language

Text:
{content}

Respond with only the CEFR level (e.g., "B2" or "B2+" or "C1"), no additional text.
"""
        
        response = self._make_api_call(prompt, max_tokens=50)
        
        # 응답에서 레벨 추출
        if response:
            response = response.strip().upper()
            valid_levels = ['A1', 'A2', 'B1', 'B1+', 'B2', 'B2+', 'C1', 'C2']
            for level in valid_levels:
                if level in response:
                    return level
        
        return "B2"  # 기본값
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text for better LLM analysis
        텍스트 정리 및 정규화
        """
        if not text:
            return ""
        
        # HTML 엔티티 디코딩
        text = html.unescape(text)
        
        # 잘못된 인코딩 수정
        replacements = {
            'Ã±': 'ñ',  # EspaÃ±ol -> Español
            'Ã¡': 'á',
            'Ã©': 'é',
            'Ã­': 'í',
            'Ã³': 'ó',
            'Ãº': 'ú',
            'Ã ': 'à',
            'Ã¨': 'è',
            'Ã¬': 'ì',
            'Ã²': 'ò',
            'Ã¹': 'ù',
            'Ã¼': 'ü',
            'Ã': 'Ñ',
            'Â': '',  # 불필요한 문자 제거
            '\xa0': ' ',  # non-breaking space
            '\u2028': '\n',  # line separator
            '\u2029': '\n\n'  # paragraph separator
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # 유니코드 정규화
        text = unicodedata.normalize('NFC', text)
        
        # 여러 공백을 하나로 정리
        text = ' '.join(text.split())
        
        return text
    
    def generate_podcast_learning_goals(self, content: str, title: str, difficulty: str = "B2", colloquial_count: int = 0) -> List[str]:
        """
        팟캐스트 내용을 분석하여 적절한 학습 목표를 생성
        
        Args:
            content: 팟캐스트 내용 (메모/스크립트)
            title: 팟캐스트 제목
            difficulty: 학습자 수준 (B1, B2, C1 등)
            colloquial_count: 분석된 구어체 표현 개수
            
        Returns:
            List of learning goals
        """
        print(f"    🎯 팟캐스트 학습 목표 생성 중... (난이도: {difficulty}, 구어체 표현: {colloquial_count}개)")
        
        # 내용 정리
        clean_content = self.clean_text(content)
        
        # 구어체 표현 개수에 따른 목표 조정
        if colloquial_count == 0:
            # 구어체 표현이 0개인 경우 다른 학습 목표에 집중
            prompt = f"""
Analyze this Spanish podcast episode and generate 3-4 specific, actionable learning goals for a {difficulty} level Spanish learner.

PODCAST TITLE: {title}
PODCAST CONTENT: {clean_content[:1500]}
COLLOQUIAL EXPRESSIONS FOUND: 0 expressions (focus on other learning aspects)

Since no colloquial expressions were found in the analysis, focus on these alternative learning aspects:
1. Main topic/theme comprehension and vocabulary
2. Formal/academic language structures present
3. Cultural and contextual learning opportunities
4. Advanced listening comprehension strategies
5. Grammar patterns and sentence structures
6. Register and tone analysis

Create learning goals that are:
- Specific and measurable
- Appropriate for {difficulty} level
- Focus on formal language skills and comprehension strategies
- Encourage deep content understanding
- Be realistic about vocabulary numbers (5-10 key words, not excessive amounts)
- EXCLUDE colloquial expression analysis since none were found

Format your response as a numbered list in Korean:
1. [구체적인 학습 목표 1]
2. [구체적인 학습 목표 2]  
3. [구체적인 학습 목표 3]
(4. [추가 목표 if relevant])

Examples of good learning goals for formal content:
- 에피소드 주제와 관련된 전문 어휘 및 표현 5-8개 학습
- 화자의 논리적 구조와 주장 전개 방식 파악
- 스페인어 정치/사회적 맥락과 문화적 배경 이해
- 복합문과 고급 문법 구조 분석 및 학습
"""
        else:
            # 구어체 표현이 있는 경우 기존 로직
            prompt = f"""
Analyze this Spanish podcast episode and generate 3-4 specific, actionable learning goals for a {difficulty} level Spanish learner.

PODCAST TITLE: {title}
PODCAST CONTENT: {clean_content[:1500]}
COLLOQUIAL EXPRESSIONS FOUND: {colloquial_count} expressions

Consider the following aspects when creating learning goals:
1. Main topic/theme of the episode
2. Vocabulary focus areas (suggest realistic number based on content length)
3. Grammar structures present
4. Cultural/contextual learning opportunities
5. Listening comprehension skills
6. Colloquial expressions: exactly {colloquial_count} expressions were found in the analysis

Create learning goals that are:
- Specific and measurable
- Appropriate for {difficulty} level
- Reflect the ACTUAL analysis results (e.g., if {colloquial_count} colloquial expressions were found, mention that exact number)
- Focus on practical language skills
- Encourage active listening and engagement
- Be realistic about vocabulary numbers (5-10 key words, not excessive amounts)

Format your response as a numbered list in Korean:
1. [구체적인 학습 목표 1]
2. [구체적인 학습 목표 2]  
3. [구체적인 학습 목표 3]
(4. [추가 목표 if relevant])

Make sure to reference the actual number of colloquial expressions found: {colloquial_count}

Examples of good learning goals:
- 에피소드 주제와 관련된 핵심 어휘 5-8개 학습 및 활용
- 화자의 감정 표현 방식과 억양 패턴 파악  
- 분석된 구어체 표현 {colloquial_count}개를 정리하고 일상 대화에서 활용하기
- 스페인어 문화적 맥락에서 사용되는 관용 표현 이해
"""
        
        response = self._make_api_call(prompt, max_tokens=600)
        
        if not response:
            # 기본 목표 반환 (구어체 표현 개수에 따라 다른 목표)
            if colloquial_count > 0:
                return [
                    f"팟캐스트 주제 관련 핵심 어휘 5-7개 학습 ({difficulty} 수준)",
                    f"분석된 구어체 표현 {colloquial_count}개 정리 및 활용",
                    "자연스러운 발음과 억양 패턴 학습"
                ]
            else:
                # 구어체 표현이 0개인 경우 다른 학습 목표 제공
                return [
                    f"팟캐스트 주제 관련 전문 어휘 및 표현 5-7개 학습 ({difficulty} 수준)",
                    "화자의 논리적 구조와 주장 전개 방식 파악",
                    "스페인어 정치/사회적 맥락과 문화적 배경 이해"
                ]
        
        # 응답에서 목표들 추출
        goals = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            # 숫자로 시작하는 줄 찾기 (1. 2. 3. 형태)
            if line and (line[0].isdigit() or line.startswith('•') or line.startswith('-')):
                # 번호 부분 제거
                if '. ' in line:
                    goal = line.split('. ', 1)[1].strip()
                elif line.startswith('• '):
                    goal = line[2:].strip()
                elif line.startswith('- '):
                    goal = line[2:].strip()
                else:
                    goal = line.strip()
                
                if goal and len(goal) > 10:  # 너무 짧은 목표는 제외
                    goals.append(goal)
        
        # 3-4개 목표 반환
        if goals:
            return goals[:4]
        else:
            # 구어체 표현 개수에 따른 fallback 목표
            if colloquial_count > 0:
                return [
                    f"팟캐스트 주제 관련 핵심 어휘 학습 ({difficulty} 수준)",
                    f"분석된 구어체 표현 {colloquial_count}개 정리 및 활용",
                    "자연스러운 발음과 억양 패턴 학습"
                ]
            else:
                return [
                    f"팟캐스트 주제 관련 전문 어휘 학습 ({difficulty} 수준)",
                    "화자의 논리적 구조와 주장 전개 방식 파악",
                    "스페인어 정치/사회적 맥락과 문화적 배경 이해"
                ]
    
    def simple_language_detection(self, content: str) -> str:
        """
        Simple language detection using LLM - returns SPANISH or ENGLISH
        LLM을 사용한 간단한 언어 검증
        """
        if not content:
            return "UNKNOWN"
        
        # 텍스트 정리
        content = self.clean_text(content)
        
        # 너무 긴 경우 처음 부분만 사용
        if len(content) > 1000:
            content = content[:1000] + "..."
        
        prompt = f"""
Analyze the following text and determine if it's primarily in Spanish or English.

Text to analyze:
{content}

Instructions:
1. Analyze the language of the text
2. Respond with ONLY ONE WORD: either "SPANISH" or "ENGLISH"
3. Do not provide any explanation or additional text
"""
        
        try:
            response = self._make_api_call(prompt, max_tokens=10)
            response = response.strip().upper()
            
            if "SPANISH" in response:
                return "SPANISH"
            elif "ENGLISH" in response:
                return "ENGLISH"
            else:
                return "UNKNOWN"
                
        except Exception as e:
            print(f"언어 검증 오류: {e}")
            return "UNKNOWN"
    
    def extract_spanish_content(self, text: str) -> str:
        """
        이중 언어 콘텐츠에서 스페인어 부분만 추출
        영어와 스페인어가 섞인 팟캐스트에서 스페인어 부분만 분석하도록 함
        """
        if not text:
            return ""
        
        # 스페인어 특징적인 단어들
        spanish_indicators = [
            'hola', 'queridos', 'amigos', 'bienvenidos', 'español', 'episodio',
            'soy', 'desde', 'barcelona', 'reflexionamos', 'situación', 'dramática',
            'mundo', 'entero', 'pandemia', 'coronavirus', 'que', 'está', 'pasando',
            'nuestro', 'sobre', 'viviendo', 'raíz', 'del'
        ]
        
        # 텍스트를 문장 단위로 분할
        sentences = text.split('.')
        spanish_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # 너무 짧은 문장 제외
                continue
            
            # 각 문장에서 스페인어 특징 단어 개수 세기
            spanish_word_count = 0
            words = sentence.lower().split()
            
            for word in words:
                # 구두점 제거
                clean_word = word.strip('.,!?";:()[]')
                if clean_word in spanish_indicators:
                    spanish_word_count += 1
            
            # 스페인어 특징 단어가 2개 이상이면 스페인어 문장으로 간주
            if spanish_word_count >= 2:
                spanish_sentences.append(sentence)
            # 특징 단어가 적어도 스페인어 문자가 있으면 포함
            elif any(char in sentence for char in 'ñáéíóúü¿¡'):
                spanish_sentences.append(sentence)
        
        # 스페인어 문장들을 다시 합치기
        spanish_content = '. '.join(spanish_sentences)
        
        # 만약 추출된 내용이 너무 적으면 원본 텍스트 사용
        if len(spanish_content.strip()) < 100:
            print(f"    📝 스페인어 추출 결과가 부족해서 원본 텍스트 사용")
            return text
        
        print(f"    📝 스페인어 콘텐츠 추출 완료: {len(spanish_content)}자")
        return spanish_content
    
    def is_metadata_only(self, text: str) -> bool:
        """
        텍스트가 메타데이터만 포함하고 있는지 확인
        실제 대화나 내용이 아닌 제목, 설명, 기술적 정보만 있는지 판단
        """
        if not text or len(text.strip()) < 50:
            return True
        
        text_lower = text.lower()
        
        # 메타데이터 특징 키워드들
        metadata_indicators = [
            'podcast', 'episodio', 'episode', 'title', 'description',
            'duration', 'fecha', 'date', 'published', 'autor', 'author',
            'categoria', 'category', 'tags', 'subscribe', 'suscribirse',
            'web:', 'website:', 'email:', 'twitter:', 'instagram:',
            'available on', 'disponible en', 'spotify', 'apple podcasts',
            'google podcasts', 'rss feed', 'feed rss'
        ]
        
        # 실제 내용 특징 키워드들
        content_indicators = [
            'hola', 'bienvenidos', 'hoy vamos', 'en este episodio',
            'quiero hablar', 'vamos a ver', 'como ya sabes',
            'bueno', 'entonces', 'por ejemplo', 'además', 'también'
        ]
        
        metadata_count = sum(1 for indicator in metadata_indicators if indicator in text_lower)
        content_count = sum(1 for indicator in content_indicators if indicator in text_lower)
        
        # 메타데이터 특징이 많고 실제 내용 특징이 적으면 메타데이터로 판단
        return metadata_count >= 3 and content_count <= 1
    
    def analyze_text_type(self, text: str) -> str:
        """
        텍스트 유형을 분석하여 구어체 표현 가능성을 예측
        """
        if not text:
            return "빈 텍스트"
        
        text_lower = text.lower()
        
        # 대화체 특징
        conversational_features = [
            'hola', 'bueno', 'pues', 'entonces', 'o sea', 'sabes',
            'verdad', 'claro', 'por cierto', 'a ver', 'vamos'
        ]
        
        # 정식/공식 특징
        formal_features = [
            'según', 'mediante', 'por tanto', 'sin embargo', 'además',
            'asimismo', 'por consiguiente', 'en consecuencia', 'no obstante'
        ]
        
        # 설명문 특징
        descriptive_features = [
            'descripción', 'resumen', 'tema', 'sobre', 'acerca de',
            'información', 'datos', 'estadísticas'
        ]
        
        conv_score = sum(1 for feature in conversational_features if feature in text_lower)
        formal_score = sum(1 for feature in formal_features if feature in text_lower)
        desc_score = sum(1 for feature in descriptive_features if feature in text_lower)
        
        if conv_score >= 3:
            return "대화체/비공식 (구어체 표현 가능성 높음)"
        elif formal_score >= 2:
            return "정식/공식적 (구어체 표현 가능성 낮음)"
        elif desc_score >= 2:
            return "설명문/메타데이터 (구어체 표현 가능성 매우 낮음)"
        else:
            return "혼합형 (구어체 표현 가능성 보통)"
    
    def predict_colloquial_likelihood(self, text: str) -> str:
        """
        텍스트에서 구어체 표현이 발견될 가능성을 예측
        """
        if not text:
            return "없음 (빈 텍스트)"
        
        text_lower = text.lower()
        
        # 구어체 표현 지표들
        colloquial_indicators = [
            'bueno', 'pues', 'entonces', 'o sea', 'sabes', 'verdad',
            'claro', 'por cierto', 'a ver', 'vamos', 'oye', 'mira',
            'que tal', 'como va', 'vale', 'está bien', 'de acuerdo'
        ]
        
        # 질문 형태 (구어체에서 흔함)
        question_patterns = ['¿', '?', 'qué', 'cómo', 'dónde', 'cuándo', 'por qué']
        
        # 감탄사나 간투사
        interjections = ['¡', '!', 'oh', 'ah', 'eh', 'uf', 'ay']
        
        colloquial_score = sum(1 for indicator in colloquial_indicators if indicator in text_lower)
        question_score = sum(1 for pattern in question_patterns if pattern in text_lower)
        interjection_score = sum(1 for interjection in interjections if interjection in text_lower)
        
        total_score = colloquial_score + question_score + interjection_score
        
        if total_score >= 5:
            return "높음 (5+ 지표)"
        elif total_score >= 3:
            return "보통 (3-4 지표)"
        elif total_score >= 1:
            return "낮음 (1-2 지표)"
        else:
            return "매우 낮음 (0 지표)"