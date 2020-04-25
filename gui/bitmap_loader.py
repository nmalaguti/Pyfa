# =============================================================================
# Copyright (C) 2010 Diego Duclos
#
# This file is part of pyfa.
#
# pyfa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyfa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyfa.  If not, see <http://www.gnu.org/licenses/>.
# =============================================================================

import math
import io
import os.path
import zipfile
from collections import OrderedDict

# noinspection PyPackageRequirements
import wx
from logbook import Logger

import config


pyfalog = Logger(__name__)


class BitmapLoader:
    # Can be None if we're running from tests
    if config.imgsZIP is None:
        pyfalog.info("Using local image files.")
        archive = None
    else:
        try:
            archive = zipfile.ZipFile(config.imgsZIP, 'r')
            pyfalog.info("Using zipped image files.")
        except (IOError, TypeError):
            pyfalog.info("Using local image files.")
            archive = None

    cached_bitmaps = OrderedDict()
    dont_use_cached_bitmaps = False
    max_cached_bitmaps = 500

    gen_scale = None
    res_scale = None

    @classmethod
    def getStaticBitmap(cls, name, parent, location):
        bitmap = cls.getBitmap(name or 0, location)
        if bitmap is None:
            return None
        static = wx.StaticBitmap(parent)
        static.SetBitmap(bitmap)
        return static

    @classmethod
    def getBitmap(cls, name, location):
        if cls.dont_use_cached_bitmaps:
            return cls.loadBitmap(name, location)

        path = "%s%s" % (name, location)

        if len(cls.cached_bitmaps) == cls.max_cached_bitmaps:
            cls.cached_bitmaps.popitem(False)

        if path not in cls.cached_bitmaps:
            bmp = cls.loadBitmap(name, location)
            cls.cached_bitmaps[path] = bmp
        else:
            bmp = cls.cached_bitmaps[path]

        return bmp

    @classmethod
    def getImage(cls, name, location):
        bmp = cls.getBitmap(name, location)
        if bmp is not None:
            return bmp.ConvertToImage()
        else:
            return None

    @classmethod
    def loadBitmap(cls, name, location):
        if cls.gen_scale is None:
            cls.gen_scale = 1 if 'wxGTK' in wx.PlatformInfo else wx.GetApp().GetTopWindow().GetContentScaleFactor()
            cls.res_scale = math.ceil(cls.gen_scale)  # We provide no images with non-int scaling factor
        # Find the biggest image we have, according to our scaling factor
        filename = img = None
        current_res_scale = cls.res_scale
        while img is None and current_res_scale > 0:
            filename, img = cls.loadScaledBitmap(name, location, current_res_scale)
            if img is not None:
                break
            current_res_scale -= 1

        if img is None:
            pyfalog.warning("Missing icon file: {0}/{1}".format(location, filename))
            return None

        w, h = img.GetSize()
        extraScale = cls.gen_scale / current_res_scale

        bmp = wx.Bitmap(img.Scale(int(w * extraScale), int(h * extraScale), quality=wx.IMAGE_QUALITY_NORMAL))
        return bmp

    @classmethod
    def loadScaledBitmap(cls, name, location, scale=1):
        """Attempts to load a scaled bitmap.

        Args:
            name (str): TypeID or basename of the image being requested.
            location (str): Path to a location that may contain the image.
            scale (int): Scale factor of the image variant to load.

        Returns:
            (str, wx.Image): Tuple of the filename that may have been loaded and the image at that location. The
                filename will always be present, but the image may be ``None``.
        """
        filename = "{0}@{1}x.png".format(name, scale)
        img = cls.loadImage(filename, location)
        if img is None and scale == 1:
            filename = "{0}.png".format(name)
            img = cls.loadImage(filename, location)
        return filename, img

    @classmethod
    def loadImage(cls, filename, location):
        if cls.archive:
            path = os.path.join(location, filename)
            if os.sep != "/" and os.sep in path:
                path = path.replace(os.sep, "/")

            try:
                img_data = cls.archive.read(path)
                bbuf = io.BytesIO(img_data)
                return wx.Image(bbuf)
            except KeyError:
                pyfalog.warning("Missing icon file from zip: {0}".format(path))
        else:
            path = os.path.join(config.pyfaPath, 'imgs', location, filename)

            if os.path.exists(path):
                return wx.Image(path)
            else:
                return None
