package com.alvis.media.service.impl;

import com.alvis.media.service.ModelRegistryService;
import com.alvis.media.utility.PythonGateway;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.Mockito;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.when;

/**
 * 数据血缘核心逻辑单元测试：
 * 当前版本标记、模型 dataVersion 关联判断、原始文件缺失时链路不完整、非法平台拦截。
 */
class DataServiceImplTest {

    @TempDir
    Path tempDir;

    private final ObjectMapper om = new ObjectMapper();

    /** 构造服务：写注册表/版本清单/文件，模型注册表用 Mock 返回。 */
    private DataServiceImpl service(boolean rawExists, String modelDataVersion) throws IOException {
        Path rawDir = tempDir.resolve("raw");
        Files.createDirectories(rawDir);
        Files.writeString(tempDir.resolve("douyin_clean.csv"), "video_id\n1\n");
        if (rawExists) {
            Files.writeString(rawDir.resolve("douyin_video_data.xlsx"), "raw");
        }

        ObjectNode registryJson = om.createObjectNode();
        registryJson.put("defaultPlatform", "douyin");
        registryJson.put("updatedAt", "2026-10-20 10:52:36");
        ObjectNode ds = registryJson.putObject("datasets").putObject("douyin");
        ds.put("rawFile", "data/raw/douyin_video_data.xlsx");
        ds.put("processedFile", "data/processed/douyin_clean.csv");
        ds.put("rows", 45476);
        ds.put("categoryCount", 14);
        ds.put("timeStart", "2025-09-01");
        ds.put("timeEnd", "2025-12-26");
        Files.writeString(tempDir.resolve("dataset_registry.json"),
                om.writerWithDefaultPrettyPrinter().writeValueAsString(registryJson));

        ObjectNode versionsJson = om.createObjectNode();
        ArrayNode list = versionsJson.putObject("datasets").putArray("douyin");
        list.addObject().put("version", "v1").put("fingerprint", "aaaaaaaaaaaa")
                .put("file", "douyin_clean.csv").put("rows", 100)
                .put("registered_at", "2026-11-01 00:00:00");
        list.addObject().put("version", "v2").put("fingerprint", "bbbbbbbbbbbb")
                .put("file", "train_clean.csv").put("rows", 200)
                .put("registered_at", "2026-11-02 00:00:00");
        Files.writeString(tempDir.resolve("dataset_versions.json"),
                om.writerWithDefaultPrettyPrinter().writeValueAsString(versionsJson));

        ObjectNode modelRegistry = om.createObjectNode();
        ObjectNode lgbm = modelRegistry.putObject("models").putObject("lgbm");
        lgbm.put("active", "v4");
        ObjectNode v4 = lgbm.putArray("versions").addObject();
        v4.put("version", "v4");
        v4.put("featureVersion", 4);
        v4.put("dataVersion", modelDataVersion);
        v4.put("r2", 0.81);
        v4.put("mae", 0.65);
        v4.put("rmse", 0.97);
        v4.put("trainedAt", "2026-11-09 04:19:36");

        ModelRegistryService registry = Mockito.mock(ModelRegistryService.class);
        when(registry.read()).thenReturn(modelRegistry);
        when(registry.activeVersionMeta("lgbm")).thenReturn(v4);

        DataServiceImpl service = new DataServiceImpl(Mockito.mock(PythonGateway.class), registry);
        ReflectionTestUtils.setField(service, "processedPath", tempDir.resolve("train_clean.csv").toString());
        ReflectionTestUtils.setField(service, "processedDir", tempDir.toString());
        ReflectionTestUtils.setField(service, "registryPath", tempDir.resolve("dataset_registry.json").toString());
        ReflectionTestUtils.setField(service, "versionsPath", tempDir.resolve("dataset_versions.json").toString());
        ReflectionTestUtils.setField(service, "rawDir", rawDir.toString());
        return service;
    }

    @Test
    void lineageMarksLatestVersionAsCurrent() throws IOException {
        JsonNode line = service(true, "v2").lineage("douyin");

        assertEquals("v2", line.path("currentVersion").asText());
        assertEquals(2, line.path("versions").size());

        JsonNode first = line.path("versions").get(0);
        assertFalse(first.path("current").asBoolean());
        assertTrue(first.path("matchesProcessed").asBoolean());
        assertTrue(first.path("exists").asBoolean());

        JsonNode last = line.path("versions").get(1);
        assertTrue(last.path("current").asBoolean());
        assertFalse(last.path("matchesProcessed").asBoolean());
        assertFalse(last.path("exists").asBoolean());
    }

    @Test
    void lineageLinksModelsWhoseDataVersionMatchesCurrent() throws IOException {
        JsonNode line = service(true, "v2").lineage("douyin");

        JsonNode model = line.path("models").get(0);
        assertEquals("lgbm", model.path("model").asText());
        assertTrue(model.path("dataLinked").asBoolean());
        assertTrue(model.path("loadable").asBoolean());
        assertEquals(1, line.path("summary").path("linkedModelCount").asInt());
        assertTrue(line.path("summary").path("chainComplete").asBoolean());

        JsonNode stale = service(true, "v1").lineage("douyin");
        assertFalse(stale.path("models").get(0).path("dataLinked").asBoolean());
        assertEquals(0, stale.path("summary").path("linkedModelCount").asInt());
        assertFalse(stale.path("summary").path("chainComplete").asBoolean());
    }

    @Test
    void lineageReportsMissingRawFile() throws IOException {
        JsonNode line = service(false, "v2").lineage("douyin");

        assertFalse(line.path("raw").path("exists").asBoolean());
        assertTrue(line.path("processed").path("exists").asBoolean());
        assertFalse(line.path("summary").path("rawExists").asBoolean());
        assertFalse(line.path("summary").path("chainComplete").asBoolean());
    }

    @Test
    void lineageRejectsUnsupportedPlatform() throws IOException {
        DataServiceImpl service = service(true, "v2");
        assertThrows(IllegalArgumentException.class, () -> service.lineage("weibo"));
    }
}
