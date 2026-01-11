# デプロイメントガイド

Python学習支援アプリケーションの本番環境へのデプロイ手順です。

## 前提条件

- Docker と Docker Compose がインストールされていること
- Anthropic API キーを取得済みであること

## クイックスタート

### 1. 環境設定

```bash
# .envファイルを作成
cp .env.example .env

# .envファイルを編集してAPI キーと設定を入力
nano .env
```

重要な設定項目:
- `ANTHROPIC_API_KEY`: Anthropic API キー（必須）
- `APP_ENV`: `production` に設定
- `DEBUG`: `false` に設定

### 2. ビルドと起動

```bash
# コンテナをビルドして起動
docker-compose up -d --build

# ログを確認
docker-compose logs -f
```

### 3. 動作確認

```bash
# ヘルスチェック
curl http://localhost/api/health

# フロントエンドにアクセス
open http://localhost
```

## 本番環境設定

### 環境変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API キー | (必須) |
| `ANTHROPIC_MODEL` | 使用するClaudeモデル | `claude-sonnet-4-20250514` |
| `APP_ENV` | 環境 (`development`/`production`) | `development` |
| `DEBUG` | デバッグモード | `true` |
| `CORS_ORIGINS` | CORS許可オリジン | `http://localhost` |
| `RATE_LIMIT_REQUESTS` | レート制限（リクエスト数/分） | `60` |
| `LOG_LEVEL` | ログレベル | `INFO` |
| `CACHE_TTL` | キャッシュ有効期限（秒） | `3600` |

### セキュリティ設定

本番環境 (`APP_ENV=production`) では以下のセキュリティ機能が自動的に有効になります:

- **レート制限**: IPベースのリクエスト制限
- **セキュリティヘッダー**: X-Frame-Options, X-Content-Type-Options など
- **CORS制限**: 指定されたオリジンのみ許可
- **HSTS**: HTTPS強制（本番環境のみ）

## Docker コマンド

```bash
# 起動
docker-compose up -d

# 停止
docker-compose down

# 再ビルド
docker-compose up -d --build

# ログ確認
docker-compose logs -f backend
docker-compose logs -f frontend

# コンテナ内でコマンド実行
docker-compose exec backend bash

# ヘルスチェック
docker-compose ps
```

## アーキテクチャ

```
┌─────────────────┐      ┌─────────────────┐
│    Frontend     │      │     Backend     │
│    (Nginx)      │─────▶│    (FastAPI)    │
│   Port 80       │      │   Port 8000     │
└─────────────────┘      └─────────────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │   SQLite    │
              │   Database  │
              └─────────────┘
```

### コンテナ構成

- **frontend**: Nginx + 静的ファイル
  - ポート: 80
  - API リクエストを backend にプロキシ

- **backend**: FastAPI + Uvicorn
  - ポート: 8000（内部のみ）
  - Claude API との通信
  - SQLite データベース

## トラブルシューティング

### コンテナが起動しない

```bash
# ログを確認
docker-compose logs backend

# コンテナの状態確認
docker-compose ps
```

### API キーエラー

1. `.env` ファイルに `ANTHROPIC_API_KEY` が設定されているか確認
2. API キーが有効か確認

### 接続エラー

1. コンテナが起動しているか確認: `docker-compose ps`
2. ヘルスチェック: `curl http://localhost/api/health`
3. ファイアウォール設定を確認

### データベースエラー

```bash
# データベースファイルの権限確認
ls -la ./data/

# データボリュームをリセット
docker-compose down -v
docker-compose up -d
```

## 本番環境のベストプラクティス

1. **HTTPS を使用**: リバースプロキシ（Cloudflare, AWS ALB など）でSSL終端
2. **定期バックアップ**: `./data/learning.db` を定期的にバックアップ
3. **監視設定**: `/api/health` エンドポイントを監視
4. **ログ管理**: ログローテーションを設定
5. **リソース制限**: docker-compose.yml でメモリ・CPU制限を設定

## スケーリング

現在の構成はシングルインスタンス用です。スケールアウトが必要な場合:

1. SQLite を PostgreSQL/MySQL に移行
2. ロードバランサーを追加
3. セッション/キャッシュを Redis に移行
