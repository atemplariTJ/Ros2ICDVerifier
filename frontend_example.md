import React, { useState } from 'react';
import { Play, Square, Download, Upload, CheckCircle, XCircle, Activity, Info, AlertTriangle, Users } from 'lucide-react';

// 초기 더미 데이터 (검증 전)
// src는 객체, dst는 객체 배열로 변경하여 1:N 구조를 지원합니다.
const INITIAL_DATA = [
  { 
    id: 1, name: '/camera/image_raw', type: 'sensor_msgs/Image', targetQos: 'BestEffort', targetHz: 30,
    src: { name: 'camera_node', type: 'Node' },
    dst: [{ name: 'perception', type: 'Node' }, { name: 'recorder', type: 'Node' }],
    actualQos: null, actualHz: null, status: '대기중', missingDst: [], raw: '대기중...' 
  },
  { 
    id: 2, name: '/cmd_vel', type: 'geometry_msgs/Twist', targetQos: 'Reliable', targetHz: 20,
    src: { name: 'nav_node', type: 'Node' },
    dst: [{ name: 'base_controller', type: 'Node' }],
    actualQos: null, actualHz: null, status: '대기중', missingDst: [], raw: '대기중...' 
  },
  { 
    id: 3, name: '/vla_model/action', type: 'std_msgs/String', targetQos: 'Reliable', targetHz: 10,
    src: { name: 'vla_inference', type: 'Node' },
    dst: [{ name: 'task_planner', type: 'Node' }],
    actualQos: null, actualHz: null, status: '대기중', missingDst: [], raw: '대기중...' 
  },
  { 
    id: 4, name: '/battery_state', type: 'sensor_msgs/BatteryState', targetQos: 'Reliable', targetHz: 1,
    src: { name: 'battery_monitor', type: 'Node' },
    dst: [{ name: 'diagnostics', type: 'Node' }, { name: 'dashboard', type: 'Node' }],
    actualQos: null, actualHz: null, status: '대기중', missingDst: [], raw: '대기중...' 
  },
  { 
    id: 5, name: '/lidar/scan', type: 'sensor_msgs/LaserScan', targetQos: 'BestEffort', targetHz: 15,
    src: { name: 'lidar_driver', type: 'Node' },
    dst: [{ name: 'mapping_node', type: 'Node' }, { name: 'obstacle_avoidance', type: 'Node' }],
    actualQos: null, actualHz: null, status: '대기중', missingDst: [], raw: '대기중...' 
  },
  { 
    id: 6, name: '/fleet/sync', type: 'custom_msgs/Sync', targetQos: 'Reliable', targetHz: 5,
    src: { name: 'ROBOT_01', type: 'ID' },
    dst: [{ name: 'ROBOT_02', type: 'ID' }, { name: 'ROBOT_03', type: 'ID' }, { name: 'ROBOT_04', type: 'ID' }],
    actualQos: null, actualHz: null, status: '대기중', missingDst: [], raw: '대기중...' 
  }
];

// 시뮬레이션용 검증 완료 데이터
const VALIDATED_RESULTS = {
  1: { actualHz: 29.8, actualQos: 'BestEffort', status: '정상', missingDst: [], raw: '{\n  "header": {\n    "stamp": {"sec": 167888, "nanosec": 123456},\n    "frame_id": "camera_link"\n  },\n  "height": 480,\n  "width": 640\n}' },
  2: { actualHz: 19.5, actualQos: 'Reliable', status: '정상', missingDst: [], raw: '{\n  "linear": {"x": 1.2, "y": 0.0, "z": 0.0},\n  "angular": {"x": 0.0, "y": 0.0, "z": 0.5}\n}' },
  3: { actualHz: 0.0, actualQos: '-', status: '미수신', missingDst: ['task_planner'], raw: '{\n  "error": "No data received. Topic not published."\n}' },
  4: { actualHz: 0.0, actualQos: 'BestEffort', status: 'QoS 불일치', missingDst: [], raw: '{\n  "error": "QoS Profile Mismatch! Expected: Reliable, Actual: BestEffort."\n}' },
  5: { actualHz: 7.2, actualQos: 'BestEffort', status: '주기 미달', missingDst: [], raw: '{\n  "header": {"stamp": {"sec": 167890}, "frame_id": "laser"},\n  "ranges": [1.2, 1.3, 1.25]\n}' },
  // 6번 항목: 다중 수신처(ID) 중 ROBOT_04가 통신을 받지 못하는 상황
  6: { actualHz: 5.0, actualQos: 'Reliable', status: '수신처 누락', missingDst: ['ROBOT_04'], raw: '{\n  "communication_header": {\n    "src_id": "ROBOT_01",\n    "received_by": ["ROBOT_02", "ROBOT_03"]\n  },\n  "error": "ROBOT_04 did not acknowledge sync."\n}' }
};

export default function App() {
  const [topics, setTopics] = useState(INITIAL_DATA);
  const [isStarted, setIsStarted] = useState(false);
  const [selectedId, setSelectedId] = useState(null);

  const handleStart = () => {
    if (isStarted) return;
    setIsStarted(true);
    setTopics(INITIAL_DATA);

    INITIAL_DATA.forEach((topic, index) => {
      setTimeout(() => {
        setTopics(prev => prev.map(t => 
          t.id === topic.id ? { ...t, ...VALIDATED_RESULTS[topic.id] } : t
        ));
      }, (index + 1) * 600);
    });
  };

  const handleStop = () => setIsStarted(false);

  const handleReset = () => {
    setIsStarted(false);
    setTopics(INITIAL_DATA);
    setSelectedId(null);
  };

  const totalCount = topics.length;
  const passCount = topics.filter(t => t.status === '정상').length;
  const failCount = topics.filter(t => t.status !== '정상' && t.status !== '대기중').length;

  const selectedTopic = topics.find(t => t.id === selectedId);

  // 상태 배지 색상 결정 함수
  const getStatusBadge = (status) => {
    switch (status) {
      case '정상': return 'bg-green-100 text-green-800 border border-green-200';
      case 'QoS 불일치': return 'bg-orange-100 text-orange-800 border border-orange-200';
      case '수신처 누락': return 'bg-purple-100 text-purple-800 border border-purple-200';
      case '대기중': return 'bg-gray-100 text-gray-800 border border-gray-200';
      default: return 'bg-red-100 text-red-800 border border-red-200';
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50 font-sans">
      <header className="flex items-center justify-between p-4 bg-white border-b shadow-sm">
        <div className="flex items-center space-x-2">
          <Activity className="w-6 h-6 text-blue-600" />
          <h1 className="text-xl font-bold text-gray-800">ROS2 ICD 검증 대시보드 (다중 Dst 지원)</h1>
        </div>
        <div className="flex space-x-3">
          <button onClick={handleReset} className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition">
            <Upload className="w-4 h-4 mr-2" />
            CSV 불러오기 (초기화)
          </button>
          <button onClick={handleStart} disabled={isStarted} className={`flex items-center px-4 py-2 text-sm font-medium text-white rounded-md transition ${isStarted ? 'bg-green-400 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700'}`}>
            <Play className="w-4 h-4 mr-2" />
            검증 시작
          </button>
          <button onClick={handleStop} disabled={!isStarted} className={`flex items-center px-4 py-2 text-sm font-medium text-white rounded-md transition ${!isStarted ? 'bg-red-400 cursor-not-allowed' : 'bg-red-600 hover:bg-red-700'}`}>
            <Square className="w-4 h-4 mr-2" />
            검증 중지
          </button>
        </div>
      </header>

      <div className="grid grid-cols-3 gap-4 p-4">
        <div className="flex items-center p-4 bg-white border rounded-lg shadow-sm">
          <div className="p-3 mr-4 bg-blue-100 rounded-full"><Info className="w-6 h-6 text-blue-600" /></div>
          <div>
            <p className="text-sm font-medium text-gray-500">전체 토픽</p>
            <p className="text-2xl font-semibold text-gray-800">{totalCount}개</p>
          </div>
        </div>
        <div className="flex items-center p-4 bg-white border rounded-lg shadow-sm">
          <div className="p-3 mr-4 bg-green-100 rounded-full"><CheckCircle className="w-6 h-6 text-green-600" /></div>
          <div>
            <p className="text-sm font-medium text-gray-500">정상 (Pass)</p>
            <p className="text-2xl font-semibold text-green-600">{passCount}개</p>
          </div>
        </div>
        <div className="flex items-center p-4 bg-white border rounded-lg shadow-sm">
          <div className="p-3 mr-4 bg-red-100 rounded-full"><XCircle className="w-6 h-6 text-red-600" /></div>
          <div>
            <p className="text-sm font-medium text-gray-500">오류 (Fail)</p>
            <p className="text-2xl font-semibold text-red-600">{failCount}개</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto px-4 pb-4">
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden h-full flex flex-col">
          <div className="overflow-auto flex-1">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">토픽명 & 타입</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/3">Src (송신) / Dst (수신) 목록</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-100">QoS (목표/실제)</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Hz (목표/실제)</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">상태</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {topics.map((topic) => {
                  const isQosMismatch = topic.actualQos && topic.actualQos !== '-' && topic.actualQos !== topic.targetQos;
                  
                  return (
                    <tr 
                      key={topic.id} 
                      onClick={() => setSelectedId(topic.id)}
                      className={`cursor-pointer transition-colors ${selectedId === topic.id ? 'bg-blue-50' : 'hover:bg-gray-50'}`}
                    >
                      {/* 1. 토픽명 & 타입 */}
                      <td className="px-4 py-4 whitespace-nowrap">
                        <div className="text-sm font-bold text-gray-900">{topic.name}</div>
                        <div className="text-xs text-gray-500 font-mono mt-1">{topic.type}</div>
                      </td>
                      
                      {/* 2. Src / 다중 Dst 목록 */}
                      <td className="px-4 py-3">
                        <div className="flex flex-col space-y-2">
                          {/* Src */}
                          <div className="flex items-start">
                            <span className="text-gray-400 text-xs font-bold w-5 mt-1">S:</span>
                            <div className="flex flex-wrap gap-1">
                              <span className="inline-flex items-center px-2 py-0.5 rounded border bg-blue-50 border-blue-200">
                                <span className="text-sm font-semibold text-blue-900 mr-1.5">{topic.src.name}</span>
                                <span className={`text-[9px] px-1 rounded font-bold ${topic.src.type === 'ID' ? 'bg-indigo-200 text-indigo-800' : 'bg-blue-200 text-blue-800'}`}>
                                  {topic.src.type}
                                </span>
                              </span>
                            </div>
                          </div>
                          
                          {/* Dst (여러 개 렌더링) */}
                          <div className="flex items-start">
                            <span className="text-gray-400 text-xs font-bold w-5 mt-1">D:</span>
                            <div className="flex flex-wrap gap-1.5">
                              {topic.dst.map((d, idx) => {
                                const isMissing = topic.missingDst.includes(d.name);
                                return (
                                  <span key={idx} className={`inline-flex items-center px-2 py-0.5 rounded border transition-colors
                                    ${isMissing ? 'bg-red-50 border-red-300' : 'bg-gray-50 border-gray-300'}`}>
                                    <span className={`text-sm font-semibold mr-1.5 ${isMissing ? 'text-red-700' : 'text-gray-700'}`}>
                                      {d.name}
                                    </span>
                                    <span className={`text-[9px] px-1 rounded font-bold 
                                      ${isMissing ? 'bg-red-200 text-red-800' : (d.type === 'ID' ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-200 text-gray-600')}`}>
                                      {d.type}
                                    </span>
                                    {isMissing && <XCircle className="w-3 h-3 text-red-500 ml-1" />}
                                  </span>
                                );
                              })}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* 3. QoS */}
                      <td className="px-4 py-4 whitespace-nowrap text-center bg-gray-50/50">
                        <div className="text-xs text-gray-500">{topic.targetQos}</div>
                        <div className={`text-sm font-bold mt-1 ${isQosMismatch ? 'text-orange-600' : 'text-gray-900'}`}>
                          {isQosMismatch && <AlertTriangle className="inline w-3 h-3 mr-1 text-orange-500" />}
                          {topic.actualQos !== null ? topic.actualQos : '-'}
                        </div>
                      </td>
                      
                      {/* 4. Hz */}
                      <td className="px-4 py-4 whitespace-nowrap text-center">
                        <div className="text-xs text-gray-500">{topic.targetHz} Hz</div>
                        <div className="text-sm font-bold text-gray-900 mt-1">
                          {topic.actualHz !== null ? topic.actualHz : '-'} Hz
                        </div>
                      </td>

                      {/* 5. 상태 */}
                      <td className="px-4 py-4 whitespace-nowrap text-center">
                        <span className={`px-3 py-1.5 inline-flex text-xs font-bold rounded-full shadow-sm ${getStatusBadge(topic.status)}`}>
                          {topic.status}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="h-64 bg-gray-900 text-gray-100 flex flex-col shadow-inner border-t-4 border-gray-700">
        <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
          <span className="text-sm font-semibold tracking-wide text-gray-300">
            수신 데이터 상세보기 (Raw Data) {selectedTopic ? `- ${selectedTopic.name}` : ''}
          </span>
          {selectedTopic && (
             <div className="flex space-x-2">
               <span className={`text-xs px-2 py-1 rounded border ${selectedTopic.missingDst.length > 0 ? 'bg-red-900/50 text-red-300 border-red-700' : 'bg-gray-700 text-gray-400 border-gray-600'}`}>
                 누락된 Dst: {selectedTopic.missingDst.length > 0 ? selectedTopic.missingDst.join(', ') : '없음'}
               </span>
             </div>
          )}
        </div>
        <div className="flex-1 p-4 overflow-auto font-mono text-sm leading-relaxed">
          {selectedTopic ? (
            <pre className={selectedTopic.status === '미수신' || selectedTopic.status === '수신처 누락' ? 'text-purple-300' : selectedTopic.status === 'QoS 불일치' ? 'text-orange-400' : 'text-green-400'}>
              {selectedTopic.raw}
            </pre>
          ) : (
            <div className="h-full flex items-center justify-center text-gray-500 italic">
              표에서 토픽을 클릭하면 상세 데이터가 표시됩니다.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
