package com.alvis.media.service;

import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.web.multipart.MultipartFile;

/**
 * 数据管理服务：读取各平台规范化数据集，提供数据集注册表、总览统计与样本分页预览。
 *
 * <p>支持多平台（抖音 / YouTube / TikTok / B 站）：由 algorithm/datasets/ingest.py
 * 归一化为 data/processed/&lt;platform&gt;_clean.csv，并登记到 dataset_registry.json。</p>
 */
public interface DataService {

    /** 数据集注册表：已导入的平台及其元信息（样本量、类别数、时间跨度、热度分位等） */
    JsonNode platforms();

    /** 数据集总览：样本量、类别分布、热度分位、时间跨度、等级分布等 */
    JsonNode overview(String platform);

    /** 样本分页预览（可按类别筛选、按视频 ID 模糊检索） */
    JsonNode samples(String platform, int page, int size, String category, String keyword);

    /** 触发某平台原始数据的导入（调用 Python ingest.py），返回导入结果 */
    JsonNode importPlatform(String platform);

    /**
     * 上传原始数据文件到 data/raw。
     *
     * <p>文件名会自动补上平台前缀（如 {@code youtube_xxx.csv}），保证 ingest.py 的关键字
     * 自动识别能匹配到该文件，避免用户改名后导入失败。
     */
    JsonNode upload(MultipartFile file, String platform);

    /** data/raw 下已存在的原始数据文件清单（含体积、更新时间、可识别的平台） */
    JsonNode rawFiles();
}
