'''
Author: Eur3ka njuscimenphy@gmail.com
Date: 2023-03-02 18:35:55
LastEditors: Eur3ka njuscimenphy@gmail.com
LastEditTime: 2023-05-06 16:31:15
Description: 
==========================================
摸鱼写代码的物理人 Koria~
佩拉小姐, 你的眼镜怎么又掉了？
==========================================
Copyright (c) 2023 by NJU/Eur3ka, All Rights Reserved. 
'''
import warnings
import numpy as np
import gdspy
import os
import pyclipper as pp
from enum import Enum
from PIL import Image


class Direction(Enum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3


def get_readout_resonator(length: float,
                          center_width: float,
                          gap: float,
                          anchor: tuple[float, float] = (0, 0),
                          layer: int = 1,
                          couple_end_length: float = 300.0,
                          unit_length: float = 200.0,
                          qubit_end_length: float = 300.0,
                          max_s_unit_count: int = 100) -> gdspy.Path:
    """
绘制读取腔
    :param length: 读取腔的长度
    :param center_width: 中心导体宽度
    :param gap: gap宽度
    :param anchor: 腔的定位点
    :param layer: 腔所处的图层
    :param couple_end_length: 读取腔和读取线之间的耦合长度
    :param unit_length: 读取腔的s单元中的直线部分的长度
    :param qubit_end_length: 读取腔的qubit耦合端结构长度
    :param max_s_unit_count: 最大允许出现的s单元数目
    :return: 读取腔的Path对象
    """
    # 提前减去qubit端的传输线接口长度
    length_without_qubit_end = length - (qubit_end_length +
                                         2.5 * center_width * np.pi)
    path = gdspy.Path(gap,
                      initial_point=anchor,
                      number_of_paths=2,
                      distance=center_width + gap)
    path.segment(couple_end_length)
    # ‘S’ unit, length = 2.0 * 5.0 * center_width * np.pi + 2.0 * unit_length
    #                                 ===
    #                                    \\
    #                                    ||
    #                                   //
    #              =====================
    #            //
    #           ||
    #           \\
    #             ======================
    s_unit_length = 10.0 * center_width * np.pi + 2.0 * unit_length
    if length_without_qubit_end < couple_end_length:
        warnings.warn(
            "Invalid length of readout resonator, because it less than coupled length!"
        )
    else:
        # 绘制了太多的s unit可能导致读取腔过长，而难以布线
        if length_without_qubit_end > max_s_unit_count * s_unit_length + couple_end_length:
            warnings.warn(
                "The length of readout resonator is too long, please change the unit length"
            )
        while length_without_qubit_end - path.length > s_unit_length:
            path.turn(5.0 * center_width, "rr")
            path.segment(unit_length, "-x")
            path.turn(5.0 * center_width, "ll")
            path.segment(unit_length, "+x")
        if length_without_qubit_end - path.length < 10.0 * center_width * np.pi:
            warnings.warn(
                "The length of readout resonator is not suitable, please change the unit length."
            )
        else:
            delta_length = path.length + s_unit_length - length_without_qubit_end
            path.turn(5.0 * center_width, "rr")
            path.segment(unit_length - 0.5 * delta_length, "-x")
            path.turn(5.0 * center_width, "ll")
            path.segment(unit_length - 0.5 * delta_length, "+x")
            # qubit端的耦合接口
            path.turn(5.0 * center_width, "r")
            path.segment(qubit_end_length)
    print("=== Building readout resonator ===")
    print("length: %.2fum" % path.length)
    # print("preset length: %.2fum" % length)
    # print("Δl: %.2fum" % (length - path.length))
    print("coupled length: %.2fum" % couple_end_length)
    print("center = %.2fum, gap = %.2fum" % (center_width, gap))
    path.layers = [layer for _ in path.layers]
    return path


def get_squid(direction: Direction,
              base_length: float,
              anchor: tuple[float, float] = (0, 0),
              squid_size: tuple[float, float] = (0.15, 0.15),
              squid_pad_size: tuple[float, float] = (6, 8),
              xy_distance: tuple[float, float] = (18, 9),
              base_layer: int = 1,
              squid_layer: int = 2) -> list[gdspy.Polygon]:
    """
绘制带底部连接“钩子”的SQUID
    :param direction: 蒸镀方向
    :param base_length: “钩子”的长度
    :param anchor: 定位点
    :param squid_size: SQUID的结面积参数
    :param squid_pad_size: SQUID的pad大小
    :param xy_distance: SQUID的pad偏移量
    :param base_layer: SQUID的底部“钩子”所处的图层
    :param squid_layer: SQUID所处的图层
    :return: 带“钩子”SQUID的Polygon对象列表
    """
    if direction not in [Direction.UP, Direction.DOWN]:
        warnings.warn("Invalid direction %s, reset to %s" %
                      (direction, Direction.UP))
        direction = Direction.UP
    if squid_pad_size[0] < 4.0 or squid_pad_size[1] < 2.0:
        warnings.warn(
            "The pads of JJs are too small, which may cause some problems!")
        print("Resetting to default size (%.2f, %.2f)" % (6, 8))
    if base_length < squid_pad_size[1]:
        warn_str = "Base length is too short (less than %.2fum), which may cause some problems!" % squid_pad_size[
            1]
        warnings.warn(warn_str)
    if xy_distance[0] < 2.0 * squid_pad_size[0] or xy_distance[
            1] < squid_pad_size[1]:
        warn_str = "The pads of JJs are too closed (%.2f, %.2f), " % xy_distance + "under (%.2f, %.2f)" % squid_pad_size
        warnings.warn(warn_str)
        print("Resetting to default distance (%.2f, %.2f)" %
              (3.0 * squid_pad_size[0], squid_pad_size[1]))
        xy_distance = (3.0 * squid_pad_size[0], squid_pad_size[1])
    dx, dy = xy_distance
    px, py = squid_pad_size
    squid_with_base_list = []
    # 绘制SQUID
    squid_pad_list = [
        gdspy.Rectangle((0, 0), squid_pad_size, layer=squid_layer),
        gdspy.Rectangle((0, 0), squid_pad_size, layer=squid_layer),
        gdspy.Rectangle((0, 0), squid_pad_size, layer=squid_layer)
    ]
    squid_pad_list[1].translate(dx, 0)
    squid_pad_list[2].translate(0.5 * dx, dy)
    squid_v_line_length = dy - py + 2
    squid_h_line_length = 0.5 * dx - px + 2
    squid_v_line_list = [
        gdspy.Rectangle((0, 0), (squid_size[0], squid_v_line_length),
                        layer=squid_layer),
        gdspy.Rectangle((0, 0), (squid_size[0], squid_v_line_length),
                        layer=squid_layer)
    ]
    squid_h_line_list = [
        gdspy.Rectangle((0, 0), (squid_h_line_length, squid_size[1]),
                        layer=squid_layer),
        gdspy.Rectangle((0, 0), (squid_h_line_length, squid_size[1]),
                        layer=squid_layer)
    ]
    if direction == Direction.UP:
        squid_v_line_list[0].translate(px - 1 - squid_size[0], py)
        squid_v_line_list[1].translate(dx + 1, py)
        squid_h_line_list[0].translate(px - 2, dy + 1)
        squid_h_line_list[1].translate(0.5 * dx + px, dy + 1)
    elif direction == Direction.DOWN:
        squid_v_line_list[0].translate(0.5 * dx + 1, py - 2)
        squid_v_line_list[1].translate(0.5 * dx + px - 1 - squid_size[0],
                                       py - 2)
        squid_h_line_list[0].translate(px, py - 1 - squid_size[1])
        squid_h_line_list[1].translate(0.5 * dx + px - 2,
                                       py - 1 - squid_size[1])
    squid_with_base_list += squid_pad_list + squid_v_line_list + squid_h_line_list
    # 绘制底部的钩子
    base_list = [
        gdspy.Curve(0, 0).l(4.0 + 0.0j, 4.0 - base_length * 1.0j,
                            2.0 - base_length * 1.0j, 2.0 - 2.0j, 0.0 - 2.0j)
    ] * 3
    base_list = [
        gdspy.Polygon(base.get_points(),
                      layer=base_layer).translate(1, py - 1)
        for base in base_list
    ]
    base_list[1].mirror((0.5 * (dx + px), 0), (0.5 * (dx + px), 1))
    base_list[2].rotate(np.pi, center=(0.25 * dx + 0.5 * px, 0.5 * (dy + py)))

    squid_with_base_list += base_list
    for poly in squid_with_base_list:
        poly.translate(anchor[0], anchor[1])
    print("=== Building SQUID with base ===")
    print("Direction: ", direction.name)
    print("base line length: %.2fum" % base_length)
    print("SQUID JJs size: (%.2fum, %.2fum)" % squid_size)
    print("SQUID pad size: (%.2fum, %.2fum)" % squid_pad_size)
    print("dx = %.2fum, dy = %.2fum" % xy_distance)
    print("Layer: SQUID = %d/0, Base = %d/0" % (squid_layer, base_layer))
    return squid_with_base_list


def get_hex_qubit(r: float,
                  s: float,
                  gr: float,
                  gs: float,
                  d: float,
                  wp: float,
                  lp: float,
                  wg: float,
                  lg: float,
                  gg: float,
                  anchor: tuple[float, float] = (0, 0),
                  layer: int = 1,
                  inverse: bool = False) -> list[gdspy.Polygon]:
    """get_hex_qubit 绘制六边形 qubit 版图

    Args:
        r (float): 六边形边至中心的距离
        s (float): 切角处的切边长度
        gr (float): pad 与 qubit 之间的间隔
        gs (float): pad 与 切角处之间的间隔
        d (float): pad 长度
        wp (float): pad 尾部矩形宽度
        lp (float): pad 尾部矩形长度
        wg (float): 切角处 ground 矩形宽度
        lg (float): 切角处 ground 矩形长度
        gg (float): 切角处 ground 与切角处之间的间隔
        layer (int, optional): hex qubit的图层 Defaults to 1.
        inverse (bool, optional): 版图文件反相 Defaults to False.

    Returns:
        list[gdspy.Polygon]: hex qubit 版图
    """
    gds_list = []
    # 绘制中心导体
    r_point = (r - s) / np.sqrt(3) + r * 1.0j
    s_point = (r + s / 2) / np.sqrt(3) + (r - s / 2) * 1.0j
    qubit_points = np.array([
        np.array([r_point, s_point]) * np.exp(-n * 1.0j * np.pi / 3)
        for n in range(6)
    ]).flatten()
    qubit_points = [(p.real, p.imag) for p in qubit_points]
    hex_qubit = gdspy.Polygon(points=qubit_points, layer=layer)
    gds_list.append(hex_qubit)
    # 绘制 pad
    pad_anchor = (r + gr - 2 * gs - s) / np.sqrt(3) + (r + gr) * 1.0j
    l_u = d / np.sqrt(3) + d * 1.0j
    r_u = -(d + 2 * (r + gr - 2 * gs - s)) / np.sqrt(3) + d * 1.0j
    r_d = -2 * (r + gr - 2 * gs - s) / np.sqrt(3) + 0.0j
    pad_curve = gdspy.Curve(pad_anchor).l(l_u, r_u, r_d)
    pad_list = [
        gdspy.Polygon(pad_curve.get_points(), layer=layer),
        gdspy.Polygon(pad_curve.get_points(), layer=layer).rotate(np.pi / 3),
        gdspy.Polygon(pad_curve.get_points(),
                      layer=layer).rotate(2 * np.pi / 3),
        gdspy.Polygon(pad_curve.get_points(), layer=layer).rotate(np.pi),
        gdspy.Polygon(pad_curve.get_points(),
                      layer=layer).rotate(4 * np.pi / 3),
        gdspy.Polygon(pad_curve.get_points(),
                      layer=layer).rotate(5 * np.pi / 3)
    ]
    p_r_u = (-wp / 2, r + gr + d + lp)
    p_l_d = (wp / 2, r + gr + d)
    pad_list += [
        gdspy.Rectangle(p_r_u, p_l_d, layer=layer),
        gdspy.Rectangle(p_r_u, p_l_d, layer=layer).rotate(np.pi / 3),
        gdspy.Rectangle(p_r_u, p_l_d, layer=layer).rotate(2 * np.pi / 3),
        gdspy.Rectangle(p_r_u, p_l_d, layer=layer).rotate(np.pi),
        gdspy.Rectangle(p_r_u, p_l_d, layer=layer).rotate(4 * np.pi / 3),
        gdspy.Rectangle(p_r_u, p_l_d, layer=layer).rotate(5 * np.pi / 3)
    ]
    edge_p1 = -wp / 2 + (r + gr + d + lp) * 1.0j
    edge_p2 = edge_p1 + wp
    edge_points = np.array([
        np.array([edge_p1, edge_p2]) * np.exp(-n * 1.0j * np.pi / 3)
        for n in range(6)
    ]).flatten()
    edge_points = [(p.real, p.imag) for p in edge_points]
    gds = gdspy.Polygon(edge_points, layer=layer)
    gds_list += pad_list
    g_anchor = (0, np.sqrt((r - s / 4)**2 / 3 + (r - s / 4)**2))
    g_p1 = (g_anchor[0] - wg / 2, g_anchor[1] + gg + lg)
    g_p2 = (g_anchor[0] + wg / 2, g_anchor[1] + gg)
    ground_list = [
        gdspy.Rectangle(g_p1, g_p2, layer=layer).rotate(np.pi / 6),
        gdspy.Rectangle(g_p1, g_p2, layer=layer).rotate(np.pi / 2),
        gdspy.Rectangle(g_p1, g_p2, layer=layer).rotate(5 * np.pi / 6),
        gdspy.Rectangle(g_p1, g_p2, layer=layer).rotate(7 * np.pi / 6),
        gdspy.Rectangle(g_p1, g_p2, layer=layer).rotate(3 * np.pi / 2),
        gdspy.Rectangle(g_p1, g_p2, layer=layer).rotate(11 * np.pi / 6)
    ]
    gds_list += ground_list
    # 生成反相版图
    for g in gds_list:
        gds = gdspy.boolean(gds, g, "not")
    gds.layers = [1]
    # 版图整体偏移
    gds.translate(anchor[0], anchor[1])
    for i in range(len(gds_list)):
        gds_list[i] = gds_list[i].translate(anchor[0], anchor[1])
    return gds_list if inverse else [gds]


def pic2gds(pic_name: str,
            thresh: int,
            is_flip: bool = False) -> list[gdspy.Rectangle]:
    """pic2gds 图片转gds版图

    Args:
        pic_name (str): 图片文件名
        thresh (int): 图片灰度截断阈值
        inverse (bool, optional): 版图文件反相 Defaults to False.

    Returns:
        list[gdspy.Rectangle]: 版图
    """
    path = os.path.split(os.path.realpath(__file__))[0] + "\\"  # 获取当前py文件所在的目录
    img = Image.open(path + pic_name)
    # 图片灰度化
    img = img.convert("L")
    # 图片二值化
    img_arr = np.array(img)
    img_arr = np.where((img_arr <= thresh), img_arr, 255)
    img_arr = np.where((img_arr > thresh), img_arr, 0)
    # gds xy坐标与图片xy坐标手性相反 需要翻转
    img_arr = np.flip(img_arr, 0)
    gds_list = []
    yl, xl = img_arr.shape
    for j in range(yl):
        for i in range(xl):
            if img_arr[j, i] == (255 if is_flip else 0):
                rect = gdspy.Rectangle((i, j), (i + 1, j + 1), layer=1)
                gds_list.append(rect)
    return gds_list


def size_shape(
    polygons_pts: list[list[tuple[float, float]]],
    margin: int,
    layer: int = 4,
    cutting_limit: int = 20,
) -> list[gdspy.Polygon | gdspy.PolygonSet]:
    """高性能多边形扩张收缩运算
    
        gdspy 的布尔操作 比较消耗性能 (超过100会可感的降低速度)
        
        耗时较长可以考虑降低 cutting_limit 或者设定为0或负数来关闭布尔剪切

    Parameters
    ----------
    polygons_pts : list[list[tuple[float, float]]]
        版图文件中的多边形点集列表
    margin : int
        收缩扩张量（正数表示扩张，负数表示收缩）
    layer : int, optional
        图层 by dault 4
    cutting_limit : int, optional
        最大布尔剪切数 by default 20
        
        版图布尔剪切
        
        用于去除操作中可能出现的多边形内部的空洞产生的多余的多边形
        
        例如 圆环版图扩张或收缩操作后会出现两个圆形多边形而非原本的圆环
        
        这是因为 pyclipper 会改变图形原本的拓扑结构
    
    Returns
    -------
    list[gdspy.Polygon | gdspy.PolygonSet]
        完成运算之后的多边形列表
    """
    # pyclipper 库的运算基于整数进行，这里为了保证版图精度，进行一定程度的缩放
    SCALE_FACTOR = 1000
    polygons = []
    # 遍历版图文件中的全部多边形 分别进行扩张（收缩）运算
    print("margin start")
    progress_max = len(polygons_pts)
    step = 1 / progress_max
    rate = 0
    for polygon_pts in polygons_pts:
        rate += step
        gds_list = []
        pco = pp.PyclipperOffset()
        pco.MiterLimit = 10  # 角落处的扩张截断 设置过小可能出现圆角，设置过大可能导致过于尖锐的“刺”
        polygon_pts = pp.scale_to_clipper(polygon_pts, SCALE_FACTOR)
        pco.AddPath(polygon_pts, pp.JT_MITER, pp.ET_CLOSEDPOLYGON)
        s = pco.Execute(margin * SCALE_FACTOR)
        # 转换多边形点集为gds版图中的多边形
        for pts in s:
            pts = pp.scale_from_clipper(pts, SCALE_FACTOR)
            gds_list.append(gdspy.Polygon(pts, layer))
        gds = gds_list[0]
        # 布尔剪切 处理多边形内部的空洞问题
        num = len(gds_list)
        os.system("cls")
        progress_str = "#" * int(rate * 50) + "-" * int((1 - rate) * 50)
        print(progress_str + f" {int(rate*100)}%")
        if 1 < num and num < cutting_limit:
            print(f"cutting {num}")
            gds_list = gds_list[1:]
            for p in gds_list:
                gds = gdspy.boolean(gds, p, "not", layer=layer)
        polygons.append(gds)
    rate += step
    os.system("cls")
    progress_str = "#" * int(rate * 50) + "-" * int((1 - rate) * 50)
    print(progress_str + f" {int(rate*100)}%")
    print("complete")
    return polygons


def size_shape_from_file(
    input_file: str,
    output_file: str,
    margin: int,
    cutting_limit: int = 20,
):
    path = os.path.split(os.path.realpath(__file__))[0] + "\\"  # 获取当前py文件所在的目录
    lib1 = gdspy.GdsLibrary(infile=path + input_file)
    top = lib1.top_level()[0]
    polygons_pts = top.get_polygons()
    lib2 = gdspy.GdsLibrary()
    cell = lib2.new_cell("TOP")
    cell.add(size_shape(polygons_pts, margin, cutting_limit))
    lib2.write_gds(path + output_file)


if __name__ == '__main__':
    # demo and test
    lib = gdspy.GdsLibrary()
    lib.new_cell("ONE").add([
        get_readout_resonator(4911, 10, 5, anchor=(-500, 0)),
        get_readout_resonator(4875, 10, 5, anchor=(0, 0)),
        get_readout_resonator(4840, 10, 5, anchor=(500, 0)),
        get_readout_resonator(4805, 10, 5, anchor=(1000, 0))
    ])
    lib.new_cell("TWO") \
        .add(get_squid(Direction.UP, 10)) \
        .add(get_squid(Direction.UP, 10, anchor=(0, 50), xy_distance=(20, 20))) \
        .add(get_squid(Direction.DOWN, 20, anchor=(50, 50))) \
        .add(get_squid(Direction.DOWN, 20, anchor=(50, 0), xy_distance=(20, 20)))
    lib.new_cell("THREE")\
        .add(get_hex_qubit(4, 1, 0.5, 0.5, 2, 2, 4, 1, 5, 0.5))\
        .add(get_hex_qubit(4, 1, 0.5, 0.5, 2, 2, 4, 1, 5, 0.5,anchor=(30,0),inverse=True))
    gdspy.LayoutViewer(lib)
    # size shape demo
    input_file = "3.GDS"
    output_file = "3s.GDS"
    lib1 = gdspy.GdsLibrary(infile=input_file)
    top = lib1.top_level()[0]
    polygons_pts = top.get_polygons()
    lib2 = gdspy.GdsLibrary("Demo")
    cell = lib2.new_cell("TOP")
    cell.add(size_shape(polygons_pts, 40))
    gdspy.LayoutViewer(lib2)
    # lib2.write_gds(output_file)