import random
import json
import os
from datetime import date
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register

@register("astrbot_plugin_marry_only", "你的名字", "从群成员中随机匹配今日伴侣，每日更新", "1.0.0")
class MarryOnlyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 数据存储路径：data/plugins/astrbot_plugin_marry_only/
        plugin_dir = os.path.dirname(__file__)
        self.data_dir = os.path.join(plugin_dir, '../../data/astrbot_plugin_marry_only')
        os.makedirs(self.data_dir, exist_ok=True)
        self.marry_file = os.path.join(self.data_dir, 'marry_data.json')

    def _read_json(self, file_path: str) -> dict:
        """读取 JSON 文件，如果不存在则返回空字典"""
        if not os.path.exists(file_path):
            return {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_json(self, file_path: str, data: dict) -> None:
        """将数据写入 JSON 文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # 可记录日志，此处忽略
            pass

    @filter.command("marry")
    async def marry(self, event: AstrMessageEvent):
        """今日随机匹配一名群友作为老婆"""
        # 仅限群聊使用
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("该指令只能在群聊中使用。")
            return

        user_id = event.get_sender_id()
        today_str = str(date.today())
        # 以群组+日期为键，确保不同群组数据隔离，且每日重置
        group_key = f"{group_id}_{today_str}"

        marry_data = self._read_json(self.marry_file)
        if group_key not in marry_data:
            marry_data[group_key] = {}  # 存储 {用户ID: 匹配对象ID}

        # 检查用户今天是否已经匹配过
        if user_id in marry_data[group_key]:
            mate_id = marry_data[group_key][user_id]
            yield event.plain_result(f"你今天的老婆是 {mate_id}，要幸福哦！")
            return

        # 获取群成员列表
        try:
            # 调用 OneBot API 获取群成员列表
            # 假设 bot 对象可以通过 event.bot 获取
            bot = event.bot
            if not bot:
                yield event.plain_result("错误：无法获取机器人实例")
                return

            # 调用 get_group_member_list API，返回成员信息列表
            member_list = await bot.call_action(
                action="get_group_member_list",
                group_id=group_id
            )

            if not member_list or len(member_list) < 2:
                yield event.plain_result("群成员不足两人，无法进行匹配。")
                return

            # 提取所有群成员的 QQ 号
            member_ids = [str(member['user_id']) for member in member_list]

            # 排除自己
            if user_id in member_ids:
                member_ids.remove(user_id)

            # 排除机器人自身（如果不想让机器人被匹配）
            # 获取机器人自己的 QQ 号（可以通过 bot.self_id 或类似方式）
            # 这里假设可以通过 bot.api.self_id 获取，如果不行可以跳过
            try:
                self_id = str(bot.self_id)
                if self_id in member_ids:
                    member_ids.remove(self_id)
            except:
                pass  # 如果无法获取机器人自身，则忽略

            if not member_ids:
                yield event.plain_result("排除自身后没有可匹配的群成员。")
                return

            # 随机选择一个
            mate_id = random.choice(member_ids)

            # 保存匹配结果
            marry_data[group_key][user_id] = mate_id
            self._write_json(self.marry_file, marry_data)

            # 获取发送者昵称，让消息更友好
            sender_name = event.get_sender_name()
            yield event.plain_result(f"🎉 恭喜 {sender_name}，今日你的老婆是 {mate_id}！")

        except Exception as e:
            # 捕获所有异常，返回友好提示
            yield event.plain_result(f"匹配失败，请稍后再试。错误信息：{str(e)}")
