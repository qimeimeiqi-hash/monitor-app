"""Composes candle patterns and trend/box context into a single buy/sell decision.

Every threshold and the composition rules themselves were confirmed explicitly with
the user; see docs/data/kline usage and CLAUDE.md's stock-monitoring section for the
narrative version. This module only reasons about a single stock's candle history —
it does not fetch data or persist anything.
"""

from src.kline_patterns import (
    has_long_upper_shadow,
    is_bearish_engulfing,
    is_bullish_engulfing,
    is_doji,
    is_evening_star,
    is_hammer,
    is_long_bullish_candle,
    is_morning_star,
)
from src.kline_trend import (
    classify_trend,
    find_box_range,
    has_volume_shrink,
    has_volume_surge,
    is_near_recent_high,
    is_near_recent_low,
)

BREAKOUT_VOLUME_MULTIPLIER = 2.0
BREAKOUT_PRICE_BREAK_RATIO = 1.02
BREAKDOWN_PRICE_BREAK_RATIO = 0.98
SELL_VOLUME_SURGE_MULTIPLIER = 1.5

MINIMUM_CANDLES_REQUIRED = 3


def _detect_breakout(candles: list, today: dict, box: dict) -> str:
    if box is None or not box["qualifies"]:
        return None
    price_breaks_out = today["close"] >= box["upper"] * BREAKOUT_PRICE_BREAK_RATIO
    volume_confirms = has_volume_surge(candles, multiplier=BREAKOUT_VOLUME_MULTIPLIER)
    if price_breaks_out and volume_confirms and is_long_bullish_candle(today):
        return f"長期箱体（¥{box['lower']:.1f}〜¥{box['upper']:.1f}）を出来高を伴って上抜け（放量大陽線でのブレイクアウト）"
    return None


def _detect_breakdown(today: dict, box: dict) -> str:
    if box is None or not box["qualifies"]:
        return None
    price_breaks_down = today["close"] <= box["lower"] * BREAKDOWN_PRICE_BREAK_RATIO
    if price_breaks_down:
        return f"長期箱体（¥{box['lower']:.1f}〜¥{box['upper']:.1f}）の下沿を割り込み（サポート崩壊、逃げ場のシグナル）"
    return None


def _collect_buy_pattern_reasons(candles: list, today: dict) -> list:
    reasons = []
    if len(candles) >= 2 and is_bullish_engulfing(candles[-2], today):
        reasons.append("安値圏で陽包陰（強気の包み足）が出現")
    if is_hammer(today):
        if has_volume_shrink(candles):
            reasons.append("安値圏で鎚子線が出現（縮量での押し目、下値支持が強い）")
        else:
            reasons.append("安値圏で鎚子線が出現（下値支持が強い）")
    if len(candles) >= 3 and is_morning_star(candles[-3], candles[-2], today):
        reasons.append("安値圏で明けの明星が出現（底打ち反転のシグナル）")
    return reasons


def _collect_sell_pattern_reasons(candles: list, today: dict) -> list:
    reasons = []
    if len(candles) >= 2 and is_bearish_engulfing(candles[-2], today):
        reasons.append("高値圏で陰包陽（弱気の包み足）が出現")
    if len(candles) >= 3 and is_evening_star(candles[-3], candles[-2], today):
        reasons.append("高値圏で宵の明星が出現（天井反転のシグナル）")
    if has_volume_surge(candles, multiplier=SELL_VOLUME_SURGE_MULTIPLIER) and (is_doji(today) or has_long_upper_shadow(today)):
        reasons.append("高値圏で出来高を伴う滞涨（十字星または長い上影線）が出現")
    return reasons


def evaluate_signal(candles: list) -> dict:
    if len(candles) < MINIMUM_CANDLES_REQUIRED:
        return None

    today = candles[-1]
    trend = classify_trend(candles)
    box = find_box_range(candles)

    buy_reasons = []
    sell_reasons = []

    breakout_reason = _detect_breakout(candles, today, box)
    if breakout_reason:
        buy_reasons.append(breakout_reason)

    breakdown_reason = _detect_breakdown(today, box)
    if breakdown_reason:
        sell_reasons.append(breakdown_reason)

    if is_near_recent_low(candles) and trend != "downtrend":
        buy_reasons.extend(_collect_buy_pattern_reasons(candles, today))

    if is_near_recent_high(candles):
        sell_reasons.extend(_collect_sell_pattern_reasons(candles, today))

    buy_signal = trend != "downtrend" and len(buy_reasons) > 0
    sell_signal = len(sell_reasons) > 0

    if not buy_signal and not sell_signal:
        return None

    if sell_signal:
        return {
            "action": "sell",
            "reasons": sell_reasons,
            "stop_loss": None,
            "date": today["date"],
            "price": today["close"],
        }

    return {
        "action": "buy",
        "reasons": buy_reasons,
        "stop_loss": today["low"],
        "date": today["date"],
        "price": today["close"],
    }
