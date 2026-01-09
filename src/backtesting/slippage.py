def slippage_cost(trade_value, pool_liquidity):
    if pool_liquidity <= 0:
        return 0.0

    fraction = trade_value / pool_liquidity

    # realistic 1inch-style behavior
    if fraction < 0.001:        # <0.1% of liquidity
        slippage = 0.0001       # 0.01%
    elif fraction < 0.01:       # <1%
        slippage = 0.0005       # 0.05%
    elif fraction < 0.05:       # <5%
        slippage = 0.0015       # 0.15%
    else:
        slippage = 0.003        # 0.30%

    return min(slippage, 0.005) # hard cap 0.5%

