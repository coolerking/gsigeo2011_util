# -*- coding: utf-8 -*-
"""
geoid.py (Height Manager)テストコード

pytestパッケージが必要です。

"""
# テストフレームワーク
import pytest

# ターゲットモジュール/クラスのimport
from geoid import HeightManager

def test_interpolate(path:str='gsigeo2011_ver2_1.asc', debug:str=True) -> None:
    """
    内挿計算のテスト。
    """
    # float値誤差
    ep = 0.00005
    # ターゲットインスタンス
    mgr = HeightManager(path, debug)

    # テストコード
    print('1:test-1   (353928.3808, 1394431.7968) -> 36.6034')
    assert 36.6034 == pytest.approx(mgr.interpolate(35.65788355, 139.74216577), ep)
    
    print('2:test-2   (100000.0000, 1390000.0000) -> 999.0000 (ValueError')
    with pytest.raises(ValueError) as e:
        mgr.interpolate(10.00000000, 139.00000000)

    print('3:test-3   (440000.0000, 1520000.0000) -> 999.0000(ValueError)')
    with pytest.raises(ValueError) as e:
        mgr.interpolate(44.00000000, 152.00000000)

    print('4:test-4   (330000.0000, 1310000.0000) -> 33.1781')
    assert 33.1781 == pytest.approx(mgr.interpolate(33.00000000, 131.00000000), ep)

    print('5:test-5   (263800.0000, 1275100.0000) -> 33.0250')
    assert 33.0250 == pytest.approx(mgr.interpolate(26.633333, 127.85), ep)

    print('6:test-6   (263800.0000, 1275110.0000) -> 33.0234')
    assert 33.0234 == pytest.approx(mgr.interpolate(26.633333, 127.852778), ep)

    print('7:test-7   (263800.0000, 1275230.0000) -> 33.0102')
    assert 33.0102 == pytest.approx(mgr.interpolate(26.633333, 127.875), ep)

    print('8:test-8   (263800.0000, 1275800.0000) -> 32.8603')
    assert 32.8603 == pytest.approx(mgr.interpolate(26.633333, 127.966667), ep)

    print('9:test-9   (263500.0000, 1280000.0000) -> 32.5583')
    assert 32.5583 == pytest.approx(mgr.interpolate(26.583333, 128.00000000), ep)

    # Geoデータテスト
    import geopandas as gpd
    import matplotlib.pyplot as plt
    geo = mgr.get_gpd()
    world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
    japan = world[world['name']=='Japan']
    ax = japan.plot()
    geo.plot(ax=ax, color='red', markersize=2)
    plt.savefig(path + '.png')

def test_clsmethod():
    # float値誤差
    ep = 0.001

    # テスト 1275110.0000
    (d, m, s) = HeightManager.to_dms(127.852778)
    assert 127 == d
    assert 51 == m
    assert 10.0000 == pytest.approx(s, ep)

    # テスト 263500.0000
    (d, m, s) = HeightManager.to_dms(26.583333)
    assert 26 == d
    #assert 35 == m
    assert 34 == m
    #assert 0.0 == pytest.approx(s, ep)
    assert 59.999 == pytest.approx(s, ep)

def test_scatter2d(path:str='gsigeo2011_ver2_1.asc', scatter_path='gsigeo2011_ver2_1_2d.png', debug:bool=True):
    """
    2次元散布図の保存
    """
    # ターゲットインスタンス
    mgr = HeightManager(path, debug)
    #  2次元散布図の保存
    mgr.get_scatter2d(scatter_path)

def test_scatter3d(path:str='gsigeo2011_ver2_1.asc', scatter_path='gsigeo2011_ver2_1_3d.png', debug:bool=True):
    """
    3次元散布図の保存
    """
    # ターゲットインスタンス
    mgr = HeightManager(path, debug)
    #  3次元散布図の保存
    mgr.get_scatter3d(scatter_path)

if __name__ == '__main__':
    """
    テストコードを実行する。
    """
    import argparse
    parser = argparse.ArgumentParser(description='gioid.py test code')
    parser.add_argument('--path', type=str, default='gsigeo2011_ver2_1.asc', help='Japan Geoid Height data file(asc) path')
    parser.add_argument('--debug', type=bool, default=False, help='print debug lines')
    args = parser.parse_args()

    # テストメソッド実行
    test_interpolate(path=args.path, debug=args.debug)
    test_scatter2d(path=args.path, scatter_path=args.path+'_2d.png', debug=args.debug)
    test_scatter3d(path=args.path, scatter_path=args.path+'_3d.png', debug=args.debug)
