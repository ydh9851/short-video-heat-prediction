package com.alvis.media.utility;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * Python 算法引擎通用调用器：用 ProcessBuilder 调 .venv 中的 Python CLI，
 * 读取其 stdout（单行 JSON 契约）。供归因分析、热度分级、模型评估等模块复用。
 */
@Component
public class PythonCliRunner {

    /** 默认超时：SHAP 全局归因等首次调用需要训练模型，给足时间但避免无限挂起。 */
    private static final int DEFAULT_TIMEOUT_SECONDS = 600;

    @Value("${system.python.path:python}")
    private String pythonPath;

    /**
     * 执行 Python 脚本并返回 stdout 文本（默认超时 600s）。
     *
     * @param scriptPath 脚本路径（相对后端工作目录，如 ../algorithm/attribution/shap_analysis.py）
     * @param args       附加参数列表（可为 null）
     */
    public String run(String scriptPath, List<String> args) {
        return run(scriptPath, args, DEFAULT_TIMEOUT_SECONDS);
    }

    /**
     * 执行 Python 脚本并返回 stdout 文本，超时后强制终止进程。
     * 交叉验证 / 超参数搜索等实验耗时较长，调用方需显式指定更长的超时。
     */
    public String run(String scriptPath, List<String> args, int timeoutSeconds) {
        if (scriptPath == null || scriptPath.trim().isEmpty()) {
            throw new IllegalStateException("未配置 Python 脚本路径");
        }
        List<String> cmd = new ArrayList<>();
        cmd.add(pythonPath);
        cmd.add(scriptPath.trim());
        if (args != null) {
            cmd.addAll(args);
        }
        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.redirectErrorStream(true);
        // 统一子进程 IO 编码与缓冲：避免中文 Windows 下 stdout 乱码、或输出滞留在缓冲区
        Map<String, String> env = pb.environment();
        env.put("PYTHONIOENCODING", "utf-8");
        env.put("PYTHONUNBUFFERED", "1");
        // 透传 traceId：算法侧异常输出会带上它，便于与 Java 日志逐条对齐
        String traceId = TraceContext.current();
        if (traceId != null) {
            env.put("TRACE_ID", traceId);
        }

        Process p;
        try {
            p = pb.start();
        } catch (IOException e) {
            throw new RuntimeException("启动 Python 进程失败: " + e.getMessage(), e);
        }

        // 读流必须与等待并行：若先读到 EOF 再 waitFor，进程卡住时 readLine 会永久阻塞，超时形同虚设
        StringBuffer sb = new StringBuffer();
        Thread reader = new Thread(() -> {
            try (BufferedReader br = new BufferedReader(
                    new InputStreamReader(p.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = br.readLine()) != null) {
                    sb.append(line).append('\n');
                }
            } catch (IOException ignored) {
                // 进程被强制终止时流会中断，属预期情况
            }
        }, "py-cli-reader");
        reader.setDaemon(true);
        reader.start();

        boolean finished;
        try {
            finished = p.waitFor(timeoutSeconds, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            p.destroyForcibly();
            Thread.currentThread().interrupt();
            throw new RuntimeException("Python 脚本执行被中断: " + scriptPath, e);
        }
        if (!finished) {
            p.destroyForcibly();
            try {
                p.waitFor(5, TimeUnit.SECONDS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            throw new RuntimeException("Python 脚本执行超时（" + timeoutSeconds + "s），已强制终止: "
                    + scriptPath + (sb.length() > 0 ? "，超时前输出: " + sb : ""));
        }
        try {
            // 进程已退出，流必然 EOF；给读线程一点时间收尾残余输出
            reader.join(5000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        String out = sb.toString().trim();
        if (p.exitValue() != 0) {
            throw new RuntimeException("python exit " + p.exitValue() + ": " + out);
        }
        return out;
    }

    /** 取输出中最后一行非空文本（Python 输出可能混入告警行）。 */
    public static String lastJsonLine(String out) {
        String last = out;
        for (String line : out.split("\\r?\\n")) {
            if (!line.trim().isEmpty()) {
                last = line.trim();
            }
        }
        return last;
    }
}
