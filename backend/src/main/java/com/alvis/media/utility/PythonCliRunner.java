package com.alvis.media.utility;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * Python 算法引擎通用调用器：用 ProcessBuilder 调 .venv 中的 Python CLI，
 * 读取其 stdout（单行 JSON 契约）。供归因分析、热度分级等模块复用。
 */
@Component
public class PythonCliRunner {

    @Value("${system.python.path:python}")
    private String pythonPath;

    /**
     * 执行 Python 脚本并返回 stdout 文本。
     *
     * @param scriptPath 脚本路径（相对后端工作目录，如 ../algorithm/attribution/shap_analysis.py）
     * @param args       附加参数列表（可为 null）
     */
    public String run(String scriptPath, List<String> args) {
        if (scriptPath == null || scriptPath.trim().isEmpty()) {
            throw new IllegalStateException("未配置 Python 脚本路径");
        }
        List<String> cmd = new ArrayList<>();
        cmd.add(pythonPath);
        cmd.add(scriptPath.trim());
        if (args != null) {
            cmd.addAll(args);
        }
        try {
            ProcessBuilder pb = new ProcessBuilder(cmd);
            pb.redirectErrorStream(true);
            Process p = pb.start();
            StringBuilder sb = new StringBuilder();
            try (BufferedReader br = new BufferedReader(
                    new InputStreamReader(p.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = br.readLine()) != null) {
                    sb.append(line).append('\n');
                }
            }
            int code = p.waitFor();
            if (code != 0) {
                throw new RuntimeException("python exit " + code + ": " + sb);
            }
            return sb.toString().trim();
        } catch (Exception e) {
            throw new RuntimeException("调用 Python 脚本失败: " + e.getMessage(), e);
        }
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
