package com.alvis.media.utility;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.Set;

/**
 * 派生缓存统一失效器：预测 / 归因 / 分级缓存的清理收口到一处。
 *
 * <p>缓存 key 已带模型/特征版本（预测命中新版本的 key 自然重算），
 * 但两类变更仍需主动失效：
 * <ul>
 *   <li>数据导入：数据口径变了，旧版本 key 的结果同样失真；</li>
 *   <li>版本切换 / 回滚：旧版本 key 会成为无人访问的垃圾，且归因等
 *       全局缓存若仍按旧版本 tag 命中会造成「切换了但页面没变」的错觉。</li>
 * </ul>
 */
@Component
public class DerivedCacheEvictor {

    private static final Logger log = LoggerFactory.getLogger(DerivedCacheEvictor.class);

    private static final String[] PATTERNS = {"predict:*", "attribution:*", "grading:*"};

    private final StringRedisTemplate redisTemplate;

    public DerivedCacheEvictor(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    /** 清理全部派生缓存；失败只记日志，不影响主流程。 */
    public void evictAll() {
        try {
            for (String pattern : PATTERNS) {
                Set<String> keys = redisTemplate.keys(pattern);
                if (keys != null && !keys.isEmpty()) {
                    redisTemplate.delete(keys);
                }
            }
        } catch (Exception e) {
            log.warn("派生缓存失效失败（不影响主流程）：{}", e.getMessage());
        }
    }
}
