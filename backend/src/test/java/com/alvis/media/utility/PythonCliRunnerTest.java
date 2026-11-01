package com.alvis.media.utility;

import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * PythonCliRunner 单元测试：覆盖单行 JSON 取值、正常执行、超时强杀、非零退出码四条关键路径。
 * 依赖运行环境中的 python 命令（与线上调用链一致）。
 */
class PythonCliRunnerTest {

    private PythonCliRunner runner() {
        PythonCliRunner runner = new PythonCliRunner();
        ReflectionTestUtils.setField(runner, "pythonPath", "python");
        return runner;
    }

    @Test
    void lastJsonLine_skipsBlankAndWarningLines() {
        String out = "[LightGBM] warning\n\n{\"ok\":1}\n\n";
        assertEquals("{\"ok\":1}", PythonCliRunner.lastJsonLine(out));
    }

    @Test
    void lastJsonLine_returnsTextWhenNoNewline() {
        assertEquals("{\"ok\":1}", PythonCliRunner.lastJsonLine("{\"ok\":1}"));
    }

    @Test
    void run_returnsStdoutOfNormalProcess() {
        // 注意：Windows 下 Java 通过 CreateProcess 传 argv，参数内的双引号会被转义掉，
        // 因此这里用不含引号的载荷验证链路；生产链路的中文参数走 URL 编码，不传裸 JSON。
        String out = runner().run("-c", List.of("print('ok-123')"), 30);
        assertEquals("ok-123", PythonCliRunner.lastJsonLine(out));
    }

    /**
     * 回归用例：旧实现先读 stdout 到 EOF 再 waitFor，Python 卡住时永久阻塞、超时形同虚设。
     * 本用例要求「3 秒超时必须在 20 秒内抛出，且异常带超时前输出」。
     */
    @Test
    void run_killsProcessWhenTimeoutExceeded() {
        long start = System.currentTimeMillis();
        RuntimeException e = assertThrows(RuntimeException.class, () -> runner()
                .run("-c", List.of("import time;print('partial',flush=True);time.sleep(60)"), 3));
        long elapsed = System.currentTimeMillis() - start;

        assertTrue(e.getMessage().contains("超时"), () -> "异常信息应包含超时提示，实际: " + e.getMessage());
        assertTrue(elapsed < 20_000, "超时后应尽快返回，实际耗时 " + elapsed + "ms");
        assertTrue(e.getMessage().contains("partial"), "应携带超时前的输出便于排查，实际: " + e.getMessage());
    }

    @Test
    void run_passesTraceIdToChildProcess() {
        TraceContext.bind("trace-abc-123");
        try {
            String out = runner().run("-c", List.of("import os;print(os.environ.get('TRACE_ID',''))"), 30);
            assertEquals("trace-abc-123", PythonCliRunner.lastJsonLine(out));
        } finally {
            TraceContext.clear();
        }
    }

    @Test
    void run_reportsNonZeroExitCode() {
        RuntimeException e = assertThrows(RuntimeException.class,
                () -> runner().run("-c", List.of("import sys;print('boom');sys.exit(3)"), 30));
        assertTrue(e.getMessage().contains("exit 3"), () -> "应带出退出码，实际: " + e.getMessage());
        assertTrue(e.getMessage().contains("boom"), () -> "应带出 stderr/stdout 内容，实际: " + e.getMessage());
    }
}
