# パッケージ更新
sudo apt update && sudo apt upgrade -y

# Docker インストール
curl -fsSL https://get.docker.com | sudo sh

# 現在のユーザーを docker グループに追加（sudo なしで使えるように）
sudo usermod -aG docker $USER

# 一度ログアウトして再接続（グループ反映のため）
exit

# 再接続後に以下で動作確認：

docker --version
docker compose version
