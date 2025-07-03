#!/usr/bin/env python3
"""
간단한 아이콘 생성 스크립트
OnBoard OLED Monitor용 아이콘을 생성합니다.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    """OnBoard OLED Monitor 아이콘 생성"""
    try:
        # 아이콘 크기들 (ICO 파일은 여러 크기를 포함)
        sizes = [16, 32, 48, 64, 128, 256]
        
        # 각 크기별 이미지 생성
        images = []
        
        for size in sizes:
            # 이미지 생성 (검은 배경)
            img = Image.new('RGBA', (size, size), (0, 0, 0, 255))
            draw = ImageDraw.Draw(img)
            
            # 외곽 테두리 (밝은 회색)
            border_width = max(1, size // 32)
            draw.rectangle([0, 0, size-1, size-1], 
                         outline=(200, 200, 200, 255), 
                         width=border_width)
            
            # 내부 사각형 (OLED 화면 표현)
            margin = size // 8
            inner_rect = [margin, margin, size-margin-1, size-margin-1]
            draw.rectangle(inner_rect, 
                         outline=(100, 150, 255, 255), 
                         width=max(1, size // 64))
            
            # 중앙에 점들 (픽셀 표현)
            if size >= 32:
                dot_size = max(1, size // 32)
                dot_spacing = size // 16
                
                # 9개의 점으로 격자 패턴
                for i in range(3):
                    for j in range(3):
                        x = size // 2 - dot_spacing + i * dot_spacing
                        y = size // 2 - dot_spacing + j * dot_spacing
                        
                        # 일부 점만 표시 (체크무늬 패턴)
                        if (i + j) % 2 == 0:
                            draw.ellipse([x-dot_size, y-dot_size, 
                                        x+dot_size, y+dot_size],
                                       fill=(0, 255, 100, 255))
            
            # 작은 크기에서는 간단한 패턴
            elif size >= 16:
                center = size // 2
                dot_size = 1
                
                # 십자 패턴
                draw.rectangle([center-1, center-3, center+1, center+3],
                             fill=(0, 255, 100, 255))
                draw.rectangle([center-3, center-1, center+3, center+1],
                             fill=(0, 255, 100, 255))
            
            images.append(img)
        
        # ICO 파일로 저장
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
        images[0].save(icon_path, format='ICO', sizes=[(img.width, img.height) for img in images])
        
        print(f"✅ 아이콘 생성 완료: {icon_path}")
        print(f"📐 크기: {', '.join([f'{s}x{s}' for s in sizes])}")
        
        return True
        
    except Exception as e:
        print(f"❌ 아이콘 생성 실패: {str(e)}")
        return False

if __name__ == "__main__":
    print("OnBoard OLED Monitor 아이콘 생성기")
    print("=" * 40)
    
    # PIL 확인
    try:
        from PIL import Image
        print("✅ PIL 라이브러리 확인됨")
    except ImportError:
        print("❌ PIL 라이브러리가 필요합니다: pip install pillow")
        exit(1)
    
    # 아이콘 생성
    success = create_icon()
    
    if success:
        print("\n🎉 아이콘 생성이 완료되었습니다!")
        print("이제 build_installer.bat을 실행할 수 있습니다.")
    else:
        print("\n❌ 아이콘 생성에 실패했습니다.")
        print("기본 아이콘 없이 빌드가 진행됩니다.") 