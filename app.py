import csv
from datetime import datetime
from pathlib import Path
import streamlit as st

st.set_page_config(page_title='QazQuiz 2.0', page_icon='💻', layout='wide')
DATA_FILE = Path(__file__).with_name('results.csv')

LESSONS = {
    5: [('Ақпарат және оның түрлері', 'Информация и её виды', [('Ақпаратты қабылдауға не көмектеседі?', 'Что помогает воспринимать информацию?', ['Сезім мүшелері', 'Органы чувств', 'Принтер'], 0), ('Мәтін қандай ақпарат түрі?', 'Какой вид информации — текст?', ['Мәтіндік', 'Текстовая', 'Дыбыстық'], 0)])],
    6: [('Жүйелік блок және компьютер жады', 'Системный блок и память компьютера', [('Компьютердің миы қандай құрылғы?', 'Какое устройство называют мозгом компьютера?', ['Процессор', 'Монитор', 'Пернетақта'], 0), ('Қай жад ақпаратты уақытша сақтайды?', 'Какая память временно хранит данные?', ['Жедел жад (ОЗУ)', 'Тұрақты жад (ПЗУ)', 'SSD'], 0), ('Процессор жиілігі немен өлшенеді?', 'В чём измеряется частота процессора?', ['ГГц', 'ГБ', 'Пиксель'], 0)])],
    7: [('Алгоритм және программалау', 'Алгоритмы и программирование', [('Алгоритм дегеніміз не?', 'Что такое алгоритм?', ['Қадамдар тізбегі', 'Последовательность шагов', 'Монитор'], 0)])],
    8: [('Python негіздері', 'Основы Python', [('Python-да экранға шығару функциясы?', 'Какая функция выводит текст?', ['print()', 'input()', 'len()'], 0)])],
    9: [('Деректер базасы', 'Базы данных', [('Деректер базасындағы жазба дегеніміз?', 'Что такое запись в базе данных?', ['Кесте жолы', 'Строка таблицы', 'Баған'], 0)])],
    10: [('Ақпараттық қауіпсіздік', 'Информационная безопасность', [('Қауіпсіз пароль қандай?', 'Какой пароль безопаснее?', ['Ұзын әрі бірегей', 'Длинный и уникальный', '123456'], 0)])],
    11: [('Машиналық оқыту', 'Машинное обучение', [('Машиналық оқыту неге сүйенеді?', 'На чём основано машинное обучение?', ['Деректер мен модельдерге', 'Данным и моделям', 'Тек мониторға'], 0)])],
}

st.title('💻 QazQuiz 2.0')
lang = st.sidebar.selectbox('Тіл / Язык', ['Қазақша', 'Русский'])
kz = lang == 'Қазақша'
student = st.sidebar.text_input('Оқушының аты-жөні' if kz else 'Имя и фамилия ученика')
grade = st.sidebar.selectbox('Сынып' if kz else 'Класс', list(LESSONS.keys()))
section = st.sidebar.radio('Бөлім' if kz else 'Раздел', ['Сабақтар', 'Нәтижелер'] if kz else ['Уроки', 'Результаты'])

if section in ('Нәтижелер', 'Результаты'):
    st.header('📊 Нәтижелер' if kz else '📊 Результаты')
    if DATA_FILE.exists():
        import pandas as pd
        df = pd.read_csv(DATA_FILE)
        if student.strip():
            df = df[df['student'].str.casefold() == student.strip().casefold()]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info('Әзірге нәтиже жоқ.' if kz else 'Результатов пока нет.')
else:
    st.header(f'{grade}-сынып' if kz else f'{grade} класс')
    lesson_options = LESSONS[grade]
    selected = st.selectbox('Сабақты таңдаңыз' if kz else 'Выберите урок', range(len(lesson_options)), format_func=lambda i: lesson_options[i][0 if kz else 1])
    title_kz, title_ru, questions = lesson_options[selected]
    st.subheader(title_kz if kz else title_ru)
    st.caption('Бұл — демонстрациялық сабақ. Тақырыптар мен сұрақтар кезең-кезеңімен толықтырылады.' if kz else 'Это демонстрационный урок. Темы и вопросы будут добавляться постепенно.')
    with st.form(f'quiz_{grade}_{selected}_{lang}'):
        answers = []
        for i, (q_kz, q_ru, options, correct) in enumerate(questions, 1):
            st.markdown(f'**{i}. {q_kz if kz else q_ru}**')
            # Each option has a distinct index, so duplicate translations do not affect scoring.
            choice = st.radio('Жауап' if kz else 'Ответ', list(range(len(options))), format_func=lambda j, opts=options: opts[j], index=None, key=f'q_{grade}_{selected}_{lang}_{i}')
            answers.append(choice)
        submit = st.form_submit_button('Жауаптарды тексеру' if kz else 'Проверить ответы', type='primary')
    if submit:
        if not student.strip():
            st.error('Алдымен аты-жөніңізді енгізіңіз.' if kz else 'Сначала введите имя и фамилию.')
        elif any(a is None for a in answers):
            st.warning('Барлық сұраққа жауап беріңіз.' if kz else 'Ответьте на все вопросы.')
        else:
            score = sum(a == q[3] for a, q in zip(answers, questions))
            percent = round(100 * score / len(questions))
            st.success(f'{"Нәтиже" if kz else "Результат"}: {score}/{len(questions)} ({percent}%)')
            st.progress(percent / 100)
            is_new = not DATA_FILE.exists()
            with DATA_FILE.open('a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                if is_new:
                    writer.writerow(['date', 'student', 'grade', 'lesson', 'score', 'total', 'percent'])
                writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M'), student.strip(), grade, title_kz, score, len(questions), percent])
            st.info('Нәтиже сақталды.' if kz else 'Результат сохранён.')
            if score == len(questions):
                st.balloons()
