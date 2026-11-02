package com.alvis.media.service;

import com.alvis.media.utility.PythonCliRunner;
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
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
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

    private final PythonCliRunner runner;
    private final ObjectMapper om = new ObjectMapper();

    public ModelRegistryService(PythonCliRunner runner) {
        this.runner = runner;
    }

    /** 扫描 model_cache 并刷新注册表，返回摘要。 */
    public JsonNode sync() {
        String out = runner.run(registryScript, List.of("--sync"), 180);
        return parse(PythonCliRunner.lastJsonLine(out));
    }

    /** 读取当前注册表摘要（不触发扫描）。 */
    public JsonNode list() {
        String out = runner.run(registryScript, List.of("--list"), 120);
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
            ObjectNode vo = (ObjectNode) v;
            if (version.equals(vo.path("version").asText())) {
                vo.put("stage", PRODUCTION);
                hit = true;
            } else if (PRODUCTION.equals(vo.path("stage").asText())) {
                vo.put("stage", ARCHIVED);
            }
        }
        if (!hit) {
            throw new IllegalArgumentException("模型 " + model + " 不存在版本 " + version);
        }
        entry.put("active", version);
        root.put("updatedAt", LocalDateTime.now().format(TIME));
        write(root);
        log.info("模型版本切换：{} -> {}", model, version);
        return root;
    }

    /** 回滚到上一个归档版本（按训练时间倒序找最近的非当前版本）。 */
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
            if (!v.equals(active)) {
                target = v;
                break;
            }
        }
        if (target == null) {
            throw new IllegalStateException("模型 " + model + " 只有一个版本，无法回滚");
        }
        return promote(model, target);
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
            Files.writeString(path, om.writerWithDefaultPrettyPrinter().writeValueAsString(root),
                    StandardCharsets.UTF_8);
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
