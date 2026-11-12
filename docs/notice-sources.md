# 서울과학기술대학교 공지사항 출처 정리

> 조사일: 2026-11-12 · 조사 범위: 본부 포털, 학부 단과대학·학과, 학생 관련 지원기관 사이트
> 각 게시판에 실제로 접속해 목록이 열리는지, 최근 글이 언제 올라왔는지 확인했다.

## 1. 한눈에 보기

- 공지가 올라오는 곳은 **본부(www) → 단과대학 → 학과/전공** 3단계와, 그 옆의 **지원기관**(취업진로본부, 국제교류처, 생활관 등)이다.
- 학과 사이트는 거의 모두 `학과명.seoultech.ac.kr` 형태의 별도 서브도메인이고, 대부분 같은 CMS를 쓴다. (예외: 건축학전공)
- 본부 **대학공지사항**에는 단과대·부서 공지가 `[공과대학]`, `[국제교류처]`처럼 말머리를 달고 다시 올라오는 경우가 많다. 반대로 학과 공지 중 상당수는 본부 공지를 옮겨 온 것이다. → **중복 제거가 꼭 필요하다.**

### 상태 표기

| 표기 | 의미 (조사일 기준) |
|---|---|
| **활발** | 최근 30일 안에 새 글 있음 (2026-10-13 이후) |
| **가끔** | 최근 글이 1~6개월 전 |
| **휴면** | 최근 글이 6개월보다 오래됐거나 게시판이 비어 있음 |

## 2. 위계 트리

```text
서울과학기술대학교
├── 본부 (www.seoultech.ac.kr/service/info)
│   ├── 대학공지사항 ............ /notice     (전 부서·단과대 공지 집결)
│   ├── 학사공지 ................ /matters    (탭: 학사공지 / 학점교류)
│   ├── 장학공지 ................ /janghak    (탭: 장학공지 / 근로장학)
│   ├── 대학원공지 .............. /graduate
│   ├── 취업공지 ................ /job        (탭: 취업공지 / 현장실습)
│   └── 채용정보 ................ /recruit    (교직원 채용, 학생 대상 아님)
│
├── 지원기관
│   ├── 취업진로본부 ............ job.seoultech.ac.kr
│   ├── 현장실습지원센터 ........ internship.seoultech.ac.kr
│   ├── 창업지원단 .............. sssf.seoultech.ac.kr
│   ├── 국제교류처 .............. global.seoultech.ac.kr
│   ├── 생활관 .................. housing.seoultech.ac.kr  (domi. 로 접속해도 이동)
│   ├── 학생상담센터 ............ counsel.seoultech.ac.kr
│   ├── 정보전산원 .............. itc.seoultech.ac.kr
│   ├── ST나눔공헌단 ............ serve.seoultech.ac.kr
│   ├── 혁신융합대학사업단(더불아이) coss.seoultech.ac.kr
│   ├── 지식재산교육선도대학사업단 ipe.seoultech.ac.kr
│   └── 일반대학원 .............. gsp.seoultech.ac.kr
│
└── 단과대학
    ├── 공과대학 ................ engineer
    │   ├── 기계시스템공학부 .... mechsys (안내 페이지만 있음, 공지 없음)
    │   │   ├── 지능형로봇전공 .. ir
    │   │   └── 미래자동차전공 .. car
    │   ├── 기계공학과 .......... mech
    │   ├── 안전공학과 .......... safety
    │   ├── 신소재공학과 ........ mse
    │   ├── 건설시스템공학과 .... civil
    │   ├── 건축학부
    │   │   ├── 건축공학전공 .... architecture
    │   │   └── 건축학전공 ...... archidesign  (※ 다른 CMS)
    │   ├── [계약] 건축기계설비공학과 ebse
    │   ├── 기계시스템디자인공학과 (~2032 존속) msd
    │   └── 기계·자동차공학과 (~2032 존속) .... mae
    │
    ├── 정보통신대학 ............ ice
    │   ├── 전기정보공학과 ...... eie
    │   ├── 전자공학과 .......... ee
    │   ├── 컴퓨터공학과 ........ computer
    │   └── 스마트ICT융합공학과 . icte
    │
    ├── 에너지바이오대학 ........ nature
    │   ├── 화공생명공학과 ...... che
    │   ├── 환경공학과 .......... enviro
    │   ├── 식품생명공학과 ...... food
    │   ├── 정밀화학과 .......... fchem
    │   ├── 스포츠과학과 ........ sports
    │   ├── 안경광학과 .......... optometry
    │   ├── 바이오메디컬학과 .... bms
    │   └── 양자융합물리학과 .... physics
    │
    ├── 조형대학 ................ and
    │   ├── 디자인학과
    │   │   ├── 산업디자인전공 .. id
    │   │   └── 시각디자인전공 .. vd
    │   ├── 도예학과 ............ ceramics
    │   ├── 금속공예디자인학과 .. metalartdesign
    │   └── 조형예술학과 ........ fineart
    │
    ├── 인문사회대학 ............ human
    │   ├── 행정학과 ............ pa
    │   ├── 영어영문학과 ........ eng
    │   └── 문예창작학과 ........ writing-creative
    │
    ├── 기술경영융합대학 ........ sgc
    │   ├── 산업공학과
    │   │   ├── 산업정보시스템전공 iise
    │   │   └── ITM전공 ......... itm
    │   ├── MSDE학과 ............ msde
    │   └── 경영학과
    │       ├── 경영학전공 ...... biz
    │       └── 글로벌테크노경영전공 gtm
    │
    ├── 미래융합대학 (재직자/성인학습자) m-disciplinary
    │   ├── 융합기계공학과 ...... cme
    │   ├── 건설환경융합공학과 .. civil-environmental
    │   ├── 헬스피트니스학과 .... wellness
    │   ├── 문화예술학과 ........ cab
    │   ├── 영어과 .............. engculture
    │   ├── 벤처경영학과 ........ v-biz
    │   └── 정보통신융합공학과 .. comm
    │
    ├── 창의융합대학 ............ cccs
    │   ├── 인공지능응용학과 .... aai
    │   ├── 지능형반도체공학과 .. dse
    │   └── 미래에너지융합학과 .. future-energy
    │
    ├── 교양대학 ................ liberal
    │   └── ST자유전공 .......... liberal/specialty
    │
    └── 국제대학 ................ ic
        ├── 글로벌한국어문화학과 gsklc
        ├── 글로벌IT컨버전스학과 gitc
        └── AI·미디어학과 ....... aimedia
```

> 트리의 짧은 이름은 서브도메인이다. 예) `computer` → `https://computer.seoultech.ac.kr`

## 3. 게시판 상세 목록

모든 URL은 목록 페이지 기준이다. "최근 글"은 조사 당시 목록 첫 페이지에서 본 가장 최근 날짜이다. (상단 고정 공지 때문에 실제 최신 글과 약간 다를 수 있다.)

### 3.1 본부 — `https://www.seoultech.ac.kr`

| 게시판 | URL | bnum | 최근 글 | 상태 | 비고 |
|---|---|---|---|---|---|
| 대학공지사항 | /service/info/notice/ | 4691 | 2026-11-12 | 활발 | 말머리로 출처 부서 표시 |
| 학사공지 | /service/info/matters/ | 6112 (학사), 57139 (학점교류) | 2026-11-11 | 활발 | 탭 구조 |
| 장학공지 | /service/info/janghak/ | 5233 (장학), 57138 (근로장학) | 2026-11-11 | 활발 | 탭 구조 |
| 대학원공지 | /service/info/graduate/ | 56589 | 2026-11-10 | 활발 | |
| 취업공지 | /service/info/job/ | 57925 (취업), 57926 (현장실습) | 2026-11-10 | 활발 | 탭 구조 |
| 채용정보 | /service/info/recruit/ | 3601 | 2026-11-12 | 활발 | 교직원 채용이라 학생 대상에서 제외 검토 |

### 3.2 지원기관

| 기관 | 게시판 | URL | 최근 글 | 상태 | 비고 |
|---|---|---|---|---|---|
| 취업진로본부 | 공지사항 | https://job.seoultech.ac.kr/program/board | 2026-11-10 | 활발 | bnum 57925 = 본부 취업공지와 **같은 게시판** |
| 취업진로본부 | 일반채용 | https://job.seoultech.ac.kr/employment/general | 2026-11 | 활발 | 일반 게시판 형식이 아님 (bnum 없음) |
| 취업진로본부 | 채용행사 | https://job.seoultech.ac.kr/employment/event | 2026-06-26 | 가끔 | 위와 같음 |
| 취업진로본부 | 추천채용 | https://job.seoultech.ac.kr/employment/recommen | – | 확인 필요 | 로그인이 필요하거나 JS로 렌더링될 가능성 |
| 현장실습지원센터 | 공지사항 | https://internship.seoultech.ac.kr/bbs/board | 2026-11-09 | 활발 | bnum 57926 = 본부 현장실습 탭과 **같은 게시판** |
| 창업지원단 | 공지사항 | https://sssf.seoultech.ac.kr/community/notice | 2026-11-11 | 활발 | |
| 국제교류처 | Notice | https://global.seoultech.ac.kr/notice/notice | 2026-10-30 | 활발 | 여러 bnum (58432~58435) 탭 구조 |
| 생활관 | 공지사항 | https://housing.seoultech.ac.kr/information/notice | 2026-11-09 | 활발 | |
| 학생상담센터 | 공지사항 | https://counsel.seoultech.ac.kr/notice/notice | 2026-11-09 | 활발 | |
| 일반대학원 | 공지/소식 | https://gsp.seoultech.ac.kr/i_plaza/notice | 2026-11-10 | 활발 | |
| 혁신융합대학사업단 | 공지사항 | https://coss.seoultech.ac.kr/community/notice | 2026-09-30 | 가끔 | |
| 정보전산원 | 공지사항 | https://itc.seoultech.ac.kr/help/notice | 2026-08-25 | 가끔 | 학생 관련은 일부 |
| ST나눔공헌단 | 공지사항 | https://serve.seoultech.ac.kr/bbs/notice | 2026-02-13 | 휴면 | 봉사활동 관련 |
| 지식재산교육선도대학사업단 | 공지사항 | https://ipe.seoultech.ac.kr/notice/bbs | 2019-10-11 | 휴면 | 수집 대상에서 제외 권장 |

### 3.3 공과대학

| 학과/전공 | 게시판 | URL | 최근 글 | 상태 |
|---|---|---|---|---|
| (단과대) 공과대학 | 공지 | https://engineer.seoultech.ac.kr/community/notice | 2026-10-24 | 활발 |
| 지능형로봇전공 | 학부공지 | https://ir.seoultech.ac.kr/bach/notice | 2026-11-10 | 활발 |
| | 대학원공지 | https://ir.seoultech.ac.kr/bach/grad_notice | 2026-10-26 | 활발 |
| | 취업정보 | https://ir.seoultech.ac.kr/info/employment | 2026-10-19 | 활발 |
| 미래자동차전공 | 공지사항 | https://car.seoultech.ac.kr/bach/notice | 2026-10-28 | 활발 |
| | 취업정보 | https://car.seoultech.ac.kr/bach/info | 2026-11-09 | 활발 |
| | 대학원공지 | https://car.seoultech.ac.kr/grad/board | 2026-10-27 | 활발 |
| 기계공학과 | 공지사항 | https://mech.seoultech.ac.kr/board/notice | 2026-11-06 | 활발 |
| | 학과소식 | https://mech.seoultech.ac.kr/board/news | 2026-11-09 | 활발 |
| | 취업정보 | https://mech.seoultech.ac.kr/board/board | 2026-10-19 | 활발 |
| | 대학원공지 | https://mech.seoultech.ac.kr/grad/notice | 2026-07-30 | 가끔 |
| 안전공학과 | 공지사항 | https://safety.seoultech.ac.kr/b_information/notic | 2026-11-06 | 활발 |
| | 취업정보 | https://safety.seoultech.ac.kr/b_information/job_info | 2026-09-22 | 가끔 |
| 신소재공학과 | 공지사항 | https://mse.seoultech.ac.kr/cmt/notice | 2026-11-12 | 활발 |
| | 학과소식 | https://mse.seoultech.ac.kr/cmt/news | 2026-10-15 | 활발 |
| 건설시스템공학과 | 학부공지 | https://civil.seoultech.ac.kr/haksainfor/notice | 2026-11-02 | 활발 |
| | 대학원공지 | https://civil.seoultech.ac.kr/graduateschool/notice | 2026-10-30 | 활발 |
| | 취업정보 | https://civil.seoultech.ac.kr/inforplaza/employment | 2026-10-27 | 활발 |
| 건축공학전공 | 공지사항 | https://architecture.seoultech.ac.kr/bachelor_of_information/notice | 2026-10-13 | 활발 |
| | 취업/대회/유학 | https://architecture.seoultech.ac.kr/bachelor_of_information/jobs | 2026-11-02 | 활발 |
| | 장학금 | https://architecture.seoultech.ac.kr/bachelor_of_information/scholarship | 2026-10-15 | 활발 |
| 건축학전공 ※ | 공지사항 | https://archidesign.seoultech.ac.kr/kr/info/notice.php | 2026-10-26 | 활발 |
| | 채용정보 | https://archidesign.seoultech.ac.kr/kr/info/recruit.php | – | 확인 필요 |
| 건축기계설비공학과 (계약) | 공지사항 | https://ebse.seoultech.ac.kr/info/notice | 2026-11-11 | 활발 |
| 기계시스템디자인공학과 | 공지사항 | https://msd.seoultech.ac.kr/information/bulletin | 2026-08-07 | 가끔 |
| | 취업정보 | https://msd.seoultech.ac.kr/information/employment | 2026-02-02 | 휴면 |
| 기계·자동차공학과 | 공지사항 | https://mae.seoultech.ac.kr/bachelor/bulletin | 2026-10-08 | 가끔 |

※ 건축학전공은 별도 PHP 사이트다. 날짜 형식이 `26.10.26`이고 글 주소가 `?bgu=view&idx=` 형태라서 파서를 따로 만들어야 한다.

### 3.4 정보통신대학

| 학과 | 게시판 | URL | 최근 글 | 상태 |
|---|---|---|---|---|
| (단과대) 정보통신대학 | 공지사항 | https://ice.seoultech.ac.kr/community/notice/bulletin | 2026-08-05 | 가끔 |
| 전기정보공학과 | 학부공지 | https://eie.seoultech.ac.kr/majornotice/notice | 2026-11-09 | 활발 |
| | 대학원공지 | https://eie.seoultech.ac.kr/graduate/gnotice | 2026-11-06 | 활발 |
| | 취업정보 | https://eie.seoultech.ac.kr/majornotice/board | 2026-11-03 | 활발 |
| | 학과소식 | https://eie.seoultech.ac.kr/majornotice/department | 2026-10-16 | 활발 |
| 전자공학과 | 공지사항 | https://ee.seoultech.ac.kr/bbs/notice | 2026-11-05 | 활발 |
| | 취업정보 | https://ee.seoultech.ac.kr/bbs/job | 2026-04-24 | 휴면 |
| 컴퓨터공학과 | 학부공지 | https://computer.seoultech.ac.kr/info/notice | 2026-11-12 | 활발 |
| | 대학원공지 | https://computer.seoultech.ac.kr/info/notice2 | 2026-08-04 | 가끔 |
| | 취업정보 | https://computer.seoultech.ac.kr/info/job | 2026-11-11 | 활발 |
| | 학과소식 | https://computer.seoultech.ac.kr/notice/news | 2026-10-29 | 활발 |
| 스마트ICT융합공학과 | 공지사항 | https://icte.seoultech.ac.kr/plaza/notice | 2026-09-18 | 가끔 |
| | 취업정보 | https://icte.seoultech.ac.kr/plaza/info | 2026-04-14 | 휴면 |

### 3.5 에너지바이오대학

| 학과 | 게시판 | URL | 최근 글 | 상태 |
|---|---|---|---|---|
| (단과대) 에너지바이오대학 | 공지사항 | https://nature.seoultech.ac.kr/community/notic | 2026-02-06 | 휴면 |
| 화공생명공학과 | 학부공지 | https://che.seoultech.ac.kr/information/notice | 2026-11-06 | 활발 |
| | 대학원공지 | https://che.seoultech.ac.kr/information/graduate | 2026-11-10 | 활발 |
| | 취업정보 | https://che.seoultech.ac.kr/information_plaza/jobs | 2026-11-10 | 활발 |
| 환경공학과 | 공지사항 | https://enviro.seoultech.ac.kr/information/notice | 2026-10-26 | 활발 |
| | 취업정보 | https://enviro.seoultech.ac.kr/information/jobs | 2026-11-03 | 활발 |
| 식품생명공학과 | 공지사항 | https://food.seoultech.ac.kr/bachelor/notice | 2026-10-28 | 활발 |
| | 취업정보 | https://food.seoultech.ac.kr/bachelor/employment | 2026-10-07 | 가끔 |
| 정밀화학과 | 공지사항 | https://fchem.seoultech.ac.kr/information/notice | 2026-11-11 | 활발 |
| | 취업정보 | https://fchem.seoultech.ac.kr/plaza/jobs | 2026-07-20 | 가끔 |
| 스포츠과학과 | 공지사항 | https://sports.seoultech.ac.kr/b_information/notic | 2026-10-22 | 활발 |
| | 취업정보 | https://sports.seoultech.ac.kr/b_information/job_info | 2026-04-14 | 휴면 |
| | 대학원게시판 | https://sports.seoultech.ac.kr/g_school/notic | 2018-12-31 | 휴면 |
| 안경광학과 | 공지사항 | https://optometry.seoultech.ac.kr/bachelor_of_information/notice | 2026-11-10 | 활발 |
| | 취업정보 | https://optometry.seoultech.ac.kr/community/jobs | 2026-09-04 | 가끔 |
| 바이오메디컬학과 | 학과공지 | https://bms.seoultech.ac.kr/information/announcement | 2026-10-30 | 활발 |
| | 학과소식 | https://bms.seoultech.ac.kr/information/news | 2026-10-08 | 가끔 |
| 양자융합물리학과 | 공지사항 | https://physics.seoultech.ac.kr/info/notice | (글 없음) | 휴면 |

### 3.6 조형대학

| 학과/전공 | 게시판 | URL | 최근 글 | 상태 |
|---|---|---|---|---|
| (단과대) 조형대학 | 공지사항 | https://and.seoultech.ac.kr/advertisements/notice | 2026-10-29 | 활발 |
| 산업디자인전공 | 공지사항 | https://id.seoultech.ac.kr/community/notice | 2026-10-15 | 활발 |
| | 채용공고 | https://id.seoultech.ac.kr/gallery/recruit | 2026-06-10 | 가끔 |
| 시각디자인전공 | 공지사항 | https://vd.seoultech.ac.kr/bachelor/bulletin | 2026-10-20 | 활발 |
| | 채용정보 | https://vd.seoultech.ac.kr/bachelor/recruit | 2026-05-04 | 휴면 |
| 도예학과 | 공지사항 | https://ceramics.seoultech.ac.kr/community/notice | 2026-09-18 | 가끔 |
| 금속공예디자인학과 | 공지사항 | https://metalartdesign.seoultech.ac.kr/b_information/notic | 2026-10-08 | 가끔 |
| | 채용공고 | https://metalartdesign.seoultech.ac.kr/b_information/free_board | 2026-05-21 | 가끔 |
| 조형예술학과 | 학부공지 | https://fineart.seoultech.ac.kr/community/notice | 2026-10-21 | 활발 |
| | 대학원공지 | https://fineart.seoultech.ac.kr/community/graduate/notice | 2026-10-21 | 활발 |
| | 공모·채용 | https://fineart.seoultech.ac.kr/community/recruit | 2026-10-22 | 활발 |

### 3.7 인문사회대학

| 학과 | 게시판 | URL | 최근 글 | 상태 |
|---|---|---|---|---|
| (단과대) 인문사회대학 | 공지사항 | https://human.seoultech.ac.kr/community/notice | 2026-09-15 | 가끔 |
| 행정학과 | 공지사항 | https://pa.seoultech.ac.kr/admini/notice | 2026-11-12 | 활발 |
| | 취업/공무원시험 | https://pa.seoultech.ac.kr/student/job | 2026-09-09 | 가끔 |
| 영어영문학과 | 공지사항 | https://eng.seoultech.ac.kr/information_plaza/notice | 2026-10-07 | 가끔 |
| | 취업정보 | https://eng.seoultech.ac.kr/information_plaza/jobs | 2026-11-12 | 활발 |
| | 대학원공지 | https://eng.seoultech.ac.kr/school_1/schoolgraduate_announcements | 2015-05-29 | 휴면 |
| 문예창작학과 | 공지사항 | https://writing-creative.seoultech.ac.kr/bachelor_of_information_/notice_ | 2026-09-17 | 가끔 |
| | 공모전/취업 | https://writing-creative.seoultech.ac.kr/bachelor_of_information_/free_board_ | 2026-10-19 | 활발 |

### 3.8 기술경영융합대학

| 학과/전공 | 게시판 | URL | 최근 글 | 상태 |
|---|---|---|---|---|
| (단과대) 기술경영융합대학 | 공지사항 | https://sgc.seoultech.ac.kr/open/notice | 2026-10-26 | 활발 |
| 산업정보시스템전공 | 공지사항 | https://iise.seoultech.ac.kr/notice/faculty_announcements_ | 2026-11-05 | 활발 |
| | 취업정보 | https://iise.seoultech.ac.kr/notice/job | 2026-10-22 | 활발 |
| ITM전공 | 공지사항 | https://itm.seoultech.ac.kr/bachelor_of_information/notice | 2026-10-20 | 활발 |
| MSDE학과 | 학부공지 | https://msde.seoultech.ac.kr/academics_/qna | 2026-10-22 | 활발 |
| | 대학원공지 | https://msde.seoultech.ac.kr/information_plaza_/notice | 2026-09-22 | 가끔 |
| | 취업정보 | https://msde.seoultech.ac.kr/community_/jobs_ | 2026-11-09 | 활발 |
| 경영학전공 | 공지사항 | https://biz.seoultech.ac.kr/railway/bizrailwaynotice | 2026-11-01 | 활발 |
| | 취업정보 | https://biz.seoultech.ac.kr/info_plaza/job_info | 2026-02-27 | 휴면 |
| 글로벌테크노경영전공 | 공지사항 | https://gtm.seoultech.ac.kr/info_plaza/notic | 2026-08-04 | 가끔 |
| | GTM소식 | https://gtm.seoultech.ac.kr/info_plaza/gtm_info | 2026-11-10 | 활발 |

참고: MSDE 학부공지는 URL이 `/qna`이지만 메뉴 이름은 "학부 공지사항"이다. 경영학전공 공지 URL도 `railway`가 들어가 있지만 메뉴의 "공지사항"이 가리키는 주소다.

### 3.9 미래융합대학 (재직자/성인학습자 대상)

7개 학과가 모두 똑같은 템플릿을 쓴다. 학사공지는 `/information/notice`, 장학금은 `/information/scholarship`에 있다.

| 학과 | 학사공지 URL | 최근 글 | 상태 |
|---|---|---|---|
| (단과대) 미래융합대학 | https://m-disciplinary.seoultech.ac.kr/community/notice | 2026-10-22 | 활발 |
| (단과대) 학생 공지 | https://m-disciplinary.seoultech.ac.kr/student/notice | 2026-11-08 | 활발 |
| 융합기계공학과 | https://cme.seoultech.ac.kr/information/notice | 2026-10-22 | 활발 |
| 건설환경융합공학과 | https://civil-environmental.seoultech.ac.kr/information/notice | 2026-10-02 | 가끔 |
| 헬스피트니스학과 | https://wellness.seoultech.ac.kr/information/notice | 2026-10-22 | 활발 |
| 문화예술학과 | https://cab.seoultech.ac.kr/information/notice | 2026-10-02 | 가끔 |
| 영어과 | https://engculture.seoultech.ac.kr/information/notice | 2026-10-23 | 활발 |
| 벤처경영학과 | https://v-biz.seoultech.ac.kr/information/notice | 2026-10-02 | 가끔 |
| 정보통신융합공학과 | https://comm.seoultech.ac.kr/information/notice | 2026-10-22 | 활발 |

### 3.10 창의융합대학

| 학과 | 게시판 | URL | 최근 글 | 상태 |
|---|---|---|---|---|
| (단과대) 창의융합대학 | 공지사항 | https://cccs.seoultech.ac.kr/community/notice | 2026-06-22 | 가끔 |
| 인공지능응용학과 | 공지사항 | https://aai.seoultech.ac.kr/information/bulletin | 2026-11-02 | 활발 |
| | 취업정보 | https://aai.seoultech.ac.kr/information/employment | 2026-11-10 | 활발 |
| 지능형반도체공학과 | 공지사항 | https://dse.seoultech.ac.kr/information/bulletin | 2026-11-10 | 활발 |
| | 대학원공지 | https://dse.seoultech.ac.kr/graduate/gra_noti | 2026-11-12 | 활발 |
| | 학과소식 | https://dse.seoultech.ac.kr/information/dse_news | 2026-10-26 | 활발 |
| 미래에너지융합학과 | 공지사항 | https://future-energy.seoultech.ac.kr/information/bulletin | 2026-11-09 | 활발 |
| | 대학원공지 / 취업정보 | /graduate/gra_noti, /information/employment | (글 없음) | 휴면 |

### 3.11 교양대학 · 국제대학

| 소속 | 게시판 | URL | 최근 글 | 상태 | 비고 |
|---|---|---|---|---|---|
| 교양대학 | 공지사항 | https://liberal.seoultech.ac.kr/community/notic | 2026-10-27 | 활발 | |
| ST자유전공 | 공지사항 | https://liberal.seoultech.ac.kr/specialty/notice | 2026-10-22 | 활발 | 자유전공 신입생에게 중요 |
| 국제대학 | 공지사항 | https://ic.seoultech.ac.kr/board/college | 2026-11-02 | 활발 | 본부 공지(bnum 4691)를 함께 보여줌 |
| 글로벌한국어문화학과 | 공지사항 | https://gsklc.seoultech.ac.kr/information/bulletin | 2026-11-11 | 활발 | |
| 글로벌IT컨버전스학과 | Notice | https://gitc.seoultech.ac.kr/notice/notice | 2026-10-21 | 활발 | 영어 공지 |
| AI·미디어학과 | 공지사항 | https://aimedia.seoultech.ac.kr/information/bulletin | 2026-11-10 | 활발 | |

## 4. 크롤링 관점 메모

### 4.1 공통 CMS 패턴 (건축학전공을 제외한 거의 전부)

- 목록: `{게시판 URL}?page={페이지}` — **페이지 이동은 `page`로 한다.** 링크에 보이는 `nowpage`는 무시되어 1페이지만 반복된다. (2차 조사에서 확인, [research-findings.md](research-findings.md) 2.6절)
- 글 상세: `{게시판 URL}?do=commonview&bnum={bnum}&bidx={글번호}`
- `bnum` = 게시판 ID, `bidx` = 글 ID이다. `bidx`는 학교 전체에서 고유하다. 미러 게시판은 같은 `bidx`를 쓰지만, **학과가 본부 공지를 다시 올리면 새 `bidx`를 받는다.** 그래서 중복 제거에는 제목 유사도 비교도 필요하다. (2026-11-13 검증, [research-findings.md](research-findings.md) 2.1절)
- 목록 HTML이 서버에서 렌더링되므로 일반 HTTP 요청 + HTML 파싱으로 수집할 수 있다. (JS 실행 불필요)

### 4.2 중복·미러 게시판

| 원본 | 같은 글이 보이는 곳 |
|---|---|
| 본부 취업공지 (bnum 57925) | 취업진로본부 공지사항 |
| 본부 현장실습 (bnum 57926) | 현장실습지원센터 공지사항 |
| 본부 대학공지 (bnum 4691) | 국제대학 공지사항 |
| 본부 학사·장학공지 | 다수 학과 공지에 같은 제목으로 다시 올라옴 (예: 경영학전공) |

### 4.3 예외·주의

- **건축학전공(archidesign)**: 별도 PHP CMS를 쓰므로 전용 파서가 필요하다.
- **취업진로본부 채용공고(일반/추천/채용행사)**: 일반 게시판 형식이 아니다. 추천채용은 목록을 읽지 못해 로그인이나 JS가 필요한지 확인해야 한다.
- **연구처·산학협력단(iac.seoultech.ac.kr)**: TLS 핸드셰이크 오류로 스크립트 접근에 실패했다. (브라우저로는 열림) 학생 대상 공지가 적어 이번 목록에서는 뺐다.
- **도서관(library.seoultech.ac.kr)**: JS 기반 사이트지만 **공개 JSON API**가 있다. `https://library.seoultech.ac.kr/pyxis-api/1/bulletin-boards/1/bulletins?max=N` (2차 조사, 2026-11-11 글까지 활발). HTML 파싱 없이 수집할 수 있다.
- **카드형 목록**: 생활관, 신소재공학과·바이오메디컬학과 학과소식 등은 표가 아니라 `<div class="blog_list">` 카드 구조다. 별도 파싱 규칙이 필요하다.
- **로그인 필요 (수집 불가)**: 교수학습개발센터 공지(`ctl.seoultech.ac.kr/reference/notice`), 취업진로본부 추천채용, 비교과 시스템 EPiC(`epic.seoultech.ac.kr`)
- **휴면 추가**: 보건진료소 공지(`health.seoultech.ac.kr/bbs/notice`, 마지막 글 2025-09-12)
- **실측 공지량**: 30일 동안 학부 대상 새 글 약 470건, 136개 게시판 중 57개는 새 글 0건 ([research-findings.md](research-findings.md) 6절)
### 4.4 robots.txt · 이용 정책 (2026-11-13 확인)

| 항목 | 결과 |
|---|---|
| robots.txt | 위 목록의 호스트 70개 중 **69개는 robots.txt가 없다** (HTTP 404). 표준(RFC 9309)상 robots.txt가 없으면 크롤링 제한도 없는 것으로 본다. |
| 예외 | archidesign(건축학전공)만 robots.txt가 있으며 `User-agent: * / allow: /`로 전체를 허용한다. |
| meta robots / X-Robots-Tag | 게시판 페이지에서 `noindex`·`nofollow`가 걸린 곳은 없다. (archidesign은 `INDEX,FOLLOW`를 명시) |
| 사이트 정책 | 모든 사이트 하단에 **이메일무단수집거부** 고지가 있다. 정보통신망법 제50조의2에 따라 홈페이지의 이메일 주소를 자동으로 수집하는 것을 금지한다. 크롤링 자체를 금지하는 이용약관은 찾지 못했다. |

정리하면, 기술적으로는 공지 목록과 본문 수집을 막는 설정이 없다. 다만 아래 사항은 지켜야 한다.

- 공지 본문에 있는 담당자 **이메일 주소는 저장하거나 노출하지 않는다.** (수집 단계에서 마스킹하거나 제거)
- robots.txt가 없다는 것이 저작권이나 학교 측 허락을 뜻하지는 않는다. 서비스에서는 제목, 요약, 원문 링크 위주로 보여주고 본문 전체를 그대로 복제하지 않는 편이 안전하다.
- 요청 간격을 넉넉히 둔다. (예: 호스트당 수 초에 1회, 하루 몇 차례 주기)
- 정식 서비스로 운영할 계획이면 학교 정보전산원이나 홍보 부서에 알리거나 협의하는 것을 권장한다.

## 5. 이번 조사에 포함하지 않은 것

- 특수대학원(산업대학원, 주택도시대학원), 전문대학원(철도, IT정책, 국방융합과학, 나노IT디자인융합, KIRAMS의과학)
- 학생회·동아리: 공식 사이트보다 인스타그램이나 카카오톡 채널에 공지를 올리는 경우가 많다.
- 에브리타임 등 외부 커뮤니티
- 학생포털, eClass 등 로그인이 필요한 시스템 안의 공지
