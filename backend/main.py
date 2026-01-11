"""
FastAPI メインアプリケーション
Python学習支援アプリケーション用
"""

from typing import Optional, List, Dict
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
import os
import subprocess
import tempfile
import re
import sys
import io
import traceback
import logging

# 設定とセキュリティモジュールのインポート
from config import settings
from security import setup_security, get_cors_origins, InputSanitizer

# ログ設定
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from database import (
    init_db, get_db, get_or_create_user, check_user_exists, User,
    add_search_history, get_search_history,
    update_understanding_level, get_understanding_level, get_learned_terms,
    get_cached_explanation, cache_explanation, clear_explanation_cache,
    clear_user_history,
    get_daily_search_counts, get_daily_understood_counts,
    get_keyword_ranking, get_study_statistics,
    # 高度な学習機能
    BADGES, LEARNING_PATHS,
    get_user_achievements, check_and_award_badges, calculate_streak,
    get_user_learning_paths, start_learning_path, update_learning_path_progress,
    save_practice_result, get_practice_results,
    save_code_execution, get_code_execution_history,
    schedule_review, get_due_reviews, get_upcoming_reviews,
    export_user_data
)

# Claude APIサービスのインポート（オプショナル）
try:
    from claude_service import ClaudeService
    claude_service = ClaudeService()
    CLAUDE_AVAILABLE = True
    print("✅ Claude API service initialized successfully")
    print(f"✅ Using model: {claude_service.model}")
except (ImportError, ValueError) as e:
    print(f"❌ Claude service not available: {e}")
    claude_service = None
    CLAUDE_AVAILABLE = False

# アプリケーション初期化
app = FastAPI(
    title="Python学習支援アプリ",
    description="AIを使った適応型Python学習アプリケーション",
    version="0.1.0"
)

# CORS設定（フロントエンドからのアクセス許可）
cors_origins = get_cors_origins() if settings.is_production else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# セキュリティミドルウェア（本番環境のみ）
if settings.is_production:
    setup_security(app)
    logger.info("Security middleware enabled for production")

# データベース初期化
init_db()


# ========== 認証関連 ==========

async def get_current_user(
    db: Session = Depends(get_db),
    x_username: str = Header(None, alias="X-Username")
) -> User:
    """X-Usernameヘッダーから現在のユーザーを取得"""
    if not x_username or not x_username.strip():
        raise HTTPException(
            status_code=401,
            detail="認証が必要です。ログインしてください。"
        )
    try:
        return get_or_create_user(db, username=x_username.strip())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class LoginRequest(BaseModel):
    """ログインリクエスト"""
    username: str


class LoginResponse(BaseModel):
    """ログインレスポンス"""
    username: str
    is_new_user: bool
    message: str


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """ユーザー名でログイン（新規の場合はアカウント作成）"""
    username = request.username.strip()

    if not username:
        raise HTTPException(status_code=400, detail="ユーザー名を入力してください")

    if len(username) < 2:
        raise HTTPException(status_code=400, detail="ユーザー名は2文字以上で入力してください")

    if len(username) > 50:
        raise HTTPException(status_code=400, detail="ユーザー名は50文字以内で入力してください")

    # ユーザーが既に存在するかチェック
    is_new = not check_user_exists(db, username)

    # ユーザーを取得または作成
    user = get_or_create_user(db, username=username)

    return LoginResponse(
        username=user.username,
        is_new_user=is_new,
        message="新しいアカウントを作成しました！" if is_new else f"おかえりなさい、{user.username}さん！"
    )


# ========== リクエスト/レスポンスモデル ==========

class SearchRequest(BaseModel):
    """検索リクエスト"""
    term: str
    level: int = 1  # デフォルトはレベル1


class SearchResponse(BaseModel):
    """検索レスポンス"""
    term: str
    level: int
    explanation: str
    cached: bool  # キャッシュから取得したかどうか
    related_keywords: List[str] = []  # 関連キーワード（コード内で使用されている他のキーワード）


class FeedbackRequest(BaseModel):
    """理解度フィードバックリクエスト"""
    term: str
    understood: bool  # True: わかった, False: もっと詳しく
    current_level: int


class FeedbackResponse(BaseModel):
    """フィードバックレスポンス"""
    term: str
    new_level: int
    explanation: Optional[str] = None  # 次のレベルの解説（もっと詳しくの場合）
    message: str


class HistoryItem(BaseModel):
    """履歴アイテム"""
    term: str
    searched_at: datetime


class HistoryItemResponse(BaseModel):
    """履歴アイテムのレスポンス"""
    term: str
    timestamp: str
    understood: bool
    level: int


class ProfileResponse(BaseModel):
    """学習者プロファイル"""
    username: str
    total_searches: int
    search_count: int  # total_searchesと同じ（フロントエンド互換用）
    understood_count: int  # 理解済み用語の数
    understood_terms: List[str]  # 理解済み用語の文字列配列
    learned_terms: List[Dict]
    recent_searches: List[Dict]


class PracticeRequest(BaseModel):
    """練習問題リクエスト"""
    term: str
    level: int = 1


class PracticeResponse(BaseModel):
    """練習問題レスポンス"""
    term: str
    level: int
    problem_title: str
    problem_description: str
    hint: str
    answer: str
    expected_output: Optional[str] = None
    output_pattern: Optional[str] = None  # 出力パターン（正規表現）


class ExecuteRequest(BaseModel):
    """コード実行リクエスト"""
    code: str
    expected_output: Optional[str] = None
    output_pattern: Optional[str] = None  # 出力パターン（正規表現）


class ExecuteResponse(BaseModel):
    """コード実行レスポンス"""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    error_line: Optional[int] = None
    suggestion: Optional[str] = None
    pattern_matched: Optional[bool] = None  # パターンマッチの結果


# ========== 関連キーワード抽出 ==========

# Pythonの主要キーワードリスト（学習対象として適切なもの）
PYTHON_KEYWORDS = {
    'def': '関数定義',
    'return': '戻り値',
    'class': 'クラス',
    'if': '条件分岐',
    'else': '条件分岐',
    'elif': '条件分岐',
    'for': 'forループ',
    'while': 'whileループ',
    'import': 'インポート',
    'from': 'インポート',
    'try': '例外処理',
    'except': '例外処理',
    'finally': '例外処理',
    'with': 'コンテキストマネージャ',
    'as': 'エイリアス',
    'lambda': 'ラムダ関数',
    'yield': 'ジェネレータ',
    'async': '非同期処理',
    'await': '非同期処理',
    'global': 'グローバル変数',
    'nonlocal': 'ノンローカル変数',
    'pass': 'パス文',
    'break': 'ループ制御',
    'continue': 'ループ制御',
    'in': 'メンバーシップ',
    'is': '同一性比較',
    'not': '論理演算',
    'and': '論理演算',
    'or': '論理演算',
    'True': '真偽値',
    'False': '真偽値',
    'None': 'None値',
    'print': '出力',
    'input': '入力',
    'len': '長さ取得',
    'range': '範囲',
    'list': 'リスト',
    'dict': '辞書',
    'set': '集合',
    'tuple': 'タプル',
    'str': '文字列',
    'int': '整数',
    'float': '浮動小数点',
    'bool': '真偽値型',
}

def extract_related_keywords(explanation: str, current_term: str, max_count: int = 3) -> List[str]:
    """
    解説文からコード例に含まれるPythonキーワードを抽出
    検索キーワード自身は除外し、関連性の高いものを返す
    """
    import re

    # コードブロックを抽出
    code_blocks = re.findall(r'```python\s*(.*?)\s*```', explanation, re.DOTALL)
    code_text = '\n'.join(code_blocks)

    # キーワードを検出
    found_keywords = []
    current_term_lower = current_term.lower()

    for keyword in PYTHON_KEYWORDS.keys():
        # 現在の検索キーワードは除外
        if keyword.lower() == current_term_lower:
            continue

        # コード内にキーワードが存在するかチェック（単語境界で）
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, code_text):
            found_keywords.append(keyword)

    # 優先度順にソート（def, return, class, if, for などを優先）
    priority_order = ['def', 'return', 'class', 'if', 'for', 'while', 'print', 'list', 'dict', 'import']

    def sort_key(kw):
        try:
            return priority_order.index(kw)
        except ValueError:
            return len(priority_order)

    found_keywords.sort(key=sort_key)

    return found_keywords[:max_count]


# ========== Claude API連携 ==========

def generate_explanation(term: str, level: int, learned_terms: Optional[List[str]] = None, previous_explanation: Optional[str] = None) -> str:
    """
    解説を生成する（Claude API使用）
    """
    print(f"🔍 generate_explanation called: term={term}, level={level}")
    print(f"🔍 CLAUDE_AVAILABLE={CLAUDE_AVAILABLE}, claude_service={claude_service is not None}")
    print(f"🔍 previous_explanation provided: {previous_explanation is not None}")

    # Claude APIが利用可能な場合は使用
    if CLAUDE_AVAILABLE and claude_service:
        try:
            print(f"🚀 Calling Claude API for term: {term}")
            result = claude_service.generate_explanation(term, level, learned_terms, previous_explanation)
            print(f"✅ Claude API response received (length: {len(result)})")
            return result
        except Exception as e:
            print(f"❌ Error generating explanation with Claude: {e}")
            import traceback
            traceback.print_exc()
            # フォールバック: サンプル解説を返す
    else:
        print(f"⚠️ Claude API not available, using fallback")
    
    # フォールバック: サンプル解説（Claude APIが利用できない場合）
    # プロトタイプ用のサンプル解説
    sample_explanations = {
        "def": {
            1: """## `def` とは？
`def` は Python で**関数を定義する**ためのキーワードです。

関数とは、特定の処理をまとめて名前をつけたものです。何度も同じ処理を書く必要がなくなります。""",
            2: """## `def` の使い方

### 基本的な構文
```python
def 関数名(引数):
    処理内容
    return 戻り値
```

### 具体例
```python
def greet(name):
    return f"こんにちは、{name}さん！"

# 関数を呼び出す
message = greet("太郎")
print(message)  # 出力: こんにちは、太郎さん！
```

**ポイント：**
- `def` の後に関数名を書く
- 括弧 `()` の中に引数（入力値）を書く
- コロン `:` を忘れずに
- 処理内容はインデント（字下げ）する""",
            3: """## `def` をもっと簡単に理解しよう

### 関数は「レシピ」のようなもの

料理のレシピを想像してください：

```python
# 「挨拶を作るレシピ」を定義
def make_greeting(name):
    greeting = "こんにちは、" + name + "さん"
    return greeting
```

**1行ずつ解説：**
1. `def make_greeting(name):` → 「make_greeting」という名前のレシピを作る。材料は「name」
2. `greeting = "こんにちは、" + name + "さん"` → 材料を使って挨拶文を作る
3. `return greeting` → できあがった挨拶文を渡す

### 使い方
```python
result = make_greeting("花子")
print(result)  # こんにちは、花子さん
```

関数を「呼び出す」= レシピを使って料理を作る、というイメージです。"""
        },
        "class": {
            1: """## `class` とは？
`class` は Python で**クラス（設計図）を定義する**ためのキーワードです。

クラスは、データ（属性）と処理（メソッド）をひとまとめにした「設計図」のようなものです。""",
            2: """## `class` の使い方

### 基本的な構文
```python
class クラス名:
    def __init__(self, 引数):
        self.属性 = 引数

    def メソッド名(self):
        処理内容
```

### 具体例
```python
class Dog:
    def __init__(self, name):
        self.name = name

    def bark(self):
        return f"{self.name}がワンワンと吠えた！"

# インスタンスを作成
my_dog = Dog("ポチ")
print(my_dog.bark())  # 出力: ポチがワンワンと吠えた！
```""",
            3: """## `class` をもっと簡単に理解しよう

### クラスは「たい焼きの型」

```python
# たい焼きの型（設計図）
class Taiyaki:
    def __init__(self, filling):
        self.filling = filling  # 中身を設定

    def describe(self):
        return f"これは{self.filling}のたい焼きです"
```

**1行ずつ解説：**
1. `class Taiyaki:` → 「Taiyaki」という型を作る
2. `def __init__(self, filling):` → 型を使う時に何を入れるか決める
3. `self.filling = filling` → 入れたものを覚えておく
4. `def describe(self):` → この型で作ったものができること

```python
# 型を使ってたい焼きを作る
anko = Taiyaki("あんこ")
cream = Taiyaki("クリーム")
print(anko.describe())  # これはあんこのたい焼きです
```"""
        }
    }

    # デフォルトの解説
    default_explanation = f"""## `{term}` について

**レベル {level} の解説**

「{term}」はPythonの{'基本的な' if level == 1 else '重要な'}構文・概念です。

{'まずは基本的な意味を理解しましょう。' if level == 1 else ''}
{'具体的なコード例を見てみましょう。' if level == 2 else ''}
{'もっと簡単な例で理解を深めましょう。' if level == 3 else ''}

*注: これはプロトタイプ版のサンプル解説です。本番環境ではClaude APIを使用して詳細な解説を生成します。*"""

    # サンプルデータがあればそれを返す、なければデフォルト
    term_lower = term.lower().strip()
    if term_lower in sample_explanations:
        return sample_explanations[term_lower].get(level, default_explanation)

    return default_explanation


def generate_practice(term: str, level: int) -> Dict:
    """
    練習問題を生成する（仮実装）
    本番ではClaude APIを使用して動的に生成
    """
    # プロトタイプ用のサンプル練習問題
    sample_practices = {
        "def": {
            "problem_title": "関数を作ってみよう",
            "problem_description": "defの関数を使って1+2を計算してみましょう。",
            "hint": "def キーワードを使って関数を定義し、return で結果を返します。引数は2つ必要です。",
            "answer": """def add(a, b):
    return a + b

# 使用例
result = add(1, 2)
print(result)  # 出力: 3""",
            "check_keywords": ["def", "return", "(", ")"],
            "expected_output": "3"
        },
        "class": {
            "problem_title": "クラスを作ってみよう",
            "problem_description": "classを使って「太郎」という名前の人を作って、挨拶を表示してみましょう。",
            "hint": "class キーワードでクラスを定義し、__init__ で初期化、self.name で属性を保存します。",
            "answer": """class Person:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"こんにちは、{self.name}です！"

# 使用例
person = Person("太郎")
print(person.greet())  # 出力: こんにちは、太郎です！""",
            "check_keywords": ["class", "def", "__init__", "self"],
            "expected_output": "こんにちは、太郎です！"
        },
        "リスト": {
            "problem_title": "リストを操作しよう",
            "problem_description": "リストを使って [1, 2, 3] を作り、4を追加して、合計を計算してみましょう。",
            "hint": "リストは [] で作成し、append() で要素を追加、sum() で合計を計算できます。",
            "answer": """numbers = [1, 2, 3]
numbers.append(4)
total = sum(numbers)
print(total)  # 出力: 10""",
            "check_keywords": ["[", "]", "append", "sum"],
            "expected_output": "10"
        },
        "変数": {
            "problem_title": "変数を使ってみよう",
            "problem_description": "変数を使って「太郎」という名前と「20」という年齢を保存して、自己紹介文を作ってみましょう。",
            "hint": "変数は = で値を代入します。文字列は引用符で囲み、f文字列で変数を埋め込めます。",
            "answer": """name = "太郎"
age = 20
message = f"私の名前は{name}で、{age}歳です。"
print(message)  # 出力: 私の名前は太郎で、20歳です。""",
            "check_keywords": ["=", "name", "age"],
            "expected_output": "私の名前は太郎で、20歳です。"
        },
        "関数": {
            "problem_title": "関数を作ってみよう",
            "problem_description": "関数を使って「花子」という名前を受け取って「こんにちは、花子さん！」と表示してみましょう。",
            "hint": "def で関数を定義し、引数で名前を受け取り、f文字列で挨拶文を作成して return します。",
            "answer": """def greet(name):
    return f"こんにちは、{name}さん！"

# 使用例
message = greet("花子")
print(message)  # 出力: こんにちは、花子さん！""",
            "check_keywords": ["def", "greet", "return"],
            "expected_output": "こんにちは、花子さん！"
        },
    }

    # デフォルトの練習問題
    default_practice = {
        "problem_title": f"「{term}」を使ってみよう",
        "problem_description": f"「{term}」を使った簡単なPythonコードを書いてみましょう。",
        "hint": f"「{term}」の基本的な使い方を思い出して、シンプルなコードを書いてみてください。",
        "answer": f"# {term}の使用例\n# (プロトタイプ版のため、具体的な解答例は準備中です)",
        "check_keywords": []
    }

    term_lower = term.lower().strip()
    practice = sample_practices.get(term_lower) or sample_practices.get(term) or default_practice

    return {
        "term": term,
        "level": level,
        **practice
    }


# ========== APIエンドポイント ==========

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {"message": "Python学習支援アプリへようこそ！", "version": "0.1.0"}


@app.post("/search", response_model=SearchResponse)
async def search_term(
    request: SearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    用語を検索し、解説を生成する
    """
    print(f"📝 /search endpoint called: term={request.term}, level={request.level}")

    term = request.term.strip()
    level = max(1, min(3, request.level))  # 1-3の範囲に制限

    if not term:
        raise HTTPException(status_code=400, detail="検索用語を入力してください")

    # 検索履歴を保存
    print(f"🔎 Search endpoint called: term='{term}', user_id={user.id}", flush=True)
    add_search_history(db, user.id, term)
    print(f"🔎 Search history saved", flush=True)

    # キャッシュをチェック
    cached = get_cached_explanation(db, term, level)
    print(f"📦 Cache check: term={term}, level={level}, cached={cached is not None}")
    if cached:
        print(f"📦 Returning cached response (length: {len(cached)})")
        # 関連キーワードを抽出
        related = extract_related_keywords(cached, term)
        return SearchResponse(
            term=term,
            level=level,
            explanation=cached,
            cached=True,
            related_keywords=related
        )

    # 学習済み用語を取得（コンテキスト認識用）
    learned = get_learned_terms(db, user.id)
    learned_term_list = [l.term for l in learned]

    # 前のレベルの解説を取得（レベル2以上の場合、文脈維持のため）
    previous_explanation = None
    if level > 1:
        previous_explanation = get_cached_explanation(db, term, level - 1)
        print(f"📚 Fetched previous explanation for level {level - 1}: {previous_explanation is not None}")

    # 解説を生成
    explanation = generate_explanation(term, level, learned_term_list, previous_explanation)

    # キャッシュに保存
    cache_explanation(db, term, level, explanation)

    # 関連キーワードを抽出
    related = extract_related_keywords(explanation, term)

    return SearchResponse(
        term=term,
        level=level,
        explanation=explanation,
        cached=False,
        related_keywords=related
    )


@app.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    理解度フィードバックを受け取り、必要に応じて次のレベルの解説を返す
    """
    term = request.term.strip()
    current_level = request.current_level
    understood = request.understood

    if understood:
        # 「わかった」→ 理解度を記録
        update_understanding_level(db, user.id, term, current_level)
        return FeedbackResponse(
            term=term,
            new_level=current_level,
            explanation=None,
            message=f"「{term}」のレベル{current_level}を理解済みとして記録しました！"
        )
    else:
        # 「もっと詳しく」→ 次のレベルの解説を生成
        new_level = min(current_level + 1, 3)

        if new_level > 3:
            return FeedbackResponse(
                term=term,
                new_level=3,
                explanation=None,
                message="これ以上詳しい解説はありません。基礎から再度学習することをお勧めします。"
            )

        # キャッシュをチェック
        cached = get_cached_explanation(db, term, new_level)
        if cached:
            explanation = cached
        else:
            learned = get_learned_terms(db, user.id)
            learned_term_list = [l.term for l in learned]

            # 前のレベルの解説を取得して文脈を維持
            previous_explanation = get_cached_explanation(db, term, current_level)
            print(f"📚 Fetched previous explanation for level {current_level}: {previous_explanation is not None}")

            explanation = generate_explanation(term, new_level, learned_term_list, previous_explanation)
            cache_explanation(db, term, new_level, explanation)

        return FeedbackResponse(
            term=term,
            new_level=new_level,
            explanation=explanation,
            message=f"レベル{new_level}のより詳しい解説です。"
        )


@app.post("/practice", response_model=PracticeResponse)
async def get_practice_problem(
    request: PracticeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """練習問題を取得（Claude API使用）"""
    term = request.term.strip()
    level = request.level

    # ユーザーの学習履歴を取得
    learned = get_learned_terms(db, user.id)
    learned_term_list = [l.term for l in learned]
    
    # Claude APIが利用可能な場合は使用
    if CLAUDE_AVAILABLE and claude_service:
        try:
            problem_data = claude_service.generate_practice_problem(
                term, level, learned_term_list
            )
            
            return PracticeResponse(
                term=term,
                level=level,
                **problem_data
            )
        except Exception as e:
            print(f"Error generating practice with Claude: {e}")
            # フォールバック: サンプル問題を返す
    
    # フォールバック: サンプル練習問題（Claude APIが利用できない場合）
    sample_problems = {
        "def": {
            1: {
                "problem_title": "簡単な関数を作ろう",
                "problem_description": "名前を受け取って、「こんにちは、〇〇さん！」と返す関数 greet を作成してください。",
                "hint": "def キーワードを使って関数を定義し、f-string を使って文字列を作成します。",
                "answer": "def greet(name):\n    return f\"こんにちは、{name}さん！\"\n\nprint(greet(\"太郎\"))",
                "expected_output": "こんにちは、太郎さん！"
            },
            2: {
                "problem_title": "関数を作ってみよう",
                "problem_description": "defの関数を使って1+2を計算してみましょう。",
                "hint": "def キーワードを使って関数を定義し、return で結果を返します。引数は2つ必要です。",
                "answer": "def add(a, b):\n    return a + b\n\nresult = add(1, 2)\nprint(result)",
                "expected_output": "3"
            },
            3: {
                "problem_title": "複数の関数を作ろう",
                "problem_description": "2つの数を受け取って、その合計と積を返す関数を作成してください。",
                "hint": "複数の関数を定義するか、1つの関数で複数の値を返すことができます。",
                "answer": "def add(a, b):\n    return a + b\n\ndef multiply(a, b):\n    return a * b\n\nprint(add(2, 3))\nprint(multiply(2, 3))",
                "expected_output": "5\n6"
            }
        },
        "class": {
            1: {
                "problem_title": "クラスを作ってみよう",
                "problem_description": "classを使って「太郎」という名前の人を作って、挨拶を表示してみましょう。",
                "hint": "class キーワードでクラスを定義し、__init__ で初期化、self.name で属性を保存します。",
                "answer": "class Person:\n    def __init__(self, name):\n        self.name = name\n\n    def greet(self):\n        return f\"こんにちは、{self.name}です！\"\n\nperson = Person(\"太郎\")\nprint(person.greet())",
                "expected_output": "こんにちは、太郎です！"
            }
        },
        "リスト": {
            1: {
                "problem_title": "リストを操作しよう",
                "problem_description": "リストを使って [1, 2, 3] を作り、4を追加して、合計を計算してみましょう。",
                "hint": "リストは [] で作成し、append() で要素を追加、sum() で合計を計算できます。",
                "answer": "numbers = [1, 2, 3]\nnumbers.append(4)\ntotal = sum(numbers)\nprint(total)",
                "expected_output": "10"
            }
        },
        "変数": {
            1: {
                "problem_title": "自分の名前と年齢を変数に保存して表示しよう",
                "problem_description": "あなたの名前を文字列として変数nameに、年齢を数値として変数ageに保存してください。そして、print文を使って「私の名前は〇〇で、年齢は〇歳です。」という形式で出力してください。",
                "hint": "文字列は引用符で囲み、数値はそのまま書きます。print文では+を使って文字列を結合できます。数値を文字列に変換するにはstr()関数を使います。",
                "answer": "name = \"太郎\"\nage = 20\nprint(\"私の名前は\" + name + \"で、年齢は\" + str(age) + \"歳です。\")",
                "expected_output": None,
                "output_pattern": "私の名前は.+で、年齢は\\d+歳です。"
            }
        },
        "関数": {
            1: {
                "problem_title": "関数を作ってみよう",
                "problem_description": "関数を使って「花子」という名前を受け取って「こんにちは、花子さん！」と表示してみましょう。",
                "hint": "def で関数を定義し、引数で名前を受け取り、f文字列で挨拶文を作成して return します。",
                "answer": "def greet(name):\n    return f\"こんにちは、{name}さん！\"\n\nmessage = greet(\"花子\")\nprint(message)",
                "expected_output": "こんにちは、花子さん！"
            }
        }
    }
    
    term_lower = term.lower()
    if term_lower in sample_problems and level in sample_problems[term_lower]:
        problem = sample_problems[term_lower][level]
        return PracticeResponse(
            term=term,
            level=level,
            **problem
        )
    
    # デフォルトの練習問題（フォールバック）
    return PracticeResponse(
        term=term,
        level=level,
        problem_title=f"{term}の練習問題",
        problem_description=f"{term}を使ったコードを書いてみましょう。",
        hint=f"{term}の基本的な使い方を思い出してください。",
        answer=f"# {term}を使った例\nprint('練習問題')",
        expected_output=None
    )


def extract_expected_output(answer_code: str) -> Optional[str]:
    """解答コードから期待される出力を抽出"""
    # print文のコメントから期待される出力を抽出
    # 例: print(result)  # 出力: 3
    pattern = r'#\s*出力:\s*(.+)'
    matches = re.findall(pattern, answer_code)
    if matches:
        return matches[-1].strip()
    return None


def analyze_error(error_message: str, code: str) -> Dict:
    """エラーメッセージを解析して、行番号と修正提案を返す"""
    error_info = {
        "error_line": None,
        "error_message": error_message,
        "suggestion": None
    }

    # 行番号を抽出（例: "File \"<string>\", line 3"）
    line_match = re.search(r'line\s+(\d+)', error_message)
    if line_match:
        error_info["error_line"] = int(line_match.group(1))

    # エラーの種類に応じて修正提案を生成
    if "SyntaxError" in error_message:
        if "invalid syntax" in error_message:
            error_info["suggestion"] = "構文エラーがあります。コロン(:)や括弧()が正しく閉じられているか確認してください。"
        elif "unexpected EOF" in error_message:
            error_info["suggestion"] = "コードが途中で終わっています。インデントや括弧が正しく閉じられているか確認してください。"
        else:
            error_info["suggestion"] = "構文エラーがあります。コードの書き方を確認してください。"
    elif "IndentationError" in error_message:
        error_info["suggestion"] = "インデント（字下げ）が正しくありません。Pythonではインデントが重要です。スペースまたはタブで統一してください。"
    elif "NameError" in error_message:
        error_info["suggestion"] = "未定義の変数や関数を使用しています。変数名のスペルミスや、定義されていない変数を使っていないか確認してください。"
    elif "TypeError" in error_message:
        error_info["suggestion"] = "型エラーが発生しています。数値と文字列を混同していないか、関数の引数の型を確認してください。"
    elif "AttributeError" in error_message:
        error_info["suggestion"] = "オブジェクトに存在しない属性やメソッドを使用しています。オブジェクトの型と使用可能なメソッドを確認してください。"
    else:
        error_info["suggestion"] = "エラーが発生しました。エラーメッセージをよく読んで、コードを見直してください。"

    return error_info


@app.post("/execute", response_model=ExecuteResponse)
async def execute_code(request: ExecuteRequest):
    """Pythonコードを実行"""
    code = request.code
    
    if not code or not code.strip():
        return ExecuteResponse(
            success=False,
            error="コードが空です",
            suggestion="コードを入力してください。"
        )
    
    # セキュリティチェック（危険な操作を禁止）
    dangerous_keywords = ['import os', 'import sys', 'import subprocess', 'exec', 'eval', '__import__', 'open(']
    for keyword in dangerous_keywords:
        if keyword in code:
            return ExecuteResponse(
                success=False,
                error=f"セキュリティ上の理由により、'{keyword}'の使用は禁止されています。",
                suggestion="基本的なPython構文のみを使用してください。"
            )
    
    # コードを実行
    output_buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = output_buffer
    
    try:
        # 実行環境を制限
        exec_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'bool': bool,
                'True': True,
                'False': False,
                'None': None,
                'abs': abs,
                'min': min,
                'max': max,
                'sum': sum,
                'sorted': sorted,
                'enumerate': enumerate,
                'zip': zip,
            }
        }
        
        exec(code, exec_globals)
        sys.stdout = old_stdout
        
        output = output_buffer.getvalue()
        output_str = output.strip() if output else ""

        # パターンマッチチェック
        pattern_matched = None
        if request.output_pattern:
            try:
                pattern_matched = bool(re.match(request.output_pattern, output_str))
            except re.error:
                pattern_matched = None

        return ExecuteResponse(
            success=True,
            output=output_str,
            pattern_matched=pattern_matched
        )
        
    except SyntaxError as e:
        sys.stdout = old_stdout
        return ExecuteResponse(
            success=False,
            error=str(e),
            error_line=e.lineno,
            suggestion="構文エラーです。コロン(:)やインデントを確認してください。"
        )
    
    except NameError as e:
        sys.stdout = old_stdout
        # Extract line number from traceback
        tb = traceback.format_exc()
        line_match = re.search(r'line (\d+)', tb)
        error_line = int(line_match.group(1)) if line_match else None
        
        return ExecuteResponse(
            success=False,
            error=str(e),
            error_line=error_line,
            suggestion="変数や関数が定義されていません。スペルを確認してください。"
        )
    
    except Exception as e:
        sys.stdout = old_stdout
        # Extract line number from traceback
        tb = traceback.format_exc()
        line_match = re.search(r'line (\d+)', tb)
        error_line = int(line_match.group(1)) if line_match else None
        
        return ExecuteResponse(
            success=False,
            error=str(e),
            error_line=error_line,
            suggestion="実行時エラーが発生しました。コードのロジックを確認してください。"
        )


@app.get("/history")
async def get_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    検索履歴を取得
    """
    history = get_search_history(db, user.id, limit)

    # 理解済み用語を取得してセットに変換（高速検索用）
    learned = get_learned_terms(db, user.id)
    learned_dict = {l.term: l.level for l in learned}

    return {
        "history": [
            {
                "term": h.term,
                "timestamp": h.searched_at.isoformat() + "Z",  # UTCを示すZサフィックスを追加
                "understood": h.term in learned_dict,
                "level": learned_dict.get(h.term, 1)
            }
            for h in history
        ]
    }


@app.get("/profile", response_model=ProfileResponse)
async def get_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    学習者プロファイルを取得
    """

    # 検索履歴
    history = get_search_history(db, user.id, 10)

    # 理解済み用語
    learned = get_learned_terms(db, user.id)

    # 総検索数
    total = len(get_search_history(db, user.id, 1000))

    # 理解済み用語の文字列リスト
    understood_term_list = [l.term for l in learned]

    return ProfileResponse(
        username=user.username,
        total_searches=total,
        search_count=total,  # フロントエンド互換用
        understood_count=len(learned),
        understood_terms=understood_term_list,
        learned_terms=[
            {"term": l.term, "level": l.level, "updated_at": l.updated_at.isoformat() + "Z"}
            for l in learned
        ],
        recent_searches=[
            {"term": h.term, "searched_at": h.searched_at.isoformat() + "Z"}
            for h in history
        ]
    )


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "environment": settings.app_env,
        "claude_available": CLAUDE_AVAILABLE
    }


@app.delete("/cache")
async def clear_cache(db: Session = Depends(get_db)):
    """解説キャッシュを全てクリア"""
    count = clear_explanation_cache(db)
    return {
        "message": f"キャッシュを{count}件クリアしました",
        "cleared_count": count
    }


@app.delete("/history")
async def clear_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """学習履歴を全てクリア（検索履歴と理解度記録）"""
    result = clear_user_history(db, user.id)
    return {
        "message": "学習履歴をクリアしました",
        "search_history_cleared": result["search_history_cleared"],
        "understanding_levels_cleared": result["understanding_levels_cleared"]
    }


# ========== 学習分析エンドポイント ==========

@app.get("/analytics/daily")
async def get_daily_analytics(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """日別の学習統計を取得"""

    search_data = get_daily_search_counts(db, user.id, 30)
    understood_data = get_daily_understood_counts(db, user.id, 30)

    return {
        "dates": search_data["dates"],
        "search_counts": search_data["counts"],
        "understood_counts": understood_data["counts"]
    }


@app.get("/analytics/keywords")
async def get_keywords_analytics(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """キーワードランキングを取得"""
    ranking = get_keyword_ranking(db, user.id, 20)

    return {"keywords": ranking}


@app.get("/analytics/progress")
async def get_progress_analytics(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """学習進捗の概要を取得"""
    stats = get_study_statistics(db, user.id)

    return stats


@app.get("/analytics/recommendations")
async def get_recommendations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """次に学ぶべきトピックを提案"""

    # 理解済み用語を取得
    learned = get_learned_terms(db, user.id)
    learned_terms = {l.term.lower() for l in learned}

    # Python学習パス定義（前提→次に学ぶべき）
    learning_paths = {
        "変数": ["print", "input", "型"],
        "print": ["変数", "f文字列", "format"],
        "if": ["else", "elif", "比較演算子"],
        "for": ["range", "リスト", "enumerate"],
        "while": ["break", "continue", "無限ループ"],
        "def": ["return", "引数", "デフォルト引数"],
        "return": ["複数の戻り値", "None", "早期リターン"],
        "リスト": ["append", "スライス", "リスト内包表記"],
        "辞書": ["keys", "values", "items"],
        "class": ["__init__", "self", "メソッド"],
        "__init__": ["継承", "super", "プロパティ"],
        "import": ["from", "as", "モジュール"],
        "try": ["except", "finally", "raise"],
        "lambda": ["map", "filter", "高階関数"],
    }

    # 初心者向け基本トピック
    beginner_topics = [
        {"term": "変数", "reason": "プログラミングの基本、データを保存する方法を学びましょう"},
        {"term": "print", "reason": "画面に出力する基本を学びましょう"},
        {"term": "if", "reason": "条件分岐の基本を学びましょう"},
        {"term": "for", "reason": "繰り返し処理の基本を学びましょう"},
        {"term": "def", "reason": "関数の定義方法を学びましょう"},
        {"term": "リスト", "reason": "複数のデータを扱う方法を学びましょう"},
    ]

    recommendations = []

    # 理解済みトピックに基づく推奨
    for learned_term in learned_terms:
        if learned_term in learning_paths:
            for next_topic in learning_paths[learned_term]:
                if next_topic.lower() not in learned_terms:
                    recommendations.append({
                        "term": next_topic,
                        "reason": f"「{learned_term}」を理解済みです。次は「{next_topic}」を学びましょう",
                        "related_to": learned_term
                    })

    # 推奨が少ない場合は初心者向けトピックを追加
    if len(recommendations) < 3:
        for topic in beginner_topics:
            if topic["term"].lower() not in learned_terms:
                if not any(r["term"] == topic["term"] for r in recommendations):
                    recommendations.append({
                        "term": topic["term"],
                        "reason": topic["reason"],
                        "related_to": None
                    })

    # 最大5件に制限
    return {"recommendations": recommendations[:5]}


# ========== 高度な学習機能 API ==========

# ---------- 達成バッジ API ----------

@app.get("/badges")
async def get_all_badges():
    """全バッジ一覧を取得"""
    return {
        "badges": [
            {"id": k, **v} for k, v in BADGES.items()
        ]
    }


@app.get("/badges/earned")
async def get_earned_badges(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """獲得済みバッジを取得"""
    achievements = get_user_achievements(db, user.id)
    return {
        "earned_badges": [
            {
                "badge_id": a.badge_id,
                "name": a.badge_name,
                "icon": a.badge_icon,
                "description": a.badge_description,
                "earned_at": a.earned_at.isoformat() + "Z" if a.earned_at else None
            }
            for a in achievements
        ],
        "total_earned": len(achievements),
        "total_available": len(BADGES)
    }


@app.post("/badges/check")
async def check_badges(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """バッジ獲得条件をチェックして付与"""
    awarded = check_and_award_badges(db, user.id)
    return {
        "newly_awarded": [
            {
                "badge_id": a.badge_id,
                "name": a.badge_name,
                "icon": a.badge_icon,
                "description": a.badge_description
            }
            for a in awarded
        ]
    }


@app.get("/streak")
async def get_streak(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """連続学習日数を取得"""
    streak = calculate_streak(db, user.id)
    return {"streak_days": streak}


# ---------- 学習パス API ----------

@app.get("/learning-paths")
async def get_all_learning_paths():
    """全学習パス一覧を取得"""
    return {
        "paths": [
            {
                "id": k,
                "name": v["name"],
                "icon": v["icon"],
                "description": v["description"],
                "steps": v["steps"],
                "total_steps": len(v["steps"])
            }
            for k, v in LEARNING_PATHS.items()
        ]
    }


@app.get("/learning-paths/progress")
async def get_learning_path_progress(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """ユーザーの学習パス進捗を取得"""
    user_paths = get_user_learning_paths(db, user.id)

    progress = []
    for p in user_paths:
        if p.path_id in LEARNING_PATHS:
            path_def = LEARNING_PATHS[p.path_id]
            progress.append({
                "path_id": p.path_id,
                "name": path_def["name"],
                "icon": path_def["icon"],
                "current_step": p.current_step,
                "total_steps": len(path_def["steps"]),
                "steps": path_def["steps"],
                "current_term": path_def["steps"][p.current_step] if p.current_step < len(path_def["steps"]) else None,
                "completed": bool(p.completed),
                "started_at": p.started_at.isoformat() + "Z" if p.started_at else None,
                "completed_at": p.completed_at.isoformat() + "Z" if p.completed_at else None,
                "progress_percent": round((p.current_step / len(path_def["steps"])) * 100, 1)
            })

    return {"progress": progress}


class StartPathRequest(BaseModel):
    path_id: str


@app.post("/learning-paths/start")
async def start_path(
    request: StartPathRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """学習パスを開始"""
    path = start_learning_path(db, user.id, request.path_id)

    if not path:
        raise HTTPException(status_code=400, detail="Invalid path ID")

    path_def = LEARNING_PATHS[request.path_id]
    return {
        "success": True,
        "path_id": request.path_id,
        "name": path_def["name"],
        "first_term": path_def["steps"][0],
        "total_steps": len(path_def["steps"])
    }


class UpdatePathRequest(BaseModel):
    path_id: str
    term: str


@app.post("/learning-paths/update")
async def update_path_progress(
    request: UpdatePathRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """学習パスの進捗を更新"""
    path = update_learning_path_progress(db, user.id, request.path_id, request.term)

    if not path:
        raise HTTPException(status_code=400, detail="Path not found or not started")

    path_def = LEARNING_PATHS[request.path_id]
    return {
        "current_step": path.current_step,
        "next_term": path_def["steps"][path.current_step] if path.current_step < len(path_def["steps"]) else None,
        "completed": bool(path.completed),
        "progress_percent": round((path.current_step / len(path_def["steps"])) * 100, 1)
    }


# ---------- 練習問題 API ----------

class SavePracticeResultRequest(BaseModel):
    term: str
    problem_id: str
    user_code: str
    is_correct: bool


@app.post("/practice/result")
async def save_practice(
    request: SavePracticeResultRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """練習問題の結果を保存"""
    result = save_practice_result(
        db, user.id,
        request.term, request.problem_id,
        request.user_code, request.is_correct
    )

    # バッジチェック
    awarded = check_and_award_badges(db, user.id)

    return {
        "saved": True,
        "result_id": result.id,
        "newly_awarded_badges": [
            {"badge_id": a.badge_id, "name": a.badge_name, "icon": a.badge_icon}
            for a in awarded
        ]
    }


@app.get("/practice/history")
async def get_practice_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """練習問題の履歴を取得"""
    results = get_practice_results(db, user.id, limit)

    # 統計計算
    total = len(results)
    correct = sum(1 for r in results if r.is_correct)

    return {
        "history": [
            {
                "term": r.term,
                "problem_id": r.problem_id,
                "is_correct": bool(r.is_correct),
                "attempted_at": r.attempted_at.isoformat() + "Z" if r.attempted_at else None
            }
            for r in results
        ],
        "statistics": {
            "total_attempts": total,
            "correct_count": correct,
            "accuracy": round((correct / total * 100), 1) if total > 0 else 0
        }
    }


# ---------- コード実行履歴 API ----------

class SaveCodeExecutionRequest(BaseModel):
    term: str
    code: str
    output: Optional[str] = None
    error: Optional[str] = None


@app.post("/code-history/save")
async def save_code_history(
    request: SaveCodeExecutionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """コード実行履歴を保存"""
    execution = save_code_execution(
        db, user.id,
        request.term, request.code,
        request.output, request.error
    )
    return {"saved": True, "execution_id": execution.id}


@app.get("/code-history")
async def get_code_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """コード実行履歴を取得"""
    history = get_code_execution_history(db, user.id, limit)

    return {
        "history": [
            {
                "id": h.id,
                "term": h.term,
                "code": h.code,
                "output": h.output,
                "error": h.error,
                "executed_at": h.executed_at.isoformat() + "Z" if h.executed_at else None
            }
            for h in history
        ]
    }


# ---------- 復習リマインダー API ----------

class ScheduleReviewRequest(BaseModel):
    term: str


@app.post("/review/schedule")
async def schedule_term_review(
    request: ScheduleReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """復習をスケジュール"""
    schedule = schedule_review(db, user.id, request.term)

    return {
        "scheduled": True,
        "term": schedule.term,
        "next_review_at": schedule.next_review_at.isoformat() + "Z" if schedule.next_review_at else None,
        "review_count": schedule.review_count,
        "interval_days": schedule.interval_days
    }


@app.get("/review/due")
async def get_due_review_items(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """期限が来た復習項目を取得"""
    due = get_due_reviews(db, user.id)

    return {
        "due_reviews": [
            {
                "term": r.term,
                "due_since": r.next_review_at.isoformat() + "Z" if r.next_review_at else None,
                "review_count": r.review_count
            }
            for r in due
        ],
        "count": len(due)
    }


@app.get("/review/upcoming")
async def get_upcoming_review_items(
    days: int = 7,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """今後の復習項目を取得"""
    upcoming = get_upcoming_reviews(db, user.id, days)

    return {
        "upcoming_reviews": [
            {
                "term": r.term,
                "scheduled_for": r.next_review_at.isoformat() + "Z" if r.next_review_at else None,
                "review_count": r.review_count,
                "interval_days": r.interval_days
            }
            for r in upcoming
        ],
        "count": len(upcoming)
    }


# ---------- データエクスポート API ----------

@app.get("/export")
async def export_data(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """学習データをエクスポート"""
    data = export_user_data(db, user.id)
    return data


# 静的ファイルの配信（フロントエンド用）
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/app")
    async def serve_frontend():
        """フロントエンドのHTMLを配信"""
        return FileResponse(os.path.join(frontend_path, "index.html"))

    @app.get("/styles.css")
    async def get_css():
        return FileResponse(os.path.join(frontend_path, "styles.css"))

    @app.get("/app.js")
    async def get_js():
        return FileResponse(os.path.join(frontend_path, "app.js"))
