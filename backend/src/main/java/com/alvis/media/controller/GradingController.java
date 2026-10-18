package com.alvis.media.controller;

import com.alvis.media.base.BaseApiController;
import com.alvis.media.base.RestResponse;
import com.alvis.media.service.GradingService;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.AllArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 热度分级接口（K-Means 聚类定等级 + 分类模型预测等级）
 */
@RestController("GradingController")
@RequestMapping(value = "/api/grade")
@AllArgsConstructor
public class GradingController extends BaseApiController {

    private final GradingService gradingService;

    @GetMapping
    public RestResponse<JsonNode> grade(@RequestParam(value = "k", defaultValue = "3") int k) {
        return RestResponse.ok(gradingService.grade(k));
    }
}
