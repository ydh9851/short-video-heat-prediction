# -*- coding: utf-8 -*-
"""
多平台短视频数据集统一 Schema 定义
====================================
本模块把「抖音 / YouTube / TikTok / B 站」等不同平台、不同语言、不同列名的原始导出文件，
归一到同一套列定义上，供导入器（ingest.py）、跨平台对比、分布漂移分析等模块复用。

统一列（UNIFIED_COLUMNS）：
    platform        平台标识（douyin / youtube / tiktok / bilibili）
    video_id        视频唯一标识
    video_category  内容类别（抖音为内容分区，YouTube 为 category，TikTok 为话题/类目）
    author_fans     作者粉丝数（YouTube = 频道订阅数，B 站 = UP 主粉丝数）
    play_cnt        播放量（YouTube = views，B 站 = 播放量）
    like_cnt        点赞量（TikTok = diggCount，B 站 = 点赞）
    comment_cnt     评论量（B 站 = 评论；另含弹幕）
    share_cnt       转发量（YouTube 无此字段，缺失记 0）
    collect_cnt     收藏量
    publish_time    发布时间（发布时即可获得的先验信息）
    heat            热度（加权互动量，本项目自定义口径，见 HEAT_FORMULA）

热度口径（跨平台统一，论文中需作为 limitation 说明）：
    heat = 播放量 + 3×点赞量 + 5×评论量 + 8×转发量
    与抖音基准数据集口径一致；缺字段的平台对应项按 0 计入。
"""
import re

UNIFIED_COLUMNS = [
    "platform", "video_id", "video_category", "author_fans",
    "play_cnt", "like_cnt", "comment_cnt", "share_cnt", "collect_cnt",
    "publish_time", "heat",
]

# 平台展示名
PLATFORM_NAMES = {
    "douyin": "抖音",
    "youtube": "YouTube",
    "tiktok": "TikTok",
    "bilibili": "哔哩哔哩",
}

# 热度权重
HEAT_W = {"play": 1.0, "like": 3.0, "comment": 5.0, "share": 8.0}

# 原始列名 -> 统一列名。中文别名、英文别名、驼峰、下划线写法都列出，
# 匹配时统一做「小写 + 去空格/下划线/点号/括号」归一化，因此大小写与写法差异不影响识别。
_ZH = {
    "video_id": ["视频ID", "视频id", "视频编号", "作品ID", "aid", "bvid", "BV号"],
    "video_category": ["视频类别", "视频分类", "类别", "分区", "内容类别", "标签", "话题"],
    "author_fans": ["作者粉丝数", "作者粉丝量", "粉丝数", "粉丝量", "UP主粉丝数", "订阅数"],
    "play_cnt": ["播放量", "播放数", "观看量", "观看数", "浏览量"],
    "like_cnt": ["点赞量", "点赞数", "点赞"],
    "comment_cnt": ["评论量", "评论数", "评论", "回复数"],
    "share_cnt": ["转发量", "转发数", "转发", "分享数", "分享量"],
    "collect_cnt": ["收藏量", "收藏数", "收藏", "投币数", "硬币数"],
    "publish_time": ["发布时间", "发布日期", "上传时间", "创建时间", "投稿时间", "时间"],
}

_EN = {
    "video_id": ["videoId", "video_id", "id", "item_id", "aweme_id", "aid"],
    "video_category": ["videoCategory", "video_category", "category", "category_id",
                       "categories", "main_category", "subcategory", "topic", "tags",
                       "video_category_id"],
    "author_fans": ["authorFans", "author_fans", "follower_count", "followerCount", "followers",
                    "fans", "subscriber_count", "subscriberCount", "subscribers",
                    "channel_subscriber_count", "channel_follower_count", "author_fans_count",
                    "followercount"],
    "play_cnt": ["playCnt", "play_cnt", "views", "view_count", "viewCount", "play_count",
                 "playCount", "plays", "video_view_count", "playcount"],
    "like_cnt": ["likeCnt", "like_cnt", "likes", "like_count", "likeCount", "diggCount",
                 "digg_count", "video_like_count", "diggcount"],
    "comment_cnt": ["commentCnt", "comment_cnt", "comments", "comment_count", "commentCount",
                    "comments_count", "reply_count", "video_comment_count", "commentcount"],
    "share_cnt": ["shareCnt", "share_cnt", "shares", "share_count", "shareCount",
                  "video_share_count", "sharecount"],
    "collect_cnt": ["collectCnt", "collect_cnt", "saves", "favorites", "favorite_count",
                    "collect_count", "bookmarks", "video_favorite_count"],
    "publish_time": ["publishTime", "publish_time", "publishedAt", "published_at",
                     "publish_date", "createTime", "create_time", "createTimeISO",
                     "post_datetime", "created_at", "upload_date", "trending_date",
                     "video_published_at"],
}


def _norm(s) -> str:
    """列名归一化：小写 + 去掉空格/下划线/点号/括号/横线，兼容中英文写法差异。"""
    return re.sub(r"[\s_\-\.\(\)（）\[\]：:]+", "", str(s)).lower()


def aliases_for(platform: str) -> dict:
    """返回某平台的「统一列 -> 候选原始列名列表」。中文别名对所有平台通用。"""
    out = {}
    for key, zh in _ZH.items():
        en = _EN.get(key, [])
        out[key] = list(dict.fromkeys(list(zh) + list(en)))
    # 平台专属补充
    extra = {
        "bilibili": {"video_id": ["bvid", "aid"], "collect_cnt": ["投币数", "硬币数", "收藏数"]},
        "youtube": {"video_category": ["category_id", "categories"], "author_fans":
                    ["subscriber_count", "channel_subscriber_count"]},
        "tiktok": {"video_category": ["main_category", "topic", "hashtags"],
                   "author_fans": ["follower_count", "followers"]},
    }.get(platform, {})
    for key, vals in extra.items():
        out.setdefault(key, [])
        out[key] = list(dict.fromkeys(out[key] + vals))
    return out


def resolve_columns(df, platform: str) -> dict:
    """把 DataFrame 的实际列名解析到统一列上。

    返回 {统一列: 实际列名 或 None}；其中 video_id/publish_time 之外允许缺失。
    """
    alias = aliases_for(platform)
    lookup = {_norm(c): c for c in df.columns}
    mapping = {}
    for key, cands in alias.items():
        hit = None
        for cand in cands:
            if _norm(cand) in lookup:
                hit = lookup[_norm(cand)]
                break
        mapping[key] = hit

    # 兜底：video_id 找不到时用「首个看起来像主键的列」
    if mapping.get("video_id") is None:
        for c in df.columns:
            if _norm(c) in ("videoid", "id", "bvid", "aid", "itemid", "awemeid"):
                mapping["video_id"] = c
                break
    return mapping


def compute_heat(df, share_available: bool):
    """按统一口径计算热度。share_available 为 False 时转发布单独按 0 计入。"""
    play = df["play_cnt"].fillna(0)
    like = df["like_cnt"].fillna(0)
    comment = df["comment_cnt"].fillna(0)
    share = df["share_cnt"].fillna(0) if share_available else 0
    return (HEAT_W["play"] * play + HEAT_W["like"] * like
            + HEAT_W["comment"] * comment + HEAT_W["share"] * share).astype(float)
