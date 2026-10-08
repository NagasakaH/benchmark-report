"""Scoped agent-tool bootstrap: official Ubuntu HTTPS, verified public CA."""
import shlex
import uuid
from pathlib import Path


def install_command(tools, ca_path):
    if not tools or any(t not in ('tmux', 'asciinema') for t in tools):
        raise ValueError('Only Terminus recording tools are allowed')
    ca = shlex.quote(ca_path)
    return f'''set -eu
tb_apt_dir=$(mktemp -d /tmp/tb-agent-apt.XXXXXX)
trap 'rm -rf "$tb_apt_dir"; rm -f {ca}' EXIT
chmod 755 "$tb_apt_dir"
mkdir "$tb_apt_dir/parts"
cp -a /etc/apt/sources.list.d/. "$tb_apt_dir/parts/"
if [ -f /etc/apt/sources.list ]; then cp /etc/apt/sources.list "$tb_apt_dir/sources.list"; else touch "$tb_apt_dir/sources.list"; fi
find "$tb_apt_dir" -type f -exec sed -i -e 's|http://archive.ubuntu.com/ubuntu|https://archive.ubuntu.com/ubuntu|g' -e 's|http://security.ubuntu.com/ubuntu|https://security.ubuntu.com/ubuntu|g' {{}} +
tb_apt() {{ DEBIAN_FRONTEND=noninteractive apt-get -o Dir::Etc::sourcelist="$tb_apt_dir/sources.list" -o Dir::Etc::sourceparts="$tb_apt_dir/parts" -o Acquire::https::CaInfo={ca} -o Acquire::Retries=0 -o Acquire::https::Timeout=15 -o APT::Update::Error-Mode=any "$@"; }}
tb_apt update
tb_apt install -y {' '.join(tools)}
'''


async def prepare_install(environment, tools):
    source = Path('/opt/benchmark/tools/terminal-bench-20261007/agent-public-ca.pem')
    target = '/tmp/tb-agent-public-ca-' + uuid.uuid4().hex + '.pem'
    await environment.upload_file(source_path=source, target_path=target)
    return install_command(tools, target)
