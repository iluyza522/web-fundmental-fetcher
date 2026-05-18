from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class User(BaseModel):
    id: int
    screen_name: str
    profile: str
    followers_count: int = 0
    friends_count: int = 0
    status_count: int = 0
    description: str | None = ""
    verified: bool = False
    verified_type: int = 0
    verified_description: str | None = ""
    gender: str = ""
    province: str = ""
    city: str = ""
    profile_image_url: str = ""
    photo_domain: str = ""
    stocks_count: int = 0
    created_at: Optional[int] = None


class CommunityPost(BaseModel):
    id: int
    user_id: int
    user: User
    created_at: int  # unix ms
    description: str
    text: str = ""
    title: str = ""
    target: str
    source: str = ""
    reply_count: int = 0
    like_count: int = 0
    fav_count: int = 0
    view_count: int = 0
    retweet_count: int = 0
    reward_count: int = 0
    hot: bool = False
    controversial: bool = False
    truncated: bool = False
    can_edit: bool = True
    editable: bool = True
    is_answer: bool = False
    is_bonus: bool = False
    is_reward: bool = False
    is_refused: bool = False
    mark: int = 0
    pic: str = ""
    flags: int = 0
    time_before: str = ""
    comment_id: int = 0

    @property
    def created_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.created_at / 1000)

    @property
    def cleaned_text(self) -> str:
        """Remove HTML tags and stock symbol links from text."""
        import re
        text = re.sub(r'<[^>]+>', '', self.text or self.description)
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#34;', '"').replace('&#39;', "'")
        return text.strip()


class StockCommunity(BaseModel):
    symbol: str
    stock_name: str = ""
    total_followers: int = 0
    posts: list[CommunityPost] = []
    total_posts: int = 0


class RecommendUser(BaseModel):
    id: int
    screen_name: str
    profile: str
    followers_count: int = 0
    friends_count: int = 0
    status_count: int = 0
    stocks_count: int = 0
    description: str | None = ""
    verified: bool = False
    verified_type: int = 0
    province: str | None = ""
    city: str | None = ""
    gender: str | None = ""
    profile_image_url: str = ""
    follow_me: bool = False
    following: bool = False


class APIResponse(BaseModel):
    about: str = ""
    count: int = 0
    key: str = ""
    items: list[CommunityPost] = []
    max_page: Optional[int] = None
    next_id: Optional[int] = None
