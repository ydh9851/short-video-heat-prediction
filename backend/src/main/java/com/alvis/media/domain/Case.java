package com.alvis.media.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Date;

/**
 * 分析场景（Case）：一次分析的完整先验输入。
 *
 * <p>是业务闭环的核心实体——用户在数据样本页/预测页保存场景后，
 * 预测、归因、反事实、报告各页面直接复用该场景的参数，
 * 不再要求重复输入（对应验收主线「全流程不重复输入」）。
 */
@Data
@EqualsAndHashCode
@NoArgsConstructor
@TableName("t_case")
public class Case implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /** 场景名称，如「美食大号周五晚 8 点」 */
    private String name;

    private String description;

    /** 选用模型（lgbm / xgb / rf / lr / knn / svm / dt） */
    private String model;

    private String videoCategory;

    private Double authorFans;

    private Integer publishHour;

    private Integer publishWeekday;

    private Integer publishMonth;

    /** 来源：manual=手动创建 / data-sample=数据样本一键生成 */
    private String source;

    private Integer userId;

    private String userName;

    private Date createTime;

    private Date updateTime;
}
