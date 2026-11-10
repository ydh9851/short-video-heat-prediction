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
 * 管理操作审计日志。
 * 由 OperationLogAspect 切面统一采集，异步写入 t_operation_log，
 * 用于回答「谁在什么时间对哪个管理接口做了什么、是否成功、耗时多久」。
 */
@Data
@EqualsAndHashCode
@NoArgsConstructor
@TableName("t_operation_log")
public class OperationLog implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    private Integer userId;

    private String userName;

    /** 操作名称，如 model.promote / data.import */
    private String operation;

    /** Controller 类名#方法名 */
    private String method;

    /** 请求参数（JSON，截断 2000 字符） */
    private String params;

    /** SUCCESS / FAILURE */
    private String result;

    private String errorMsg;

    private Long costMs;

    private String traceId;

    private String ip;

    private Date createTime;
}
