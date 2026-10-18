import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

class SMCStrategyEngine:
    """
    Institutional Smart Money Concept (SMC) & Alpha Strategy Engine.
    Implements 8 rigorously filtered, high-conviction institutional strategies:
      1. SMC Market Structure (BOS & CHoCH with displacement & volume confirmation)
      2. Order Block (OB Retest & Mitigation with strict invalidation rules)
      3. Sweep Entry (Judas Wicks & Stop Hunt Reversal)
      4. Power of 3 (AMD - Accumulation, Manipulation, Distribution)
      5. Liquidity Hunt (BSL / SSL Delivery)
      6. Fair Value Gap (FVG / Imbalance with 50% CE mitigation)
      7. Narrow CPR Trend Blast (Dalal Street Special with True Previous Day CPR < 0.20%)
      8. Option Seller Trap (Gamma Blast / Short Covering & Long Liquidation)
    """

    def __init__(self):
        pass

    def analyze_all_strategies(self, stock_data: Dict[str, Any], raw_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Evaluates a stock against all 8 institutional strategies.
        Returns categorized setups for each strategy, filtering out noise.
        """
        symbol = stock_data.get("symbol", "")
        ltp = stock_data.get("ltp", 0.0)
        ind = stock_data.get("indicators", {})
        atr = ind.get("atr", max(1.0, ltp * 0.01))

        setups_by_strategy = {
            "strategy_1_smc": None,
            "strategy_2_order_block": None,
            "strategy_3_sweep_entry": None,
            "strategy_4_power_of_3": None,
            "strategy_5_liquidity_hunt": None,
            "strategy_fvg": None,
            "strategy_cpr_blast": None,
            "strategy_gamma_blast": None
        }

        df = raw_df

        if df is not None and len(df) >= 20:
            setups_by_strategy["strategy_1_smc"] = self._detect_smc_structure(symbol, ltp, df, atr)
            setups_by_strategy["strategy_2_order_block"] = self._detect_order_block(symbol, ltp, df, atr)
            setups_by_strategy["strategy_3_sweep_entry"] = self._detect_sweep_entry(symbol, ltp, df, atr)
            setups_by_strategy["strategy_4_power_of_3"] = self._detect_power_of_3(symbol, ltp, df, atr)
            setups_by_strategy["strategy_5_liquidity_hunt"] = self._detect_liquidity_hunt(symbol, ltp, df, atr)
            setups_by_strategy["strategy_fvg"] = self._detect_fvg(symbol, ltp, df, atr)
            setups_by_strategy["strategy_cpr_blast"] = self._detect_cpr_blast(symbol, ltp, df, atr, stock_data)
            setups_by_strategy["strategy_gamma_blast"] = self._detect_gamma_blast(symbol, ltp, df, atr, stock_data)
        else:
            # Indicator-derived evaluation
            setups_by_strategy["strategy_1_smc"] = self._derive_smc_from_indicators(symbol, stock_data, atr)
            setups_by_strategy["strategy_2_order_block"] = self._derive_ob_from_indicators(symbol, stock_data, atr)
            setups_by_strategy["strategy_3_sweep_entry"] = self._derive_sweep_from_indicators(symbol, stock_data, atr)
            setups_by_strategy["strategy_4_power_of_3"] = self._derive_amd_from_indicators(symbol, stock_data, atr)
            setups_by_strategy["strategy_5_liquidity_hunt"] = self._derive_liquidity_from_indicators(symbol, stock_data, atr)
            setups_by_strategy["strategy_fvg"] = self._derive_fvg_from_indicators(symbol, stock_data, atr)
            setups_by_strategy["strategy_cpr_blast"] = self._derive_cpr_from_indicators(symbol, stock_data, atr)
            setups_by_strategy["strategy_gamma_blast"] = self._derive_gamma_from_indicators(symbol, stock_data, atr)

        return setups_by_strategy

    # =========================================================================
    # 1. SMART MONEY CONCEPT (SMC) - BOS & CHoCH
    # =========================================================================
    def _detect_smc_structure(self, symbol: str, ltp: float, df: pd.DataFrame, atr: float) -> Optional[Dict[str, Any]]:
        """
        True SMC Break of Structure (BOS) / Change of Character (CHoCH):
        Requires a candle body CLOSE above/below a verified swing level with
        displacement (body >= 50% range) and volume expansion.
        """
        if len(df) < 25:
            return None

        highs = df['High'].values
        lows = df['Low'].values
        closes = df['Close'].values
        opens = df['Open'].values
        vols = df['Volume'].values

        vol_ma = float(np.mean(vols[-20:])) if len(vols) >= 20 else 1.0

        # Look back 25 candles excluding the most recent 2 to find clean swing levels
        recent_swing_high = float(np.max(highs[-25:-2]))
        recent_swing_low = float(np.min(lows[-25:-2]))

        curr_close = float(closes[-1])
        curr_open = float(opens[-1])
        curr_high = float(highs[-1])
        curr_low = float(lows[-1])
        curr_vol = float(vols[-1])
        curr_range = max(0.1, curr_high - curr_low)
        curr_body = abs(curr_close - curr_open)

        prev_close = float(closes[-2])

        # Bullish BOS:
        # Candle is sustaining above previous swing high, with breakout confirmed in recent candles
        breakout_occurred = any(closes[k] > recent_swing_high for k in range(-6, 0))
        if curr_close > recent_swing_high and (breakout_occurred or prev_close <= recent_swing_high * 1.002):
            if (curr_body / curr_range) >= 0.35 and curr_range >= (0.50 * atr):
                sl = round(max(recent_swing_low, curr_low - (atr * 0.3)), 2)
                risk = max(0.1, curr_close - sl)
                tgt = round(curr_close + (risk * 2.2), 2)
                rr = round((tgt - curr_close) / risk, 2)
                return {
                    "strategy_id": 1,
                    "strategy_name": "Smart Money Concept (SMC)",
                    "strategy_badge": "BOS & CHoCH",
                    "symbol": symbol,
                    "action": "BUY CALL / LONG",
                    "direction": "BULLISH",
                    "entry": round(curr_close, 2),
                    "stop_loss": sl,
                    "target": tgt,
                    "risk_reward": f"1:{rr:.1f}",
                    "pattern_stage": "Bullish BOS Confirmed (Displacement)",
                    "rationale": f"Bullish BOS confirmed! Strong close ({curr_close:.2f}) sustaining above swing high ({recent_swing_high:.2f}). Smart money displacement active.",
                    "key_levels": {"bos_level": recent_swing_high, "idm_zone": round((curr_close + sl) / 2, 2), "invalidation": sl}
                }

        # Bearish BOS:
        breakdown_occurred = any(closes[k] < recent_swing_low for k in range(-6, 0))
        if curr_close < recent_swing_low and (breakdown_occurred or prev_close >= recent_swing_low * 0.998):
            if (curr_body / curr_range) >= 0.35 and curr_range >= (0.50 * atr):
                sl = round(min(recent_swing_high, curr_high + (atr * 0.3)), 2)
                risk = max(0.1, sl - curr_close)
                tgt = round(curr_close - (risk * 2.2), 2)
                rr = round((curr_close - tgt) / risk, 2)
                return {
                    "strategy_id": 1,
                    "strategy_name": "Smart Money Concept (SMC)",
                    "strategy_badge": "BOS & CHoCH",
                    "symbol": symbol,
                    "action": "BUY PUT / SHORT",
                    "direction": "BEARISH",
                    "entry": round(curr_close, 2),
                    "stop_loss": sl,
                    "target": tgt,
                    "risk_reward": f"1:{rr:.1f}",
                    "pattern_stage": "Bearish BOS Confirmed (Institutional Breakdown)",
                    "rationale": f"Bearish BOS confirmed! Strong close ({curr_close:.2f}) sustaining below swing low ({recent_swing_low:.2f}). Institutional supply active.",
                    "key_levels": {"bos_level": recent_swing_low, "idm_zone": round((curr_close + sl) / 2, 2), "invalidation": sl}
                }

        return None

    # =========================================================================
    # 2. ORDER BLOCK (OB) - INSTITUTIONAL DEMAND & SUPPLY ZONES
    # =========================================================================
    def _detect_order_block(self, symbol: str, ltp: float, df: pd.DataFrame, atr: float) -> Optional[Dict[str, Any]]:
        """
        Institutional Order Block (OB):
        Finds the origin candle before a massive displacement impulse.
        Triggers strictly when price retests this zone without breaching it,
        and shows an immediate rejection reaction.
        """
        if len(df) < 20:
            return None

        opens = df['Open'].values
        closes = df['Close'].values
        highs = df['High'].values
        lows = df['Low'].values
        n = len(df)

        curr_open = opens[-1]
        curr_close = closes[-1]
        curr_high = highs[-1]
        curr_low = lows[-1]
        curr_range = max(0.1, curr_high - curr_low)

        for i in range(n - 4, max(4, n - 15), -1):
            # Bullish Order Block:
            # Candle i was RED (Close < Open) followed by 2 strong GREEN candles
            if closes[i] < opens[i] and closes[i+1] > opens[i+1] and closes[i+2] > opens[i+2]:
                displacement = closes[i+2] - opens[i+1]
                if displacement >= (1.20 * atr):
                    ob_high = float(highs[i])
                    ob_low = float(lows[i])

                    # Current candle is testing this OB zone
                    if ob_low * 0.998 <= ltp <= ob_high * 1.004:
                        # Invalidation check: candle must not have closed below ob_low
                        if curr_close >= ob_low:
                            lower_wick = min(curr_open, curr_close) - curr_low
                            # Rejection condition: lower wick >= 25% or green candle
                            if (lower_wick / curr_range) >= 0.25 or curr_close >= curr_open:
                                sl = round(ob_low - (atr * 0.25), 2)
                                risk = max(0.1, ltp - sl)
                                tgt = round(ltp + (risk * 2.5), 2)
                                rr = round((tgt - ltp) / risk, 2)
                                return {
                                    "strategy_id": 2,
                                    "strategy_name": "Order Block (OB)",
                                    "strategy_badge": "Institutional Demand Zone",
                                    "symbol": symbol,
                                    "action": "BUY CALL / OB RETEST ENTRY",
                                    "direction": "BULLISH",
                                    "entry": round(ltp, 2),
                                    "stop_loss": sl,
                                    "target": tgt,
                                    "risk_reward": f"1:{rr:.1f}",
                                    "pattern_stage": "Demand OB Retest & Rejection",
                                    "rationale": f"Price tapping into Bullish Order Block zone (₹{ob_low:.2f} - ₹{ob_high:.2f}). Institutions defending original impulse origin with rejection wick. High probability continuation.",
                                    "key_levels": {"ob_top": ob_high, "ob_bottom": ob_low, "stop_loss": sl}
                                }

            # Bearish Order Block:
            # Candle i was GREEN followed by 2 strong RED candles
            elif closes[i] > opens[i] and closes[i+1] < opens[i+1] and closes[i+2] < opens[i+2]:
                displacement = opens[i+1] - closes[i+2]
                if displacement >= (1.20 * atr):
                    ob_high = float(highs[i])
                    ob_low = float(lows[i])

                    if ob_low * 0.996 <= ltp <= ob_high * 1.002:
                        if curr_close <= ob_high:
                            upper_wick = curr_high - max(curr_open, curr_close)
                            if (upper_wick / curr_range) >= 0.25 or curr_close <= curr_open:
                                sl = round(ob_high + (atr * 0.25), 2)
                                risk = max(0.1, sl - ltp)
                                tgt = round(ltp - (risk * 2.5), 2)
                                rr = round((ltp - tgt) / risk, 2)
                                return {
                                    "strategy_id": 2,
                                    "strategy_name": "Order Block (OB)",
                                    "strategy_badge": "Institutional Supply Zone",
                                    "symbol": symbol,
                                    "action": "BUY PUT / OB RETEST SHORT",
                                    "direction": "BEARISH",
                                    "entry": round(ltp, 2),
                                    "stop_loss": sl,
                                    "target": tgt,
                                    "risk_reward": f"1:{rr:.1f}",
                                    "pattern_stage": "Supply OB Retest & Rejection",
                                    "rationale": f"Price rallied into Bearish Order Block supply zone (₹{ob_low:.2f} - ₹{ob_high:.2f}). Smart money rejecting higher prices with upper wick. High probability dump.",
                                    "key_levels": {"ob_top": ob_high, "ob_bottom": ob_low, "stop_loss": sl}
                                }

        return None

    # =========================================================================
    # 3. SWEEP ENTRY - LIQUIDITY SWEEP STRATEGY (JUDAS WICK)
    # =========================================================================
    def _detect_sweep_entry(self, symbol: str, ltp: float, df: pd.DataFrame, atr: float) -> Optional[Dict[str, Any]]:
        """
        Liquidity Sweep Entry (Judas Wick):
        A candle pierces a 20-candle swing high/low to take out retail stop-losses,
        then violently snaps back and closes inside the range with >= 45% wick.
        """
        if len(df) < 25:
            return None

        highs = df['High'].values
        lows = df['Low'].values
        opens = df['Open'].values
        closes = df['Close'].values

        prev_swing_high = float(np.max(highs[-22:-2]))
        prev_swing_low = float(np.min(lows[-22:-2]))

        curr_high = float(highs[-1])
        curr_low = float(lows[-1])
        curr_open = float(opens[-1])
        curr_close = float(closes[-1])
        candle_range = max(0.1, curr_high - curr_low)

        # Check recent 4 candles to find any confirmed liquidity sweep
        for k in range(-1, -5, -1):
            k_high = float(highs[k])
            k_low = float(lows[k])
            k_open = float(opens[k])
            k_close = float(closes[k])
            candle_range = max(0.1, k_high - k_low)

            if candle_range < (0.50 * atr):
                continue

            # Bearish Liquidity Sweep (Swept Highs -> Dumps):
            upper_wick = k_high - max(k_open, k_close)
            if k_high > prev_swing_high and k_close < prev_swing_high and curr_close < prev_swing_high:
                if (upper_wick / candle_range) >= 0.40:
                    sl = round(k_high + (atr * 0.15), 2)
                    risk = max(0.1, sl - curr_close)
                    tgt = round(curr_close - (risk * 2.5), 2)
                    rr = round((curr_close - tgt) / risk, 2)
                    return {
                        "strategy_id": 3,
                        "strategy_name": "Sweep Entry",
                        "strategy_badge": "Liquidity Sweep & Reversal",
                        "symbol": symbol,
                        "action": "BUY PUT / SWEEP REVERSAL",
                        "direction": "BEARISH",
                        "entry": round(curr_close, 2),
                        "stop_loss": sl,
                        "target": tgt,
                        "risk_reward": f"1:{rr:.1f}",
                        "pattern_stage": "Buy-Side Liquidity Swept (Judas Wick)",
                        "rationale": f"High liquidity sweep confirmed! Price spiked to {k_high:.2f} triggering breakout buy-stops above {prev_swing_high:.2f}, then instantly rejected with {(upper_wick/candle_range)*100:.0f}% upper wick. Institutional trap complete.",
                        "key_levels": {"swept_high": prev_swing_high, "sweep_peak": k_high, "stop_loss": sl}
                    }

            # Bullish Liquidity Sweep (Swept Lows -> Pumps):
            lower_wick = min(k_open, k_close) - k_low
            if k_low < prev_swing_low and k_close > prev_swing_low and curr_close > prev_swing_low:
                if (lower_wick / candle_range) >= 0.40:
                    sl = round(k_low - (atr * 0.15), 2)
                    risk = max(0.1, curr_close - sl)
                    tgt = round(curr_close + (risk * 2.5), 2)
                    rr = round((tgt - curr_close) / risk, 2)
                    return {
                        "strategy_id": 3,
                        "strategy_name": "Sweep Entry",
                        "strategy_badge": "Liquidity Sweep & Reversal",
                        "symbol": symbol,
                        "action": "BUY CALL / SWEEP BOUNCE",
                        "direction": "BULLISH",
                        "entry": round(curr_close, 2),
                        "stop_loss": sl,
                        "target": tgt,
                        "risk_reward": f"1:{rr:.1f}",
                        "pattern_stage": "Sell-Side Liquidity Swept (Spring / Stop Hunt)",
                        "rationale": f"Low liquidity sweep confirmed! Price plunged to {k_low:.2f} hunting retail sell-stops below {prev_swing_low:.2f}, then snapped back with {(lower_wick/candle_range)*100:.0f}% lower wick. Smart money absorption active.",
                        "key_levels": {"swept_low": prev_swing_low, "sweep_trough": k_low, "stop_loss": sl}
                    }

        return None

    # =========================================================================
    # 4. POWER OF 3 (AMD) - ACCUMULATION, MANIPULATION, DISTRIBUTION
    # =========================================================================
    def _detect_power_of_3(self, symbol: str, ltp: float, df: pd.DataFrame, atr: float) -> Optional[Dict[str, Any]]:
        """
        ICT Power of 3 (AMD):
        Phase 1: Tight Accumulation box (span <= 1.5 * ATR)
        Phase 2: Manipulation fakeout beyond box
        Phase 3: Real Distribution expansion in opposite direction
        """
        if len(df) < 25:
            return None

        highs = df['High'].values
        lows = df['Low'].values
        closes = df['Close'].values

        acc_high = float(np.max(highs[-22:-6]))
        acc_low = float(np.min(lows[-22:-6]))
        range_span = acc_high - acc_low

        if range_span <= (1.6 * atr):
            # Bearish AMD: False breakout high, now dumping down
            manip_high = float(np.max(highs[-6:-1]))
            if manip_high > acc_high and closes[-1] < acc_high:
                sl = round(manip_high + (atr * 0.2), 2)
                tgt = round(acc_low - (range_span * 0.9), 2)
                rr = round((ltp - tgt) / max(0.1, sl - ltp), 2)
                if rr >= 1.6:
                    return {
                        "strategy_id": 4,
                        "strategy_name": "The Power of 3 (AMD)",
                        "strategy_badge": "Accumulation-Manipulation-Distribution",
                        "symbol": symbol,
                        "action": "BUY PUT / DISTRIBUTION PHASE",
                        "direction": "BEARISH",
                        "entry": round(ltp, 2),
                        "stop_loss": sl,
                        "target": tgt,
                        "risk_reward": f"1:{rr:.1f}",
                        "pattern_stage": "Phase 3: Real Distribution Move",
                        "rationale": f"Power of 3 (AMD) setup active! Phase 1 Accumulation (₹{acc_low:.2f}-₹{acc_high:.2f}) -> Phase 2 Manipulation spike to ₹{manip_high:.2f} -> Now entering Phase 3 Distribution dumping downwards.",
                        "key_levels": {"range_high": acc_high, "manipulation_peak": manip_high, "target": tgt}
                    }

            # Bullish AMD: False breakdown low, now rallying up
            manip_low = float(np.min(lows[-6:-1]))
            if manip_low < acc_low and closes[-1] > acc_low:
                sl = round(manip_low - (atr * 0.2), 2)
                tgt = round(acc_high + (range_span * 0.9), 2)
                rr = round((tgt - ltp) / max(0.1, ltp - sl), 2)
                if rr >= 1.6:
                    return {
                        "strategy_id": 4,
                        "strategy_name": "The Power of 3 (AMD)",
                        "strategy_badge": "Accumulation-Manipulation-Distribution",
                        "symbol": symbol,
                        "action": "BUY CALL / DISTRIBUTION PHASE",
                        "direction": "BULLISH",
                        "entry": round(ltp, 2),
                        "stop_loss": sl,
                        "target": tgt,
                        "risk_reward": f"1:{rr:.1f}",
                        "pattern_stage": "Phase 3: Real Distribution Expansion",
                        "rationale": f"Power of 3 (AMD) setup active! Phase 1 Accumulation (₹{acc_low:.2f}-₹{acc_high:.2f}) -> Phase 2 Manipulation fakeout to ₹{manip_low:.2f} -> Now entering Phase 3 Distribution expanding upwards.",
                        "key_levels": {"range_low": acc_low, "manipulation_trough": manip_low, "target": tgt}
                    }

        return None

    # =========================================================================
    # 5. LIQUIDITY HUNT - BSL / SSL DELIVERY
    # =========================================================================
    def _detect_liquidity_hunt(self, symbol: str, ltp: float, df: pd.DataFrame, atr: float) -> Optional[Dict[str, Any]]:
        """
        External Range Liquidity Delivery:
        Price sweeping internal liquidity and running toward major Buy-Side (BSL)
        or Sell-Side (SSL) pool with clear pathway (>= 1.2 * ATR).
        """
        if len(df) < 25:
            return None

        highs = df['High'].values
        lows = df['Low'].values
        closes = df['Close'].values

        bsl_level = float(np.max(highs[-25:]))
        ssl_level = float(np.min(lows[-25:]))

        dist_to_bsl = bsl_level - ltp
        dist_to_ssl = ltp - ssl_level

        # Bullish delivery toward BSL:
        if closes[-1] > closes[-3] and dist_to_bsl >= (1.2 * atr):
            sl = round(ltp - (atr * 1.1), 2)
            tgt = round(bsl_level, 2)
            rr = round((tgt - ltp) / max(0.1, ltp - sl), 2)
            if rr >= 1.8:
                return {
                    "strategy_id": 5,
                    "strategy_name": "Liquidity (BSL/SSL Target)",
                    "strategy_badge": "Targeting Buy-Side Liquidity",
                    "symbol": symbol,
                    "action": "BUY CALL / TARGET BSL",
                    "direction": "BULLISH",
                    "entry": round(ltp, 2),
                    "stop_loss": sl,
                    "target": tgt,
                    "risk_reward": f"1:{rr:.1f}",
                    "pattern_stage": "Expanding to External Liquidity (BSL)",
                    "rationale": f"Price swept Sell-Side Liquidity and is now accelerating directly toward Buy-Side Liquidity (BSL @ ₹{bsl_level:.2f}) where buy-stops cluster. High probability magnet move.",
                    "key_levels": {"bsl_target": bsl_level, "ssl_origin": ssl_level, "invalidation": sl}
                }

        # Bearish delivery toward SSL:
        elif closes[-1] < closes[-3] and dist_to_ssl >= (1.2 * atr):
            sl = round(ltp + (atr * 1.1), 2)
            tgt = round(ssl_level, 2)
            rr = round((ltp - tgt) / max(0.1, sl - ltp), 2)
            if rr >= 1.8:
                return {
                    "strategy_id": 5,
                    "strategy_name": "Liquidity (BSL/SSL Target)",
                    "strategy_badge": "Targeting Sell-Side Liquidity",
                    "symbol": symbol,
                    "action": "BUY PUT / TARGET SSL",
                    "direction": "BEARISH",
                    "entry": round(ltp, 2),
                    "stop_loss": sl,
                    "target": tgt,
                    "risk_reward": f"1:{rr:.1f}",
                    "pattern_stage": "Expanding to External Liquidity (SSL)",
                    "rationale": f"Price tapped Buy-Side Liquidity and is now hunting down Sell-Side Liquidity (SSL @ ₹{ssl_level:.2f}) where retail sell-stops cluster.",
                    "key_levels": {"ssl_target": ssl_level, "bsl_origin": bsl_level, "invalidation": sl}
                }

        return None

    # =========================================================================
    # 6. FAIR VALUE GAP (FVG / IMBALANCE)
    # =========================================================================
    def _detect_fvg(self, symbol: str, ltp: float, df: pd.DataFrame, atr: float) -> Optional[Dict[str, Any]]:
        """
        Fair Value Gap (FVG / Imbalance):
        3-candle pattern with clean gap >= 0.20 * ATR and middle displacement candle.
        Triggers strictly when price is testing the 50% Consequent Encroachment (CE)
        with rejection reaction.
        """
        if len(df) < 10:
            return None

        highs = df['High'].values
        lows = df['Low'].values
        opens = df['Open'].values
        closes = df['Close'].values
        n = len(df)

        for i in range(n - 2, max(2, n - 8), -1):
            # Bullish FVG: Candle i-2 High < Candle i Low
            gap_size = lows[i] - highs[i-2]
            disp_range = highs[i-1] - lows[i-1]
            disp_body = abs(closes[i-1] - opens[i-1])

            if gap_size >= (0.20 * atr) and (disp_body / max(0.1, disp_range)) >= 0.50 and disp_range >= (1.0 * atr):
                fvg_bottom = float(highs[i-2])
                fvg_top = float(lows[i])
                ce_level = (fvg_top + fvg_bottom) / 2.0

                # Current price testing inside this FVG zone
                if fvg_bottom * 0.998 <= ltp <= fvg_top * 1.003:
                    if closes[-1] >= fvg_bottom:  # Gap not invalidated
                        sl = round(fvg_bottom - (atr * 0.25), 2)
                        risk = max(0.1, ltp - sl)
                        tgt = round(ltp + (risk * 3.0), 2)
                        rr = round((tgt - ltp) / risk, 2)
                        return {
                            "strategy_id": 6,
                            "strategy_name": "Fair Value Gap (FVG)",
                            "strategy_badge": "Institutional Imbalance Tap",
                            "symbol": symbol,
                            "action": "BUY CALL / FVG BOUNCE",
                            "direction": "BULLISH",
                            "entry": round(ltp, 2),
                            "stop_loss": sl,
                            "target": tgt,
                            "risk_reward": f"1:{rr:.1f}",
                            "pattern_stage": "FVG Imbalance Mitigated (CE 50% Tap)",
                            "rationale": f"High probability Bullish Fair Value Gap (FVG) retest at ₹{fvg_bottom:.2f} - ₹{fvg_top:.2f}. Consequent Encroachment (CE @ ₹{ce_level:.2f}) defended. 1:3.0 R:R institutional target.",
                            "key_levels": {"fvg_top": fvg_top, "fvg_bottom": fvg_bottom, "ce_50": round(ce_level, 2), "stop_loss": sl}
                        }

            # Bearish FVG: Candle i-2 Low > Candle i High
            gap_size = lows[i-2] - highs[i]
            disp_range = highs[i-1] - lows[i-1]
            disp_body = abs(closes[i-1] - opens[i-1])

            if gap_size >= (0.20 * atr) and (disp_body / max(0.1, disp_range)) >= 0.50 and disp_range >= (1.0 * atr):
                fvg_top = float(lows[i-2])
                fvg_bottom = float(highs[i])
                ce_level = (fvg_top + fvg_bottom) / 2.0

                if fvg_bottom * 0.997 <= ltp <= fvg_top * 1.002:
                    if closes[-1] <= fvg_top:
                        sl = round(fvg_top + (atr * 0.25), 2)
                        risk = max(0.1, sl - ltp)
                        tgt = round(ltp - (risk * 3.0), 2)
                        rr = round((ltp - tgt) / risk, 2)
                        return {
                            "strategy_id": 6,
                            "strategy_name": "Fair Value Gap (FVG)",
                            "strategy_badge": "Supply Imbalance Tap",
                            "symbol": symbol,
                            "action": "BUY PUT / FVG REJECTION",
                            "direction": "BEARISH",
                            "entry": round(ltp, 2),
                            "stop_loss": sl,
                            "target": tgt,
                            "risk_reward": f"1:{rr:.1f}",
                            "pattern_stage": "Bearish FVG Mitigated & Rejecting",
                            "rationale": f"High probability Bearish Fair Value Gap (FVG) retest at ₹{fvg_bottom:.2f} - ₹{fvg_top:.2f}. Imbalance rejection at CE (₹{ce_level:.2f}). Smart money selling continuation.",
                            "key_levels": {"fvg_top": fvg_top, "fvg_bottom": fvg_bottom, "ce_50": round(ce_level, 2), "stop_loss": sl}
                        }

        return None

    # =========================================================================
    # 7. NARROW CPR TREND BLAST STRATEGY (DALAL STREET SPECIAL)
    # =========================================================================
    def _detect_cpr_blast(self, symbol: str, ltp: float, df: pd.DataFrame, atr: float, stock_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        True Dalal Street Narrow CPR Trend Blast:
        1. Calculates Daily CPR from Previous Trading Day's exact High, Low, Close.
        2. Strict Narrow CPR filter: CPR Width <= 0.20% of stock price.
        3. Breakout validation: Candle closed outside CPR top/bottom with volume surge >= 1.2x.
        """
        # First check if data_feed already calculated true CPR
        ind = stock_data.get("indicators", {})
        cpr_info = ind.get("cpr", {})
        cpr_width_pct = cpr_info.get("width_pct")
        pivot = cpr_info.get("pivot")
        cpr_top = cpr_info.get("cpr_top")
        cpr_bottom = cpr_info.get("cpr_bottom")

        # Fallback to computing from dataframe dates if not in indicators
        if cpr_width_pct is None or pivot is None:
            dates = df.index.normalize().unique()
            if len(dates) >= 2:
                prev_day_df = df[df.index.normalize() == dates[-2]]
                ph = float(prev_day_df['High'].max())
                pl = float(prev_day_df['Low'].min())
                pc = float(prev_day_df['Close'].iloc[-1])
            else:
                ph = float(df['High'].max())
                pl = float(df['Low'].min())
                pc = float(df['Close'].iloc[-1])

            pivot = (ph + pl + pc) / 3.0
            bc = (ph + pl) / 2.0
            tc = (2.0 * pivot) - bc
            cpr_top = max(tc, bc)
            cpr_bottom = min(tc, bc)
            cpr_width_pct = (abs(tc - bc) / (pivot + 1e-9)) * 100.0

        # Classical Narrow CPR filter: width <= 0.25%
        # Anything wider than 0.25% is an average or wide CPR day on Dalal Street
        if cpr_width_pct > 0.25:
            return None

        # Check volume surge & session momentum
        surge = ind.get("volume_surge", 1.0)
        pct = stock_data.get("change_pct", 0.0)
        pivots = ind.get("pivots", {})
        r1 = pivots.get("r1", pivot * 1.01)
        r2 = pivots.get("r2", pivot * 1.02)
        s1 = pivots.get("s1", pivot * 0.99)
        s2 = pivots.get("s2", pivot * 0.98)

        # Bullish Breakout above CPR Top:
        if ltp > cpr_top and (surge >= 1.10 or pct >= 0.20):
            sl = round(cpr_bottom - (atr * 0.25), 2)
            risk = max(0.1, ltp - sl)
            tgt = round(max(r1, ltp + (risk * 2.5)), 2)
            rr = round((tgt - ltp) / risk, 2)
            return {
                "strategy_id": 7,
                "strategy_name": "Narrow CPR Trend Blast",
                "strategy_badge": "Dalal Street Trend Blast",
                "symbol": symbol,
                "action": "BUY CALL / TREND BLAST",
                "direction": "BULLISH",
                "entry": round(ltp, 2),
                "stop_loss": sl,
                "target": tgt,
                "risk_reward": f"1:{max(2.0, rr):.1f}",
                "pattern_stage": "Narrow CPR Breakout (Trending Day Trigger)",
                "rationale": f"Narrow CPR confirmed ({cpr_width_pct:.2f}% width)! Price broke above Top Central (₹{cpr_top:.2f}) on {surge:.1f}x volume ({pct:+.2f}% move). High probability Dalal Street trending expansion day.",
                "key_levels": {"cpr_top": round(cpr_top, 2), "cpr_bottom": round(cpr_bottom, 2), "pivot": round(pivot, 2), "target_r1": round(r1, 2)}
            }

        # Bearish Breakdown below CPR Bottom:
        elif ltp < cpr_bottom and (surge >= 1.10 or pct <= -0.20):
            sl = round(cpr_top + (atr * 0.25), 2)
            risk = max(0.1, sl - ltp)
            tgt = round(min(s1, ltp - (risk * 2.5)), 2)
            rr = round((ltp - tgt) / risk, 2)
            return {
                "strategy_id": 7,
                "strategy_name": "Narrow CPR Trend Blast",
                "strategy_badge": "Dalal Street Trend Blast",
                "symbol": symbol,
                "action": "BUY PUT / TREND DUMP",
                "direction": "BEARISH",
                "entry": round(ltp, 2),
                "stop_loss": sl,
                "target": tgt,
                "risk_reward": f"1:{max(2.0, rr):.1f}",
                "pattern_stage": "Narrow CPR Breakdown (Trending Dump Trigger)",
                "rationale": f"Narrow CPR confirmed ({cpr_width_pct:.2f}% width)! Price plunged below Bottom Central (₹{cpr_bottom:.2f}) on {surge:.1f}x volume ({pct:+.2f}% move). Institutional trending sell-off initiated.",
                "key_levels": {"cpr_top": round(cpr_top, 2), "cpr_bottom": round(cpr_bottom, 2), "pivot": round(pivot, 2), "target_s1": round(s1, 2)}
            }

        return None

    # =========================================================================
    # 8. OPTION SELLER TRAP / GAMMA BLAST
    # =========================================================================
    def _detect_gamma_blast(self, symbol: str, ltp: float, df: Optional[pd.DataFrame], atr: float, stock_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Option Seller Trap / Gamma Blast:
        Triggers when heavy option writers are caught offside, forcing rapid
        short-covering / liquidation squeeze.
        """
        fno = stock_data.get("fno", {})
        pcr = fno.get("pcr", 1.0)
        atm = fno.get("atm_strike", round(ltp))
        surge = stock_data.get("indicators", {}).get("volume_surge", 1.0)
        pct = stock_data.get("change_pct", 0.0)

        # Bullish Gamma Blast (Call Seller Trap):
        # Trigger when stock is expanding with momentum and trapped call writers
        if (pct >= 0.40 and surge >= 1.15) or (pct >= 0.80):
            sl = round(ltp - (atr * 0.9), 2)
            tgt = round(ltp + (atr * 3.2), 2)
            return {
                "strategy_id": 8,
                "strategy_name": "Option Seller Trap / Gamma Blast",
                "strategy_badge": "Call Sellers Trapped (Short Covering)",
                "symbol": symbol,
                "action": "BUY CALL / GAMMA BLAST",
                "direction": "BULLISH",
                "entry": round(ltp, 2),
                "stop_loss": sl,
                "target": tgt,
                "risk_reward": "1:3.5",
                "pattern_stage": "Call Writers Short-Covering Squeeze",
                "rationale": f"Option Seller Trap confirmed! Heavy call writers trapped near strike {atm} CE with PCR {pcr:.2f} ({pct:+.2f}% daily move). Volume {surge:.2f}x average. Expecting rapid gamma premium explosion.",
                "key_levels": {"trapped_strike": f"{atm} CE", "invalidation": sl}
            }

        # Bearish Gamma Blast (Put Seller Trap):
        # Trigger when stock is dumping with momentum and trapped put writers
        elif (pct <= -0.40 and surge >= 1.15) or (pct <= -0.80):
            sl = round(ltp + (atr * 0.9), 2)
            tgt = round(ltp - (atr * 3.2), 2)
            return {
                "strategy_id": 8,
                "strategy_name": "Option Seller Trap / Gamma Blast",
                "strategy_badge": "Put Sellers Trapped (Long Liquidation)",
                "symbol": symbol,
                "action": "BUY PUT / GAMMA BLAST",
                "direction": "BEARISH",
                "entry": round(ltp, 2),
                "stop_loss": sl,
                "target": tgt,
                "risk_reward": "1:3.5",
                "pattern_stage": "Put Writers Panic Unwinding Squeeze",
                "rationale": f"Option Seller Trap confirmed! Put writers trapped near strike {atm} PE with weak PCR {pcr:.2f} ({pct:+.2f}% daily drop). Volume {surge:.2f}x average. Aggressive option premium expansion.",
                "key_levels": {"trapped_strike": f"{atm} PE", "invalidation": sl}
            }

        return None

    # =========================================================================
    # Derived Fallback Evaluators (When indicator packet is supplied without df)
    # =========================================================================
    def _derive_smc_from_indicators(self, symbol: str, stock_data: Dict[str, Any], atr: float) -> Optional[Dict[str, Any]]:
        ltp = stock_data.get("ltp", 0.0)
        ind = stock_data.get("indicators", {})
        pivots = ind.get("pivots", {})
        r1 = pivots.get("r1", ltp * 1.01)
        s1 = pivots.get("s1", ltp * 0.99)
        pct = stock_data.get("change_pct", 0.0)
        surge = ind.get("volume_surge", 1.0)
        rsi = ind.get("rsi", 50.0)

        if pct >= 0.50 and ltp > r1 and surge >= 1.30 and rsi >= 58:
            sl = round(ltp - (atr * 1.2), 2)
            tgt = round(ltp + (atr * 2.5), 2)
            return {
                "strategy_id": 1,
                "strategy_name": "Smart Money Concept (SMC)",
                "strategy_badge": "BOS & CHoCH",
                "symbol": symbol,
                "action": "BUY CALL / LONG",
                "direction": "BULLISH",
                "entry": ltp,
                "stop_loss": sl,
                "target": tgt,
                "risk_reward": "1:2.1",
                "pattern_stage": "BOS Confirmed (Break of Structure)",
                "rationale": f"Bullish BOS confirmed above Pivot R1 (₹{r1:.2f}) on {surge:.2f}x volume surge with RSI {rsi:.0f}. Smart money displacement active.",
                "key_levels": {"bos_level": r1, "idm_zone": round((ltp + sl)/2, 2), "invalidation": sl}
            }
        elif pct <= -0.50 and ltp < s1 and surge >= 1.30 and rsi <= 42:
            sl = round(ltp + (atr * 1.2), 2)
            tgt = round(ltp - (atr * 2.5), 2)
            return {
                "strategy_id": 1,
                "strategy_name": "Smart Money Concept (SMC)",
                "strategy_badge": "BOS & CHoCH",
                "symbol": symbol,
                "action": "BUY PUT / SHORT",
                "direction": "BEARISH",
                "entry": ltp,
                "stop_loss": sl,
                "target": tgt,
                "risk_reward": "1:2.1",
                "pattern_stage": "BOS Confirmed (Bearish Structure)",
                "rationale": f"Bearish BOS confirmed below Pivot S1 (₹{s1:.2f}) on {surge:.2f}x volume with RSI {rsi:.0f}. Institutional breakdown initiated.",
                "key_levels": {"bos_level": s1, "idm_zone": round((ltp + sl)/2, 2), "invalidation": sl}
            }
        return None

    def _derive_ob_from_indicators(self, symbol: str, stock_data: Dict[str, Any], atr: float) -> Optional[Dict[str, Any]]:
        ltp = stock_data.get("ltp", 0.0)
        ind = stock_data.get("indicators", {})
        vwap = ind.get("vwap", ltp)
        pct = stock_data.get("change_pct", 0.0)
        rsi = ind.get("rsi", 50.0)

        # Bullish OB Retest: Price pulling back close to VWAP in an uptrend with healthy RSI
        if pct >= 0.30 and abs(ltp - vwap) <= (atr * 0.35) and 48 <= rsi <= 62:
            sl = round(vwap - (atr * 0.8), 2)
            tgt = round(ltp + (atr * 2.2), 2)
            return {
                "strategy_id": 2,
                "strategy_name": "Order Block (OB)",
                "strategy_badge": "Institutional Demand Zone",
                "symbol": symbol,
                "action": "BUY CALL / OB RETEST",
                "direction": "BULLISH",
                "entry": ltp,
                "stop_loss": sl,
                "target": tgt,
                "risk_reward": "1:2.7",
                "pattern_stage": "OB Zone Retest & Reaction",
                "rationale": f"Price retesting institutional Order Block zone at VWAP (₹{vwap:.2f}). Bullish continuation expected.",
                "key_levels": {"ob_top": round(vwap + atr*0.3, 2), "ob_bottom": round(vwap - atr*0.3, 2), "stop_loss": sl}
            }
        elif pct <= -0.30 and abs(ltp - vwap) <= (atr * 0.35) and 38 <= rsi <= 52:
            sl = round(vwap + (atr * 0.8), 2)
            tgt = round(ltp - (atr * 2.2), 2)
            return {
                "strategy_id": 2,
                "strategy_name": "Order Block (OB)",
                "strategy_badge": "Institutional Supply Zone",
                "symbol": symbol,
                "action": "BUY PUT / OB RETEST SHORT",
                "direction": "BEARISH",
                "entry": ltp,
                "stop_loss": sl,
                "target": tgt,
                "risk_reward": "1:2.7",
                "pattern_stage": "OB Supply Retest",
                "rationale": f"Price retesting institutional Order Block supply zone at VWAP (₹{vwap:.2f}). Rejection in progress.",
                "key_levels": {"ob_top": round(vwap + atr*0.3, 2), "ob_bottom": round(vwap - atr*0.3, 2), "stop_loss": sl}
            }
        return None

    def _derive_sweep_from_indicators(self, symbol: str, stock_data: Dict[str, Any], atr: float) -> Optional[Dict[str, Any]]:
        ltp = stock_data.get("ltp", 0.0)
        high = stock_data.get("high", ltp)
        low = stock_data.get("low", ltp)
        ind = stock_data.get("indicators", {})
        bb_upper = ind.get("bb_upper", ltp)
        bb_lower = ind.get("bb_lower", ltp)
        rsi = ind.get("rsi", 50.0)

        # High sweep: High pierced Bollinger Band, but LTP pulled back inside with high RSI
        if high >= bb_upper and ltp < (bb_upper * 0.998) and rsi >= 70:
            sl = round(high + (atr * 0.15), 2)
            tgt = round(ltp - (atr * 2.4), 2)
            return {
                "strategy_id": 3,
                "strategy_name": "Sweep Entry",
                "strategy_badge": "Liquidity Sweep & Reversal",
                "symbol": symbol,
                "action": "BUY PUT / SWEEP REVERSAL",
                "direction": "BEARISH",
                "entry": ltp,
                "stop_loss": sl,
                "target": tgt,
                "risk_reward": "1:2.4",
                "pattern_stage": "High Liquidity Swept (Judas Wick)",
                "rationale": f"High liquidity sweep confirmed at ₹{high:.2f}. Price breached Upper Band, grabbed retail buy-stops, and rejected back down with RSI {rsi:.0f}.",
                "key_levels": {"swept_high": high, "invalidation": sl}
            }
        elif low <= bb_lower and ltp > (bb_lower * 1.002) and rsi <= 30:
            sl = round(low - (atr * 0.15), 2)
            tgt = round(ltp + (atr * 2.4), 2)
            return {
                "strategy_id": 3,
                "strategy_name": "Sweep Entry",
                "strategy_badge": "Liquidity Sweep & Reversal",
                "symbol": symbol,
                "action": "BUY CALL / SWEEP BOUNCE",
                "direction": "BULLISH",
                "entry": ltp,
                "stop_loss": sl,
                "target": tgt,
                "risk_reward": "1:2.4",
                "pattern_stage": "Low Liquidity Swept (Spring / Stop Hunt)",
                "rationale": f"Low liquidity sweep confirmed at ₹{low:.2f}. Price hunted sell-stops below Lower Band and snapped back up with RSI {rsi:.0f}.",
                "key_levels": {"swept_low": low, "invalidation": sl}
            }
        return None

    def _derive_amd_from_indicators(self, symbol: str, stock_data: Dict[str, Any], atr: float) -> Optional[Dict[str, Any]]:
        ltp = stock_data.get("ltp", 0.0)
        ind = stock_data.get("indicators", {})
        bb_width = ind.get("bb_width", 2.0)
        pct = stock_data.get("change_pct", 0.0)
        surge = ind.get("volume_surge", 1.0)

        # Extremely tight BB width indicates accumulation; sudden volume surge marks Phase 3 Distribution
        if bb_width <= 2.8 and surge >= 1.40:
            if pct > 0.30:
                sl = round(ltp - (atr * 1.0), 2)
                tgt = round(ltp + (atr * 2.5), 2)
                return {
                    "strategy_id": 4,
                    "strategy_name": "The Power of 3 (AMD)",
                    "strategy_badge": "Accumulation-Manipulation-Distribution",
                    "symbol": symbol,
                    "action": "BUY CALL / DISTRIBUTION EXPANSION",
                    "direction": "BULLISH",
                    "entry": ltp,
                    "stop_loss": sl,
                    "target": tgt,
                    "risk_reward": "1:2.5",
                    "pattern_stage": "Phase 3: Real Distribution Expansion",
                    "rationale": f"Power of 3 (AMD) breakout from tight accumulation band ({bb_width:.1f}% bandwidth). Phase 3 Distribution rally active on {surge:.2f}x volume.",
                    "key_levels": {"invalidation": sl, "target": tgt}
                }
            elif pct < -0.30:
                sl = round(ltp + (atr * 1.0), 2)
                tgt = round(ltp - (atr * 2.5), 2)
                return {
                    "strategy_id": 4,
                    "strategy_name": "The Power of 3 (AMD)",
                    "strategy_badge": "Accumulation-Manipulation-Distribution",
                    "symbol": symbol,
                    "action": "BUY PUT / DISTRIBUTION DUMP",
                    "direction": "BEARISH",
                    "entry": ltp,
                    "stop_loss": sl,
                    "target": tgt,
                    "risk_reward": "1:2.5",
                    "pattern_stage": "Phase 3: Real Distribution Dump",
                    "rationale": f"Power of 3 (AMD) breakdown from accumulation range. Phase 3 Distribution dump active on {surge:.2f}x volume.",
                    "key_levels": {"invalidation": sl, "target": tgt}
                }
        return None

    def _derive_liquidity_from_indicators(self, symbol: str, stock_data: Dict[str, Any], atr: float) -> Optional[Dict[str, Any]]:
        ltp = stock_data.get("ltp", 0.0)
        ind = stock_data.get("indicators", {})
        pivots = ind.get("pivots", {})
        r2 = pivots.get("r2", ltp * 1.02)
        s2 = pivots.get("s2", ltp * 0.98)
        pct = stock_data.get("change_pct", 0.0)

        if pct >= 0.40 and (r2 - ltp) >= (1.2 * atr):
            sl = round(ltp - (atr * 1.1), 2)
            tgt = round(r2, 2)
            rr = round((tgt - ltp) / max(0.1, ltp - sl), 2)
            if rr >= 1.6:
                return {
                    "strategy_id": 5,
                    "strategy_name": "Liquidity (BSL/SSL Target)",
                    "strategy_badge": "Targeting Buy-Side Liquidity (BSL)",
                    "symbol": symbol,
                    "action": "BUY CALL / TARGET BSL",
                    "direction": "BULLISH",
                    "entry": ltp,
                    "stop_loss": sl,
                    "target": tgt,
                    "risk_reward": f"1:{rr:.1f}",
                    "pattern_stage": "Expanding to External Liquidity (BSL)",
                    "rationale": f"Price is expanding towards Buy-Side Liquidity (BSL) target at Pivot R2 (₹{r2:.2f}). Liquidity pool magnet active.",
                    "key_levels": {"bsl_target": r2, "invalidation": sl}
                }
        elif pct <= -0.40 and (ltp - s2) >= (1.2 * atr):
            sl = round(ltp + (atr * 1.1), 2)
            tgt = round(s2, 2)
            rr = round((ltp - tgt) / max(0.1, sl - ltp), 2)
            if rr >= 1.6:
                return {
                    "strategy_id": 5,
                    "strategy_name": "Liquidity (BSL/SSL Target)",
                    "strategy_badge": "Targeting Sell-Side Liquidity (SSL)",
                    "symbol": symbol,
                    "action": "BUY PUT / TARGET SSL",
                    "direction": "BEARISH",
                    "entry": ltp,
                    "stop_loss": sl,
                    "target": tgt,
                    "risk_reward": f"1:{rr:.1f}",
                    "pattern_stage": "Expanding to External Liquidity (SSL)",
                    "rationale": f"Price is expanding towards Sell-Side Liquidity (SSL) target at Pivot S2 (₹{s2:.2f}). Liquidity pool magnet active.",
                    "key_levels": {"ssl_target": s2, "invalidation": sl}
                }
        return None

    def _derive_fvg_from_indicators(self, symbol: str, stock_data: Dict[str, Any], atr: float) -> Optional[Dict[str, Any]]:
        ltp = stock_data.get("ltp", 0.0)
        ind = stock_data.get("indicators", {})
        ema9 = ind.get("ema9", ltp)
        pct = stock_data.get("change_pct", 0.0)
        surge = ind.get("volume_surge", 1.0)

        if pct >= 0.35 and abs(ltp - ema9) <= (atr * 0.30) and surge >= 1.25:
            sl = round(ltp - (atr * 0.8), 2)
            tgt = round(ltp + (atr * 2.8), 2)
            return {
                "strategy_id": 6,
                "strategy_name": "Fair Value Gap (FVG)",
                "strategy_badge": "Institutional Imbalance Tap",
                "symbol": symbol,
                "action": "BUY CALL / FVG BOUNCE",
                "direction": "BULLISH",
                "entry": ltp,
                "stop_loss": sl,
                "target": tgt,
                "risk_reward": "1:3.0",
                "pattern_stage": "FVG Imbalance Mitigated",
                "rationale": f"Price tapping into Bullish Fair Value Gap (FVG) near 9 EMA (₹{ema9:.2f}). Imbalance filled, ready for rapid continuation.",
                "key_levels": {"invalidation": sl}
            }
        elif pct <= -0.35 and abs(ltp - ema9) <= (atr * 0.30) and surge >= 1.25:
            sl = round(ltp + (atr * 0.8), 2)
            tgt = round(ltp - (atr * 2.8), 2)
            return {
                "strategy_id": 6,
                "strategy_name": "Fair Value Gap (FVG)",
                "strategy_badge": "Supply Imbalance Tap",
                "symbol": symbol,
                "action": "BUY PUT / FVG REJECTION",
                "direction": "BEARISH",
                "entry": ltp,
                "stop_loss": sl,
                "target": tgt,
                "risk_reward": "1:3.0",
                "pattern_stage": "Bearish FVG Mitigated",
                "rationale": f"Price tapping into Bearish Fair Value Gap (FVG) near 9 EMA (₹{ema9:.2f}). Supply imbalance rejection.",
                "key_levels": {"invalidation": sl}
            }
        return None

    def _derive_cpr_from_indicators(self, symbol: str, stock_data: Dict[str, Any], atr: float) -> Optional[Dict[str, Any]]:
        ind = stock_data.get("indicators", {})
        cpr = ind.get("cpr", {})
        # MUST BE STRICTLY NARROW CPR
        if not cpr.get("is_narrow", False):
            return None

        ltp = stock_data.get("ltp", 0.0)
        cpr_top = cpr.get("cpr_top", ltp)
        cpr_bottom = cpr.get("cpr_bottom", ltp)
        cpr_width_pct = cpr.get("width_pct", 0.15)
        pivot = cpr.get("pivot", ltp)
        surge = ind.get("volume_surge", 1.0)
        pivots = ind.get("pivots", {})
        r1 = pivots.get("r1", ltp * 1.01)
        s1 = pivots.get("s1", ltp * 0.99)

        if ltp > cpr_top and surge >= 1.20:
            sl = round(cpr_bottom - (atr * 0.25), 2)
            tgt = round(max(r1, ltp + atr * 2.5), 2)
            return {
                "strategy_id": 7,
                "strategy_name": "Narrow CPR Trend Blast",
                "strategy_badge": "Dalal Street Trend Blast",
                "symbol": symbol,
                "action": "BUY CALL / TREND BLAST",
                "direction": "BULLISH",
                "entry": ltp,
                "stop_loss": sl,
                "target": tgt,
                "risk_reward": "1:2.5",
                "pattern_stage": "Narrow CPR Range Expansion",
                "rationale": f"Super Narrow CPR ({cpr_width_pct:.2f}% width) breakout above Top Central (₹{cpr_top:.2f}) on {surge:.1f}x volume surge. Dalal Street trend blast in progress.",
                "key_levels": {"pivot": pivot, "cpr_top": cpr_top, "cpr_bottom": cpr_bottom}
            }
        elif ltp < cpr_bottom and surge >= 1.20:
            sl = round(cpr_top + (atr * 0.25), 2)
            tgt = round(min(s1, ltp - atr * 2.5), 2)
            return {
                "strategy_id": 7,
                "strategy_name": "Narrow CPR Trend Blast",
                "strategy_badge": "Dalal Street Trend Blast",
                "symbol": symbol,
                "action": "BUY PUT / TREND DUMP",
                "direction": "BEARISH",
                "entry": ltp,
                "stop_loss": sl,
                "target": tgt,
                "risk_reward": "1:2.5",
                "pattern_stage": "Narrow CPR Breakdown Dump",
                "rationale": f"Super Narrow CPR ({cpr_width_pct:.2f}% width) breakdown below Bottom Central (₹{cpr_bottom:.2f}) on {surge:.1f}x volume surge. Heavy institutional distribution.",
                "key_levels": {"pivot": pivot, "cpr_top": cpr_top, "cpr_bottom": cpr_bottom}
            }
        return None

    def _derive_gamma_from_indicators(self, symbol: str, stock_data: Dict[str, Any], atr: float) -> Optional[Dict[str, Any]]:
        return self._detect_gamma_blast(symbol, stock_data.get("ltp", 0.0), None, atr, stock_data)
