# -*- coding: utf-8 -*-
"""
성능 모니터 - 시스템 성능 추적 및 분석
"""

import time
import threading
from collections import deque, defaultdict
from typing import Dict, Any, Optional, List
import statistics

from core.interfaces import PerformanceMonitorInterface

class PerformanceMonitor(PerformanceMonitorInterface):
    """성능 모니터링 클래스"""
    
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self.lock = threading.Lock()
        
        # 타이밍 데이터
        self.timing_data = {}
        
        # FPS 계산용
        self.frame_times = deque(maxlen=max_samples)
        self.last_frame_time = time.time()
        
        # 통계 데이터
        self.stats = {
            'start_time': time.time(),
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'average_fps': 0.0,
            'current_fps': 0.0,
            'peak_fps': 0.0,
            'min_fps': float('inf'),
        }
        
        # 작업별 통계
        self.operation_stats = {}
    
    def record_timing(self, operation: str, duration: float):
        """타이밍 기록"""
        with self.lock:
            if operation not in self.timing_data:
                self.timing_data[operation] = deque(maxlen=self.max_samples)
            
            self.timing_data[operation].append({
                'duration': duration,
                'timestamp': time.time()
            })
            
            # 작업별 통계 업데이트
            self._update_operation_stats(operation, duration)
            
            # 전체 통계 업데이트
            self.stats['total_operations'] += 1
    
    def record_frame(self):
        """프레임 기록 (FPS 계산용)"""
        current_time = time.time()
        
        with self.lock:
            frame_time = current_time - self.last_frame_time
            self.frame_times.append(frame_time)
            self.last_frame_time = current_time
            
            # FPS 계산
            self._calculate_fps()
    
    def record_success(self, operation: str = None):
        """성공 기록"""
        with self.lock:
            self.stats['successful_operations'] += 1
            
            if operation:
                if operation not in self.operation_stats:
                    self.operation_stats[operation] = {
                        'success_count': 0,
                        'failure_count': 0,
                        'total_time': 0.0,
                        'avg_time': 0.0,
                        'min_time': float('inf'),
                        'max_time': 0.0
                    }
                self.operation_stats[operation]['success_count'] += 1
    
    def record_failure(self, operation: str = None):
        """실패 기록"""
        with self.lock:
            self.stats['failed_operations'] += 1
            
            if operation:
                if operation not in self.operation_stats:
                    self.operation_stats[operation] = {
                        'success_count': 0,
                        'failure_count': 0,
                        'total_time': 0.0,
                        'avg_time': 0.0,
                        'min_time': float('inf'),
                        'max_time': 0.0
                    }
                self.operation_stats[operation]['failure_count'] += 1
    
    def _update_operation_stats(self, operation: str, duration: float):
        """작업별 통계 업데이트"""
        if operation not in self.operation_stats:
            self.operation_stats[operation] = {
                'success_count': 0,
                'failure_count': 0,
                'total_time': 0.0,
                'avg_time': 0.0,
                'min_time': float('inf'),
                'max_time': 0.0
            }
        
        stats = self.operation_stats[operation]
        stats['total_time'] += duration
        stats['min_time'] = min(stats['min_time'], duration)
        stats['max_time'] = max(stats['max_time'], duration)
        
        # 평균 시간 계산
        total_ops = stats['success_count'] + stats['failure_count']
        if total_ops > 0:
            stats['avg_time'] = stats['total_time'] / total_ops
    
    def _calculate_fps(self):
        """FPS 계산"""
        if len(self.frame_times) < 2:
            return
        
        # 현재 FPS (최근 몇 프레임 기준)
        recent_frames = min(10, len(self.frame_times))
        if recent_frames > 1:
            recent_avg = sum(list(self.frame_times)[-recent_frames:]) / recent_frames
            current_fps = 1.0 / recent_avg if recent_avg > 0 else 0.0
            self.stats['current_fps'] = current_fps
            
            # 피크 FPS 업데이트
            self.stats['peak_fps'] = max(self.stats['peak_fps'], current_fps)
            
            # 최소 FPS 업데이트
            if current_fps > 0:
                self.stats['min_fps'] = min(self.stats['min_fps'], current_fps)
        
        # 평균 FPS
        if len(self.frame_times) > 0:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            self.stats['average_fps'] = 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        with self.lock:
            current_time = time.time()
            uptime = current_time - self.stats['start_time']
            
            # 기본 통계
            basic_stats = self.stats.copy()
            basic_stats['uptime'] = uptime
            basic_stats['operations_per_second'] = self.stats['total_operations'] / uptime if uptime > 0 else 0
            
            # 성공률 계산
            total_ops = self.stats['successful_operations'] + self.stats['failed_operations']
            if total_ops > 0:
                basic_stats['success_rate'] = self.stats['successful_operations'] / total_ops
            else:
                basic_stats['success_rate'] = 0.0
            
            # 작업별 통계
            operation_stats = {}
            for op, stats in self.operation_stats.items():
                total_ops = stats['success_count'] + stats['failure_count']
                operation_stats[op] = {
                    'total_operations': total_ops,
                    'success_count': stats['success_count'],
                    'failure_count': stats['failure_count'],
                    'success_rate': stats['success_count'] / total_ops if total_ops > 0 else 0.0,
                    'average_time': stats['avg_time'],
                    'min_time': stats['min_time'] if stats['min_time'] != float('inf') else 0.0,
                    'max_time': stats['max_time']
                }
            
            # 타이밍 통계
            timing_stats = {}
            for op, timings in self.timing_data.items():
                if timings:
                    durations = [t['duration'] for t in timings]
                    timing_stats[op] = {
                        'count': len(durations),
                        'average': sum(durations) / len(durations),
                        'min': min(durations),
                        'max': max(durations),
                        'recent_average': sum(durations[-10:]) / min(10, len(durations))
                    }
            
            return {
                'basic': basic_stats,
                'operations': operation_stats,
                'timings': timing_stats,
                'fps': {
                    'current': self.stats['current_fps'],
                    'average': self.stats['average_fps'],
                    'peak': self.stats['peak_fps'],
                    'min': self.stats['min_fps'] if self.stats['min_fps'] != float('inf') else 0.0
                }
            }
    
    def get_fps(self) -> float:
        """현재 FPS 반환"""
        with self.lock:
            return self.stats['current_fps']
    
    def get_average_timing(self, operation: str) -> float:
        """특정 작업의 평균 시간 반환"""
        with self.lock:
            if operation in self.timing_data and self.timing_data[operation]:
                durations = [t['duration'] for t in self.timing_data[operation]]
                return sum(durations) / len(durations)
            return 0.0
    
    def get_recent_timing(self, operation: str, count: int = 10) -> List[float]:
        """최근 타이밍 데이터 반환"""
        with self.lock:
            if operation in self.timing_data:
                recent_data = list(self.timing_data[operation])[-count:]
                return [t['duration'] for t in recent_data]
            return []
    
    def reset(self):
        """통계 초기화"""
        with self.lock:
            self.timing_data.clear()
            self.frame_times.clear()
            self.operation_stats.clear()
            
            self.stats = {
                'start_time': time.time(),
                'total_operations': 0,
                'successful_operations': 0,
                'failed_operations': 0,
                'average_fps': 0.0,
                'current_fps': 0.0,
                'peak_fps': 0.0,
                'min_fps': float('inf'),
            }
            
            self.last_frame_time = time.time()
    
    def get_performance_summary(self) -> str:
        """성능 요약 문자열 반환"""
        stats = self.get_stats()
        
        summary = f"""
성능 모니터링 요약:
- 가동 시간: {stats['basic']['uptime']:.1f}초
- 총 작업 수: {stats['basic']['total_operations']}
- 초당 작업 수: {stats['basic']['operations_per_second']:.1f}
- 성공률: {stats['basic']['success_rate']*100:.1f}%
- 현재 FPS: {stats['fps']['current']:.1f}
- 평균 FPS: {stats['fps']['average']:.1f}
- 최고 FPS: {stats['fps']['peak']:.1f}
"""
        
        return summary.strip()
    
    def export_stats(self, filename: str = None):
        """통계를 파일로 내보내기"""
        if filename is None:
            filename = f"performance_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        stats = self.get_stats()
        
        import json
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        return filename 