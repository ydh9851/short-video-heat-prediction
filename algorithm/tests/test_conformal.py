# -*- coding: utf-8 -*-
"""保形预测（Split Conformal + Mondrian）的单元测试。

测试原则：用数学定义验证实现，而不是只验证"能跑通"。
这些函数是论文第 10.11 节结论的计算内核，一旦被改错，
系统界面上的覆盖率与区间宽度就会悄悄失真。
"""
import numpy as np
import pytest

import conformal_predict as cp


class TestQhat:
    def test_finite_sample_correction(self):
        """q̂ 的取位必须是 ceil((n+1)(1-α))/n，而不是朴素的 (1-α) 分位。"""
        scores = np.arange(100, dtype=float)
        q = cp._qhat(scores, 0.1)
        expected_level = np.ceil(101 * 0.9) / 100  # = 0.91
        assert expected_level == pytest.approx(0.91)
        assert q == pytest.approx(float(np.quantile(scores, expected_level)))

    def test_higher_confidence_gives_wider_qhat(self):
        """置信水平越高（α 越小），q̂ 应越大 → 区间越宽。"""
        scores = np.random.RandomState(0).rand(500)
        q80 = cp._qhat(scores, 0.2)
        q90 = cp._qhat(scores, 0.1)
        q95 = cp._qhat(scores, 0.05)
        assert q80 < q90 < q95

    def test_empty_scores_gives_infinity(self):
        assert cp._qhat(np.array([]), 0.1) == float("inf")


class TestInterval:
    def test_geometric_symmetry_in_raw_space(self):
        """log 空间对称 → 原始空间几何对称（(lo+1)(hi+1)=(pred+1)^2）。"""
        pred_log = float(np.log1p(100.0))
        q = 0.5
        lo, hi = cp._interval_raw(np.array([pred_log]), q)
        assert lo[0] < 100.0 < hi[0]
        assert (lo[0] + 1.0) * (hi[0] + 1.0) == pytest.approx((100.0 + 1.0) ** 2, rel=1e-9)

    def test_arithmetically_asymmetric(self):
        """原始空间区间是算术不对称的——这正是热度长尾分布应有的形态。"""
        pred_log = float(np.log1p(100.0))
        lo, hi = cp._interval_raw(np.array([pred_log]), 0.5)
        assert (lo[0] + hi[0]) / 2.0 != pytest.approx(100.0, rel=1e-6)

    def test_wider_q_gives_wider_interval(self):
        pred_log = float(np.log1p(100.0))
        lo1, hi1 = cp._interval_raw(np.array([pred_log]), 0.2)
        lo2, hi2 = cp._interval_raw(np.array([pred_log]), 0.8)
        assert (hi2[0] - lo2[0]) > (hi1[0] - lo1[0])


class TestCoverage:
    def test_all_inside(self):
        lo = np.array([0.0, 10.0])
        hi = np.array([20.0, 30.0])
        y = np.array([5.0, 25.0])
        assert cp._coverage(y, lo, hi) == pytest.approx(1.0)

    def test_half_inside(self):
        lo = np.array([0.0, 10.0])
        hi = np.array([20.0, 30.0])
        y = np.array([5.0, 100.0])
        assert cp._coverage(y, lo, hi) == pytest.approx(0.5)

    def test_boundary_counts_as_covered(self):
        """区间是闭区间，端点命中应算覆盖。"""
        assert cp._coverage(np.array([0.0]), np.array([0.0]), np.array([10.0])) == pytest.approx(1.0)
        assert cp._coverage(np.array([10.0]), np.array([0.0]), np.array([10.0])) == pytest.approx(1.0)

    def test_width_stats(self):
        lo = np.array([0.0, 10.0])
        hi = np.array([20.0, 30.0])
        st = cp._width_stats(lo, hi)
        assert st["avg_width"] == pytest.approx(20.0)
        assert st["median_width"] == pytest.approx(20.0)


class TestGradeGroups:
    def test_three_levels(self):
        heats = [100.0, 684.0, 1000.0, 15661.0, 20000.0]
        groups = cp._grade_groups(np.array(heats))
        assert list(groups) == ["低热度", "中热度", "中热度", "高热度", "高热度"]


class TestSplit:
    def test_disjoint_and_ratio(self):
        X = np.arange(100).reshape(100, 1).astype(float)
        y = np.arange(100).astype(float)
        X_fit, y_fit, X_cal, y_cal = cp._split_train_calib(X, y, ratio=0.2, seed=42)
        assert len(X_fit) == 80 and len(X_cal) == 20
        assert len(set(y_fit.tolist()) & set(y_cal.tolist())) == 0

    def test_deterministic_with_same_seed(self):
        X = np.arange(50).reshape(50, 1).astype(float)
        y = np.arange(50).astype(float)
        _, y_fit1, _, y_cal1 = cp._split_train_calib(X, y, seed=7)
        _, y_fit2, _, y_cal2 = cp._split_train_calib(X, y, seed=7)
        assert np.array_equal(y_fit1, y_fit2)
        assert np.array_equal(y_cal1, y_cal2)