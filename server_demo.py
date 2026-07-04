# -*- coding: utf-8 -*-
"""
简易接收服务示例 — 运行后开发者即可接收使用者上报信息。
用法：
  pip install flask
  python server_demo.py
然后修改 telemetry_config.json 中的 upload_url 为 http://127.0.0.1:5000/api/report
"""

import json
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

LOG_FILE = "usage_log.jsonl"


@app.route("/api/report", methods=["POST"])
def report():
    data = request.get_json(force=True)
    timestamp = data.get("timestamp", datetime.now().isoformat())

    # 记录到文件
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

    # 同时打印到控制台
    user = data.get("user", {})
    name = user.get("name", "??")
    dept = user.get("department", "")
    event = data.get("event", "")
    print(f"[{timestamp}] 使用者：{name} {dept} | 事件：{event}")
    return jsonify({"status": "ok"})


@app.route("/api/stats", methods=["GET"])
def stats():
    """查看汇总统计"""
    users = set()
    count = 0
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
                d = json.loads(line)
                u = d.get("user", {}).get("name", "")
                if u:
                    users.add(u)
    return jsonify({
        "total_reports": count,
        "unique_users": len(users),
        "users": list(users),
    })


if __name__ == "__main__":
    import os
    cert = os.path.join('.', "cert.pem")
    key = os.path.join('.', "key.pem")
    print(f"接收服务启动（HTTPS），日志写入 {LOG_FILE}")
    print("请将 telemetry_config.json 中的 upload_url 设为：")
    print("  https://192.168.1.101:5844/api/report")
    app.run(host="0.0.0.0", port=5844, ssl_context=(cert, key), debug=False)
