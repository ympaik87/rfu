# PIX2RFU

## How to use

### 1. Make Datasheet in CFX96 format from the real-time PCR images

To create a datasheet from entire images

```bash
$ activate rfu
$ cd rfu
# for a 16 well image (latest algorithm)
$ python pix2rfu_16well.py "F:/path to experiment directory"
# for switching back to previous algoritm
$ python pix2rfu_16well_legacy.py "F:/path to experiment directory"
```

It will create `DSP_datasheet` folder in a higher level from the experiment path, and save datasheets according to the CFX96 format.

if there are missing dye,

```bash
$ python pix2rfu_16well.py "F:/path to experiment directory" -d <missing dyes>
# for example, if FAM and HEX channels are missing
$ python pix2rfu_16well.py "F:/path to experiment directory" -d f h
```

The acceptable inputs are the following:

Intended Value | Valid Input
---------------|-------------
FAM | `f`
HEX | `h`
Cal Red 610 | `c`
Quasar 670 | `q6`
Quasar 705 | `q7`

### 2. Get image processing result from an image of single camera test

If you wish to take a look at an image processing result with single image for the test purpose, try the following feature:

```bash
$ python pix2rfu_16well.py "F:/path to a 16 well image" s
```

![Result Image2](doc/Single_Result_2fa4d62-0_0_c-190812_135311_(new).jpg)
It is composed of 4 images, a heatmap, and one data table.

* Original: the original image from camera with cropping area as a red rectangle
* Gray: the 2D density plot from cropped image with sum of RGB
* Reference: the reference image for locating wells
* Processed Result: the result image with objects with well location
* Data table: table of RFU values, which are sum of RGB, corresponding to their
  well location
* Heatmap: show each RFUs devided by the mean of the 16well RFUs in order to
  visualize their uniformity.

Similary, you can generate the image result with previous algorithm

```bash
$ python pix2rfu_16well_legacy.py "F:/path to a 16 well image" s
```

This will produce the following images.
![Result Image](doc/Single_Result_2fa4d62-0_0_c_(old).jpg)
It is composed of 4 images, a heatmap, and one data table.

* Original: the original image from camera with cropping area as a red rectangle
* Gray: the 2D density plot from cropped image with sum of RGB
* Labeled: the image of labeled objects after image processing the gray image
* Processed Result: the result image with objects with well location
* Data table: table of RFU values, which are sum of RGB, corresponding to their
  well location
* Heatmap: show each RFUs devided by the mean of the 16well RFUs in order to
visualize their uniformity.

## Requirements

### Environment

* Python 3.5.3
* Conda
* git

### Installation with virtual environment (Windows)

```bash
$ git clone https://github.com/ympaik87/rfu.git
$ conda create -n rfu python=3.5.3
# used python 3.5 because RP3's default Python version is the one
$ activate rfu
$ cd rfu
$ pip install -r requirements.txt
```

### Installation (Linux)

```bash
# library dependency for scikit-image
$ sudo apt-get install libatlas-base-dev
$ sudo apt-get install python3-matplotlib python3-numpy python3-pil python3-scipy python3-tk
$ sudo apt-get install build-essential cython3
$ pip install -r requirements_rp3.txt
```

### To update the code

```bash
$ git pull
```

If you have local changes, and it causes to abort `git pull`, one way to get around this is the following:

```bash
# removing the local changes
$ git stash
# update
$ git pull
# put the local changes back on top of the recent update
$ git stash pop
```
