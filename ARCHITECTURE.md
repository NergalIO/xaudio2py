# Архитектура проекта xaudio2py

## Обзор

Проект был полностью рефакторен с применением принципов ООП и SOLID для улучшения структуры, расширяемости и тестируемости кода.

## Новая структура проекта

```
src/xaudio2py/
├── api/                    # Публичный API (фасады)
│   ├── engine.py           # AudioEngine - чистый фасад
│   └── sound.py            # Sound, PlaybackHandle
│
├── core/                   # Доменная логика и абстракции
│   ├── exceptions.py       # Исключения (новые + алиасы для совместимости)
│   ├── interfaces.py       # Протоколы (IAudioBackend, IVoice, IAudioFormat)
│   ├── models.py           # Модели данных (AudioFormat, SoundData, etc.)
│   ├── registry.py         # PlaybackRegistry - управление воспроизведениями
│   └── thread.py           # Обратная совместимость (реэкспорт)
│
├── services/               # Use-cases / Orchestration
│   ├── engine_lifecycle.py # EngineLifecycleService - управление жизненным циклом
│   └── playback.py         # PlaybackService - операции воспроизведения
│
├── concurrency/            # Управление потоками
│   └── worker.py           # BackendWorker - worker thread без sleep
│
├── backends/               # Конкретные реализации бэкендов
│   ├── null_backend.py     # Тестовый бэкенд
│   └── xaudio2/            # XAudio2 реализация
│
├── formats/                # Парсеры форматов
│   ├── wav.py
│   └── mp3.py
│
└── utils/                  # Вспомогательные модули
    ├── log.py
    └── validate.py
```

## Применённые принципы SOLID

### SRP (Single Responsibility Principle)

**До рефакторинга:**
- `AudioEngine` делал всё: управление жизненным циклом, воспроизведениями, потоками, загрузкой форматов

**После рефакторинга:**
- `AudioEngine` - только фасад, делегирует работу сервисам
- `EngineLifecycleService` - только управление жизненным циклом
- `PlaybackService` - только операции воспроизведения
- `PlaybackRegistry` - только хранение и управление воспроизведениями
- `BackendWorker` - только выполнение команд в worker thread

### OCP (Open/Closed Principle)

**Реализовано через:**
- Интерфейсы (`IAudioBackend`, `IVoice`, `IAudioFormat`)
- Реестр форматов (автоматическое обнаружение)
- Dependency Injection в конструкторах

**Результат:**
- Новый backend можно добавить без изменения `AudioEngine`
- Новый формат можно добавить без изменения loader'а
- Новый worker можно добавить без изменения сервисов

### LSP (Liskov Substitution Principle)

**Гарантии:**
- Любой `IAudioBackend` может заменить другой без изменения логики engine
- `NullBackend` полностью совместим с `XAudio2Backend` по контракту
- Все backend'ы имеют одинаковые гарантии поведения

### ISP (Interface Segregation Principle)

**Разделение интерфейсов:**
- `IAudioBackend` - только операции с backend
- `IVoice` - только управление голосом
- `IBackendWorker` - только выполнение команд
- `IAudioFormat` - только загрузка форматов

**Результат:**
- Клиенты не зависят от интерфейсов, которые не используют
- Легко создавать mock-объекты для тестирования

### DIP (Dependency Inversion Principle)

**До рефакторинга:**
- `AudioEngine` зависел от конкретного `XAudio2Backend`
- Прямые вызовы `BackendWorker`

**После рефакторинга:**
- `AudioEngine` зависит от абстракций (`IAudioBackend`, сервисы)
- Сервисы зависят от интерфейсов, а не конкретных реализаций
- Конкретные реализации инжектируются через конструкторы

## Ключевые изменения

### 1. AudioEngine как чистый фасад

**Было:**
```python
class AudioEngine:
    def __init__(self):
        self._worker = BackendWorker(...)
        self._playbacks = {}
        # ... вся логика внутри
```

**Стало:**
```python
class AudioEngine:
    def __init__(self):
        self._lifecycle_service = EngineLifecycleService(...)
        self._playback_service = None  # Инициализируется в start()
    
    def play(self, sound, ...):
        return self._playback_service.start_playback(...)
```

### 2. Разделение ответственностей

**EngineLifecycleService:**
- Управление жизненным циклом движка
- Инициализация и shutdown backend
- Управление worker thread

**PlaybackService:**
- Операции воспроизведения (play, stop, pause, resume)
- Управление громкостью и панорамой
- Отслеживание состояния воспроизведений

**PlaybackRegistry:**
- Хранение информации о воспроизведениях
- Поиск и удаление воспроизведений
- Thread-safe доступ к данным

### 3. Улучшение работы с потоками

**Было:**
```python
time.sleep(0.01)  # ❌ Использование sleep
```

**Стало:**
```python
self._ready_event = threading.Event()
# ...
if not self._ready_event.wait(timeout=5.0):  # ✅ Использование Event
    raise RuntimeError("Worker thread failed to start")
```

**Улучшения:**
- Убран `sleep` как механизм синхронизации
- Использование `threading.Event` для ожидания готовности
- Явный shutdown с `join()` и таймаутами
- Гарантия невозможности вызова worker после остановки

### 4. Новая система исключений

**Новые исключения:**
- `AudioEngineError` - базовое исключение
- `EngineNotStartedError` - движок не запущен
- `PlaybackNotFoundError` - воспроизведение не найдено
- `BackendError` - ошибка backend (заменяет XAudio2Error)
- `AudioFormatError` - ошибка формата (заменяет InvalidAudioFormat)

**Обратная совместимость:**
- Старые имена (`XAudio2Error`, `InvalidAudioFormat`, etc.) доступны как алиасы
- Существующий код продолжает работать без изменений

### 5. Расширяемость

**Добавление нового backend:**
```python
class MyBackend(IAudioBackend):
    def initialize(self): ...
    def create_source_voice(self, ...): ...
    # ...

engine = AudioEngine(backend=MyBackend())
```

**Добавление нового формата:**
```python
class MyFormat(IAudioFormat):
    @property
    def extensions(self): return (".myformat",)
    def can_load(self, path): ...
    def load(self, path): ...

my_format = MyFormat()  # Автоматически регистрируется
```

## Обратная совместимость

### Сохранено:
- ✅ Публичный API `AudioEngine` полностью совместим
- ✅ Все методы работают так же, как раньше
- ✅ Старые имена исключений доступны как алиасы
- ✅ Примеры работают без изменений
- ✅ `BackendWorker` доступен из `core.thread` (реэкспорт)

### Изменено (внутреннее):
- ⚠️ Внутренняя структура `AudioEngine` изменилась
- ⚠️ Приватные атрибуты (`_playbacks`, `_worker`) больше не существуют напрямую
- ⚠️ Для доступа к внутренним компонентам используйте сервисы

## Тестирование

### Новые возможности:
- Легко создавать mock-объекты для сервисов
- `NullBackend` полностью изолирован
- Тесты не зависят от конкретных реализаций

### Пример теста:
```python
def test_playback_service():
    backend = NullBackend()
    worker = BackendWorker(backend)
    worker.start()
    
    service = PlaybackService(worker, backend)
    # ... тестирование
```

## Миграция

### Для пользователей библиотеки:
**Ничего не нужно менять!** Публичный API остался прежним.

### Для разработчиков:
1. Используйте новые имена исключений в новом коде
2. Используйте сервисы для расширения функциональности
3. Следуйте интерфейсам для создания новых компонентов

## Преимущества новой архитектуры

1. **Тестируемость**: Легко тестировать каждый компонент отдельно
2. **Расширяемость**: Легко добавлять новые backend'ы и форматы
3. **Поддерживаемость**: Чёткое разделение ответственностей
4. **Надёжность**: Улучшенная работа с потоками и исключениями
5. **Читаемость**: Понятная структура и именование

## Следующие шаги

- [ ] Добавить больше unit-тестов для сервисов
- [ ] Добавить интеграционные тесты
- [ ] Документировать внутренние API для расширения
- [ ] Рассмотреть добавление событий (events) для воспроизведений

