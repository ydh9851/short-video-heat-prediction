package com.alvis.media.controller;

import io.swagger.v3.oas.annotations.tags.Tag;
import com.alvis.media.base.BaseApiController;
import com.alvis.media.base.RestResponse;
import com.alvis.media.service.DataService;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.AllArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/**
 * 数据管理接口：多平台规范化数据集的总览统计、样本预览与导入。
 *
 * <p>platform 取值：douyin（抖音）/ youtube / tiktok / bilibili（哔哩哔哩）。
 * 缺省时使用数据集注册表中的 defaultPlatform。</p>
 */
@RestController("DataController")
@Tag(name = "数据治理")
@RequestMapping(value = "/api/data")
@AllArgsConstructor
public class DataController extends BaseApiController {

    private final DataService dataService;

    /** 数据集注册表：已导入的平台与元信息 */
    @GetMapping("/platforms")
    public RestResponse<JsonNode> platforms() {
        return RestResponse.ok(dataService.platforms());
    }

    /** 数据集总览 */
    @GetMapping("/overview")
    public RestResponse<JsonNode> overview(
            @RequestParam(value = "platform", required = false) String platform) {
        return RestResponse.ok(dataService.overview(resolve(platform)));
    }

    /** 样本分页预览（可按类别筛选、按视频 ID 模糊检索） */
    @GetMapping("/samples")
    public RestResponse<JsonNode> samples(
            @RequestParam(value = "platform", required = false) String platform,
            @RequestParam(value = "page", defaultValue = "1") int page,
            @RequestParam(value = "size", defaultValue = "20") int size,
            @RequestParam(value = "category", required = false) String category,
            @RequestParam(value = "keyword", required = false) String keyword) {
        return RestResponse.ok(dataService.samples(resolve(platform), page, size, category, keyword));
    }

    /** 触发某平台原始数据导入（读取 data/raw 下对应文件，调用 Python ingest.py 归一化） */
    @PostMapping("/import")
    public RestResponse<JsonNode> importDataset(
            @RequestParam(value = "platform") String platform) {
        return RestResponse.ok(dataService.importPlatform(platform));
    }

    /** 上传原始数据文件到 data/raw（自动补平台前缀，保证导入时能被自动识别） */
    @PostMapping("/upload")
    public RestResponse<JsonNode> upload(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "platform") String platform) {
        return RestResponse.ok(dataService.upload(file, platform));
    }

    /** data/raw 下已存在的原始数据文件清单（体积、更新时间、可识别平台） */
    @GetMapping("/raw-files")
    public RestResponse<JsonNode> rawFiles() {
        return RestResponse.ok(dataService.rawFiles());
    }

    /** 数据质量门禁：8 项断言，返回 PASS / WARN / FAIL 与逐项明细 */
    @GetMapping("/quality")
    public RestResponse<JsonNode> quality(
            @RequestParam(value = "platform", required = false) String platform) {
        return RestResponse.ok(dataService.quality(resolve(platform)));
    }

    /** 未显式传平台时用注册表默认平台，保持旧接口调用方式兼容 */
    private String resolve(String platform) {
        if (platform != null && !platform.trim().isEmpty()) {
            return platform.trim();
        }
        JsonNode reg = dataService.platforms();
        return reg.path("defaultPlatform").asText("douyin");
    }
}
