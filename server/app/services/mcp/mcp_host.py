"""
简配MCP Host
用于管理和调用MCP服务器，集成到大模型API中
"""
import asyncio
import json
import logging
import subprocess
from typing import Dict, Any, Optional, List
from datetime import datetime


logger = logging.getLogger(__name__)


class MCPTool:
    """MCP工具描述"""

    def __init__(self, name: str, description: str, input_schema: Dict[str, Any]):
        self.name = name
        self.description = description
        self.input_schema = input_schema


class MCPClient:
    """MCP客户端 - 连接到单个MCP服务器"""

    def __init__(self, name: str, command: str):
        """
        初始化MCP客户端

        Args:
            name: 服务器名称
            command: 启动MCP服务器的命令
        """
        self.name = name
        self.command = command
        self.process: Optional[asyncio.subprocess.Process] = None
        self.tools: List[MCPTool] = []
        self.initialized = False

    async def start(self):
        """启动MCP服务器进程"""
        if self.process and self.process.returncode is None:
            logger.warning(f"{self.name} 已经在运行中")
            return True

        try:
            logger.info(f"启动MCP服务器: {self.name}")
            logger.info(f"启动命令: {self.command}")

            # 获取当前脚本的目录作为工作目录
            import sys
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 向上3级: mcp/ -> services/ -> app/ -> server/
            server_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

            logger.info(f"工作目录: {server_dir}")

            # 解析命令
            # 将 "python -m app.services.mcp.weather_server" 拆分为可执行文件和参数
            import shlex
            command_parts = shlex.split(self.command)

            if not command_parts:
                raise ValueError("命令为空")

            # 设置环境变量，添加当前目录到 PYTHONPATH
            import os
            env = os.environ.copy()
            python_path = env.get('PYTHONPATH', '')
            env['PYTHONPATH'] = f"{server_dir}{os.pathsep}{python_path}" if python_path else server_dir

            logger.info(f"设置 PYTHONPATH: {env['PYTHONPATH']}")

            # 使用 asyncio.create_subprocess_exec 启动进程
            self.process = await asyncio.create_subprocess_exec(
                *command_parts,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=server_dir,
                env=env  # 传递环境变量
            )

            # 等待一小段时间让进程启动
            await asyncio.sleep(0.5)

            # 检查进程是否成功启动
            if self.process.returncode is not None:
                logger.error(f"{self.name} 进程启动失败，返回码: {self.process.returncode}")
                # 读取错误输出
                if self.process.stderr:
                    stderr_output = await self.process.stderr.read()
                    logger.error(f"错误输出: {stderr_output.decode('utf-8', errors='ignore')}")
                return False

            # 初始化MCP会话
            logger.info(f"正在初始化 {self.name} MCP会话...")
            await self._initialize()

            # 获取可用工具列表
            logger.info(f"正在获取 {self.name} 工具列表...")
            await self._list_tools()

            logger.info(f"{self.name} 启动成功，可用工具: {len(self.tools)}")
            return True

        except Exception as e:
            import traceback
            logger.error(f"启动 {self.name} 失败: {e}")
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False

    async def _initialize(self):
        """初始化MCP会话"""
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "smart-gardening-assistant",
                    "version": "1.0.0"
                }
            }
        }

        response = await self._send_request(init_request)
        if response and "result" in response:
            self.initialized = True
            logger.info(f"{self.name} MCP会话已初始化")
        else:
            raise Exception("MCP初始化失败")

    async def _list_tools(self):
        """获取可用工具列表"""
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        response = await self._send_request(tools_request)
        if response and "result" in response:
            tools_data = response["result"].get("tools", [])
            self.tools = [
                MCPTool(
                    name=tool["name"],
                    description=tool["description"],
                    input_schema=tool.get("inputSchema", {})
                )
                for tool in tools_data
            ]
            logger.info(f"获取到 {len(self.tools)} 个工具:")
            for tool in self.tools:
                logger.info(f"  - {tool.name}: {tool.description}")

    async def _send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        发送请求到MCP服务器

        Args:
            request: JSON-RPC请求

        Returns:
            JSON-RPC响应
        """
        if not self.process or self.process.returncode is not None:
            logger.error(f"{self.name} 未运行")
            return None

        try:
            # 发送请求
            request_json = json.dumps(request, ensure_ascii=False) + "\n"
            self.process.stdin.write(request_json.encode('utf-8'))
            await self.process.stdin.drain()

            # 读取响应
            response_line = await self.process.stdout.readline()
            if not response_line:
                logger.error(f"{self.name} 无响应")
                return None

            response = json.loads(response_line.decode())

            # 检查错误
            if "error" in response:
                logger.error(f"{self.name} 返回错误: {response['error']}")
                return None

            return response

        except Exception as e:
            logger.error(f"{self.name} 请求失败: {e}")
            return None

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Any]:
        """
        调用工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        if not self.initialized:
            logger.error(f"{self.name} 未初始化")
            return None

        try:
            # 调用工具
            tool_request = {
                "jsonrpc": "2.0",
                "id": int(datetime.now().timestamp()),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            response = await self._send_request(tool_request)
            if response and "result" in response:
                # 解析返回的content
                content = response["result"].get("content", [])
                if content and content[0].get("type") == "text":
                    return content[0].get("text")

                # 返回原始结果
                return response["result"]

            return None

        except Exception as e:
            logger.error(f"{self.name} 调用工具 {tool_name} 失败: {e}")
            return None

    async def stop(self):
        """停止MCP服务器"""
        if self.process:
            logger.info(f"停止 {self.name}")

            try:
                # 步骤1: 关闭 stdin，让进程知道不会再有输入
                if self.process.stdin:
                    self.process.stdin.close()
                    await asyncio.sleep(0.1)

                # 步骤2: 等待进程自然退出（给2秒时间）
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=2.0)
                    logger.info(f"{self.name} 已正常关闭")
                except asyncio.TimeoutError:
                    # 步骤3: 如果超时，尝试 terminate
                    logger.warning(f"{self.name} 未能自然退出，尝试终止...")
                    self.process.terminate()

                    try:
                        await asyncio.wait_for(self.process.wait(), timeout=3.0)
                        logger.info(f"{self.name} 已被终止")
                    except asyncio.TimeoutError:
                        # 步骤4: 如果还是超时，强制 kill
                        logger.warning(f"{self.name} 未能正常终止，强制结束")
                        self.process.kill()
                        await self.process.wait()
                        logger.info(f"{self.name} 已被强制结束")

            except Exception as e:
                logger.error(f"关闭 {self.name} 时出错: {e}")
                # 出错时强制清理
                try:
                    if self.process.returncode is None:
                        self.process.kill()
                        await self.process.wait()
                except:
                    pass

            finally:
                # 清理资源
                self.process = None
                self.initialized = False


class MCPHost:
    """
    简配MCP Host
    管理多个MCP客户端，提供统一的工具调用接口
    """

    def __init__(self):
        """初始化MCP Host"""
        self.clients: Dict[str, MCPClient] = {}
        self.logger = logger

    async def add_server(self, name: str, command: str) -> bool:
        """
        添加并启动一个MCP服务器

        Args:
            name: 服务器名称（唯一标识）
            command: 启动命令

        Returns:
            是否成功启动
        """
        # 检查是否已存在且仍在运行
        if name in self.clients:
            client = self.clients[name]
            # 检查进程是否还在运行
            if client.process and client.process.returncode is None:
                self.logger.warning(f"服务器 {name} 已在运行中")
                return True
            else:
                # 进程已关闭，移除旧的客户端
                self.logger.info(f"服务器 {name} 已关闭，重新启动")
                del self.clients[name]

        client = MCPClient(name, command)
        if await client.start():
            self.clients[name] = client
            return True
        return False

    async def remove_server(self, name: str):
        """
        移除并停止一个MCP服务器

        Args:
            name: 服务器名称
        """
        if name in self.clients:
            await self.clients[name].stop()
            del self.clients[name]

    def get_all_tools(self) -> List[MCPTool]:
        """
        获取所有MCP服务器的工具列表

        Returns:
            所有工具的列表
        """
        all_tools = []
        for client in self.clients.values():
            all_tools.extend(client.tools)
        return all_tools

    def get_tools_description(self) -> str:
        """
        获取所有工具的描述（用于大模型提示词）

        Returns:
            工具描述文本
        """
        descriptions = []
        for client in self.clients.values():
            descriptions.append(f"\n## {client.name}\n")
            for tool in client.tools:
                desc = f"- {tool.name}: {tool.description}"
                if tool.input_schema.get("properties"):
                    params = []
                    for param_name, param_info in tool.input_schema["properties"].items():
                        param_desc = param_info.get("description", param_name)
                        required = param_name in tool.input_schema.get("required", [])
                        req_str = " (必须)" if required else " (可选)"
                        params.append(f"  * {param_name}{req_str}: {param_desc}")

                    if params:
                        desc += "\n  参数:\n" + "\n".join(params)

                descriptions.append(desc)

        return "\n".join(descriptions)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
        """
        调用指定工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        # 在所有客户端中查找工具
        for client in self.clients.values():
            for tool in client.tools:
                if tool.name == tool_name:
                    self.logger.info(f"调用工具: {tool_name} (来自 {client.name})")
                    result = await client.call_tool(tool_name, arguments)
                    return result

        self.logger.error(f"未找到工具: {tool_name}")
        return None

    async def find_tool_for_intent(self, intent: str) -> Optional[str]:
        """
        根据意图查找合适的工具

        Args:
            intent: 用户意图描述

        Returns:
            工具名称
        """
        intent_lower = intent.lower()

        # 简单的关键词匹配
        for client in self.clients.values():
            for tool in client.tools:
                tool_name = tool.name.lower()
                tool_desc = tool.description.lower()

                # 天气相关
                if "天气" in intent_lower or "weather" in intent_lower:
                    if "weather" in tool_name or "天气" in tool_desc:
                        return tool.name
                    if "forecast" in tool_name and ("预报" in intent_lower or "未来" in intent_lower):
                        return tool.name
                    if "alert" in tool_name and ("预警" in intent_lower or "警告" in intent_lower):
                        return tool.name

        return None

    async def shutdown(self):
        """关闭所有MCP服务器"""
        self.logger.info("关闭所有MCP服务器...")
        for client in self.clients.values():
            await client.stop()
        self.clients.clear()


# 全局MCP Host实例
_mcp_host: Optional[MCPHost] = None


def get_mcp_host() -> MCPHost:
    """
    获取全局MCP Host实例（单例模式）

    Returns:
        MCPHost实例
    """
    global _mcp_host
    if _mcp_host is None:
        _mcp_host = MCPHost()
    return _mcp_host


async def initialize_mcp_servers(servers: Dict[str, str]) -> bool:
    """
    初始化MCP服务器

    Args:
        servers: 服务器配置字典 {名称: 启动命令}

    Returns:
        是否全部成功
    """
    host = get_mcp_host()
    success_count = 0

    for name, command in servers.items():
        if await host.add_server(name, command):
            success_count += 1
        else:
            logger.error(f"启动 {name} 失败")

    logger.info(f"MCP服务器初始化完成: {success_count}/{len(servers)} 成功")
    return success_count == len(servers)


async def shutdown_mcp_servers():
    """关闭所有MCP服务器"""
    global _mcp_host
    if _mcp_host:
        await _mcp_host.shutdown()
        _mcp_host = None
