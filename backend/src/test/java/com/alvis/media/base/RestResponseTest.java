package com.alvis.media.base;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

/** 统一响应体契约测试：前端按 code/message/response 三字段解析，改动会直接影响所有页面。 */
class RestResponseTest {

    @Test
    void okWrapsResponseData() {
        RestResponse<String> resp = RestResponse.ok("hello");
        assertEquals(SystemCode.OK.getCode(), resp.getCode());
        assertEquals("hello", resp.getResponse());
    }

    @Test
    void failCarriesCodeAndMessage() {
        RestResponse<?> resp = RestResponse.fail(500, "系统内部错误");
        assertEquals(500, resp.getCode());
        assertEquals("系统内部错误", resp.getMessage());
        assertNull(resp.getResponse());
    }
}
