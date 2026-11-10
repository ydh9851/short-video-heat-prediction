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

    /**
     * 数据血缘：原始文件 → 规范化数据集 → 数据集版本 → 模型版本。
     *
     * <p>合并 dataset_registry.json、dataset_versions.json 与模型注册表三份元数据，
     * 回答「线上模型用的是哪一版数据」，并给出链路完整性判断。</p>
     */
    JsonNode lineage(String platform);

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

    /**
     * 数据质量门禁：对该平台规范化数据集做 8 项断言（schema / 缺失率 / 负值 / 重复率 /
     * 类别覆盖 / 热度分布 PSI / 时间区间），返回 PASS / WARN / FAIL 与逐项明细。
     */
    JsonNode quality(String platform);
}
