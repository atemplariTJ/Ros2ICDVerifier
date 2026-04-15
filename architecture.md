# ROS2 ICD Verifier 아키텍처 설계 문서

본 문서는 `frontend_example.md`에 명시된 모든 프론트엔드 기능과 ROS2 백엔드 요구사항을 만족하기 위한 애플리케이션 아키텍처를 정의합니다.

## 1. 프로젝트 디렉토리 구조
관심사 분리(Separation of Concerns) 원칙에 따라 핵심 비즈니스 로직, GUI 프론트엔드, ROS2 통신 모듈을 분리합니다.

```text
Ros2ICDVerifier/
├── main.py                 # 앱 진입점 (QApplication 및 rclpy 초기화)
├── requirements.txt        # 패키지 의존성 목록
├── config/
│   ├── __init__.py
│   └── settings.py         # 공통 상수, 색상(Badge 등), 설정값
├── core/                   # 핵심 데이터 및 비즈니스 로직
│   ├── __init__.py
│   ├── models.py           # 데이터 모델 (TopicInfo: 검증 대상, ValidationResult: 결과)
│   ├── csv_parser.py       # CSV 파일 읽기 및 데이터 모델 변환 (pandas 활용)
│   └── report_excel.py     # 검증 결과를 엑셀 파일로 출력 (openpyxl 활용)
├── gui/                    # PyQt6 기반 프론트엔드 뷰
│   ├── __init__.py
│   ├── main_window.py      # 메인 대시보드 창 (버튼, 요약 패널, 테이블, 상세뷰)
│   ├── table_model.py      # QAbstractTableModel 구현체 (데이터와 뷰의 효율적 바인딩)
│   └── components.py       # 상태 배지(Badge) 렌더링 등 커스텀 UI 위젯
└── ros2/                   # ROS2 rclpy 연동 모듈
    ├── __init__.py
    ├── worker.py           # QThread를 상속받은 백그라운드 작업자 (UI 블로킹 방지)
    └── verifier_node.py    # rclpy.Node를 상속받아 실제 구독, Hz 계산, QoS 체크 수행
```

## 2. 프론트엔드 요구사항과 백엔드 모듈 매핑

프론트엔드 예시에서 도출된 주요 기능들을 다음과 같이 아키텍처에 매핑합니다.

| 프론트엔드 기능 | 매핑되는 백엔드/아키텍처 모듈 | 설명 및 동작 방식 |
| :--- | :--- | :--- |
| **"CSV 불러오기" 버튼** | `gui.main_window` & `core.csv_parser` | 파일 다이얼로그로 CSV를 선택 후, `pandas`로 파싱하여 `core.models.TopicInfo` 리스트로 변환합니다. |
| **"검증 시작" 버튼** | `gui.main_window` & `ros2.worker` | `ros2.worker.VerifierThread`를 시작하여, 백그라운드에서 ROS2 노드( `verifier_node`)를 스핀(spin)시킵니다. |
| **"검증 중지" 버튼** | `gui.main_window` & `ros2.worker` | 스레드 및 ROS2 구독(Subscription)을 안전하게 종료/일시정지합니다. |
| **통계 패널 (전체/정상/오류)** | `gui.main_window` | Worker 스레드에서 주기적으로 발생시키는 Qt Signal(`pyqtSignal`)을 받아 UI 텍스트를 업데이트합니다. |
| **메인 상태판 (테이블)** | `gui.table_model` | `QAbstractTableModel`을 사용하여, 데이터 변경 시 테이블 UI가 즉각 반영되도록 합니다. (상태에 따른 배경색/뱃지 지원) |
| **Src / 다중 Dst 렌더링** | `core.models` & `gui.table_model` | 1:N 구조(하나의 Src, 다수의 Dst)를 모델화하고, 누락된 Dst를 판별하여 테이블의 컬럼에 렌더링합니다. |
| **QoS 및 Hz (목표/실제) 비교** | `ros2.verifier_node` & `core.models` | `create_subscription`을 통해 메시지 수신 시간을 기록하여 실제 Hz를 계산하고, Node Info API로 실제 QoS를 확인합니다. |
| **상세보기 (Raw Data 및 누락 Dst)** | `gui.main_window` | 테이블 행(Row) 클릭 시, 해당 토픽의 최신 수신 메시지(JSON 포맷팅)와 누락된 Dst 목록을 하단 `QTextEdit` 영역에 출력합니다. |

## 3. 핵심 동작 시나리오 (Data Flow)

1. **초기화**: `main.py` 실행 시 PyQt 메인 루프와 ROS2 초기화(`rclpy.init()`)가 수행됩니다.
2. **데이터 로드**: 사용자가 CSV를 불러오면 `csv_parser`가 데이터를 읽어 `TableModel`에 주입합니다. UI에는 '대기중' 상태로 표시됩니다.
3. **검증 수행**: 사용자가 '검증 시작' 클릭 시:
   - `worker.py` (QThread)가 백그라운드에서 시작됩니다.
   - `verifier_node.py` 내의 검증 로직이 활성화되어 각 토픽의 Hz, QoS, Pub/Sub 정보를 수집합니다.
   - 데이터가 갱신될 때마다 `pyqtSignal`을 통해 메인 UI 스레드에 변경된 데이터(실제 Hz, 상태, Raw Data 등)를 전달합니다.
4. **UI 업데이트**: Signal을 받은 `main_window`는 `table_model`에 데이터를 갱신하고, 통계 및 상세 패널을 다시 그립니다.
5. **보고서 출력**: (예정) '보고서 저장' 버튼을 누르면 현재 테이블의 최종 검증 상태를 `report_excel.py`로 전달하여 엑셀 문서화합니다.

## 4. 고려 사항 (설계 제약)
*   **스레드 안전성(Thread Safety)**: rclpy 콜백은 Worker 스레드에서 돌고 UI 업데이트는 Main 스레드에서 돕니다. Qt의 Signal/Slot 메커니즘을 적극 활용하여 스레드 충돌을 원천 차단합니다.
*   **다중 Dst 검증**: 하나의 토픽을 여러 노드(Dst)가 수신해야 하는 상황을 검증하기 위해, `node.get_subscriptions_info_by_topic()` 반환값 리스트와 예상 Dst 리스트의 차집합을 계산해 누락(Missing)된 Dst를 식별합니다.