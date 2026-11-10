package com.alvis.media.service.impl;

import com.alvis.media.domain.RehearsalReport;
import com.alvis.media.exception.BusinessException;
import com.alvis.media.repository.RehearsalReportMapper;
import com.alvis.media.service.JobService;
import com.alvis.media.service.ModelRegistryService;
import com.alvis.media.utility.PythonGateway;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.data.redis.core.StringRedisTemplate;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

/**
 * 上线预演门禁（requirePassed）单元测试：
 * 未预演 / 预演未通过 / 预演基于旧线上版本 三种场景必须拦截 promote，
 * 只有「通过且基于当前线上版本」的报告才放行。
 */
class RehearsalServiceImplTest {

    private final RehearsalReportMapper mapper = Mockito.mock(RehearsalReportMapper.class);
    private final ModelRegistryService registry = Mockito.mock(ModelRegistryService.class);

    private RehearsalServiceImpl service() {
        return new RehearsalServiceImpl(
                Mockito.mock(JobService.class), mapper, registry,
                Mockito.mock(PythonGateway.class), Mockito.mock(StringRedisTemplate.class));
    }

    private RehearsalReport report(boolean passed, String activeVersion) {
        RehearsalReport r = new RehearsalReport();
        r.setModel("lgbm");
        r.setCandidateVersion("v4-b");
        r.setActiveVersion(activeVersion);
        r.setPassed(passed);
        r.setMeanAbsDiffPct(passed ? 2.0 : 50.0);
        r.setPearsonCorr(0.99);
        r.setTop10Overlap(0.9);
        return r;
    }

    @Test
    void requirePassed_rejectsWhenNoReport() {
        when(mapper.selectOne(any())).thenReturn(null);
        BusinessException e = assertThrows(BusinessException.class,
                () -> service().requirePassed("lgbm", "v4-b"));
        assertEquals(409, e.getCode());
        assertTrue(e.getMessage().contains("尚未进行上线预演"), "实际: " + e.getMessage());
    }

    @Test
    void requirePassed_rejectsWhenNotPassed() {
        when(mapper.selectOne(any())).thenReturn(report(false, "v4-a"));
        BusinessException e = assertThrows(BusinessException.class,
                () -> service().requirePassed("lgbm", "v4-b"));
        assertEquals(409, e.getCode());
        assertTrue(e.getMessage().contains("预演未通过"), "实际: " + e.getMessage());
    }

    @Test
    void requirePassed_rejectsWhenActiveChanged() {
        when(mapper.selectOne(any())).thenReturn(report(true, "v4-old"));
        when(registry.activeVersion("lgbm")).thenReturn("v4-new");
        BusinessException e = assertThrows(BusinessException.class,
                () -> service().requirePassed("lgbm", "v4-b"));
        assertEquals(409, e.getCode());
        assertTrue(e.getMessage().contains("预演结果失效"), "实际: " + e.getMessage());
    }

    @Test
    void requirePassed_allowsWhenPassedAndActiveMatches() {
        when(mapper.selectOne(any())).thenReturn(report(true, "v4-a"));
        when(registry.activeVersion("lgbm")).thenReturn("v4-a");
        assertDoesNotThrow(() -> service().requirePassed("lgbm", "v4-b"));
    }
}
