# -*- coding: utf-8 -*-
"""
国土交通省国土地理院基盤地図情報数値標高モデルを
扱うためのユーティリティモジュール。
"""
import gc
import os
import csv
import numpy as np
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt

import geopandas as gpd
from shapely.geometry import Point


class Mesh:
    """
    国土交通省国土地理院基盤地図情報数値標高モデルダウンロードファイル(GML形式)
    をよみこみ、GISデータとして変換するためのクラス。
    1インスタンスで1ダウンロードファイルを扱う。
    """
    
    """
    データなし時の数値
    """
    NO_DATA = -9999.0

    def __init__(self, path:str=None, debug:bool=False) -> None:
        """
        
        """
        # デバッグフラグ
        self.debug = debug

        # GMLファイルを読み込みメタ情報及びデータを
        # インスタンス変数へ格納
        self.load(path)

        # メタ情報から緯度経度リストを生成し
        # インスタンス変数へ格納
        (self.x, self.y) = self.create_xy(self.lower, self.upper, 
            self.low, self.high, self.order)

        # メタ情報表示
        if self.debug:
            self.show_meta()
    
    def load(self, path:str) -> None:
        """
        国土交通省国土地理院基盤地図情報数値標高モデルダウンロードファイル(GML形式)
        を読み込み、インスタンス変数へ格納する。
        全件データ要素をインスタンス変数へ格納するため、メモリ不足に注意。

        Parameters
        ----
        path:str        読み込み対象ファイルパス
        """
        # XMLファイルパス
        self.path = path

        # XMLスキーママッピング
        prefix_map = {
           'gml': 'http://www.opengis.net/gml/3.2',
            '': 'http://fgd.gsi.go.jp/spec/2008/FGD_GMLSchema',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }

        # XMLファイルのパース
        root_element = ET.parse(path).getroot()

        # データ名称
        self.name = root_element.find('.//gml:name', prefix_map).text
        # データの説明
        self.description = root_element.find('.//gml:description', prefix_map).text
        # メッシュ番号
        self.mesh_no = root_element.find('.//mesh', prefix_map).text
        # データ種類
        self.mesh_type = root_element.find('.//type', prefix_map).text

        # メッシュ矩形左下頂点位置
        lower_element = root_element.find('.//gml:lowerCorner', prefix_map).text.split()
        self.lower = [float(lower_element[0]), float(lower_element[1])]
        # メッシュ矩形右上頂点位置
        upper_element = root_element.find('.//gml:upperCorner', prefix_map).text.split()
        self.upper = [float(upper_element[0]), float(upper_element[1])]

        grid_element = root_element.find('.//gml:Grid', prefix_map)
        low_coord = grid_element.find('.//gml:low', prefix_map).text.split()
        high_coord = grid_element.find('.//gml:high', prefix_map).text.split()
        axislavels_element = grid_element.find('.//gml:axisLabels', prefix_map).text.split()

        # データ始点位置、データ終点位置
        if axislavels_element[0] == 'y':
            # 先頭ラベルが 'y' なら座標位置を置換
            self.low =  [self.low[1],  self.low[0]]
            self.high = [self.high[1], self.high[0]]
        else:
            self.low =  [int(low_coord[0]),  int(low_coord[1])]
            self.high = [int(high_coord[0]), int(high_coord[1])]

        seq_rule_element = root_element.find('.//gml:sequenceRule', prefix_map)
        order_element = seq_rule_element.get('order')

        # メッシュデータの並び方
        self.seq_rule = seq_rule_element.text

        # メッシュデータの方向
        if '-x' in order_element and '-y' in order_element:
            # X(緯度、横軸)方向負、Y(経度、縦軸)方向負
            self.order = [-1, -1]
        elif '-x' in order_element and '+y' in order_element:
            # X(緯度、横軸)方向負、Y(経度、縦軸)方向正
            self.order = [-1, 1]
        elif '+x' in order_element and '-y' in order_element:
            # X(緯度、横軸)方向正、Y(経度、縦軸)方向負
            self.order = [1, -1]
        else:
            # X(緯度、横軸)方向正、Y(経度、縦軸)方向正
            self.order = [1, 1]

        data_block_element = root_element.find('.//gml:DataBlock', prefix_map)

        # データ要素の種類
        self.uom = data_block_element.find('.//gml:QuantityList', prefix_map).get('uom')

        # データ全要素
        tupples = data_block_element.find('.//gml:tupleList', prefix_map).text.split()

        # 各要素の種別
        self.types = []
        # 各要素の標高
        self.z = []
        for tupple in tupples:
            point = tupple.strip().split(',')
            self.types.append(point[0])
            self.z.append(float(point[1]))

        # ガーベージコレクション
        del root_element, lower_element, upper_element, \
            grid_element, axislavels_element, seq_rule_element, order_element, \
            data_block_element, tupples
        gc.collect()

    def create_xy(self, lower:list, upper:list, 
    low:list, high:list, order:list, debug:bool=False) -> tuple[list, list]:
        """
        メタ情報をもとに緯度(X)経度(Y)リストを生成する。

        Parameters
        ----
        lower:list
            矩形左下頂点座標（緯度経度）
        upper:list
            矩形左下頂点座標（緯度経度）
        low:list
            メッシュデータ開始位置（緯度方向インデックス、経度方向インデックス）
        high:list
            メッシュデータ終了位置（緯度方向インデックス、経度方向インデックス）
        order:list
            緯度方向正（南から北）負（北から南）、経度方向正（東から西）負（西から東）
        debug:bool
            デバッグオプション

        Returns
        ----
        tuple(list, list)
            緯度リスト（単位：度）
            経度リスト（単位：度）
        """
        # x 緯度
        # 最大値、最小値
        x_max = max(lower[0], upper[0])
        x_min = min(lower[0], upper[0])

        if debug:
            print(f'min:{x_min}, max:{x_max}')
        # 緯度方向メッシュ点の数 -1
        points_x = abs(high[0] - low[0])
        if debug:
            print(f'points_x = {points_x}')
        # 緯度方向範囲
        edge_x = x_max - x_min
        if debug:
            print(f'({upper[0]},{lower[0]}) edge_x = {edge_x}')
        # 緯度方向メッシュ間の距離
        delta_x = edge_x / points_x
        if debug:
            print(f'delta_x = {delta_x}')

        mesh_x = []
        for i in range(points_x):
            mesh_x.append(x_min + i * delta_x)
        mesh_x.append(x_max)

        if order[0] < 0:
            mesh_x = mesh_x.reverse()

        # y 経度
        # 最大値、最小値
        y_max = max(lower[1], upper[1])
        y_min = min(lower[1], upper[1])
        if debug:
            print(f'min:{y_min}, max:{y_max}')
        # 経度方向メッシュ点の数 -1
        points_y = abs(high[1] - low[1])
        if debug:
            print(f'points_y = {points_y}')
        # 経度方向範囲
        edge_y = y_max - y_min
        if debug:
            print(f'({upper[1]},{lower[1]}) edge_y = {edge_y}')
        # 緯度方向メッシュ間の距離
        delta_y = edge_y / points_y
        if debug:
            print(f'delta_y = {delta_y}')

        mesh_y = []
        for i in range(points_y):
            mesh_y.append(y_min + i * delta_y)
        mesh_y.append(y_max)

        if order[1] < 0:
            mesh_y.reverse()

        x, y = [], []
        for y_i in range(len(mesh_y)):
            for x_i in range(len(mesh_x)):
                x.append(mesh_x[x_i])
                y.append(mesh_y[y_i])

        # 中間データのガーベージコレクト
        del mesh_x, mesh_y
        gc.collect()

        # 緯度リスト、経度リストの返却
        return (x, y)

    def show_meta(self):
        """
        メタ情報を表示する。
        """
        print(f'path:        {self.path}')
        print(f'name:        {self.name}')
        print(f'description: {self.description}')
        print(f'mesh no:     {self.mesh_no}')
        print(f'mesh type:   {self.mesh_type}')
        print(f'mesh range:  [{self.lower[0]}, {self.lower[1]}] - [{self.upper[0]}, {self.upper[1]}]')
        print(f'mesh position range: [{self.low[0]}, {self.low[1]}] - [{self.high[0]}, {self.high[1]}] sequence: {self.seq_rule}')
        print(f'mesh order:          [{self.order[0]}, {self.order[1]}]')
        print(f'mesh length: x:{len(self.x)}, y:{len(self.y)}, z:{len(self.z)} type:{len(self.types)} uom:{self.uom}')

    def get_histgram(self, path:str=None):
        """
        標高値のヒストグラムを表示・保存する。
        負値(値なし相当値-9999.0含む)は対象外とする。

        Parameters
        ----
        path:str
            保存先ファイルパス、指定しない場合表示される。
        """

        # フォントファミリ指定
        plt.rcParams['font.family'] = 'Meiryo'

        # figure の作成
        fig = plt.figure(figsize=(8, 6))

        # subplot の追加
        ax = fig.add_subplot()

        # タイトルの作成
        ax.set_title(self.path, size=10)
        ax.hist(self.z, range(0, int(np.max(np.array(self.z)))+1))
        
        # 保存先パスが定義されていない場合
        if path is None:
            # グラフを表示
            plt.show()
        else:
            plt.savefig(path)
            if self.debug:
                print(f'saved histgram to {path}')

    def get_scatter3d(self, path:str=None) -> None:
        """
        3次元散布図を表示・保存する

        Parameters
        ----
        path:str
            3次元散布図保存先ファイルパス、指定なしの場合表示させる
        """
        # フォントファミリ指定
        plt.rcParams['font.family'] = 'Meiryo'

        # figure の作成
        fig = plt.figure(figsize=(8, 6))

        # subplot の追加
        ax = fig.add_subplot(projection='3d')

        # タイトルの作成
        ax.set_title(self.path, size=10)
 
        # 軸ラベルのサイズと色を設定
        ax.set_xlabel('latitude(north)',size=10,color='black')
        ax.set_ylabel('longitude(east)',size=10,color='black')
        ax.set_zlabel('height(m)', size=10, color='black')

        # リストx:緯度、リストy:経度、リストz:ジオイド高 に変換
        (x, y, z) = self.convert_xyz()

        # 散布図を描画
        ax.scatter(x, y, z, s=1, c='red')

        # 保存先指定なし
        if path is None:
            # 散布図を表示
            plt.show()
        else:
            # 散布図を保存
            plt.savefig(path)
            if self.debug:
                print(f'saved 3d scatter to {path}')

    def convert_xyz(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        標高データをnp.ndarray形式のリストX(緯度、単位：度)、
        Y(経度、単位：度)、Z(標高、単位：メートル)に変換する。
        ただし、標高データがない座標はリストに加えない。
        
        Returns
        ----
        tuple[x:np.ndarray, y:np.ndarray, z:np.ndarray]
            x: 緯度、単位：度
            y: 経度、単位：度
            z: ジオイド高、単位：メートル
        """
        # NO_DATA除外されたリスト作成
        _x = [] # 経度(東経)
        _y = [] # 緯度(北緯)
        _z = [] # 標高(m)
        for i in range(len(self.z)):
            if self.z[i] > self.NO_DATA:
                _x.append(self.x[i])
                _y.append(self.y[i])
                _z.append(self.z[i])

        if self.debug:
            print(f'omitted no data -> x:{len(_x)}, y:{len(_y)}, z:{len(_z)}')

        # ndarray化して返却
        return(np.array(_x, dtype=float), np.array(_y, dtype=float), np.array(_z, dtype=float))

    def save_csv(self, path:str) -> None:
        """
        CSV形式ファイルとして保存する。
        緯度、経度、標高、種類の順に保存される。

        Parameters
        ----
        path:str
            保存先ファイルパス。
        """
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=',')
            for i in range(len(self.z)):
                writer.writerow([self.x[i], self.y[i], self.z[i], self.types[i]])
        if self.debug:
            print(f'saved csv to {path}')

    def save_geojson(self, path:str, crs:str='EPSG:4326') -> None:
        """
        指定された測地系でGeoJSON形式として保存する。

        Parameters
        ----
        crs:str
            測地系。デフォルトは世界測地系(EPSG:4326)
        """
        self.get_gpd(crs=crs).to_file(driver='GeoJSON', filename=path)
        if self.debug:
            print(f'saved geojson to {path}')

    def save_geoshp(self, path:str='geoid.shp', crs:str='EPSG:4326'):
        """
        指定された測地系でShp形式で保存する。

        Parameters
        ----
        path:str
            GIS Shape形式ファイルパス
        crs:str
            座標系（デフォルト: 'EPSG:4326'）
        """
        self.get_gpd(crs=crs).to_file(driver='ESRI Shapefile', filename=path)
        if self.debug:
            print(f'saved shp to {path}')

    def get_gpd(self, crs:str='EPSG:4326') -> gpd.GeoDataFrame:
        """
        DEMデータをGeoDataFrame オブジェクトとして取得する。
        データなし(-9999.0)である座標は削除済みオブジェクトとなる。

        Parameters
        ----
        crs:str
            座標系（デフォルト EPSG:4326）
        
        Returns
        ----
        gpd.GeoDataFrame
            ジオイドモデル(標高:'height'属性、種類：'type'属性)
        """
        _x = [] # 経度(東経)
        _y = [] # 緯度(北緯)
        _z = [] # 標高(m)
        _t = [] # 種類
        for i in range(len(self.z)):
            if self.z[i] > self.NO_DATA:
                _x.append(self.x[i])
                _y.append(self.y[i])
                _z.append(self.z[i])
                _t.append(self.types[i])
        geometry = []
        total = len(_x)
        for i in range(total):
            geometry.append(Point(_x[i], _y[i]))
        return gpd.GeoDataFrame({'height':_z, 'type':_t, 'geometry':geometry}, crs=crs)

if __name__ == '__main__':
    """
    疎通テスト。
    """
    # 10mデータサンプル
    '''
    dir_path_10m = 'FG-GML-5339-25-DEM10B'
    dem10b_path = os.path.join(dir_path_10m, 'FG-GML-5339-25-dem10b-20161001.xml')
    print('****************')
    dem10b = Mesh(dem10b_path, True)
    dem10b.get_histgram(dem10b_path + '_hist.png')
    dem10b.get_scatter3d(dem10b_path + '_3d.png')
    dem10b.save_csv(dem10b_path + '.csv')
    dem10b.save_geojson(dem10b_path + '.json')
    dem10b.save_geoshp(dem10b_path + '.shp')

    # 5mデータサンプル
    dir_path_5m = 'FG-GML-5339-25-DEM5A'
    dem5a_path = os.path.join(dir_path_5m, 'FG-GML-5339-25-00-DEM5A-20161001.xml')
    print('****************')
    dem5a = Mesh(dem5a_path, True)
    dem5a.get_histgram(dem5a_path + '_hist.png')
    dem5a.get_scatter3d(dem5a_path + '_3d.png')
    dem5a.save_csv(dem5a_path + '.csv')
    dem5a.save_geojson(dem5a_path + '.json')
    dem5a.save_geoshp(dem5a_path + '.shp')
    '''

    dir_path_10m = 'FG-GML-5339-26-DEM10B'
    dem10b_path = os.path.join(dir_path_10m, 'FG-GML-5339-26-dem10b-20161001.xml')
    print('****************')
    dem10b = Mesh(dem10b_path, True)
    dem10b.get_histgram(dem10b_path + '_hist.png')
    dem10b.get_scatter3d(dem10b_path + '_3d.png')
    dem10b.save_csv(dem10b_path + '.csv')
    dem10b.save_geojson(dem10b_path + '.json')
    dem10b.save_geoshp(dem10b_path + '.shp')