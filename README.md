# Team85-Life Tree — APAC Quant Trading Hackathon Bot

## 戦略概要
クロスセクショナル・モメンタム（ロングのみ、中頻度・方向性戦略）。
14銘柄の流動性上位ユニバース（BTC, ETH, SOL, XRP, DOGE, ADA, AVAX, LINK, LTC, UNI, NEAR, SUI, DOT, HBAR）を対象に、7日間（168時間）のリターンで順位付けし、上位3銘柄（かつリターンが正のもの）へ等ウェイトで投資する。リバランスは毎日00:00 UTC。全銘柄がマイナスの場合は現金で待機する。

## 根拠（バックテスト）
- データ：Coinbase 1時間足 180日分（Roostoo価格との乖離は全14銘柄で±0.15%以内を検証済み）
- 手数料：実測テイカー0.1%/片道を全トレードに課金
- 評価：コンペと同じ長さのローリング14日窓の分布で評価（単一パスでの過学習を回避）
- 採用構成（L=168h, k=3, 日次, 総投下80%）：全期間 +114.7%、日次Sharpe 2.66、Sortino 4.01、Calmar 4.38、最大DD -26.2%
- 14日窓：中央値 +6.8%、プラス窓率 74.7%
- 期間中の手数料総額は初期資金の約8.9%（180日で334約定）。回転数は日平均約1.9件で中頻度の要件を満たす
- 不採用案：時系列モメンタム（窓Sharpeが低い）、k=1集中型（最大DD -42%と脆い）、ロング・ショート合成（スコア改善がなく実装リスクのみ増える）、平均回帰（トレンド相場で劣後）

## リスク管理
- 1銘柄あたり上限30%、総投下上限80%（残りは現金）
- クラッシュガード：保有銘柄が24時間で-10%下落したらその銘柄を即時成行で解消（毎時点検）
- キルスイッチ：評価額が過去ピークから-10%で全ポジション解消し24時間停止（自動復帰）
- 2%未満のウェイト差は取引しない（手数料節約）
- 全判断と全注文を logs/YYYYMMDD.jsonl に理由コード付きで記録
- ルートに HALT ファイルを置くと新規停止（手動停止用）

## セットアップ
1. `pip3 install -r requirements.txt`
2. `.env.example` を `.env` にコピーし、4つのキーを設定（.envはgitにコミットしないこと）
3. テスト口座で確認： `MODE=test DRY_RUN=1 python3 -m roostoo_bot.main`
4. 本番： `MODE=prod python3 -m roostoo_bot.main`（サーバーではsystemdで常駐。runbook.md参照）

## 構成
- roostoo_bot/config.py … パラメータと環境変数
- roostoo_bot/api_client.py … Roostoo API（HMAC-SHA256署名、5回連続失敗で停止）
- roostoo_bot/datafeed.py … 価格履歴の初期化（Coinbase）とRoostooティッカーの追記
- roostoo_bot/signals.py … モメンタム選定とクラッシュガード
- roostoo_bot/risk.py … キルスイッチ・停止状態・上限適用（state.jsonに永続化）
- roostoo_bot/executor.py … 目標ウェイトへの寄せ（売り先順）、全解消
- roostoo_bot/main.py … 1時間ループ本体
- tests/ … ロジックのユニットテスト（5件）
- analysis/ … バックテスト一式（backtest.py, results/backtest_summary.csv）

## ライブ結果
（コンペ終了後に追記）

## 注意
- 本番口座への手動API売買は大会ルールで禁止。発注はこのボット経由のみ
- ショートは現バージョンでは使用しない（バックテストで優位性が確認できなかったため）
