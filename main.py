import re
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


# =========================================================
# 페이지 설정
# =========================================================

st.set_page_config(
    page_title="맞춤형 학교 급식 추천",
    page_icon="🍱",
    layout="wide",
)


# =========================================================
# 음식 데이터
# =========================================================

FOOD_DATA = [
    {
        "name": "제육볶음",
        "image": "images/jeyuk.jpg",
        "emoji": "🥩",
        "category": "육류",
        "keywords": ["돼지", "돈육", "제육", "고기"],
    },
    {
        "name": "닭갈비",
        "image": "images/dakgalbi.jpg",
        "emoji": "🍗",
        "category": "육류",
        "keywords": ["닭", "닭갈비", "치킨"],
    },
    {
        "name": "돈가스",
        "image": "images/pork_cutlet.jpg",
        "emoji": "🍖",
        "category": "육류",
        "keywords": ["돈가스", "돈까스", "돼지"],
    },
    {
        "name": "샐러드",
        "image": "images/salad.jpg",
        "emoji": "🥗",
        "category": "채식",
        "keywords": ["샐러드", "채소", "야채"],
    },
    {
        "name": "비빔밥",
        "image": "images/bibimbap.jpg",
        "emoji": "🍚",
        "category": "채식",
        "keywords": ["비빔밥", "나물", "채소"],
    },
    {
        "name": "생선구이",
        "image": "images/fish.jpg",
        "emoji": "🐟",
        "category": "해산물",
        "keywords": ["생선", "고등어", "갈치", "구이"],
    },
    {
        "name": "잔치국수",
        "image": "images/noodles.jpg",
        "emoji": "🍜",
        "category": "면류",
        "keywords": ["국수", "면", "우동", "소면"],
    },
    {
        "name": "과일",
        "image": "images/fruit.jpg",
        "emoji": "🍎",
        "category": "후식",
        "keywords": ["과일", "사과", "배", "귤", "바나나"],
    },
]


# =========================================================
# 키워드
# =========================================================

MEAT_KEYWORDS = [
    "돼지", "돈육", "제육", "삼겹", "목살",
    "소고기", "쇠고기", "불고기", "갈비",
    "닭", "치킨", "닭갈비", "닭볶음",
    "오리", "햄", "소시지", "베이컨",
    "고기", "스테이크", "돈가스", "돈까스",
]

SEAFOOD_KEYWORDS = [
    "생선", "고등어", "연어", "참치",
    "오징어", "새우", "멸치", "어묵",
    "꽃게", "조기", "갈치", "낙지",
    "문어", "해물", "굴", "홍합",
]

VEGETARIAN_KEYWORDS = [
    "두부", "콩", "버섯", "채소",
    "나물", "샐러드", "야채",
    "감자", "고구마", "호박",
    "김치", "비빔밥", "채식",
    "시금치", "부추", "가지", "연근",
]

SPICY_KEYWORDS = [
    "김치", "매운", "매콤", "고추",
    "제육", "닭갈비", "떡볶이", "찌개",
]

DESSERT_KEYWORDS = [
    "과일", "사과", "배", "귤", "오렌지",
    "바나나", "포도", "수박", "요거트",
    "푸딩", "케이크", "빵", "떡", "음료",
]


# =========================================================
# 세션 상태 초기화
# =========================================================

if "selected_foods" not in st.session_state:
    st.session_state.selected_foods = []

if "school_results" not in st.session_state:
    st.session_state.school_results = None

if "selected_school" not in st.session_state:
    st.session_state.selected_school = None

if "meal_df" not in st.session_state:
    st.session_state.meal_df = None


# =========================================================
# 유틸리티 함수
# =========================================================

def get_api_key():
    """
    Streamlit Secrets에서 NEIS API 키를 가져옵니다.
    .streamlit/secrets.toml에 NEIS_API_KEY를 저장해야 합니다.
    """
    try:
        return st.secrets["NEIS_API_KEY"]
    except Exception:
        return ""


def has_image(path):
    """이미지 파일이 존재하는지 확인합니다."""
    try:
        with open(path, "rb"):
            return True
    except FileNotFoundError:
        return False


def contains_keyword(text, keywords):
    """문자열에 키워드가 포함되어 있는지 확인합니다."""
    return any(keyword in text for keyword in keywords)


def clean_menu_text(text):
    """NEIS 메뉴 데이터의 HTML 태그를 제거합니다."""
    if not text:
        return ""

    text = str(text)
    text = text.replace("<br/>", "\n")
    text = text.replace("<br>", "\n")
    text = text.replace("<BR/>", "\n")

    return text.strip()


def split_menus(text):
    """급식 메뉴를 개별 메뉴로 분리합니다."""
    if not text:
        return []

    text = clean_menu_text(text)
    menus = []

    for menu in text.split("\n"):
        menu = re.sub(r"\([^)]*\)", "", menu)
        menu = menu.strip()

        if menu:
            menus.append(menu)

    return menus


def analyze_meal(menu_text):
    """한 끼 급식을 분석합니다."""
    menus = split_menus(menu_text)
    joined_text = " ".join(menus)

    meat_count = sum(
        contains_keyword(menu, MEAT_KEYWORDS)
        for menu in menus
    )

    seafood_count = sum(
        contains_keyword(menu, SEAFOOD_KEYWORDS)
        for menu in menus
    )

    vegetarian_count = sum(
        contains_keyword(menu, VEGETARIAN_KEYWORDS)
        for menu in menus
    )

    is_spicy = contains_keyword(joined_text, SPICY_KEYWORDS)
    has_dessert = contains_keyword(joined_text, DESSERT_KEYWORDS)

    if meat_count >= vegetarian_count + 2:
        category = "육류 중심"
    elif vegetarian_count >= meat_count + 2:
        category = "채식 친화"
    else:
        category = "균형형"

    return {
        "category": category,
        "meat_count": meat_count,
        "seafood_count": seafood_count,
        "vegetarian_count": vegetarian_count,
        "is_spicy": is_spicy,
        "has_dessert": has_dessert,
    }


def calculate_preference():
    """선택한 음식으로 사용자의 취향 점수를 계산합니다."""
    scores = {
        "육류": 0,
        "채식": 0,
        "해산물": 0,
        "면류": 0,
        "후식": 0,
    }

    for food in FOOD_DATA:
        if food["name"] in st.session_state.selected_foods:
            scores[food["category"]] += 1

    return scores


def get_main_preference(scores):
    """가장 높은 선호 카테고리를 반환합니다."""
    if sum(scores.values()) == 0:
        return "아직 선택한 음식이 없습니다."

    max_score = max(scores.values())
    main_categories = [
        category
        for category, score in scores.items()
        if score == max_score
    ]

    if len(main_categories) >= 2:
        return "다양한 음식을 선호하는 편입니다."

    return f"{main_categories[0]} 메뉴를 가장 선호합니다."


# =========================================================
# NEIS 학교 검색 API
# =========================================================

@st.cache_data(ttl=600)
def search_schools(api_key, school_name, office_code=""):
    """
    NEIS 학교기본정보 API를 이용해 학교를 검색합니다.
    """
    url = "https://open.neis.go.kr/hub/schoolInfo"

    params = {
        "KEY": api_key,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "SCHUL_NM": school_name,
    }

    if office_code:
        params["ATPT_OFCDC_SC_CODE"] = office_code

    response = requests.get(
        url,
        params=params,
        timeout=15,
    )

    response.raise_for_status()
    data = response.json()

    if "schoolInfo" not in data:
        result = data.get("RESULT", {})
        message = result.get(
            "MESSAGE",
            "검색된 학교가 없습니다.",
        )
        raise ValueError(message)

    school_info = data["schoolInfo"]

    if len(school_info) < 2:
        raise ValueError("검색된 학교가 없습니다.")

    rows = school_info[1].get("row", [])

    if not rows:
        raise ValueError("검색된 학교가 없습니다.")

    result = pd.DataFrame(rows)

    needed_columns = [
        "SCHUL_NM",
        "ATPT_OFCDC_SC_CODE",
        "ATPT_OFCDC_SC_NM",
        "SD_SCHUL_CODE",
        "ORG_RDNMA",
        "SCHUL_KND_SC_NM",
    ]

    for column in needed_columns:
        if column not in result.columns:
            result[column] = ""

    result = result[needed_columns].copy()

    result = result.rename(
        columns={
            "SCHUL_NM": "학교명",
            "ATPT_OFCDC_SC_CODE": "교육청코드",
            "ATPT_OFCDC_SC_NM": "교육청명",
            "SD_SCHUL_CODE": "학교코드",
            "ORG_RDNMA": "주소",
            "SCHUL_KND_SC_NM": "학교종류",
        }
    )

    return result


# =========================================================
# NEIS 급식 API
# =========================================================

@st.cache_data(ttl=600)
def fetch_meals(
    api_key,
    office_code,
    school_code,
    start_date,
    end_date,
):
    """
    NEIS 급식 API에서 급식 데이터를 가져옵니다.
    """
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"

    params = {
        "KEY": api_key,
        "Type": "json",
        "pIndex": 1,
        "pSize": 1000,
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MLSV_FROM_YMD": start_date,
        "MLSV_TO_YMD": end_date,
    }

    response = requests.get(
        url,
        params=params,
        timeout=15,
    )

    response.raise_for_status()
    data = response.json()

    if "mealServiceDietInfo" not in data:
        result = data.get("RESULT", {})
        message = result.get(
            "MESSAGE",
            "급식 데이터를 찾을 수 없습니다.",
        )
        raise ValueError(message)

    meal_info = data["mealServiceDietInfo"]

    if len(meal_info) < 2:
        raise ValueError("조회된 급식 데이터가 없습니다.")

    rows = meal_info[1].get("row", [])

    if not rows:
        raise ValueError("해당 기간에 급식 데이터가 없습니다.")

    df = pd.DataFrame(rows)

    for column in [
        "SCHUL_NM",
        "MMEAL_SC_NM",
        "MLSV_YMD",
        "DDISH_NM",
        "CAL_INFO",
    ]:
        if column not in df.columns:
            df[column] = ""

    df["메뉴"] = df["DDISH_NM"].apply(clean_menu_text)
    df["분석"] = df["DDISH_NM"].apply(analyze_meal)

    df["분류"] = df["분석"].apply(
        lambda value: value["category"]
    )

    df["육류수"] = df["분석"].apply(
        lambda value: value["meat_count"]
    )

    df["해산물수"] = df["분석"].apply(
        lambda value: value["seafood_count"]
    )

    df["채식수"] = df["분석"].apply(
        lambda value: value["vegetarian_count"]
    )

    df["매운메뉴"] = df["분석"].apply(
        lambda value: value["is_spicy"]
    )

    df["후식포함"] = df["분석"].apply(
        lambda value: value["has_dessert"]
    )

    df["칼로리"] = (
        df["CAL_INFO"]
        .astype(str)
        .str.extract(r"([\d.]+)", expand=False)
    )

    df["칼로리"] = pd.to_numeric(
        df["칼로리"],
        errors="coerce",
    )

    df["날짜"] = pd.to_datetime(
        df["MLSV_YMD"].astype(str),
        format="%Y%m%d",
        errors="coerce",
    )

    return df


# =========================================================
# 급식 통계 함수
# =========================================================

def get_meal_summary(df):
    """학교 급식의 전체 통계를 계산합니다."""
    total = len(df)

    if total == 0:
        return {}

    category_counts = df["분류"].value_counts()

    meat_ratio = (
        category_counts.get("육류 중심", 0)
        / total
        * 100
    )

    vegetarian_ratio = (
        category_counts.get("채식 친화", 0)
        / total
        * 100
    )

    balanced_ratio = (
        category_counts.get("균형형", 0)
        / total
        * 100
    )

    seafood_ratio = (
        (df["해산물수"] > 0).sum()
        / total
        * 100
    )

    spicy_ratio = (
        df["매운메뉴"].sum()
        / total
        * 100
    )

    dessert_ratio = (
        df["후식포함"].sum()
        / total
        * 100
    )

    average_calorie = df["칼로리"].mean()

    return {
        "전체식단수": total,
        "육류비율": meat_ratio,
        "채식비율": vegetarian_ratio,
        "균형형비율": balanced_ratio,
        "해산물비율": seafood_ratio,
        "매운메뉴비율": spicy_ratio,
        "후식비율": dessert_ratio,
        "평균칼로리": average_calorie,
    }


def calculate_match_score(preference_scores, summary):
    """
    사용자 취향과 학교 급식 통계를 비교합니다.
    100점에 가까울수록 취향에 잘 맞는다는 뜻입니다.
    """
    total_preference = sum(preference_scores.values())

    if total_preference == 0:
        return 0

    user_meat = (
        preference_scores["육류"]
        / total_preference
        * 100
    )

    user_vegetarian = (
        preference_scores["채식"]
        / total_preference
        * 100
    )

    user_seafood = (
        preference_scores["해산물"]
        / total_preference
        * 100
    )

    school_meat = summary["육류비율"]
    school_vegetarian = summary["채식비율"]
    school_seafood = summary["해산물비율"]

    meat_score = 0

    if user_meat > 0:
        meat_score = min(
            30,
            abs(user_meat - school_meat) / 100 * 30,
        )

    vegetarian_score = 0

    if user_vegetarian > 0:
        vegetarian_score = min(
            25,
            abs(user_vegetarian - school_vegetarian)
            / 100
            * 25,
        )

    seafood_score = 0

    if user_seafood > 0:
        seafood_score = min(
            20,
            abs(user_seafood - school_seafood)
            / 100
            * 20,
        )

    # 차이가 작을수록 높은 점수를 주기 위한 계산
    meat_match = 30 - meat_score
    vegetarian_match = 25 - vegetarian_score
    seafood_match = 20 - seafood_score

    balanced_bonus = summary["균형형비율"] * 0.15

    score = (
        meat_match
        + vegetarian_match
        + seafood_match
        + balanced_bonus
    )

    return round(max(0, min(100, score)), 1)


# =========================================================
# 사이드바: API 키와 조회 설정
# =========================================================

api_key = get_api_key()

st.sidebar.title("⚙️ 조회 설정")

if not api_key:
    st.sidebar.error(
        "NEIS_API_KEY가 설정되지 않았습니다."
    )
    st.sidebar.code(
        ".streamlit/secrets.toml\n\n"
        'NEIS_API_KEY = "인증키"',
        language="toml",
    )

st.sidebar.markdown("### 급식 조회 기간")

today = date.today()

start_date = st.sidebar.date_input(
    "시작일",
    value=today.replace(day=1),
)

end_date = st.sidebar.date_input(
    "종료일",
    value=today + timedelta(days=30),
)


# =========================================================
# 제목
# =========================================================

st.title("🍱 맞춤형 학교 급식 추천 서비스")

st.write(
    "좋아하는 음식 사진을 선택하면 급식 취향을 분석하고, "
    "NEIS 급식 데이터를 바탕으로 학교 급식과의 적합도를 계산합니다."
)

st.info(
    "급식 평가는 메뉴명과 공개된 영양 정보를 기반으로 한 "
    "참고용 분석입니다. 실제 재료와 조리 방법은 학교의 "
    "공식 안내를 확인하세요."
)


# =========================================================
# 1단계: 음식 사진 선택
# =========================================================

st.header("1️⃣ 좋아하는 음식 선택")

st.write(
    "좋아하는 음식에 체크하세요. 선택 결과는 급식 취향 분석에 사용됩니다."
)

food_columns = st.columns(4)

for index, food in enumerate(FOOD_DATA):
    with food_columns[index % 4]:
        if has_image(food["image"]):
            st.image(
                food["image"],
                use_container_width=True,
            )
        else:
            st.markdown(
                f"<div style='font-size:80px; text-align:center;'>"
                f"{food['emoji']}</div>",
                unsafe_allow_html=True,
            )

        selected = st.checkbox(
            f"{food['name']} ({food['category']})",
            value=food["name"] in st.session_state.selected_foods,
            key=f"food_{food['name']}",
        )

        if selected and food["name"] not in st.session_state.selected_foods:
            st.session_state.selected_foods.append(food["name"])

        if (
            not selected
            and food["name"] in st.session_state.selected_foods
        ):
            st.session_state.selected_foods.remove(food["name"])


preference_scores = calculate_preference()
main_preference = get_main_preference(preference_scores)

st.divider()

preference_col1, preference_col2 = st.columns([1, 2])

with preference_col1:
    st.subheader("나의 주요 취향")
    st.success(main_preference)

with preference_col2:
    score_df = pd.DataFrame(
        {
            "음식 유형": list(preference_scores.keys()),
            "선택 수": list(preference_scores.values()),
        }
    )

    fig = px.bar(
        score_df,
        x="음식 유형",
        y="선택 수",
        title="음식 유형별 선호도",
        text_auto=True,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# =========================================================
# 2단계: 학교 검색
# =========================================================

st.header("2️⃣ 학교 검색")

st.write(
    "학교 이름을 입력하면 NEIS 학교기본정보 API에서 학교를 검색합니다."
)

search_col1, search_col2, search_col3 = st.columns(
    [2, 1, 1]
)

with search_col1:
    school_name_input = st.text_input(
        "학교 이름",
        placeholder="예: 당곡고등학교",
    )

with search_col2:
    office_code_input = st.text_input(
        "교육청 코드 선택사항",
        value="B10",
        help="서울교육청은 B10입니다. 전국 검색은 비워두세요.",
    )

with search_col3:
    st.write("")
    st.write("")
    search_button = st.button(
        "학교 검색",
        type="primary",
        use_container_width=True,
    )


if search_button:
    if not api_key:
        st.error(
            "NEIS_API_KEY가 설정되지 않았습니다."
        )

    elif not school_name_input.strip():
        st.warning("학교 이름을 입력하세요.")

    else:
        try:
            with st.spinner("학교를 검색하는 중입니다..."):
                st.session_state.school_results = search_schools(
                    api_key=api_key,
                    school_name=school_name_input.strip(),
                    office_code=office_code_input.strip(),
                )

            st.success(
                f"{len(st.session_state.school_results)}개의 "
                "학교를 찾았습니다."
            )

        except requests.exceptions.RequestException as error:
            st.error(f"학교 검색 요청 오류: {error}")

        except ValueError as error:
            st.warning(str(error))

        except Exception as error:
            st.error(f"학교 검색 오류: {error}")


# =========================================================
# 3단계: 학교 선택
# =========================================================

if (
    st.session_state.school_results is not None
    and not st.session_state.school_results.empty
):
    st.subheader("검색 결과에서 학교를 선택하세요")

    school_results = st.session_state.school_results

    school_options = []

    for _, row in school_results.iterrows():
        option = (
            f"{row['학교명']} | "
            f"{row['교육청명']} | "
            f"{row['주소']}"
        )
        school_options.append(option)

    selected_index = st.selectbox(
        "검색된 학교",
        options=range(len(school_options)),
        format_func=lambda index: school_options[index],
    )

    selected_school = school_results.iloc[selected_index]

    st.session_state.selected_school = selected_school

    school_info_col1, school_info_col2, school_info_col3 = st.columns(3)

    with school_info_col1:
        st.metric(
            "학교명",
            selected_school["학교명"],
        )

    with school_info_col2:
        st.metric(
            "교육청 코드",
            selected_school["교육청코드"],
        )

    with school_info_col3:
        st.metric(
            "학교 코드",
            selected_school["학교코드"],
        )

    st.caption(
        f"주소: {selected_school['주소']}"
    )


# =========================================================
# 4단계: 급식 조회
# =========================================================

st.header("3️⃣ 급식 조회 및 분석")

meal_button = st.button(
    "선택한 학교 급식 조회",
    type="primary",
    use_container_width=True,
)

if meal_button:
    if not api_key:
        st.error(
            "NEIS_API_KEY가 설정되지 않았습니다."
        )

    elif st.session_state.selected_school is None:
        st.warning(
            "먼저 학교를 검색하고 학교를 선택하세요."
        )

    elif start_date > end_date:
        st.warning(
            "시작일은 종료일보다 빠르거나 같아야 합니다."
        )

    else:
        selected_school = st.session_state.selected_school

        try:
            with st.spinner("급식 데이터를 가져오는 중입니다..."):
                st.session_state.meal_df = fetch_meals(
                    api_key=api_key,
                    office_code=selected_school["교육청코드"],
                    school_code=selected_school["학교코드"],
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                )

            st.success("급식 데이터를 불러왔습니다.")

        except requests.exceptions.RequestException as error:
            st.error(f"급식 API 요청 오류: {error}")

        except ValueError as error:
            st.warning(str(error))

        except Exception as error:
            st.error(f"급식 조회 오류: {error}")


# =========================================================
# 5단계: 결과 표시
# =========================================================

df = st.session_state.meal_df

if df is not None and not df.empty:
    selected_school = st.session_state.selected_school
    summary = get_meal_summary(df)

    st.divider()

    st.header(
        f"📊 {selected_school['학교명']} 급식 분석 결과"
    )

    result_col1, result_col2, result_col3, result_col4 = st.columns(4)

    with result_col1:
        st.metric(
            "분석한 식단",
            f"{summary['전체식단수']}개",
        )

    with result_col2:
        st.metric(
            "육류 중심",
            f"{summary['육류비율']:.1f}%",
        )

    with result_col3:
        st.metric(
            "채식 친화",
            f"{summary['채식비율']:.1f}%",
        )

    with result_col4:
        if pd.isna(summary["평균칼로리"]):
            calorie_text = "정보 없음"
        else:
            calorie_text = f"{summary['평균칼로리']:.0f}kcal"

        st.metric(
            "평균 칼로리",
            calorie_text,
        )

    tab1, tab2, tab3 = st.tabs(
        [
            "🍚 급식 목록",
            "📈 학교 급식 특징",
            "🎯 취향 적합도",
        ]
    )

    # -----------------------------------------------------
    # 급식 목록
    # -----------------------------------------------------

    with tab1:
        display_df = df[
            [
                "날짜",
                "MMEAL_SC_NM",
                "메뉴",
                "분류",
                "CAL_INFO",
            ]
        ].copy()

        display_df.columns = [
            "날짜",
            "식사",
            "메뉴",
            "분류",
            "칼로리",
        ]

        display_df["날짜"] = display_df["날짜"].dt.strftime(
            "%Y-%m-%d"
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )

    # -----------------------------------------------------
    # 학교 급식 특징
    # -----------------------------------------------------

    with tab2:
        st.subheader("급식 유형 비율")

        category_df = pd.DataFrame(
            {
                "유형": [
                    "육류 중심",
                    "채식 친화",
                    "균형형",
                ],
                "비율": [
                    summary["육류비율"],
                    summary["채식비율"],
                    summary["균형형비율"],
                ],
            }
        )

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            fig = px.pie(
                category_df,
                names="유형",
                values="비율",
                title="급식 유형 비율",
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

        with chart_col2:
            feature_df = pd.DataFrame(
                {
                    "특징": [
                        "해산물 포함",
                        "매운 메뉴",
                        "후식 포함",
                    ],
                    "비율": [
                        summary["해산물비율"],
                        summary["매운메뉴비율"],
                        summary["후식비율"],
                    ],
                }
            )

            fig = px.bar(
                feature_df,
                x="특징",
                y="비율",
                title="급식 세부 특징",
                text_auto=".1f",
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

        st.subheader("학교 급식 평가")

        if summary["육류비율"] >= 50:
            st.write(
                "🥩 육류 메뉴가 비교적 자주 제공되는 "
                "육류 중심 식단입니다."
            )
        elif summary["채식비율"] >= 30:
            st.write(
                "🥗 채소와 식물성 재료가 비교적 자주 "
                "포함되는 채식 친화 식단입니다."
            )
        else:
            st.write(
                "⚖️ 육류와 채소 메뉴가 비교적 균형 있게 "
                "제공되는 식단입니다."
            )

        st.write(
            f"- 해산물 포함 식단: "
            f"{summary['해산물비율']:.1f}%"
        )

        st.write(
            f"- 매운 메뉴 포함 식단: "
            f"{summary['매운메뉴비율']:.1f}%"
        )

        st.write(
            f"- 후식 포함 식단: "
            f"{summary['후식비율']:.1f}%"
        )

    # -----------------------------------------------------
    # 취향 적합도
    # -----------------------------------------------------

    with tab3:
        st.subheader("나의 음식 취향과 학교 급식 비교")

        match_score = calculate_match_score(
            preference_scores=preference_scores,
            summary=summary,
        )

        st.metric(
            "취향 적합도",
            f"{match_score}점 / 100점",
        )

        if match_score >= 80:
            st.success(
                "선택한 음식 취향과 매우 잘 맞는 학교입니다."
            )
        elif match_score >= 60:
            st.info(
                "선택한 음식 취향과 어느 정도 잘 맞는 학교입니다."
            )
        else:
            st.warning(
                "선택한 음식 취향과 차이가 있을 수 있습니다."
            )

        st.subheader("추천 이유")

        if preference_scores["육류"] > 0:
            st.write(
                f"- 좋아하는 육류 음식 "
                f"{preference_scores['육류']}개를 선택했습니다."
            )

        if preference_scores["채식"] > 0:
            st.write(
                f"- 좋아하는 채식 음식 "
                f"{preference_scores['채식']}개를 선택했습니다."
            )

        if preference_scores["해산물"] > 0:
            st.write(
                f"- 좋아하는 해산물 음식 "
                f"{preference_scores['해산물']}개를 선택했습니다."
            )

        st.write(
            f"- 이 학교의 육류 중심 식단 비율은 "
            f"{summary['육류비율']:.1f}%입니다."
        )

        st.write(
            f"- 이 학교의 채식 친화 식단 비율은 "
            f"{summary['채식비율']:.1f}%입니다."
        )

        st.write(
            f"- 이 학교의 해산물 포함 식단 비율은 "
            f"{summary['해산물비율']:.1f}%입니다."
        )

        st.caption(
            "취향 적합도는 사용자가 선택한 음식 카테고리와 "
            "학교 급식 통계의 유사도를 계산한 참고 점수입니다."
        )


# =========================================================
# 하단 안내
# =========================================================

st.divider()

st.caption(
    "주의: 이 서비스는 메뉴명과 공개된 영양 정보를 이용한 "
    "참고용 분석입니다. 실제 재료, 알레르기 정보, 조리 방법은 "
    "학교의 공식 급식 안내를 확인하세요."
)
