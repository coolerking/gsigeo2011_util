# -*- coding: utf-8 -*-
"""
日本のジオイド ジオイドモデルをWeb UIで可視化するモジュール。

python app.py を実行し http://127.0.0.1/5000 をブラウザで開く。
"""
import argparse
from flask import Flask, jsonify, render_template, request

from geoid import HeightManager

# 引数の定義及び読み込み
parser = argparse.ArgumentParser(description='Japan geoid height manager with web server')
parser.add_argument('--path', type=str, default='gsigeo2011_ver2_1.asc', help='Japan Geoid Height data file(asc) path')
parser.add_argument('--port', type=int, default=5000, help='listen port')
parser.add_argument('--host', type=str, default='127.0.0.1', help='web server host address')
parser.add_argument('--debug', type=bool, default=False, help='print debug lines')
args = parser.parse_args()

# ジオイドモデル管理クラスのインスタンス化
mgr = HeightManager(path=args.path, debug=args.debug)

# 2次元散布図データを取得
(x, y, z) = mgr.convert_xyz()
lats = list(x)
lots = list(y)
hgts = list(z)
scatter2d_data = []
total = len(lats)
for i in range(total):
    scatter2d_data.append({'x':float(lats[i]), 'y':float(lots[i])})
print(scatter2d_data)
#msg = {'data': [list(lats), list(lots)]}
msg = {'data': [lats, lots]}

# アプリケーションオブジェクト生成
app = Flask(__name__)
# session 用シークレットキー
app.secret_key='japan_geoid_model_web_ui'



@app.route('/', methods=['GET'])
def show_index():
    """
    index.html を表示する。
    """
    # templates/index.html を表示する
    return render_template('index.html')

@app.route('/scatter2d_data', methods=['POST'])
def get_scatter2d_data():
    return jsonify(msg)

@app.route('/height', methods=['POST'])
def get_height():
    """
    ジオイド高を返却する。
    """
    # パラメータの取得
    req = request.json
    latitude = float(req.get('latitude'))
    longitude = float(req.get('longitude'))
    try:
        height = mgr.interpolate(latitude, longitude)
        return height
    except ValueError as e:
        print(f'target out of range:({latitude},{longitude})')

if __name__ == '__main__':
    """
    起動時のオプション処理を行い、Webアプリケーションを開始する。
    """
    app.run(debug=args.debug,host=args.host, port=args.port)