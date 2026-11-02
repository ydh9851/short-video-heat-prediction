# -*- coding: utf-8 -*-
"""数据质量门禁的单元测试：PSI 漂移度量与断言分级。"""
import numpy as np
import pytest

import quality_check as qc


class TestPsi:
    def test_identical_distribution_is_zero(self):
        """基准与实际分布完全一致时 PSI 应为 0。"""
        expected = [0.25, 0.25, 0.25, 0.15, 0.10]
        assert qc._psi(expected, expected) == pytest.approx(0.0, abs=1e-9)

    def test_shift_increases_psi(self):
        """热度分布整体右移时 PSI 必须显著大于 0（漂移能被门禁发现）。"""
        expected = [0.25, 0.25, 0.25, 0.15, 0.10]
        shifted = [0.05, 0.10, 0.20, 0.30, 0.35]
        assert qc._psi(expected, shifted) > 0.25

    def test_zero_bucket_does_not_crash(self):
        """某一桶实际占比为 0 时不能出现 inf / nan（平滑项生效）。"""
        expected = [0.25, 0.25, 0.25, 0.15, 0.10]
        actual = [0.0, 0.25, 0.25, 0.25, 0.25]
        value = qc._psi(expected, actual)
        assert np.isfinite(value)
        assert value >= 0

    def test_monotonic_with_shift_magnitude(self):
        """偏移越大，PSI 越大——保证门禁的严重度分级是有意义的。"""
        expected = [0.25, 0.25, 0.25, 0.15, 0.10]
        mild = [0.20, 0.24, 0.26, 0.17, 0.13]
        severe = [0.02, 0.08, 0.20, 0.30, 0.40]
        assert qc._psi(expected, mild) < qc._psi(expected, severe)

    def test_symmetric_under_swap(self):
        """PSI 是对称的：把基准与实际互换，数值不变。"""
        expected = [0.4, 0.3, 0.2, 0.1]
        actual = [0.1, 0.2, 0.3, 0.4]
        assert qc._psi(expected, actual) == pytest.approx(qc._psi(actual, expected), rel=1e-9)