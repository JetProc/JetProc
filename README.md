# Soonjae Kwoun (JetProc)

제가 만든 기능이 실제로 어떻게 쓰이는지 궁금해하는 프론트엔드 개발자입니다.  
무엇을 만들지 함께 고민하고, 사용자에게 내보낸 뒤의 반응을 살피며 다음 개선을 이어갑니다.

## Selected Work

### Rilog

개인 블로그와 팀 블로그 **Co-log**를 함께 운영하는 기록 서비스입니다. 우아한테크코스 팀 프로젝트에서 프론트엔드 개발에 참여하고 있습니다.

[Repository](https://github.com/woowacourse-teams/2026-rilog) · [My pull requests](https://github.com/woowacourse-teams/2026-rilog/pulls?q=is%3Apr+author%3AJetProc)

| 주제 | 직접 기여한 내용 | 근거 |
| --- | --- | --- |
| 사용자 행동 분석 | 로그인·읽기·작성·발행 이벤트의 타입과 수집 기준을 통일하고, 자유 입력값 대신 제한된 값으로 분석 데이터를 수집했습니다. | [#381](https://github.com/woowacourse-teams/2026-rilog/pull/381) |
| 테스트 설계 | 구현 세부사항을 복제하는 검증을 줄이고, 실제 mutation hook과 API 경계를 통과하는 발행 테스트로 연결을 검증했습니다. | [#618](https://github.com/woowacourse-teams/2026-rilog/pull/618) |
| 품질 자동화 | PR에서 품질 검사와 production build 기반 E2E를 실행하고, 필수 흐름 누락·skip·실패를 감지하며 진단 자료를 보존하도록 구성했습니다. | [#619](https://github.com/woowacourse-teams/2026-rilog/pull/619) |

### 찜꽁 Helper

우아한테크코스 판교 캠퍼스의 회의실·페어링 존 예약을 돕는 Chrome 확장 프로그램입니다. 날짜·시간·공간을 한 화면에서 살펴보고 예약 폼에 연결하도록 만들었습니다.

회의실 타임테이블에서 시작해 페어링 존, 내 예약 조회, 예약 공유로 기능을 확장했습니다. Content Script, 페이지 컨텍스트, Service Worker의 역할을 나누어 기존 예약 서비스와 연결합니다.

[Repository & technical notes](https://github.com/JetProc/zzimkkong-helper)

### Performance Optimization

우아한테크코스 성능 최적화 미션에서 초기 리소스 크기, 요청 시점, 캐시 정책을 나누어 개선했습니다.

| Home 기준 | 개선 전 | 개선 후 |
| --- | ---: | ---: |
| 초기 JavaScript — gzip 재현 | 310,567 B | 59,396 B |
| LCP | 9.382 s | 0.554 s |
| Lighthouse Performance | 75 | 100 |

LCP와 Lighthouse 점수는 **Desktop Navigation · Performance-only 조건에서 각각 3회 측정한 중앙값**입니다. 초기 JavaScript는 gzip으로 재현한 크기이며, 위 수치는 실사용자 지표가 아닌 미션 측정 결과입니다.

[Implementation — jetproc branch](https://github.com/JetProc/perf-basecamp/tree/jetproc) · [Measurement & decisions — PR #210](https://github.com/woowacourse/perf-basecamp/pull/210)

## Open Source Contributions

병합된 외부 오픈소스 기여를 코드와 문서 기여로 구분했습니다. 각 PR에서 변경 범위와 검증 내용을 확인할 수 있습니다.

<!-- merged-contributions:start -->
### Code Contributions

| 저장소 | 기여 내용 | PR |
|:---|:---|:---|
| [toss/react-simplikit](https://github.com/toss/react-simplikit) | useLongPress의 unmount 이후 콜백 실행 방지 및 회귀 테스트 추가 | [#473](https://github.com/toss/react-simplikit/pull/473) |
| [akan-team/akanjs](https://github.com/akan-team/akanjs) | 파일 미리보기 URL 경로 오류 수정 | [#16](https://github.com/akan-team/akanjs/pull/16) |
| [akan-team/akanjs](https://github.com/akan-team/akanjs) | 무한 스크롤 중복 요청 수정 | [#15](https://github.com/akan-team/akanjs/pull/15) |
| [toss/es-toolkit](https://github.com/toss/es-toolkit) | isNumber 판별 기준을 다른 타입 가드와 일치하도록 수정 | [#1726](https://github.com/toss/es-toolkit/pull/1726) |

### Documentation / Community

| 저장소 | 기여 내용 | PR |
|:---|:---|:---|
| [lodash/lodash](https://github.com/lodash/lodash) | 기여 가이드 링크 오류 수정 | [#6196](https://github.com/lodash/lodash/pull/6196) |
| [reactjs/ko.react.dev](https://github.com/reactjs/ko.react.dev) | 테스트 도구 지원 중단 안내 한국어 번역 | [#1525](https://github.com/reactjs/ko.react.dev/pull/1525) |
<!-- merged-contributions:end -->

## Core Skills

**Frontend**  
TypeScript · React · Next.js · TanStack Query

**Quality**  
Vitest · React Testing Library · Playwright · GitHub Actions

**Product / Operation**  
PostHog · Chrome Extension · AWS

## Background

| 기간 | 활동 |
| --- | --- |
| 2026.02–현재 | 우아한테크코스 8기 프론트엔드 크루 |
| 2024.06–2026.01 | 국방통합데이터센터 보안관제 |
| 2023.07–2024.01 | StageUs Web Frontend 16기 |
| 2022–현재 | 인하대학교 공과대학 정보통신공학과 |
| 2019–2021 | 한국디지털미디어고등학교 18기 웹프로그래밍과 |

## Contact

[Email — soonjae8297@gmail.com](mailto:soonjae8297@gmail.com)

## Currently Learning

TypeScript · AI Agents
