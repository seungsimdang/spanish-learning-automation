#!/usr/bin/env python3
"""
Test script for alternative finding logic
"""
import os
import sys
import subprocess

def test_alternative_finding():
    """Test the alternative finding logic"""
    print("=== Alternative Finding Test ===")
    
    # Set up test environment variables
    test_env = os.environ.copy()
    test_env.update({
        'NOTION_TOKEN': 'test_token',
        'NOTION_DATABASE_ID': 'test_db_id',
        'READING_SOURCE': '20minutos',
        'PODCAST_NAME': 'Test Podcast',
        'PODCAST_RSS': 'https://www.hoyhablamos.com/podcast.rss',
        'PODCAST_APPLE_BASE': 'https://podcasts.apple.com/kr/podcast/hoy-hablamos-podcast-diario-para-aprender-español-learn/id1201483158',
        'WEEKDAY_NAME': '월요일',
        'FORCE_ALTERNATIVE': 'true',
        'GITHUB_OUTPUT': '/tmp/test_output.txt'
    })
    
    print("1. Testing collect_materials.py with alternative mode...")
    try:
        result = subprocess.run([
            sys.executable,
            'scripts/collect_materials.py'
        ], env=test_env, capture_output=True, text=True, timeout=30)
        
        print("Exit code:", result.returncode)
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
    except subprocess.TimeoutExpired:
        print("Test timed out")
    except Exception as e:
        print(f"Test error: {e}")
    
    print("\n2. Testing create_notion_pages.py...")
    try:
        # Set up minimal test environment for create_notion_pages.py
        test_env_notion = test_env.copy()
        test_env_notion.update({
            'ARTICLE_TITLE': 'Test Article',
            'ARTICLE_URL': 'https://example.com/test',
            'ARTICLE_CATEGORY': 'Test Category',
            'ARTICLE_VOCABULARY': 'test, vocabulary',
            'ARTICLE_DIFFICULTY': 'B2',
            'ARTICLE_MEMO': 'Test memo'
        })
        
        result = subprocess.run([
            sys.executable,
            'scripts/create_notion_pages.py'
        ], env=test_env_notion, capture_output=True, text=True, timeout=30)
        
        print("Exit code:", result.returncode)
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
    except subprocess.TimeoutExpired:
        print("Test timed out")
    except Exception as e:
        print(f"Test error: {e}")

if __name__ == "__main__":
    test_alternative_finding()
