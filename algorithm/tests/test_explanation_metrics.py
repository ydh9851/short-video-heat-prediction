# -*- coding: utf-8 -*-
"""解释质量评估指标的单元测试：Kendall τ / Spearman / Jaccard / Top-K。

这些指标支撑论文第 10.12 节的"解释是否可信"结论，
实现被改错会直接导致可信度徽章显示错误数值。
"""
import numpy as np
import pytest

import explanation_quality as eq


class TestKendall:
    def test_perfect_agreement(self):
        a = [1.0, 2.0, 3.0, 4.0]
        assert eq._kendall(a, a) == pytest.approx(1.0)

    def test_perfect_reversal(self):
        a = [1.0, 2.0, 3.0, 4.0]
        b = [4.0, 3.0, 2.0, 1.0]
        assert eq._kendall(a, b) == pytest.approx(-1.0)

    def test_constant_input_returns_none(self):
        """常量序列无法定义秩相关，应返回 None 而不是 0 或抛异常。"""
        assert eq._kendall([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None
        assert eq._kendall(None, [1.0]) is None


class TestSpearman:
    def test_monotone_transform_keeps_correlation(self):
        """Spearman 只看秩，单调变换后相关性应保持为 1。"""
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        b = np.exp(a)
        assert eq._spearman(a, b) == pytest.approx(1.0)

    def test_constant_returns_none(self):
        assert eq._spearman([2.0, 2.0, 2.0], [1.0, 2.0, 3.0]) is None


class TestTopKAndJaccard:
    def test_topk_picks_largest_values(self):
        vec = [0.1, 0.9, 0.5, 0.7]
        assert eq._topk_set(vec, 2) == {1, 3}

    def test_jaccard_identical_is_one(self):
        assert eq._jaccard({1, 2, 3}, {1, 2, 3}) == pytest.approx(1.0)

    def test_jaccard_disjoint_is_zero(self):
        assert eq._jaccard({1, 2}, {3, 4}) == pytest.approx(0.0)

    def test_jaccard_partial(self):
        assert eq._jaccard({1, 2}, {2, 3}) == pytest.approx(1.0 / 3.0)

    def test_jaccard_both_empty_is_one(self):
        assert eq._jaccard(set(), set()) == pytest.approx(1.0)