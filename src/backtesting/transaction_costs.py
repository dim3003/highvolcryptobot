def apply_transaction_costs(
    trade_value,
    dex_fee=0.0008,   # ~0.08% average for 1inch
    gas_fee_usd=0.08  # Arbitrum/Base realistic
):
    return trade_value * dex_fee + gas_fee_usd

