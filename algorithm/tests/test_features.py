# -*- coding: utf-8 -*-
"""特征工程与分级规则的单元测试：时段分桶、热度分级、ISO 8601 时长解析。"""
import pytest

import predict_api as P
from feature_enrichment import _iso_duration


class TestHourBucket:
    @pytest.mark.parametrize("hour,expected", [
        (0, "凌晨(0-5)"),
        (5, "凌晨(0-5)"),
        (6, "上午(6-11)"),
        (11, "上午(6-11)"),
        (12, "下午(12-17)"),
        (17, "下午(12-17)"),
        (18, "晚间(18-23)"),
        (23, "晚间(18-23)"),
    ])
    def test_bucket_boundaries(self, hour, expected):
        """时段分桶的边界必须严格按 [0,6) [6,12) [12,18) [18,24) 划分。"""
        assert P._hour_bucket(hour) == expected

    def test_bucket_accepts_string_input(self):
        """前端可能传字符串小时，不应抛异常。"""
        assert P._hour_bucket("20") == "晚间(18-23)"


class TestGradeOf:
    @pytest.mark.parametrize("heat,expected", [
        (0.0, "低热度"),
        (683.9, "低热度"),
        (684.0, "中热度"),
        (15660.0, "中热度"),
        (15661.0, "高热度"),
        (999999.0, "高热度"),
    ])
    def test_thresholds(self, heat, expected):
        """分级阈值为 684 与 15661，左闭右开。"""
        assert P.grade_of(heat) == expected


class TestIsoDuration:
    def test_full_duration(self):
        assert _iso_duration("PT1H2M3S") == 3723

    def test_minutes_only(self):
        assert _iso_duration("PT5M") == 300

    def test_hours_only(self):
        assert _iso_duration("PT2H") == 7200

    def test_invalid_returns_minus_one(self):
        """非法输入返回 -1（表示"缺失"），而不是抛异常中断整列解析。"""
        assert _iso_duration("") == -1
        assert _iso_duration(None) == -1
        assert _iso_duration("1H30M") == -1
        assert _iso_duration("PTH") == -1