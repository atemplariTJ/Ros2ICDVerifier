# ROS2 ICD Verifier 프로젝트 구현 계획 및 지침 (GEMINI.md)

## 1. 프로젝트 개요
ROS2 시스템의 복잡성 증가에 대응하기 위해 ICD(Interface Control Document) 기반의 자동화된 검증 도구를 개발합니다. Python 기반으로 GUI와 ROS2 노드를 통합하여 요구사항을 만족하는 애플리케이션을 구축합니다.

- **핵심 기술 스택**
  - **언어**: Python 3 (ROS2 호환 버전)
  - **ROS2 API**: `rclpy`
  - **GUI 프레임워크**: PyQt6 또는 PySide6 (표 구현 및 스레드 관리 용이)
  - **데이터 처리**: `pandas` (CSV 파싱 및 결과 데이터 관리)
  - **보고서 생성**: `openpyxl` (엑셀 보고서) 또는 `ReportLab` (PDF 보고서)

## 2. 제약사항 및 환경 설정 (필수 지침)
- **가상환경**: 본 프로젝트 개발은 반드시 `common_ros_env`라는 이름의 새로운 Conda 가상환경에서 진행해야 합니다.
- **의존성 관리**: 프로젝트 수행 동안 설치한 모든 라이브러리는 반드시 `requirements.txt` 문서로 별도 관리해야 합니다.

## 3. 단계별 구현 계획

### 1단계: 아키텍처 설계 및 환경 셋업
- **스레드 분리 (핵심)**: `rclpy.spin()`의 블로킹으로 인한 GUI 멈춤 현상을 방지하기 위해 GUI 메인 스레드와 ROS2 Worker 스레드를 완벽히 분리합니다.
  - **UI 스레드**: 화면 렌더링, 사용자 입력 처리, 결과 표출
  - **ROS2 Worker 스레드**: 주기적 토픽 업데이트, 메시지 구독, Hz 계산, 백그라운드 검증 수행 (`QThread` 또는 `threading` 활용)
- **데이터 공유**: Qt의 Signal/Slot 구조 또는 Thread-safe한 Queue를 사용하여 ROS2 스레드에서 UI 스레드로 결과를 전달합니다.

### 2단계: CSV 파서 및 데이터 모델 구축
- `pandas`를 이용하여 사용자가 업로드한 CSV 파일을 파싱합니다.
- 각 행(Row)을 시스템이 이해할 수 있는 `TopicInfo` 데이터 클래스(또는 딕셔너리)로 매핑합니다.
- **필수 필드**: `topic_name`, `expected_src`, `expected_dst`, `topic_type`, `expected_qos`, `expected_hz`

### 3단계: ROS2 검증 코어 로직 구현
- **토픽 생성 및 타입 일치 여부**: `node.get_topic_names_and_types()`를 호출하여 CSV 데이터와 현재 활성화된 토픽 및 타입을 비교합니다.
- **주기(Hz) 검증**: 대상 토픽에 대해 동적으로 `create_subscription`을 수행하고, 메시지 수신 타임스탬프 기반 이동 평균(Moving Average)으로 실제 Hz를 계산하여 오차 범위를 검증합니다.
- **Src / Dst 일치 여부 검증**:
  - 헤더(`communication_header`) 존재 시: 메시지 콜백에서 필드를 파싱해 src/dst(수신처 누락 여부 등)를 확인합니다.
  - 헤더 부재 시: `node.get_publishers_info_by_topic()` 및 `node.get_subscriptions_info_by_topic()`을 사용하여 실제 연결된 노드 이름을 추출 및 검증합니다.

### 4단계: GUI 프론트엔드 구현
`frontend_example.md`에 정의된 React 기반 대시보드의 UI/UX를 참고하여 PyQt/PySide로 데스크톱 프론트엔드를 구현합니다.
- **상단 제어부**: CSV 파일 선택, 검증 시작/중지, 보고서 저장 버튼
- **요약 패널**: 전체 토픽 건수, 정상(Pass) 건수, 오류(Fail) 건수 요약 표시
- **메인 상태판 (`QTableView` / `QTableWidget`)**:
  - 컬럼: 토픽명 & 타입, Src / Dst 목록(다중 Dst 지원), QoS(목표/실제), Hz(목표/실제), 상태
  - 결과 상태(정상, QoS 불일치, 수신처 누락, 대기중 등)에 따라 직관적인 상태 뱃지 또는 배경색 적용
- **상세보기 (`QDialog` 또는 하단 패널)**: 표에서 특정 토픽 선택 시 가장 최근 수신된 Raw Data(JSON 형식 등) 및 누락된 Dst 정보를 `QTextEdit`에 실시간으로 출력합니다. (터미널의 `ros2 topic echo` 기능 대체)

### 5단계: 보고서 생성 기능
- 검증 완료된 최종 데이터(Pandas DataFrame)를 `to_excel()`을 사용하여 엑셀 파일로 추출합니다.
- 단순 데이터 출력뿐만 아니라 요약 정보(전체 토픽 수, 성공/실패 수)를 포함하여 보고서의 퀄리티를 높입니다.

## 4. 기술적 주의사항 (Key Challenges)
- **동적 메시지 타입 캐스팅**: `rosidl_runtime_py.utilities.get_message("std_msgs/msg/String")` 등을 활용하여 텍스트로 읽어온 토픽 타입을 실제 Python 클래스로 변환하여 동적으로 Subscribe 할 수 있도록 처리합니다.
- **성능 최적화**: 수백 개의 토픽을 동시 검증 시 네트워크/CPU 부하가 발생할 수 있으므로, 순차적(Batch) 검증이나 일정 시간 샘플링 후 Subscribe를 해제하는 방식을 도입할 수 있도록 설계합니다.