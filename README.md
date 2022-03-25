# Utils4GDSII

**utils for drawing qubit chip gds**

## Manuel

The GDSII file is called a library in gdspy, which contains multiple cells.

Geometry must be placed in cells. So the object you got from utils.py must be added in a cell.

To save the **library** in a file called 'xxx.gds', you can use `write_gds`
function. Optionally, you can save an image of the **cell** as SVG by using
`write_svg` function. Also, you can display all cells using the internal viewer
`gdspy.LayoutViewer`.

## Demo

```python
import gdspy
from utils import get_readout_resonator, get_squid, Direction

lib = gdspy.GdsLibrary()
lib.new_cell("ONE").add([
    get_readout_resonator(4911, 10, 5, anchor=(-500, 0)),
    get_readout_resonator(4875, 10, 5, anchor=(0, 0)),
    get_readout_resonator(4840, 10, 5, anchor=(500, 0)),
    get_readout_resonator(4805, 10, 5, anchor=(1000, 0))
])
lib.new_cell("TWO")\
    .add(get_squid(Direction.UP, 10))\
    .add(get_squid(Direction.UP, 10, anchor=(0, 50), xy_distance=(20, 20)))\
    .add(get_squid(Direction.DOWN, 20, anchor=(50, 50)))\
    .add(get_squid(Direction.DOWN, 20, anchor=(50, 0), xy_distance=(20, 20)))
lib.write_gds("demo.gds")
gdspy.LayoutViewer(lib)
```

## Dependencies

+ `gdspy`
+ `numpy`

```commandline
pip install gdspy numpy
```