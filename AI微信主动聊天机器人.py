import httpx
import json
import time
import base64
import os
import io
import threading
import re
from PIL import Image
import datetime
import random
import websocket

# 配置信息
SERVER_URL = ""  # WeChatPad服务地址

# 对话历史
conversation_history = [
    {
        "role": "system",
        "content": "You are a helpful assistant."
    }
]

# AI API配置
AI_API_URL = "https://zzzzapi.com/v1/chat/completions"
AI_API_KEY = ""

# 发送微信文本消息
def send_wechat_message(to_user, message, token):
    """
    发送微信消息
    :param to_user: 接收者ID (wxid或特殊ID如filehelper)
    :param message: 要发送的消息内容
    :param token: 微信登录token
    :return: 是否发送成功
    """
    url = f"{SERVER_URL}/message/SendTextMessage?key={token}"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "MsgItem": [
            {
                "AtWxIDList": [],
                "ImageContent": "",
                "MsgType": 0,
                "TextContent": message,
                "ToUserName": to_user
            }
        ]
    }
    
    try:
        response = httpx.post(url, headers=headers, json=payload)
        data = response.json()
        
        if data.get("Code") == 200:
            result = data.get("Data", [])[0]
            success = result.get("isSendSuccess", False)
            
            if success:
                print(f"消息发送成功: '{message}' -> {to_user}")
                return True
            else:
                error = result.get("errMsg", "未知错误")
                print(f"消息发送失败: {error}")
        else:
            print(f"请求失败: {data.get('Text')}")
    except Exception as e:
        print(f"发送消息异常: {e}")
    
    return False

# 历史对话记录管理
class ConversationManager:
    def __init__(self, max_history=50):
        self.history = []
        self.system_message = {"role": "system", "content": "You are a helpful assistant."}
        self.max_history = max_history
        self.character_data = None
        self.conversation_file = "conversation_history.json"
        
        # 尝试加载历史记录
        self.load_history()
    
    def reset(self):
        """重置对话历史"""
        self.history = []
        self.initialize_with_system_message()
    
    def initialize_with_system_message(self):
        """使用系统消息初始化历史记录"""
        self.history = [self.system_message]
    
    def set_character(self, character_data):
        """设置角色并更新系统消息"""
        self.character_data = character_data
        
        # 验证角色卡
        card_validator = TavernCardValidator(character_data)
        card_version = card_validator.validate()
        
        if not card_version:
            print(f"角色卡验证失败: {card_validator.lastValidationError}")
            return False
        
        # 根据角色卡版本设置系统提示词
        if card_version == 1:
            # V1格式
            system_content = f"You are {character_data.get('name', 'Assistant')}, {character_data.get('description', '')}. Your personality: {character_data.get('personality', '')}. Scenario: {character_data.get('scenario', '')}"
            char_name = character_data.get('name', 'Assistant')
        else:
            # V2/V3格式
            data = character_data.get('data', {})
            system_content = data.get('system_prompt', '') or \
                           f"You are {data.get('name', 'Assistant')}, {data.get('description', '')}. Your personality: {data.get('personality', '')}. Scenario: {data.get('scenario', '')}"
            char_name = data.get('name', 'Assistant')
        
        # 更新系统消息
        self.system_message = {"role": "system", "content": system_content}
        
        # 重置历史记录并添加第一条消息
        self.reset()
        
        # 添加角色的第一条消息
        first_message = ""
        if card_version == 1:
            first_message = character_data.get('first_mes', '')
        else:
            first_message = character_data.get('data', {}).get('first_mes', '')
        
        if first_message:
            self.add_message("assistant", first_message)
            print(f"{char_name}: {first_message}")
        
        print(f"已加载角色卡: {char_name} (版本 V{card_version})")
        return True
    
    def add_message(self, role, content):
        """添加消息到历史记录"""
        self.history.append({"role": role, "content": content})
        
        # 如果超过最大历史记录数，删除最早的非系统消息
        if len(self.history) > self.max_history + 1:  # +1是因为系统消息
            # 找到第一个非系统消息
            for i in range(1, len(self.history)):
                if self.history[i]["role"] != "system":
                    self.history.pop(i)
                    break
        
        # 保存历史记录
        self.save_history()
    
    def get_history_for_api(self):
        """获取用于API调用的历史记录"""
        return self.history.copy()
    
    def get_formatted_history(self, include_system=False, max_items=None):
        """获取格式化的历史记录文本"""
        result = ""
        history = self.history.copy()
        
        if not include_system:
            history = [msg for msg in history if msg["role"] != "system"]
        
        if max_items and len(history) > max_items:
            history = history[-max_items:]
        
        for msg in history:
            role_name = "系统" if msg["role"] == "system" else \
                        "用户" if msg["role"] == "user" else \
                        self.get_character_name()
            result += f"{role_name}: {msg['content']}\n\n"
        
        return result
    
    def save_history(self):
        """保存对话历史到文件"""
        try:
            with open(self.conversation_file, 'w', encoding='utf-8') as f:
                save_data = {
                    "history": self.history,
                    "timestamp": time.time(),
                    "character": self.character_data
                }
                json.dump(save_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存对话历史失败: {e}")
    
    def load_history(self):
        """从文件加载对话历史"""
        try:
            if os.path.exists(self.conversation_file):
                with open(self.conversation_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    self.history = data.get("history", [])
                    
                    # 如果有角色数据，也加载
                    if data.get("character"):
                        self.character_data = data.get("character")
                        
                    print(f"已加载{len(self.history)}条历史消息")
                    return True
        except Exception as e:
            print(f"加载对话历史失败: {e}")
        
        # 如果加载失败，初始化空历史
        self.initialize_with_system_message()
        return False
    
    def get_character_name(self):
        """获取角色名称"""
        if not self.character_data:
            return "Assistant"
        
        card_validator = TavernCardValidator(self.character_data)
        card_version = card_validator.validate()
        
        if card_version == 1:
            return self.character_data.get("name", "Assistant")
        else:
            return self.character_data.get("data", {}).get("name", "Assistant")

# TavernCardValidator类 - 角色卡验证器
class TavernCardValidator:
    def __init__(self, card):
        self.card = card
        self.lastValidationError = None

    def validate(self):
        self.lastValidationError = None

        if self.validateV1():
            return 1

        if self.validateV2():
            return 2

        if self.validateV3():
            return 3

        return False

    def validateV1(self):
        required_fields = ['name', 'description', 'personality', 'scenario', 'first_mes', 'mes_example']
        for field in required_fields:
            if field not in self.card:
                self.lastValidationError = field
                return False
        return True

    def validateV2(self):
        # 验证spec字段
        if self.card.get('spec') != 'chara_card_v2':
            self.lastValidationError = 'spec'
            return False
        
        # 验证版本
        if self.card.get('spec_version') != '2.0':
            self.lastValidationError = 'spec_version'
            return False
        
        # 验证数据
        data = self.card.get('data')
        if not data:
            self.lastValidationError = 'No tavern card data found'
            return False
        
        required_fields = ['name', 'description', 'personality', 'scenario', 'first_mes', 'mes_example', 
                           'creator_notes', 'system_prompt', 'post_history_instructions', 
                           'alternate_greetings', 'tags', 'creator', 'character_version', 'extensions']
        
        for field in required_fields:
            if field not in data:
                self.lastValidationError = f'data.{field}'
                return False
        
        return (isinstance(data.get('alternate_greetings'), list) and 
                isinstance(data.get('tags'), list) and 
                isinstance(data.get('extensions'), dict))

    def validateV3(self):
        # 验证spec字段
        if self.card.get('spec') != 'chara_card_v3':
            self.lastValidationError = 'spec'
            return False
        
        # 验证版本
        spec_version = self.card.get('spec_version', '0')
        try:
            version_num = float(spec_version)
            if version_num < 3.0 or version_num >= 4.0:
                self.lastValidationError = 'spec_version'
                return False
        except:
            self.lastValidationError = 'Invalid spec_version'
            return False
        
        # 验证数据
        data = self.card.get('data')
        if not data or not isinstance(data, dict):
            self.lastValidationError = 'No tavern card data found'
            return False
        
        return True

# 角色卡处理
def load_character_card(file_path):
    """加载角色卡（支持JSON和PNG格式）"""
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return None
    
    file_ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if file_ext == '.json':
            # 加载JSON文件
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        elif file_ext == '.png':
            # 从PNG中提取角色数据
            return extract_character_from_png(file_path)
        else:
            print(f"不支持的文件格式: {file_ext}")
            return None
    except Exception as e:
        print(f"加载角色卡失败: {e}")
        return None

def extract_character_from_png(png_path):
    """从PNG图片中提取角色卡数据"""
    try:
        # 读取PNG文件
        with open(png_path, 'rb') as f:
            buffer = f.read()
        
        # 提取文本块
        chunks = extract_chunks(buffer)
        text_chunks = [chunk for chunk in chunks if chunk["type"] == b'tEXt']
        
        if not text_chunks:
            print("PNG图片中不包含任何文本块")
            return None
        
        # 优先查找ccv3格式的数据
        ccv3_data = None
        chara_data = None
        
        for chunk in text_chunks:
            keyword, text = decode_text_chunk(chunk["data"])
            if keyword.lower() == 'ccv3':
                ccv3_data = text
            elif keyword.lower() == 'chara':
                chara_data = text
        
        # 尝试解析ccv3数据
        if ccv3_data:
            try:
                decoded_data = base64.b64decode(ccv3_data).decode('utf-8')
                return json.loads(decoded_data)
            except:
                pass
        
        # 如果没有ccv3或解析失败，尝试解析chara数据
        if chara_data:
            try:
                decoded_data = base64.b64decode(chara_data).decode('utf-8')
                return json.loads(decoded_data)
            except:
                pass
        
        print("无法从PNG提取角色数据")
        return None
    except Exception as e:
        print(f"提取角色数据时出错: {e}")
        return None

# PNG解析辅助函数
def extract_chunks(data):
    """提取PNG中的数据块"""
    chunks = []
    
    # PNG头部是8字节
    pos = 8
    
    while pos < len(data):
        # 每个块由4字节长度、4字节类型、数据和4字节CRC组成
        chunk_length = int.from_bytes(data[pos:pos+4], 'big')
        chunk_type = data[pos+4:pos+8]
        chunk_data = data[pos+8:pos+8+chunk_length]
        
        chunks.append({
            "length": chunk_length,
            "type": chunk_type,
            "data": chunk_data
        })
        
        # 移动到下一个块
        pos += 12 + chunk_length
    
    return chunks

def decode_text_chunk(data):
    """解码文本块数据"""
    # 文本块包含一个关键字（以null字节结束）和文本值
    null_pos = data.find(0)
    if null_pos == -1:
        return None, None
    
    keyword = data[:null_pos].decode('latin1')
    text = data[null_pos+1:].decode('latin1')
    
    return keyword, text

# AI自主消息系统
class AIAutonomousSystem:
    def __init__(self, token, conversation_manager):
        self.token = token
        self.wxid = "filehelper"  # 默认发送到文件传输助手
        self.conversation_manager = conversation_manager
        self.running = False
        self.thread = None
        self.last_analysis_time = 0
        self.analyze_interval = 60  # 每60秒分析一次
        self.is_analyzing = False
        self.last_user_message_time = time.time()
        self.listener = None
    
    def start(self):
        """启动自主消息系统"""
        if self.running:
            print("AI自主消息系统已在运行中")
            return
        
        if not self.conversation_manager.character_data:
            print("请先加载角色卡再启动自主消息系统")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._autonomous_loop)
        self.thread.daemon = True
        self.thread.start()
        print(f"已启动AI自主消息系统 (目标: {self.wxid})")
        
        # 立即进行第一次分析
        self.analyze_now()
    
    def stop(self):
        """停止自主消息系统"""
        if not self.running:
            print("AI自主消息系统未运行")
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        print("已停止AI自主消息系统")
    
    def record_user_activity(self):
        """记录用户活动时间"""
        self.last_user_message_time = time.time()
    
    def analyze_now(self):
        """立即分析对话状态"""
        if not self.is_analyzing and self.running:
            self._analyze_conversation_state()
    
    def _autonomous_loop(self):
        """自主消息循环"""
        while self.running:
            try:
                now = time.time()
                # 只在间隔时间到了才分析
                if now - self.last_analysis_time > self.analyze_interval:
                    # 确保WebSocket连接正常后再进行分析
                    if hasattr(self, 'listener') and self.listener and self.listener.ws and self.listener.ws.sock and self.listener.ws.sock.connected:
                        self._analyze_conversation_state()
                        self.last_analysis_time = now
                    else:
                        print("WebSocket连接未就绪，跳过本次分析")
                
                time.sleep(5)  # 检查间隔
            except Exception as e:
                print(f"自主消息循环出错: {e}")
                time.sleep(5)
    
    def _analyze_conversation_state(self):
        """分析对话状态，决定是否发送消息"""
        if self.is_analyzing:
            return
        
        self.is_analyzing = True
        
        try:
            # 创建分析提示词
            system_prompt = "你将分析一个角色是否会在当前对话情境中自然地主动发言。分析时使用角色卡中的原始定义。请返回JSON格式：{\"shouldSendMessage\": true/false, \"reason\": \"理由\", \"messageType\": \"消息类型\"}"
            user_prompt = f"""以下是原始角色卡数据：
```json
{json.dumps(self.conversation_manager.character_data, ensure_ascii=False, indent=2)}
```

完整对话历史记录（从开始到现在）：
{self.conversation_manager.get_formatted_history(include_system=False)}

请根据角色卡原始数据与完整对话历史，仔细分析判断角色是否会在当前情境下主动发言。分析时考虑：
1. 角色的个性特点和内在动机
2. 当前对话的情感氛围和上下文
3. 角色与用户之间建立的关系
4. 对话中的重要线索或信息
5. 角色面临的情景和环境

只有当符合角色的性格和当前情境时，才返回shouldSendMessage=true。
记住，一个写得好的角色不会频繁打断用户，而是会在合适的时机自然地主动发言。"""

            # 发送分析请求
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False
            }
            
            response = httpx.post(AI_API_URL, headers=headers, json=payload)
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                analysis_result = data["choices"][0]["message"]["content"]
                
                # 解析JSON结果 - 处理可能的markdown格式
                try:
                    # 尝试从markdown代码块中提取JSON
                    json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', analysis_result)
                    if json_match:
                        decision = json.loads(json_match.group(1))
                    else:
                        # 直接尝试解析整个文本
                        decision = json.loads(analysis_result)
                    
                    if decision.get("shouldSendMessage"):
                        print(f"[分析] {self.conversation_manager.get_character_name()}会在此时主动发言，原因：{decision.get('reason')}")
                        self._generate_and_send_message(decision.get("messageType", "一般对话"))
                    else:
                        print(f"[分析] {self.conversation_manager.get_character_name()}此时不会主动发言，原因：{decision.get('reason')}")
                
                except json.JSONDecodeError:
                    # 如果JSON解析失败，使用简单的文本匹配
                    if "应该主动发言" in analysis_result.lower() and "不应该主动发言" not in analysis_result.lower():
                        print("[分析] 基于文本分析，角色应该主动发言")
                        self._generate_and_send_message("一般对话")
                    else:
                        print("[分析] 基于文本分析，角色不应该主动发言")
            
            else:
                print("分析API返回格式错误")
        
        except Exception as e:
            print(f"分析对话状态出错: {e}")
        
        finally:
            self.is_analyzing = False
    
    def _generate_and_send_message(self, message_type):
        """生成并发送自主消息"""
        try:
            # 创建生成消息的提示词
            system_prompt = "根据角色卡定义和对话历史生成一条符合当前情境的自然回复。"
            user_prompt = f"""角色卡数据：
```json
{json.dumps(self.conversation_manager.character_data, ensure_ascii=False, indent=2)}
```

完整对话历史记录：
{self.conversation_manager.get_formatted_history(include_system=False)}

请直接输出角色在此时此刻会说的话，不添加额外说明。"""

            # 发送请求
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False
            }
            
            response = httpx.post(AI_API_URL, headers=headers, json=payload)
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                message = data["choices"][0]["message"]["content"]
                
                # 添加到对话历史
                self.conversation_manager.add_message("assistant", message)
                
                # 发送消息
                send_wechat_message(self.wxid, message, self.token)
                
                # 输出提示
                print(f"\n========== 自主消息 ==========")
                print(f"{self.conversation_manager.get_character_name()}: {message}")
                print(f"==============================\n")
            
            else:
                print("生成消息API返回格式错误")
        
        except Exception as e:
            print(f"生成和发送自主消息出错: {e}")

# 从AI获取回复
def get_ai_response(user_message, conversation_manager):
    # 将用户消息添加到对话历史
    conversation_manager.add_message("user", user_message)
    
    # 调用AI API
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-4o",
        "messages": conversation_manager.get_history_for_api(),
        "stream": False
    }
    
    try:
        response = httpx.post(AI_API_URL, headers=headers, json=payload)
        data = response.json()
        
        if "choices" in data and len(data["choices"]) > 0:
            ai_response = data["choices"][0]["message"]["content"]
            
            # 将AI回复添加到对话历史
            conversation_manager.add_message("assistant", ai_response)
            
            return ai_response
        else:
            error_message = "AI响应格式错误"
            print(error_message)
            return f"抱歉，生成回复时出现问题: {error_message}"
    except Exception as e:
        error_message = str(e)
        print(f"调用AI API失败: {error_message}")
        return f"抱歉，无法连接到AI服务: {error_message}"

# 添加微信消息监听器类
class WeChatMessageListener:
    def __init__(self, server_url, token, conversation_manager, ai_system=None):
        self.server_url = server_url
        self.token = token
        self.ws = None
        self.conversation_manager = conversation_manager
        self.ai_system = ai_system
        self.running = False
        self.thread = None
        self.target_wxid = None  # 添加目标wxid属性，为None时接收所有消息
        self.debug_mode = False  # 调试模式，用于查看所有消息
        self.processed_messages = {}  # 添加已处理消息缓存
        
    def set_target_wxid(self, wxid):
        """设置要监听的目标wxid"""
        self.target_wxid = wxid
        if wxid:
            print(f"已设置只监听wxid: {wxid}的消息")
        else:
            print("已设置监听所有微信号的消息")
            
    def set_debug_mode(self, enabled=True):
        """设置调试模式，开启后会显示所有收到的WebSocket消息"""
        self.debug_mode = enabled
        print(f"调试模式: {'开启' if enabled else '关闭'}")
        
    def start(self):
        """启动WebSocket监听"""
        if self.running:
            print("消息监听器已在运行中")
            return False
            
        self.running = True
        self.thread = threading.Thread(target=self._connect_websocket)
        self.thread.daemon = True
        self.thread.start()
        return True
        
    def stop(self):
        """停止WebSocket监听"""
        if not self.running:
            return
            
        self.running = False
        if self.ws:
            self.ws.close()
        
        if self.thread:
            self.thread.join(timeout=1.0)
        print("已停止消息监听")
    
    def _connect_websocket(self):
        """连接WebSocket"""
        # 修改WebSocket路径，添加/ws/前缀
        ws_url = f"{self.server_url.replace('http://', 'ws://')}/ws/GetSyncMsg?key={self.token}"
        print(f"正在连接WebSocket: {ws_url}")
        
        # 配置WebSocket
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        
        # 最大重试次数
        max_retries = 5
        retry_count = 0
        
        while self.running and retry_count < max_retries:
            try:
                # 运行WebSocket客户端
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
                
                # 如果WebSocket关闭但程序仍在运行，则尝试重连
                if self.running:
                    retry_count += 1
                    print(f"WebSocket连接断开，尝试重连... (尝试 {retry_count}/{max_retries})")
                    time.sleep(5)
                else:
                    break
            except Exception as e:
                retry_count += 1
                print(f"WebSocket连接异常: {e}，尝试重连... (尝试 {retry_count}/{max_retries})")
                time.sleep(5)
        
        if retry_count >= max_retries and self.running:
            print("WebSocket连接失败，已达到最大重试次数。请检查网络或服务器状态。")
            print("提示: 您可以继续使用其他功能，或尝试重新启动程序。")
    
    def _on_message(self, ws, message):
        """处理收到的消息"""
        try:
            # 解析消息
            data = json.loads(message)
            
            # 调试模式下打印所有消息
            if self.debug_mode:
                print(f"[DEBUG] 收到WebSocket消息: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            # 获取消息发送者ID
            from_wxid = data.get('from_user_name', {}).get('str', '')
            
            # 立即检查是否是目标wxid的消息，如果设置了target_wxid且消息不是来自目标，直接返回
            if self.target_wxid and from_wxid != self.target_wxid:
                # 完全静默处理，不显示任何提示，就像这条消息从未收到过一样
                return
                
            # 判断消息类型和方向
            to_wxid = data.get('to_user_name', {}).get('str', '')
            is_sent_by_self = data.get('is_self_msg', 0) == 1
            
            # 过滤自己发送的消息和特殊账号
            if (from_wxid.startswith('gh_') or 
                from_wxid == 'weixin' or 
                from_wxid == to_wxid or
                is_sent_by_self):
                return
                
            content = data.get('content', {}).get('str', '')
            if not content:  # 添加对空内容的检查
                return
            
            # 处理群消息
            if '@chatroom' in from_wxid:
                # 提取发送者ID和消息内容
                parts = content.split(':', 1)
                if len(parts) > 1:
                    sender_id = parts[0]
                    message_text = parts[1].strip()
                else:
                    return
            else:
                # 私聊消息
                message_text = content
            
            # 添加消息去重逻辑
            # 使用消息内容和发送者作为唯一标识
            msg_id = f"{from_wxid}:{message_text}"
            current_time = time.time()
            
            # 检查是否已处理过这条消息(5秒内的相同消息视为重复)
            if msg_id in self.processed_messages:
                last_time = self.processed_messages[msg_id]
                if current_time - last_time < 5:  # 5秒内的相同消息不重复处理
                    return
            
            # 记录这条消息已被处理
            self.processed_messages[msg_id] = current_time
            
            # 清理过期的消息记录(保留最近10分钟内的)
            self.processed_messages = {k: v for k, v in self.processed_messages.items() 
                                    if current_time - v < 600}
            
            # 记录用户活动
            if self.ai_system:
                self.ai_system.record_user_activity()
                # 直接设置ai_system的wxid属性
                self.ai_system.wxid = from_wxid
            
            # 处理消息并生成回复
            print(f"\n收到消息 [{from_wxid}]: {message_text}")
            
            # 添加时间戳和消息来源标记，以区分不同消息
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] 开始处理消息...")
            
            ai_response = get_ai_response(message_text, self.conversation_manager)
            
            # 发送回复
            success = send_wechat_message(from_wxid, ai_response, self.token)
            if success:
                print(f"发送回复 -> [{from_wxid}]: {ai_response}\n")
            else:
                print(f"回复发送失败，请检查网络和token是否有效\n")
            
        except json.JSONDecodeError:
            print("收到无效的JSON数据")
        except Exception as e:
            print(f"处理收到的消息出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_error(self, ws, error):
        """处理WebSocket错误"""
        print(f"WebSocket错误: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """处理WebSocket关闭"""
        print(f"WebSocket连接关闭: {close_status_code} {close_msg}")
    
    def _on_open(self, ws):
        """处理WebSocket连接建立"""
        print("WebSocket连接已建立，开始接收消息")

    def is_connected(self):
        """检查WebSocket连接状态"""
        return (self.ws and 
                hasattr(self.ws, 'sock') and 
                self.ws.sock and 
                hasattr(self.ws.sock, 'connected') and 
                self.ws.sock.connected)

    def reconnect(self):
        """强制重新连接WebSocket"""
        print("正在尝试重新连接WebSocket...")
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        
        # 重新启动连接线程
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        
        self.thread = threading.Thread(target=self._connect_websocket)
        self.thread.daemon = True
        self.thread.start()
        return True

# 添加根据微信号查找wxid的功能
def find_wxid_by_wechat_account(token, wechat_account):
    """根据微信号查找wxid"""
    # 使用friend/SearchContact API查找
    try:
        url = f"{SERVER_URL}/friend/SearchContact?key={token}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "FromScene": 0,
            "OpCode": 0, 
            "SearchScene": 0,
            "UserName": wechat_account
        }
        
        response = httpx.post(url, headers=headers, json=payload)
        
        try:
            data = response.json()
            
            if data.get("Code") == 200 and "Data" in data:
                # 从返回数据中提取wxid
                user_name = data["Data"].get("user_name", {}).get("str")
                if user_name:
                    print(f"已找到微信号 {wechat_account} 对应的wxid: {user_name}")
                    return user_name
        except json.JSONDecodeError:
            print("搜索API返回的数据格式异常")
    except Exception as e:
        print(f"搜索联系人失败: {e}")
    
    print(f"未找到微信号 {wechat_account} 对应的wxid")
    return None

# 修改主菜单，简化选项
def show_menu():
    """显示简化后的主菜单"""
    print("\n==== 微信AI助手 ====")
    print("1. 加载/更换角色卡")
    print("0. 退出程序")
    print("===================")

# 修改主程序流程
if __name__ == "__main__":
    # 打印程序启动信息
    print("=" * 50)
    print("微信AI助手 - 启动中...")
    print("=" * 50)
    
    token = input("请输入微信token: ")
    
    # 初始化对话管理器
    conversation_manager = ConversationManager()
    
    # 提示输入监听目标
    target_input = input("请输入要监听的微信号或wxid: ")
    
    # 如果输入为空，使用文件传输助手作为默认值
    if not target_input:
        target_input = "filehelper"
        print("未输入目标，将使用文件传输助手作为默认目标")
    
    # 检查输入的是微信号还是wxid
    if target_input.startswith("wxid_") or target_input == "filehelper":
        # 如果输入的是wxid，直接使用
        target_wxid = target_input
    else:
        # 如果输入的是微信号，查找对应的wxid
        print(f"正在查找微信号 {target_input} 对应的wxid...")
        target_wxid = find_wxid_by_wechat_account(token, target_input)
        
        # 如果找不到对应的wxid，提示用户
        if not target_wxid:
            print(f"警告: 未找到微信号 {target_input} 对应的wxid，将使用原始输入作为wxid")
            target_wxid = target_input
    
    # 初始化消息监听器
    listener = WeChatMessageListener(SERVER_URL, token, conversation_manager, None)
    
    # 设置监听目标
    listener.set_target_wxid(target_wxid)
    print(f"已设置消息接收和发送目标: {target_wxid}")
    
    # 初始化AI自主系统并设置关联
    ai_system = AIAutonomousSystem(token, conversation_manager)
    ai_system.listener = listener  # 添加对listener的引用
    ai_system.wxid = target_wxid  # 设置AI系统发送目标
    listener.ai_system = ai_system  # 关联AI系统到监听器
    
    # 自动启动监听器
    listener.start()
    print("已自动启动消息监听器")
    
    # 自动加载默认角色卡(如果存在)
    default_card_paths = ["角色卡.json", "character.json", "default.json"]
    loaded_default = False
    
    for card_path in default_card_paths:
        if os.path.exists(card_path):
            print(f"发现默认角色卡: {card_path}，正在加载...")
            character_data = load_character_card(card_path)
            if character_data and conversation_manager.set_character(character_data):
                print("默认角色卡加载成功，自动启动AI自主系统")
                ai_system.start()
                loaded_default = True
                break
    
    # 主循环
    while True:
        show_menu()
        choice = input("请选择操作 (0-1): ")
        
        if choice == "1":
            # 加载角色卡
            file_path = input("请输入角色卡文件路径 (PNG或JSON): ")
            if not file_path:
                print("未输入文件路径，操作取消")
                continue
                
            character_data = load_character_card(file_path)
            if character_data:
                if conversation_manager.set_character(character_data):
                    print("角色卡加载成功，自动启动AI自主系统")
                    # 如果AI系统还未启动，启动它
                    if not ai_system.running:
                        ai_system.start()
                    else:
                        # 已经启动，只需触发立即分析
                        ai_system.analyze_now()
            
        elif choice == "0":
            # 退出程序
            print("正在退出程序...")
            ai_system.stop()
            if listener:
                listener.stop()
            break
            
        else:
            print("无效选择，请重新输入")