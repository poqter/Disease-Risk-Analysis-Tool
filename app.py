import streamlit as st
import pandas as pd

# --- 페이지 설정 ---
st.set_page_config(page_title="질병 위험률 분석 도구", layout="wide")

# --- 사이드바 정보 ---
st.sidebar.markdown("""
👨‍💻 제작자: 드림지점 박병선 팀장  
🗓️ 버전: v1.0.0  
📅 최종 업데이트: 2025-07-06
""")

# --- 데이터 불러오기 ---
df_risk = pd.read_csv("disease_risk.csv")
df_adjust = pd.read_csv("disease_adjust.csv")
df_treat = pd.read_csv("disease_treatment.csv")
df_coverage = pd.read_csv("disease_coverage.csv")

# --- 메인 타이틀 ---
st.title("🧬 질병 위험률 분석 도구")
st.markdown("""
#### 고객님의 연령대, 성별, 건강상태를 바탕으로 위험률을 분석합니다.
""")

# --- 입력 카드 UI ---
with st.container():
    st.subheader("📥 상담 정보 입력")
    col1, col2 = st.columns(2)
    with col1:
        age_group = st.selectbox("연령대", options=sorted(df_risk["연령대"].unique()), key="age")
        gender = st.selectbox("성별", options=sorted(df_risk["성별"].unique()), key="gender")
        smoke = st.selectbox("흡연 여부", options=sorted(df_risk["흡연여부"].unique()), key="smoke")
        drink = st.selectbox("음주 여부", options=sorted(df_risk["음주여부"].unique()), key="drink")
    with col2:
        family = st.selectbox("가족력", options=sorted(df_risk["가족력"].unique()), key="family")
        disease_options = df_risk["기저질환"].str.split("+").explode().unique()
        conditions = st.multiselect("보유 질병", options=sorted(disease_options), key="conditions")
        job = st.selectbox("직업", options=["사무직", "육체노동직", "학생", "자영업", "무직"], key="job")
        exercise = st.selectbox("운동 습관", options=["규칙적으로 운동함", "가끔 운동함", "거의 안 함"], key="exercise")

    if st.button("🔄 입력값 초기화"):
        st.session_state.clear()
        st.experimental_rerun()

    run_analysis = st.button("📊 결과 확인하기")

# --- 결과 분석 ---
if run_analysis:
    filtered = df_risk[
        (df_risk["연령대"] == age_group) &
        (df_risk["성별"] == gender) &
        (df_risk["흡연여부"] == smoke) &
        (df_risk["음주여부"] == drink) &
        (df_risk["가족력"] == family)
    ]

    if conditions:
        filtered = filtered[
            filtered["기저질환"].apply(lambda x: any(cond in x for cond in conditions))
        ]
    else:
        filtered = filtered[filtered["기저질환"] == "없음"]

    if not filtered.empty:
        st.subheader("📊 분석 결과")

        category_map = {
            "암": lambda x: "암" in x,
            "뇌": lambda x: any(keyword in x for keyword in ["뇌", "뇌졸중", "뇌출혈"]),
            "심장": lambda x: any(keyword in x for keyword in ["심장", "심근경색", "허혈성"])
        }

        output_blocks = []

        for cat, condition in category_map.items():
            cat_df = filtered[filtered["질병"].apply(condition)]
            if not cat_df.empty:
                top_disease = cat_df.sort_values(by="위험률(1000명당)", ascending=False).iloc[0]
                disease = top_disease["질병"]
                base_risk = top_disease["위험률(1000명당)"]

                adjust_factors = []
                for kind, value in zip(
                    ["기저질환"] * len(conditions) + ["흡연여부", "음주여부", "가족력", "직업", "운동 습관"],
                    conditions + [smoke, drink, family, job, exercise]
                ):
                    row = df_adjust[(df_adjust["항목종류"] == kind) & (df_adjust["항목명"] == value)]
                    if not row.empty:
                        adjust_factors.append(row["조정계수"].values[0])

                # 기저질환 많을수록 가중치 약화
                if conditions:
                    adjusted_weights = [1.0 - 0.1 * (len(conditions)-1)] * len(conditions)
                else:
                    adjusted_weights = []
                remaining_weights = [1.0] * (len(adjust_factors) - len(adjusted_weights))
                weights = adjusted_weights + remaining_weights

                weighted_sum = sum(a * w for a, w in zip(adjust_factors, weights))
                final_adjust = round(weighted_sum / sum(weights), 2) if weights else 1.0
                final_risk = round(base_risk * final_adjust, 1)

                treat_info = df_treat[df_treat["질병"] == disease]
                coverage_info = df_coverage[df_coverage["질병"] == disease]

                d_rate = coverage_info['진단비보유율(%)'].values[0] if not coverage_info.empty else '-'
                t_rate = coverage_info['치료비보유율(%)'].values[0] if not coverage_info.empty else '-'

                if final_risk >= 10:
                    ment = "이 질병은 통계적으로도 매우 높은 빈도로 발생하고 있습니다. 지금 바로 준비가 필요합니다."
                elif final_risk >= 3:
                    ment = "생각보다 발생 빈도가 높은 질병입니다. 지금 준비하면 가장 효과적입니다."
                elif final_risk > 1:
                    ment = "현재는 낮은 편이지만, 조기 대비는 항상 후회 없는 선택입니다."
                else:
                    ment = "위험률은 낮지만, 기본 보장으로 준비하는 경우가 많습니다."

                result_block = f"""
🔹 **{cat} 위험 - {disease}**
- 기본 위험률: 1000명 중 **{base_risk}명**
- 보정 위험률 (개인조건 반영): **{final_risk}명** (보정 계수 평균: {final_adjust})
- 진단비 보유율: {d_rate}% / 치료비 보유율: {t_rate}%
- 🧾 설득 멘트: {ment}
                """
                output_blocks.append(result_block)

        for block in output_blocks:
            st.markdown(block)
            st.markdown("---")

    else:
        st.warning("❗ 입력하신 조건에 해당하는 데이터가 없습니다. 다른 조건을 시도해주세요.")
