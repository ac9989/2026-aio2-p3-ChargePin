"""Generate editable SVG screen specifications from the current Frontend implementation."""
from pathlib import Path
from html import escape
import textwrap, xml.etree.ElementTree as ET, zipfile, json
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'screen-spec'
OUT.mkdir(exist_ok=True)
INK='#202830'; MUTED='#657180'; LINE='#D7DFE7'; DARK='#292E35'; AMBER='#FFBC42'
def rect(x,y,w,h,fill='white',stroke='none',r=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}"/>'
def txt(x,y,value,size=18,color=INK,weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(str(value))}</text>'
def lines(x,y,value,size=17,color=MUTED,width=48,leading=27):
    return ''.join(txt(x,y+i*leading,line,size,color) for i,line in enumerate(textwrap.wrap(value,width=width,break_long_words=True) or ['']))
def tag(x,y,label,fill='#F2F4F6',color=MUTED):
    w=max(70,len(label)*14+22)
    return rect(x,y,w,28,fill,r=14)+txt(x+11,y+20,label,13,color,650)
def num(n,x,y):
    return f'<circle cx="{x}" cy="{y}" r="15" fill="{AMBER}" stroke="{DARK}"/>'+f'<text x="{x}" y="{y+5}" text-anchor="middle" font-size="14" font-weight="750" fill="{DARK}">{n}</text>'
def button(x,y,w,label,selected=True):
    return rect(x,y,w,42,DARK if selected else 'white',DARK if selected else LINE,10)+f'<text x="{x+w/2}" y="{y+27}" text-anchor="middle" font-size="16" font-weight="650" fill="{ "white" if selected else INK}">{escape(label)}</text>'
def inputbox(x,y,w,label):
    return rect(x,y,w,44,'#F3F5F7',r=10)+txt(x+15,y+28,label,15,MUTED)
def header(admin=False,active=0):
    bg=DARK if admin else 'white'
    a=rect(0,0,1440,150 if admin else 110,bg)
    a+=rect(28,24,48,48,DARK if not admin else '#41474F',r=15)
    a+='<path d="M55 30 40 52H51L47 67 63 45H53Z" fill="url(#bolt)"/>'
    a+=txt(90,48,'ChargePin 운영 대시보드' if admin else 'ChargePin',24,'white' if admin else INK,750)
    a+=txt(90,72,'서비스 상태 및 운영 이력' if admin else '서울 전기차 충전소 안내',14,'#CED4DA' if admin else MUTED)
    for x,power in [(1290,False),(1350,True)]:
        a+=f'<circle cx="{x+22}" cy="48" r="22" fill="{ "#41474F" if admin else "#F5F7F9"}" stroke="{ "#6A717A" if admin else LINE}"/>'
        if power:
            a+=f'<path d="M{x+22} 34V47 M{x+13} 39 A13 13 0 1 0 {x+31} 39" fill="none" stroke="{ "white" if admin else DARK}" stroke-width="2.5"/>'
        else:
            a+=txt(x+11,56,'⚙',24,'white' if admin else DARK)
    if admin:
        for i,label in enumerate(['운영 개요','서비스 운영','배포 · 감사 이력']):
            x=30+i*180
            a+=txt(x,125,label,17,'white' if i==active else '#CED4DA',650)
            if i==active:a+=rect(x,142,140,3,AMBER)
    else:a+=rect(28,104,1384,1,LINE)
    return a
def card(x,y,w,h,title,subtitle=None):
    a=rect(x,y,w,h,'white',LINE,14)+txt(x+20,y+35,title,19,INK,750)
    if subtitle:a+=txt(x+20,y+63,subtitle,14,MUTED)
    return a
def pending(x,y,w,label):
    return rect(x,y,w,42,'#F3F5F7',r=8)+f'<circle cx="{x+15}" cy="{y+21}" r="3" fill="#96A2AF"/>'+txt(x+29,y+26,label,14,MUTED)
def mapview(x=455,y=130,w=955,h=490):
    a=rect(x,y,w,h,'#EEF2F5',LINE,16)
    for q in range(1,6):
        a+=rect(x+q*w/6,y,12,h,'white')
    for q in range(1,4):a+=rect(x,y+q*h/4,w,10,'white')
    a+=f'<path d="M{x+40} {y+h} L{x+w*.65} {y}" stroke="#DCE7ED" stroke-width="64"/>'
    a+=f'<circle cx="{x+w/2}" cy="{y+h/2}" r="145" fill="#FFBC4212" stroke="{AMBER}" stroke-width="2" stroke-dasharray="6 5"/>'
    a+=tag(x+20,y+20,'카카오 지도 영역 / 도식','#FFFFFF')
    a+=txt(x+15,y+h+28,'선택한 위치 기준 · 카카오 지도 · 충전 상태는 환경공단 API 기준입니다.',14,MUTED)
    return a
def filters():
    a=card(28,130,400,620,'충전 장소 찾기')
    a+=button(48,185,160,'탐색')+button(220,185,160,'AI 챗',False)
    a+=txt(48,263,'검색 반경',16,INK,650)
    for i,label in enumerate(['1 km','3 km','5 km']):a+=button(48+i*110,278,100,label,i==1)
    a+=txt(48,354,'검색 중심',16,INK,650)+inputbox(48,368,350,'장소명 입력 (예: 강남역, 서울시청)')
    a+=txt(48,446,'충전기 타입',16,INK,650)
    a+=inputbox(48,461,350,'')+tag(57,469,'급속 ×',DARK,'white')+tag(147,469,'완속 ×',DARK,'white')
    a+=txt(48,543,'충전소 분류',16,MUTED,650)+inputbox(48,559,350,'전체                        ⌄')
    a+=txt(48,628,'검색 결과에 분류 정보가 있으면 선택할 수 있어요.',13,MUTED)
    a+=button(48,663,350,'충전소 검색')
    return a
def screen_result(x,y,w,name):
    a=card(x,y,w,212,name)
    a+=txt(x+20,y+62,'주소 · API 응답값',13,MUTED)
    a+=tag(x+20,y+77,'급속')+tag(x+100,y+77,'정보 지연','#FFF3D6','#8A5E12')
    for i,(k,v) in enumerate([('이용 시간','API 응답값'),('주차','무료 여부 / 확인 필요'),('이용 제한','API 응답값'),('갱신 시각','보고 시각 / 조회 시각')]):
        a+=txt(x+20,y+128+i*22,k,13,MUTED)+txt(x+w-210,y+128+i*22,v,13,INK)
    return a
def base(code,title,subtitle,screen,rows,notes,index):
    a=f'<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1800" viewBox="0 0 1600 1800"><title>{escape(code+" "+title)}</title><defs><linearGradient id="bolt" x2="0" y2="1"><stop stop-color="#FFD064"/><stop offset=".5" stop-color="#FF8E3C"/><stop offset="1" stop-color="#EC4F51"/></linearGradient></defs><g font-family="Pretendard, Malgun Gothic, sans-serif">'
    a+=rect(0,0,1600,1800,'#F8FAFC')+rect(0,0,1600,136,'#EDF1F5')
    a+=tag(48,30,code,DARK,'white')+txt(170,56,title,30,INK,750)
    a+=txt(48,98,subtitle,17,MUTED)
    a+=rect(48,166,1504,840,'white',LINE,18)
    a+='<g id="screen" transform="translate(80 190)">'+screen+'</g>'
    a+=txt(48,1054,'구성요소 명세',24,INK,750)+txt(1280,1054,'Docker local · 2026.11.05',15,MUTED)
    a+=rect(48,1076,1504,42,DARK,r=8)
    for x,t in [(64,'No'),(126,'구성요소'),(360,'동작 · 표시 규칙'),(1120,'데이터 · API / 상태')]:a+=txt(x,1103,t,15,'white',650)
    yy=1118
    for n,name,rule,api in rows:
        a+=rect(48,yy,1504,68,'white',LINE)
        a+=txt(68,yy+28,n,16,INK,750)+txt(126,yy+28,name,17,INK,650)
        a+=lines(360,yy+25,rule,15,MUTED,47,23)
        a+=lines(1120,yy+25,api,14,MUTED,34,23)
        yy+=68
    a+=txt(48,yy+43,'구현 범위 · 확인 사항',20,INK,750)
    for i,note in enumerate(notes):a+=txt(64,yy+78+i*29,'• '+note,16,MUTED)
    a+=txt(48,1758,'ChargePin / 화면 설계서 1.1 / 로컬 구현 기준 · 화면 속 데이터는 명세용 표기',14,MUTED)
    a+=txt(1480,1758,f'{index:02d}',16,MUTED)
    return a+'</g></svg>'

pages=[]
def add(code,title,sub,screen,rows,notes):pages.append((code,title,base(code,title,sub,screen,rows,notes,len(pages)+1)))
# Overview
a=header()
a+=txt(45,172,'사용자 니즈를 대화로 좁히는 충전소 탐색',30,INK,750)
a+=txt(45,212,'탐색과 AI 챗은 같은 결과 영역을 사용합니다.',18,MUTED)
for x,title,items in [(45,'사용자 흐름',['차지핀 시작하기','접속 코드 입력','탐색 또는 AI 챗','지도 · 충전소 결과']), (510,'운영 흐름',['관리자 접속','톱니바퀴로 화면 전환','운영 개요 / 서비스 운영','배포 · 감사 이력']), (975,'현재 데이터 경계',['지도 · 장소: 카카오','충전 정보: 환경공단','아파트 식별 결과 제외','운영 지표: 연결 대기'])]:
    a+=card(x,260,420,400,title)
    for i,t in enumerate(items):a+=rect(x+20,325+i*70,380,50,'#F3F5F7',r=10)+txt(x+35,357+i*70,t,19,INK,650)
add('00','문서 개요 · 화면 흐름','참고 PDF의 번호 주석·명세표 형식 / 현재 Frontend 소스와 Docker 로컬 실행 기준',a,
[('1','실행 기준','사용자와 운영 화면은 별도 주소 없이 동일 앱 내부에서 전환합니다.','http://localhost:8501'),
('2','표현 규칙','연결 대기, 정보 지연, 확인 필요를 구분하며 운영 수치를 임의로 생성하지 않습니다.','Frontend/app.py'),
('3','편집 방식','화면·텍스트·주석은 벡터 요소입니다. 각 SVG를 Figma 캔버스에 드래그합니다.','SVG / 1600 × 1800'),
('4','기능 상태','현재 동작과 미연결 기능을 각 화면의 확인 사항에 구분했습니다.','API 계약은 api_client.py 기준')],
['참고 PDF의 기존 역할 분할·검색 전 확인 UI는 복제하지 않았습니다.','지도는 카카오 타일 캡처가 아닌 위치 영역 도식입니다. 실측 캡처 문서가 아닙니다.'])
# Login
a=header()+card(370,200,700,370,'차지핀 시작하기')
a+=txt(395,300,'접속 코드',16,INK,650)+inputbox(395,320,650,'접속 코드를 입력해주세요')
a+=button(395,393,650,'접속하기')
a+=num(1,1090,235)+num(2,1065,342)+num(3,1065,414)+num(4,90,30)
add('S00','초기 접속','공통 브랜드 / Pretendard / 화이트 배경 · 차콜 주요 버튼',a,
[('1','시작하기','제목은 “차지핀 시작하기”이며 역할 설명 문구는 표시하지 않습니다.','로그인 전 화면'),
('2','접속 코드','비밀번호 입력 필드. 빈 값은 전송 전에 자연어로 안내합니다.','service_key / 원문 문서 비노출'),
('3','접속하기','서버 인증 성공 후 사용자 화면으로 진입합니다. 실패는 자연어로 표시합니다.','POST /api/v1/auth/login'),
('4','공통 브랜드','번개 아이콘·서비스명·부제 위치와 크기를 사용자·운영 화면에 통일합니다.','서울 전기차 충전소 안내')],
['로그인 키와 토큰은 SVG에 포함하지 않습니다.','기본 진입 시 충전소 검색은 자동 실행하지 않습니다.'])
# Explore
a=header()+filters()+mapview()
a+=num(1,410,260)+num(2,410,354)+num(3,410,446)+num(4,410,543)+num(5,410,684)+num(6,1400,650)
add('S01','탐색 · 직접 검색','검색 반경을 최상단에 배치 / 조건 선택 후 검색 / 최초 진입은 미조회',a,
[('1','검색 반경','1 / 3 / 5 km를 선택합니다. 현재 직접 탐색 기본값은 3 km입니다.','radius_km'),
('2','검색 중심','장소 입력 후 카카오 후보에서 검색 기준 장소를 선택합니다.','POST /api/v1/places/suggest'),
('3','충전기 타입','급속·완속 다중 선택. 선택 태그와 주요 버튼은 차콜입니다.','connector_types: FAST / SLOW'),
('4','충전소 분류','검색 결과에 전달된 시설 분류만 선택할 수 있습니다. 없으면 비활성입니다.','results[].facility_type'),
('5','충전소 검색','선택된 장소와 조건을 보내고 지도·목록을 갱신합니다.','POST /api/v1/search'),
('6','지도 출처','카카오 지도와 환경공단 충전 상태의 출처 안내는 지도 아래에 표시합니다.','Kakao Maps JS / ChargerResult')],
['외부인 이용·주차 요금·출력·커넥터 상세 필터는 현재 탐색 UI에 구현되어 있지 않습니다.','아파트·공동주택으로 이름 또는 시설 분류에서 식별된 결과를 프론트에서 제외합니다.'])
# Chat
a=header()+card(28,130,400,620,'충전 장소 찾기')
a+=button(48,185,160,'탐색',False)+button(220,185,160,'AI 챗')
a+=rect(48,257,350,88,'#F1F4F7',r=12)+lines(64,286,'강남역 주변 충전소 찾아줘',17,INK,18)
a+=rect(48,375,350,112,'#FFF7E6',r=12)+lines(64,404,'강남역 주변 충전소를 찾았어요.',17,INK,18)
a+=inputbox(48,650,350,'메시지 입력')
a+=mapview()
a+=num(1,410,205)+num(2,410,300)+num(3,410,415)+num(4,410,671)
add('S02','AI 챗 · 즉시 검색','조건 해석 후 확인 버튼 없이 검색 / 지도와 목록을 같은 화면에서 갱신',a,
[('1','모드 전환','탐색과 AI 챗을 같은 패널에서 선택합니다. 헤더 위치는 유지합니다.','session_state.mode'),
('2','채팅 입력','사용자 문장을 해석 API로 보냅니다. 현 서버는 규칙 기반 해석입니다.','POST /api/v1/chat/plan'),
('3','자동 실행','확인 대기 응답이면 프론트가 즉시 확인 API를 호출합니다. 장소는 우선 후보를 사용합니다.','POST /api/v1/search/{id}/confirm'),
('4','응답 표시','선택 장소와 결과 수를 안내합니다. 부분 실패는 정상 완료와 구분합니다.','status / results / applied_request')],
['무료·장시간 우선 추천, 대안 사유 설명, 후속 대화 조건 유지는 목표 기능이며 현재 미구현입니다.','장소 후보 확인 경로는 백엔드가 반경을 3 km로 고정합니다. 입력 반경 유지 보완이 필요합니다.'])
# Results
a=header()
a+=txt(28,145,'충전소 결과 · 페이지당 10개',22,INK,750)
for i in range(4):a+=screen_result(28+(i%2)*704,170+(i//2)*238,680,'충전소명 · API 응답값')
a+=button(520,680,90,'이전',False)+txt(655,707,'1 / N',16,MUTED)+button(770,680,90,'다음',False)
a+=num(1,1400,145)+num(2,1385,205)+num(3,1385,435)+num(4,900,700)
add('S03','결과 목록 · 상태 정보','2열 카드 / 10개 단위 페이지 / 목록 내부 스크롤 · 이 화면은 4개 카드만 발췌',a,
[('1','결과 수','프론트 주거시설 제외 및 시설 분류 필터가 적용된 목록의 개수를 표시합니다.','filtered results'),
('2','카드 정보','시설명·주소·시설 유형·급속/완속·직선거리·상태를 표시합니다.','ChargerResult'),
('3','부가 정보','이용시간·무료주차 여부·이용제한·보고 및 조회 시각을 표시합니다.','use_time / parking_free / restriction_detail'),
('4','페이지 이동','한 페이지 10개를 2열로 표시합니다. 이전·다음과 페이지 번호는 가운데 정렬합니다.','result_page / page_size=10')],
['충전기 사용 상태와 주차장 만차는 별도 정보입니다. 주차 만차나 예상 빈자리 시각을 추정하지 않습니다.','시설 코드가 누락되면 아파트 전체를 완전하게 제외할 수 없습니다. 백엔드 코드 매핑 보완 대상입니다.'])
# States
a=header()
states=[('결과 없음','조건에 맞는 충전소를 찾지 못했습니다.','#F3F5F7'),('정보 지연','최근 상태를 확인하기 어렵습니다.','#FFF3D6'),('요청 제한','요청이 많습니다. 잠시 후 다시 시도해 주세요.','#FFF3D6'),('인증 · 권한 오류','접속 정보 또는 접근 권한을 확인해 주세요.','#FDEDEC'),('AI 챗 연결 실패','응답을 받지 못했습니다. 잠시 후 다시 시도해 주세요.','#FDEDEC')]
for i,(title,msg,c) in enumerate(states):
    y=145+i*108;a+=card(28,y,1380,92,title)+rect(270,y+20,1115,52,c,r=8)+txt(290,y+53,msg,17,MUTED)+num(i+1,1388,y+13)
add('S04','시스템 상태 · 시연','번개 아이콘에서 시연 메뉴 호출 / 실제 오류는 API 응답에 따라 안내',a,
[('1','결과 없음','정상 검색 후 결과가 없으면 빈 목록 안내를 표시합니다.','results=[]'),
('2','정보 지연','검증 결과와 출처 상태를 근거로 지연·확인 필요를 구분합니다.','critic_findings / availability'),
('3','요청 제한','API 오류를 자연어로 안내합니다. 현재 시연 메뉴는 boom 응답 표시입니다.','GET /boom/1..5'),
('4','인증 · 권한','접속·운영 접근은 서버 인증 결과를 따릅니다.','401 / 403'),
('5','챗 실패','예외를 대화에 표시하고 확인 질문 없이 재시도 가능한 입력을 유지합니다.','ApiError')],
['시연 응답 표시와 화면 전체 입력 잠금은 구분해야 합니다. 시연 메뉴만으로 전역 입력은 잠기지 않습니다.','본문 문구는 상태별 표현 규칙 예시이며 API 원문을 그대로 노출하지 않습니다.'])
# Admin overview
a=header(True,0)
for i,(k,v) in enumerate([('백엔드','정상 / 연결 불가'),('요청 성공률','연결 대기'),('재시도율','연결 대기'),('최근 배포','연결 대기')]):
    x=28+i*350;a+=card(x,175,330,120,k)+txt(x+20,263,v,24,INK,750)
a+=card(28,315,1380,105,'요청 현황')+pending(48,365,1340,'시계열 지표 연결 대기')
a+=card(28,440,680,195,'외부 연결')
for i,(k,v) in enumerate([('카카오 지도','지도 키 설정 여부'),('카카오 장소','최근 조회 / 호출 이력'),('환경공단 충전기','검색 응답 / 원천 상태 확인'),('캐시','상태 수집 대기')]):
    a+=txt(48,505+i*29,k,14)+txt(400,505+i*29,v,14,MUTED)
a+=card(728,440,680,195,'데이터 품질')+txt(748,512,'최신성 · 누락 · 비정상 값',15,MUTED)+pending(748,554,640,'품질 분포 차트 · 데이터 연결 대기')
a+=card(28,655,1380,100,'최근 운영 이벤트')+pending(48,702,1340,'요청 ID · 발생 시각 · 처리 단계 · 결과 연결 대기')
a+=num(1,1390,128)+num(2,1390,190)+num(3,690,455)+num(4,1390,455)+num(5,1390,668)
add('A01','운영 개요','차콜 헤더·메뉴 / 화이트 본문 / 카드 내부 여백 20 px / 공통 헤더 정렬',a,
[('1','운영 메뉴','운영 개요·서비스 운영·배포 감사 이력. 활성 메뉴에 앰버 밑선을 표시합니다.','session_state.dashboard_navigation'),
('2','핵심 지표','백엔드 상태만 health 응답입니다. 성공률·재시도·최근 배포는 연결 대기입니다.','GET /healthz'),
('3','외부 연결','키 설정과 세션 호출 이력을 표시합니다. 원천 서비스 정상 판정과 구분합니다.','provider_states() / 세션 기반'),
('4','데이터 품질','현재 데이터 집계 연결 대기입니다. 연결 후 차트로 표시할 영역입니다.','운영 집계 API 미구현'),
('5','운영 이벤트','실제 이벤트 수집 경로 연결 전에는 이벤트 수치를 생성하지 않습니다.','운영 로그 API 미구현')],
['화면 도식의 “정상 / 연결 불가”는 상태 종류입니다. 실제 상태 스냅샷을 의미하지 않습니다.','기본 관리자 운영 화면은 하나입니다. 문서에서 관리자 1·2·3 별도 화면을 추가하지 않습니다.'])
# Service
a=header(True,1)
for x,y,w,h,title,body in [(28,175,680,220,'외부 API','지도·장소·환경공단의 설정 및 최근 호출 상태'),(728,175,680,220,'에이전트 · 재시도','Planner · Executor · Critic · Memory Keeper'),(28,415,680,120,'캐시 · 복구','캐시 조회·갱신·Circuit Breaker 연결 대기'),(728,415,680,120,'데이터 품질 · 가드레일','지연·누락·이상값·차단 유형 연결 대기'),(28,555,680,135,'외부 API 응답 시간','응답 시간 추이 · 데이터 연결 대기'),(728,555,680,135,'오류 · 재시도 유형','유형별 건수 차트 · 데이터 연결 대기')]:
    a+=card(x,y,w,h,title)+pending(x+20,y+65,w-40,body)
a+=num(1,690,190)+num(2,1390,190)+num(3,690,430)+num(4,1390,430)+num(5,1390,570)
add('A02','서비스 운영','출처 연결·처리 흐름·복구·품질·오류를 한 화면에서 구분',a,
[('1','외부 API','현재 확인 가능한 키 설정 및 세션 호출 상태를 보여 줍니다.','provider_states()'),
('2','에이전트','에이전트 처리 단계·재시도 원인과 횟수는 수집 API 연결 대상입니다.','에이전트 관측 API 미구현'),
('3','캐시 · 복구','캐시 및 Circuit 상태 수집 전에는 연결 대기를 표시합니다.','캐시 관측 API 미구현'),
('4','품질 · 가드레일','품질과 차단 유형은 원문 대화 없이 집계 데이터로 연결할 영역입니다.','집계 API 미구현'),
('5','차트','응답 시간은 추이, 오류·재시도는 유형별 건수 차트가 적합합니다.','현재 차트 데이터 연결 대기')],
['현재 시각화 영역은 빈 상태 표시입니다. 운영 샘플 수치를 실제 데이터처럼 표시하지 않습니다.','하단 오류·이벤트 영역에는 요청 ID·시각·출처·오류 유형·결과를 연결할 예정입니다.'])
# Deploy
a=header(True,2)
a+=card(28,175,1380,160,'배포 파이프라인')
for i,k in enumerate(['테스트','빌드','이미지','배포','동작 확인']):
    x=48+i*270;a+=txt(x,250,k,17,INK,650)+tag(x,267,'연결 대기')
for i,(title,label) in enumerate([('실행 상세 · 로그','실행 번호 · 브랜치 · 커밋 · 환경 · 시간 · 단계별 로그'),('Docker · AWS 운영 상태','컨테이너 상태 · 이미지 버전 · 재시작 · 배포 환경'),('감사 이력','시각 · 작업자 · 작업 · 대상 · 결과 · 요청 ID')]):
    y=355+i*130;a+=card(28,y,1380,110,title)+pending(48,y+55,1340,label+' · 연결 대기')
a+=num(1,1390,190)+num(2,1390,370)+num(3,1390,500)+num(4,1390,630)
add('A03','배포 · 감사 이력','배포 실행·환경 상태·운영 변경 이력을 구분 / GitHub·AWS 데이터 미연결',a,
[('1','파이프라인','테스트·빌드·이미지·배포·동작 확인을 단계별로 표시할 영역입니다.','GitHub Actions API 미연결'),
('2','실행 상세','실행 정보와 로그는 실제 연동 전까지 연결 대기로 표시합니다.','워크플로 실행 / job 로그'),
('3','배포 환경','로컬 Docker 실행과 AWS 관측 연결 여부를 혼동하지 않습니다.','Docker 실행 중 / AWS 관측 미연결'),
('4','감사 이력','운영 변경 이벤트만 조회하는 영역입니다. 현재 수집 경로는 미연결입니다.','감사 API 미구현')],
['로컬 Docker가 실행된다고 AWS 배포가 완료된 것은 아닙니다.','재배포·캐시 갱신·권한 변경 같은 쓰기 작업은 현재 이 화면에 구현되어 있지 않습니다.'])
for code,title,svg in pages:
    ET.fromstring(svg)
    (OUT/f'{code}_ChargePin.svg').write_text(svg,encoding='utf-8')
readme='''# ChargePin 화면 설계서 1.1

기준: 2026-11-05 / Docker 로컬 앱 http://localhost:8501 / Frontend/app.py 및 api_client.py.

## Figma에서 보기
1. Pretendard를 설치하면 로컬 앱과 같은 글꼴로 편집하기 편합니다.
2. SVG 파일들을 Figma 캔버스에 드래그합니다.
3. 각 파일은 1600 × 1800이며 화면, 번호 주석, 동작·API 표가 포함됩니다.
4. 프레임별로 나눠 보려면 파일 하나씩 가져오세요.

SVG는 스크린샷을 붙인 이미지가 아니라 텍스트와 도형으로 재구성한 설계도입니다.
참고 PDF의 상단 화면 / 하단 명세표 양식을 따르며, 색상과 기능은 현재 로컬 구현을 기준으로 했습니다.
카카오 지도는 도식입니다. 지도 타일과 실제 충전소 조회값은 복제하지 않았습니다.
명세용 예시를 운영 실측 데이터로 사용하지 마세요.

## 화면 목록
'''+''.join(f'- {code}: {title}\n' for code,title,_ in pages)+'''
## 현재 구현과 목표 기능
- 구현: 직접 탐색, 채팅 즉시 검색, 카카오 지도, 상태/주차 부가정보, 주거시설 식별 제외, 2열 10개 목록.
- 제한: 시설 코드 매핑이 미완성이므로 모든 아파트를 완벽히 제외하지 못합니다.
- 제한: 채팅 장소 후보 경로의 반경은 서버에서 3 km로 고정됩니다.
- 미구현: 대화 문맥 유지, 무료/장시간 우선순위와 대안 사유 추천, 상세 출력/커넥터 필터.
- 미연결: 운영 시계열·품질 집계·이벤트·배포/감사 로그·AWS 관측.
- 시연: 번개 메뉴는 boom 응답을 표시하며 전역 입력 잠금을 구현한 것은 아닙니다.

접속 코드, API 키, 토큰은 포함하지 않았습니다. 앱 소스와 백엔드는 변경하지 않았습니다.
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')
zip_path=ROOT/'ChargePin_screen-spec_1.1.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.glob('*.svg')):z.write(p,p.name)
    z.write(OUT/'README.md','README.md')
print(json.dumps({'pages':len(pages),'zip':str(zip_path),'output':str(OUT)},ensure_ascii=False))
