import requests
from bs4 import BeautifulSoup
import time
from pymongo import MongoClient
from datetime import datetime

def connect_mongodb():
    """MongoDB 연결을 설정하고 데이터베이스와 컬렉션을 반환합니다."""
    client = MongoClient('mongodb://admin:adminpassword@localhost:27017/')
    db = client['insanalyzedb']
    collection = db['executive_order']
    return client, collection

def get_order_content(url):
    """행정명령의 상세 내용을 가져옵니다."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 날짜 가져오기
        time_tag = soup.find('time')
        if time_tag and 'datetime' in time_tag.attrs:
            order_date = datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
        else:
            order_date = datetime.now()
            
        # 내용 가져오기
        main_content = soup.find('main')
        if main_content:
            # 각 p 태그의 텍스트를 리스트로 저장
            paragraphs = [p.get_text().strip() for p in main_content.find_all('p') if p.get_text().strip()]
            # 문단을 구분하여 하나의 문자열로 합치기
            content = '\n\n'.join(paragraphs)
        else:
            content = ""
            
        return order_date, content
        
    except Exception as e:
        print(f"상세 내용 가져오기 실패: {e}")
        return datetime.now(), ""

def get_executive_orders(collection):
    """행정명령을 가져와서 MongoDB에 저장합니다."""
    base_url = "https://www.whitehouse.gov/presidential-actions"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print("=== 백악관 행정명령 목록 ===\n")
    order_count = 0
    
    try:
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 행정명령 목록을 찾습니다
        orders = soup.find_all('h2', class_='wp-block-post-title')
        
        for order in orders:
            title = order.find('a').get_text().strip()
            
            # 이미 저장된 행정명령인지 확인
            existing_order = collection.find_one({'title': title})
            if existing_order:
                print(f"\n이미 저장된 행정명령을 발견했습니다: {title}")
                break
                
            order_count += 1
            link = order.find('a')['href']
            
            # 상세 내용 가져오기
            order_date, content = get_order_content(link)
            
            # MongoDB에 저장할 데이터 준비
            order_data = {
                'title': title,
                'link': link,
                'created_at': datetime.now(),
                'order_date': order_date,
                'content': content,
                'source': 'whitehouse.gov'
            }
            
            # MongoDB에 저장
            collection.insert_one(order_data)
            print(f"{order_count}. {title}")
        # 페이지 간 대기
        time.sleep(1)
            
    except requests.RequestException as e:
        print(f"에러 발생: {e}")
    
    print(f"\n총 {order_count}개의 행정명령이 저장되었습니다.")
    return order_count

def print_first_order(collection):
    """첫 번째 행정명령의 내용을 출력합니다."""
    first_order = collection.find_one(sort=[('created_at', -1)])
    if first_order:
        print("\n=== 가장 최근 행정명령 내용 ===")
        print(f"제목: {first_order['title']}")
        print(f"날짜: {first_order['order_date']}")
        print("\n내용:")
        # print(first_order['content'])
        # 문단을 구분하여 출력
        paragraphs = first_order['content'].split('\n\n')
        for i, paragraph in enumerate(paragraphs, 1):
            print(f"\n[문단 {i}]")
            print(paragraph)
        print("\n" + "="*50 + "\n")
    else:
        print("저장된 행정명령이 없습니다.")

def main():
    """행정명령을 수집하고 출력하는 메인 함수입니다."""
    print(f"\n[{datetime.now()}] 행정명령 수집 시작")
    
    # MongoDB 연결
    client, collection = connect_mongodb()
    
    try:
        # 행정명령 수집
        get_executive_orders(collection)
        
        # 첫 번째 행정명령 출력
        print_first_order(collection)
        
    finally:
        # MongoDB 연결 종료
        client.close()
    
    print(f"[{datetime.now()}] 행정명령 수집 완료")

def run_scheduler():
    """스케줄러를 실행합니다."""
    print("스케줄러가 시작되었습니다.")
    print("매일 자정에 행정명령을 수집합니다.")
    
    # 자정에 실행하도록 스케줄 설정
    schedule.every().day.at("00:00").do(main)
    
    # 스케줄러 실행
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 스케줄 확인
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--scheduler":
        # 스케줄러 모드로 실행
        run_scheduler()
    else:
        # 즉시 실행
        main()
    