import os
import csv
import json
import struct
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from PIL import Image, ExifTags
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

SUPPORTED_EXT = ('.bmp', '.png', '.jpg', '.jpeg', '.jpe', '.gif',
                 '.tif', '.tiff', '.pcx')

EXIF_TAGS = {v: k for k, v in ExifTags.TAGS.items()} if PIL_AVAILABLE else {}


class ImageMetaParser:
    @staticmethod
    def parse_file(filepath):
        result = {
            'filename': os.path.basename(filepath),
            'path': filepath,
            'format': None,
            'width': None,
            'height': None,
            'dpi': None,
            'color_depth': None,
            'compression': None,
            'exif': '',
            'status': 'OK',
            'extra': ''
        }
        try:
            with open(filepath, 'rb') as f:
                header = f.read(32)
                if len(header) < 2:
                    result['status'] = 'Файл поврежден'
                    return result
                if header[:2] == b'BM':
                    result['format'] = 'BMP'
                    ImageMetaParser._parse_bmp(f, result)
                elif header[:8] == b'\x89PNG\r\n\x1a\n':
                    result['format'] = 'PNG'
                    ImageMetaParser._parse_png(f, result)
                elif header[:2] == b'\xff\xd8':
                    result['format'] = 'JPEG'
                    ImageMetaParser._parse_jpeg(f, result)
                elif header[:6] in (b'GIF87a', b'GIF89a'):
                    result['format'] = 'GIF'
                    ImageMetaParser._parse_gif(f, result)
                elif header[:4] in (b'II*\x00', b'MM\x00*'):
                    result['format'] = 'TIFF'
                    ImageMetaParser._parse_tiff(f, result)
                elif header[:1] == b'\x0a':
                    result['format'] = 'PCX'
                    ImageMetaParser._parse_pcx(f, result)
                else:
                    result['status'] = 'Неизвестный формат'
        except Exception:
            result['status'] = 'Файл поврежден'

        if PIL_AVAILABLE:
            ImageMetaParser._enrich_with_pillow(filepath, result)

        return result

    @staticmethod
    def _enrich_with_pillow(filepath, result):
        try:
            with Image.open(filepath) as img:
                if result['width'] is None or result['height'] is None:
                    result['width'], result['height'] = img.size
                if result['dpi'] in (None, 'N/A'):
                    dpi = img.info.get('dpi')
                    if dpi:
                        result['dpi'] = round(dpi[0], 2)
                if result['color_depth'] is None:
                    result['color_depth'] = len(img.getbands()) * 8
                if not result['format']:
                    result['format'] = img.format

                exif = img.getexif()
                if exif:
                    parts = []
                    make = exif.get(EXIF_TAGS.get('Make', 271))
                    model = exif.get(EXIF_TAGS.get('Model', 272))
                    dt = exif.get(EXIF_TAGS.get('DateTime', 306))
                    iso = exif.get(EXIF_TAGS.get('ISOSpeedRatings', 34855))
                    exposure = exif.get(EXIF_TAGS.get('ExposureTime', 33434))
                    fnumber = exif.get(EXIF_TAGS.get('FNumber', 33437))
                    focal = exif.get(EXIF_TAGS.get('FocalLength', 37386))

                    if make:
                        parts.append(f"Make={make}")
                    if model:
                        parts.append(f"Model={model}")
                    if dt:
                        parts.append(f"DateTime={dt}")
                    if iso:
                        parts.append(f"ISO={iso}")
                    if exposure:
                        parts.append(f"Exposure={exposure}")
                    if fnumber:
                        parts.append(f"FNumber={fnumber}")
                    if focal:
                        parts.append(f"Focal={focal}")

                    gps_ifd = exif.get_ifd(0x8825) if hasattr(exif, 'get_ifd') else {}
                    if gps_ifd:
                        lat = gps_ifd.get(2)
                        lon = gps_ifd.get(4)
                        if lat and lon:
                            parts.append(f"GPS=({lat},{lon})")

                    result['exif'] = '; '.join(parts)
        except Exception:
            pass

    @staticmethod
    def _parse_bmp(f, result):
        f.seek(0)
        data = f.read(54)
        if len(data) < 54:
            result['status'] = 'Файл поврежден'
            return
        file_size = struct.unpack_from('<I', data, 2)[0]
        if os.fstat(f.fileno()).st_size < file_size:
            result['status'] = 'Файл поврежден'
            return
        width = struct.unpack_from('<i', data, 18)[0]
        height = struct.unpack_from('<i', data, 22)[0]
        bpp = struct.unpack_from('<H', data, 28)[0]
        compression = struct.unpack_from('<I', data, 30)[0]
        xppm = struct.unpack_from('<i', data, 38)[0]
        result['width'] = abs(width)
        result['height'] = abs(height)
        result['color_depth'] = bpp
        if xppm > 0:
            result['dpi'] = round(xppm * 0.0254, 2)
        comp_map = {0: 'BI_RGB', 1: 'BI_RLE8', 2: 'BI_RLE4',
                    3: 'BI_BITFIELDS', 4: 'BI_JPEG', 5: 'BI_PNG'}
        result['compression'] = comp_map.get(compression, f'Unknown({compression})')
        if bpp <= 8:
            result['extra'] = f'Палитра: {1 << bpp} цветов'

    @staticmethod
    def _parse_png(f, result):
        f.seek(8)
        ihdr_found = False
        iend_found = False
        while True:
            chunk_header = f.read(8)
            if len(chunk_header) < 8:
                break
            length = struct.unpack('>I', chunk_header[:4])[0]
            chunk_type = chunk_header[4:8]

            if chunk_type == b'IHDR':
                ihdr_data = f.read(13)
                if len(ihdr_data) < 13:
                    result['status'] = 'Файл поврежден'
                    return
                width = struct.unpack('>I', ihdr_data[0:4])[0]
                height = struct.unpack('>I', ihdr_data[4:8])[0]
                bit_depth = ihdr_data[8]
                color_type = ihdr_data[9]
                interlace = ihdr_data[12]
                result['width'] = width
                result['height'] = height
                result['color_depth'] = bit_depth
                ct_map = {0: 'Grayscale', 2: 'Truecolor', 3: 'Indexed',
                          4: 'Grayscale+Alpha', 6: 'Truecolor+Alpha'}
                result['extra'] = (f'Тип цвета: {ct_map.get(color_type, color_type)}, '
                                   f'Interlace: {interlace}')
                f.read(4)
                ihdr_found = True
                continue

            if chunk_type == b'pHYs':
                phys = f.read(9)
                if len(phys) == 9:
                    ppu_x = struct.unpack('>I', phys[0:4])[0]
                    unit = phys[8]
                    if unit == 1 and ppu_x > 0:
                        result['dpi'] = round(ppu_x * 0.0254, 2)
                f.read(4)
                continue

            if chunk_type == b'IEND':
                iend_found = True
                break
            f.seek(length + 4, 1)

        if not ihdr_found or not iend_found:
            result['status'] = 'Файл поврежден'
        if result.get('dpi') is None:
            result['dpi'] = 'N/A'

    @staticmethod
    def _parse_jpeg(f, result):
        f.seek(2)
        while True:
            byte = f.read(1)
            if not byte:
                break
            if byte != b'\xff':
                continue
            marker = f.read(1)
            while marker == b'\xff':
                marker = f.read(1)
            if not marker:
                break
            m = marker[0]
            if m == 0xD9:
                break
            if m in (0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0x01):
                continue
            if m == 0xDA:
                break
            length_bytes = f.read(2)
            if len(length_bytes) < 2:
                break
            length = struct.unpack('>H', length_bytes)[0]
            if length < 2:
                break

            if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                     0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                seg = f.read(6)
                if len(seg) < 6:
                    result['status'] = 'Файл поврежден'
                    return
                precision = seg[0]
                height = struct.unpack('>H', seg[1:3])[0]
                width = struct.unpack('>H', seg[3:5])[0]
                num_components = seg[5]
                result['width'] = width
                result['height'] = height
                result['color_depth'] = precision * num_components
                sof_map = {0xC0: 'Baseline', 0xC1: 'Extended sequential',
                           0xC2: 'Progressive', 0xC3: 'Lossless'}
                result['compression'] = sof_map.get(m, f'SOF{m:02X}')
                f.seek(length - 8, 1)
            elif m == 0xE0:
                seg = f.read(length - 2)
                if len(seg) >= 12 and seg[:5] == b'JFIF\x00':
                    units = seg[7]
                    xdens = struct.unpack('>H', seg[8:10])[0]
                    if units == 1:
                        result['dpi'] = xdens
                    elif units == 2:
                        result['dpi'] = round(xdens * 2.54, 2)
                    else:
                        result['dpi'] = 'N/A'
            else:
                f.seek(length - 2, 1)

        if result['width'] is None:
            result['status'] = 'Файл поврежден'
        if result.get('dpi') is None:
            result['dpi'] = 'N/A'

    @staticmethod
    def _parse_gif(f, result):
        f.seek(0)
        data = f.read(13)
        if len(data) < 13:
            result['status'] = 'Файл поврежден'
            return
        width = struct.unpack('<H', data[6:8])[0]
        height = struct.unpack('<H', data[8:10])[0]
        packed = data[10]
        gct_flag = (packed >> 7) & 1
        color_res = ((packed >> 4) & 7) + 1
        gct_size = 2 ** ((packed & 7) + 1) if gct_flag else 0
        result['width'] = width
        result['height'] = height
        result['color_depth'] = color_res
        result['compression'] = 'LZW'
        result['dpi'] = 'N/A'
        if gct_flag:
            result['extra'] = f'Палитра: {gct_size} цветов'

    @staticmethod
    def _parse_tiff(f, result):
        f.seek(0)
        data = f.read(8)
        if len(data) < 8:
            result['status'] = 'Файл поврежден'
            return
        endian = '<' if data[:2] == b'II' else '>'
        magic = struct.unpack(endian + 'H', data[2:4])[0]
        if magic != 42:
            result['status'] = 'Файл поврежден'
            return
        ifd_offset = struct.unpack(endian + 'I', data[4:8])[0]
        f.seek(ifd_offset)
        num_entries_data = f.read(2)
        if len(num_entries_data) < 2:
            result['status'] = 'Файл поврежден'
            return
        num_entries = struct.unpack(endian + 'H', num_entries_data)[0]

        tags = {}
        for _ in range(num_entries):
            entry = f.read(12)
            if len(entry) < 12:
                break
            tag = struct.unpack(endian + 'H', entry[0:2])[0]
            typ = struct.unpack(endian + 'H', entry[2:4])[0]
            count = struct.unpack(endian + 'I', entry[4:8])[0]
            value_bytes = entry[8:12]

            if typ == 3 and count == 1:
                tags[tag] = struct.unpack(endian + 'H', value_bytes[:2])[0]
            elif typ == 4 and count == 1:
                tags[tag] = struct.unpack(endian + 'I', value_bytes)[0]
            elif typ == 5 and count == 1:
                offset = struct.unpack(endian + 'I', value_bytes)[0]
                cur = f.tell()
                f.seek(offset)
                num = struct.unpack(endian + 'I', f.read(4))[0]
                den = struct.unpack(endian + 'I', f.read(4))[0]
                f.seek(cur)
                tags[tag] = (num / den) if den else 0.0
            else:
                tags[tag] = value_bytes

        width = tags.get(256)
        height = tags.get(257)
        bits = tags.get(258)
        compression = tags.get(259)
        xres = tags.get(282)
        res_unit = tags.get(296)

        result['width'] = width
        result['height'] = height

        if isinstance(bits, int):
            result['color_depth'] = bits
        elif isinstance(bits, bytes) and len(bits) >= 2:
            result['color_depth'] = struct.unpack(endian + 'H', bits[:2])[0]
        else:
            result['color_depth'] = bits

        comp_map = {1: 'None', 2: 'CCITT RLE', 5: 'LZW', 6: 'JPEG',
                    7: 'JPEG', 8: 'Deflate', 32773: 'PackBits'}
        result['compression'] = comp_map.get(compression, str(compression)) \
            if isinstance(compression, int) else str(compression)

        if isinstance(xres, float) and res_unit == 2:
            result['dpi'] = round(xres, 2)
        elif isinstance(xres, float) and res_unit == 3:
            result['dpi'] = round(xres * 2.54, 2)
        elif isinstance(xres, int) and res_unit == 2:
            result['dpi'] = xres
        else:
            result['dpi'] = 'N/A'

        if result['width'] is None or result['height'] is None:
            result['status'] = 'Файл поврежден'

    @staticmethod
    def _parse_pcx(f, result):
        f.seek(0)
        data = f.read(128)
        if len(data) < 128 or data[0] != 0x0A:
            result['status'] = 'Файл поврежден'
            return
        version = data[1]
        encoding = data[2]
        bpp = data[3]
        xmin = struct.unpack('<H', data[4:6])[0]
        ymin = struct.unpack('<H', data[6:8])[0]
        xmax = struct.unpack('<H', data[8:10])[0]
        ymax = struct.unpack('<H', data[10:12])[0]
        hdpi = struct.unpack('<H', data[12:14])[0]
        result['width'] = xmax - xmin + 1
        result['height'] = ymax - ymin + 1
        result['color_depth'] = bpp * 8 if bpp <= 8 else bpp
        result['dpi'] = hdpi if hdpi > 0 else 'N/A'
        result['compression'] = {0: 'Raw', 1: 'RLE'}.get(encoding, str(encoding))
        result['extra'] = f'Версия: {version}, Бит на плоскость: {bpp}'


class App:
    def __init__(self, root):
        self.root = root
        self.root.title('Image Metadata Parser')
        self.root.geometry('1400x750')
        self.folder = tk.StringVar()
        self.results = []
        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=5)
        top.pack(fill=tk.X)
        ttk.Entry(top, textvariable=self.folder, width=70).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text='Обзор', command=self.browse).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text='Сканировать', command=self.scan).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text='Экспорт CSV', command=self.export_csv).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text='Экспорт JSON', command=self.export_json).pack(side=tk.LEFT, padx=2)

        self.progress = ttk.Progressbar(self.root, mode='determinate')
        self.progress.pack(fill=tk.X, padx=5, pady=2)

        self.status_label = ttk.Label(
            self.root,
            text=f'Готов. Pillow: {"есть" if PIL_AVAILABLE else "НЕТ (EXIF недоступен)"}'
        )
        self.status_label.pack(anchor=tk.W, padx=5)

        cols = ('filename', 'format', 'width', 'height', 'dpi',
                'color_depth', 'compression', 'exif', 'status', 'extra')
        self.tree = ttk.Treeview(self.root, columns=cols, show='headings')
        headers = {
            'filename': 'Файл', 'format': 'Формат', 'width': 'Ширина',
            'height': 'Высота', 'dpi': 'DPI', 'color_depth': 'Глубина',
            'compression': 'Сжатие', 'exif': 'EXIF', 'status': 'Статус',
            'extra': 'Доп.'
        }
        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=110, anchor=tk.W)
        self.tree.column('filename', width=200)
        self.tree.column('exif', width=300)
        self.tree.column('extra', width=200)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        vsb = ttk.Scrollbar(self.tree, orient='vertical', command=self.tree.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=vsb.set)

    def browse(self):
        d = filedialog.askdirectory()
        if d:
            self.folder.set(d)

    def scan(self):
        folder = self.folder.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror('Ошибка', 'Укажите корректную папку')
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results = []

        files = []
        for root_dir, _, filenames in os.walk(folder):
            for fn in filenames:
                if fn.lower().endswith(SUPPORTED_EXT):
                    files.append(os.path.join(root_dir, fn))

        total = len(files)
        if total == 0:
            self.status_label.config(text='Файлы не найдены')
            return
        self.progress['maximum'] = total
        self.progress['value'] = 0
        self.status_label.config(text=f'Обработка {total} файлов...')
        threading.Thread(target=self._process_files,
                         args=(files, total), daemon=True).start()

    def _process_files(self, files, total):
        results = []
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
            futures = {executor.submit(ImageMetaParser.parse_file, fp): fp for fp in files}
            done = 0
            for future in as_completed(futures):
                try:
                    res = future.result()
                except Exception:
                    res = {'filename': os.path.basename(futures[future]),
                           'status': 'Ошибка', 'width': None, 'height': None,
                           'dpi': None, 'color_depth': None, 'compression': None,
                           'exif': '', 'extra': '', 'format': None}
                results.append(res)
                done += 1
                if done % 10 == 0 or done == total:
                    self.root.after(0, self._update_progress, done, total)
        self.root.after(0, self._display_results, results)

    def _update_progress(self, done, total):
        self.progress['value'] = done
        self.status_label.config(text=f'Обработано {done} из {total}')

    def _display_results(self, results):
        results.sort(key=lambda x: x['filename'])
        self.results = results
        for r in results:
            self.tree.insert('', tk.END, values=(
                r.get('filename', ''),
                r.get('format', ''),
                r.get('width', ''),
                r.get('height', ''),
                r.get('dpi', ''),
                r.get('color_depth', ''),
                r.get('compression', ''),
                r.get('exif', ''),
                r.get('status', ''),
                r.get('extra', '')
            ))
        self.status_label.config(text=f'Готово. Обработано {len(results)} файлов.')

    def export_csv(self):
        if not self.results:
            messagebox.showinfo('Экспорт', 'Нет данных для экспорта')
            return
        path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV', '*.csv')])
        if not path:
            return
        fields = ['filename', 'format', 'width', 'height', 'dpi',
                  'color_depth', 'compression', 'exif', 'status', 'extra']
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as fp:
                writer = csv.DictWriter(fp, fieldnames=fields,
                                        extrasaction='ignore')
                writer.writeheader()
                for r in self.results:
                    writer.writerow(r)
            messagebox.showinfo('Экспорт', f'Сохранено: {path}')
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))

    def export_json(self):
        if not self.results:
            messagebox.showinfo('Экспорт', 'Нет данных для экспорта')
            return
        path = filedialog.asksaveasfilename(
            defaultextension='.json',
            filetypes=[('JSON', '*.json')])
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as fp:
                json.dump(self.results, fp, ensure_ascii=False, indent=2)
            messagebox.showinfo('Экспорт', f'Сохранено: {path}')
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))


if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()