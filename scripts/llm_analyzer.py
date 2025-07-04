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
        if not transcript:
            return []
        
        # 텍스트 정리 및 인코딩 문제 해결
        transcript = self.clean_text(transcript)
        
        # 정리된 텍스트가 비어있거나 너무 짧으면 건너뛰기
        if len(transcript.strip()) < 50:
            print(f"    ⚠️  정리된 텍스트가 너무 짧습니다: {len(transcript.strip())}자")
            return []
        
        # 텍스트가 너무 길면 처음 2000자만 사용
        if len(transcript) > 2000:
            transcript = transcript[:2000] + "..."
        
        print(f"    📝 정리된 텍스트 미리보기: {transcript[:100]}...")
        
        prompt = f"""
You are analyzing Spanish text to find ACTUAL colloquial expressions that appear in the text.

CRITICAL RULE: Only extract expressions that are ACTUALLY PRESENT in the provided text. Do not suggest or create expressions that are not in the text.

Text to analyze:
{transcript}

Instructions:
1. Read the text carefully
2. Look for actual colloquial expressions, informal phrases, or conversational elements that appear in the text
3. If the text is formal and contains no colloquial expressions, return "NO_COLLOQUIAL_EXPRESSIONS_FOUND"
4. If you find expressions, format them as: "expression" → Korean translation (usage context)

Examples of what to look for (ONLY if they actually appear in the text):
- Conversational fillers: o sea, bueno, pues, entonces
- Question tags: verdad, no, sabes
- Informal transitions: por cierto, a proposito, ademas
- Opinion expressions: me parece que, creo que, la cosa es que

Response format (only if expressions are found in the text):
- "actual_expression_from_text" → Korean meaning (context)

If no colloquial expressions are found in this formal text, respond with: NO_COLLOQUIAL_EXPRESSIONS_FOUND
"""
        
        response = self._make_api_call(prompt, max_tokens=400)
        
        if not response:
            return []
        
        # "NO_COLLOQUIAL_EXPRESSIONS_FOUND" 응답 처리
        if "NO_COLLOQUIAL_EXPRESSIONS_FOUND" in response:
            print(f"    📝 LLM 분석 결과: 텍스트에 구어체 표현이 없음")
            return []
        
        # 응답에서 표현들 추출
        expressions = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('-') and '"' in line and '→' in line:
                try:
                    # "- "expression" → meaning (context)" 형식 파싱
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
                            expressions.append(f"{expression} ({meaning})")
                except Exception as e:
                    print(f"구어체 표현 파싱 오류: {e}")
                    continue
        
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
        colloquial_goal = f"구어체 표현 {colloquial_count}개" if colloquial_count > 0 else "구어체 표현"
        
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
            # 기본 목표 반환 (구어체 표현 개수 반영)
            if colloquial_count > 0:
                return [
                    f"팟캐스트 주제 관련 핵심 어휘 5-7개 학습 ({difficulty} 수준)",
                    f"분석된 구어체 표현 {colloquial_count}개 정리 및 활용",
                    "자연스러운 발음과 억양 패턴 학습"
                ]
            else:
                return [
                    f"팟캐스트 주제 관련 어휘 학습 ({difficulty} 수준)",
                    "스페인어 구어체 표현 파악 및 이해",
                    "자연스러운 발음과 억양 패턴 학습"
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
        return goals[:4] if goals else [
            f"팟캐스트 주제 관련 어휘 학습 ({difficulty} 수준)",
            "스페인어 구어체 표현 파악 및 이해",
            "자연스러운 발음과 억양 패턴 학습"
        ]