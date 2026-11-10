package com.alvis.media.viewmodel.scenario;

import lombok.Data;

import java.util.List;

/**
 * 场景对比请求：2~3 个场景 ID（顺序即展示顺序，首个作为基准）。
 */
@Data
public class CaseCompareRequestVM {

    private List<Long> ids;
}
