#!/usr/bin/env python3
"""
LLM-based Spanish content analyzer using ChatGPT API.
ChatGPT API를 사용한 스페인어 콘텐츠 분석기
"""

import os
import json
import requests
import time
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
        
        # 텍스트가 너무 길면 처음 2000자만 사용
        if len(transcript) > 2000:
            transcript = transcript[:2000] + "..."
        
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
- Question tags: ¿verdad?, ¿no?, ¿sabes?
- Informal transitions: por cierto, a propósito, además
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
    
    def analyze_article_grammar(self, article_content: str, difficulty: str = "B2") -> List[str]:
        """
        Analyze grammar structures in article content using LLM
        기사 내용의 문법 구조 분석
        """
        if not article_content:
            return []
        
        # 텍스트가 너무 길면 처음 1500자만 사용
        if len(article_content) > 1500:
            article_content = article_content[:1500] + "..."
        
        prompt = f"""
Analyze this Spanish article and identify 3-4 specific grammar structures suitable for {difficulty} level learners.

For each grammar point, provide:
1. The exact sentence from the text where it appears
2. The specific grammar structure used in Korean
3. The CEFR level of that structure
4. A brief explanation in Korean

Article content:
{article_content}

Please provide exactly 3-4 grammar points in this format:
- 문장: "exact sentence from text"
- 문법: Korean grammar term
- 레벨: CEFR level (A1, A2, B1, B2, C1, C2)
- 설명: Brief Korean explanation

Example format:
- 문장: "Si hubiera tenido más tiempo, habría terminado el proyecto."
- 문법: 접속법 과거완료
- 레벨: C1
- 설명: 과거의 비현실적 상황과 그 결과를 표현하는 구조

Focus on grammar structures appropriate for {difficulty} level such as:
- B1: 현재/과거 시제, ser vs estar, 재귀동사
- B2: 접속법 현재/과거, 조건법, 완료 시제
- C1: 접속법 완료, 복합 조건문, 수동태

Return only the grammar points in the exact format above, no additional text.
"""
        
        response = self._make_api_call(prompt, max_tokens=600)
        
        if not response:
            return []
        
        # 응답에서 문법 포인트들 추출하고 새로운 형식으로 변환
        grammar_points = []
        lines = response.split('\n')
        
        current_point = {}
        for line in lines:
            line = line.strip()
            if line.startswith('- 문장:'):
                if current_point:  # 이전 포인트 저장
                    if all(key in current_point for key in ['문장', '문법', '레벨']):
                        # 새로운 형식으로 변환: "이 문장에는 접속법 과거가 쓰이고 있다 (B2): '문장' - 설명"
                        sentence = current_point['문장']
                        grammar = current_point['문법']
                        level = current_point['레벨']
                        explanation = current_point.get('설명', '')
                        
                        if len(sentence) > 80:
                            sentence = sentence[:80] + "..."
                        
                        point_text = f"이 문장에는 {grammar}가 쓰이고 있다 ({level}): '{sentence}'"
                        if explanation:
                            point_text += f" - {explanation}"
                        
                        grammar_points.append(point_text)
                current_point = {'문장': line[6:].strip().strip('"')}
            elif line.startswith('- 문법:'):
                current_point['문법'] = line[6:].strip()
            elif line.startswith('- 레벨:'):
                current_point['레벨'] = line[6:].strip()
            elif line.startswith('- 설명:'):
                current_point['설명'] = line[6:].strip()
        
        # 마지막 포인트 저장
        if current_point and all(key in current_point for key in ['문장', '문법', '레벨']):
            sentence = current_point['문장']
            grammar = current_point['문법']
            level = current_point['레벨']
            explanation = current_point.get('설명', '')
            
            if len(sentence) > 80:
                sentence = sentence[:80] + "..."
            
            point_text = f"이 문장에는 {grammar}가 쓰이고 있다 ({level}): '{sentence}'"
            if explanation:
                point_text += f" - {explanation}"
            
            grammar_points.append(point_text)
        
        return grammar_points[:4]  # 최대 4개 반환
    
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