"""QazQuiz 5.0 — public lesson catalog and Supabase teacher login (pilot).
Teacher login uses Supabase Auth and per-user RLS, never a service-role key.
Do not use real student data until legal/privacy/security review is complete.
"""
import csv
from pathlib import Path
import requests
import streamlit as st

st.set_page_config(page_title="QazQuiz 5.0", page_icon="📘", layout="wide")


def config():
    try:
        url = str(st.secrets["SUPABASE_URL"]).strip().rstrip("/")
        key = str(st.secrets["SUPABASE_KEY"]).strip()
        if not url.startswith("https://") or not key.startswith(("sb_publishable_", "eyJ")):
            return None
        return (url, key)
    except Exception:
        return None


def api(method, path, *, token=None, payload=None, params=None):
    cfg = config()
    if cfg is None:
        raise RuntimeError("Supabase settings are missing")
    url, key = cfg
    headers = {"apikey": key, "Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    response = requests.request(method, url + path, headers=headers, json=payload,
                                params=params, timeout=15)
    if response.status_code >= 400:
        raise RuntimeError("Supabase request failed (HTTP " + str(response.status_code) + ")")
    if not response.content:
        return None
    return response.json()


def current_session():
    session = st.session_state.get("qz_session")
    if not session:
        return None
    try:
        # Refresh every page run. This verifies the session and obtains a fresh access token.
        data = api("POST", "/auth/v1/token", payload={"refresh_token": session["refresh_token"]},
                   params={"grant_type": "refresh_token"})
        st.session_state.qz_session = data
        return data
    except (RuntimeError, KeyError, requests.RequestException, ValueError):
        st.session_state.pop("qz_session", None)
        return None


def login():
    st.subheader("🔐 Мұғалім ретінде кіру / Вход учителя")
    if not config():
        st.error("SUPABASE_URL және SUPABASE_KEY Streamlit Secrets ішінде табылмады.")
        return
    with st.form("teacher_login"):
        email = st.text_input("Email")
        password = st.text_input("Пароль", type="password")
        submit = st.form_submit_button("Кіру / Войти")
    if submit:
        try:
            data = api("POST", "/auth/v1/token", payload={"email": email.strip(),
                        "password": password, "gotrue_meta_security": {}},
                       params={"grant_type": "password"})
            if not data.get("access_token") or not data.get("refresh_token"):
                raise RuntimeError("No session")
            st.session_state.qz_session = data
            st.rerun()
        except (RuntimeError, requests.RequestException, ValueError):
            st.error("Кіру мүмкін болмады. Email мен парольді тексеріңіз. / Не удалось войти.")


def teacher_panel(session):
    token = session["access_token"]
    uid = session.get("user", {}).get("id")
    if not uid:
        st.error("Сеанс дұрыс емес. / Недействительная сессия.")
        return
    try:
        teachers = api("GET", "/rest/v1/teachers", token=token,
                       params={"select": "id,display_name", "id": "eq." + uid, "limit": "1"})
    except (RuntimeError, requests.RequestException, ValueError):
        st.error("Мұғалім профилін оқу мүмкін болмады. RLS саясаттарын тексеріңіз.")
        return
    if not teachers:
        st.warning("Бұл аккаунт teachers кестесінде тіркелмеген. / Аккаунт не назначен учителем.")
        return
    st.header("👩‍🏫 Мұғалім кабинеті / Кабинет учителя")
    st.write("Қош келдіңіз, **" + str(teachers[0]["display_name"]) + "**!")
    st.caption("Сынақ режимі: нақты балалардың деректерін енгізбеңіз.")
    with st.form("new_class", clear_on_submit=True):
        name = st.text_input("Сынып атауы / Название класса", placeholder="6А (сынақ)", max_chars=80)
        grade = st.selectbox("Сынып / Класс", list(range(1, 12)), index=5)
        submitted = st.form_submit_button("Сынып құру / Создать класс")
    if submitted:
        if not name.strip():
            st.warning("Сынып атауын енгізіңіз.")
        else:
            try:
                api("POST", "/rest/v1/classes", token=token,
                    payload={"teacher_id": uid, "name": name.strip(), "grade": grade})
                st.success("Сынып құрылды / Класс создан")
            except (RuntimeError, requests.RequestException, ValueError):
                st.error("Сыныпты сақтау мүмкін болмады. Кіру құқықтарын тексеріңіз.")
    try:
        classes = api("GET", "/rest/v1/classes", token=token,
                      params={"select": "id,name,grade,created_at", "teacher_id": "eq." + uid,
                              "order": "created_at.desc", "limit": "100"})
    except (RuntimeError, requests.RequestException, ValueError):
        st.error("Сыныптар тізімі ашылмады.")
        return
    st.subheader("Менің сыныптарым / Мои классы")
    if classes:
        st.dataframe(classes, hide_index=True, use_container_width=True)
    else:
        st.info("Әзірге сынып жоқ / Пока классов нет")
    st.info("Оқушыларға логин беру және нәтижелерді сақтау келесі кезеңде қосылады. ")


def show_teacher():
    session = current_session()
    if session:
        if st.button("Шығу / Выйти", key="logout"):
            try:
                api("POST", "/auth/v1/logout", token=session["access_token"])
            except (RuntimeError, requests.RequestException):
                pass
            st.session_state.pop("qz_session", None)
            st.rerun()
        teacher_panel(session)
    else:
        login()

def show_catalog():
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
    st.info(tr('КТЖ тақырыптары сақталған. 6-сыныптың компьютер жады тақырыбына алғашқы интерактивті сабақ қосылды.', 'Темы КТП сохранены. Первый интерактивный урок добавлен для темы памяти компьютера в 6 классе.'))

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

            # Бірінші интерактивті сабақ тек сәйкес оқу мақсатына тіркеледі.
            if grade == 6 and '6.1.1.1' in r['objective']:
                st.divider()
                st.subheader(tr('🧠 Интерактивті сабақ', '🧠 Интерактивный урок'))
                st.write(tr(
                    'Процессор командаларды орындайды. Жедел жад (RAM) жұмыс істеп тұрған бағдарламалардың деректерін уақытша сақтайды; қуат өшсе, ондағы ақпарат жоғалады. ROM тұрақты нұсқауларды сақтайды. SSD/HDD файлдарды ұзақ мерзімге сақтайды. Кэш — процессорға жақын орналасқан өте жылдам шағын жад. Процессордың негізгі сипаттамаларына ядролар саны және тактілік жиілік жатады.',
                    'Процессор выполняет команды. Оперативная память (ОЗУ/RAM) временно хранит данные работающих программ; после отключения питания данные теряются. ПЗУ (ROM) хранит постоянные инструкции. SSD/HDD предназначены для долговременного хранения файлов. Кэш — небольшая очень быстрая память рядом с процессором. Основные характеристики процессора — число ядер и тактовая частота.'
                ))
                # Суреттер тек теория бөлімінде беріледі, тест сұрақтары өзгермейді.
                st.markdown('#### ' + tr('🖼️ Құрылғыларды суреттен таны', '🖼️ Изучаем устройства по изображениям'))
                cards = [
                    ('system_unit', 'Жүйелік блок', 'Системный блок',
                     'Негізгі құрылғылар орналасатын корпус.', 'Корпус, в котором размещены основные компоненты.'),
                    ('cpu', 'Процессор (CPU)', 'Процессор (CPU)',
                     'Командаларды орындайды.', 'Выполняет команды.'),
                    ('ram', 'Жедел жад (RAM)', 'Оперативная память (RAM)',
                     'Деректерді уақытша сақтайды.', 'Временно хранит данные.'),
                    ('rom', 'Тұрақты жад (ROM)', 'Постоянная память (ROM)',
                     'Жүйені іске қосуға қажет нұсқауларды сақтайды.', 'Хранит инструкции для запуска системы.'),
                    ('storage', 'HDD және SSD', 'HDD и SSD',
                     'Файлдарды ұзақ мерзімге сақтайды.', 'Долго хранят файлы.'),
                    ('cache', 'Кэш-жад', 'Кэш-память',
                     'Процессордың деректерге қол жеткізуін жылдамдатады.', 'Ускоряет доступ процессора к данным.'),
                ]
                for offset in range(0, len(cards), 3):
                    cols = st.columns(3)
                    for col, (file, title_kk, title_ru, desc_kk, desc_ru) in zip(cols, cards[offset:offset+3]):
                        with col:
                            st.image(str(Path(__file__).parent / 'images' / (file + '.png')),
                                     caption=tr(title_kk, title_ru), use_container_width=True)
                            st.caption(tr(desc_kk, desc_ru))
                st.divider()
                st.subheader(tr('🎯 Үш деңгейлі тапсырмалар', '🎯 Три уровня заданий'))
                st.caption(tr('Әр деңгейді жеке орындаңыз. Нәтиже әзірге серверде сақталмайды.',
                              'Проходите уровни по отдельности. Результаты пока не сохраняются на сервере.'))

                easy = [
                    (tr('Қай құрылғы командаларды орындайды?', 'Какое устройство выполняет команды?'),
                     [tr('Процессор', 'Процессор'), tr('Монитор', 'Монитор'), tr('Пернетақта', 'Клавиатура')], 0,
                     tr('Процессор командаларды орындайды.', 'Процессор выполняет команды.')),
                    (tr('Қуат өшкенде қай жадтағы деректер жоғалады?', 'Данные какой памяти исчезают после отключения питания?'),
                     ['RAM (ОЗУ)', 'SSD', 'ROM (ПЗУ)'], 0,
                     tr('RAM — уақытша, энергияға тәуелді жад.', 'RAM — временная энергозависимая память.')),
                    (tr('Файлдарды ұзақ уақыт сақтайтын құрылғы?', 'Какое устройство долго хранит файлы?'),
                     ['SSD', 'RAM (ОЗУ)', tr('Кэш', 'Кэш')], 0,
                     tr('SSD — тұрақты жинақтауыш.', 'SSD — накопитель для долговременного хранения.')),
                    (tr('Процессорға жақын өте жылдам жад?', 'Какая память очень быстрая и близка к процессору?'),
                     [tr('Кэш', 'Кэш'), 'HDD', 'DVD'], 0,
                     tr('Кэш деректерге қол жеткізуді жылдамдатады.', 'Кэш ускоряет доступ к данным.')),
                    (tr('Тактiлік жиілік қандай бірлікпен өлшенеді?', 'В каких единицах измеряют тактовую частоту?'),
                     ['ГГц', 'ГБ', tr('Пиксель', 'Пиксель')], 0,
                     tr('Жиілік герцпен және оның еселік бірліктерімен өлшенеді.', 'Частоту измеряют в герцах и кратных единицах.')),
                ]
                medium = [
                    (tr('RAM қуат өшкеннен кейін де деректерді сақтайды.', 'RAM сохраняет данные после выключения питания.'), False,
                     tr('RAM энергияға тәуелді.', 'RAM энергозависима.')),
                    (tr('Кэш-жад процессордың жұмысын жылдамдатуға көмектеседі.', 'Кэш помогает ускорить работу процессора.'), True,
                     tr('Кэш жиі қажет болатын деректерге жылдам қол жеткізеді.', 'Кэш обеспечивает быстрый доступ к часто нужным данным.')),
                    (tr('SSD — тек ақпарат енгізуге арналған құрылғы.', 'SSD служит только для ввода информации.'), False,
                     tr('SSD файлдарды ұзақ сақтайды.', 'SSD долго хранит файлы.')),
                    (tr('Процессордың ядролар саны оның сипаттамаларының бірі.', 'Число ядер — одна из характеристик процессора.'), True,
                     tr('Ядролар саны — процессордың негізгі сипаттамасы.', 'Число ядер — характеристика процессора.')),
                ]
                hard = [
                    (tr('Компьютерді өшірген соң құжат жоғалмауы үшін қайда сақтау керек?',
                        'Где сохранить документ, чтобы он остался после выключения компьютера?'),
                     [tr('Жедел жадқа (RAM)', 'В RAM'), tr('SSD/HDD жинақтауышына', 'На SSD/HDD'), tr('Кэшке', 'В кэш')], 1,
                     tr('Файлды тұрақты жинақтауышқа сақтау керек.', 'Файл нужно сохранить на постоянный накопитель.')),
                    (tr('Бір мезгілде бірнеше бағдарлама жұмыс істеп тұр. Қай жад оларды уақытша қамтамасыз етеді?',
                        'Одновременно запущено несколько программ. Какая память временно хранит их данные?'),
                     [tr('Жедел жад (RAM)', 'RAM'), 'DVD', 'ROM'], 0,
                     tr('Іске қосылған бағдарламалар RAM қолданады.', 'Запущенные программы используют RAM.')),
                    (tr('Процессор жиі қолданатын деректерге тез жетуі үшін қай жад тиімді?',
                        'Какая память помогает процессору быстро получать часто используемые данные?'),
                     ['HDD', tr('Кэш-жад', 'Кэш'), 'DVD'], 1,
                     tr('Кэш-жад кідірісті азайтады.', 'Кэш уменьшает задержку доступа.')),
                ]

                def render_level(level_id, label, mode, questions):
                    with st.expander(label, expanded=(level_id == 'easy')):
                        form_key = f'level_{level_id}_{lang}_{grade}_{track}_{r["lesson_no"]}_{r["quarter"]}'
                        with st.form(form_key):
                            answers = []
                            for i, question in enumerate(questions, 1):
                                if mode == 'tf':
                                    prompt, correct, explanation = question
                                    options = [tr('Дұрыс', 'Верно'), tr('Бұрыс', 'Неверно')]
                                else:
                                    prompt, options, correct, explanation = question
                                answer = st.radio(f'{i}. {prompt}', options, index=None,
                                                  key=f'{form_key}_{i}')
                                answers.append(answer)
                            submitted = st.form_submit_button(tr('Деңгейді тексеру', 'Проверить уровень'))
                        if submitted:
                            if any(a is None for a in answers):
                                st.warning(tr('Барлық сұраққа жауап беріңіз.', 'Ответьте на все вопросы.'))
                            else:
                                score = 0
                                mistakes = []
                                for i, (answer, question) in enumerate(zip(answers, questions), 1):
                                    if mode == 'tf':
                                        _, correct, explanation = question
                                        expected = tr('Дұрыс', 'Верно') if correct else tr('Бұрыс', 'Неверно')
                                    else:
                                        _, options, correct, explanation = question
                                        expected = options[correct]
                                    if answer == expected:
                                        score += 1
                                    else:
                                        mistakes.append((i, expected, explanation))
                                total = len(questions)
                                st.success(tr(f'Нәтиже: {score}/{total} ({score/total:.0%})',
                                              f'Результат: {score}/{total} ({score/total:.0%})'))
                                st.progress(score / total)
                                for i, expected, explanation in mistakes:
                                    st.error(f'{i}. ' + tr('Дұрыс жауап: ', 'Правильный ответ: ') + expected + '. ' + explanation)
                                if score == total:
                                    st.balloons()

                render_level('easy', tr('🟢 1-деңгей — Жеңіл (5 сұрақ)', '🟢 Уровень 1 — Лёгкий (5 вопросов)'), 'mc', easy)
                render_level('medium', tr('🟡 2-деңгей — Орташа (4 дұрыс/бұрыс)', '🟡 Уровень 2 — Средний (4 верно/неверно)'), 'tf', medium)
                render_level('hard', tr('🔴 3-деңгей — Күрделі (3 жағдаяттық сұрақ)', '🔴 Уровень 3 — Сложный (3 задачи)'), 'mc', hard)
                st.caption(tr('Демо-нұсқа: нәтижелер серверде сақталмайды.',
                              'Демо-версия: результаты не сохраняются на сервере.'))


    st.divider()
    st.caption(tr('Ескерту: қазақша және орысша КТЖ деректері өз файлдарынан бөлек алынған; тақырыптар реті әртүрлі болуы мүмкін.', 'Примечание: казахские и русские планы извлечены отдельно из исходных файлов; порядок тем может различаться.'))

mode = st.sidebar.radio("Бөлім / Раздел", ["📚 Сабақтар / Уроки", "👩‍🏫 Мұғалім / Учитель"])
if mode.startswith("📚"):
    show_catalog()
else:
    show_teacher()
