#!/usr/bin/env python3
"""
新编译服务器 SSH key 自动配置 (v1.2.0 通用化)

用途: 首次遇到新编译服务器时, 把用户的 SSH 公钥自动部署过去, 之后免密登录。

通用化变更:
- 移除硬编码 ontim 用户, 用 BUILD_SERVER_USER env
- 移除硬编码 ontim@ontim 公钥, 用 MY_SSH_PUB_KEY env (用户自填)
- 双密码尝试保留 (BUILD_SERVER_PASS / BUILD_SERVER_PASS_ALT)
- 路径自定位

使用方法:
1. 把自己的 SSH 公钥填到 ~/.hermes/.env:
   MY_SSH_PUB_KEY="ssh-rsa AAAAB3NzaC1yc2EAAAA... user@host"
2. python3 scripts/setup_ssh_key.py <SERVER_IP>
"""
import os
import sys
import paramiko
from pathlib import Path
from dotenv import load_dotenv

# 路径自定位 (用于错误信息显示, 不强制依赖)
SKILL_DIR = Path(__file__).parent.parent

# 加载 env
load_dotenv(os.path.expanduser("~/.hermes/.env"))

# 必需配置
BUILD_SERVER_USER = os.environ.get("BUILD_SERVER_USER")
if not BUILD_SERVER_USER:
    print("❌ BUILD_SERVER_USER 未配置, 请在 ~/.hermes/.env 设置")
    sys.exit(1)

MY_SSH_PUB_KEY = os.environ.get("MY_SSH_PUB_KEY")
if not MY_SSH_PUB_KEY:
    print("❌ MY_SSH_PUB_KEY 未配置, 请在 ~/.hermes/.env 设置你的公钥")
    print("   例: MY_SSH_PUB_KEY=\"ssh-rsa AAAAB3NzaC1yc2E... user@host\"")
    print("   生成: ssh-keygen -t rsa; cat ~/.ssh/id_rsa.pub")
    sys.exit(1)


def setup_ssh_key(ip: str, user: str, password: str, pub_key: str) -> bool:
    """通过密码登录, 部署 SSH 公钥"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            ip,
            username=user,
            password=password,
            timeout=15,
            look_for_keys=False,
        )

        # 1. 准备 ~/.ssh 目录
        client.exec_command("mkdir -p ~/.ssh && chmod 700 ~/.ssh")

        # 2. 追加公钥
        client.exec_command(
            f"echo '{pub_key}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
        )

        # 3. 验证
        verify, _, _ = client.exec_command(
            f"grep -c '{pub_key[-20:]}' ~/.ssh/authorized_keys"
        )
        count = int(verify.read().decode().strip())
        print(f"  ✅ {ip}: SSH key 添加成功 (共 {count} 条)")

        client.close()
        return True
    except Exception as e:
        print(f"  ❌ {ip}: {e}")
        return False


def add_new_server(ip: str):
    """尝试两个密码, 第一个成功就用"""
    passwords = [os.environ.get("BUILD_SERVER_PASS", "")]
    alt = os.environ.get("BUILD_SERVER_PASS_ALT", "")
    if alt:
        passwords.append(alt)

    for pwd in passwords:
        if not pwd:
            continue
        if setup_ssh_key(ip, BUILD_SERVER_USER, pwd, MY_SSH_PUB_KEY):
            return

    print(f"  ❌ {ip}: 所有密码都失败, 需手动检查")


def main():
    if len(sys.argv) < 2:
        print(f"用法: python3 {sys.argv[0]} <SERVER_IP>")
        print(f"  例: python3 {sys.argv[0]} 192.168.1.10")
        sys.exit(1)

    ip = sys.argv[1]
    print(f"🔑 给 {ip} 配置 SSH key")
    print(f"   用户: {BUILD_SERVER_USER}")
    print(f"   公钥: {MY_SSH_PUB_KEY[:50]}...{MY_SSH_PUB_KEY[-20:]}")

    add_new_server(ip)


if __name__ == "__main__":
    main()
