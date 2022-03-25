import warnings
from enum import Enum

import gdspy
import numpy as np


class Direction(Enum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3


def get_readout_resonator(
        length: float,
        center_width: float,
        gap: float,
        anchor: tuple[float, float] = (0, 0),
        layer: int = 1,
        couple_end_length: float = 300.0,
        unit_length: float = 200.0,
        qubit_end_length: float = 300.0,
        max_s_unit_count: int = 100
) -> gdspy.Path:
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
    length_without_qubit_end = length - (qubit_end_length + 2.5 * center_width * np.pi)
    path = gdspy.Path(gap, initial_point=anchor, number_of_paths=2, distance=center_width + gap)
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
        warnings.warn("Invalid length of readout resonator, because it less than coupled length!")
    else:
        # 绘制了太多的s unit可能导致读取腔过长，而难以布线
        if length_without_qubit_end > max_s_unit_count * s_unit_length + couple_end_length:
            warnings.warn("The length of readout resonator is too long, please change the unit length")
        while length_without_qubit_end - path.length > s_unit_length:
            path.turn(5.0 * center_width, "rr")
            path.segment(unit_length, "-x")
            path.turn(5.0 * center_width, "ll")
            path.segment(unit_length, "+x")
        if length_without_qubit_end - path.length < 10.0 * center_width * np.pi:
            warnings.warn("The length of readout resonator is not suitable, please change the unit length.")
        else:
            delta_length = path.length + s_unit_length - length_without_qubit_end
            path.turn(5.0 * center_width, "rr")
            path.segment(unit_length - 0.5 * delta_length, "-x")
            path.turn(5.0 * center_width, "ll")
            path.segment(unit_length - 0.5 * delta_length, "+x")
            # qubit端的耦合接口
            path.turn(5.0 * center_width, "r")
            path.segment(qubit_end_length)
    print("length: %.2fum" % path.length)
    print("preset length: %.2fum" % length)
    print("Δl: %.2fum" % (length - path.length))
    path.layers = [layer for _ in path.layers]
    return path


def get_squid(
        direction: Direction,
        base_length: float,
        squid_size: tuple[float, float] = (0.15, 0.15),
        anchor: tuple[float, float] = (0, 0),
        xy_distance: tuple[float, float] = (18, 9),
        base_layer: int = 1,
        squid_layer: int = 2
) -> list[gdspy.Polygon]:
    """
绘制带底部连接“钩子”的SQUID
    :param direction: 蒸镀方向
    :param base_length: “钩子”的长度
    :param squid_size: SQUID的结面积参数
    :param anchor: 定位点
    :param xy_distance: SQUID的间距
    :param base_layer: SQUID的底部“钩子”所处的图层
    :param squid_layer: SQUID所处的图层
    :return: 带“钩子”SQUID的Polygon对象列表
    """
    if direction not in [Direction.UP, Direction.DOWN]:
        warnings.warn("Invalid direction %s, reset to %s" % (direction, Direction.UP))
        direction = Direction.UP
    if base_length < 5.0:
        warnings.warn("Base length is too short (less than 6.0um), may cause some problems!")
    if xy_distance[0] < 12.0 or xy_distance[1] < 6.0:
        warnings.warn("The pads of JJs are too closed (%.2f, %.2f), under (12.0, 6.0)" % xy_distance)
        print("Resetting to default distance (18.0, 9.0)")
        xy_distance = (18, 9)
    squid_with_base_list = []
    # 绘制SQUID
    squid_pad_list = [
        gdspy.Rectangle((0, 0), (6, 6), layer=squid_layer),
        gdspy.Rectangle((0, 0), (6, 6), layer=squid_layer),
        gdspy.Rectangle((0, 0), (6, 6), layer=squid_layer)
    ]
    squid_pad_list[1].translate(xy_distance[0], 0)
    squid_pad_list[2].translate(0.5 * xy_distance[0], xy_distance[1])
    squid_v_line_length = xy_distance[1] - 4
    squid_h_line_length = 0.5 * xy_distance[0] - 4
    squid_v_line_list = [
        gdspy.Rectangle((0, 0), (squid_size[0], squid_v_line_length), layer=squid_layer),
        gdspy.Rectangle((0, 0), (squid_size[0], squid_v_line_length), layer=squid_layer)
    ]
    squid_h_line_list = [
        gdspy.Rectangle((0, 0), (squid_h_line_length, squid_size[1]), layer=squid_layer),
        gdspy.Rectangle((0, 0), (squid_h_line_length, squid_size[1]), layer=squid_layer)
    ]
    if direction == Direction.UP:
        squid_v_line_list[0].translate(5 - squid_size[0], 6)
        squid_v_line_list[1].translate(xy_distance[0] + 1, 6)
        squid_h_line_list[0].translate(4, xy_distance[1] + 1)
        squid_h_line_list[1].translate(0.5 * xy_distance[0] + 6, xy_distance[1] + 1)
    elif direction == Direction.DOWN:
        squid_v_line_list[0].translate(0.5 * xy_distance[0] + 1, 4)
        squid_v_line_list[1].translate(0.5 * xy_distance[0] + 5 - squid_size[0], 4)
        squid_h_line_list[0].translate(6, 5 - squid_size[1])
        squid_h_line_list[1].translate(0.5 * xy_distance[0] + 4, 5 - squid_size[1])
    squid_with_base_list += squid_pad_list + squid_v_line_list + squid_h_line_list
    # 绘制底部的钩子
    base_list = [
                    gdspy.Curve(0, 0).l(
                        4.0 + 0.0j,
                        4.0 - base_length * 1.0j,
                        2.0 - base_length * 1.0j,
                        2.0 - 2.0j,
                        0.0 - 2.0j
                    )] * 3
    base_list = [gdspy.Polygon(base.get_points(), layer=base_layer).translate(1, 5) for base in base_list]
    base_list[1].mirror((0.5 * xy_distance[0] + 3, 0), (0.5 * xy_distance[0] + 3, 1))
    base_list[2].rotate(np.pi, center=(0.25 * xy_distance[0] + 3, 0.5 * xy_distance[1] + 3))

    squid_with_base_list += base_list
    for poly in squid_with_base_list:
        poly.translate(anchor[0], anchor[1])
    return squid_with_base_list


if __name__ == '__main__':
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
    gdspy.LayoutViewer(lib)
