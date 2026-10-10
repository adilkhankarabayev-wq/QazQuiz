import csv
from pathlib import Path
import streamlit as st

st.set_page_config(page_title='QazQuiz | 1–11', page_icon='📘', layout='wide')

@st.cache_data
def load_lessons():
    with (Path(__file__).parent / 'lessons.csv').open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

lessons = load_lessons()
lang = st.sidebar.selectbox('Тіл / Язык', ['Қазақша', 'Русский'])
kk = lang == 'Қазақша'
tr = (lambda a, b: a if kk else b)
st.title('📘 QazQuiz — 1–11')
st.caption(tr('2026–2027 оқу жылына арналған КТЖ сабақтарының каталогы', 'Каталог уроков КТП на 2026–2027 учебный год'))
st.info(tr('Бұл нұсқада сабақ тақырыптары мен оқу мақсаттары берілген. Тест тапсырмалары кейін қосылады.', 'В этой версии доступны темы уроков и цели обучения. Тестовые задания будут добавлены позже.'))

col1, col2, col3 = st.columns(3)
with col1:
    grade = st.selectbox(tr('Сынып', 'Класс'), list(range(1, 12)), index=5)
with col2:
    track = st.selectbox(tr('Бағыт', 'Направление'), ['ЖМБ', 'ҚГБ'] if grade >= 10 else ['Жалпы'], format_func=lambda x: ('ЕМН' if x == 'ЖМБ' else 'ОГН' if x == 'ҚГБ' else tr('Жалпы', 'Общее')) if not kk else x)
with col3:
    q = st.selectbox(tr('Тоқсан', 'Четверть'), [0, 1, 2, 3, 4], format_func=lambda x: tr('Барлығы', 'Все') if x == 0 else str(x))

items = [r for r in lessons if r['language'] == ('kk' if kk else 'ru') and int(r['grade']) == grade and r['track'] == track and (q == 0 or int(r['quarter']) == q)]
query = st.text_input(tr('Тақырып немесе оқу мақсаты бойынша іздеу', 'Поиск по теме или цели обучения'))
if query.strip():
    items = [r for r in items if query.casefold() in (r['topic'] + ' ' + r['objective']).casefold()]
st.metric(tr('Табылған сабақтар', 'Найдено уроков'), len(items))
if not items:
    st.warning(tr('Бұл таңдау бойынша сабақ табылмады.', 'Уроки не найдены.'))
for r in items:
    with st.expander(f"{r['lesson_no']}. {r['topic']}"):
        st.write('**' + tr('Бөлім', 'Раздел') + ':** ' + r['section'])
        st.write('**' + tr('Оқу мақсаты', 'Цель обучения') + ':** ' + (r['objective'] or '—'))
        st.write('**' + tr('Сағат', 'Часов') + ':** ' + (r['hours'] or '—'))
        st.caption(tr('Дереккөз', 'Источник') + ': ' + r['source'])

st.divider()
st.caption(tr('Ескерту: қазақша және орысша КТЖ деректері өз файлдарынан бөлек алынған; тақырыптар реті әртүрлі болуы мүмкін.', 'Примечание: казахские и русские планы извлечены отдельно из исходных файлов; порядок тем может различаться.'))
