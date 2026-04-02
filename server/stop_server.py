"""
停止服务器脚本
关闭占用8000端口的进程
"""
import subprocess
import sys


def stop_server():
    """查找并关闭占用8000端口的进程"""
    try:
        # 查找占用8000端口的进程
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True
        )

        # 查找包含8000的行
        lines = result.stdout.split('\n')
        pids = []

        for line in lines:
            if ':8000' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1].strip()
                    if pid.isdigit():
                        pids.append(pid)

        if not pids:
            print("✅ 没有发现占用8000端口的进程")
            return

        print(f"发现占用8000端口的进程: {pids}")

        # 关闭这些进程
        for pid in pids:
            print(f"正在关闭进程 {pid}...")
            subprocess.run(
                ['taskkill', '/F', '/PID', pid],
                capture_output=True
            )
            print(f"✅ 进程 {pid} 已关闭")

        print("\n✅ 端口8000已释放")

    except Exception as e:
        print(f"❌ 停止服务器失败: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(stop_server())
