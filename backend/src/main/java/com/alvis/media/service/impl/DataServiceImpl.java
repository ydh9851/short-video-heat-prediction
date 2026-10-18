package com.alvis.media.service.impl;

import com.alvis.media.service.DataService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 数据管理服务实现：直接读取 Python 流水线产出的规范化数据集 data/processed/train_clean.csv，
 * 首次访问时加载进内存并缓存（数据量不大，避免每次请求都读盘）。
 */
@Service
public class DataServiceImpl implements DataService {

    /** 与分级模块一致的热度分级阈值 */
    private static final double GRADE_LOW = 684.0;
    private static final double GRADE_HIGH = 15661.0;

    @Value("${system.data.processed:../data/processed/train_clean.csv}")
    private String processedPath;

    private final ObjectMapper om = new ObjectMapper();

    private volatile String[] cols;
    private volatile List<String[]> rows;

    private synchronized void ensureLoaded() {
        if (rows != null) {
            return;
        }
        List<String[]> list = new ArrayList<>();
        String[] header;
        try (BufferedReader br = new BufferedReader(
                new InputStreamReader(new FileInputStream(processedPath), StandardCharsets.UTF_8))) {
            String head = br.readLine();
            if (head == null) {
                cols = new String[0];
                rows = list;
                return;
            }
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
        } catch (Exception e) {
            throw new RuntimeException("读取数据集失败(" + processedPath + "): " + e.getMessage(), e);
        }
        cols = header;
        rows = list;
    }

    private int idx(String name) {
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

    @Override
    public JsonNode overview() {
        ensureLoaded();
        int iCat = idx("video_category"), iHeat = idx("heat"),
                iFans = idx("author_fans"), iTime = idx("publish_time");

        Map<String, Integer> catCount = new LinkedHashMap<>();
        List<Double> heats = new ArrayList<>();
        List<Double> fans = new ArrayList<>();
        int lo = 0, mid = 0, hi = 0;
        String minTime = null, maxTime = null;
        double fansSum = 0, heatSum = 0;

        for (String[] r : rows) {
            catCount.merge(iCat >= 0 && iCat < r.length ? r[iCat] : "未知", 1, Integer::sum);

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

    @Override
    public JsonNode samples(int page, int size, String category) {
        ensureLoaded();
        if (page < 1) page = 1;
        if (size < 1) size = 20;
        if (size > 200) size = 200;

        int iId = idx("video_id"), iCat = idx("video_category"), iFans = idx("author_fans"),
                iTime = idx("publish_time"), iPlay = idx("play_cnt"), iLike = idx("like_cnt"),
                iComment = idx("comment_cnt"), iShare = idx("share_cnt"),
                iHeat = idx("heat"), iHeatLog = idx("heat_log");

        List<String[]> filtered = new ArrayList<>();
        boolean filter = category != null && !category.trim().isEmpty() && !"全部".equals(category);
        for (String[] r : rows) {
            if (filter) {
                String c = iCat >= 0 && iCat < r.length ? r[iCat] : "";
                if (!category.trim().equals(c)) {
                    continue;
                }
            }
            filtered.add(r);
        }

        int total = filtered.size();
        int from = (page - 1) * size;
        int to = Math.min(from + size, total);

        ObjectNode root = om.createObjectNode();
        root.put("total", total);
        root.put("page", page);
        root.put("size", size);
        ArrayNode list = root.putArray("list");
        for (int i = Math.max(0, from); i < to; i++) {
            String[] r = filtered.get(i);
            double heat = iHeat >= 0 ? d(r[iHeat]) : Double.NaN;
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

    private static String val(String[] r, int i) {
        return (i >= 0 && i < r.length) ? r[i] : "";
    }
}
