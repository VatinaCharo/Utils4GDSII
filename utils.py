import warnings

import gdspy
import numpy as np


def get_readout_resonator(
        length: float,
        center_width: float,
        gap: float,
        anchor: tuple = (0, 0),
        couple_end_length: float = 300.0,
        unit_length: float = 200.0,
        qubit_end_length: float = 300.0,
        max_s_unit_count: int = 100) -> gdspy.Path:
    """
构建读取腔
    :param length: 读取腔的长度
    :param center_width: 中心导体宽度
    :param gap: gap宽度
    :param anchor: 腔的定位点
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
    return path


if __name__ == '__main__':
    lib = gdspy.GdsLibrary()
    lib.add(
        lib.new_cell("TOP").add([
            get_readout_resonator(4911, 10, 5, anchor=(-500, 0)),
            get_readout_resonator(4875, 10, 5, anchor=(0, 0)),
            get_readout_resonator(4840, 10, 5, anchor=(500, 0)),
            get_readout_resonator(4805, 10, 5, anchor=(1000, 0))
        ])
    )
    gdspy.LayoutViewer(lib)
