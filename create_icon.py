"""
create_icon.py
Generates a simple app icon and converts it to .icns for macOS.
Run once: python create_icon.py
"""

import os
import struct
import zlib


def create_png(size=1024):
    """Creates a simple green circle PNG icon in memory."""

    def write_chunk(chunk_type, data):
        chunk_len = struct.pack('>I', len(data))
        chunk_data = chunk_type + data
        chunk_crc = struct.pack('>I', zlib.crc32(chunk_data) & 0xffffffff)
        return chunk_len + chunk_data + chunk_crc

    # PNG header
    png_header = b'\x89PNG\r\n\x1a\n'

    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)
    ihdr = write_chunk(b'IHDR', ihdr_data)

    # Image data — green background with white circle
    raw_rows = []
    cx, cy, r = size // 2, size // 2, int(size * 0.42)
    ir = int(size * 0.22)

    for y in range(size):
        row = bytearray()
        for x in range(size):
            dx, dy = x - cx, y - cy
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < r:
                if dist < ir:
                    # White inner circle (coin hole effect)
                    row += bytearray([248, 250, 252])
                else:
                    # Green ring
                    row += bytearray([22, 163, 74])
            else:
                # Transparent-ish background (dark blue)
                row += bytearray([30, 58, 95])
        raw_rows.append(b'\x00' + bytes(row))

    compressed = zlib.compress(b''.join(raw_rows), 9)
    idat = write_chunk(b'IDAT', compressed)
    iend = write_chunk(b'IEND', b'')

    return png_header + ihdr + idat + iend


def create_icns():
    """Creates a .icns file from PNG data for macOS."""
    os.makedirs("assets", exist_ok=True)

    # Save PNG files at required sizes
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    png_files = {}

    for size in sizes:
        png_data = create_png(size)
        path = f"assets/icon_{size}.png"
        with open(path, 'wb') as f:
            f.write(png_data)
        png_files[size] = path
        print(f"✅ Created icon_{size}.png")

    # Build .icns using iconutil (macOS built-in tool)
    iconset_dir = "assets/BudgetWise.iconset"
    os.makedirs(iconset_dir, exist_ok=True)

    # macOS requires specific filenames inside .iconset
    iconset_map = {
        16:   "icon_16x16.png",
        32:   "icon_16x16@2x.png",
        32:   "icon_32x32.png",
        64:   "icon_32x32@2x.png",
        128:  "icon_128x128.png",
        256:  "icon_128x128@2x.png",
        256:  "icon_256x256.png",
        512:  "icon_256x256@2x.png",
        512:  "icon_512x512.png",
        1024: "icon_512x512@2x.png",
    }

    import shutil
    for size, filename in iconset_map.items():
        src = png_files.get(size, png_files[512])
        dst = os.path.join(iconset_dir, filename)
        shutil.copy(src, dst)

    # Convert .iconset → .icns
    result = os.system(f"iconutil -c icns {iconset_dir} -o assets/BudgetWise.icns")

    if result == 0:
        print("✅ BudgetWise.icns created successfully")
    else:
        print("⚠️  iconutil failed — using PNG as fallback")
        shutil.copy(png_files[512], "assets/BudgetWise.png")

    # Cleanup temp files
    shutil.rmtree(iconset_dir)
    for path in png_files.values():
        os.remove(path)

    print("🎨 Icon generation complete")


if __name__ == "__main__":
    create_icns()