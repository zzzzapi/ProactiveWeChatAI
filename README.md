# AI微信主动聊天机器人

基于WeChatPadPro协议开发的智能微信机器人，支持角色扮演和自主对话功能。

## 项目简介

AI微信主动聊天机器人是一个Python开发的微信聊天助手，可以自动回复消息，支持加载角色卡进行角色扮演，还可以根据对话情境主动发起聊天。项目依赖于[WeChatPadPro](https://github.com/luolin-ai/WeChatPadPro)项目提供的微信API接口服务，并使用[zzzzapi.com](https://zzzzapi.com/)作为AI中转API平台调用大型语言模型。

## 主要功能

- 🤖 **AI智能回复**：使用GPT-4o等大型语言模型进行对话
- 🎭 **角色扮演**：支持加载角色卡(Tavern格式)，让AI扮演特定角色
- 🔄 **自主对话**：AI会分析对话情境，在适当时机主动发起对话
- 📱 **微信消息监听**：可以监听特定微信号的消息
- 📊 **会话管理**：自动保存和加载对话历史
- 🖼️ **多格式角色卡**：支持从JSON或PNG格式加载角色卡

## 安装方法

1. 克隆项目到本地
   ```bash
   git clone https://github.com/zzzzapi/WeChat-AI-Bot.git
   cd WeChat-AI-Bot
   ```

2. 安装依赖
   ```bash
   pip install httpx websocket-client pillow
   ```

3. 设置配置信息
   在`AI微信主动聊天机器人.py`文件中，修改以下配置：
   ```python
   # 配置信息
   SERVER_URL = "http://你的WeChatPadPro服务地址:端口"
   
   # AI API配置（使用zzzzapi.com中转API）
   AI_API_URL = "https://zzzzapi.com/v1/chat/completions"
   AI_API_KEY = "你的zzzzapi密钥"
   ```

## 使用方法

1. 首先确保你已经按照[WeChatPadPro](https://github.com/luolin-ai/WeChatPadPro)的说明部署了微信API服务

2. 确保你已在[zzzzapi.com](https://zzzzapi.com/)注册并获取API密钥

3. 运行程序
   ```bash
   python AI微信主动聊天机器人.py
   ```

4. 按照提示输入：
   - 微信token (从WeChatPadPro服务获取)
   - 要监听的微信号或wxid (可以是微信号、wxid或留空使用文件传输助手)

5. 加载角色卡：
   - 选择菜单中的"1. 加载/更换角色卡"
   - 输入角色卡文件路径(支持JSON或PNG格式)

## 角色卡说明

程序支持Tavern格式的角色卡(V1/V2/V3版本)，可以是JSON文件或PNG图片(内嵌角色数据)。

角色卡示例结构：
```json
{
  "name": "角色名称",
  "description": "角色描述",
  "personality": "角色性格",
  "scenario": "角色所处场景",
  "first_mes": "角色的第一条消息"
}
```

## 依赖项目

本项目基于以下开源项目和服务：
- [WeChatPadPro](https://github.com/luolin-ai/WeChatPadPro) - 提供微信API接口
- [zzzzapi.com](https://zzzzapi.com/) - AI中转API平台，用于调用GPT等大模型

## 注意事项

- 本项目仅供学习和研究使用
- 使用前请确保遵守相关法律法规和微信使用条款
- 不要将此工具用于任何非法或侵犯他人隐私的用途
- 使用[zzzzapi.com](https://zzzzapi.com/)服务需遵守其服务条款

## 许可证

MIT License 
