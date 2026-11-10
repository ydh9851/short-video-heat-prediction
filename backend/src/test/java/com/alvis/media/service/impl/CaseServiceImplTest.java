package com.alvis.media.service.impl;

import com.alvis.media.context.WebContext;
import com.alvis.media.domain.Case;
import com.alvis.media.domain.User;
import com.alvis.media.domain.enums.RoleEnum;
import com.alvis.media.exception.BusinessException;
import com.alvis.media.repository.CaseMapper;
import com.alvis.media.service.PredictService;
import com.alvis.media.viewmodel.predict.PredictRequestVM;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * 场景对比核心逻辑单测：数量校验、字段映射、单列失败降级、不存在场景。
 */
class CaseServiceImplTest {

    private final ObjectMapper om = new ObjectMapper();

    private CaseMapper caseMapper;
    private PredictService predictService;
    private CaseServiceImpl service;

    @BeforeEach
    void setUp() {
        caseMapper = mock(CaseMapper.class);
        WebContext webContext = mock(WebContext.class);
        predictService = mock(PredictService.class);

        User admin = new User();
        admin.setId(1);
        admin.setRole(RoleEnum.ADMIN.getCode());
        when(webContext.getCurrentUser()).thenReturn(admin);

        service = new CaseServiceImpl(caseMapper, webContext, predictService);
    }

    private Case sample(Long id, String name) {
        Case c = new Case();
        c.setId(id);
        c.setName(name);
        c.setModel("lgbm");
        c.setVideoCategory("美食");
        c.setAuthorFans(50000.0);
        c.setPublishHour(20);
        c.setPublishWeekday(5);
        c.setPublishMonth(6);
        return c;
    }

    private ObjectNode interval(double prediction, double lo, double hi, String grade) {
        ObjectNode node = om.createObjectNode();
        node.put("prediction", prediction);
        node.put("lo", lo);
        node.put("hi", hi);
        node.put("grade", grade);
        node.put("alpha", 0.1);
        node.put("target_coverage", 0.9);
        return node;
    }

    @Test
    void compareRejectsWrongSize() {
        BusinessException one = assertThrows(BusinessException.class,
                () -> service.compare(Collections.singletonList(1L)));
        assertEquals(400, one.getCode());

        BusinessException four = assertThrows(BusinessException.class,
                () -> service.compare(Arrays.asList(1L, 2L, 3L, 4L)));
        assertEquals(400, four.getCode());
    }

    @Test
    void compareMapsPredictionFields() {
        when(caseMapper.selectById(1L)).thenReturn(sample(1L, "美食大号"));
        when(caseMapper.selectById(2L)).thenReturn(sample(2L, "宠物小号"));
        when(predictService.interval(any(PredictRequestVM.class)))
                .thenReturn(interval(12345.6, 8000.0, 20000.0, "B"));

        JsonNode result = service.compare(Arrays.asList(1L, 2L));

        assertEquals(1L, result.path("baseId").asLong());
        assertEquals(2, result.path("items").size());
        assertFalse(result.path("generatedAt").asText("").isEmpty());

        JsonNode first = result.path("items").get(0);
        assertEquals("美食大号", first.path("name").asText());
        assertEquals(12345.6, first.path("prediction").asDouble(), 0.001);
        assertEquals(8000.0, first.path("lo").asDouble(), 0.001);
        assertEquals(20000.0, first.path("hi").asDouble(), 0.001);
        assertEquals("B", first.path("grade").asText());
        assertEquals(0.9, first.path("coverage").asDouble(), 0.001);
        assertTrue(first.path("error").isNull());
    }

    @Test
    void compareKeepsOtherColumnsWhenOneFails() {
        when(caseMapper.selectById(1L)).thenReturn(sample(1L, "成功场景"));
        when(caseMapper.selectById(2L)).thenReturn(sample(2L, "失败场景"));
        when(predictService.interval(any(PredictRequestVM.class)))
                .thenReturn(interval(100.0, 50.0, 200.0, "C"))
                .thenThrow(new RuntimeException("boom"));

        JsonNode items = service.compare(Arrays.asList(1L, 2L)).path("items");

        assertEquals(100.0, items.get(0).path("prediction").asDouble(), 0.001);
        assertTrue(items.get(0).path("error").isNull());

        assertTrue(items.get(1).path("prediction").isNull());
        assertEquals("boom", items.get(1).path("error").asText());
        assertEquals("失败场景", items.get(1).path("name").asText());
    }

    @Test
    void compareRejectsMissingCase() {
        when(caseMapper.selectById(1L)).thenReturn(sample(1L, "存在的场景"));
        when(caseMapper.selectById(2L)).thenReturn(null);

        BusinessException e = assertThrows(BusinessException.class,
                () -> service.compare(Arrays.asList(1L, 2L)));
        assertEquals(404, e.getCode());
    }
}
