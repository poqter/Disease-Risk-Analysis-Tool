import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- 페이지 설정 ---
st.set_page_config(page_title="질병 위험률 분석 도구", layout="wide")

# --- 사이드바 정보 ---
st.sidebar.markdown("""
👨‍💻 제작자: 드림지점 박병선 팀장  
🗓️ 버전: v1.0.0  
📅 최종 업데이트: 2025-07-06
""")

# --- 데이터 불러오기 (예시로 내부 생성) ---
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

    # 전체 초기화 버튼
    if st.button("🔄 입력값 초기화"):
        st.session_state.clear()
        st.experimental_rerun()

    # 결과 확인 버튼
    run_analysis = st.button("📊 결과 확인하기")

# --- 결과 분석 ---
if run_analysis:
    # --- 조건 필터링 ---
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

    # --- 위험률 계산 ---
    if not filtered.empty:
        st.subheader("📊 분석 결과")
        for _, row in filtered.iterrows():
            disease = row["질병"]
            base_risk = row["위험률(1000명당)"]
            cond_key = row["기저질환"] if row["기저질환"] in df_adjust["기저질환"].values else "없음"
            adjust_row = df_adjust[df_adjust["기저질환"] == cond_key]
            adjust = adjust_row["조정계수"].values[0] if not adjust_row.empty else 1.0
            final_risk = round(base_risk * adjust, 1)
            risk_multiplier = round(adjust, 1)

            # 수술 정보
            treat_info = df_treat[df_treat["질병"] == disease]
            coverage_info = df_coverage[df_coverage["질병"] == disease]

            # 멘트 자동 생성
            auto_ment = f"""
✅ **{cond_key}** 보유 시, {disease} 위험률은 평균보다 **{risk_multiplier}배** 증가합니다.  
→ 현재 고객님의 예상 위험률은 **1000명 중 {final_risk}명**입니다.
"""
            if not coverage_info.empty:
                d_rate = coverage_info['진단비보유율(%)'].values[0]
                t_rate = coverage_info['치료비보유율(%)'].values[0]
                auto_ment += f"""
📉 평균적으로 고객의 **{d_rate}%**는 해당 질병에 대한 진단비를, **{t_rate}%**는 치료비 특약을 보유하고 있습니다.  
→ 가입이 늦으면, 가입 자체가 어려워질 수 있습니다.
"""
            auto_ment += "\n⚠️ 보험은 건강할 때만 가입할 수 있습니다. 지금이 가장 빠른 시점입니다."

            st.markdown(f"""
            ### 🩺 {disease}
            - 기본 위험률: **1000명 중 {base_risk}명**
            - 보정 위험률 (기저질환 반영): **{final_risk}명**
            - 수술명: {treat_info['대표수술'].values[0] if not treat_info.empty else '정보 없음'}
            - 수술등급: {treat_info['수술등급'].values[0] if not treat_info.empty else '-'}등급
            - 평균 수술비: {treat_info['수술비용(만원)'].values[0] if not treat_info.empty else '-'}만원
            - 평균 회복기간: {treat_info['평균회복기간(일)'].values[0] if not treat_info.empty else '-'}일
            - 진단비 보유율: {d_rate if not coverage_info.empty else '-'}%
            - 치료비 보유율: {t_rate if not coverage_info.empty else '-'}%

            ---
            #### 🎯 자동 설득 멘트
            {auto_ment}
            """)

        # 시뮬레이션 그래프 (예: 흡연 vs 비흡연 비교)
        st.subheader("📈 위험률 비교 시뮬레이션")
        sim_data = filtered.groupby("흡연여부")["위험률(1000명당)"].mean().reset_index()
        fig, ax = plt.subplots()
        ax.bar(sim_data["흡연여부"], sim_data["위험률(1000명당)"], width=0.5)
        ax.set_ylabel("위험률 (1000명당)")
        ax.set_title("흡연 여부에 따른 평균 위험률 비교")
        st.pyplot(fig)
    else:
        st.warning("❗ 입력하신 조건에 해당하는 데이터가 없습니다. 다른 조건을 시도해주세요.")
