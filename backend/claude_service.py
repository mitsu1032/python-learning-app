"""
Claude API統合サービス
Python学習支援アプリケーション用
"""

import os
import json
import re
from anthropic import Anthropic
from typing import List, Optional
from dotenv import load_dotenv

# 環境変数を読み込む
load_dotenv()


class ClaudeService:
    """Claude APIを使用した解説・練習問題生成サービス"""
    
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        try:
            self.client = Anthropic(api_key=api_key)
        except Exception as e:
            print(f"Warning: Failed to initialize Claude API client: {e}")
            self.client = None

        self.model = "claude-sonnet-4-20250514"
    
    def generate_explanation(
        self,
        term: str,
        level: int,
        learned_terms: Optional[List[str]] = None,
        previous_explanation: Optional[str] = None
    ) -> str:
        """
        用語の解説を生成

        Args:
            term: 解説する用語
            level: 解説レベル（1-3）
            learned_terms: 既習概念のリスト
            previous_explanation: 前のレベルの解説（文脈維持用）

        Returns:
            Markdown形式の解説文
        """
        # Claude APIが利用できない場合はエラーを投げる
        if self.client is None:
            raise Exception("Claude API client is not available")

        # レベル別の指示を構築
        level_instructions = {
            1: """【キーワード集中】「{term}」だけに焦点を当てて説明してください。
- 他のPythonキーワード（def, class, if等）の説明は最小限に
- 「{term}」が何をするものかを初心者にも分かるように説明
- 具体的な日常シーンの例え話を使ってください（例：ケーキ屋さん、ピザ配達など）
- コード例を1つ含め、**{term}の行にコメントで「← ここが{term}！」と目印をつけてください**
- 100-200文字程度で簡潔に""",
            2: """【絶対厳守】レベル1で使った「同じ具体的シナリオ」と「同じ関数名」を引き継いで発展させてください。
- レベル1で「ケーキ屋さん」なら、レベル2も「ケーキ屋さん」を続ける（コンビニ等に変えない）
- レベル1で「make_cake()」関数なら、それを拡張した「make_cake(flavor, size)」等を使う

【キーワード使用制限】
- 「{term}」に引き続き焦点を当てる
- 学習済みキーワードがあれば、その中から**1つだけ**関連づけて説明可
- コード例で**{term}の行にコメントで「← {term}」と目印をつけてください**

300-500文字程度で説明してください。""",
            3: """【絶対厳守】レベル1・レベル2で使った「同じ具体的シナリオ」と「同じ関数名」を引き継いで、さらに発展させてください。
- 3レベル通して同じお店（ケーキ屋さんならケーキ屋さん）の話を続けてください
- 同じ関数名を拡張・応用してください

【キーワード使用】
- 「{term}」に引き続き焦点を当てる
- 学習済みキーワードがあれば、関連するものを**複数**組み合わせて実践的な例を示す
- コード例で**{term}の行にコメントで「← {term}」と目印をつけてください**

500-800文字程度で説明してください。"""
        }
        
        # 学習履歴を考慮したコンテキスト（レベル別に使用制限）
        context = ""
        if learned_terms and len(learned_terms) > 0:
            terms_list = ', '.join(learned_terms[:5])
            if level == 1:
                context = f"\n\n【参考情報】学習者は以下を理解済み: {terms_list}\nただしLv1では「{term}」のみに集中し、他のキーワードには触れないでください。"
            elif level == 2:
                context = f"\n\n【参考情報】学習者は以下を理解済み: {terms_list}\nLv2では上記から**1つだけ**選んで「{term}」と関連づけて説明できます。"
            else:
                context = f"\n\n【参考情報】学習者は以下を理解済み: {terms_list}\nLv3では上記の複数を「{term}」と組み合わせた実践的な例を示せます。"
        
        # システムプロンプト
        system_prompt = f"""あなたはPythonプログラミングの優秀な教師です。
初心者がAIを使ってプログラミングを学ぶのをサポートします。
学習者のレベルに合わせた丁寧で分かりやすい解説を提供してください。

【最重要】今回説明するキーワードは「{term}」です。
- 説明文中では「{term}」を**太字**で強調してください
- コード例では「{term}」が使われている行に「# ← ここが{term}！」のようにコメントで目印をつけてください

出力形式:
- Markdown形式で記述
- コードブロックは ```python で囲む
- 見出しは ## を使用
- 重要なポイントは **太字** で強調
- 箇条書きは - を使用
- コード例にはコメントを付ける（特に{term}の行は目立たせる）"""
        
        # 前のレベルの解説がある場合は含める
        previous_context = ""
        if previous_explanation and level > 1:
            previous_context = f"""

【最重要：前のレベルの解説 - この具体例を必ず引き継いでください】
{previous_explanation}

---
【絶対厳守事項 - 違反禁止】
1. **具体的なシナリオをそのまま継続してください**
   - 前のレベルで「ケーキ屋さん」の例なら、このレベルも「ケーキ屋さん」の例を続ける
   - 前のレベルで「make_cake」関数なら、このレベルも「make_cake」を拡張する
   - 「買い物」「料理」などの抽象的なテーマではなく、「ケーキ屋さん」「お寿司屋さん」など具体的な設定を維持

2. **コード例は前のレベルの関数名・変数名を引き継いでください**
   - 前: `make_cake(flavor)` → 次: `make_cake(flavor, size)` や `make_birthday_cake(flavor, message)`
   - 前: `order_pizza(topping)` → 次: `order_pizza(topping, size, quantity)`
   - 絶対に新しい無関係な関数名（例：コンビニでお買い物）に変えないでください

3. **禁止事項**
   - 「ケーキ屋さん」→「コンビニ」のように場所を変えることは禁止
   - 前のレベルと無関係な新しい例を導入することは禁止
   - 抽象度を上げる（具体→一般化）ことは禁止

4. **レベル間の連続性**
   - 学習者が「同じケーキ屋さんの話が続いている」と感じるようにしてください
   - 前のレベルのコードに機能を追加・拡張する形で説明してください"""

        # ユーザープロンプト
        user_prompt = f"""Python の「{term}」について、レベル{level}の解説を作成してください。

{level_instructions.get(level, level_instructions[1]).format(term=term)}
{context}
{previous_context}

解説をMarkdown形式で出力してください。"""
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                timeout=30.0  # 30秒でタイムアウト
            )
            
            return message.content[0].text
            
        except Exception as e:
            print(f"Claude API error: {e}")
            # フォールバック: エラー時はシンプルな説明を返す
            return f"## {term}\n\n申し訳ございません。現在、詳細な解説を生成できません。後ほど再度お試しください。"
    
    def generate_practice_problem(
        self,
        term: str,
        level: int,
        learned_terms: Optional[List[str]] = None
    ) -> dict:
        """
        練習問題を生成

        Args:
            term: 問題の対象となる用語
            level: 問題レベル（1-3）
            learned_terms: 既習概念のリスト

        Returns:
            練習問題の辞書（problem_title, problem_description, hint, answer, expected_output）
        """
        # Claude APIが利用できない場合はエラーを投げる
        if self.client is None:
            raise Exception("Claude API client is not available")

        # レベル別の難易度指示
        level_instructions = {
            1: """非常に簡単な問題を作成してください。
基本的な構文のみを使用し、1-3行程度のコードで解決できる問題にしてください。
初心者でも理解できる明確な指示を出してください。""",
            2: """中程度の難易度の問題を作成してください。
基本的な構文を組み合わせて、5-10行程度のコードで解決できる問題にしてください。
実践的な例題を出してください。""",
            3: """やや難しい問題を作成してください。
複数の概念を組み合わせて、10-20行程度のコードで解決できる問題にしてください。
実際の開発で使えるような実践的な問題にしてください。"""
        }
        
        # 学習履歴を考慮したコンテキスト
        context = ""
        if learned_terms and len(learned_terms) > 0:
            terms_list = ', '.join(learned_terms[:5])
            context = f"\n\n学習者は既に以下の概念を理解しています: {terms_list}\nこれらを活用できる問題を作成してください。"
        
        # システムプロンプト
        system_prompt = """あなたはPythonプログラミングの優秀な教師です。
学習者が実際に手を動かして学べる練習問題を作成してください。

出力形式:
以下のJSON形式で出力してください（コードブロックは使わず、テキストとして出力）:
{
    "problem_title": "問題のタイトル",
    "problem_description": "問題の説明（何を実装するか、具体的な指示）",
    "hint": "ヒント（解き方のヒント、使うべき構文など）",
    "answer": "解答例のコード（\\nで改行を表現）",
    "expected_output": "期待される出力（print文がある場合の出力結果）"
}

注意:
- answerは実行可能なPythonコードとして記述
- print文を含む場合は、expected_outputに出力結果を記載
- コードは\\nで改行を表現（実際の改行ではなく）"""
        
        # ユーザープロンプト
        user_prompt = f"""Python の「{term}」に関する練習問題を、レベル{level}で作成してください。

{level_instructions.get(level, level_instructions[1])}
{context}

上記のJSON形式で出力してください。"""
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                timeout=30.0  # 30秒でタイムアウト
            )
            
            response_text = message.content[0].text
            
            # JSON形式のレスポンスをパース
            # コードブロックを除去
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
            
            # JSON部分を抽出
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    problem_data = json.loads(json_str)
                    
                    # 必須フィールドのチェック
                    required_fields = ['problem_title', 'problem_description', 'hint', 'answer']
                    for field in required_fields:
                        if field not in problem_data:
                            raise ValueError(f"Missing required field: {field}")
                    
                    # 改行文字を実際の改行に変換
                    if 'answer' in problem_data:
                        problem_data['answer'] = problem_data['answer'].replace('\\n', '\n')
                    
                    # expected_outputがNoneの場合はNoneを設定
                    if 'expected_output' not in problem_data:
                        problem_data['expected_output'] = None
                    
                    return problem_data
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    raise ValueError(f"Invalid JSON format: {e}")
            else:
                # JSONが見つからない場合はデフォルトを返す
                raise ValueError("JSON format not found in response")
                
        except Exception as e:
            print(f"Claude API error: {e}")
            # フォールバック: デフォルト問題を返す
            return {
                "problem_title": f"{term}の練習問題",
                "problem_description": f"{term}を使ったコードを書いてみましょう。",
                "hint": f"{term}の基本的な使い方を思い出してください。",
                "answer": f"# {term}を使った例\nprint('練習問題')",
                "expected_output": None
            }
