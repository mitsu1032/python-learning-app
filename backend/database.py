"""
SQLite データベース設定とモデル定義
Python学習支援アプリケーション用
"""

from datetime import datetime, timedelta
from typing import Optional, List
from collections import Counter
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
import os

# データベースファイルのパス（環境変数またはデフォルト）
DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "data", "learning.db"))
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# SQLAlchemyエンジンとセッション設定
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ========== モデル定義 ==========

class User(Base):
    """ユーザー情報（プロトタイプでは1ユーザー想定）"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # リレーション
    search_history = relationship("SearchHistory", back_populates="user")
    understanding_levels = relationship("UnderstandingLevel", back_populates="user")


class SearchHistory(Base):
    """検索履歴（用語、タイムスタンプ、検索回数）"""
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    term = Column(String(200), index=True)  # 検索した用語
    searched_at = Column(DateTime, default=datetime.utcnow)
    search_count = Column(Integer, default=1)  # 検索回数

    # リレーション
    user = relationship("User", back_populates="search_history")


class UnderstandingLevel(Base):
    """理解度記録（用語、到達レベル、タイムスタンプ）"""
    __tablename__ = "understanding_levels"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    term = Column(String(200), index=True)  # 用語
    level = Column(Integer, default=1)  # 到達した理解レベル（1-3）
    updated_at = Column(DateTime, default=datetime.utcnow)

    # リレーション
    user = relationship("User", back_populates="understanding_levels")


class ExplanationCache(Base):
    """生成された解説のキャッシュ"""
    __tablename__ = "explanations_cache"

    id = Column(Integer, primary_key=True, index=True)
    term = Column(String(200), index=True)  # 用語
    level = Column(Integer)  # 解説レベル（1-3）
    explanation = Column(Text)  # 生成された解説内容
    created_at = Column(DateTime, default=datetime.utcnow)

    class Config:
        # 同じ用語・レベルの組み合わせはユニーク
        unique_together = ("term", "level")


class Achievement(Base):
    """達成バッジ・実績"""
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    badge_id = Column(String(50), index=True)  # バッジの識別子
    badge_name = Column(String(100))  # バッジ名
    badge_icon = Column(String(10))  # 絵文字アイコン
    badge_description = Column(String(500))  # バッジの説明
    earned_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="achievements")


class LearningPath(Base):
    """学習パス設定"""
    __tablename__ = "learning_paths"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    path_id = Column(String(50), index=True)  # パスの識別子
    current_step = Column(Integer, default=0)  # 現在のステップ
    completed = Column(Integer, default=0)  # 完了フラグ (0 or 1)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="learning_paths")


class PracticeResult(Base):
    """練習問題の結果"""
    __tablename__ = "practice_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    term = Column(String(200), index=True)  # 関連用語
    problem_id = Column(String(50))  # 問題ID
    user_code = Column(Text)  # ユーザーが書いたコード
    is_correct = Column(Integer, default=0)  # 正解かどうか (0 or 1)
    attempted_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="practice_results")


class CodeExecutionHistory(Base):
    """コード実行履歴"""
    __tablename__ = "code_execution_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    term = Column(String(200), index=True)  # 関連用語
    code = Column(Text)  # 実行したコード
    output = Column(Text, nullable=True)  # 実行結果
    error = Column(Text, nullable=True)  # エラーメッセージ
    executed_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="code_executions")


class ReviewSchedule(Base):
    """復習スケジュール"""
    __tablename__ = "review_schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    term = Column(String(200), index=True)  # 復習対象の用語
    next_review_at = Column(DateTime)  # 次の復習日時
    review_count = Column(Integer, default=0)  # 復習回数
    interval_days = Column(Integer, default=1)  # 復習間隔（日）
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="review_schedules")


# ========== データベース操作関数 ==========

def init_db():
    """データベースの初期化（テーブル作成）"""
    # dataディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db():
    """データベースセッションを取得（依存性注入用）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_user(db, username: str = "default_user") -> User:
    """ユーザーを取得または作成"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def normalize_term(term: str) -> str:
    """用語を正規化（小文字に変換、前後の空白を削除）"""
    return term.strip().lower()


def add_search_history(db, user_id: int, term: str) -> SearchHistory:
    """検索履歴を追加（同じ用語は検索回数をインクリメント）"""
    # 用語を正規化
    normalized_term = normalize_term(term)

    # 既存の履歴をチェック（正規化された用語で検索）
    existing = db.query(SearchHistory)\
        .filter(SearchHistory.user_id == user_id, SearchHistory.term == normalized_term)\
        .first()

    now = datetime.utcnow()

    if existing:
        # 既存の履歴がある場合はタイムスタンプと検索回数を更新
        new_count = (existing.search_count or 1) + 1
        print(f"📝 Updating history for '{normalized_term}': count={existing.search_count} -> {new_count}", flush=True)
        db.query(SearchHistory)\
            .filter(SearchHistory.id == existing.id)\
            .update({"searched_at": now, "search_count": new_count}, synchronize_session='fetch')
        db.commit()
        # 更新後のデータを再取得
        existing = db.query(SearchHistory).filter(SearchHistory.id == existing.id).first()
        return existing
    else:
        # 新規の場合は作成（正規化された用語で保存）
        print(f"📝 Creating new history for '{normalized_term}'", flush=True)
        history = SearchHistory(user_id=user_id, term=normalized_term, searched_at=now, search_count=1)
        db.add(history)
        db.commit()
        db.refresh(history)
        return history


def get_search_history(db, user_id: int, limit: int = 50) -> list:
    """検索履歴を取得"""
    return db.query(SearchHistory)\
        .filter(SearchHistory.user_id == user_id)\
        .order_by(SearchHistory.searched_at.desc())\
        .limit(limit)\
        .all()


def update_understanding_level(db, user_id: int, term: str, level: int) -> UnderstandingLevel:
    """理解度レベルを更新または作成"""
    # 用語を正規化
    normalized_term = normalize_term(term)

    understanding = db.query(UnderstandingLevel)\
        .filter(UnderstandingLevel.user_id == user_id, UnderstandingLevel.term == normalized_term)\
        .first()

    if understanding:
        understanding.level = level
        understanding.updated_at = datetime.utcnow()
    else:
        understanding = UnderstandingLevel(user_id=user_id, term=normalized_term, level=level)
        db.add(understanding)

    db.commit()
    db.refresh(understanding)
    return understanding


def get_understanding_level(db, user_id: int, term: str) -> int:
    """特定用語の理解度レベルを取得（未記録の場合は0）"""
    normalized_term = normalize_term(term)
    understanding = db.query(UnderstandingLevel)\
        .filter(UnderstandingLevel.user_id == user_id, UnderstandingLevel.term == normalized_term)\
        .first()
    return understanding.level if understanding else 0


def get_learned_terms(db, user_id: int) -> list:
    """理解済みの用語リストを取得"""
    return db.query(UnderstandingLevel)\
        .filter(UnderstandingLevel.user_id == user_id)\
        .all()


def get_cached_explanation(db, term: str, level: int) -> Optional[str]:
    """キャッシュされた解説を取得"""
    normalized_term = normalize_term(term)
    cache = db.query(ExplanationCache)\
        .filter(ExplanationCache.term == normalized_term, ExplanationCache.level == level)\
        .first()
    return cache.explanation if cache else None


def cache_explanation(db, term: str, level: int, explanation: str) -> ExplanationCache:
    """解説をキャッシュに保存"""
    # 用語を正規化
    normalized_term = normalize_term(term)

    # 既存のキャッシュがあれば更新
    cache = db.query(ExplanationCache)\
        .filter(ExplanationCache.term == normalized_term, ExplanationCache.level == level)\
        .first()

    if cache:
        cache.explanation = explanation
        cache.created_at = datetime.utcnow()
    else:
        cache = ExplanationCache(term=normalized_term, level=level, explanation=explanation)
        db.add(cache)

    db.commit()
    db.refresh(cache)
    return cache


def clear_explanation_cache(db) -> int:
    """全ての解説キャッシュをクリア"""
    count = db.query(ExplanationCache).delete()
    db.commit()
    return count


def clear_explanation_cache_for_term(db, term: str) -> int:
    """特定の用語のキャッシュをクリア"""
    normalized_term = normalize_term(term)
    count = db.query(ExplanationCache)\
        .filter(ExplanationCache.term == normalized_term)\
        .delete()
    db.commit()
    return count


def clear_user_history(db, user_id: int) -> dict:
    """ユーザーの学習履歴を全てクリア"""
    # 検索履歴をクリア
    search_count = db.query(SearchHistory)\
        .filter(SearchHistory.user_id == user_id)\
        .delete()

    # 理解度記録をクリア
    understanding_count = db.query(UnderstandingLevel)\
        .filter(UnderstandingLevel.user_id == user_id)\
        .delete()

    db.commit()
    return {
        "search_history_cleared": search_count,
        "understanding_levels_cleared": understanding_count
    }


# ========== 分析用ヘルパー関数 ==========

def get_daily_search_counts(db, user_id: int, days: int = 30) -> dict:
    """日別の検索数を取得"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    history = db.query(SearchHistory)\
        .filter(
            SearchHistory.user_id == user_id,
            SearchHistory.searched_at >= start_date
        )\
        .all()

    # 日付ごとにグループ化
    date_counts = Counter()
    for h in history:
        date_str = h.searched_at.strftime('%Y-%m-%d')
        date_counts[date_str] += 1

    # 過去N日分の日付リストを生成
    dates = []
    counts = []
    for i in range(days):
        date = end_date - timedelta(days=days-1-i)
        date_str = date.strftime('%Y-%m-%d')
        dates.append(date_str)
        counts.append(date_counts.get(date_str, 0))

    return {"dates": dates, "counts": counts}


def get_daily_understood_counts(db, user_id: int, days: int = 30) -> dict:
    """日別の理解済み用語数を取得"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    understood = db.query(UnderstandingLevel)\
        .filter(
            UnderstandingLevel.user_id == user_id,
            UnderstandingLevel.updated_at >= start_date
        )\
        .all()

    # 日付ごとにグループ化
    date_counts = Counter()
    for u in understood:
        date_str = u.updated_at.strftime('%Y-%m-%d')
        date_counts[date_str] += 1

    # 過去N日分の日付リストを生成
    dates = []
    counts = []
    for i in range(days):
        date = end_date - timedelta(days=days-1-i)
        date_str = date.strftime('%Y-%m-%d')
        dates.append(date_str)
        counts.append(date_counts.get(date_str, 0))

    return {"dates": dates, "counts": counts}


def get_keyword_ranking(db, user_id: int, limit: int = 20) -> list:
    """キーワード別の検索回数ランキングを取得"""
    history = db.query(SearchHistory)\
        .filter(SearchHistory.user_id == user_id)\
        .order_by(SearchHistory.search_count.desc())\
        .limit(limit)\
        .all()

    # 理解済み用語を取得
    understood = get_learned_terms(db, user_id)
    understood_set = {u.term for u in understood}

    # ランキング形式に変換（search_countフィールドを使用）
    ranking = [
        {
            "term": h.term,
            "count": h.search_count or 1,
            "understood": h.term in understood_set
        }
        for h in history
    ]

    return ranking


def get_study_statistics(db, user_id: int) -> dict:
    """学習統計を取得"""
    # 理解済み用語
    learned = get_learned_terms(db, user_id)

    # レベル別にカウント
    level_counts = Counter(l.level for l in learned)

    # 検索履歴
    all_history = get_search_history(db, user_id, 1000)

    # 総検索回数（search_countの合計）
    total_searches = sum(h.search_count or 1 for h in all_history)

    # 学習日数（ユニークな日付数）
    study_dates = set(h.searched_at.date() for h in all_history)
    study_days = len(study_dates)

    # 平均検索数
    avg_searches = total_searches / study_days if study_days > 0 else 0

    # 最終学習日
    last_study_date = all_history[0].searched_at if all_history else None

    return {
        "total_terms_learned": len(learned),
        "level_1_count": level_counts.get(1, 0),
        "level_2_count": level_counts.get(2, 0),
        "level_3_count": level_counts.get(3, 0),
        "total_searches": total_searches,
        "avg_searches_per_day": round(avg_searches, 1),
        "study_days": study_days,
        "last_study_date": last_study_date.isoformat() + "Z" if last_study_date else None
    }


# ========== 達成バッジ関連 ==========

# バッジ定義
BADGES = {
    "first_search": {"name": "初めての一歩", "icon": "🎯", "description": "初めて用語を検索した"},
    "10_searches": {"name": "探求者", "icon": "🔍", "description": "10回検索を行った"},
    "50_searches": {"name": "知識の探検家", "icon": "🧭", "description": "50回検索を行った"},
    "100_searches": {"name": "マスター検索者", "icon": "🏅", "description": "100回検索を行った"},
    "first_understand": {"name": "理解の芽生え", "icon": "🌱", "description": "初めて用語を理解した"},
    "10_understand": {"name": "成長中", "icon": "🌿", "description": "10個の用語を理解した"},
    "50_understand": {"name": "知識の木", "icon": "🌳", "description": "50個の用語を理解した"},
    "100_understand": {"name": "Python博士", "icon": "🎓", "description": "100個の用語を理解した"},
    "first_practice": {"name": "実践者", "icon": "💻", "description": "初めて練習問題に挑戦した"},
    "10_practice": {"name": "コーダー", "icon": "⌨️", "description": "10回練習問題に挑戦した"},
    "practice_master": {"name": "練習の達人", "icon": "🏆", "description": "50回練習問題に正解した"},
    "3_day_streak": {"name": "3日連続学習", "icon": "🔥", "description": "3日連続で学習した"},
    "7_day_streak": {"name": "1週間の習慣", "icon": "📅", "description": "7日連続で学習した"},
    "30_day_streak": {"name": "学習の達人", "icon": "👑", "description": "30日連続で学習した"},
    "path_beginner": {"name": "学習パス開始", "icon": "🗺️", "description": "学習パスを開始した"},
    "path_complete": {"name": "パス完了", "icon": "🎊", "description": "学習パスを完了した"},
}


def get_user_achievements(db, user_id: int) -> list:
    """ユーザーの獲得バッジを取得"""
    return db.query(Achievement).filter(Achievement.user_id == user_id).all()


def award_badge(db, user_id: int, badge_id: str) -> Optional[Achievement]:
    """バッジを付与（既に持っていない場合のみ）"""
    if badge_id not in BADGES:
        return None

    existing = db.query(Achievement).filter(
        Achievement.user_id == user_id,
        Achievement.badge_id == badge_id
    ).first()

    if existing:
        return None  # 既に持っている

    badge = BADGES[badge_id]
    achievement = Achievement(
        user_id=user_id,
        badge_id=badge_id,
        badge_name=badge["name"],
        badge_icon=badge["icon"],
        badge_description=badge["description"]
    )
    db.add(achievement)
    db.commit()
    db.refresh(achievement)
    return achievement


def check_and_award_badges(db, user_id: int) -> list:
    """条件を満たすバッジをチェックして付与"""
    awarded = []

    # 検索回数バッジ
    search_count = db.query(SearchHistory).filter(SearchHistory.user_id == user_id).count()
    if search_count >= 1:
        badge = award_badge(db, user_id, "first_search")
        if badge: awarded.append(badge)
    if search_count >= 10:
        badge = award_badge(db, user_id, "10_searches")
        if badge: awarded.append(badge)
    if search_count >= 50:
        badge = award_badge(db, user_id, "50_searches")
        if badge: awarded.append(badge)
    if search_count >= 100:
        badge = award_badge(db, user_id, "100_searches")
        if badge: awarded.append(badge)

    # 理解数バッジ
    understand_count = db.query(UnderstandingLevel).filter(UnderstandingLevel.user_id == user_id).count()
    if understand_count >= 1:
        badge = award_badge(db, user_id, "first_understand")
        if badge: awarded.append(badge)
    if understand_count >= 10:
        badge = award_badge(db, user_id, "10_understand")
        if badge: awarded.append(badge)
    if understand_count >= 50:
        badge = award_badge(db, user_id, "50_understand")
        if badge: awarded.append(badge)
    if understand_count >= 100:
        badge = award_badge(db, user_id, "100_understand")
        if badge: awarded.append(badge)

    # 練習回数バッジ
    practice_count = db.query(PracticeResult).filter(PracticeResult.user_id == user_id).count()
    if practice_count >= 1:
        badge = award_badge(db, user_id, "first_practice")
        if badge: awarded.append(badge)
    if practice_count >= 10:
        badge = award_badge(db, user_id, "10_practice")
        if badge: awarded.append(badge)

    correct_count = db.query(PracticeResult).filter(
        PracticeResult.user_id == user_id,
        PracticeResult.is_correct == 1
    ).count()
    if correct_count >= 50:
        badge = award_badge(db, user_id, "practice_master")
        if badge: awarded.append(badge)

    # 連続学習バッジ
    streak = calculate_streak(db, user_id)
    if streak >= 3:
        badge = award_badge(db, user_id, "3_day_streak")
        if badge: awarded.append(badge)
    if streak >= 7:
        badge = award_badge(db, user_id, "7_day_streak")
        if badge: awarded.append(badge)
    if streak >= 30:
        badge = award_badge(db, user_id, "30_day_streak")
        if badge: awarded.append(badge)

    return awarded


def calculate_streak(db, user_id: int) -> int:
    """連続学習日数を計算"""
    history = db.query(SearchHistory).filter(
        SearchHistory.user_id == user_id
    ).order_by(SearchHistory.searched_at.desc()).all()

    if not history:
        return 0

    dates = sorted(set(h.searched_at.date() for h in history), reverse=True)
    today = datetime.utcnow().date()

    # 今日か昨日から始まっているかチェック
    if dates[0] != today and dates[0] != today - timedelta(days=1):
        return 0

    streak = 1
    for i in range(1, len(dates)):
        if dates[i-1] - dates[i] == timedelta(days=1):
            streak += 1
        else:
            break

    return streak


# ========== 学習パス関連 ==========

LEARNING_PATHS = {
    "beginner": {
        "name": "Python入門",
        "icon": "🌱",
        "description": "Pythonの基礎を学ぶ",
        "steps": ["変数", "データ型", "演算子", "条件分岐", "ループ", "関数", "リスト", "辞書"]
    },
    "intermediate": {
        "name": "Python中級",
        "icon": "📚",
        "description": "より深いPythonの知識",
        "steps": ["クラス", "継承", "例外処理", "ファイル操作", "モジュール", "リスト内包表記", "ジェネレータ", "デコレータ"]
    },
    "advanced": {
        "name": "Python上級",
        "icon": "🎓",
        "description": "高度なPythonテクニック",
        "steps": ["メタクラス", "コンテキストマネージャ", "非同期処理", "マルチスレッド", "型ヒント", "プロトコル", "デスクリプタ", "ABC"]
    },
    "data_science": {
        "name": "データサイエンス入門",
        "icon": "📊",
        "description": "データ分析の基礎",
        "steps": ["NumPy", "pandas", "matplotlib", "データフレーム", "配列操作", "データ可視化", "統計処理", "CSV読み込み"]
    }
}


def get_user_learning_paths(db, user_id: int) -> list:
    """ユーザーの学習パス進捗を取得"""
    return db.query(LearningPath).filter(LearningPath.user_id == user_id).all()


def start_learning_path(db, user_id: int, path_id: str) -> Optional[LearningPath]:
    """学習パスを開始"""
    if path_id not in LEARNING_PATHS:
        return None

    existing = db.query(LearningPath).filter(
        LearningPath.user_id == user_id,
        LearningPath.path_id == path_id
    ).first()

    if existing:
        return existing

    path = LearningPath(user_id=user_id, path_id=path_id)
    db.add(path)
    db.commit()
    db.refresh(path)

    # バッジ付与
    award_badge(db, user_id, "path_beginner")

    return path


def update_learning_path_progress(db, user_id: int, path_id: str, term: str) -> Optional[LearningPath]:
    """学習パスの進捗を更新"""
    path_record = db.query(LearningPath).filter(
        LearningPath.user_id == user_id,
        LearningPath.path_id == path_id
    ).first()

    if not path_record or path_id not in LEARNING_PATHS:
        return None

    path_def = LEARNING_PATHS[path_id]
    steps = path_def["steps"]

    # 現在のステップの用語と一致するかチェック
    normalized_term = normalize_term(term)
    current_step_term = normalize_term(steps[path_record.current_step]) if path_record.current_step < len(steps) else None

    if current_step_term and normalized_term == current_step_term:
        path_record.current_step += 1

        if path_record.current_step >= len(steps):
            path_record.completed = 1
            path_record.completed_at = datetime.utcnow()
            award_badge(db, user_id, "path_complete")

        db.commit()
        db.refresh(path_record)

    return path_record


# ========== 練習問題結果関連 ==========

def save_practice_result(db, user_id: int, term: str, problem_id: str, user_code: str, is_correct: bool) -> PracticeResult:
    """練習問題の結果を保存"""
    result = PracticeResult(
        user_id=user_id,
        term=normalize_term(term),
        problem_id=problem_id,
        user_code=user_code,
        is_correct=1 if is_correct else 0
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def get_practice_results(db, user_id: int, limit: int = 50) -> list:
    """練習問題の結果を取得"""
    return db.query(PracticeResult).filter(
        PracticeResult.user_id == user_id
    ).order_by(PracticeResult.attempted_at.desc()).limit(limit).all()


# ========== コード実行履歴関連 ==========

def save_code_execution(db, user_id: int, term: str, code: str, output: str = None, error: str = None) -> CodeExecutionHistory:
    """コード実行履歴を保存"""
    execution = CodeExecutionHistory(
        user_id=user_id,
        term=normalize_term(term),
        code=code,
        output=output,
        error=error
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def get_code_execution_history(db, user_id: int, limit: int = 50) -> list:
    """コード実行履歴を取得"""
    return db.query(CodeExecutionHistory).filter(
        CodeExecutionHistory.user_id == user_id
    ).order_by(CodeExecutionHistory.executed_at.desc()).limit(limit).all()


# ========== 復習スケジュール関連 ==========

def schedule_review(db, user_id: int, term: str) -> ReviewSchedule:
    """復習をスケジュール（間隔反復学習）"""
    normalized_term = normalize_term(term)

    existing = db.query(ReviewSchedule).filter(
        ReviewSchedule.user_id == user_id,
        ReviewSchedule.term == normalized_term
    ).first()

    if existing:
        # 復習完了、次の間隔を計算（1, 3, 7, 14, 30日）
        intervals = [1, 3, 7, 14, 30, 60]
        next_interval = intervals[min(existing.review_count, len(intervals) - 1)]
        existing.next_review_at = datetime.utcnow() + timedelta(days=next_interval)
        existing.review_count += 1
        existing.interval_days = next_interval
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # 新規スケジュール
        schedule = ReviewSchedule(
            user_id=user_id,
            term=normalized_term,
            next_review_at=datetime.utcnow() + timedelta(days=1),
            interval_days=1
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule


def get_due_reviews(db, user_id: int) -> list:
    """期限が来た復習項目を取得"""
    now = datetime.utcnow()
    return db.query(ReviewSchedule).filter(
        ReviewSchedule.user_id == user_id,
        ReviewSchedule.next_review_at <= now
    ).order_by(ReviewSchedule.next_review_at).all()


def get_upcoming_reviews(db, user_id: int, days: int = 7) -> list:
    """今後の復習項目を取得"""
    now = datetime.utcnow()
    future = now + timedelta(days=days)
    return db.query(ReviewSchedule).filter(
        ReviewSchedule.user_id == user_id,
        ReviewSchedule.next_review_at <= future
    ).order_by(ReviewSchedule.next_review_at).all()


# ========== データエクスポート ==========

def export_user_data(db, user_id: int) -> dict:
    """ユーザーの全学習データをエクスポート"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {}

    search_history = get_search_history(db, user_id, 1000)
    learned_terms = get_learned_terms(db, user_id)
    achievements = get_user_achievements(db, user_id)
    learning_paths = get_user_learning_paths(db, user_id)
    practice_results = get_practice_results(db, user_id, 1000)
    code_history = get_code_execution_history(db, user_id, 1000)
    review_schedules = db.query(ReviewSchedule).filter(ReviewSchedule.user_id == user_id).all()

    return {
        "export_date": datetime.utcnow().isoformat() + "Z",
        "user": {
            "username": user.username,
            "created_at": user.created_at.isoformat() + "Z" if user.created_at else None
        },
        "statistics": get_study_statistics(db, user_id),
        "search_history": [
            {
                "term": h.term,
                "search_count": h.search_count,
                "searched_at": h.searched_at.isoformat() + "Z" if h.searched_at else None
            }
            for h in search_history
        ],
        "learned_terms": [
            {
                "term": t.term,
                "level": t.level,
                "updated_at": t.updated_at.isoformat() + "Z" if t.updated_at else None
            }
            for t in learned_terms
        ],
        "achievements": [
            {
                "badge_id": a.badge_id,
                "badge_name": a.badge_name,
                "badge_icon": a.badge_icon,
                "earned_at": a.earned_at.isoformat() + "Z" if a.earned_at else None
            }
            for a in achievements
        ],
        "learning_paths": [
            {
                "path_id": p.path_id,
                "current_step": p.current_step,
                "completed": bool(p.completed),
                "started_at": p.started_at.isoformat() + "Z" if p.started_at else None,
                "completed_at": p.completed_at.isoformat() + "Z" if p.completed_at else None
            }
            for p in learning_paths
        ],
        "practice_results": [
            {
                "term": r.term,
                "problem_id": r.problem_id,
                "is_correct": bool(r.is_correct),
                "attempted_at": r.attempted_at.isoformat() + "Z" if r.attempted_at else None
            }
            for r in practice_results
        ],
        "code_executions": [
            {
                "term": c.term,
                "code": c.code,
                "output": c.output,
                "error": c.error,
                "executed_at": c.executed_at.isoformat() + "Z" if c.executed_at else None
            }
            for c in code_history
        ],
        "review_schedules": [
            {
                "term": r.term,
                "next_review_at": r.next_review_at.isoformat() + "Z" if r.next_review_at else None,
                "review_count": r.review_count,
                "interval_days": r.interval_days
            }
            for r in review_schedules
        ]
    }


# 起動時にデータベースを初期化
if __name__ == "__main__":
    init_db()
    print(f"Database initialized at: {DATABASE_PATH}")
