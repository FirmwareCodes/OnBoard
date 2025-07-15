#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
배터리 내부저항 계산기
Battery Internal Resistance Calculator

부하 전후의 전압과 부하저항값을 입력하여 배터리의 내부저항을 계산합니다.
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import json

# 로컬 모듈 임포트 추가
from calculation_engine import BatteryCalculationEngine

class BatteryResistanceCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("배터리 내부저항 계산기 - 직류부하법 (DC Load Method)")
        self.root.geometry("900x800")  # 창 크기 확대
        
        # 계산 결과 저장을 위한 리스트
        self.calculation_history = []
        
        self.create_widgets()
        
    def create_widgets(self):
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 제목
        title_label = ttk.Label(main_frame, text="배터리 내부저항 계산기 - 직류부하법 (DC Load Method)", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=4, pady=(0, 15))
        
        # 측정 안내 섹션 (간소화)
        guide_frame = ttk.LabelFrame(main_frame, text="직류부하법 측정 안내", padding="8")
        guide_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))
        
        guide_text = """직류부하법 측정 순서: 1) 개방전압(OCV) 측정 → 2) 직류 부하 연결 → 3) 안정화 대기 → 4) 부하 단자전압 및 전류 측정

⚠️ 중요: 직류부하법은 부하 연결 후 충분한 안정화 시간이 필요합니다! (과도응답 제거)

권장 안정화 시간: • 1S-4S 리튬이온: 10-15초  • 6S 이상 리튬이온: 15-30초  • 납축전지: 30-60초

적절한 부하 선택: • 1S (3.7V): 1-5Ω  • 6S (22.2V): 5-20Ω  • 12V 납축전지: 1-10Ω

📌 팁: 전류를 직접 측정하면 더 정확한 결과를 얻을 수 있습니다."""
        
        guide_label = tk.Label(guide_frame, text=guide_text, justify=tk.LEFT, 
                              font=("Arial", 9), wraplength=850)
        guide_label.pack(fill=tk.BOTH, expand=True)
        
        # 입력 섹션
        input_frame = ttk.LabelFrame(main_frame, text="직류부하법 측정값 입력", padding="10")
        input_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 개방전압 입력 (OCV)
        ttk.Label(input_frame, text="개방전압 OCV (V):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.no_load_voltage = tk.StringVar(value="22.2")  # 6S 배터리 기본값
        ttk.Entry(input_frame, textvariable=self.no_load_voltage, width=15).grid(row=0, column=1, padx=5, pady=5)
        
        # 부하 단자전압 입력
        ttk.Label(input_frame, text="부하 단자전압 (V):").grid(row=0, column=2, sticky=tk.W, pady=5)
        self.load_voltage = tk.StringVar(value="21.5")  # 6S 배터리 기본값
        ttk.Entry(input_frame, textvariable=self.load_voltage, width=15).grid(row=0, column=3, padx=5, pady=5)
        
        # 부하 저항 입력
        ttk.Label(input_frame, text="부하 저항 (Ω):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.load_resistance = tk.StringVar(value="10.0")  # 6S 배터리 기본값
        ttk.Entry(input_frame, textvariable=self.load_resistance, width=15).grid(row=1, column=1, padx=5, pady=5)
        
        # 측정된 부하 전류 입력 (선택적)
        ttk.Label(input_frame, text="측정된 부하전류 (A):").grid(row=1, column=2, sticky=tk.W, pady=5)
        self.measured_current = tk.StringVar()  # 기본값 없음 (선택적)
        current_entry = ttk.Entry(input_frame, textvariable=self.measured_current, width=15)
        current_entry.grid(row=1, column=3, padx=5, pady=5)
        
        # 전류 입력 설명 라벨
        current_help = ttk.Label(input_frame, text="(선택사항: 암페어미터로 직접 측정한 값)", font=("Arial", 8), foreground="gray")
        current_help.grid(row=2, column=2, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        # 측정 대기시간 입력
        ttk.Label(input_frame, text="안정화 시간 (초):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.stabilization_time = tk.StringVar(value="20")  # 6S 배터리 기본값
        ttk.Entry(input_frame, textvariable=self.stabilization_time, width=15).grid(row=3, column=1, padx=5, pady=5)
        
        # 계산 버튼
        calc_button = ttk.Button(input_frame, text="직류부하법 내부저항 계산", command=self.calculate_internal_resistance)
        calc_button.grid(row=4, column=0, columnspan=4, padx=5, pady=15)
        
        # 결과 섹션
        result_frame = ttk.LabelFrame(main_frame, text="계산 결과", padding="10")
        result_frame.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 결과 표시 (크기 증가)
        self.result_text = tk.Text(result_frame, height=18, width=80, wrap=tk.WORD)
        self.result_text.grid(row=0, column=0, columnspan=4, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 스크롤바
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_text.yview)
        scrollbar.grid(row=0, column=4, sticky=(tk.N, tk.S), padx=(5, 0))
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        # 버튼 섹션
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=4, pady=10)
        
        ttk.Button(button_frame, text="결과 지우기", command=self.clear_results).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="결과 저장", command=self.save_results).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="도움말", command=self.show_help).grid(row=0, column=2, padx=5)
        
        # 그리드 설정 (창 크기 조정 대응)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)  # 결과 프레임이 확장되도록
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
    def calculate_internal_resistance(self):
        try:
            # 입력값 검증
            v_ocv = float(self.no_load_voltage.get())     # 개방전압 (OCV)
            v_load = float(self.load_voltage.get())       # 부하 단자전압
            r_load = float(self.load_resistance.get())    # 부하 저항
            stab_time = float(self.stabilization_time.get())
            
            # 측정된 전류 (선택적)
            measured_current_str = self.measured_current.get().strip()
            i_measured = float(measured_current_str) if measured_current_str else None
            
            if v_ocv <= 0 or v_load <= 0 or r_load <= 0:
                messagebox.showerror("오류", "모든 값은 양수여야 합니다.")
                return
                
            if v_load >= v_ocv:
                messagebox.showerror("오류", "부하 전압은 개방전압(무부하 전압)보다 작아야 합니다.")
                return
            
            if i_measured is not None and i_measured <= 0:
                messagebox.showerror("오류", "측정된 전류는 양수여야 합니다.")
                return
            
            # BatteryMeasurement 객체 생성
            from calculation_engine import BatteryMeasurement
            measurement = BatteryMeasurement(
                no_load_voltage=v_ocv,
                load_voltage=v_load,
                load_resistance=r_load,
                measured_current=i_measured
            )
            
            # 직류부하법 계산 실행
            result = BatteryCalculationEngine.calculate_internal_resistance(measurement)
            
            # 셀 개수 자동 감지
            cell_count = BatteryCalculationEngine.detect_cell_count(v_ocv)
            cell_analysis = BatteryCalculationEngine.calculate_per_cell_resistance(
                v_ocv, result.internal_resistance, cell_count
            )
            
            # 배터리 타입 추정
            battery_analysis = BatteryCalculationEngine.estimate_battery_capacity(v_ocv, result.internal_resistance)
            
            # 측정 시간 검증
            time_validation = self.validate_measurement_time(cell_count, stab_time)
            
            # 결과 표시
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result_text = f"\n{'='*70}\n"
            result_text += f"직류부하법 (DC Load Method) 내부저항 측정 결과\n"
            result_text += f"계산 시간: {timestamp}\n"
            result_text += f"{'='*70}\n"
            
            result_text += f"입력 값:\n"
            result_text += f"  개방전압 (OCV): {v_ocv:.3f} V\n"
            result_text += f"  부하 단자전압: {v_load:.3f} V\n"
            result_text += f"  부하 저항: {r_load:.3f} Ω\n"
            if i_measured is not None:
                result_text += f"  측정된 전류: {i_measured:.3f} A ✓\n"
            result_text += f"  안정화 시간: {stab_time:.0f} 초\n"
            
            result_text += f"\n측정 시간 검증:\n"
            result_text += f"  {time_validation}\n"
            
            # 직류부하법 계산 과정 표시
            current_source = getattr(result, '_current_source', 'unknown')
            result_text += f"\n직류부하법 계산 과정:\n"
            
            if current_source == "measured":
                result_text += f"  1단계 - 부하 전류: I = {result.load_current:.3f} A (측정값 사용 ✓)\n"
                i_calc = v_load / r_load
                deviation = getattr(result, '_current_deviation', 0)
                result_text += f"           계산값과 비교: {i_calc:.3f} A (편차: {deviation:.1f}%)\n"
            else:
                result_text += f"  1단계 - 부하 전류: I = V_부하 / R_부하 = {v_load:.3f}V / {r_load:.3f}Ω = {result.load_current:.3f} A\n"
            
            result_text += f"  2단계 - 전압강하: ΔV = V_OCV - V_부하 = {v_ocv:.3f}V - {v_load:.3f}V = {result.voltage_drop:.3f} V\n"
            result_text += f"  3단계 - 내부저항: R = ΔV / I = {result.voltage_drop:.3f}V / {result.load_current:.3f}A = {result.internal_resistance:.6f} Ω\n"
            
            # 검증 결과
            verification_error = getattr(result, '_verification_error', 0)
            calculated_v_load = v_ocv - (result.load_current * result.internal_resistance)
            result_text += f"  4단계 - 검증: V_부하 = V_OCV - (I × R) = {v_ocv:.3f} - ({result.load_current:.3f} × {result.internal_resistance:.6f}) = {calculated_v_load:.3f} V\n"
            result_text += f"           검증 오차: {verification_error*1000:.2f} mV\n"
            
            result_text += f"\n배터리 구성:\n"
            result_text += f"  추정 셀 개수: {cell_count}S 배터리\n"
            result_text += f"  셀당 전압: {cell_analysis['cell_voltage']:.3f} V\n"
            result_text += f"  셀당 내부저항: {cell_analysis['estimated_cell_resistance']:.6f} Ω ({cell_analysis['estimated_cell_resistance_mohm']:.3f} mΩ)\n"
            
            # 직류부하법 특성 분석
            load_factor = getattr(result, '_load_factor', 0)
            internal_drop_ratio = getattr(result, '_internal_drop_ratio', 0)
            power_load = getattr(result, '_power_load', 0)
            power_total = getattr(result, '_power_total', 0)
            
            result_text += f"\n직류부하법 전기적 특성:\n"
            result_text += f"  전체 내부저항: {result.internal_resistance:.6f} Ω ({result.internal_resistance*1000:.3f} mΩ)\n"
            result_text += f"  부하 전류: {result.load_current:.3f} A\n"
            result_text += f"  내부 전압강하: {result.voltage_drop:.3f} V ({internal_drop_ratio:.2f}%)\n"
            result_text += f"  부하율: {load_factor:.3f}\n"
            result_text += f"  부하 전력: {power_load:.3f} W\n"
            result_text += f"  내부 전력손실: {result.power_loss:.3f} W\n"
            result_text += f"  총 공급전력: {power_total:.3f} W\n"
            result_text += f"  효율: {result.efficiency:.2f} %\n"
            result_text += f"  전력손실율: {(result.power_loss/power_total)*100:.2f} %\n"
            
            result_text += f"\n배터리 분석:\n"
            result_text += f"  추정 타입: {battery_analysis['estimated_type']}\n"
            result_text += f"  신뢰도: {battery_analysis['confidence']:.1%}\n"
            result_text += f"  상태: {battery_analysis['health_status']}\n"
            
            # 6S 배터리 특별 분석
            if cell_count == 6:
                result_text += f"\n6S 배터리 전용 분석:\n"
                result_text += f"  권장 충전 전압: {cell_count * 4.2:.1f}V (셀당 4.2V)\n"
                result_text += f"  방전 차단 전압: {cell_count * 3.0:.1f}V (셀당 3.0V)\n"
                result_text += f"  저장 전압: {cell_count * 3.8:.1f}V (셀당 3.8V)\n"
                
                if result.internal_resistance * 1000 > 400:
                    result_text += f"  ⚠️ 경고: 6S 배터리 내부저항이 높습니다.\n"
                elif result.internal_resistance * 1000 > 250:
                    result_text += f"  📊 주의: 6S 배터리 내부저항이 다소 높습니다.\n"
                else:
                    result_text += f"  ✅ 양호: 6S 배터리 내부저항이 정상 범위입니다.\n"
            
            result_text += f"{'='*70}\n"
            
            self.result_text.insert(tk.END, result_text)
            self.result_text.see(tk.END)
            
            # 계산 히스토리에 저장
            calculation_data = {
                'timestamp': timestamp,
                'method': 'DC_Load_Method',
                'v_ocv': v_ocv,
                'v_load': v_load,
                'r_load': r_load,
                'i_measured': i_measured,
                'stabilization_time': stab_time,
                'r_internal': result.internal_resistance,
                'i_load': result.load_current,
                'v_drop': result.voltage_drop,
                'load_power': power_load,
                'power_loss': result.power_loss,
                'total_power': power_total,
                'efficiency': result.efficiency,
                'cell_count': cell_count,
                'battery_type': battery_analysis['estimated_type'],
                'current_source': current_source
            }
            self.calculation_history.append(calculation_data)
            
        except ValueError as e:
            messagebox.showerror("오류", f"입력값 오류: {str(e)}")
        except Exception as e:
            messagebox.showerror("오류", f"계산 중 오류가 발생했습니다: {str(e)}")
    
    def validate_measurement_time(self, cell_count, actual_time):
        """측정 시간 검증"""
        if cell_count == 1:
            recommended_min, recommended_max = 10, 15
            battery_type = "리튬이온 1S"
        elif cell_count <= 4:
            recommended_min, recommended_max = 10, 15
            battery_type = f"리튬이온 {cell_count}S"
        elif cell_count >= 6:
            recommended_min, recommended_max = 15, 30
            battery_type = f"리튬이온 {cell_count}S"
        else:
            recommended_min, recommended_max = 20, 60
            battery_type = "기타 배터리"
        
        if actual_time < recommended_min:
            return f"⚠️ 경고: 안정화 시간이 부족합니다. {battery_type}는 최소 {recommended_min}초 권장"
        elif actual_time > recommended_max + 30:
            return f"📊 정보: 안정화 시간이 충분합니다. ({recommended_min}-{recommended_max}초 권장)"
        else:
            return f"✅ 적절: 안정화 시간이 적절합니다. ({recommended_min}-{recommended_max}초 권장)"
    
    def clear_results(self):
        self.result_text.delete(1.0, tk.END)
    
    def save_results(self):
        if not self.calculation_history:
            messagebox.showwarning("경고", "저장할 계산 결과가 없습니다.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                if filename.endswith('.json'):
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(self.calculation_history, f, ensure_ascii=False, indent=2)
                else:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(self.result_text.get(1.0, tk.END))
                
                messagebox.showinfo("성공", f"결과가 저장되었습니다: {filename}")
            except Exception as e:
                messagebox.showerror("오류", f"저장 중 오류가 발생했습니다: {str(e)}")
    
    def show_help(self):
        help_text = """
직류부하법 (DC Load Method) 배터리 내부저항 계산기 도움말

1. 직류부하법이란?
   직류부하법은 배터리에 일정한 직류 부하를 연결하여 내부저항을 측정하는 표준 방법입니다.
   IEC 61951-1, IEEE Std 1188 등의 국제 표준에서 규정된 방법입니다.

2. 측정 순서 (중요!):
   1) 개방전압(OCV) 측정: 부하 연결 없이 배터리 단자전압 측정
   2) 직류 부하 연결: 적절한 저항값의 부하를 배터리에 연결
   3) 안정화 대기: 과도응답이 끝날 때까지 충분히 대기
   4) 부하 상태 측정: 부하 단자전압과 부하전류 측정

3. 안정화 시간의 중요성:
   - 부하 연결 직후: 급격한 전압 변화 (과도응답)
   - 안정화 과정: 배터리 내부 화학반응이 평형상태에 도달
   - 안정화 완료: 일정한 전압과 전류 유지
   - 너무 빠른 측정: 과도응답으로 인한 오차 발생

4. 배터리별 권장 안정화 시간:
   - 1S-4S 리튬이온: 10-15초 (빠른 응답특성)
   - 6S 이상 리튬이온: 15-30초 (높은 전압, 복잡한 응답)
   - 납축전지: 30-60초 (느린 화학반응)
   - 니켈수소: 20-30초 (중간 수준 응답)

5. 직류부하법 계산 공식:
   R_internal = (V_OCV - V_load) / I_load
   
   여기서:
   - V_OCV: 개방전압 (Open Circuit Voltage)
   - V_load: 부하 단자전압
   - I_load: 부하전류
   - R_internal: 내부저항

6. 측정 정확도 향상 방법:
   - 전류 직접 측정: 암페어미터로 실제 전류 측정 (권장)
   - 적절한 부하 선택: 전압강하 0.1-0.5V 정도가 되는 부하
   - 온도 고려: 실온(20-25℃)에서 측정
   - 반복 측정: 동일 조건에서 3회 이상 측정하여 평균값 사용

7. 부하 선택 가이드:
   - 1S (3.7V): 1-5Ω (전류 0.7-3.7A)
   - 6S (22.2V): 5-20Ω (전류 1.1-4.4A)
   - 12V 납축전지: 1-10Ω (전류 1.2-12A)

8. 주의사항:
   - 모든 값은 양수여야 합니다
   - 부하 단자전압은 개방전압보다 작아야 합니다
   - 과부하 방지: 배터리 허용전류 내에서 측정
   - 안전: 고전압 배터리(6S 이상) 취급 시 절연 주의
   - 검증: 계산 검증 오차가 큰 경우 측정값 재확인

9. 프로그램 기능:
   - 직류부하법 표준 공식 적용
   - 측정값과 계산값 비교 검증
   - 계산 과정 단계별 표시
   - 배터리 타입 자동 추정
   - 6S 배터리 전용 분석
   - 측정 시간 적절성 검증
   - 결과 저장 (JSON/텍스트 파일)

10. 측정 오차 원인 및 해결:
    - 전류 편차 5% 이상: 부하 저항값 또는 전류 측정 재확인
    - 계산 검증 오차 1mV 이상: 측정값 정확성 재점검
    - 비정상적인 내부저항값: 배터리 상태 또는 측정 방법 점검
        """
        
        messagebox.showinfo("직류부하법 도움말", help_text)

def main():
    root = tk.Tk()
    app = BatteryResistanceCalculator(root)
    root.mainloop()

if __name__ == "__main__":
    main() 