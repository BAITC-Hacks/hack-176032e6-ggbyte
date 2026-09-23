"""Independent synthetic demonstration authored for this repository, NOT organizer data."""
import csv
import json
from pathlib import Path


def dataset():
    meta = {'dataset': 'Independent GGBYTE SKILLS demo', 'as_of_date': '2026-10-01',
            'content_version': 2, 'synthetic': True,
            'description': 'Учебные профили, навыки и события созданы для демонстрации. Это не сотрудники или данные банка.'}
    skill_rows = [
        ('DESIGN', 'System Design', 'hard', 'engineering', 'Проектирование границ сервисов, хранения данных и отказоустойчивых решений.'),
        ('SPEAK', 'Public Speaking', 'soft', 'communication', 'Понятные выступления, структура аргументов и ответы на вопросы аудитории.'),
        ('CODE', 'Programming', 'hard', 'engineering', 'Читаемый код, обработка ошибок, проверки и безопасный рефакторинг.'),
        ('SQL', 'SQL и работа с данными', 'hard', 'data', 'Запросы, объединения таблиц, оконные функции и проверка качества данных.'),
        ('ANALYSIS', 'Аналитическое мышление', 'hard', 'data', 'Формулировка гипотез, выбор метрик и проверка выводов на данных.'),
        ('VIZ', 'Визуализация данных', 'hard', 'data', 'Выбор диаграмм и создание понятных отчётов для принятия решений.'),
        ('TEST', 'Тестирование и качество', 'hard', 'engineering', 'Тест-дизайн, проверка рисков и воспроизводимые проверки продукта.'),
        ('SECURITY', 'Безопасная разработка', 'hard', 'engineering', 'Моделирование угроз, контроль доступа и защита чувствительных данных.'),
        ('DELIVERY', 'CI/CD и выпуск изменений', 'hard', 'engineering', 'Автоматизация проверок, безопасные релизы и восстановление после ошибок.'),
        ('COLLAB', 'Командная работа', 'soft', 'communication', 'Согласование решений, конструктивная обратная связь и совместная работа.'),
        ('LEADERSHIP', 'Наставничество', 'soft', 'leadership', 'Развитие коллег, постановка целей и поддержка самостоятельности команды.'),
        ('PRODUCT', 'Продуктовое мышление', 'soft', 'product', 'Связь пользовательской проблемы, ценности решения и измеримого результата.'),
    ]
    skills = [dict(zip(('skill_id', 'name', 'type', 'category', 'description'), row)) for row in skill_rows]
    roles = ['Backend Engineer', 'Data Analyst', 'QA Engineer']
    grades = ['Junior', 'Middle', 'Senior', 'Lead']
    # Keep the original three requirements and the E0001 Senior demonstration intact.
    profiles = [{'role': roles[0], 'grade': grade,
                 'required_skills': {'DESIGN': n, 'SPEAK': min(2, n), 'CODE': n},
                 'critical_skills': ['DESIGN']}
                for grade, n in [('Junior', 1), ('Middle', 2), ('Senior', 4)]]
    profiles.append({'role': roles[0], 'grade': 'Lead', 'required_skills': {
        'DESIGN': 5, 'SPEAK': 2, 'CODE': 5, 'SQL': 3, 'ANALYSIS': 2, 'VIZ': 2,
        'TEST': 3, 'SECURITY': 3, 'DELIVERY': 3, 'COLLAB': 4, 'LEADERSHIP': 3, 'PRODUCT': 3},
        'critical_skills': ['DESIGN', 'SECURITY', 'LEADERSHIP']})
    requirements = {
        'Data Analyst': [
            {'SQL': 1, 'ANALYSIS': 1, 'VIZ': 1, 'PRODUCT': 1, 'COLLAB': 1, 'SPEAK': 1},
            {'SQL': 3, 'ANALYSIS': 2, 'VIZ': 2, 'PRODUCT': 2, 'COLLAB': 2, 'SPEAK': 2},
            {'SQL': 4, 'ANALYSIS': 4, 'VIZ': 4, 'PRODUCT': 3, 'COLLAB': 3, 'SPEAK': 2},
            {'SQL': 5, 'ANALYSIS': 5, 'VIZ': 4, 'PRODUCT': 4, 'COLLAB': 4, 'LEADERSHIP': 3, 'SPEAK': 2},
        ],
        'QA Engineer': [
            {'TEST': 1, 'CODE': 1, 'SECURITY': 1, 'COLLAB': 1, 'SPEAK': 1},
            {'TEST': 3, 'CODE': 2, 'SECURITY': 2, 'DELIVERY': 2, 'SQL': 2, 'COLLAB': 2, 'SPEAK': 1},
            {'TEST': 4, 'CODE': 3, 'SECURITY': 3, 'DELIVERY': 3, 'SQL': 3, 'COLLAB': 3, 'SPEAK': 2},
            {'TEST': 5, 'CODE': 3, 'SECURITY': 4, 'DELIVERY': 4, 'SQL': 4, 'COLLAB': 4, 'LEADERSHIP': 3, 'SPEAK': 2},
        ],
    }
    for role, targets in requirements.items():
        for grade, required in zip(grades, targets):
            profiles.append({'role': role, 'grade': grade, 'required_skills': required,
                             'critical_skills': ['SQL', 'ANALYSIS'] if role == 'Data Analyst' else ['TEST', 'SECURITY']})

    def levels(**values):
        return {row[0]: values.get(row[0], 0) for row in skill_rows}

    staff = [
        ('E0001', 'Demo Employee', roles[0], 'Middle', 'Senior', levels(DESIGN=2, SPEAK=0, CODE=3, SQL=1, ANALYSIS=1, VIZ=0, TEST=2, SECURITY=1, DELIVERY=2, COLLAB=2, LEADERSHIP=1, PRODUCT=1)),
        ('DEMO2', 'Ready Employee', roles[0], 'Middle', 'Senior', levels(DESIGN=4, SPEAK=2, CODE=4, SQL=3, ANALYSIS=2, VIZ=2, TEST=3, SECURITY=3, DELIVERY=3, COLLAB=3, LEADERSHIP=2, PRODUCT=2)),
        ('DEMO3', 'Starter Employee', roles[0], 'Middle', 'Senior', levels(DESIGN=0, SPEAK=1, CODE=1, SQL=1, ANALYSIS=1, TEST=1, SECURITY=1, DELIVERY=1, COLLAB=1, PRODUCT=1)),
        ('DEMO4', 'Демо · Начинающий аналитик', roles[1], 'Junior', 'Middle', levels(DESIGN=1, SPEAK=1, CODE=1, SQL=1, ANALYSIS=1, VIZ=0, TEST=1, SECURITY=1, COLLAB=2, PRODUCT=1)),
        ('DEMO5', 'Демо · Продуктовый аналитик', roles[1], 'Middle', 'Senior', levels(DESIGN=1, SPEAK=1, CODE=2, SQL=3, ANALYSIS=3, VIZ=2, TEST=1, SECURITY=1, DELIVERY=1, COLLAB=2, LEADERSHIP=1, PRODUCT=2)),
        ('DEMO6', 'Демо · Начинающий тестировщик', roles[2], 'Junior', 'Middle', levels(DESIGN=1, SPEAK=1, CODE=2, SQL=1, ANALYSIS=1, TEST=1, SECURITY=1, DELIVERY=1, COLLAB=1, PRODUCT=1)),
        ('DEMO7', 'Демо · Инженер качества', roles[2], 'Middle', 'Senior', levels(DESIGN=2, SPEAK=1, CODE=3, SQL=2, ANALYSIS=2, VIZ=1, TEST=3, SECURITY=1, DELIVERY=2, COLLAB=2, LEADERSHIP=1, PRODUCT=2)),
        ('DEMO8', 'Демо · Будущий технический лидер', roles[0], 'Senior', 'Lead', levels(DESIGN=4, SPEAK=2, CODE=4, SQL=3, ANALYSIS=2, VIZ=1, TEST=3, SECURITY=2, DELIVERY=3, COLLAB=3, LEADERSHIP=1, PRODUCT=2)),
    ]
    departments = {roles[0]: 'Демо · Разработка', roles[1]: 'Демо · Аналитика', roles[2]: 'Демо · Качество'}
    employees = [{'employee_id': eid, 'full_name': name, 'department': departments[role], 'role': role, 'grade': grade,
                  'manager_id': None, 'hire_date': '2024-01-01', 'tenure_months': 33, 'work_format': 'remote', 'preferred_language': 'ru',
                  'career_goal': {'target_role': role, 'target_grade': target}, 'skills': values, 'last_review_date': '2026-09-01'}
                 for eid, name, role, grade, target, values in staff]

    def gain(skill, amount, cap=4):
        return {'skill_id': skill, 'gain': amount, 'max_level': cap}

    def event(eid, title, description, gains, **extra):
        return {'event_id': eid, 'title': title, 'description': description, 'type': 'course', 'format': 'self_paced',
                'duration_hours': 4, 'mandatory': False, 'target_roles': roles[:], 'target_grades': grades[:],
                'develops_skills': gains, 'prerequisites': {}, 'upcoming_sessions': [], **extra}

    events = [
        event('DEMO_DESIGN', 'Практика проектирования систем', 'Разберите учебный сервис: выделите компоненты, сравните варианты хранения данных и составьте схему обработки отказов.', [gain('DESIGN', 2)], target_roles=[roles[0]]),
        event('DEMO_SPEAK', 'Презентации без стресса', 'Подготовьте пятиминутное объяснение технической идеи и потренируйте структуру выступления на небольшой учебной группе.', [gain('SPEAK', 1)], type='workshop', format='online', upcoming_sessions=['2026-10-10']),
        event('DEMO_SPEAK_PRACTICE', 'Практика выступления с обратной связью', 'Запишите короткую презентацию, получите обратную связь по аргументам и темпу и улучшите выступление перед повторной попыткой.', [gain('SPEAK', 1)], duration_hours=2, prerequisites={'SPEAK': 1}),
        event('DEMO_CODE', 'Надёжный код', 'Улучшите обработку ошибок в учебном модуле, добавьте проверки граничных случаев и проведите небольшой рефакторинг.', [gain('CODE', 1)], prerequisites={'CODE': 2}, target_roles=[roles[0]]),
        event('DEMO_MANDATORY', 'Обязательный инструктаж', 'Обязательное знакомство с учебными правилами работы и каналами обращения за помощью. Не влияет на карьерные рекомендации.', [], mandatory=True, duration_hours=1),
        event('DEMO_FUTURE', 'Архитектурная лаборатория', 'На совместном разборе защитите выбор границ сервисов и стратегии масштабирования учебной системы.', [gain('DESIGN', 1)], format='online', upcoming_sessions=['2026-11-01'], prerequisites={'DESIGN': 3}, target_roles=[roles[0]]),
        event('DEMO_FOUNDATIONS', 'От первого модуля к сервису', 'Соберите небольшой сервис из модулей, опишите его зависимости и закрепите основы кода перед архитектурным практикумом.', [gain('DESIGN', 2, 2), gain('CODE', 2, 3)], duration_hours=6, target_roles=[roles[0]]),
        event('DEMO_SQL_BASE', 'SQL: запросы для рабочих задач', 'Изучите объединения, группировки и проверки пропусков на синтетических таблицах. Подготовьте воспроизводимый запрос для отчёта.', [gain('SQL', 2, 3)], duration_hours=5),
        event('DEMO_SQL_ADV', 'SQL: сложные запросы и качество данных', 'Используйте оконные функции, исследуйте план выполнения и добавьте проверки согласованности учебных данных.', [gain('SQL', 2, 5)], duration_hours=6, prerequisites={'SQL': 2}),
        event('DEMO_ANALYSIS_BASE', 'От вопроса к проверяемой гипотезе', 'Переведите пользовательский вопрос в гипотезу, определите метрику и отделите наблюдение от причинного объяснения.', [gain('ANALYSIS', 2, 3)], duration_hours=3),
        event('DEMO_ANALYSIS_ADV', 'Эксперименты и обоснованные решения', 'Сравните варианты решения на синтетическом эксперименте, оцените неопределённость и сформулируйте ограничения вывода.', [gain('ANALYSIS', 2, 5)], duration_hours=5, prerequisites={'ANALYSIS': 2}),
        event('DEMO_VIZ', 'Понятные дашборды', 'Выберите подходящие диаграммы, уберите неоднозначные шкалы и создайте отчёт с ясным ответом на вопрос пользователя.', [gain('VIZ', 3, 4)], duration_hours=4, prerequisites={'ANALYSIS': 1}),
        event('DEMO_PRODUCT', 'Ценность продукта и метрики результата', 'Разберите учебный пользовательский сценарий, сформулируйте ожидаемую ценность и согласуйте метрики полезного результата.', [gain('PRODUCT', 3, 4)], type='workshop', format='online', upcoming_sessions=['2026-10-16'], duration_hours=3),
        event('DEMO_TEST_BASE', 'Тест-дизайн по рискам', 'Составьте проверки для учебного продукта: границы значений, негативные сценарии и приоритеты по последствиям ошибки.', [gain('TEST', 2, 3)], duration_hours=4),
        event('DEMO_TEST_ADV', 'Стратегия качества сервиса', 'Постройте уровни проверок, определите критерии выпуска и научитесь разбирать нестабильные тесты на учебном сервисе.', [gain('TEST', 2, 5)], duration_hours=6, prerequisites={'TEST': 2}),
        event('DEMO_SECURITY', 'Безопасность в повседневной разработке', 'Найдите угрозы в учебном API, проверьте границы доступа и предложите безопасную обработку входных данных и секретов.', [gain('SECURITY', 3, 4)], duration_hours=5, prerequisites={'CODE': 1}),
        event('DEMO_DELIVERY', 'Проверяемый и обратимый релиз', 'Соберите учебный процесс сборки и тестирования, подготовьте план отката и разберите сигнал неудачного выпуска.', [gain('DELIVERY', 3, 4)], duration_hours=5, prerequisites={'CODE': 1}),
        event('DEMO_COLLAB', 'Рабочие договорённости и обратная связь', 'Потренируйте обсуждение спорного решения, запрос обратной связи и фиксацию договорённостей в совместной учебной задаче.', [gain('COLLAB', 2, 4)], type='workshop', format='online', upcoming_sessions=['2026-10-14'], duration_hours=2),
        event('DEMO_LEADERSHIP', 'Наставник: помогать, не решая за коллегу', 'Составьте план развития учебного подопечного, проведите встречу с обратной связью и определите проверяемые признаки самостоятельности.', [gain('LEADERSHIP', 2, 3), gain('COLLAB', 1, 4)], type='mentoring', format='online', upcoming_sessions=['2026-10-21'], prerequisites={'COLLAB': 3}, duration_hours=4),
        event('DEMO_SYSTEM_LEAD', 'Архитектурные решения технического лидера', 'Проведите ревью сложного учебного сервиса: согласуйте архитектурные компромиссы, стандарты кода и план технических изменений.', [gain('DESIGN', 1, 5), gain('CODE', 1, 5)], prerequisites={'DESIGN': 4, 'CODE': 4, 'SPEAK': 2}, target_roles=[roles[0]], duration_hours=6),
        event('DEMO_VIZ_ADV', 'От отчёта к аналитической истории', 'Перестройте готовый дашборд под решение руководителя, свяжите несколько метрик и объясните ограничения интерпретации данных.', [gain('VIZ', 1, 5)], prerequisites={'VIZ': 3, 'ANALYSIS': 2}, duration_hours=3),
        event('DEMO_QA_AUTOMATION', 'Автоматизация проверок данных и API', 'Свяжите проверки API с SQL-проверками результата, подготовьте устойчивые учебные сценарии и разберите причины ложных срабатываний.', [gain('TEST', 1, 5), gain('SQL', 1, 4)], prerequisites={'TEST': 3, 'SQL': 2, 'CODE': 2}, duration_hours=5),
    ]
    history = [{'record_id': f'FIX{i}', 'employee_id': 'E0001', 'event_id': 'DEMO_SPEAK', 'date': f'2026-08-{i+10}', 'due_date': '',
                'status': 'no_show', 'completion_pct': 0, 'score': '', 'feedback_rating': '', 'assigned_by': 'self'} for i in range(3)]
    participation = [
        ('DEMO2', 'DEMO_DESIGN', '2026-07-10', 'completed', 100),
        ('DEMO2', 'DEMO_CODE', '2026-08-15', 'completed', 100),
        ('DEMO2', 'DEMO_SPEAK', '2026-08-20', 'completed', 100),
        ('DEMO2', 'DEMO_SPEAK_PRACTICE', '2026-08-25', 'completed', 100),
        ('DEMO3', 'DEMO_FOUNDATIONS', '2026-09-29', 'in_progress', 40),
        ('DEMO3', 'DEMO_MANDATORY', '2026-09-15', 'completed', 100),
        ('DEMO4', 'DEMO_SQL_BASE', '2026-09-25', 'in_progress', 60),
        ('DEMO4', 'DEMO_VIZ', '2026-08-28', 'no_show', 0),
        ('DEMO4', 'DEMO_PRODUCT', '2026-09-22', 'declined', 0),
        ('DEMO5', 'DEMO_SQL_BASE', '2026-08-01', 'completed', 100),
        ('DEMO5', 'DEMO_ANALYSIS_BASE', '2026-08-15', 'completed', 100),
        ('DEMO5', 'DEMO_VIZ', '2026-09-28', 'in_progress', 70),
        ('DEMO5', 'DEMO_SPEAK', '2026-08-17', 'dropped', 35),
        ('DEMO6', 'DEMO_TEST_BASE', '2026-09-26', 'in_progress', 50),
        ('DEMO6', 'DEMO_SECURITY', '2026-09-18', 'overdue', 25),
        ('DEMO6', 'DEMO_MANDATORY', '2026-08-12', 'completed', 100),
        ('DEMO7', 'DEMO_TEST_BASE', '2026-08-20', 'completed', 100),
        ('DEMO7', 'DEMO_SECURITY', '2026-09-15', 'no_show', 0),
        ('DEMO7', 'DEMO_QA_AUTOMATION', '2026-09-30', 'in_progress', 20),
        ('DEMO8', 'DEMO_COLLAB', '2026-08-11', 'completed', 100),
        ('DEMO8', 'DEMO_DELIVERY', '2026-08-19', 'completed', 100),
        ('DEMO8', 'DEMO_SECURITY', '2026-09-23', 'completed', 100),
        ('DEMO8', 'DEMO_LEADERSHIP', '2026-09-30', 'in_progress', 30),
    ]
    for i, (eid, activity, day, status, percentage) in enumerate(participation, 1):
        history.append({'record_id': f'DEMO_HISTORY_{i:03}', 'employee_id': eid, 'event_id': activity, 'date': day,
                        'due_date': '2026-09-17' if status == 'overdue' else '', 'status': status,
                        'completion_pct': percentage, 'score': '', 'feedback_rating': '', 'assigned_by': 'self'})
    return {'employees': {'meta': meta, 'employees': employees}, 'events': {'meta': meta, 'events': events},
            'skills': {'meta': meta, 'skills': skills, 'role_profiles': profiles,
                       'proficiency_scale': dict(enumerate(['Нет практики', 'Знаком с основами', 'Работает с поддержкой',
                                                          'Работает самостоятельно', 'Решает сложные задачи', 'Развивает практику']))}, 'history': history}


def write(root):
    data = Path(root) / 'data'
    data.mkdir(exist_ok=True)
    fixtures = dataset()
    for name in ('employees', 'events', 'skills'):
        (data / f'{name}.json').write_text(json.dumps(fixtures[name], ensure_ascii=False, indent=2), encoding='utf-8')
    with (data / 'activity_history.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(fixtures['history'][0]))
        writer.writeheader()
        writer.writerows(fixtures['history'])
