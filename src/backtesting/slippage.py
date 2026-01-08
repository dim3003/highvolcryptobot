def slippage_cost(trade_value, pool_liquidity):
    """
    Approximate slippage for constant product AMM (Uniswap V2/V3 style).
    trade_value: USD amount you want to swap
    pool_liquidity: USD value of the pool's reserve for that token
    Returns slippage fraction (0.0 = no slippage)
    """
    fraction_of_pool = trade_value / pool_liquidity
    # Simple non-linear approximation
    slippage = fraction_of_pool / (1 - fraction_of_pool)
    return slippage

