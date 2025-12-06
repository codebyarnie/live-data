"""
Filter Calculation Logic

Calculates direction and position filters from candle patterns.
Adapted from temp/live_data.py to work with Candle dataclass.
"""

import sys
import os
from typing import List, Dict

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from schemas.market_data import Candle


class CandleScienceFilterCalculator:
    """
    Calculates direction and position filters from candle data.

    Analyzes candle patterns to produce filter settings for dashboards.
    Filters include:
    - Direction filters: Bullish/Bearish for each candle
    - Position filters: Relative placement (Above/Below) of consecutive candles
    """

    @staticmethod
    def analyze_direction(candle: Candle) -> str:
        """
        Determine if candle is bullish or bearish.

        Args:
            candle: Candle object

        Returns:
            "Bullish" or "Bearish"
        """
        return 'Bullish' if candle.close >= candle.open else 'Bearish'

    @staticmethod
    def build_direction_filters(candles: List[Candle]) -> Dict[str, str]:
        """
        Build direction filters from candles.

        Args:
            candles: List of N candles (oldest to newest)

        Returns:
            Dictionary mapping filter keys to values
            Example: {"C1_body_direction": "Bullish", "C2_body_direction": "Bearish"}
        """
        if not candles:
            return {}

        filters = {}
        for idx, candle in enumerate(candles):
            candle_num = idx + 1
            direction_key = f'C{candle_num}_body_direction'
            direction = CandleScienceFilterCalculator.analyze_direction(candle)
            filters[direction_key] = direction

        return filters

    @staticmethod
    def build_position_filters(candles: List[Candle]) -> Dict[str, str]:
        """
        Build position filters from candles.

        Analyzes relationships between consecutive candles:
        - High wick placements
        - Low wick placements
        - Body/close positions relative to previous candle

        Args:
            candles: List of N candles (oldest to newest)

        Returns:
            Dictionary of position filters
            Example: {"C2_high_diff_prev_high": "Above", "C2_low_diff_prev_low": "Below"}
        """
        if not candles or len(candles) < 2:
            return {}

        filters = {}

        # Process each consecutive candle pair
        for idx in range(len(candles) - 1):
            c1 = candles[idx]  # Previous candle
            c2 = candles[idx + 1]  # Current candle

            candle_num = idx + 2  # C2, C3, C4, etc.

            c1_direction = CandleScienceFilterCalculator.analyze_direction(c1)
            c2_direction = CandleScienceFilterCalculator.analyze_direction(c2)

            # Get C1 body boundaries
            if c1_direction == 'Bullish':
                c1_body_top = c1.close
                c1_body_bottom = c1.open
            else:
                c1_body_top = c1.open
                c1_body_bottom = c1.close

            # ========== CASE 1: C1 IS BULLISH ==========
            if c1_direction == 'Bullish':
                if c2_direction == 'Bullish':
                    # Bullish -> Bullish
                    if c2.close > c1.high:
                        filters[f'C{candle_num}_close_diff_prev_high'] = "Above"
                    elif c2.high < c1.high:
                        filters[f'C{candle_num}_high_diff_prev_high'] = "Below"
                    elif c2.high > c1.high:
                        filters[f'C{candle_num}_high_diff_prev_high'] = "Above"
                        filters[f'C{candle_num}_close_diff_prev_high'] = "Below"

                    # Low placement
                    if c2.low < c1.low:
                        filters[f'C{candle_num}_low_diff_prev_low'] = "Below"
                    elif c2.low > c1_body_bottom:
                        filters[f'C{candle_num}_low_diff_prev_open'] = "Above"
                    elif c2.low > c1.low and c2.low < c1_body_bottom:
                        filters[f'C{candle_num}_low_diff_prev_open'] = "Below"
                        filters[f'C{candle_num}_low_diff_prev_low'] = "Above"

                else:
                    # Bullish -> Bearish
                    if c2.close < c1.low:
                        filters[f'C{candle_num}_close_diff_prev_low'] = "Below"
                    elif c2.low > c1_body_bottom:
                        filters[f'C{candle_num}_low_diff_prev_open'] = "Above"
                    elif c2.low > c1.low and c2.low < c1_body_bottom:
                        filters[f'C{candle_num}_low_diff_prev_low'] = "Above"
                        filters[f'C{candle_num}_low_diff_prev_open'] = "Below"

                        if c2.close < c1_body_bottom:
                            filters[f'C{candle_num}_close_diff_prev_open'] = "Below"
                        else:
                            filters[f'C{candle_num}_close_diff_prev_open'] = "Above"

                    # Place high
                    if c2.high > c1.high:
                        filters[f'C{candle_num}_high_diff_prev_high'] = "Above"
                    else:
                        filters[f'C{candle_num}_high_diff_prev_high'] = "Below"

            # ========== CASE 2: C1 IS BEARISH ==========
            elif c1_direction == 'Bearish':
                if c2_direction == 'Bearish':
                    # Bearish -> Bearish
                    if c2.close < c1.low:
                        filters[f'C{candle_num}_close_diff_prev_low'] = "Below"
                    elif c2.low > c1.low:
                        filters[f'C{candle_num}_low_diff_prev_low'] = "Above"
                    elif c2.low < c1.low:
                        filters[f'C{candle_num}_low_diff_prev_low'] = "Below"
                        filters[f'C{candle_num}_close_diff_prev_low'] = "Above"

                    # High placement
                    if c2.high > c1.high:
                        filters[f'C{candle_num}_high_diff_prev_high'] = "Above"
                    elif c2.high < c1_body_top:
                        filters[f'C{candle_num}_high_diff_prev_open'] = "Below"
                    elif c2.high < c1.high and c2.high > c1_body_top:
                        filters[f'C{candle_num}_high_diff_prev_open'] = "Above"
                        filters[f'C{candle_num}_high_diff_prev_high'] = "Below"

                else:
                    # Bearish -> Bullish
                    if c2.close > c1.high:
                        filters[f'C{candle_num}_close_diff_prev_high'] = "Above"
                    elif c2.high < c1_body_top:
                        filters[f'C{candle_num}_high_diff_prev_open'] = "Below"
                    elif c2.high < c1.high and c2.high > c1_body_top:
                        filters[f'C{candle_num}_high_diff_prev_high'] = "Below"
                        filters[f'C{candle_num}_high_diff_prev_open'] = "Above"

                        if c2.close > c1_body_top:
                            filters[f'C{candle_num}_close_diff_prev_open'] = "Above"
                        else:
                            filters[f'C{candle_num}_close_diff_prev_open'] = "Below"

                    # Place low
                    if c2.low < c1.low:
                        filters[f'C{candle_num}_low_diff_prev_low'] = "Below"
                    else:
                        filters[f'C{candle_num}_low_diff_prev_low'] = "Above"

        return filters

    @staticmethod
    def build_all_filters(candles: List[Candle]) -> Dict[str, str]:
        """
        Build complete filter configuration.

        Combines direction and position filters.

        Args:
            candles: List of N candles (oldest to newest)

        Returns:
            Dictionary with all filters
        """
        direction_filters = CandleScienceFilterCalculator.build_direction_filters(candles)
        position_filters = CandleScienceFilterCalculator.build_position_filters(candles)

        # Merge both dictionaries
        return {**direction_filters, **position_filters}
