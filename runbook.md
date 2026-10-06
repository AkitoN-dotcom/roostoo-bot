# 運用手順（runbook）

## デプロイ（初回）
1. AWSアクセスポータルから HackathonPermissionSet のマネジメントコンソールを開く
2. リージョンを ap-southeast-2（シドニー）に切り替える（他リージョンは権限外）
3. EC2 → 起動テンプレート → Hackathon-Starter-Template を選択 → テンプレートからインスタンスを起動
   - キーペアは「キーペアなしで続行」。それ以外はデフォルト
   - インスタンスは絶対に1台だけ（2台目は自動で terminate される）
4. インスタンスのステータスチェックが 2/2 になるまで1〜2分待つ
5. インスタンスを選択 → 接続 → セッションマネージャー → 接続
6. 以下の2つを順に貼って実行（詳細はチャットの手順どおり）
   - ダウンロード＆セットアップ: `curl -sL <配布URL> -o /tmp/roostoo-bot.tar.gz && sudo bash /opt/...`（実際のコマンドは配布時のものを使う）
   - .env 作成と起動
7. `journalctl -u roostoo-bot -f` で boot / heartbeat / rebalance_done が出ることを確認

## 日常監視（1日1回・5分）
- Notionのチャットで「チェックして」と送る（残高・ポジション・稼働日数を確認してもらう）
- またはサーバーで `journalctl -u roostoo-bot --since today` を見る
- heartbeat が毎時出ていれば正常。出ていなければ `systemctl status roostoo-bot`

## 更新（戦略変更・バグ修正）
1. ローカルでコードを修正しテスト（pytest）
2. git にコミット（審査はコミット履歴の一貫性を見る。修正は隠さず全て履歴に残す）
3. サーバー側でファイルを差し替え `systemctl restart roostoo-bot`

## 停止・復旧
- 緊急停止: `sudo touch /opt/roostoo-bot/HALT`（新規取引が止まる）
- 全解消して止めたい場合はキルスイッチ相当なので、チャットで依頼するか手動では行わないこと（手動売買は失格事由のため、必ずボットの機能で行う）
- キルスイッチ発動後は24時間で自動復帰。延長したい場合は state.json の halt_until を将来時刻に書き換えて restart
- インスタンスが停止した場合は EC2 から「開始」。Terminate は絶対にしない（データが消える）

## 障害時の連絡
- APIエラーが5回連続するとボットは安全停止する。復旧したら `systemctl start roostoo-bot`
- 原因が分からない場合は WhatsApp の運営チャンネルに logs/ の該当日を添えて質問
