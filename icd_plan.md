# 구현 플랜

ROS2 시스템이 복잡해질수록 ICD(Interface Control Document) 기반의 자동화된 검증 도구는 필수적입니다.

Python 기반으로 GUI와 ROS2 노드를 통합하여 요구사항을 만족하는 애플리케이션을 개발하기 위한 단계별 구현 플랜을 제안합니다.

🛠️ 기술 스택 추천
언어: Python 3 (ROS2 호환 버전)

ROS2 API: rclpy

GUI 프레임워크: PyQt6 또는 PySide6 (Tkinter보다 표(Table) 구현과 스레드 관리에 훨씬 유리합니다.)

데이터 처리: pandas (CSV 파싱 및 결과 데이터 관리)

보고서 생성: openpyxl (엑셀 보고서) 또는 ReportLab (PDF 보고서)

📋 단계별 구현 플랜
1단계: 아키텍처 설계 및 환경 셋업 (1주 차)
가장 중요한 것은 GUI 스레드와 ROS2 스레드의 분리입니다. rclpy.spin()은 블로킹(Blocking) 함수이므로 GUI 메인 스레드에서 실행하면 화면이 멈춥니다.

UI 스레드: 화면 렌더링, 사용자 입력 처리, 결과 표출.

ROS2 Worker 스레드 (QThread 또는 threading 활용): 주기적으로 토픽 리스트 업데이트, 메시지 구독, Hz(주기) 계산, 백그라운드 검증 수행.

데이터 공유: Qt의 Signal/Slot 구조나 Thread-safe 한 큐(Queue)를 사용하여 ROS2 스레드에서 UI 스레드로 검증 결과를 전달합니다.

2단계: CSV 파서 및 데이터 모델 구축 (1~2주 차)
사용자가 업로드한 CSV 파일을 시스템이 이해할 수 있는 데이터 모델로 변환합니다.

pandas를 이용해 CSV 읽기.

각 행(Row)을 TopicInfo라는 데이터 클래스(또는 딕셔너리)로 매핑.

필수 필드: topic_name, expected_src, expected_dst, topic_type, expected_qos, expected_hz.

3단계: ROS2 검증 코어 로직 구현 (2~3주 차)
가장 핵심이 되는 백엔드 로직입니다. ROS2 API를 활용해 실제 네트워크 상태를 수집합니다.

토픽 생성 및 타입 일치 여부:

node.get_topic_names_and_types()를 호출하여 현재 활성화된 토픽과 타입을 가져와 CSV 데이터와 비교합니다.

주기(Hz) 검증:

검증 대상 토픽에 대해 동적으로 create_subscription을 수행합니다.

메시지가 들어올 때마다 타임스탬프를 기록하여 이동 평균(Moving Average)으로 실제 Hz를 계산하고, CSV의 '주기'와 오차 범위 내에 있는지 비교합니다.

Src / Dst 일치 여부 검증:

Header가 있는 경우 (communication_header): 메시지를 subscribe 하여 콜백 함수에서 해당 필드를 파싱해 src/dst를 확인합니다. (이를 위해 rosidl_runtime_py를 이용해 동적으로 메시지 모듈을 임포트하는 로직이 필요합니다.)

Header가 없는 경우: node.get_publishers_info_by_topic() 및 node.get_subscriptions_info_by_topic()을 사용하여 해당 토픽을 물고 있는 실제 노드(Node) 이름들을 추출하여 검증합니다.

4단계: GUI 프론트엔드 구현 (3~4주 차)
PyQt/PySide를 활용하여 사용자 친화적인 대시보드를 만듭니다.

상단 제어부: CSV 파일 선택 버튼(File Dialog), '검증 시작', '검증 중지', '보고서 저장' 버튼.

메인 상태판 (QTableView / QTableWidget):

열(Column): 토픽명, 생성여부(Pass/Fail), 타입(Pass/Fail), 주기(실제/목표), Src(Pass/Fail), Dst(Pass/Fail), 상태(통과/오류).

결과에 따라 셀 배경색을 초록색(Pass) / 빨간색(Fail)으로 직관적으로 표시합니다.

상세보기 (QDialog):

표에서 특정 토픽 행을 더블클릭하거나 '상세보기' 버튼을 누르면 팝업창이 뜹니다.

해당 토픽의 가장 최근 수신된 raw data (JSON 형식 등)를 QTextEdit에 실시간으로 출력합니다. (터미널의 ros2 topic echo 기능)

5단계: 보고서 생성 기능 (4주 차)
검증이 끝난 후 결과를 문서화하는 기능입니다.

검증된 최종 데이터(Pandas DataFrame 형태)를 to_excel()을 사용하여 엑셀 파일로 추출합니다.

단순 데이터뿐만 아니라, 요약 정보(전체 토픽 수, 성공 수, 실패 수)를 상단에 추가하여 보고서의 퀄리티를 높입니다.

💡 기술적 주의사항 (Key Challenges)
동적 메시지 타입 캐스팅: CSV에서 텍스트로 읽어온 토픽 타입(예: std_msgs/msg/String)을 Python 코드에서 실제 Subscribe 하기 위해 클래스로 변환해야 합니다. 이는 rosidl_runtime_py.utilities.get_message("std_msgs/msg/String") 기능을 사용하면 깔끔하게 해결됩니다.

성능 최적화: 검증해야 할 토픽이 수백 개 단위라면, 한 번에 모든 토픽을 Subscribe 할 때 네트워크 부하나 CPU 점유율이 급증할 수 있습니다. 검증을 순차적(Batch)으로 진행하거나, 일정 시간 샘플링 후 Subscribe를 해제하는 방식이 필요할 수 있습니다.

# 예시 프론트앤드 파일 
예시 프론트앤드 파일 : Fronted_example.md

# 제약사항
본 프로젝트 개발사항은 새로운 conda환경에서 진행하며, 가상환경 이름은 common_ros_env이다.
본 프로젝트 수행동안 설치한 라이브러리는 requriement문서로 별도 관리해야한다.