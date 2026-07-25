# おかいものメモ（PWA版）

無料の買い物リスト・予算管理・価格記録アプリ。単一ページで動作し、データは利用者の端末内にのみ保存されます。

## GitHub Pagesでの公開手順

1. GitHubで新しいリポジトリを作成（例: `okaimono`）
2. このフォルダの全ファイル（index.html / manifest.webmanifest / sw.js / icon-192.png / icon-512.png / apple-touch-icon.png）をアップロード
3. リポジトリの Settings → Pages → Branch を `main` / `(root)` にして Save
4. 数分後、`https://<ユーザー名>.github.io/okaimono/` で公開されます

## 利用者向け：スマホへの「インストール」

- **iPhone**: Safariで開く → 共有ボタン → 「ホーム画面に追加」
- **Android**: Chromeで開く → メニュー → 「アプリをインストール」

ホーム画面から起動すると全画面表示になり、2回目以降はオフラインでも起動できます。

## 更新方法

index.htmlを差し替えるだけで、利用者がオンラインで開いた際に自動で最新版になります（ページ本体はネットワーク優先で配信）。アイコンやsw.js自体を変更した場合のみ、sw.js内の `okaimono-v1` を `v2` に上げてください。

## ライセンス

MIT License — 自由に利用・改変・再配布できます。
