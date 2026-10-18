package com.alvis.media.service.impl;

import com.alvis.media.service.HeatLogService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.extern.slf4j.Slf4j;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

/**
 * 预测记录服务实现：直接使用 JdbcTemplate（该表结构简单，不必引入实体/Mapper）。
 * 落库失败不影响预测主流程，仅记录告警。
 */
@Slf4j
@Service
public class HeatLogServiceImpl implements HeatLogService {

    /** 与 Python 分级模块一致的阈值 */
    private static final double GRADE_LOW = 684.0;
    private static final double GRADE_HIGH = 15661.0;

    private final JdbcTemplate jdbc;
    private final ObjectMapper om = new ObjectMapper();

    public HeatLogServiceImpl(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private static String gradeOf(Double heat) {
        if (heat == null) {
            return "未知";
        }
        if (heat < GRADE_LOW) {
            return "低热度";
        }
        if (heat < GRADE_HIGH) {
            return "中热度";
        }
        return "高热度";
    }

    @Override
    public void save(String model, String category, Double fans, Integer hour, Integer weekday, Integer month,
                     Double prediction, Double predictionLog, String source, Integer creatorId) {
        try {
            jdbc.update(
                    "INSERT INTO t_heat_predict_log(model, video_category, author_fans, publish_hour, "
                            + "publish_weekday, publish_month, prediction, prediction_log, grade, source, "
                            + "creator_id, create_time) VALUES(?,?,?,?,?,?,?,?,?,?,?,NOW())",
                    model,
                    category,
                    fans == null ? null : fans.longValue(),
                    hour, weekday, month,
                    prediction, predictionLog,
                    gradeOf(prediction), source, creatorId);
        } catch (Exception e) {
            log.warn("保存预测记录失败: {}", e.getMessage());
        }
    }

    @Override
    public JsonNode page(int page, int size) {
        if (page < 1) page = 1;
        if (size < 1) size = 10;
        if (size > 200) size = 200;

        ObjectNode root = om.createObjectNode();
        try {
            Integer total = jdbc.queryForObject("SELECT COUNT(*) FROM t_heat_predict_log", Integer.class);
            int t = total == null ? 0 : total;
            List<Map<String, Object>> list = jdbc.queryForList(
                    "SELECT id, model, video_category AS videoCategory, author_fans AS authorFans, "
                            + "publish_hour AS publishHour, publish_weekday AS publishWeekday, "
                            + "publish_month AS publishMonth, prediction, prediction_log AS predictionLog, "
                            + "grade, source, "
                            + "DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS createTime "
                            + "FROM t_heat_predict_log ORDER BY id DESC LIMIT ? OFFSET ?",
                    size, (page - 1) * size);
            root.put("total", t);
            root.put("page", page);
            root.put("size", size);
            root.set("list", om.valueToTree(list));
        } catch (Exception e) {
            log.warn("查询预测记录失败: {}", e.getMessage());
            root.put("total", 0);
            root.put("page", page);
            root.put("size", size);
            root.putArray("list");
        }
        return root;
    }
}
