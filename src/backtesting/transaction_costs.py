def apply_transaction_costs(trade_value, dex_fee=0.003, gas_fee_usd=0.15):
    # trade_value: USD allocated to the token
    total_cost = trade_value * dex_fee + gas_fee_usd
    return total_cost
