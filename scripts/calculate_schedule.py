#!/usr/bin/env python3
"""
Calculate learning phase and schedule based on current date.
"""
import os
from datetime import datetime, timedelta

def main():
    # 학습 시작일 (2025-07-01)
    start_date = datetime(2025, 7, 1)
    current_date = datetime.now()

    # 주차 계산
    week_num = (current_date - start_date).days // 7 + 1
    weekday = current_date.weekday()  # 0=월요일

    # 독해 소스 결정
    if week_num <= 2:
        reading_source = "20minutos"
        reading_url = "https://www.20minutos.es/"
        reading_difficulty = "B2"
    elif week_num <= 4:
        reading_source = "El País 단신"
        reading_url = "https://elpais.com/"
        reading_difficulty = "B2"
    else:
        reading_source = "El País 사설"
        reading_url = "https://elpais.com/opinion/"
        reading_difficulty = "C1"
        
    # 팟캐스트 일정 (RSS 피드와 Apple Podcasts 링크)
    podcast_schedule = {
        0: {
            "name": "Hoy Hablamos",
            "rss": "https://feeds.feedburner.com/hoyhablamos",
            "apple_base": "https://podcasts.apple.com/kr/podcast/hoy-hablamos-podcast-diario-para-aprender-español-learn/id1201483158",
            "region": "스페인",
            "backup_url": "https://www.hoyhablamos.com/"
        },
        1: {
            "name": "Radio Ambulante", 
            "rss": "https://feeds.npr.org/510311/podcast.xml",
            "apple_base": "https://podcasts.apple.com/kr/podcast/radio-ambulante/id527614348",
            "region": "중남미",
            "backup_url": "https://radioambulante.org/"
        },
        2: {
            "name": "Advanced Spanish",
            "rss": "https://feeds.buzzsprout.com/1829091.rss", 
            "apple_base": "https://podcasts.apple.com/kr/podcast/advanced-spanish-podcast-español-avanzado/id1632291264",
            "region": "스페인",
            "backup_url": "https://www.spanishlanguagecoach.com/podcast/"
        },
        3: {
            "name": "Radio Ambulante",
            "rss": "https://feeds.npr.org/510311/podcast.xml",
            "apple_base": "https://podcasts.apple.com/kr/podcast/radio-ambulante/id527614348", 
            "region": "중남미",
            "backup_url": "https://radioambulante.org/"
        },
        4: {
            "name": "DELE Podcast",
            "rss": "https://anchor.fm/s/f4f4a4f0/podcast/rss",
            "apple_base": "https://podcasts.apple.com/us/podcast/examen-dele/id1705001626",
            "region": "스페인", 
            "backup_url": "https://anchor.fm/examen-dele"
        }
    }

    podcast_info = podcast_schedule.get(weekday, podcast_schedule[0])

    # GitHub Actions 환경변수로 출력
    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write(f"week_num={week_num}\n")
        f.write(f"reading_source={reading_source}\n")
        f.write(f"reading_url={reading_url}\n")
        f.write(f"reading_difficulty={reading_difficulty}\n")
        f.write(f"podcast_name={podcast_info['name']}\n")
        f.write(f"podcast_rss={podcast_info['rss']}\n")
        f.write(f"podcast_apple_base={podcast_info['apple_base']}\n")
        f.write(f"podcast_region={podcast_info['region']}\n")
        f.write(f"podcast_backup={podcast_info['backup_url']}\n")
        f.write(f"date={current_date.strftime('%Y-%m-%d')}\n")
        f.write(f"weekday_name={['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일'][weekday]}\n")

if __name__ == "__main__":
    main()
