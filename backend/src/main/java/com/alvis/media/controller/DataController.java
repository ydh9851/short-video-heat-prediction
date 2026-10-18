package com.alvis.media.controller;

import com.alvis.media.base.BaseApiController;
import com.alvis.media.base.RestResponse;
import com.alvis.media.service.DataService;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.AllArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 数据管理接口：规范化数据集的总览统计与样本预览
 */
@RestController("DataController")
@RequestMapping(value = "/api/data")
@AllArgsConstructor
public class DataController extends BaseApiController {

    private final DataService dataService;

    /** 数据集总览 */
    @GetMapping("/overview")
    public RestResponse<JsonNode> overview() {
        return RestResponse.ok(dataService.overview());
    }

    /** 样本分页预览（可按类别筛选） */
    @GetMapping("/samples")
    public RestResponse<JsonNode> samples(
            @RequestParam(value = "page", defaultValue = "1") int page,
            @RequestParam(value = "size", defaultValue = "20") int size,
            @RequestParam(value = "category", required = false) String category) {
        return RestResponse.ok(dataService.samples(page, size, category));
    }
}
