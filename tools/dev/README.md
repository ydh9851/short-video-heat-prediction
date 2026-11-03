# Git 代理配置说明（飞鸟 VPN / 无代理）

## 1. 诊断结果（2026-11-02 实测）

| 项 | 值 |
|---|---|
| 原有配置 | `http.https://github.com.proxy = http://127.0.0.1:7892`（**端口写错，7892 无监听**） |
| 飞鸟 VPN 实际监听端口 | **7890**（进程被伪装，pid 1760） |
| 雷神加速器端口 | 10908（`leishenSdk`）——**与本配置无关，绝不写入 Git** |
| 修改后配置 | `http.proxy` / `https.proxy` = `http://127.0.0.1:7890` |

## 2. 两种模式

| 模式 | Git 配置 | 适用场景 |
|---|---|---|
| 代理模式 | `http.proxy` = `https.proxy` = `http://127.0.0.1:7890` | 飞鸟开启「系统代理」 |
| 无代理模式 | 不写任何 proxy 配置（直连） | 飞鸟开启「TUN / 全局模式」，或网络本身可访问 GitHub |

## 3. 一键切换

双击运行，或在项目根目录执行：

```bat
tools\dev\git-proxy-on.cmd      :: 切换为飞鸟代理模式
tools\dev\git-proxy-off.cmd     :: 切换为无代理（直连）模式
tools\dev\git-proxy-status.cmd  :: 查看当前配置 + 端口监听 + 远程连通性
```

三个脚本都会在切换后自动做一次 `git ls-remote` 自检并打印结果。

## 4. 手动命令（不想用脚本时）

```bat
:: 代理模式
git config --global http.proxy  http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890

:: 无代理模式
git config --global --unset-all http.proxy
git config --global --unset-all https.proxy

:: 查看当前配置
git config --global --get-regexp proxy
```

## 5. 如何验证生效

任选其一：

```bat
:: ① 一行看配置 + 连通性
tools\dev\git-proxy-status.cmd

:: ② 读远程引用（不产生任何改动）
git ls-remote --heads origin

:: ③ 试运行 fetch（不落盘）
git fetch --dry-run origin
```

- 代理模式预期：`port 7890 is listening` + `[OK] pull / push available`
- 无代理模式预期：`(none = direct connection)` + `[OK] direct connection works`

## 6. 常见问题

**Q：飞鸟换了端口怎么办？**
用下面命令查实际监听端口，然后改 `git-proxy-on.cmd` 里的 `PROXY` 变量：

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 7890,7891,7892,1080,10808,10809 } |
  Select-Object LocalPort, OwningProcess
```

**Q：无代理模式 fetch 失败？**
说明当前线路直连 GitHub 被阻断。到飞鸟里开启 **TUN / 全局模式**，或直接切回代理模式：
`tools\dev\git-proxy-on.cmd`。

**Q：要不要把雷神的端口也配上？**
不要。雷神是游戏加速器，走的是它自己的虚拟网卡 / 私有协议，不是 HTTP 代理；把 10908 写进
Git 只会导致所有 git 操作失败。

**Q：这些脚本为什么是英文提示？**
`.cmd` 在中文 Windows 下用 UTF-8/GBK 混排时，cmd 解析阶段（早于 `chcp` 生效）会把中文双字节
撕开导致整行命令错乱。因此脚本内容保持纯 ASCII，说明文字放在本文件里。
