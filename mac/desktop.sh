#!/usr/bin/env bash

# Configure the browser desktop; safe to rerun in an existing container.
set -euo pipefail

ln -sfn /ws/mac/desktop.html /usr/share/novnc/desktop.html
status_file="${TIAGO_CPU_STATUS_FILE:-/tmp/tiago-cpu-usage.json}"
if [[ ! -e "$status_file" ]]; then
  printf '{"time":0,"system":null,"robots":{}}\n' > "$status_file"
fi
ln -sfn "$status_file" /usr/share/novnc/cpu-usage.json

python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET

namespace = 'http://openbox.org/3.4/rc'
ET.register_namespace('', namespace)
config = Path.home() / '.config/openbox/rc.xml'
tree = ET.parse(config if config.exists() else '/etc/xdg/openbox/rc.xml')
applications = tree.getroot().find(f'{{{namespace}}}applications')
if applications is None:
    applications = ET.SubElement(tree.getroot(), f'{{{namespace}}}applications')
rule = applications.find("{*}application[@name='gz-sim-gui'][@class='Gazebo GUI']")
if rule is None:
    rule = ET.SubElement(applications, f'{{{namespace}}}application', {
        'name': 'gz-sim-gui', 'class': 'Gazebo GUI', 'type': 'normal',
    })
maximized = rule.find(f'{{{namespace}}}maximized')
if maximized is None:
    maximized = ET.SubElement(rule, f'{{{namespace}}}maximized')
maximized.text = 'yes'
config.parent.mkdir(parents=True, exist_ok=True)
tree.write(config, encoding='utf-8', xml_declaration=True)
PY

if pgrep -x openbox >/dev/null; then
  openbox --reconfigure
fi
