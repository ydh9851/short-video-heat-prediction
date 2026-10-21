package com.alvis.media.service.impl;

import com.alvis.media.service.DataService;
import com.alvis.media.utility.PythonCliRunner;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 数据管理服务实现：
 * <ul>
 *   <li>按平台读取 algorithm/datasets/ingest.py 归一化产出的 data/processed/&lt;platform&gt;_clean.csv；</li>
 *   <li>内存缓存每个平台的数据（首次访问加载，导入后失效重载）；</li>
 *   <li>数据集注册表来自 data/processed/dataset_registry.json。</li>
 * </ul>
 */
@Service
public class DataServiceImpl implements DataService {

    /** 与分级模块一致的热度分级阈值 */
    private static final double GRADE_LOW = 684.0;
    private static final double GRADE_HIGH = 15661.0;

    /** 平台展示名（与 algorithm/datasets/platform_schema.py 保持一致） */
    private static final Map<String, String> PLATFORM_NAMES = Map.of(
            "douyin", "抖音",
            "youtube", "YouTube",
            "tiktok", "TikTok",
            "bilibili", "哔哩哔哩");

    private static final List<String> SUPPORTED = List.of("douyin", "youtube", "tiktok", "bilibili");

    /** 默认规范化数据集（抖音 train_clean.csv），作为注册表缺失时的兜底 */
    @Value("${system.data.processed:../data/processed/train_clean.csv}")
    private String processedPath;

    /** 各平台归一化产物目录 */
    @Value("${system.data.processedDir:../data/processed}")
    private String processedDir;

    /** 数据集注册表 */
    @Value("${system.data.registry:../data/processed/dataset_registry.json}")
    private String registryPath;

    /** 多平台导入脚本 */
    @Value("${system.python.ingestScript:../algorithm/datasets/ingest.py}")
    private String ingestScript;

    private final PythonCliRunner pythonCliRunner;

    /**
     * 只注入算法引擎调用器；其余为 @Value 配置项，走字段注入。
     * （不能用 Lombok @AllArgsConstructor —— 它会把 @Value 的 String 字段也作为构造参数，
     *  Spring 无法为 java.lang.String 找到候选 Bean）
     */
    public DataServiceImpl(PythonCliRunner pythonCliRunner) {
        this.pythonCliRunner = pythonCliRunner;
    }

    private final ObjectMapper om = new ObjectMapper();

    /** 每个平台一份内存缓存 */
    private final Map<String, Cache> cache = new ConcurrentHashMap<>();
    private final Object lock = new Object();

    private static final class Cache {
        final String[] cols;
        final List<String[]> rows;

        Cache(String[] cols, List<String[]> rows) {
            this.cols = cols;
            this.rows = rows;
        }
    }

    // ------------------------------------------------------------------ 注册表
    private JsonNode readRegistry() {
        try {
            File f = new File(registryPath);
            if (!f.isFile()) {
                return null;
            }
            return om.readTree(f);
        } catch (Exception e) {
            return null;
        }
    }

    private String defaultPlatform(JsonNode registry) {
        if (registry != null && registry.hasNonNull("defaultPlatform")) {
            String p = registry.get("defaultPlatform").asText();
            if (SUPPORTED.contains(p)) {
                return p;
            }
        }
        return "douyin";
    }

    /** 平台数据文件路径：优先 <平台>_clean.csv，缺失时若为默认平台则回退到配置的 processed 路径 */
    private File resolveFile(String platform) {
        File f = Paths.get(processedDir, platform + "_clean.csv").toFile();
        if (f.isFile()) {
            return f;
        }
        if (platform.equals(defaultPlatform(readRegistry()))) {
            File fallback = new File(processedPath);
            if (fallback.isFile()) {
                return fallback;
            }
        }
        return null;
    }

    @Override
    public JsonNode platforms() {
        JsonNode registry = readRegistry();
        String def = defaultPlatform(registry);
        ObjectNode root = om.createObjectNode();
        root.put("defaultPlatform", def);

        ArrayNode list = root.putArray("platforms");
        Map<String, JsonNode> imported = new LinkedHashMap<>();
        if (registry != null && registry.has("datasets")) {
            registry.get("datasets").fields().forEachRemaining(e -> imported.put(e.getKey(), e.getValue()));
        }

        // 先输出已导入的平台（保持注册表顺序），再补充未导入但受支持的平台
        List<String> ordered = new ArrayList<>(imported.keySet());
        for (String p : SUPPORTED) {
            if (!ordered.contains(p)) {
                ordered.add(p);
            }
        }

        for (String platform : ordered) {
            JsonNode meta = imported.get(platform);
            ObjectNode o = om.createObjectNode();
            boolean available = resolveFile(platform) != null;
            o.put("platform", platform);
            o.put("displayName", PLATFORM_NAMES.getOrDefault(platform, platform));
            o.put("available", available);
            o.put("isDefault", platform.equals(def));
            if (meta != null) {
                o.setAll((ObjectNode) meta.deepCopy());
            } else {
                o.put("rows", 0);
            }
            list.add(o);
        }
        return root;
    }

    // ------------------------------------------------------------------ 加载
    private Cache ensureLoaded(String platform) {
        Cache c = cache.get(platform);
        if (c != null) {
            return c;
        }
        synchronized (lock) {
            c = cache.get(platform);
            if (c != null) {
                return c;
            }
            File f = resolveFile(platform);
            if (f == null) {
                throw new IllegalStateException(
                        "该平台数据集尚未导入：" + PLATFORM_NAMES.getOrDefault(platform, platform)
                                + "。请把原始数据放入 data/raw 后点击「导入数据集」，"
                                + "或执行 python algorithm/datasets/ingest.py --platform " + platform);
            }
            List<String[]> list = new ArrayList<>();
            String[] header;
            try (BufferedReader br = new BufferedReader(
                    new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8))) {
                String head = br.readLine();
                if (head == null) {
                    header = new String[0];
                } else {
                    if (head.startsWith("\uFEFF")) {   // 去掉 pandas 写出的 UTF-8 BOM
                        head = head.substring(1);
                    }
                    header = head.split(",", -1);
                    String line;
                    while ((line = br.readLine()) != null) {
                        if (line.trim().isEmpty()) {
                            continue;
                        }
                        list.add(line.split(",", -1));
                    }
                }
            } catch (Exception e) {
                throw new RuntimeException("读取数据集失败(" + f.getPath() + "): " + e.getMessage(), e);
            }
            c = new Cache(header, list);
            cache.put(platform, c);
            return c;
        }
    }

    private int idx(String[] cols, String name) {
        for (int i = 0; i < cols.length; i++) {
            if (cols[i].equals(name)) {
                return i;
            }
        }
        return -1;
    }

    private static double d(String s) {
        try {
            return Double.parseDouble(s);
        } catch (Exception e) {
            return Double.NaN;
        }
    }

    private static String grade(double heat) {
        if (heat < GRADE_LOW) {
            return "低热度";
        }
        if (heat < GRADE_HIGH) {
            return "中热度";
        }
        return "高热度";
    }

    private static double quantile(List<Double> sorted, double p) {
        if (sorted.isEmpty()) {
            return 0d;
        }
        int i = (int) Math.floor(p * (sorted.size() - 1));
        i = Math.max(0, Math.min(sorted.size() - 1, i));
        return sorted.get(i);
    }

    private static String val(String[] r, int i) {
        return (i >= 0 && i < r.length) ? r[i] : "";
    }

    // ------------------------------------------------------------------ 总览
    @Override
    public JsonNode overview(String platform) {
        Cache c = ensureLoaded(platform);
        String[] cols = c.cols;
        List<String[]> rows = c.rows;
        int iCat = idx(cols, "video_category"), iHeat = idx(cols, "heat"),
                iFans = idx(cols, "author_fans"), iTime = idx(cols, "publish_time");

        Map<String, Integer> catCount = new LinkedHashMap<>();
        List<Double> heats = new ArrayList<>();
        List<Double> fans = new ArrayList<>();
        int lo = 0, mid = 0, hi = 0;
        String minTime = null, maxTime = null;
        double fansSum = 0, heatSum = 0;

        for (String[] r : rows) {
            catCount.merge(val(r, iCat).isEmpty() ? "未知" : r[iCat], 1, Integer::sum);

            double h = iHeat >= 0 && iHeat < r.length ? d(r[iHeat]) : Double.NaN;
            if (!Double.isNaN(h)) {
                heats.add(h);
                heatSum += h;
                if (h < GRADE_LOW) lo++;
                else if (h < GRADE_HIGH) mid++;
                else hi++;
            }
            double f = iFans >= 0 && iFans < r.length ? d(r[iFans]) : Double.NaN;
            if (!Double.isNaN(f)) {
                fans.add(f);
                fansSum += f;
            }
            if (iTime >= 0 && iTime < r.length) {
                String t = r[iTime];
                if (minTime == null || t.compareTo(minTime) < 0) minTime = t;
                if (maxTime == null || t.compareTo(maxTime) > 0) maxTime = t;
            }
        }
        Collections.sort(heats);
        Collections.sort(fans);

        ObjectNode root = om.createObjectNode();
        root.put("platform", platform);
        root.put("displayName", PLATFORM_NAMES.getOrDefault(platform, platform));
        root.put("total", rows.size());
        root.put("categoryCount", catCount.size());

        ArrayNode cats = root.putArray("categories");
        catCount.entrySet().stream()
                .sorted((a, b) -> b.getValue() - a.getValue())
                .forEach(e -> cats.addObject().put("name", e.getKey()).put("count", e.getValue()));

        ObjectNode h = root.putObject("heat");
        h.put("min", quantile(heats, 0));
        h.put("q1", quantile(heats, 0.25));
        h.put("median", quantile(heats, 0.5));
        h.put("q3", quantile(heats, 0.75));
        h.put("max", heats.isEmpty() ? 0 : heats.get(heats.size() - 1));
        h.put("mean", heats.isEmpty() ? 0 : heatSum / heats.size());

        ObjectNode f = root.putObject("fans");
        f.put("min", quantile(fans, 0));
        f.put("median", quantile(fans, 0.5));
        f.put("max", fans.isEmpty() ? 0 : fans.get(fans.size() - 1));
        f.put("mean", fans.isEmpty() ? 0 : fansSum / fans.size());

        ObjectNode t = root.putObject("publishRange");
        t.put("start", minTime == null ? "" : minTime);
        t.put("end", maxTime == null ? "" : maxTime);

        ArrayNode g = root.putArray("gradeDistribution");
        g.addObject().put("grade", "低热度").put("count", lo);
        g.addObject().put("grade", "中热度").put("count", mid);
        g.addObject().put("grade", "高热度").put("count", hi);
        return root;
    }

    // ------------------------------------------------------------------ 样本
    @Override
    public JsonNode samples(String platform, int page, int size, String category, String keyword) {
        Cache c = ensureLoaded(platform);
        String[] cols = c.cols;
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        if (size > 200) size = 200;

        int iId = idx(cols, "video_id"), iCat = idx(cols, "video_category"),
                iFans = idx(cols, "author_fans"), iTime = idx(cols, "publish_time"),
                iPlay = idx(cols, "play_cnt"), iLike = idx(cols, "like_cnt"),
                iComment = idx(cols, "comment_cnt"), iShare = idx(cols, "share_cnt"),
                iHeat = idx(cols, "heat"), iHeatLog = idx(cols, "heat_log");

        List<String[]> filtered = new ArrayList<>();
        boolean filter = category != null && !category.trim().isEmpty() && !"全部".equals(category);
        String kw = keyword == null ? "" : keyword.trim().toLowerCase();
        for (String[] r : c.rows) {
            if (filter && !category.trim().equals(val(r, iCat))) {
                continue;
            }
            if (!kw.isEmpty() && !val(r, iId).toLowerCase().contains(kw)) {
                continue;
            }
            filtered.add(r);
        }

        int total = filtered.size();
        int from = (page - 1) * size;
        int to = Math.min(from + size, total);

        ObjectNode root = om.createObjectNode();
        root.put("platform", platform);
        root.put("total", total);
        root.put("page", page);
        root.put("size", size);
        ArrayNode list = root.putArray("list");
        for (int i = Math.max(0, from); i < to; i++) {
            String[] r = filtered.get(i);
            double heat = iHeat >= 0 ? d(val(r, iHeat)) : Double.NaN;
            ObjectNode o = list.addObject();
            o.put("videoId", val(r, iId));
            o.put("videoCategory", val(r, iCat));
            o.put("authorFans", d(val(r, iFans)));
            o.put("publishTime", val(r, iTime));
            o.put("playCnt", d(val(r, iPlay)));
            o.put("likeCnt", d(val(r, iLike)));
            o.put("commentCnt", d(val(r, iComment)));
            o.put("shareCnt", d(val(r, iShare)));
            o.put("heat", heat);
            o.put("heatLog", d(val(r, iHeatLog)));
            o.put("grade", Double.isNaN(heat) ? "未知" : grade(heat));
        }
        return root;
    }

    // ------------------------------------------------------------------ 导入
    @Override
    public JsonNode importPlatform(String platform) {
        List<String> args = Arrays.asList("--platform", platform);
        String out;
        try {
            out = pythonCliRunner.run(ingestScript, args, 900);
        } catch (Exception e) {
            throw new RuntimeException("调用数据导入脚本失败：" + e.getMessage(), e);
        }
        String json = PythonCliRunner.lastJsonLine(out);
        JsonNode node;
        try {
            node = om.readTree(json);
        } catch (Exception e) {
            throw new RuntimeException("解析导入结果失败：" + e.getMessage() + " | 原始输出：" + out, e);
        }
        // 导入成功后清空该平台缓存，下次访问即重新加载新数据
        if (node.path("code").asInt() == 1) {
            cache.remove(platform);
        }
        return node;
    }
}
