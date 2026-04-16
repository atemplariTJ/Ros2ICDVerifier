# ROS2 ICD Verifier

ROS2 시스템의 토픽이 ICD(Interface Control Document) 규격대로 동작하는지 실시간으로 검증하는 GUI 대시보드입니다.

## 주요 기능

- CSV로 정의된 ICD 스펙(토픽명 / 타입 / QoS / 주기)을 로드하여 실시간 검증
- 실제 연결된 송신·수신 노드 정보 표시 (`communication_header` 포함 시 RobotID 파싱)
- 송신 QoS / 수신 QoS 각각 검증 (BestEffort 송신 + Reliable 수신 비호환 감지)
- 비주기 토픽(Hz=0): 1회 수신 시 정상 처리
- 검증 항목별 상태 배지 — 수신 / QoS / 주기 / 종합
- 검증 결과 Excel 보고서 저장

## 요구사항

- ROS2 (Humble 이상)
- Python 3.10+
- PyQt6, pandas, openpyxl, rclpy

```bash
pip install PyQt6 pandas openpyxl
```

커스텀 메시지(`icd_custom_msgs`) 사용 시 워크스페이스 빌드 필요:

```bash
cd icd_ws
colcon build
```

## 실행

```bash
# ROS2 환경 및 커스텀 메시지 소싱 후 실행
source /opt/ros/<distro>/setup.bash
source icd_ws/install/setup.bash

python main.py
```

또는 제공된 스크립트 사용:

```bash
./run.sh
```

## CSV 포맷

| 컬럼 | 설명 | 예시 |
|------|------|------|
| Topic | 토픽명 | `/camera/image_raw` |
| Type | 메시지 타입 | `sensor_msgs/Image` |
| Qos | 목표 QoS | `BestEffort` / `Reliable` |
| Hz | 목표 주기 (0 = 비주기) | `30` |
| Src | 송신 노드 | `camera_node` / `1(ID)` |
| Dst | 수신 노드 (콤마 구분) | `perception, recorder` |

`sample_icd.csv` 파일을 참고하세요.
