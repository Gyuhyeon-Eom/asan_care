def calculate_rule_weight(df_train, rule_condition, fraud_col='부정행위'):
    """각 룰의 가중치를 WoE로 계산"""
    # 룰 충족 시 부정행위 비율
    fraud_rate_when_rule = df_train[rule_condition][fraud_col].mean()

    # 전체 부정행위 비율
    base_fraud_rate = df_train[fraud_col].mean()

    # Weight of Evidence
    woe = np.log(
        (fraud_rate_when_rule + 1e-6) / (base_fraud_rate + 1e-6)
    )

    # 0~5점 스케일로 정규화
    score = np.clip(woe * 2, 0, 5)  # 조정 필요

    return score, {
        'fraud_rate_when_rule': fraud_rate_when_rule,
        'base_rate': base_fraud_rate,
        'woe': woe,
        'score': score
    }


# 사용 예시
rule1_condition = (df_train['delay_days'] >= 14)
rule1_score, rule1_stats = calculate_rule_weight(df_train, rule1_condition)

print(f"Rule1 통계: {rule1_stats}")
# 출력: {'fraud_rate_when_rule': 0.15, 'base_rate': 0.05, 'woe': 1.098, 'score': 2.2}
