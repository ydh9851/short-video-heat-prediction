package com.alvis.media.service.impl;

import com.alvis.media.context.WebContext;
import com.alvis.media.domain.Case;
import com.alvis.media.domain.Report;
import com.alvis.media.domain.User;
import com.alvis.media.exception.BusinessException;
import com.alvis.media.repository.ReportMapper;
import com.alvis.media.service.CaseService;
import com.alvis.media.service.JobService;
import com.alvis.media.service.ModelRegistryService;
import com.alvis.media.utility.PythonGateway;
import com.alvis.media.viewmodel.report.ReportGenerateRequestVM;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mockito;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 报告中心核心逻辑单元测试：
 * 版本快照固化、场景不存在拦截、分享 token 生成与复用、非 DONE 不可分享访问、归属隔离。
 */
class ReportServiceImplTest {

    private final ReportMapper mapper = Mockito.mock(ReportMapper.class);
    private final CaseService caseService = Mockito.mock(CaseService.class);
    private final JobService jobService = Mockito.mock(JobService.class);
    private final ModelRegistryService registry = Mockito.mock(ModelRegistryService.class);
    private final WebContext webContext = Mockito.mock(WebContext.class);
    private final ObjectMapper om = new ObjectMapper();

    private ReportServiceImpl service() {
        return new ReportServiceImpl(mapper, caseService, jobService, registry,
                Mockito.mock(PythonGateway.class), webContext);
    }

    private User user(int id) {
        User u = new User();
        u.setId(id);
        u.setUserName("user" + id);
        u.setRole(1); // 普通用户（非管理员）
        return u;
    }

    private Case sampleCase() {
        Case c = new Case();
        c.setId(7L);
        c.setName("美食大号周五晚8点");
        c.setModel("lgbm");
        c.setVideoCategory("美食");
        c.setAuthorFans(50000.0);
        c.setPublishHour(20);
        c.setPublishWeekday(4);
        c.setPublishMonth(9);
        c.setUserId(1);
        return c;
    }

    @Test
    void generate_withCase_createsRowWithVersionSnapshot() throws Exception {
        when(webContext.getCurrentUser()).thenReturn(user(1));
        when(caseService.getOwn(7L)).thenReturn(sampleCase());
        ObjectNode meta = om.createObjectNode();
        meta.put("version", "v4-20261109_041936_208829");
        meta.put("dataVersion", "v20261104-010645-414489");
        meta.put("featureVersion", 4);
        when(registry.activeVersionMeta("lgbm")).thenReturn(meta);
        when(jobService.submit(eq("report.generate"), anyMap())).thenReturn(99L);

        ReportGenerateRequestVM vm = new ReportGenerateRequestVM();
        vm.setCaseId(7L);
        ObjectNode result = service().generate(vm);

        ArgumentCaptor<Report> captor = ArgumentCaptor.forClass(Report.class);
        verify(mapper).insert(captor.capture());
        Report saved = captor.getValue();
        assertEquals("GENERATING", saved.getStatus());
        assertEquals(7L, saved.getCaseId());
        assertEquals("美食大号周五晚8点", saved.getCaseName());
        assertEquals("v4-20261109_041936_208829", saved.getModelVersion());
        assertEquals("v20261104-010645-414489", saved.getDataVersion());
        assertEquals(4, saved.getFeatureVersion());
        assertEquals(1, saved.getUserId());
        // 场景参数固化为报告参数
        assertTrue(saved.getParams().contains("美食"), "实际: " + saved.getParams());
        assertTrue(saved.getParams().contains("\"hour\":20"), "实际: " + saved.getParams());
        verify(jobService).submit(eq("report.generate"), anyMap());
        assertEquals(99L, result.path("jobId").asLong());
        assertNotNull(result.path("reportId").asLong());
    }

    @Test
    void generate_caseNotFound_throws404() {
        when(webContext.getCurrentUser()).thenReturn(user(1));
        when(caseService.getOwn(404L)).thenReturn(null);
        ReportGenerateRequestVM vm = new ReportGenerateRequestVM();
        vm.setCaseId(404L);
        BusinessException e = assertThrows(BusinessException.class, () -> service().generate(vm));
        assertEquals(404, e.getCode());
        verify(mapper, never()).insert(any(Report.class));
    }

    @Test
    void generate_invalidHour_throws400() {
        when(webContext.getCurrentUser()).thenReturn(user(1));
        ReportGenerateRequestVM vm = new ReportGenerateRequestVM();
        vm.setVideoCategory("美食");
        vm.setPublishHour(25);
        vm.setPublishWeekday(4);
        vm.setPublishMonth(9);
        BusinessException e = assertThrows(BusinessException.class, () -> service().generate(vm));
        assertEquals(400, e.getCode());
        verify(mapper, never()).insert(any(Report.class));
    }

    @Test
    void share_generatesTokenAndReusesOnSecondCall() {
        when(webContext.getCurrentUser()).thenReturn(user(1));
        Report r = new Report();
        r.setId(5L);
        r.setUserId(1);
        r.setStatus("DONE");
        when(mapper.selectById(5L)).thenReturn(r);

        String token1 = service().share(5L);
        assertNotNull(token1);
        assertEquals(32, token1.length());
        verify(mapper).updateById(any(Report.class));

        // 第二次调用：已有 token 直接复用，不再写库
        r.setShareToken(token1);
        Mockito.clearInvocations(mapper);
        String token2 = service().share(5L);
        assertEquals(token1, token2);
        verify(mapper, never()).updateById(any(Report.class));
    }

    @Test
    void share_notDone_throws400() {
        when(webContext.getCurrentUser()).thenReturn(user(1));
        Report r = new Report();
        r.setId(6L);
        r.setUserId(1);
        r.setStatus("GENERATING");
        when(mapper.selectById(6L)).thenReturn(r);
        BusinessException e = assertThrows(BusinessException.class, () -> service().share(6L));
        assertEquals(400, e.getCode());
    }

    @Test
    void getShared_notDone_returnsNull() {
        Report r = new Report();
        r.setId(8L);
        r.setStatus("GENERATING");
        r.setShareToken("abc");
        when(mapper.selectOne(any())).thenReturn(r);
        assertNull(service().getShared("abc"));
    }

    @Test
    void deleteOwn_notOwner_throws404() {
        when(webContext.getCurrentUser()).thenReturn(user(2));
        Report r = new Report();
        r.setId(9L);
        r.setUserId(1); // 属于 user1，当前登录 user2
        when(mapper.selectById(9L)).thenReturn(r);
        BusinessException e = assertThrows(BusinessException.class, () -> service().deleteOwn(9L));
        assertEquals(404, e.getCode());
        verify(mapper, never()).deleteById(any(Long.class));
    }
}
