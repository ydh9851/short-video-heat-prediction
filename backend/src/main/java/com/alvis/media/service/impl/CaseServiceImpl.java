package com.alvis.media.service.impl;

import com.alvis.media.context.WebContext;
import com.alvis.media.domain.Case;
import com.alvis.media.domain.User;
import com.alvis.media.domain.enums.RoleEnum;
import com.alvis.media.exception.BusinessException;
import com.alvis.media.repository.CaseMapper;
import com.alvis.media.service.CaseService;
import com.alvis.media.service.PredictService;
import com.alvis.media.viewmodel.predict.PredictRequestVM;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

@Service
public class CaseServiceImpl implements CaseService {

    private static final DateTimeFormatter TIME_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private final CaseMapper caseMapper;
    private final WebContext webContext;
    private final PredictService predictService;
    private final ObjectMapper om = new ObjectMapper();

    public CaseServiceImpl(CaseMapper caseMapper, WebContext webContext, PredictService predictService) {
        this.caseMapper = caseMapper;
        this.webContext = webContext;
        this.predictService = predictService;
    }

    @Override
    public Long create(Case c) {
        validate(c);
        User user = webContext.getCurrentUser();
        if (user != null) {
            c.setUserId(user.getId());
            c.setUserName(user.getUserName());
        }
        c.setId(null);
        c.setCreateTime(new Date());
        caseMapper.insert(c);
        return c.getId();
    }

    @Override
    public Case getOwn(Long id) {
        if (id == null) {
            return null;
        }
        Case c = caseMapper.selectById(id);
        if (c == null || !canAccess(c)) {
            return null;
        }
        return c;
    }

    @Override
    public IPage<Case> page(int pageIndex, int pageSize, String name) {
        LambdaQueryWrapper<Case> qw = new LambdaQueryWrapper<>();
        User user = webContext.getCurrentUser();
        if (!isAdmin(user)) {
            qw.eq(Case::getUserId, user == null ? -1 : user.getId());
        }
        if (name != null && !name.trim().isEmpty()) {
            qw.like(Case::getName, name.trim());
        }
        qw.orderByDesc(Case::getId);
        return caseMapper.selectPage(new Page<>(pageIndex, pageSize), qw);
    }

    @Override
    public void updateOwn(Case c) {
        if (c.getId() == null) {
            throw new BusinessException(400, "缺少场景 ID");
        }
        Case origin = caseMapper.selectById(c.getId());
        if (origin == null || !canAccess(origin)) {
            throw new BusinessException(404, "场景不存在");
        }
        validate(c);
        // 只允许改业务字段，归属与创建时间不可变
        origin.setName(c.getName());
        origin.setDescription(c.getDescription());
        origin.setModel(c.getModel());
        origin.setVideoCategory(c.getVideoCategory());
        origin.setAuthorFans(c.getAuthorFans());
        origin.setPublishHour(c.getPublishHour());
        origin.setPublishWeekday(c.getPublishWeekday());
        origin.setPublishMonth(c.getPublishMonth());
        origin.setUpdateTime(new Date());
        caseMapper.updateById(origin);
    }

    @Override
    public void deleteOwn(Long id) {
        Case origin = id == null ? null : caseMapper.selectById(id);
        if (origin == null || !canAccess(origin)) {
            throw new BusinessException(404, "场景不存在");
        }
        caseMapper.deleteById(id);
    }

    @Override
    public JsonNode compare(List<Long> ids) {
        // 去重保序：前端可能因重复点击传入重复 id
        List<Long> distinct = new ArrayList<>();
        if (ids != null) {
            for (Long id : ids) {
                if (id != null && !distinct.contains(id)) {
                    distinct.add(id);
                }
            }
        }
        if (distinct.size() < 2 || distinct.size() > 3) {
            throw new BusinessException(400, "请选择 2-3 个场景进行对比");
        }

        List<Case> cases = new ArrayList<>();
        for (Long id : distinct) {
            Case c = caseMapper.selectById(id);
            if (c == null || !canAccess(c)) {
                throw new BusinessException(404, "场景不存在");
            }
            cases.add(c);
        }

        ObjectNode root = om.createObjectNode();
        root.put("generatedAt", LocalDateTime.now().format(TIME_FORMAT));
        root.put("baseId", cases.get(0).getId());
        ArrayNode items = root.putArray("items");
        for (Case c : cases) {
            ObjectNode item = items.addObject();
            item.put("id", c.getId());
            item.put("name", c.getName());
            item.put("description", c.getDescription());
            item.put("model", c.getModel());
            item.put("videoCategory", c.getVideoCategory());
            item.put("authorFans", c.getAuthorFans());
            item.put("publishHour", c.getPublishHour());
            item.put("publishWeekday", c.getPublishWeekday());
            item.put("publishMonth", c.getPublishMonth());
            try {
                JsonNode interval = predictService.interval(toRequest(c));
                item.put("prediction", interval.path("prediction").asDouble());
                item.put("lo", interval.path("lo").asDouble());
                item.put("hi", interval.path("hi").asDouble());
                item.put("grade", interval.path("grade").asText(""));
                item.put("alpha", interval.path("alpha").asDouble(0.1));
                item.put("coverage", interval.path("target_coverage").asDouble(0.9));
                item.putNull("error");
            } catch (Exception e) {
                // 单列失败降级：其余场景仍可对比
                item.putNull("prediction");
                item.putNull("lo");
                item.putNull("hi");
                item.put("grade", "");
                item.putNull("alpha");
                item.putNull("coverage");
                item.put("error", e.getMessage() == null ? "预测区间计算失败" : e.getMessage());
            }
        }
        return root;
    }

    private PredictRequestVM toRequest(Case c) {
        PredictRequestVM req = new PredictRequestVM();
        req.setModel(c.getModel());
        req.setVideoCategory(c.getVideoCategory());
        req.setAuthorFans(c.getAuthorFans());
        req.setPublishHour(c.getPublishHour());
        req.setPublishWeekday(c.getPublishWeekday());
        req.setPublishMonth(c.getPublishMonth());
        return req;
    }

    // ------------------------------------------------------------------

    private boolean canAccess(Case c) {
        User user = webContext.getCurrentUser();
        if (isAdmin(user)) {
            return true;
        }
        return user != null && c.getUserId() != null && c.getUserId().equals(user.getId());
    }

    private boolean isAdmin(User user) {
        return user != null && user.getRole() != null
                && user.getRole() == RoleEnum.ADMIN.getCode();
    }

    private void validate(Case c) {
        if (c.getName() == null || c.getName().trim().isEmpty()) {
            throw new BusinessException(400, "场景名称不能为空");
        }
        if (c.getVideoCategory() == null || c.getVideoCategory().trim().isEmpty()) {
            throw new BusinessException(400, "视频类别不能为空");
        }
        if (c.getModel() == null || c.getModel().trim().isEmpty()) {
            c.setModel("lgbm");
        }
        if (c.getAuthorFans() == null || c.getAuthorFans() < 0) {
            c.setAuthorFans(0.0);
        }
        if (c.getPublishHour() == null || c.getPublishHour() < 0 || c.getPublishHour() > 23) {
            throw new BusinessException(400, "发布小时需在 0-23 之间");
        }
        if (c.getPublishWeekday() == null || c.getPublishWeekday() < 0 || c.getPublishWeekday() > 6) {
            throw new BusinessException(400, "发布星期需在 0-6 之间");
        }
        if (c.getPublishMonth() == null || c.getPublishMonth() < 1 || c.getPublishMonth() > 12) {
            throw new BusinessException(400, "发布月份需在 1-12 之间");
        }
    }
}
