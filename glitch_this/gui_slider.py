#!/usr/bin/env python3
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import math
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class GlitchSliderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("裸眼3D空间壁纸制作器")
        self.root.geometry("1000x800")
        self.root.configure(bg='#1a1a2e')

        self.images = []  # 多张素材图
        self.depth_map = None  # 深度图
        self.display_image = None
        self.canvas_width = 900
        self.canvas_height = 500

        # 鼠标位置 (归一化 -0.5 到 0.5)
        self.mouse_x = 0.0
        self.mouse_y = 0.0
        self.mouse_in_canvas = False

        # 动画相关
        self.animation_enabled = False
        self.animation_thread = None
        self.stop_animation = False

        self.setup_ui()
        self.start_mouse_tracking()

    def setup_ui(self):
        # 标题
        title = tk.Label(self.root, text="裸眼3D空间壁纸制作器 (鼠标控制视角)", font=("微软雅黑", 20, "bold"),
                        bg='#1a1a2e', fg='#00d9ff')
        title.pack(pady=10)

        # 提示
        hint = tk.Label(self.root, text="移动鼠标查看3D空间效果 | 前景不动，后景随鼠标移动",
                       font=("微软雅黑", 11), bg='#1a1a2e', fg='#888')
        hint.pack()

        # 图片显示区域
        self.canvas = tk.Canvas(self.root, bg='#0f0f23', width=self.canvas_width,
                                height=self.canvas_height, highlightthickness=0,
                                cursor='crosshair')
        self.canvas.pack(pady=10)

        # 鼠标位置显示
        self.mouse_label = tk.Label(self.root, text="鼠标位置: (0, 0)", font=("Consolas", 10),
                                    bg='#1a1a2e', fg='#00ff88')
        self.mouse_label.pack()

        # 控制面板
        control_frame = ttk.LabelFrame(self.root, text="参数调节面板", padding=15)
        control_frame.pack(fill='x', padx=10, pady=5)

        # 图片加载
        row0 = ttk.Frame(control_frame)
        row0.pack(fill='x', pady=8)

        ttk.Button(row0, text="加载素材图1", command=lambda: self.load_image(0)).pack(side='left', padx=5)
        self.btn_img1 = ttk.Button(row0, text="加载素材图2", command=lambda: self.load_image(1), state='disabled')
        self.btn_img1.pack(side='left', padx=5)
        self.btn_img2 = ttk.Button(row0, text="加载素材图3", command=lambda: self.load_image(2), state='disabled')
        self.btn_img2.pack(side='left', padx=5)
        self.btn_img3 = ttk.Button(row0, text="加载素材图4", command=lambda: self.load_image(3), state='disabled')
        self.btn_img3.pack(side='left', padx=5)
        ttk.Button(row0, text="加载深度图", command=self.load_depth_map).pack(side='left', padx=10)
        ttk.Button(row0, text="清空全部", command=self.clear_all).pack(side='left', padx=5)

        self.status_label = tk.Label(row0, text="未加载图片", fg='#888', bg='#1a1a2e')
        self.status_label.pack(side='left', padx=15)

        # 视差强度
        row1 = ttk.Frame(control_frame)
        row1.pack(fill='x', pady=8)

        ttk.Label(row1, text="视差强度:", font=("微软雅黑", 10)).pack(side='left', padx=5)
        self.parallax_var = tk.IntVar(value=50)
        parallax_scale = ttk.Scale(row1, from_=0, to=100, orient='h',
                                   variable=self.parallax_var, command=self.update_preview)
        parallax_scale.pack(side='left', fill='x', expand=True, padx=5)
        self.parallax_label = ttk.Label(row1, text="50")
        self.parallax_label.pack(side='left', padx=5)

        # 前景固定强度
        row2 = ttk.Frame(control_frame)
        row2.pack(fill='x', pady=8)

        ttk.Label(row2, text="前景固定:", font=("微软雅黑", 10)).pack(side='left', padx=5)
        self.front_fixed_var = tk.IntVar(value=80)
        front_scale = ttk.Scale(row2, from_=0, to=100, orient='h',
                                variable=self.front_fixed_var, command=self.update_preview)
        front_scale.pack(side='left', fill='x', expand=True, padx=5)
        self.front_fixed_label = ttk.Label(row2, text="80")
        self.front_fixed_label.pack(side='left', padx=5)

        # 背景深度
        row3 = ttk.Frame(control_frame)
        row3.pack(fill='x', pady=8)

        ttk.Label(row3, text="背景深度:", font=("微软雅黑", 10)).pack(side='left', padx=5)
        self.bg_depth_var = tk.IntVar(value=80)
        bg_scale = ttk.Scale(row3, from_=0, to=100, orient='h',
                             variable=self.bg_depth_var, command=self.update_preview)
        bg_scale.pack(side='left', fill='x', expand=True, padx=5)
        self.bg_depth_label = ttk.Label(row3, text="80")
        self.bg_depth_label.pack(side='left', padx=5)

        # Z轴位移
        row4 = ttk.Frame(control_frame)
        row4.pack(fill='x', pady=8)

        ttk.Label(row4, text="Z轴位移:", font=("微软雅黑", 10)).pack(side='left', padx=5)
        self.z_offset_var = tk.IntVar(value=0)
        z_scale = ttk.Scale(row4, from_=-100, to=100, orient='h',
                           variable=self.z_offset_var, command=self.update_preview)
        z_scale.pack(side='left', fill='x', expand=True, padx=5)
        self.z_offset_label = ttk.Label(row4, text="0")
        self.z_offset_label.pack(side='left', padx=5)

        # 效果选项
        row5 = ttk.Frame(control_frame)
        row5.pack(fill='x', pady=8)

        self.vignette_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row5, text="暗角", variable=self.vignette_var,
                       command=self.update_preview).pack(side='left', padx=10)

        self.glow_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row5, text="光晕", variable=self.glow_var,
                       command=self.update_preview).pack(side='left', padx=10)

        self.animate_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row5, text="自动摆头", variable=self.animate_var,
                       command=self.toggle_animation).pack(side='left', padx=10)

        # 动画速度
        ttk.Label(row5, text="速度:", font=("微软雅黑", 10)).pack(side='left', padx=5)
        self.anim_speed_var = tk.IntVar(value=30)
        ttk.Spinbox(row5, from_=5, to=100, width=5, textvariable=self.anim_speed_var,
                   command=self.update_preview).pack(side='left', padx=5)

        # 导出按钮
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="导出静态壁纸", command=self.export_wallpaper,
                  width=15).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="导出动画GIF", command=self.export_gif,
                  width=15).pack(side='left', padx=10)

    def start_mouse_tracking(self):
        """启动鼠标追踪"""
        self.canvas.bind('<Motion>', self.on_mouse_move)
        self.canvas.bind('<Enter>', self.on_mouse_enter)
        self.canvas.bind('<Leave>', self.on_mouse_leave)

    def on_mouse_enter(self, event):
        self.mouse_in_canvas = True

    def on_mouse_leave(self, event):
        self.mouse_in_canvas = False
        self.mouse_x = 0.0
        self.mouse_y = 0.0
        self.update_preview()

    def on_mouse_move(self, event):
        """鼠标移动时更新位置并重绘"""
        if self.mouse_in_canvas:
            # 归一化鼠标位置 (-0.5 到 0.5)
            self.mouse_x = (event.x - self.canvas_width // 2) / (self.canvas_width // 2)
            self.mouse_y = (event.y - self.canvas_height // 2) / (self.canvas_height // 2)

            # 限制范围
            self.mouse_x = max(-0.5, min(0.5, self.mouse_x))
            self.mouse_y = max(-0.5, min(0.5, self.mouse_y))

            self.mouse_label.config(text=f"鼠标位置: ({self.mouse_x:.2f}, {self.mouse_y:.2f})")
            self.update_preview()

    def toggle_animation(self):
        """切换自动摆头动画"""
        if self.animate_var.get():
            self.animation_enabled = True
            self.stop_animation = False
            self.run_animation()
        else:
            self.animation_enabled = False
            self.stop_animation = True

    def run_animation(self):
        """自动摆头动画"""
        def animate():
            import time
            t = 0
            while self.animation_enabled and not self.stop_animation:
                # 正弦波摆动
                self.mouse_x = math.sin(t * 0.02) * 0.4
                self.mouse_y = math.sin(t * 0.013) * 0.25
                self.root.after(16, self.update_preview)
                time.sleep(0.016)
                t += 1

        if self.animation_thread is None or not self.animation_thread.is_alive():
            self.animation_thread = threading.Thread(target=animate, daemon=True)
            self.animation_thread.start()

    def load_image(self, index):
        path = filedialog.askopenfilename(filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp")])
        if path:
            img = Image.open(path).copy()
            while len(self.images) <= index:
                self.images.append(None)
            self.images[index] = img
            self.update_status()
            self.update_preview()

    def load_depth_map(self):
        path = filedialog.askopenfilename(filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp")])
        if path:
            self.depth_map = Image.open(path).copy()
            self.depth_map = self.depth_map.convert('L')
            self.update_status()
            self.update_preview()

    def clear_all(self):
        self.images = []
        self.depth_map = None
        self.btn_img1.config(state='disabled')
        self.btn_img2.config(state='disabled')
        self.btn_img3.config(state='disabled')
        self.update_status()
        self.canvas.delete('all')
        self.canvas.create_text(self.canvas_width//2, self.canvas_height//2,
                              text="请加载素材图片", fill='#555', font=("微软雅黑", 16))

    def update_status(self):
        count = len([x for x in self.images if x is not None])
        depth_status = "已" if self.depth_map else "未"
        self.status_label.config(text=f"素材图: {count}张 | 深度图: {depth_status}加载", fg='#00ff88')

        if count >= 1:
            self.btn_img1.config(state='normal')
        if count >= 2:
            self.btn_img2.config(state='normal')
        if count >= 3:
            self.btn_img3.config(state='normal')

    def update_preview(self, *args):
        self.parallax_label.config(text=str(self.parallax_var.get()))
        self.front_fixed_label.config(text=str(self.front_fixed_var.get()))
        self.bg_depth_label.config(text=str(self.bg_depth_var.get()))
        self.z_offset_label.config(text=str(self.z_offset_var.get()))

        if not self.images or self.images[0] is None:
            self.canvas.delete('all')
            self.canvas.create_text(self.canvas_width//2, self.canvas_height//2,
                                  text="请加载素材图片", fill='#555', font=("微软雅黑", 16))
            return

        result = self.create_mouse_3d_effect()

        if result:
            result = result.resize((self.canvas_width, self.canvas_height), Image.Resampling.LANCZOS)
            self.display_image = ImageTk.PhotoImage(result)
            self.canvas.delete('all')
            self.canvas.create_image(0, 0, anchor='nw', image=self.display_image)

    def create_mouse_3d_effect(self):
        """根据鼠标位置创建3D空间效果"""
        base_img = self.images[0].copy()
        width, height = base_img.size

        parallax = self.parallax_var.get()
        front_fixed = self.front_fixed_var.get() / 100  # 前景固定比例
        bg_depth = self.bg_depth_var.get() / 100  # 背景深度比例
        z_offset = self.z_offset_var.get() / 100

        # 获取鼠标归一化偏移 (限制最大视差)
        max_offset_x = self.mouse_x * parallax
        max_offset_y = self.mouse_y * parallax * 0.6  # 垂直视差稍小

        output = Image.new('RGBA', (width, height), (0, 0, 0, 255))

        # 如果有深度图，使用深度图计算
        if self.depth_map:
            result = self.create_depth_based_effect(base_img, width, height,
                                                     max_offset_x, max_offset_y,
                                                     front_fixed, bg_depth)
            result = self.add_effects(result)
            return result.convert('RGB')

        # 使用多层图片的视差效果
        num_layers = len([x for x in self.images if x])

        # 前景层（最前）- 固定不动或几乎不动
        if num_layers >= 1:
            front_layer = self.images[0].copy()
            front_layer = front_layer.resize((width, height), Image.Resampling.LANCZOS)

            # 前景几乎不动
            front_offset_x = int(max_offset_x * (1 - front_fixed))
            front_offset_y = int(max_offset_y * (1 - front_fixed))

            temp = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            temp.paste(front_layer, (front_offset_x, front_offset_y),
                      front_layer if front_layer.mode == 'RGBA' else None)
            output = Image.alpha_composite(output, temp)

        # 中间层
        if num_layers >= 2:
            mid_layer = self.images[1].copy()
            mid_layer = mid_layer.resize((width, height), Image.Resampling.LANCZOS)

            mid_depth = 0.4 * bg_depth + z_offset
            mid_offset_x = int(max_offset_x * mid_depth)
            mid_offset_y = int(max_offset_y * mid_depth)

            # 添加模糊模拟景深
            blur_radius = int((1 - mid_depth) * parallax / 8)
            if blur_radius > 0:
                mid_layer = mid_layer.filter(ImageFilter.GaussianBlur(radius=blur_radius))

            temp = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            temp.paste(mid_layer, (mid_offset_x, mid_offset_y),
                      mid_layer if mid_layer.mode == 'RGBA' else None)
            output = Image.alpha_composite(output, temp)

        # 后景层 - 移动最多
        if num_layers >= 3:
            back_layer = self.images[2].copy()
            back_layer = back_layer.resize((width, height), Image.Resampling.LANCZOS)

            back_depth = 0.7 * bg_depth + z_offset
            back_offset_x = int(max_offset_x * back_depth)
            back_offset_y = int(max_offset_y * back_depth)

            # 后景模糊更强
            blur_radius = int((1 - back_depth) * parallax / 5)
            if blur_radius > 0:
                back_layer = back_layer.filter(ImageFilter.GaussianBlur(radius=blur_radius))

            temp = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            temp.paste(back_layer, (back_offset_x, back_offset_y),
                      back_layer if back_layer.mode == 'RGBA' else None)
            output = Image.alpha_composite(output, temp)

        # 最远背景
        if num_layers >= 4:
            far_layer = self.images[3].copy()
            far_layer = far_layer.resize((width, height), Image.Resampling.LANCZOS)

            far_depth = 1.0 * bg_depth + z_offset
            far_offset_x = int(max_offset_x * far_depth)
            far_offset_y = int(max_offset_y * far_depth)

            # 最远背景模糊最强
            blur_radius = int((1 - far_depth * 0.5) * parallax / 4)
            if blur_radius > 0:
                far_layer = far_layer.filter(ImageFilter.GaussianBlur(radius=blur_radius))

            temp = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            temp.paste(far_layer, (far_offset_x, far_offset_y),
                      far_layer if far_layer.mode == 'RGBA' else None)
            output = Image.alpha_composite(output, temp)

        # 如果只有一张图，模拟单图3D效果
        if num_layers == 1:
            result = self.create_single_image_3d(base_img, width, height,
                                                  max_offset_x, max_offset_y,
                                                  front_fixed, bg_depth)
            result = self.add_effects(result)
            return result.convert('RGB')

        output = self.add_effects(output)
        return output.convert('RGB')

    def create_depth_based_effect(self, base_img, width, height,
                                   offset_x, offset_y,
                                   front_fixed, bg_depth):
        """基于深度图的3D效果"""
        if self.depth_map:
            depth = self.depth_map.copy()
            depth = depth.resize((width, height), Image.Resampling.LANCZOS)
        else:
            depth = Image.new('L', (width, height), 128)

        rgba_img = base_img.convert('RGBA')
        output = Image.new('RGBA', (width, height), (0, 0, 0, 255))
        depth_pixels = depth.load()

        for y in range(height):
            for x in range(width):
                d = depth_pixels[x, y] / 255.0  # 0=近, 1=远

                # 前景固定，后景移动多
                move_factor = d * bg_depth  # 远处移动多
                fx = (1 - front_fixed) * (1 - d)  # 前景几乎不动
                fx = fx + move_factor

                src_x = max(0, min(width - 1, int(x - offset_x * fx)))
                src_y = max(0, min(height - 1, int(y - offset_y * fx * 0.6)))

                output.putpixel((x, y), rgba_img.getpixel((src_x, src_y)))

        return output

    def create_single_image_3d(self, base_img, width, height,
                               offset_x, offset_y,
                               front_fixed, bg_depth):
        """单图模拟3D空间效果（使用边缘渐变模拟景深）"""
        rgba_img = base_img.convert('RGBA')
        output = Image.new('RGBA', (width, height), (0, 0, 0, 255))

        # 创建模拟深度：中心近，边缘远
        cx, cy = width // 2, height // 2
        max_dist = math.sqrt(cx**2 + cy**2)

        for y in range(height):
            for x in range(width):
                # 计算到中心距离
                dist = math.sqrt((x - cx)**2 + (y - cy)**2)
                d = min(1.0, dist / max_dist)  # 边缘=1(远), 中心=0(近)

                # 近处(中心)固定，远处(边缘)移动
                move_factor = d * bg_depth
                fx = (1 - front_fixed) * d + move_factor

                src_x = max(0, min(width - 1, int(x - offset_x * fx)))
                src_y = max(0, min(height - 1, int(y - offset_y * fx * 0.6)))

                output.putpixel((x, y), rgba_img.getpixel((src_x, src_y)))

        return output

    def add_effects(self, img):
        """添加特效"""
        width, height = img.size

        if self.vignette_var.get():
            vignette = Image.new('L', (width, height), 255)
            draw = ImageDraw.Draw(vignette)
            max_r = min(width, height) // 2
            for i in range(max_r // 2):
                alpha = int(180 * i / (max_r // 2))
                draw.ellipse([i, i, width-i, height-i], fill=255-alpha)
            vignette = vignette.filter(ImageFilter.GaussianBlur(radius=max_r//4))
            if img.mode == 'RGB':
                img.paste(vignette, mask=vignette)
            elif img.mode == 'RGBA':
                vign = Image.new('RGBA', (width, height), (0,0,0,0))
                vign.paste(vignette, mask=vignette)
                img = Image.alpha_composite(img, vign)

        if self.glow_var.get():
            glow = img.copy()
            if glow.mode != 'RGB':
                glow = glow.convert('RGB')
            glow = glow.filter(ImageFilter.GaussianBlur(radius=20))
            img = Image.blend(img, glow, 0.3)

        return img

    def export_wallpaper(self):
        if not self.images or self.images[0] is None:
            messagebox.showwarning("警告", "请先加载素材图片")
            return

        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG图片", "*.png")])
        if path:
            try:
                # 使用中心位置导出静态图
                old_mouse_x, old_mouse_y = self.mouse_x, self.mouse_y
                self.mouse_x, self.mouse_y = 0, 0

                result = self.create_mouse_3d_effect()
                result.save(path)

                self.mouse_x, self.mouse_y = old_mouse_x, old_mouse_y

                messagebox.showinfo("成功", f"壁纸已保存:\n{path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")

    def export_gif(self):
        if not self.images or self.images[0] is None:
            messagebox.showwarning("警告", "请先加载素材图片")
            return

        path = filedialog.asksaveasfilename(defaultextension=".gif",
                                            filetypes=[("GIF动画", "*.gif")])
        if path:
            try:
                frames = []
                num_frames = 30
                speed = self.anim_speed_var.get()

                for i in range(num_frames):
                    # 模拟摆头动画
                    self.mouse_x = math.sin(i / num_frames * 2 * math.pi) * 0.35
                    self.mouse_y = math.sin(i / num_frames * 2 * math.pi * 0.5) * 0.2
                    result = self.create_mouse_3d_effect()
                    result = result.resize((800, 450), Image.Resampling.LANCZOS)
                    frames.append(result)

                frames[0].save(path, format="GIF", append_images=frames[1:],
                             save_all=True, duration=speed, loop=0)
                messagebox.showinfo("成功", f"动画GIF已保存:\n{path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")


if __name__ == '__main__':
    root = tk.Tk()
    app = GlitchSliderApp(root)
    root.mainloop()
