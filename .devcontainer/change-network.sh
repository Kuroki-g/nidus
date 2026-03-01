#!/bin/bash
# .devcontainer/change-network.sh
#
# Claude CodeのOAuth認証用ポートリバインドモニター。
#
# 使い方:
#   1. このスクリプトを実行して待機させる
#   2. 別タブで `claude login` を実行する
#   3. ポートを検知したらsocatで0.0.0.0にリバインドし、VS Codeが自動フォワード
#   4. ブラウザでOAuth認証を完了したらこのスクリプトはCtrl+Cで終了
#
# 期待仕様 (変わったら要見直し):
#   - claudeが [::1] (IPv6 loopback) にbind
#   - ポートはエフェメラルポート範囲 (32768-60999)
#
# 依存パッケージ (Ubuntu標準に含まれないもの):
#   - socat:    sudo apt-get install -y socat
#   - iproute2: sudo apt-get install -y iproute2  (ss コマンド)
#               ※ Ubuntu 20.04以降は通常プリインストール済み

set -euo pipefail

EXPECTED_BIND="[::1]"
PORT_MIN=32768
PORT_MAX=60999

if ! command -v socat &>/dev/null; then
    echo "ERROR: socat not found. Run: sudo apt-get install -y socat" >&2
    exit 1
fi

if ! command -v ss &>/dev/null; then
    echo "ERROR: ss not found. Run: sudo apt-get install -y iproute2" >&2
    exit 1
fi

echo "Waiting for claude OAuth callback port..."
echo "-> Run 'claude login' in another tab."
echo ""

SOCAT_PID=""

cleanup() {
    # shellcheck disable=SC2181
    # SOCAT_PIDが空でなければkill。終了コードは無視してよい
    [[ -n "$SOCAT_PID" ]] && kill "$SOCAT_PID" 2>/dev/null || true
    echo ""
    echo "Done."
}
trap cleanup EXIT

while true; do
    # grep の終了コード1(マッチなし)をset -eに拾わせないため || true
    line=$(ss -tlnp 2>/dev/null | grep '"claude"' || true)

    if [[ -n "$line" ]]; then
        # [::1]:XXXXX 形式からbindアドレスとポートを分離: rev + cut で末尾のポート番号を取り出す
        bind_addr=$(echo "$line" | awk '{print $4}' | rev | cut -d: -f2- | rev)
        port=$(echo "$line" | awk '{print $4}' | rev | cut -d: -f1 | rev)

        # 仕様変更検知: bindアドレス
        if [[ "$bind_addr" != "$EXPECTED_BIND" ]]; then
            echo "WARNING: Unexpected bind address: '$bind_addr' (expected: '$EXPECTED_BIND')" >&2
            echo "WARNING: Claude's OAuth implementation may have changed. Review this script." >&2
            exit 1
        fi

        # 仕様変更検知: ポート範囲
        if ! [[ "$port" =~ ^[0-9]+$ ]] || (( port < PORT_MIN || port > PORT_MAX )); then
            echo "WARNING: Unexpected port: '$port' (expected: ${PORT_MIN}-${PORT_MAX})" >&2
            echo "WARNING: Claude's OAuth implementation may have changed. Review this script." >&2
            exit 1
        fi

        echo "Detected: ${bind_addr}:${port}"
        echo "Starting socat relay on 0.0.0.0:${port} ..."

        socat "TCP-LISTEN:${port},bind=0.0.0.0,reuseaddr,fork" \
              "TCP6:[::1]:${port}" &
        SOCAT_PID=$!

        echo "Ready. Complete the OAuth flow in your browser."
        echo "(Ctrl+C to stop)"
        wait "$SOCAT_PID" || true
        break
    fi

    sleep 0.5
done
