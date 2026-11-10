package com.alvis.media.service;

import com.alvis.media.utility.PythonCliRunner;
import com.alvis.media.utility.PythonGateway;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;

/**
 * 模型注册表（参考 MLflow Model Registry 的版本 + 阶段概念，落盘为 JSON）。
 *
 * <p>为什么不建表：模型元数据天然是「低频变更 + 需要人读」的数据，
 * JSON 文件便于直接查看、diff 和纳管；单机毕设场景无并发写入压力。
 *
 * <p>版本号由 Python 侧按「特征版本 + 缓存文件时间戳」生成，
 * 因此特征工程一变、模型一重训，版本必然不同，无法出现"版本没变但内容变了"的脏状态。
 */
@Service
public class ModelRegistryService {

    private static final Logger log = LoggerFactory.getLogger(ModelRegistryService.class);

    private static final String PRODUCTION = "production";
    private static final String ARCHIVED = "archived";
    private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @Value("${system.data.registryFile:../data/models/model_registry.json}")
    private String registryFile;

    @Value("${system.python.registryScript:../algorithm/prediction/registry.py}")
    private String registryScript;

    private final PythonGateway gateway;
    private final ObjectMapper om = new ObjectMapper();

    public ModelRegistryService(PythonGateway gateway) {
        this.gateway = gateway;
    }

    /** 扫描 model_cache 并刷新注册表，返回摘要。 */
    public JsonNode sync() {
        String out = gateway.runCli(registryScript, List.of("--sync"), 180);
        return parse(PythonCliRunner.lastJsonLine(out));
    }

    /** 读取当前注册表摘要（不触发扫描）。 */
    public JsonNode list() {
        String out = gateway.runCli(registryScript, List.of("--list"), 120);
        return parse(PythonCliRunner.lastJsonLine(out));
    }

    /** 把指定版本切为线上版本，其余版本归档。 */
    public JsonNode promote(String model, String version) {
        ObjectNode root = read();
        if (root == null) {
            throw new IllegalStateException("注册表不存在，请先执行同步");
        }
        ObjectNode entry = (ObjectNode) root.path("models").get(model);
        if (entry == null) {
            throw new IllegalArgumentException("未知模型：" + model);
        }
        ArrayNode versions = (ArrayNode) entry.path("versions");
        boolean hit = false;
        for (JsonNode v : versions) {
            if (version.equals(v.path("version").asText())) {
                hit = true;
                break;
            }
        }
        if (!hit) {
            throw new IllegalArgumentException("模型 " + model + " 不存在版本 " + version);
        }
        // 只有归档文件真实存在，切线上才有意义；否则注册表会指向一个无法加载的版本
        if (!artifactExists(model, entry, version)) {
            throw new IllegalArgumentException("版本 " + version + " 缺少归档文件，无法上线（请先同步或重新训练）");
        }
        // 特征体系升级后旧权重无法被当前代码加载，禁止上线
        JsonNode target = findVersion(entry, version);
        JsonNode currentFv = root.get("featureVersion");
        if (currentFv != null && target != null && target.hasNonNull("featureVersion")
                && currentFv.asInt() != target.path("featureVersion").asInt()) {
            throw new IllegalArgumentException("版本 " + version + " 的特征体系（v"
                    + target.path("featureVersion").asText() + "）与当前代码（v"
                    + currentFv.asText() + "）不一致，请重新训练后再上线");
        }
        for (JsonNode v : versions) {
            ObjectNode vo = (ObjectNode) v;
            if (version.equals(vo.path("version").asText())) {
                vo.put("stage", PRODUCTION);
            } else if (PRODUCTION.equals(vo.path("stage").asText())) {
                vo.put("stage", ARCHIVED);
            }
        }
        entry.put("active", version);
        root.put("updatedAt", LocalDateTime.now().format(TIME));
        write(root);
        log.info("模型版本切换：{} -> {}", model, version);
        return root;
    }

    /** 回滚到最近一个可加载（归档文件存在）的非当前版本。 */
    public JsonNode rollback(String model) {
        ObjectNode root = read();
        if (root == null) {
            throw new IllegalStateException("注册表不存在，请先执行同步");
        }
        ObjectNode entry = (ObjectNode) root.path("models").get(model);
        if (entry == null) {
            throw new IllegalArgumentException("未知模型：" + model);
        }
        String active = entry.path("active").asText();
        ArrayNode versions = (ArrayNode) entry.path("versions");
        String target = null;
        for (int i = versions.size() - 1; i >= 0; i--) {
            String v = versions.get(i).path("version").asText();
            // 跳过当前版本和已丢失归档的历史版本，避免回滚后线上模型加载失败
            if (!v.equals(active) && artifactExists(model, entry, v)) {
                target = v;
                break;
            }
        }
        if (target == null) {
            throw new IllegalStateException("模型 " + model + " 没有可回滚的历史版本（归档文件缺失或仅一个版本）");
        }
        return promote(model, target);
    }

    /**
     * 指定模型的当前线上版本条目（含 dataVersion / featureVersion 等元数据）：
     * 注册表 active 指向的版本且归档文件存在、特征版本一致时返回，否则返回 null。
     * 报告中心据此做「生成时模型/数据版本」快照。
     */
    public JsonNode activeVersionMeta(String model) {
        ObjectNode root = read();
        if (root == null) {
            return null;
        }
        JsonNode entry = root.path("models").get(model);
        if (entry == null) {
            return null;
        }
        String active = entry.path("active").asText(null);
        if (active == null || active.isEmpty()) {
            return null;
        }
        if (!artifactExists(model, entry, active)) {
            return null;
        }
        // 注册表顶层记录了最近一次同步/训练的特征版本；与目标版本不一致则视为不可加载
        JsonNode currentFv = root.get("featureVersion");
        JsonNode item = findVersion(entry, active);
        if (currentFv != null && item != null && item.hasNonNull("featureVersion")
                && currentFv.asInt() != item.path("featureVersion").asInt()) {
            return null;
        }
        return item;
    }

    /**
     * 指定模型的当前线上版本：注册表 active 指向的版本且有归档文件时返回，否则返回 null。
     * 预测服务据此决定加载哪个版本、以及缓存 key 的版本维度。
     */
    public String activeVersion(String model) {
        JsonNode item = activeVersionMeta(model);
        return item == null ? null : item.path("version").asText(null);
    }

    /** 在模型的版本列表中查找指定版本条目。 */
    private JsonNode findVersion(JsonNode entry, String version) {
        for (JsonNode v : entry.path("versions")) {
            if (version.equals(v.path("version").asText())) {
                return v;
            }
        }
        return null;
    }

    /** 版本归档文件是否存在（artifact 字段相对 data/models，缺省为 versions/<model>/<version>.joblib）。 */
    private boolean artifactExists(String model, JsonNode entry, String version) {
        JsonNode item = findVersion(entry, version);
        String rel = item == null ? null : item.path("artifact").asText(null);
        Path base = Paths.get(registryFile).toAbsolutePath().normalize().getParent();
        Path artifact = (rel != null && !rel.isEmpty())
                ? base.resolve(rel)
                : base.resolve("versions").resolve(model).resolve(version + ".joblib");
        return Files.isRegularFile(artifact);
    }

    /** 读取注册表原文（供其它服务使用）。 */
    public ObjectNode read() {
        try {
            Path path = Paths.get(registryFile).toAbsolutePath().normalize();
            if (!Files.isRegularFile(path)) {
                return null;
            }
            JsonNode node = om.readTree(Files.readString(path, StandardCharsets.UTF_8));
            return node instanceof ObjectNode ? (ObjectNode) node : null;
        } catch (IOException e) {
            throw new RuntimeException("读取模型注册表失败：" + e.getMessage(), e);
        }
    }

    private void write(ObjectNode root) {
        try {
            Path path = Paths.get(registryFile).toAbsolutePath().normalize();
            Files.createDirectories(path.getParent());
            // 先写临时文件再原子替换：避免进程中断留下半截 JSON，导致注册表整体不可读
            Path tmp = path.resolveSibling(path.getFileName() + ".tmp");
            Files.writeString(tmp, om.writerWithDefaultPrettyPrinter().writeValueAsString(root),
                    StandardCharsets.UTF_8);
            Files.move(tmp, path, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            throw new RuntimeException("写入模型注册表失败：" + e.getMessage(), e);
        }
    }

    private JsonNode parse(String json) {
        try {
            JsonNode node = om.readTree(json);
            if (node.hasNonNull("error")) {
                throw new RuntimeException(node.path("error").asText());
            }
            return node;
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("解析模型注册表输出失败：" + e.getMessage(), e);
        }
    }
}
