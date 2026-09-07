import os
import re
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


# ==================================================
# 페이지 설정
# ==================================================

st.set_page_config(
    page_title="학교 급식 비교 서비스",
    page_icon="🍱",
    layout="wide",
)


# ==================================================
# 음식 데이터
# ==================================================

FOODS = [
    {
        "name": "제육볶음",
        "category": "육류",
        "emoji": "🥩",
        "image": "images/jeyuk.jpg",
    },
    {
        "name": "닭갈비",
        "category": "육류",
        "emoji": "🍗",
        "image": "images/dakgalbi.jpg",
    },
    {
        "name": "돈가스",
        "category": "육류",
        "emoji": "🍖",
        "image": "images/pork_cutlet.jpg",
    },
    {
        "name": "샐러드",
        "category": "채식",
        "emoji": "🥗",
        "image": "images/salad.jpg",
    },
    {
        "name": "비빔밥",
        "category": "채식",
        "emoji": "🍚",
        "image": "images/bibimbap.jpg",
    },
    {
        "name": "생선구이",
        "category": "해산물",
        "emoji": "🐟",
        "image": "images/fish.jpg",
    },
    {
        "name": "잔치국수",
        "category": "면류",
        "emoji": "🍜",
        "image": "images/noodles.jpg",
    },
    {
        "name": "과일",
        "category": "후식",
        "emoji": "🍎",
        "image": "images/fruit.jpg",
    },
]


# ==================================================
# 키워드
# ==================================================

MEAT_KEYWORDS = [
    "돼지", "돈육", "제육", "삼겹", "목살",
    "소고기", "쇠고기", "불고기", "갈비",
    "닭", "치킨", "닭갈비", "오리",
    "햄", "소시지", "베이컨", "고기",
    "돈가스", "돈까스", "스테이크",
]

SEAFOOD_KEYWORDS = [
    "생선", "고등어", "연어", "참치",
    "오징어", "새우", "멸치", "어묵",
    "꽃게", "조기", "갈치", "낙지",
    "문어", "해물", "굴", "홍합",
]

VEGETARIAN_KEYWORDS = [
    "두부", "콩", "버섯", "채소", "나물",
    "샐러드", "야채", "감자", "고구마",
    "호박", "김치", "비빔밥", "시금치",
    "부추", "가지", "연근",
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


# ==================================================
# 세션 상태
# ==================================================

if "selected_foods" not in st.session_state:
    st.session_state.selected_foods = []

if "school_results" not in st.session_state:
    st.session_state.school_results = None

if "comparison_results" not in st.session_state:
    st.session_state.comparison_results = None


# ==================================================
# 기본 함수
# ==================================================

def get_api_key():
    """Streamlit Secrets에서 NEIS API 키를 가져옵니다."""
    try:
        return st.secrets["NEIS_API_KEY"]
    except Exception:
        return ""


def image_exists(path):
    """이미지 파일이 존재하는지 확인합니다."""
    return os.path.exists(path)


def contains_keyword(text, keywords):
    return any(keyword in text for keyword in keywords)


def clean_menu_text(text):
    """급식 문자열의 HTML 태그를 정리합니다."""
    if not text:
        return ""

    text = str(text)
    text = text.replace("<br/>", "\n")
    text = text.replace("<br>", "\n")
    text = text.replace("<BR/>", "\n")

    return text.strip()


def split_menus(text):
    """급식 문자열을 개별 메뉴로 나눕니다."""
    text = clean_menu_text(text)
    menus = []

    for menu in text.split("\n"):
        menu = re.sub(r"\([^)]*\)", "", menu).strip()

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


def calculate_user_preferences():
    """사용자가 선택한 음식으로 취향 점수를 계산합니다."""
    scores = {
        "육류": 0,
        "채식": 0,
        "해산물": 0,
        "면류": 0,
        "후식": 0,
    }

    for food in FOODS:
        if food["name"] in st.session_state.selected_foods:
            scores[food["category"]] += 1

    return scores


def calculate_match_score(preferences, summary):
    """사용자 취향과 학교 급식 특징을 비교합니다."""
    total = sum(preferences.values())

    if total == 0:
        return 0

    user_meat = preferences["육류"] / total * 100
    user_vegetarian = preferences["채식"] / total * 100
    user_seafood = preferences["해산물"] / total * 100

    school_meat = summary["육류 중심 비율"]
    school_vegetarian = summary["채식 친화 비율"]
    school_seafood = summary["해산물 포함 비율"]

    meat_match = max(0, 30 - abs(user_meat - school_meat) * 0.3)
    vegetarian_match = max(
        0,
        25 - abs(user_vegetarian - school_vegetarian) * 0.25,
    )
    seafood_match = max(
        0,
        20 - abs(user_seafood - school_seafood) * 0.2,
    )

    balanced_bonus = summary["균형형 비율"] * 0.25

    score = (
        meat_match
        + vegetarian_match
        + seafood_match
        + balanced_bonus
    )

    return round(min(score, 100), 1)


# ==================================================
# 학교 검색 API
# ==================================================

@st.cache_data(ttl=600)
def search_schools(api_key, school_name, office_code=""):
    """NEIS 학교기본정보 API로 학교를 검색합니다."""
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
        raise ValueError(
            result.get("MESSAGE", "학교를 찾을 수 없습니다.")
        )

    school_info = data["schoolInfo"]

    if len(school_info) < 2:
        raise ValueError("학교 검색 결과가 없습니다.")

    rows = school_info[1].get("row", [])

    if not rows:
        raise ValueError("학교 검색 결과가 없습니다.")

    result = pd.DataFrame(rows)

    columns = [
        "SCHUL_NM",
        "ATPT_OFCDC_SC_CODE",
        "ATPT_OFCDC_SC_NM",
        "SD_SCHUL_CODE",
        "ORG_RDNMA",
        "SCHUL_KND_SC_NM",
    ]

    for column in columns:
        if column not in result.columns:
            result[column] = ""

    result = result[columns]

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


# ==================================================
# 급식 조회 API
# ==================================================

@st.cache_data(ttl=600)
def fetch_meals(
    api_key,
    office_code,
    school_code,
    start_date,
    end_date,
):
    """NEIS 급식 API로 급식 데이터를 가져옵니다."""
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
        raise ValueError(
            result.get(
                "MESSAGE",
                "급식 데이터를 찾을 수 없습니다.",
            )
        )

    meal_info = data["mealServiceDietInfo"]

    if len(meal_info) < 2:
        raise ValueError("급식 데이터가 없습니다.")

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
        lambda x: x["category"]
    )

    df["육류수"] = df["분석"].apply(
        lambda x: x["meat_count"]
    )

    df["해산물수"] = df["분석"].apply(
        lambda x: x["seafood_count"]
    )

    df["채식수"] = df["분석"].apply(
        lambda x: x["vegetarian_count"]
    )

    df["매운메뉴"] = df["분석"].apply(
        lambda x: x["is_spicy"]
    )

    df["후식포함"] = df["분석"].apply(
        lambda x: x["has_dessert"]
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


def summarize_meals(df):
    """한 학교의 급식 통계를 계산합니다."""
    total = len(df)

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
        "식단 수": total,
        "육류 중심 비율": round(meat_ratio, 1),
        "채식 친화 비율": round(vegetarian_ratio, 1),
        "균형형 비율": round(balanced_ratio, 1),
        "해산물 포함 비율": round(seafood_ratio, 1),
        "매운 메뉴 비율": round(spicy_ratio, 1),
        "후식 포함 비율": round(dessert_ratio, 1),
        "평균 칼로리": (
            round(average_calorie, 1)
            if not pd.isna(average_calorie)
            else 0
        ),
    }


# ==================================================
# 기본 정보 및 사이드바
# ==================================================

api_key = get_api_key()

st.sidebar.title("🍱 급식 비교 설정")

if not api_key:
    st.sidebar.error("NEIS_API_KEY가 없습니다.")
    st.sidebar.code(
        '[secrets.toml]\n\n'
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


# ==================================================
# 제목
# ==================================================

st.title("🍱 여러 학교 급식 비교 서비스")

st.write(
    "좋아하는 음식으로 취향을 분석한 뒤, "
    "여러 학교의 급식을 비교해 보세요."
)

st.info(
    "급식 평가는 메뉴명에 포함된 키워드를 바탕으로 계산한 "
    "참고용 분석입니다."
)


# ==================================================
# 1단계: 음식 선택
# ==================================================

st.header("1️⃣ 좋아하는 음식 선택")

st.write(
    "좋아하는 음식에 체크하세요. 선택한 결과는 학교 추천 점수에 사용됩니다."
)

food_columns = st.columns(4)

for index, food in enumerate(FOODS):
    with food_columns[index % 4]:
        if image_exists(food["image"]):
            st.image(
                food["image"],
                use_container_width=True,
            )
        else:
            st.markdown(
                f"<div style='font-size:70px; "
                f"text-align:center'>{food['emoji']}</div>",
                unsafe_allow_html=True,
            )

        checked = st.checkbox(
            f"{food['name']} ({food['category']})",
            value=food["name"]
            in st.session_state.selected_foods,
            key=f"food_{food['name']}",
        )

        if (
            checked
            and food["name"]
            not in st.session_state.selected_foods
        ):
            st.session_state.selected_foods.append(food["name"])

        if (
            not checked
            and food["name"]
            in st.session_state.selected_foods
        ):
            st.session_state.selected_foods.remove(food["name"])


preferences = calculate_user_preferences()

st.subheader("나의 취향")

preference_df = pd.DataFrame(
    {
        "음식 유형": list(preferences.keys()),
        "선택 수": list(preferences.values()),
    }
)

fig = px.bar(
    preference_df,
    x="음식 유형",
    y="선택 수",
    text_auto=True,
    title="음식 유형별 선호도",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ==================================================
# 2단계: 학교 검색
# ==================================================

st.header("2️⃣ 비교할 학교 검색")

search_col1, search_col2, search_col3 = st.columns(
    [2, 1, 1]
)

with search_col1:
    school_search_name = st.text_input(
        "학교 이름",
        placeholder="예: 고등학교, 당곡고등학교",
    )

with search_col2:
    office_code = st.text_input(
        "교육청 코드 선택사항",
        value="B10",
        help="서울교육청은 B10입니다.",
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
        st.error("NEIS_API_KEY가 설정되지 않았습니다.")

    elif not school_search_name.strip():
        st.warning("학교 이름을 입력하세요.")

    else:
        try:
            with st.spinner("학교를 검색하는 중입니다..."):
                st.session_state.school_results = search_schools(
                    api_key,
                    school_search_name.strip(),
                    office_code.strip(),
                )

            st.success(
                f"{len(st.session_state.school_results)}개 학교를 찾았습니다."
            )

        except Exception as error:
            st.error(f"학교 검색 오류: {error}")


# ==================================================
# 3단계: 여러 학교 선택
# ==================================================

school_results = st.session_state.school_results

if school_results is not None:
    st.header("3️⃣ 비교할 학교 선택")

    st.write(
        "최대 5개 학교까지 선택할 수 있습니다."
    )

    school_options = []

    for index, row in school_results.iterrows():
        label = (
            f"{index} | "
            f"{row['학교명']} | "
            f"{row['교육청명']} | "
            f"{row['주소']}"
        )
        school_options.append(label)

    selected_options = st.multiselect(
        "비교할 학교를 선택하세요.",
        options=school_options,
        max_selections=5,
    )

    selected_indexes = []

    for option in selected_options:
        index = int(option.split(" | ")[0])
        selected_indexes.append(index)

    selected_schools = school_results.loc[
        selected_indexes
    ].copy()

    if selected_schools.empty:
        st.info("비교할 학교를 하나 이상 선택하세요.")

    else:
        st.dataframe(
            selected_schools[
                [
                    "학교명",
                    "교육청명",
                    "학교종류",
                    "주소",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        compare_button = st.button(
            "선택한 학교 급식 비교하기",
            type="primary",
            use_container_width=True,
        )

        if compare_button:
            if start_date > end_date:
                st.error(
                    "시작일은 종료일보다 빠르거나 같아야 합니다."
                )
            else:
                comparison_results = []
                meal_data_by_school = {}

                progress = st.progress(0)
                total_schools = len(selected_schools)

                for count, (_, school) in enumerate(
                    selected_schools.iterrows(),
                    start=1,
                ):
                    try:
                        meals = fetch_meals(
                            api_key=api_key,
                            office_code=school["교육청코드"],
                            school_code=school["학교코드"],
                            start_date=start_date.strftime(
                                "%Y%m%d"
                            ),
                            end_date=end_date.strftime(
                                "%Y%m%d"
                            ),
                        )

                        summary = summarize_meals(meals)

                        summary["학교명"] = school["학교명"]
                        summary["주소"] = school["주소"]
                        summary["취향 적합도"] = calculate_match_score(
                            preferences,
                            summary,
                        )

                        comparison_results.append(summary)
                        meal_data_by_school[
                            school["학교명"]
                        ] = meals

                    except Exception as error:
                        st.warning(
                            f"{school['학교명']} 조회 실패: {error}"
                        )

                    progress.progress(
                        count / total_schools
                    )

                st.session_state.comparison_results = (
                    comparison_results
                )

                st.session_state.meal_data_by_school = (
                    meal_data_by_school
                )


# ==================================================
# 4단계: 비교 결과
# ==================================================

results = st.session_state.comparison_results

if results:
    st.header("4️⃣ 학교별 급식 비교 결과")

    result_df = pd.DataFrame(results)

    result_df = result_df.sort_values(
        "취향 적합도",
        ascending=False,
    )

    best_school = result_df.iloc[0]

    st.success(
        f"🎉 현재 선택한 학교 중 가장 잘 맞는 학교는 "
        f"**{best_school['학교명']}**입니다. "
        f"취향 적합도는 **{best_school['취향 적합도']}점**입니다."
    )

    display_columns = [
        "学校名",
        "식단 수",
        "육류 중심 비율",
        "채식 친화 비율",
        "균형형 비율",
        "해산물 포함 비율",
        "평균 칼로리",
        "취향 적합도",
    ]

    # 학교명 컬럼명을 잘못 입력하지 않도록 실제 컬럼을 구성합니다.
    display_columns = [
        "학교명",
        "식단 수",
        "육류 중심 비율",
        "채식 친화 비율",
        "균형형 비율",
        "해산물 포함 비율",
        "평균 칼로리",
        "취향 적합도",
    ]

    st.dataframe(
        result_df[display_columns],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("취향 적합도 순위")

    score_chart = px.bar(
        result_df,
        x="학교명",
        y="취향 적합도",
        color="학교명",
        text_auto=True,
        title="학교별 취향 적합도",
    )

    st.plotly_chart(
        score_chart,
        use_container_width=True,
    )

    st.subheader("급식 유형 비교")

    category_chart = px.bar(
        result_df,
        x="학교명",
        y=[
            "육류 중심 비율",
            "채식 친화 비율",
            "균형형 비율",
        ],
        barmode="group",
        title="학교별 급식 유형 비교",
    )

    st.plotly_chart(
        category_chart,
        use_container_width=True,
    )

    st.subheader("학교별 상세 특징")

    for _, row in result_df.iterrows():
        with st.expander(
            f"{row['학교명']} 상세 보기"
        ):
            detail_col1, detail_col2, detail_col3 = st.columns(3)

            with detail_col1:
                st.metric(
                    "육류 중심",
                    f"{row['육류 중심 비율']}%",
                )
                st.metric(
                    "채식 친화",
                    f"{row['채식 친화 비율']}%",
                )

            with detail_col2:
                st.metric(
                    "해산물 포함",
                    f"{row['해산물 포함 비율']}%",
                )
                st.metric(
                    "매운 메뉴",
                    f"{row['매운 메뉴 비율']}%",
                )

            with detail_col3:
                st.metric(
                    "후식 포함",
                    f"{row['후식 포함 비율']}%",
                )
                st.metric(
                    "평균 칼로리",
                    f"{row['평균 칼로리']}kcal",
                )

            school_name = row["학교명"]
            meal_data = st.session_state.meal_data_by_school.get(
                school_name
            )

            if meal_data is not None:
                detail_df = meal_data[
                    [
                        "날짜",
                        "MMEAL_SC_NM",
                        "메뉴",
                        "분류",
                        "CAL_INFO",
                    ]
                ].copy()

                detail_df.columns = [
                    "날짜",
                    "식사",
                    "메뉴",
                    "분류",
                    "칼로리",
                ]

                detail_df["날짜"] = detail_df[
                    "날짜"
                ].dt.strftime("%Y-%m-%d")

                st.dataframe(
                    detail_df,
                    use_container_width=True,
                    hide_index=True,
                )


# ==================================================
# 안내
# ==================================================

st.divider()

st.caption(
    "이 서비스의 결과는 메뉴명 키워드를 기반으로 한 "
    "참고용 분석입니다. 실제 원재료, 알레르기 정보, "
    "조리 방법은 학교 공식 급식 정보를 확인하세요."
)
