"""Проверка модели Vosk"""
import vosk
from pathlib import Path

model_path = Path('models/vosk-model-ru-0.42')
print('Проверка модели...')
print(f'Путь: {model_path.absolute()}')

if not model_path.exists():
    print('❌ Модель не найдена!')
    exit(1)

try:
    model = vosk.Model(str(model_path))
    print('✓ Модель загружена успешно!')
    
    # Подсчет размера
    total_size = sum(f.stat().st_size for f in model_path.rglob('*') if f.is_file())
    size_mb = total_size / (1024 * 1024)
    print(f'Размер модели: {size_mb:.1f} МБ')
    
    # Проверка ключевых файлов
    required_files = [
        'am/final.mdl',
        'graph/HCLG.fst',
        'conf/model.conf',
    ]
    
    print('\nПроверка ключевых файлов:')
    all_ok = True
    for file in required_files:
        file_path = model_path / file
        if file_path.exists():
            print(f'  ✓ {file}')
        else:
            print(f'  ❌ {file} - НЕ НАЙДЕН!')
            all_ok = False
    
    if all_ok:
        print('\n✅ Модель полностью готова к использованию!')
    else:
        print('\n⚠️ Модель неполная!')
        exit(1)
        
except Exception as e:
    print(f'❌ Ошибка при загрузке модели: {e}')
    exit(1)

