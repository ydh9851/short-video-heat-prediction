package com.alvis.media.controller;

import com.alvis.media.base.BaseApiController;
import com.alvis.media.base.RestResponse;
import com.alvis.media.service.ModelRegistryService;
import com.alvis.media.service.ShadowService;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.AllArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 模型治理接口：注册表（版本 + 阶段）与影子模式（线上/候选模型并行打分差异）。
 */
@RestController("ModelController")
@RequestMapping(value = "/api/models")
@AllArgsConstructor
public class ModelController extends BaseApiController {

    private final ModelRegistryService registryService;

    private final ShadowService shadowService;

    /** 模型注册表摘要（不触发扫描） */
    @GetMapping
    public RestResponse<JsonNode> list() {
        return RestResponse.ok(registryService.list());
    }

    /** 扫描 model_cache，把新训练的模型登记进注册表（新版本默认 staging） */
    @PostMapping("/sync")
    public RestResponse<JsonNode> sync() {
        return RestResponse.ok(registryService.sync());
    }

    /** 把指定版本切为线上（production），其余归档 */
    @PostMapping("/{model}/promote")
    public RestResponse<JsonNode> promote(@PathVariable("model") String model,
                                          @RequestParam("version") String version) {
        return RestResponse.ok(registryService.promote(model, version));
    }

    /** 回滚到上一个可用版本 */
    @PostMapping("/{model}/rollback")
    public RestResponse<JsonNode> rollback(@PathVariable("model") String model) {
        return RestResponse.ok(registryService.rollback(model));
    }

    /** 影子模式统计：样本数、平均/中位/90 分位绝对偏差、最近记录 */
    @GetMapping("/shadow")
    public RestResponse<JsonNode> shadow(@RequestParam(value = "recent", defaultValue = "10") int recent) {
        return RestResponse.ok(shadowService.stats(recent));
    }
}
